//! A small camera-JPEG composite for inspecting a bracket before RAW processing.
//!
//! This is deliberately separate from the RAW engine. Camera processing has
//! already changed colour, noise and local contrast, so these pixels cannot
//! predict the RAW merge's detail, confidence or noise. The injected RAW noise
//! model is neither approximated nor re-estimated here. See SYNTHESIS §3.3 and
//! M86/M103 for direct graph registration; M173's capture audit also distinguishes
//! camera JPEGs from measurement RAWs. The focus response is a blend weight only:
//! noise/sharpening can increase it, so it is never an acceptance metric.
//!
//! Two uses share the registration and blend. [`start_draft_preview`] builds
//! one composite of a finished bracket. [`ProofJob`] builds the in-flight
//! proof of a capture (Studio 2, 7.4) as its planes arrive: each frame is
//! decoded and its pyramid built once, measured pairs are kept, and the
//! global solve and blend run again every [`PROOF_EVERY_PLANES`] new planes or
//! [`PROOF_EVERY`], on one below-normal-priority thread. Every display of it
//! says it is from the camera previews, not the RAW stack: for the reason
//! above it cannot predict the RAW merge.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{self, Receiver};
use std::thread;
use std::time::{Duration, Instant};

use anyhow::{Context, Result, ensure};
use strehl_core::align::{
    AlignConfig, AlignEdge, AlignFrame, AlignPyramid, Cx, GlobalOptions, PlaneRef, Similarity,
    Weighting, align_pair, downsample, graph_stats, reachable_from_zero, solve_global, tile_grid,
};
use strehl_core::boxfilter::box_mean;
use strehl_core::plane::PlaneGeometry;

use crate::preview::PreviewImage;
use crate::source_preview::load_draft_source;

const DRAFT_SIDE: u32 = 480;
const MAX_FRAMES: usize = 512;
// Unwarped RGBA + reduced luma and alignment pyramids. Decoder scratch is
// separately bounded by the embedded-JPEG reader and is released per frame.
const RESIDENT_LIMIT: usize = 256 * 1024 * 1024;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DraftStage {
    Reading,
    Aligning,
    Blending,
}

impl DraftStage {
    pub fn label(self) -> &'static str {
        match self {
            Self::Reading => "Reading camera previews",
            Self::Aligning => "Registering preview pairs",
            Self::Blending => "Blending camera previews",
        }
    }
}

pub enum DraftEvent {
    Progress {
        stage: DraftStage,
        completed: usize,
        total: usize,
    },
    Finished(Result<DraftPreview, String>),
}

pub struct DraftPreview {
    pub image: PreviewImage,
    pub source_frames: usize,
    pub aligned_frames: usize,
    pub skipped_frames: usize,
    pub alignment_edges: usize,
    pub cycle_rank: usize,
    /// Zero-based index in the original input list. Geometry is measured in
    /// reduced camera JPEG pixels, referenced to this middle connected frame.
    pub reference_frame: usize,
    pub warnings: Vec<String>,
}

pub struct DraftJob {
    pub receiver: Receiver<DraftEvent>,
    cancelled: Arc<AtomicBool>,
}

impl DraftJob {
    /// Request cancellation without detaching the worker. Keep receiving until
    /// Finished/disconnection before starting another draft, so cancelling a
    /// JPEG decode cannot briefly multiply the bracket's memory footprint.
    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::Relaxed);
    }

    #[cfg(test)]
    pub(crate) fn test_receiver(receiver: Receiver<DraftEvent>) -> Self {
        Self {
            receiver,
            cancelled: Arc::new(AtomicBool::new(false)),
        }
    }
}

impl Drop for DraftJob {
    fn drop(&mut self) {
        self.cancel();
    }
}

pub fn start_draft_preview(paths: Vec<PathBuf>) -> DraftJob {
    let (sender, receiver) = mpsc::sync_channel(24);
    let cancelled = Arc::new(AtomicBool::new(false));
    let worker_cancelled = Arc::clone(&cancelled);
    let failed_start = sender.clone();
    if let Err(error) = thread::Builder::new()
        .name("strehl-jpeg-draft".into())
        .spawn(move || {
            let result = build(&paths, &worker_cancelled, |stage, completed, total| {
                let _ = sender.try_send(DraftEvent::Progress {
                    stage,
                    completed,
                    total,
                });
            });
            let result = if worker_cancelled.load(Ordering::Relaxed) {
                Err("JPEG draft cancelled".into())
            } else {
                result.map_err(|error| format!("{error:#}"))
            };
            // A retained cancelling job needs a terminal event too. Sending
            // fails harmlessly when its receiver was dropped as a fallback.
            let _ = sender.send(DraftEvent::Finished(result));
        })
    {
        let _ = failed_start.send(DraftEvent::Finished(Err(format!(
            "Starting the JPEG draft worker: {error}"
        ))));
    }
    DraftJob {
        receiver,
        cancelled,
    }
}

struct Frame {
    source_index: usize,
    path: PathBuf,
    rgba: Vec<u8>,
    luma: Vec<f32>,
    pyramid: AlignPyramid,
}

/// Measured pairs by the frames' source indices; `None` for a pair that
/// did not register, so it is not measured again.
type EdgeCache = BTreeMap<(usize, usize), Option<AlignEdge>>;

/// One camera preview made ready for registration and blending, with its
/// reduced geometry and the bytes it keeps resident.
fn prepare(
    image: crate::preview::PreviewImage,
    source_index: usize,
    path: PathBuf,
    config: &AlignConfig,
) -> Result<(Frame, PlaneGeometry, usize)> {
    ensure!(
        image.size.iter().all(|&side| side >= 80),
        "A camera preview is too small to register reliably; RAW stacking remains available"
    );
    let [width, height] = image.size;
    let luma: Vec<f32> = image
        .rgba
        .as_chunks::<4>()
        .0
        .iter()
        .map(|p| 0.2126 * p[0] as f32 + 0.7152 * p[1] as f32 + 0.0722 * p[2] as f32)
        .collect();
    let reduced = downsample(
        PlaneRef::new(&luma, width, height).context("Invalid camera preview pixels")?,
        2,
    )
    .context("Camera preview is too small for registration")?;
    let pyramid = AlignPyramid::build(reduced.as_ref(), config)
        .context("Building the draft registration pyramid")?;
    let geometry = reduced.as_ref().geometry();
    let bytes = image.rgba.len() + reduced.data.len() * 4 + pyramid.samples() * 4;
    Ok((
        Frame {
            source_index,
            path,
            rgba: image.rgba,
            luma: reduced.data,
            pyramid,
        },
        geometry,
        bytes,
    ))
}

fn check_cancelled(cancelled: &AtomicBool) -> Result<()> {
    ensure!(!cancelled.load(Ordering::Relaxed), "JPEG draft cancelled");
    Ok(())
}

fn draft_config() -> AlignConfig {
    AlignConfig {
        coarse_factors: vec![2],
        coarse_tile: 12,
        coarse_grid: (4, 3),
        coarse_radius: 4,
        fine_tile: 16,
        fine_grid: (5, 4),
        fine_radius: 3,
        margin: 12,
        min_contrast: 2.0,
        min_peak: 0.55,
        min_tiles: 6,
        fine_iters: 2,
        warp_tiles: true,
        ..AlignConfig::shallow()
    }
}

