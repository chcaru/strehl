"""Freeze pre-treatment PMax-native physical sites for one comparator."""

from __future__ import annotations

import argparse
import json
import sys

import cover_core as cc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", choices=sorted(cc.PMAX), required=True)
    args = parser.parse_args()
    cc.verify_hashes()
    frozen = cc.freeze_sites(cc.SCALE_MASTER, cc.PMAX[args.subject])
    counts = {
        label: sum(site["label"] == label for site in frozen["sites"])
        for label in ("detail", "flat")
    }
    if counts["detail"] < 12 or counts["flat"] < 6:
        raise RuntimeError(f"too few frozen sites: {counts}")
    payload = {
        "subject": args.subject,
        "scale_master_sha256": cc.HASHES[cc.SCALE_MASTER],
        "comparator_sha256": cc.HASHES[cc.PMAX[args.subject]],
        **frozen,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
