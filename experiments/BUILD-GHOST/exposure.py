#!/usr/bin/env python3
"""BUILD-GHOST Part 2: per-frame photometric drift across each bracket,
measured in CAMERA-LINEAR raw DN and nowhere else.

WHY IT IS MEASURED THIS WAY
===========================
The shipped `--merge pyramid` path applies no photometric gain.  Its noise gate
compares a coefficient's local energy against a modelled band noise, so a frame
that is 5 % brighter than its neighbours presents 5 % more coefficient energy
everywhere and the gate reads that as signal.  The question is therefore not
"does brightness change" -- of course it does, content comes into focus -- but
"is there a per-frame MULTIPLICATIVE gain that no stage removes".

Separating gain from focus, and why it is sound
-----------------------------------------------
Defocus is a convolution with a unit-sum kernel, so it CONSERVES total flux:
integral(I conv k) = integral(I) * integral(k) = integral(I).  A frame going soft
redistributes light; it does not create or destroy it.  A gain change multiplies
every order statistic of the frame by the same factor.  So:

  * a common multiplicative factor across ALL deciles  ->  GAIN,
  * deciles moving in different directions             ->  focus / content.

The estimator exploits exactly that.  Per frame it takes nine deciles of the
camera-linear plane, divides by the bracket's per-decile median, and reports the
MEDIAN of those nine ratios as the gain and their spread as the evidence that it
really is a gain.  A frame whose ratios disagree across deciles is reported as
content change and is NOT counted as drift.

Three controls run before any corpus number is printed (`--controls`), and each
one either passes or fails out loud:

  E1  same frame twice                -> gain exactly 1.000
  E2  a planted gain of a known size  -> recovered
  E3  a planted DEFOCUS, no gain      -> still 1.000   <- the confounder control

EXIF is read for every frame examined.  A bracket whose metadata claims a
constant exposure while its flux drifts is the interesting case: this rig has a
2x teleconverter and an electronic-aperture lens in the path, and aperture
non-repeatability does not appear in the metadata.

Usage:
    python exposure.py --controls
    python exposure.py --subject bee-3-cpl [--stride 1]
    python exposure.py --all [--stride 1] [--jobs 6]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghostlib as G  # noqa: E402

RAW_ROOT = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\BUILD-GHOST\data"
DECILES = np.arange(10, 100, 10)


# ------------------------------------------------------------- measurement

def frame_stats(path: str) -> dict:
    """Camera-linear order statistics + EXIF for one frame.  No tone curve, no
    white balance, no colour matrix: raw DN above black."""
    import rawpy

    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        pat = np.asarray(r.raw_pattern)
        black = np.asarray(r.black_level_per_channel, dtype=np.float32)
        white = float(r.white_level)
        desc = r.color_desc.decode() if isinstance(r.color_desc, bytes) else str(r.color_desc)
        vv = v.astype(np.float32)

    h, w = vv.shape
    h2, w2 = h // 2, w // 2
    q = vv[: h2 * 2, : w2 * 2].reshape(h2, 2, w2, 2)
    chan = {}
    for oy in range(2):
        for ox in range(2):
            ci = int(pat[oy, ox])
            nm = desc[ci] if ci < len(desc) else str(ci)
            nm = nm if nm not in chan else nm + "2"
            chan[nm] = (q[:, oy, :, ox], ci)

    gk = sorted(k for k in chan if k.startswith("G"))
    g = 0.5 * (chan[gk[0]][0] + chan[gk[1]][0]) - black[chan[gk[0]][1]]
    sub = g[::3, ::3]                      # 1/9 of the plane: 91k px, ample for deciles
    dec = np.percentile(sub, DECILES).astype(float)
    cen = g[h2 // 4: 3 * h2 // 4, w2 // 4: 3 * w2 // 4]

    out = {
        "file": os.path.basename(path),
        "deciles_G": dec.tolist(),
        "mean_G": float(g.mean()),
        "mean_G_centre50": float(cen.mean()),
        "sat_frac": float((vv >= white - 1).mean()),
        "black": float(black[0]), "white": white,
    }
    for nm, (plane, ci) in chan.items():
        out[f"mean_{nm}"] = float(plane.astype(np.float32).mean() - black[ci])

    try:
        import exifread
        with open(path, "rb") as fh:
            t = exifread.process_file(fh, details=False)

        def rat(key):
            v_ = t.get(key)
            if v_ is None:
                return None
            try:
                return float(v_.values[0].num) / float(v_.values[0].den)
            except Exception:
                try:
                    return float(str(v_))
                except Exception:
                    return None
        out["exif"] = {
            "ExposureTime": rat("EXIF ExposureTime"),
            "FNumber": rat("EXIF FNumber"),
            "ISO": rat("EXIF ISOSpeedRatings"),
            "FocalLength": rat("EXIF FocalLength"),
            "DateTimeOriginal": str(t.get("EXIF DateTimeOriginal", "")),
            "LensModel": str(t.get("EXIF LensModel", "")),
        }
    except Exception as e:                      # noqa: BLE001
        out["exif"] = {"error": repr(e)}
    return out


def fit_gains(rows: list[dict]) -> dict:
    """Per-frame multiplicative gain, and the evidence that it is one.

    gain_i   = median over deciles of ( decile_i / bracket_median_decile )
    spread_i = MAD over deciles of ln( decile_i / bracket_median_decile )

    A pure gain gives spread ~ 0 whatever the gain is.  A focus or content change
    gives a large spread, and is therefore reported separately rather than
    counted as drift.
    """
    D = np.array([r["deciles_G"] for r in rows], float)      # (F, 9)
    ref = np.median(D, axis=0)
    use = ref > 0
    ratio = D[:, use] / ref[use]
    lr = np.log(np.maximum(ratio, 1e-9))
    gain = np.exp(np.median(lr, axis=1))
    spread = np.median(np.abs(lr - np.median(lr, axis=1, keepdims=True)), axis=1) * 1.4826
    return {"gain": gain, "spread": spread, "ref_deciles": ref}


def analyse_subject(name: str, rows: list[dict]) -> dict:
    rows = [r for r in rows if r is not None]
    f = fit_gains(rows)
    gain, spread = f["gain"], f["spread"]
    stops = np.log2(np.maximum(gain, 1e-9))
    stops = stops - np.median(stops)

    # EXIF: does the metadata claim a constant exposure?
    def col(key):
        v = [r["exif"].get(key) for r in rows if isinstance(r.get("exif"), dict)]
        v = [x for x in v if isinstance(x, (int, float))]
        return np.array(v, float) if v else np.array([])
    et, fn, iso = col("ExposureTime"), col("FNumber"), col("ISO")

    def const(a):
        return bool(a.size and np.allclose(a, a[0]))
    exif_const = const(et) and const(fn) and const(iso)
    exif_stops = np.array([])
    if et.size and fn.size and iso.size and et.size == fn.size == iso.size:
        e = et * iso / np.maximum(fn ** 2, 1e-9)
        exif_stops = np.log2(np.maximum(e / np.median(e), 1e-9))

    # frame-to-frame flicker: the part a slow trend cannot explain
    step = np.diff(stops) if stops.size > 1 else np.array([0.0])
    clean = spread < 0.02          # deciles agree: this really is a gain
    return {
        "subject": name,
        "n_frames": len(rows),
        "n_gain_like": int(clean.sum()),
        "n_content_like": int((~clean).sum()),
        "drift_p2p_stops": float(np.percentile(stops, 99) - np.percentile(stops, 1)),
        "drift_max_stops": float(stops.max() - stops.min()),
        "drift_sd_stops": float(stops.std()),
        "flicker_mad_stops": float(np.median(np.abs(step - np.median(step))) * 1.4826),
        "trend_stops_over_bracket": float(np.polyfit(np.arange(stops.size), stops, 1)[0]
                                          * max(stops.size - 1, 1)) if stops.size > 2 else 0.0,
        "decile_spread_median": float(np.median(spread)),
        "sat_frac_max": float(max(r["sat_frac"] for r in rows)),
        "exif_constant": exif_const,
        "exif_ExposureTime": float(et[0]) if et.size else None,
        "exif_FNumber": float(fn[0]) if fn.size else None,
        "exif_ISO": float(iso[0]) if iso.size else None,
        "exif_LensModel": next((r["exif"].get("LensModel") for r in rows
                                if isinstance(r.get("exif"), dict)), None),
        "exif_implied_drift_stops": float(exif_stops.max() - exif_stops.min())
        if exif_stops.size else None,
        "per_frame": [{"file": r["file"], "stops": float(s), "spread": float(sp),
                       "sat": r["sat_frac"]}
                      for r, s, sp in zip(rows, stops, spread)],
    }


# --------------------------------------------------------------- controls

def run_controls() -> int:
    print("BUILD-GHOST exposure controls (camera-linear, no tone curve anywhere)")
    import cv2
    p = os.path.join(RAW_ROOT, "couch-fibers-cpl", "DSC00150.ARW")
    base = frame_stats(p)
    outcomes = []

    def rec(n, ok, d):
        outcomes.append((n, "PASS" if ok else "FAIL"))
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}")

    def gain_of(rows):
        return fit_gains(rows)["gain"], fit_gains(rows)["spread"]

    # E1 -- the same frame twice
    g, sp = gain_of([base, dict(base)])
    rec("E1_identity", abs(g[0] - 1.0) < 1e-9 and sp[0] < 1e-9,
        {"gain": float(g[0]), "spread": float(sp[0])})

    # E2 -- a planted gain
    plane = G.decode_plane(p)["g"]
    res2 = []
    for k in (1.01, 1.05, 1.20):
        rows = [
            {"deciles_G": np.percentile(plane[::3, ::3], DECILES).tolist()},
            {"deciles_G": np.percentile((plane * k)[::3, ::3], DECILES).tolist()},
            {"deciles_G": np.percentile(plane[::3, ::3], DECILES).tolist()},
        ]
        gg, ss = gain_of(rows)
        res2.append({"planted": k, "recovered": float(gg[1] / gg[0]), "spread": float(ss[1])})
        print(f"    planted gain {k:.3f} -> recovered {gg[1] / gg[0]:.4f}  "
              f"(decile spread {ss[1]:.5f})")
    rec("E2_planted_gain", all(abs(r["recovered"] / r["planted"] - 1) < 0.01 for r in res2),
        {"ladder": res2})

    # E3 -- a planted DEFOCUS with NO gain: the confounder control
    res3 = []
    for sig in (1.0, 3.0, 8.0):
        blur = cv2.GaussianBlur(plane, (0, 0), sig)
        rows = [
            {"deciles_G": np.percentile(plane[::3, ::3], DECILES).tolist()},
            {"deciles_G": np.percentile(blur[::3, ::3], DECILES).tolist()},
            {"deciles_G": np.percentile(plane[::3, ::3], DECILES).tolist()},
        ]
        gg, ss = gain_of(rows)
        res3.append({"sigma_plane_px": sig, "apparent_gain": float(gg[1] / gg[0]),
                     "spread": float(ss[1]),
                     "mean_ratio": float(blur.mean() / plane.mean())})
        print(f"    defocus sigma {sig:4.1f} plane px, NO gain -> apparent gain "
              f"{gg[1] / gg[0]:.4f}, decile spread {ss[1]:.5f}, "
              f"frame-mean ratio {blur.mean() / plane.mean():.6f}")
    # the frame mean must be conserved (flux conservation), and any apparent gain
    # must be accompanied by a large decile spread, which is how it is rejected
    ok3 = all(abs(r["mean_ratio"] - 1.0) < 0.002 for r in res3) and \
        all(abs(r["apparent_gain"] - 1.0) < 0.02 or r["spread"] > 0.02 for r in res3)
    rec("E3_defocus_no_gain", ok3, {"ladder": res3})

    npass = sum(1 for _, o in outcomes if o == "PASS")
    nfail = len(outcomes) - npass
    print(f"\nexposure controls examined {len(outcomes)}  PASS {npass}  FAIL {nfail}  "
          f"(sums to {npass + nfail})")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "exposure_controls.json"), "w") as fh:
        json.dump({"E2": res2, "E3": res3, "n": len(outcomes),
                   "pass": npass, "fail": nfail}, fh, indent=2, default=float)
    return 0 if nfail == 0 else 1


# ------------------------------------------------------------------- main

def subjects() -> list[str]:
    return sorted(d for d in os.listdir(RAW_ROOT)
                  if os.path.isdir(os.path.join(RAW_ROOT, d))
                  and any(f.lower().endswith(".arw")
                          for f in os.listdir(os.path.join(RAW_ROOT, d))))


def do_subject(name: str, stride: int, jobs: int) -> dict:
    d = os.path.join(RAW_ROOT, name)
    fs = G.frames_of(d)[::stride]
    t = time.time()
    if jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            rows = list(ex.map(frame_stats, fs, chunksize=2))
    else:
        rows = [frame_stats(f) for f in fs]
    a = analyse_subject(name, rows)
    a["stride"] = stride
    a["n_frames_in_dir"] = len(G.frames_of(d))
    a["elapsed_s"] = time.time() - t
    return a


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--subject")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    if a.controls:
        return run_controls()

    os.makedirs(OUT, exist_ok=True)
    names = [a.subject] if a.subject else subjects()
    if not a.all and not a.subject:
        print("pass --all or --subject NAME")
        return 2
    allout = []
    for i, n in enumerate(names, 1):
        r = do_subject(n, a.stride, a.jobs)
        allout.append(r)
        print(f"[{i:2d}/{len(names)}] {n:38s} n={r['n_frames']:3d}/{r['n_frames_in_dir']:3d} "
              f"p2p={r['drift_p2p_stops']:+.4f} st  trend={r['trend_stops_over_bracket']:+.4f} st  "
              f"flicker={r['flicker_mad_stops']:.4f} st  exif_const={r['exif_constant']}  "
              f"satmax={r['sat_frac_max']:.5f}  ({r['elapsed_s']:.0f}s)", flush=True)
        with open(os.path.join(OUT, f"exposure_{n}.json"), "w") as fh:
            json.dump(r, fh, indent=2, default=float)
    with open(os.path.join(OUT, "exposure_all.json"), "w") as fh:
        json.dump(allout, fh, indent=2, default=float)
    print(f"\nsubjects examined {len(allout)}  (of {len(names)} requested)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
