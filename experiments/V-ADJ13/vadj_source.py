r"""V-ADJ13 ARM SOURCE -- the gate's two statistics on the frames each master was
built from, for the 13 subjects the DELIVER-V6 gate left unresolved.

THIS IS THE INSTRUMENT THE GATE NAMES, RE-POINTED AT THE CORPUS BEING SCORED.

`orch_printready.py` prints, beside every REVIEW row, the control that resolves
it: `orch_blotch.py` source arm for blotch, `orch_chromapair.py` for chroma. The
V-REVIEW lane built the registered form of that control (vr_source.py) and it is
imported here rather than re-typed -- registration (vr_reg2.register_best),
window warp (vr_lib.warp_window), context NCC (vr_reg2.context_ncc) and both
statistics (orch_blotch.blotch_ratio, orch_chroma.chroma_blotch) are the same
code that adjudicated the nine subjects now on record.

WHAT IS DIFFERENT HERE, AND WHY IT HAD TO CHANGE

vr_lib is welded to SHIP-V3: its corpus, its pin, and a per-subject `--exposure`
table read off masters rendered with `--auto-exposure`. DELIVER-V6 is a
different corpus rendered by a different binary with a different exposure
policy -- its own manifest states the invocation as

    <exe> stack <dir> -o <subject>.tiff --srgb

with no exposure flag at all and STREHL_CACHE_DIR privately scoped. So the
source frames are rendered with THAT invocation plus STREHL_ONLY_FRAME=k, which
makes demosaic, CA, alignment resample, colour matrix, the sRGB curve AND the
exposure policy common mode by construction rather than by a transcribed table.
The binary is not named in a constant either: it is verified by SHA256 against
the value DELIVER-V6's own manifest records, so a re-pointed corpus cannot be
measured with the wrong renderer.

THE RULE BEING APPLIED is the one frozen in vr_baseline.json's `gate_rule`:
`source_baseline = max over registered source frames`, `elevated_multiple` 1.3.
For blotch and chroma LOW is good, so the max over sources is the WORST frame,
and a master at or below it is not exhibiting a merge defect. That bound is
weak, deliberately: it is the bound the nine acquittals on record were granted
under, and changing it here would make this lane's verdicts incomparable with
theirs. Both the worst-frame ratio AND the median-frame ratio are reported so a
reader can see how weak.

DISK. One source render exists at a time (198 MB) and is deleted as soon as it
is measured; every number it produced is in the JSON and on stdout before the
file is removed.

READ-ONLY on D:\personal\macro and on DELIVER-V6. Writes only under
C:\dev\strehl-out\V-ADJ13.

  python vadj_source.py SUBJECT [n_coarse] [n_refine]
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

import numpy as np

REPO = r"C:\dev\blog\death-of-software\projects\strehl"
ORCH = os.path.join(REPO, "experiments", "ORCH-drift-check")
VREV = os.path.join(REPO, "experiments", "V-REVIEW")
for p in (ORCH, VREV):
    if p not in sys.path:
        sys.path.insert(0, p)

import vr_lib as V                                            # noqa: E402
import vr_reg2 as R                                           # noqa: E402
from orch_chroma import chroma_blotch                         # noqa: E402

EXE = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe")
EXE_SHA = "2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7"
MASTERS = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V6\masters")
MANIFESTS = ("MANIFEST.txt", "MANIFEST-ORCH7.txt")
SRC = pathlib.Path(r"D:\personal\macro")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-ADJ13")
BWIN, CWIN = V.BWIN, V.CWIN
NCC_MIN = 0.75                       # vr_source.py's declared registration floor
ELEVATED_X = 1.3                     # vr_baseline.json gate_rule.elevated_multiple


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest().upper()


def check_binary():
    """The renderer is verified against the corpus's own manifest, not declared."""
    got = sha256(EXE)
    if got != EXE_SHA:
        raise SystemExit("PIN GUARD: %s hashes %s, DELIVER-V6's manifest records %s"
                         % (EXE, got, EXE_SHA))
    return got


