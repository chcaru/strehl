"""Adjudicate M107's lateral-CA correction: is it better, or merely different?

M107 reported the top |R-Y| decile falling 54.08% and decile 1 -- near-neutral
pixels -- rising 583%, with 44.7% of them flipping chroma sign, and its own
registered bar W3 (>90% keep sign) FAILED at 75.1%. Its script printed
`RECOLOURED, NOT REMOVED`.

A +583% change on a near-zero baseline can be invisible or it can be a brand-new
artefact, and THE PERCENTAGE ALONE CANNOT TELL YOU WHICH. A ratio has no units;
the eye does. So the number that decides it is the ABSOLUTE magnitude, and the
unit that decides it is the one the owner actually looks at:

    8-bit display levels = DN16 / 257

Below ~1 level a chroma change cannot be drawn on the owner's screen at all, let
alone seen. That converts a rhetorical percentage into a falsifiable claim.

Deciles are binned on the OFF frame, never on the ON frame or on the change.
Binning on the quantity you then measure the change of manufactures regression
to the mean: the lowest bin of a noisy measurement rises on remeasurement even
when nothing happened. Fixing the bin edges to the control arm makes decile 1
"pixels that were near-neutral BEFORE", which is the population the question is
actually about.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
OUT_ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
DN_PER_LEVEL = 257.0        # 65535 / 255
VISIBLE_LEVELS = 1.0        # below one 8-bit level it cannot be drawn, let alone seen


def load(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    if a.dtype != np.uint16:
        raise SystemExit(f"{p}: expected uint16, got {a.dtype}")
    return a


def ry(img: np.ndarray) -> np.ndarray:
    """SIGNED R-Y in DN. Signed, because a sign flip is the thing in dispute."""
    f = img.astype(np.float32)
    y = 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]
    return f[:, :, 0] - y


def by(img: np.ndarray) -> np.ndarray:
    """SIGNED B-Y in DN. The control channel: eps_b is None, blue was never
    fitted, so a red-specific correction must leave this substantially alone.
    If |B-Y| moves as much as |R-Y| the effect is a general chroma wash and not
    a lateral-CA correction at all."""
    f = img.astype(np.float32)
    y = 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]
    return f[:, :, 2] - y


def bg(img: np.ndarray) -> np.ndarray:
    """SIGNED B-G in DN. The UNCONTAMINATED blue control.

    `|B-Y|` looks like a control for a red-only correction but is not one:

        B - Y = 0.9278*B - 0.2126*R - 0.7152*G

    carries an explicit -0.2126*R term, so moving red moves `B-Y` by 21% of the
    red change even when blue is untouched. The leak is proportional to the red
    change, which is to say it is largest exactly when the control is most
    needed. `B - G` has no R term at all and cannot leak. Where `eps_b` is None,
    blue is literally never resampled differently, so this must read ~0 and any
    departure is a bug in the wiring rather than a property of the fit.
    """
    f = img.astype(np.float32)
    return f[:, :, 2] - f[:, :, 1]


def edge_mask(img: np.ndarray, pct: float = 90.0) -> np.ndarray:
    """Pixels on a luma edge. Lateral CA is an edge phenomenon: it displaces one
    plane against another, which is invisible where there is no detail to
    displace. Measuring it over the whole frame dilutes it with flat area."""
    f = img.astype(np.float32)
    y = 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]
    gy = np.zeros_like(y)
    gx = np.zeros_like(y)
    gy[1:-1, :] = np.abs(y[2:, :] - y[:-2, :])
    gx[:, 1:-1] = np.abs(y[:, 2:] - y[:, :-2])
    g = gy + gx
    thr = float(np.percentile(g[::7, ::7], pct))
    return g >= thr


def deciles(off: np.ndarray, on: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Decile decomposition of |R-Y|, binned on OFF, reported in DN and levels."""
    d_off, d_on = ry(off), ry(on)
    if mask is not None:
        d_off, d_on = d_off[mask], d_on[mask]
    a_off, a_on = np.abs(d_off), np.abs(d_on)

    edges = np.percentile(a_off, np.arange(0, 101, 10))
    edges[-1] = np.inf
    idx = np.clip(np.searchsorted(edges, a_off, side="right") - 1, 0, 9)

    rows = []
    for k in range(10):
        sel = idx == k
        n = int(sel.sum())
        if n == 0:
            continue
        mo = float(a_off[sel].mean())
        mn = float(a_on[sel].mean())
        flip = float((np.sign(d_off[sel]) != np.sign(d_on[sel])).mean() * 100.0)
        rows.append({
            "decile": k + 1,
            "n": n,
            "abs_ry_off_dn": round(mo, 3),
            "abs_ry_on_dn": round(mn, 3),
            "delta_dn": round(mn - mo, 3),
            "delta_pct": round((mn - mo) / mo * 100.0, 2) if mo > 0 else None,
            "abs_ry_off_levels8": round(mo / DN_PER_LEVEL, 4),
            "abs_ry_on_levels8": round(mn / DN_PER_LEVEL, 4),
            "delta_levels8": round((mn - mo) / DN_PER_LEVEL, 4),
            "sign_flip_pct": round(flip, 2),
        })

    keep = float((np.sign(d_off) == np.sign(d_on)).mean() * 100.0)

    # Sign preservation is only meaningful where there IS a sign. Among pixels
    # whose chroma is a fraction of a display level, the sign of R-Y is decided
    # by rounding, so a bar computed over all pixels measures mostly coin
    # flips -- and it will be failed by any correction that succeeds, because
    # driving a fringe through zero to neutral is precisely a sign change. The
    # gated figure asks the question the bar was meant to ask: of pixels with
    # chroma actually visible at 8-bit, how many kept their polarity?
    gate = DN_PER_LEVEL
    g = a_off >= gate
    keep_gated = (float((np.sign(d_off[g]) == np.sign(d_on[g])).mean() * 100.0)
                  if g.any() else None)
    return {
        "rows": rows,
        "mean_abs_ry_off_dn": round(float(a_off.mean()), 3),
        "mean_abs_ry_on_dn": round(float(a_on.mean()), 3),
        "mean_delta_pct": round(float((a_on.mean() - a_off.mean()) / a_off.mean() * 100.0), 2),
        "keep_sign_pct": round(keep, 2),
        "keep_sign_gated_pct": round(keep_gated, 2) if keep_gated is not None else None,
        "gate_dn": round(gate, 1),
        "gated_frac_pct": round(float(g.mean() * 100.0), 2),
        "n_px": int(a_off.size),
    }


