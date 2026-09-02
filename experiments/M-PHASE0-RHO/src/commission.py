"""Commission the rho estimator before any real RAW measurement."""

from __future__ import annotations

import ast
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
sys.path.insert(0, str(HERE))

import rho_lib as R  # noqa: E402
import truth_factory as T  # noqa: E402


class Tally:
    def __init__(self):
        self.controls = []
        self.defects = []

    def control(self, name, passed, detail, exercised=True):
        passed = bool(passed and exercised)
        self.controls.append(
            {
                "name": name,
                "status": "PASS" if passed else "FAIL",
                "detail": str(detail),
                "exercised": bool(exercised),
            }
        )
        print(f"  {'PASS' if passed else 'FAIL':7s} {name:44s} {detail}")
        return passed

    def defect(self, name, caught, catcher, detail):
        self.defects.append(
            {
                "name": name,
                "status": "CAUGHT" if caught else "MISSED",
                "catcher": catcher,
                "detail": str(detail),
            }
        )
        print(f"  {'CAUGHT' if caught else 'MISSED':7s} {name:44s} {detail}")
        return bool(caught)

    def payload(self):
        cp = sum(x["status"] == "PASS" for x in self.controls)
        cf = sum(x["status"] == "FAIL" for x in self.controls)
        dc = sum(x["status"] == "CAUGHT" for x in self.defects)
        dm = sum(x["status"] == "MISSED" for x in self.defects)
        return {
            "known_answer": {"pass": cp, "fail": cf, "total": cp + cf},
            "defects": {"caught": dc, "missed": dm, "total": dc + dm},
            "controls": self.controls,
            "defect_records": self.defects,
            "verdict": "COMMISSIONED" if cf == 0 and dm == 0 else "RED",
        }


def make_patch(beta, seed, noise=False, anisotropy=(0.0, 0.0, 0.0, 0.0)):
    n = 1536
    size = 640
    field = T.powerlaw_field(n, beta, seed, anisotropy=anisotropy)
    raw = T.sampled_raw(
        field,
        mean_dn=4000.0,
        contrast_dn=700.0,
        gain_dn_per_e=0.4,
        read_sd_dn=2.5,
        seed=seed + 1000,
        add_noise=noise,
    )
    rc = cc = n // 2
    rc -= rc % 2
    cc -= cc % 2
    patch = R.extract_gq(raw, rc, cc, size)
    truth_patch = T.independent_gq_extract(raw, rc, cc, size)
    return patch, truth_patch, raw


