#!/usr/bin/env python3
"""Stage 2: does the MERGE hold the detail the SOURCE FRAMES hold?

The two arms, and what makes them comparable
--------------------------------------------
arm A  the merge          strehl stack <dir> --merge pyramid --pyramid-gate 4.5
                          --linear-srgb --demosaic
arm B  one source frame   STREHL_ONLY_FRAME=<k> and otherwise the SAME command,
                          the SAME pinned binary, the SAME backend.

Everything except the merge itself is therefore common-mode: the same RAW
decode, the same Malvar-He-Cutler demosaic, the same lateral-CA correction, the
same camera->linear-sRGB matrix, the same black and white points, and NO
transfer curve on either side.  Nothing here is measured on an --srgb master.

The one thing that is NOT common-mode is the alignment gather.  A merge crops
the field of view to its own k so every frame covers every pixel and upsamples
back; k runs 0.9046..0.9916 across this corpus.  A one-frame render re-solves
alignment on a stack of one, so its k is the 3 px floor, 0.9974.  The two arms
therefore sit on grids that differ in magnification by up to 7.4%, which is
~38 px of differential stretch across a 512 px window -- far too much for a
translation match to absorb.

So arm B is resampled onto arm A's grid with the same Catmull-Rom kernel the
pipeline uses.  That leaves arm B carrying TWO gathers against arm A's one, and
that is a real handicap in arm B's disfavour.  It is not assumed away and it is
not taken from a quoted constant.  It is MEASURED, per subject and per site, by
putting arm A through the identical extra gather on the identical content and
seeing what it costs:

    cost = high(gather(armA)) / high(armA)          <- self-calibration
    armB_corrected = high(gather(armB)) / cost

Both arms then stand at one effective gather.  Every number below is reported
BOTH ways, raw and corrected, together with `cost`, so a reader can disbelieve
the correction and still see the answer.

Levels are reported in absolute DN alongside every ratio, because an additive
bias is invisible in a ratio and invisible in an error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402
import focuscurve as FC  # noqa: E402

EXE = r"C:\dev\strehl-out\ORCH-SHIP\src\target\release\strehl.exe"
FRAMEDIR = os.path.join(tri.OUT, "frames")
K_ONLY = 0.9974  # the 3 px coverage floor a one-frame render always lands on
N_WIN = 512


def render_frame(subject: str, k: int) -> tuple[str, dict]:
    """Render one source frame through the WHOLE pipeline, linear, full res."""
    os.makedirs(FRAMEDIR, exist_ok=True)
    out = os.path.join(FRAMEDIR, f"{subject}.f{k}.tiff")
    log = out[:-5] + ".log"
    if not os.path.exists(out):
        env = dict(os.environ, STREHL_ONLY_FRAME=str(k))
        env.pop("STREHL_FIX_CA", None)
        with open(log, "w", encoding="utf-8") as fh:
            rc = subprocess.call(
                [EXE, "stack", os.path.join(tri.RAW, subject),
                 "--merge", "pyramid", "--pyramid-gate", "4.5",
                 "--linear-srgb", "--demosaic", "-o", out],
                stdout=fh, stderr=subprocess.STDOUT, env=env)
        if rc != 0:
            raise RuntimeError(f"{subject} frame {k}: strehl rc={rc}, see {log}")
    meta = tri.read_log(log)
    assert meta.get("n_frames") == 1, (
        f"{subject} f{k}: log says n_frames={meta.get('n_frames')}, expected 1 "
        "-- STREHL_ONLY_FRAME did not take and this is NOT a single-frame arm")
    return out, meta


def _rescaled_window(img: np.ndarray, k: float, cy: int, cx: int,
                     n: int, search: int) -> tuple[np.ndarray, int, int]:
    """The k-rescaled neighbourhood of (cy,cx), and its origin in frame coords."""
    h, w = img.shape
    y0 = int(np.clip(cy - search, 0, h - n - 2 * search))
    x0 = int(np.clip(cx - search, 0, w - n - 2 * search))
    hh = min(n + 2 * search, h - y0)
    ww = min(n + 2 * search, w - x0)
    return tri.catmull_rom_scale(img, k, (y0, x0, hh, ww)), y0, x0


def measure_site(r: dict, ka: float, tA: np.ndarray, nA: float,
                 tB: np.ndarray, nB: float) -> dict:
    """Attach NOISE-SUBTRACTED band metrics to a site, using per-arm templates.

    Called only after the FLAT site has supplied a noise template for each arm,
    because the merge and a single frame differ in noise by roughly 2x and that
    difference alone manufactures a 2x false sharpness advantage for the frame
    (commissioning C8c).  The gathered arm-A tile is noise-subtracted with arm
    A's own template so the gather cost is a SIGNAL cost, not a noise cost.
    """
    tile_a, tile_b, tile_a2 = r["_tiles"]
    s = r["scale"]

    # ---- PRIMARY VERDICT: noise-robust edge sharpness, in DN/px -------------
    ea, eb = tri.edge_slope(tile_a), tri.edge_slope(tile_b)
    ecost = float(np.mean([
        tri.edge_slope(tri.catmull_rom_shift(tile_a, ph, ph,
                                             (8, 8, tile_a.shape[0] - 16,
                                              tile_a.shape[1] - 16)))
        / tri.edge_slope(tile_a[8:-8, 8:-8]) for ph in tri.GATHER_PHASES]))
    if abs(1.0 - s) < 0.005:
        ecost = 1.0   # see the band-metric note above: no meaningful resample
    eb_corr = eb / ecost if ecost else float("nan")
    eratio = ea / eb_corr if eb_corr > 0 else float("nan")
    r["edge"] = {
        "merge_dnpx": round(ea, 3),
        "frame_dnpx": round(eb, 3),
        "frame_corr_dnpx": round(eb_corr, 3),
        "gather_cost": round(ecost, 4),
        "ratio": round(eratio, 4),
        "deficit_dnpx": round(eb_corr - ea, 3),
        "blur_equiv_px": round(tri.blur_equiv(tile_a, eratio), 3),
        "noise_merge_dn": round(tri.pixel_noise(tile_a), 3),
        "noise_frame_dn": round(tri.pixel_noise(tile_b), 3),
    }
    nmg = r["edge"]["noise_merge_dn"]
    r["edge"]["noise_ratio"] = round(r["edge"]["noise_frame_dn"] / nmg, 3) if nmg else None

    A = tri.band_amp_sig(tile_a, ka, tA, nA)
    B = tri.band_amp_sig(tile_b, ka, tB, nB)
    A2 = tri.band_amp_sig(tile_a2, ka * s, tA, nA)
    for band in tri.BANDS:
        cs = r[band]["cost_shift"]
        d = r[band]
        bcorr = B[band] / cs if cs else float("nan")
        d.update({
            "sig_merge_dn": round(A[band], 4),
            "sig_frame_dn": round(B[band], 4),
            "sig_frame_corr_dn": round(bcorr, 4),
            "noise_merge_dn": round(A[band + "_noise"], 4),
            "noise_frame_dn": round(B[band + "_noise"], 4),
            "tot_merge_dn": round(A[band + "_tot"], 4),
            "tot_frame_dn": round(B[band + "_tot"], 4),
            "cost_sig": round(A2[band] / A[band], 4) if A[band] > 0 else None,
            "ratio_sig": round(A[band] / bcorr, 4) if bcorr > 0 else None,
            "sig_deficit_dn": round(bcorr - A[band], 4),
        })
        # Detail below the noise floor is not detail.  A site where BOTH arms
        # are noise carries no evidence either way and must not vote.
        d["has_signal"] = bool(A[band] > 0.20 * A[band + "_tot"]
                               or B[band] > 0.20 * B[band + "_tot"])
    r["noise_ratio_high"] = round(
        B["high_noise"] / A["high_noise"], 4) if A["high_noise"] > 0 else None
    return r


def compare_site(ya: np.ndarray, yb: np.ndarray, ka: float, kb: float,
                 cy: int, cx: int, n: int = N_WIN, search: int = 96) -> dict:
    """One site, both arms, on arm A's grid, with the gather self-calibrated."""
    s = ka / kb  # arm B's grid -> arm A's grid
    h, w = ya.shape
    cy = int(np.clip(cy, n, h - n - 1))
    cx = int(np.clip(cx, n, w - n - 1))
    tile_a = np.ascontiguousarray(ya[cy:cy + n, cx:cx + n])

    wb, by0, bx0 = _rescaled_window(yb, s, cy, cx, n, search)
    my, mx, ncc = tri.find_match(tile_a, wb, cy - by0, cx - bx0, n, search=search)
    tile_b = np.ascontiguousarray(wb[my:my + n, mx:mx + n])
    my, mx = my + by0, mx + bx0

    # Self-calibration: what does ONE extra Catmull-Rom gather cost, on THIS
    # content, at THIS site?  Measured with pure sub-pixel translations averaged
    # over phase (see tri.GATHER_PHASES), so the content scale is untouched and
    # the before/after are the same pixels -- no registration is involved and
    # so none can fail.
    A = tri.band_amp(tile_a, ka)
    costs: dict[str, list[float]] = {b: [] for b in tri.BANDS}
    m = 8
    for ph in tri.GATHER_PHASES:
        sh = tri.catmull_rom_shift(ya, ph, ph, (cy - m, cx - m, n + 2 * m, n + 2 * m))
        t = np.ascontiguousarray(sh[m:m + n, m:m + n])
        S = tri.band_amp(t, ka)
        for b in tri.BANDS:
            costs[b].append(S[b] / A[b] if A[b] > 0 else float("nan"))
    cost_shift = {b: float(np.mean(costs[b])) for b in tri.BANDS}

    # Second, independent estimator of the SAME quantity, using the actual s
    # rather than a phase stand-in: put arm A through the identical rescale and
    # read its bands at k*s, i.e. at matched SENSOR frequency.  A PSD needs no
    # registration, but it DOES need the same content under the window -- the
    # rescale moves a feature at radius r out to r/s, which is 75 px at this
    # corpus's radii.  Sampling the same COORDINATES would compare different
    # CONTENT, the exact error C4 caught once already, so the window is placed
    # at the analytic destination of (cy,cx) instead.
    ch, cw = (h - 1) / 2.0, (w - 1) / 2.0
    dy_ = int(round((cy - ch) / s + ch))
    dx_ = int(round((cx - cw) / s + cw))
    dy_ = int(np.clip(dy_, 0, h - n - 1))
    dx_ = int(np.clip(dx_, 0, w - n - 1))
    wa2, ay0, ax0 = _rescaled_window(ya, s, dy_, dx_, n, 0)
    tile_a2 = np.ascontiguousarray(wa2[dy_ - ay0:dy_ - ay0 + n, dx_ - ax0:dx_ - ax0 + n])
    A2s = tri.band_amp(tile_a2, ka * s)
    cost_scale = {b: (A2s[b] / A[b] if A[b] > 0 else float("nan")) for b in tri.BANDS}

    A2 = {b: A[b] * cost_scale[b] for b in tri.BANDS}
    ncc_a = 1.0  # no registration step exists in either self-cal path

    B = tri.band_amp(tile_b, ka)

    out = {"x": cx, "y": cy, "ncc": round(ncc, 4), "ncc_selfcal": round(ncc_a, 4),
           "dx": int(mx - cx), "dy": int(my - cy), "scale": round(s, 6)}
    out["_tiles"] = (tile_a, tile_b, tile_a2)
    for band in tri.BANDS:
        # PRIMARY = the phase-averaged shift estimator.  It cannot mis-register
        # (there is no registration) and it is stable when the site is nearly
        # featureless, where the exact-s estimator's ratio is dominated by noise
        # and can return an impossible >1.  The exact-s estimator is retained as
        # an independent CROSS-CHECK: on well-signalled sites the two agree to
        # ~1%, which is the evidence that the correction is physical and not an
        # artefact of either method.
        # PRIMARY = the phase-averaged shift estimator, EXCEPT where almost no
        # resampling actually happens.  The stand-in assumes a rescale that
        # sweeps sub-pixel phase uniformly; when s is within 0.5% of 1 there is
        # no such sweep and no meaningful gather, so charging the full
        # phase-averaged loss would inflate the source arm by ~20% and bias
        # against the merge.  highly-angled-ruler-mm-cpl is the case: the
        # aligner REFUSES it as a tilted subject and combines frames
        # unregistered, so k is exactly 1 and s = 1.0026.
        if abs(1.0 - s) < 0.005:
            cost = min(1.0, cost_scale[band]) if np.isfinite(cost_scale[band]) else 1.0
            cost_rule = "no meaningful resample (|1-s|<0.005); exact-s used"
        else:
            cost = cost_shift[band]
            cost_rule = "phase-averaged shift"
        bcorr = B[band] / cost if cost and np.isfinite(cost) else float("nan")
        out[band] = {
            "merge_dn": round(A[band], 4),
            "frame_dn": round(B[band], 4),
            "frame_corr_dn": round(bcorr, 4),
            "gather_cost": round(cost, 4),
            "cost_shift": round(cost_shift[band], 4),
            "cost_scale": round(cost_scale[band], 4),
            "cost_spread": round(abs(cost_shift[band] - cost_scale[band]), 4),
            "cost_rule": cost_rule,
            "ratio_raw": round(A[band] / B[band], 4) if B[band] > 0 else None,
            "ratio_corr": round(A[band] / bcorr, 4) if bcorr > 0 else None,
            "deficit_dn": round(bcorr - A[band], 4),
        }
    out["level"] = {
        "merge_mean_dn": round(A["mean"], 2),
        "frame_mean_dn": round(B["mean"], 2),
        "delta_dn": round(B["mean"] - A["mean"], 2),
        "merge_sd_dn": round(A["sd"], 2),
        "frame_sd_dn": round(B["sd"], 2),
    }
    return out