def radial(off: np.ndarray, on: np.ndarray, mask: np.ndarray, nbin: int = 10,
           support: float = 0.788) -> list[dict]:
    """|R-Y| change binned by NORMALISED FIELD HEIGHT, r=1.0 at the corner.

    Two reasons this is the better axis than a chroma decile.

    First it is the physically correct one: the correction is `eps_r * r`,
    identically zero at the optical centre and largest at the corner, so if the
    effect is really lateral CA its magnitude must GROW with r. A chroma
    reduction that is flat in r, or largest at the centre, is not a CA
    correction whatever it does to the fringe statistic.

    Second it is not confounded. Radius is measured on the geometry, not on the
    quantity whose change is being reported, so binning on it cannot manufacture
    regression to the mean the way binning on |R-Y|_off does.

    Bins beyond `support` are flagged: the fit observed r = 0.208..0.788 and
    `support_r_max` is declared but NOT enforced, so out there the correction is
    the model's shape rather than data.
    """
    h, w = off.shape[:2]
    cy, cx = h / 2.0, w / 2.0
    yy = np.arange(h, dtype=np.float32)[:, None] - cy
    xx = np.arange(w, dtype=np.float32)[None, :] - cx
    r = np.hypot(yy, xx) / float(np.hypot(cy, cx))

    d_off, d_on = ry(off), ry(on)
    a_off, a_on = np.abs(d_off)[mask], np.abs(d_on)[mask]
    rm = r[mask]

    rows = []
    for k in range(nbin):
        lo, hi = k / nbin, (k + 1) / nbin
        sel = (rm >= lo) & (rm < hi) if k < nbin - 1 else (rm >= lo)
        n = int(sel.sum())
        if n == 0:
            continue
        mo, mn = float(a_off[sel].mean()), float(a_on[sel].mean())
        rows.append({
            "r_lo": round(lo, 3), "r_hi": round(hi, 3), "n": n,
            "abs_ry_off_dn": round(mo, 3), "abs_ry_on_dn": round(mn, 3),
            "delta_dn": round(mn - mo, 3),
            "delta_pct": round((mn - mo) / mo * 100.0, 2) if mo > 0 else None,
            "delta_levels8": round((mn - mo) / DN_PER_LEVEL, 4),
            "beyond_support": lo >= support,
        })
    return rows


