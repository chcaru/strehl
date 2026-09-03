"""Commission every M-PHASE0-CURV instrument before real measurement.

Each control is run once through the intended path and once with the exact
defect it targets planted.  A plant counts only when the intended path is GREEN
and the defective path makes that same predicate RED.
"""

from __future__ import annotations

import json
import hashlib
import math
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import rawpy
from scipy import ndimage

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
REPO = ROOT.parents[1]
sys.path.insert(0, str(HERE))
import curvlib as C  # noqa: E402


EXTERNAL = (
    REPO
    / "experiments"
    / "M84b-ruler-metrology"
    / "out"
    / "depth-truth-params.json"
)
EXTERNAL_SHA = "745bbbcEDB3DA04842740A88A01CE21109A75393DCC371804D62874C63973D69".lower()
RAW_STACK = (
    Path(r"D:\personal\macro\requests\8-tilted-planar")
    / "ruler-incline-ang10.26deg-inches-f5.6-sw7-cpl"
)
WIDTH = 7032.0
HEIGHT = 4688.0


def coordinates(nx: int = 15, ny: int = 11) -> tuple[np.ndarray, np.ndarray]:
    xs = np.linspace(0.06 * WIDTH, 0.94 * WIDTH, nx)
    ys = np.linspace(0.08 * HEIGHT, 0.92 * HEIGHT, ny)
    x, y = np.meshgrid(xs, ys)
    return x.ravel(), y.ravel()


