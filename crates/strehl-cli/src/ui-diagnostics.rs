//! Spatially bounded views of every actual merge fold. None of these values are
//! returned to the image pipeline, and disabled/placebo runs create no tap.

use super::Progress;
use super::evidence;
use std::path::Path;
use strehl_core::pyramid::{
    AccumulatorObservation, BandMerge, BandObservation, FoldPhase, LevelSize, MergeObserver,
    Pyramid, Workspace,
};

// Retain four times as many real observations as the original desktop grid.
// This is still a bounded read-only tap; pyramid coefficient spacing does not
// change and unsampled coefficients are never synthesized for the display.
const GRID_WIDTH: usize = 128;
const GRID_HEIGHT: usize = 96;
const PREVIEW_WIDTH: usize = 512;
const PREVIEW_HEIGHT: usize = 384;

#[derive(Default)]
pub(super) struct DiagnosticCounts {
    sequence: u64,
    bands: Vec<usize>,
    accumulator_frames: usize,
    /// This pass's evidence file ([`Progress::begin_evidence`]): its
    /// per-plane maps go there instead of into the log.
    evidence: Option<evidence::Writer>,
}

/// The desktop's lattice for a map of a `size` grid: at most `GRID_WIDTH` x
/// `GRID_HEIGHT`, aspect preserved, never upsampled. Every map kind but the
/// preview, the evidence file's header and the GPU fold's admission maps use
/// it, so all of them sample the same sites.
pub(crate) fn lattice(size: LevelSize) -> [usize; 2] {
    lattice_within(size, GRID_WIDTH, GRID_HEIGHT)
}

fn lattice_within(size: LevelSize, max_width: usize, max_height: usize) -> [usize; 2] {
    let factor = (max_width as f64 / size.width as f64)
        .min(max_height as f64 / size.height as f64)
        .min(1.0);
    [
        (size.width as f64 * factor).floor().max(1.0) as usize,
        (size.height as f64 * factor).floor().max(1.0) as usize,
    ]
}

/// The bytes of a map as the log's hex lines carry them.
fn hex(pixels: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut hex = String::with_capacity(pixels.len() * 2);
    for &pixel in pixels {
        hex.push(DIGITS[(pixel >> 4) as usize] as char);
        hex.push(DIGITS[(pixel & 15) as usize] as char);
    }
    hex
}

pub(crate) struct FrameTap<'a> {
    progress: &'a Progress,
    index: usize,
    levels: usize,
}

impl<'a> FrameTap<'a> {
    pub(crate) fn new(progress: &'a Progress, index: usize, levels: usize) -> Self {
        Self {
            progress,
            index,
            levels,
        }
    }
}

impl MergeObserver for FrameTap<'_> {
    #[cfg(feature = "temporal-energy")]
    fn supports_absolute_floor(&self) -> bool {
        true
    }
    fn phase(&self, phase: FoldPhase) {
        match phase {
            FoldPhase::PyramidStarted => self
                .progress
                .merge_step(self.index, "pyramid", None, "started"),
            FoldPhase::PyramidReady => self
                .progress
                .merge_step(self.index, "pyramid", None, "finished"),
            FoldPhase::FocusStarted(level) => {
                self.progress
                    .merge_step(self.index, "focus", Some(level), "started")
            }
            FoldPhase::FoldStarted(level) => {
                self.progress
                    .merge_step(self.index, "fold", Some(level), "started")
            }
            FoldPhase::FoldFinished(level) => {
                self.progress.band_finished(self.index, level);
                self.progress
                    .merge_step(self.index, "fold", Some(level), "finished");
            }
        }
    }

    fn band(&self, band: BandObservation<'_>) {
        if !self.progress.enabled || band.level >= self.levels {
            return;
        }
        if let Some(energy) = band.energy {
            self.progress.surface(
                self.index,
                band.level,
                "focus-energy",
                "frame",
                "log",
                1,
                band.size,
                |index| energy[index],
                None,
            );
        }
        #[cfg(feature = "temporal-energy")]
        if let Some(floor) = band.absolute_floor {
            self.progress.surface(
                self.index,
                band.level,
                "gate-floor",
                "frame",
                "log",
                1,
                band.size,
                |index| floor[index],
                None,
            );
        }
        if let Some(variance) = band.variance {
            self.progress.surface(
                self.index,
                band.level,
                "gate-floor",
                "frame",
                "log",
                1,
                band.size,
                |index| band.floor_multiplier * variance[index].max(0.0),
                None,
            );
        }
        self.progress.surface(
            self.index,
            band.level,
            "gate-support",
            "frame",
            "linear",
            1,
            band.size,
            |index| if band.weights[index] > 0.0 { 1.0 } else { 0.0 },
            Some((0.0, 1.0)),
        );
    }
}

