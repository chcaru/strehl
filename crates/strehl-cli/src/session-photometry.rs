//! Bounded radiometric calibration for opt-in HDR sessions.
//!
//! Geometry only proposes pairs. Fixed spatial patches must support one scalar,
//! textured agreement and stability across focus ranks before a pass is admitted.
//! This calibrates signal units, never a new noise model or a global focus truth.
use std::collections::BTreeSet;

use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use strehl_core::CfaPlane;
use strehl_core::noise::NoiseModel;
use strehl_core::optics::OpticalProfile;
use strehl_core::plane::PlaneGeometry;

use crate::session_align::SessionAlignment;
use crate::session_cache::SourceCache;
use crate::session_input::{ResolvedSession, SourceIdentity};
use crate::session_sampling::{NativeSampler, SampledCfa, SamplingDomain, sampling_bytes};

pub const GENERATION: &str = "hdr-spatial-cross-validation-v1";

/// Explicit engineering tolerances, not inferred camera constants.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PhotometryConfig {
    pub grid: [usize; 2],
    pub patch_side: usize,
    pub margin: usize,
    pub max_pairs_per_pass: usize,
    pub minimum_pairs: usize,
    pub minimum_rank_span: f32,
    pub minimum_fit_patches: usize,
    pub minimum_validation_patches: usize,
    pub minimum_textured_patches: usize,
    pub minimum_signal_sigma: f32,
    pub correction_limit_ev: f32,
    pub median_relative_limit: f32,
    pub p95_relative_limit: f32,
    pub maximum_relative_limit: f32,
    pub stability_relative_limit: f32,
    pub texture_residual_limit: f32,
    /// Generous single-sample variance allowance for compatibility eligibility;
    /// not a precision estimate, effective sample count or delivered gain claim.
    pub noise_variance_allowance: f32,
    pub workspace_limit_bytes: usize,
}
impl Default for PhotometryConfig {
    fn default() -> Self {
        Self {
            grid: [8, 6],
            patch_side: 32,
            margin: 96,
            max_pairs_per_pass: 9,
            minimum_pairs: 3,
            minimum_rank_span: 0.5,
            minimum_fit_patches: 6,
            minimum_validation_patches: 6,
            minimum_textured_patches: 4,
            minimum_signal_sigma: 8.0,
            correction_limit_ev: 0.25,
            median_relative_limit: 0.01,
            p95_relative_limit: 0.03,
            maximum_relative_limit: 0.05,
            stability_relative_limit: 0.02,
            texture_residual_limit: 0.1,
            noise_variance_allowance: 16.0,
            workspace_limit_bytes: 1024 * 1024 * 1024,
        }
    }
}
impl PhotometryConfig {
    fn validate(&self) -> Result<()> {
        ensure!(
            self.grid.iter().all(|&n| (2..=16).contains(&n)),
            "photometry grid must be 2..16 per dimension"
        );
        ensure!(
            (4..=64).contains(&self.patch_side),
            "photometry patch must be 4..64 plane pixels"
        );
        ensure!(
            (3..=15).contains(&self.max_pairs_per_pass)
                && (3..=self.max_pairs_per_pass).contains(&self.minimum_pairs),
            "photometry requires 3..15 bounded pairs"
        );
        ensure!(
            self.minimum_fit_patches >= 3
                && self.minimum_validation_patches >= 3
                && self.minimum_textured_patches >= 2,
            "photometry needs spatial and textured evidence"
        );
        for value in [
            self.minimum_rank_span,
            self.minimum_signal_sigma,
            self.correction_limit_ev,
            self.median_relative_limit,
            self.p95_relative_limit,
            self.maximum_relative_limit,
            self.stability_relative_limit,
            self.texture_residual_limit,
            self.noise_variance_allowance,
        ] {
            ensure!(
                value.is_finite() && value > 0.0,
                "invalid photometry tolerance"
            );
        }
        ensure!(
            self.minimum_rank_span <= 1.0 && self.correction_limit_ev <= 1.0,
            "unbounded photometry correction or rank span"
        );
        ensure!(
            self.median_relative_limit <= self.p95_relative_limit
                && self.p95_relative_limit <= self.maximum_relative_limit
                && self.maximum_relative_limit <= 0.25
                && self.stability_relative_limit <= 0.1,
            "invalid photometry residual bounds"
        );
        ensure!(
            self.noise_variance_allowance >= 1.0 && self.noise_variance_allowance <= 64.0,
            "invalid photometry noise allowance"
        );
        Ok(())
    }
}