fn pair_set(n: usize) -> Vec<(usize, usize)> {
    let mut pairs = BTreeSet::new();
    // Short edges retain local information; the long spans and frame-0 edges
    // supply cycles. No measured transform is ever chained into another fit.
    for span in [1, 2, 4, 12, 32, 96, 256] {
        for i in 0..n.saturating_sub(span) {
            pairs.insert((i, i + span));
        }
    }
    for j in 1..n {
        pairs.insert((0, j));
    }
    pairs.into_iter().collect()
}

fn build(
    paths: &[PathBuf],
    cancelled: &AtomicBool,
    mut progress: impl FnMut(DraftStage, usize, usize),
) -> Result<DraftPreview> {
    ensure!(
        paths.len() >= 2,
        "Choose at least two source frames for a draft"
    );
    ensure!(
        paths.len() <= MAX_FRAMES,
        "The JPEG draft supports up to {MAX_FRAMES} frames; this bracket has {}. RAW stacking remains available.",
        paths.len()
    );
    let config = draft_config();
    let mut frames = Vec::with_capacity(paths.len());
    let mut size = None;
    let mut geometry = None;
    let mut resident = 0usize;
    let mut warnings = Vec::new();
    progress(DraftStage::Reading, 0, paths.len());
    for (source_index, path) in paths.iter().enumerate() {
        check_cancelled(cancelled)?;
        match load_draft_source(path, DRAFT_SIDE, cancelled) {
            Ok(image) => {
                ensure!(
                    image.size.iter().all(|&side| side >= 80),
                    "A camera preview is too small to register reliably; RAW stacking remains available"
                );
                if let Some(expected) = size {
                    ensure!(
                        image.size == expected,
                        "Camera previews have different dimensions; a reliable JPEG draft is unavailable"
                    );
                } else {
                    size = Some(image.size);
                }
                let (frame, geom, bytes) = prepare(image, source_index, path.clone(), &config)?;
                geometry = Some(geom);
                resident += bytes;
                ensure!(
                    resident <= RESIDENT_LIMIT,
                    "This bracket exceeds the JPEG draft's 256 MiB source budget. RAW stacking remains available."
                );
                frames.push(frame);
            }
            Err(error) => {
                check_cancelled(cancelled)?;
                warnings.push(format!(
                    "Frame {} has no usable camera preview: {error}",
                    source_index + 1
                ));
            }
        }
        progress(DraftStage::Reading, source_index + 1, paths.len());
    }
    ensure!(
        frames.len() >= 2,
        "Fewer than two frames have usable camera JPEGs; RAW stacking remains available"
    );
    let geometry = geometry.context("No camera preview geometry")?;
    let size = size.context("No camera preview dimensions")?;
    let (placement, edges, cycle_rank) =
        register(&frames, geometry, &config, cancelled, &mut progress)?;
    compose(
        &frames,
        &placement,
        size,
        Composed {
            considered: paths.len(),
            alignment_edges: edges,
            cycle_rank,
            warnings,
        },
        cancelled,
        &mut progress,
    )
}

/// What [`compose`] reports beside the picture.
struct Composed {
    /// Frames the composite stands for: the 90 % registration floor and the
    /// omitted count are over these.
    considered: usize,
    alignment_edges: usize,
    cycle_rank: usize,
    warnings: Vec<String>,
}

/// The reference (the middle connected frame), the transforms into it, the
/// coverage floor and the blend.
fn compose(
    frames: &[Frame],
    placement: &[Option<Similarity>],
    size: [usize; 2],
    report: Composed,
    cancelled: &AtomicBool,
    progress: &mut impl FnMut(DraftStage, usize, usize),
) -> Result<DraftPreview> {
    let [width, height] = size;
    let Composed {
        considered,
        alignment_edges,
        cycle_rank,
        mut warnings,
    } = report;
    let reference = (0..frames.len())
        .filter(|&i| placement[i].is_some())
        .min_by_key(|&i| i.abs_diff(frames.len() / 2))
        .context("No connected camera previews")?;
    let anchor = placement[reference].context("No reference placement")?;
    let mut transforms = Vec::with_capacity(frames.len());
    for (index, transform) in placement.iter().enumerate() {
        if index == reference {
            // Exact identity guarantees coverage at every border pixel; an
            // inverse composed with itself can leave tiny negative roundoff.
            transforms.push(Some(Similarity::IDENTITY));
            continue;
        }
        let transform = transform.and_then(|t| Similarity::relative(anchor, t));
        transforms.push(transform.map(|t| full_size_transform(t, width, height)));
    }
    let aligned_frames = transforms.iter().filter(|t| t.is_some()).count();
    ensure!(
        aligned_frames * 10 >= considered * 9,
        "Only {aligned_frames}/{considered} camera previews could be registered. A JPEG composite would omit too much of this bracket; RAW stacking remains available."
    );
    let skipped_frames = considered - aligned_frames;
    if skipped_frames > 0 {
        warnings.push(format!(
            "The JPEG draft omits {skipped_frames} source frames"
        ));
    }
    let rgba = blend(
        frames,
        &transforms,
        PlaneGeometry { width, height },
        cancelled,
        progress,
    )?;
    Ok(DraftPreview {
        image: PreviewImage {
            path: frames[reference].path.clone(),
            source_size: [width as u32, height as u32],
            size: [width, height],
            rgba,
            is_overview: true,
        },
        source_frames: considered,
        aligned_frames,
        skipped_frames,
        alignment_edges,
        cycle_rank,
        reference_frame: frames[reference].source_index,
        warnings,
    })
}

fn register(
    frames: &[Frame],
    geometry: PlaneGeometry,
    config: &AlignConfig,
    cancelled: &AtomicBool,
    progress: &mut impl FnMut(DraftStage, usize, usize),
) -> Result<(Vec<Option<Similarity>>, usize, usize)> {
    register_cached(
        frames,
        geometry,
        config,
        &mut EdgeCache::new(),
        cancelled,
        progress,
    )
}

