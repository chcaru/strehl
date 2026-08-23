"""
M28 / 01 -- Is an outlier mask separable from defocus in a focus stack?

Review item R10 asks for a Wronski-style robustness mask: per-tile, per-frame,
noise-normalised disagreement against a running estimate. That shape is correct
for a BURST, where every frame is nominally identical so disagreement means
motion. A focus stack is the opposite case: the frames are SUPPOSED to disagree,
and their disagreement is the entire signal the merge exists to harvest. A naive
robustness mask would down-weight exactly the defocused frames the estimation
thesis wants to use.

So the prior question is whether outlier signal is separable from defocus at all.

Proposed separator: SPATIAL SCALE. Defocus is a lowpass operation -- it destroys
high frequencies and leaves low ones nearly untouched (MTF -> 1 as f -> 0 for any
PSF that conserves energy). A real outlier (a subject that moved, a bubble that
burst) displaces mass and therefore changes LOW frequencies too. So above some
spatial scale the residual should stop being defocus and start being outliers.

PRE-REGISTERED PREDICTIONS (written before the first run):

  P1  At full resolution the residual is large in EVERY stack, including the
      clean negative control, because it is measuring defocus and not outliers.
  P2  Under progressive lowpass the negative control's residual collapses toward
      the noise floor (|z| ~ 1) while the positive control's does not.
  P3  There is a crossover scale, and it is the design parameter the merge needs.
  P4  CONFOUND MADE VISIBLE: breathing (-1.0 to -1.8% scale drift, unaligned
      here) also displaces mass, so it also survives the lowpass. Its signature
      is RADIAL -- residual grows with distance from the scale centre -- while a
      genuine outlier does not care about radius. Script 02 tests this.

CONTROLS:
  negative   109MSDCF       22 frames, ISO 160. Photometrically quietest stack
                            in the corpus (0.91% p-p, fact 180), no known motion.
  intermediate coffee-bubbles 19 frames, ISO 1000. Bubbles move slowly.
  positive   foam           100 frames. REJECTED as a stack because the scene
                            visibly evolves -- which makes it the ideal
                            known-real positive control for this question.

Per fact 182 the per-frame gain is FITTED, never read from EXIF.
"""
import sys, glob, os, json
import numpy as np
import rawpy
import exifread

BLACK = 512.0
CROP = 3072          # centred crop of the full sensor, before sublattice
DECIM = [1, 2, 4, 8, 16, 32, 64]

STACKS = [
    ("109MSDCF",       r"D:\personal\macro\109MSDCF",       1,  "negative"),
    ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles", 1,  "intermediate"),
    ("foam",           r"D:\personal\macro\foam",           2,  "positive"),
]


def iso_of(path):
    with open(path, "rb") as fh:
        t = exifread.process_file(fh, stop_tag="EXIF ISOSpeedRatings", details=False)
    for k in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if k in t:
            return float(str(t[k]).strip("[]").split(",")[0])
    return None


def noise_params(iso):
    """sigma^2(S) = g*S + (RN_e*g)^2 in native raw DN, per M4."""
    g = iso / 436.8
    rn_e = 4.20 if iso < 400 else 1.47
    return g, (rn_e * g) ** 2


def load_green(path):
    """Centred CROP x CROP window of the sensor, green sublattice at (0,1)."""
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        h, w = v.shape
        y0 = ((h - CROP) // 2) & ~1
        x0 = ((w - CROP) // 2) & ~1
        blk = v[y0:y0 + CROP, x0:x0 + CROP]
        g = blk[0::2, 1::2].astype(np.float32) - BLACK
    return g


def area_mean(a, d):
    if d == 1:
        return a
    n, h, w = a.shape
    h2, w2 = (h // d) * d, (w // d) * d
    return a[:, :h2, :w2].reshape(n, h2 // d, d, w2 // d, d).mean(axis=(2, 4))


def run(name, folder, step, role, out):
    files = sorted(glob.glob(os.path.join(folder, "*.ARW")))[::step]
    iso = iso_of(files[0])
    g, rn2 = noise_params(iso)
    print(f"\n=== {name}  ({role})  {len(files)} frames  ISO {iso:.0f}  "
          f"g={g:.4f} DN/e-  RN_DN={np.sqrt(rn2):.3f} ===", flush=True)

    stack = np.stack([load_green(f) for f in files])
    print(f"    loaded {stack.shape}", flush=True)

    # Fitted per-frame gain (fact 182: never from EXIF).
    med = np.median(stack.reshape(len(files), -1), axis=1)
    gain = med / np.median(med)
    stack /= gain[:, None, None]
    print(f"    fitted gain range {gain.min():.4f} .. {gain.max():.4f} "
          f"(p-p {100*(gain.max()-gain.min()):.2f}%)", flush=True)

    rows = []
    for d in DECIM:
        a = area_mean(stack, d)
        ref = np.median(a, axis=0)
        # Averaging d^2 independent pixels divides the variance by d^2.
        sig = np.sqrt(np.maximum(g * np.maximum(ref, 0) + rn2, 1e-6)) / d
        z = np.abs(a - ref) / sig
        per_frame = np.median(z.reshape(len(files), -1), axis=1)
        rows.append(dict(
            d=d, shape=list(a.shape[1:]),
            med_z=float(np.median(z)),
            max_frame_med=float(per_frame.max()),
            min_frame_med=float(per_frame.min()),
            spread=float(per_frame.max() / max(per_frame.min(), 1e-9)),
            frac_z5=float((z > 5).mean()),
            per_frame=[round(float(x), 3) for x in per_frame],
        ))
        print(f"    d={d:3d}  {a.shape[1]:5d}x{a.shape[2]:<5d}  "
              f"median|z| {rows[-1]['med_z']:8.2f}   "
              f"per-frame med|z| {rows[-1]['min_frame_med']:7.2f} .. "
              f"{rows[-1]['max_frame_med']:7.2f}  "
              f"(x{rows[-1]['spread']:5.2f})   frac|z|>5 {rows[-1]['frac_z5']:.4f}",
              flush=True)

    out[name] = dict(role=role, n=len(files), iso=iso, g=g,
                     gain_pp=float(100 * (gain.max() - gain.min())), rows=rows)


if __name__ == "__main__":
    out = {}
    for name, folder, step, role in STACKS:
        run(name, folder, step, role, out)
    dest = os.path.join(os.path.dirname(__file__), "..", "out")
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "01-scale-sweep.json"), "w") as fh:
        json.dump(out, fh, indent=1)

    print("\n" + "=" * 78)
    print("READ: P1 predicts a large median|z| at d=1 in ALL stacks (defocus).")
    print("      P2 predicts the negative control collapses toward |z|~1 under")
    print("      lowpass while the positive control does not.")
    print("      The ratio of the two is the separability this milestone is about.")
    print("=" * 78)
    for d_i, d in enumerate(DECIM):
        vals = {k: v["rows"][d_i]["med_z"] for k, v in out.items()}
        neg = vals["109MSDCF"]
        print(f"  d={d:3d}   " + "   ".join(f"{k} {v:8.2f}" for k, v in vals.items())
              + f"    |   pos/neg {vals['foam']/max(neg,1e-9):7.2f}")
