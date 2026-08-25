"""N3 -- commission the instrument by PLANT, before any real image is scored.

Rule 20 / discipline 839 / SYNTHESIS fact 1646: an instrument that has never
been shown to move, and never been shown to REJECT the thing it must decline,
is not an instrument.  This script refuses to let anything else run unless:

  P1 NULL          a clean edge with nothing planted reads |S| and |C| below
                   the null tolerance on both components, and the verdict is
                   literally "NULL (no rim)".
  P2 SENSITIVITY   a planted CONTRAST-ENHANCING halo of known amplitude 0.030
                   and known half-width 13 px is recovered as C ~ +2*0.030
                   (the decomposition doubles it), S ~ 0, and a width within
                   +/- 3 px of 13.
  P3 SPECIFICITY   a planted ADDITIVE-BRIGHT glow of the same amplitude and
                   width is recovered as S ~ +2*0.030 and C ~ 0.  This is the
                   control that gives the verdict its meaning: without it, a
                   bright-on-both-sides glow and a contrast overshoot are the
                   same reading.  The FIRST version of this instrument failed
                   exactly here, twice -- once because the peak statistic was
                   an argmax that could not return a negative number, and once
                   because the edge transition itself swamped the raw
                   per-side statistics.  Both defects were caught before a
                   single real pixel was scored.
  P4 WIDTH POWER   a plant at half-width 26 px must read a width about twice
                   the 13 px plant's, so the width axis is not a constant.
  P5 CROSSTALK     neither plant may be misreported as the other: the contrast
                   plant's |S| and the additive plant's |C| must both stay
                   under a quarter of the planted signal.

Any failure raises.  A green from an uncommissioned instrument is worthless.

Run:  python experiments/M121-halo-polarity/n3_plant.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from m121_io import OUT  # noqa: E402
from runner import scan, sign_table  # noqa: E402

LO, HI = 2000.0, 18000.0
# AGENTS.md rule 9: the flat-ROI amplitude floor that E2 and the controls use.
# The plants have A = 16000 DN, far above it, so it changes nothing here --
# but N3 must commission the EXACT configuration the analysis runs.
MIN_AMPLITUDE = 2000.0
AMP = 0.030
GAIN = 2.0              # S and C are (bright -/+ dark), so a plant of `amp` on
                        # each side reads 2*amp in the component that carries it
W13, W26 = 13.0, 26.0
NOISE = 60.0            # DN; near the measured single-frame background sd scale
NULL_TOL = 0.006        # dimensionless; what "zero" looks like for this rig


def base_edge(h=768, w=768, angle_deg=0.0, blur=1.5, seed=7) -> tuple[np.ndarray, np.ndarray]:
    """A blurred step edge at `angle_deg`, plus signed distance to the edge."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    th = np.deg2rad(angle_deg)
    # normal direction (cos, sin); signed distance from the image centre line
    s = (xx - w / 2) * np.cos(th) + (yy - h / 2) * np.sin(th)
    img = np.where(s > 0, HI, LO)
    img = gaussian_filter(img, blur)
    rng = np.random.default_rng(seed)
    img = img + rng.normal(0.0, NOISE, img.shape)
    return img.astype(np.float32), s


def plant(img: np.ndarray, s: np.ndarray, amp: float, width: float, mode: str) -> np.ndarray:
    """Add a rim of amplitude `amp * (HI - LO)` within `width` px of the edge."""
    A = HI - LO
    band = (np.abs(s) <= width) & (np.abs(s) > 0.0)
    out = img.copy()
    if mode == "contrast":
        out[band & (s > 0)] += amp * A          # bright side pushed up
        out[band & (s < 0)] -= amp * A          # dark side pushed down
    elif mode == "additive":
        out[band] += amp * A                    # both sides lifted
    else:
        raise ValueError(mode)
    return out


def run(name, img):
    return scan(img, label=name, grad_percentile=99.5, max_edges=400,
                isolation_frac=0.35, flat_tol=0.20, min_amplitude=MIN_AMPLITUDE)


def _pack(v):
    def comp(k):
        c = v.get(k)
        if c is None:
            return None
        return {"ext": c["peak"], "at": c["peak_at"], "w50": c["w50"],
                "w10": c["w10"], "cutoff": c["cutoff"], "d0": c["d0"],
                "boot": [c["boot_median"], c["boot_lo95"], c["boot_hi95"]],
                "bands": c["bands"]}
    return {"S": comp("S"), "C": comp("C"), "bright": comp("bright"),
            "dark": comp("dark"), "verdict": sign_table(v),
            "n_pair": v["n_pair"], "rise_p90": v["rise_p90"],
            "rise_median": v["rise_median"], "C_d0": v["C_d0"]}


