// Source-prepared fixed decision adapter only. No standalone harness or admission.
// Inputs are the frozen actual-Laplacian R, mean-green, B energy/floor fields.
use strehl_core::pyramid::{LevelSize, MergeConfig, rb_own_guide_diagnostic as consumer};

/// Sum channel SNR energies, then use one resulting field for all four planes.
/// Each input floor already includes cfg.gate; no private variance is estimated.
/// A zero/nonfinite floor is a refusal, never a new fitted epsilon or noise model.
pub(crate) fn shared_snr_fields(
    sizes: &[LevelSize],
    cfg: MergeConfig,
    channels: [&consumer::Fields; 3],
) -> Result<consumer::Fields, &'static str> {
    if sizes.len() < 2 || cfg.gate != 2.0 || cfg.significance_scale != 0.0 {
        return Err("fixed gate2/no significance-scale contract required");
    }
    let bands = sizes.len() - 1;
    if channels
        .iter()
        .any(|c| c.energy.len() != bands || c.floor.len() != bands)
    {
        return Err("three complete R/mean-green/B AC fields required");
    }
    let mut energy = Vec::with_capacity(bands);
    let mut floor = Vec::with_capacity(bands);
    for (band, size) in sizes[..bands].iter().enumerate() {
        let count = size.pixels();
        if channels
            .iter()
            .any(|c| c.energy[band].len() != count || c.floor[band].len() != count)
        {
            return Err("channel energy/floor geometry differs");
        }
        let mut joint = vec![0.0_f32; count];
        for (pixel, value) in joint.iter_mut().enumerate() {
            for channel in &channels {
                let e = channel.energy[band][pixel];
                let f = channel.floor[band][pixel];
                if !e.is_finite() || e < 0.0 || !f.is_finite() || f <= 0.0 {
                    return Err("finite energy and strictly positive propagated floor required");
                }
                // f=gate*V, so this is E/V. No WB factor survives E/V scaling.
                *value += cfg.gate * e / f;
            }
            if !value.is_finite() {
                return Err("normalized joint energy overflow");
            }
        }
        energy.push(joint);
        floor.push(vec![3.0 * cfg.gate; count]);
    }
    Ok(consumer::fields_from_energy(sizes, cfg, energy, floor))
}

// Consumer contract: exactly one add_fields call on a four-plane BandMerge,
// supplying these weights and [R,G1,G2,B]. Do not use the old ColourArm that
// replaces only R/B while retaining canonical greens. Terminal mean, input hull,
// final MHC and native synthesis remain untouched. See brief.md before use.
