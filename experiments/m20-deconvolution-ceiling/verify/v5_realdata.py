"""M20 verification -- Gate 3.3: the real-data local-SNR distribution, on TWO stacks.

Independent re-measurement of report section 7, plus:
  * an explicit CFA-phase audit from rawpy metadata (not assumed)
  * the second green plane G2 as a control -- the two must agree
  * an unbiased local-variance estimator (the box estimator is biased by (n-1)/n)
  * 119MSDCF, which the report never ran, and which fact 88 says is noisier
Nothing is written to C:\\dev\\macro.  rawpy.imread opens read-only.
"""
import os
import sys
import glob
import numpy as np
import rawpy
import exifread
from scipy.ndimage import uniform_filter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
W = 9
BLACK = 512


def read_iso(path):
    with open(path, "rb") as fh:
        tags = exifread.process_file(fh, details=False)
    for k in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if k in tags:
            return int(str(tags[k]).split(",")[0].strip("[] "))
    return None


def cfa_audit(path):
    with rawpy.imread(path) as r:
        pat = r.raw_pattern.tolist()
        desc = r.color_desc.decode()
        cv = r.raw_colors_visible
        planes = {
            "[0::2,1::2]": cv[0::2, 1::2],
            "[1::2,0::2]": cv[1::2, 0::2],
            "[0::2,0::2]": cv[0::2, 0::2],
            "[1::2,1::2]": cv[1::2, 1::2],
        }
        info = {}
        for k, v in planes.items():
            idx = np.unique(v)
            info[k] = (idx.tolist(), "".join(desc[i] for i in idx))
        shape = r.raw_image_visible.shape
        black = list(r.black_level_per_channel)
    return pat, desc, info, shape, black


def local_stats(a, w=W, unbiased=True):
    m = uniform_filter(a, w)
    m2 = uniform_filter(a * a, w)
    v = np.maximum(m2 - m * m, 0.0)
    if unbiased:
        n = float(w * w)
        v = v * (n / (n - 1.0))
    return m, v


def measure(stack_dir, slicer, unbiased=True, label=""):
    files = sorted(glob.glob(os.path.join(stack_dir, "*.ARW")))
    iso = read_iso(files[0])
    g = iso / 436.8
    rn_e = 1.47 if iso >= 400 else 4.20
    print(f"  [{label}] {len(files)} frames, ISO {iso} -> g = {g:.5f} DN/e-, RN = {rn_e} e-")
    best = None
    best_sharp = None
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            gp = slicer(r.raw_image_visible).astype(np.float32) - BLACK
        m, v = local_stats(gp, unbiased=unbiased)
        nvar = g * np.maximum(m, 0.0) + (rn_e * g) ** 2
        sig_n = np.sqrt(np.maximum(nvar, 1e-6))
        signal = np.sqrt(np.maximum(v - nvar, 0.0))
        rel = sig_n / np.maximum(signal, 1e-6)
        if best is None:
            best = rel
            best_sharp = signal
            print(f"       plane {gp.shape}, modelled sigma {sig_n.min():.1f}..{sig_n.max():.1f} DN, "
                  f"local mean {m.min():.0f}..{m.max():.0f} DN")
        else:
            np.minimum(best, rel, out=best)
            np.maximum(best_sharp, signal, out=best_sharp)
        del gp, m, v, nvar, sig_n, signal, rel
    return best, best_sharp, iso, g, rn_e


def report(best, tag, crossovers):
    print(f"    percentiles of sigma_local/signal_local at each pixel's BEST frame [{tag}]:")
    line = "      "
    for p in (5, 10, 25, 50, 75, 90):
        line += f"p{p}={np.percentile(best, p):7.4f}  "
    print(line)
    for lab, c in crossovers:
        print(f"      frac below {c:.4f} ({lab}): {float(np.mean(best < c))*100:6.2f}%")
    return float(np.median(best))


def main():
    stacks = [
        ("109MSDCF", r"C:\dev\macro\test\109MSDCF"),
        ("119MSDCF", r"C:\dev\macro\test\119MSDCF"),
    ]
    print("=" * 92)
    print("GATE 3.3a -- CFA PHASE AUDIT (the report asserts [0::2,1::2] is a green plane)")
    print("=" * 92)
    for name, d in stacks:
        f0 = sorted(glob.glob(os.path.join(d, "*.ARW")))[0]
        pat, desc, info, shape, black = cfa_audit(f0)
        print(f"  {name}: raw_pattern {pat}  color_desc {desc}  visible {shape}  black {black}")
        for k, (idx, letters) in info.items():
            mark = "  <-- used by the report" if k == "[0::2,1::2]" else ""
            print(f"      {k} -> colour index {idx} = '{letters}'{mark}")
    print()

    crossovers_109 = None
    results = {}
    print("=" * 92)
    print("GATE 3.3b -- local-SNR distribution, both green planes, both stacks")
    print("=" * 92)
    for name, d in stacks:
        print(f"--- {name} ---")
        for tag, sl in (("G1 [0::2,1::2]", lambda a: a[0::2, 1::2]),
                        ("G2 [1::2,0::2]", lambda a: a[1::2, 0::2])):
            best, sharp, iso, g, rn = measure(d, sl, unbiased=True, label=f"{name} {tag}")
            med = report(best, tag, [("report's 0.3440", 0.3440),
                                     ("oracle 0.5734", 0.5734)])
            results[(name, tag)] = med
            np.save(os.path.join(OUT, f"best_{name}_{tag.split()[0]}.npy"),
                    best.astype(np.float32))
            del best, sharp
        print()

    print("=" * 92)
    print("GATE 3.3c -- estimator-bias control: biased vs unbiased local variance, 109 G1")
    print("=" * 92)
    for ub in (False, True):
        best, _, _, _, _ = measure(stacks[0][1], lambda a: a[0::2, 1::2], unbiased=ub,
                                   label=f"109 unbiased={ub}")
        report(best, f"unbiased={ub}", [("0.3440", 0.3440)])
        del best
    print()
    print("median sigma_rel summary:")
    for k, v in results.items():
        print(f"  {k[0]} {k[1]}: {v:.4f}")


if __name__ == "__main__":
    main()
