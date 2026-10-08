"""Owned checkout/payload regressions; no full reproduction or remote access."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import verify_release as verifier


class StopBeforeLargeWorkflows(RuntimeError):
    pass


class ReleaseHygieneTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="p105-checkout-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.payload = self.base / "payload"
        self.payload.mkdir()

    def git(self, *args):
        executable = shutil.which("git")
        if executable is None:
            self.skipTest("Git is required for the owned local-checkout regression")
        # Ignore caller Git routing/configuration; use only this temporary tree.
        environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_CONFIG_SYSTEM=os.devnull, GIT_TERMINAL_PROMPT="0",
                           GIT_ALLOW_PROTOCOL="file")
        result = subprocess.run(
            [executable, "-c", "core.hooksPath=" + os.devnull, *args],
            cwd=self.base, env=environment, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def local_clone(self):
        source = self.base / "source"
        self.git("init", "--template=", "--initial-branch=main", str(source))
        names = (
            "verify_release.py", "check_certificate.py", "check_certificate_core.py",
            "src/__init__.py", "src/checker.py",
            "results/certificate_model.json", "results/certificate.json",
        )
        manifest = []
        for name in names:
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
            manifest.append(hashlib.sha256(target.read_bytes()).hexdigest() + "  " + name)
        (source / "RELEASE-MANIFEST.sha256").write_text(
            "\n".join(manifest) + "\n", encoding="utf-8"
        )
        self.git("-C", str(source), "add", "--", ".")
        self.git("-C", str(source), "-c", "user.name=Owned regression fixture",
                 "-c", "user.email=fixture@example.invalid", "commit", "--no-gpg-sign",
                 "-m", "Temporary owned checkout fixture")
        clone = self.base / "clone"
        self.git("clone", "--no-hardlinks", "--", str(source), str(clone))
        return source, clone, len(names)

    def assert_rejected(self, root, expected):
        with self.assertRaisesRegex(RuntimeError, "release hygiene failure") as raised:
            verifier.check_release_hygiene(root)
        self.assertIn(repr(expected)[1:-1], str(raised.exception))

    def test_clean_export(self):
        (self.payload / "input.txt").write_text("owned finite input\n", encoding="utf-8")
        verifier.check_release_hygiene(self.payload)

    def test_normal_clone_prunes_metadata_and_reaches_real_gates(self):
        _, clone, entries = self.local_clone()
        cache = clone / ".git" / "__pycache__"
        cache.mkdir()
        (cache / "metadata.pyc").write_bytes(b"owned metadata marker\n")
        visited = []
        real_walk, real_call = os.walk, verifier.call
        completed = []

        def tracked_walk(*args, **kwargs):
            for item in real_walk(*args, **kwargs):
                visited.append(Path(item[0]))
                yield item

        def bounded_call(command, cwd, **kwargs):
            if command[2] != "check_certificate.py":
                self.assertEqual(command[2], "adversarial_certificate_tests.py")
                raise StopBeforeLargeWorkflows("bounded regression stops here")
            result = real_call(command, cwd, timeout=20, **kwargs)
            completed.append(result)
            return result

        with mock.patch.object(verifier, "__file__", str(clone / "verify_release.py")), \
             mock.patch.object(verifier.os, "walk", side_effect=tracked_walk), \
             mock.patch.object(verifier, "verify_manifest", wraps=verifier.verify_manifest) as manifest, \
             mock.patch.object(verifier, "call", side_effect=bounded_call):
            with self.assertRaises(StopBeforeLargeWorkflows):
                verifier.main()
        manifest.assert_called_once_with(clone)
        self.assertEqual(verifier.verify_manifest(clone), entries)
        self.assertTrue(visited)
        self.assertFalse(any(path == clone / ".git" or clone / ".git" in path.parents
                             for path in visited))
        self.assertEqual([result.returncode for result in completed], [0, 1])
        self.assertIn("CERTIFIED upper bound: 9/2", completed[0].stdout)
        self.assertIn("REJECTED: capacity not certified", completed[1].stderr)

    def test_normal_clone_rejects_nested_git_before_manifest(self):
        _, clone, _ = self.local_clone()
        self.git("init", "--template=", "--initial-branch=main", str(clone / "inputs"))
        nested = clone / "inputs" / ".git"
        (nested / "owned-marker.pyc").write_bytes(b"owned nested metadata marker\n")
        with mock.patch.object(verifier, "__file__", str(clone / "verify_release.py")), \
             mock.patch.object(verifier, "verify_manifest") as manifest:
            with self.assertRaisesRegex(RuntimeError, "release hygiene failure"):
                verifier.main()
        manifest.assert_not_called()

    def test_real_worktree_gitfile(self):
        source, _, entries = self.local_clone()
        worktree = self.base / "worktree"
        self.git("-C", str(source), "worktree", "add", "--detach", str(worktree))
        self.assertTrue((worktree / ".git").is_file())
        verifier.check_release_hygiene(worktree)
        self.assertEqual(verifier.verify_manifest(worktree), entries)

    def test_unrecognized_root_git_entries(self):
        git = self.payload / ".git"
        git.mkdir()
        self.assert_rejected(self.payload, "generated:.git")
        (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        self.assert_rejected(self.payload, "generated:.git")
        for index, raw in enumerate((b"owned payload\n", b"gitdir: \n",
                                     b"gitdir: fixture\nextra\n", b"\xff",
                                     b"gitdir: " + b"a" * 4096)):
            root = self.base / ("nonmetadata-" + str(index))
            root.mkdir()
            (root / ".git").write_bytes(raw)
            self.assert_rejected(root, "generated:.git")

    def test_nested_git_directory_and_file(self):
        for name in ("inputs", "other/deeper"):
            root = self.base / name
            root.mkdir(parents=True)
            (root / ".git").mkdir()
            self.assert_rejected(self.base, "generated:")
        file_root = self.base / "gitfile-payload"
        nested = file_root / "inputs"
        nested.mkdir(parents=True)
        (nested / ".git").write_text("gitdir: owned-fixture\n", encoding="utf-8")
        self.assert_rejected(file_root, "generated:" + str(Path("inputs/.git")))

    def test_bytecode_and_cache_directory_or_file(self):
        for name in ("inputs/__pycache__", "other/example.pyc", "__pycache__"):
            root = self.base / ("generated-" + name.split("/")[0])
            root.mkdir(exist_ok=True)
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if name == "inputs/__pycache__":
                path.mkdir()
            else:
                path.write_bytes(b"owned generated marker\n")
            self.assert_rejected(root, "generated:" + str(Path(name)))

    def test_symlinks_including_root_git_are_rejected(self):
        target = self.base / "owned-target"
        target.mkdir()
        (target / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        (target / "objects").mkdir()
        (target / "refs").mkdir()
        (target / "input.txt").write_text("owned input\n", encoding="utf-8")
        for name, destination, directory in (("link.txt", target / "input.txt", False),
                                             ("linked-directory", target, True),
                                             (".git", target, True)):
            with self.subTest(name=name):
                root = self.base / ("links-" + name)
                root.mkdir()
                try:
                    (root / name).symlink_to(destination, target_is_directory=directory)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest("Symlink creation unavailable: " + str(exc))
                self.assert_rejected(root, "symlink:" + name)

    def test_scan_errors_are_not_silently_accepted(self):
        def failed_walk(*args, **kwargs):
            kwargs["onerror"](PermissionError("owned scan-error fixture"))
            return iter(())
        with mock.patch.object(verifier.os, "walk", side_effect=failed_walk):
            with self.assertRaisesRegex(PermissionError, "owned scan-error fixture"):
                verifier.check_release_hygiene(self.payload)


if __name__ == "__main__":
    unittest.main()
