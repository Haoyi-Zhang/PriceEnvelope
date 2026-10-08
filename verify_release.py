#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any


def call(
    command: list[str],
    cwd: Path,
    *,
    timeout: int = 2400,
    expect: int | str = 0,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        env={
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        },
    )
    if expect == "nonzero":
        unexpected = completed.returncode == 0
    else:
        unexpected = completed.returncode != expect
    if unexpected:
        raise RuntimeError(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout[-5000:],
                "stderr": completed.stderr[-5000:],
            }
        )
    combined = (completed.stdout or "") + (completed.stderr or "")
    if "Traceback" in combined:
        raise RuntimeError(f"traceback leaked from {command!r}")
    return completed


def parse_last_json_line(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("expected a JSON summary on stdout")
    parsed = json.loads(lines[-1])
    if not isinstance(parsed, dict):
        raise RuntimeError("expected a JSON object summary")
    return parsed


def explicit_certificate_inputs(results: Path) -> tuple[Path, Path]:
    """Bind the model and proof object by exact filename, never by glob order."""
    model = results / "certificate_model.json"
    certificate = results / "certificate.json"
    missing = [str(path) for path in (model, certificate) if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing certificate input(s): {missing!r}")
    return model, certificate


def check_reverse_order_binding_fixture() -> dict[str, Any]:
    """Exercise the former wildcard hazard with both artificial file orders."""
    with tempfile.TemporaryDirectory(prefix="certificate-binding-") as directory:
        fixture = Path(directory)
        # Create the proof object first and the model second so filesystem creation
        # order is the opposite of the former model-first assumption.
        certificate = fixture / "certificate.json"
        model = fixture / "certificate_model.json"
        certificate.write_text('{"fixture_kind":"certificate"}\n', encoding="utf-8")
        model.write_text('{"fixture_kind":"model"}\n', encoding="utf-8")

        forward = [certificate, model]
        reverse = list(reversed(forward))
        forward_matches = [
            path.name
            for path in forward
            if fnmatch.fnmatch(path.name, "*certificate*.json")
        ]
        reverse_matches = [
            path.name
            for path in reverse
            if fnmatch.fnmatch(path.name, "*certificate*.json")
        ]
        if len(forward_matches) != 2 or len(reverse_matches) != 2:
            raise RuntimeError("fixture no longer exercises both wildcard matches")
        if forward_matches[0] == reverse_matches[0]:
            raise RuntimeError("fixture did not reverse the legacy first match")

        bound_model, bound_certificate = explicit_certificate_inputs(fixture)
        if bound_model.name != "certificate_model.json":
            raise RuntimeError("model binding is not exact-name based")
        if bound_certificate.name != "certificate.json":
            raise RuntimeError("certificate binding is not exact-name based")
        if json.loads(bound_model.read_text(encoding="utf-8"))["fixture_kind"] != "model":
            raise RuntimeError("model fixture was misbound")
        if (
            json.loads(bound_certificate.read_text(encoding="utf-8"))["fixture_kind"]
            != "certificate"
        ):
            raise RuntimeError("certificate fixture was misbound")

    return {
        "status": "PASS",
        "legacy_pattern_matches_both_files": True,
        "opposite_first_matches": [forward_matches[0], reverse_matches[0]],
        "exact_model_name": "certificate_model.json",
        "exact_certificate_name": "certificate.json",
    }


def check_slack_examples() -> dict[str, Any]:
    """Exact rational checks for the two examples stated after Proposition 6.8."""
    samples: dict[str, str] = {}
    for t in (1, 2, 5, 10, 100):
        upper = Fraction(1, 1) + Fraction(1, t)
        multiplier = min(Fraction(1, 1), Fraction(1, 1) / upper)
        expected = Fraction(t, t + 1)
        if multiplier != expected:
            raise RuntimeError((t, multiplier, expected))
        samples[str(t)] = str(multiplier)
    fixed_multiplier = min(Fraction(1, 1), Fraction(1, 2))
    if fixed_multiplier != Fraction(1, 2):
        raise RuntimeError("fixed-slack example failed")
    return {
        "status": "PASS",
        "vanishing_slack_samples": samples,
        "fixed_U_2_multiplier": str(fixed_multiplier),
    }


def verify_manifest(root: Path) -> int:
    manifest = root / "RELEASE-MANIFEST.sha256"
    if not manifest.is_file():
        return 0
    checked = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"manifest path is missing: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"manifest mismatch: {relative}")
        checked += 1
    return checked


def _root_git_metadata(path: Path) -> bool:
    """Recognize a checkout's metadata directory or worktree gitfile, not links."""
    if path.is_symlink():
        return False
    if path.is_dir():
        return (
            (path / "HEAD").is_file()
            and (path / "objects").is_dir()
            and (path / "refs").is_dir()
        )
    if path.is_file() and path.stat().st_size <= 4096:
        try:
            marker = path.read_text(encoding="utf-8").strip()
        except UnicodeError:
            return False
        # Do not follow the gitdir target; it is outside the release payload.
        return (
            marker.startswith("gitdir: ")
            and bool(marker[len("gitdir: "):].strip())
            and "\n" not in marker
            and "\r" not in marker
        )
    return False


def check_release_hygiene(root: Path) -> None:
    """Scan the payload without descending into recognized root Git metadata."""
    root = root.resolve()

    def walk_error(error: OSError) -> None:
        raise error

    bad: list[str] = []
    for directory, subdirectories, files in os.walk(
        root, topdown=True, followlinks=False, onerror=walk_error
    ):
        parent = Path(directory)
        for name in list(subdirectories) + files:
            path = parent / name
            relative = path.relative_to(root)
            if parent == root and name == ".git" and _root_git_metadata(path):
                if name in subdirectories:
                    subdirectories.remove(name)
                continue
            if path.is_symlink():
                bad.append("symlink:" + str(relative))
            if any(part in relative.parts for part in (".git", "__pycache__")):
                bad.append("generated:" + str(relative))
            if path.suffix == ".pyc":
                bad.append("generated:" + str(relative))
    if bad:
        raise RuntimeError("release hygiene failure: " + repr(bad))


def main() -> None:
    root = Path(__file__).resolve().parent
    check_release_hygiene(root)

    manifest_entries = verify_manifest(root)
    binding_fixture = check_reverse_order_binding_fixture()
    slack_examples = check_slack_examples()

    model, certificate = explicit_certificate_inputs(root / "results")
    positive = call(
        [
            sys.executable,
            "-B",
            "check_certificate.py",
            str(model),
            str(certificate),
            "--capacity",
            "9/2",
        ],
        root,
    )
    if "CERTIFIED upper bound: 9/2" not in positive.stdout:
        raise RuntimeError("positive certificate did not report the expected bound")

    negative = call(
        [
            sys.executable,
            "-B",
            "check_certificate.py",
            str(model),
            str(certificate),
            "--capacity",
            "449/100",
        ],
        root,
        expect="nonzero",
    )
    negative_text = (negative.stdout or "") + (negative.stderr or "")
    if "REJECTED: capacity not certified" not in negative_text:
        raise RuntimeError("strict-negative certificate query was not explicitly rejected")

    # Run the many short malformed-input subprocesses before the two exact
    # reproduction passes.  This avoids transient post-reproduction startup
    # slowdown on constrained clean containers without changing any check.
    adversarial = parse_last_json_line(
        call(
            [
                sys.executable,
                "-B",
                "adversarial_certificate_tests.py",
                "--model",
                str(model.relative_to(root)),
                "--certificate",
                str(certificate.relative_to(root)),
            ],
            root,
        )
    )
    tamper = parse_last_json_line(
        call([sys.executable, "-B", "reference_tamper_tests.py"], root)
    )

    reproduced = root / "_verify_reproduced"
    shutil.rmtree(reproduced, ignore_errors=True)
    try:
        call(
            [
                sys.executable,
                "-B",
                "reproduce.py",
                "--output",
                str(reproduced),
                "--check-against",
                "results",
            ],
            root,
        )
    finally:
        shutil.rmtree(reproduced, ignore_errors=True)

    # No matching implementation or frozen 128-case output exists in the
    # supplied project.  Do not manufacture or silently skip that check.
    missing_check = {
        "check": "independent_random_exact_cases",
        "status": "NOT_EXECUTED_MISSING_ASSET",
        "reason": (
            "independent_random_exact_cases.py and a frozen 128-case result "
            "are not present in the delivered project"
        ),
    }

    summary = {
        "status": "PASS_FOR_DELIVERED_CHECKS",
        "executed_checks": {
            "release_hygiene": True,
            "manifest_entries": manifest_entries,
            "main_reproduction_matches_results": True,
            "certificate_binding_fixture": binding_fixture,
            "certificate_9_2_accepted": True,
            "certificate_449_100_rejected": True,
            "adversarial_certificate_tests": adversarial,
            "tampered_reference_rejected": tamper,
            "control_slack_examples": slack_examples,
        },
        "not_executed": [missing_check],
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"VERIFY FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
