"""Classify all 26 subjects into the triage categories, and print the arithmetic.

The central question, per subject and per region:

    Is this soft because the MERGE lost detail the source frames contain
    (retouch -- a bug we fix), or because NO SOURCE FRAME ever contained that
    detail (reshoot -- a capture limit we report)?

Three independent evidence streams answer it, and none of them is allowed to
answer it alone:

  focuscurve.py  compares FRAMES AGAINST OTHER FRAMES, entirely inside the raw
                 Bayer domain.  It never touches a merge, so a coverage gap it
                 reports cannot be an artefact of the merge.

  localmotion.py exploits the fact that adjacent frames are one focus step
                 apart: after low-passing, structural change between neighbours
                 is MOTION, not focus.  Validated on the two stacks known to
                 have moved.

  compare.py     puts the merge and the best source frame through the SAME
                 pinned binary in camera-linear sRGB and measures edge slope in
                 DN/px, noise-robustly, with the extra gather self-calibrated.

MOTION IS ADJUDICATED BEFORE MERGE LOSS.  A subject that moved during the
bracket produces merge < frame for a reason that is not the merge's fault, and
calling that MERGE-LIMITED would route a reshoot to the wrong team.

Every category must be reachable, every subject must land in exactly one, and
the arithmetic must be printed.  A subject that cannot be classified gets an
explicit UNRESOLVED row rather than silently vanishing -- a count that does not
move looks identical whether nothing was wrong or nothing was examined.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

# --- thresholds, all justified by commissioning or by measured corpus spread --
BLUR_FLOOR_PX = 0.35     # E3b: planted 0.30 px reads as 0.21; below this is noise
BLUR_BAD_PX = 0.80       # a defect worth routing a fix for
MOTION_MED = 0.9900      # foam 0.9794 / bubbles 0.9459 vs bee-3 0.99967
MOTION_BLOCKS = 6        # blocks below 0.98 out of 24
GAP_BLOCKS = 6           # blocks of 24 whose focus peak sits at a bracket end
GAP_BLOCKS_BAD = 12
# --- coverage, per-pixel (supersedes the 24-block aggregate above) ----------
# The primary coverage instrument is now the per-pixel election map: the share
# of pixels whose elected frame is the first or last rung of the bracket.  A
# pixel electing an end is telling you its true optimum lies outside the
# bracket.  Raw `boundary %` is NOT usable on its own, because on this corpus
# it is dominated by featureless backdrop -- `tweezers-cpl` has 4.761% of its
# pixels at a bracket end and 0.000% of its DETAIL-bearing pixels there, and
# `coffee-bean` likewise falls 8.570% -> 0.000%.  Electing an end where there
# is nothing to resolve costs nothing and no reshoot can fix it.  So the gate
# is the rate among detail-bearing pixels, and it must beat its own
# size-matched shuffled null before it counts as targeting detail at all.
#
# 2.0% sits in an empty band in the measured corpus: the rates run
#   ... 0.499 (119MSDCF), 0.517 (pencil-steep), 0.803 (lavendar)
#   then 2.595 (flower-bud-alone), 6.200 (fern), 7.336 (ruler), 55.167 (flowers)
# -- a 3.2x jump with no subject inside it.  Like the motion threshold, this is
# read off the corpus rather than asserted.
GAP_DETAIL_PCT = 2.0
GAP_ENRICH = 1.0         # must target detail more than a random mask would
# Diffraction: the source's own best frame never delivers a sharp edge anywhere.
# Expressed against the corpus, not asserted a priori.
DIFFRACTION_DNPX = 600.0

# Which mechanism produces the end-elections is NOT reliably separable by the
# summary statistics -- `flowers-cpl` (occlusion) and `highly-angled-ruler-mm-cpl`
# (a genuine gap) sit at enrichment 1.57 and 1.50 and conHi3 0.472 and 0.449,
# i.e. indistinguishable.  The split below is therefore made by INSPECTION of
# each subject's election map, recorded here so the call is auditable rather
# than hidden in a threshold that does not actually separate the cases.
# See covermaps/<subject>.jpg for the picture each verdict was read from.
OCCLUSION = {
    # Sec 23 of docs/captures-needed.md established this per-pixel: the boundary
    # pixels are thin ribbons tracing petal edges, concentrated 7.8x in the
    # highest-contrast decile, and it explicitly WITHDREW the "reshoot wider"
    # advice.  The election map confirms it and adds a second component -- broad
    # interstitial shadow between overlapping petals, which is occluded from the
    # lens, not merely out of focus.  Neither component is fixable with frames.
    #
    # RE-CONFIRMED against the source frames themselves, after an intermediate
    # draft of this file wrongly relabelled it a coverage gap at end0.  That
    # draft rested on a level-normalised focus score, which at a low-signal site
    # tracks shot noise / level ~ 1/sqrt(level) and therefore always elects the
    # DARKEST frame -- frame 0 of a bracket that brightens 19.1%.  The
    # unnormalised form has the mirror bias and elects the brightest.  With the
    # noise subtracted (sitescan.focus_score, commissioned C16/C17) the picture
    # is unambiguous and matches the crops:
    #   * at (1180,900) the through-focus response is FLAT across all 176
    #     frames (hf_rel 0.0551 -> 0.0562) and every frame is a featureless
    #     gradient at 1:1.  A bracket that stopped short rises toward an end;
    #     this does not rise at all.  Nothing reaches that site, ever.
    #   * at the three background sites both arms sit below 1% modulation and
    #     54-68% of the SOURCE frame's measured edge power is grain rather than
    #     detail (grainprobe.py), against ~3% for the merge.
    #   * where the subject IS reachable, at (1504,1502), the merge beats the
    #     best single frame by 5.07x and resolves trichomes and pollen grains
    #     that no individual frame holds.
    # So the merge is not losing anything here; most of this frame is at depths
    # no focus plane in this bracket reaches.  Drift is 0.00 px, so not motion.
    "flowers-cpl": (
        "a dense mass of overlapping petals: the end-elections are rim ribbons "
        "on petal edges plus deep interstitial shadow that no focus plane can "
        "reach, not a bracket that stopped short"),
}


def _side_table(name: str) -> dict:
    """Corpus-wide side tables keyed by subject, loaded once."""
    p = os.path.join(tri.OUT, name)
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return {r["subject"]: r for r in json.load(fh)}


COVERAGE = _side_table("coverage.json")
DIMS = _side_table("dims.json")


def load(sub: str) -> dict:
    out = {}
    for kind in ("focus", "motion", "compare"):
        p = os.path.join(tri.OUT, kind, sub + ".json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                out[kind] = json.load(fh)
    return out


def classify(sub: str, ev: dict) -> dict:
    """Return a verdict dict.  Never raises; missing evidence -> UNRESOLVED."""
    r: dict = {"subject": sub, "why": [], "remedy": "", "evidence": {}}
    foc, mot, cmp_ = ev.get("focus"), ev.get("motion"), ev.get("compare")

    missing = [k for k in ("focus", "motion", "compare") if k not in ev]
    if missing:
        r["verdict"] = "UNRESOLVED"
        r["why"].append("missing evidence: " + ", ".join(missing))
        r["remedy"] = "re-run the missing stage; NOT a statement about the image"
        return r

    # ---- capture-side facts, all measured frame-against-frame ---------------
    blocks = foc["blocks"]
    n_gap_far = sum(1 for b in blocks if b.get("at_end") == "far")
    n_gap_near = sum(1 for b in blocks if b.get("at_end") == "near")
    n_gap = n_gap_far + n_gap_near
    med = mot["median_pair_ncc"]
    nmot = mot["n_blocks_below_098"]
    src_best = max((b["hf_max_dn"] for b in blocks), default=0.0)

    sites = cmp_["sites"]
    # A site whose "edges" are not clear of its own pixel noise carries no
    # evidence about sharpness in either direction, and must not vote.
    # bee-2-cpl DEFICIT is the worked example: a blank white background corner
    # where the source's 263 DN/px "edge slope" sits on 130 DN of pixel noise,
    # scoring the merge at 0.159 and a saturated 3.00 px of blur. The crop shows
    # two featureless white squares. Left in, it would have manufactured the
    # single worst MERGE-LIMITED verdict in the corpus out of nothing.
    SNR_MIN = 4.0

    def weak(v: dict) -> bool:
        """Reject a site that cannot bear a merge-loss verdict.

        Two-sided by construction.  ``edge_slope`` is the p99.5 gradient of a
        median-filtered tile; on a tile that contains real edges it is immune to
        noise to 0.45% across a 16x noise range (commission E2), but on a
        *featureless* tile there is nothing else for the p99.5 to land on and the
        statistic degenerates into a noise measure.

        The earlier gate tested the merge arm only, which is backwards for the
        direction that matters.  A pyramid merge carries 1.4-7x LESS pixel noise
        than any single frame, so a merge-only gate sets the *stricter* threshold
        on the *cleaner* arm and waves through exactly the sites where the source
        looks sharper purely because it is noisier.  flowers-cpl DEFICIT is the
        worked example: source 96.7 DN/px sitting on 46.7 DN of its own noise
        (2.07x) against merge 37.5 DN/px on 6.7 DN (5.6x).  The merge arm passed,
        the site was scored ratio=0.388 / blur=3.00 px, and the crop shows two
        blank panels with no detail in either arm.

        So: a site may only testify to merge loss (ratio < 1) if BOTH arms are
        clear of their own noise.  A site showing the merge ahead (ratio >= 1)
        needs only the merge arm to be real -- you cannot manufacture a merge win
        out of source noise, but you can certainly manufacture a merge loss.
        """
        if any("not clear of" in c for c in v.get("caution", [])):
            return True
        e = v.get("edge") or {}
        m, f = e.get("merge_dnpx", 0.0), e.get("frame_corr_dnpx", 0.0)
        nm, nf = e.get("noise_merge_dn", 0.0), e.get("noise_frame_dn", 0.0)
        if nm > 0 and m < SNR_MIN * nm:
            return True
        if e.get("ratio", 1.0) < 1.0 and nf > 0 and f < SNR_MIN * nf:
            return True
        return False

    usable = {k: v for k, v in sites.items()
              if k != "FLAT" and v.get("reliable", True) and not weak(v)}
    dropped = [k for k, v in sites.items()
               if k != "FLAT" and (not v.get("reliable", True) or weak(v))]
    dropped_desc = "; ".join(
        f"{k}({'; '.join(sites[k].get('caution') or sites[k].get('why_unreliable') or ['no signal over noise'])})"
        for k in dropped)
    blur = {k: v["edge"]["blur_equiv_px"] for k, v in usable.items()}
    ratio = {k: v["edge"]["ratio"] for k, v in usable.items()}
    worst_blur = max(blur.values()) if blur else float("nan")
    worst_site = max(blur, key=blur.get) if blur else None
    edge_best = max((v["edge"]["merge_dnpx"] for v in usable.values()), default=0.0)
    frame_best = max((v["edge"]["frame_dnpx"] for v in usable.values()), default=0.0)
    noise_gain = [v["edge"]["noise_ratio"] for v in usable.values()
                  if v["edge"].get("noise_ratio")]

    # Pixel noise is quoted from the FLAT reference site ONLY.
    # pixel_noise() is the residual after a 3x3 median, which at a detail-rich
    # site counts genuinely resolved structure as noise: across the corpus the
    # median noise_ratio is 1.47x (merge cleaner) at FLAT but 0.72x at DETAIL,
    # and the crops at those DETAIL sites -- bee-3-cpl's ommatidia lattice,
    # 109MSDCF's stroke edges -- show more resolved detail in the merge, not
    # more grain.  The statistic cannot separate the two, so it is only reported
    # where there is no detail for it to confuse itself with.
    flat_site = sites.get("FLAT") or {}
    flat_nr = (flat_site.get("edge") or {}).get("noise_ratio")

    r["evidence"] = {
        "n_gap_blocks": n_gap, "gap_far": n_gap_far, "gap_near": n_gap_near,
        "motion_med_ncc": med, "motion_blocks": nmot,
        "worst_blur_px": round(worst_blur, 3) if blur else None,
        "worst_site": worst_site,
        "edge_ratio_min": round(min(ratio.values()), 4) if ratio else None,
        "merge_edge_dnpx": round(edge_best, 1),
        "frame_edge_dnpx": round(frame_best, 1),
        "noise_advantage": round(sum(noise_gain) / len(noise_gain), 2)
        if noise_gain else None,
        "noise_flat": round(flat_nr, 2) if flat_nr else None,
        "n_sites_used": len(usable),
        "n_sites_dropped": len(dropped),
        "n_frames": foc["n_frames"],
        "master_h": (DIMS.get(sub) or {}).get("h"),
        "master_w": (DIMS.get(sub) or {}).get("w"),
    }

    # ---- ADJUDICATION ORDER MATTERS ----------------------------------------
    # 1. Motion first: it produces merge<frame for a reason the merge cannot fix.
    #    BOTH conditions are required.  The corpus separates cleanly: the four
    #    lowest median NCCs (0.9459, 0.9794, 0.9856, 0.9893) sit below 0.99 and
    #    the next subject jumps to 0.99642.  Both stacks known a priori to have
    #    moved -- foam and coffee-bubbles -- are inside that group, which is what
    #    makes the threshold evidence rather than a guess.  Requiring the block
    #    count as well stops a handful of noisy blocks in an otherwise static
    #    stack from being read as motion: 113MSDCF (0.99759) fired on blocks
    #    alone, yet its crops show the merge beating the best frame everywhere.
    if med < MOTION_MED and nmot >= MOTION_BLOCKS:
        r["verdict"] = "CAPTURE-LIMITED - motion"
        r["why"].append(
            f"adjacent-frame NCC median {med:.5f} and {nmot}/24 blocks below "
            f"0.98; a static stack measures 0.9997 (bee-3-cpl)")
        r["remedy"] = ("reshoot: subject moved during the bracket. Shorten the "
                       "bracket or stabilise; no merge change can recover this.")
        return r

    # 2. Coverage, from the per-pixel election map.  Two conditions, because
    #    either alone misclassifies a subject in this corpus: the rate among
    #    detail-bearing pixels must clear the corpus break, AND the boundary
    #    set must target detail more than a size-matched random mask would.
    #    `flower-bud-alone-cpl` is why the second is needed -- 2.595% of its
    #    detail-bearing pixels elect an end, above the threshold, but at 0.34x
    #    of its own null: the bud is a smooth fully-spanned depth map and every
    #    end-election is on the blown backdrop behind it.  Reshooting it wider
    #    would change nothing.
    cov = COVERAGE.get(sub) or {}
    dgap = cov.get("detail_gap_pct")
    enr = cov.get("detail_enrichment")
    if dgap is not None:
        r["evidence"].update({
            "boundary_pct": cov.get("boundary_pct"),
            "detail_gap_pct": dgap,
            "detail_enrichment": enr,
            "end0_pct": cov.get("end0_pct"),
            "endN_pct": cov.get("endN_pct"),
        })
    if dgap is not None and dgap >= GAP_DETAIL_PCT and (enr or 0) >= GAP_ENRICH:
        e0, eN = cov.get("end0_pct", 0.0), cov.get("endN_pct", 0.0)
        end = "first" if e0 >= eN else "last"
        lop = max(e0, eN) / max(min(e0, eN), 1e-6)
        loc = cov.get("location") or "across the frame"
        if sub in OCCLUSION:
            r["verdict"] = "CAPTURE-LIMITED - occlusion/geometry"
            r["why"].append(
                f"{dgap:.1f}% of detail-bearing pixels elect an end of the "
                f"bracket ({enr:.2f}x its own shuffled null), but the geometry "
                f"is the cause, not the bracket: {OCCLUSION[sub]}")
            r["remedy"] = (
                "not fixable by more frames: those regions are occluded, not "
                "merely defocused. Reshoot from another angle.")
            return r
        r["verdict"] = "CAPTURE-LIMITED - coverage gap"
        r["why"].append(
            f"{dgap:.1f}% of detail-bearing pixels elect the {end} frame of "
            f"the bracket ({enr:.2f}x its own shuffled null, {lop:.0f}x "
            f"lopsided to that end); centred {loc}. Their true focus lies "
            f"outside the bracket, so no frame ever held them sharp")
        r["remedy"] = (
            f"reshoot extending the bracket past the {end} frame; "
            f"the merge cannot invent focus no frame captured.")
        return r

    # 3. Merge loss: only now, and only above the instrument's own floor.
    #    This is the FIRST test that needs a usable comparison site, so the
    #    "no site survived" bail-out belongs here and not earlier.  Motion and
    #    coverage gap are measured frame-against-frame by the motion detector
    #    and the focus curve; neither consults the merge, so neither is affected
    #    when every merge-vs-source site is rejected for want of signal.
    #    Returning UNRESOLVED before them threw away decisive independent
    #    evidence: flowers-cpl has 16/24 blocks peaking at the far end of its
    #    bracket, which settles the subject, yet it landed in UNRESOLVED purely
    #    because its comparison sites were featureless in both arms.
    if not usable:
        r["verdict"] = "UNRESOLVED"
        r["why"].append(
            "no capture-side defect found, and every merge-vs-source site was "
            "rejected for want of signal: " + dropped_desc)
        r["remedy"] = ("re-site the comparison on this subject; NOT a statement "
                       "about the image")
        return r

    if worst_blur >= BLUR_BAD_PX:
        r["verdict"] = "MERGE-LIMITED"
        r["why"].append(
            f"merge is {worst_blur:.2f} px-equivalent softer than the best "
            f"source frame at {worst_site} ({edge_best:.0f} vs {frame_best:.0f} "
            f"DN/px); instrument floor is {BLUR_FLOOR_PX} px")
        r["remedy"] = ("retouch: the source frames hold detail the merge did "
                       "not keep. Route to the merge, not to the camera.")
        return r

    # 4. Diffraction: nothing anywhere is sharp, in EITHER arm.
    if frame_best < DIFFRACTION_DNPX and edge_best < DIFFRACTION_DNPX:
        r["verdict"] = "CAPTURE-LIMITED - diffraction/magnification"
        r["why"].append(
            f"the best SOURCE frame delivers only {frame_best:.0f} DN/px at its "
            f"sharpest edge; the merge delivers {edge_best:.0f}. No frame ever "
            f"contained fine detail, so there is nothing to recover.")
        r["remedy"] = ("reshoot at a wider marked aperture; at this "
                       "magnification the effective f-number is ~3x the marked "
                       "one and MTF at Nyquist is near zero.")
        return r

    # 5. GOOD.
    r["verdict"] = "GOOD"
    na = r["evidence"]["noise_advantage"]
    r["why"].append(
        f"merge matches the best source frame everywhere measured (worst "
        f"{worst_blur:.2f} px-equivalent, at/near the {BLUR_FLOOR_PX} px "
        f"instrument floor)" + (f" while carrying {na}x less pixel noise"
                                if na else ""))
    r["remedy"] = "none"
    return r


def main() -> int:
    subs = tri.SUBJECTS
    rows = [classify(s, load(s)) for s in subs]

    order = ["GOOD", "MERGE-LIMITED", "CAPTURE-LIMITED - coverage gap",
             "CAPTURE-LIMITED - occlusion/geometry",
             "CAPTURE-LIMITED - diffraction/magnification",
             "CAPTURE-LIMITED - motion", "UNRESOLVED"]
    unlisted = sorted({r["verdict"] for r in rows} - set(order))
    assert not unlisted, (
        f"verdict(s) not in the arithmetic: {unlisted}. A category missing from "
        f"`order` is counted nowhere and the subject silently disappears.")
    print("=" * 118)
    print("BUILD-TRIAGE: all 26 subjects")
    print("=" * 118)
    print(f"{'subject':<38} {'verdict':<44} {'blur px':>8} {'gap':>5} "
          f"{'motion':>8} {'edge DN/px':>11}")
    print("-" * 118)
    for cat in order:
        for r in [x for x in rows if x["verdict"] == cat]:
            e = r["evidence"]
            print(f"{r['subject']:<38} {r['verdict']:<44} "
                  f"{(e.get('worst_blur_px') if e.get('worst_blur_px') is not None else float('nan')):>8.2f} "
                  f"{e.get('n_gap_blocks', 0):>5} "
                  f"{(e.get('motion_med_ncc') or 0):>8.5f} "
                  f"{(e.get('merge_edge_dnpx') or 0):>11.0f}")
    print("-" * 118)
    counts = {c: sum(1 for r in rows if r["verdict"] == c) for c in order}
    print("\nARITHMETIC")
    tot = 0
    for c in order:
        print(f"  {counts[c]:>3}  {c}")
        tot += counts[c]
    print(f"  {'---':>3}")
    print(f"  {tot:>3}  TOTAL   (must be 26: {'OK' if tot == 26 else 'MISMATCH'})")
    assert tot == len(subs) == 26, f"category counts sum to {tot}, not 26"

    with open(os.path.join(tri.OUT, "triage.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "counts": counts}, fh, indent=1)
    print(f"\n-> {os.path.join(tri.OUT, 'triage.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
