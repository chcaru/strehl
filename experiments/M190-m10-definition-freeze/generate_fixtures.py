from __future__ import annotations

import json
from pathlib import Path

from reference import development_summary, make_fixtures, make_sample_manifest


ROOT = Path(__file__).resolve().parent
DEVELOPMENT_SEED = bytes(range(32))


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    write_json(ROOT / "fixtures.json", make_fixtures())
    write_json(ROOT / "sample-depth-manifest.json", make_sample_manifest())
    write_json(
        ROOT / "development-synthetic-summary.json",
        development_summary(DEVELOPMENT_SEED),
    )
    print("WROTE fixtures.json")
    print("WROTE sample-depth-manifest.json")
    print("WROTE development-synthetic-summary.json")


if __name__ == "__main__":
    main()