def _one(tag, img, s, results, failures, hard: bool):
        fail = failures if hard else []
        local = []
        r_null = run(f"P1-null-{tag}", img)
        r_con13 = run(f"P2-contrast-w13-{tag}", plant(img, s, AMP, W13, "contrast"))
        r_add13 = run(f"P3-additive-w13-{tag}", plant(img, s, AMP, W13, "additive"))
        r_con26 = run(f"P4-contrast-w26-{tag}", plant(img, s, AMP, W26, "contrast"))

        results[tag] = {k: _pack(v) for k, v in
                        (("null", r_null), ("contrast13", r_con13),
                         ("additive13", r_add13), ("contrast26", r_con26))}

        want = GAIN * AMP

        # --- P1 NULL -------------------------------------------------------
        for comp in ("S", "C", "bright", "dark"):
            pk = r_null[comp]["boot_median"]
            if abs(pk) >= NULL_TOL:
                local.append(f"P1 NULL {tag} {comp}: |{pk:+.5f}| >= {NULL_TOL}")
        if sign_table(r_null) != "NULL (no rim)":
            local.append(f"P1 {tag}: null verdict is {sign_table(r_null)!r}, not NULL")

        # --- P2 SENSITIVITY -------------------------------------------------
        c = r_con13["C"]["boot_median"]
        if not (0.75 * want <= c <= 1.25 * want):
            local.append(f"P2 amp {tag}: C={c:+.5f} outside 25% of {want}")
        w = r_con13["C"]["w50"]
        if not (W13 - 3.0 <= w <= W13 + 3.0):
            local.append(f"P2 width {tag}: C w50={w:.2f} outside {W13}+/-3")
        if sign_table(r_con13) != "CONTRAST-ENHANCING (both sides pushed outward)":
            local.append(f"P2 {tag}: contrast plant reads "
                            f"{sign_table(r_con13)!r}, not CONTRAST-ENHANCING")
        # per-side, read beyond the transition: BOTH sides must be positive
        for side in ("bright", "dark"):
            v = r_con13[side]["boot_median"]
            if not (0.6 * AMP <= v <= 1.4 * AMP):
                local.append(f"P2 side {tag} {side}: {v:+.5f} not ~ +{AMP}")

        # --- P3 SPECIFICITY -------------------------------------------------
        sv = r_add13["S"]["boot_median"]
        if not (0.75 * want <= sv <= 1.25 * want):
            local.append(f"P3 amp {tag}: additive S={sv:+.5f} outside 25% of {want}")
        w = r_add13["S"]["w50"]
        if not (W13 - 3.0 <= w <= W13 + 3.0):
            local.append(f"P3 width {tag}: additive S w50={w:.2f} outside {W13}+/-3")
        if sign_table(r_add13) != "ADDITIVE-BRIGHT (both sides lifted)":
            local.append(f"P3 {tag}: additive plant reads "
                            f"{sign_table(r_add13)!r}, not ADDITIVE-BRIGHT -- "
                            "the instrument cannot tell an additive glow from a "
                            "contrast rim, which is the whole question")
        # THE per-side specificity gate, and the one the first two versions of
        # this instrument failed: an additive glow must read BRIGHT POSITIVE
        # and DARK NEGATIVE.  This is the reading the report's polarity table
        # is built on, so it is gated directly and not only through S.
        bb = r_add13["bright"]["boot_median"]
        db = r_add13["dark"]["boot_median"]
        if not (0.6 * AMP <= bb <= 1.4 * AMP):
            local.append(f"P3 side {tag} bright: {bb:+.5f} not ~ +{AMP}")
        if not (-1.4 * AMP <= db <= -0.6 * AMP):
            local.append(f"P3 side {tag} dark: {db:+.5f} is not ~ -{AMP} -- the "
                         "per-side reading cannot separate an additive glow "
                         "from a contrast rim")

        # --- P4 WIDTH POWER --------------------------------------------------
        w13, w26 = r_con13["C"]["w50"], r_con26["C"]["w50"]
        if not (w26 > w13 + 6.0):
            local.append(f"P4 {tag}: w26={w26:.2f} not clearly above w13={w13:.2f}")
        k13, k26 = r_con13["C"]["cutoff"], r_con26["C"]["cutoff"]
        if not (k26 > k13 + 6.0):
            local.append(f"P4 {tag}: cutoff26={k26:.2f} not above cutoff13={k13:.2f}")

        # --- P5 CROSSTALK ----------------------------------------------------
        xs = abs(r_con13["S"]["boot_median"])
        if xs > 0.25 * want:
            local.append(f"P5 {tag}: contrast plant leaks S={xs:.5f} (> {0.25*want:.5f})")
        xc = abs(r_add13["C"]["boot_median"])
        if xc > 0.25 * want:
            local.append(f"P5 {tag}: additive plant leaks C={xc:.5f} (> {0.25*want:.5f})")

        results[tag]["gates"] = local
        results[tag]["passed"] = not local
        # `S` alone is a weaker but genuinely separate claim: it is the
        # transition-immune component, and it is the one that decides
        # ADDITIVE vs CONTRAST.  Track whether S survives even where C does not.
        results[tag]["S_passed"] = not [g for g in local if "P3" in g or "P1" in g]
        if hard:
            failures.extend(local)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    failures = []

    # A LADDER of edge softnesses, not a single operating point.  The
    # instrument is HARD-gated at the sharpest rung only; the rest map the
    # envelope.  E2 is then required to filter its real edges to the softest
    # rung that passed, because a claim about `C` on an edge softer than that
    # would be an assertion of absence from an instrument shown to be blind
    # there (rule 43).
    for angle in (0.0, 27.0):
        for blur in (1.5, 2.0, 2.5, 3.0, 4.0):
            tag = f"a{int(angle)}b{blur:g}"
            img, s = base_edge(angle_deg=angle, blur=blur)
            _one(tag, img, s, results, failures, hard=(blur <= 1.5))

    # The envelope: the largest 10-90 rise at which EVERY gate passed at BOTH
    # angles.  `S` gets its own, looser envelope for the same reason.
    by_blur = {}
    for tag, blk in results.items():
        blur = float(tag.split("b")[1])
        rise = max(v["rise_p90"] for k, v in blk.items()
                   if isinstance(v, dict) and "rise_p90" in v)
        ok_all = blk["passed"]
        ok_S = blk["S_passed"]
        prev = by_blur.setdefault(blur, {"rise": 0.0, "all": True, "S": True})
        prev["rise"] = max(prev["rise"], rise)
        prev["all"] &= ok_all
        prev["S"] &= ok_S

    good_all = [v["rise"] for v in by_blur.values() if v["all"]]
    good_S = [v["rise"] for v in by_blur.values() if v["S"]]
    envelope = {
        "rise_p90_full": max(good_all) if good_all else float("nan"),
        "rise_p90_S_only": max(good_S) if good_S else float("nan"),
        "ladder": {f"blur{b:g}": {"rise_p90": v["rise"], "all_gates": v["all"],
                                  "S_gates": v["S"]}
                   for b, v in sorted(by_blur.items())},
        "note": ("`rise_p90_full` is the softest edge at which BOTH the "
                 "additive component S and the contrast component C were shown "
                 "to recover a planted 13 px rim.  Beyond it C goes blind: the "
                 "transition exclusion (1.6x the 10-90 rise) swallows a 13 px "
                 "rim entirely, so C reads ~0 for a plant that is certainly "
                 "there.  `rise_p90_S_only` is the softest edge at which S "
                 "alone still recovers it.  E2 must respect both."),
    }
    results["envelope"] = envelope

    (OUT / "n3-plant.json").write_text(json.dumps(results, indent=1, default=float))
    print("\n=== N3 commissioning ladder ===")
    for tag in sorted(results, key=lambda t: (t != "envelope", t)):
        if tag == "envelope":
            continue
        blk = results[tag]
        for k in ("null", "contrast13", "additive13", "contrast26"):
            v = blk[k]
            sv = v["S"]["boot"][0] if v["S"] else float("nan")
            cv = v["C"]["boot"][0] if v["C"] else float("nan")
            wv = v["C"]["w50"] if v["C"] else float("nan")
            ws = v["S"]["w50"] if v["S"] else float("nan")
            print(f"  {tag:8s} {k:11s} rise90={v['rise_p90']:5.2f} Cd0={v['C_d0']:5.2f}  "
                  f"S={sv:+.5f} (w50 {ws:5.2f})  C={cv:+.5f} (w50 {wv:5.2f})   {v['verdict']}")
        print(f"  {tag:8s} {'GATES':11s} {'PASS' if blk['passed'] else 'fail: ' + '; '.join(blk['gates'])}")
    print("\n=== ENVELOPE ===")
    for b, v in envelope["ladder"].items():
        print(f"  {b:9s} rise_p90={v['rise_p90']:6.2f}  all_gates={v['all_gates']}  S_gates={v['S_gates']}")
    print(f"  -> S and C both valid for 10-90 rise <= {envelope['rise_p90_full']:.2f} px")
    print(f"  -> S alone valid for 10-90 rise <= {envelope['rise_p90_S_only']:.2f} px")
    if failures:
        print()
        for f in failures:
            print("FAIL:", f)
        raise SystemExit("N3 FAILED at the hard-gated rung -- the instrument is not "
                         "commissioned; every other number in this milestone is void.")
    print("\nN3 PASS at the hard-gated rung, envelope mapped above.")


if __name__ == "__main__":
    main()