def master_sha_of(subj):
    """The out SHA256 DELIVER-V6 recorded for this master, if it recorded one."""
    want = "%s.tiff" % subj
    for mf in MANIFESTS:
        p = MASTERS / mf
        if not p.is_file():
            continue
        cur, txt = None, p.read_text(encoding="utf-8", errors="replace")
        for line in txt.splitlines():
            if line.startswith("subject   :"):
                cur = line.split(":", 1)[1].strip()
            elif line.startswith("out SHA256:") and cur == subj:
                return line.split(":", 1)[1].strip().upper(), mf
    return None, None


def master_cover_of(subj):
    """Fit-to-cover ratio of the MASTER render, from its own log if it kept one."""
    for name in ("%s.render.log" % subj,):
        p = MASTERS / name
        if p.is_file():
            return R.cover_of_log(p.read_text(encoding="utf-8", errors="replace")), str(p)
    return None, None


def render_frame(subj, k, out_tiff):
    """One frame, DELIVER-V6's exact invocation plus STREHL_ONLY_FRAME."""
    env = {kk: v for kk, v in os.environ.items() if not kk.startswith("STREHL_")}
    env["STREHL_ONLY_FRAME"] = str(k)
    env["STREHL_CACHE_DIR"] = str(OUT / "cache")
    cmd = [str(EXE), "stack", str(SRC / subj), "-o", str(out_tiff), "--srgb"]
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=3600)
    log = p.stderr.decode("utf-8", "replace")
    if p.returncode != 0:
        raise RuntimeError("render rc=%d\n%s" % (p.returncode, log[-2000:]))
    return log, cmd


def cleanup(tif):
    for p in (tif, pathlib.Path(str(tif) + ".ok"),
              pathlib.Path(str(tif) + ".provenance.txt")):
        try:
            pathlib.Path(p).unlink()
        except OSError:
            pass


def measure_frame(subj, k, mlum, bw, cw, km):
    t0 = time.time()
    tif = OUT / ("%s--f%04d.tiff" % (subj, k))
    log, _ = render_frame(subj, k, tif)
    ks = R.cover_of_log(log) or 1.0
    srgb = V.read_rgb(str(tif))
    slum = V.lum_of(srgb)
    A, d = R.register_best(mlum, slum, km / ks, bw[0], bw[1], BWIN)
    row = dict(frame=int(k), how=d.get("how"), ecc=d.get("ecc"),
               scale=d.get("scale"), ncc_b=d.get("ncc_context"), cover_src=ks)
    if A is None:
        row["state"] = "UNREGISTERED"
    else:
        row["ncc_c"] = R.context_ncc(mlum, slum, A, cw[0], cw[1], CWIN)
        wb = V.warp_window(srgb, A, bw[0], bw[1], BWIN)
        wc = V.warp_window(srgb, A, cw[0], cw[1], CWIN)
        if wb is None or wc is None:
            row["state"] = "WINDOW-OUTSIDE-SOURCE"
        else:
            r, bd, nd, md = V.blotch_ratio(V.lum_of(wb))
            cb = chroma_blotch(wc, at=(0, 0))
            row.update(state="OK", blotch=float(r), band=float(bd), noise=float(nd),
                       mean=float(md), relhf=float(nd / max(md, 1e-9)),
                       chroma=float(cb[0]), chr_std=float(cb[3]))
            if row["ncc_b"] is None or not np.isfinite(row["ncc_b"]) \
                    or row["ncc_b"] < NCC_MIN:
                row["state"] = "POOR-REG"
    del srgb, slum
    cleanup(tif)
    row["secs"] = round(time.time() - t0, 1)
    return row


def f(v, spec="%9.5f"):
    try:
        return spec % v
    except (TypeError, ValueError):
        return "%*s" % (int(spec[1:spec.index(".")]), "-")


