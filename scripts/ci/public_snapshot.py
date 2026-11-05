#!/usr/bin/env python3
"""Create an unreferenced, history-free commit from the public source allowlist."""
import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import package_preview


ROOT = Path(__file__).resolve().parents[2]


def run_git(repository, arguments, env=None, input_data=None):
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        input=input_data,
    ).stdout


def index_entries(repository, env):
    raw = run_git(repository, ["ls-files", "--stage", "-z"], env=env)
    entries = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, name = record.split(b"\t", 1)
        mode, object_id, stage = metadata.split()
        path = os.fsdecode(name)
        if stage != b"0":
            raise ValueError(f"unmerged index entry: {path}")
        if package_preview.source_allowed(path):
            entries.append((mode.decode("ascii"), object_id.decode("ascii"), name, path))
    return entries


def scan_public_blobs(repository, entries):
    paths_by_object = {}
    symlinks = {}
    for mode, object_id, _, path in entries:
        paths_by_object.setdefault(object_id, []).append(path)
        if mode == "120000":
            symlinks.setdefault(object_id, []).append(path)

    command = ["git", "-C", str(repository), "cat-file", "--batch"]
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        for object_id, paths in paths_by_object.items():
            process.stdin.write(object_id.encode("ascii") + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise ValueError(f"invalid source blob returned for {paths[0]}")
            size = int(header[2])
            has_private_key, digest, link_target = read_blob(process.stdout, size, object_id in symlinks)
            if process.stdout.read(1) != b"\n":
                raise ValueError(f"truncated source blob returned for {paths[0]}")

            if has_private_key:
                for path in paths:
                    if package_preview.PUBLIC_KEY_FIXTURE_SHA256.get(path) != digest:
                        raise ValueError(f"private key detected in public source: {path}")
            if object_id in symlinks:
                target = os.fsdecode(link_target)
                for path in symlinks[object_id]:
                    try:
                        package_preview.validate_link(path, target)
                    except ValueError as error:
                        raise ValueError(f"invalid public source symlink {path}: {error}") from error

        process.stdin.close()
        error = process.stderr.read().decode("utf-8", "replace").strip()
        if process.wait() != 0:
            raise ValueError(error or "git cat-file failed while scanning source")


def read_blob(stream, size, is_symlink):
    digest = hashlib.sha256()
    previous = b""
    has_private_key = False
    link_target = bytearray()
    remaining = size
    while remaining:
        chunk = stream.read(min(1024 * 1024, remaining))
        if not chunk:
            raise ValueError("truncated source blob")
        remaining -= len(chunk)
        digest.update(chunk)
        if is_symlink:
            if size > 4096:
                raise ValueError("symlink target exceeds the supported length")
            link_target.extend(chunk)

        # Retain more than the longest PEM header across chunk boundaries. A
        # sentinel prevents a chunk boundary from looking like the end of a
        # PEM line; skipping offset zero on later chunks preserves line starts.
        sample = previous + chunk + (b"x" if remaining else b"")
        if package_preview.PRIVATE_KEY.search(sample, 1 if previous else 0):
            has_private_key = True
        previous = (previous + chunk)[-1024:]

    return has_private_key, digest.hexdigest(), bytes(link_target)


def make_snapshot(repository, message):
    repository = repository.resolve()
    run_git(repository, ["rev-parse", "--verify", "HEAD"])

    with tempfile.TemporaryDirectory(prefix="private-chat-snapshot-") as directory:
        index_path = Path(directory) / "index"
        real_index = Path(os.fsdecode(run_git(repository, ["rev-parse", "--git-path", "index"]).strip()))
        if not real_index.is_absolute():
            real_index = repository / real_index
        index_path.write_bytes(real_index.read_bytes())
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(index_path)

        # Preserve the real index's stat cache, but make its optimization flags
        # ineffective only in this temporary copy so all working tree edits are
        # included. Rebuilding the index from HEAD rereads every tracked file.
        paths = run_git(repository, ["ls-files", "-z"], env=env)
        for flag in ("--no-assume-unchanged", "--no-skip-worktree"):
            run_git(
                repository,
                ["update-index", flag, "-z", "--stdin"],
                env=env,
                input_data=paths,
            )
        run_git(repository, ["add", "--all", "--", "."], env=env)
        entries = index_entries(repository, env)
        package_preview.validate_source_tree((mode, path) for mode, _, _, path in entries)
        scan_public_blobs(repository, entries)

        run_git(repository, ["read-tree", "--empty"], env=env)
        index_info = b"".join(
            f"{mode} {object_id} 0\t".encode("ascii") + name + b"\0"
            for mode, object_id, name, _ in entries
        )
        run_git(repository, ["update-index", "-z", "--index-info"], env=env, input_data=index_info)
        tree = run_git(repository, ["write-tree"], env=env).decode("ascii").strip()

    commit = run_git(
        repository,
        ["-c", "user.name=Private Chat Snapshot", "-c", "user.email=snapshot@private-chat.invalid",
         "commit-tree", tree, "-m", message],
    )
    return commit.decode("ascii").strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--message", default="Public source snapshot")
    args = parser.parse_args(argv)
    if not args.message.strip():
        parser.error("--message must not be empty")

    try:
        print(make_snapshot(args.repository, args.message))
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        detail = error.stderr.decode("utf-8", "replace").strip() if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(f"public snapshot failed: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
