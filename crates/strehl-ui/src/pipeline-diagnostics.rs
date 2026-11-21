//! Strict parsing of bounded, actual kernel observations. Invalid snapshots
//! never replace a valid surface or advance the displayed processing stage.

use super::{PipelineProgress, Stage};
use std::sync::Arc;

const MAX_MASK_BINS: usize = 1024;
/// The recent display ring's length (`MAX_SURFACES` in `process-scales.rs`).
const MAX_RECENT_SURFACES: usize = 384;

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
        let on = pixels.iter().filter(|&&value| value == 255).count() as u64;
        self.record_counted(index, on, pixels.len() as u64);
    }
    fn record_counted(&mut self, index: usize, on: u64, samples: u64) {
        let bin = index * self.bins.len() / self.total;
        let bit = 1u64 << (index - self.range(bin).start);
        let sample = &mut self.bins[bin];
        if sample.observed & bit == 0 {
            sample.observed |= bit;
            sample.on_samples += on;
            sample.samples += samples;
        }
    }
}

/// One plane's admitted share at one level: sampled lattice sites whose gate
/// weight was positive, over all sampled sites. It is support at the noise
/// gate, not the plane's share of the blend.
#[cfg_attr(
    not(test),
    allow(dead_code, reason = "the Stack station (plan P3) reads plane shares")
)]
#[derive(Clone, Debug, PartialEq)]
pub struct PlaneShare {
    pub share: f32,
    pub source: ShareSource,
}

