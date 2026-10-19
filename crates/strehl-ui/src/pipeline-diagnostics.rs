//! Strict parsing of bounded, actual kernel observations. Invalid snapshots
//! never replace a valid surface or advance the displayed processing stage.

use super::{PipelineProgress, Stage};
use std::sync::Arc;

const MAX_MASK_BINS: usize = 1024;

/// Durable aggregate of actual nearest-sampled binary masks. The bitset records
/// exact observed positions within this bin (at most 64, because total ≤ 65,536).
/// A missing observation is never interpreted as an all-zero mask.
#[derive(Clone, Debug, Default)]
pub struct SampledMaskBin {
    observed: u64,
    pub on_samples: u64,
    pub samples: u64,
}
impl SampledMaskBin {
    pub fn observations(&self) -> usize {
        self.observed.count_ones() as usize
    }
    #[cfg(test)]
    pub fn fraction(&self) -> Option<f32> {
        (self.samples > 0).then(|| self.on_samples as f32 / self.samples as f32)
    }
}

/// Capture order for admitted masks; accepted-prefix order for fallback masks.
/// The first valid mask at each exact position is kept, independently of texture
/// delivery, foreground view and the bounded recent-packet queue.
#[derive(Clone, Debug)]
pub struct SampledMaskHistory {
    pub level: usize,
    pub kind: DiagnosticKind,
    pub total: usize,
    pub bins: Vec<SampledMaskBin>,
}
impl SampledMaskHistory {
    pub fn observations(&self) -> usize {
        self.bins.iter().map(SampledMaskBin::observations).sum()
    }
    /// Exact zero-based axis positions covered by one fixed bin.
    pub fn range(&self, bin: usize) -> std::ops::Range<usize> {
        let bins = self.bins.len();
        (bin * self.total).div_ceil(bins)..((bin + 1) * self.total).div_ceil(bins)
    }
    fn record(&mut self, index: usize, pixels: &[u8]) {
        let bin = index * self.bins.len() / self.total;
        let bit = 1u64 << (index - self.range(bin).start);
        let sample = &mut self.bins[bin];
        if sample.observed & bit == 0 {
            sample.observed |= bit;
            sample.on_samples += pixels.iter().filter(|&&value| value == 255).count() as u64;
            sample.samples += pixels.len() as u64;
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MergeStep {
    Decode,
    Gather,
    Extract,
    Pyramid,
    Focus,
    Fold,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RenderStep {
    Reconstruct,
    Develop,
    Write,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WorkState {
    Started,
    Finished,
    Skipped,
}

/// Compact, durable observations for one real capture. Bits identify only
/// levels whose actual events were received; they are never count prefixes.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct MergeFrameObservation {
    pub decode: Option<WorkState>,
    pub gather: Option<WorkState>,
    pub extract: Option<WorkState>,
    pub pyramid: Option<WorkState>,
    pub focus_started: u64,
    pub fold_started: u64,
    pub fold_finished: u64,
}

impl MergeFrameObservation {
    #[cfg(test)]
    pub fn focus_observed(self, level: usize) -> bool {
        level < 64 && self.focus_started & (1u64 << level) != 0
    }

    #[cfg(test)]
    pub fn fold_state(self, level: usize) -> Option<WorkState> {
        if level >= 64 {
            None
        } else if self.fold_finished & (1u64 << level) != 0 {
            Some(WorkState::Finished)
        } else if self.fold_started & (1u64 << level) != 0 {
            Some(WorkState::Started)
        } else {
            None
        }
    }

    fn observe(&mut self, step: MergeStep, level: Option<usize>, state: WorkState) -> bool {
        let slot = match step {
            MergeStep::Decode => &mut self.decode,
            MergeStep::Gather => &mut self.gather,
            MergeStep::Extract => &mut self.extract,
            MergeStep::Pyramid => &mut self.pyramid,
            MergeStep::Focus | MergeStep::Fold => {
                let Some(level) = level.filter(|level| *level < 64) else {
                    return false;
                };
                let bit = 1u64 << level;
                if step == MergeStep::Focus {
                    if state != WorkState::Started || self.fold_finished & bit != 0 {
                        return false;
                    }
                    self.focus_started |= bit;
                } else {
                    match state {
                        WorkState::Started if self.fold_finished & bit == 0 => {
                            self.fold_started |= bit
                        }
                        WorkState::Finished => self.fold_finished |= bit,
                        _ => return false,
                    }
                }
                return true;
            }
        };
        match (*slot, state) {
            (None | Some(WorkState::Started), _) => *slot = Some(state),
            (Some(previous), next) if previous == next => (),
            _ => return false,
        }
        true
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DiagnosticKind {
    FocusEnergy,
    GateFloor,
    GateSupport,
    Averaging,
    Coefficient,
    /// Coarse canonical green reconstruction, before hull bounds and colour.
    Preview,
    Reconstructed,
}
impl DiagnosticKind {
    pub fn title(self) -> &'static str {
        match self {
            Self::FocusEnergy => "Focus energy",
            Self::GateFloor => "Noise gate floor",
            Self::GateSupport => "Frame gate support",
            Self::Averaging => "Accumulated fallback",
            Self::Coefficient => "Merged green band",
            Self::Preview => "Coarse green reconstruction · pre-hull",
            Self::Reconstructed => "Reconstructed green luma",
        }
    }
    pub fn units(self) -> &'static str {
        match self {
            Self::FocusEnergy | Self::GateFloor => "DN²",
            Self::GateSupport | Self::Averaging => "0–1",
            Self::Coefficient | Self::Preview | Self::Reconstructed => "DN",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DiagnosticScope {
    Frame,
    Stack,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DiagnosticScale {
    Linear,
    Log,
    Symmetric,
}

#[derive(Clone, Debug)]
pub struct DiagnosticSurface {
    pub sequence: u64,
    pub frame: usize,
    pub level: usize,
    pub kind: DiagnosticKind,
    pub scope: DiagnosticScope,
    pub scale: DiagnosticScale,
    pub width: usize,
    pub height: usize,
    pub min: f32,
    pub max: f32,
    pub pixels: Arc<[u8]>,
    pub folded: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct BandWork {
    pub completed: usize,
    pub total: usize,
    pub last_frame: usize,
}

impl PipelineProgress {
    pub(super) fn diagnostic_event(&mut self, fields: &str) {
        let mut keys = std::collections::BTreeMap::new();
        for part in fields.split_whitespace() {
            let Some((key, value)) = part.split_once('=') else {
                return;
            };
            if key.is_empty() || value.is_empty() || keys.insert(key, value).is_some() {
                return;
            }
        }
        let field = |name| keys.get(name).copied();
        let number = |name| field(name).and_then(|v| v.parse::<usize>().ok());
        let Some(total) = number("total") else { return };
        if total == 0
            || total > super::MAX_FRAME_OBSERVATIONS
            || self.frames_total.is_some_and(|known| known != total)
        {
            return;
        }
        let state = || match field("state") {
            Some("started") => Some(WorkState::Started),
            Some("finished") => Some(WorkState::Finished),
            Some("skipped") => Some(WorkState::Skipped),
            _ => None,
        };
        match field("event") {
            Some("merge-step") => {
                if self.stage > Stage::Merge {
                    return;
                }
                let (Some(index), Some(state)) = (number("index"), state()) else {
                    return;
                };
                if index >= total {
                    return;
                }
                let step = match field("name") {
                    Some("decode") => MergeStep::Decode,
                    Some("gather") => MergeStep::Gather,
                    Some("extract") => MergeStep::Extract,
                    Some("pyramid") => MergeStep::Pyramid,
                    Some("focus") => MergeStep::Focus,
                    Some("fold") => MergeStep::Fold,
                    _ => return,
                };
                let level = match field("level") {
                    Some("none") => None,
                    Some(v) => match v.parse::<usize>() {
                        Ok(v) if v < 64 => Some(v),
                        _ => return,
                    },
                    None => return,
                };
                if matches!(step, MergeStep::Focus | MergeStep::Fold) != level.is_some() {
                    return;
                }
                if state == WorkState::Skipped && step != MergeStep::Gather
                    || step == MergeStep::Focus && state != WorkState::Started
                {
                    return;
                }
                if !self
                    .merge_frame_observations
                    .entry(index)
                    .or_default()
                    .observe(step, level, state)
                {
                    return;
                }
                self.frames_total = Some(total);
                self.advance(Stage::Merge);
                self.merge_step = Some(step);
                self.merge_step_frame = Some(index);
                self.merge_step_level = level;
                self.merge_step_state = Some(state);
                self.processing_frame = Some(index);
            }
            Some("band-work") => {
                if self.stage > Stage::Merge {
                    return;
                }
                let (Some(index), Some(level), Some(completed)) =
                    (number("index"), number("level"), number("completed"))
                else {
                    return;
                };
                if index >= total
                    || level >= 64
                    || completed == 0
                    || completed > total
                    || self
                        .merge_bands
                        .get(&level)
                        .is_some_and(|old| old.total != total || completed <= old.completed)
                {
                    return;
                }
                self.frames_total = Some(total);
                self.advance(Stage::Merge);
                self.merge_bands.insert(
                    level,
                    BandWork {
                        completed,
                        total,
                        last_frame: index,
                    },
                );
                self.merge_frame_observations
                    .entry(index)
                    .or_default()
                    .fold_finished |= 1u64 << level;
            }
            Some("render-step") => {
                let Some(state) = state() else { return };
                if state == WorkState::Skipped {
                    return;
                }
                let step = match field("name") {
                    Some("reconstruct") => RenderStep::Reconstruct,
                    Some("develop") => RenderStep::Develop,
                    Some("write") => RenderStep::Write,
                    _ => return,
                };
                if self.stage > Stage::Rendering {
                    return;
                }
                self.frames_total = Some(total);
                self.advance(Stage::Rendering);
                self.render_step = Some(step);
                self.render_step_state = Some(state);
            }
            Some("diagnostic") => {
                if self.stage > Stage::Rendering {
                    return;
                }
                let (
                    Some(sequence),
                    Some(frame),
                    Some(level),
                    Some(width),
                    Some(height),
                    Some(folded),
                ) = (
                    field("seq").and_then(|v| v.parse::<u64>().ok()),
                    number("frame"),
                    number("level"),
                    number("width"),
                    number("height"),
                    number("folded"),
                )
                else {
                    return;
                };
                let kind = match field("kind") {
                    Some("focus-energy") => DiagnosticKind::FocusEnergy,
                    Some("gate-floor") => DiagnosticKind::GateFloor,
                    Some("gate-support") => DiagnosticKind::GateSupport,
                    Some("averaging") => DiagnosticKind::Averaging,
                    Some("coefficient") => DiagnosticKind::Coefficient,
                    Some("preview") => DiagnosticKind::Preview,
                    Some("reconstructed") => DiagnosticKind::Reconstructed,
                    _ => return,
                };
                let (max_width, max_height) = if kind == DiagnosticKind::Preview {
                    (512, 384)
                } else {
                    let [width, height] = crate::process_provenance::SAMPLE_LIMIT;
                    (width, height)
                };
                if sequence == 0
                    || self
                        .diagnostic_surfaces
                        .back()
                        .is_some_and(|old| sequence <= old.sequence)
                    || frame >= total
                    || level >= 64
                    || width == 0
                    || width > max_width
                    || height == 0
                    || height > max_height
                    || folded == 0
                    || folded > total
                    || field("sampling") != Some("nearest")
                {
                    return;
                }
                let scope = match field("scope") {
                    Some("frame") => DiagnosticScope::Frame,
                    Some("stack") => DiagnosticScope::Stack,
                    _ => return,
                };
                let scale = match field("scale") {
                    Some("linear") => DiagnosticScale::Linear,
                    Some("log") => DiagnosticScale::Log,
                    Some("symmetric") => DiagnosticScale::Symmetric,
                    _ => return,
                };
                let float = |name| {
                    field(name)
                        .and_then(|v| v.parse::<f32>().ok())
                        .filter(|v| v.is_finite())
                };
                let (Some(min), Some(max), Some(data)) =
                    (float("min"), float("max"), field("data"))
                else {
                    return;
                };
                if min > max || data.len() != width * height * 2 || !data.is_ascii() {
                    return;
                }
                let expected = match kind {
                    DiagnosticKind::FocusEnergy | DiagnosticKind::GateFloor => {
                        (DiagnosticScope::Frame, DiagnosticScale::Log)
                    }
                    DiagnosticKind::GateSupport => {
                        (DiagnosticScope::Frame, DiagnosticScale::Linear)
                    }
                    DiagnosticKind::Averaging => (DiagnosticScope::Stack, DiagnosticScale::Linear),
                    DiagnosticKind::Coefficient => {
                        (DiagnosticScope::Stack, DiagnosticScale::Symmetric)
                    }
                    DiagnosticKind::Preview | DiagnosticKind::Reconstructed => {
                        (DiagnosticScope::Stack, DiagnosticScale::Linear)
                    }
                };
                if (scope, scale) != expected
                    || scope == DiagnosticScope::Frame && folded != 1
                    || matches!(
                        kind,
                        DiagnosticKind::FocusEnergy
                            | DiagnosticKind::GateFloor
                            | DiagnosticKind::GateSupport
                            | DiagnosticKind::Averaging
                    ) && min < 0.0
                    || matches!(
                        kind,
                        DiagnosticKind::GateSupport | DiagnosticKind::Averaging
                    ) && (min != 0.0 || max != 1.0)
                {
                    return;
                }
                let pixels = data
                    .as_bytes()
                    .as_chunks::<2>()
                    .0
                    .iter()
                    .map(|pair| {
                        let digit = |v: u8| match v {
                            b'0'..=b'9' => Some(v - b'0'),
                            b'a'..=b'f' => Some(v - b'a' + 10),
                            _ => None,
                        };
                        Some(digit(pair[0])? * 16 + digit(pair[1])?)
                    })
                    .collect::<Option<Vec<_>>>();
                let Some(pixels) = pixels else { return };
                let binary = matches!(
                    kind,
                    DiagnosticKind::GateSupport | DiagnosticKind::Averaging
                );
                if binary && pixels.iter().any(|&value| value != 0 && value != 255) {
                    return;
                }
                if binary
                    && self
                        .sampled_mask_history
                        .first()
                        .is_some_and(|history| history.total != total)
                {
                    return;
                }
                let stage = if kind == DiagnosticKind::Reconstructed {
                    Stage::Rendering
                } else {
                    Stage::Merge
                };
                if stage < self.stage {
                    return;
                }
                self.frames_total = Some(total);
                self.advance(stage);
                if binary {
                    let index = if kind == DiagnosticKind::GateSupport {
                        frame
                    } else {
                        folded - 1
                    };
                    if let Some(history) = self
                        .sampled_mask_history
                        .iter_mut()
                        .find(|history| history.level == level && history.kind == kind)
                    {
                        history.record(index, &pixels);
                    } else {
                        let mut history = SampledMaskHistory {
                            level,
                            kind,
                            total,
                            bins: vec![SampledMaskBin::default(); total.min(MAX_MASK_BINS)],
                        };
                        history.record(index, &pixels);
                        self.sampled_mask_history.push(history);
                    }
                }
                let packet = DiagnosticSurface {
                    sequence,
                    frame,
                    level,
                    kind,
                    scope,
                    scale,
                    width,
                    height,
                    min,
                    max,
                    pixels: pixels.into(),
                    folded,
                };
                self.live_preview.observe(
                    &packet,
                    total,
                    self.analysis_size.or(self.plane_size),
                    self.analysis_origin.unwrap_or([0, 0]),
                );
                if let Some(extent) = self.analysis_size.or(self.plane_size) {
                    self.admission_archive.ingest(&packet, extent);
                    self.revisions.observe(&packet, extent);
                }
                if self.diagnostic_surfaces.len() == 384 {
                    self.diagnostic_surfaces.pop_front();
                }
                self.diagnostic_surfaces.push_back(packet);
            }
            _ => (),
        }
    }
}

#[cfg(test)]
#[path = "pipeline-diagnostics-tests.rs"]
mod tests;
