from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
M70_SRC = ROOT / "experiments" / "M70-through-focus-spectrum" / "src"
M71 = ROOT / "experiments" / "M71-flat-fields"
M71_CACHE = M71 / "out" / "cache"
M76B_RESULT = ROOT / "experiments" / "M76b-reconciliations" / "out" / "item1.json"
DARK = Path(r"D:\macro-dark-frames")

sys.path.insert(0, str(M70_SRC))
import m70lib as M  # noqa: E402
import s04_through_focus as S4  # noqa: E402
import s05_analyse as A5  # noqa: E402

spec = importlib.util.spec_from_file_location("m71_kappa", M71 / "src" / "05-kappa.py")
m71_kappa = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m71_kappa)

L = M.L
PATCH = 256
TILE = 128
BANDS = tuple(M.MID_BANDS)
PAIRS = [
    ("e0.004-A", "e0.004-B"),
    ("e0.008-A", "e0.008-B"),
    ("e0.016666666666666666-A", "e0.016666666666666666-B"),
    ("e0.03333333333333333-A", "e0.03333333333333333-B"),
    ("e0.05-A", "e0.05-B"),
]
ROW_ISO = {
    "109MSDCF": 160,
    "112MSDCF": 500,
    "coffee-bean": 50,
    "bee-1": 100,
    "bee-2": 400,
    "bee-3": 100,
}
M76B_ROWS = json.loads(M76B_RESULT.read_text(encoding="utf-8"))["rows"]
ROWS = [
    (
        row["stack"],
        ROW_ISO[row["stack"]],
        row["level_dn"],
        row["remainder_dn2"],
        row["e_flat_dn2"],
    )
    for row in M76B_ROWS
]
KAPPA = 0.003096
SEED = 76003
BOOT = 10_000
DARK_FOLDERS = {50: "122MSDCF", 100: "118MSDCF", 200: "123MSDCF",
                400: "119MSDCF", 500: "125MSDCF"}
M4_SIGMA_FPN = {50: 0.3730, 100: 0.3768, 200: 0.3420,
                400: 0.3756, 500: 0.3966}


