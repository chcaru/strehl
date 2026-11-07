"""Derived optical/sampling limits; deliberately not a measured camera benchmark."""
import hashlib
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/sony-upgrade-2026-11-07"
P33 = np.float32(5.12)
P61 = np.float32(35.7 * 1000 / 9504)
N_RANGE = (5.6 * 2.412, 5.6 * 3.064)
nodes, weights = np.polynomial.legendre.leggauss(256)
NODES = nodes.astype(np.float32)
WEIGHTS = weights.astype(np.float32)


def diffraction(frequency, wavelength_um, working_f):
    nu = np.asarray(frequency, dtype=np.float32) * np.float32(wavelength_um * working_f / 1000)
    safe = np.clip(nu, 0, 1)
    return np.float32(2 / np.pi) * (np.arccos(safe) - safe * np.sqrt(np.maximum(0, 1 - safe * safe)))


def pixel_aperture(frequency, pitch_um):
    # Uniform square photosite aperture, along a sensor axis. Real microlens/
    # diffusion response is unmeasured. Pixel shift never changes this width.
    return np.sinc(np.asarray(frequency, dtype=np.float32) * np.float32(pitch_um / 1000))


def defocused_otf(frequency, wavelength_um, working_f, magnification, object_offset_um):
    nu = np.asarray(frequency, dtype=np.float32) * np.float32(wavelength_um * working_f / 1000)
    length = np.maximum(0, 1 - nu)
    x = length[:, None] * (NODES[None, :] + 1) / np.float32(2)
    upper = np.sqrt(np.maximum(0, 1 - (x + nu[:, None]) ** 2))
    # Paraxial longitudinal magnification m^2. Quadratic pupil phase only.
    phi = np.float32(np.pi * magnification ** 2 * object_offset_um / (4 * wavelength_um * working_f ** 2))
    integrand = upper * np.cos(np.float32(4) * phi * nu[:, None] * x)
    return np.float32(4 / np.pi) * length / np.float32(2) * np.sum(integrand * WEIGHTS, axis=1, dtype=np.float32)


