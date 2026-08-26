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
import re
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

# --- FIELD DEFINITIONS, SHIPPED WITH THE NUMBERS ----------------------------
# Every field this tool emits is defined here, and `triage.json` carries this
# dict verbatim under "fields".  The definition travels WITH the number.
#
# WHY THIS EXISTS.  `noise_flat` and `noise_ratio_all_sites_diag` are the same
# ratio over different site sets.  They differ by 17x in opposite directions on
# `pencil-steep-angle-cpl` (10.31 vs 0.60).  Nothing in the artifact said so,
# and the wrong one shipped inside a user-facing sentence on 9 of 26 rows.
#
# Names that are near-synonyms get read as corroborating even when they
# disagree wildly.  A definition kept anywhere other than beside the number --
# a README, a docstring, an agent's report -- is a definition the reader of the
# artifact does not have.
FIELD_DEFS = {
    # -- row level --
    "subject": "master filename stem in SHIP-V1 (<subject>.tiff)",
    "verdict": "classification; the full set with counts is in top-level "
               "'counts', including categories with zero members",
    "why": "the evidence sentences behind the verdict. Every number in them "
           "is derived at render time from the fields in 'evidence'",
    "remedy": "the action that would fix it, or 'none'",
    "evidence": "the measurements the verdict rests on; keys defined here",
    # -- capture: focus coverage --
    "n_frames": "frames in the bracket",
    "n_gap_blocks": "focus blocks whose sharpest frame is the first or last "
                    "in the bracket = gap_far + gap_near",
    "gap_far": "of n_gap_blocks, how many elected the FAR end",
    "gap_near": "of n_gap_blocks, how many elected the NEAR end",
    "boundary_pct": "% of ALL pixels electing the first or last frame",
    "detail_gap_pct": "% of DETAIL-BEARING pixels (top 3 contrast deciles of "
                      "this subject, a within-subject percentile -- never an "
                      "absolute DN threshold) electing an end frame",
    "detail_enrichment": "detail_gap_pct divided by the same statistic on a "
                         "size-matched RANDOM mask. >1 means end-elections "
                         "target detail; <1 means they are on blank areas and "
                         "the gap is not costing resolved structure",
    "end0_pct": "% of pixels electing the FIRST frame",
    "endN_pct": "% of pixels electing the LAST frame",
    # -- capture: motion --
    "motion_med_ncc": "median normalised cross-correlation between adjacent "
                      "frames. A static stack measures 0.9997 (bee-3-cpl)",
    "motion_blocks": "of 24 blocks, how many have adjacent-frame NCC < 0.98",
    # -- merge vs best source frame --
    "n_sites_used": f"comparison sites passing the arm-SNR gate (>= "
                    f"{4.0}); only these vote on the verdict",
    "n_sites_dropped": "sites rejected by that gate. A site whose edges are "
                       "not clear of its own pixel noise carries no evidence "
                       "in either direction",
    "edge_ratio_min": "LOWEST merge/frame edge-slope ratio across usable "
                      "sites, gather-corrected. >1 means the merge is "
                      "sharper. This is the field the verdict uses",
    "merge_edge_dnpx": "merge edge slope, DN/px, camera-linear: the MAXIMUM "
                       "over usable sites. NOT DIVISIBLE by frame_edge_dnpx "
                       "-- see that field",
    "frame_edge_dnpx": "best single source frame's edge slope, DN/px, "
                       "camera-linear, NOT gather-corrected, MAXIMUM over "
                       "usable sites -- possibly a DIFFERENT site from "
                       "merge_edge_dnpx. Dividing the two does NOT give "
                       "edge_ratio_min (it disagrees on 13 of 25 rows, worst "
                       "1.92 vs 1.43 on bee-2-cpl). Use edge_ratio_min",
    "worst_blur_px": f"largest merge-vs-best-frame softness across usable "
                     f"sites, as an equivalent Gaussian sigma in pixels. "
                     f"Instrument floor {BLUR_FLOOR_PX} px: a planted 0.30 px "
                     f"blur reads as 0.21, so values at or below the floor "
                     f"are not distinguishable from zero",
    "worst_site": "which site produced worst_blur_px",
    # -- noise: the pair that caused the shipped defect --
    "noise_flat": "best source frame's pixel noise DIVIDED BY the merge's, at "
                  "the FLAT site ONLY. >1 means the MERGE IS CLEANER; <1 "
                  "means the merge is NOISIER. Flat-only because pixel_noise "
                  "is the residual after a 3x3 median, which at a detail-rich "
                  "site counts resolved structure as noise. THIS IS THE "
                  "REPORTABLE FIGURE",
    "noise_ratio_all_sites_diag": "the same ratio averaged over ALL usable "
                                  "sites INCLUDING DETAIL, where the "
                                  "estimator is confounded (corpus medians: "
                                  "1.47x at FLAT, 0.72x at DETAIL). "
                                  "DIAGNOSTIC ONLY, NOT REPORTABLE. Retained "
                                  "because it shipped inside a user-facing "
                                  "sentence and the audit trail needs it",
    # -- ORCH's independently chosen site --
    "orch_site_ratio": "merge/frame edge-slope ratio at ORCH's independently "
                       "chosen best-resolved site, not mine",
    "orch_site_merge_dnpx": "merge edge slope at that ORCH-chosen site, DN/px",
    "orch_site_frame_dnpx": "best frame's edge slope at that site, DN/px",
    "orch_site_frame_snr": "the frame arm's signal-to-noise at that site; "
                           "below the gate it carries no evidence",
    # -- provenance --
    "master_w": "master width in pixels",
    "master_h": "master height in pixels",
}

