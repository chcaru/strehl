//! A bounded observer for the engine's real log, not a timer-based progress model.
//!
//! Unknown lines never advance a stage. Current engines opt into explicit frame
//! events. Older engines' merge remains indeterminate until its final summary.
//! Alignment counts are completed reads, pyramid preparations and pair attempts;
//! global solving has named phases, without an invented within-solve percentage.

use std::collections::{BTreeMap, BTreeSet, VecDeque};

#[path = "pipeline-view.rs"]
mod view;
pub(crate) use view::ViewProgress;

#[path = "pipeline-confidence.rs"]
mod confidence;
#[path = "pipeline-diagnostics.rs"]
mod diagnostics;
#[path = "pipeline-live-preview.rs"]
mod live_preview;
pub use confidence::ConfidenceProgress;
pub use diagnostics::{
    BandWork, DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface,
    MergeFrameObservation, MergeStep, RenderStep, SampledMaskHistory, WorkState,
};

const MAX_LINE_BYTES: usize = 512 * 1024;
const MAX_EVENTS: usize = 32;
const MAX_FRAME_OBSERVATIONS: usize = 65_536;
const MAX_ALIGNMENT_OBSERVATIONS: usize = 512;
const MAX_ALIGNMENT_EDGE_OBSERVATIONS: usize = 65_536;
pub(crate) const LOG_GAP: &str = "\nLive output skipped ahead; the complete log is saved.\n";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SourceRepairProgress {
    pub region: usize,
    pub regions: usize,
    pub first: usize,
    pub last: usize,
    pub current: usize,
    pub completed: usize,
    pub accepted: usize,
    pub finished: bool,
}

#[cfg(test)]
#[path = "pipeline-history-tests.rs"]
mod history_tests;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, PartialOrd, Ord)]
pub enum Stage {
    #[default]
    Preparing,
    Alignment,
    Merge,
    Rendering,
    Complete,
    Failed,
    Cancelled,
}

impl Stage {
    pub const ALL: [Self; 4] = [
        Self::Preparing,
        Self::Alignment,
        Self::Merge,
        Self::Rendering,
    ];

    pub fn title(self) -> &'static str {
        match self {
            Self::Preparing => "Read capture",
            Self::Alignment => "Align frames",
            Self::Merge => "Build the stack",
            Self::Rendering => "Render & save",
            Self::Complete => "Stack complete",
            Self::Failed => "Stopped with an error",
            Self::Cancelled => "Stack cancelled",
        }
    }

    pub fn description(self) -> &'static str {
        match self {
            Self::Preparing => "Read the RAW capture and resolve its sensor noise model.",
            Self::Alignment => "Fit frame placements and find the area shared by the stack.",
            Self::Merge => {
                "Gather RAW samples and blend detail at each Laplacian scale, averaging below the noise gate."
            }
            Self::Rendering => {
                "Reconstruct colour, apply the viewing tone, and write the 16-bit TIFF."
            }
            Self::Complete => "The TIFF has been checked and saved.",
            Self::Failed => "The engine stopped. Open the saved log for its full explanation.",
            Self::Cancelled => "The owned render process has stopped.",
        }
    }
}