impl Progress {
    pub(crate) fn merge_step(&self, index: usize, name: &str, level: Option<usize>, state: &str) {
        if self.enabled {
            self.emit(format!(
                "event=merge-step index={index} name={name} state={state} level={} total={}",
                level.map_or_else(|| "none".into(), |level| level.to_string()),
                self.total
            ));
        }
    }

    fn band_finished(&self, index: usize, level: usize) {
        if !self.enabled || level >= 64 {
            return;
        }
        let mut counts = self
            .diagnostics
            .lock()
            .expect("merge diagnostics lock poisoned");
        if counts.bands.len() <= level {
            counts.bands.resize(level + 1, 0);
        }
        counts.bands[level] += 1;
        let completed = counts.bands[level];
        self.emit(format!(
            "event=band-work index={index} level={level} completed={completed} total={}",
            self.total
        ));
    }

    pub(crate) fn accumulator(
        &self,
        merge: &BandMerge,
        index: usize,
        _chunk: usize,
        _chunks: usize,
    ) {
        // The canonical boundary is also a valid observation site, but the
        // per-frame path already emitted its accepted generation. Do not
        // replay it or pretend that a refused-only chunk adds new evidence.
        self.live_accumulator(None, merge, index);
    }

    /// After every real accepted fold, show the canonical prefix together with
    /// the current disjoint chunk. Neither accumulator is mutated or cloned.
    /// Only spatial resolution is sampled; no accepted frame or level is lost.
    pub(crate) fn live_accumulator(
        &self,
        prefix: Option<&BandMerge>,
        current: &BandMerge,
        index: usize,
    ) {
        if !self.enabled {
            return;
        }
        let frames = current.frames() as usize + prefix.map_or(0, |merge| merge.frames() as usize);
        {
            let mut counts = self
                .diagnostics
                .lock()
                .expect("merge diagnostics lock poisoned");
            if frames <= counts.accumulator_frames {
                return;
            }
            counts.accumulator_frames = frames;
        }
        let observe = |band: AccumulatorObservation<'_>| {
            self.surface(
                index,
                band.level,
                "averaging",
                "stack",
                "linear",
                band.frames,
                band.size,
                |index| if band.averaging(index) { 1.0 } else { 0.0 },
                Some((0.0, 1.0)),
            );
            self.surface(
                index,
                band.level,
                "coefficient",
                "stack",
                "symmetric",
                band.frames,
                band.size,
                |index| band.coefficient(index),
                None,
            );
        };
        if let Some(prefix) = prefix {
            prefix.observe_accumulator_with(current, observe);
        } else {
            current.observe_accumulator(observe);
        }
        if let Some(preview) = coarse_preview_with(prefix, current) {
            self.surface(
                index,
                preview.level,
                "preview",
                "stack",
                "linear",
                preview.frames,
                preview.size,
                |index| preview.pixels[index],
                None,
            );
        }
    }

    pub(crate) fn reconstruction(
        &self,
        planes: &[Vec<f32>],
        size: LevelSize,
        index: usize,
        folded: usize,
    ) {
        if !self.enabled || planes.len() < 3 {
            return;
        }
        self.surface(
            index,
            0,
            "reconstructed",
            "stack",
            "linear",
            folded,
            size,
            |index| 0.5 * (planes[1][index] + planes[2][index]),
            None,
        );
    }

    pub(crate) fn render_step(&self, name: &str, state: &str) {
        if self.enabled {
            self.emit(format!(
                "event=render-step name={name} state={state} total={}",
                self.total
            ));
        }
    }

    #[allow(clippy::too_many_arguments)]
    pub(crate) fn surface(
        &self,
        frame: usize,
        level: usize,
        kind: &str,
        scope: &str,
        scale: &str,
        folded: usize,
        size: LevelSize,
        mut value: impl FnMut(usize) -> f32,
        range: Option<(f32, f32)>,
    ) {
        if !self.enabled || size.width == 0 || size.height == 0 {
            return;
        }
        let [width, height] = if kind == "preview" {
            lattice_within(size, PREVIEW_WIDTH, PREVIEW_HEIGHT)
        } else {
            lattice(size)
        };
        let mut samples = Vec::with_capacity(width * height);
        for y in 0..height {
            let source_y = ((2 * y + 1) * size.height / (2 * height)).min(size.height - 1);
            for x in 0..width {
                let source_x = ((2 * x + 1) * size.width / (2 * width)).min(size.width - 1);
                let sample = value(source_y * size.width + source_x);
                if !sample.is_finite() {
                    return;
                }
                samples.push(sample);
            }
        }
        let (min, max) = range.unwrap_or_else(|| {
            (
                samples.iter().copied().fold(f32::INFINITY, f32::min),
                samples.iter().copied().fold(f32::NEG_INFINITY, f32::max),
            )
        });
        let transform = |v: f32| match scale {
            "log" => v.max(0.0).ln_1p(),
            "symmetric" => v.signum() * v.abs().ln_1p(),
            _ => v,
        };
        let (lo, hi) = if scale == "symmetric" {
            let extent = min.abs().max(max.abs());
            (-transform(extent), transform(extent))
        } else {
            (transform(min), transform(max))
        };
        let pixels: Vec<u8> = samples
            .into_iter()
            .map(|sample| {
                let normalized = if hi > lo {
                    (transform(sample) - lo) / (hi - lo)
                } else {
                    0.0
                };
                (normalized.clamp(0.0, 1.0) * 255.0).round() as u8
            })
            .collect();
        let mut guard = self
            .diagnostics
            .lock()
            .expect("merge diagnostics lock poisoned");
        let counts = &mut *guard;
        // A plane's own maps go to the evidence file when this pass has one;
        // its float maps only for the planes the file keeps them for.
        let file_kind = if scope == "frame" {
            evidence::Kind::of(kind)
        } else {
            None
        };
        if let (Some(file_kind), Some(writer)) = (file_kind, counts.evidence.as_mut()) {
            let payload = match file_kind {
                evidence::Kind::GateSupport => evidence::pack_support(&pixels),
                _ if !evidence::float_kept(frame, self.total) => return,
                _ => [&min.to_le_bytes()[..], &max.to_le_bytes(), &pixels].concat(),
            };
            let sequence = counts.sequence + 1;
            if writer.append(frame, level, file_kind, sequence, &payload) {
                counts.sequence = sequence;
                return;
            }
        }
        counts.sequence += 1;
        self.emit(format!("event=diagnostic seq={} frame={frame} level={level} kind={kind} scope={scope} scale={scale} width={width} height={height} min={min:e} max={max:e} folded={folded} total={} sampling=nearest data={}", counts.sequence, self.total, hex(&pixels)));
    }

    /// Open this pass's evidence file beside `out` (the desktop's run
    /// folder), with the merge's level grids, and name it in the log. Without
    /// an output, or if the file cannot be made, the maps stay in the log.
    pub(crate) fn begin_evidence(&self, sizes: &[LevelSize], out: Option<&Path>) {
        let Some(out) = out.filter(|_| self.enabled && !sizes.is_empty()) else {
            return;
        };
        let directory = out
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
            .unwrap_or(Path::new("."));
        let header = evidence::Header {
            levels: sizes
                .iter()
                .map(|&size| (lattice(size), [size.width, size.height]))
                .collect(),
            frames: self.total,
        };
        match evidence::Writer::open(directory, header) {
            Ok((writer, opened)) => {
                if opened == evidence::Opened::Created {
                    self.emit(format!(
                        "event=evidence-file path={} version={}",
                        evidence::FILE_NAME,
                        evidence::VERSION
                    ));
                }
                self.diagnostics
                    .lock()
                    .expect("merge diagnostics lock poisoned")
                    .evidence = Some(writer);
            }
            Err(why) => {
                eprintln!("evidence file   : not written ({why}); per-plane maps stay in this log");
            }
        }
    }

    /// One frame's gate-support maps from the GPU fold: per level, `weight >
    /// 0` at each of `lattice(sizes[k])`'s sites, packed as the evidence
    /// file's bits (`strehl_gpu::SupportMaps`). The same records, or the same
    /// hex lines, the CPU fold's observer gives for its weights.
    pub(crate) fn gpu_support(&self, frame: usize, levels: &[Vec<u8>], sizes: &[LevelSize]) {
        if !self.enabled {
            return;
        }
        let mut guard = self
            .diagnostics
            .lock()
            .expect("merge diagnostics lock poisoned");
        let counts = &mut *guard;
        // One sequence per level, as the CPU observer numbers them. A frame's
        // records go to the file in one write; if the file cannot take them,
        // the same maps stay in the log as hex lines.
        let first = counts.sequence + 1;
        counts.sequence += levels.len() as u64;
        if let Some(writer) = counts.evidence.as_mut() {
            let mut records = Vec::new();
            let encoded = levels.iter().enumerate().all(|(level, bits)| {
                let sequence = first + level as u64;
                writer.encode(
                    frame,
                    level,
                    evidence::Kind::GateSupport,
                    sequence,
                    bits,
                    &mut records,
                )
            });
            if encoded && writer.write(&records) {
                return;
            }
        }
        for (level, (bits, &size)) in levels.iter().zip(sizes).enumerate() {
            let sequence = first + level as u64;
            let [width, height] = lattice(size);
            if bits.len() != (width * height).div_ceil(8) {
                continue;
            }
            let pixels: Vec<u8> = (0..width * height)
                .map(|i| {
                    if bits[i / 8] & (1 << (i % 8)) != 0 {
                        255
                    } else {
                        0
                    }
                })
                .collect();
            self.emit(format!("event=diagnostic seq={sequence} frame={frame} level={level} kind=gate-support scope=frame scale=linear width={width} height={height} min={:e} max={:e} folded=1 total={} sampling=nearest data={}", 0.0f32, 1.0f32, self.total, hex(&pixels)));
        }
    }
}

