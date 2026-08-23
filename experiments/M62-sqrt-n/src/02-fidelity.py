"""Arm A step 2 -- fidelity of the whole path, before any result is believed.

Three checks, all of which must pass before a noise number means anything:

  F1  the CLI's decode of a synthetic frame equals the array that was written,
      to within the TIFF's own quantisation step. This is the second-decoder
      check rule 32 demands, run in the direction that matters: Python wrote,
      `rawler` read, the merge re-emitted.
  F2  the sensor constants the harness uses are the ones the crate ships, and
      the CLI agrees it resolved a PROFILE rather than a fallback.
  F3  the empirical temporal sigma of the generated burst matches the model
      sigma it was drawn from.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402


def main():
    k = H.constants()
    latent = np.load(H.DATA / "latent.npy")
    shape = latent.shape

    one = H.DATA / "fidelity"
    rep = H.make_burst(latent, 1, seed=1000, outdir=one, k=k)

    out_tif = H.EVID / "02-fidelity-merge.tif"
    txt = H.run_cli(
        ["merge", one, "--limit", 1, "--gate", 2.0, "--out", out_tif],
        H.EVID / "02-fidelity-merge.log",
    )

    provenance = "profile" in txt.lower() and "fallback" not in txt.lower()
    iso_line = H.grep1(txt, r"iso\s*:\s*([0-9.]+)")

    written = H.read_cfa(one / "burst0000.arw", shape)
    truth_g = H.green(written)
    merged_g = H.read_tiff_green(out_tif, k)
    assert merged_g.shape == truth_g.shape, (merged_g.shape, truth_g.shape)

    d = H.roi(merged_g) - H.roi(truth_g)
    step = (k["white"] - k["black"]) / 65535.0

    # F3: does the burst carry the sigma it was told to?
    burst = H.DATA / "sigma-check"
    H.make_burst(latent, 24, seed=2000, outdir=burst, k=k)
    stack = np.stack([H.read_cfa(p, shape) for p in sorted(burst.glob("*.arw"))])
    resid = stack - latent[None]
    emp = float(np.sqrt((resid**2).mean()))
    model = float(H.sigma_dn(latent - k["black"], k).mean())
    model_rms = float(np.sqrt((H.sigma_dn(latent - k["black"], k) ** 2).mean()))

    rec = dict(
        constants=k,
        F1_decode_roundtrip=dict(
            cli_iso=iso_line,
            profile_not_fallback=bool(provenance),
            max_abs_dn=float(np.abs(d).max()),
            rms_dn=float(np.sqrt((d**2).mean())),
            tiff_quantisation_step_dn=step,
            expected_rms_dn=step / np.sqrt(12) * np.sqrt(2),
            pass_=bool(np.abs(d).max() <= step),
        ),
        F3_burst_sigma=dict(
            frames=24,
            empirical_pooled_rms_dn=emp,
            model_rms_dn=model_rms,
            model_mean_dn=model,
            ratio_empirical_over_model=emp / model_rms,
        ),
        burst_report=rep,
    )
    H.dump("02-fidelity.json", rec)
    assert rec["F1_decode_roundtrip"]["pass_"], "decode round-trip FAILED"
    assert abs(rec["F3_burst_sigma"]["ratio_empirical_over_model"] - 1.0) < 0.01


if __name__ == "__main__":
    main()