/// [`register`], measuring only the pairs `cache` does not hold (keyed by
/// source index, so a frame keeps its pairs when others are dropped).
fn register_cached(
    frames: &[Frame],
    geometry: PlaneGeometry,
    config: &AlignConfig,
    cache: &mut EdgeCache,
    cancelled: &AtomicBool,
    progress: &mut impl FnMut(DraftStage, usize, usize),
) -> Result<(Vec<Option<Similarity>>, usize, usize)> {
    let spots = tile_grid(
        PlaneRef::from_geometry(&frames[0].luma, geometry).context("Invalid preview luma")?,
        config.fine_tile,
        config.fine_grid.0,
        config.fine_grid.1,
        config.margin,
    )
    .context("Camera previews are too small for the registration grid")?;
    let pairs = pair_set(frames.len());
    let mut edges = Vec::with_capacity(pairs.len());
    progress(DraftStage::Aligning, 0, pairs.len());
    for (done, &(i, j)) in pairs.iter().enumerate() {
        check_cancelled(cancelled)?;
        let key = (frames[i].source_index, frames[j].source_index);
        let measured = *cache.entry(key).or_insert_with(|| {
            let frame = |index: usize| AlignFrame {
                plane: PlaneRef::from_geometry(&frames[index].luma, geometry).unwrap(),
                pyramid: &frames[index].pyramid,
            };
            align_pair(frame(i), frame(j), &spots, config)
                .ok()
                .filter(|fit| sane_transform(fit.similarity(), geometry))
                .map(|fit| AlignEdge::from_stage(i, j, &fit))
        });
        if let Some(mut edge) = measured {
            // The pair's positions in this frame list.
            edge.i = i;
            edge.j = j;
            edges.push(edge);
        }
        progress(DraftStage::Aligning, done + 1, pairs.len());
    }
    let reachable = reachable_from_zero(&edges, frames.len());
    let connected_edges: Vec<_> = edges
        .iter()
        .copied()
        .filter(|e| reachable[e.i] && reachable[e.j])
        .collect();
    let stats = graph_stats(&connected_edges, frames.len());
    ensure!(
        stats.reachable_from_0 >= 2 && (frames.len() == 2 || stats.cycle_rank > 0),
        "The camera previews share too little texture for a connected registration graph. RAW stacking remains available."
    );
    let mut options = GlobalOptions::new(geometry);
    options.weighting = if frames.len() > 60 {
        Weighting::Unit
    } else {
        Weighting::InverseVariance
    };
    let mut placement = solve_global(&edges, frames.len(), &options)
        .context("The camera previews could not be registered")?;
    for item in &mut placement {
        if item.is_some_and(|t| !sane_transform(t, geometry)) {
            *item = None;
        }
    }
    Ok((placement, edges.len(), stats.cycle_rank))
}

fn sane_transform(transform: Similarity, geometry: PlaneGeometry) -> bool {
    transform.a.is_finite()
        && transform.b.is_finite()
        && (0.7..=1.4).contains(&transform.scale())
        && transform.rotation().abs() <= 0.15
        && transform.b.abs() <= geometry.width.max(geometry.height) as f64 * 0.25
}

fn full_size_transform(mut transform: Similarity, width: usize, height: usize) -> Similarity {
    // A reduced sample is centred on its 2x2 block, at (2x+.5, 2y+.5).
    // Account for this offset and the dropped last row/column at odd extents.
    let offset = Cx::new(
        (width / 2) as f64 + 0.5 - width as f64 / 2.0,
        (height / 2) as f64 + 0.5 - height as f64 / 2.0,
    );
    transform.b = transform.b.scale(2.0) + offset - transform.a * offset;
    transform
}

fn focus_weights(rgba: &[u8], geometry: PlaneGeometry) -> Vec<f32> {
    let (w, h) = (geometry.width, geometry.height);
    let luma: Vec<f32> = rgba
        .as_chunks::<4>()
        .0
        .iter()
        .map(|p| (0.2126 * p[0] as f32 + 0.7152 * p[1] as f32 + 0.0722 * p[2] as f32) / 255.0)
        .collect();
    let mut gradient = vec![0.0; geometry.pixels()];
    for y in 1..h - 1 {
        for x in 1..w - 1 {
            let i = y * w + x;
            gradient[i] = (luma[i + 1] - luma[i - 1]).hypot(luma[i + w] - luma[i - w]);
        }
    }
    let mut scratch = vec![0.0; geometry.pixels()];
    let mut weights = vec![0.0; geometry.pixels()];
    box_mean(&gradient, geometry, 4, &mut scratch, &mut weights);
    for weight in &mut weights {
        // Positive averaging floor, in display-code units, not a sensor noise
        // estimate. Flat inputs therefore average; no coefficient is argmaxed.
        *weight = weight.powi(2) + (1.0f32 / 255.0).powi(2);
    }
    weights
}

fn blend(
    frames: &[Frame],
    transforms: &[Option<Similarity>],
    geometry: PlaneGeometry,
    cancelled: &AtomicBool,
    progress: &mut impl FnMut(DraftStage, usize, usize),
) -> Result<Vec<u8>> {
    let (w, h) = (geometry.width, geometry.height);
    let mut accum = vec![[0.0f32; 4]; geometry.pixels()];
    let linear: [f32; 256] = std::array::from_fn(|i| srgb_to_linear(i as f32 / 255.0));
    let total = transforms.iter().filter(|t| t.is_some()).count();
    let mut done = 0;
    progress(DraftStage::Blending, done, total);
    for (frame, transform) in frames.iter().zip(transforms) {
        check_cancelled(cancelled)?;
        let Some(transform) = transform else { continue };
        let weights = focus_weights(&frame.rgba, geometry);
        for y in 0..h {
            if y % 32 == 0 {
                check_cancelled(cancelled)?;
            }
            for x in 0..w {
                let (sx, sy) =
                    transform.apply_at(x as f64, y as f64, w as f64 / 2.0, h as f64 / 2.0);
                const BORDER_ROUNDOFF: f64 = 1e-6;
                if sx < -BORDER_ROUNDOFF
                    || sy < -BORDER_ROUNDOFF
                    || sx > (w - 1) as f64 + BORDER_ROUNDOFF
                    || sy > (h - 1) as f64 + BORDER_ROUNDOFF
                {
                    continue;
                }
                let sx = sx.clamp(0.0, (w - 1) as f64);
                let sy = sy.clamp(0.0, (h - 1) as f64);
                let x0 = sx.floor() as usize;
                let y0 = sy.floor() as usize;
                let x1 = (x0 + 1).min(w - 1);
                let y1 = (y0 + 1).min(h - 1);
                let fx = sx as f32 - x0 as f32;
                let fy = sy as f32 - y0 as f32;
                let taps = [
                    (y0 * w + x0, (1.0 - fx) * (1.0 - fy)),
                    (y0 * w + x1, fx * (1.0 - fy)),
                    (y1 * w + x0, (1.0 - fx) * fy),
                    (y1 * w + x1, fx * fy),
                ];
                let weight: f32 = taps.iter().map(|&(i, f)| weights[i] * f).sum();
                let out = &mut accum[y * w + x];
                for c in 0..3 {
                    let value: f32 = taps
                        .iter()
                        .map(|&(i, f)| linear[frame.rgba[i * 4 + c] as usize] * f)
                        .sum();
                    out[c] += value * weight;
                }
                out[3] += weight;
            }
        }
        done += 1;
        progress(DraftStage::Blending, done, total);
    }
    let mut rgba = Vec::with_capacity(geometry.pixels() * 4);
    for pixel in accum {
        ensure!(
            pixel[3] > 0.0,
            "The registered JPEG draft has uncovered pixels"
        );
        for value in &pixel[..3] {
            rgba.push(
                (linear_to_srgb(value / pixel[3]) * 255.0)
                    .round()
                    .clamp(0.0, 255.0) as u8,
            );
        }
        rgba.push(255);
    }
    Ok(rgba)
}

// The in-flight proof below is built for the Capture station (Studio 2,
// P6), which feeds it; until then nothing in the desktop starts one.
/// The proof is solved and blended again after this many new planes...
#[allow(dead_code)]
pub const PROOF_EVERY_PLANES: usize = 4;
/// ...or this long after the last update with at least one new plane.
#[allow(dead_code)]
pub const PROOF_EVERY: Duration = Duration::from_secs(5);
/// Shown with every display of the proof.
#[allow(dead_code)]
pub const PROOF_CAUTION: &str = "from the camera previews, not the RAW stack";

