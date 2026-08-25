"""M113-spectral S8 (POST-HOC, raised after S7): is the between-subject spread in
`needed_R` a property of the OPTICS, or an artefact of MERGING A DEEP SUBJECT?

S7 part 1 forced this question. On a single frame restricted to its in-focus
windows, bee-3 reads 623.5 ppm against its merged 529.9, and couch reads 690.5
against its merged 654.9, while the FLAT subject flat-on-ruler-cpl reads 636.5
against its merged 631.7. The merge deficit is -93.6, -35.6 and -4.8 ppm, and
those rank exactly with how three-dimensional the subject is.

If that holds across the corpus it dismantles the spectral attribution, because
the ordering of merged `needed_R` would then be an ordering of SUBJECT DEPTH --
tweezers, leaf, couch and a flat ruler read high; bees, lavendar and a marker tip
read low -- and depth has nothing to do with wavelength.

THE TEST. Measure every stack on its OWN reference frame, un-aligned and
un-merged, restricted to the windows that are actually in focus in that frame.
That removes the merge from the measurement entirely and leaves the optics.

PRE-REGISTERED BAR, stated before the numbers exist:
  Let Sm = range of merged needed_R over the stacks (measured: 144.8 ppm) and
  Ss = range of single-frame in-focus needed_R over the same stacks.
  - Ss <= 60 ppm  -> the optics are scene-INDEPENDENT and the entire spread is a
                     merge artefact. SPECTRAL REFUTED.
  - Ss >= 0.75*Sm -> the spread survives with the merge removed. It is optical
                     and scene-dependent; spectral stays live.
  - in between    -> the merge contributes materially but does not explain it
                     all. Report both components, verdict UNDETERMINED.
This bar is post-hoc with respect to the original pre-registration and is
labelled as such wherever it is reported.
"""
import json, os, shutil, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import stats

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                        # noqa: E402
from c4_globalfit import cs, fit_eps, EPS_R       # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_measure import measure_ch                 # noqa: E402

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
ROOT = Path(r"C:\dev\strehl-out\M113-spectral")
MACRO = Path(r"D:\personal\macro")
CA_LIN = Path(r"C:\dev\strehl-out\M113-ca\lin")
TILE = c4g.TILE
STACKS = ["tweezers-cpl", "leaf-2-cpl", "bee-1-cpl", "couch-fibers-cpl", "lavendar-cpl",
          "dry-erase-marker-head-cpl", "bee-2-cpl", "bee-3-cpl", "flat-on-ruler-cpl"]

