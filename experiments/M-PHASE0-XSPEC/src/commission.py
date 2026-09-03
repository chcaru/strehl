"""Commission every XSPEC instrument before any outcome stack is measured."""

from __future__ import annotations

import json
import math
from pathlib import Path
import re
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
REPO = ROOT.parent.parent
sys.path.insert(0, str(HERE))

import truth_factory as T  # noqa: E402
import xspec_lib as X  # noqa: E402


RAW_CONTROL = Path(r"D:\personal\macro\bee-1-cpl\DSC00001.ARW")


class Tally:
    def __init__(self) -> None:
        self.controls: list[dict] = []
        self.plants: list[dict] = []

    def control(self, name: str, passed: bool, **detail) -> bool:
        row = {"name": name, "status": "PASS" if passed else "FAIL", **detail}
        self.controls.append(row)
        print(f"  {row['status']:6s} {name}: {detail}")
        return bool(passed)

    def plant(self, name: str, landed: bool, went_red: bool, **detail) -> bool:
        caught = bool(landed and went_red)
        row = {
            "name": name,
            "status": "CAUGHT" if caught else "MISSED",
            "landed": bool(landed),
            "target_went_red": bool(went_red),
            **detail,
        }
        self.plants.append(row)
        print(f"  {row['status']:6s} {name}: {detail}")
        return caught


def fixed_crop_fixture() -> tuple[np.ndarray, np.ndarray, tuple[float, float], dict]:
    active, meta = X.load_active(RAW_CONTROL)
    reference = X.extract_gq(active, 2344, 3514, X.PATCH)
    du, dv = 2, -1
    # Exact periodic coordinate permutation of untouched captured samples.
    # Rectangular-window DFT below makes the shift theorem exact; the shift
    # predicate comes only from these integer indices.
    moving = np.roll(reference, shift=(-du, -dv), axis=(0, 1))
    # Sensor y=u+v and x=u-v.  This predicate comes from crop coordinates,
    # not from the estimator or a generated image.
    expected = (float(du - dv), float(du + dv))
    return moving, reference, expected, meta


def crop_reading(
    fixture,
    *,
    shift_sign: float = 1.0,
    swap_axes: bool = False,
    unit_scale: float = 1.0,
) -> dict:
    moving, reference, expected, _ = fixture
    bundle = X.cross_bundle(moving, reference, X.PATCH, window="rect")
    got = X.fit_phase_shift(
        bundle,
        shift_sign=shift_sign,
        swap_axes=swap_axes,
        unit_scale=unit_scale,
    )
    error = math.hypot(got["dx"] - expected[0], got["dy"] - expected[1])
    return {"got": [got["dx"], got["dy"]], "expected": list(expected), "error": error}


def subpixel_reading() -> dict:
    scene = T.textured_scene()
    du, dv = 0.27, -0.19
    moving = T.spatial_shift_gq(scene, du, dv)
    expected = (du - dv, du + dv)
    bundle = X.cross_bundle(moving, scene, 64)
    got = X.fit_phase_shift(bundle)
    spatial = X.fit_spatial_shift(moving, scene, 64)
    return {
        "expected": list(expected),
        "phase": [got["dx"], got["dy"]],
        "phase_error": math.hypot(got["dx"] - expected[0], got["dy"] - expected[1]),
        "spatial": [spatial["dx"], spatial["dy"]],
        "spatial_error": math.hypot(
            spatial["dx"] - expected[0], spatial["dy"] - expected[1]
        ),
    }


def odd_reading(*, magnitude_only: bool = False) -> dict:
    scene = T.textured_scene()
    plus, minus, truth = T.odd_phase_pair(scene)
    forward = X.cross_bundle(plus, minus, 64)
    fit = X.fit_phase_shift(forward)
    f = X.phase_field_and_floor(
        forward,
        (fit["dx"], fit["dy"]),
        magnitude_only=magnitude_only,
    )
    reverse = X.cross_bundle(minus, plus, 64)
    rfit = X.fit_phase_shift(reverse)
    r = X.phase_field_and_floor(
        reverse,
        (rfit["dx"], rfit["dy"]),
        magnitude_only=magnitude_only,
    )
    basis_f = f["fx"] ** 3 - 3.0 * f["fx"] * f["fy"] ** 2
    basis_r = r["fx"] ** 3 - 3.0 * r["fx"] * r["fy"] ** 2
    projection_f = float(np.average(f["theta"] * basis_f, weights=f["weight"]))
    projection_r = float(np.average(r["theta"] * basis_r, weights=r["weight"]))
    return {
        "forward_rms_rad": f["observed_rms_rad"],
        "reverse_rms_rad": r["observed_rms_rad"],
        "forward_projection": projection_f,
        "reverse_projection": projection_r,
        **truth,
    }


