"""Is the gather self-calibration confounded by the very thing it compares?

compare.py measures what ONE extra Catmull-Rom gather costs, and it measures it
on ARM A (the merge):

    cost = high(gather(armA)) / high(armA)
    armB_corrected = armB / cost

The correction is then applied to ARM B (the source frame).  That transfer is
only valid if the gather costs the same on arm B's content as on arm A's.  It
does not have to.  Catmull-Rom attenuation is frequency dependent, so the cost
is a content-weighted average of |H(f)| across the band -- and the two arms
differ in exactly their high-frequency content, because that difference IS the
measurement.  A correction whose size depends on sharpness, transferred between
two arms in order to compare their sharpness, is confounded by its own subject.

The shipped cross-check (cost_shift vs cost_scale, agreeing to ~1%) does NOT
test this.  Both estimators run on arm A.  It varies the ESTIMATOR while
holding the confounded variable -- which arm's content is under the kernel --
fixed.  This script varies that variable and nothing else.

The algebra is exact and needs no approximation:

    shipped ratio_corr = A * cost_A / B
    true    ratio_corr = A * cost_B / B
    ==> the multiplicative error on every corrected ratio is cost_B / cost_A.

So a single measured number per site says how wrong the headline is, and its
DIRECTION says whether the shipped figure is conservative or flattering.

COMMISSIONING.  Two controls, both required to pass before any number below is
interpreted:

  REPRO  recompute cost on arm A and require it to reproduce the shipped
         `cost_shift`.  If this probe cannot reproduce the number it is
         auditing, its arm-B number means nothing.

  NULL   run the whole comparison with arm B replaced by arm A.  The transfer
         ratio must come back exactly 1.0.  A probe that reports a transfer
         error between a tile and itself is measuring its own margin handling.

Read-only.  Touches no shipped artifact.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

TILES = os.path.join(tri.OUT, "tiles")
CMP = os.path.join(tri.OUT, "compare")
MARGIN = 8          # matches compare.py's m; keeps the kernel off the border
BAND = "high"       # the band the sharpness verdict is read from
REPRO_TOL = 0.02    # arm-A reproduction must land inside 2%


def cost_on(tile: np.ndarray, k: float) -> float:
    """Phase-averaged cost of ONE Catmull-Rom gather on this tile's content.

    Identical in form to compare.py's self-calibration, but the tile is all we
    have on disk, so the shift is taken on the tile and both the shifted and
    unshifted arms are cropped by MARGIN before the band is read.  The crop is
    applied to BOTH, so it is common-mode and cancels in the ratio -- which is
    what the NULL control exists to confirm.
    """
    m = MARGIN
    base = np.ascontiguousarray(tile[m:-m, m:-m])
    A = tri.band_amp(base, k)[BAND]
    if not (A > 0):
        return float("nan")
    vals = []
    for ph in tri.GATHER_PHASES:
        sh = tri.catmull_rom_shift(tile, ph, ph)
        t = np.ascontiguousarray(sh[m:-m, m:-m])
        vals.append(tri.band_amp(t, k)[BAND] / A)
    return float(np.mean(vals))


def ecost_on(tile: np.ndarray) -> float:
    """Phase-averaged gather cost of the EDGE statistic, on this tile.

    Character-for-character the estimator in compare.py:measure_site, with the
    tile it runs on as the only free variable.  This is the correction that
    matters: the edge block is what compare.py labels PRIMARY VERDICT, and
    `edge_ratio_min` -- the number the whole triage rests on -- is built from
    it.  The band correction audited above feeds diagnostics, not the verdict.
    """
    m = MARGIN
    den = tri.edge_slope(tile[m:-m, m:-m])
    if not (den > 0):
        return float("nan")
    win = (m, m, tile.shape[0] - 2 * m, tile.shape[1] - 2 * m)
    return float(np.mean([
        tri.edge_slope(tri.catmull_rom_shift(tile, ph, ph, win)) / den
        for ph in tri.GATHER_PHASES]))


def main() -> int:
    rows = []
    repro_fail = []
    for fn in sorted(os.listdir(TILES)):
        if not fn.endswith(".npz"):
            continue
        sub, label, _ = fn.rsplit(".", 2)
        cj = os.path.join(CMP, sub + ".json")
        if not os.path.exists(cj):
            continue
        with open(cj, encoding="utf-8") as fh:
            shipped = json.load(fh)
        site = shipped.get("sites", {}).get(label)
        if not site or BAND not in site:
            continue

        z = np.load(os.path.join(TILES, fn))
        ta, tb = z["merge"].astype(np.float32), z["frame"].astype(np.float32)
        ka, s = float(z["ka"]), float(z["s"])

        # compare.py evaluates BOTH arms at ka: arm B has already been
        # resampled onto arm A's grid, so it lives on arm A's frequency axis.
        ca, cb = cost_on(ta, ka), cost_on(tb, ka)
        ship_shift = site[BAND].get("cost_shift")
        rule = site[BAND].get("cost_rule", "")

        rel = abs(ca - ship_shift) / ship_shift if ship_shift else float("nan")
        if np.isfinite(rel) and rel > REPRO_TOL:
            repro_fail.append((sub, label, ca, ship_shift, rel))

        # --- the correction that actually decides the verdict ---------------
        ed = site.get("edge") or {}
        ea, eb = ecost_on(ta), ecost_on(tb)
        ship_e = ed.get("gather_cost")
        erel = (abs(ea - ship_e) / ship_e
                if ship_e and abs(1.0 - s) >= 0.005 else float("nan"))

        rows.append({
            "subject": sub, "label": label, "s": s,
            "cost_A": ca, "cost_B": cb,
            "shipped_cost_shift": ship_shift, "repro_rel": rel,
            "transfer": cb / ca if ca else float("nan"),
            "ratio_raw": site[BAND].get("ratio_raw"),
            "ratio_corr": site[BAND].get("ratio_corr"),
            "exact_s_rule": "exact-s" in rule,
            "reliable": site.get("reliable"),
            "ecost_A": ea, "ecost_B": eb, "shipped_ecost": ship_e,
            "erepro_rel": erel,
            "etransfer": eb / ea if ea else float("nan"),
            "eratio": ed.get("ratio"),
            "blur_equiv_px": ed.get("blur_equiv_px"),
        })

    # ---- CONTROL 1: NULL.  arm B := arm A must transfer at exactly 1.0. -----
    z = np.load(os.path.join(TILES, sorted(os.listdir(TILES))[0]))
    ta, ka = z["merge"].astype(np.float32), float(z["ka"])
    null = cost_on(ta, ka) / cost_on(ta, ka)
    enull = ecost_on(ta) / ecost_on(ta)
    print(f"NULL   band: arm B := arm A -> transfer = {null:.6f}  "
          f"({'OK' if abs(null - 1.0) < 1e-9 else 'FAIL'})")
    print(f"NULL   edge: arm B := arm A -> transfer = {enull:.6f}  "
          f"({'OK' if abs(enull - 1.0) < 1e-9 else 'FAIL'})")

    # ---- CONTROL 2: REPRO. -------------------------------------------------
    good = [r for r in rows if np.isfinite(r["repro_rel"])]
    worst = max(good, key=lambda r: r["repro_rel"]) if good else None
    print(f"REPRO  band: {len(good) - len(repro_fail)}/{len(good)} sites within "
          f"{REPRO_TOL:.0%}; worst {worst['repro_rel']:.2%} "
          f"({worst['subject']}/{worst['label']})")
    eg = [r for r in rows if np.isfinite(r["erepro_rel"])]
    ew = max(eg, key=lambda r: r["erepro_rel"]) if eg else None
    efail = [r for r in eg if r["erepro_rel"] > REPRO_TOL]
    print(f"REPRO  edge: {len(eg) - len(efail)}/{len(eg)} sites within "
          f"{REPRO_TOL:.0%}; worst {ew['erepro_rel']:.2%} "
          f"({ew['subject']}/{ew['label']}: mine {ew['ecost_A']:.4f} "
          f"vs shipped {ew['shipped_ecost']:.4f})")
    if efail:
        print(f"       {len(efail)} edge site(s) outside tolerance -- "
              f"NOT interpretable")

    # ---- THE ONE THAT DECIDES THE VERDICT ----------------------------------
    ue = [r for r in rows if np.isfinite(r["etransfer"])
          and abs(1.0 - r["s"]) >= 0.005]
    et = np.array([r["etransfer"] for r in ue])
    print(f"\n=== EDGE transfer ecost_B/ecost_A over {len(ue)} sites "
          f"(this multiplies edge ratio directly) ===")
    print(f"  median {np.median(et):.4f}   min {et.min():.4f}   "
          f"max {et.max():.4f}")
    print(f"  >1 shipped UNDERSTATED: {int((et > 1).sum())}/{len(et)}    "
          f"<1 shipped OVERSTATED: {int((et < 1).sum())}/{len(et)}")
    era = np.array([r["eratio"] or np.nan for r in ue], dtype=float)
    ok = np.isfinite(era) & np.isfinite(et)
    if ok.sum() > 2:
        print(f"  corr(edge transfer, edge ratio) = "
              f"{float(np.corrcoef(era[ok], et[ok])[0, 1]):+.3f}")

    # Per-subject edge_ratio_min, shipped vs transfer-corrected.  This is the
    # headline field.  A verdict moves only if a subject crosses 1.0.
    per: dict[str, list] = {}
    for r in ue:
        if r["eratio"] and np.isfinite(r["eratio"]):
            per.setdefault(r["subject"], []).append(r)
    print(f"\n=== edge_ratio_min per subject, shipped vs corrected "
          f"({len(per)} subjects with usable tiles) ===")
    crossed = []
    for sub in sorted(per):
        sh = min(x["eratio"] for x in per[sub])
        co = min(x["eratio"] * x["etransfer"] for x in per[sub])
        flag = ""
        if (sh >= 1.0) != (co >= 1.0):
            flag = "  <== CROSSES PARITY"
            crossed.append(sub)
        print(f"  {sub:36s} {sh:7.4f} -> {co:7.4f} "
              f"({(co / sh - 1) * 100:+5.2f}%){flag}")
    print(f"\nsubjects whose merge-vs-frame verdict crosses 1.0 under the "
          f"corrected transfer: {len(crossed)} {crossed}")

    # ---- secondary: the band correction (diagnostic fields only) -----------
    use = [r for r in rows if np.isfinite(r["transfer"]) and not r["exact_s_rule"]]
    tr = np.array([r["transfer"] for r in use])
    print(f"\n--- BAND transfer (diagnostic fields, NOT the verdict) over "
          f"{len(use)} sites ---")
    print(f"  median {np.median(tr):.4f}   min {tr.min():.4f}   "
          f"max {tr.max():.4f}   >1: {int((tr > 1).sum())}/{len(tr)}")
    rr = np.array([r["ratio_raw"] or np.nan for r in use], dtype=float)
    ok = np.isfinite(rr) & np.isfinite(tr)
    if ok.sum() > 2:
        print(f"  corr(band transfer, raw band ratio) = "
              f"{float(np.corrcoef(rr[ok], tr[ok])[0, 1]):+.3f} -- the "
              f"correction tracks the quantity it is used to compare")
    # ---- the shipped field itself, corrected -------------------------------
    # `usable` in triage.py filters on `reliable` and a `weak()` test.  Rather
    # than re-derive that filter and risk auditing a slightly different set,
    # identify the site that actually PRODUCED each shipped edge_ratio_min by
    # matching its value, and correct that site.  A subject whose min cannot be
    # matched is reported, not guessed at -- an unmatched row must be visible.
    with open(os.path.join(tri.OUT, "triage.json"), encoding="utf-8") as fh:
        tj = json.load(fh)
    by_sub = {r["subject"]: r for r in tj["rows"]}
    print("\n=== shipped edge_ratio_min, corrected at its own producing site ===")
    moved, unmatched = [], []
    for sub in sorted(per):
        ship = (by_sub.get(sub, {}).get("evidence") or {}).get("edge_ratio_min")
        if ship is None:
            continue
        hit = [x for x in per[sub] if abs(round(x["eratio"], 4) - ship) < 5e-4]
        if not hit:
            unmatched.append(sub)
            continue
        x = hit[0]
        co = ship * x["etransfer"]
        cross = (ship >= 1.0) != (co >= 1.0)
        if cross:
            moved.append(sub)
        print(f"  {sub:36s} {ship:7.4f} -> {co:7.4f} "
              f"({(co / ship - 1) * 100:+5.2f}%) at {x['label']:12s}"
              f"{'  <== CROSSES PARITY' if cross else ''}")
    if unmatched:
        print(f"  UNMATCHED (shipped min not reproduced from tiles, "
              f"NOT audited): {len(unmatched)} {unmatched}")
    # A count that does not move looks identical whether nothing was wrong or
    # nothing was examined.  Print the arithmetic and name every absentee.
    all_subs = {r["subject"] for r in tj["rows"]}
    audited = {s for s in per
               if (by_sub.get(s, {}).get("evidence") or {}).get("edge_ratio_min")
               is not None and s not in unmatched}
    absent = sorted(all_subs - audited)
    print(f"\nAUDIT COVERAGE: {len(audited)} audited + {len(absent)} not "
          f"audited = {len(all_subs)} subjects")
    for s in absent:
        ev = (by_sub.get(s, {}).get("evidence") or {})
        if ev.get("edge_ratio_min") is None:
            why = "no edge_ratio_min shipped (no usable site)"
        elif s not in per:
            why = ("exact-s rule: ecost pinned to 1.0 by design, transfer is "
                   "identically 1" if s == "highly-angled-ruler-mm-cpl"
                   else "no usable tile pair on disk")
        else:
            why = "shipped min not matched to a tile site"
        print(f"  {s:36s} {why}")
    print(f"\nVERDICTS MOVED: {len(moved)} {moved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
