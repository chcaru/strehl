"""Audit whether the two retained Lightroom source sets isolate sharpening."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import sharpening_core as sc


TAGS = (
    "OriginalDocumentID",
    "Exposure2012",
    "Contrast2012",
    "Highlights2012",
    "Shadows2012",
    "Whites2012",
    "Blacks2012",
    "Texture",
    "Clarity2012",
    "Dehaze",
    "Sharpness",
    "SharpenRadius",
    "SharpenDetail",
    "SharpenEdgeMasking",
    "LuminanceSmoothing",
    "ColorNoiseReduction",
    "PostCropVignetteAmount",
    "FilterListFiltersName",
)


def census(rows: list[dict], tag: str) -> dict[str, int]:
    values = Counter(
        "<ABSENT>" if tag not in row else str(row[tag])
        for row in rows
    )
    return dict(sorted(values.items()))


def main() -> int:
    command = [
        "exiftool",
        "-json",
        "-s",
        "-FilePath",
        "-XMP-xmpMM:OriginalDocumentID",
        *[f"-XMP-crs:{tag}" for tag in TAGS if tag != "OriginalDocumentID"],
        str(sc.SOURCE_0),
        str(sc.SOURCE_40),
    ]
    proc = subprocess.run(command, check=True, capture_output=True, text=True)
    all_rows = json.loads(proc.stdout)
    grouped: dict[str, list[dict]] = {"sharpness0": [], "sharpness40": []}
    source_re = re.compile(r"20260507-DSC(\d{5})\.tif$", re.IGNORECASE)
    for row in all_rows:
        path = Path(row["FilePath"].replace("/", "\\"))
        match = source_re.search(path.name)
        if not match:
            continue
        parent = path.parent.name.lower()
        key = "sharpness0" if parent == "test2" else "sharpness40" if parent == "test" else None
        if key is not None:
            row["_identity"] = int(match.group(1))
            grouped[key].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: row["_identity"])
    if any(len(rows) != 63 for rows in grouped.values()):
        raise RuntimeError({key: len(rows) for key, rows in grouped.items()})
    ids_match = all(
        a["_identity"] == b["_identity"]
        and a.get("OriginalDocumentID") == b.get("OriginalDocumentID")
        for a, b in zip(grouped["sharpness0"], grouped["sharpness40"])
    )
    settings = {
        key: {tag: census(rows, tag) for tag in TAGS if tag != "OriginalDocumentID"}
        for key, rows in grouped.items()
    }
    differing = [
        tag
        for tag in TAGS
        if tag != "OriginalDocumentID"
        and settings["sharpness0"][tag] != settings["sharpness40"][tag]
    ]
    result = {
        "counts": {key: len(rows) for key, rows in grouped.items()},
        "original_document_ids_match": ids_match,
        "settings": settings,
        "differing_fields": differing,
        "isolates_sharpening": set(differing).issubset(
            {
                "Sharpness",
                "SharpenRadius",
                "SharpenDetail",
                "SharpenEdgeMasking",
            }
        ),
    }
    print("SOURCE_METADATA_JSON=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if ids_match and not result["isolates_sharpening"] else 2


if __name__ == "__main__":
    sys.exit(main())