struct CoarsePreview {
    level: usize,
    size: LevelSize,
    frames: usize,
    pixels: Vec<f32>,
}

/// Reconstruct an actual coarse GREEN image from the canonical accumulator's
/// coefficients, never from quantised diagnostic maps. Allocation starts only
/// at a retained level that fits the bounded viewport. The result is before
/// finish's per-level/final hull bounds and colour development, not final RGB.
#[cfg(test)]
fn coarse_preview(merge: &BandMerge) -> Option<CoarsePreview> {
    coarse_preview_with(None, merge)
}

fn coarse_preview_with(prefix: Option<&BandMerge>, current: &BandMerge) -> Option<CoarsePreview> {
    let frames = current.frames() as usize + prefix.map_or(0, |merge| merge.frames() as usize);
    if frames == 0 {
        return None;
    }
    let level = current
        .sizes()
        .iter()
        .position(|size| size.width <= PREVIEW_WIDTH && size.height <= PREVIEW_HEIGHT)?;
    let sizes = &current.sizes()[level..];
    let mut pyramid = Pyramid::zeros(sizes);
    let observe = |band: AccumulatorObservation<'_>| {
        if band.level < level {
            return;
        }
        for (index, coefficient) in pyramid.level_mut(band.level - level).iter_mut().enumerate() {
            *coefficient = band.coefficient(index);
        }
    };
    if let Some(prefix) = prefix {
        prefix.observe_accumulator_with(current, observe);
    } else {
        current.observe_accumulator(observe);
    }
    let pixels = pyramid.collapse(&mut Workspace::new(sizes));
    Some(CoarsePreview {
        level,
        size: sizes[0],
        frames,
        pixels,
    })
}

#[cfg(test)]
#[path = "ui-diagnostics-tests.rs"]
mod tests;