/// The in-flight proof's frames and measured pairs, kept between updates.
/// Above [`MAX_FRAMES`] planes (or the resident budget) it keeps every
/// second plane of those it had, and so on: an even subsample, plane 0 and
/// its pairs always among them.
#[allow(dead_code)]
pub(crate) struct Incremental {
    config: AlignConfig,
    frames: Vec<Frame>,
    /// Frames offered, kept or not.
    received: usize,
    /// One plane in `stride` is kept.
    stride: usize,
    size: Option<[usize; 2]>,
    geometry: Option<PlaneGeometry>,
    resident: usize,
    edges: EdgeCache,
    warnings: Vec<String>,
    /// Kept frames since the last update.
    fresh: usize,
    last_update: Option<Instant>,
    revision: u64,
}

/// One proof: the composite, and how it stands for the capture so far.
#[allow(dead_code)]
pub struct ProofUpdate {
    pub draft: DraftPreview,
    /// Planes offered so far.
    pub received: usize,
    /// Planes in the composite's registration (an even subsample above 512).
    pub used: usize,
    /// One plane in `stride` was used.
    pub stride: usize,
    /// Counts updates: a new one replaces the shown proof.
    pub revision: u64,
}

impl Default for Incremental {
    fn default() -> Self {
        Self {
            config: draft_config(),
            frames: Vec::new(),
            received: 0,
            stride: 1,
            size: None,
            geometry: None,
            resident: 0,
            edges: EdgeCache::new(),
            warnings: Vec::new(),
            fresh: 0,
            last_update: None,
            revision: 0,
        }
    }
}

#[allow(dead_code)]
impl Incremental {
    /// Offers the next plane's file: its camera preview is read only when
    /// the plane is one of the kept subsample.
    pub fn add_path(&mut self, path: &Path, cancelled: &AtomicBool) -> Result<()> {
        let index = self.received;
        self.received += 1;
        if !index.is_multiple_of(self.stride) {
            return Ok(());
        }
        match load_draft_source(path, DRAFT_SIDE, cancelled) {
            Ok(image) => self.add_image(image, index, path.to_path_buf()),
            Err(error) => {
                check_cancelled(cancelled)?;
                self.warnings.push(format!(
                    "Plane {} has no usable camera preview: {error}",
                    index + 1
                ));
                Ok(())
            }
        }
    }
    /// A plane's preview, already decoded (`index` counts from the first
    /// plane offered). A plane off the kept subsample is not added.
    fn add_image(&mut self, image: PreviewImage, index: usize, path: PathBuf) -> Result<()> {
        if !index.is_multiple_of(self.stride) {
            return Ok(());
        }
        let size = image.size;
        ensure!(
            size.iter().all(|&side| side >= 80),
            "A camera preview is too small to register reliably"
        );
        if let Some(expected) = self.size {
            ensure!(
                size == expected,
                "Camera previews have different dimensions; a reliable JPEG proof is unavailable"
            );
        }
        let (frame, geometry, bytes) = prepare(image, index, path, &self.config)?;
        self.size = Some(size);
        self.geometry = Some(geometry);
        self.resident += bytes;
        self.frames.push(frame);
        self.fresh += 1;
        while self.frames.len() > MAX_FRAMES || self.resident > RESIDENT_LIMIT {
            self.thin();
        }
        Ok(())
    }
    /// Keeps every second kept plane (twice the stride) and their pairs.
    fn thin(&mut self) {
        self.stride *= 2;
        let stride = self.stride;
        let before = self.frames.len();
        self.frames
            .retain(|f| f.source_index.is_multiple_of(stride));
        self.edges
            .retain(|(i, j), _| i.is_multiple_of(stride) && j.is_multiple_of(stride));
        self.resident = self.resident * self.frames.len() / before.max(1);
    }
    /// Whether an update is due: four new planes, or five seconds since the
    /// last with one new plane.
    pub fn due(&self, now: Instant) -> bool {
        self.frames.len() >= 2
            && (self.fresh >= PROOF_EVERY_PLANES
                || (self.fresh > 0
                    && self
                        .last_update
                        .is_none_or(|t| now.duration_since(t) >= PROOF_EVERY)))
    }
    /// Solves the registration again over every kept frame (measuring only
    /// new pairs) and blends.
    pub fn update(&mut self, cancelled: &AtomicBool) -> Result<ProofUpdate> {
        self.fresh = 0;
        self.last_update = Some(Instant::now());
        ensure!(
            self.frames.len() >= 2,
            "The proof needs two planes with camera previews"
        );
        let geometry = self.geometry.context("No camera preview geometry")?;
        let size = self.size.context("No camera preview dimensions")?;
        let mut progress = |_: DraftStage, _: usize, _: usize| {};
        let (placement, edges, cycle_rank) = register_cached(
            &self.frames,
            geometry,
            &self.config,
            &mut self.edges,
            cancelled,
            &mut progress,
        )?;
        let mut draft = compose(
            &self.frames,
            &placement,
            size,
            Composed {
                considered: self.frames.len(),
                alignment_edges: edges,
                cycle_rank,
                warnings: self.warnings.clone(),
            },
            cancelled,
            &mut progress,
        )?;
        draft.source_frames = self.received;
        if self.stride > 1 {
            draft.warnings.push(format!(
                "The proof uses one plane in {} of the {} so far",
                self.stride, self.received
            ));
        }
        self.revision += 1;
        Ok(ProofUpdate {
            draft,
            received: self.received,
            used: self.frames.len(),
            stride: self.stride,
            revision: self.revision,
        })
    }
}

/// What the proof's worker reports.
#[allow(dead_code)]
pub enum ProofEvent {
    Updated(Box<ProofUpdate>),
    /// This update failed; the last proof still stands.
    Failed(String),
}

#[allow(dead_code)]
enum ProofInput {
    Frame(PathBuf),
    /// An update now, if any plane is new (the capture ended).
    Finish,
}

/// The in-flight proof, built on its own below-normal-priority thread.
/// Dropping it ends the thread after its current step.
#[allow(dead_code)]
pub struct ProofJob {
    sender: mpsc::Sender<ProofInput>,
    receiver: Receiver<ProofEvent>,
    cancelled: Arc<AtomicBool>,
}

