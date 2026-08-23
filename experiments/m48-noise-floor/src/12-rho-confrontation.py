r"""M48 script 12 -- confront the measured dark rho with M46's fitted 0.3094.

Consumes script 09's per-ISO decomposition and answers the three questions the
brief asks, arithmetically rather than rhetorically.

The two rho's are fractions of different denominators, and this script makes
that concrete rather than asserting it. Writing D for the dark-signal
non-uniformity (fixed offset spread, in DN), P for photo-response
non-uniformity (a fractional gain spread), R for the temporal read sigma and S
for the black-subtracted signal in DN at gain g:

    dark frame          var = R^2 + D^2                 (no photons at all)
    illuminated frame   var = g*S + R^2 + D^2 + (P*S)^2

    rho_dark  = D^2 / (R^2 + D^2)
    rho_M46   = (D^2 + (P*S)^2) / (g*S + R^2 + D^2 + (P*S)^2)

They coincide only as S -> 0. Darks cannot see P at all, because P multiplies a
signal that is not there. So the question "do 0.0638 and 0.3094 agree" is not
well posed until S is fixed, and this script evaluates rho_dark's own
contribution at the signal levels the corpus actually contains (measured by
script 10) and solves for the P that M46's number would require.
"""

import json
import os

import numpy as np

GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "rho-confrontation.json")

# Median black-subtracted green luma of the real corpus stacks, MEASURED by
# script 10 on the frames themselves.
CORPUS_SIGNAL_DN = {500.0: 271.0, 1000.0: 191.5, 50.0: 3253.5}
M46_RHO = 0.3094
M46_ISO = 500.0