#[derive(Clone, Debug)]
pub struct PipelineEvent {
    pub stage: Stage,
    pub detail: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FrameObservation {
    Started,
    Processed,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum AlignmentPhase {
    Cache,
    Planes,
    Pyramids,
    Pairs,
    CycleCheck,
    Solve,
    Validate,
    Complete,
    Bypassed,
}

impl AlignmentPhase {
    pub fn title(self) -> &'static str {
        match self {
            Self::Cache => "Load saved alignment",
            Self::Planes => "Read alignment frames",
            Self::Pyramids => "Prepare image scales",
            Self::Pairs => "Compare frame pairs",
            Self::CycleCheck => "Check graph consistency",
            Self::Solve => "Place frames together",
            Self::Validate => "Check held-out pairs",
            Self::Complete => "Alignment ready",
            Self::Bypassed => "Alignment bypassed",
        }
    }
}

/// An individual result is known only when the published cumulative delta
/// identifies every result in that interval. Mixed sampled gaps stay unknown.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AlignmentOutcome {
    Accepted,
    Refused,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct AlignmentEdgeObservation {
    pub pair: [usize; 2],
    pub outcome: AlignmentOutcome,
    pub completed: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct MemoryPlan {
    pub chunks: usize,
    pub frame_workers: usize,
    pub retained_accumulators: usize,
    pub scratch_accumulators: usize,
    pub threads: usize,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum CoveragePlan {
    Whole,
    Scaled(f32),
    Cropped {
        width: usize,
        height: usize,
        x: usize,
        y: usize,
        grid_width: usize,
        grid_height: usize,
    },
    Uncovered,
}

#[derive(Debug, Default)]
pub struct PipelineProgress {
    pub(crate) view: Option<ViewProgress>,
    pub(crate) view_observations_missing: bool,
    pub(crate) view_expected: bool,
    pub stage: Stage,
    pub observed_stages: BTreeSet<Stage>,
    pub diagnostic_surfaces: VecDeque<DiagnosticSurface>,
    pub(crate) live_preview: live_preview::LivePreview,
    /// Spatial admission and revision evidence is captured before image-ring eviction.
    pub(crate) admission_archive: crate::process_provenance::AdmissionArchive,
    pub(crate) revisions: crate::process_revision::RevisionField,
    pub(crate) diagnostic_epoch: u64,
    /// Per-position sampled-mask evidence survives recent image-packet eviction.
    pub sampled_mask_history: Vec<SampledMaskHistory>,
    pub merge_step: Option<MergeStep>,
    pub merge_step_frame: Option<usize>,
    pub merge_step_level: Option<usize>,
    pub merge_step_state: Option<WorkState>,
    pub merge_bands: BTreeMap<usize, BandWork>,
    /// Only identities and levels actually present in the bounded event stream.
    /// Cumulative counts never fill in unobserved frames or level prefixes.
    pub merge_frame_observations: BTreeMap<usize, MergeFrameObservation>,
    pub render_step: Option<RenderStep>,
    pub render_step_state: Option<WorkState>,
    pub confidence: Option<ConfidenceProgress>,
    pub(crate) source_repair: Option<SourceRepairProgress>,
    pub frames_total: Option<usize>,
    pub folded: Option<(usize, usize)>,
    pub frames_processed: Option<usize>,
    pub frames_accepted: Option<usize>,
    pub processing_frame: Option<usize>,
    pub reference_frame: Option<usize>,
    pub placed: Option<usize>,
    pub refused: Option<usize>,
    pub bands: Option<usize>,
    pub camera: Option<String>,
    pub iso: Option<String>,
    pub levels: Option<String>,
    pub noise_model: Option<String>,
    pub lateral_ca: Option<String>,
    pub planes: Option<String>,
    pub selection: Option<String>,
    pub gate: Option<String>,
    pub exponents: Option<String>,
    pub base: Option<String>,
    pub alignment: Option<String>,
    pub alignment_error: Option<String>,
    pub alignment_phase: Option<AlignmentPhase>,
    pub alignment_phase_history: BTreeSet<AlignmentPhase>,
    pub alignment_planes: Option<(usize, usize)>,
    pub alignment_pyramids: Option<(usize, usize)>,
    pub alignment_plane_observations: BTreeSet<usize>,
    pub alignment_pyramid_observations: BTreeSet<usize>,
    /// Completed attempts, accepted direct fits, planned attempts. Refusals
    /// contribute to completed work, never to accepted geometry.
    pub alignment_pairs: Option<(usize, usize, usize)>,
    pub alignment_pairs_started: Option<usize>,
    /// Latest emitted started comparison; several workers may be active.
    pub alignment_current_pair: Option<[usize; 2]>,
    pub alignment_latest_pair: Option<[usize; 2]>,
    /// Completed comparisons actually present in the bounded live stream.
    /// This is a sampled history, not the complete graph or fit acceptance.
    pub alignment_observed_pairs: VecDeque<[usize; 2]>,
    /// Durable first observations for the additive atlas, separate from the
    /// recent-pair lane. Once full, later events cannot erase earlier evidence.
    pub alignment_edge_observations: VecDeque<AlignmentEdgeObservation>,
    /// Valid received edge events omitted only after the atlas reached its cap.
    /// This never includes comparisons absent from a sampled progress stream.
    pub alignment_edge_history_omitted: usize,
    pub alignment_source: Option<String>,
    pub coverage: Option<String>,
    pub memory: Option<String>,
    pub averaged: Option<String>,
    pub measured_floor: Option<String>,
    /// All numeric band vectors use the engine's fine-to-coarse index order.
    /// The exponent banner alone prints coarse-to-fine and is reversed on read.
    pub band_exponents: Vec<f32>,
    pub band_averaged: Vec<f32>,
    pub band_floor: Vec<f32>,
    pub band_white: Vec<f32>,
    pub plane_size: Option<[usize; 2]>,
    /// Actual cropped working domain used by sampled merge diagnostics.
    pub analysis_size: Option<[usize; 2]>,
    pub analysis_origin: Option<[usize; 2]>,
    /// The writer's original TIFF dimensions and sampling mode, never a GPU overview.
    pub(crate) output_geometry: Option<crate::process_output_space::OutputGeometry>,
    pub(crate) output_domain: crate::process_output_space::OutputDomain,
    pub memory_plan: Option<MemoryPlan>,
    pub coverage_plan: Option<CoveragePlan>,
    pub frame_observations: BTreeMap<usize, FrameObservation>,
    pub tone: Option<String>,
    pub events: VecDeque<PipelineEvent>,
    pending: String,
    discarding_line: bool,
}

impl PipelineProgress {
    #[cfg(test)]
    pub fn alignment_edge_history_saturated(&self) -> bool {
        self.alignment_edge_history_omitted > 0
    }

    pub fn ingest(&mut self, chunk: &str) {
        // A queue/backlog gap must never splice the beginning and end of
        // unrelated lines into what looks like a real observation.
        let chunk = if let Some(chunk) = chunk.strip_prefix(LOG_GAP) {
            self.view_gap();
            self.pending.clear();
            // File reads resume at an arbitrary byte, so the first resumed
            // line is incomplete too. Resume parsing after its terminator.
            self.discarding_line = true;
            self.record("Some live output was skipped; the saved log is complete.".into());
            chunk
        } else {
            chunk
        };
        for character in chunk.chars() {
            if character == '\n' || character == '\r' {
                if !self.discarding_line {
                    let line = std::mem::take(&mut self.pending);
                    self.line(&line);
                }
                self.pending.clear();
                self.discarding_line = false;
            } else if !self.discarding_line {
                if self.pending.len() + character.len_utf8() > MAX_LINE_BYTES {
                    self.pending.clear();
                    self.discarding_line = true;
                } else {
                    self.pending.push(character);
                }
            }
        }
    }

    pub fn finish(&mut self) {
        if !self.discarding_line {
            let line = std::mem::take(&mut self.pending);
            self.line(&line);
        }
        self.pending.clear();
        self.discarding_line = false;
    }

    pub fn mark_complete(&mut self) {
        self.finish();
        self.stage = Stage::Complete;
    }

    pub fn mark_failed(&mut self) {
        self.finish();
        self.stage = Stage::Failed;
    }

    pub fn mark_cancelled(&mut self) {
        self.finish();
        self.stage = Stage::Cancelled;
    }

    fn advance(&mut self, stage: Stage) {
        if self.stage <= Stage::Rendering && stage >= self.stage {
            self.observed_stages.insert(stage);
            if stage > self.stage {
                self.stage = stage;
            }
        }
    }

    fn record(&mut self, detail: String) {
        if self
            .events
            .back()
            .is_some_and(|event| event.detail == detail)
        {
            return;
        }
        if self.events.len() == MAX_EVENTS {
            self.events.pop_front();
        }
        self.events.push_back(PipelineEvent {
            stage: self.stage,
            detail,
        });
    }

    fn line(&mut self, line: &str) {
        let line = line.trim();
        if let Some(context) = line.strip_prefix("STREHL_UI_VIEW ") {
            self.view_context(context);
            return;
        }
        if self.view_observations_missing {
            return;
        }
        if let Some(fields) = line.strip_prefix("STREHL_UI_PROGRESS ") {
            self.progress_event(fields);
            return;
        }
        if line.starts_with("align: track prior ") {
            self.record(format!("Alignment configuration · {line}"));
            return;
        }
        let Some((key, value)) = line.split_once(':') else {
            return;
        };
        let key = key.trim();
        let value = value.trim();
        if value.is_empty() {
            return;
        }
        let observation = match key {
            "camera" => {
                self.observed_stages.insert(Stage::Preparing);
                self.camera = Some(value.into());
                format!("Camera · {value}")
            }
            "iso" => {
                self.observed_stages.insert(Stage::Preparing);
                self.iso = Some(value.into());
                format!("ISO · {value}")
            }
            "levels" => {
                self.levels = Some(value.into());
                return;
            }
            "noise model" => {
                self.noise_model = Some(value.into());
                format!("Noise model · {value}")
            }
            "lateral CA" => {
                self.lateral_ca = Some(value.into());
                format!("Lateral colour correction · {value}")
            }
            "frames" => {
                let Some(count) = leading_usize(value) else {
                    return;
                };
                if !value.contains(" from ") {
                    return;
                }
                if count == 0 || self.view.as_ref().is_some_and(|v| count != v.source_count) {
                    return;
                }
                self.observed_stages.insert(Stage::Preparing);
                self.frames_total = Some(count);
                format!("{count} RAW frames in filename order")
            }
            "planes" => {
                self.planes = Some(value.into());
                self.plane_size = dimensions(value);
                if self.plane_size.is_some() {
                    self.observed_stages.insert(Stage::Preparing);
                }
                format!("RAW working grid · {value}")
            }
            "analysis domain" => {
                let Some(size) = dimensions(value) else {
                    return;
                };
                let Some(origin) = value
                    .split_once("at full-plane origin (")
                    .and_then(|(_, tail)| tail.split_once(')'))
                    .and_then(|(pair, _)| pair.split_once(','))
                    .and_then(|(x, y)| {
                        Some([
                            x.trim().parse::<usize>().ok()?,
                            y.trim().parse::<usize>().ok()?,
                        ])
                    })
                else {
                    return;
                };
                if self.analysis_size.or(self.plane_size) != Some(size)
                    || self.analysis_origin.unwrap_or([0, 0]) != origin
                {
                    self.diagnostic_epoch = self.diagnostic_epoch.wrapping_add(1);
                    self.admission_archive = Default::default();
                    self.revisions = Default::default();
                    self.live_preview = Default::default();
                    self.diagnostic_surfaces.clear();
                    self.sampled_mask_history.clear();
                }
                self.analysis_size = Some(size);
                self.analysis_origin = Some(origin);
                format!("Merge working domain · {value}")
            }
            "bands" => {
                let Some(count) = leading_usize(value) else {
                    return;
                };
                if !value.contains(" Laplacian levels") {
                    return;
                }
                self.bands = Some(count);
                format!("{count} detail bands plus a tone base")
            }
            "selection" => {
                self.selection = Some(value.into());
                return;
            }
            "noise gate" => {
                self.gate = Some(value.into());
                format!("Noise gate · {value}")
            }
            "per-band exp" => {
                self.exponents = Some(value.into());
                self.band_exponents = numeric_list(value, false).unwrap_or_default();
                self.band_exponents.reverse();
                return;
            }
            "base band" => {
                self.base = Some(value.into());
                return;
            }
            "alignment" => {
                self.alignment = Some(value.into());
                self.reference_frame = number_after(value, "reference frame ");
                self.placed = number_before(value, " placed");
                self.refused = number_before(value, " refused");
                self.advance(Stage::Alignment);
                format!("Alignment · {value}")
            }
            "held-out err" => {
                self.alignment_error = Some(value.into());
                return;
            }
            "coverage" => {
                self.coverage = Some(value.into());
                self.coverage_plan = coverage_plan(value);
                format!("Shared field of view · {value}")
            }
            "memory plan" => {
                self.memory = Some(value.into());
                self.memory_plan = memory_plan(value);
                self.advance(Stage::Merge);
                format!("Memory plan · {value}")
            }
            "folded" => {
                let Some((done, rest)) = value.split_once(" / ") else {
                    return;
                };
                let (Ok(done), Some(total)) = (done.parse::<usize>(), leading_usize(rest)) else {
                    return;
                };
                if total == 0 || done > total || !rest.contains(" frames in ") {
                    return;
                }
                self.folded = Some((done, total));
                // This is a terminal fold summary, including any refused
                // frames; only a structured render-stage event or the colour
                // output proves reconstruction has actually started.
                self.advance(Stage::Merge);
                format!("{done} / {total} frames folded")
            }
            "averaged" => {
                self.averaged = Some(value.into());
                self.band_averaged = numeric_list(value, true).unwrap_or_default();
                format!("Averaged below the gate, by band · {value}")
            }
            "measured floor" => {
                self.measured_floor = Some(value.into());
                self.band_floor = numeric_list(value, false).unwrap_or_default();
                return;
            }
            "band noise gain" => {
                self.band_white = numeric_list(value, false).unwrap_or_default();
                return;
            }
            "colour" => {
                self.advance(Stage::Rendering);
                format!("Colour transform · {value}")
            }
            "tone" => {
                self.tone = Some(value.into());
                self.advance(Stage::Rendering);
                format!("Viewing tone · {value}")
            }
            "output domain" => {
                self.output_domain = crate::process_output_space::OutputDomain::parse(value);
                return;
            }
            "wrote" => {
                self.output_geometry = crate::process_output_space::OutputGeometry::parse(value);
                self.advance(Stage::Rendering);
                "TIFF written; checking the completed file before publication.".into()
            }
            _ => return,
        };
        self.record(observation);
    }

    fn progress_event(&mut self, fields: &str) {
        let mut keys = BTreeSet::new();
        for part in fields.split_whitespace() {
            let Some((key, value)) = part.split_once('=') else {
                return;
            };
            if key.is_empty() || value.is_empty() || !keys.insert(key) {
                return;
            }
        }
        let field = |name: &str| {
            fields.split_whitespace().find_map(|part| {
                let (key, value) = part.split_once('=')?;
                (key == name).then_some(value)
            })
        };
        if field("event") == Some("source-repair") {
            let number = |name| field(name).and_then(|value| value.parse::<usize>().ok());
            let (
                Some(region),
                Some(regions),
                Some(first),
                Some(last),
                Some(current),
                Some(completed),
                Some(accepted),
                Some(total),
            ) = (
                number("region"),
                number("regions"),
                number("first"),
                number("last"),
                number("index"),
                number("completed"),
                number("accepted"),
                number("total"),
            )
            else {
                return;
            };
            let state = field("state");
            if regions == 0
                || regions > 128
                || region >= regions
                || first > last
                || last >= MAX_FRAME_OBSERVATIONS
                || current < first
                || current > last
                || total != last - first + 1
                || completed > total
                || accepted > completed
                || !matches!(state, Some("started" | "folded" | "finished"))
                || state == Some("finished") && completed != total
                || self.stage > Stage::Rendering
            {
                return;
            }
            if let Some(previous) = self.source_repair
                && (region < previous.region
                    || region == previous.region
                        && (completed < previous.completed
                            || previous.finished && state != Some("finished")))
            {
                return;
            }
            self.source_repair = Some(SourceRepairProgress {
                region,
                regions,
                first,
                last,
                current,
                completed,
                accepted,
                finished: state == Some("finished"),
            });
            self.advance(Stage::Rendering);
            self.record(format!(
                "Region {} / {regions} · {completed}/{total} captures rebuilt · {accepted} placed",
                region + 1
            ));
            return;
        }
        if field("event").is_some_and(|event| event.starts_with("align-")) {
            self.alignment_event(fields);
            return;
        }
        if matches!(field("event"), Some("confidence-pass" | "confidence-frame")) {
            self.confidence_event(fields);
            return;
        }
        if matches!(
            field("event"),
            Some("merge-step" | "band-work" | "render-step" | "diagnostic")
        ) {
            self.diagnostic_event(fields);
            return;
        }
        let Some(total) = field("total").and_then(|value| value.parse::<usize>().ok()) else {
            return;
        };
        if total == 0
            || total > MAX_FRAME_OBSERVATIONS
            || self.frames_total.is_some_and(|known| known != total)
            || self.stage > Stage::Rendering
        {
            return;
        }
        match field("event") {
            Some("stage") => {
                let stage = match field("name") {
                    Some("read") => Stage::Preparing,
                    Some("alignment") => Stage::Alignment,
                    Some("merge") => Stage::Merge,
                    Some("render") => Stage::Rendering,
                    _ => return,
                };
                if stage < self.stage {
                    return;
                }
                self.frames_total = Some(total);
                if stage > Stage::Alignment {
                    self.alignment_current_pair = None;
                    self.processing_frame = None;
                }
                self.advance(stage);
                self.record(stage.description().into());
            }
            Some("frame-started") => {
                if self.stage > Stage::Merge {
                    return;
                }
                let Some(index) = field("index").and_then(|value| value.parse::<usize>().ok())
                else {
                    return;
                };
                if index >= total {
                    return;
                }
                self.advance(Stage::Merge);
                self.frames_total = Some(total);
                self.processing_frame = Some(index);
                if self.frame_observations.len() < MAX_FRAME_OBSERVATIONS {
                    self.frame_observations
                        .entry(index)
                        .or_insert(FrameObservation::Started);
                }
            }
            Some("frame-finished") => {
                if self.stage > Stage::Merge {
                    return;
                }
                let number = |name| field(name).and_then(|value| value.parse::<usize>().ok());
                let (Some(index), Some(processed), Some(accepted)) =
                    (number("index"), number("processed"), number("accepted"))
                else {
                    return;
                };
                if index >= total || processed == 0 || processed > total || accepted > processed {
                    return;
                }
                // Never move an already observed count backwards after a gap
                // or an out-of-order event from a future parallel producer.
                if self
                    .frames_processed
                    .is_some_and(|previous| processed < previous)
                {
                    return;
                }
                self.advance(Stage::Merge);
                self.frames_total = Some(total);
                self.frames_processed = Some(processed);
                self.frames_accepted = Some(accepted);
                self.processing_frame = None;
                if self.frame_observations.len() < MAX_FRAME_OBSERVATIONS
                    || self.frame_observations.contains_key(&index)
                {
                    self.frame_observations
                        .insert(index, FrameObservation::Processed);
                }
                self.record(format!(
                    "{processed} / {total} frames processed · {accepted} accepted by alignment"
                ));
            }
            _ => (),
        }
    }

    fn alignment_event(&mut self, fields: &str) {
        if self.stage > Stage::Alignment {
            return;
        }
        let mut keys = BTreeSet::new();
        for part in fields.split_whitespace() {
            let Some((key, value)) = part.split_once('=') else {
                return;
            };
            if key.is_empty() || value.is_empty() || !keys.insert(key) {
                return;
            }
        }
        let field = |name: &str| {
            fields.split_whitespace().find_map(|part| {
                let (key, value) = part.split_once('=')?;
                (key == name).then_some(value)
            })
        };
        let number = |name| field(name).and_then(|value| value.parse::<usize>().ok());
        let (Some(frames), Some(total)) = (number("frames"), number("total")) else {
            return;
        };
        if frames == 0
            || frames > MAX_FRAME_OBSERVATIONS
            || self.frames_total.is_some_and(|known| known != frames)
        {
            return;
        }
        let count =
            |index: usize, completed: usize| index < frames && completed > 0 && completed <= total;
        match field("event") {
            Some("align-phase") => {
                let phase = match field("name") {
                    Some("cache") => AlignmentPhase::Cache,
                    Some("planes") => AlignmentPhase::Planes,
                    Some("pyramids") => AlignmentPhase::Pyramids,
                    Some("pairs") => AlignmentPhase::Pairs,
                    Some("cycle-check") => AlignmentPhase::CycleCheck,
                    Some("solve") => AlignmentPhase::Solve,
                    Some("validate") => AlignmentPhase::Validate,
                    _ => return,
                };
                if self
                    .alignment_phase
                    .is_some_and(|previous| phase <= previous)
                {
                    return;
                }
                let frame_phase = matches!(
                    phase,
                    AlignmentPhase::Cache
                        | AlignmentPhase::Planes
                        | AlignmentPhase::Pyramids
                        | AlignmentPhase::Solve
                );
                if frame_phase && total != frames {
                    return;
                }
                if !frame_phase && total > frames * (frames - 1) / 2 {
                    return;
                }
                self.frames_total = Some(frames);
                self.advance(Stage::Alignment);
                self.alignment_phase = Some(phase);
                self.alignment_phase_history.insert(phase);
                self.alignment_current_pair = None;
                self.processing_frame = None;
                match phase {
                    AlignmentPhase::Planes => self.alignment_planes = Some((0, total)),
                    AlignmentPhase::Pyramids => self.alignment_pyramids = Some((0, total)),
                    AlignmentPhase::Pairs => self.alignment_pairs = Some((0, 0, total)),
                    _ => (),
                }
                self.record(phase.title().into());
            }
            Some("align-plane-start") => {
                let Some(index) = number("index") else { return };
                if self.alignment_phase != Some(AlignmentPhase::Planes)
                    || total != frames
                    || index >= frames
                {
                    return;
                }
                self.processing_frame = Some(index);
            }
            Some("align-plane") => {
                let (Some(index), Some(completed)) = (number("index"), number("completed")) else {
                    return;
                };
                if self.alignment_phase != Some(AlignmentPhase::Planes)
                    || total != frames
                    || !count(index, completed)
                    || self
                        .alignment_planes
                        .is_some_and(|(previous, _)| completed <= previous)
                {
                    return;
                }
                self.alignment_planes = Some((completed, total));
                self.alignment_plane_observations.insert(index);
                self.processing_frame = Some(index);
            }
            Some("align-pyramid") => {
                let (Some(index), Some(completed)) = (number("index"), number("completed")) else {
                    return;
                };
                if self.alignment_phase != Some(AlignmentPhase::Pyramids)
                    || total != frames
                    || !count(index, completed)
                    || self
                        .alignment_pyramids
                        .is_some_and(|(previous, _)| completed <= previous)
                {
                    return;
                }
                self.alignment_pyramids = Some((completed, total));
                self.alignment_pyramid_observations.insert(index);
                self.processing_frame = Some(index);
            }
            Some("align-pair-start") | Some("align-pair") => {
                let (Some(i), Some(j)) = (number("i"), number("j")) else {
                    return;
                };
                if self.alignment_phase != Some(AlignmentPhase::Pairs)
                    || i >= j
                    || j >= frames
                    || total == 0
                    || self
                        .alignment_pairs
                        .is_none_or(|(_, _, planned)| total != planned)
                {
                    return;
                }
                if field("event") == Some("align-pair-start") {
                    let Some(started) = number("started") else {
                        return;
                    };
                    if started == 0
                        || started > total
                        || self
                            .alignment_pairs_started
                            .is_some_and(|old| started <= old)
                    {
                        return;
                    }
                    self.alignment_pairs_started = Some(started);
                    self.alignment_current_pair = Some([i, j]);
                    self.processing_frame = Some(j);
                } else {
                    let (Some(completed), Some(accepted)) =
                        (number("completed"), number("accepted"))
                    else {
                        return;
                    };
                    let (old, old_accepted, _) = self.alignment_pairs.unwrap();
                    if completed <= old
                        || completed > total
                        || accepted < old_accepted
                        || accepted > completed
                        || accepted - old_accepted > completed - old
                    {
                        return;
                    }
                    self.alignment_pairs = Some((completed, accepted, total));
                    self.alignment_latest_pair = Some([i, j]);
                    let outcome = if accepted == old_accepted {
                        AlignmentOutcome::Refused
                    } else if accepted - old_accepted == completed - old {
                        AlignmentOutcome::Accepted
                    } else {
                        AlignmentOutcome::Unknown
                    };
                    if self.alignment_observed_pairs.len() == MAX_ALIGNMENT_OBSERVATIONS {
                        self.alignment_observed_pairs.pop_front();
                    }
                    self.alignment_observed_pairs.push_back([i, j]);
                    if self.alignment_edge_observations.len() < MAX_ALIGNMENT_EDGE_OBSERVATIONS {
                        self.alignment_edge_observations
                            .push_back(AlignmentEdgeObservation {
                                pair: [i, j],
                                outcome,
                                completed,
                            });
                    } else {
                        self.alignment_edge_history_omitted += 1;
                    }
                    if self.alignment_current_pair == Some([i, j]) {
                        self.alignment_current_pair = None;
                    }
                    self.processing_frame = Some(j);
                    self.record(format!(
                        "{completed} / {total} comparisons · {accepted} accepted fits"
                    ));
                }
            }
            Some("align-result") => {
                if matches!(
                    self.alignment_phase,
                    Some(AlignmentPhase::Complete | AlignmentPhase::Bypassed)
                ) {
                    return;
                }
                let (Some(reference), Some(placed), Some(refused)) =
                    (number("reference"), number("placed"), number("refused"))
                else {
                    return;
                };
                let Some(source) = field("source") else {
                    return;
                };
                let bypassed = matches!(source, "off" | "refused");
                if !matches!(source, "solved" | "cache" | "override" | "off" | "refused")
                    || total != frames
                    || reference >= frames
                    || placed > frames
                    || refused > frames
                    || if bypassed {
                        placed != 0 || refused != 0
                    } else {
                        placed + refused != frames
                    }
                {
                    return;
                }
                self.frames_total = Some(frames);
                self.advance(Stage::Alignment);
                self.alignment_source = Some(source.into());
                self.alignment_phase = Some(if bypassed {
                    AlignmentPhase::Bypassed
                } else {
                    AlignmentPhase::Complete
                });
                self.alignment_phase_history
                    .insert(self.alignment_phase.unwrap());
                self.alignment_current_pair = None;
                if bypassed {
                    self.placed = None;
                    self.refused = None;
                    self.reference_frame = None;
                    self.processing_frame = None;
                } else {
                    self.placed = Some(placed);
                    self.refused = Some(refused);
                    self.reference_frame = Some(reference);
                    self.processing_frame = Some(reference);
                }
                self.record(if bypassed {
                    format!("Alignment bypassed · {source}")
                } else {
                    format!("{placed} / {frames} placed · {refused} refused · {source}")
                });
            }
            _ => (),
        }
    }
}

fn dimensions(text: &str) -> Option<[usize; 2]> {
    let mut words = text.split_whitespace();
    let width = words.next()?.parse().ok()?;
    if words.next()? != "x" {
        return None;
    }
    let height = words.next()?.trim_end_matches(',').parse().ok()?;
    (width > 0 && height > 0).then_some([width, height])
}

fn numeric_list(text: &str, percentages: bool) -> Option<Vec<f32>> {
    let text = text.split('(').next()?;
    let values = text
        .split_whitespace()
        .map(|word| {
            let word = if percentages {
                word.strip_suffix('%')?
            } else {
                word
            };
            let value = word.parse::<f32>().ok()?;
            if !value.is_finite() || value < 0.0 || percentages && value > 100.0 {
                return None;
            }
            Some(if percentages { value / 100.0 } else { value })
        })
        .collect::<Option<Vec<_>>>()?;
    (!values.is_empty()).then_some(values)
}

fn memory_plan(text: &str) -> Option<MemoryPlan> {
    let plan = MemoryPlan {
        chunks: number_before(text, " canonical chunks")?,
        frame_workers: number_before(text, " reusable frame worker")?,
        retained_accumulators: number_before(text, " retained")?,
        scratch_accumulators: number_before(text, " scratch accumulator")?,
        threads: number_before(text, " execution threads")?,
    };
    (plan.chunks > 0 && plan.frame_workers > 0 && plan.threads > 0).then_some(plan)
}

fn coverage_plan(text: &str) -> Option<CoveragePlan> {
    if text.contains("every frame covers the whole grid")
        || text.contains("every frame already covers the whole grid")
    {
        return Some(CoveragePlan::Whole);
    }
    if text.starts_with("WARNING -- could not fit a fully covered grid") {
        return Some(CoveragePlan::Uncovered);
    }
    if let Some(rest) = text.strip_prefix("field of view scaled to ") {
        let scale = rest.split_whitespace().next()?.parse::<f32>().ok()?;
        return (scale.is_finite() && scale > 0.0 && scale <= 1.0)
            .then_some(CoveragePlan::Scaled(scale));
    }
    let rest = text.strip_prefix("CROPPED to the region EVERY frame covers -- ")?;
    let [width, height] = dimensions(rest)?;
    let origin = rest.split_once("plane px at (")?.1;
    let (x, origin) = origin.split_once(", ")?;
    let (y, grid) = origin.split_once(") of ")?;
    let (x, y) = (x.parse::<usize>().ok()?, y.parse::<usize>().ok()?);
    let [grid_width, grid_height] = dimensions(grid.trim_end_matches(','))?;
    if x.checked_add(width)? > grid_width || y.checked_add(height)? > grid_height {
        return None;
    }
    Some(CoveragePlan::Cropped {
        width,
        height,
        x,
        y,
        grid_width,
        grid_height,
    })
}

fn leading_usize(text: &str) -> Option<usize> {
    text.split_whitespace().next()?.parse().ok()
}

fn number_after(text: &str, marker: &str) -> Option<usize> {
    let rest = text.split_once(marker)?.1;
    rest.split(|character: char| !character.is_ascii_digit())
        .next()?
        .parse()
        .ok()
}

fn number_before(text: &str, marker: &str) -> Option<usize> {
    text.split_once(marker)?
        .0
        .split_whitespace()
        .last()?
        .parse()
        .ok()
}

/// Keep at most three trailing bytes while a UTF-8 character spans file reads.
#[derive(Default)]
pub(crate) struct Utf8LogDecoder {
    pending: Vec<u8>,
}

impl Utf8LogDecoder {
    pub(crate) fn decode(&mut self, bytes: &[u8], finished: bool) -> String {
        self.pending.extend_from_slice(bytes);
        let mut decoded = String::new();
        let mut offset = 0;
        while offset < self.pending.len() {
            match std::str::from_utf8(&self.pending[offset..]) {
                Ok(text) => {
                    decoded.push_str(text);
                    offset = self.pending.len();
                }
                Err(error) => {
                    let end = offset + error.valid_up_to();
                    decoded.push_str(
                        std::str::from_utf8(&self.pending[offset..end])
                            .expect("validated UTF-8 prefix"),
                    );
                    offset = end;
                    match error.error_len() {
                        Some(length) => {
                            decoded.push('\u{fffd}');
                            offset += length;
                        }
                        None if finished => {
                            decoded.push('\u{fffd}');
                            offset = self.pending.len();
                        }
                        None => break,
                    }
                }
            }
        }
        self.pending.drain(..offset);
        decoded
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn regional_repair_progress_is_actual_work_and_never_rewinds_global_counts() {
        let mut progress = PipelineProgress {
            frames_total: Some(197),
            frames_processed: Some(197),
            stage: Stage::Merge,
            ..Default::default()
        };
        progress.ingest("STREHL_UI_PROGRESS event=source-repair region=0 regions=2 first=40 last=49 index=40 completed=0 accepted=0 total=10 state=started\n");
        assert_eq!(progress.stage, Stage::Rendering);
        assert_eq!(progress.frames_total, Some(197));
        assert_eq!(progress.frames_processed, Some(197));
        progress.ingest("STREHL_UI_PROGRESS event=source-repair region=0 regions=2 first=40 last=49 index=45 completed=6 accepted=4 total=10 state=folded\n");
        let observed = progress.source_repair.unwrap();
        assert_eq!(observed.completed, 6);
        assert_eq!(observed.accepted, 4);
        for invalid in [
            "region=0 regions=2 first=40 last=49 index=41 completed=2 accepted=2 total=10 state=folded",
            "region=0 regions=2 first=40 last=49 index=45 completed=6 accepted=7 total=10 state=folded",
            "region=0 regions=2 first=40 last=49 index=45 completed=6 accepted=4 total=10 state=finished",
            "region=0 regions=2 first=40 last=49 index=45 completed=6 accepted=4 total=197 state=folded",
        ] {
            progress.ingest(&format!(
                "STREHL_UI_PROGRESS event=source-repair {invalid}\n"
            ));
            assert_eq!(progress.source_repair, Some(observed));
        }
        progress.ingest("STREHL_UI_PROGRESS event=source-repair region=0 regions=2 first=40 last=49 index=49 completed=10 accepted=8 total=10 state=finished\n");
        assert!(progress.source_repair.unwrap().finished);
        progress.ingest("STREHL_UI_PROGRESS event=source-repair region=1 regions=2 first=80 last=80 index=80 completed=0 accepted=0 total=1 state=started\n");
        assert_eq!(progress.source_repair.unwrap().region, 1);
        assert!(!progress.source_repair.unwrap().finished);
    }

    // Retained output: outputs/strehl-1792271060583-37452-0/render.log.
    const LOG: &str = "align: track prior on, lambda=1 huber=Some(1.0) px\n\
camera          : ILCE-7CM2\n\
noise model     : PROVENANCE=Profile -- camera profile at ISO 100. Trustworthy for ranking.\n\
frames          : 259 from D:\\capture  (first decode 0.13 s)\n\
bands           : 7 Laplacian levels + 1 base, coarsest 28 x 19\n\
alignment       : ON (solved), reference frame 129, 259 placed / 0 refused, 63.9 s\n\
  held-out err  : 2.728 px   resampler: CatmullRom\n\
memory plan     : 4 canonical chunks, 1 reusable frame worker, 1 retained + 1 scratch accumulator, 4 execution threads\n\
folded          : 259 / 259 frames in 344.6 s (1.33 s per frame, 4 execution threads)\n\
tone            : black 0.01568, white 0.51089 (linear), contrast 0.55\n\
wrote           : result.partial.tiff (7032 x 4688, 16-bit RGB)\n";

    #[test]
    fn retained_engine_lines_survive_arbitrary_chunks_and_carriage_returns() {
        let mut progress = PipelineProgress::default();
        for character in LOG.replace('\n', "\r\n").chars() {
            progress.ingest(&character.to_string());
        }
        assert_eq!(progress.stage, Stage::Rendering);
        assert_eq!(progress.frames_total, Some(259));
        assert_eq!(progress.folded, Some((259, 259)));
        assert_eq!(progress.reference_frame, Some(129));
        assert_eq!((progress.placed, progress.refused), (Some(259), Some(0)));
        assert_eq!(progress.bands, Some(7));
        assert!(
            progress
                .noise_model
                .as_deref()
                .unwrap()
                .contains("PROVENANCE=Profile")
        );
        progress.mark_complete();
        assert_eq!(progress.stage, Stage::Complete);
    }

    #[test]
    fn unrelated_numbers_and_promised_stages_cannot_invent_progress() {
        let mut progress = PipelineProgress::default();
        progress.ingest(
            "Arguments: [stack, --pyramid-bands, 8]\n\
not applied     : photometric gain, clip census, outlier rejection, through-focus statistics\n\
WARN rawler: frames: 99 / 100, wrote: example\n\
folded          : 5 / 3 frames in 1 s\n\
folded          : 1 / 0 frames in 1 s\n",
        );
        assert_eq!(progress.stage, Stage::Preparing);
        assert!(progress.events.is_empty());
        assert_eq!(progress.frames_total, None);
        assert_eq!(progress.folded, None);
        progress.ingest("memory plan     : 4 chunks\n");
        assert_eq!(progress.stage, Stage::Merge);
        assert_eq!(
            progress.folded, None,
            "no count is known during the real fold"
        );
        progress.ingest("folded: 1 / 259 frames in 1 s\n");
        assert_eq!(
            progress.stage,
            Stage::Merge,
            "a partial/refused count cannot imply reconstruction started"
        );
        assert_eq!(progress.folded, Some((1, 259)));
    }

    #[test]
    fn partial_lines_gaps_and_oversize_lines_do_not_fabricate_observations() {
        let mut progress = PipelineProgress::default();
        progress.ingest("frames          : 9");
        progress.ingest(&format!("{LOG_GAP}99 from other capture\n"));
        assert_eq!(progress.frames_total, None);
        progress.ingest(&"x".repeat(MAX_LINE_BYTES + 1));
        progress.ingest("frames: 42 from a misleading long line\r");
        assert_eq!(progress.frames_total, None);
        progress.ingest("frames: 42 from real capture");
        assert_eq!(progress.frames_total, None);
        progress.finish();
        assert_eq!(progress.frames_total, Some(42));
        for index in 0..100 {
            progress.ingest(&format!("iso: {index}\n"));
        }
        assert_eq!(progress.events.len(), MAX_EVENTS);
    }

    #[test]
    fn utf8_split_at_every_byte_is_lossless_and_invalid_bytes_are_bounded() {
        let text = "camera: caméra · スタック\r\n";
        let mut decoder = Utf8LogDecoder::default();
        let mut decoded = String::new();
        for byte in text.as_bytes() {
            decoded.push_str(&decoder.decode(&[*byte], false));
            assert!(decoder.pending.len() <= 3);
        }
        decoded.push_str(&decoder.decode(&[], true));
        assert_eq!(decoded, text);
        assert_eq!(decoder.decode(&[0xff, b'a', 0xe2], false), "\u{fffd}a");
        assert_eq!(decoder.decode(&[], true), "\u{fffd}");
        assert!(decoder.pending.is_empty());
    }

    #[test]
    fn structured_counts_distinguish_processed_from_accepted_and_reject_invalid_events() {
        let mut progress = PipelineProgress::default();
        progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=3\n");
        assert_eq!(progress.stage, Stage::Alignment);
        progress.ingest("STREHL_UI_PROGRESS event=frame-started index=0 total=3\n");
        assert_eq!(progress.processing_frame, Some(0));
        progress.ingest(
            "STREHL_UI_PROGRESS event=frame-finished index=0 processed=1 accepted=1 total=3\n\
STREHL_UI_PROGRESS event=frame-finished index=1 processed=2 accepted=1 total=3\n",
        );
        assert_eq!(progress.frames_processed, Some(2));
        assert_eq!(progress.frames_accepted, Some(1));
        assert_eq!(progress.stage, Stage::Merge);
        progress.ingest(
            "STREHL_UI_PROGRESS event=frame-finished index=1 processed=1 accepted=1 total=3\n\
STREHL_UI_PROGRESS event=frame-finished index=3 processed=4 accepted=4 total=3\n\
STREHL_UI_PROGRESS event=frame-finished index=2 processed=3 accepted=4 total=3\n\
STREHL_UI_PROGRESS event=stage name=complete total=3\n",
        );
        assert_eq!(progress.frames_processed, Some(2));
        assert_eq!(progress.stage, Stage::Merge);
        progress.ingest(
            "STREHL_UI_PROGRESS event=frame-finished index=2 processed=3 accepted=2 total=3\n",
        );
        assert_eq!(progress.frames_processed, Some(3));
        assert_eq!(
            progress.stage,
            Stage::Merge,
            "finishing frame processing does not mean the TIFF is saved"
        );
    }

    #[test]
    fn retained_pyramid_statistics_keep_their_actual_band_order_and_units() {
        // The exponent banner reverses the merge's index order. The other
        // banners do not. An un-reversed implementation swaps B0's 98.7%
        // averaging result onto the wrong configured exponent.
        let mut progress = PipelineProgress::default();
        progress.ingest(
            "planes: 3516 x 2344 per CFA plane\n\
per-band exp: 2 3 4 5 8 8 8   (coarsest -> finest)\n\
memory plan: 3 canonical chunks, 1 reusable frame worker, 1 retained + 1 scratch accumulator, 1 execution threads\n\
band noise gain: 0.8898 0.0529 0.0101 0.0024 0.0006 0.0001 0.0000 0.0000\n\
measured floor: 1.0237 0.0490 0.0099 0.0024\n\
averaged: 98.7% 80.1% 41.7% 2.8% 0.0% 0.0% 0.0% 100.0%\n",
        );
        assert_eq!(progress.plane_size, Some([3516, 2344]));
        assert_eq!(progress.band_exponents, [8.0, 8.0, 8.0, 5.0, 4.0, 3.0, 2.0]);
        assert!((progress.band_averaged[0] - 0.987).abs() < 0.0001);
        assert_eq!(progress.band_averaged.last(), Some(&1.0));
        assert_eq!(
            progress.band_floor.len(),
            4,
            "no invented coarse-band measurements"
        );
        assert!((progress.band_floor[0] / progress.band_white[0] - 1.1505).abs() < 0.0001);
        assert_eq!(
            progress.memory_plan,
            Some(MemoryPlan {
                chunks: 3,
                frame_workers: 1,
                retained_accumulators: 1,
                scratch_accumulators: 1,
                threads: 1,
            })
        );
    }

    #[test]
    fn coverage_schematic_requires_a_real_supported_geometry_observation() {
        assert_eq!(
            coverage_plan("field of view scaled to 0.9562 so that EVERY frame covers every pixel"),
            Some(CoveragePlan::Scaled(0.9562))
        );
        assert_eq!(
            coverage_plan(
                "CROPPED to the region EVERY frame covers -- 3300 x 2200 plane px at (100, 60) of 3516 x 2344, emitted at UNITY SCALE. 6.1% of width dropped"
            ),
            Some(CoveragePlan::Cropped {
                width: 3300,
                height: 2200,
                x: 100,
                y: 60,
                grid_width: 3516,
                grid_height: 2344,
            })
        );
        for text in [
            "field of view scaled to NaN",
            "field of view scaled to 1.25",
            "CROPPED to the region EVERY frame covers -- 3300 x 2200 plane px at (300, 60) of 3516 x 2344, emitted at UNITY SCALE.",
            "99.0% of the frames are probably aligned",
        ] {
            assert_eq!(coverage_plan(text), None, "{text}");
        }
        assert_eq!(numeric_list("98% NaN%", true), None);
        assert_eq!(numeric_list("101%", true), None);
        assert_eq!(numeric_list("-1 2", false), None);
        assert_eq!(memory_plan("4 chunks, 20 GiB maybe"), None);
    }

    #[test]
    fn gaps_and_missing_events_leave_frame_identity_unknown() {
        let mut progress = PipelineProgress::default();
        progress.ingest("STREHL_UI_PROGRESS event=frame-started index=0 total=4\n");
        assert_eq!(
            progress.frame_observations.get(&0),
            Some(&FrameObservation::Started)
        );
        progress.ingest(
            "STREHL_UI_PROGRESS event=frame-finished index=0 processed=1 accepted=1 total=4\n",
        );
        progress.ingest(&format!("{LOG_GAP}incomplete line\n"));
        progress.ingest(
            "STREHL_UI_PROGRESS event=frame-finished index=3 processed=4 accepted=3 total=4\n",
        );
        assert_eq!(progress.frames_processed, Some(4));
        assert_eq!(
            progress.frame_observations.get(&0),
            Some(&FrameObservation::Processed)
        );
        assert_eq!(
            progress.frame_observations.get(&3),
            Some(&FrameObservation::Processed)
        );
        assert!(!progress.frame_observations.contains_key(&1));
        assert!(!progress.frame_observations.contains_key(&2));
        assert_eq!(
            progress.frames_accepted,
            Some(3),
            "aggregate acceptance cannot identify which frame refused"
        );
    }

    #[test]
    fn alignment_work_reports_real_counts_and_rejects_regressions_and_impossible_acceptance() {
        // Refused comparisons, missing snapshots and concurrent start/finish
        // order are deliberately different from a sequential all-success log.
        let mut progress = PipelineProgress::default();
        let ingest = |progress: &mut PipelineProgress, fields: &str| {
            progress.ingest(&format!("STREHL_UI_PROGRESS {fields} frames=4\n"));
        };
        ingest(&mut progress, "event=align-phase name=planes total=4");
        ingest(&mut progress, "event=align-plane-start index=3 total=4");
        assert_eq!(progress.processing_frame, Some(3));
        ingest(
            &mut progress,
            "event=align-plane index=3 completed=1 total=4",
        );
        ingest(
            &mut progress,
            "event=align-plane index=1 completed=3 total=4",
        );
        ingest(
            &mut progress,
            "event=align-plane index=2 completed=2 total=4",
        );
        assert_eq!(progress.alignment_planes, Some((3, 4)));
        assert_eq!(progress.processing_frame, Some(1));
        ingest(&mut progress, "event=align-phase name=pyramids total=4");
        ingest(
            &mut progress,
            "event=align-pyramid index=2 completed=4 total=4",
        );
        assert_eq!(progress.alignment_pyramids, Some((4, 4)));
        assert_eq!(progress.processing_frame, Some(2));
        ingest(&mut progress, "event=align-phase name=pairs total=6");
        ingest(
            &mut progress,
            "event=align-pair-start i=0 j=3 started=1 total=6",
        );
        assert_eq!(progress.alignment_current_pair, Some([0, 3]));
        assert_eq!(progress.processing_frame, Some(3));
        ingest(
            &mut progress,
            "event=align-pair i=0 j=3 completed=1 accepted=0 total=6",
        );
        assert_eq!(progress.alignment_current_pair, None);
        assert_eq!(progress.alignment_latest_pair, Some([0, 3]));
        ingest(
            &mut progress,
            "event=align-pair-start i=1 j=3 started=3 total=6",
        );
        ingest(
            &mut progress,
            "event=align-pair i=0 j=2 completed=3 accepted=1 total=6",
        );
        assert_eq!(
            progress.alignment_current_pair,
            Some([1, 3]),
            "Another worker completing must not finish the latest active comparison"
        );
        assert_eq!(progress.alignment_pairs, Some((3, 1, 6)));
        let snapshot = (
            progress.alignment_pairs,
            progress.alignment_current_pair,
            progress.processing_frame,
        );
        for invalid in [
            "event=align-pair i=0 j=1 completed=2 accepted=1 total=6",
            "event=align-pair i=0 j=1 completed=4 accepted=3 total=6",
            "event=align-pair i=0 j=1 completed=4 accepted=0 total=6",
            "event=align-pair i=0 j=4 completed=4 accepted=2 total=6",
            "event=align-pair i=2 j=1 completed=4 accepted=2 total=6",
            "event=align-pair i=1 j=1 completed=4 accepted=2 total=6",
            "event=align-pair i=0 j=1 completed=7 accepted=2 total=6",
            "event=align-pair i=0 j=1 completed=4 accepted=2 total=6 total=3",
            "event=align-pair-start i=0 j=1 started=2 total=6",
            "event=align-phase name=planes total=4",
        ] {
            ingest(&mut progress, invalid);
            assert_eq!(
                (
                    progress.alignment_pairs,
                    progress.alignment_current_pair,
                    progress.processing_frame
                ),
                snapshot,
                "Accepted invalid event: {invalid}"
            );
        }
        ingest(&mut progress, "event=align-phase name=cycle-check total=1");
        ingest(&mut progress, "event=align-phase name=solve total=4");
        assert_eq!(progress.alignment_phase, Some(AlignmentPhase::Solve));
        assert_eq!(
            progress.processing_frame, None,
            "A global solve has no invented active source frame"
        );
        assert_eq!(
            progress.alignment_pairs,
            Some((3, 1, 6)),
            "A phase change cannot manufacture unobserved completions"
        );
        ingest(&mut progress, "event=align-phase name=validate total=1");
        ingest(
            &mut progress,
            "event=align-result source=solved reference=2 placed=3 refused=1 total=4",
        );
        assert_eq!(progress.alignment_phase, Some(AlignmentPhase::Complete));
        assert_eq!(progress.alignment_source.as_deref(), Some("solved"));
        assert_eq!(
            (progress.placed, progress.refused, progress.reference_frame),
            (Some(3), Some(1), Some(2))
        );
        assert_eq!(progress.processing_frame, Some(2));
        progress.ingest("STREHL_UI_PROGRESS event=stage name=merge total=4\nSTREHL_UI_PROGRESS event=frame-started index=1 total=4\n");
        ingest(
            &mut progress,
            "event=align-pair i=0 j=1 completed=6 accepted=4 total=6",
        );
        assert_eq!(progress.stage, Stage::Merge);
        assert_eq!(
            progress.processing_frame,
            Some(1),
            "Late alignment cannot steal merge follow focus"
        );
        assert_eq!(progress.alignment_pairs, Some((3, 1, 6)));
    }

    #[test]
    fn cached_and_bypassed_alignment_never_invents_plane_or_pair_work() {
        for source in ["cache", "override", "off", "refused"] {
            let mut progress = PipelineProgress::default();
            progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=8\n");
            if matches!(source, "cache" | "override") {
                progress
                    .ingest("STREHL_UI_PROGRESS event=align-phase name=cache total=8 frames=8\n");
            }
            let (placed, refused) = if matches!(source, "off" | "refused") {
                (0, 0)
            } else {
                (7, 1)
            };
            let event = format!(
                "STREHL_UI_PROGRESS event=align-result source={source} reference=4 placed={placed} refused={refused} total=8 frames=8\n"
            );
            let split = event.len() / 2;
            progress.ingest(&event[..split]);
            assert!(
                progress.alignment_source.is_none(),
                "Partial lines cannot certify a result"
            );
            progress.ingest(&event[split..]);
            assert_eq!(progress.alignment_source.as_deref(), Some(source));
            assert!(progress.alignment_planes.is_none());
            assert!(progress.alignment_pyramids.is_none());
            assert!(progress.alignment_pairs.is_none());
            assert!(progress.alignment_current_pair.is_none());
            assert_eq!(
                progress.alignment_phase,
                Some(if placed == 0 {
                    AlignmentPhase::Bypassed
                } else {
                    AlignmentPhase::Complete
                })
            );
            assert_eq!(progress.placed, (placed > 0).then_some(placed));
        }
        let mut progress = PipelineProgress::default();
        for invalid in [
            "event=align-phase name=planes total=4 frames=0",
            "event=align-phase name=pairs total=100 frames=4",
            "event=align-plane index=0 completed=1 total=4 frames=4",
            "event=align-result source=guessed reference=2 placed=4 refused=0 total=4 frames=4",
            "event=align-result source=solved reference=4 placed=4 refused=0 total=4 frames=4",
            "event=align-result source=solved reference=2 placed=4 refused=1 total=4 frames=4",
            "event=align-result source=off reference=0 placed=4 refused=0 total=4 frames=4",
        ] {
            progress.ingest(&format!("STREHL_UI_PROGRESS {invalid}\n"));
        }
        assert_eq!(progress.stage, Stage::Preparing);
        assert!(progress.alignment_phase.is_none());
        assert!(progress.frames_total.is_none());
    }

    #[test]
    fn alignment_graph_keeps_only_bounded_observed_connections_and_never_fills_gaps() {
        let mut sparse = PipelineProgress::default();
        sparse.ingest(
            "STREHL_UI_PROGRESS event=align-phase name=pairs total=780 frames=40\n\
STREHL_UI_PROGRESS event=align-pair i=0 j=37 completed=37 accepted=19 total=780 frames=40\n\
STREHL_UI_PROGRESS event=align-pair i=5 j=30 completed=250 accepted=125 total=780 frames=40\n",
        );
        assert_eq!(
            sparse.alignment_observed_pairs,
            VecDeque::from([[0, 37], [5, 30]]),
            "A skipped/sampled count cannot manufacture missing graph edges"
        );
        sparse.ingest("STREHL_UI_PROGRESS event=align-pair i=1 j=2 completed=100 accepted=50 total=780 frames=40\n");
        assert_eq!(
            sparse.alignment_observed_pairs.len(),
            2,
            "An out-of-order observation cannot add a connection"
        );

        let pairs: Vec<_> = (0..40)
            .flat_map(|i| (i + 1..40).map(move |j| [i, j]))
            .collect();
        let mut dense = PipelineProgress::default();
        dense.ingest("STREHL_UI_PROGRESS event=align-phase name=pairs total=780 frames=40\n");
        for (index, [i, j]) in pairs.iter().copied().take(600).enumerate() {
            let completed = index + 1;
            dense.ingest(&format!("STREHL_UI_PROGRESS event=align-pair i={i} j={j} completed={completed} accepted={} total=780 frames=40\n", completed / 2));
        }
        assert_eq!(dense.alignment_observed_pairs.len(), 512);
        assert_eq!(dense.alignment_observed_pairs.front(), Some(&pairs[88]));
        assert_eq!(dense.alignment_observed_pairs.back(), Some(&pairs[599]));
        assert_eq!(
            dense.alignment_pairs,
            Some((600, 300, 780)),
            "The graph's memory budget cannot change the aggregate work count"
        );
        assert_ne!(
            sparse.alignment_observed_pairs.len(),
            dense.alignment_observed_pairs.len(),
            "The control must distinguish two observed connections from a populated history"
        );
    }
}