pub struct PassPhotometryInput<'a> {
    /// Existing exposure normalization into the chosen anchor's signal units.
    pub nominal_gain: f32,
    pub noise: &'a NoiseModel,
    pub profile: Option<&'a OpticalProfile>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PhotometryPatch {
    pub id: usize,
    pub x: usize,
    pub y: usize,
    pub side: usize,
    pub validation: bool,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PatchEvidence {
    pub id: usize,
    pub validation: bool,
    pub log_ratios: Option<[f32; 4]>,
    pub textured: bool,
    pub texture_residual: Option<f32>,
    pub refusal: Option<String>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ResidualSummary {
    pub median: f32,
    pub p95: f32,
    pub maximum: f32,
    pub samples: usize,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PairRefusalKind {
    /// No usable correspondence/coverage/texture witness was obtained.
    UnavailableEvidence,
    /// Supported measurements affirmatively contradict the one-scalar model.
    ContradictoryRadiometry,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PairPhotometryReport {
    pub anchor_frame: usize,
    pub source_frame: usize,
    pub anchor_rank: f32,
    pub source_rank: f32,
    pub anchor_identity: String,
    pub source_identity: String,
    pub fitted_log_ratio: Option<f32>,
    pub validation: Option<ResidualSummary>,
    pub textured_patches: usize,
    pub refusal_kind: Option<PairRefusalKind>,
    pub accepted: bool,
    pub refusal: Option<String>,
    pub patches: Vec<PatchEvidence>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PassPhotometryReport {
    pub pass: usize,
    pub nominal_gain: f32,
    pub corrected_gain: Option<f32>,
    pub correction_ev: Option<f32>,
    pub stability_relative: Option<f32>,
    pub anchor_rank_span: Option<f32>,
    pub source_rank_span: Option<f32>,
    pub validation: Option<ResidualSummary>,
    pub accepted: bool,
    pub refusal: Option<String>,
    pub pairs: Vec<PairPhotometryReport>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PhotometryReport {
    pub generation: String,
    pub anchor_pass: usize,
    pub config: PhotometryConfig,
    pub patches: Vec<PhotometryPatch>,
    /// Separate calibration-phase buffers; excludes original cache and decode.
    pub workspace_bytes: usize,
    /// Checked bound for retained pass/pair/patch report records and strings.
    pub retained_report_bytes: usize,
    pub passes: Vec<PassPhotometryReport>,
    /// None on any refusal. There is deliberately no silent nominal fallback.
    pub calibrated_gains: Option<Vec<f32>>,
    pub limitations: Vec<String>,
}
impl PhotometryReport {
    pub fn require_gains(&self) -> Result<&[f32]> {
        self.calibrated_gains.as_deref().ok_or_else(|| {
            let reasons = self.passes.iter().filter(|p| !p.accepted).map(|p| format!("pass {}: {}", p.pass, p.refusal.as_deref().unwrap_or("insufficient calibrated overlap"))).collect::<Vec<_>>().join("; ");
            anyhow::anyhow!("HDR exposure calibration refused ({reasons}). Export aligned layers or acquire stable overlapping exposure passes; nominal shutter ratios alone were not accepted.")
        })
    }
}

fn checked_sum(terms: &[(usize, usize)]) -> Result<usize> {
    terms.iter().try_fold(0usize, |sum, &(a, b)| {
        a.checked_mul(b)
            .and_then(|v| sum.checked_add(v))
            .ok_or_else(|| anyhow::anyhow!("photometry workspace overflows"))
    })
}
/// Includes one full consumer sampler, two compact patch sets and conservative
/// sorting/report scratch. Original u16 cache/decoder remains caller-budgeted.
pub fn workspace_bytes(geometry: PlaneGeometry, cfg: &PhotometryConfig) -> Result<usize> {
    cfg.validate()?;
    let points = checked_sum(&[(cfg.patch_side, cfg.patch_side)])?;
    let patches = checked_sum(&[(cfg.grid[0], cfg.grid[1])])?;
    let compact = checked_sum(&[(points, patches)])?;
    let bytes = checked_sum(&[
        (sampling_bytes(SamplingDomain::full(geometry))?, 1),
        (compact, 40),
        (patches, 4096),
        (points, 64),
    ])?;
    ensure!(
        bytes <= isize::MAX as usize && bytes <= cfg.workspace_limit_bytes,
        "photometry workspace needs {bytes} bytes, limit {}",
        cfg.workspace_limit_bytes
    );
    Ok(bytes)
}

/// Conservative retained report bound, including Vec growth and bounded reason/
/// identity strings. Numerical source/patch buffers are in workspace_bytes.
pub fn report_bytes(passes: usize, cfg: &PhotometryConfig) -> Result<usize> {
    cfg.validate()?;
    ensure!(passes > 0, "photometry report needs at least one pass");
    let patches = checked_sum(&[(cfg.grid[0], cfg.grid[1])])?;
    let pairs = checked_sum(&[(passes, cfg.max_pairs_per_pass)])?;
    let evidence = checked_sum(&[(pairs, patches)])?;
    let bytes = checked_sum(&[
        (1, std::mem::size_of::<PhotometryReport>() + 4096),
        (passes, std::mem::size_of::<PassPhotometryReport>() + 512),
        (pairs, std::mem::size_of::<PairPhotometryReport>() + 512),
        (evidence, std::mem::size_of::<PatchEvidence>() + 256),
        (patches, 2 * std::mem::size_of::<PhotometryPatch>()),
    ])?;
    ensure!(
        bytes <= isize::MAX as usize,
        "photometry report allocation exceeds address range"
    );
    Ok(bytes)
}

fn patch_grid(geometry: PlaneGeometry, cfg: &PhotometryConfig) -> Result<Vec<PhotometryPatch>> {
    let inset = cfg
        .margin
        .checked_mul(2)
        .and_then(|v| v.checked_add(cfg.patch_side))
        .ok_or_else(|| anyhow::anyhow!("photometry patch geometry overflows"))?;
    ensure!(
        geometry.width >= inset && geometry.height >= inset,
        "image too small for photometry patches"
    );
    let room = [geometry.width - inset, geometry.height - inset];
    ensure!(
        room[0] / (cfg.grid[0] - 1) >= cfg.patch_side
            && room[1] / (cfg.grid[1] - 1) >= cfg.patch_side,
        "photometry fit/validation patches overlap"
    );
    let mut patches = Vec::new();
    for y in 0..cfg.grid[1] {
        for x in 0..cfg.grid[0] {
            patches.push(PhotometryPatch {
                id: patches.len(),
                x: cfg.margin + room[0] * x / (cfg.grid[0] - 1),
                y: cfg.margin + room[1] * y / (cfg.grid[1] - 1),
                side: cfg.patch_side,
                validation: (x + y) % 2 == 1,
            });
        }
    }
    Ok(patches)
}

#[derive(Clone)]
struct CompactPatch {
    values: [Vec<f32>; 4],
    refusal: Option<String>,
}
fn compact_patches(
    samples: &SampledCfa,
    geometry: PlaneGeometry,
    patches: &[PhotometryPatch],
) -> Vec<CompactPatch> {
    patches
        .iter()
        .map(|p| {
            let indices = (p.y..p.y + p.side)
                .flat_map(|y| (p.x..p.x + p.side).map(move |x| y * geometry.width + x))
                .collect::<Vec<_>>();
            let refusal = if indices.iter().any(|&i| !samples.coverage[i]) {
                Some("missing original coverage".into())
            } else if indices.iter().any(|&i| !samples.support[i]) {
                Some("an original contributing CFA tap is clipped".into())
            } else {
                None
            };
            let values = std::array::from_fn(|c| {
                if refusal.is_none() {
                    indices.iter().map(|&i| samples.planes[c][i]).collect()
                } else {
                    Vec::new()
                }
            });
            CompactPatch { values, refusal }
        })
        .collect()
}
fn percentile(values: &[f32], fraction: f32) -> f32 {
    let mut sorted = values.to_vec();
    sorted.sort_by(f32::total_cmp);
    let position = fraction * (sorted.len() - 1) as f32;
    let low = position.floor() as usize;
    let high = position.ceil() as usize;
    sorted[low] + (sorted[high] - sorted[low]) * (position - low as f32)
}
fn trimmed_mean(values: &[f32]) -> Option<f32> {
    if values.is_empty() || values.iter().any(|v| !v.is_finite()) {
        return None;
    }
    let mut sorted = values.to_vec();
    sorted.sort_by(f32::total_cmp);
    let trim = sorted.len() / 10;
    let kept = &sorted[trim..sorted.len() - trim];
    Some(kept.iter().sum::<f32>() / kept.len() as f32)
}
fn residual_summary(log_ratios: &[f32], fitted: f32) -> Option<ResidualSummary> {
    if log_ratios.is_empty() {
        return None;
    }
    let values = log_ratios
        .iter()
        .map(|r| ((r - fitted).exp() - 1.0).abs())
        .collect::<Vec<_>>();
    Some(ResidualSummary {
        median: percentile(&values, 0.5),
        p95: percentile(&values, 0.95),
        maximum: values.iter().copied().fold(0.0, f32::max),
        samples: values.len(),
    })
}
fn passes_residuals(summary: &ResidualSummary, cfg: &PhotometryConfig) -> bool {
    summary.median <= cfg.median_relative_limit
        && summary.p95 <= cfg.p95_relative_limit
        && summary.maximum <= cfg.maximum_relative_limit
}
fn scaled_variance(noise: &NoiseModel, color: CfaPlane, original: f32, gain: f32) -> f32 {
    noise.variance(color, original) * gain * gain
}

fn assess_pair(
    anchor: &[CompactPatch],
    source: &[CompactPatch],
    inputs: [&PassPhotometryInput<'_>; 2],
    patches: &[PhotometryPatch],
    cfg: &PhotometryConfig,
    mut report: PairPhotometryReport,
) -> PairPhotometryReport {
    let [a, b] = inputs;
    let mut fit = Vec::new();
    let mut fit_patches = 0;
    let mut validation_patches = 0;
    for ((left, right), patch) in anchor.iter().zip(source).zip(patches) {
        let mut evidence = PatchEvidence {
            id: patch.id,
            validation: patch.validation,
            log_ratios: None,
            textured: false,
            texture_residual: None,
            refusal: left.refusal.clone().or_else(|| right.refusal.clone()),
        };
        if evidence.refusal.is_none() {
            let mut ratios = [0.0; 4];
            for (c, color) in CfaPlane::ALL.into_iter().enumerate() {
                let (Some(ma), Some(mb)) = (
                    trimmed_mean(&left.values[c]),
                    trimmed_mean(&right.values[c]),
                ) else {
                    evidence.refusal = Some("nonfinite or empty patch".into());
                    break;
                };
                let va = a.noise.variance(color, ma);
                let vb = b.noise.variance(color, mb);
                if !va.is_finite()
                    || !vb.is_finite()
                    || va < 0.0
                    || vb < 0.0
                    || ma <= cfg.minimum_signal_sigma * va.sqrt()
                    || mb <= cfg.minimum_signal_sigma * vb.sqrt()
                {
                    evidence.refusal = Some("patch signal lacks injected-noise margin".into());
                    break;
                }
                ratios[c] = ((mb * b.nominal_gain) / (ma * a.nominal_gain)).ln();
                if !ratios[c].is_finite() {
                    evidence.refusal = Some("nonfinite radiometric ratio".into());
                    break;
                }
            }
            if evidence.refusal.is_none() {
                evidence.log_ratios = Some(ratios);
                if patch.validation {
                    validation_patches += 1;
                } else {
                    fit.extend(ratios);
                    fit_patches += 1;
                }
            }
        }
        report.patches.push(evidence);
    }
    if fit_patches < cfg.minimum_fit_patches || validation_patches < cfg.minimum_validation_patches
    {
        report.refusal_kind = Some(PairRefusalKind::UnavailableEvidence);
        report.refusal = Some(format!(
            "only {fit_patches} fit and {validation_patches} validation patches have unclipped four-color signal"
        ));
        return report;
    }
    let fitted = percentile(&fit, 0.5);
    report.fitted_log_ratio = Some(fitted);
    if fitted.abs() / std::f32::consts::LN_2 > cfg.correction_limit_ev {
        report.refusal_kind = Some(PairRefusalKind::ContradictoryRadiometry);
        report.refusal = Some("required exposure correction exceeds configured EV limit".into());
        return report;
    }
    let validation = report
        .patches
        .iter()
        .filter(|p| p.validation)
        .filter_map(|p| p.log_ratios)
        .flatten()
        .collect::<Vec<_>>();
    report.validation = residual_summary(&validation, fitted);
    if !report
        .validation
        .as_ref()
        .is_some_and(|s| passes_residuals(s, cfg))
    {
        report.refusal_kind = Some(PairRefusalKind::ContradictoryRadiometry);
        report.refusal =
            Some("held-out spatial/color residual exceeds scalar exposure model".into());
        return report;
    }
    let gain_b = b.nominal_gain / fitted.exp();
    let mut texture_bad = false;
    for (index, evidence) in report.patches.iter_mut().enumerate() {
        if evidence.log_ratios.is_none() {
            continue;
        }
        let mut worst = 0.0f32;
        for (c, color) in CfaPlane::ALL.into_iter().enumerate() {
            let x = &anchor[index].values[c];
            let y = &source[index].values[c];
            let n = x.len() as f32;
            let mx = x.iter().sum::<f32>() / n;
            let my = y.iter().sum::<f32>() / n;
            let mut tx = 0.0;
            let mut ty = 0.0;
            let mut difference = 0.0;
            let mut variance = 0.0;
            for (&x, &y) in x.iter().zip(y) {
                let dx = (x - mx) * a.nominal_gain;
                let dy = (y - my) * gain_b;
                tx += dx * dx;
                ty += dy * dy;
                difference += (dx - dy) * (dx - dy);
                variance += scaled_variance(a.noise, color, x, a.nominal_gain)
                    + scaled_variance(b.noise, color, y, gain_b);
            }
            tx /= n;
            ty /= n;
            difference /= n;
            variance = variance / n * cfg.noise_variance_allowance;
            // Flat noise cannot constitute a focus/placement compatibility witness.
            if tx.min(ty) > 16.0 * variance {
                evidence.textured = true;
                worst = worst.max((difference - variance).max(0.0) / tx.max(ty));
            }
        }
        if evidence.textured {
            report.textured_patches += 1;
            evidence.texture_residual = Some(worst);
            if worst > cfg.texture_residual_limit {
                texture_bad = true;
            }
        }
    }
    if texture_bad {
        report.refusal_kind = Some(PairRefusalKind::UnavailableEvidence);
        report.refusal = Some("textured overlap disagrees after scalar correction (focus, motion, lighting or placement)".into());
    } else if report.textured_patches < cfg.minimum_textured_patches {
        report.refusal_kind = Some(PairRefusalKind::UnavailableEvidence);
        report.refusal =
            Some("flat-only overlap cannot validate compatible focus/placement".into());
    } else {
        report.accepted = true;
    }
    report
}

fn finalize_pass(
    pass: usize,
    nominal_gain: f32,
    pairs: Vec<PairPhotometryReport>,
    cfg: &PhotometryConfig,
) -> PassPhotometryReport {
    let mut report = PassPhotometryReport {
        pass,
        nominal_gain,
        corrected_gain: None,
        correction_ev: None,
        stability_relative: None,
        anchor_rank_span: None,
        source_rank_span: None,
        validation: None,
        accepted: false,
        refusal: None,
        pairs,
    };
    // Refusing one supported contradiction is essential: choosing only the
    // surviving pairs would certify a scalar that is applied to every frame.
    let contradictions = report
        .pairs
        .iter()
        .filter(|p| p.refusal_kind == Some(PairRefusalKind::ContradictoryRadiometry))
        .count();
    if contradictions > 0 {
        report.refusal = Some(format!(
            "{contradictions} supported pair(s) contradict the exposure model; stable survivors cannot certify this pass"
        ));
        return report;
    }
    let accepted = report
        .pairs
        .iter()
        .filter(|p| p.accepted)
        .collect::<Vec<_>>();
    if accepted.len() < cfg.minimum_pairs {
        report.refusal = Some(format!(
            "only {} compatible independent focus pairs; need {}",
            accepted.len(),
            cfg.minimum_pairs
        ));
        return report;
    }
    let span = |anchor: bool| {
        let ranks = accepted
            .iter()
            .map(|p| if anchor { p.anchor_rank } else { p.source_rank })
            .collect::<Vec<_>>();
        ranks.iter().copied().fold(f32::NEG_INFINITY, f32::max)
            - ranks.iter().copied().fold(f32::INFINITY, f32::min)
    };
    let (anchor_span, source_span) = (span(true), span(false));
    report.anchor_rank_span = Some(anchor_span);
    report.source_rank_span = Some(source_span);
    if anchor_span < cfg.minimum_rank_span || source_span < cfg.minimum_rank_span {
        report.refusal = Some("compatible pairs do not span enough of both focus tracks".into());
        return report;
    }
    let logs = accepted
        .iter()
        .map(|p| p.fitted_log_ratio.expect("accepted pair has fit"))
        .collect::<Vec<_>>();
    let fitted = percentile(&logs, 0.5);
    let stability = (logs.iter().copied().fold(f32::NEG_INFINITY, f32::max)
        - logs.iter().copied().fold(f32::INFINITY, f32::min))
    .exp()
        - 1.0;
    report.stability_relative = Some(stability);
    report.correction_ev = Some(-fitted / std::f32::consts::LN_2);
    if stability > cfg.stability_relative_limit {
        report.refusal = Some("radiometric correction changes across focus ranks".into());
        return report;
    }
    let validation = accepted
        .iter()
        .flat_map(|p| p.patches.iter())
        .filter(|p| p.validation)
        .filter_map(|p| p.log_ratios)
        .flatten()
        .collect::<Vec<_>>();
    report.validation = residual_summary(&validation, fitted);
    if !report
        .validation
        .as_ref()
        .is_some_and(|s| passes_residuals(s, cfg))
    {
        report.refusal = Some("one pass-wide scalar fails pooled held-out validation".into());
        return report;
    }
    report.corrected_gain = Some(nominal_gain / fitted.exp());
    report.accepted = true;
    report
}

/// Calibrate before allocating merge buffers. One full sampler is reused; only
/// two bounded compact patch sets survive a source gather. Alignment candidates
/// remain unvalidated outside this sampled radiometric compatibility decision.
pub fn calibrate(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    alignment: &SessionAlignment,
    cache: &mut SourceCache,
    anchor_pass: usize,
    inputs: &[PassPhotometryInput<'_>],
    cfg: &PhotometryConfig,
) -> Result<PhotometryReport> {
    cfg.validate()?;
    ensure!(
        anchor_pass < session.passes.len()
            && inputs.len() == session.passes.len()
            && identities.len() == session.frames.len(),
        "photometry session shape mismatch"
    );
    let unique = identities
        .iter()
        .map(|i| &i.sha256)
        .collect::<BTreeSet<_>>();
    ensure!(
        unique.len() == identities.len(),
        "photometry refuses repeated original source identity"
    );
    for input in inputs {
        ensure!(
            input.nominal_gain.is_finite()
                && input.nominal_gain > 0.0
                && input.nominal_gain <= 1024.0
                && input.noise.is_trustworthy(),
            "HDR calibration requires finite exposure gains and a trustworthy injected noise model"
        );
    }
    let geometry = alignment.map.geometry();
    let bytes = workspace_bytes(geometry, cfg)?;
    let retained_report_bytes = report_bytes(session.passes.len(), cfg)?;
    let total_phase_bytes = checked_sum(&[(bytes, 1), (retained_report_bytes, 1)])?;
    ensure!(
        total_phase_bytes <= cfg.workspace_limit_bytes,
        "HDR calibration numerical/report phase needs {total_phase_bytes} bytes, limit {}",
        cfg.workspace_limit_bytes
    );
    let patches = patch_grid(geometry, cfg)?;
    let mut sampler = NativeSampler::new(SamplingDomain::full(geometry))?;
    let mut reports = Vec::new();
    for pass in 0..session.passes.len() {
        if pass == anchor_pass {
            reports.push(PassPhotometryReport {
                pass,
                nominal_gain: inputs[pass].nominal_gain,
                corrected_gain: Some(inputs[pass].nominal_gain),
                correction_ev: Some(0.0),
                stability_relative: None,
                anchor_rank_span: None,
                source_rank_span: None,
                validation: None,
                accepted: true,
                refusal: None,
                pairs: Vec::new(),
            });
            continue;
        }
        let mut candidates = Vec::new();
        let mut used_anchor = BTreeSet::new();
        let mut used_source = BTreeSet::new();
        for candidate in &alignment.pair_candidates {
            ensure!(
                candidate.i < session.frames.len() && candidate.j < session.frames.len(),
                "photometry candidate index outside session"
            );
            let i = &session.frames[candidate.i];
            let j = &session.frames[candidate.j];
            let pair = if i.pass_index == anchor_pass && j.pass_index == pass {
                Some((candidate.i, candidate.j))
            } else if j.pass_index == anchor_pass && i.pass_index == pass {
                Some((candidate.j, candidate.i))
            } else {
                None
            };
            if candidate.candidate_same_focus
                && candidate.mutual_nearest
                && let Some((a, b)) = pair
            {
                candidates.push((a, b));
            }
        }
        candidates.sort_unstable_by_key(|&(a, b)| {
            (
                session.frames[a].pass_frame_index,
                session.frames[b].pass_frame_index,
            )
        });
        candidates.retain(|&(a, b)| {
            if used_anchor.contains(&a) || used_source.contains(&b) {
                false
            } else {
                used_anchor.insert(a);
                used_source.insert(b);
                true
            }
        });
        let selected = if candidates.len() <= cfg.max_pairs_per_pass {
            candidates
        } else {
            (0..cfg.max_pairs_per_pass)
                .map(|i| candidates[i * (candidates.len() - 1) / (cfg.max_pairs_per_pass - 1)])
                .collect()
        };
        let mut pairs = Vec::new();
        for (anchor, source) in selected {
            let mut compact = Vec::new();
            for index in [anchor, source] {
                let original = cache.load_or_decode(&session.frames[index], &identities[index])?;
                let input = &inputs[session.frames[index].pass_index];
                for color in CfaPlane::ALL {
                    let levels = input.noise.plane(color).levels;
                    ensure!(
                        levels.black.to_bits() == original.levels().black.to_bits()
                            && levels.white.to_bits() == original.levels().white.to_bits(),
                        "photometry noise model and original levels differ"
                    );
                }
                let gathered = sampler.gather(
                    original.as_ref(),
                    original.levels(),
                    alignment.map.placement(index)?,
                    input.profile,
                    alignment.map.resampler(),
                )?;
                compact.push(compact_patches(gathered, geometry, &patches));
            }
            let rank = |index: usize| {
                let frame = &session.frames[index];
                frame.pass_frame_index as f32
                    / (session.passes[frame.pass_index]
                        .global_range
                        .len()
                        .saturating_sub(1))
                    .max(1) as f32
            };
            let pair = PairPhotometryReport {
                anchor_frame: anchor,
                source_frame: source,
                anchor_rank: rank(anchor),
                source_rank: rank(source),
                anchor_identity: identities[anchor].sha256.clone(),
                source_identity: identities[source].sha256.clone(),
                fitted_log_ratio: None,
                validation: None,
                textured_patches: 0,
                refusal_kind: None,
                accepted: false,
                refusal: None,
                patches: Vec::new(),
            };
            pairs.push(assess_pair(
                &compact[0],
                &compact[1],
                [&inputs[anchor_pass], &inputs[pass]],
                &patches,
                cfg,
                pair,
            ));
        }
        reports.push(finalize_pass(pass, inputs[pass].nominal_gain, pairs, cfg));
    }
    let gains = reports
        .iter()
        .map(|r| r.corrected_gain)
        .collect::<Option<Vec<_>>>();
    Ok(PhotometryReport { generation: GENERATION.into(), anchor_pass, config: cfg.clone(), patches, workspace_bytes: bytes, retained_report_bytes, passes: reports, calibrated_gains: gains, limitations: vec!["Spatial validation is held out from exposure fitting; it is not independently held out from alignment.".into(), "Sampled textured compatibility does not certify equal focus or illumination everywhere.".into(), "Absolute noise comes only from the supplied model; final consumer must apply total gain squared to propagated variance.".into()] })
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::noise::{Levels, PlaneNoise, Provenance};

    fn config() -> PhotometryConfig {
        PhotometryConfig {
            grid: [4, 4],
            patch_side: 8,
            margin: 4,
            minimum_fit_patches: 3,
            minimum_validation_patches: 3,
            minimum_textured_patches: 2,
            ..PhotometryConfig::default()
        }
    }
    fn model() -> NoiseModel {
        NoiseModel::new(
            [PlaneNoise {
                gain_dn_per_e: 0.001,
                read_noise_e: 2000.0,
                levels: Levels {
                    black: 512.0,
                    white: 15360.0,
                },
            }; 4],
            100.0,
            Provenance::Profile,
        )
    }
    fn geometry() -> PlaneGeometry {
        PlaneGeometry {
            width: 64,
            height: 64,
        }
    }
    fn blank_report(index: usize) -> PairPhotometryReport {
        PairPhotometryReport {
            anchor_frame: index,
            source_frame: index + 100,
            anchor_rank: index as f32 * 0.5,
            source_rank: index as f32 * 0.5,
            anchor_identity: format!("a{index}"),
            source_identity: format!("b{index}"),
            fitted_log_ratio: None,
            validation: None,
            textured_patches: 0,
            refusal_kind: None,
            accepted: false,
            refusal: None,
            patches: Vec::new(),
        }
    }
    fn fixture(patches: &[PhotometryPatch], texture: bool) -> Vec<CompactPatch> {
        patches
            .iter()
            .map(|p| CompactPatch {
                values: std::array::from_fn(|c| {
                    (0..p.side * p.side)
                        .map(|i| {
                            let detail = if texture {
                                if (i % p.side + i / p.side) % 2 == 0 {
                                    180.0
                                } else {
                                    -180.0
                                }
                            } else {
                                ((i * 7 + p.id * 3 + c) % 3) as f32 - 1.0
                            };
                            1000.0 + p.id as f32 * 5.0 + c as f32 * 30.0 + detail
                        })
                        .collect()
                }),
                refusal: None,
            })
            .collect()
    }
    fn multiply(input: &[CompactPatch], gain: f32) -> Vec<CompactPatch> {
        input
            .iter()
            .map(|p| CompactPatch {
                values: std::array::from_fn(|c| p.values[c].iter().map(|v| v * gain).collect()),
                refusal: p.refusal.clone(),
            })
            .collect()
    }
    fn run_pair(
        anchor: &[CompactPatch],
        source: &[CompactPatch],
        gain: f32,
        index: usize,
    ) -> PairPhotometryReport {
        let cfg = config();
        let n = model();
        let patches = patch_grid(geometry(), &cfg).unwrap();
        let a = PassPhotometryInput {
            nominal_gain: 1.0,
            noise: &n,
            profile: None,
        };
        let b = PassPhotometryInput {
            nominal_gain: gain,
            noise: &n,
            profile: None,
        };
        assess_pair(
            anchor,
            source,
            [&a, &b],
            &patches,
            &cfg,
            blank_report(index),
        )
    }

    #[test]
    fn a00_flat_noise_cannot_certify_focus_compatibility() {
        let patches = patch_grid(geometry(), &config()).unwrap();
        let a = fixture(&patches, false);
        let b = multiply(&a, 6.4);
        let r = run_pair(&a, &b, 1.0 / 6.0, 0);
        assert!(!r.accepted);
        assert_eq!(r.textured_patches, 0);
        assert!(r.refusal.unwrap().contains("flat-only"));
        assert!((r.fitted_log_ratio.unwrap().exp() - 6.4 / 6.0).abs() < 1e-5);
    }
    #[test]
    fn a01_recovers_bounded_exposure_and_keeps_identity() {
        let patches = patch_grid(geometry(), &config()).unwrap();
        let a = fixture(&patches, true);
        let r = run_pair(&a, &multiply(&a, 6.4), 1.0 / 6.0, 0);
        assert!(r.accepted, "{r:?}");
        assert!(r.textured_patches >= 4);
        assert!((r.fitted_log_ratio.unwrap().exp() - 6.4 / 6.0).abs() < 1e-5);
        assert!(r.validation.unwrap().maximum < 2e-6);
        let no_op = run_pair(&a, &a, 1.0, 0);
        assert!(no_op.accepted);
        assert_eq!(no_op.fitted_log_ratio.unwrap().to_bits(), 0.0f32.to_bits());
    }
    #[test]
    fn a02_rejects_excess_gain_color_drift_and_spatial_drift() {
        let patches = patch_grid(geometry(), &config()).unwrap();
        let a = fixture(&patches, true);
        let excess = run_pair(&a, &multiply(&a, 1.4), 1.0, 0);
        assert!(!excess.accepted);
        assert!(excess.refusal.unwrap().contains("EV limit"));
        let mut color = a.clone();
        for p in &mut color {
            for v in &mut p.values[2] {
                *v *= 1.10;
            }
        }
        let r = run_pair(&a, &color, 1.0, 0);
        assert!(!r.accepted);
        assert!(r.refusal.unwrap().contains("spatial/color"));
        let mut spatial = a.clone();
        for (p, g) in spatial.iter_mut().zip(&patches) {
            if g.validation {
                for c in &mut p.values {
                    for v in c {
                        *v *= 1.10;
                    }
                }
            }
        }
        assert!(!run_pair(&a, &spatial, 1.0, 0).accepted);
    }
    #[test]
    fn a03_single_local_flare_cannot_hide_below_percentile() {
        let patches = patch_grid(geometry(), &config()).unwrap();
        let a = fixture(&patches, true);
        let mut b = a.clone();
        let i = patches.iter().position(|p| p.validation).unwrap();
        for values in &mut b[i].values {
            for v in values {
                *v *= 1.20;
            }
        }
        let r = run_pair(&a, &b, 1.0, 0);
        assert!(!r.accepted);
        assert!(r.validation.unwrap().maximum > 0.19);
        let evidence = vec![0.0; 100];
        let mut ratios = evidence;
        ratios[0] = 1.1f32.ln();
        let s = residual_summary(&ratios, 0.0).unwrap();
        assert_eq!(s.p95, 0.0);
        assert!(!passes_residuals(&s, &config()));
    }
    #[test]
    fn a04_blur_and_misregistered_detail_fail_despite_equal_means() {
        let patches = patch_grid(geometry(), &config()).unwrap();
        let a = fixture(&patches, true);
        for detail_gain in [0.5, -1.0] {
            let mut b = a.clone();
            for p in &mut b {
                for c in &mut p.values {
                    let mean = c.iter().sum::<f32>() / c.len() as f32;
                    for v in c {
                        *v = mean + (*v - mean) * detail_gain;
                    }
                }
            }
            let r = run_pair(&a, &b, 1.0, 0);
            assert!(!r.accepted);
            assert!(r.refusal.unwrap().contains("textured overlap"));
            assert!(r.validation.unwrap().maximum < 1e-5);
        }
    }
    #[test]
    fn a05_censored_anchor_and_true_missing_coverage_are_not_evidence() {
        let cfg = config();
        let g = geometry();
        let patches = patch_grid(g, &cfg).unwrap();
        let n = g.width * g.height;
        let mut samples = SampledCfa {
            // Strong texture is deliberate: the short source is six times
            // darker, so its read noise grows by36 in anchor units. This
            // positive support control must exceed the fixed texture guard.
            planes: std::array::from_fn(|c| {
                (0..n)
                    .map(|i| {
                        1000.0
                            + c as f32 * 30.0
                            + if (i % g.width + i / g.width).is_multiple_of(2) {
                                360.0
                            } else {
                                -360.0
                            }
                    })
                    .collect()
            }),
            coverage: vec![true; n],
            clipped: vec![false; n],
            support: vec![true; n],
        };
        let i = patches[0].y * g.width + patches[0].x;
        samples.clipped[i] = true;
        samples.support[i] = false;
        let j = patches[1].y * g.width + patches[1].x;
        samples.coverage[j] = false;
        samples.support[j] = false;
        for plane in &mut samples.planes {
            plane[j] = f32::NAN;
        }
        let compact = compact_patches(&samples, g, &patches);
        assert!(compact[0].refusal.as_ref().unwrap().contains("clipped"));
        assert!(compact[0].values[0].is_empty());
        assert!(compact[1].refusal.as_ref().unwrap().contains("coverage"));
        assert!(compact[1].values[0].is_empty());
        let a = compact;
        let b = multiply(&a, 1.0 / 6.0);
        let r = run_pair(&a, &b, 6.0, 0);
        assert!(r.accepted, "{r:?}");
        assert!(r.textured_patches >= 4);
        assert_eq!(r.patches.iter().filter(|p| p.refusal.is_some()).count(), 2);
    }
    #[test]
    fn a06_variance_uses_original_units_then_gain_squared() {
        let n = model();
        let actual = scaled_variance(&n, CfaPlane::R, 1000.0, 0.25);
        assert_eq!(
            actual.to_bits(),
            (n.variance(CfaPlane::R, 1000.0) * 0.0625).to_bits()
        );
        assert!((actual - n.variance(CfaPlane::R, 250.0)).abs() > 1.0);
    }
    #[test]
    fn a07_requires_multiple_independent_ranks_and_stable_pass_scalar() {
        let cfg = config();
        let patches = patch_grid(geometry(), &cfg).unwrap();
        let a = fixture(&patches, true);
        let pairs = (0..3)
            .map(|i| run_pair(&a, &multiply(&a, 6.4), 1.0 / 6.0, i))
            .collect();
        let good = finalize_pass(1, 1.0 / 6.0, pairs, &cfg);
        assert!(good.accepted, "{good:?}");
        assert!((good.corrected_gain.unwrap() - 1.0 / 6.4).abs() < 1e-6);
        let few = finalize_pass(1, 1.0, good.pairs[..2].to_vec(), &cfg);
        assert!(!few.accepted);
        let mut narrow = good.pairs.clone();
        for p in &mut narrow {
            p.anchor_rank *= 0.1;
        }
        assert!(
            finalize_pass(1, 1.0, narrow, &cfg)
                .refusal
                .unwrap()
                .contains("span")
        );
        let drift = [1.0, 1.01, 1.03]
            .into_iter()
            .enumerate()
            .map(|(i, r)| run_pair(&a, &multiply(&a, r), 1.0, i))
            .collect();
        assert!(
            finalize_pass(1, 1.0, drift, &cfg)
                .refusal
                .unwrap()
                .contains("changes across")
        );
    }
    #[test]
    fn a08_revalidates_with_one_pass_scalar_not_each_pairs_own_fit() {
        let cfg = config();
        let patches = patch_grid(geometry(), &cfg).unwrap();
        let a = fixture(&patches, true);
        let mut pairs = Vec::new();
        for (i, ratio) in [0.991, 1.009, 1.009].into_iter().enumerate() {
            let mut b = multiply(&a, ratio);
            if i == 0 {
                for index in patches
                    .iter()
                    .enumerate()
                    .filter(|(_, p)| p.validation)
                    .take(2)
                    .map(|(i, _)| i)
                {
                    for c in &mut b[index].values {
                        for v in c {
                            *v *= 0.972;
                        }
                    }
                }
            }
            let r = run_pair(&a, &b, 1.0, i);
            assert!(r.accepted, "{r:?}");
            pairs.push(r);
        }
        let r = finalize_pass(1, 1.0, pairs, &cfg);
        assert!(!r.accepted);
        assert!(r.refusal.unwrap().contains("pooled held-out"));
    }
    #[test]
    fn a09_surviving_good_pairs_cannot_hide_supported_contradictions() {
        let cfg = config();
        let patches = patch_grid(geometry(), &cfg).unwrap();
        let a = fixture(&patches, true);
        let good = (0..3).map(|i| run_pair(&a, &a, 1.0, i)).collect::<Vec<_>>();
        assert!(good.iter().all(|p| p.accepted));
        let mut mixed = good.clone();
        for i in 3..9 {
            let mut b = a.clone();
            if i % 2 == 0 {
                b = multiply(&a, 1.4);
            } else {
                for p in &mut b {
                    for v in &mut p.values[2] {
                        *v *= 1.1;
                    }
                }
            }
            let mut pair = run_pair(&a, &b, 1.0, i);
            pair.anchor_rank = (i - 2) as f32 / 8.0;
            pair.source_rank = pair.anchor_rank;
            assert_eq!(
                pair.refusal_kind,
                Some(PairRefusalKind::ContradictoryRadiometry)
            );
            mixed.push(pair);
        }
        let refused = finalize_pass(1, 1.0, mixed, &cfg);
        assert!(!refused.accepted);
        assert!(refused.corrected_gain.is_none());
        assert_eq!(refused.pairs.len(), 9);
        assert_eq!(refused.pairs.iter().filter(|p| p.accepted).count(), 3);
        assert!(refused.refusal.unwrap().contains("contradict"));

        let flat = fixture(&patches, false);
        let mut unavailable = good;
        for i in 3..9 {
            let mut pair = run_pair(&flat, &flat, 1.0, i);
            pair.anchor_rank = (i - 2) as f32 / 8.0;
            pair.source_rank = pair.anchor_rank;
            assert_eq!(
                pair.refusal_kind,
                Some(PairRefusalKind::UnavailableEvidence)
            );
            unavailable.push(pair);
        }
        assert!(finalize_pass(1, 1.0, unavailable, &cfg).accepted);
    }

    #[test]
    fn a10_preflight_refuses_overflow_overlap_and_invalid_limits() {
        let cfg = config();
        let g = geometry();
        assert!(report_bytes(64, &cfg).unwrap() > report_bytes(3, &cfg).unwrap());
        assert!(report_bytes(usize::MAX, &cfg).is_err());
        assert!(report_bytes(0, &cfg).is_err());
        let report_floor = 3
            * cfg.max_pairs_per_pass
            * cfg.grid[0]
            * cfg.grid[1]
            * std::mem::size_of::<PatchEvidence>();
        assert!(report_bytes(3, &cfg).unwrap() > report_floor);
        assert!(
            workspace_bytes(g, &cfg).unwrap() >= sampling_bytes(SamplingDomain::full(g)).unwrap()
        );
        assert!(
            workspace_bytes(
                PlaneGeometry {
                    width: usize::MAX,
                    height: 2
                },
                &cfg
            )
            .is_err()
        );
        let mut bad = cfg.clone();
        bad.workspace_limit_bytes = 1;
        assert!(workspace_bytes(g, &bad).is_err());
        bad = cfg.clone();
        bad.margin = usize::MAX;
        assert!(patch_grid(g, &bad).is_err());
        bad = cfg.clone();
        bad.patch_side = 32;
        assert!(patch_grid(g, &bad).is_err());
        bad = cfg;
        bad.correction_limit_ev = f32::NAN;
        assert!(workspace_bytes(g, &bad).is_err());
    }
}
