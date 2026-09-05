from __future__ import annotations

from pathlib import Path

from reference import make_fixtures, write_json


ROOT = Path(__file__).resolve().parent


def main() -> None:
    write_json(ROOT / "fixtures.json", make_fixtures())
    print("WROTE fixtures.json")


if __name__ == "__main__":
    main()