# Thresholds the verdicts are actually computed with, shipped alongside them so
# a reader can see WHICH threshold produced a verdict without reading source.
# Also so that no downstream renderer has to hardcode one: the contact sheet
# printed "instrument floor 0.3 px" against a real floor of 0.35 for as long as
# both existed, because the number was retyped into prose instead of read.
CONSTANTS = {
    "blur_floor_px": {
        "value": BLUR_FLOOR_PX,
        "meaning": "blur below this is not distinguishable from zero: a "
                   "planted 0.30 px blur reads as 0.21 (commission E3b)"},
    "arm_snr_min": {
        "value": 4.0,
        "meaning": "a comparison site must clear this on BOTH arms to vote; "
                   "read off a corpus gap of 1.54-2.99 vs 5.59-43.46"},
    "motion_median_ncc": {
        "value": MOTION_MED,
        "meaning": "adjacent-frame NCC median below this, AND at least "
                   "motion_blocks blocks below 0.98, classifies as motion"},
    "motion_blocks": {
        "value": MOTION_BLOCKS,
        "meaning": "of 24 blocks; both conditions required"},
    "gap_detail_pct": {
        "value": GAP_DETAIL_PCT,
        "meaning": "% of detail-bearing pixels electing an end frame above "
                   "which a coverage gap is called; corpus gap 0.803 -> 2.595"},
    "gap_enrichment_min": {
        "value": GAP_ENRICH,
        "meaning": "end-elections must target detail at least this much more "
                   "than a size-matched random mask would"},
}

# --- localised vs pervasive coverage gap ------------------------------------
# A coverage gap that touches 6-7% of detail pixels and one that touches 55% are
# not the same product problem, and collapsing them into one label is what let
# the owner judge the whole tool by its worst tiles.  The corpus separates them
# by itself, with the largest gap in the whole distribution:
#
#   0.00 ... 0.80 (lavendar), 2.59 (flower-bud-alone), 6.20 (fern),
#   7.34 (ruler)   <-- then nothing at all until -->   55.17 (flowers-cpl)
#
# a 7.5x jump with no subject inside it.  Read off the corpus, not asserted;
# any threshold in (7.34, 55.17) classifies all 26 identically.  20.1% is the
# geometric midpoint of that empty band, so it is maximally far from both edges.
LOCALISED_GAP_PCT = 20.1

# A localised gap is downgraded to "predominantly sound" ONLY when the merge is
# also shown to be at or ahead of the best single source frame at the subject's
# own best-resolved site.  That second condition matters: without it this would
# be a bare threshold that assumes a small gap is harmless.  With it, the claim
# is "the gap is small AND the rest of the frame is measurably good", which is
# what the label asserts.  See §8 of docs/research/BUILD-TRIAGE.md -- both
# subjects that trip this rule (`highly-angled-ruler-mm-cpl` x1.916 and
# `flower-bud-with-background-fern-cpl` x1.889) were originally mislabelled
# because compare.py's own windows landed on empty background.
LOCALISED_MERGE_AHEAD = 0.95

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


