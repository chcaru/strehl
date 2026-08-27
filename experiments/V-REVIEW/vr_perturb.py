"""PLANT a known mid-scale mottle into a master, to commission vr_recheck.py.

Writes <dst>/<subj>--<arm>.tiff = master + mottle.  The mottle is band-limited
noise centred inside the 50-400 px band the blotch statistic measures, added to
all three channels (a luma blotch, the defect the gate is looking for).

An uncommissioned checker is one green light of unknown meaning.  This produces
the RED.
"""
import argparse, os, sys
import numpy as np, cv2, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V


def box(a, r):
    return cv2.blur(a, (2 * r + 1, 2 * r + 1), borderType=cv2.BORDER_REFLECT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("amp_dn", type=float, help="target sd of the planted mottle, DN")
    ap.add_argument("--dst", default=r"C:\dev\strehl-out\V-REVIEW\commission-masters")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    os.makedirs(a.dst, exist_ok=True)
    src = V.master_path(a.subject)
    img = tifffile.imread(src)
    assert img.dtype == np.uint16, img.dtype
    h, w = img.shape[:2]

    rng = np.random.default_rng(a.seed)
    n = rng.standard_normal((h, w), dtype=np.float32)
    # band-limit into the statistic's own 50-400 px window: smooth at 100 px,
    # then remove everything slower than 400 px so it is genuinely MID-scale.
    m = box(n, 100) - box(box(n, 100), 400)
    sd = float(m.std())
    if sd <= 0:
        print("degenerate mottle"); return 1
    m *= (a.amp_dn / sd)
    print("planted mottle: target sd %.1f DN, achieved %.1f DN, span %.1f..%.1f"
          % (a.amp_dn, m.std(), m.min(), m.max()))

    out = np.clip(img.astype(np.float32) + m[:, :, None], 0, 65535).astype(np.uint16)
    dst = os.path.join(a.dst, "%s--%s.tiff" % (a.subject, V.ARM))
    tifffile.imwrite(dst, out)
    print("wrote %s  (%.0f MB)" % (dst, os.path.getsize(dst) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
