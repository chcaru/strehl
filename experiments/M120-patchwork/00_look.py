"""M120 step 0: look at the three renders ORCH named, downscaled for viewing."""
import sys
from pathlib import Path

from PIL import Image

SRC = Path(r"C:\dev\strehl-out\M87-before-after")
OUT = Path(r"C:\dev\strehl-out\M120\look")
OUT.mkdir(parents=True, exist_ok=True)

NAMES = [
    "00-BEFORE-shipped-merge-tight2x.png",
    "01-AFTER-F1-mode-partition-d40-tight2x.png",
    "04-AFTER-F2-two-layer-unmix-tight2x.png",
]


def main() -> int:
    for n in NAMES:
        p = SRC / n
        im = Image.open(p)
        print(f"{n}: mode={im.mode} size={im.size}")
        w, h = im.size
        scale = 900 / w
        small = im.convert("RGB").resize((900, max(1, round(h * scale))), Image.LANCZOS)
        small.save(OUT / f"small-{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