def main():
    subj = sys.argv[1]
    ncoarse = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    nrefine = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cache").mkdir(exist_ok=True)
    exe_sha = check_binary()

    with open(OUT / "vadj_master.json", encoding="utf-8") as fh:
        ms = json.load(fh)[subj]
    bw = tuple(ms["blotch_window_yx"])
    cw = tuple(ms["chroma_window_yx"])
    mpath = MASTERS / ("%s.tiff" % subj)
    msha, mman = master_sha_of(subj)
    got = sha256(mpath)
    frames = sorted(str(p) for p in (SRC / subj).iterdir()
                    if p.suffix.lower() == ".arw")
    n = len(frames)
    km, klog = master_cover_of(subj)
    km_src = klog
    mlum = V.lum_of(V.read_rgb(str(mpath)))
    if km is None:
        # The 26 masters rendered before the ORCH7 batch kept no banner, so the
        # master's own cover ratio is not on record. It is MEASURED instead:
        # ORB needs no scale prior, so frame n//2 supplies km = scale * k_source.
        # Stated, not assumed -- an unmeasured prior would silently bias every
        # model-ECC fallback that follows it.
        k0 = n // 2
        tif = OUT / ("%s--cover.tiff" % subj)
        log, _ = render_frame(subj, k0, tif)
        ks0 = R.cover_of_log(log) or 1.0
        slum = V.lum_of(V.read_rgb(str(tif)))
        A0, d0 = V.register(mlum, slum)
        cleanup(tif)
        del slum
        if A0 is None or d0.get("inliers", 0) < 40:
            km, km_src = ks0, "ORB failed on frame %d; assumed master cover = source cover" % k0
        else:
            km = float(d0["scale"]) * ks0
            km_src = ("MEASURED: ORB frame %d, scale %.5f x source cover %.4f, %d inliers"
                      % (k0, d0["scale"], ks0, d0["inliers"]))

    print("SUBJECT %s" % subj)
    print("  master     %s" % mpath)
    print("  master sha %s  %s" % (got, "MATCHES %s" % mman if msha == got else
                                   ("*** MANIFEST SAYS %s ***" % msha) if msha else
                                   "(no manifest record)"))
    print("  renderer   %s  sha %s (verified against DELIVER-V6 manifest)" % (EXE, exe_sha))
    print("  frames     %d ARW in %s" % (n, SRC / subj))
    print("  master cover %.4f  <- %s" % (km, km_src))
    print("  gate windows: blotch %r  chroma %r" % (bw, cw))
    print("  master: blotch %.5f  chroma %.6f  band %.1f DN  mean %.1f DN  relHF %.5f"
          % (ms["blotch"], ms["chroma"], ms["blotch_band_dn"], ms["blotch_mean_dn"],
             ms["blotch_noise_dn"] / max(ms["blotch_mean_dn"], 1e-9)))
    print("%6s %9s %9s %9s %8s %7s %7s %7s %10s %5s %s"
          % ("frame", "blotch", "chroma", "meanDN", "relHF", "ncc_b", "ncc_c",
             "scale", "how", "secs", "state"))
    rows, done = [], set()

    def run(idx):
        for k in idx:
            k = int(k)
            if k in done or k < 0 or k >= n:
                continue
            done.add(k)
            r = measure_frame(subj, k, mlum, bw, cw, km)
            rows.append(r)
            print("%6d %s %s %s %s %s %s %s %10s %5.0f %s"
                  % (k, f(r.get("blotch")), f(r.get("chroma"), "%9.6f"),
                     f(r.get("mean"), "%9.1f"), f(r.get("relhf"), "%8.5f"),
                     f(r.get("ncc_b"), "%7.3f"), f(r.get("ncc_c"), "%7.3f"),
                     f(r.get("scale"), "%7.4f"), r.get("how"), r["secs"], r["state"]))
            sys.stdout.flush()

    run(sorted(set(np.linspace(0, n - 1, ncoarse).astype(int).tolist())))
    step = max(1, (n - 1) // max(ncoarse - 1, 1))
    for _ in range(2):
        ok = [r for r in rows if r["state"] == "OK"]
        if not ok or not nrefine:
            break
        extra = []
        for key in ("blotch", "chroma"):
            best = max(ok, key=lambda r: r[key])["frame"]
            extra += [best - step // 2, best + step // 2, best - step // 4,
                      best + step // 4, best - 1, best + 1]
        run(sorted(set(int(e) for e in extra))[:2 * nrefine])
        step = max(1, step // 2)

    ok = [r for r in rows if r["state"] == "OK"]
    mrelhf = ms["blotch_noise_dn"] / max(ms["blotch_mean_dn"], 1e-9)
    out = dict(subject=subj, arm="DELIVER-V6", exe=str(EXE), exe_sha256=exe_sha,
               master_path=str(mpath), master_sha256=got, master_manifest=mman,
               n_frames=n, master=ms, master_relhf=mrelhf, master_cover=km,
               master_cover_source=km_src, blotch_window_yx=list(bw),
               chroma_window_yx=list(cw), ncc_min=NCC_MIN, rows=rows,
               sampled=sorted(done))
    if ok:
        for key in ("blotch", "chroma"):
            v = [r[key] for r in ok]
            best = max(ok, key=lambda r: r[key])
            out["src_%s_max" % key] = float(max(v))
            out["src_%s_min" % key] = float(min(v))
            out["src_%s_med" % key] = float(np.median(v))
            out["src_%s_argmax" % key] = int(best["frame"])
            out["src_%s_relhf" % key] = best.get("relhf")
        out["src_band_max"] = float(max(r["band"] for r in ok))
        out["src_mean_med"] = float(np.median([r["mean"] for r in ok]))
        out["n_ok"] = len(ok)
        mb, mc = ms["blotch"], ms["chroma"]
        out["ratio"] = {
            "blotch": mb / out["src_blotch_max"],
            "chroma": mc / out["src_chroma_max"],
            "blotch_band_dn": ms["blotch_band_dn"] / out["src_band_max"],
            "blotch_vs_median_source": mb / max(out["src_blotch_med"], 1e-12),
            "chroma_vs_median_source": mc / max(out["src_chroma_med"], 1e-12),
        }
        print("\nBLOTCH  master %9.5f  source max %9.5f (frame %d, relHF %.5f vs master "
              "%.5f)  med %9.5f  RATIO %.3f  (vs median %.3f)"
              % (mb, out["src_blotch_max"], out["src_blotch_argmax"],
                 out["src_blotch_relhf"] or float("nan"), mrelhf,
                 out["src_blotch_med"], out["ratio"]["blotch"],
                 out["ratio"]["blotch_vs_median_source"]))
        print("BAND DN master %9.1f  source max %9.1f  RATIO %.3f  "
              "(raw DN, only comparable because the arms share a pipeline)"
              % (ms["blotch_band_dn"], out["src_band_max"],
                 out["ratio"]["blotch_band_dn"]))
        print("CHROMA  master %9.6f  source max %9.6f (frame %d)  med %9.6f  RATIO %.3f"
              "  (vs median %.3f)"
              % (mc, out["src_chroma_max"], out["src_chroma_argmax"],
                 out["src_chroma_med"], out["ratio"]["chroma"],
                 out["ratio"]["chroma_vs_median_source"]))
        add = mc ** 2 - out["src_chroma_max"] ** 2
        print("CHROMA  component the merge could have added: %s"
              % (("<= %.6f" % np.sqrt(add)) if add > 0 else "NONE (master <= source max)"))
        print("registered OK %d of %d rendered (floor ncc %.2f)"
              % (len(ok), len(rows), NCC_MIN))
        for key, rev in (("blotch", 0.02), ("chroma", 0.015)):
            val = mb if key == "blotch" else mc
            if val <= rev:
                print("VERDICT %-6s not at review (%.5f <= %.4f); no adjudication needed"
                      % (key.upper(), val, rev))
                continue
            rat = out["ratio"][key]
            if rat <= 1.0:
                print("VERDICT %-6s ACQUIT -- master reads BELOW the worst source frame "
                      "(%.3fx)" % (key.upper(), rat))
            elif rat <= ELEVATED_X:
                print("VERDICT %-6s ACQUIT -- %.3fx the worst source frame, under the "
                      "commissioned %.1fx elevation" % (key.upper(), rat, ELEVATED_X))
            else:
                print("VERDICT %-6s REAL DEFECT -- %.3fx the worst source frame, above "
                      "the %.1fx elevation: structure no input contains"
                      % (key.upper(), rat, ELEVATED_X))
    else:
        print("\nNO FRAME REGISTERED -- the control cannot speak. UNRESOLVED.")
    with open(OUT / ("source_%s.json" % subj), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("wrote %s" % (OUT / ("source_%s.json" % subj)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