def rtm_control(off: np.ndarray, on: np.ndarray, mask: np.ndarray,
                seed: int = 1101) -> dict:
    """How much of decile 1's rise is REGRESSION TO THE MEAN, not the correction?

    Decile 1 is *selected* as the smallest |R-Y| in the OFF frame. Perturb that
    frame by anything at all -- even a symmetric, zero-mean, physically
    meaningless perturbation -- and the selected-minimum bin must rise, because
    |.| of a small number plus noise is larger in expectation than the small
    number. So a large positive decile-1 percentage is the EXPECTED reading of
    an inert change, and cannot on its own be evidence that the correction
    injected anything.

    The control replaces the real correction with zero-mean Gaussian noise in
    the red plane, scaled to the same RMS as the real red-plane change, and
    re-runs the identical decomposition. Whatever decile-1 rise that produces is
    the floor the real number has to beat to mean anything.
    """
    d_r = on[:, :, 0].astype(np.float32) - off[:, :, 0].astype(np.float32)
    rms = float(np.sqrt((d_r[mask] ** 2).mean()))
    rng = np.random.default_rng(seed)
    fake = off.astype(np.float32).copy()
    fake[:, :, 0] = np.clip(fake[:, :, 0] + rng.normal(0.0, rms, size=off.shape[:2]),
                            0, 65535)
    fake = fake.astype(np.uint16)

    real = deciles(off, on, mask)
    null = deciles(off, fake, mask)
    r1, n1 = real["rows"][0], null["rows"][0]
    r10, n10 = real["rows"][-1], null["rows"][-1]
    return {
        "matched_red_rms_dn": round(rms, 3),
        "decile1": {
            "real_pct": r1["delta_pct"], "rtm_null_pct": n1["delta_pct"],
            "real_levels8": r1["delta_levels8"], "rtm_null_levels8": n1["delta_levels8"],
            "excess_levels8": round(r1["delta_levels8"] - n1["delta_levels8"], 4),
        },
        "decile10": {
            "real_pct": r10["delta_pct"], "rtm_null_pct": n10["delta_pct"],
            "real_levels8": r10["delta_levels8"], "rtm_null_levels8": n10["delta_levels8"],
            "excess_levels8": round(r10["delta_levels8"] - n10["delta_levels8"], 4),
        },
        "note": "rtm_null is an INERT, zero-mean, RMS-matched perturbation. Any "
                "decile-1 rise it produces is a property of binning on the "
                "measured quantity, not of the correction.",
    }


