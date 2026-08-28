r"""sigma-equivalent blur difference, take 2.

Take 1 used a windowed second moment of |dp/dt| and FAILED commission with a
bias that grew with sigma (-0.21 at 0.2 px, -0.45 at 1.2 px). Mechanism: the
+/-10 sample window truncates the tails, and a second moment weights by t^2 so
truncation removes proportionally more as the distribution widens.

Three tail-insensitive candidates, all commissioned against planted sigma. I
select among them on COMMISSION performance against known ground truth, never
on the answer they give for old-vs-new.

  peak : gaussian-equivalent width from rise/peak,  sigma = A / (peak*sqrt(2pi))
  fwhm : half-maximum width of |dp/dt|,             sigma = fwhm / 2.3548
  mom  : take 1, kept so the comparison is visible
"""
import numpy as np, sys, os
from scipy.ndimage import gaussian_filter
import vc_ca

OLD = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\%s.tiff"
NEW = r"C:\dev\strehl-out\DELIVER-V6\masters\%s.tiff"
CAP = 260
SQ2PI = np.sqrt(2.0 * np.pi)


def _d(p):
    return np.diff(p.astype(np.float64))


def w_peak(p):
    d = _d(p); a = np.abs(d)
    pk = float(a.max())
    if pk <= 0: return None
    A = float(abs(d.sum()))                      # net rise across the profile
    if A <= 0: return None
    return (A / (pk * SQ2PI)) ** 2               # returned as a VARIANCE


def w_fwhm(p):
    a = np.abs(_d(p))
    pk = float(a.max())
    if pk <= 0: return None
    k = int(np.argmax(a)); half = pk / 2.0
    i = k
    while i > 0 and a[i] > half: i -= 1
    lo = i + (half - a[i]) / max(1e-9, a[i+1] - a[i]) if i + 1 <= k else float(k)
    j = k
    while j < len(a) - 1 and a[j] > half: j += 1
    hi = j - (half - a[j]) / max(1e-9, a[j-1] - a[j]) if j - 1 >= k else float(k)
    f = hi - lo
    if not np.isfinite(f) or f <= 0: return None
    return (f / 2.3548) ** 2


def w_mom(p, WIN=10):
    d = np.abs(_d(p))
    if d.sum() <= 0: return None
    k = int(np.argmax(d)); lo, hi = max(0, k-WIN), min(len(d), k+WIN+1)
    d = d[lo:hi]; t = np.arange(lo, hi, dtype=np.float64); w = d / d.sum()
    c = float((w*t).sum())
    return float((w*(t-c)**2).sum())


STATS = {"peak": w_peak, "fwhm": w_fwhm, "mom": w_mom}


def widths(img, S, fn):
    out = {}
    for (py, px, nx, ny, r, m, al) in S:
        p = vc_ca.profile(img[:, :, 1], py, px, nx, ny)
        if p is None: continue
        v = fn(p)
        if v is None or v <= 0: continue
        out[(py, px)] = v
    return out


def sigma_equiv(wa, wb):
    both = sorted(set(wa) & set(wb))
    if len(both) < vc_ca.MIN_SITES: return None, 0
    dv = np.array([wb[k] - wa[k] for k in both])
    md = float(np.median(dv))
    return float(np.sign(md) * np.sqrt(abs(md))), len(both)


def load_sites(path):
    img = vc_ca.load(path)
    H, W = img.shape[:2]
    S = vc_ca.sites(img[:, :, 1], (H/2.0, W/2.0))
    return img, S[::max(1, len(S)//CAP)][:CAP]


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "commission":
        subject = sys.argv[2]
        img, S = load_sites(OLD % subject)
        print("COMMISSION sigma-equivalent  subject=%s  sites=%d" % (subject, len(S)))
        print("selection is on recovery of PLANTED sigma, not on any old-vs-new answer\n")
        base = {k: widths(img, S, f) for k, f in STATS.items()}
        ladder = [0.0, 0.2, 0.3, 0.5, 0.8, 1.2]
        print("%10s | %s" % ("planted", " | ".join("%17s" % ("%s: rec (err)" % k) for k in STATS)))
        bad = {k: 0 for k in STATS}
        for sg in ladder:
            if sg == 0.0: bl = img
            else:
                bl = img.copy()
                for c in range(3):
                    bl[:, :, c] = gaussian_filter(img[:, :, c].astype(np.float32), sg).astype(np.uint16)
            cells = []
            for k, f in STATS.items():
                se, n = sigma_equiv(base[k], widths(bl, S, f))
                if se is None:
                    cells.append("%17s" % "UNSCORED"); bad[k] += 1; continue
                err = se - sg
                ok = abs(err) <= max(0.06, 0.20*sg)
                bad[k] += (not ok)
                cells.append("%17s" % ("%6.3f (%+.3f)%s" % (se, err, "" if ok else "!")))
            print("%10.2f | %s" % (sg, " | ".join(cells)))
            sys.stdout.flush()
        print()
        good = [k for k in STATS if bad[k] == 0]
        for k in STATS:
            print("  %-5s : %d/%d arms ok  %s" % (k, len(ladder)-bad[k], len(ladder),
                                                  "PASSED" if bad[k] == 0 else "FAILED"))
        print("\nusable statistics: %s" % (", ".join(good) if good else "NONE"))
        sys.exit(0 if good else 1)

    stat = sys.argv[2]; fn = STATS[stat]
    print("sigma-equivalent blur difference, NEW relative to OLD  (stat=%s)" % stat)
    print("positive => new blurrier; negative => new sharper\n")
    print("%-34s %6s %10s   %s" % ("subject", "n", "sigma_eq", "reading"))
    print("-" * 78)
    for subject in sys.argv[3:]:
        if not os.path.exists(NEW % subject):
            print("%-34s  NEW MASTER ABSENT" % subject); continue
        img, S = load_sites(OLD % subject)
        nimg = vc_ca.load(NEW % subject)
        if nimg.shape != img.shape:
            print("%-34s  GEOMETRY DIFFERS %s vs %s" % (subject, img.shape, nimg.shape)); continue
        se, n = sigma_equiv(widths(img, S, fn), widths(nimg, S, fn))
        if se is None:
            print("%-34s %6d  UNSCORED" % (subject, n)); continue
        rd = "new BLURRIER" if se > 0.05 else ("new SHARPER" if se < -0.05 else "no blur difference")
        print("%-34s %6d %10.3f   %s" % (subject, n, se, rd))
        sys.stdout.flush()