def gain(iso):
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def main():
    with open(os.path.join(DATA, "fpn-rho.json"), encoding="utf-8") as fh:
        rho_data = json.load(fh)

    rows = []
    for s in rho_data["sets"]:
        iso = float(s["iso"])
        pl = s["planes"]
        # Average the two greens: green luma is what the merge gates on.
        d2 = np.mean([pl["G1"]["v_fpn_cross"], pl["G2"]["v_fpn_cross"]])
        r2 = np.mean([pl["G1"]["v_temporal"], pl["G2"]["v_temporal"]])
        rows.append(
            {
                "iso": iso,
                "dsnu_dn": float(np.sqrt(max(d2, 0.0))),
                "read_dn": float(np.sqrt(r2)),
                "rho_dark": float(d2 / (d2 + r2)),
                "rho_dark_G1": pl["G1"]["rho"],
                "rho_dark_G2": pl["G2"]["rho"],
                "rho_censored_G1": pl["G1"]["rho_censored"],
                "sem": pl["G1"]["rho_tile_sem"],
                "plane_spread": abs(pl["G1"]["rho"] - pl["G2"]["rho"]),
            }
        )
    rows.sort(key=lambda r: r["iso"])

    # --- Q2: is rho constant across ISO? Is the DSNU itself constant? ---
    rho = np.array([r["rho_dark"] for r in rows])
    dsnu = np.array([r["dsnu_dn"] for r in rows])
    sem = np.array([r["sem"] for r in rows])
    rho_spread = float(rho.max() / rho.min())
    # Weighted chi-square against a single shared rho, and against a single
    # shared DSNU in DN. Whichever is constant is the real invariant.
    w = 1.0 / sem**2
    rho_bar = float((w * rho).sum() / w.sum())
    chi2_rho = float((w * (rho - rho_bar) ** 2).sum())
    # For DSNU the per-set precision is not directly measured; use the spread
    # between the two greens as an independent-plane error proxy.
    dsnu_bar = float(dsnu.mean())
    dsnu_cv = float(dsnu.std(ddof=1) / dsnu_bar)

    # --- Q3/Q4: what does the dark rho contribute on a LIT frame? ---
    transfer = []
    for r in rows:
        iso = r["iso"]
        if iso not in CORPUS_SIGNAL_DN:
            continue
        g = gain(iso)
        s_dn = CORPUS_SIGNAL_DN[iso]
        d2, r2 = r["dsnu_dn"] ** 2, r["read_dn"] ** 2
        shot = g * s_dn
        rho_lit_dsnu_only = d2 / (d2 + r2 + shot)
        # Signal at which the dark rho falls to half its S=0 value.
        s_half = (d2 + r2) / g
        transfer.append(
            {
                "iso": iso,
                "corpus_median_signal_dn": s_dn,
                "rho_dark_at_zero_signal": r["rho_dark"],
                "rho_from_dsnu_at_corpus_signal": float(rho_lit_dsnu_only),
                "attenuation_factor": float(r["rho_dark"] / rho_lit_dsnu_only),
                "signal_dn_where_rho_halves": float(s_half),
            }
        )

    # --- Q3: solve for the PRNU that M46's number would require ---
    row500 = next(r for r in rows if r["iso"] == M46_ISO)
    g = gain(M46_ISO)
    s_dn = CORPUS_SIGNAL_DN[M46_ISO]
    d2, r2 = row500["dsnu_dn"] ** 2, row500["read_dn"] ** 2
    shot = g * s_dn
    # rho = (d2 + p2s2)/(shot + r2 + d2 + p2s2)  ->  solve for p2s2
    k = M46_RHO / (1.0 - M46_RHO)
    p2s2 = k * (shot + r2) - d2 * 1.0
    p2s2 = max(p2s2, 0.0)
    fpn_tot = d2 + p2s2
    confront = {
        "m46_rho": M46_RHO,
        "m46_iso": M46_ISO,
        "assumed_signal_dn": s_dn,
        "measured_rho_dark_same_iso": row500["rho_dark"],
        "naive_ratio": M46_RHO / row500["rho_dark"],
        "dsnu_variance_dn2": d2,
        "implied_total_fpn_variance_dn2": fpn_tot,
        "dsnu_share_of_m46_fpn": float(d2 / fpn_tot) if fpn_tot else None,
        "implied_prnu_sd_dn": float(np.sqrt(p2s2)),
        "implied_prnu_fraction_of_signal": float(np.sqrt(p2s2) / s_dn),
        "dsnu_share_of_lit_frame_variance": float(d2 / (shot + r2 + d2)),
    }

    payload = {
        "_meta": {
            "script": "12-rho-confrontation.py",
            "question": "SYNTHESIS 142",
            "rho_dark_definition": "D^2/(R^2+D^2) on a dark frame: the fraction "
            "of a DARK frame's variance that is fixed-pattern. Contains no "
            "photon shot noise and no PRNU.",
            "m46_rho_definition": "fraction of an ILLUMINATED flat ROI's "
            "single-frame variance that is common-mode, solved from "
            "FRC_flat/(1-FRC_flat)/n_eff. Contains PRNU and any residual "
            "scene structure; darks contain neither.",
        },
        "per_iso": rows,
        "constancy": {
            "rho_min": float(rho.min()),
            "rho_max": float(rho.max()),
            "rho_max_over_min": rho_spread,
            "rho_weighted_mean": rho_bar,
            "chi2_vs_single_rho": chi2_rho,
            "dof": len(rho) - 1,
            "dsnu_mean_dn": dsnu_bar,
            "dsnu_cv": dsnu_cv,
            "dsnu_min_dn": float(dsnu.min()),
            "dsnu_max_dn": float(dsnu.max()),
            "dsnu_max_over_min": float(dsnu.max() / dsnu.min()),
        },
        "transfer_to_lit_frames": transfer,
        "confrontation": confront,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print("ISO   DSNU_DN  read_DN   rho_dark    +-SEM    rho_cens  G1-G2")
    for r in rows:
        print(
            f"{r['iso']:5.0f}  {r['dsnu_dn']:7.4f}  {r['read_dn']:7.4f}  "
            f"{r['rho_dark']:.5f}  {r['sem']:.5f}  {r['rho_censored_G1']:.5f}  "
            f"{r['plane_spread']:.5f}"
        )
    print(
        f"\nrho spans {rho.min():.4f}..{rho.max():.4f} = {rho_spread:.2f}x; "
        f"chi2 vs a single rho = {chi2_rho:.0f} on {len(rho)-1} dof"
    )
    print(
        f"DSNU spans {dsnu.min():.4f}..{dsnu.max():.4f} DN "
        f"= {dsnu.max()/dsnu.min():.2f}x, CV {dsnu_cv*100:.1f}%"
    )
    print("\nTransfer to lit frames:")
    for t in transfer:
        print(
            f"  ISO {t['iso']:5.0f}  S={t['corpus_median_signal_dn']:7.1f} DN  "
            f"rho {t['rho_dark_at_zero_signal']:.5f} -> "
            f"{t['rho_from_dsnu_at_corpus_signal']:.6f}  "
            f"({t['attenuation_factor']:.0f}x weaker); halves at "
            f"S={t['signal_dn_where_rho_halves']:.2f} DN"
        )
    print("\nConfrontation with M46 at ISO 500:")
    for k2, v in confront.items():
        print(f"  {k2}: {v}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
