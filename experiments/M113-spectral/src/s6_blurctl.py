"""M113-spectral S6: is S5's failure real, or is it defocus attenuation?

S5 measured needed_R = 192.0 ppm on a single un-aligned frame of bee-3-cpl
against 529.9 ppm on the aligned merge, and the focus sweep ranged 14.4 to
192.0 ppm within one stack. Read naively that says align and merge manufacture
most of needed_R.

I DO NOT BELIEVE IT YET, BECAUSE MY OWN TEST IS CONFOUNDED. A single frame of a
299-frame macro bracket is IN FOCUS ONLY IN A NARROW BAND; the rest of the field
is defocused. Defocus is a low-pass, and M113-ca established on this exact
measurement that a low-pass attenuates the recovered inter-channel displacement:
blurring drove ORCH's estimator from -40.8 ppm to -707.2 ppm in one direction,
and the guided demosaic suppressed the honest signal in the other. A merged
all-in-focus image and a mostly-defocused single frame are therefore NOT
comparable, and the sweep's correlation with rms (0.2821 at frame 0 where
needed_R reads 14.4, against 0.4862 at frame 149 where it reads 192.0) is what
that confound would look like.

TWO CONTROLS.

A. BLUR THE MERGE. Apply a Gaussian to the all-in-focus merged image and
   re-measure. If needed_R falls toward the single-frame value, the single-frame
   deficit is defocus attenuation and S5's raw delta means nothing.

B. A FLAT SUBJECT. flat-on-ruler-cpl is normal to the optical axis, so a single
   frame near best focus is sharp across the WHOLE field and is directly
   comparable to its own merge. This is the like-for-like version of S5.
"""
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                        # noqa: E402
from c4_globalfit import cs, fit_eps              # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_measure import measure_ch                 # noqa: E402

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
ROOT = Path(r"C:\dev\strehl-out\M113-spectral")
MACRO = Path(r"D:\personal\macro")
CA_LIN = Path(r"C:\dev\strehl-out\M113-ca\lin")

def eps_arr(arr):
    H, W = arr.shape[:2]
    cx, cy = W / 2.0, H / 2.0
    ws = c4g.grid(arr, W, H)
    m = measure_ch(arr, ws, 0, cx, cy)
    eps, tx, ty, n, rms = fit_eps(m, cx, cy)
    return eps, len(ws), rms

def hf_energy(arr):
    g = np.asarray(arr[::4, ::4, 1]).astype(np.float32)
    return float(np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean())

