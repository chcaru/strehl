//! Exact four-arm production-core invocation copied from the prior paired assay.
use super::context as warped;
use anyhow::{Context, Result};
use serde_json::{Value, json};
use strehl_cli::session_sampling::SampledCfa;
use strehl_core::pyramid::{
    MergeConfig,
    session_fusion::{
        FrozenPrediction, GroupFocusReference, GroupMode, GroupPolicy, GroupWorkspace,
        PreparedSource, SessionMerge, SourceKey,
    },
};
type Planes = [Vec<f32>; 4];
const W: usize = 128;
pub struct Outcome {
    pub planes: Planes,
    pub valid: Vec<bool>,
    pub diagnostics: Value,
}
fn beta(report: &Value, index: usize, name: &str) -> Result<Vec<f32>> {
    Ok(report["frames"]
        .as_array()
        .context("frames")?
        .iter()
        .find(|v| v["frame"] == index)
        .context("frame")?[name]
        .as_array()
        .context("beta")?
        .iter()
        .map(|v| v.as_f64().unwrap() as f32)
        .collect())
}
pub fn produce(
    c: &warped::Contexts,
    report: &Value,
    indices: [usize; 2],
    guide: &Planes,
    guide_support: &[bool],
    guide_id: usize,
    mut load: impl FnMut(usize) -> Result<SampledCfa>,
) -> Result<Vec<Outcome>> {
    let cfg = MergeConfig {
        bands: 7,
        gate: 2.,
        exponent: 2.,
        sharpen_per_octave: 1.4,
        ..Default::default()
    };
    let policy = GroupPolicy {
        mode: GroupMode::Repeat,
        ..Default::default()
    };
    let mut merges: Vec<_> = (0..4)
        .map(|_| SessionMerge::new(W, W, cfg))
        .collect::<std::result::Result<_, _>>()?;
    let mut groups: Vec<_> = (0..4)
        .map(|i| GroupWorkspace::new_with_precision(W, W, cfg, policy, i == 3))
        .collect::<std::result::Result<_, _>>()?;
    let mut source = PreparedSource::new(W, W, cfg)?;
    for pass in 0..2 {
        let index = indices[pass];
        let measured = load(index)?;
        let lb = beta(report, index, "luma_beta")?;
        let cb = beta(report, index, "color_beta")?;
        source.prepare_with_masks(
            SourceKey {
                acquisition: index as u64,
                bracket: pass,
            },
            std::array::from_fn(|color| measured.planes[color].as_slice()),
            &c.noise[pass],
            Some(&lb),
            Some(&cb),
            &measured.coverage,
            &measured.support,
            c.gains[pass],
        )?;
        merges[pass].add_source(&mut groups[pass], &source)?;
        merges[2].add_source(&mut groups[2], &source)?;
        let prediction: Planes =
            std::array::from_fn(|color| guide[color].iter().map(|v| v / c.gains[pass]).collect());
        source.predict_precision(
            FrozenPrediction {
                acquisition: guide_id as u64,
                signal: std::array::from_fn(|color| prediction[color].as_slice()),
                support: guide_support,
            },
            &c.noise[pass],
            c.gains[pass],
            Some(&lb),
            Some(&cb),
        )?;
        merges[3].add_source(&mut groups[3], &source)?;
    }
    let mut result = Vec::new();
    for arm in 0..4 {
        if arm == 3 {
            merges[arm].fold_group_with_focus_reference(
                &mut groups[arm],
                GroupFocusReference::EqualObservation,
            )?;
        } else {
            merges[arm].fold_group(&mut groups[arm])?;
        }
        let out = merges[arm].finish()?;
        let diagnostics=out.diagnostics.iter().map(|v|json!({"averaged":v.averaged_coefficients,"precision":v.precision_averaged_coefficients,"missing_prediction":v.missing_prediction_coefficients,"ordinary_fallback":v.ordinary_fallback_coefficients,"saturated":v.saturated_fallback_coefficients})).collect::<Vec<_>>();
        result.push(Outcome {
            planes: out.planes,
            valid: out.valid,
            diagnostics: json!(diagnostics),
        });
    }
    Ok(result)
}