def even_reading(*, omit_derotation: bool = False) -> dict:
    scene = T.textured_scene()
    moving, reference, truth = T.even_blur_translated_pair(scene)
    bundle = X.cross_bundle(moving, reference, 64)
    fit = X.fit_phase_shift(bundle)
    phase = X.phase_field_and_floor(
        bundle,
        (fit["dx"], fit["dy"]),
        omit_derotation=omit_derotation,
    )
    return {
        "phase_rms_rad": phase["observed_rms_rad"],
        "fit": [fit["dx"], fit["dy"]],
        "expected": [truth["dx_sensor"], truth["dy_sensor"]],
        "shift_error": math.hypot(
            fit["dx"] - truth["dx_sensor"],
            fit["dy"] - truth["dy_sensor"],
        ),
    }


def inversion_reading(
    *,
    magnitude_only: bool = False,
    clip_negative: bool = False,
) -> dict:
    scene = T.textured_scene()
    inverted = -(scene - float(np.mean(scene))) + float(np.mean(scene))
    bundle = X.cross_bundle(inverted, scene, 64)
    fit = X.fit_phase_shift(bundle)
    rows = [
        X.band_correlation(
            bundle,
            (fit["dx"], fit["dy"]),
            band,
            bootstrap=200,
            seed=700 + i,
            magnitude_only=magnitude_only,
            clip_negative=clip_negative,
        )
        for i, band in enumerate(X.INVERSION_BANDS)
    ]
    return {
        "shift": [fit["dx"], fit["dy"]],
        "phase_intercept_cycles": fit["phase_intercept_cycles"],
        "bands": rows,
    }


def grid_reading(*, scale: float = 1.0) -> dict:
    names = {
        "registration": X.REG_BAND,
        "odd": X.ODD_BAND,
        "inv0": X.INVERSION_BANDS[0],
        "inv1": X.INVERSION_BANDS[1],
        "inv2": X.INVERSION_BANDS[2],
    }
    rows = {}
    for n in X.WELCH_GRIDS:
        expected = T.independent_grid_counts(n)
        got = {
            name: int(X.frequency_mask(n, band, scale=scale).sum())
            for name, band in names.items()
        }
        rows[str(n)] = {
            "expected": expected,
            "got": got,
            "matches": got == expected,
        }
    return {"scale": scale, "grids": rows}


def noise_floor_reading(*, floor_scale: float = 1.0) -> dict:
    train = []
    holdout = []
    for sigma, seed in ((80.0, 8100), (180.0, 18100)):
        pairs = T.noisy_pairs(32, sigma, seed=seed)
        for i, (a, b) in enumerate(pairs):
            bundle = X.cross_bundle(a, b, 64)
            fit = X.fit_phase_shift(bundle)
            row = X.phase_field_and_floor(bundle, (fit["dx"], fit["dy"]))
            ratio = row["observed_rms_rad"] / max(
                row["nominal_floor_rad"], np.finfo(float).tiny
            )
            (train if i < 16 else holdout).append(
                {"sigma": sigma, "ratio_nominal": float(ratio)}
            )
    q = float(np.median([x["ratio_nominal"] for x in train]))
    calibrated = np.asarray(
        [x["ratio_nominal"] / (q * floor_scale) for x in holdout],
        dtype=float,
    )
    return {
        "q": q,
        "floor_scale": float(floor_scale),
        "holdout_median": float(np.median(calibrated)),
        "holdout_p10_p90": [
            float(np.percentile(calibrated, 10)),
            float(np.percentile(calibrated, 90)),
        ],
        "within_factor_two_fraction": float(
            np.mean((calibrated >= 0.5) & (calibrated <= 2.0))
        ),
        "train_n": len(train),
        "holdout_n": len(holdout),
    }


