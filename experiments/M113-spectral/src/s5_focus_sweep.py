"""M113-spectral S5 + rival 6: does lateral CA vary THROUGH the focus sweep?

RIVAL 6, WHICH I RAISED AFTER SEEING S2/S3 AND WHICH IS NOT SPECTRAL.
The merge elects a different frame per pixel. Every frame sits at a different
focus, and focus breathing changes magnification frame to frame (the project
measures 232.7 px corner-to-corner on bee-3-cpl). Align removes the per-frame
similarity but it is ACHROMATIC, so it cannot create or remove an INTER-CHANNEL
scale. What it also cannot remove is this: if the lens's lateral CA itself varies
through the focus sweep, then the merged image's effective CA is a
DEPTH-WEIGHTED MIXTURE over whichever frames each subject elects. Two subjects
with different depth structure would then need different coefficients through the
same glass with no spectral effect whatsoever.

This is a simpler explanation than spectrum and it must be excluded before the
owner is sent to shoot coloured gels.

TEST. Render single frames from across one stack's focus sweep, each alone, with
STREHL_ALIGN=0 so there is no align and no merge, and measure needed_R on each.
  * needed_R flat across the sweep -> the mixture cannot vary between subjects,
    rival 6 is dead.
  * needed_R varying across the sweep by an amount comparable to the 118.7 ppm
    between-subject spread -> rival 6 is live and gels are the wrong capture.

ALSO NOTED: with STREHL_ALIGN=0 the OFF and ON arms come out BYTE-IDENTICAL, so
STREHL_FIX_CA is a silent no-op when alignment is disabled. Only the OFF arm is
measured here; that is all this test needs.
"""
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                        # noqa: E402
from c4_globalfit import cs, fit_eps              # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_measure import paths, measure_ch, FOCUS   # noqa: E402

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
ROOT = Path(r"C:\dev\strehl-out\M113-spectral")
MACRO = Path(r"D:\personal\macro")
SWEEP = {"bee-3-cpl": [0, 75, 149, 224, 298], "couch-fibers-cpl": [0, 75, 149, 224, 298]}

def render_one(stack, idx):
    tif = ROOT / "arms" / ("%s-f%03d.tif" % (stack, idx))
    if tif.exists():
        return tif
    frames = sorted((MACRO / stack).glob("*.ARW"))
    scratch = ROOT / "sweep" / ("%s-f%03d" % (stack, idx))
    scratch.mkdir(parents=True, exist_ok=True)
    dst = scratch / frames[idx].name
    if not dst.exists():
        shutil.copy2(frames[idx], dst)                 # reads D:, writes C:
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    env["STREHL_ALIGN"] = "0"
    cache = ROOT / "cache" / ("sweep-%s-f%03d" % (stack, idx))
    cache.mkdir(parents=True, exist_ok=True)
    env["STREHL_CACHE_DIR"] = str(cache)
    p = subprocess.run([str(EXE), "stack", str(scratch), "-o", str(tif)],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        print((p.stdout or "") + (p.stderr or "")); sys.exit("sweep render failed")
    return tif

def eps_of(path):
    img, W, H = cs.load_tiff_u16(str(path))
    cx, cy = W / 2.0, H / 2.0
    ws = c4g.grid(img, W, H)
    m = measure_ch(img, ws, 0, cx, cy)
    eps, tx, ty, n, rms = fit_eps(m, cx, cy)
    del img
    return eps, len(ws), n, rms

def main():
    c4g.STEP = 100
    out = {}

    print("=" * 96)
    print("S5 -- ALIGN + MERGE null: single un-aligned frame vs the aligned merge")
    print("=" * 96)
    print("%-20s %14s %14s %10s %8s" % ("stack", "merged ppm", "1 frame ppm", "delta", "windows"))
    for name in ("bee-3-cpl", "couch-fibers-cpl", "bee-1-cpl"):
        one = ROOT / "arms" / ("%s-1frame-off.tif" % name)
        if not one.exists():
            continue
        e1, nw, n, rms = eps_of(one)
        poff, _ = paths(name)
        em, _, _, _ = eps_of(poff)
        out[name] = dict(merged=-em, one=-e1, windows=nw)
        print("%-20s %14.1f %14.1f %10.1f %8d"
              % (name, -em * 1e6, -e1 * 1e6, (-e1 + em) * 1e6, nw))
    print("\nBAR: agreement within 60 ppm means align and merge do not manufacture needed_R.")

    print("\n" + "=" * 96)
    print("RIVAL 6 -- lateral CA THROUGH the focus sweep (single frames, no align, no merge)")
    print("=" * 96)
    for stack, idxs in SWEEP.items():
        print("\n%s" % stack)
        print("  %-8s %14s %10s %8s" % ("frame", "needed_R ppm", "windows", "rms px"))
        vals = []
        for i in idxs:
            t = render_one(stack, i)
            e, nw, n, rms = eps_of(t)
            vals.append(-e * 1e6)
            print("  %-8d %14.1f %10d %8.4f" % (i, -e * 1e6, nw, rms))
        out["sweep_" + stack] = vals
        v = np.array(vals)
        print("  range across the sweep = %.1f ppm  (between-subject spread is 118.7 ppm)" % (v.max() - v.min()))

    print("\n" + "=" * 96)
    a = out.get("sweep_bee-3-cpl"); b = out.get("sweep_couch-fibers-cpl")
    if a and b:
        ra, rb = max(a) - min(a), max(b) - min(b)
        print("VERDICT ON RIVAL 6: sweep ranges %.1f and %.1f ppm vs 118.7 ppm between subjects."
              % (ra, rb))
        print("  means: bee-3 %.1f ppm, couch %.1f ppm -- separation %.1f ppm"
              % (np.mean(a), np.mean(b), abs(np.mean(a) - np.mean(b))))
        if max(ra, rb) < 60:
            print("  -> CA is stable through focus; a depth-weighted mixture cannot")
            print("     produce the between-subject spread. RIVAL 6 REFUTED.")
        else:
            print("  -> CA varies through focus; depth structure is a live rival to spectrum.")

    with open(ROOT / "s5_focus_sweep.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote s5_focus_sweep.json")

if __name__ == "__main__":
    main()