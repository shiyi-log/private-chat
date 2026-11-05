import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'local_mtproto_smoke.py'

class LocalBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('local_mtproto_smoke', SCRIPT)
        cls.smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.smoke)

    def test_otp_is_selected_by_transaction_not_latest_file(self):
        import json
        import time
        with tempfile.TemporaryDirectory() as directory:
            outbox = Path(directory)
            (outbox / 'wrong.json').write_text(json.dumps({'phone_number': '12025550101', 'code_hash': 'other', 'code': '99999', 'expires_at': int(time.time()) + 60}))
            (outbox / 'right.json').write_text(json.dumps({'phone_number': '12025550101', 'code_hash': 'wanted', 'code': '24680', 'expires_at': int(time.time()) + 60}))
            self.assertEqual(self.smoke.read_otp(outbox, '12025550101', 'wanted'), '24680')

    def test_expired_or_wrong_phone_delivery_is_rejected(self):
        import json
        import time
        with tempfile.TemporaryDirectory() as directory:
            outbox = Path(directory)
            (outbox / 'expired.json').write_text(json.dumps({'phone_number': '12025550101', 'code_hash': 'wanted', 'code': '24680', 'expires_at': int(time.time()) - 1}))
            (outbox / 'other.json').write_text(json.dumps({'phone_number': '12025550102', 'code_hash': 'wanted', 'code': '13579', 'expires_at': int(time.time()) + 60}))
            with self.assertRaises(LookupError):
                self.smoke.read_otp(outbox, '12025550101', 'wanted')

    def test_malformed_outbox_records_do_not_hide_valid_transaction(self):
        import json
        import time
        with tempfile.TemporaryDirectory() as directory:
            outbox = Path(directory)
            records = [[], {'phone_number': '12025550101', 'code_hash': 'wanted',
                            'expires_at': 'not-a-number', 'code': '24680'},
                       {'phone_number': '12025550101', 'code_hash': 'wanted',
                        'expires_at': time.time() + 60, 'code': 24680}]
            for index, record in enumerate(records):
                (outbox / f'malformed-{index}.json').write_text(json.dumps(record))
            valid = outbox / 'valid.json'
            valid.write_text(json.dumps({'phone_number': '12025550101', 'code_hash': 'wanted',
                                         'expires_at': time.time() + 60, 'code': '24680'}))
            # Supply each malformed record first, independent of filesystem order.
            from unittest.mock import Mock
            for index in range(len(records)):
                source = Mock()
                source.glob.return_value = [outbox / f'malformed-{index}.json', valid]
                with self.subTest(index=index):
                    self.assertEqual(self.smoke.read_otp(source, '12025550101', 'wanted'), '24680')

    def test_endpoint_validation_rejects_remote_or_migrated_dc(self):
        self.smoke.validate_endpoint(1, '127.0.0.1', 10443)
        for args in [(2, '127.0.0.1', 10443), (1, '149.154.167.50', 10443), (1, 'localhost', 443), (1, '10.0.0.2', 10443)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.smoke.validate_endpoint(*args)

    def test_ipv6_loopback_rejected_before_telethon_address_family_fallback(self):
        # The smoke uses use_ipv6=False. Telethon replaces a mismatched IPv6
        # session with its public default DC before connecting.
        with self.assertRaises(ValueError):
            self.smoke.validate_endpoint(1, '::1', 10443)

    def test_modern_rsa_pad_roundtrips_with_server_private_key(self):
        import hashlib
        import rsa
        from telethon.crypto import AES

        public_key, private_key = rsa.newkeys(2048)
        payload = b'\x01\x02\x03serialized pq inner data'
        encrypted = self.smoke.rsa_pad_encrypt(payload, public_key)
        self.assertEqual(len(encrypted), 256)

        decoded = rsa.core.decrypt_int(int.from_bytes(encrypted, 'big'), private_key.d, private_key.n).to_bytes(256, 'big')
        encrypted_data = decoded[32:]
        temp_key = bytes(left ^ right for left, right in zip(decoded[:32], hashlib.sha256(encrypted_data).digest()))
        padded_with_hash = AES.decrypt_ige(encrypted_data, temp_key, bytes(32))
        padded = padded_with_hash[:192][::-1]
        self.assertEqual(padded_with_hash[192:], hashlib.sha256(temp_key + padded).digest())
        self.assertTrue(padded.startswith(payload))

    def test_modern_rsa_pad_rejects_oversized_payload(self):
        import rsa

        public_key, _ = rsa.newkeys(2048)
        with self.assertRaises(ValueError):
            self.smoke.rsa_pad_encrypt(bytes(145), public_key)

if __name__ == '__main__':
    unittest.main()