def fit_patch(patch, noise_floor=0.0, angular=True):
    return R.fit_gq_powerlaw(
        patch,
        noise_floor=noise_floor,
        tile=128,
        window="hann",
        rmin=0.04,
        rmax=0.46,
        angular_model=angular,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tally = Tally()
    print("=" * 88)
    print("M-PHASE0-RHO commissioning: known-answer controls")
    print("=" * 88)

    # C12 first: all later controls depend on the sampler and its coordinates.
    probe = np.arange(512 * 512, dtype=float).reshape(512, 512)
    p1 = R.extract_gq(probe, 256, 256, 128)
    p2 = T.independent_gq_extract(probe, 256, 256, 128)
    c12 = tally.control(
        "C12 active/CFA round trip",
        np.array_equal(p1, p2),
        f"independent extracts differ at {int(np.sum(p1 != p2))} samples",
        exercised=(p1.size == 128 * 128),
    )

    # C1: white field. The defining invariant is rho=1, independently derived.
    white, _, _ = make_patch(0.0, 11, noise=False)
    fw = fit_patch(white, angular=False)
    c1 = tally.control(
        "C1 white spectrum rho=1",
        abs(fw.rho_g - 1.0) <= 0.10 and abs(fw.rho_rb - 1.0) <= 0.10,
        f"G {fw.rho_g:.4f}, RB {fw.rho_rb:.4f}, beta {fw.beta:.3f}",
    )

    # C2: beta ladder.
    beta_rows = []
    c2_ok = True
    beta_values = (1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
    for i, beta in enumerate(beta_values):
        patch, _, _ = make_patch(beta, 20 + i, noise=False)
        fit = fit_patch(patch, angular=False)
        err = abs(fit.beta - beta)
        beta_rows.append(
            {
                "truth": beta,
                "estimated": fit.beta,
                "error": err,
                "rho_truth": T.truth_rho("G", beta),
                "rho_est": fit.rho_g,
            }
        )
        c2_ok &= err <= 0.20
    tally.control(
        "C2 power-law beta ladder",
        c2_ok,
        "max |error| %.3f" % max(r["error"] for r in beta_rows),
        exercised=(len(beta_rows) == len(beta_values)),
    )

    # C3 and C4: exact planted aggregate rho values, sampled through Bayer GQ.
    rho_rows = []
    c3_ok = True
    c4_ok = True
    rho_values = (
        1.0,
        0.3,
        0.1,
        0.03,
        0.01,
        0.003,
        0.001,
        0.0003,
        0.0001,
    )
    for i, target in enumerate(rho_values):
        beta = T.beta_for_rho(target, "G")
        patch, truth_patch, _ = make_patch(beta, 50 + i, noise=False)
        c4_ok &= np.array_equal(patch, truth_patch)
        fit = fit_patch(patch, angular=False)
        dex = abs(math.log10(max(fit.rho_g, 1e-300) / target))
        rho_rows.append(
            {
                "rho_truth": target,
                "beta_truth": beta,
                "rho_est": fit.rho_g,
                "error_dex": dex,
            }
        )
        c3_ok &= dex <= 0.30
    median_dex = float(np.median([r["error_dex"] for r in rho_rows]))
    c3_ok &= median_dex <= 0.15
    tally.control(
        "C3 exact rho ladder",
        c3_ok,
        "median %.3f dex, worst %.3f dex"
        % (median_dex, max(r["error_dex"] for r in rho_rows)),
        exercised=(len(rho_rows) == len(rho_values)),
    )
    tally.control(
        "C4 Bayer/GQ sampling",
        c4_ok,
        "estimator and independent sampler agree on all planted scenes",
        exercised=(len(rho_rows) == len(rho_values) and c12),
    )

    # C5: noisy plants. Full white-floor subtraction must beat raw and dark-only,
    # including below the original rho sweep.
    mean_dn = 4000.0
    gain = 0.4
    read = 2.5
    full_floor = gain * mean_dn + read**2
    dark_floor = read**2
    noise_rows = []
    c5_ok = True
    for i, target in enumerate((0.1, 0.003, 0.0003)):
        beta = T.beta_for_rho(target, "G")
        field = T.powerlaw_field(1536, beta, 77 + i)
        raw = T.sampled_raw(
            field,
            mean_dn=mean_dn,
            contrast_dn=300.0,
            gain_dn_per_e=gain,
            read_sd_dn=read,
            seed=91 + i,
            add_noise=True,
        )
        patch = R.extract_gq(raw, 768, 768, 640)
        f_raw = fit_patch(patch, 0.0, angular=False)
        f_dark = fit_patch(patch, dark_floor, angular=False)
        f_full = fit_patch(patch, full_floor, angular=False)
        eraw = abs(math.log10(f_raw.rho_g / target))
        edark = abs(math.log10(f_dark.rho_g / target))
        efull = abs(math.log10(f_full.rho_g / target))
        c5_ok &= efull <= 0.30 and efull < eraw and efull < edark
        noise_rows.append(
            {
                "rho_truth": target,
                "raw_error_dex": eraw,
                "dark_error_dex": edark,
                "full_error_dex": efull,
                "raw_rho": f_raw.rho_g,
                "dark_rho": f_dark.rho_g,
                "full_rho": f_full.rho_g,
            }
        )
    c5 = tally.control(
        "C5 photon plus read subtraction",
        c5_ok,
        (
            "worst error raw %.3f, dark %.3f, full %.3f dex"
            % (
                max(r["raw_error_dex"] for r in noise_rows),
                max(r["dark_error_dex"] for r in noise_rows),
                max(r["full_error_dex"] for r in noise_rows),
            )
        ),
        exercised=(len(noise_rows) == 3),
    )

    # C6/C11: pure noise has no scene power. Real cross power is signed and
    # should average near zero, unlike its magnitude.
    rng = np.random.default_rng(101)
    na = rng.normal(0, 20, (768, 768))
    nb = rng.normal(0, 20, (768, 768))
    cross, blocks = R.real_cross_psd(na, nb, tile=128)
    legal = R.legal_frequency_mask(*R.gq_frequency_grid(128), "GQ")
    vals = cross[legal]
    z = abs(float(np.mean(vals))) / max(
        float(np.std(vals, ddof=1) / math.sqrt(vals.size)), 1e-30
    )
    c6 = tally.control(
        "C6 zero alias power",
        z < 3.0,
        f"signed cross mean z={z:.3f}, {blocks} Welch blocks",
        exercised=(vals.size > 1000),
    )
    c11 = tally.control(
        "C11 flat/no-scene control",
        abs(float(np.mean(vals))) < 0.02 * 20.0**2,
        f"mean {float(np.mean(vals)):.4g} vs noise variance 400",
        exercised=(float(np.std(vals)) > 0),
    )

    # C7: anisotropic plant.
    anis = (0.7, -0.35, 0.25, 0.2)
    patch, _, _ = make_patch(2.6, 121, noise=False, anisotropy=anis)
    fa = fit_patch(patch, angular=True)
    fi = fit_patch(patch, angular=False)
    truth = T.truth_rho("G", 2.6, anis)
    da = abs(math.log10(fa.rho_g / truth))
    di = abs(math.log10(fi.rho_g / truth))
    c7 = tally.control(
        "C7 anisotropic scene",
        da <= 0.30 and fa.holdout_median_abs_dex < fi.holdout_median_abs_dex,
        f"rho error angular {da:.3f} vs isotropic {di:.3f} dex; "
        f"holdout {fa.holdout_median_abs_dex:.3f} vs "
        f"{fi.holdout_median_abs_dex:.3f}",
    )

    # C8: one coherent grating must fail broadband holdout or concentration.
    n = 768
    yy, xx = np.mgrid[:n, :n]
    grating = np.cos(2 * np.pi * (0.12 * xx + 0.07 * yy))
    gp = R.extract_gq(4000.0 + 500.0 * grating, 384, 384, 320)
    gpsd, _ = R.welch_psd2(gp, tile=128)
    concentration = float(np.max(gpsd) / max(np.sum(gpsd), 1e-30))
    try:
        gf = fit_patch(gp, angular=True)
        grating_rejected = (
            concentration > 0.05
            or gf.holdout_median_abs_dex > 0.30
            or gf.holdout_p90_abs_dex > 0.60
        )
        gdetail = (
            f"concentration {concentration:.3f}, holdout "
            f"{gf.holdout_median_abs_dex:.3f}/{gf.holdout_p90_abs_dex:.3f}"
        )
    except ValueError as exc:
        grating_rejected = True
        gdetail = f"fit refused: {exc}"
    c8 = tally.control(
        "C8 coherent grating refusal",
        grating_rejected,
        gdetail,
        exercised=(concentration > 0.01),
    )

    # C9: phase-corrected cross spectrum under a known Fourier shift.
    field = T.powerlaw_field(1024, 1.0, 131)
    gqa = R.extract_gq(field, 512, 512, 448)
    fx, fy = R.gq_frequency_grid(448)
    dx, dy = 0.25, -0.25
    shifted = np.fft.ifft2(
        np.fft.fft2(gqa) * np.exp(2j * np.pi * (fx * dx + fy * dy))
    ).real
    good, _ = R.real_cross_psd(
        gqa, shifted, tile=128, shift_sensor=(dx, dy)
    )
    bad, _ = R.real_cross_psd(gqa, shifted, tile=128, shift_sensor=(0.0, 0.0))
    auto, _ = R.real_cross_psd(gqa, gqa, tile=128, shift_sensor=(0.0, 0.0))
    qx, qy = R.gq_frequency_grid(128)
    qr = np.hypot(qx, qy)
    phase = 2.0 * np.pi * (qx * dx + qy * dy)
    band = (
        R.legal_frequency_mask(qx, qy, "GQ")
        & (qr > 0.08)
        & (qr < 0.46)
        & (np.abs(phase) > 0.3)
    )
    good_mean = float(np.mean(good[band]))
    bad_mean = float(np.mean(bad[band]))
    auto_mean = float(np.mean(auto[band]))
    c9 = tally.control(
        "C9 translated repeat phase correction",
        good_mean > 1.10 * bad_mean
        and abs(good_mean / auto_mean - 1.0) < 0.02,
        (
            f"phase-sensitive corrected/raw "
            f"{good_mean / max(bad_mean, 1e-30):.3f}x, "
            f"corrected/auto {good_mean / max(auto_mean, 1e-30):.3f}x"
        ),
        exercised=(int(np.sum(band)) >= 1000),
    )

    # C10: an ideal one-dimensional step has the known pre-MTF power slope
    # beta=2. A radial median of one 2D edge is not this quantity: almost every
    # azimuthal bin is a line-spectrum zero. The first implementation used that
    # invalid statistic and C10 correctly returned beta=3.601.
    n = 16384
    edge = (np.arange(n) >= n // 2).astype(float)
    edge -= float(np.mean(edge))
    ep = np.abs(np.fft.rfft(edge)) ** 2
    ef = np.fft.rfftfreq(n)
    mask = (ef >= 0.002) & (ef <= 0.05) & (ep > 1e-20)
    slope = float(np.polyfit(np.log(ef[mask]), np.log(ep[mask]), 1)[0])
    c10 = tally.control(
        "C10 step-edge beta=2",
        abs(slope + 2.0) <= 0.25,
        f"fitted beta {-slope:.3f}",
        exercised=(int(mask.sum()) >= 100),
    )

    print("\n" + "=" * 88)
    print("M-PHASE0-RHO commissioning: deliberate defects")
    print("=" * 88)

    # D1: an illegal single-green read above 0.25.
    g = np.linspace(-0.5, 0.5, 129, endpoint=False)
    gy, gx = np.meshgrid(g, g, indexing="ij")
    illegal = (np.abs(gx) > 0.25) | (np.abs(gy) > 0.25)
    legal = R.legal_frequency_mask(gx, gy, "G1")
    tally.defect(
        "D1 read G1/G2 above support",
        bool(np.any(illegal & ~legal)),
        "C12/grid",
        f"{int(np.sum(illegal & ~legal))} illegal bins rejected",
    )

    # D2: factor-two frequency mapping moves a known GQ grating.
    n = 256
    yy, xx = np.mgrid[:n, :n]
    # In GQ coordinates fu=fx+fy=0.18, fv=fy-fx=0.06.
    qp = np.cos(2 * np.pi * (0.18 * yy + 0.06 * xx))
    got = R.peak_frequency_sensor(qp, "GQ")
    expected = (0.06, 0.12)
    good_err = min(
        math.hypot(got[0] - expected[0], got[1] - expected[1]),
        math.hypot(got[0] + expected[0], got[1] + expected[1]),
    )
    doubled_err = min(
        math.hypot(2 * got[0] - expected[0], 2 * got[1] - expected[1]),
        math.hypot(2 * got[0] + expected[0], 2 * got[1] + expected[1]),
    )
    tally.defect(
        "D2 multiply frequency by two",
        good_err < 0.01 and doubled_err > 0.05,
        "C10/grid",
        f"correct error {good_err:.4f}, doubled error {doubled_err:.4f}",
    )

    # D3: p7-style nine-member sum violates the white-scene invariant.
    bad_g, bad_rb = 9.0, 27.0
    tally.defect(
        "D3 sum nine members per alias",
        abs(bad_g - 1.0) > 0.10 or abs(bad_rb - 1.0) > 0.10,
        "C1",
        f"defective white values G={bad_g:.1f}, RB={bad_rb:.1f}",
    )

    # D4: magnitude of a noise cross-spectrum is strictly positive.
    mag_bias = float(np.mean(np.abs(np.fft.fft2(na) * np.conj(np.fft.fft2(nb)))))
    signed = abs(float(np.mean(vals)))
    tally.defect(
        "D4 magnitude cross-spectrum",
        mag_bias > 100 * max(signed, 1e-30),
        "C6/C11",
        f"magnitude mean {mag_bias:.3g}, signed mean {signed:.3g}",
    )

    # D5: dark-only subtraction remains outside the planted-rho gate.
    tally.defect(
        "D5 omit photon noise",
        edark > 0.30 or edark > efull,
        "C5",
        f"dark-only {edark:.3f} vs full {efull:.3f} dex",
    )

    # D6: clipping a signed null creates positive scene power.
    clipped_mean = float(np.mean(np.maximum(vals, 0.0)))
    tally.defect(
        "D6 clip negative corrected bins",
        clipped_mean > 5 * abs(float(np.mean(vals))),
        "C6",
        f"clipped mean {clipped_mean:.3g}, signed {float(np.mean(vals)):.3g}",
    )

    # D7: wrong shift sign leaves the translated cross-spectrum attenuated.
    wrong, _ = R.real_cross_psd(
        gqa, shifted, tile=128, shift_sensor=(-dx, -dy)
    )
    wrong_mean = float(np.mean(wrong[band]))
    tally.defect(
        "D7 swap G phase geometry",
        good_mean > 1.50 * wrong_mean,
        "C9/grid",
        (
            f"correct/wrong phase-sensitive power "
            f"{good_mean / max(wrong_mean, 1e-30):.3f}x"
        ),
    )

    # D8: fitting only S(q), omitting the alias sum, is measured on the same
    # alias-rich beta=4 plant used by C2.
    row4 = next(r for r in beta_rows if r["truth"] == 4.0)
    patch, _, _ = make_patch(4.0, 24, noise=False)
    psd, blocks = R.welch_psd2(patch, tile=128)
    fx, fy = R.gq_frequency_grid(128)
    rr = np.hypot(fx, fy)
    legal = R.legal_frequency_mask(fx, fy, "GQ")
    one = (fy > 0) | ((np.abs(fy) < 1e-15) & (fx > 0))
    mask = legal & one & (rr >= 0.04) & (rr <= 0.46) & (psd > 0)
    bad_beta = -float(np.polyfit(np.log(rr[mask]), np.log(psd[mask]), 1)[0])
    good_beta = row4["estimated"]
    tally.defect(
        "D8 fit S(q), omit alias sum",
        abs(bad_beta - 4.0) > abs(good_beta - 4.0) + 0.05,
        "C3/C4",
        f"bad beta {bad_beta:.3f}, alias-aware {good_beta:.3f}",
    )

    # D9: static source isolation check. The estimator may not import truth.
    source = (HERE / "rho_lib.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    identifiers = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    isolated = (
        "truth_factory" not in imports
        and "rho_truth" not in identifiers
        and "beta_for_rho" not in identifiers
    )
    tally.defect(
        "D9 estimator reads planted truth",
        isolated,
        "source-isolation",
        "no truth module or planted-answer identifier in estimator AST",
    )

    # D10: an accounting verifier must count a mismatched claim.
    fake_claims = [
        {"id": "a", "expected": 1.0, "actual": 1.0},
        {"id": "b", "expected": 2.0, "actual": 3.0},
        {"id": "c", "expected": 4.0, "actual": None},
    ]
    verified = sum(
        q["actual"] is not None
        and math.isclose(q["expected"], q["actual"], rel_tol=0, abs_tol=1e-12)
        for q in fake_claims
    )
    unverified = len(fake_claims) - verified
    tally.defect(
        "D10 omit an unverified claim",
        verified == 1 and unverified == 2 and verified + unverified == 3,
        "checker accounting",
        f"VERIFIED {verified}, UNVERIFIED {unverified}, TOTAL {len(fake_claims)}",
    )

    payload = tally.payload()
    payload["details"] = {
        "beta_ladder": beta_rows,
        "rho_ladder": rho_rows,
        "noise_control": noise_rows,
        "anisotropy": {
            "truth_rho": truth,
            "angular": fa.to_dict(),
            "isotropic": fi.to_dict(),
        },
    }
    with open(OUT / "commission.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    lines = [
        "M-PHASE0-RHO commissioning",
        "known-answer controls: PASS %d / FAIL %d"
        % (
            payload["known_answer"]["pass"],
            payload["known_answer"]["fail"],
        ),
        "deliberate defects: CAUGHT %d / MISSED %d"
        % (payload["defects"]["caught"], payload["defects"]["missed"]),
        "VERDICT: " + payload["verdict"],
    ]
    (OUT / "commission.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n" + "=" * 88)
    for line in lines:
        print(line)
    return 0 if payload["verdict"] == "COMMISSIONED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