def rust_probe() -> dict:
    exe = REPO / "target" / "release" / "strehl.exe"
    if not exe.exists():
        raise FileNotFoundError(f"release binary is absent: {exe}")
    proc = subprocess.run(
        [str(exe), "probe", "--limit", "1", str(RAW_CONTROL.parent)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"strehl probe exited {proc.returncode}: {proc.stdout}")
    size = re.search(r"active area\s*:\s*(\d+) x (\d+)", proc.stdout)
    levels = re.search(r"levels\s*:\s*black (\d+), white (\d+)", proc.stdout)
    if not size or not levels:
        raise RuntimeError(f"could not parse probe output:\n{proc.stdout}")
    return {
        "command": [
            str(exe),
            "probe",
            "--limit",
            "1",
            str(RAW_CONTROL.parent),
        ],
        "exit": proc.returncode,
        "active_width": int(size.group(1)),
        "active_height": int(size.group(2)),
        "black": int(levels.group(1)),
        "white": int(levels.group(2)),
        "stdout": proc.stdout,
    }


def loader_reading(*, mutate_rawpy_width: bool = False) -> dict:
    first, meta = X.load_active(RAW_CONTROL)
    second, meta2 = X.load_active(RAW_CONTROL)
    probe = rust_probe()
    rawpy_width = int(meta["shape"][1])
    if mutate_rawpy_width:
        rawpy_width = probe["active_width"]
    equal = bool(np.array_equal(first, second))
    passed = bool(
        meta == meta2
        and equal
        and probe["active_height"] == meta["shape"][0]
        and probe["active_width"] - rawpy_width == 4
        and probe["black"] == int(X.BLACK_LEVEL)
        and probe["white"] == int(X.CAMERA_WHITE_LEVEL)
    )
    return {
        "check_passed": passed,
        "rawpy_shape": meta["shape"],
        "rawpy_width_used": rawpy_width,
        "rust_shape": [probe["active_height"], probe["active_width"]],
        "levels": [probe["black"], probe["white"]],
        "pixel_repeat_equal": equal,
        "pixel_sha256": __import__("hashlib").sha256(first.tobytes()).hexdigest(),
        "probe": probe,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tally = Tally()
    print("M-PHASE0-XSPEC commissioning")
    print("=" * 78)

    fixture = fixed_crop_fixture()
    crop = crop_reading(fixture)
    tally.control(
        "C1 fixed external integer crop",
        crop["error"] <= 0.03,
        **crop,
    )

    subpixel = subpixel_reading()
    tally.control(
        "C2 independent spatial subpixel shift",
        subpixel["phase_error"] <= 0.04,
        **subpixel,
    )

    odd = odd_reading()
    odd_ok = bool(
        odd["forward_rms_rad"] >= 0.08
        and odd["reverse_rms_rad"] >= 0.08
        and odd["forward_projection"] * odd["reverse_projection"] < 0.0
        and abs(odd["forward_rms_rad"] / odd["reverse_rms_rad"] - 1.0) <= 0.02
    )
    tally.control("C3 independent odd-phase transfer", odd_ok, **odd)

    even = even_reading()
    tally.control(
        "C4 even blur plus translation derotates to null",
        even["phase_rms_rad"] <= 0.03 and even["shift_error"] <= 0.04,
        **even,
    )

    inversion = inversion_reading()
    inv_ok = bool(
        math.hypot(*inversion["shift"]) <= 0.03
        and abs(abs(inversion["phase_intercept_cycles"]) - 0.5) <= 1e-6
        and all(abs(row["rho"] + 1.0) <= 1e-9 for row in inversion["bands"])
        and all(row["ci95"][1] <= -0.95 for row in inversion["bands"])
    )
    tally.control(
        "C5 full contrast inversion reaches estimator ceiling",
        inv_ok,
        **inversion,
    )

    grid = grid_reading()
    tally.control(
        "C6 fixed frequency grid and boundaries",
        all(row["matches"] for row in grid["grids"].values()),
        **grid,
    )

    floor = noise_floor_reading()
    floor_ok = bool(
        0.75 <= floor["holdout_median"] <= 1.33
        and floor["within_factor_two_fraction"] >= 0.80
    )
    tally.control("C7 analytic phase floor predicts holdout", floor_ok, **floor)

    loader = loader_reading()
    tally.control(
        "C8 rawpy loader against Rust rawler probe",
        loader["check_passed"],
        **loader,
    )

    print("\nPlanted defects: every target must go RED")
    print("-" * 78)
    p = crop_reading(fixture, shift_sign=-1.0)
    tally.plant(
        "P1 shift sign reversed",
        landed=p["got"][0] < 0 and p["got"][1] < 0,
        went_red=p["error"] > 0.03,
        **p,
    )
    p = crop_reading(fixture, swap_axes=True)
    tally.plant(
        "P2 sensor axes swapped",
        landed=abs(p["got"][0] - crop["got"][1]) < 1e-9,
        went_red=p["error"] > 0.03,
        **p,
    )
    p = crop_reading(fixture, unit_scale=0.5)
    tally.plant(
        "P3 GQ displacement misread as sensor units",
        landed=math.hypot(*p["got"]) < 0.75 * math.hypot(*crop["got"]),
        went_red=p["error"] > 0.03,
        **p,
    )
    p = grid_reading(scale=2.0)
    tally.plant(
        "P4 frequency axes doubled",
        landed=p["scale"] == 2.0,
        went_red=not all(row["matches"] for row in p["grids"].values()),
        **p,
    )
    p = even_reading(omit_derotation=True)
    tally.plant(
        "P5 linear phase ramp not removed",
        landed=p["phase_rms_rad"] > 3.0 * even["phase_rms_rad"],
        went_red=p["phase_rms_rad"] > 0.03,
        **p,
    )
    p_odd = odd_reading(magnitude_only=True)
    p_inv = inversion_reading(magnitude_only=True)
    p_odd_ok = bool(
        p_odd["forward_rms_rad"] >= 0.08
        and p_odd["forward_projection"] * p_odd["reverse_projection"] < 0.0
    )
    p_inv_ok = all(abs(row["rho"] + 1.0) <= 1e-9 for row in p_inv["bands"])
    tally.plant(
        "P6 complex cross-spectrum replaced by magnitude",
        landed=all(row["rho"] > 0.95 for row in p_inv["bands"]),
        went_red=not p_odd_ok and not p_inv_ok,
        odd=p_odd,
        inversion=p_inv,
    )
    p = inversion_reading(clip_negative=True)
    tally.plant(
        "P7 negative correlation clipped at zero",
        landed=all(row["rho"] == 0.0 for row in p["bands"]),
        went_red=not all(abs(row["rho"] + 1.0) <= 1e-9 for row in p["bands"]),
        **p,
    )
    p = noise_floor_reading(floor_scale=0.5)
    p_ok = bool(
        0.75 <= p["holdout_median"] <= 1.33
        and p["within_factor_two_fraction"] >= 0.80
    )
    tally.plant(
        "P8 phase floor halved",
        landed=abs(p["floor_scale"] - 0.5) < 1e-12,
        went_red=not p_ok,
        **p,
    )
    p = loader_reading(mutate_rawpy_width=True)
    tally.plant(
        "P9 rawpy visible width treated as rawler width",
        landed=p["rawpy_width_used"] == p["rust_shape"][1],
        went_red=not p["check_passed"],
        **p,
    )

    controls_pass = sum(row["status"] == "PASS" for row in tally.controls)
    plants_caught = sum(row["status"] == "CAUGHT" for row in tally.plants)
    green = controls_pass == len(tally.controls) and plants_caught == len(tally.plants)
    payload = {
        "status": "GREEN" if green else "RED",
        "controls_pass": controls_pass,
        "controls_fail": len(tally.controls) - controls_pass,
        "plants_caught": plants_caught,
        "plants_missed": len(tally.plants) - plants_caught,
        "controls": tally.controls,
        "plants": tally.plants,
    }
    with open(OUT / "commission.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print("=" * 78)
    print(
        f"controls PASS {controls_pass} / FAIL {len(tally.controls)-controls_pass}; "
        f"plants CAUGHT {plants_caught} / MISSED {len(tally.plants)-plants_caught}"
    )
    print(f"COMMISSIONED - {payload['status']}")
    print(f"wrote {OUT / 'commission.json'}")
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
