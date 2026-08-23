"""M62 -- the trap, audited against the CLI's own instrument.

Three things are checked here and none of them is a new arm:

  T1  the pre-registered prediction for the shipped flat-ROI high-pass
      invariant, against what the CLI actually printed. Convention matters and
      is stated: PREREGISTRATION.md quotes a REDUCTION FACTOR (reference over
      merged); the CLI prints a NOISE RATIO (merged over reference). They are
      reciprocals and the report says so rather than flipping quietly.
  T2  the 0.026% gap between the Python ideal mean and `strehl merge` at a gate
      that admits every frame, against the TIFF's own quantisation step.
  T3  the dynamic range each statistic has between a selector and an estimator,
      which is the whole argument for the capture.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness as H  # noqa: E402

N = 30
HP_G2 = (1.0 - 1.0 / 81.0)  # HP_NOISE_GAIN^2, flat_ratio.rs


def parsed(log):
    t = pathlib.Path(log).read_text(encoding="utf-8")
    ref = float(re.search(r"reference hp sd\s*:\s*median\s+([0-9.]+)", t).group(1))
    row = re.search(r"^\s*[0-9.]+\s+([0-9.]+)\s+([0-9.]+)x\s+\[", t, re.M)
    mdl = float(re.search(r"model predicts\s*:\s*sigma\s+([0-9.]+)", t).group(1))
    lvl = float(re.search(r"single frame \d+\s*:\s*raw sd\s+[0-9.]+ DN\s+mean\s+([0-9.]+)", t).group(1))
    return dict(ref_hp_sd=ref, merged_hp_sd=float(row.group(1)),
                hp_ratio=float(row.group(2)), cli_model_sigma=mdl, cli_mean_dn=lvl)


def main():
    prereg = json.loads((H.EVID / "03-prereg-inputs.json").read_text())
    arms = json.loads((H.EVID / "04-arms.json").read_text())
    hp_l = prereg["trap"]["latent_hp_sd_dn"]
    v = prereg["binned_green_noise"]["model_var_dn2"]

    cli = parsed(H.EVID / "04-merge-s0-g8.0.log")

    pred_ref = float(np.sqrt(hp_l**2 + HP_G2 * v))
    pred_merged = float(np.sqrt(hp_l**2 + HP_G2 * v / N))
    T1 = dict(
        convention="PREREGISTRATION quotes reference/merged; the CLI prints merged/reference",
        predicted_reference_hp_sd_dn=pred_ref,
        cli_reference_hp_sd_dn=cli["ref_hp_sd"],
        predicted_merged_hp_sd_dn=pred_merged,
        cli_merged_hp_sd_dn=cli["merged_hp_sd"],
        predicted_reduction_factor=prereg["trap"]["predicted_flat_roi_hp_ratio"],
        predicted_cli_ratio=1.0 / prereg["trap"]["predicted_flat_roi_hp_ratio"],
        cli_ratio=cli["hp_ratio"],
        model_sigma_harness_dn=prereg["binned_green_noise"]["model_sigma_dn"],
        model_sigma_cli_dn=cli["cli_model_sigma"],
        mean_signal_harness_dn=prereg["latent_green"]["mean_signal_dn"],
        mean_signal_cli_dn=cli["cli_mean_dn"],
    )

    # T2: the ideal Python mean vs the CLI merge at a gate admitting all 30.
    ideal = arms["summary"]["A0-30"]["ratio_mean"]
    cli_g8 = arms["summary"]["A1-g8.0"]["ratio_mean"]
    sigma_merged = prereg["binned_green_noise"]["model_sigma_dn"] / np.sqrt(N)
    step = (15360.0 - 512.0) / 65535.0
    q = step / np.sqrt(12.0)
    predicted_gap = 1.0 / np.sqrt(1.0 + q**2 / sigma_merged**2)
    T2 = dict(
        python_ideal_mean_ratio=ideal,
        cli_merge_gate8_ratio=cli_g8,
        measured_gap=cli_g8 / ideal,
        tiff_quantisation_sd_dn=q,
        merged_residual_sd_dn=float(sigma_merged),
        predicted_gap_from_quantisation=float(predicted_gap),
    )

    # T3: what each statistic can see between a pure selector and the estimator.
    sel_truth = arms["summary"]["A1-g0.0"]["ratio_mean"]
    est_truth = arms["summary"]["A1-g8.0"]["ratio_mean"]
    sel_hp = arms["summary"]["A1-g0.0"]["cli_flat_roi_hp_ratio"]
    est_hp = arms["summary"]["A1-g8.0"]["cli_flat_roi_hp_ratio"]
    # Counterfactual: the same statistic on a TEXTURE-FREE ROI, with and without
    # the shared latent. This is where the trap actually bites.
    flat_shared = float(np.sqrt(2 * N / (N + 1)))
    flat_real = float(np.sqrt(N))
    T3 = dict(
        truth_referenced=dict(selector=sel_truth, estimator=est_truth,
                              separation=est_truth / sel_truth),
        cli_flat_roi_hp_on_this_textured_roi=dict(
            selector=sel_hp, estimator=est_hp, separation=sel_hp / est_hp),
        counterfactual_texture_free_roi=dict(
            shared_latent_plant_reduction=flat_shared,
            real_independent_burst_reduction=flat_real,
            trap_cost_factor=flat_real / flat_shared),
        structure_floor_hp_sd_over_model_sigma=cli["ref_hp_sd"] / cli["cli_model_sigma"],
    )

    H.dump("05-trap-audit.json", dict(T1=T1, T2=T2, T3=T3))


if __name__ == "__main__":
    main()
