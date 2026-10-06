"""Finite integrity/capacity gates using owned fixtures; no subprocess or cleanup."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adversarial_certificate_tests import PAYLOADS
from check_certificate import InputError, strict_file
from src.checker import check, InvalidCertificate
from verify_release import verify_manifest


def run_checks(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    entries = verify_manifest(ROOT)
    if not entries:
        raise AssertionError('release manifest must be present and nonempty')
    model = strict_file(ROOT / 'results/certificate_model.json')
    certificate = strict_file(ROOT / 'results/certificate.json')
    assert str(check(model, certificate, '9/2')) == '9/2'
    try:
        check(model, certificate, '449/100')
    except InvalidCertificate as exc:
        assert str(exc) == 'capacity not certified'
    else:
        raise AssertionError('below-bound capacity accepted')

    # Exercise the manifest comparison itself, not just the current digests.
    fixture = output / 'manifest-fixture'
    fixture.mkdir()
    original = b'owned finite input\n'
    (fixture / 'input.txt').write_bytes(original + b'changed\n')
    (fixture / 'RELEASE-MANIFEST.sha256').write_text(
        hashlib.sha256(original).hexdigest() + '  input.txt\n', encoding='utf-8')
    try:
        verify_manifest(fixture)
    except RuntimeError as exc:
        assert str(exc) == 'manifest mismatch: input.txt'
    else:
        raise AssertionError('modified manifest input accepted')

    # These are serialized owned examples, not third-party parser targets.
    rejections = []
    for name, payload in PAYLOADS:
        path = output / (name + '.json')
        path.write_bytes(payload)
        for slot in ('model', 'certificate'):
            try:
                parsed = strict_file(path)
                check(parsed if slot == 'model' else model,
                      parsed if slot == 'certificate' else certificate, '9/2')
            except (InputError, InvalidCertificate) as exc:
                rejections.append({'case': name, 'slot': slot, 'reason': str(exc)})
            else:
                raise AssertionError('invalid owned input accepted: ' + name + '/' + slot)
    report = {'manifest_entries': entries, 'changed_manifest_fixture_rejected': True,
              'certificate_9_2_accepted': True, 'certificate_449_100_rejected': True,
              'payload_classes': len(PAYLOADS), 'in_process_rejections': len(rejections),
              'rejections': rejections, 'wall_seconds': time.perf_counter() - started,
              'scope': 'In-process fixed-input checks, not black-box CLI or third-party testing.'}
    (output / 'checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New directory for retained raw owned fixtures')
    args = parser.parse_args()
    print(json.dumps(run_checks(args.output.resolve()), indent=2))
