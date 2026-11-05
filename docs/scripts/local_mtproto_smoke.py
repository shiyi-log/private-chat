#!/usr/bin/env python3
"""Local-only MTProto acceptance check for the isolated Private Chat stack."""

import argparse
import asyncio
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parents[2]
PHONES = ("12025550101", "12025550102")


def rsa_pad_encrypt(data, key):
    """MTProto RSA_PAD from https://core.telegram.org/mtproto/auth_key#4-1."""
    from telethon.crypto import AES

    if len(data) > 144 or key.n.bit_length() != 2048:
        raise ValueError("RSA_PAD requires at most 144 bytes and a 2048-bit key")
    padded = data + os.urandom(192 - len(data))
    while True:
        temp_key = os.urandom(32)
        with_hash = padded[::-1] + hashlib.sha256(temp_key + padded).digest()
        encrypted = AES.encrypt_ige(with_hash, temp_key, bytes(32))
        mask = hashlib.sha256(encrypted).digest()
        key_xor = bytes(left ^ right for left, right in zip(temp_key, mask))
        candidate = int.from_bytes(key_xor + encrypted, "big")
        if candidate < key.n:
            return pow(candidate, key.e, key.n).to_bytes(256, "big")


def read_otp(outbox, phone, code_hash):
    for path in outbox.glob("*.json"):
        try:
            record = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        if not isinstance(record, dict):
            continue
        expiry, code = record.get("expires_at"), record.get("code")
        if not isinstance(expiry, (int, float)) or not isinstance(code, str):
            continue
        if (record.get("phone_number") == phone
                and record.get("code_hash") == code_hash
                and expiry > time.time()
                and re.fullmatch(r"\d{5}", code)):
            return code
    raise LookupError("No current local OTP delivery matches this transaction")


def validate_endpoint(dc_id, host, port):
    # Match the IPv4 client mode exactly. Upstream Telethon substitutes its
    # public default DC if an IPv4 client is handed an IPv6 session address.
    if dc_id != 1 or host != "127.0.0.1" or port != 10443:
        raise ValueError("Protocol smoke is restricted to DC 1 at 127.0.0.1:10443")


async def wait_for_message(client, peer, predicate, timeout=15):
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        history = await client.get_messages(peer, limit=20)
        for message in history:
            if predicate(message):
                return message
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError("Expected message missing from peer history after delivery timeout")
        await asyncio.sleep(0.25)