def _orch_best(sub: str) -> dict | None:
    """Merge-vs-source at ORCH's independently chosen best-resolved site.

    A SECOND, INDEPENDENT WINDOW.  compare.py's own selectors include the
    emptiest sites in the frame by design (see `weak()` below), so a subject
    whose windows all land on background reads as "no detail anywhere", which is
    indistinguishable from a genuine capture limit.  ORCH's detailgallery.py
    picks one site per subject by mean |laplacian| on a coarse grid -- a
    different statistic, chosen by a different agent -- so agreement between the
    two pickers is worth more than either alone.  See experiments/BUILD-TRIAGE/
    orchsites.py for the coordinates and the worked failure that motivated this.
    """
    p = os.path.join(tri.OUT, "compare", f"{sub}.orch.json")
    if not os.path.exists(p):
        return None
    try:
        s = (json.load(open(p, encoding="utf-8"))["sites"] or {}).get("ORCH-BEST")
    except Exception:
        return None
    if not s:
        return None
    e = s.get("edge") or {}
    nm = e.get("noise_merge_dn") or 0.0
    nf = e.get("noise_frame_dn") or 0.0
    m = e.get("merge_dnpx") or 0.0
    f = e.get("frame_corr_dnpx") or 0.0
    msnr = m / nm if nm > 0 else float("inf")
    fsnr = f / nf if nf > 0 else float("inf")
    return {"ratio": e.get("ratio"), "merge_dnpx": m, "frame_dnpx": f,
            "merge_snr": msnr, "frame_snr": fsnr,
            "votes": bool(min(msnr, fsnr) >= 4.0)}


def noise_phrase(nr: float | None) -> str:
    """Render a noise ratio into words, deriving the WORD from the NUMBER.

    `nr` is frame_noise / merge_noise (`compare.py:131`, stated at
    `noisesite.py:2`), so **nr > 1 means the merge is cleaner** and nr < 1 means
    the merge is noisier.

    This is the only place noise is turned into English, because a sentence
    written *alongside* a number drifts from it. The shipped v1 hard-coded the
    word "less" and rendered nr = 0.88 as "0.88x less pixel noise" -- asserting
    an advantage where the measurement records a disadvantage, on 9 of 12 GOOD
    rows, in an artifact a user reads. It survived review because a factor below
    1 attached to "less" still skims as a gain. Two rules follow, and both are
    enforced by `audit_noise_sentence` rather than by care:

      1. the comparative is chosen by the number, never fixed in the format string
      2. the magnitude quoted beside a comparative is always >= 1, because a
         factor below 1 cannot modify "less" or "more" in English
    """
    if nr is None:
        return ""
    if nr > 1.0:
        return (f" while carrying {nr:.2f}x less pixel noise than the best "
                f"source frame")
    if nr < 1.0:
        return (f" while carrying {1.0 / nr:.2f}x more pixel noise than the "
                f"best source frame")
    return " with the same pixel noise as the best source frame"


# Comparative -> the direction of `nr` that alone justifies it.
_COMPARATIVES = {"less": "gt", "cleaner": "gt", "more": "lt", "noisier": "lt"}


def audit_noise_sentence(text: str, nr: float | None) -> list[str]:
    """Violations where a rendered noise claim disagrees with its own number.

    Returns a list so a caller can gate the whole corpus at once. Checks both
    failure modes of the shipped defect: a comparative pointing the wrong way,
    and a sub-unit magnitude attached to a comparative at all.
    """
    if nr is None or not text:
        return []
    bad = []
    words = [w for w in _COMPARATIVES if re.search(rf"\b{w}\b", text)]
    for w in words:
        want = _COMPARATIVES[w]
        if want == "gt" and not nr > 1.0:
            bad.append(f"says {w!r} but noise ratio is {nr} (merge is noisier)")
        if want == "lt" and not nr < 1.0:
            bad.append(f"says {w!r} but noise ratio is {nr} (merge is cleaner)")
    if words:
        for mag in re.findall(r"(\d+(?:\.\d+)?)x", text):
            if float(mag) < 1.0:
                bad.append(f"quotes {mag}x beside a comparative; a factor "
                           f"below 1 cannot modify {words[0]!r}")
    return bad


def merge_limited_phrase(worst_site: str, worst_blur: float, ws: dict,
                         floor_px: float) -> str:
    """The MERGE-LIMITED sentence, quoting the site it names.

    Kept separate so it can be commissioned. The corpus currently holds ZERO
    MERGE-LIMITED rows, so this branch never executes on real data -- which is
    exactly why it previously shipped quoting `edge_best`/`frame_best`, maxima
    taken over EVERY usable site, in a sentence that names one specific site. A
    reader checking the named crop would find numbers from a different one.
    """
    m = ws.get("merge_dnpx", float("nan"))
    f = ws.get("frame_corr_dnpx", ws.get("frame_dnpx", float("nan")))
    return (f"merge is {worst_blur:.2f} px-equivalent softer than the best "
            f"source frame at {worst_site} ({m:.0f} vs {f:.0f} DN/px at that "
            f"site, ratio {ws.get('ratio', float('nan')):.3f}); instrument "
            f"floor is {floor_px} px")


