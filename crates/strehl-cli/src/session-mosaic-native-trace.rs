//! Bounded copies of the actual estimator's selected tile observations. A
//! refusal must retain measured residuals, not erase the evidence that caused it.
use super::*;
use strehl_core::align::PairTrace;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NativeMeasurement {
    pub direction: String,
    pub termination: String,
    pub attempted_passes: usize,
    pub selected_pass: Option<usize>,
    pub seed: Option<[f64; 4]>,
    /// Absolute native-quad affine matrices [a,b,c,d,tx,ty], when that opt-in
    /// consumer actually gathered its moving patches through this model.
    #[serde(default)]
    pub affine_seed: Option<[f64; 6]>,
    #[serde(default)]
    pub affine_fit: Option<[f64; 6]>,
    #[serde(default)]
    pub leave_one_tile_out_rms_quad: Option<f32>,
    #[serde(default)]
    pub center_residual_quad: Option<f32>,
    #[serde(default)]
    pub center_leave_one_out_error_quad: Option<f32>,
    /// Actual reference and moving footprint corners per affine probe.
    #[serde(default)]
    pub affine_footprints: Vec<[[[f64; 2]; 4]; 2]>,
    /// Conservative inclusive original-quad bounds of all attempted similarity
    /// passes, including coarse boxes and moving interpolation taps.
    #[serde(default)]
    pub sampled_bounds_quad: Option<[[[f64; 2]; 2]; 2]>,
    pub plane_center: [f64; 2],
    pub sample_step_quad: usize,
    pub rms_quad: Option<f32>,
    pub peak_mean: Option<f32>,
    pub used_tiles: usize,
    pub support_reserved: bool,
    pub support_unclipped: bool,
    /// [ux,uy,dx,dy], in the actual estimator's centered plane gauge.
    pub observations: Vec<[f32; 4]>,
    pub kept: Vec<bool>,
    pub initial_residuals: Vec<f32>,
    pub final_residuals: Vec<f32>,
    /// Actual tile origin, side and search radius for the recorded stage.
    pub probes: Vec<[usize; 4]>,
    pub statuses: Vec<String>,
}

pub(super) fn capture(
    direction: &str,
    trace: &PairTrace,
    support_reserved: bool,
    support_unclipped: bool,
    sample_step_quad: usize,
) -> NativeMeasurement {
    let stage = trace
        .selected_fine_pass
        .and_then(|n| trace.fine_passes.get(n))
        .or_else(|| trace.fine_passes.last())
        .map(|s| &s.stage.measurements);
    let fit = trace.result.as_ref().ok();
    NativeMeasurement {
        direction: direction.into(),
        termination: format!("{:?}", trace.termination),
        attempted_passes: trace.fine_passes.len(),
        selected_pass: trace.selected_fine_pass,
        seed: stage.and_then(|s| s.seed).map(|p| {
            let t = Similarity::from_params(p);
            [t.a.re, t.a.im, t.b.re, t.b.im]
        }),
        affine_seed: None,
        affine_fit: None,
        leave_one_tile_out_rms_quad: None,
        center_residual_quad: None,
        center_leave_one_out_error_quad: None,
        affine_footprints: Vec::new(),
        sampled_bounds_quad: sampled_bounds(trace, sample_step_quad),
        plane_center: stage.map_or([0.0; 2], |s| [s.plane_center.0, s.plane_center.1]),
        sample_step_quad,
        rms_quad: fit.map(|f| f.rms * sample_step_quad as f32),
        peak_mean: fit.map(|f| f.peak_mean),
        used_tiles: fit.map_or(0, |f| f.used),
        support_reserved,
        support_unclipped,
        observations: stage.map_or_else(Vec::new, |s| {
            s.tiles
                .iter()
                .filter_map(|t| t.observation)
                .map(|o| [o.ux, o.uy, o.dx, o.dy])
                .collect()
        }),
        kept: stage.and_then(|s| s.keep.clone()).unwrap_or_default(),
        initial_residuals: stage
            .and_then(|s| s.initial_residuals.clone())
            .unwrap_or_default(),
        final_residuals: stage
            .and_then(|s| s.final_residuals.clone())
            .unwrap_or_default(),
        probes: stage.map_or_else(Vec::new, |s| {
            s.tiles
                .iter()
                .map(|t| {
                    [
                        t.probe.tx,
                        t.probe.ty,
                        t.probe.size,
                        t.probe.radius as usize,
                    ]
                })
                .collect()
        }),
        statuses: stage.map_or_else(Vec::new, |s| {
            s.tiles
                .iter()
                .map(|t| format!("{:?}", t.measurement.status))
                .collect()
        }),
    }
}

fn sampled_bounds(trace: &PairTrace, factor: usize) -> Option<[[[f64; 2]; 2]; 2]> {
    if factor == 0 || trace.fine_passes.is_empty() {
        return None;
    }
    let mut result = [[[f64::INFINITY; 2], [f64::NEG_INFINITY; 2]]; 2];
    for pass in &trace.fine_passes {
        let stage = &pass.stage.measurements;
        if !stage.warped_tiles_used {
            return None;
        }
        let warp = Similarity::from_params(stage.seed?);
        for tile in &stage.tiles {
            let p = tile.probe;
            let x = p.tx as f64;
            let y = p.ty as f64;
            let last_x = (p.tx + p.size - 1) as f64;
            let last_y = (p.ty + p.size - 1) as f64;
            let reference = [[x, y], [x, last_y], [last_x, y], [last_x, last_y]];
            let radius = f64::from(p.radius);
            let half = p.size as f64 * 0.5;
            let center = [
                x + half + f64::from(p.predicted.0),
                y + half + f64::from(p.predicted.1),
            ];
            let moving = [
                [x - radius, y - radius],
                [x - radius, last_y + radius],
                [last_x + radius, y - radius],
                [last_x + radius, last_y + radius],
            ]
            .map(|q| {
                let u = q[0] - x - half;
                let v = q[1] - y - half;
                [
                    center[0] + warp.a.re * u - warp.a.im * v,
                    center[1] + warp.a.im * u + warp.a.re * v,
                ]
            });
            for (source, corners) in [reference, moving].iter().enumerate() {
                for q in corners {
                    for (axis, value) in q.iter().enumerate() {
                        let first = value.floor() * factor as f64;
                        result[source][0][axis] = result[source][0][axis].min(first);
                        result[source][1][axis] = result[source][1][axis].max(
                            first
                                + (factor - 1) as f64
                                + if source == 1 { factor as f64 } else { 0.0 },
                        );
                    }
                }
            }
        }
    }
    result
        .iter()
        .flatten()
        .flatten()
        .all(|v| v.is_finite())
        .then_some(result)
}