def render_ref(stack):
    frames = sorted((MACRO / stack).glob("*.ARW"))
    idx = len(frames) // 2
    tif = ROOT / "arms" / ("%s-ref1frame.tif" % stack)
    if tif.exists():
        return tif, len(frames), idx
    scratch = ROOT / "oneframe" / stack
    scratch.mkdir(parents=True, exist_ok=True)
    dst = scratch / frames[idx].name
    if not dst.exists():
        shutil.copy2(frames[idx], dst)
    env = dict(os.environ); env.pop("STREHL_FIX_CA", None)
    env["STREHL_ALIGN"] = "0"
    cache = ROOT / "cache" / ("ref1-" + stack); cache.mkdir(parents=True, exist_ok=True)
    env["STREHL_CACHE_DIR"] = str(cache)
    p = subprocess.run([str(EXE), "stack", str(scratch), "-o", str(tif)],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        print((p.stdout or "")[-600:] + (p.stderr or "")[-600:]); sys.exit("render failed " + stack)
    return tif, len(frames), idx

def eps_sharp(path, q):
    a, W, H = cs.load_tiff_u16(str(path))
    ws = c4g.grid(a, W, H)
    sh = np.array([float(cs.grad_mag(np.asarray(
        a[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float32)).mean()) for (x0, y0) in ws])
    thr = np.quantile(sh, q)
    sel = [w for w, s in zip(ws, sh) if s >= thr]
    cx, cy = W / 2.0, H / 2.0
    e, tx, ty, n, rms = fit_eps(measure_ch(a, sel, 0, cx, cy), cx, cy)
    del a
    return -e * 1e6, len(sel), rms

def main():
    c4g.STEP = 100
    merged = {k: v["needed_R"] * 1e6 for k, v in json.load(open(ROOT / "s3_analyse.json")).items()}
    a, W, H = cs.load_tiff_u16(str(ROOT / "arms" / "flat-on-ruler-cpl-binned-off.tif"))
    cx, cy = W / 2.0, H / 2.0
    e, _, _, _, _ = fit_eps(measure_ch(a, c4g.grid(a, W, H), 0, cx, cy), cx, cy)
    merged["flat-on-ruler-cpl"] = -e * 1e6
    del a

    print("=" * 100)
    print("S8 (POST-HOC) -- every stack measured on its OWN reference frame, no align, no merge,")
    print("                 restricted to the windows in focus in that frame")
    print("=" * 100)
    print("%-28s %7s %11s %13s %13s %10s %7s"
          % ("stack", "frames", "merged ppm", "1frame all", "1frame sharp", "deficit", "n"))
    rows = []
    for st in STACKS:
        tif, nfr, idx = render_ref(st)
        v_all, n_all, _ = eps_sharp(tif, 0.0)
        v_sh, n_sh, rms = eps_sharp(tif, 0.75)
        m = merged[st]
        rows.append(dict(stack=st, frames=nfr, merged=m, one_all=v_all, one_sharp=v_sh,
                         deficit=m - v_sh, n=n_sh, rms=rms))
        print("%-28s %7d %11.1f %13.1f %13.1f %10.1f %7d"
              % (st, nfr, m, v_all, v_sh, m - v_sh, n_sh))

    ms = np.array([r["merged"] for r in rows]); ss = np.array([r["one_sharp"] for r in rows])
    fr = np.array([r["frames"] for r in rows], dtype=float)
    df = np.array([r["deficit"] for r in rows])
    Sm = ms.max() - ms.min(); Ss = ss.max() - ss.min()
    print("\n" + "-" * 100)
    print("merged spread          Sm = %.1f ppm   (%.1f to %.1f)" % (Sm, ms.min(), ms.max()))
    print("single-frame spread    Ss = %.1f ppm   (%.1f to %.1f)" % (Ss, ss.min(), ss.max()))
    print("Ss / Sm = %.3f" % (Ss / Sm))
    if Ss <= 60:
        v = "SPECTRAL REFUTED -- optics are scene-independent, the spread is a merge artefact"
    elif Ss >= 0.75 * Sm:
        v = "spread SURVIVES removal of the merge -- optical and scene-dependent"
    else:
        v = "PARTIAL -- the merge contributes materially but does not explain it all"
    print("S8 BAR RESULT: %s" % v)

    rho_f, p_f = stats.spearmanr(fr, ms)
    rho_d, p_d = stats.spearmanr(fr, df)
    print("\ndepth proxy = frame count (the owner shot as many frames as the subject's depth needed)")
    print("  merged needed_R vs frames : rho = %+.4f  p = %.4f  (deeper subject -> lower needed?)"
          % (rho_f, p_f))
    print("  merge deficit  vs frames : rho = %+.4f  p = %.4f  (deeper subject -> bigger deficit?)"
          % (rho_d, p_d))
    print("  single-frame   vs frames : rho = %+.4f  p = %.4f  (should be ~0 if depth acts via merge)"
          % stats.spearmanr(fr, ss))

    json.dump(dict(rows=rows, Sm=Sm, Ss=Ss, verdict=v, rho_frames_merged=rho_f, p=p_f,
                   rho_frames_deficit=rho_d), open(ROOT / "s8_depth.json", "w"), indent=2, default=float)
    print("\nwrote s8_depth.json")

if __name__ == "__main__":
    main()