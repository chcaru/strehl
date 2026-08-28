"""Commission build.py's tagger BEFORE it runs on 1.2 GB of deliverable.

The claim the whole change rests on is "pixels must not change".  A comparison
that cannot detect a change would confirm that claim on any input, so the
negative control is not optional here -- it is the arm that gives the other
arms meaning.

  A1  decoded pixels identical after tagging      (the invariant)
  A2  NEGATIVE CONTROL: plant +1 in one channel of one pixel and require A1's
      comparison to FAIL -- otherwise A1 is vacuous
  A3  the profile read back equals the MASTER's profile, by md5
  A4  pHYs reads 300 dpi
  A5  idempotent: tagging twice equals tagging once, byte for byte
  A6  IDAT bytes are literally untouched (structural, not statistical)
"""

import hashlib
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "DELIVER-V5"))
import build as B          # noqa: E402
from png_probe import probe, dpi_of  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
TMP = Path(r"D:\strehl-out\BUILD-OUTPUT\scratch\tagcheck")
SRC = Path(r"C:\dev\strehl-out\DELIVER-V5\crops-1to1")


def idat(p):
    return hashlib.sha256(b"".join(d for t, d in B._chunks(Path(p).read_bytes())
                                   if t == b"IDAT")).hexdigest()[:16]


def pixels(p):
    return np.asarray(Image.open(p).convert("RGB"))


def main():
    fails = []

    def chk(name, cond, got):
        print(f"  {'PASS' if cond else 'FAIL':<5} {name:<50} {got}")
        if not cond:
            fails.append(name)

    TMP.mkdir(parents=True, exist_ok=True)
    src = sorted(SRC.glob("*.png"))[0]
    work = TMP / "work.png"
    shutil.copy2(src, work)
    print(f"fixture: {src.name}\n")

    before = pixels(work)
    idat_before = idat(work)
    B.tag_png(str(work))
    after = pixels(work)

    chk("A1 decoded pixels identical after tagging",
        before.shape == after.shape and np.array_equal(before, after),
        f"{before.shape} vs {after.shape}")

    # A2: the comparison must be able to convict.
    planted = before.copy()
    planted[7, 11, 1] = (int(planted[7, 11, 1]) + 1) % 256
    chk("A2 NEG CONTROL: +1 in one channel is detected",
        not np.array_equal(before, planted),
        f"differing pixels {int((before != planted).sum())}")

    r = probe(work)
    want = hashlib.md5(B.master_icc()).hexdigest()[:12]
    chk("A3 profile == the MASTER's profile (md5)",
        r["state"] == "ICCP" and r["icc"]["md5"] == want,
        f"{r['state']} {r['icc']['md5'] if r['icc'] else '-'} vs master {want}")
    chk("A4 pHYs reads 300 dpi",
        r["phys"] is not None and abs(r["phys"][0] * 0.0254 - 300) < 0.5,
        dpi_of(r))

    once = work.read_bytes()
    B.tag_png(str(work))
    chk("A5 idempotent: second tagging is a no-op",
        work.read_bytes() == once, f"{len(once)} bytes")

    chk("A6 IDAT bytes literally untouched",
        idat(work) == idat_before, f"{idat_before} -> {idat(work)}")

    print()
    if fails:
        print(f"TAGGER COMMISSIONING: FAIL -- {fails}")
        return 1
    print("TAGGER COMMISSIONING: PASS -- safe to run on the delivered tree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