#[allow(dead_code)]
impl ProofJob {
    pub fn start() -> Self {
        Self::spawn(None)
    }
    /// A proof of the capture being written to `run`: its worker reads the
    /// run's transfer receipts and offers the first RAW of each plane that
    /// arrives (`shots` RAWs a plane), and makes a last update when the
    /// capture's `result.json` appears.
    pub fn for_run(run: PathBuf, shots: u64) -> Self {
        Self::spawn(Some(RunTail::new(run, shots)))
    }
    fn spawn(tail: Option<RunTail>) -> Self {
        let (sender, inputs) = mpsc::channel();
        let (events, receiver) = mpsc::sync_channel(4);
        let cancelled = Arc::new(AtomicBool::new(false));
        let worker_cancelled = Arc::clone(&cancelled);
        let failed = events.clone();
        if let Err(error) = thread::Builder::new()
            .name("strehl-capture-proof".into())
            .spawn(move || {
                lower_thread_priority();
                proof_worker(&inputs, &events, &worker_cancelled, tail);
            })
        {
            let _ = failed.try_send(ProofEvent::Failed(format!(
                "Starting the proof worker: {error}"
            )));
        }
        Self {
            sender,
            receiver,
            cancelled,
        }
    }
    /// Offers the next plane's RAW (its embedded camera preview is read).
    /// `false` once the worker has ended.
    pub fn add_frame(&self, path: PathBuf) -> bool {
        self.sender.send(ProofInput::Frame(path)).is_ok()
    }
    /// Asks for an update with every plane offered so far.
    pub fn finish(&self) {
        let _ = self.sender.send(ProofInput::Finish);
    }
    /// The newest event, if any; older updates are superseded.
    pub fn poll(&self) -> Option<ProofEvent> {
        let mut latest = None;
        while let Ok(event) = self.receiver.try_recv() {
            latest = Some(event);
        }
        latest
    }
    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::Relaxed);
    }
}

impl Drop for ProofJob {
    fn drop(&mut self) {
        self.cancel();
    }
}

#[allow(dead_code)]
fn proof_worker(
    inputs: &Receiver<ProofInput>,
    events: &mpsc::SyncSender<ProofEvent>,
    cancelled: &AtomicBool,
    mut tail: Option<RunTail>,
) {
    let mut proof = Incremental::default();
    loop {
        if cancelled.load(Ordering::Relaxed) {
            return;
        }
        let mut finish = false;
        if let Some(run) = &mut tail {
            let (paths, ended) = run.poll();
            for path in paths {
                add_frame(&mut proof, &path, cancelled, events);
            }
            finish |= ended;
        }
        match inputs.recv_timeout(Duration::from_millis(250)) {
            Ok(ProofInput::Frame(path)) => {
                add_frame(&mut proof, &path, cancelled, events);
                // Take every plane already queued, so one update covers them.
                loop {
                    match inputs.try_recv() {
                        Ok(ProofInput::Frame(path)) => {
                            add_frame(&mut proof, &path, cancelled, events)
                        }
                        Ok(ProofInput::Finish) => finish = true,
                        Err(_) => break,
                    }
                }
            }
            Ok(ProofInput::Finish) => finish = true,
            Err(mpsc::RecvTimeoutError::Timeout) => {}
            // The job was dropped, which cancels it.
            Err(mpsc::RecvTimeoutError::Disconnected) => return,
        }
        if cancelled.load(Ordering::Relaxed) {
            return;
        }
        if proof.due(Instant::now()) || (finish && proof.fresh > 0 && proof.frames.len() >= 2) {
            let event = match proof.update(cancelled) {
                Ok(update) => ProofEvent::Updated(Box::new(update)),
                Err(error) => ProofEvent::Failed(format!("{error:#}")),
            };
            if cancelled.load(Ordering::Relaxed) {
                return;
            }
            // A full queue means the UI has not read the last one: replace
            // nothing, it reads the newest of what is queued.
            let _ = events.try_send(event);
        }
    }
}

/// Follows a capture's transfer receipts: one RAW a plane, in arrival order.
#[allow(dead_code)]
struct RunTail {
    run: PathBuf,
    shots: u64,
    offset: u64,
    partial: Vec<u8>,
    planes: BTreeSet<u64>,
    ended: bool,
}

#[allow(dead_code)]
impl RunTail {
    fn new(run: PathBuf, shots: u64) -> Self {
        Self {
            run,
            shots: shots.max(1),
            offset: 0,
            partial: Vec::new(),
            planes: BTreeSet::new(),
            ended: false,
        }
    }
    /// The new planes' files, and whether the capture has just ended (its
    /// result written and every receipt read).
    fn poll(&mut self) -> (Vec<PathBuf>, bool) {
        use std::io::{Read, Seek, SeekFrom};
        let mut out = Vec::new();
        let receipts = self.run.join("transfer-receipts.jsonl");
        let len = std::fs::metadata(&receipts).map_or(0, |m| m.len());
        if len > self.offset
            && let Ok(mut file) = std::fs::File::open(&receipts)
            && file.seek(SeekFrom::Start(self.offset)).is_ok()
        {
            let mut chunk = Vec::new();
            if file
                .take((len - self.offset).min(1 << 20))
                .read_to_end(&mut chunk)
                .is_ok()
            {
                self.offset += chunk.len() as u64;
                self.partial.extend_from_slice(&chunk);
                if let Some(end) = self.partial.iter().rposition(|b| *b == b'\n') {
                    let rest = self.partial.split_off(end + 1);
                    let lines = std::mem::replace(&mut self.partial, rest);
                    for line in lines.split(|b| *b == b'\n') {
                        if let Some(path) = self.plane_file(line) {
                            out.push(path);
                        }
                    }
                }
            }
        }
        let ended = !self.ended && self.offset >= len && self.run.join("result.json").is_file();
        self.ended |= ended;
        (out, ended)
    }
    /// The stored file of a receipt line, if it is the first RAW seen of
    /// its plane.
    fn plane_file(&mut self, line: &[u8]) -> Option<PathBuf> {
        let r: serde_json::Value = serde_json::from_slice(line).ok()?;
        if r["ok"] != true || r["durable"] != true {
            return None;
        }
        let name = r["logical_name"].as_str()?;
        let ordinal: u64 = name
            .strip_prefix("frame-")?
            .strip_suffix(".ARW")?
            .parse()
            .ok()?;
        let plane = ordinal.checked_sub(1)? / self.shots;
        if !self.planes.insert(plane) {
            return None;
        }
        Some(self.run.join(match r["storage_encoding"].as_str() {
            Some("identity") | None => name.to_owned(),
            Some(_) => format!("{name}.straw"),
        }))
    }
}

#[allow(dead_code)]
fn add_frame(
    proof: &mut Incremental,
    path: &Path,
    cancelled: &AtomicBool,
    events: &mpsc::SyncSender<ProofEvent>,
) {
    if cancelled.load(Ordering::Relaxed) {
        return;
    }
    if let Err(error) = proof.add_path(path, cancelled)
        && !cancelled.load(Ordering::Relaxed)
    {
        let _ = events.try_send(ProofEvent::Failed(format!("{error:#}")));
    }
}

/// The proof runs below the desktop's and the receiver's priority, so it
/// never competes with the capture's own work.
#[cfg(windows)]
#[allow(dead_code)]
fn lower_thread_priority() {
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetCurrentThread() -> *mut std::ffi::c_void;
        fn SetThreadPriority(thread: *mut std::ffi::c_void, priority: i32) -> i32;
    }
    const THREAD_PRIORITY_BELOW_NORMAL: i32 = -1;
    // SAFETY: the calling thread's pseudo-handle and a documented priority
    // value; no memory is shared.
    unsafe {
        SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_BELOW_NORMAL);
    }
}
#[cfg(not(windows))]
#[allow(dead_code)]
fn lower_thread_priority() {}

fn srgb_to_linear(value: f32) -> f32 {
    if value <= 0.04045 {
        value / 12.92
    } else {
        ((value + 0.055) / 1.055).powf(2.4)
    }
}

