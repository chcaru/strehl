"""M35 step 1: build dense focus volumes on two stacks with different apertures.

Question 70 asks whether M33's result -- that the log-domain (Gaussian) three-point
fit beats the parabolic one for sub-frame peak HEIGHT -- survives away from
`coffee-bean`'s optics.  Fact 274 already gives a reason to doubt it: the implied
Gaussian width drifts 1.68 -> 2.45 dense frames across the decimation ladder, so
the through-focus response has heavier shoulders than a Gaussian and the log fit
is an approximation that merely happens to be a much better one *there*.

EXIF gives a clean aperture ladder at fixed focal length (200 mm, i.e. the 100 mm
GM with the 2x TC in the path):

    119MSDCF     33 frames   f/5.6   ISO  50    <- same ISO as coffee-bean
    coffee-bean 105 frames   f/8     ISO  50    <- M33's stack
    112MSDCF     79 frames   f/11    ISO 500

CONFOUND, STATED UP FRONT: 119 vs coffee-bean is a clean aperture-only comparison
(both ISO 50).  112 changes aperture AND ISO together, so it cannot separate the
two on its own -- it is here to extend the aperture range, and any 112-only
finding has to be reported as aperture-or-SNR, not aperture.

Everything matches M33 exactly so the numbers are comparable: green sublattice
[0::2, 1::2], centred crop CY,CX,H = 1172,1757,512, black 512, Sobel magnitude
smoothed by a radius-2 box.  Nothing here is tuned per stack.
"""
import rawpy, numpy as np, glob, os, time, json
from scipy.ndimage import sobel, uniform_filter

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "out")
CACHE = os.path.join(OUT, "cache")
BLACK, R = 512, 2
CY, CX, H = 1172, 1757, 512

STACKS = {
    "119MSDCF": dict(path=r"D:\personal\macro\119MSDCF", f_marked=5.6, iso=50),
    "112MSDCF": dict(path=r"D:\personal\macro\112MSDCF", f_marked=11.0, iso=500),
}

meta = {}
for name, spec in STACKS.items():
    files = sorted(glob.glob(os.path.join(spec["path"], "*.ARW")))
    n = len(files)
    ys, xs = slice(0, 4688, 2), slice(1, 7028, 2)
    t0 = time.time()
    vol = np.empty((n, 2 * H, 2 * H), np.float32)
    sig0 = None
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible[ys, xs][CY - H:CY + H, CX - H:CX + H].astype(np.float32) - BLACK
        if i == 0:
            sig0 = v.copy()
        gx = sobel(v, axis=1, mode="nearest")
        gy = sobel(v, axis=0, mode="nearest")
        vol[i] = uniform_filter(np.hypot(gx, gy), size=2 * R + 1, mode="nearest")
    dt = time.time() - t0
    np.save(os.path.join(CACHE, f"{name}_focus.npy"), vol)

    g = spec["iso"] / 436.8
    rn = 4.20 if spec["iso"] < 400 else 1.47
    snr = np.clip(sig0, 0, None) / np.sqrt(g * np.clip(sig0, 0, None) + (rn * g) ** 2)
    am = vol.argmax(0)
    meta[name] = dict(
        n_frames=int(n), f_marked=spec["f_marked"], iso=spec["iso"], g=g, rn_e=rn,
        decode_s=round(dt, 1),
        signal_median=float(np.median(sig0)),
        snr_median=float(np.median(snr)), frac_below_snr10=float((snr < 10).mean()),
        argmax_p05=int(np.percentile(am, 5)), argmax_median=int(np.median(am)),
        argmax_p95=int(np.percentile(am, 95)),
        frac_argmax_at_boundary=float(((am <= 1) | (am >= n - 2)).mean()),
    )
    print(f"{name}: n={n} f/{spec['f_marked']} ISO{spec['iso']}  {dt:.0f}s  "
          f"SNR med {meta[name]['snr_median']:.1f}  "
          f"argmax p05-p95 {meta[name]['argmax_p05']}-{meta[name]['argmax_p95']}  "
          f"boundary {meta[name]['frac_argmax_at_boundary']:.2%}")

json.dump(meta, open(os.path.join(OUT, "01-build.json"), "w"), indent=1)
print("wrote 01-build.json")