def _legacy_noise_phrase(nr: float) -> str:
    """THE SHIPPED DEFECT, retained solely as a plant for the auditor.

    Never called in anger. If `audit_noise_sentence` stops flagging this, the
    guard has regressed and the bug can ship again.
    """
    return f" while carrying {nr}x less pixel noise"


def commission_wording() -> None:
    """Plant the defect the auditor must catch, and the null it must pass."""
    # PLANT: the shipped form at the real corpus value. Must be caught twice --
    # once for direction, once for the sub-unit magnitude.
    v = audit_noise_sentence(_legacy_noise_phrase(0.88), 0.88)
    assert len(v) >= 2, f"auditor missed the shipped defect at nr=0.88: {v}"
    # PLANT: direction alone, with a legal magnitude.
    v = audit_noise_sentence(" while carrying 1.14x less pixel noise", 0.88)
    assert v, "auditor missed an inverted comparative at nr=0.88"
    # NULL: the corrected renderer must be silent at BOTH branches.
    for nr in (0.88, 1.47, 1.0):
        v = audit_noise_sentence(noise_phrase(nr), nr)
        assert not v, f"auditor fired on the corrected form at nr={nr}: {v}"
    # The two branches must actually differ in word, not merely in number.
    assert "more pixel noise" in noise_phrase(0.88), noise_phrase(0.88)
    assert "less pixel noise" in noise_phrase(1.47), noise_phrase(1.47)
    # And the magnitude must be reciprocated, not reprinted.
    assert "1.14x" in noise_phrase(0.88), noise_phrase(0.88)

    # MERGE-LIMITED sentence: it must quote the NAMED site, not a corpus max.
    # This branch has no live row (0 MERGE-LIMITED in the corpus), so without a
    # plant it would ship unexecuted -- which is how it acquired the defect.
    named = {"merge_dnpx": 900.0, "frame_corr_dnpx": 1500.0, "ratio": 0.600}
    other = {"merge_dnpx": 9999.0, "frame_corr_dnpx": 8888.0, "ratio": 1.125}
    s = merge_limited_phrase("DETAIL", 1.23, named, 0.35)
    assert "900 vs 1500" in s, s
    assert "0.600" in s, s
    assert "9999" not in s and "8888" not in s, \
        f"MERGE-LIMITED sentence leaked a non-named site's numbers: {s}"
    assert "DETAIL" in s, s
    # The plant that proves the assertion above can fail: feeding the OTHER
    # site's numbers must change the sentence.
    assert merge_limited_phrase("DETAIL", 1.23, other, 0.35) != s

    print("wording commissioning OK  (shipped defect caught on 2 counts; "
          "inverted comparative caught;\n                          corrected "
          "form silent at nr = 0.88 / 1.47 / 1.00; branches differ in word;\n"
          "                          MERGE-LIMITED quotes its named site, not "
          "a corpus maximum)")


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
    #
    # `noise_gain` below averages over ALL usable sites, DETAIL included, and so
    # violates the policy in the paragraph above it.  That is not hypothetical:
    # the shipped GOOD sentence quoted it, the confounded DETAIL sites dragged
    # the mean under 1, and the row then read "0.88x less pixel noise" -- an
    # inverted claim caused by the wrong field, not by the wording alone.  It is
    # kept as an all-sites diagnostic and named so it cannot be mistaken for a
    # reportable figure.  ANY SENTENCE ABOUT NOISE MUST USE `flat_nr`.
    #
    # A comment stating a policy is not an implementation of it: this one was
    # right and the code eight lines below it did the other thing.
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
        "noise_ratio_all_sites_diag": round(sum(noise_gain) / len(noise_gain), 2)
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

        # LOCALISED?  A 6-7% gap in an otherwise excellent frame is a different
        # product problem from a 55% one, and the corpus separates them by 7.5x
        # with nothing in between.  Downgrade only when the merge is ALSO shown
        # ahead of the best single frame at the subject's own best-resolved
        # site -- so the claim is "small gap AND the rest measurably good".
        ob = _orch_best(sub)
        if ob:
            r["evidence"]["orch_site_ratio"] = ob["ratio"]
            r["evidence"]["orch_site_merge_dnpx"] = round(ob["merge_dnpx"], 1)
            r["evidence"]["orch_site_frame_dnpx"] = round(ob["frame_dnpx"], 1)
            r["evidence"]["orch_site_frame_snr"] = round(ob["frame_snr"], 1)
        if (dgap < LOCALISED_GAP_PCT and ob and ob["votes"]
                and (ob["ratio"] or 0) >= LOCALISED_MERGE_AHEAD):
            r["verdict"] = "GOOD - localised coverage gap"
            r["why"] = [
                f"predominantly sound: at its own best-resolved site the merge "
                f"is x{ob['ratio']:.2f} the best single source frame "
                f"({ob['merge_dnpx']:.0f} vs {ob['frame_dnpx']:.0f} DN/px, "
                f"frame SNR {ob['frame_snr']:.1f}), but {dgap:.1f}% of "
                f"detail-bearing pixels (centred {loc}) elect the {end} frame "
                f"and were never captured sharp"]
            r["remedy"] = (
                f"usable as delivered; to recover the {loc} region, extend the "
                f"bracket past the {end} frame.")
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
        # Quote the NAMED site's own numbers.  `edge_best`/`frame_best` are
        # maxima over every usable site, so a sentence that names `worst_site`
        # and then quotes them invites a reader to check the named crop against
        # figures that came from a different one -- and they will not match.
        ws = (usable.get(worst_site) or {}).get("edge") or {}
        r["why"].append(
            merge_limited_phrase(worst_site, worst_blur, ws, BLUR_FLOOR_PX))
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
    # `noise_flat`, NOT the all-sites diagnostic: see the policy note above the
    # flat_nr assignment.  Wording is derived from the number by noise_phrase().
    r["why"].append(
        f"merge matches the best source frame everywhere measured (worst "
        f"{worst_blur:.2f} px-equivalent, at/near the {BLUR_FLOOR_PX} px "
        f"instrument floor)" + noise_phrase(r["evidence"].get("noise_flat")))
    r["remedy"] = "none"
    return r


