"""M113-ca B10: the ONLY measurement space with no cross-channel operator in it.

THE PROBLEM WITH EVERY SPACE MEASURED SO FAR. Both M114 renders and my own
linear renders pass through Malvar-He-Cutler. demosaic.rs documents its own
assumption in its own test name and doc comment:

    "Malvar-He-Cutler's gradient correction assumes the *colour difference*
     R - G is smoother than either channel, which is a property of real scenes
     and not a theorem."

A lateral-CA fringe IS roughness in R - G at an edge. So the demosaic's core
assumption is violated by exactly the signal being measured, and it smooths that
signal towards zero. Any inter-channel displacement measured on a demosaiced
render is therefore ATTENUATED by an unknown factor. `--srgb` then adds a
non-diagonal colour matrix on top of that.

THE BINNED RENDER HAS NEITHER. From the CLI's own help: "each output pixel is
one real sensor quad, R = R, G = (G1+G2)/2, B = B ... with white balance but NO
colour matrix", and "it is the file every number in this project's corpus was
measured on. It is byte-frozen."

CALIBRATION, NOT JUST COMPARISON. `applied = eps_on - eps_off` has a KNOWN
TRUTH: the ON arm warps red by a compile-time constant eps_r = -704.5 ppm. So
applied/eps_r measures the measurement chain's own transfer, and a space that
reports 1.0 is uncontaminated. That makes this a calibration of every other
space rather than a fourth opinion.

STEP is halved because the binned grid is half resolution, so that the windows
sample the same fraction of the field as at full resolution.
"""
import hashlib, json, os, subprocess, sys, time
from pathlib import Path
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c4_globalfit as c4g                                   # noqa: E402
from c4_globalfit import cs, measure, fit_eps, EPS_R          # noqa: E402

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
OUT = Path(r"C:\dev\strehl-out\M113-ca")
LIN = Path(r"C:\dev\strehl-out\M113-ca\lin")
KEY = "a7c2-fe100gm-2xtc-x4cpl"
STACKS = [
    ("bee-3-cpl", Path(r"D:\personal\macro\bee-3-cpl"),
     Path(r"C:\dev\strehl-out\M114-ca-verify\r1\m114-warpmap.txt")),
    ("couch-fibers-cpl", Path(r"D:\personal\macro\couch-fibers-cpl"),
     LIN / "couch-fibers-cpl-warpmap.txt"),
]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()

def render():
    for name, d, side in STACKS:
        for arm, val in (("off", None), ("on", KEY)):
            tif = LIN / ("%s-binned-%s.tif" % (name, arm))
            if tif.exists():
                print("  %-18s %-3s exists %s" % (name, arm, sha(tif)[:16]), flush=True); continue
            env = dict(os.environ)
            env.pop("STREHL_FIX_CA", None)
            env["STREHL_CACHE_DIR"] = str(OUT / "cache")
            env["STREHL_WARPMAP"] = str(side)
            if val is not None:
                env["STREHL_FIX_CA"] = val
            t = time.time()
            p = subprocess.run([str(EXE), "stack", str(d), "-o", str(tif)],
                               capture_output=True, text=True, env=env)
            if p.returncode != 0:
                print((p.stdout or "") + (p.stderr or ""))
                sys.exit("BINNED STACK FAILED %s %s" % (name, arm))
            print("  %-18s %-3s EXIT=0 %5.1fs  %s"
                  % (name, arm, time.time() - t, sha(tif)[:16]), flush=True)

def main():
    print("rendering binned (no --demosaic, no --srgb) arms")
    render()
    c4g.STEP = 100          # half-resolution grid -> half the step
    res = {}
    for name, _, _ in STACKS:
        poff = LIN / ("%s-binned-off.tif" % name)
        pon = LIN / ("%s-binned-on.tif" % name)
        off, W, H = cs.load_tiff_u16(str(poff))
        on, W2, H2 = cs.load_tiff_u16(str(pon))
        assert (W, H) == (W2, H2)
        cx, cy = W / 2.0, H / 2.0
        ws = c4g.grid(off, W, H)
        print("\n" + "=" * 96)
        print("%s  BINNED  %dx%d  %d windows" % (name, W, H, len(ws)))
        print("=" * 96)
        print("%-6s %-5s %12s %10s %10s %7s %8s" % ("est", "arm", "eps ppm", "tx px", "ty px", "n", "rms px"))
        cell = {}
        for which in ("lk", "orch"):
            for arm, img in (("off", off), ("on", on)):
                m = measure(img, ws, which, cx=cx, cy=cy)
                eps, tx, ty, n, rms = fit_eps(m, cx, cy)
                cell["%s_%s" % (which, arm)] = dict(eps=eps, tx=tx, ty=ty, n=n, rms=rms)
                print("%-6s %-5s %12.1f %10.4f %10.4f %7d %8.4f" % (which, arm, eps * 1e6, tx, ty, n, rms))
        print("-" * 96)
        print("%-6s %13s %13s %9s %11s" % ("est", "needed ppm", "applied ppm", "gain", "appl/eps_r"))
        for which in ("lk", "orch"):
            eo = cell["%s_off" % which]["eps"]; en = cell["%s_on" % which]["eps"]
            needed, applied = -eo, en - eo
            cell["gain_%s" % which] = applied / needed if needed else float("nan")
            cell["needed_%s" % which] = needed
            cell["applied_%s" % which] = applied
            cell["transfer_%s" % which] = applied / (-EPS_R)
            print("%-6s %13.1f %13.1f %9.4f %11.4f"
                  % (which, needed * 1e6, applied * 1e6, cell["gain_%s" % which], cell["transfer_%s" % which]))
        res[name] = cell
        del off, on

    print("\n" + "=" * 96)
    print("B10 -- CHAIN TRANSFER.  applied/eps_r must be 1.00 in an uncontaminated space.")
    print("=" * 96)
    for k, v in res.items():
        print("  %-18s transfer = %.4f   gain = %.4f   needed = %.1f ppm  (corrected %.1f)"
              % (k, v["transfer_lk"], v["gain_lk"], v["needed_lk"] * 1e6,
                 v["needed_lk"] * 1e6 / v["transfer_lk"]))
    with open(OUT / "c9_binned.json", "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote c9_binned.json")

if __name__ == "__main__":
    main()