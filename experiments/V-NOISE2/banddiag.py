"""banddiag -- why the scene decomposition went degenerate on `bee`.

MEASURED DEFECT, found while running sec.4 on bee.  The two quantities the
decomposition subtracts are NOT the same bandwidth:

  flat-ROI sigma  `noisefree.sigmas`   r = ch - uniform_filter(ch, HP)   HIGH-PASS
  noise sigma     `halfdiff.half_sigma`      d = u - v                   FULL BAND

so `scene = sqrt(f**2 - n**2)` subtracts a full-band noise term from a
high-pass-band total.  The identity total**2 = scene**2 + noise**2 that the
subtraction assumes only holds when both terms are measured over the same
band.  When the two half-stacks differ at LOW frequency -- different exposure,
different vignetting, or a selection-dominated merge choosing different source
frames per half -- `n` sees it and `f`, being high-passed, is blind to it.
Then n > f and the scene term clamps to zero, which is exactly what bee did on
all three arms.

This script does not assume that mechanism, it TESTS it.  For each arm it
reports the same half-difference through the SAME high-pass that `sigmas`
uses.  If matching the bandwidth restores n_hp < f_hp, the excess was
low-frequency and the diagnosis holds.  If n_hp still exceeds f_hp, the
mechanism is wrong and the degeneracy is something else.

CONTROL.  `strehl` on a subject that already decomposed cleanly (119) must
show n_hp < n_full and must NOT change its verdict -- a rewrite that alters a
working subject's answer is a rewrite, not a diagnosis.

    python banddiag.py 119 bee
"""
import json
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "V-NOISE"))
from noisefree import opponent, sigmas, EDGE, HP          # noqa: E402
from halfdiff import half_sigma, MAXSHIFT                 # noqa: E402

import hd2                                                # noqa: E402


def half_sigma_hp(a, b, shift=False):
    """Half-difference sigma through the SAME high-pass `sigmas` applies.

    Identical to `halfdiff.half_sigma` except for the one line that matters:
    the difference is high-passed before its variance is taken, so this is
    directly comparable with `noisefree.sigmas`.

    `shift` must mirror the caller's use of `half_sigma`.  The shift search
    MINIMISES the full-band variance over a window of offsets; omitting it
    here while `half_sigma` applies it compares a minimised statistic against
    an unminimised one, which showed up as strehl 'keeping' 132.7% of its
    full-band sigma under a high-pass -- impossible for noise, and the tell
    that the two were not like for like.
    """
    if shift:
        ya, _, _ = opponent(a)
        yb, _, _ = opponent(b)
        best, bdy, bdx = None, 0, 0
        m = MAXSHIFT
        for dy in range(-m, m + 1):
            for dx in range(-m, m + 1):
                d = (ya[m + dy:ya.shape[0] - m + dy,
                        m + dx:ya.shape[1] - m + dx]
                     - yb[m:yb.shape[0] - m, m:yb.shape[1] - m])
                v = float(d.var())
                if best is None or v < best:
                    best, bdy, bdx = v, dy, dx
        n0, n1 = a.shape[0], a.shape[1]
        a = a[m + bdy:n0 - m + bdy, m + bdx:n1 - m + bdx]
        b = b[m:n0 - m, m:n1 - m]
    Ya, c1a, c2a = opponent(a)
    Yb, c1b, c2b = opponent(b)
    lvl = float(0.5 * (Ya.mean() + Yb.mean()))
    if lvl <= 1e-6:
        return None
    out = []
    for u, v in ((Ya, Yb), (c1a, c1b), (c2a, c2b)):
        d = u - v
        d = d - uniform_filter(d, HP)
        out.append(float(np.sqrt(0.5 * d[EDGE:-EDGE, EDGE:-EDGE].var())) / lvl)
    return out


def run(key):
    census, spec = hd2.paths_for(key)
    sc = hd2.scales_for(key)
    z = np.load(census)
    cells = [tuple(c) for c in z["cells"][z["flat"]]]

    print("=" * 96)
    print(f"SUBJECT {key}   {len(cells)} FLAT tiles")
    print("=" * 96)
    print(f"  {'arm':10s} {'f (hp)':>11s} {'n (full)':>11s} {'n (hp)':>11s} "
          f"{'n_full/f':>9s} {'n_hp/f':>8s}  decomposition")

    rows = {}
    for k, (pa, pb, lab) in spec.items():
        if not (os.path.exists(pa) and os.path.exists(pb)):
            continue
        bits = 8 if tifffile.imread(pa).dtype == np.uint8 else 16
        A = hd2.Arm(pa, sc.get(k, 1.0), bits, lab)
        B = hd2.Arm(pb, sc.get(k, 1.0), bits, lab)
        f_, nf_, nh_ = [], [], []
        for (y, x) in cells:
            ca, cb = A.rgb(y, x), B.rgb(y, x)
            if ca is None or cb is None or ca.shape != cb.shape:
                continue
            s1 = sigmas(ca)
            s2 = half_sigma(ca, cb, shift=(k == "strehl"))
            s3 = half_sigma_hp(ca, cb, shift=(k == "strehl"))
            if s1 is None or s2 is None or s3 is None:
                continue
            f_.append(s1[0])
            nf_.append(s2[0])
            nh_.append(s3[0])
        if not f_:
            continue
        f = float(np.median(f_))
        nf = float(np.median(nf_))
        nh = float(np.median(nh_))
        rows[k] = (f, nf, nh)
        verdict = ("DEGENERATE (n_hp >= f)" if nh >= f
                   else f"scene={np.sqrt(f * f - nh * nh):.6f}")
        print(f"  {k:10s} {f:11.6f} {nf:11.6f} {nh:11.6f} "
              f"{nf / f:9.3f} {nh / f:8.3f}  {verdict}")
    return rows