async def run():
    from telethon import TelegramClient, functions, types, errors
    from telethon.crypto import rsa
    from telethon.sessions import MemorySession
    from telethon.tl.alltlobjects import LAYER

    if LAYER != 224:
        raise RuntimeError("Install the pinned smoke requirements (Telethon layer 224); server supports layers through 225")

    class LocalClient(TelegramClient):
        async def get_me(self, *args, **kwargs):
            # Teamgram answers AUTH_RESTART to users.getUsers before login,
            # while Telethon's startup probe expects an UnauthorizedError.
            # This check uses explicit auth RPCs and only probes after success.
            if not getattr(self, "_local_login_complete", False):
                return None
            return await super().get_me(*args, **kwargs)

        async def _get_dc(self, dc_id, *args, **kwargs):
            dc = await super()._get_dc(dc_id, *args, **kwargs)
            validate_endpoint(dc.id, dc.ip_address, dc.port)
            return dc

        async def _switch_dc(self, new_dc):
            validate_endpoint(new_dc, "127.0.0.1", 10443)
            return await super()._switch_dc(new_dc)

        async def _create_exported_sender(self, dc_id):
            # A smoke check must never export credentials to a public DC.
            raise ValueError("Exported senders are not enabled in local smoke")

    source = (SUITE / "desktop/Telegram/SourceFiles/mtproto/mtproto_dc_options.cpp").read_text()
    pem = re.search(r"-----BEGIN RSA PUBLIC KEY-----(.*?)-----END RSA PUBLIC KEY-----", source, re.S)
    if not pem:
        raise ValueError("Desktop private server public key not found")
    public_key = "-----BEGIN RSA PUBLIC KEY-----\n" + pem[1].replace("\\n", "").replace("\\", "").strip() + "\n-----END RSA PUBLIC KEY-----"
    rsa._server_keys.clear()
    rsa.add_key(public_key, old=False)
    # The pinned Telethon uses legacy SHA1 padding. Only this isolated smoke
    # process adapts its encrypt callback to the server's modern RSA_PAD.
    def encrypt(fingerprint, data, *, use_old=False):
        key, old = rsa._server_keys.get(fingerprint, (None, None))
        if key is None or (old and not use_old):
            return None
        return rsa_pad_encrypt(data, key)

    rsa.encrypt = encrypt
    api_id = int(os.getenv("PRIVATE_CHAT_SMOKE_API_ID", "100001"))
    api_hash = os.getenv("PRIVATE_CHAT_SMOKE_API_HASH", "0123456789abcdef0123456789abcdef")
    outbox = SUITE / "server/data/local-integration/otp"
    clients = []
    report = {"scope": "local protocol clients; native client UI not covered", "endpoint": "127.0.0.1:10443", "checks": []}
    try:
        for index, phone in enumerate(PHONES):
            print(f"Connecting local protocol client {index + 1}", file=sys.stderr, flush=True)
            session = MemorySession()
            session.set_dc(1, "127.0.0.1", 10443)
            client = LocalClient(session, api_id, api_hash, timeout=10, connection_retries=1, request_retries=0, auto_reconnect=False, receive_updates=False)
            clients.append(client)
            await client.connect()
            print(f"Connected client {index + 1}; requesting local test OTP", file=sys.stderr, flush=True)
            validate_endpoint(client.session.dc_id, client.session.server_address, client.session.port)
            sent = await client(functions.auth.SendCodeRequest(phone, api_id, api_hash, types.CodeSettings()))
            code = read_otp(outbox, phone, sent.phone_code_hash)
            try:
                auth = await client(functions.auth.SignInRequest(phone, sent.phone_code_hash, phone_code=code))
                if isinstance(auth, types.auth.AuthorizationSignUpRequired):
                    auth = await client(functions.auth.SignUpRequest(phone, sent.phone_code_hash, "Local", f"Smoke {index + 1}"))
            except errors.PhoneNumberUnoccupiedError:
                auth = await client(functions.auth.SignUpRequest(phone, sent.phone_code_hash, "Local", f"Smoke {index + 1}"))
            client._authorized = True
            client._local_login_complete = True
            report["checks"].append({"name": f"login_{index + 1}", "passed": True, "user_id": auth.user.id})
            print(f"Local login {index + 1} passed", file=sys.stderr, flush=True)

        peers = []
        for index, client in enumerate(clients):
            imported = await client(functions.contacts.ImportContactsRequest([types.InputPhoneContact(1, PHONES[1-index], "Local", f"Smoke {2-index}")]))
            peer = imported.users[0]
            peers.append(types.InputPeerUser(peer.id, peer.access_hash))
        marker = f"Private Chat local smoke {time.time_ns()}"
        for index, client in enumerate(clients):
            text = f"{marker} direction {index + 1}"
            await client.send_message(peers[index], text)
            await wait_for_message(clients[1-index], peers[1-index], lambda message: message.message == text)
            report["checks"].append({"name": f"text_roundtrip_{index + 1}", "passed": True})
            print(f"Text direction {index + 1} passed", file=sys.stderr, flush=True)

        payload = (marker + "\nlocal file roundtrip\n").encode()
        attachment = io.BytesIO(payload)
        attachment.name = "private-chat-smoke.txt"
        await clients[0].send_file(peers[0], attachment, force_document=True, caption=marker)
        message = await wait_for_message(clients[1], peers[1], lambda item: item.document and item.message == marker)
        downloaded = await clients[1].download_media(message, file=bytes)
        if downloaded != payload:
            raise AssertionError("Downloaded attachment differs from uploaded bytes")
        report["checks"].append({"name": "file_roundtrip", "passed": True, "bytes": len(payload), "sha256": hashlib.sha256(downloaded).hexdigest()})
        report["passed"] = True
        return report
    finally:
        for client in clients:
            await client.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-local-test", action="store_true", help="Explicitly create/use the two allowlisted local test accounts")
    args = parser.parse_args()
    if not args.run_local_test:
        parser.error("Pass --run-local-test to create/use local test accounts")
    print(json.dumps(asyncio.run(asyncio.wait_for(run(), timeout=180)), indent=2))


if __name__ == "__main__":
    main()