def render_1frame(stack, idx, tag):
    tif = ROOT / "arms" / ("%s-%s.tif" % (stack, tag))
    if tif.exists():
        return tif
    frames = sorted((MACRO / stack).glob("*.ARW"))
    scratch = ROOT / "sweep" / ("%s-%s" % (stack, tag))
    scratch.mkdir(parents=True, exist_ok=True)
    dst = scratch / frames[idx].name
    if not dst.exists():
        shutil.copy2(frames[idx], dst)
    env = dict(os.environ); env.pop("STREHL_FIX_CA", None)
    env["STREHL_ALIGN"] = "0"
    cache = ROOT / "cache" / ("blur-%s-%s" % (stack, tag)); cache.mkdir(parents=True, exist_ok=True)
    env["STREHL_CACHE_DIR"] = str(cache)
    p = subprocess.run([str(EXE), "stack", str(scratch), "-o", str(tif)],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        print((p.stdout or "") + (p.stderr or "")); sys.exit("render failed")
    return tif

def main():
    c4g.STEP = 100
    out = {}

    print("=" * 92)
    print("CONTROL A -- blur the ALL-IN-FOCUS merge and re-measure needed_R")
    print("=" * 92)
    img, W, H = cs.load_tiff_u16(str(CA_LIN / "bee-3-cpl-binned-off.tif"))
    base = np.asarray(img[:, :, :]).astype(np.float32)
    del img
    one, _, _ = cs.load_tiff_u16(str(ROOT / "arms" / "bee-3-cpl-1frame-off.tif"))
    hf_one = hf_energy(one)
    e_one, _, rms_one = eps_arr(one)
    del one
    print("%-12s %13s %10s %12s" % ("sigma px", "needed_R ppm", "rms px", "hf energy"))
    rows = []
    for sg in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
        arr = base if sg == 0 else np.stack([gaussian_filter(base[:, :, c], sg) for c in range(3)], axis=2)
        e, nw, rms = eps_arr(arr)
        hf = hf_energy(arr)
        rows.append(dict(sigma=sg, needed=-e * 1e6, rms=rms, hf=hf))
        print("%-12.1f %13.1f %10.4f %12.2f" % (sg, -e * 1e6, rms, hf))
        if sg:
            del arr
    print("%-12s %13.1f %10.4f %12.2f   <- single un-aligned frame"
          % ("1 frame", -e_one * 1e6, rms_one, hf_one))
    out["blur"] = rows
    out["one"] = dict(needed=-e_one * 1e6, rms=rms_one, hf=hf_one)
    matched = [r for r in rows if r["hf"] <= hf_one]
    print("\nThe single frame's high-frequency energy is %.2f. Merge sigmas whose hf falls to"
          % hf_one)
    print("that level or below: %s" % (["%.1f" % r["sigma"] for r in matched] or "none in sweep"))
    if matched:
        m = matched[0]
        print("At sigma = %.1f the ALL-IN-FOCUS merge reads %.1f ppm, against the single frame's %.1f."
              % (m["sigma"], m["needed"], -e_one * 1e6))
    del base

    print("\n" + "=" * 92)
    print("CONTROL B -- flat-on-ruler-cpl: a subject normal to the axis, so one frame is")
    print("             sharp across the whole field and IS comparable to its merge")
    print("=" * 92)
    stack = "flat-on-ruler-cpl"
    frames = sorted((MACRO / stack).glob("*.ARW"))
    n = len(frames); ref = n // 2
    side = ROOT / ("%s-warpmap.txt" % stack)
    merged = ROOT / "arms" / ("%s-binned-off.tif" % stack)
    ok = True
    if not merged.exists():
        if not side.exists():
            env = dict(os.environ); env.pop("STREHL_FIX_CA", None)
            cache = ROOT / "cache" / (stack + "-align"); cache.mkdir(parents=True, exist_ok=True)
            env["STREHL_CACHE_DIR"] = str(cache)
            p = subprocess.run([str(EXE), "align", str(MACRO / stack), "--out", str(side),
                                "--reference", str(ref)], capture_output=True, text=True, env=env)
            if p.returncode != 0:
                print("  align refused: %s" % ((p.stdout + p.stderr).strip().splitlines() or ["?"])[-1])
                ok = False
        if ok:
            env = dict(os.environ); env.pop("STREHL_FIX_CA", None)
            env["STREHL_WARPMAP"] = str(side)
            cache = ROOT / "cache" / (stack + "-off"); cache.mkdir(parents=True, exist_ok=True)
            env["STREHL_CACHE_DIR"] = str(cache)
            p = subprocess.run([str(EXE), "stack", str(MACRO / stack), "-o", str(merged)],
                               capture_output=True, text=True, env=env)
            if p.returncode != 0:
                print(p.stdout[-800:] + p.stderr[-800:]); ok = False
    if ok and merged.exists():
        a, _, _ = cs.load_tiff_u16(str(merged))
        em, _, rm = eps_arr(a); hm = hf_energy(a); del a
        t = render_1frame(stack, ref, "flat1frame")
        b, _, _ = cs.load_tiff_u16(str(t))
        e1, _, r1 = eps_arr(b); h1 = hf_energy(b); del b
        print("%-22s %13s %10s %12s" % ("arm", "needed_R ppm", "rms px", "hf energy"))
        print("%-22s %13.1f %10.4f %12.2f" % ("aligned merge", -em * 1e6, rm, hm))
        print("%-22s %13.1f %10.4f %12.2f" % ("single frame, no align", -e1 * 1e6, r1, h1))
        print("\ndelta = %.1f ppm ; hf ratio single/merge = %.3f" % ((-e1 + em) * 1e6, h1 / hm))
        print("BAR: |delta| <= 60 ppm means align and merge do not manufacture needed_R.")
        print("RESULT: %s" % ("PASS -- pipeline is not the source" if abs((-e1 + em) * 1e6) <= 60
                              else "FAIL -- part of needed_R is manufactured"))
        out["flat"] = dict(merged=-em * 1e6, one=-e1 * 1e6, hf_merge=hm, hf_one=h1)

    with open(ROOT / "s6_blurctl.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote s6_blurctl.json")

if __name__ == "__main__":
    main()