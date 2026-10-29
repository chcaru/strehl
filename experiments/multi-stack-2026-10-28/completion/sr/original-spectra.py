"""Descriptive original-grid spectra, with injected-noise and alias controls."""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def spectrum(signal, variance):
    h, w = signal.shape
    window = np.outer(np.hanning(h), np.hanning(w))
    weight = window.sum()
    mean = np.sum(signal * window) / weight
    ft = np.fft.fft2(window * (signal - mean))
    window_ft = np.fft.fft2(window)
    # Exact constant-variance expectation for the weighted-mean-removal
    # operator. This is the injected model, not a fitted spectral noise floor.
    kernel_energy = (np.sum(window**2)
                     - 2 * np.real(np.fft.fft2(window**2) * window_ft.conj()) / weight
                     + abs(window_ft)**2 * np.sum(window**2) / weight**2)
    expected = variance * np.maximum(kernel_energy, 0)
    observed = abs(ft)**2
    fy, fx = np.meshgrid(np.fft.fftfreq(h), np.fft.fftfreq(w), indexing="ij")
    masks = {
        "horizontal": (abs(fx) >= .35) & (abs(fx) <= .5) & (abs(fy) <= .125),
        "vertical": (abs(fy) >= .35) & (abs(fy) <= .5) & (abs(fx) <= .125),
        "any_axis": (np.maximum(abs(fx), abs(fy)) >= .35),
    }
    return {name: {"bins": int(mask.sum()),
                   "observed_energy": float(observed[mask].sum()),
                   "injected_noise_energy": float(expected[mask].sum()),
                   "signed_excess_energy": float((observed[mask] - expected[mask]).sum()),
                   "observed_to_noise": float(observed[mask].sum() / expected[mask].sum()) if expected[mask].sum() else None}
            for name, mask in masks.items()}


def controls():
    n = 96
    yy, xx = np.mgrid[:n, :n]
    flat = spectrum(np.full((n, n), 500.), 0.)
    assert all(b["observed_energy"] < 1e-15 for b in flat.values())
    rng = np.random.default_rng(183728)
    ratios = np.array([[b["observed_to_noise"] for b in spectrum(500. + rng.normal(0, 10, (n, n)), 100.).values()] for _ in range(128)])
    assert np.all(abs(ratios.mean(axis=0) - 1) < .04), ratios.mean(axis=0)
    # Distinct continuous frequencies .4 and .6 cycles/quad are the same
    # physical sampled cosine: a direct proof this instrument cannot certify
    # which side of the original CFA Nyquist the optics transmitted.
    a = 500. + 50 * np.cos(2*np.pi*.4*xx)
    b = 500. + 50 * np.cos(2*np.pi*.6*xx)
    assert np.allclose(a, b, rtol=0, atol=2e-11)
    high = spectrum(a, 100.)
    low = spectrum(500. + 50*np.cos(2*np.pi*.08*xx), 100.)
    assert high["horizontal"]["observed_to_noise"] > 10
    assert high["vertical"]["observed_to_noise"] < .001
    assert low["any_axis"]["observed_to_noise"] < .001
    return {"flat_first": flat, "noisy_flat_128_mean_ratios": ratios.mean(axis=0).tolist(),
            "known_high_band": high, "known_low_band": low,
            "optically_distinct_aliases_have_identical_samples": True,
            "frequency_units": "cycles per original same-color quad; sensor frequency is half this"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--controls", action="store_true")
    p.add_argument("--input", type=Path, action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = {"schema": "strehl.original-sampled-spectra.v1", "command": sys.argv,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Descriptive original-grid signal near same-color Nyquist; aliases indistinguishable, window leakage possible, no optical cutoff or reconstruction quality certificate. Constant local variance from injected camera model at weighted patch mean; spatial nonstationarity and target-derived mean limit the noise comparison."}
    if a.controls:
        result["controls"] = controls()
    records = []
    for path in a.input:
        manifest = json.loads(path.read_text())
        for source in manifest["records"]:
            raw = (path.parent / source["file"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == source["sha256"]
            n = source["side_quad"]
            codes = np.frombuffer(raw, dtype="<u2").reshape(n, n)
            signal = codes.astype(float) - source["black"]
            window = np.outer(np.hanning(n), np.hanning(n))
            mean = np.sum(window*signal) / window.sum()
            variance = source["gain_dn_per_e"]*max(mean, 0) + (source["gain_dn_per_e"]*source["read_noise_e"])**2
            clipped = int(np.sum(codes >= source["white"]))
            record = {"manifest": str(path), "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "source": source, "weighted_signal_mean_dn": float(mean),
                      "injected_variance_dn2": float(variance), "clipped_original_codes": clipped}
            if clipped:
                record["status"] = "clipped; no spectral noise interpretation"
            else:
                record["status"] = "descriptive unclipped sampled spectrum"
                record["bands"] = spectrum(signal, variance)
            records.append(record)
    result["records"] = records
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"out": str(a.out), "controls": a.controls, "records": len(records)}))


if __name__ == "__main__":
    main()
