//! A small camera-JPEG composite for inspecting a bracket before RAW processing.
//!
//! This is deliberately separate from the RAW engine. Camera processing has
//! already changed colour, noise and local contrast, so these pixels cannot
//! predict the RAW merge's detail, confidence or noise. The injected RAW noise
//! model is neither approximated nor re-estimated here. See SYNTHESIS §3.3 and
//! M86/M103 for direct graph registration; M173's capture audit also distinguishes
//! camera JPEGs from measurement RAWs. The focus response is a blend weight only:
//! noise/sharpening can increase it, so it is never an acceptance metric.

use std::collections::BTreeSet;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{self, Receiver};
use std::thread;

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
    rgba: Vec<u8>,
    luma: Vec<f32>,
    pyramid: AlignPyramid,
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
                let pyramid = AlignPyramid::build(reduced.as_ref(), &config)
                    .context("Building the draft registration pyramid")?;
                let geom = reduced.as_ref().geometry();
                geometry = Some(geom);
                resident += image.rgba.len() + reduced.data.len() * 4 + pyramid.samples() * 4;
                ensure!(
                    resident <= RESIDENT_LIMIT,
                    "This bracket exceeds the JPEG draft's 256 MiB source budget. RAW stacking remains available."
                );
                frames.push(Frame {
                    source_index,
                    rgba: image.rgba,
                    luma: reduced.data,
                    pyramid,
                });
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
    let [width, height] = size.context("No camera preview dimensions")?;
    let (placement, edges, cycle_rank) =
        register(&frames, geometry, &config, cancelled, &mut progress)?;
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
        aligned_frames * 10 >= paths.len() * 9,
        "Only {aligned_frames}/{} camera previews could be registered. A JPEG composite would omit too much of this bracket; RAW stacking remains available.",
        paths.len()
    );
    let skipped_frames = paths.len() - aligned_frames;
    if skipped_frames > 0 {
        warnings.push(format!(
            "The JPEG draft omits {skipped_frames} source frames"
        ));
    }
    let rgba = blend(
        &frames,
        &transforms,
        PlaneGeometry { width, height },
        cancelled,
        &mut progress,
    )?;
    Ok(DraftPreview {
        image: PreviewImage {
            path: paths[frames[reference].source_index].clone(),
            source_size: [width as u32, height as u32],
            size: [width, height],
            rgba,
            is_overview: true,
        },
        source_frames: paths.len(),
        aligned_frames,
        skipped_frames,
        alignment_edges: edges,
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
        let frame = |index: usize| AlignFrame {
            plane: PlaneRef::from_geometry(&frames[index].luma, geometry).unwrap(),
            pyramid: &frames[index].pyramid,
        };
        if let Ok(fit) = align_pair(frame(i), frame(j), &spots, config) {
            let transform = fit.similarity();
            if sane_transform(transform, geometry) {
                edges.push(AlignEdge::from_stage(i, j, &fit));
            }
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
            rgba,
            luma,
            pyramid,
        }
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