def main() -> int:
    commission_wording()
    subs = tri.SUBJECTS
    rows = [classify(s, load(s)) for s in subs]

    order = ["GOOD", "GOOD - localised coverage gap", "MERGE-LIMITED",
             "CAPTURE-LIMITED - coverage gap",
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

    # SHIPPING GATE.  No row may leave with a sentence that disagrees with its
    # own measurement.  This runs on the real emitted strings, not on samples --
    # the inverted form shipped on 9 of 12 GOOD rows precisely because nothing
    # ever compared the words against the number they were describing.
    viol = []
    for r in rows:
        nr = (r.get("evidence") or {}).get("noise_flat")
        for w in r.get("why") or []:
            for v in audit_noise_sentence(w, nr):
                viol.append(f"  {r['subject']}: {v}\n      {w!r}")
    if viol:
        raise SystemExit("noise wording disagrees with the measurement:\n"
                         + "\n".join(viol))
    print(f"wording gate OK: {len(rows)} rows, every noise claim agrees with "
          f"its own noise_flat")

    # DEFINITION GATE.  Every field that ships must carry its definition, and
    # every definition must correspond to a field that ships.  Checked in BOTH
    # directions: an undefined field is unreadable, and a definition for a
    # field that no longer exists is worse than none, because it describes
    # something the reader cannot find and will map onto the nearest name.
    emitted = set()
    for r in rows:
        emitted |= set(r.keys())
        emitted |= set((r.get("evidence") or {}).keys())
    undefined = sorted(emitted - set(FIELD_DEFS))
    orphaned = sorted(set(FIELD_DEFS) - emitted)
    if undefined or orphaned:
        raise SystemExit(
            "field definitions out of step with the emitted fields:\n"
            + "".join(f"  UNDEFINED (ships with no definition): {k}\n"
                      for k in undefined)
            + "".join(f"  ORPHANED (defined but never emitted): {k}\n"
                      for k in orphaned))
    print(f"definition gate OK: {len(emitted)} emitted fields, all defined; "
          f"no orphaned definitions")

    with open(os.path.join(tri.OUT, "triage.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "counts": counts, "fields": FIELD_DEFS,
                   "constants": CONSTANTS}, fh, indent=1)
    print(f"\n-> {os.path.join(tri.OUT, 'triage.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
