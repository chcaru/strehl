"""Exploratory focus-band position on tilted targets; not an image-quality score."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import affine_transform, gaussian_filter, gaussian_filter1d
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/sony-focus-control-capture-review"
GAIN = np.float32(100 / 436.8)
READ_VAR = np.float32((4.2 * float(GAIN)) ** 2)
SIGMAS = (1.2, 8.0)
cv2.setNumThreads(1)


def kernel_energy(sigma):
    impulse = np.zeros((101, 101), np.float32)
    impulse[50, 50] = 1
    return float(sum(np.sum(gaussian_filter(impulse, sigma, order=o) ** 2, dtype=np.float32)
                     for o in ((1, 0), (0, 1))))


ENERGY = [kernel_energy(s) for s in SIGMAS]


def energies(green):
    signal = green.astype(np.float32) - np.float32(512)
    variance = np.maximum(signal, 0) * GAIN + READ_VAR
    result, floors = [], []
    for sigma, factor in zip(SIGMAS, ENERGY):
        dx = gaussian_filter(signal, sigma, order=(0, 1))
        dy = gaussian_filter(signal, sigma, order=(1, 0))
        # Local-constant noise approximation; tested first on homogeneous controls.
        floor = gaussian_filter(variance, sigma / np.sqrt(2)) * np.float32(factor)
        result.append(dx * dx + dy * dy - floor)
        floors.append(floor)
    return result, floors


def profiles(energy, slope, sections=3):
    h, w = energy[0].shape
    # Each frame is consumed independently; no aligned frame volume is stored.
    shear = [affine_transform(e, np.array([[1, -slope], [0, 1]], np.float32),
                              offset=[slope * w / 2, 0], order=1, mode="constant", cval=0)
             for e in energy]
    bounds = np.linspace(w * .12, w * .88, sections + 1).astype(int)
    curves = []
    for left, right in zip(bounds[:-1], bounds[1:]):
        numerator = gaussian_filter1d(np.sum(shear[0][:, left:right], axis=1, dtype=np.float32), 20)
        denominator = gaussian_filter1d(np.sum(shear[1][:, left:right], axis=1, dtype=np.float32), 20)
        valid = denominator > np.max(denominator) * .03
        curve = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=valid)
        curves.append(curve)
    return np.stack(curves)


def fit_curve(curve, centre=None):
    y = np.arange(len(curve), dtype=np.float32)
    lo, hi = int(len(curve) * .18), int(len(curve) * .85)
    if centre is not None:
        lo, hi = max(lo, int(centre - 500)), min(hi, int(centre + 500))
    good = (y >= lo) & (y < hi) & (curve > 0)
    x, target = y[good], curve[good]
    peak = float(x[np.argmax(target)])
    baseline = float(np.percentile(target, 10))
    amplitude = float(target.max() - baseline)
    def model(p):
        base, amp, position, width = map(np.float32, p)
        z = (x - position) / width
        return base + amp / np.sqrt(1 + z * z)
    # Explicit finite differences larger than f32 roundoff.
    fit = least_squares(lambda p: (model(p) - target).astype(np.float64),
                        [max(0, baseline), max(.01, amplitude), peak, 80],
                        bounds=([0, .001, lo, 5], [max(100, float(target.max())), 500, hi, 700]),
                        diff_step=1e-3, max_nfev=100)
    prediction = model(fit.x)
    r2 = 1 - float(np.sum((prediction-target)**2, dtype=np.float32) /
                   np.maximum(np.sum((target-target.mean())**2, dtype=np.float32), np.float32(1e-12)))
    return {"centre_green_px": float(fit.x[2]), "width_green_px": float(fit.x[3]),
            "amplitude": float(fit.x[1]), "r2": r2, "peak_green_px": peak,
            "at_bound": bool(abs(fit.x[2]-lo)<3 or abs(fit.x[2]-hi)<3)}


def controls():
    rng = np.random.default_rng(4607)
    level = np.float32(500)
    noise_sd = np.sqrt(level * GAIN + READ_VAR)
    flats = (512 + level + rng.normal(0, noise_sd, (5, 512, 512))).astype(np.float32)
    flat_results = []
    for flat in flats:
        energy, floors = energies(flat)
        ratio = float(np.mean(energy[0], dtype=np.float32) / np.mean(floors[0], dtype=np.float32))
        flat_results.append(ratio)
        assert abs(ratio) < .08, ratio
    # A flat/noise-only image cannot supply admitted structured focus signal.
    assert all(value < 3 for value in flat_results)
    h, w = 900, 1000
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    board = np.where(((xx // 33 + yy // 39).astype(np.int32) & 1) == 0, 200, 800).astype(np.float32)
    levels = np.array([.3, 1., 2., 4., 8., 16.], np.float32)
    blurred = [gaussian_filter(board, float(s)) for s in levels]
    fitted = []
    slope = .32
    for centre in (425, 445, 465):
        sigma = np.sqrt(np.float32(.7)**2 + ((yy + slope*(xx-w/2)-centre)*.035)**2)
        simulated = np.zeros((h, w), np.float32)
        for k in range(len(levels)-1):
            weight = np.clip((sigma-levels[k])/(levels[k+1]-levels[k]), 0, 1)
            select = (sigma >= levels[k]) & ((sigma < levels[k+1]) if k+1 < len(levels)-1 else True)
            simulated[select] = ((1-weight)*blurred[k] + weight*blurred[k+1])[select]
        simulated += rng.normal(0, np.sqrt(np.maximum(simulated, 0)*GAIN+READ_VAR)).astype(np.float32)
        energy, floors = energies(simulated+512)
        assert np.mean(energy[0]) > 3*np.mean(floors[0])
        fits = [fit_curve(c) for c in profiles(energy, slope)]
        fitted.append(float(np.median([f["centre_green_px"] for f in fits])))
    movement = np.diff(np.array(fitted))
    assert np.all(np.abs(movement-20) < 3), (fitted, movement)
    return {"flat_net_energy_over_noise": flat_results, "synthetic_centres": [425,445,465],
            "estimated_centres": fitted, "recovered_movements": movement.tolist(),
            "limitations": "Spatially varying blur plant validates position estimator only, not optical calibration."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--first-only", action="store_true")
    args = parser.parse_args()
    check = controls()
    (OUT / "band-controls.json").write_text(json.dumps(check, indent=2)+"\n")
    print("Flat and synthetic focus-band controls passed", flush=True)
    if args.controls_only:
        return
    inventory = json.loads((OUT / "inventory.json").read_text())
    records = []
    real_controls = []
    directions = []
    for run_index, run in enumerate(inventory["sessions"], 1):
        # Real featureless witnesses are checked before any run's sharpness fits.
        box = (750, 1900, 150, 150) if run_index == 1 else (40, 40, 150, 100)
        x, y, w, h = box
        witnesses = np.stack([np.load(OUT / "green-cfa" / f"run-{run_index}-{i:02d}.npy")[y:y+h,x:x+w]
                              for i in range(1,6)]).astype(np.float32)
        means = witnesses.mean(axis=(1,2), dtype=np.float32)
        residual = witnesses-means[:,None,None]
        temporal_sigma = float(np.sqrt(np.mean(np.var(residual,axis=0,ddof=1),dtype=np.float32)))
        predicted_sigma = float(np.sqrt((means.mean()-512)*GAIN+READ_VAR))
        ratios = []
        for witness in witnesses:
            en, floor = energies(witness)
            ratios.append(float(np.mean(en[0],dtype=np.float32)/np.mean(floor[0],dtype=np.float32)))
        assert max(ratios) < 3, (run_index, ratios)
        real_controls.append({"run":run_index,"green_box":box,"sensor_origin":[2*x+1,2*y],
            "sensor_size":[2*w,2*h],"frame_means_dn":means.tolist(),"temporal_sigma_dn":temporal_sigma,
            "profile_predicted_sigma_dn":predicted_sigma,"net_gradient_over_noise":ratios})
        first = np.load(OUT / "green-cfa" / f"run-{run_index}-01.npy").astype(np.float32)
        # Direction chosen from orientation previews, fixed before fine-step fits.
        slope = .35
        first_energy = energies(first)[0]
        if run_index == 2:
            coarse = [fit_curve(c)["centre_green_px"] for c in profiles(first_energy,slope)]
            bounds = np.linspace(first.shape[1]*.12,first.shape[1]*.88,4)
            centres = (bounds[:-1]+bounds[1:])/2
            slope -= float(np.polyfit(centres,coarse,1)[0])
        directions.append(slope)
        initial_profiles = profiles(first_energy, slope)
        initial_fits = [fit_curve(c) for c in initial_profiles]
        print(f"Run {run_index} baseline fits: {initial_fits}", flush=True)
        curves = []
        for frame in run["frames"][:1 if args.first_only else None]:
            ordinal = frame["ordinal"]
            green = np.load(OUT / "green-cfa" / f"run-{run_index}-{ordinal:02d}.npy")
            energy, floors = energies(green)
            structured = float(np.mean(energy[0]) / np.mean(floors[0]))
            curve = profiles(energy, slope)
            fits = [fit_curve(c, baseline["centre_green_px"]) for c,baseline in zip(curve,initial_fits)]
            curves.append(curve)
            records.append({"run":run_index,"ordinal":ordinal,"phase":frame["phase"],
                "repeat":frame["repeat"],"offset":frame["offset"],"approach_side":frame["approach_side"],
                "group_member":frame["group_member"],"structured_energy_over_noise":structured,"fits":fits})
            if ordinal % 12 == 0:
                print(f"Run {run_index}: focus profiles {ordinal}/73", flush=True)
        np.save(OUT / f"run-{run_index}-band-profiles.npy", np.stack(curves))
        fig, axes = plt.subplots(3, 1, figsize=(10,8), sharex=True)
        select = [0] if args.first_only else [0,4,8,10,11,14,22,55,56,63]
        for section, axis in enumerate(axes):
            for index in select:
                axis.plot(np.arange(curves[index].shape[1])*2, curves[index][section], label=str(index+1))
            axis.set_ylim(0, min(30,float(np.percentile(np.stack(curves)[:,section],99.5))))
            axis.set_ylabel(f"Section {section+1}\nfocus response")
        axes[0].legend(ncol=5, title="Image ordinal")
        axes[-1].set_xlabel(f"Tilt-normal coordinate, sensor pixels (slope {slope:.4f})")
        fig.suptitle(f"Run {run_index}: exploratory sharp-band profiles; not resolution scores")
        fig.tight_layout()
        fig.savefig(OUT / f"run-{run_index}-focus-profiles.png", dpi=140)
        plt.close(fig)
    result = {"controls":check,"real_flat_controls":real_controls,"parameters":{"slopes":directions,"sigmas":SIGMAS,"gain":float(GAIN),
        "read_variance":float(READ_VAR),"energy_kernel_norms":ENERGY,"workers":1},"records":records,
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUT / ("band-first.json" if args.first_only else "band-results.json")).write_text(json.dumps(result,indent=2)+"\n")


if __name__ == "__main__":
    main()