#[cfg_attr(
    not(test),
    allow(dead_code, reason = "the Stack station (plan P3) reads plane shares")
)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ShareSource {
    /// The plane's own retained map.
    Map,
    /// No retained map: the pooled history bin holding this plane, which
    /// covers `frames` and pools the `observed` maps actually received in
    /// them. An approximation for this plane; label it as such.
    Bin {
        frames: std::ops::Range<usize>,
        observed: usize,
    },
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
                    || self.last_log_surface.is_some_and(|old| sequence <= old)
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
                self.last_log_surface = Some(sequence);
                self.retain_surface(packet);
            }
            _ => (),
        }
    }

    /// Keep `packet` in the recent display ring, ordered by the engine's
    /// sequence. The log's stack maps and the evidence file's plane maps
    /// share that sequence but arrive through two readers; ordering by it
    /// keeps the ring what one interleaved stream would have left, so a map
    /// read late never displaces a newer one.
    fn retain_surface(&mut self, packet: DiagnosticSurface) {
        let mut position = self
            .diagnostic_surfaces
            .partition_point(|old| old.sequence <= packet.sequence);
        if self.diagnostic_surfaces.len() == MAX_RECENT_SURFACES {
            if position == 0 {
                return;
            }
            self.diagnostic_surfaces.pop_front();
            position -= 1;
        }
        self.diagnostic_surfaces.insert(position, packet);
    }

    /// One map from the run's evidence file (`evidence-file.rs`). It is
    /// retained evidence, not a stage observation: it never advances the
    /// displayed stage, and a map read after the log has moved on still
    /// counts. Its validation is the hex lines' (done by the decoder), and it
    /// reaches the same stores: the admission archive, the per-position
    /// history and the recent ring.
    pub(crate) fn ingest_evidence(
        &mut self,
        header: &crate::evidence_file::EvidenceHeader,
        record: crate::evidence_file::EvidenceRecord,
    ) {
        let total = header.frames_total;
        if total == 0
            || total > super::MAX_FRAME_OBSERVATIONS
            || self.frames_total.is_some_and(|known| known != total)
        {
            self.evidence_refused += 1;
            return;
        }
        use crate::evidence_file::Role;
        let packet = record.surface;
        // The log's domain when it has named one, as for the hex maps;
        // otherwise the file's own analysis extent.
        let extent = self
            .analysis_size
            .or(self.plane_size)
            .unwrap_or(header.analysis_extent());
        if record.role == Role::RevisionSample {
            // Only the revision trace reads these samples; the displayed
            // preview comes whole from the live file.
            self.revisions.observe(&packet, extent);
            self.evidence_records += 1;
            return;
        }
        if let Some(packed) = &record.packed {
            let binary = match record.role {
                Role::Plane => packet.kind == DiagnosticKind::GateSupport,
                Role::Averaging => packet.kind == DiagnosticKind::Averaging,
                Role::RevisionSample => false,
            };
            if !binary
                || self
                    .sampled_mask_history
                    .first()
                    .is_some_and(|history| history.total != total)
            {
                self.evidence_refused += 1;
                return;
            }
            // Capture order for a plane's masks, accepted-prefix order for
            // the stack's averaging masks, as for the hex maps.
            let index = if packet.kind == DiagnosticKind::GateSupport {
                packet.frame
            } else {
                packet.folded - 1
            };
            let samples = (packet.width * packet.height) as u64;
            if let Some(history) = self
                .sampled_mask_history
                .iter_mut()
                .find(|history| history.level == packet.level && history.kind == packet.kind)
            {
                history.record_counted(index, packed.on, samples);
            } else {
                let mut history = SampledMaskHistory {
                    level: packet.level,
                    kind: packet.kind,
                    total,
                    bins: vec![SampledMaskBin::default(); total.min(MAX_MASK_BINS)],
                };
                history.record_counted(index, packed.on, samples);
                self.sampled_mask_history.push(history);
            }
            if packet.kind == DiagnosticKind::GateSupport {
                self.admission_archive
                    .ingest_packed(&packet, extent, &packed.bits);
            }
        }
        self.evidence_records += 1;
        self.retain_surface(packet);
    }

    /// The newest generation's coefficient maps and coarse preview from the
    /// run's live file. Like the evidence file's maps they never advance the
    /// stage; the preview reaches the live view and the recent ring, the
    /// coefficient maps the ring. Older or repeated sequences change nothing.
    pub(crate) fn ingest_live(&mut self, live: crate::evidence_file::LiveSet) {
        let total = live.frames_total;
        if total == 0
            || total > super::MAX_FRAME_OBSERVATIONS
            || self.frames_total.is_some_and(|known| known != total)
        {
            self.evidence_refused += 1;
            return;
        }
        for packet in live.surfaces {
            if self
                .diagnostic_surfaces
                .iter()
                .any(|old| old.sequence == packet.sequence && old.kind == packet.kind)
            {
                continue;
            }
            if packet.kind == DiagnosticKind::Preview {
                self.live_preview.observe(
                    &packet,
                    total,
                    self.analysis_size.or(self.plane_size),
                    self.analysis_origin.unwrap_or([0, 0]),
                );
            }
            self.evidence_records += 1;
            self.retain_surface(packet);
        }
    }

    /// Everything one render-job event carries, in file order.
    pub(crate) fn ingest_evidence_batch(&mut self, batch: crate::evidence_file::EvidenceBatch) {
        if let Some(header) = batch.header {
            for record in batch.records {
                self.ingest_evidence(&header, record);
            }
        }
        if let Some(live) = batch.live {
            self.ingest_live(live);
        }
    }

    /// The admitted share of `frame` at `level` for views that draw one value
    /// per plane (the Stack station's depth rail). The plane's own retained
    /// map when there is one; otherwise its pooled history bin, marked
    /// [`ShareSource::Bin`]. `None` when nothing was observed for it.
    ///
    /// Cost: a binary search, or one bin read; safe per plane per paint only
    /// through a cache keyed on the archive's revision (plan 5.2).
    #[cfg_attr(
        not(test),
        allow(dead_code, reason = "the Stack station (plan P3) reads plane shares")
    )]
    pub fn plane_share(&self, level: usize, frame: usize) -> Option<PlaneShare> {
        if let Some((admitted, total)) = self.admission_archive.counts(level, frame)
            && total > 0
        {
            return Some(PlaneShare {
                share: admitted as f32 / total as f32,
                source: ShareSource::Map,
            });
        }
        let history = self.sampled_mask_history.iter().find(|history| {
            history.level == level && history.kind == DiagnosticKind::GateSupport
        })?;
        if frame >= history.total {
            return None;
        }
        let index = frame * history.bins.len() / history.total;
        let bin = &history.bins[index];
        (bin.samples > 0).then(|| PlaneShare {
            share: bin.on_samples as f32 / bin.samples as f32,
            source: ShareSource::Bin {
                frames: history.range(index),
                observed: bin.observations(),
            },
        })
    }
}

#[cfg(test)]
#[path = "pipeline-diagnostics-tests.rs"]
mod tests;