def gq_patch_from_planes(g1: np.ndarray, g2: np.ndarray, rc: int, cc: int,
                         size: int = PATCH) -> np.ndarray:
    u0 = (rc + cc) // 2
    v0 = (rc - cc) // 2
    k = np.arange(size) - size // 2
    u = (u0 + k)[:, None]
    v = (v0 + k)[None, :]
    r = u + v
    c = u - v + 1
    out = np.empty((size, size), dtype=np.float32)
    even = (r & 1) == 0
    out[even] = g1[(r[even] // 2), ((c[even] - 1) // 2)]
    out[~even] = g2[((r[~even] - 1) // 2), (c[~even] // 2)]
    return out


def cross_bands(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    starts = L.tile_starts(PATCH, TILE)
    w = L.window_2d(TILE, "hann")
    wnorm = float((w * w).sum())
    acc = np.zeros((TILE, TILE), dtype=np.float64)
    n = 0
    for y in starts:
        for x in starts:
            ta = a[y:y + TILE, x:x + TILE].astype(np.float64)
            tb = b[y:y + TILE, x:x + TILE].astype(np.float64)
            fa = np.fft.fft2((ta - ta.mean()) * w)
            fb = np.fft.fft2((tb - tb.mean()) * w)
            acc += np.real(fa * np.conj(fb)) / wnorm
            n += 1
    f, p, counts = L.radial_psd(acc / n, "GQ", "iso")
    ba = M.band_average(f, p, counts)
    return {name: float(ba[name][0]) for name in BANDS}


def boot_matrix(mat: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    n_pair, n_patch = mat.shape
    out = np.empty(BOOT)
    for d in range(BOOT):
        pi = rng.integers(0, n_pair, n_pair)
        vals = []
        for p in pi:
            ji = rng.integers(0, n_patch, n_patch)
            vals.append(float(mat[p, ji].mean()))
        out[d] = np.mean(vals)
    return out


def flat_arm(rng: np.random.Generator) -> dict:
    print("=" * 100)
    print("ARM A — total repeating multiplicative green power on M71 true flats")
    print("=" * 100)
    mat = np.zeros((len(PAIRS), len(S4.CENTRES)))
    by_band: list[list[dict[str, float]]] = []
    for ip, (ta, tb) in enumerate(PAIRS):
        residuals = {}
        for tag in (ta, tb):
            for plane in ("G1", "G2"):
                mean = np.load(M71_CACHE / f"{tag}-{plane}-mean.npy")
                residuals[(tag, plane)] = m71_kappa.residual(mean)
                del mean
        pair_bands = []
        for j, (rc, cc) in enumerate(S4.CENTRES):
            a = gq_patch_from_planes(residuals[(ta, "G1")],
                                       residuals[(ta, "G2")], rc, cc)
            b = gq_patch_from_planes(residuals[(tb, "G1")],
                                       residuals[(tb, "G2")], rc, cc)
            bands = cross_bands(a, b)
            pair_bands.append(bands)
            mat[ip, j] = np.mean(list(bands.values()))
        by_band.append(pair_bands)
        print(f"{ta[:-2]:26s} V_flat={mat[ip].mean():.8e} "
              f"k={100*math.sqrt(max(mat[ip].mean(), 0)):.4f}% "
              f"patch range {mat[ip].min():+.3e}..{mat[ip].max():+.3e}")
        del residuals

    v = float(mat.mean())
    boots = boot_matrix(mat, rng)
    ci = np.percentile(boots, [2.5, 97.5])
    sum_s2 = sum(r[2] ** 2 for r in ROWS)
    sum_r = sum(r[3] for r in ROWS)

    def f_mult(x: float) -> float:
        return max(x - KAPPA**2, 0.0) * sum_s2 / sum_r

    fboots = np.array([f_mult(x) for x in boots])
    fci = np.percentile(fboots, [2.5, 97.5])
    print(f"\npooled V_flat={v:.8e} 95% [{ci[0]:.8e}, {ci[1]:.8e}]")
    print(f"k_total={100*math.sqrt(max(v, 0)):.4f}%  M71 kappa={100*KAPPA:.4f}%")
    print(f"V_extra=max(V_flat-kappa^2,0)={max(v-KAPPA**2,0):.8e}")
    print(f"F_mult={f_mult(v):.5f} 95% [{fci[0]:.5f}, {fci[1]:.5f}] of remainder")
    return {
        "pair_patch_values": mat.tolist(),
        "pair_values": mat.mean(axis=1).tolist(),
        "patch_values": mat.mean(axis=0).tolist(),
        "by_band": by_band,
        "v_flat": v,
        "v_flat_ci95": ci.tolist(),
        "k_total": math.sqrt(max(v, 0)),
        "v_extra": max(v - KAPPA**2, 0),
        "f_mult": f_mult(v),
        "f_mult_ci95": fci.tolist(),
        "_boots": boots,
        "_fboots": fboots,
    }


def synthetic_controls(rng: np.random.Generator) -> dict:
    print("\n" + "=" * 100)
    print("CONTROLS — fixed-pattern plant, independent null, and shift null")
    print("=" * 100)
    sum_s2 = sum(r[2] ** 2 for r in ROWS)
    sum_r = sum(r[3] for r in ROWS)
    vplant = sum_r / sum_s2
    planted = []
    independent = []
    patches = []
    for _ in range(24):
        common = rng.normal(0.0, math.sqrt(vplant), (PATCH, PATCH)).astype(np.float32)
        a = common + rng.normal(0.0, 0.01, common.shape).astype(np.float32)
        b = common + rng.normal(0.0, 0.01, common.shape).astype(np.float32)
        planted.append(np.mean(list(cross_bands(a, b).values())))
        ia = rng.normal(0.0, math.sqrt(vplant), common.shape).astype(np.float32)
        ib = rng.normal(0.0, math.sqrt(vplant), common.shape).astype(np.float32)
        independent.append(np.mean(list(cross_bands(ia, ib).values())))
        patches.append(common)
    recovered = float(np.mean(planted))
    null = float(np.mean(independent))
    null_se = float(np.std(independent, ddof=1) / math.sqrt(len(independent)))

    base = patches[0]
    unshifted = float(np.mean(list(cross_bands(base, base).values())))
    shifts = np.empty(1000)
    for i in range(1000):
        dy, dx = rng.integers(32, 225, 2)
        shifted = np.roll(np.roll(base, int(dy), axis=0), int(dx), axis=1)
        shifts[i] = np.mean(list(cross_bands(base, shifted).values()))
    shift_mean = float(shifts.mean())
    shift_sd = float(shifts.std(ddof=1))
    z_shift = (unshifted - shift_mean) / shift_sd
    recovery = recovered / vplant
    z_null = null / null_se
    print(f"V_plant={vplant:.8e}; recovered={recovered:.8e} ({recovery:.4f}x)")
    print(f"independent null={null:+.8e}, SE={null_se:.3e}, z={z_null:+.3f}")
    print(f"shift null mean={shift_mean:+.8e}, sd={shift_sd:.3e}, "
          f"unshifted z={z_shift:.1f}")
    return {
        "v_plant": vplant,
        "recovered": recovered,
        "recovery_ratio": recovery,
        "independent_null": null,
        "independent_null_se": null_se,
        "independent_null_z": z_null,
        "shift_mean": shift_mean,
        "shift_sd": shift_sd,
        "unshifted": unshifted,
        "unshifted_shift_z": z_shift,
        "plant_pass": 0.9 <= recovery <= 1.1,
        "independent_pass": abs(z_null) <= 3.0,
        "shift_pass": z_shift >= 10.0,
    }


def dark_patch_means(folder: Path) -> tuple[np.ndarray, np.ndarray]:
    fs = sorted(folder.glob("*.ARW"))[2:]
    assert len(fs) == 20, (folder, len(fs))
    sums = [np.zeros((len(S4.CENTRES), PATCH, PATCH), dtype=np.float64)
            for _ in range(2)]
    for i, path in enumerate(fs):
        active = L.load_active(str(path))
        half = 0 if i < 10 else 1
        for j, (rc, cc) in enumerate(S4.CENTRES):
            sums[half][j] += L.crop_lattice(active, "GQ", rc, cc, PATCH)
        del active
    return (sums[0] / 10.0).astype(np.float32), (sums[1] / 10.0).astype(np.float32)


def dark_arm(rng: np.random.Generator) -> dict:
    print("\n" + "=" * 100)
    print("ARM B — additive fixed power from M4 darks")
    print("=" * 100)
    result = {}
    for iso, folder in DARK_FOLDERS.items():
        a, b = dark_patch_means(DARK / folder)
        vals = np.array([
            np.mean(list(cross_bands(a[j], b[j]).values()))
            for j in range(len(S4.CENTRES))
        ])
        boot = np.array([
            vals[rng.integers(0, len(vals), len(vals))].mean()
            for _ in range(BOOT)
        ])
        ci = np.percentile(boot, [2.5, 97.5])
        point = float(vals.mean())
        total = M4_SIGMA_FPN[iso] ** 2
        print(f"ISO {iso:3d}: V_dark={point:+.7f} DN^2 "
              f"95% [{ci[0]:+.7f},{ci[1]:+.7f}] "
              f"M4 total bound={total:.7f}")
        result[str(iso)] = {
            "folder": folder,
            "patch_values": vals.tolist(),
            "v_dark": point,
            "ci95": ci.tolist(),
            "m4_total_bound": total,
        }

    def for_iso(iso: int, key: str) -> float:
        if iso == 160:
            return max(result["100"][key], result["200"][key])
        return result[str(iso)][key]

    sum_r = sum(r[3] for r in ROWS)
    measured_sum = sum(max(for_iso(iso, "v_dark"), 0.0)
                       for _, iso, _, _, _ in ROWS)
    total_sum = sum(for_iso(iso, "m4_total_bound")
                    for _, iso, _, _, _ in ROWS)
    f_add = measured_sum / sum_r
    f_add_upper = total_sum / sum_r
    nonnegative = sum(1 for v in result.values() if v["v_dark"] >= 0)
    below_total = all(v["ci95"][1] <= v["m4_total_bound"] for v in result.values())
    control = nonnegative >= 4 and below_total
    print(f"\nF_add measured={f_add:.7f}; M4-total conservative upper={f_add_upper:.7f}")
    print(f"dark control: nonnegative {nonnegative}/5, upper CI <= total "
          f"{'5/5' if below_total else 'FAIL'} -> {'PASS' if control else 'FAIL'}")
    return {
        "iso": result,
        "measured_sum_dn2": measured_sum,
        "total_bound_sum_dn2": total_sum,
        "f_add": f_add,
        "f_add_upper": f_add_upper,
        "nonnegative_count": nonnegative,
        "below_total_all": below_total,
        "control_pass": control,
    }


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    aa = a - a.mean()
    bb = b - b.mean()
    den = math.sqrt(float((aa * aa).sum() * (bb * bb).sum()))
    return float((aa * bb).sum() / den) if den else float("nan")


def scene_arm(rng: np.random.Generator) -> dict:
    print("\n" + "=" * 100)
    print("ARM C — sensor-coordinate repetition across M70 stacks")
    print("=" * 100)
    stacks = [
        "coffee-bubbles", "109MSDCF", "119MSDCF", "113MSDCF", "112MSDCF",
        "foam", "coffee-bean", "wrapped-text-2", "wrapped-text-1",
        "bee-1", "bee-2", "bee-3",
    ]
    q = {}
    for st in stacks:
        d = A5.load(st)
        nvar = M.noise_var_dn2(d["level"], d["iso"])
        mid = [d["bands"].index(b) for b in BANDS]
        rel = (d["power"][:, :, mid] - nvar[:, :, None]) / np.maximum(
            d["level"][:, :, None] ** 2, 1e-30
        )
        q[st] = rel.mean(axis=(0, 2))

    same_set = {
        tuple(sorted(x)) for x in [
            ("112MSDCF", "113MSDCF"),
            ("wrapped-text-1", "wrapped-text-2"),
            ("bee-1", "bee-2"), ("bee-1", "bee-3"), ("bee-2", "bee-3"),
        ]
    }
    same, unrelated = {}, {}
    for i, a in enumerate(stacks):
        for b in stacks[i + 1:]:
            key = tuple(sorted((a, b)))
            r = pearson(q[a], q[b])
            (same if key in same_set else unrelated)[f"{a}|{b}"] = r

    same_obs = float(np.median(list(same.values())))
    unrel_obs = float(np.median(list(unrelated.values())))
    same_null = np.empty(BOOT)
    unrel_null = np.empty(BOOT)
    same_pairs = [k.split("|") for k in same]
    unrel_pairs = [k.split("|") for k in unrelated]
    for d in range(BOOT):
        same_null[d] = np.median([
            pearson(q[a], q[b][rng.permutation(24)]) for a, b in same_pairs
        ])
        unrel_null[d] = np.median([
            pearson(q[a], q[b][rng.permutation(24)]) for a, b in unrel_pairs
        ])
    same95 = float(np.percentile(same_null, 95))
    unrel95 = float(np.percentile(unrel_null, 95))
    scene_pass = same_obs > same95
    sensor_repeat = unrel_obs > unrel95
    print(f"same-subject median r={same_obs:+.4f}; null p95={same95:+.4f} "
          f"-> {'SENSITIVE' if scene_pass else 'INSENSITIVE'}")
    print(f"unrelated median r={unrel_obs:+.4f}; null p95={unrel95:+.4f} "
          f"-> {'REPEATS' if sensor_repeat else 'NO REPEAT'}")
    print("same-subject pairs:")
    for k, v in same.items():
        print(f"  {k:34s} {v:+.4f}")
    return {
        "vectors": {k: v.tolist() for k, v in q.items()},
        "same": same,
        "unrelated": unrelated,
        "same_median": same_obs,
        "unrelated_median": unrel_obs,
        "same_null_p95": same95,
        "unrelated_null_p95": unrel95,
        "scene_control_pass": scene_pass,
        "sensor_repeat": sensor_repeat,
    }


def consequences(flat: dict, controls: dict, dark: dict) -> dict:
    f_mult_lo, f_mult_hi = flat["f_mult_ci95"]
    f_sensor = flat["f_mult"] + dark["f_add"]
    f_lo = f_mult_lo
    f_hi = f_mult_hi + dark["f_add_upper"]
    arm_a_controls = all(controls[k] for k in (
        "plant_pass", "independent_pass", "shift_pass"
    ))
    if not arm_a_controls or not dark["control_pass"]:
        verdict = "INCONCLUSIVE"
    elif f_hi < 0.5:
        verdict = "SCENE-DOMINATED REMAINDER"
    elif f_lo > 0.5:
        verdict = "SENSOR-DOMINATED REMAINDER"
    else:
        verdict = "SPLIT OR UNDECIDABLE"

    m71_ptc = json.loads((M71 / "data" / "03-ptc.json").read_text(encoding="utf-8"))
    g = 0.5 * (m71_ptc["G1"]["g"] + m71_ptc["G2"]["g"])
    sigma0 = 0.961538
    v_extra_hi = max(flat["v_flat_ci95"][1] - KAPPA**2, 0.0)
    dark_hi_100 = M4_SIGMA_FPN[100] ** 2

    def sigma_existing(s: float) -> float:
        return math.sqrt(g * s + sigma0**2 + (KAPPA * s) ** 2)

    def sigma_upper(s: float) -> float:
        return math.sqrt(g * s + sigma0**2 + (KAPPA * s) ** 2
                         + v_extra_hi * s**2 + dark_hi_100)

    sigma_move_8000 = sigma_upper(8000) / sigma_existing(8000) - 1
    gate_flag = sigma_move_8000 >= 0.02

    remaining = []
    for stack, iso, level, _, e_flat in ROWS:
        dark_point = max(
            dark["iso"][str(100 if iso == 160 else iso)]["v_dark"]
            if iso != 160
            else max(dark["iso"]["100"]["v_dark"],
                     dark["iso"]["200"]["v_dark"]),
            0.0,
        )
        value = e_flat - flat["v_flat"] * level**2 - dark_point
        remaining.append((stack, level, value))
    positive = [(level, value) for _, level, value in remaining if value > 0]
    lx = np.log([x for x, _ in positive])
    ly = np.log([y for _, y in positive])
    slope, intercept = np.polyfit(lx, ly, 1)
    pred = intercept + slope * lx
    r2 = 1.0 - float(np.sum((ly - pred) ** 2) / np.sum((ly - ly.mean()) ** 2))
    print("\n" + "=" * 100)
    print("DECISION AND CONSEQUENCES")
    print("=" * 100)
    print(f"F_sensor point={f_sensor:.5f}; decision interval [0,{f_hi:.5f}]")
    print(f"VERDICT: {verdict}")
    print(f"post-fixed-term remainder exponent={slope:.4f}, R^2={r2:.4f} "
          f"({len(positive)}/{len(remaining)} positive rows)")
    print(f"upper-bound sigma movement at S=8000: {100*sigma_move_8000:.3f}% "
          f"-> M77 {'FLAG' if gate_flag else 'NO FLAG'}")
    return {
        "f_sensor_point": f_sensor,
        "f_sensor_lower": f_lo,
        "f_sensor_upper": f_hi,
        "verdict": verdict,
        "arm_a_controls_pass": arm_a_controls,
        "post_fixed_rows": [
            {"stack": stack, "level_dn": level, "remainder_dn2": value}
            for stack, level, value in remaining
        ],
        "post_fixed_exponent": float(slope),
        "post_fixed_r2": r2,
        "v_extra_upper": v_extra_hi,
        "dark_upper_iso100": dark_hi_100,
        "sigma_move_upper_at_8000": sigma_move_8000,
        "m77_flag": gate_flag,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    flat = flat_arm(rng)
    controls = synthetic_controls(rng)
    dark = dark_arm(rng)
    scene = scene_arm(rng)
    decision = consequences(flat, controls, dark)
    serial_flat = {k: v for k, v in flat.items() if not k.startswith("_")}
    result = {
        "constants": {
            "patch": PATCH, "tile": TILE, "bands": BANDS, "seed": SEED,
            "bootstrap_reps": BOOT, "kappa": KAPPA,
        },
        "flat": serial_flat,
        "controls": controls,
        "dark": dark,
        "scene": scene,
        "decision": decision,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT / 'result.json'}")


if __name__ == "__main__":
    main()