def threshold(frequency, mtf, target):
    return float(np.interp(target, mtf[::-1], frequency[::-1]))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = np.linspace(0, 300, 3001, dtype=np.float32)
    n, wavelength, magnification, spacing = 15.5, .55, 2.7198, 40.
    optical = diffraction(f, wavelength, n)
    assert float(optical[0]) == 1
    assert np.all(optical[f > 1000 / (wavelength * n)] == 0)
    numeric = defocused_otf(f, wavelength, n, magnification, 0)
    zero_error = float(np.max(np.abs(numeric - optical)))
    assert zero_error < 2e-5, zero_error
    old = optical * pixel_aperture(f, P33)
    new = optical * pixel_aperture(f, P61)
    # Same detector aperture, regardless of the requested reconstruction grid.
    ps16 = optical * pixel_aperture(f, P61)
    assert np.array_equal(new, ps16)
    assert np.sqrt(.5) < 1

    rows = []
    for working_f in [N_RANGE[0], n, N_RANGE[1]]:
        row = {"working_f": working_f, "cutoff_lp_mm": {}, "airy_diameter_um": 2.44 * .55 * working_f}
        for label, wave in [("blue_450nm", .45), ("green_550nm", .55), ("red_650nm", .65)]:
            row["cutoff_lp_mm"][label] = 1000 / (wave * working_f)
        for label, pitch in [("a7c2", P33), ("a7cr", P61)]:
            curve = diffraction(f, .55, working_f) * pixel_aperture(f, pitch)
            row[label] = {"mtf50_lp_mm": threshold(f, curve, .5), "mtf10_lp_mm": threshold(f, curve, .1),
                          "mtf_at_80_lp_mm": float(curve[800]), "mtf_at_100_lp_mm": float(curve[1000])}
        rows.append(row)
    focus_rows = []
    for working_f in [N_RANGE[0], n, N_RANGE[1]]:
        for native_step in [32., 40., 49.]:
            best = diffraction(f, .55, working_f)
            coarse = defocused_otf(f, .55, working_f, magnification, native_step / 2)
            fine = defocused_otf(f, .55, working_f, magnification, native_step / 6)
            assert np.all(fine >= coarse - 1e-6)
            assert np.max(np.abs(defocused_otf(f, .55, working_f, magnification, 0) - best)) < 2e-5
            focus_rows.append({"working_f": working_f, "native_spacing_um": native_step,
                               "midpoint_mtf_ratio_60_lp_mm": float(fine[600] / coarse[600]),
                               "midpoint_mtf_ratio_80_lp_mm": float(fine[800] / coarse[800]),
                               "coarse_mtf50_lp_mm": threshold(f, coarse, .5),
                               "fine_mtf50_lp_mm": threshold(f, fine, .5),
                               "already_in_focus_gain": 1.})
    scenarios = []
    for label, planes, shift_count, output_mp, pitch in [
            ("A7C II current", 300, 1, 7008 * 4672 / 1e6, P33),
            ("A7C II fine focus", 900, 1, 7008 * 4672 / 1e6, P33),
            ("A7CR fine focus", 900, 1, 9504 * 6336 / 1e6, P61),
            ("A7CR fine + 4 shift", 900, 4, 9504 * 6336 / 1e6, P61),
            ("A7CR fine + 16 shift", 900, 16, 19008 * 12672 / 1e6, P61)]:
        captures = planes * shift_count
        scenarios.append({"name": label, "planes": planes, "raw_count": captures, "output_mp": output_mp,
                          "relative_integrated_exposure": captures / 300,
                          "ideal_same_output_snr_factor": float(np.sqrt(captures / 300)),
                          "exposure_only_minutes_at_0_2s": captures * .2 / 60,
                          "exposure_only_minutes_at_1s": captures / 60,
                          "relative_source_samples": captures / 300 *
                          ((7008 * 4672 if pitch == P33 else 9504 * 6336) / (7008 * 4672))})

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for label, wave, color in [("Blue: 450 nm", .45, "#477cc4"), ("Green: 550 nm", .55, "#328454"), ("Red: 650 nm", .65, "#ba4f4f")]:
        axes[0].plot(f, diffraction(f, wave, n) * pixel_aperture(f, P61), color=color, label=label)
    for x, label in [(1000 / (2 * P33), "33 MP grid"), (1000 / (2 * P61), "61 MP / 4-shot"), (1000 / P61, "16-shot grid")]:
        axes[0].axvline(x, color="#666666", linestyle="--", linewidth=.8)
        axes[0].text(x + 2, .83, label, rotation=90, va="top", fontsize=9)
    axes[0].set(xlim=(0, 285), ylim=(0, 1), xlabel="Sensor-plane frequency (line pairs/mm)", ylabel="Remaining contrast (MTF)",
                title="16-shot grid extends beyond the modeled optical signal")
    axes[0].legend(loc="upper right", fontsize=8)
    ideal = diffraction(f, wavelength, n) * pixel_aperture(f, P61)
    for label, offset, color in [("Exactly in focus", 0, "#444444"), ("300 planes: worst midpoint", spacing / 2, "#d37e2c"),
                                  ("900 planes: worst midpoint", spacing / 6, "#477cc4")]:
        curve = defocused_otf(f, wavelength, n, magnification, offset) * pixel_aperture(f, P61)
        axes[1].plot(f, curve, color=color, label=label)
    axes[1].set(xlim=(0, 135), ylim=(0, 1), xlabel="Sensor-plane frequency (line pairs/mm)", ylabel="Remaining contrast (MTF)",
                title="Finer focus reduces defocus; diffraction remains")
    axes[1].legend(fontsize=8)
    for axis in axes:
        axis.grid(alpha=.15)
    fig.suptitle("Illustrative physical model, not measured A7CR performance\nEffective f/15.5; ideal circular pupil; uniform 3.76 µm pixel aperture; focus example m=2.72, native spacing=40 µm", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "optical-limits.png", dpi=155)
    fig.savefig(OUT / "optical-limits.svg")
    plt.close(fig)
    result = {"classification": "DERIVED: analytical model, no new photographic quality measurement", "workers": 1,
              "environment": {"python": platform.python_version(), "numpy": np.__version__},
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "assumptions": {"n_range": N_RANGE, "representative_n": n, "magnification_example": magnification,
                              "native_step_example_um": spacing, "pixel_aperture": "uniform full-pitch square, axial response",
                              "omissions": "aberrations, measured CFA spectra, sensor MTF/OLPF, real pupil, coherence, drift, occlusion and merge behavior"},
              "controls": {"dc_and_cutoff": True, "quadrature_zero_defocus_max_error": zero_error,
                           "output_grid_cannot_change_optical_mtf": True, "in_focus_placebo": True},
              "sampling": {"pitch_a7c2_um": float(P33), "pitch_a7cr_um": float(P61),
                           "nyquist_a7c2_lp_mm": float(1000 / (2 * P33)), "nyquist_a7cr_lp_mm": float(1000 / (2 * P61)),
                           "nyquist_16shift_lp_mm": float(1000 / P61), "a7cr_pixel_area_ratio": float((P61 / P33) ** 2)},
              "optics": rows, "focus_examples": focus_rows, "scenarios": scenarios}
    def plain(value):
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value))
    (OUT / "model.json").write_text(json.dumps(result, indent=2, default=plain) + "\n")
    print(json.dumps({"controls": result["controls"], "sampling": result["sampling"],
                      "representative_optics": rows[1], "representative_focus": focus_rows[4],
                      "scenarios": scenarios}, indent=2, default=plain))


if __name__ == "__main__":
    main()
