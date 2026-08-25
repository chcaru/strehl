"""Count the canonical sites of each duplicated claim, so verify_ca can pin an
exact occurrence count instead of a presence test. A presence test is satisfied
by any duplicate, which is why negctl_ca's D1/D2/D11 walked straight past it."""
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEXT = " ".join((ROOT / "docs" / "research" / "M116-promotion.md")
                .read_text(encoding="utf-8").split())

NEEDLES = [
    "90.1 %", "95.2 %", "−0.7478 px", "+0.0741 px", "−0.6861 px", "+0.0332 px",
    "1.099", "1.048", "+0.485", "+0.440", "+0.015", "+0.120",
    "0.085 px", "0.075 px", "0.330 px", "0.310 px",
    "−0.00169", "−0.00101", "−0.00155", "−0.00184",
    "on every subject scored", "VOID", "0.42",
]
for n in NEEDLES:
    print(f"{TEXT.count(n):3}  {n!r}")
