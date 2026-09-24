"""Offline traceability checks for the delivered scholarly-source inventory."""
from __future__ import annotations

from pathlib import Path
import csv
import re

MIN_REFERENCES = 55
WORKFLOW_TYPES = {"official rules", "official template source", "official policy"}


def _normal(value: str) -> str:
    value = value.replace("--", "-").translate(str.maketrans({"{": "", "}": "", "–": "-", "—": "-"}))
    value = re.sub(r"\\([A-Za-z]+)", r" \1 ", value)
    value = re.sub(r"[^0-9A-Za-z]+", " ", value)
    return " ".join(value.casefold().split())


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def run_reference_audit(root: Path | None = None) -> dict[str, int]:
    root = (root or Path(__file__).resolve().parents[1]).resolve()
    manifest = _read(root / "reference_manifest.csv")
    resources = _read(root / "external_resources.csv")
    calibration = _read(root / "literature_calibration.csv")
    if len(manifest) < MIN_REFERENCES:
        raise AssertionError("bibliography inventory below the declared minimum")
    for field in ("key", "title", "year", "publication_type", "venue", "scholarly_url", "reading_status"):
        values = [row[field].strip() for row in manifest]
        if any(not value for value in values):
            raise AssertionError(f"blank reference-manifest field: {field}")
        if field in {"key", "title", "scholarly_url"} and len(values) != len(set(values)):
            raise AssertionError(f"duplicate reference-manifest field: {field}")
    if any(not re.fullmatch(r"(?:19|20)\d{2}", row["year"]) for row in manifest):
        raise AssertionError("invalid publication year")
    if any(not row["scholarly_url"].startswith("https://") for row in manifest):
        raise AssertionError("non-HTTPS scholarly URL")
    if any("placeholder" in row["scholarly_url"].casefold() or "example." in row["scholarly_url"].casefold()
           for row in manifest):
        raise AssertionError("placeholder scholarly URL")

    scholarly = [row for row in resources if row["resource_type"] not in WORKFLOW_TYPES]
    manifest_titles = {_normal(row["title"]) for row in manifest}
    scholarly_titles = {_normal(row["name"]) for row in scholarly}
    calibration_titles = {_normal(row["title"]) for row in calibration}
    if len(manifest_titles) != len(manifest):
        raise AssertionError("duplicate normalized manifest title")
    if len(scholarly_titles) != len(scholarly):
        raise AssertionError("duplicate normalized source-ledger title")
    if len(calibration_titles) != len(calibration):
        raise AssertionError("duplicate normalized calibration title")
    if not (manifest_titles == scholarly_titles == calibration_titles):
        raise AssertionError("reference manifest, source ledger, and calibration do not agree")
    resource_urls = {_normal(row["name"]): row["url"] for row in scholarly}
    for row in manifest:
        if resource_urls[_normal(row["title"])] != row["scholarly_url"]:
            raise AssertionError("manifest URL does not match source ledger")
    return {
        "scholarly_references": len(manifest),
        "source_ledger_rows": len(resources),
        "literature_calibration_rows": len(calibration),
        "minimum_references": MIN_REFERENCES,
    }


if __name__ == "__main__":
    print(run_reference_audit())