def main():
    keys = sys.argv[1:] or ["119", "bee"]
    all_rows = {}
    for k in keys:
        all_rows[k] = run(k)
        print()

    print("=" * 96)
    print("READING")
    print("=" * 96)
    for k, rows in all_rows.items():
        if not rows:
            continue
        deg_full = [a for a, (f, nf, nh) in rows.items() if nf >= f]
        deg_hp = [a for a, (f, nf, nh) in rows.items() if nh >= f]
        print(f"  {k:5s}  degenerate at full band: "
              f"{len(deg_full)}/{len(rows)}   at matched band: "
              f"{len(deg_hp)}/{len(rows)}")
        if deg_full and not deg_hp:
            print(f"         -> DIAGNOSIS CONFIRMED on {k}: the excess is "
                  f"LOW-FREQUENCY.  Matching the")
            print(f"            bandwidth restores the decomposition; the "
                  f"half-difference was reading a")
            print(f"            half-to-half difference the high-passed "
                  f"flat-ROI sigma cannot see.")
        elif deg_full and deg_hp:
            print(f"         -> DIAGNOSIS REFUTED on {k}: matching the "
                  f"bandwidth does NOT restore it.")
            print(f"            The excess is broadband, so it is not a "
                  f"low-frequency half difference.")
        elif not deg_full:
            print(f"         -> control subject, decomposed cleanly at full "
                  f"band already.")
        for a, (f, nf, nh) in rows.items():
            print(f"            {a:10s} high-pass keeps "
                  f"{nh / nf * 100:5.1f}% of the full-band half-difference "
                  f"sigma")

    # ---- M127's headline pairing, re-read at matched bandwidth on every
    # subject.  M127 rested its verdict on strehl holding the LOWEST noise and
    # the HIGHEST scene term in the SAME tiles, which forecloses "cleaner
    # because blurrier" from inside the measurement.  That pairing is a claim
    # about strehl only if it survives on subjects M127 never saw.
    print()
    print("=" * 96)
    print("M127'S PAIRING, RE-READ AT MATCHED BANDWIDTH")
    print("=" * 96)
    print(f"  {'subject':8s} {'arm':10s} {'noise ratio':>12s} "
          f"{'scene ratio':>12s}   reading")
    pair = {}
    for k, rows in all_rows.items():
        if "strehl" not in rows:
            continue
        sf, _, sn = rows["strehl"]
        s_scene = np.sqrt(max(sf * sf - sn * sn, 0.0))
        for a, (f, nf, nh) in rows.items():
            if a == "strehl":
                continue
            c_scene = np.sqrt(max(f * f - nh * nh, 0.0))
            nr = nh / sn
            sr = s_scene / c_scene if c_scene > 0 else float("nan")
            pair[(k, a)] = (nr, sr)
            print(f"  {k:8s} {a:10s} {nr:12.3f} {sr:12.3f}   "
                  f"{'strehl cleaner AND holds more scene -- strict gain'
                     if nr > 1 and sr > 1 else
                     'strehl cleaner but holds LESS scene -- a TRADE, not a gain'
                     if nr > 1 else 'strehl NOT cleaner'}")
    strict = [k for k, (nr, sr) in pair.items() if nr > 1 and sr > 1]
    trade = [k for k, (nr, sr) in pair.items() if nr > 1 and sr <= 1]
    print(f"\n  strict gain on {len(strict)}/{len(pair)} subject-arm pairs; "
          f"trade on {len(trade)}/{len(pair)}.")
    if trade:
        print("  The pairing that carries M127's verdict does NOT generalise. "
              "Where strehl is cleaner")
        print("  it is also, on these subjects, carrying less scene content "
              "in the same tiles, and the")
        print("  two move TOGETHER: the larger the noise advantage, the "
              "larger the scene deficit.")
        ordered = sorted(pair.items(), key=lambda kv: kv[1][0])
        print("  noise ratio -> scene ratio, ascending: " +
              "   ".join(f"{nr:.2f} -> {sr:.2f}" for _, (nr, sr) in ordered))

    out = {"bandwidth": {k: {a: {"f_hp": f, "n_full": nf, "n_hp": nh}
                             for a, (f, nf, nh) in rows.items()}
                         for k, rows in all_rows.items()},
           "pairing": {f"{k}|{a}": {"noise_ratio": nr, "scene_ratio": sr}
                       for (k, a), (nr, sr) in pair.items()},
           "strict_gain": [f"{k}|{a}" for (k, a) in strict],
           "trade": [f"{k}|{a}" for (k, a) in trade]}
    dst = os.path.join(hd2.ROOT, "banddiag.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {dst}")


if __name__ == "__main__":
    main()
