"""The mean_coarse dose at FLAT and DETAIL sites, with intervals.

WHY THIS EXISTS. bandcheck.py measures the one 400 px site ORCH's 1:1 verdict was
formed on. That site is the FLATTEST region of the subject, chosen because mottle is
only legible where the subject is not. Sharpness measured there is close to
meaningless: a change that abolished focus selection at 4-64 px would be catastrophic
on detail and nearly invisible on a flat field. Reporting `sharp 0.981` from a flat
site as evidence that a fix is free is the single most likely way to be wrong here,
and ORCH named it in advance.

So the same commissioned gauge is run at both site classes, and every mid-band number
is quoted beside a sharpness number measured on the SAME pixels.

Only mc arms are compared here. They come from one binary on one subject with one
differing environment variable, so they share a lattice exactly and need no
registration -- which keeps the sub-pixel resampling that would blur the measurand out
of the measurement entirely. The comparator arms need registration and stay in
bandcheck.py at the site where the published manifest supplies an integer shift.
"""
import json
import sys

import numpy as np
import tifffile

from bandcheck import commission
from bandlib import (ARMS, BANDS, CROP, MANIFEST, MC_DIR, boxblur, call, display,
                     fit_to, terms, verdict)

N_SITES = 8
BOOT = 2000
MARGIN = 300


def lum(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)


def pick_sites(ref, n, flattest):
    """Non-overlapping CROP-sized windows, by texture, PINNED on the reference arm.

    Pinned on one arm so every arm is measured on identical pixels; choosing per-arm
    would let each arm pick its own favourable ground.
    """
    l = lum(ref)
    s = 16
    d = l[::s, ::s]
    g = (np.abs(np.diff(d, axis=0)[:, :-1]) + np.abs(np.diff(d, axis=1)[:-1, :])).astype(np.float32)
    t = boxblur(g, max(1, CROP // (2 * s)))
    m = MARGIN // s
    t[:m, :] = t[-m:, :] = t[:, :m] = t[:, -m:] = np.nan
    order = np.argsort(np.nan_to_num(t, nan=np.inf if flattest else -np.inf), axis=None)
    if not flattest:
        order = order[::-1]
    out = []
    for idx in order:
        iy, ix = np.unravel_index(idx, t.shape)
        y = int(np.clip(iy * s - CROP // 2, 0, ref.shape[0] - CROP))
        x = int(np.clip(ix * s - CROP // 2, 0, ref.shape[1] - CROP))
        if all(abs(y - yy) >= CROP or abs(x - xx) >= CROP for yy, xx in out):
            out.append((y, x))
        if len(out) == n:
            break
    return out


def crop(a, y, x):
    if y < 0 or x < 0 or y + CROP > a.shape[0] or x + CROP > a.shape[1]:
        raise SystemExit("CROP OUT OF BOUNDS [%d:%d, %d:%d] of %s -- a silent clip "
                         "returns plausible numbers for pixels it never read"
                         % (y, y + CROP, x, x + CROP, a.shape))
    return a[y:y + CROP, x:x + CROP, :3].astype(np.float32)


def boot_ci(vals, rng, boot=BOOT):
    v = np.asarray(vals, float)
    idx = rng.integers(0, len(v), (boot, len(v)))
    m = np.median(v[idx], axis=1)
    return float(np.median(v)), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else "119MSDCF"
    man = json.loads(MANIFEST.read_text())
    site = next(s for s in man["sites"] if s.get("label") == "worst-on-subject")
    expo = site["exposure"]
    fits = site["fits"]["strehl"]

    ref16 = tifffile.imread(str(ARMS / "strehl-A.tiff"))
    y, x = site["y"] + fits["shift"][0], site["x"] + fits["shift"][1]
    c = crop(ref16, y, x) * np.array(fits["gain"], np.float32) + np.array(fits["offset"], np.float32)
    rng = np.random.default_rng(20260827)
    if not commission(c, expo, rng):
        print("\nREFUSING to report: the gauge is not commissioned")
        return 1
    del ref16, c

    base = tifffile.imread(str(MC_DIR / ("%s--mc0.tiff" % subject)))
    if subject != "119MSDCF":
        # No published manifest for this subject. Exposure is derived from the
        # REFERENCE arm and then PINNED across every arm, so the display nonlinearity
        # is identical on both sides of every ratio. Choosing it per arm would let a
        # brighter arm sit on a different part of the sRGB curve.
        expo = float(0.9 * 65535.0 / max(np.percentile(base[..., :3], 99.5), 1.0))
    print("\nsubject %s   exposure x%.4g (pinned across arms)" % (subject, expo))
    flat = pick_sites(base, N_SITES, True)
    det = pick_sites(base, N_SITES, False)
    print("\nsites: %d flat, %d detail, %d px each, pinned on mc=0"
          % (len(flat), len(det), CROP))
    bcrops = {"flat": [crop(base, *p) for p in flat],
              "detail": [crop(base, *p) for p in det]}
    bterms = {k: [terms(display(c, expo)) for c in v] for k, v in bcrops.items()}
    for k in ("flat", "detail"):
        mids = [float(np.mean(t["20-60"])) for t in bterms[k]]
        shs = [float(np.mean(t["sharp"])) for t in bterms[k]]
        print("  mc=0 %-7s 20-60 absolute median %6.3f   sharp median %7.3f"
              % (k, float(np.median(mids)), float(np.median(shs))))
    del base

    print("\n%-6s %-7s %-34s %s" % ("arm", "sites", "20-60 ratio [95% CI]",
                                    "  ".join("%7s" % b for b, _, _ in BANDS[:3])
                                    + "    sharp [95% CI]"))
    for mc in (3, 5, 7):
        p = MC_DIR / ("%s--mc%d.tiff" % (subject, mc))
        if not p.exists():
            continue
        a = tifffile.imread(str(p))
        for k, pts in (("flat", flat), ("detail", det)):
            vs = []
            for (yy, xx), bt in zip(pts, bterms[k]):
                ac = crop(a, yy, xx)
                g, o = fit_to(bcrops[k][pts.index((yy, xx))], ac)
                vs.append(verdict(bt, terms(display(ac * g + o, expo))))
            mid = boot_ci([v["20-60"] for v in vs], rng)
            sh = boot_ci([v["sharp"] for v in vs], rng)
            fine = float(np.median([v["5-15"] for v in vs]))
            n_sm = sum(v["smoothed"] for v in vs)
            print("mc=%-4d %-7s %6.3f [%6.3f, %6.3f]  %19s %7.3f  %6.3f [%6.3f, %6.3f]  "
                  "smoothed %d/%d"
                  % (mc, k, mid[0], mid[1], mid[2], "", fine, sh[0], sh[1], sh[2],
                     n_sm, len(vs)))
        del a
    return 0


if __name__ == "__main__":
    sys.exit(main())