def refine_best_frame(subject: str, u: float, v: float, coarse: int,
                      n_frames: int, span: int, sampled: list[int]) -> dict:
    """Find the frame that is TRULY sharpest at this exact site.

    Stage 1 samples at most 40 frames of a bracket that can hold 299, and it
    measures over a 768 sensor-px window.  The compare window is ~477 sensor px
    and sits at one place.  Both differences matter: a 512 px window that spans
    two depths has no single best frame, and a coarse ladder can step straight
    over a focus peak.

    Getting this wrong is DANGEROUS IN THE FLATTERING DIRECTION -- if the
    "best" frame is not actually the best, the merge is compared against
    something blurrier than the capture really offers and a merge-limited
    subject is certified GOOD.  So the coarse pick is refined densely, in raw
    green-plane space, over a window matched to the compare window, and every
    frame in the neighbourhood is measured rather than interpolated.
    """
    d = os.path.join(tri.RAW, subject)
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))
    lo = max(0, coarse - span)
    hi = min(len(files) - 1, coarse + span)
    cand = list(range(lo, hi + 1))
    # Cap the work: if the neighbourhood is huge, walk it at a stride that
    # still cannot step over a peak the coarse ladder already localised.
    if len(cand) > 25:
        cand = sorted(set(np.linspace(lo, hi, 25).round().astype(int).tolist()))

    vals: dict[int, float] = {}
    for k in cand:
        g = FC.green_plane(os.path.join(d, files[k]))
        h, w = g.shape
        half = 119  # ~477 sensor px, matched to the 512 px compare window
        cy = int(np.clip(v * h, half, h - half))
        cx = int(np.clip(u * w, half, w - half))
        t = g[cy - half:cy + half, cx - half:cx + half]
        lap = (4 * t[1:-1, 1:-1] - t[:-2, 1:-1] - t[2:, 1:-1]
               - t[1:-1, :-2] - t[1:-1, 2:])
        vals[k] = float(np.sqrt((lap ** 2).mean()))
    best = max(vals, key=vals.get)
    return {"best": int(best), "coarse": int(coarse),
            "moved_by": int(best - coarse),
            "hf_best": round(vals[best], 3),
            "hf_coarse": round(vals.get(coarse, float("nan")), 3),
            "scanned": [int(k) for k in cand]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--keep", action="store_true",
                    help="keep the 188 MB single-frame renders")
    ap.add_argument("--block", action="append", default=[], metavar="LABEL:R,C",
                    help="force an extra comparison site at focus-grid block "
                         "(R,C). Repeatable. Use to interrogate a named region "
                         "rather than a percentile-selected one -- the "
                         "percentile sites answer 'where is this image best and "
                         "worst', which is not the same question as 'what is "
                         "happening in the corner the owner is pointing at'.")
    ap.add_argument("--tag", default="",
                    help="suffix for the output JSON, so a regional run does "
                         "not overwrite the corpus sweep")
    args = ap.parse_args()
    sub = args.subject

    mp = os.path.join(tri.LIN, sub + ".tiff")
    meta_a = tri.read_log(os.path.join(tri.LIN, sub + ".log"),
                          require=("coverage_k", "n_frames", "resampler"))
    ka = meta_a["coverage_k"]
    ya = tri.luma(tri.load16(mp))
    h, w = ya.shape

    with open(os.path.join(tri.OUT, "focus", sub + ".json"), encoding="utf-8") as fh:
        foc = json.load(fh)

    # --- site selection -----------------------------------------------------
    # Merge-side detail per block, and source-side detail per block, are in
    # DIFFERENT spaces and are never compared as numbers.  They are compared as
    # RANKS, which are invariant to any monotone per-arm transformation --
    # including the gather and the tone curve.  Ranks pick the site; stage 2
    # then measures the magnitude there in DN.
    nb_r, nb_c = foc["grid"]
    mrg = np.zeros(len(foc["blocks"]), np.float64)
    src = np.zeros(len(foc["blocks"]), np.float64)
    pos = []
    for i, b in enumerate(foc["blocks"]):
        cx = int(b["u"] * w) - N_WIN // 2
        cy = int(b["v"] * h) - N_WIN // 2
        cx = int(np.clip(cx, N_WIN, w - N_WIN - 1))
        cy = int(np.clip(cy, N_WIN, h - N_WIN - 1))
        pos.append((cy, cx, b))
        mrg[i] = tri.band_amp(
            np.ascontiguousarray(ya[cy:cy + N_WIN, cx:cx + N_WIN]), ka)["high"]
        src[i] = b["hf_max_dn"]

    rm = np.argsort(np.argsort(mrg))
    rs = np.argsort(np.argsort(src))
    sites = {
        "FLAT": int(np.argmin(src)),            # least detail anywhere: NOISE REF
        "DETAIL": int(np.argmax(mrg)),          # merge at its best
        "SOURCE-BEST": int(np.argmax(src)),     # where the capture put the most
        "DEFICIT": int(np.argmax(rs - rm)),     # source ranks high, merge low
    }

    # Forced regional sites.  Anchored on the (r,c) actually present in the
    # focus grid and hard-errored if absent, so a typo cannot silently fall
    # back to a percentile site and be reported as a regional answer.
    for spec in args.block:
        label, _, rc = spec.partition(":")
        rr, _, cc = rc.partition(",")
        rr, cc = int(rr), int(cc)
        hit = [i for i, b in enumerate(foc["blocks"])
               if b["r"] == rr and b["c"] == cc]
        if not hit:
            raise SystemExit(
                f"--block {spec}: no block (r={rr},c={cc}) in the {nb_r}x{nb_c} "
                f"focus grid for {sub}")
        sites[label or f"BLOCK-{rr}-{cc}"] = hit[0]

    res = {"subject": sub, "coverage_k_merge": ka, "coverage_k_frame": K_ONLY,
           "ref_frame": meta_a.get("ref_frame"), "n_frames": meta_a.get("n_frames"),
           "resampler": meta_a.get("resampler"), "colour": meta_a.get("colour"),
           "levels": meta_a.get("levels"), "window_px": N_WIN, "sites": {}}

    rendered: list[str] = []
    pending: list = []
    tmplA = tmplB = None
    nqA = nqB = 0.0
    step = max(1, foc["n_frames"] // max(1, len(foc["sampled"])))
    for label, bi in sites.items():
        cy, cx, b = pos[bi]
        ref = refine_best_frame(sub, b["u"], b["v"], b["best_frame"],
                                foc["n_frames"], span=max(2, step), 
                                sampled=foc["sampled"])
        kf = ref["best"]
        tif, meta_b = render_frame(sub, kf)
        rendered.append(tif)
        yb = tri.luma(tri.load16(tif))
        kb = meta_b.get("coverage_k", K_ONLY)
        r = compare_site(ya, yb, ka, kb, cy, cx)
        ta, tb, ta2 = r["_tiles"]
        td = os.path.join(tri.OUT, "tiles")
        os.makedirs(td, exist_ok=True)
        np.savez_compressed(os.path.join(td, f"{sub}.{label}.npz"),
                            merge=ta, frame=tb, merge_gathered=ta2,
                            ka=ka, kb=kb, s=ka / kb)
        if label == "FLAT":
            # This subject's own noise, measured per arm, on real content.
            tmplA, nqA = tri.noise_template(ta)
            tmplB, nqB = tri.noise_template(tb)
            res["noise_ref"] = {"block": [b["r"], b["c"]], "x": cx, "y": cy,
                                "merge_nyq_dn": round(float(np.sqrt(nqA)), 4),
                                "frame_nyq_dn": round(float(np.sqrt(nqB)), 4)}
        pending.append((label, b, kf, ref, kb, r))

    assert tmplA is not None, "FLAT site did not run; no noise template"
    for label, b, kf, ref, kb, r in pending:
        measure_site(r, ka, tmplA, nqA, tmplB, nqB)
        r.pop("_tiles", None)
        # QUALITY GATES.  A site whose two arms do not actually match, or whose
        # self-calibration returns a physically impossible gather gain, has not
        # been measured -- it has been guessed.  Say so rather than let it vote.
        bad = []
        caution = []
        gc = r["high"]["gather_cost"]
        if not (0.50 <= gc <= 1.00):
            bad.append(f"gather_cost={gc:.3f} outside 0.50..1.00 (unphysical)")
        if r["high"]["cost_spread"] > 0.15:
            caution.append(f"cost cross-check differs by {r['high']['cost_spread']:.3f}"
                           f" (exact-s={r['high']['cost_scale']:.3f} vs"
                           f" phase-avg={r['high']['cost_shift']:.3f});"
                           f" {r["high"]["cost_rule"]}")
        r["reliable"] = not bad
        r["why_unreliable"] = bad
        r["caution"] = caution
        # A low arm-to-arm ncc is NOT an instrument failure: at a site whose
        # depth spans more than one frame, the merge legitimately does not look
        # like ANY single frame.  It is recorded so the classifier can require
        # merge>frame before reading it as the merge doing its job.
        r["depth_complex"] = r["ncc"] < 0.85
        # A site whose strongest edges are not well clear of its own pixel
        # noise carries no evidence about sharpness either way.  Judged on the
        # EDGE metric, which is primary; the band figures are kept only to show
        # what the superseded metric would have claimed.
        eg = r["edge"]
        if eg["merge_dnpx"] < 4.0 * eg["noise_merge_dn"]:
            caution.append(f"edges ({eg['merge_dnpx']:.0f} DN/px) not clear of "
                           f"noise ({eg['noise_merge_dn']:.0f} DN); weak evidence")
        if 0.0 < eg["blur_equiv_px"] <= 0.35:
            caution.append("blur equivalent at or below the instrument floor "
                           "(0.3 px, commissioning E3b)")
        if eg["blur_equiv_px"] >= 3.0:
            caution.append("blur equivalent SATURATED at the top of the "
                           "calibration grid; true value is >= 3.0 px")
        r.update({"block": [b["r"], b["c"]], "best_frame": kf, "refine": ref,
                  "frame_coverage_k": kb, "at_bracket_end": b["at_end"],
                  "src_hf_max_dn": b["hf_max_dn"], "src_hf_min_dn": b["hf_min_dn"],
                  "fall_near": b["fall_near"], "fall_far": b["fall_far"]})
        res["sites"][label] = r
        flag = ("" if r["reliable"] else "  UNRELIABLE: " + "; ".join(bad))
        flag += ("  CAUTION: " + "; ".join(caution)) if caution else ""
        hi = r["high"]
        e = r["edge"]
        print(f"  {label:<12s} block({b['r']},{b['c']}) @({r['x']},{r['y']}) "
              f"frame {kf}/{foc['n_frames']} (coarse {ref['coarse']}"
              f"{ref['moved_by']:+d})  ncc={r['ncc']:.3f}\n"
              f"      EDGE   merge={e['merge_dnpx']:9.1f} frame={e['frame_dnpx']:9.1f} "
              f"corr={e['frame_corr_dnpx']:9.1f} DN/px   ratio={e['ratio']:.4f}"
              f"   blur_equiv={e['blur_equiv_px']:.2f}px"
              f"   deficit={e['deficit_dnpx']:+.1f} DN/px\n"
              f"      noise  merge={e['noise_merge_dn']:7.1f} frame="
              f"{e['noise_frame_dn']:7.1f} DN ({e['noise_ratio']}x)"
              f"   [band metric would say {hi['ratio_corr']}]{flag}")

    out = os.path.join(tri.OUT, "compare", sub + args.tag + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)

    if not args.keep:
        for t in set(rendered):
            try:
                os.remove(t)
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
