"""Full-resolution viewable exports of the shipping masters.

WHY THIS EXISTS
    Every artifact handed upward so far has been either a 380 px true-1:1 crop
    or a box-4x reduced overview. Neither is a thing you can open and pan
    around, and "is this print worthy" is a judgement made at full size on a
    real monitor. This writes one visually-lossless JPEG per shipping master at
    native resolution.

THE DEFECT THIS SCRIPT IS WRITTEN AGAINST
    true11.py shipped a 16->8 bit conversion that wrapped pure white to pure
    black, because it scaled in a wider type and then cast without clipping.
    308 px in tweezers-cpl and 507 px in lavendar-cpl were rendered black, on
    specular highlights -- exactly the pixels a reviewer looks at.

    to8() below clips before it casts, and commission() plants an
    above-range value and requires 255 rather than a wrap. The commission runs
    before any master is touched and hard-errors on failure.

WHY PNG AND NOT JPEG
    The first version of this script wrote JPEG q98 4:4:4, which is the usual
    "visually lossless" setting. export_fidelity.py measured it against the
    master at full resolution and it failed a tolerance registered before the
    run: max error 10-12 DN and mean error 0.82-1.28 DN in 8-bit, on the five
    highest-detail subjects.

    Whether 1 DN of mean error is visible is arguable. That is exactly why the
    artifact changed rather than the threshold -- a tolerance loosened after
    seeing the number it failed is not a tolerance. PNG removes the argument:
    the encoder contributes exactly zero, and export_fidelity.py now demands
    bit-exactness rather than a tolerance anyone could negotiate.
"""
import sys, pathlib, numpy as np, tifffile
from PIL import Image

SRC = pathlib.Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
DST = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V5\full-resolution")


def to8(a):
    """uint16 (or wider) -> uint8, clipped. Never wraps."""
    return np.clip(np.asarray(a, dtype=np.float64) / 257.0, 0.0, 255.0).round().astype(np.uint8)


def commission():
    """A conversion that cannot express the failure certifies nothing."""
    checks = []
    # 1. pure white survives
    checks.append(("white 65535 -> 255", int(to8(np.array([65535], dtype=np.uint16))[0]), 255))
    # 2. pure black survives
    checks.append(("black 0 -> 0", int(to8(np.array([0], dtype=np.uint16))[0]), 0))
    # 3. THE PLANT: an above-range value must clamp, not wrap.
    #    the old code did int(v) >> 8 on a float64 that had exceeded 65535;
    #    70000 >> 8 == 273, which truncates to 17 in uint8. black.
    checks.append(("overrange 70000 -> 255 (not 17)", int(to8(np.array([70000.0]))[0]), 255))
    # 4. and the negative side
    checks.append(("underrange -5 -> 0", int(to8(np.array([-5.0]))[0]), 0))
    # 5. midpoint is not shifted
    checks.append(("mid 32896 -> 128", int(to8(np.array([32896], dtype=np.uint16))[0]), 128))
    bad = 0
    for name, got, want in checks:
        ok = got == want
        bad += 0 if ok else 1
        print(f"  [{'ok ' if ok else 'BAD'}] {name}: got {got}, want {want}")
    if bad:
        raise SystemExit(f"COMMISSION FAILED: {bad}/{len(checks)} -- refusing to write anything")
    print(f"  commission {len(checks)}/{len(checks)} PASS\n")


def main():
    print("commissioning the 16->8 conversion against the true11 wrap defect:")
    commission()

    DST.mkdir(parents=True, exist_ok=True)
    masters = sorted(p for p in SRC.glob("*.tiff") if p.suffix == ".tiff")
    if not masters:
        raise SystemExit(f"no masters under {SRC}")

    written = failed = 0
    print(f"{'subject':<40} {'out MB':>7}  {'white px':>9}  {'black px':>9}")
    print("-" * 72)
    for m in masters:
        subject = m.stem.replace("--SHIP-V4", "")
        try:
            a = tifffile.imread(str(m))
            if a.ndim != 3 or a.shape[2] < 3:
                raise ValueError(f"unexpected shape {a.shape}")
            rgb = to8(a[:, :, :3])
            # report the two extremes: if the wrap defect were present, the
            # white count would collapse and the black count would inherit it.
            wht = int((rgb == 255).all(axis=2).sum())
            blk = int((rgb == 0).all(axis=2).sum())
            out = DST / f"{subject}.png"
            Image.fromarray(rgb, "RGB").save(out, compress_level=6)
            mb = out.stat().st_size / 1024 / 1024
            print(f"{subject:<40} {mb:>7.1f}  {wht:>9,}  {blk:>9,}")
            written += 1
        except Exception as e:
            print(f"{subject:<40} {'FAILED':>7}  {e}")
            failed += 1

    print("-" * 72)
    print(f"masters found : {len(masters)}")
    print(f"written       : {written}")
    print(f"failed        : {failed}")
    if written + failed != len(masters):
        raise SystemExit("PARTITION BROKEN: written + failed != found")
    print(f"OUT: {DST}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
