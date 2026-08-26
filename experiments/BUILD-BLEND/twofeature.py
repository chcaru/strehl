"""Two-feature differential profile: merge arm minus single-frame reference.

ORCH measured two defects at very different scales and opposite signs:

    feature      sign             peak                    extent
    tight rim    merge brighter   +984 DN at d=6 px       dies by d~13 px
    broad aura   merge DARKER     -4293 DN at d=117 px    reaches d~300 px

A single "halo score" would hide the fact that these have opposite signs, and
would let an arm that fixes one while worsening the other read as progress. So
this script reports them SEPARATELY and its commissioning gate specifically
tests that it can tell them apart: a planted rim must not show up as an aura,
and a planted aura must not show up as a rim.

The reference arm is STREHL_ONLY_FRAME, which performs no election at all -- one
frame is trivially its own winner everywhere. Anything that differs between a
merge and that reference is the merge's doing; the scene cancels by
construction. That is the whole reason this comparison is worth making, and it
is a reference no merge-versus-merge comparison can provide.

Measured on LINEAR camera-native output. The tone curve amplifies the rim about
4x, so a --srgb render would overstate any fix.

    python twofeature.py <ref.tif> <label:arm.tif> [<label:arm.tif> ...] [--json OUT]
    python twofeature.py --commission
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

try:
    import tifffile
except ImportError:  # pragma: no cover
    sys.exit("need tifffile: PIL.Image silently returns 8-bit for 16-bit RGB TIFFs")

from scipy import ndimage

# ORCH's bin edges, so the two agents' numbers land in the same rows -- extended
# INWARD past the contour.
#
# The inward half is not cosmetic. ORCH's diffmap.png shows "a thin red thread on
# the contour"; a bin set that starts at d=0 can only ever see the outside of that
# contour, and if the thread straddles or sits inside the silhouette such a bin set
# reports its absence rather than its position. Running this instrument in its
# original outside-only form against ORCH's own TIFFs reproduced their aura to
# within 5% and found no rim at all, which is the signature of a window that
# cannot express the feature, not of a feature that is not there.
BIN_EDGES = [
    -100, -80, -65, -50, -40, -30, -25, -20, -16, -12,
    -8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8,
    10, 12, 16, 20, 25, 30, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300,
    400, 500, 600,
]

# ORCH measured a +984 DN rim at d=6 and this instrument, in an earlier form,
# reported none -- on ORCH's own TIFFs. Two window defects were responsible and
# both are fixed above:
#
#   1. Bins started at d=0, so only the OUTSIDE of the contour was ever
#      profiled. ORCH's diffmap.png shows the thread ON the contour.
#   2. The narrowest bin was 4 px. A median over a bin that a thin feature only
#      half fills returns roughly the unaffected half: commissioning a 4 px-wide
#      plant straddling the contour recovered +108 DN of a planted +984, an 89%
#      amplitude error. A feature narrower than the bin is attenuated, and the
#      attenuation is invisible in the output -- it just reads as absence.
#
# Hence 1 px bins across d in [-8, 8]. The contour is long enough that even a
# 1 px annulus holds tens of thousands of pixels.

# The far field: far enough from the subject that no merge behaviour should
# reach, close enough to stay on the same illumination plateau. ORCH's window.
FAR_LO, FAR_HI = 600.0, 1400.0

# Feature windows. The rim dies by d~13; the aura peaks at 117 and reaches 300.
# The rim window spans BOTH sides of the contour for the reason above. 16 px is
# the split: past the rim's death, well inside the aura's rise, and a bin edge,
# so no bin is shared between the two features.
RIM_MIN_D = -16.0
RIM_MAX_D = 16.0
AURA_MIN_D = 16.0


def luma(path: Path) -> np.ndarray:
    """Unweighted channel mean.

    These are camera-native primaries, so colorimetric luma weights would be
    dishonest -- they are defined against sRGB primaries this image is not in.
    """
    arr = tifffile.imread(str(path))
    if arr.dtype != np.uint16:
        raise SystemExit(f"{path}: dtype is {arr.dtype}, expected uint16")
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise SystemExit(f"{path}: shape is {arr.shape}, expected (h, w, 3)")
    out = arr.astype(np.float32).mean(axis=2)
    del arr
    return out


def subject_mask(ref: np.ndarray) -> np.ndarray:
    """Largest connected dark component of the single-frame reference.

    Taken from the REFERENCE, not from either merge, so neither arm gets to
    choose the geometry it is scored against.

    Largest-component only because dust specks and stray debris are also dark
    and would each grow their own distance field.
    """
    lo, hi = np.percentile(ref, [5, 95])
    thresh = 0.5 * (lo + hi)
    dark = ref < thresh
    lab, n = ndimage.label(dark)
    if n == 0:
        raise SystemExit("no dark component found; is the subject dark on light?")
    sizes = ndimage.sum(dark, lab, index=np.arange(1, n + 1))
    keep = int(np.argmax(sizes)) + 1
    return lab == keep


def signed_distance(mask: np.ndarray) -> np.ndarray:
    """Positive outside the subject, negative inside."""
    outside = ndimage.distance_transform_edt(~mask).astype(np.float32)
    inside = ndimage.distance_transform_edt(mask).astype(np.float32)
    return outside - inside


def profile(diff: np.ndarray, dist: np.ndarray, ref: np.ndarray | None = None) -> dict:
    """Median differential per distance bin, plus the far-field offset.

    Median, not mean: the backdrop of a real frame carries dust and the
    occasional out-of-family pixel, and one of them in a thin annulus moves a
    mean by more than the effect being measured.

    The `pct` column is the difference as a fraction of the reference's own
    level in that same bin. It is here to discriminate two things that look
    identical in DN: a per-frame LEVEL difference, which is multiplicative and
    so reads as a constant percentage across every bin, and a genuine spatial
    artifact, which does not. Neither arm normalises frame level (`--photometric`
    is opt-in and off by default), so a level effect is a live possibility and
    has to be ruled out rather than assumed away.
    """
    far = (dist > FAR_LO) & (dist < FAR_HI)
    if far.sum() < 1000:
        raise SystemExit(f"far field has only {far.sum()} px; frame too small or subject too big")
    far_off = float(np.median(diff[far]))

    rows = []
    for lo, hi in zip(BIN_EDGES[:-1], BIN_EDGES[1:]):
        sel = (dist >= lo) & (dist < hi)
        n = int(sel.sum())
        if n < 200:
            rows.append({"lo": lo, "hi": hi, "n": n, "raw": None, "ref": None,
                         "p95": None, "p05": None, "ref_med": None, "pct": None})
            continue
        raw = float(np.median(diff[sel]))
        rm = float(np.median(ref[sel])) if ref is not None else None
        vals = diff[sel]
        p95 = float(np.percentile(vals, 95.0))
        p05 = float(np.percentile(vals, 5.0))
        rows.append({
            "lo": lo, "hi": hi, "n": n,
            "raw": raw,               # reported beside every referenced number
            "ref": raw - far_off,     # excess over the far field
            "p95": p95 - far_off,     # a feature on PART of the contour
            "p05": p05 - far_off,
            "ref_med": rm,
            "pct": (raw / rm * 100.0) if rm else None,
        })
    return {"far_offset": far_off, "far_n": int(far.sum()), "rows": rows}


def features(prof: dict) -> dict:
    """Pull the two features out separately. Never combine them.

    Two statistics per feature, because they answer different questions:

      `med`  the median over the whole annulus -- what the merge does to the
             typical pixel at that distance. A feature present on only part of
             a long, complex silhouette does not move it.
      `p95`  the 95th percentile over the same annulus -- what the merge does
             to the worst part of the contour. ORCH's diffmap.png shows a thin
             red THREAD, which is a localised object; the median over a 7 Mpx
             silhouette's annulus is structurally unable to see one, and will
             report its absence rather than its locality.
    """
    rim = {"med": 0.0, "d": None, "p95": 0.0, "p95_d": None}
    aura = {"med": 0.0, "d": None, "p05": 0.0, "p05_d": None}
    for r in prof["rows"]:
        if r["ref"] is None:
            continue
        mid = 0.5 * (r["lo"] + r["hi"])
        if RIM_MIN_D <= r["lo"] and r["hi"] <= RIM_MAX_D:
            # the rim is the merge running BRIGHT: take the maximum
            if r["ref"] > rim["med"]:
                rim["med"], rim["d"] = r["ref"], mid
            if r["p95"] > rim["p95"]:
                rim["p95"], rim["p95_d"] = r["p95"], mid
        elif r["lo"] >= AURA_MIN_D:
            # the aura is the merge running DARK: take the minimum
            if r["ref"] < aura["med"]:
                aura["med"], aura["d"] = r["ref"], mid
            if r["p05"] < aura["p05"]:
                aura["p05"], aura["p05_d"] = r["p05"], mid
    # back-compat keys for callers that want the headline number
    rim["peak"] = rim["med"]
    aura["peak"] = aura["med"]
    return {"rim": rim, "aura": aura}


def extents(prof: dict, floor: float) -> dict:
    """Outermost distance at which each feature still clears the noise floor.

    The floor comes from a subject-free control region of the same frame, so it
    is this instrument's own noise on this data, not an assumed number.
    """
    rim_ext, aura_ext = 0.0, 0.0
    for r in prof["rows"]:
        if r["ref"] is None:
            continue
        if RIM_MIN_D <= r["lo"] and r["hi"] <= RIM_MAX_D and r["ref"] > floor:
            rim_ext = max(rim_ext, abs(float(r["hi"])), abs(float(r["lo"])))
        if r["lo"] >= AURA_MIN_D and r["ref"] < -floor:
            aura_ext = max(aura_ext, float(r["hi"]))
    return {"rim": rim_ext, "aura": aura_ext}


def null_floor(diff: np.ndarray, mask: np.ndarray) -> float:
    """Instrument noise: the same profile run where there is no subject.

    A subject-free corner is given a synthetic silhouette and profiled exactly
    as the real one is. Whatever comes back is what this instrument reports
    when the answer is known to be nothing.
    """
    h, w = diff.shape
    # Quadrant with the least subject in it.
    quads = {
        "tl": (slice(0, h // 2), slice(0, w // 2)),
        "tr": (slice(0, h // 2), slice(w // 2, w)),
        "bl": (slice(h // 2, h), slice(0, w // 2)),
        "br": (slice(h // 2, h), slice(w // 2, w)),
    }
    best, best_frac = None, 2.0
    for name, sl in quads.items():
        frac = float(mask[sl].mean())
        if frac < best_frac:
            best, best_frac = sl, frac
    sub = diff[best]
    sh, sw = sub.shape
    fake = np.zeros((sh, sw), dtype=bool)
    r = min(sh, sw) // 8
    yy, xx = np.ogrid[:sh, :sw]
    fake[(yy - sh // 2) ** 2 + (xx - sw // 2) ** 2 < r * r] = True
    d = signed_distance(fake)
    p = profile(sub, d)
    dev = [abs(x["ref"]) for x in p["rows"] if x["ref"] is not None]
    return (max(dev) if dev else 0.0), best_frac


def render(label: str, prof: dict, feat: dict, ext: dict, floor: float,
           backdrop: float) -> str:
    out = []
    out.append(f"\n--- {label} ---")
    out.append(f"far-field offset (arm - ref, {FAR_LO:.0f}-{FAR_HI:.0f} px): "
               f"{prof['far_offset']:+.1f} DN over {prof['far_n']:,} px")
    out.append(f"instrument noise floor (subject-free quadrant): {floor:.1f} DN")
    out.append("")
    out.append(f"  {'d (px)':>10}  {'n':>9}  {'ref DN':>8}  {'med DN':>9}  "
               f"{'vs far':>9}  {'p95':>9}  {'p05':>9}  {'med %':>7}")
    for r in prof["rows"]:
        rng = f"{r['lo']}-{r['hi']}"
        if r["ref"] is None:
            out.append(f"  {rng:>10}  {r['n']:>9,}  {'--':>8}  {'--':>9}  "
                       f"{'--':>9}  {'--':>9}  {'--':>9}  {'--':>7}")
        else:
            rm = f"{r['ref_med']:.0f}" if r["ref_med"] is not None else "--"
            pc = f"{r['pct']:+.2f}" if r["pct"] is not None else "--"
            out.append(f"  {rng:>10}  {r['n']:>9,}  {rm:>8}  {r['raw']:>+9.1f}  "
                       f"{r['ref']:>+9.1f}  {r['p95']:>+9.1f}  {r['p05']:>+9.1f}  {pc:>7}")
    out.append("")
    rim, aura = feat["rim"], feat["aura"]
    out.append(f"  {'feature':<12} {'statistic':<24} {'peak':>26}  {'extent':>16}")
    rd = f"at d={rim['d']:+.1f} px" if rim["d"] is not None else ""
    ad = f"at d={aura['d']:+.1f} px" if aura["d"] is not None else ""
    rpd = f"at d={rim['p95_d']:+.1f} px" if rim["p95_d"] is not None else ""
    apd = f"at d={aura['p05_d']:+.1f} px" if aura["p05_d"] is not None else ""
    rext = ("dies by d~" + format(ext["rim"], ".0f") + " px") if ext["rim"] else "below floor"
    aext = ("reaches d~" + format(ext["aura"], ".0f") + " px") if ext["aura"] else "below floor"
    out.append(f"  {'tight rim':<12} {'median (typical px)':<24} "
               f"{rim['med']:>+12.1f} DN {rd:>11}  {rext:>16}")
    out.append(f"  {'':<12} {'p95 (worst of contour)':<24} "
               f"{rim['p95']:>+12.1f} DN {rpd:>11}")
    out.append(f"  {'broad aura':<12} {'median (typical px)':<24} "
               f"{aura['med']:>+12.1f} DN {ad:>11}  {aext:>16}")
    out.append(f"  {'':<12} {'p05 (worst of contour)':<24} "
               f"{aura['p05']:>+12.1f} DN {apd:>11}")
    if backdrop > 0:
        out.append(f"  as a fraction of the {backdrop:.0f} DN backdrop: "
                   f"rim med {rim['med']/backdrop*100:+.1f}%, "
                   f"aura med {aura['med']/backdrop*100:+.1f}%")
    return "\n".join(out)


def analyse(ref: np.ndarray, arm: np.ndarray, mask: np.ndarray,
            dist: np.ndarray, backdrop: float, label: str):
    diff = arm - ref
    floor, qfrac = null_floor(diff, mask)
    prof = profile(diff, dist, ref)
    feat = features(prof)
    ext = extents(prof, floor)
    text = render(label, prof, feat, ext, floor, backdrop)
    return text, {"label": label, "floor": floor, "quad_subject_frac": qfrac,
                  "profile": prof, "features": feat, "extents": ext}


# --------------------------------------------------------------------------
# commissioning
# --------------------------------------------------------------------------

def _synth(h=3000, w=3000, seed=0):
    rng = np.random.default_rng(seed)
    ref = np.full((h, w), 19032.0, dtype=np.float32)
    # illumination field: the scene's own gradient, which must NOT be reported
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ref += 900.0 * (xx / w) + 400.0 * (yy / h)
    ref += rng.normal(0.0, 60.0, (h, w)).astype(np.float32)
    mask = np.zeros((h, w), dtype=bool)
    cy, cx, r = h // 2, w // 2, 400
    ygrid, xgrid = np.ogrid[:h, :w]
    mask[(ygrid - cy) ** 2 + (xgrid - cx) ** 2 < r * r] = True
    ref[mask] *= 0.18
    d = signed_distance(mask)
    return ref, mask, d


def _plant(ref, d, rim_amp, aura_amp, noise=60.0, seed=1, rim_band=(4, 8),
           rim_arc=1.0):
    """Copy the reference, add an INDEPENDENT noise realisation, plant features.

    The independent noise matters. Without it `arm - ref` is exactly zero
    everywhere the plant is absent, the measured noise floor comes back at
    exactly 0.0 DN, and every detection gate written as `peak > k * floor`
    silently degrades to `peak > 0`. A commissioning run that cannot produce a
    non-zero floor has not exercised the gate it claims to have tested.

    `rim_band` is a SIGNED distance band, so the rim can be planted outside the
    contour, straddling it, or inside it. The inside case is the one that
    matters: it is the case the original outside-only bin set could not see.

    `rim_arc` is the fraction of the contour the rim is planted on. A real
    silhouette is a complicated shape and a defect may sit on one side of it;
    a median over the whole annulus cannot see a feature on 15% of it, which is
    why the p95 statistic exists and why this knob has to be commissioned.
    """
    rng = np.random.default_rng(seed)
    arm = ref + rng.normal(0.0, noise, ref.shape).astype(np.float32)
    if rim_amp:
        sel = (d >= rim_band[0]) & (d < rim_band[1])
        if rim_arc < 1.0:
            h, w = ref.shape
            yy, xx = np.mgrid[0:h, 0:w]
            ang = np.arctan2(yy - h // 2, xx - w // 2)
            sel &= (ang > -np.pi) & (ang < -np.pi + 2 * np.pi * rim_arc)
        arm[sel] += rim_amp
    if aura_amp:
        arm[(d >= 100) & (d < 125)] += aura_amp
    return arm


def commission() -> int:
    print("=" * 74)
    print("COMMISSIONING twofeature.py")
    print("=" * 74)
    ref, mask, d = _synth()
    backdrop = float(np.median(ref[(d > FAR_LO) & (d < FAR_HI)]))
    fails = []

    cases = [
        # name,                       rim,  aura, want_rim, want_aura, rim_band, arc
        ("null (arm == ref)",         0.0,     0.0, False, False, (4, 8), 1.0),
        ("rim OUTSIDE (+984 @ d=6)",  984.0,   0.0, True,  False, (4, 8), 1.0),
        ("rim INSIDE  (+984 @ d=-6)", 984.0,   0.0, True,  False, (-8, -4), 1.0),
        ("rim ON contour (+984)",     984.0,   0.0, True,  False, (-2, 2), 1.0),
        ("rim THIN 2px on contour",   984.0,   0.0, True,  False, (-1, 1), 1.0),
        ("aura only (-4293 @ d=112)",   0.0, -4293.0, False, True, (4, 8), 1.0),
        ("both",                      984.0, -4293.0, True,  True, (4, 8), 1.0),
    ]
    for name, ra, aa, want_rim, want_aura, band, arc in cases:
        arm = _plant(ref, d, ra, aa, rim_band=band, rim_arc=arc)
        text, res = analyse(ref, arm, mask, d, backdrop, name)
        f = res["features"]
        got_rim = f["rim"]["peak"] > 5 * res["floor"]
        got_aura = f["aura"]["peak"] < -5 * res["floor"]
        ok = (got_rim == want_rim) and (got_aura == want_aura)
        # amplitude recovery, only where a feature was planted
        amp_ok = True
        detail = ""
        if want_rim:
            err = abs(f["rim"]["peak"] - ra) / ra
            amp_ok &= err < 0.20
            detail += f" rim {f['rim']['peak']:+.0f} vs {ra:+.0f} ({err*100:.1f}% err)"
        if want_aura:
            err = abs(f["aura"]["peak"] - aa) / abs(aa)
            amp_ok &= err < 0.20
            detail += f" aura {f['aura']['peak']:+.0f} vs {aa:+.0f} ({err*100:.1f}% err)"
        verdict = "PASS" if (ok and amp_ok) else "FAIL"
        if verdict == "FAIL":
            fails.append(name)
        print(f"\n[{verdict}] {name}")
        print(f"       floor={res['floor']:.1f} DN  "
              f"rim={f['rim']['peak']:+.1f}@{f['rim']['d']}  "
              f"aura={f['aura']['peak']:+.1f}@{f['aura']['d']}")
        print(f"       want rim={want_rim} got {got_rim} | want aura={want_aura} got {got_aura}"
              + ("|" + detail if detail else ""))

    # A defect on PART of a silhouette. The median cannot see it. That is not a
    # bug in the median -- it is the entire reason the p95 column exists, and it
    # is the leading candidate for why this instrument reported no rim on ORCH's
    # own TIFFs while their difference map plainly shows a thread. This block
    # asserts both halves: the median goes quiet, and p95 still finds it.
    print("\n" + "-" * 74)
    print("localised rim: a 2 px thread on PART of the contour")
    print("  (diffmap.png shows a THREAD, which is a localised object)")
    for arc in (0.50, 0.15):
        arm = _plant(ref, d, 984.0, 0.0, rim_band=(-1, 1), rim_arc=arc)
        _, res = analyse(ref, arm, mask, d, backdrop, f"arc {arc}")
        f = res["features"]
        med, p95 = f["rim"]["med"], f["rim"]["p95"]
        err = abs(p95 - 984.0) / 984.0
        ok = err < 0.20
        print(f"  arc={arc*100:>3.0f}% of contour: median={med:>+8.1f} DN   "
              f"p95={p95:>+8.1f} DN ({err*100:>4.1f}% err)   {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"localised rim arc={arc}")
    arm = _plant(ref, d, 984.0, 0.0, rim_band=(-1, 1), rim_arc=0.15)
    _, res = analyse(ref, arm, mask, d, backdrop, "arc 0.15")
    if res["features"]["rim"]["med"] > 5 * res["floor"]:
        print("  note: the median DID see the 15% arc, so p95 is belt-and-braces here")
    else:
        print("  confirmed: the median reports NOTHING for a 15% arc that p95 recovers")
        print("  -> a median-only instrument would have called this arm clean")

    # The floor is the denominator of every detection gate above. If it is
    # trivially zero, `peak > 5 * floor` is `peak > 0` and nothing was tested.
    # If it does not respond to noise, it is a constant wearing a measurement's
    # clothes. Both have to be ruled out explicitly.
    print("\n" + "-" * 74)
    print("floor responsiveness (the gate's denominator must be real and must move)")
    floors = []
    for sigma in (60.0, 240.0, 960.0):
        arm = _plant(ref, d, 0.0, 0.0, noise=sigma, seed=7)
        _, res = analyse(ref, arm, mask, d, backdrop, f"noise {sigma:.0f}")
        floors.append(res["floor"])
        print(f"  arm noise sigma={sigma:>6.0f} DN  ->  floor={res['floor']:>7.2f} DN")
    if floors[0] <= 0.0:
        fails.append("floor is trivially zero")
        print("  FAIL: floor is 0.0, so every `peak > k*floor` gate is `peak > 0`")
    elif not (floors[0] < floors[1] < floors[2]):
        fails.append("floor does not track noise")
        print("  FAIL: floor does not rise monotonically with injected noise")
    else:
        ratio = floors[2] / floors[0]
        print(f"  PASS: floor is non-zero and rises monotonically "
              f"({ratio:.1f}x across a 16x noise range)")
    if fails:
        print(f"COMMISSIONING FAILED: {len(fails)} case(s): {', '.join(fails)}")
        print("The instrument is not fit to score either arm. Do not use its numbers.")
        return 1
    print("COMMISSIONING PASSED")
    print("  - reports nothing when nothing was planted")
    print("  - recovers each feature's amplitude to within 20%")
    print("  - a planted rim does NOT read as an aura, and vice versa: the two")
    print("    features are separable, so an arm cannot fix one, worsen the")
    print("    other, and have this instrument call it progress")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", nargs="?")
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--json")
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args()

    if a.commission:
        return commission()
    if not a.ref or not a.arms:
        ap.error("need <ref.tif> and at least one <label:arm.tif>")

    ref = luma(Path(a.ref))
    print(f"reference : {a.ref}  {ref.shape}")
    mask = subject_mask(ref)
    print(f"subject   : {mask.sum():,} px ({mask.mean()*100:.1f}% of frame)")
    dist = signed_distance(mask)
    backdrop = float(np.median(ref[(dist > FAR_LO) & (dist < FAR_HI)]))
    print(f"backdrop  : {backdrop:.0f} DN (median, {FAR_LO:.0f}-{FAR_HI:.0f} px from silhouette)")

    results = []
    for spec in a.arms:
        label, _, path = spec.partition(":")
        if not path:
            label, path = Path(spec).stem, spec
        arm = luma(Path(path))
        if arm.shape != ref.shape:
            raise SystemExit(f"{path}: shape {arm.shape} != reference {ref.shape}")
        text, res = analyse(ref, arm, mask, dist, backdrop, label)
        print(text)
        results.append(res)
        del arm

    if a.json:
        Path(a.json).write_text(json.dumps(
            {"ref": a.ref, "backdrop": backdrop, "arms": results}, indent=2))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