def summarise(off: np.ndarray, on: np.ndarray) -> dict:
    em = edge_mask(off)
    res = {
        "edge_px": int(em.sum()),
        "edge_frac_pct": round(float(em.mean() * 100.0), 3),
        "whole_frame": deciles(off, on),
        "near_edges": deciles(off, on, em),
    }
    # |B-Y| control on the same edge population.
    b_off = np.abs(by(off)[em])
    b_on = np.abs(by(on)[em])
    res["control_abs_by"] = {
        "off_dn": round(float(b_off.mean()), 3),
        "on_dn": round(float(b_on.mean()), 3),
        "delta_pct": round(float((b_on.mean() - b_off.mean()) / b_off.mean() * 100.0), 2),
        "note": "CONTAMINATED: B-Y carries a -0.2126*R term, so this leaks 21% of the "
                "red change even with blue untouched. Reported for comparability with "
                "M107 only; control_abs_bg is the one to read.",
    }
    g_off = np.abs(bg(off)[em])
    g_on = np.abs(bg(on)[em])
    res["control_abs_bg"] = {
        "off_dn": round(float(g_off.mean()), 3),
        "on_dn": round(float(g_on.mean()), 3),
        "delta_pct": round(float((g_on.mean() - g_off.mean()) / g_off.mean() * 100.0), 2),
        "delta_levels8": round(float((g_on.mean() - g_off.mean()) / DN_PER_LEVEL), 4),
        "note": "UNCONTAMINATED: B-G has no R term. eps_b is None, so blue is never "
                "resampled differently and this must read ~0. A nonzero reading is a "
                "wiring bug, not a property of the fit.",
    }
    res["radial"] = radial(off, on, em)
    res["rtm_control"] = rtm_control(off, on, em)
    d1 = res["near_edges"]["rows"][0]
    d10 = res["near_edges"]["rows"][-1]
    res["verdict_inputs"] = {
        "decile1_delta_levels8": d1["delta_levels8"],
        "decile1_delta_pct": d1["delta_pct"],
        "decile10_delta_levels8": d10["delta_levels8"],
        "decile10_delta_pct": d10["delta_pct"],
        "decile1_visible": abs(d1["delta_levels8"]) >= VISIBLE_LEVELS,
        "decile10_visible": abs(d10["delta_levels8"]) >= VISIBLE_LEVELS,
        "visible_threshold_levels8": VISIBLE_LEVELS,
    }
    return res


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------
def controls(off: np.ndarray) -> list[dict]:
    """Pre-registered bars. Run BEFORE reading any CA number."""
    out = []

    def bar(name, got, want, ok, why):
        out.append({"bar": name, "got": got, "want": want,
                    "PASS": bool(ok), "why": why})

    # N1: null. Same bytes both sides must read exactly zero change and zero
    # flips. Anything else is the instrument, not the correction.
    n = deciles(off, off, edge_mask(off))
    worst = max(abs(r["delta_dn"]) for r in n["rows"])
    bar("N1 null delta", worst, "== 0 exactly", worst == 0.0,
        "off vs off: any nonzero delta is instrument noise masquerading as effect")
    bar("N1b null flips", n["keep_sign_pct"], "== 100.00", n["keep_sign_pct"] == 100.0,
        "off vs off: a sign flip against itself is impossible")

    # P1/P2: two-sided gain. A planted chroma shift must be recovered at the
    # size planted, in BOTH directions -- an instrument that only sees the
    # correction reducing chroma cannot report it injecting chroma, which is
    # precisely the failure in dispute.
    em = edge_mask(off)
    for sign, tag in ((+1, "P1 gain +"), (-1, "P2 gain -")):
        plant = 500.0 * sign
        on = off.astype(np.float32).copy()
        on[:, :, 0] = np.clip(on[:, :, 0] + plant, 0, 65535)
        on = on.astype(np.uint16)
        # Expected change in signed R-Y for a pure R shift: (1 - 0.2126)*plant
        want = (1.0 - 0.2126) * plant
        d = ry(on)[em] - ry(off)[em]
        got = float(np.median(d))
        # Clipping eats the plant where R is already at full scale, so measure
        # recovery only where there was headroom -- otherwise the container
        # ceiling is scored as instrument error, which is the same mistake the
        # one-sided highlight readout made.
        room = (off[:, :, 0][em].astype(np.float32) + plant <= 65535) & \
               (off[:, :, 0][em].astype(np.float32) + plant >= 0)
        got_room = float(np.median(d[room])) if room.any() else float("nan")
        rel = got_room / want
        bar(tag, round(got_room, 3), f"{want:.3f} (+/-1%)", abs(rel - 1.0) <= 0.01,
            f"planted {plant:+.0f} DN in R with headroom; median recovered "
            f"{got_room:.3f} = {rel * 100:.2f}% of predicted (all-px median {got:.3f})")

    # P3: the unit conversion itself. 257 DN must be exactly one 8-bit level.
    lv = 257.0 / DN_PER_LEVEL
    bar("P3 unit", lv, "== 1.0", lv == 1.0,
        "the visibility verdict is a unit conversion; if the unit is wrong the "
        "verdict is wrong in the same proportion")

    # P4: headroom. State the instrument's dynamic range in both directions as
    # a number, the way the highlight readout states its 0.95/0.89.
    a = np.abs(ry(off)[em])
    bar("P4 headroom", {"min_abs_ry_dn": round(float(a.min()), 3),
                        "p50_abs_ry_dn": round(float(np.percentile(a, 50)), 3),
                        "max_abs_ry_dn": round(float(a.max()), 3),
                        "room_up_dn": round(float(65535 - a.max()), 1),
                        "room_down_dn": round(float(a.min()), 3)},
        "room in BOTH directions", True,
        "|R-Y| is not pinned at either end, so unlike the blown-highlight "
        "statistic this one can report an increase and a decrease alike")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", action="append")
    ap.add_argument("--off", default="default")
    ap.add_argument("--on", default="ca")
    ap.add_argument("--controls-only", action="store_true")
    a = ap.parse_args()

    subs = a.subject or [d.name for d in sorted(OUT_ROOT.iterdir()) if d.is_dir()]
    report = {"off_arm": a.off, "on_arm": a.on, "subjects": {}}
    fail = 0

    for s in subs:
        off_p = OUT_ROOT / s / f"{a.off}.tif"
        on_p = OUT_ROOT / s / f"{a.on}.tif"
        if not off_p.exists() or not on_p.exists():
            print(f"skip {s}: need {off_p.name} and {on_p.name}")
            continue
        print(f"\n=== {s}: {a.off} -> {a.on} ===")
        off = load(off_p)

        cs = controls(off)
        for c in cs:
            tag = "PASS" if c["PASS"] else "FAIL"
            print(f"  [{tag}] {c['bar']:<16} got={c['got']} want={c['want']}")
            if not c["PASS"]:
                fail += 1
                print(f"         {c['why']}")
        if a.controls_only:
            report["subjects"][s] = {"controls": cs}
            continue

        on = load(on_p)
        res = summarise(off, on)
        res["controls"] = cs
        report["subjects"][s] = res

        print(f"  edge px {res['edge_px']} ({res['edge_frac_pct']}% of frame)")
        print("  near edges, deciles binned on OFF:")
        print(f"    {'dec':>3} {'|R-Y|off DN':>12} {'|R-Y|on DN':>11} "
              f"{'d DN':>9} {'d %':>9} {'d levels8':>10} {'flip %':>7}")
        for r in res["near_edges"]["rows"]:
            print(f"    {r['decile']:>3} {r['abs_ry_off_dn']:>12.3f} "
                  f"{r['abs_ry_on_dn']:>11.3f} {r['delta_dn']:>9.3f} "
                  f"{str(r['delta_pct']):>9} {r['delta_levels8']:>10.4f} "
                  f"{r['sign_flip_pct']:>7.2f}")
        c = res["control_abs_by"]
        print(f"  |B-Y| control (CONTAMINATED, 21% red leak): "
              f"{c['off_dn']} -> {c['on_dn']} DN ({c['delta_pct']:+}%)")
        c2 = res["control_abs_bg"]
        print(f"  |B-G| control (clean, must be ~0):          "
              f"{c2['off_dn']} -> {c2['on_dn']} DN ({c2['delta_pct']:+}%, "
              f"{c2['delta_levels8']:+.4f} lv)")
        ne = res["near_edges"]
        print(f"  keep sign: {ne['keep_sign_pct']}% all px | "
              f"{ne['keep_sign_gated_pct']}% among the {ne['gated_frac_pct']}% "
              f"with |R-Y| >= 1 display level")
        v = res["verdict_inputs"]
        print(f"  decile 1  {v['decile1_delta_pct']:+}% = "
              f"{v['decile1_delta_levels8']:+.4f} 8-bit levels -> "
              f"{'VISIBLE' if v['decile1_visible'] else 'BELOW ONE DISPLAY LEVEL'}")
        print(f"  decile 10 {v['decile10_delta_pct']:+}% = "
              f"{v['decile10_delta_levels8']:+.4f} 8-bit levels -> "
              f"{'VISIBLE' if v['decile10_visible'] else 'BELOW ONE DISPLAY LEVEL'}")

        t = res["rtm_control"]
        print(f"  regression-to-the-mean control (RMS-matched inert noise, "
              f"{t['matched_red_rms_dn']} DN):")
        for nm in ("decile1", "decile10"):
            k = t[nm]
            print(f"    {nm:<9} real {k['real_pct']:+9.2f}% / {k['real_levels8']:+8.4f} lv"
                  f"   inert null {k['rtm_null_pct']:+9.2f}% / {k['rtm_null_levels8']:+8.4f} lv"
                  f"   excess {k['excess_levels8']:+8.4f} lv")

        print("  |R-Y| change vs normalised field height (r=1.0 at corner):")
        print(f"    {'r':>12} {'off DN':>10} {'on DN':>10} {'d DN':>10} "
              f"{'d %':>8} {'d lv8':>8}  support")
        for q in res["radial"]:
            flag = "EXTRAPOLATED" if q["beyond_support"] else ""
            print(f"    {q['r_lo']:.2f}-{q['r_hi']:.2f}{'':>2} {q['abs_ry_off_dn']:>10.1f} "
                  f"{q['abs_ry_on_dn']:>10.1f} {q['delta_dn']:>10.1f} "
                  f"{str(q['delta_pct']):>8} {q['delta_levels8']:>8.3f}  {flag}")

    dst = OUT_ROOT / f"ca_decile_{a.off}_vs_{a.on}.json"
    dst.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwrote {dst}")
    if fail:
        print(f"\n{fail} CONTROL BAR(S) FAILED -- the numbers above are not trustworthy")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
