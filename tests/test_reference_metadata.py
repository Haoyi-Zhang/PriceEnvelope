"""Check bibliographic identity independently of cross-file agreement."""
from __future__ import annotations

import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from reference_audit import run_reference_audit


class ReferenceMetadataTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        source = Path(__file__).resolve().parents[1]
        for name in ("reference_manifest.csv", "external_resources.csv", "literature_calibration.csv"):
            shutil.copy2(source / name, self.root / name)

    def replace_value(self, filename, field, before, after):
        path = self.root / filename
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            rows = list(reader)
        changed = 0
        for row in rows:
            if row[field] == before:
                row[field] = after
                changed += 1
        self.assertEqual(changed, 1)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_current_inventory(self):
        self.assertEqual(run_reference_audit(self.root)["scholarly_references"], 56)

    def test_matching_truncated_titles_are_rejected(self):
        title = "Finite Adaptability in Multistage Linear Optimization"
        for filename, field in (
            ("reference_manifest.csv", "title"),
            ("external_resources.csv", "name"),
            ("literature_calibration.csv", "title"),
        ):
            self.replace_value(filename, field, title, "Finite Adaptability in Linear Optimization")
        with self.assertRaisesRegex(AssertionError, "reference identity mismatch: bertsimas2010"):
            run_reference_audit(self.root)

    def test_matching_wrong_source_urls_are_rejected(self):
        for filename, field in (
            ("reference_manifest.csv", "scholarly_url"),
            ("external_resources.csv", "url"),
        ):
            self.replace_value(filename, field, "https://doi.org/10.1109/TAC.2010.2049764",
                               "https://doi.org/10.1109/TAC.2010.2049765")
        with self.assertRaisesRegex(AssertionError, "reference identity mismatch: bertsimas2010"):
            run_reference_audit(self.root)


if __name__ == "__main__":
    unittest.main()