def independent_response_generator(
    q: float,
    width: float,
    seed: int,
    *,
    angle_deg: float = 17.0,
    centre: tuple[float, float] = (0.0, 0.0),
    width_varies: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate response curves without calling any curvlib surface function."""
    x, y = coordinates()
    xn = (x - WIDTH / 2.0) / (HEIGHT / 2.0)
    yn = (y - HEIGHT / 2.0) / (HEIGHT / 2.0)
    t = math.radians(angle_deg)
    u = math.cos(t) * xn + math.sin(t) * yn
    v = -math.sin(t) * xn + math.cos(t) * yn
    cu, cv = centre
    # A plane passed through a deliberately nonlinear focus axis, plus an
    # independently expressed radial focal-surface plant.
    z = 35.0 + 6.0 * u + 1.30 * u * u - 0.18 * u**3
    z += q * ((u - cu) ** 2 + (v - cv) ** 2)
    frame = np.arange(71, dtype=np.float64)[:, None]
    local_width = (
        width * (1.0 + 0.15 * v * v)
        if width_varies
        else np.full_like(v, width)
    )
    amp = 0.8 + 0.15 * np.cos(1.7 * u) + 0.05 * np.sin(2.3 * v)
    signal = 0.035 + amp[None, :] * np.exp(
        -0.5 * ((frame - z[None, :]) / local_width[None, :]) ** 2
    )
    rng = np.random.default_rng(seed)
    g1 = np.maximum(signal + rng.normal(0.0, 0.0015, signal.shape), 1e-8)
    g2 = np.maximum(signal + rng.normal(0.0, 0.0015, signal.shape), 1e-8)
    return x, y, g1, g2


def recover_synthetic(
    q: float,
    width: float,
    seed: int,
    *,
    angle_deg: float = 17.0,
    centre: tuple[float, float] = (0.0, 0.0),
    width_varies: bool = False,
    fit_defect: str | None = None,
    peak_width_coupling: float = 0.0,
) -> dict[str, object]:
    x, y, g1, g2 = independent_response_generator(
        q,
        width,
        seed,
        angle_deg=angle_deg,
        centre=centre,
        width_varies=width_varies,
    )
    values: list[float] = []
    valid: list[bool] = []
    for i in range(len(x)):
        p = C.peaks_for_site(
            g1[:, i],
            g2[:, i],
            width_coupling=peak_width_coupling,
        )
        values.append(float(p["k_primary_avg"]))
        valid.append(bool(p["valid"]))
    keep = np.asarray(valid) & np.isfinite(values)
    fit = C.fit_surface(
        x[keep],
        y[keep],
        np.asarray(values)[keep],
        WIDTH,
        HEIGHT,
        defect=fit_defect,
    )
    fit["valid_fraction"] = float(np.mean(keep))
    return fit


def add_control(
    controls: list[dict[str, object]],
    name: str,
    passed: bool,
    readings: dict[str, object],
) -> None:
    controls.append(
        {"id": name, "green": bool(passed), "readings": readings}
    )


def add_plant(
    plants: list[dict[str, object]],
    name: str,
    red: bool,
    reading: object,
) -> None:
    plants.append(
        {"id": name, "red": bool(red), "defective_reading": reading}
    )


def external_plane() -> tuple[float, float]:
    if C.sha256_file(EXTERNAL).lower() != EXTERNAL_SHA:
        raise RuntimeError("external fixture hash changed")
    d = json.loads(EXTERNAL.read_text(encoding="utf-8"))
    xq, yq = np.meshgrid(
        np.linspace(1500.0, 2480.0, 31),
        np.linspace(80.0, 2260.0, 21),
    )
    xr = xq - float(d["s"]) * (yq - float(d["y_ref"]))
    k = (xr - float(d["A"])) / (float(d["B"]) - float(d["C"]) * xr)
    n = np.polyval(np.asarray(d["n_model_poly_k2k1k0"], dtype=float), k)
    good = C.fit_surface(
        xq.ravel(),
        yq.ravel(),
        n.ravel(),
        3514.0,
        2344.0,
    )
    bad = C.fit_surface(
        xq.ravel(),
        yq.ravel(),
        n.ravel(),
        3514.0,
        2344.0,
        defect="naive_radial",
    )
    return float(good["q_h_frames"]), float(bad["q_h_frames"])


def pure_noise_valid_fraction(bypass: bool) -> float:
    rng = np.random.default_rng(0xC5E4)
    curves1 = np.maximum(rng.normal(1.0, 0.02, (71, 651)), 1e-8)
    curves2 = np.maximum(rng.normal(1.0, 0.02, (71, 651)), 1e-8)
    valid = [
        bool(
            C.peaks_for_site(
                curves1[:, i], curves2[:, i], bypass_reality=bypass
            )["valid"]
        )
        for i in range(curves1.shape[1])
    ]
    return float(np.mean(valid))


def mock_ladder_verdict(ignore_ladders: bool = False) -> str:
    primary = C.classify_interval(1.2, [0.7, 1.7])
    aperture = C.classify_interval(0.0, [-0.1, 0.1])
    if ignore_ladders:
        return "SURVIVE" if primary == "MATERIAL" else "NARROWED"
    if {primary, aperture} == {"MATERIAL", "NEGLIGIBLE"}:
        return "NOT ROBUST"
    return "NARROWED"


def parse_probe(text: str) -> dict[str, object]:
    active = re.search(r"active area\s*:\s*(\d+)\s*x\s*(\d+)", text)
    levels = re.search(r"levels\s*:\s*black\s+(\d+),\s*white\s+(\d+)", text)
    camera = re.search(r"camera\s*:\s*(.+)", text)
    if not active or not levels or not camera:
        raise RuntimeError(f"cannot parse strehl probe output:\n{text}")
    return {
        "active_width": int(active.group(1)),
        "active_height": int(active.group(2)),
        "black": int(levels.group(1)),
        "white": int(levels.group(2)),
        "camera": camera.group(1).strip(),
    }


def raw_contract() -> tuple[dict[str, object], bool]:
    exe = REPO / "target" / "release" / "strehl.exe"
    if not exe.exists():
        raise FileNotFoundError(f"release binary missing: {exe}")
    files = sorted(RAW_STACK.glob("*.ARW"))
    first = files[0]
    proc = subprocess.run(
        [str(exe), "probe", str(RAW_STACK), "--limit", "1"],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"strehl probe exited {proc.returncode}: {proc.stderr}")
    rust = parse_probe(proc.stdout + "\n" + proc.stderr)

    def load() -> tuple[np.ndarray, dict[str, object]]:
        with rawpy.imread(str(first)) as raw:
            active = np.array(raw.raw_image_visible, copy=True)
            pattern = np.array(raw.raw_pattern, copy=True)
            meta = {
                "shape": list(active.shape),
                "black": int(max(raw.black_level_per_channel)),
                "container_white": int(raw.white_level),
                "pattern": pattern.tolist(),
            }
        return active, meta

    a, meta_a = load()
    b, meta_b = load()
    greens = {int(meta_a["pattern"][0][1]), int(meta_a["pattern"][1][0])}

    def contract_pass(meta: dict[str, object]) -> bool:
        return bool(
            meta["shape"]
            == [
                int(rust["active_height"]),
                int(rust["active_width"]) - 4,
            ]
            and int(meta["black"]) == int(rust["black"]) == 512
            and int(rust["white"]) == 15360
            and int(meta["container_white"]) == 16383
            and int(meta["container_white"]) >= int(rust["white"])
            and len(greens) in {1, 2}
            and "ILCE-7CM2" in str(rust["camera"])
        )

    pixel_a = hashlib.sha256(a.tobytes()).hexdigest()
    pixel_b = hashlib.sha256(b.tobytes()).hexdigest()
    good = bool(meta_a == meta_b and pixel_a == pixel_b and contract_pass(meta_a))
    reading = {
        "file": str(first),
        "rust": rust,
        "rawpy": meta_a,
        "pixel_sha256_first": pixel_a,
        "pixel_sha256_second": pixel_b,
        "repeat_pixel_sha_equal": bool(pixel_a == pixel_b),
        "contract_green": good,
    }
    mutated = json.loads(json.dumps(meta_a))
    mutated["shape"][1] += 2
    bad_passes = contract_pass(mutated)
    return reading, bad_passes


def image_response_control() -> tuple[dict[str, object], int]:
    """Independent blur generator versus production 2-D response operator."""
    rng = np.random.default_rng(0xC5E900)
    base = ndimage.gaussian_filter(rng.normal(size=(256, 320)), 0.55)
    base = (base - np.mean(base)) / np.std(base)
    k0 = 7
    sigmas = np.array([0.20 + 0.55 * abs(k - k0) for k in range(15)])
    cube = np.stack(
        [
            np.maximum(
                1000.0 + 180.0 * ndimage.gaussian_filter(base, float(s)),
                40.0,
            ).astype(np.float32)
            for s in sigmas
        ]
    )
    good_scores = []
    for plane in cube:
        response, _ = C.focus_response(plane)
        good_scores.append(float(np.mean(response[24:-24, 24:-24])))
    good_scores = np.asarray(good_scores)
    good_peak = int(np.argmax(good_scores))
    grouped = [
        float(np.mean(good_scores[np.isclose(sigmas, s)]))
        for s in sorted(set(float(v) for v in sigmas))
    ]
    monotone = bool(np.all(np.diff(grouped) < 0.0))

    # Deliberate P11 defect: differentiate along the non-spatial frame axis.
    # This is the exact class ruled out by AGENTS rule 23.
    temporal = ndimage.sobel(cube, axis=0, mode="reflect")
    bad_energy = ndimage.uniform_filter(
        temporal * temporal, size=(1, 17, 17), mode="reflect"
    )
    bad_level = ndimage.uniform_filter(cube, size=(1, 17, 17), mode="reflect")
    bad_response = bad_energy / np.maximum(bad_level, 32.0) ** 2
    bad_scores = np.mean(bad_response[:, 24:-24, 24:-24], axis=(1, 2))
    bad_peak = int(np.argmax(bad_scores))
    return {
        "fixed_in_focus_frame": k0,
        "production_peak_frame": good_peak,
        "production_blur_scores": grouped,
        "strictly_decreases_with_blur": monotone,
        "wrong_axis_peak_frame": bad_peak,
    }, bad_peak


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    controls: list[dict[str, object]] = []
    plants: list[dict[str, object]] = []

    # E1: data produced by an independent prior lane, fixed by SHA.
    external_good, external_naive = external_plane()
    add_control(
        controls,
        "E1-external-plane",
        abs(external_good) <= 0.05,
        {
            "fixture_sha256": C.sha256_file(EXTERNAL),
            "registered_q_h": external_good,
        },
    )
    add_plant(
        plants,
        "P1-affine-radial-on-external-plane",
        abs(external_naive) > 0.05,
        external_naive,
    )

    # E2: response-cube curvature dose and sign.
    doses = [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0]
    dose_rows: dict[str, list[float]] = {str(v): [] for v in doses}
    sign_ok = True
    for dose in doses:
        for seed in range(32):
            q = float(recover_synthetic(dose, 4.0, 0xC5E200 + seed)["q_h_frames"])
            dose_rows[str(dose)].append(q)
            if dose and math.copysign(1.0, q) != math.copysign(1.0, dose):
                sign_ok = False
    medians = {k: float(np.median(v)) for k, v in dose_rows.items()}
    ratios = [
        abs(medians[str(d)] / d)
        for d in doses
        if d != 0
    ]
    slope = float(np.polyfit(np.asarray(doses), np.asarray(list(medians.values())), 1)[0])
    e2_green = bool(
        sign_ok
        and all(0.80 <= r <= 1.20 for r in ratios)
        and 0.80 <= slope <= 1.20
        and abs(medians["0.0"]) <= 0.10
    )
    add_control(
        controls,
        "E2-curvature-dose",
        e2_green,
        {
            "median_recovered": medians,
            "ratios_nonzero": ratios,
            "dose_slope": slope,
            "fully_present_minus2_reading": medians["-2.0"],
            "fully_present_plus2_reading": medians["2.0"],
            "seeds_per_dose": 32,
        },
    )
    inverted = float(
        recover_synthetic(2.0, 4.0, 0xC5E2FF, fit_defect="invert_q")[
            "q_h_frames"
        ]
    )
    add_plant(plants, "P2-inverted-curvature-sign", inverted < 0.0, inverted)

    # E3: nonlinear tilted planes are not bowls.
    null_good = []
    null_bad = []
    for i, angle in enumerate([-35.0, 0.0, 31.0]):
        null_good.append(
            float(recover_synthetic(0.0, 4.0, 0xC5E300 + i, angle_deg=angle)["q_h_frames"])
        )
        null_bad.append(
            float(
                recover_synthetic(
                    0.0,
                    4.0,
                    0xC5E300 + i,
                    angle_deg=angle,
                    fit_defect="naive_radial",
                )["q_h_frames"]
            )
        )
    add_control(
        controls,
        "E3-tilt-nonlinearity-null",
        max(abs(v) for v in null_good) <= 0.10,
        {"registered_q_h": null_good},
    )
    add_plant(
        plants,
        "P3-affine-plus-radius-leakage",
        max(abs(v) for v in null_bad) > 0.10,
        null_bad,
    )

    # E4: a pure-noise argmax is not a focus peak.
    noise_good = pure_noise_valid_fraction(False)
    noise_bad = pure_noise_valid_fraction(True)
    add_control(
        controls,
        "E4-pure-noise-refusal",
        noise_good < 0.02,
        {"valid_fraction": noise_good},
    )
    add_plant(
        plants,
        "P4-bypassed-peak-reality",
        noise_bad >= 0.02,
        noise_bad,
    )

    # E5: peak position remains a position as DOF broadens.
    widths = [2.0, 4.0, 8.0]
    width_q = [
        float(
            recover_synthetic(
                1.0,
                w,
                0xC5E500 + i,
                width_varies=True,
            )["q_h_frames"]
        )
        for i, w in enumerate(widths)
    ]
    e5_green = max(abs(v - width_q[0]) for v in width_q[1:]) <= 0.20 * abs(width_q[0])
    add_control(
        controls,
        "E5-aperture-width",
        e5_green,
        {"widths_frames": widths, "q_h": width_q},
    )
    x, y, g1, g2 = independent_response_generator(
        1.0, 8.0, 0xC5E5FF, width_varies=True
    )
    z_bad = []
    valid_bad = []
    xn = (x - WIDTH / 2) / (HEIGHT / 2)
    yn = (y - HEIGHT / 2) / (HEIGHT / 2)
    t = math.radians(17.0)
    vcoord = -math.sin(t) * xn + math.cos(t) * yn
    for i in range(len(x)):
        p = C.peaks_for_site(g1[:, i], g2[:, i])
        z_bad.append(float(p["k_primary_avg"]) + 0.65 * 8.0 * vcoord[i] ** 2)
        valid_bad.append(bool(p["valid"]))
    kk = np.asarray(valid_bad)
    width_defect_q = float(
        C.fit_surface(x[kk], y[kk], np.asarray(z_bad)[kk], WIDTH, HEIGHT)["q_h_frames"]
    )
    add_plant(
        plants,
        "P5-width-coupled-position",
        abs(width_defect_q - width_q[0]) > 0.20 * abs(width_q[0]),
        width_defect_q,
    )

    # E6: translating the optical centre changes linear terms, not q.
    centre0 = float(recover_synthetic(1.0, 4.0, 0xC5E600)["q_h_frames"])
    centre1 = float(
        recover_synthetic(
            1.0, 4.0, 0xC5E600, centre=(0.30, -0.22)
        )["q_h_frames"]
    )
    add_control(
        controls,
        "E6-centre-invariance",
        abs(centre1 - centre0) < 0.02,
        {"centred_q_h": centre0, "translated_q_h": centre1},
    )
    centre_bad = float(
        recover_synthetic(
            1.0,
            4.0,
            0xC5E600,
            centre=(0.30, -0.22),
            fit_defect="drop_linear",
        )["q_h_frames"]
    )
    add_plant(
        plants,
        "P6-dropped-linear-nuisance",
        abs(centre_bad - centre0) >= 0.02,
        centre_bad,
    )

    # E7: robustness is a property of all rungs, not the primary alone.
    ladder_good = mock_ladder_verdict(False)
    ladder_bad = mock_ladder_verdict(True)
    add_control(
        controls,
        "E7-ladder-verdict",
        ladder_good == "NOT ROBUST",
        {"registered": ladder_good},
    )
    add_plant(
        plants,
        "P7-primary-only-verdict",
        ladder_bad != "NOT ROBUST",
        ladder_bad,
    )

    # E8: independent decoder contract plus report checker self-tests.
    raw_reading, wrong_dimension_passed = raw_contract()
    checker = subprocess.run(
        [sys.executable, str(HERE / "check_results.py"), "--self-test"],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        checker_result = json.loads(checker.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"checker self-test was not JSON: {checker.stdout}") from exc
    add_control(
        controls,
        "E8-raw-contract-and-checker",
        bool(
            raw_reading["contract_green"]
            and checker.returncode == 0
            and checker_result["baseline_green"]
        ),
        {"raw": raw_reading, "checker": checker_result},
    )
    add_plant(
        plants,
        "P8-wrong-active-dimension",
        not wrong_dimension_passed,
        {"wrong_dimension_passed": wrong_dimension_passed},
    )
    add_plant(
        plants,
        "P9-stale-deciding-number",
        bool(checker_result["number_plant_red"]),
        checker_result["number_plant_red"],
    )
    add_plant(
        plants,
        "P10-flipped-report-verdict",
        bool(checker_result["verdict_plant_red"]),
        checker_result["verdict_plant_red"],
    )

    # E9 (Amendment A2): the production Sobel path sees one 2-D plane.
    image_reading, wrong_axis_peak = image_response_control()
    add_control(
        controls,
        "E9-image-response-axis",
        bool(
            image_reading["production_peak_frame"]
            == image_reading["fixed_in_focus_frame"]
            and image_reading["strictly_decreases_with_blur"]
        ),
        image_reading,
    )
    add_plant(
        plants,
        "P11-frame-axis-sobel",
        wrong_axis_peak != int(image_reading["fixed_in_focus_frame"]),
        wrong_axis_peak,
    )

    summary = {
        "controls": len(controls),
        "controls_green": sum(bool(r["green"]) for r in controls),
        "plants": len(plants),
        "plants_red": sum(bool(r["red"]) for r in plants),
    }
    result = {
        "status": (
            "GREEN"
            if summary["controls"] == summary["controls_green"]
            and summary["plants"] == summary["plants_red"]
            else "RED"
        ),
        "summary": summary,
        "controls": controls,
        "plants": plants,
    }
    (OUT / "commission.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
