from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"PASS {name}")


def main() -> None:
    item1 = json.loads((OUT / "item1.json").read_text(encoding="utf-8"))
    log128 = (OUT / "m5-tile128.log").read_text(encoding="utf-8")
    log256 = (OUT / "m5-default-tile256.log").read_text(encoding="utf-8")
    report5 = (ROOT / "docs/research/M5-diffraction-measured.md").read_text(
        encoding="utf-8"
    )
    driver = (ROOT / "experiments/m5-diffraction/m5_measure.py").read_text(
        encoding="utf-8"
    )

    check("M70 exponent reproduces", abs(item1["original_exponent"] - 1.8261) < 5e-5)
    check("registered aggregate fraction", abs(item1["ratio_of_sums"] - 0.2512) < 5e-5)
    check("all six remainders positive", all(r["remainder_dn2"] > 0 for r in item1["rows"]))

    row128 = re.search(
        r"centre\s+GQ\s+tile\s+0\.351\s+1297\.2\s+0\.056\s+\|\s+"
        r"0\.2762\s+3\.064.*\|\s+11\.91\s+4",
        log128,
    )
    check("tile-128 primary fingerprint", row128 is not None)
    check(
        "tile-128 placebo fingerprint",
        re.search(
            r"centre\s+GQ\s+\|\s+0\.2762\s+0\.2154\s+\|\s+"
            r"11\.91\s+12\.00\s+\|\s+1297\.2\s+893\.9",
            log128,
        )
        is not None,
    )

    row256 = re.search(
        r"centre\s+GQ\s+tile\s+0\.352\s+322\.6\s+1\.214\s+\|\s+"
        r"0\.2375\s+3\.563.*\|\s+11\.72\s+1",
        log256,
    )
    check("tile-256 primary fingerprint", row256 is not None)
    check(
        "tile-256 placebo fingerprint",
        re.search(
            r"centre\s+GQ\s+\|\s+0\.2375\s+0\.2154\s+\|\s+"
            r"11\.72\s+11\.84\s+\|\s+322\.6\s+206\.8",
            log256,
        )
        is not None,
    )

    check("M5 report specifies tile 128", "--tile 128" in report5)
    check("committed driver defaults to tile 256", re.search(r"^TILE = 256$", driver, re.M) is not None)

    rmax = 0.5 / 2**0.5
    max_convention_shift = 0.5 * (rmax / (128 // 2))
    observed = 0.2762 - 0.2375
    check("bin convention cannot explain discrepancy", max_convention_shift < observed / 10)

    print("verify: 10/10 PASS")


if __name__ == "__main__":
    main()