fn linear_to_srgb(value: f32) -> f32 {
    if value <= 0.0031308 {
        value * 12.92
    } else {
        1.055 * value.max(0.0).powf(1.0 / 2.4) - 0.055
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::align::SimilarityParams;

    fn frame(luma: Vec<f32>, geometry: PlaneGeometry, source_index: usize) -> Frame {
        let mut rgba = Vec::with_capacity(geometry.pixels() * 4);
        for value in &luma {
            let value = value.round().clamp(0.0, 255.0) as u8;
            rgba.extend_from_slice(&[value, value, value, 255]);
        }
        let pyramid = AlignPyramid::build(
            PlaneRef::from_geometry(&luma, geometry).unwrap(),
            &draft_config(),
        )
        .unwrap();
        Frame {
            source_index,
            path: PathBuf::new(),
            rgba,
            luma,
            pyramid,
        }
    }

    /// A textured scene shifted by `(dx, dy)` and scaled by `1 + g`, as an
    /// RGBA camera preview of `width` x `height`.
    fn scene_image(width: usize, height: usize, dx: f64, dy: f64, g: f64) -> PreviewImage {
        let mut rgba = Vec::with_capacity(width * height * 4);
        let (cx, cy) = (width as f64 / 2.0, height as f64 / 2.0);
        for y in 0..height {
            for x in 0..width {
                let (sx, sy) = (
                    (x as f64 - cx) / (1.0 + g) + cx - dx,
                    (y as f64 - cy) / (1.0 + g) + cy - dy,
                );
                let v = 120.0
                    + 30.0 * (sx / 9.1 + sy / 13.7).sin()
                    + 25.0 * (sx / 21.3 - sy / 7.9).cos()
                    + 18.0 * (sx / 5.3).sin() * (sy / 8.6).cos();
                let v = v.round().clamp(0.0, 255.0) as u8;
                rgba.extend_from_slice(&[v, v.saturating_sub(10), v / 2 + 40, 255]);
            }
        }
        PreviewImage {
            path: PathBuf::from("synthetic"),
            source_size: [width as u32, height as u32],
            size: [width, height],
            rgba,
            is_overview: false,
        }
    }

    fn drift(i: usize) -> (f64, f64, f64) {
        let t = i as f64;
        (0.9 * t, -0.6 * t, 0.002 * t)
    }

    /// The proof built plane by plane, its pairs measured once and kept, is
    /// the composite a fresh registration of the same frames makes; it is
    /// due at two planes, then every four new planes.
    #[test]
    fn the_incremental_proof_matches_a_fresh_registration_of_its_frames() {
        let (w, h) = (480, 320);
        let cancel = AtomicBool::new(false);
        let mut proof = Incremental::default();
        let now = Instant::now();
        for i in 0..2 {
            let (dx, dy, g) = drift(i);
            proof
                .add_image(
                    scene_image(w, h, dx, dy, g),
                    i,
                    PathBuf::from(format!("p{i}")),
                )
                .unwrap();
            proof.received += 1;
        }
        assert!(proof.due(now), "the first proof needs only two planes");
        let first = proof.update(&cancel).unwrap();
        assert_eq!((first.used, first.revision), (2, 1));
        let measured_after_first = proof.edges.len();
        for i in 2..9 {
            let (dx, dy, g) = drift(i);
            proof
                .add_image(
                    scene_image(w, h, dx, dy, g),
                    i,
                    PathBuf::from(format!("p{i}")),
                )
                .unwrap();
            proof.received += 1;
            let due = proof.due(Instant::now());
            assert_eq!(due, proof.fresh >= PROOF_EVERY_PLANES, "plane {i}");
            if due {
                proof.update(&cancel).unwrap();
            }
        }
        assert!(proof.fresh > 0, "plane 9 is not due yet");
        let last = proof.update(&cancel).unwrap();
        assert_eq!((last.used, last.received, last.stride), (9, 9, 1));
        assert_eq!(last.draft.aligned_frames, 9);
        assert!(proof.edges.len() > measured_after_first);
        // The same frames, registered from nothing.
        let config = draft_config();
        let frames: Vec<Frame> = (0..9)
            .map(|i| {
                let (dx, dy, g) = drift(i);
                prepare(
                    scene_image(w, h, dx, dy, g),
                    i,
                    PathBuf::from(format!("p{i}")),
                    &config,
                )
                .unwrap()
                .0
            })
            .collect();
        let geometry = proof.geometry.unwrap();
        let (placement, edges, cycle_rank) =
            register(&frames, geometry, &config, &cancel, &mut |_, _, _| {}).unwrap();
        let fresh = compose(
            &frames,
            &placement,
            [w, h],
            Composed {
                considered: 9,
                alignment_edges: edges,
                cycle_rank,
                warnings: Vec::new(),
            },
            &cancel,
            &mut |_, _, _| {},
        )
        .unwrap();
        assert_eq!(fresh.reference_frame, last.draft.reference_frame);
        assert_eq!(fresh.alignment_edges, last.draft.alignment_edges);
        assert!(
            fresh.image.rgba == last.draft.image.rgba,
            "kept pairs must give the fresh registration's composite"
        );
    }

    /// Above 512 planes the proof keeps an even subsample: every second
    /// plane, the first always among them, and the planes it skips are not
    /// read at all.
    #[test]
    fn a_long_capture_is_subsampled_evenly() {
        let mut proof = Incremental::default();
        for i in 0..=MAX_FRAMES {
            proof
                .add_image(scene_image(160, 120, 0.0, 0.0, 0.0), i, PathBuf::new())
                .unwrap();
            proof.received += 1;
        }
        assert_eq!(proof.stride, 2);
        assert_eq!(proof.frames.len(), MAX_FRAMES / 2 + 1);
        assert!(proof.frames.iter().all(|f| f.source_index % 2 == 0));
        assert_eq!(proof.frames[0].source_index, 0);
        let kept = proof.frames.len();
        proof
            .add_image(
                scene_image(160, 120, 0.0, 0.0, 0.0),
                MAX_FRAMES + 1,
                PathBuf::new(),
            )
            .unwrap();
        assert_eq!(proof.frames.len(), kept, "an odd plane is not kept");
        // An odd plane is skipped unread (a missing file would warn).
        let cancel = AtomicBool::new(false);
        proof
            .add_path(Path::new("missing-odd.ARW"), &cancel)
            .unwrap();
        assert!(proof.warnings.is_empty());
        proof
            .add_path(Path::new("missing-even.ARW"), &cancel)
            .unwrap();
        assert_eq!(proof.warnings.len(), 1, "{:?}", proof.warnings);
        assert_eq!(proof.received, MAX_FRAMES + 3);
    }

    #[test]
    fn the_proof_is_due_after_four_planes_or_five_seconds() {
        let mut proof = Incremental::default();
        let start = Instant::now();
        proof
            .add_image(scene_image(160, 120, 0.0, 0.0, 0.0), 0, PathBuf::new())
            .unwrap();
        assert!(!proof.due(start), "one plane is not a proof");
        proof
            .add_image(scene_image(160, 120, 0.0, 0.0, 0.0), 1, PathBuf::new())
            .unwrap();
        assert!(proof.due(start));
        proof.fresh = 0;
        proof.last_update = Some(start);
        proof
            .add_image(scene_image(160, 120, 0.0, 0.0, 0.0), 2, PathBuf::new())
            .unwrap();
        assert!(!proof.due(start + Duration::from_secs(1)));
        assert!(proof.due(start + PROOF_EVERY));
        for i in 3..6 {
            proof
                .add_image(scene_image(160, 120, 0.0, 0.0, 0.0), i, PathBuf::new())
                .unwrap();
        }
        assert!(proof.due(start + Duration::from_secs(1)), "four new planes");
    }

    /// The proof's cost through a 512-plane capture at the A7CR preview size
    /// (480 x 320 at `DRAFT_SIDE`): every update as it falls due. Run with
    /// `cargo test --release -p strehl-ui proof_update_cost -- --ignored --nocapture`.
    #[test]
    #[ignore = "benchmark: prints the proof's update times"]
    fn proof_update_cost() {
        let cancel = AtomicBool::new(false);
        let mut proof = Incremental::default();
        let (mut times, mut peak) = (Vec::new(), 0usize);
        let started = Instant::now();
        for i in 0..512 {
            let t = i as f64 / 64.0;
            proof
                .add_image(
                    scene_image(480, 320, 1.5 * t.sin(), 0.8 * t, 0.001 * t),
                    i,
                    PathBuf::new(),
                )
                .unwrap();
            proof.received += 1;
            peak = peak.max(proof.resident);
            if proof.fresh >= PROOF_EVERY_PLANES || (proof.revision == 0 && proof.frames.len() >= 2)
            {
                let at = Instant::now();
                let update = proof.update(&cancel).unwrap();
                times.push((update.received, update.used, at.elapsed().as_secs_f64()));
            }
        }
        let worst = times.iter().map(|t| t.2).fold(0.0, f64::max);
        let last = times.last().unwrap();
        println!(
            "proof: {} updates in {:.1} s; worst update {:.3} s; last update {:.3} s over {} of {} planes (stride {}); peak resident {:.0} MiB; pairs kept {}",
            times.len(),
            started.elapsed().as_secs_f64(),
            worst,
            last.2,
            last.1,
            last.0,
            proof.stride,
            peak as f64 / 1048576.0,
            proof.edges.len()
        );
        for (received, used, seconds) in times.iter().step_by(16) {
            println!("  at {received:>3} planes: {used:>3} used, {seconds:.3} s");
        }
    }

    /// The run tail offers the first RAW of each plane as its receipt
    /// arrives, skips the other members and undurable receipts, and reports
    /// the end once the result is written.
    #[test]
    fn the_run_tail_offers_one_raw_a_plane() {
        let dir = tempfile::tempdir().unwrap();
        let mut tail = RunTail::new(dir.path().to_path_buf(), 4);
        assert_eq!(tail.poll(), (vec![], false));
        let receipt = |n: u64, durable: bool| {
            format!(
                "{{\"logical_name\":\"frame-{n:06}.ARW\",\"ok\":true,\"durable\":{durable},\"storage_encoding\":\"strehl-archive-v2\"}}\n"
            )
        };
        let mut text =
            String::from("{\"logical_name\":\"manifest.json\",\"ok\":true,\"durable\":true}\n");
        for n in 1..=6 {
            text.push_str(&receipt(n, n != 5));
        }
        std::fs::write(dir.path().join("transfer-receipts.jsonl"), &text).unwrap();
        let (paths, ended) = tail.poll();
        assert!(!ended);
        assert_eq!(
            paths,
            [
                dir.path().join("frame-000001.ARW.straw"),
                dir.path().join("frame-000006.ARW.straw")
            ],
            "plane 1 from its first member; plane 2 from member 6 (5 was not durable)"
        );
        text.push_str(&receipt(9, true));
        std::fs::write(dir.path().join("transfer-receipts.jsonl"), &text).unwrap();
        std::fs::write(dir.path().join("result.json"), b"{}").unwrap();
        let (paths, ended) = tail.poll();
        assert_eq!(paths, [dir.path().join("frame-000009.ARW.straw")]);
        assert!(ended);
        assert_eq!(tail.poll(), (vec![], false), "the end is reported once");
    }

    /// A TIFF container holding one camera JPEG, as a RAW's embedded preview.
    fn preview_file(path: &Path, image: &PreviewImage) {
        let rgb: Vec<u8> = image
            .rgba
            .as_chunks::<4>()
            .0
            .iter()
            .flat_map(|p| [p[0], p[1], p[2]])
            .collect();
        let mut jpeg = Vec::new();
        image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg, 95)
            .encode(
                &rgb,
                image.size[0] as u32,
                image.size[1] as u32,
                image::ExtendedColorType::Rgb8,
            )
            .unwrap();
        let mut bytes = vec![0_u8; 128];
        bytes[..8].copy_from_slice(&[b'I', b'I', 42, 0, 8, 0, 0, 0]);
        bytes[8..10].copy_from_slice(&2_u16.to_le_bytes());
        for (i, (tag, value)) in [(513_u16, 128_u32), (514, jpeg.len() as u32)]
            .into_iter()
            .enumerate()
        {
            let entry = &mut bytes[10 + 12 * i..22 + 12 * i];
            entry[..2].copy_from_slice(&tag.to_le_bytes());
            entry[2..4].copy_from_slice(&4_u16.to_le_bytes());
            entry[4..8].copy_from_slice(&1_u32.to_le_bytes());
            entry[8..12].copy_from_slice(&value.to_le_bytes());
        }
        bytes.extend(jpeg);
        std::fs::write(path, bytes).unwrap();
    }

    /// The worker end to end: planes offered as files arrive as proofs, the
    /// last covering every plane once the capture is finished.
    #[test]
    fn the_proof_job_reads_planes_as_they_arrive() {
        let dir = tempfile::tempdir().unwrap();
        let job = ProofJob::start();
        let deadline = Instant::now() + Duration::from_secs(60);
        let mut latest = None;
        for i in 0..6 {
            let (dx, dy, g) = drift(i);
            let path = dir.path().join(format!("frame-{i:06}.ARW"));
            preview_file(&path, &scene_image(480, 320, dx, dy, g));
            assert!(job.add_frame(path));
        }
        job.finish();
        while latest.as_ref().is_none_or(|u: &ProofUpdate| u.used < 6) {
            assert!(Instant::now() < deadline, "no proof of six planes");
            match job.poll() {
                Some(ProofEvent::Updated(update)) => latest = Some(*update),
                Some(ProofEvent::Failed(error)) => panic!("{error}"),
                None => std::thread::sleep(Duration::from_millis(20)),
            }
        }
        let update = latest.unwrap();
        assert_eq!((update.received, update.stride), (6, 1));
        assert_eq!(update.draft.aligned_frames, 6);
        assert_eq!(update.draft.image.size, [480, 320]);
        assert!(PROOF_CAUTION.contains("not the RAW"));
    }

    #[test]
    fn flat_control_averages_in_linear_light_without_inventing_detail() {
        // A selector, nonlinear averaging or any manufactured spatial response
        // fails this flat-ROI control. Different codes make selection observable.
        let geometry = PlaneGeometry {
            width: 32,
            height: 24,
        };
        let frames: Vec<_> = [64.0, 128.0, 192.0]
            .into_iter()
            .enumerate()
            .map(|(i, value)| frame(vec![value; geometry.pixels()], geometry, i))
            .collect();
        let output = blend(
            &frames,
            &[Some(Similarity::IDENTITY); 3],
            geometry,
            &AtomicBool::new(false),
            &mut |_, _, _| {},
        )
        .unwrap();
        let expected = (linear_to_srgb(
            [64, 128, 192]
                .into_iter()
                .map(|v| srgb_to_linear(v as f32 / 255.0))
                .sum::<f32>()
                / 3.0,
        ) * 255.0)
            .round() as u8;
        assert_ne!(expected, 64);
        assert_ne!(expected, 128);
        assert_ne!(expected, 192);
        assert!(
            output
                .as_chunks::<4>()
                .0
                .iter()
                .all(|p| *p == [expected, expected, expected, 255])
        );
        for frame in &frames {
            let weights = focus_weights(&frame.rgba, geometry);
            assert!(weights.windows(2).all(|p| p[0] == p[1]));
        }
    }

    #[test]
    fn flat_stack_is_not_reported_as_successfully_registered() {
        // No texture means no measurable geometric information. An identity
        // fallback would make this test incorrectly green in the product.
        let geometry = PlaneGeometry {
            width: 120,
            height: 80,
        };
        let frames: Vec<_> = (0..4)
            .map(|i| frame(vec![100.0; geometry.pixels()], geometry, i))
            .collect();
        assert!(
            register(
                &frames,
                geometry,
                &draft_config(),
                &AtomicBool::new(false),
                &mut |_, _, _| {}
            )
            .is_err()
        );
    }

    #[test]
    fn pair_graph_has_cycles_and_full_population_without_duplicate_edges() {
        let pairs = pair_set(299);
        assert_eq!(
            pairs.iter().copied().collect::<BTreeSet<_>>().len(),
            pairs.len()
        );
        assert!((1..299).all(|j| pairs.contains(&(0, j))));
        assert!(
            pairs.contains(&(41, 297)),
            "Long baselines must actually be measured"
        );
        let edges: Vec<_> = pairs
            .into_iter()
            .map(|(i, j)| AlignEdge {
                i,
                j,
                t: Similarity::IDENTITY,
                rms: 1.0,
                used: 20,
                lever: 40.0,
            })
            .collect();
        let stats = graph_stats(&edges, 299);
        assert_eq!(stats.reachable_from_0, 299);
        assert!(stats.cycle_rank > 299);
    }

    #[test]
    fn curved_similarity_track_is_checked_per_frame_in_middle_reference_gauge() {
        // A chord-only placement, inverted gather, omitted scale or wrong
        // anchor fails at interior frames even if the endpoints happen to fit.
        let geometry = PlaneGeometry {
            width: 240,
            height: 160,
        };
        let scene = |x: f64, y: f64| -> f32 {
            (120.0
                + 24.0 * (x / 5.7 + y / 8.3).sin()
                + 19.0 * (x / 13.1 - y / 4.9).cos()
                + 14.0 * (x / 3.9).sin() * (y / 6.4).cos()) as f32
        };
        let truth: Vec<_> = (0..9)
            .map(|i| {
                let t = (i as f64 - 4.0) / 4.0;
                Similarity::from_params(SimilarityParams {
                    g: 0.012 * t + 0.02 * t * t,
                    rot: 0.003 * t * t,
                    ax: 2.5 * t + 0.8 * t * t,
                    ay: -1.5 * t + 0.5 * t * t,
                })
            })
            .collect();
        let chord = Similarity {
            a: (truth[0].a + truth[8].a).scale(0.5),
            b: (truth[0].b + truth[8].b).scale(0.5),
        };
        assert!(
            chord.corner_err(truth[4], geometry) > 2.0,
            "The fixture must carry measurable non-linear curvature"
        );
        let frames: Vec<_> = truth
            .iter()
            .enumerate()
            .map(|(i, transform)| {
                let inverse = transform.invert().unwrap();
                let luma = (0..geometry.pixels())
                    .map(|pixel| {
                        let (x, y) = inverse.apply_at(
                            (pixel % geometry.width) as f64,
                            (pixel / geometry.width) as f64,
                            geometry.width as f64 / 2.0,
                            geometry.height as f64 / 2.0,
                        );
                        scene(x, y)
                    })
                    .collect();
                frame(luma, geometry, i)
            })
            .collect();
        let (placement, _, cycle_rank) = register(
            &frames,
            geometry,
            &draft_config(),
            &AtomicBool::new(false),
            &mut |_, _, _| {},
        )
        .unwrap();
        assert!(cycle_rank > 0);
        assert!(
            placement.iter().all(Option::is_some),
            "Every planted frame must be placed"
        );
        let planted_anchor = truth[4];
        let measured_anchor = placement[4].unwrap();
        let mut saw_nonidentity = false;
        for (i, measured) in placement.iter().enumerate() {
            let expected = Similarity::relative(planted_anchor, truth[i]).unwrap();
            let actual = Similarity::relative(measured_anchor, measured.unwrap()).unwrap();
            let error = actual.corner_err(expected, geometry);
            assert!(
                error < 0.8,
                "Frame {i}: {error:.3} reduced JPEG px, referenced to middle frame 4"
            );
            saw_nonidentity |= (expected.a - Cx::ONE).abs() > 0.005;
        }
        assert!(
            saw_nonidentity,
            "Identity-only fixtures cannot test scale registration"
        );
    }

    #[test]
    fn cancelled_and_oversized_drafts_fail_before_reading_sources() {
        let paths = vec![PathBuf::from("missing.arw"); MAX_FRAMES + 1];
        assert!(
            build(&paths, &AtomicBool::new(false), |_, _, _| {})
                .err()
                .unwrap()
                .to_string()
                .contains("up to 512")
        );
        assert!(
            build(&paths[..2], &AtomicBool::new(true), |_, _, _| {})
                .err()
                .unwrap()
                .to_string()
                .contains("cancelled")
        );
    }

    #[test]
    fn reduced_transform_maps_the_same_block_centres_at_even_and_odd_extents() {
        let transform = Similarity::from_params(SimilarityParams {
            g: 0.08,
            rot: 0.03,
            ax: 3.5,
            ay: -2.2,
        });
        for (width, height) in [(480, 320), (479, 319), (480, 319)] {
            let full = full_size_transform(transform, width, height);
            for (x, y) in [(0.0, 0.0), (91.0, 63.0), (220.0, 142.0)] {
                let (sx, sy) =
                    transform.apply_at(x, y, (width / 2) as f64 / 2.0, (height / 2) as f64 / 2.0);
                let actual = full.apply_at(
                    2.0 * x + 0.5,
                    2.0 * y + 0.5,
                    width as f64 / 2.0,
                    height as f64 / 2.0,
                );
                assert!((actual.0 - (2.0 * sx + 0.5)).abs() < 1e-10);
                assert!((actual.1 - (2.0 * sy + 0.5)).abs() < 1e-10);
            }
        }
    }
}
