//! Opt-in session geometry: bounded source workspaces and direct native edges.
//!
//! Guide scales propose cross-pass searches. They never certify equal focus.
//! Delivered placements come from one native-edge solve with explicit tracks.
use crate::session_cache::{CachedSource, SourceCache};
use crate::session_input::{ResolvedSession, SessionSpec, SourceIdentity, hex};
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;
use strehl_core::align::{
    AlignConfig, AlignEdge, AlignFailure, AlignFrame, AlignPyramid, GlobalOptions, PlaneRef,
    Resampler, Similarity, StageFit, align_pair, graph_stats, lift_box_decimated_similarity,
    refine_pair_observed, solve_global_in_tracks, tile_grid,
};
use crate::session_frame_photometry::{self as frame_photometry, EdgePhotometry, FramePhotometry};
use strehl_core::align_global::{GlobalSearchConfig, global_similarity_candidates};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma};
use strehl_core::warpmap::{FrameWarp, Provenance, StackIdentity, WarpMap};

const GENERATION: &str = "session-native-direct-tracks-v1";
const ENVELOPE_VERSION: u32 = 1;
const MAX_ENVELOPE_BYTES: u64 = 128 << 20;
static NEXT_TEMP: AtomicU64 = AtomicU64::new(0);

/// Every search/solver bar is explicit and bound into the alignment envelope.
/// Memory is a conservative reservation, not a measured peak-RSS guarantee.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct SessionAlignConfig {
    pub memory_limit_bytes: usize,
    pub workers: usize,
    pub guide_max_side: usize,
    pub guide_tile: usize,
    pub guide_grid: [usize; 2],
    pub guide_radius: i32,
    pub native_tile: usize,
    pub native_grid: [usize; 2],
    pub native_radius: i32,
    pub native_margin: usize,
    pub native_iterations: usize,
    pub minimum_peak: f32,
    pub minimum_contrast: f32,
    pub minimum_tiles: usize,
    pub outlier_mads: f32,
    pub intra_spans: Vec<usize>,
    pub cross_probes: usize,
    pub cross_neighbor_radius: usize,
    pub focus_step_fraction: f64,
    pub smooth: f64,
    pub smooth_huber_plane_px: Option<f64>,
    pub edge_huber_plane_px: f64,
    pub irls_iterations: usize,
    /// Representative pass frames searched by the wide-baseline initializer
    /// when a pass has no accepted cross probe; zero disables it.
    pub wide_baseline_searches: usize,
}

impl Default for SessionAlignConfig {
    fn default() -> Self {
        Self {
            memory_limit_bytes: 8 << 30,
            workers: std::thread::available_parallelism().map_or(1, usize::from),
            guide_max_side: 1024,
            guide_tile: 32,
            guide_grid: [8, 6],
            guide_radius: 6,
            native_tile: 128,
            native_grid: [12, 8],
            native_radius: 6,
            native_margin: 96,
            native_iterations: 8,
            minimum_peak: 0.5,
            minimum_contrast: 4.0,
            minimum_tiles: 8,
            outlier_mads: 3.0,
            intra_spans: vec![1, 2, 4, 8, 16, 32, 64, 128],
            cross_probes: 7,
            cross_neighbor_radius: 1,
            focus_step_fraction: 0.25,
            smooth: 1.0,
            smooth_huber_plane_px: Some(1.0),
            edge_huber_plane_px: 3.0,
            irls_iterations: 3,
            wide_baseline_searches: 3,
        }
    }
}

impl SessionAlignConfig {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.workers > 0 && self.workers <= 1024,
            "alignment workers must be 1..1024"
        );
        ensure!(
            self.guide_max_side >= 128 && self.guide_max_side <= 4096,
            "guide maximum side must be 128..4096"
        );
        ensure!(
            self.guide_tile >= 8 && self.native_tile >= 8,
            "alignment tiles must be at least 8 pixels"
        );
        ensure!(
            self.guide_radius > 0
                && self.guide_radius <= 64
                && self.native_radius > 0
                && self.native_radius <= 64,
            "alignment search radii must be 1..64"
        );
        ensure!(
            self.guide_grid
                .iter()
                .chain(&self.native_grid)
                .all(|&n| (2..=64).contains(&n)),
            "alignment grid dimensions must be 2..64"
        );
        ensure!(
            self.minimum_tiles >= 3
                && self.minimum_tiles <= 24
                && self.minimum_tiles <= self.guide_grid[0] * self.guide_grid[1]
                && self.minimum_tiles <= self.native_grid[0] * self.native_grid[1],
            "minimum tile count does not fit alignment grids"
        );
        ensure!(
            self.native_tile <= 2048 && self.guide_tile <= 256 && self.native_margin <= 4096,
            "alignment tile or margin exceeds bounded workspace limits"
        );
        ensure!(
            self.minimum_peak.is_finite() && (0.0..=1.0).contains(&self.minimum_peak),
            "minimum peak must be finite in 0..1"
        );
        ensure!(
            self.minimum_contrast.is_finite()
                && self.minimum_contrast >= 0.0
                && self.outlier_mads.is_finite()
                && self.outlier_mads > 0.0,
            "invalid contrast or outlier bar"
        );
        ensure!(
            !self.intra_spans.is_empty()
                && self.intra_spans.contains(&1)
                && self.intra_spans.iter().all(|&s| s > 0),
            "intra-pass spans must be positive and include span 1"
        );
        ensure!(
            (2..=32).contains(&self.cross_probes) && self.cross_neighbor_radius <= 4,
            "invalid cross-pass search bounds"
        );
        ensure!(
            self.wide_baseline_searches <= 8,
            "wide-baseline searches must be 0..8"
        );
        ensure!(
            self.native_iterations > 0
                && self.native_iterations <= 32
                && self.irls_iterations > 0
                && self.irls_iterations <= 32,
            "iteration counts must be 1..32"
        );
        ensure!(
            self.focus_step_fraction.is_finite()
                && self.focus_step_fraction > 0.0
                && self.focus_step_fraction <= 0.5,
            "focus hint fraction must be in (0,0.5]"
        );
        ensure!(
            self.smooth.is_finite()
                && self.smooth >= 0.0
                && self.edge_huber_plane_px.is_finite()
                && self.edge_huber_plane_px > 0.0
                && self
                    .smooth_huber_plane_px
                    .is_none_or(|v| v.is_finite() && v > 0.0),
            "invalid solver prior or Huber bar"
        );
        Ok(())
    }

    fn estimator(&self, guide: bool) -> AlignConfig {
        AlignConfig {
            coarse_factors: vec![4, 2],
            coarse_tile: 16,
            coarse_grid: (6, 4),
            coarse_radius: 8,
            fine_tile: if guide {
                self.guide_tile
            } else {
                self.native_tile
            },
            fine_grid: if guide {
                (self.guide_grid[0], self.guide_grid[1])
            } else {
                (self.native_grid[0], self.native_grid[1])
            },
            fine_radius: if guide {
                self.guide_radius
            } else {
                self.native_radius
            },
            margin: if guide { 24 } else { self.native_margin },
            min_contrast: self.minimum_contrast,
            min_peak: self.minimum_peak,
            min_tiles: self.minimum_tiles,
            outlier_mads: self.outlier_mads,
            fine_iters: if guide { 2 } else { self.native_iterations },
            warp_tiles: true,
            ..AlignConfig::shallow()
        }
    }

    fn solver(&self, geometry: PlaneGeometry) -> GlobalOptions {
        GlobalOptions {
            smooth: self.smooth,
            smooth_huber_px: self.smooth_huber_plane_px,
            huber_px: self.edge_huber_plane_px,
            irls_iters: self.irls_iterations,
            ..GlobalOptions::new(geometry)
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AlignmentMemoryPlan {
    pub limit_bytes: usize,
    pub source_cache_reserved_bytes: usize,
    /// Four original padded frame buffers, conservatively reserved for one decode.
    pub decoder_reserved_bytes: usize,
    pub solver_reserved_bytes: usize,
    pub guide_cache_reserved_bytes: usize,
    pub native_green_reserved_bytes: usize,
    pub pair_scratch_reserved_bytes: usize,
    pub planned_total_bytes: usize,
    pub guide_workers: usize,
    pub native_workers: usize,
    pub peak_guide_bytes: usize,
    pub peak_native_green_bytes: usize,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PairPurpose {
    IntraPass,
    CrossProbe,
    CrossCandidate,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EdgeReceipt {
    pub i: usize,
    pub j: usize,
    pub purpose: PairPurpose,
    pub stage: String,
    pub accepted: bool,
    /// Exact full-plane similarity coefficients [a.re,a.im,b.re,b.im].
    pub transform_bits: Option<[u64; 4]>,
    pub rms_plane_px: Option<f64>,
    pub used: usize,
    pub attempted: usize,
    pub correlated: usize,
    pub peak_mean: Option<f32>,
    pub lever_plane_px: Option<f64>,
    pub refusal: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FocusPairCandidate {
    pub i: usize,
    pub j: usize,
    pub mutual_nearest: bool,
    pub log_scale_gap: f64,
    pub allowed_log_scale_gap: Option<f64>,
    pub candidate_same_focus: bool,
    /// Geometry cannot establish equal focus; a separate consumer must validate it.
    pub validated_same_focus: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PassAlignmentReport {
    pub pass_index: usize,
    pub name: String,
    pub frames: usize,
    pub placed: usize,
    pub refused: usize,
    pub measured_intra_edges: usize,
    pub measured_cross_edges: usize,
    pub intra_components: usize,
    pub intra_cycle_rank: usize,
    /// Joined to the anchor only through wide-baseline seeds.
    #[serde(default)]
    pub wide_baseline: bool,
    /// Median tiles retained by accepted native cross edges divided by the
    /// pass's own median intra-edge tiles. Self-normalizes texture, exposure
    /// and tile geometry; a low value means one 2-D placement explains only a
    /// local part of the overlap (for example a pose change between sessions).
    #[serde(default)]
    pub cross_support_ratio: Option<f64>,
    /// Median placed-frame magnification relative to the anchor pass.
    #[serde(default)]
    pub relative_scale: Option<f64>,
    /// False when a wide-baseline pass fails the support bar; fused outputs
    /// must not consume it (ghosting). Ordinary passes are never flagged.
    #[serde(default = "default_true")]
    pub geometry_consistent: bool,
    /// Multiplier applied to the featureless-tile contrast floor for this pass.
    #[serde(default = "default_one")]
    pub contrast_scale: f32,
    /// Remaining local displacement (guide px) of the pass's focus-nearest
    /// frame against the reference frame after placement.
    #[serde(default)]
    pub geometric_residual: Option<crate::session_geometry_check::GeometricResidual>,
    /// Median spatial spread of block brightness ratios on edges to the anchor
    /// pass (natural log). Large values mean shading, not only level, differs.
    #[serde(default)]
    pub cross_photometric_spread: Option<f64>,
    /// Median absolute residual of those edges after the per-frame solve.
    #[serde(default)]
    pub cross_photometric_residual: Option<f64>,
    /// Solved per-frame log brightness range within the pass.
    #[serde(default)]
    pub log_brightness_range: Option<[f64; 2]>,
}

fn default_one() -> f32 {
    1.0
}

fn default_true() -> bool {
    true
}

/// Minimum [`PassAlignmentReport::cross_support_ratio`] for a wide-baseline
/// pass. Bug-3 subsets: a compatible pass measured 1.17; pose-changed passes
/// 0.15-0.28. An engineering bar, not a calibrated constant.
pub const WIDE_SUPPORT_RATIO: f64 = 0.5;

/// Largest median post-placement displacement (guide px) for a wide-baseline
/// pass; the direct test, preferred over the support proxy whenever measurable.
/// Bug-3 pose-changed passes measured about 6.5; bug-4's relit 104 about 0.5.
pub const WIDE_RESIDUAL_GUIDE_PX: f64 = 1.5;

fn median_usize(mut values: Vec<usize>) -> Option<f64> {
    values.sort_unstable();
    (!values.is_empty()).then(|| {
        let mid = values.len() / 2;
        if values.len() % 2 == 1 {
            values[mid] as f64
        } else {
            0.5 * (values[mid - 1] + values[mid]) as f64
        }
    })
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SessionAlignmentReport {
    pub generation: String,
    pub binding_sha256: String,
    pub primary_pass: Option<usize>,
    pub reference_pass: usize,
    pub reference_frame: usize,
    pub geometry_plane_pixels: [usize; 2],
    pub sensor_pixels_per_plane_pixel: usize,
    pub guide_factor: usize,
    pub frames: usize,
    pub measured_edges: usize,
    pub components: usize,
    pub cycle_rank: usize,
    pub anchor_component_cycle_rank: usize,
    pub passes: Vec<PassAlignmentReport>,
    pub edges: Vec<EdgeReceipt>,
    pub focus_candidates: Vec<FocusPairCandidate>,
    pub memory: AlignmentMemoryPlan,
    pub source_cache_peak_bytes: usize,
    pub source_decodes: u64,
    pub source_disk_hits: u64,
    pub elapsed_seconds: f64,
    /// Wide-baseline proposals for passes without an accepted cross probe.
    #[serde(default)]
    pub wide_baseline: Vec<WideBaselineReport>,
    /// Per-frame brightness relative to the reference frame, from overlaps.
    #[serde(default)]
    pub frame_photometry: Option<FramePhotometry>,
    #[serde(default)]
    pub photometric_edges: Vec<EdgePhotometry>,
}

/// One global-search attempt. Candidates are proposals; only `validated`
/// candidates were confirmed by a direct seeded guide refinement.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WideBaselineCandidate {
    pub scale: f64,
    pub rotation_degrees: f64,
    pub ncc: f64,
    pub overlap_px: f64,
    pub validated: bool,
    pub used_tiles: usize,
    pub rms_guide_px: Option<f32>,
    pub refusal: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WideBaselineReport {
    pub pass: usize,
    pub anchor_frame: usize,
    pub pass_frame: usize,
    pub elapsed_seconds: f64,
    pub candidates: Vec<WideBaselineCandidate>,
    /// Seed (anchor frame -> pass frame, guide-centred) used for re-measurement.
    pub selected_seed_bits: Option<[u64; 4]>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
struct Binding {
    generation: String,
    algorithm_sha256: String,
    session: SessionSpec,
    sources: Vec<SourceIdentity>,
    config: SessionAlignConfig,
    resampler: String,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Envelope {
    version: u32,
    binding: Binding,
    warpmap: String,
    warpmap_sha256: String,
    report: SessionAlignmentReport,
}

pub struct SessionAlignment {
    pub map: WarpMap,
    pub report: SessionAlignmentReport,
    pub pair_candidates: Vec<FocusPairCandidate>,
    binding: Binding,
}

/// Source bytes as bound into cache identities, with CRLF line endings
/// normalised to LF so a checkout's line-ending conversion cannot change a
/// cache key (it once forced a full re-alignment).
pub(crate) fn source_text(bytes: &[u8]) -> std::borrow::Cow<'_, [u8]> {
    if !bytes.contains(&b'\r') {
        return std::borrow::Cow::Borrowed(bytes);
    }
    let mut out = Vec::with_capacity(bytes.len());
    for (i, &b) in bytes.iter().enumerate() {
        if !(b == b'\r' && bytes.get(i + 1) == Some(&b'\n')) {
            out.push(b);
        }
    }
    std::borrow::Cow::Owned(out)
}

fn binding(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    config: &SessionAlignConfig,
    resampler: Resampler,
) -> Result<Binding> {
    session.spec.validate()?;
    config.validate()?;
    ensure!(
        identities.len() == session.len() && !session.is_empty(),
        "session identity count mismatch"
    );
    for (frame, identity) in session.frames.iter().zip(identities) {
        identity.validate()?;
        identity.check_unchanged()?;
        ensure!(
            frame.path == identity.path
                && frame.bytes == identity.bytes
                && frame.modified_unix_nanos == identity.modified_unix_nanos,
            "source identity differs from session frame {}",
            frame.global_index
        );
    }
    let mut algorithm = Sha256::new();
    for bytes in [
        include_bytes!("session-align.rs").as_slice(),
        include_bytes!("../../strehl-core/src/align.rs").as_slice(),
        include_bytes!("../../strehl-core/src/align-global.rs").as_slice(),
        include_bytes!("session-frame-photometry.rs").as_slice(),
        include_bytes!("session-geometry-check.rs").as_slice(),
        include_bytes!("../../strehl-core/src/plane.rs").as_slice(),
        include_bytes!("../../strehl-core/src/warpmap.rs").as_slice(),
        include_bytes!("../../strehl-raw/src/lib.rs").as_slice(),
        include_bytes!("../../../Cargo.lock").as_slice(),
        include_bytes!("session-cache.rs").as_slice(),
        include_bytes!("session-input.rs").as_slice(),
    ] {
        algorithm.update(source_text(bytes));
    }
    Ok(Binding {
        generation: GENERATION.into(),
        algorithm_sha256: hex(&algorithm.finalize()),
        session: session.spec.clone(),
        sources: identities.to_vec(),
        config: config.clone(),
        resampler: format!("{resampler:?}"),
    })
}

fn binding_digest(binding: &Binding) -> Result<String> {
    Ok(hex(&Sha256::digest(serde_json::to_vec(binding)?)))
}

impl SessionAlignment {
    pub fn save(&self, path: &Path, session: &ResolvedSession) -> Result<()> {
        ensure!(
            session.spec == self.binding.session,
            "alignment belongs to a different session"
        );
        let path = session.ensure_output_outside_sources(path)?;
        let parent = path
            .parent()
            .context("alignment envelope needs a parent directory")?;
        fs::create_dir_all(parent)?;
        let path = session.ensure_output_outside_sources(&path)?;
        let temp = path.with_extension(format!(
            "{}.{}.partial",
            std::process::id(),
            NEXT_TEMP.fetch_add(1, Ordering::Relaxed)
        ));
        session.ensure_output_outside_sources(&temp)?;
        let warpmap = self.map.to_text();
        let envelope = Envelope {
            version: ENVELOPE_VERSION,
            binding: self.binding.clone(),
            warpmap_sha256: hex(&Sha256::digest(warpmap.as_bytes())),
            warpmap,
            report: self.report.clone(),
        };
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp)?;
        let written = (|| -> Result<()> {
            serde_json::to_writer(&mut file, &envelope)?;
            file.write_all(b"\n")?;
            file.sync_all()?;
            Ok(())
        })();
        drop(file);
        if let Err(error) = written {
            let _ = fs::remove_file(&temp);
            return Err(error);
        }
        session.ensure_output_outside_sources(&path)?;
        if let Err(error) = publish_without_replace(&temp, &path) {
            let _ = fs::remove_file(&temp);
            return Err(error.into());
        }
        Ok(())
    }

    pub fn load(
        path: &Path,
        session: &ResolvedSession,
        identities: &[SourceIdentity],
        config: &SessionAlignConfig,
        resampler: Resampler,
    ) -> Result<Self> {
        let expected = binding(session, identities, config, resampler)?;
        let file = File::open(path)?;
        ensure!(
            file.metadata()?.len() <= MAX_ENVELOPE_BYTES,
            "alignment envelope too large"
        );
        let mut bytes = Vec::new();
        file.take(MAX_ENVELOPE_BYTES + 1).read_to_end(&mut bytes)?;
        ensure!(
            bytes.len() as u64 <= MAX_ENVELOPE_BYTES,
            "alignment envelope grew beyond limit"
        );
        let mut envelope: Envelope = serde_json::from_slice(&bytes)?;
        ensure!(
            envelope.version == ENVELOPE_VERSION && envelope.binding == expected,
            "alignment envelope does not match sources, session layout, algorithm or settings"
        );
        ensure!(
            envelope.report.binding_sha256 == binding_digest(&expected)?,
            "alignment report binding is inconsistent"
        );
        ensure!(
            envelope.warpmap_sha256 == hex(&Sha256::digest(envelope.warpmap.as_bytes())),
            "alignment map payload checksum mismatch"
        );
        let map = WarpMap::from_text(&envelope.warpmap)?;
        ensure!(
            map.len() == session.len()
                && map.resampler() == resampler
                && map.provenance().strategy == GENERATION,
            "alignment map does not match session policy"
        );
        map.check_stack(&StackIdentity::from_paths(
            "multi-stack session",
            &session.paths(),
        )?)?;
        ensure!(
            map.provenance().reference == reference(session).1
                && envelope.report.reference_frame == map.provenance().reference,
            "alignment reference differs from session"
        );
        ensure!(
            envelope.report.frames == session.len()
                && envelope.report.primary_pass == session.primary_pass_index()
                && envelope.report.reference_pass == reference(session).0
                && envelope.report.geometry_plane_pixels
                    == [map.geometry().width, map.geometry().height],
            "alignment report geometry or reference is inconsistent"
        );
        ensure!(
            map.geometry().width > 0
                && map.geometry().height > 0
                && envelope.report.sensor_pixels_per_plane_pixel == 2
                && envelope.report.guide_factor > 0,
            "alignment has invalid pixel geometry"
        );
        ensure!(
            envelope.report.passes.len() == session.passes.len(),
            "alignment pass report count mismatch"
        );
        for (index, (reported, pass)) in envelope
            .report
            .passes
            .iter()
            .zip(&session.passes)
            .enumerate()
        {
            let placed = pass
                .global_range
                .clone()
                .filter(|&i| map.placement(i).is_ok())
                .count();
            ensure!(
                reported.pass_index == index
                    && reported.frames == pass.global_range.len()
                    && reported.placed == placed
                    && reported.refused == pass.global_range.len() - placed,
                "alignment pass coverage report mismatch"
            );
        }
        let mut seen = BTreeSet::new();
        let mut native_edges = Vec::new();
        for edge in &envelope.report.edges {
            ensure!(
                edge.i < edge.j
                    && edge.j < session.len()
                    && matches!(
                        edge.stage.as_str(),
                        "guide" | "native" | "guide-wide" | "native-wide" | "guide-identity"
                    )
                    && seen.insert((edge.i, edge.j, edge.stage.as_str())),
                "alignment edge report has invalid or duplicate indices"
            );
            let intra = session.frames[edge.i].pass_index == session.frames[edge.j].pass_index;
            ensure!(
                (edge.purpose == PairPurpose::IntraPass) == intra,
                "alignment edge purpose disagrees with its pass indices"
            );
            if edge.accepted && matches!(edge.stage.as_str(), "native" | "native-wide") {
                let bits = edge
                    .transform_bits
                    .context("accepted native edge lacks transform")?;
                let t = Similarity {
                    a: strehl_core::align::Cx::new(
                        f64::from_bits(bits[0]),
                        f64::from_bits(bits[1]),
                    ),
                    b: strehl_core::align::Cx::new(
                        f64::from_bits(bits[2]),
                        f64::from_bits(bits[3]),
                    ),
                };
                ensure!(
                    t.a.is_finite() && t.b.is_finite() && t.a.norm_sq() > 0.0,
                    "accepted edge has invalid transform"
                );
                native_edges.push(AlignEdge {
                    i: edge.i,
                    j: edge.j,
                    t,
                    rms: edge.rms_plane_px.context("accepted edge lacks residual")?,
                    used: edge.used,
                    lever: edge.lever_plane_px.context("accepted edge lacks lever")?,
                });
            }
        }
        let stats = graph_stats(&native_edges, session.len());
        ensure!(
            envelope.report.measured_edges == native_edges.len()
                && envelope.report.components == stats.components
                && envelope.report.cycle_rank == stats.cycle_rank,
            "alignment graph report mismatch"
        );
        let reached =
            strehl_core::align::reachable_from(&native_edges, session.len(), reference(session).1);
        ensure!(
            reached
                .iter()
                .enumerate()
                .all(|(i, &reached)| reached == map.placement(i).is_ok()),
            "alignment map coverage differs from its measured graph"
        );
        let poses: Vec<_> = (0..session.len()).map(|i| map.placement(i).ok()).collect();
        // Report candidates are evidence hints, never authority over source indices.
        // Rebuild them from the bound map so corrupted flags cannot certify focus.
        envelope.report.focus_candidates = focus_candidates(
            session,
            &poses,
            reference(session).0,
            config.focus_step_fraction,
        );
        Ok(Self {
            map,
            pair_candidates: envelope.report.focus_candidates.clone(),
            report: envelope.report,
            binding: expected,
        })
    }
}

fn publish_without_replace(temporary: &Path, destination: &Path) -> std::io::Result<()> {
    // Both files are in one directory. A hard-link publication is atomic and
    // refuses an existing name on Windows and Unix; complete bytes appear once.
    // Filesystems without hard links refuse rather than fall back to clobbering.
    fs::hard_link(temporary, destination)?;
    fs::remove_file(temporary)
}

fn reference(session: &ResolvedSession) -> (usize, usize) {
    let pass = session.primary_pass_index().unwrap_or_else(|| {
        session
            .passes
            .iter()
            .enumerate()
            .max_by_key(|(i, pass)| (pass.global_range.len(), std::cmp::Reverse(*i)))
            .map_or(0, |(i, _)| i)
    });
    let range = &session.passes[pass].global_range;
    (pass, range.start + range.len() / 2)
}

struct Guide {
    data: Vec<f32>,
    geometry: PlaneGeometry,
    pyramid: AlignPyramid,
    /// Black-subtracted clipping level in guide units.
    ceiling: f32,
}
impl Guide {
    fn bytes(&self) -> usize {
        (self.data.len() + self.pyramid.samples()) * 4
    }
}
struct NativePlane {
    data: Vec<f32>,
    geometry: PlaneGeometry,
}

struct Resident<T> {
    data: Arc<T>,
    bytes: usize,
    touched: u64,
}
struct BoundedPlanes<T> {
    entries: HashMap<usize, Resident<T>>,
    budget: usize,
    resident: usize,
    peak: usize,
    clock: u64,
}
impl<T> BoundedPlanes<T> {
    fn new(budget: usize) -> Self {
        Self {
            entries: HashMap::new(),
            budget,
            resident: 0,
            peak: 0,
            clock: 0,
        }
    }
    fn get(&mut self, index: usize) -> Option<Arc<T>> {
        self.clock += 1;
        let item = self.entries.get_mut(&index)?;
        item.touched = self.clock;
        Some(Arc::clone(&item.data))
    }
    fn reserve(&mut self, bytes: usize) -> Result<()> {
        ensure!(
            bytes <= self.budget,
            "one alignment plane exceeds its cache reservation"
        );
        while self.resident > self.budget - bytes {
            let victim = self
                .entries
                .iter()
                .filter(|(_, entry)| Arc::strong_count(&entry.data) == 1)
                .min_by_key(|(index, entry)| (entry.touched, **index))
                .map(|(&index, _)| index)
                .context("alignment plane reservation exhausted by pinned pair handles")?;
            self.resident -= self.entries.remove(&victim).expect("selected entry").bytes;
        }
        Ok(())
    }
    fn insert(&mut self, index: usize, data: T, bytes: usize) -> Arc<T> {
        self.clock += 1;
        let data = Arc::new(data);
        self.resident += bytes;
        self.peak = self.peak.max(self.resident);
        self.entries.insert(
            index,
            Resident {
                data: Arc::clone(&data),
                bytes,
                touched: self.clock,
            },
        );
        data
    }
}

fn product(a: usize, b: usize) -> Result<usize> {
    a.checked_mul(b).context("alignment resource size overflow")
}

fn sum(values: &[usize]) -> Result<usize> {
    values.iter().try_fold(0usize, |a, b| {
        a.checked_add(*b)
            .context("alignment resource size overflow")
    })
}

/// The dense solver holds two complex matrices; the additional matrix allowance,
/// edge receipts and fixed overhead deliberately exceed its current live set.
fn memory_plan(
    config: &SessionAlignConfig,
    frames: usize,
    passes: usize,
    cache_bytes: usize,
    decoded_frame_bytes: usize,
    native_geometry: PlaneGeometry,
) -> Result<AlignmentMemoryPlan> {
    // A smaller active crop can cross an integer reduction-factor boundary.
    // Reserve the maximum square, rather than assuming the header aspect ratio.
    let guide_geometry = PlaneGeometry {
        width: config.guide_max_side,
        height: config.guide_max_side,
    };
    let guide_bytes = guide_bytes(guide_geometry)?;
    let native_bytes = product(native_geometry.pixels(), 4)?;
    let decoder_reserved_bytes = product(decoded_frame_bytes, 4)?;
    let search_per_frame = sum(&[
        config.intra_spans.len(),
        product(passes, 2 * (2 * config.cross_neighbor_radius + 1))?,
    ])?;
    let edge_bound = sum(&[
        product(frames, search_per_frame)?,
        product(passes, product(config.cross_probes, config.cross_probes)?)?,
    ])?;
    let solver_reserved_bytes = sum(&[
        product(product(frames, frames)?, 48)?,
        product(edge_bound, 4096)?,
        64 << 20,
    ])?;
    let fixed = sum(&[cache_bytes, decoder_reserved_bytes, solver_reserved_bytes])?;
    let available = config.memory_limit_bytes.checked_sub(fixed).context("alignment memory limit cannot hold the source cache, decoder and global solver reservations")?;
    let minimum_guides = product(guide_bytes, 2)?;
    let guide_cache_reserved_bytes =
        product(frames.max(2), guide_bytes)?.min((available / 3).max(minimum_guides));
    let pair_side = config.native_tile.max(config.guide_tile)
        + 2 * config.native_radius.max(config.guide_radius) as usize
        + 8;
    // NCC integrals, tile extraction, correlation surface and fit observations.
    let scratch_per_worker = sum(&[product(product(pair_side, pair_side)?, 32)?, 1 << 20])?;
    let native_pair_cost = sum(&[product(native_bytes, 2)?, scratch_per_worker])?;
    let after_guides = available
        .checked_sub(guide_cache_reserved_bytes)
        .context("alignment memory limit cannot hold two guide planes")?;
    let native_workers = config.workers.min(after_guides / native_pair_cost);
    ensure!(
        native_workers > 0,
        "alignment memory limit cannot hold one direct native pair and its scratch workspace"
    );
    let guide_workers = config
        .workers
        .min(native_workers)
        .min(guide_cache_reserved_bytes / minimum_guides);
    ensure!(
        guide_workers > 0,
        "alignment memory limit cannot hold a guide pair"
    );
    let pair_scratch_reserved_bytes = product(native_workers, scratch_per_worker)?;
    let native_green_reserved_bytes =
        (after_guides - pair_scratch_reserved_bytes).min(product(frames.max(2), native_bytes)?);
    let planned_total_bytes = sum(&[
        fixed,
        guide_cache_reserved_bytes,
        native_green_reserved_bytes,
        pair_scratch_reserved_bytes,
    ])?;
    ensure!(
        planned_total_bytes <= config.memory_limit_bytes,
        "internal alignment memory reservation exceeds limit"
    );
    Ok(AlignmentMemoryPlan {
        limit_bytes: config.memory_limit_bytes,
        source_cache_reserved_bytes: cache_bytes,
        decoder_reserved_bytes,
        solver_reserved_bytes,
        guide_cache_reserved_bytes,
        native_green_reserved_bytes,
        pair_scratch_reserved_bytes,
        planned_total_bytes,
        guide_workers,
        native_workers,
        peak_guide_bytes: 0,
        peak_native_green_bytes: 0,
    })
}

fn guide_bytes(geometry: PlaneGeometry) -> Result<usize> {
    product(
        sum(&[
            geometry.pixels(),
            product(geometry.width / 2, geometry.height / 2)?,
            product(geometry.width / 4, geometry.height / 4)?,
        ])?,
        4,
    )
}

/// Box-reduce green directly from the unchanged active CFA. Arithmetic matches
/// green_luma followed by the core box reducer, including clamp-before-average.
fn boxed_green(source: &impl QuadSource, black: f32, factor: usize) -> (Vec<f32>, PlaneGeometry) {
    let full = source.geometry();
    let geometry = PlaneGeometry {
        width: full.width / factor,
        height: full.height / factor,
    };
    let mut data = vec![0.0f32; geometry.pixels()];
    let inverse = 1.0 / (factor * factor) as f32;
    for y in 0..geometry.height {
        for x in 0..geometry.width {
            let mut value = 0.0f32;
            for dy in 0..factor {
                let (top, bottom) = source.quad_rows(y * factor + dy);
                for dx in 0..factor {
                    let sx = 2 * (x * factor + dx);
                    value += 0.5
                        * ((top[sx + 1] as f32 - black).max(0.0)
                            + (bottom[sx] as f32 - black).max(0.0));
                }
            }
            data[geometry.index(x, y)] = value * inverse;
        }
    }
    (data, geometry)
}

fn source(
    index: usize,
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    cache: &mut SourceCache,
) -> Result<Arc<CachedSource>> {
    cache
        .load_or_decode(&session.frames[index], &identities[index])
        .map_err(anyhow::Error::from)
}

struct PlaneInputs<'a> {
    session: &'a ResolvedSession,
    identities: &'a [SourceIdentity],
    geometry: PlaneGeometry,
    factor: usize,
    guide_config: AlignConfig,
    /// Per-frame multiplier on the featureless-tile contrast floor (DN^2).
    /// NCC is gain-invariant but the floor is absolute, so a substantially
    /// darker pass would lose tiles to exposure alone. Empty means 1.
    contrast_scale: Vec<f32>,
}

/// Passes at least this fraction of the brightest pass's signal level keep the
/// unscaled contrast floor, so equal-exposure sessions are measured unchanged.
const CONTRAST_SCALE_ONSET: f32 = 0.8;

/// Robust bright-signal level of a guide: its 99th percentile on a sparse sample.
fn signal_level(data: &[f32]) -> f32 {
    let mut sample: Vec<f32> = data.iter().step_by(7).copied().filter(|v| v.is_finite()).collect();
    if sample.is_empty() {
        return 0.0;
    }
    let k = (sample.len() * 99 / 100).min(sample.len() - 1);
    *sample.select_nth_unstable_by(k, f32::total_cmp).1
}

/// Per-pass contrast-floor multipliers from per-frame guide levels.
fn contrast_scales(session: &ResolvedSession, levels: &[f32]) -> Vec<f32> {
    let pass_levels: Vec<f32> = session
        .passes
        .iter()
        .map(|pass| {
            let mut v: Vec<f32> = levels[pass.global_range.clone()].to_vec();
            v.sort_by(f32::total_cmp);
            v.get(v.len() / 2).copied().unwrap_or(0.0)
        })
        .collect();
    let brightest = pass_levels.iter().copied().fold(0.0f32, f32::max);
    pass_levels
        .iter()
        .map(|&level| {
            let ratio = if brightest > 0.0 { level / brightest } else { 1.0 };
            if ratio.is_finite() && ratio > 0.0 && ratio < CONTRAST_SCALE_ONSET {
                ratio * ratio
            } else {
                1.0
            }
        })
        .collect()
}

impl PlaneInputs<'_> {
    /// Estimator for pair `(i, j)` with the darker frame's contrast floor.
    fn pair_config(&self, base: &AlignConfig, i: usize, j: usize) -> AlignConfig {
        let mut cfg = base.clone();
        let scale = |k: usize| self.contrast_scale.get(k).copied().unwrap_or(1.0);
        let s = scale(i).min(scale(j));
        if s < 1.0 {
            cfg.min_contrast *= s;
        }
        cfg
    }

    fn guide(
        &self,
        index: usize,
        sources: &mut SourceCache,
        planes: &mut BoundedPlanes<Guide>,
    ) -> Result<Arc<Guide>> {
        if let Some(plane) = planes.get(index) {
            return Ok(plane);
        }
        let geometry = PlaneGeometry {
            width: self.geometry.width / self.factor,
            height: self.geometry.height / self.factor,
        };
        let bytes = guide_bytes(geometry)?;
        planes.reserve(bytes)?;
        let source = source(index, self.session, self.identities, sources)?;
        ensure!(
            source.geometry() == self.geometry,
            "source plane geometry changed during alignment"
        );
        let (data, geometry) = boxed_green(&*source, source.levels().black, self.factor);
        let pyramid = AlignPyramid::build(
            PlaneRef::from_geometry(&data, geometry).context("invalid guide plane")?,
            &self.guide_config,
        )
        .context("guide is too small for the configured pyramid")?;
        let levels = source.levels();
        let guide = Guide {
            data,
            geometry,
            pyramid,
            ceiling: (levels.white - levels.black).max(1.0),
        };
        ensure!(guide.bytes() == bytes, "guide accounting mismatch");
        Ok(planes.insert(index, guide, bytes))
    }

    fn native(
        &self,
        index: usize,
        sources: &mut SourceCache,
        planes: &mut BoundedPlanes<NativePlane>,
    ) -> Result<Arc<NativePlane>> {
        if let Some(plane) = planes.get(index) {
            return Ok(plane);
        }
        let bytes = product(self.geometry.pixels(), 4)?;
        planes.reserve(bytes)?;
        let source = source(index, self.session, self.identities, sources)?;
        ensure!(
            source.geometry() == self.geometry,
            "source plane geometry changed during alignment"
        );
        let mut data = vec![0.0; self.geometry.pixels()];
        green_luma(&*source, source.levels().black, &mut data);
        Ok(planes.insert(
            index,
            NativePlane {
                data,
                geometry: self.geometry,
            },
            bytes,
        ))
    }
}

fn add_pair(
    pairs: &mut BTreeMap<(usize, usize), PairPurpose>,
    i: usize,
    j: usize,
    purpose: PairPurpose,
) {
    if i != j {
        pairs.entry((i.min(j), i.max(j))).or_insert(purpose);
    }
}

fn distributed(range: std::ops::Range<usize>, count: usize) -> Vec<usize> {
    let n = count.min(range.len());
    (0..n)
        .map(|i| range.start + i * (range.len() - 1) / (n - 1).max(1))
        .collect()
}

fn initial_pairs(
    session: &ResolvedSession,
    config: &SessionAlignConfig,
    reference_pass: usize,
) -> BTreeMap<(usize, usize), PairPurpose> {
    let mut pairs = BTreeMap::new();
    for pass in &session.passes {
        for i in pass.global_range.clone() {
            for &span in &config.intra_spans {
                if let Some(j) = i.checked_add(span).filter(|&j| j < pass.global_range.end) {
                    add_pair(&mut pairs, i, j, PairPurpose::IntraPass);
                }
            }
        }
    }
    let anchors = distributed(
        session.passes[reference_pass].global_range.clone(),
        config.cross_probes,
    );
    for (pass_index, pass) in session.passes.iter().enumerate() {
        if pass_index == reference_pass {
            continue;
        }
        for i in &anchors {
            for j in distributed(pass.global_range.clone(), config.cross_probes) {
                add_pair(&mut pairs, *i, j, PairPurpose::CrossProbe);
            }
        }
    }
    pairs
}

fn receipt(
    i: usize,
    j: usize,
    purpose: PairPurpose,
    stage: &str,
    result: &std::result::Result<StageFit, AlignFailure>,
    full: PlaneGeometry,
    factor: usize,
) -> (EdgeReceipt, Option<AlignEdge>) {
    let mut record = EdgeReceipt {
        i,
        j,
        purpose,
        stage: stage.into(),
        accepted: false,
        transform_bits: None,
        rms_plane_px: None,
        used: 0,
        attempted: 0,
        correlated: 0,
        peak_mean: None,
        lever_plane_px: None,
        refusal: None,
    };
    match result {
        Ok(fit) => {
            if let Some(t) = lift_box_decimated_similarity(fit.similarity(), full, full, factor) {
                let edge = AlignEdge {
                    i,
                    j,
                    t,
                    rms: fit.rms as f64 * factor as f64,
                    used: fit.used,
                    lever: fit.lever_rms as f64 * factor as f64,
                };
                record.accepted = true;
                record.transform_bits = Some([
                    t.a.re.to_bits(),
                    t.a.im.to_bits(),
                    t.b.re.to_bits(),
                    t.b.im.to_bits(),
                ]);
                record.rms_plane_px = Some(edge.rms);
                record.used = fit.used;
                record.attempted = fit.total;
                record.correlated = fit.raw_n;
                record.peak_mean = Some(fit.peak_mean);
                record.lever_plane_px = Some(edge.lever);
                (record, Some(edge))
            } else {
                record.refusal = Some("nonfinite or singular coordinate lift".into());
                (record, None)
            }
        }
        Err(error) => {
            record.refusal = Some(format!("{error:?}"));
            (record, None)
        }
    }
}

struct PairMeasurement {
    receipt: EdgeReceipt,
    edge: Option<AlignEdge>,
    /// Relative brightness over the overlap, from the accepted guide fit.
    photometry: Option<EdgePhotometry>,
}

/// Block-mean brightness ratio through an accepted guide fit (guide-centred).
fn guide_photometry(
    i: usize,
    j: usize,
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    a: &Guide,
    b: &Guide,
    result: &std::result::Result<StageFit, AlignFailure>,
) -> Option<EdgePhotometry> {
    let fit = result.as_ref().ok()?;
    let (log_ratio, spread, blocks) =
        frame_photometry::measure(reference, moving, fit.similarity(), a.ceiling, b.ceiling)?;
    Some(EdgePhotometry {
        i,
        j,
        log_ratio,
        spread,
        blocks,
    })
}

/// Seeds magnifying beyond this are measured with the more magnified frame as
/// the tile reference, so its tiles fall inside the other frame. Ordinary focus
/// breathing stays far below this, leaving those measurements unchanged.
const ORIENTATION_SWAP_SCALE: f64 = 1.25;
/// Wide-baseline pairs always tile the more magnified frame: their fields of
/// view differ by construction. Only pairs recovered by the wide-baseline
/// initializer use this; ordinary pairs keep [`ORIENTATION_SWAP_SCALE`].
const WIDE_ORIENTATION_SWAP_SCALE: f64 = 1.0;
const WIDE_STAGE_GUIDE: &str = "guide-wide";
/// Intra-pass guide pair measured from identity after the coarse ladder failed.
const IDENTITY_STAGE_GUIDE: &str = "guide-identity";

/// Direct fine refinement from `seed` (reference -> moving, centred). When the
/// seed magnifies strongly, measure moving -> reference and invert, so the
/// result keeps the caller's orientation. Tile statistics are then stated in
/// the moving frame's pixels.
fn refine_oriented(
    reference: PlaneRef<'_>,
    moving: PlaneRef<'_>,
    cfg: &AlignConfig,
    seed: Similarity,
    swap_above: f64,
) -> std::result::Result<StageFit, AlignFailure> {
    let swap = seed.scale() > swap_above;
    let (fixed, other, seed) = if swap {
        (
            moving,
            reference,
            seed.invert().ok_or(AlignFailure::InvalidSeed)?,
        )
    } else {
        (reference, moving, seed)
    };
    let spots = tile_grid(
        fixed,
        cfg.fine_tile,
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.margin,
    )
    .ok_or(AlignFailure::GridTooSmall)?;
    let mut fit = refine_pair_observed(fixed, other, &spots, cfg, seed, None)?;
    if swap {
        let inverse = fit.similarity().invert().ok_or(AlignFailure::InvalidSeed)?;
        fit.fit = inverse.to_params();
    }
    Ok(fit)
}

/// Re-measure explicit pairs at guide resolution from supplied seeds.
fn measure_guides_seeded(
    jobs: &[(usize, usize, PairPurpose, Similarity)],
    inputs: &PlaneInputs<'_>,
    sources: &mut SourceCache,
    planes: &mut BoundedPlanes<Guide>,
    workers: usize,
    pool: &rayon::ThreadPool,
) -> Result<Vec<PairMeasurement>> {
    let mut measured = Vec::with_capacity(jobs.len());
    for batch in jobs.chunks(workers.max(1)) {
        let mut loaded = Vec::with_capacity(batch.len());
        for &(i, j, purpose, seed) in batch {
            loaded.push((
                i,
                j,
                purpose,
                seed,
                inputs.guide(i, sources, planes)?,
                inputs.guide(j, sources, planes)?,
            ));
        }
        let mut results = pool.install(|| {
            loaded
                .par_iter()
                .map(|(i, j, purpose, seed, a, b)| {
                    let reference =
                        PlaneRef::from_geometry(&a.data, a.geometry).expect("constructed guide");
                    let moving =
                        PlaneRef::from_geometry(&b.data, b.geometry).expect("constructed guide");
                    let result = refine_oriented(
                        reference,
                        moving,
                        &inputs.pair_config(&inputs.guide_config, *i, *j),
                        *seed,
                        WIDE_ORIENTATION_SWAP_SCALE,
                    );
                    let (receipt, edge) = receipt(
                        *i,
                        *j,
                        *purpose,
                        WIDE_STAGE_GUIDE,
                        &result,
                        inputs.geometry,
                        inputs.factor,
                    );
                    let photometry = guide_photometry(*i, *j, reference, moving, a, b, &result);
                    PairMeasurement {
                        receipt,
                        edge,
                        photometry,
                    }
                })
                .collect::<Vec<_>>()
        });
        measured.append(&mut results);
    }
    Ok(measured)
}

/// For a pass with no accepted guide cross probe, propose global similarities
/// between representative anchor/pass frames and keep the first candidate that
/// a direct seeded guide refinement confirms. Returns the guide-centred seed
/// (anchor frame -> pass frame) and the audit record of every attempt.
#[allow(clippy::too_many_arguments)]
fn wide_baseline_seed(
    session: &ResolvedSession,
    config: &SessionAlignConfig,
    inputs: &PlaneInputs<'_>,
    sources: &mut SourceCache,
    planes: &mut BoundedPlanes<Guide>,
    reference_pass: usize,
    pass: usize,
    pool: &rayon::ThreadPool,
) -> Result<(Option<Similarity>, Vec<WideBaselineReport>)> {
    let anchor_range = session.passes[reference_pass].global_range.clone();
    let anchor = anchor_range.start + anchor_range.len() / 2;
    let range = session.passes[pass].global_range.clone();
    let count = config.wide_baseline_searches.min(range.len());
    let mut frames: Vec<usize> = (0..count)
        .map(|k| range.start + (2 * k + 1) * range.len() / (2 * count))
        .collect();
    // Search the middle of the pass first: it is the likeliest to share sharp
    // structure with the middle of the anchor.
    frames.sort_by_key(|&f| f.abs_diff(range.start + range.len() / 2));
    let search = GlobalSearchConfig::default();
    let mut reports = Vec::new();
    for frame in frames {
        let started = Instant::now();
        let a = inputs.guide(anchor, sources, planes)?;
        let b = inputs.guide(frame, sources, planes)?;
        let reference = PlaneRef::from_geometry(&a.data, a.geometry).expect("constructed guide");
        let moving = PlaneRef::from_geometry(&b.data, b.geometry).expect("constructed guide");
        let found = pool.install(|| global_similarity_candidates(reference, moving, &search));
        let mut candidates = Vec::new();
        let mut selected: Option<(Similarity, usize, f32)> = None;
        for candidate in &found {
            let result = refine_oriented(
                reference,
                moving,
                &inputs.pair_config(&inputs.guide_config, anchor, frame),
                candidate.transform,
                WIDE_ORIENTATION_SWAP_SCALE,
            );
            let mut record = WideBaselineCandidate {
                scale: candidate.transform.scale(),
                rotation_degrees: candidate.transform.rotation().to_degrees(),
                ncc: candidate.ncc,
                overlap_px: candidate.overlap,
                validated: false,
                used_tiles: 0,
                rms_guide_px: None,
                refusal: None,
            };
            match result {
                Ok(fit) => {
                    record.validated = true;
                    record.used_tiles = fit.used;
                    record.rms_guide_px = Some(fit.rms);
                    let better = selected.is_none_or(|(_, used, rms)| {
                        fit.used > used || (fit.used == used && fit.rms < rms)
                    });
                    if better {
                        selected = Some((fit.similarity(), fit.used, fit.rms));
                    }
                }
                Err(error) => record.refusal = Some(format!("{error:?}")),
            }
            candidates.push(record);
        }
        let seed = selected.map(|(seed, _, _)| seed);
        reports.push(WideBaselineReport {
            pass,
            anchor_frame: anchor,
            pass_frame: frame,
            elapsed_seconds: started.elapsed().as_secs_f64(),
            candidates,
            selected_seed_bits: seed.map(|t| {
                [
                    t.a.re.to_bits(),
                    t.a.im.to_bits(),
                    t.b.re.to_bits(),
                    t.b.im.to_bits(),
                ]
            }),
        });
        if seed.is_some() {
            return Ok((seed, reports));
        }
    }
    Ok((None, reports))
}

/// Orient a pass-level seed (anchor -> pass) for pair `(i, j)`.
fn oriented_seed(
    session: &ResolvedSession,
    reference_pass: usize,
    seeds: &BTreeMap<usize, Similarity>,
    i: usize,
    j: usize,
) -> Option<Similarity> {
    let (pi, pj) = (session.frames[i].pass_index, session.frames[j].pass_index);
    if pi == reference_pass {
        seeds.get(&pj).copied()
    } else if pj == reference_pass {
        seeds.get(&pi).and_then(|s| s.invert())
    } else {
        None
    }
}

fn measure_guides(
    pairs: &BTreeMap<(usize, usize), PairPurpose>,
    inputs: &PlaneInputs<'_>,
    sources: &mut SourceCache,
    planes: &mut BoundedPlanes<Guide>,
    workers: usize,
    pool: &rayon::ThreadPool,
) -> Result<Vec<PairMeasurement>> {
    let pairs: Vec<_> = pairs
        .iter()
        .map(|(&(i, j), &purpose)| (i, j, purpose))
        .collect();
    let mut measured = Vec::with_capacity(pairs.len());
    for batch in pairs.chunks(workers) {
        let mut jobs = Vec::with_capacity(batch.len());
        for &(i, j, purpose) in batch {
            jobs.push((
                i,
                j,
                purpose,
                inputs.guide(i, sources, planes)?,
                inputs.guide(j, sources, planes)?,
            ));
        }
        let mut results = pool.install(|| {
            jobs.par_iter()
                .map(|(i, j, purpose, a, b)| {
                    let reference =
                        PlaneRef::from_geometry(&a.data, a.geometry).expect("constructed guide");
                    let moving =
                        PlaneRef::from_geometry(&b.data, b.geometry).expect("constructed guide");
                    let cfg = &inputs.pair_config(&inputs.guide_config, *i, *j);
                    let mut identity_retry = false;
                    let result = match tile_grid(
                        reference,
                        cfg.fine_tile,
                        cfg.fine_grid.0,
                        cfg.fine_grid.1,
                        cfg.margin,
                    ) {
                        Some(spots) => {
                            let ladder = align_pair(
                                AlignFrame {
                                    plane: reference,
                                    pyramid: &a.pyramid,
                                },
                                AlignFrame {
                                    plane: moving,
                                    pyramid: &b.pyramid,
                                },
                                &spots,
                                cfg,
                            );
                            // The coarse ladder only brings the fine stage into
                            // capture range. Within one sweep identity already is,
                            // and a dark or sparse frame can starve the 24-tile
                            // coarse grid; retry the direct fine stage from it.
                            match ladder {
                                Err(AlignFailure::CoarseStageFailed { .. })
                                    if *purpose == PairPurpose::IntraPass =>
                                {
                                    identity_retry = true;
                                    refine_pair_observed(
                                        reference,
                                        moving,
                                        &spots,
                                        cfg,
                                        Similarity::IDENTITY,
                                        None,
                                    )
                                }
                                other => other,
                            }
                        }
                        None => Err(AlignFailure::GridTooSmall),
                    };
                    let (receipt, edge) = receipt(
                        *i,
                        *j,
                        *purpose,
                        if identity_retry { IDENTITY_STAGE_GUIDE } else { "guide" },
                        &result,
                        inputs.geometry,
                        inputs.factor,
                    );
                    let photometry = guide_photometry(*i, *j, reference, moving, a, b, &result);
                    PairMeasurement {
                        receipt,
                        edge,
                        photometry,
                    }
                })
                .collect::<Vec<_>>()
        });
        measured.append(&mut results);
    }
    Ok(measured)
}

fn median(mut values: Vec<f64>) -> Option<f64> {
    values.retain(|v| v.is_finite());
    if values.is_empty() {
        return None;
    }
    values.sort_by(f64::total_cmp);
    let mid = values.len() / 2;
    Some(if values.len() % 2 == 1 {
        values[mid]
    } else {
        0.5 * (values[mid - 1] + values[mid])
    })
}

fn nearest(values: &[Option<f64>], range: std::ops::Range<usize>, target: f64) -> Option<usize> {
    range
        .filter_map(|i| values[i].map(|v| (i, (v - target).abs())))
        .min_by(|a, b| a.1.total_cmp(&b.1).then(a.0.cmp(&b.0)))
        .map(|(i, _)| i)
}

/// Local-scale gauges and cross-probe offsets are used only to propose direct
/// measurements. None of these composed hints enters the delivered placement.
fn cross_candidates(
    session: &ResolvedSession,
    config: &SessionAlignConfig,
    edges: &[AlignEdge],
    geometry: PlaneGeometry,
    reference_pass: usize,
) -> Result<BTreeMap<(usize, usize), PairPurpose>> {
    let mut scales = vec![None; session.len()];
    for pass in &session.passes {
        let start = pass.global_range.start;
        let local: Vec<_> = edges
            .iter()
            .filter(|e| pass.global_range.contains(&e.i) && pass.global_range.contains(&e.j))
            .map(|e| AlignEdge {
                i: e.i - start,
                j: e.j - start,
                ..*e
            })
            .collect();
        let n = pass.global_range.len();
        let placement = solve_global_in_tracks(
            &local,
            n,
            &config.solver(geometry),
            n / 2,
            &[(0..n).collect()],
        )?;
        for (i, pose) in placement.iter().enumerate() {
            scales[start + i] = pose.map(|p| p.a.abs().ln()).filter(|v| v.is_finite());
        }
    }
    let anchor = &session.passes[reference_pass].global_range;
    for (pass_index, pass) in session.passes.iter().enumerate() {
        if pass_index == reference_pass {
            continue;
        }
        let offsets: Vec<_> = edges
            .iter()
            .filter_map(|e| {
                let si = scales[e.i]?;
                let sj = scales[e.j]?;
                if anchor.contains(&e.i) && pass.global_range.contains(&e.j) {
                    Some(e.t.a.abs().ln() + si - sj)
                } else if anchor.contains(&e.j) && pass.global_range.contains(&e.i) {
                    Some(-e.t.a.abs().ln() + sj - si)
                } else {
                    None
                }
            })
            .collect();
        if let Some(offset) = median(offsets) {
            for i in pass.global_range.clone() {
                scales[i] = scales[i].map(|v| v + offset);
            }
        } else {
            for i in pass.global_range.clone() {
                scales[i] = None;
            }
        }
    }
    let mut pairs = BTreeMap::new();
    for (pass_index, pass) in session.passes.iter().enumerate() {
        if pass_index == reference_pass {
            continue;
        }
        for (a, b) in [
            (anchor.clone(), pass.global_range.clone()),
            (pass.global_range.clone(), anchor.clone()),
        ] {
            for i in a {
                let Some(value) = scales[i] else {
                    continue;
                };
                let Some(j) = nearest(&scales, b.clone(), value) else {
                    continue;
                };
                let lower = j.saturating_sub(config.cross_neighbor_radius).max(b.start);
                let upper = j
                    .saturating_add(config.cross_neighbor_radius)
                    .min(b.end - 1);
                for neighbor in lower..=upper {
                    add_pair(&mut pairs, i, neighbor, PairPurpose::CrossCandidate);
                }
            }
        }
    }
    Ok(pairs)
}

fn focus_candidates(
    session: &ResolvedSession,
    poses: &[Option<Similarity>],
    reference_pass: usize,
    fraction: f64,
) -> Vec<FocusPairCandidate> {
    let scales: Vec<_> = poses
        .iter()
        .map(|pose| pose.map(|p| p.a.abs().ln()).filter(|v| v.is_finite()))
        .collect();
    let steps: Vec<_> = session
        .passes
        .iter()
        .map(|pass| {
            median(
                pass.global_range
                    .clone()
                    .skip(1)
                    .filter_map(|i| Some((scales[i]? - scales[i - 1]?).abs()))
                    .collect(),
            )
            .filter(|&v| v > 1e-9)
        })
        .collect();
    let anchor = session.passes[reference_pass].global_range.clone();
    let mut result = Vec::new();
    for (pass_index, pass) in session.passes.iter().enumerate() {
        if pass_index == reference_pass {
            continue;
        }
        let allowed = steps[reference_pass]
            .zip(steps[pass_index])
            .map(|(a, b)| fraction * a.min(b));
        let mut pairs = BTreeSet::new();
        for (a, b) in [
            (anchor.clone(), pass.global_range.clone()),
            (pass.global_range.clone(), anchor.clone()),
        ] {
            for i in a {
                if let Some(j) = scales[i].and_then(|value| nearest(&scales, b.clone(), value)) {
                    pairs.insert((i.min(j), i.max(j)));
                }
            }
        }
        for (i, j) in pairs {
            let (a, b) = if anchor.contains(&i) { (i, j) } else { (j, i) };
            let av = scales[a].expect("candidate scale");
            let bv = scales[b].expect("candidate scale");
            let mutual = nearest(&scales, pass.global_range.clone(), av) == Some(b)
                && nearest(&scales, anchor.clone(), bv) == Some(a);
            let gap = (av - bv).abs();
            result.push(FocusPairCandidate {
                i,
                j,
                mutual_nearest: mutual,
                log_scale_gap: gap,
                allowed_log_scale_gap: allowed,
                candidate_same_focus: mutual && allowed.is_some_and(|bar| gap <= bar),
                validated_same_focus: false,
            });
        }
    }
    result.sort_by_key(|p| (p.i, p.j));
    result
}

fn measure_native(
    seeds: &[PairMeasurement],
    inputs: &PlaneInputs<'_>,
    sources: &mut SourceCache,
    planes: &mut BoundedPlanes<NativePlane>,
    config: &SessionAlignConfig,
    workers: usize,
    pool: &rayon::ThreadPool,
) -> Result<Vec<PairMeasurement>> {
    let pairs: Vec<_> = seeds
        .iter()
        .filter_map(|measurement| {
            measurement.edge.map(|edge| {
                let wide = measurement.receipt.stage == WIDE_STAGE_GUIDE;
                (edge, measurement.receipt.purpose, wide)
            })
        })
        .collect();
    let mut measured = Vec::with_capacity(pairs.len());
    let native_config = config.estimator(false);
    let refine = |job: &(AlignEdge, PairPurpose, bool, Arc<NativePlane>, Arc<NativePlane>)| {
        let (edge, purpose, wide, a, b) = job;
        let reference = PlaneRef::from_geometry(&a.data, a.geometry)
            .expect("constructed native plane");
        let moving = PlaneRef::from_geometry(&b.data, b.geometry)
            .expect("constructed native plane");
        let cfg = inputs.pair_config(&native_config, edge.i, edge.j);
        let swap_above = if *wide {
            WIDE_ORIENTATION_SWAP_SCALE
        } else {
            ORIENTATION_SWAP_SCALE
        };
        let result = if *wide || edge.t.scale() > ORIENTATION_SWAP_SCALE {
            refine_oriented(reference, moving, &cfg, edge.t, swap_above)
        } else {
            match tile_grid(
                reference,
                cfg.fine_tile,
                cfg.fine_grid.0,
                cfg.fine_grid.1,
                cfg.margin,
            ) {
                Some(spots) => {
                    refine_pair_observed(reference, moving, &spots, &cfg, edge.t, None)
                }
                None => Err(AlignFailure::GridTooSmall),
            }
        };
        let (receipt, edge) = receipt(
            edge.i,
            edge.j,
            *purpose,
            if *wide { "native-wide" } else { "native" },
            &result,
            inputs.geometry,
            1,
        );
        PairMeasurement {
            receipt,
            edge,
            photometry: None,
        }
    };
    // When the plane budget allows, the next batch's planes are loaded
    // (serially: the caches need exclusive access) while the current batch
    // refines, and batches are twice the workers. Each pair's refinement is a
    // pure function of its two planes and results keep pair order, so the
    // measurements equal those of the one-batch-at-a-time loop. Two batches
    // in flight pin up to four planes per pair slot, so overlap needs a budget
    // of four planes per worker (eight for double batches); a tighter budget
    // keeps the original load-then-refine loop.
    let plane_bytes = inputs.geometry.pixels().saturating_mul(4).max(1);
    let capacity = planes.budget / plane_bytes;
    let workers = workers.max(1);
    let pipelined = capacity >= workers.saturating_mul(4);
    let batch_size = if capacity >= workers.saturating_mul(8) {
        workers.saturating_mul(2)
    } else {
        workers
    };
    let batches: Vec<_> = pairs.chunks(batch_size).collect();
    let load = |batch: &[(AlignEdge, PairPurpose, bool)],
                sources: &mut SourceCache,
                planes: &mut BoundedPlanes<NativePlane>|
     -> Result<Vec<_>> {
        let mut jobs = Vec::with_capacity(batch.len());
        for &(edge, purpose, wide) in batch {
            jobs.push((
                edge,
                purpose,
                wide,
                inputs.native(edge.i, sources, planes)?,
                inputs.native(edge.j, sources, planes)?,
            ));
        }
        Ok(jobs)
    };
    let started = Instant::now();
    let mut next = match batches.first() {
        Some(batch) if pipelined => load(batch, sources, planes)?,
        _ => Vec::new(),
    };
    for index in 0..batches.len() {
        let jobs = if pipelined {
            std::mem::take(&mut next)
        } else {
            load(batches[index], sources, planes)?
        };
        let following = batches.get(index + 1).copied().filter(|_| pipelined);
        let (mut results, loaded) = pool.install(|| {
            rayon::join(
                || jobs.par_iter().map(refine).collect::<Vec<_>>(),
                || following.map(|batch| load(batch, sources, planes)).transpose(),
            )
        });
        measured.append(&mut results);
        next = loaded?.unwrap_or_default();
    }
    eprintln!(
        "session alignment: native refinement {:.1} s",
        started.elapsed().as_secs_f64()
    );
    Ok(measured)
}

/// Fit all pass placements in a shared native-plane gauge. This never writes a
/// source-directory sidecar and never invokes the ordinary single-stack path.
pub fn align_session(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    cache: &mut SourceCache,
    config: &SessionAlignConfig,
    resampler: Resampler,
) -> Result<SessionAlignment> {
    let started = Instant::now();
    let initial_cache_stats = cache.stats();
    let binding = binding(session, identities, config, resampler)?;
    let (reference_pass, reference_frame) = reference(session);
    let metadata = session.read_metadata()?;
    let mut decoded_frame_bytes = 0usize;
    let mut upper_geometry = PlaneGeometry {
        width: 0,
        height: 0,
    };
    let mut maximum_active_bytes = 0usize;
    for item in &metadata {
        let [width, height] = item.stored_dimensions.with_context(|| format!("session alignment requires stored dimensions before allocating decode workspace: {}", item.path.display()))?;
        let (width, height) = (width as usize, height as usize);
        ensure!(width > 0 && height > 0, "source has zero stored dimensions");
        // Allow 256 extra columns and rows in the decoder's padded allocation.
        // Four such u16 buffers cover the serialized decode and cache-write path.
        decoded_frame_bytes = decoded_frame_bytes.max(product(
            product(
                width.checked_add(256).context("stored width overflow")?,
                height.checked_add(256).context("stored height overflow")?,
            )?,
            2,
        )?);
        maximum_active_bytes = maximum_active_bytes.max(product(product(width, height)?, 2)?);
        upper_geometry.width = upper_geometry.width.max(width / 2);
        upper_geometry.height = upper_geometry.height.max(height / 2);
    }
    ensure!(
        cache.budget_bytes() >= maximum_active_bytes,
        "source cache budget is smaller than one header-sized active CFA frame (need at least {maximum_active_bytes} bytes)"
    );
    let mut memory = memory_plan(
        config,
        session.len(),
        session.passes.len(),
        cache.budget_bytes(),
        decoded_frame_bytes,
        upper_geometry,
    )?;
    let first = source(0, session, identities, cache)?;
    let geometry = first.geometry();
    let source_geometry = first.geometry;
    let camera = first.camera().to_owned();
    ensure!(
        geometry.width > 0 && geometry.height > 0,
        "source plane is empty"
    );
    drop(first);
    let factor = geometry
        .width
        .max(geometry.height)
        .div_ceil(config.guide_max_side)
        .max(1);
    let mut inputs = PlaneInputs {
        session,
        identities,
        geometry,
        factor,
        guide_config: config.estimator(true),
        contrast_scale: Vec::new(),
    };
    let mut levels = Vec::with_capacity(session.len());
    let mut guides = BoundedPlanes::new(memory.guide_cache_reserved_bytes);
    eprintln!(
        "session alignment: preparing {} sources; reserved {:.2} GiB of {:.2} GiB, {} native pair workers",
        session.len(),
        memory.planned_total_bytes as f64 / (1u64 << 30) as f64,
        config.memory_limit_bytes as f64 / (1u64 << 30) as f64,
        memory.native_workers
    );
    for (i, item) in metadata.iter().enumerate() {
        let cached = source(i, session, identities, cache)?;
        let [width, height] = item.stored_dimensions.expect("preflight dimensions");
        ensure!(
            cached.geometry.width <= width as usize
                && cached.geometry.height <= height as usize
                && cached
                    .geometry
                    .full_frame_bytes()
                    .is_some_and(|bytes| bytes <= decoded_frame_bytes),
            "decoded source exceeds its header-derived allocation reservation: {}",
            item.path.display()
        );
        ensure!(
            cached.geometry == source_geometry && cached.camera() == camera,
            "session sources must share camera model and exact decoded sensor geometry: {}",
            item.path.display()
        );
        drop(cached);
        let guide = inputs.guide(i, cache, &mut guides)?;
        levels.push(signal_level(&guide.data));
        drop(guide);
        if (i + 1) % 100 == 0 {
            eprintln!(
                "session alignment: prepared {}/{} original CFA sources",
                i + 1,
                session.len()
            );
        }
    }
    let pass_contrast_scale = contrast_scales(session, &levels);
    inputs.contrast_scale = session
        .frames
        .iter()
        .map(|frame| pass_contrast_scale[frame.pass_index])
        .collect();
    for (pass, scale) in pass_contrast_scale.iter().enumerate() {
        if *scale < 1.0 {
            eprintln!(
                "session alignment: pass '{}' is darker than the brightest pass; contrast floor x{scale:.3}",
                session.passes[pass].name
            );
        }
    }
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(memory.native_workers.max(memory.guide_workers))
        .build()?;
    let initial = initial_pairs(session, config, reference_pass);
    eprintln!("session alignment: measuring {} guide pairs", initial.len());
    let mut guide_measurements = measure_guides(
        &initial,
        &inputs,
        cache,
        &mut guides,
        memory.guide_workers,
        &pool,
    )?;
    // Wide-baseline recovery: a pass whose every probe against the anchor was
    // refused gets globally searched seeds, confirmed by direct refinement.
    let mut wide_seeds = BTreeMap::new();
    let mut wide_reports = Vec::new();
    if config.wide_baseline_searches > 0 {
        for pass in 0..session.passes.len() {
            if pass == reference_pass {
                continue;
            }
            let spans = |i: usize, j: usize| {
                let (pi, pj) = (session.frames[i].pass_index, session.frames[j].pass_index);
                (pi, pj) == (reference_pass, pass) || (pi, pj) == (pass, reference_pass)
            };
            let joined = guide_measurements
                .iter()
                .any(|m| m.edge.is_some() && spans(m.receipt.i, m.receipt.j));
            if joined {
                continue;
            }
            eprintln!(
                "session alignment: pass '{}' has no accepted cross probe; searching wide-baseline seeds",
                session.passes[pass].name
            );
            let (seed, mut reports) = wide_baseline_seed(
                session,
                config,
                &inputs,
                cache,
                &mut guides,
                reference_pass,
                pass,
                &pool,
            )?;
            wide_reports.append(&mut reports);
            match seed {
                Some(seed) => {
                    eprintln!(
                        "session alignment: pass '{}' wide-baseline seed scale {:.3}, rotation {:.2} deg",
                        session.passes[pass].name,
                        seed.scale(),
                        seed.rotation().to_degrees()
                    );
                    wide_seeds.insert(pass, seed);
                }
                None => eprintln!(
                    "session alignment: pass '{}' has no confirmed wide-baseline seed",
                    session.passes[pass].name
                ),
            }
        }
    }
    let reseed =
        |measurements: &[PairMeasurement]| -> Vec<(usize, usize, PairPurpose, Similarity)> {
            measurements
                .iter()
                .filter(|m| m.edge.is_none())
                .filter_map(|m| {
                    oriented_seed(
                        session,
                        reference_pass,
                        &wide_seeds,
                        m.receipt.i,
                        m.receipt.j,
                    )
                    .map(|seed| (m.receipt.i, m.receipt.j, m.receipt.purpose, seed))
                })
                .collect()
        };
    if !wide_seeds.is_empty() {
        let jobs = reseed(&guide_measurements);
        eprintln!(
            "session alignment: re-measuring {} refused cross probes from wide-baseline seeds",
            jobs.len()
        );
        guide_measurements.extend(measure_guides_seeded(
            &jobs,
            &inputs,
            cache,
            &mut guides,
            memory.guide_workers,
            &pool,
        )?);
    }
    let initial_edges: Vec<_> = guide_measurements.iter().filter_map(|m| m.edge).collect();
    let mut candidates =
        cross_candidates(session, config, &initial_edges, geometry, reference_pass)?;
    candidates.retain(|pair, _| !initial.contains_key(pair));
    eprintln!(
        "session alignment: measuring {} additional cross-pass guide candidates",
        candidates.len()
    );
    let candidate_measurements = measure_guides(
        &candidates,
        &inputs,
        cache,
        &mut guides,
        memory.guide_workers,
        &pool,
    )?;
    let candidate_jobs = reseed(&candidate_measurements);
    guide_measurements.extend(candidate_measurements);
    if !candidate_jobs.is_empty() {
        eprintln!(
            "session alignment: re-measuring {} refused cross candidates from wide-baseline seeds",
            candidate_jobs.len()
        );
        guide_measurements.extend(measure_guides_seeded(
            &candidate_jobs,
            &inputs,
            cache,
            &mut guides,
            memory.guide_workers,
            &pool,
        )?);
    }
    guide_measurements.sort_by_key(|m| (m.receipt.i, m.receipt.j));
    memory.peak_guide_bytes = guides.peak;
    // Guide residency is no longer needed; only compact accepted seed records live.
    drop(guides);
    let mut native = BoundedPlanes::new(memory.native_green_reserved_bytes);
    eprintln!(
        "session alignment: refining {} accepted seeds directly at native resolution",
        guide_measurements
            .iter()
            .filter(|m| m.edge.is_some())
            .count()
    );
    let native_measurements = measure_native(
        &guide_measurements,
        &inputs,
        cache,
        &mut native,
        config,
        memory.native_workers,
        &pool,
    )?;
    memory.peak_native_green_bytes = native.peak;
    drop(native);
    let edges: Vec<_> = native_measurements.iter().filter_map(|m| m.edge).collect();
    let tracks: Vec<Vec<usize>> = session
        .passes
        .iter()
        .map(|pass| pass.global_range.clone().collect())
        .collect();
    let placement = solve_global_in_tracks(
        &edges,
        session.len(),
        &config.solver(geometry),
        reference_frame,
        &tracks,
    )?;
    let from_reference = placement[reference_frame]
        .and_then(Similarity::invert)
        .context("reference frame has no invertible measured placement")?;
    let poses: Vec<_> = placement
        .iter()
        .map(|pose| pose.map(|p| from_reference.then(p)))
        .collect();
    let pair_candidates =
        focus_candidates(session, &poses, reference_pass, config.focus_step_fraction);
    // Per-frame photometry over geometry-confirmed overlaps only.
    let confirmed: BTreeSet<(usize, usize)> = edges.iter().map(|e| (e.i, e.j)).collect();
    let photometric_edges: Vec<EdgePhotometry> = guide_measurements
        .iter()
        .filter_map(|m| m.photometry)
        .filter(|p| {
            confirmed.contains(&(p.i, p.j)) && poses[p.i].is_some() && poses[p.j].is_some()
        })
        .collect();
    let photometry = frame_photometry::solve(session.len(), reference_frame, &photometric_edges);
    eprintln!(
        "session alignment: per-frame photometry from {} overlaps, residual {:.4} ln",
        photometry.edges_used, photometry.residual_rms
    );
    // Direct post-placement geometry check of each non-reference pass: the
    // reference frame against the pass's focus-nearest placed frame.
    let mut check_planes = BoundedPlanes::new(memory.guide_cache_reserved_bytes.max(1 << 28));
    let mut geometric_residuals = vec![None; session.passes.len()];
    for (index, pass) in session.passes.iter().enumerate() {
        if index == reference_pass {
            continue;
        }
        let Some(frame) = pass
            .global_range
            .clone()
            .filter_map(|k| poses[k].map(|p| (k, p.scale().ln().abs())))
            .min_by(|a, b| a.1.total_cmp(&b.1))
            .map(|(k, _)| k)
        else {
            continue;
        };
        let pose = poses[frame].expect("placed frame");
        let a = inputs.guide(reference_frame, cache, &mut check_planes)?;
        let b = inputs.guide(frame, cache, &mut check_planes)?;
        let reference = PlaneRef::from_geometry(&a.data, a.geometry).expect("constructed guide");
        let moving = PlaneRef::from_geometry(&b.data, b.geometry).expect("constructed guide");
        // Full-plane centred placement expressed on the guide lattice.
        let t = Similarity {
            a: pose.a,
            b: pose.b.scale(1.0 / inputs.factor as f64),
        };
        geometric_residuals[index] = crate::session_geometry_check::measure(reference, moving, t);
        drop((a, b));
    }
    drop(check_planes);
    let stats = graph_stats(&edges, session.len());
    let placed = poses.iter().filter(|pose| pose.is_some()).count();
    let anchor_edges = edges
        .iter()
        .filter(|edge| poses[edge.i].is_some() && poses[edge.j].is_some())
        .count();
    let anchor_component_cycle_rank = anchor_edges.saturating_sub(placed.saturating_sub(1));
    let passes = session
        .passes
        .iter()
        .enumerate()
        .map(|(index, pass)| {
            let placed = pass
                .global_range
                .clone()
                .filter(|&i| poses[i].is_some())
                .count();
            let intra_edges: Vec<_> = edges
                .iter()
                .filter(|edge| {
                    pass.global_range.contains(&edge.i) && pass.global_range.contains(&edge.j)
                })
                .map(|edge| AlignEdge {
                    i: edge.i - pass.global_range.start,
                    j: edge.j - pass.global_range.start,
                    ..*edge
                })
                .collect();
            let intra_stats = graph_stats(&intra_edges, pass.global_range.len());
            let cross_edges: Vec<_> = edges
                .iter()
                .filter(|edge| {
                    pass.global_range.contains(&edge.i) != pass.global_range.contains(&edge.j)
                })
                .collect();
            let cross_support_ratio = if index == reference_pass {
                None
            } else {
                median_usize(cross_edges.iter().map(|e| e.used).collect())
                    .zip(median_usize(intra_edges.iter().map(|e| e.used).collect()))
                    .filter(|&(_, intra)| intra > 0.0)
                    .map(|(cross, intra)| cross / intra)
            };
            let scale = |range: std::ops::Range<usize>| {
                median(range.filter_map(|i| poses[i].map(|p| p.scale())).collect())
            };
            let relative_scale = scale(pass.global_range.clone())
                .zip(scale(session.passes[reference_pass].global_range.clone()))
                .map(|(s, anchor)| s / anchor);
            let wide_baseline = wide_seeds.contains_key(&index);
            let anchor_range = &session.passes[reference_pass].global_range;
            let cross_photometry: Vec<&EdgePhotometry> = if index == reference_pass {
                Vec::new()
            } else {
                photometric_edges
                    .iter()
                    .filter(|p| {
                        (pass.global_range.contains(&p.i) && anchor_range.contains(&p.j))
                            || (pass.global_range.contains(&p.j) && anchor_range.contains(&p.i))
                    })
                    .collect()
            };
            let cross_photometric_spread =
                median(cross_photometry.iter().map(|p| p.spread).collect());
            let cross_photometric_residual = median(
                cross_photometry
                    .iter()
                    .filter_map(|p| {
                        Some(
                            (photometry.log_brightness[p.j]? - photometry.log_brightness[p.i]?
                                - p.log_ratio)
                                .abs(),
                        )
                    })
                    .collect(),
            );
            let brightness: Vec<f64> = pass
                .global_range
                .clone()
                .filter_map(|k| photometry.log_brightness[k])
                .collect();
            let log_brightness_range = (!brightness.is_empty()).then(|| {
                [
                    brightness.iter().copied().fold(f64::INFINITY, f64::min),
                    brightness.iter().copied().fold(f64::NEG_INFINITY, f64::max),
                ]
            });
            PassAlignmentReport {
                pass_index: index,
                name: pass.name.clone(),
                frames: pass.global_range.len(),
                placed,
                refused: pass.global_range.len() - placed,
                measured_intra_edges: intra_edges.len(),
                measured_cross_edges: cross_edges.len(),
                intra_components: intra_stats.components,
                intra_cycle_rank: intra_stats.cycle_rank,
                wide_baseline,
                cross_support_ratio,
                relative_scale,
                geometry_consistent: !wide_baseline
                    || match geometric_residuals[index] {
                        Some(residual) => residual.median <= WIDE_RESIDUAL_GUIDE_PX,
                        None => cross_support_ratio.is_some_and(|r| r >= WIDE_SUPPORT_RATIO),
                    },
                geometric_residual: geometric_residuals[index],
                contrast_scale: pass_contrast_scale[index],
                cross_photometric_spread,
                cross_photometric_residual,
                log_brightness_range,
            }
        })
        .collect();
    let mut receipts: Vec<_> = guide_measurements
        .into_iter()
        .map(|m| m.receipt)
        .chain(native_measurements.into_iter().map(|m| m.receipt))
        .collect();
    receipts.sort_by(|a, b| (a.i, a.j, &a.stage).cmp(&(b.i, b.j, &b.stage)));
    let cache_stats = cache.stats();
    let report = SessionAlignmentReport {
        generation: GENERATION.into(),
        binding_sha256: binding_digest(&binding)?,
        primary_pass: session.primary_pass_index(),
        reference_pass,
        reference_frame,
        geometry_plane_pixels: [geometry.width, geometry.height],
        sensor_pixels_per_plane_pixel: 2,
        guide_factor: factor,
        frames: session.len(),
        measured_edges: edges.len(),
        components: stats.components,
        cycle_rank: stats.cycle_rank,
        anchor_component_cycle_rank,
        passes,
        edges: receipts,
        focus_candidates: pair_candidates.clone(),
        memory,
        source_cache_peak_bytes: cache_stats.peak_resident_cfa_bytes,
        source_decodes: cache_stats.decodes - initial_cache_stats.decodes,
        source_disk_hits: cache_stats.disk_hits - initial_cache_stats.disk_hits,
        elapsed_seconds: started.elapsed().as_secs_f64(),
        wide_baseline: wide_reports,
        frame_photometry: Some(photometry),
        photometric_edges,
    };
    let map = WarpMap::new(Provenance { stack: StackIdentity::from_paths("multi-stack session", &session.paths())?, strategy: GENERATION.into(), heldout_px: None, cycle_floor_px: None, reference: reference_frame, note: "Direct native-green pair measurements; explicit per-pass tracks; common reference gauge. Geometry focus candidates remain unvalidated. Camera model/decoded geometry checked; physical body identity is not established.".into() }, geometry, resampler, poses.into_iter().map(|pose| pose.map_or_else(|| FrameWarp::Refused("outside reference's measured edge component".into()), FrameWarp::Placed)).collect());
    eprintln!(
        "session alignment: {placed}/{} placed, {} native edges, {} components, {} anchor-component cycles",
        session.len(),
        edges.len(),
        stats.components,
        anchor_component_cycle_rank
    );
    Ok(SessionAlignment {
        map,
        report,
        pair_candidates,
        binding,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session_input::PassSpec;
    use std::path::PathBuf;
    use std::sync::Barrier;
    use strehl_core::align::{Cx, SimilarityParams, downsample};
    use strehl_core::noise::Levels;
    use strehl_raw::{Frame, Region};

    struct Fixture {
        root: PathBuf,
        session: ResolvedSession,
        identities: Vec<SourceIdentity>,
    }
    impl Fixture {
        fn new(counts: &[usize]) -> Self {
            let root = std::env::temp_dir().join(format!(
                "strehl-session-align-{}-{}",
                std::process::id(),
                NEXT_TEMP.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&root).unwrap();
            let mut passes = Vec::new();
            for (pass, &count) in counts.iter().enumerate() {
                let directory = root.join(format!("pass-{pass}"));
                fs::create_dir(&directory).unwrap();
                for i in 0..count {
                    fs::write(
                        directory.join(format!("{i:03}.ARW")),
                        format!("distinct original test source {pass}/{i}"),
                    )
                    .unwrap();
                }
                passes.push(PassSpec {
                    name: format!("pass-{pass}"),
                    directories: vec![directory],
                });
            }
            let session = SessionSpec {
                passes,
                ..Default::default()
            }
            .resolve_from(&root)
            .unwrap();
            let identities = session.hash_sources(true).unwrap();
            Self {
                root,
                session,
                identities,
            }
        }
        fn frame(
            &self,
            index: usize,
            geometry: PlaneGeometry,
            pose: Similarity,
            flat: bool,
        ) -> Frame {
            let width = 2 * geometry.width;
            let height = 2 * geometry.height;
            let stride = width + 6;
            let mut data = vec![65535; stride * (height + 4)];
            let inverse = pose.invert().unwrap();
            for y in 0..height {
                for x in 0..width {
                    let (sx, sy) = inverse.apply_at(
                        (x / 2) as f64,
                        (y / 2) as f64,
                        geometry.width as f64 * 0.5,
                        geometry.height as f64 * 0.5,
                    );
                    let value = if flat {
                        500.0
                    } else {
                        1000.0
                            + 160.0 * (0.043 * sx + 0.019 * sy).sin()
                            + 150.0 * (0.029 * sx - 0.061 * sy).cos()
                            + 91.0 * (0.173 * sx + 0.079 * sy).sin()
                            + 73.0 * (0.097 * sx - 0.231 * sy).cos()
                            + 48.0 * (0.307 * sx + 0.137 * sy).sin()
                            + 31.0 * (0.053 * sx - 0.331 * sy).cos()
                    };
                    data[(y + 2) * stride + x + 2] = (64.0 + value).round() as u16;
                }
            }
            Frame {
                data,
                stride,
                buffer_height: height + 4,
                active: Region {
                    x: 2,
                    y: 2,
                    width,
                    height,
                },
                levels: Levels {
                    black: 64.0,
                    white: 4095.0,
                },
                iso: Some(100.0),
                wb_coeffs: [2.0, 1.0, 1.5, f32::NAN],
                xyz_to_cam_rgbe: [[0.0; 3]; 4],
                color_matrices: vec![],
                camera: "analytic-fixture".into(),
                path: self.identities[index].path.clone(),
            }
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.root);
        }
    }

    fn geometry() -> PlaneGeometry {
        PlaneGeometry {
            width: 512,
            height: 384,
        }
    }

    /// Diagnostic only: `STREHL_PAIR_TRACE_DIR` holds two real ARWs (copies).
    /// Traces the guide estimator's termination at several contrast floors.
    #[test]
    #[ignore = "requires private RAW copies"]
    fn session_align_trace_real_guide_pair() {
        let Some(dir) = std::env::var_os("STREHL_PAIR_TRACE_DIR") else {
            return;
        };
        let dir = PathBuf::from(dir);
        let session = SessionSpec {
            passes: vec![PassSpec {
                name: "pair".into(),
                directories: vec![dir.clone()],
            }],
            ..Default::default()
        }
        .resolve_from(&dir)
        .unwrap();
        let identities = session.hash_sources(true).unwrap();
        let cache_dir = std::env::temp_dir().join(format!("strehl-pair-trace-{}", std::process::id()));
        let mut cache = SourceCache::new(&cache_dir, &session, 2 << 30).unwrap();
        let config = SessionAlignConfig::default();
        let first = source(0, &session, &identities, &mut cache).unwrap();
        let geometry = first.geometry();
        drop(first);
        let factor = geometry.width.max(geometry.height).div_ceil(config.guide_max_side);
        let inputs = PlaneInputs {
            session: &session,
            identities: &identities,
            geometry,
            factor,
            guide_config: config.estimator(true),
            contrast_scale: Vec::new(),
        };
        let mut planes = BoundedPlanes::new(1 << 30);
        let a = inputs.guide(0, &mut cache, &mut planes).unwrap();
        let b = inputs.guide(1, &mut cache, &mut planes).unwrap();
        eprintln!("levels {} {}", signal_level(&a.data), signal_level(&b.data));
        for scale in [1.0f32, 0.1, 0.01] {
            let mut cfg = config.estimator(true);
            cfg.min_contrast *= scale;
            let reference = PlaneRef::from_geometry(&a.data, a.geometry).unwrap();
            let moving = PlaneRef::from_geometry(&b.data, b.geometry).unwrap();
            let spots =
                tile_grid(reference, cfg.fine_tile, cfg.fine_grid.0, cfg.fine_grid.1, cfg.margin)
                    .unwrap();
            let mut seen = None;
            let mut observe = |t: &strehl_core::align::PairTrace| {
                seen = Some(format!("{:?}", t.termination));
            };
            let result = strehl_core::align::align_pair_observed(
                AlignFrame { plane: reference, pyramid: &a.pyramid },
                AlignFrame { plane: moving, pyramid: &b.pyramid },
                &spots,
                &cfg,
                Some(&mut observe),
            );
            eprintln!(
                "contrast x{scale}: {} -> {:?}",
                seen.unwrap_or_default(),
                result.map(|f| (f.used, f.rms, f.rejected))
            );
        }
    }

    #[test]
    fn session_align_contrast_floor_scales_only_substantially_darker_passes() {
        let fixture = Fixture::new(&[2, 2, 2]);
        // Pass levels 1000, 900 (within the onset band) and 400.
        let levels = [1000.0, 1000.0, 900.0, 900.0, 400.0, 400.0];
        let scales = contrast_scales(&fixture.session, &levels);
        assert_eq!(scales[0], 1.0);
        assert_eq!(scales[1], 1.0, "a 10% darker pass keeps the exact floor");
        assert!((scales[2] - 0.16).abs() < 1e-6);
        // Equal levels are untouched; a degenerate session does not divide by zero.
        assert_eq!(contrast_scales(&fixture.session, &[5.0; 6]), vec![1.0; 3]);
        assert_eq!(contrast_scales(&fixture.session, &[0.0; 6]), vec![1.0; 3]);
        assert!((signal_level(&(0..1000).map(|v| v as f32).collect::<Vec<_>>()) - 987.0).abs() < 10.0);
    }

    #[test]
    fn session_align_box_guides_match_green_then_core_reduce_including_clamps_and_crop() {
        let fixture = Fixture::new(&[1]);
        let geometry = PlaneGeometry {
            width: 17,
            height: 13,
        };
        let mut frame = fixture.frame(0, geometry, Similarity::IDENTITY, false);
        for y in 0..frame.active.height {
            for x in 0..frame.active.width {
                frame.data[(y + 2) * frame.stride + x + 2] = ((71 * y + 29 * x) % 131) as u16;
            }
        }
        let mut native = vec![0.0; geometry.pixels()];
        green_luma(&frame, frame.levels.black, &mut native);
        for factor in [1, 2, 3, 5] {
            let expected =
                downsample(PlaneRef::from_geometry(&native, geometry).unwrap(), factor).unwrap();
            let (actual, actual_geometry) = boxed_green(&frame, frame.levels.black, factor);
            assert_eq!(
                actual_geometry,
                PlaneGeometry {
                    width: expected.width,
                    height: expected.height
                }
            );
            assert_eq!(
                actual.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                expected
                    .data
                    .iter()
                    .map(|v| v.to_bits())
                    .collect::<Vec<_>>()
            );
        }
        let (actual, _) = boxed_green(&frame, frame.levels.black, 3);
        assert!(
            actual.iter().all(|&v| v < 131.0),
            "padding poison must not enter guide samples"
        );
    }

    #[test]
    fn session_align_plane_cache_refuses_pinned_overcommit_and_evicts_released_planes() {
        let mut cache = BoundedPlanes::new(12);
        cache.reserve(8).unwrap();
        let first = cache.insert(0, 123u32, 8);
        assert!(
            cache.reserve(5).is_err(),
            "a pinned plane cannot be hidden from residency accounting"
        );
        cache.reserve(4).unwrap();
        let second = cache.insert(1, 456u32, 4);
        assert_eq!(cache.resident, 12);
        drop(first);
        cache.reserve(8).unwrap();
        let _third = cache.insert(2, 789u32, 8);
        assert!(cache.get(0).is_none());
        assert_eq!(*second, 456);
        assert_eq!(cache.peak, 12);
        assert!(cache.reserve(13).is_err());
    }

    #[test]
    fn session_align_memory_reserves_decode_cache_workers_and_dense_solve_before_work() {
        let config = SessionAlignConfig {
            memory_limit_bytes: 2 << 30,
            workers: 128,
            ..Default::default()
        };
        let plan = memory_plan(
            &config,
            598,
            2,
            128 << 20,
            128 << 20,
            PlaneGeometry {
                width: 4752,
                height: 3168,
            },
        )
        .unwrap();
        assert!(plan.native_workers < config.workers);
        assert!(plan.guide_workers > 0 && plan.native_workers > 0);
        assert!(plan.native_green_reserved_bytes >= 2 * plan.native_workers * 4752 * 3168 * 4);
        assert_eq!(plan.decoder_reserved_bytes, (4 * 128) << 20);
        assert!(plan.solver_reserved_bytes >= 32 * 598 * 598);
        assert!(plan.planned_total_bytes <= config.memory_limit_bytes);
        let impossible = SessionAlignConfig {
            memory_limit_bytes: 64 << 20,
            ..config.clone()
        };
        assert!(memory_plan(&impossible, 598, 2, 128 << 20, 128 << 20, geometry()).is_err());
        assert!(memory_plan(&config, usize::MAX, 2, 128 << 20, 128 << 20, geometry()).is_err());
    }

    #[test]
    fn session_align_pass_boundaries_are_never_intra_edges_and_primary_is_explicit() {
        let mut fixture = Fixture::new(&[3, 5, 2]);
        assert_eq!(reference(&fixture.session), (1, 5));
        let config = SessionAlignConfig::default();
        let pairs = initial_pairs(&fixture.session, &config, 1);
        for (&(i, j), purpose) in &pairs {
            if *purpose == PairPurpose::IntraPass {
                assert_eq!(
                    fixture.session.frames[i].pass_index,
                    fixture.session.frames[j].pass_index
                );
            }
        }
        assert_eq!(pairs.get(&(2, 3)), Some(&PairPurpose::CrossProbe));
        fixture.session.spec.primary_pass = Some(0);
        assert_eq!(reference(&fixture.session), (0, 1));
        assert_eq!(distributed(10..11, 7), vec![10]);
        assert_eq!(distributed(10..20, 3), vec![10, 14, 19]);
    }

    fn scale_pose(log_scale: f64) -> Similarity {
        Similarity {
            a: Cx::real(log_scale.exp()),
            b: Cx::ZERO,
        }
    }

    #[test]
    fn session_align_focus_hints_handle_reversed_passes_but_never_certify_equal_focus() {
        let fixture = Fixture::new(&[3, 3]);
        let poses: Vec<_> = [0.0, 0.1, 0.2, 0.2, 0.1, 0.0]
            .into_iter()
            .map(|s| Some(scale_pose(s)))
            .collect();
        let candidates = focus_candidates(&fixture.session, &poses, 0, 0.25);
        assert_eq!(
            candidates
                .iter()
                .filter(|c| c.candidate_same_focus)
                .map(|c| (c.i, c.j))
                .collect::<Vec<_>>(),
            vec![(0, 5), (1, 4), (2, 3)]
        );
        assert!(candidates.iter().all(|c| !c.validated_same_focus));
        let shifted: Vec<_> = [0.0, 0.1, 0.2, 0.25, 0.15, 0.05]
            .into_iter()
            .map(|s| Some(scale_pose(s)))
            .collect();
        assert!(
            focus_candidates(&fixture.session, &shifted, 0, 0.25)
                .iter()
                .all(|c| !c.candidate_same_focus)
        );
        let flat = vec![Some(Similarity::IDENTITY); 6];
        assert!(
            focus_candidates(&fixture.session, &flat, 0, 0.25)
                .iter()
                .all(|c| !c.candidate_same_focus && c.allowed_log_scale_gap.is_none())
        );
    }

    #[test]
    fn session_align_cross_search_uses_probes_in_either_normalized_edge_direction() {
        let fixture = Fixture::new(&[3, 3]);
        let truth: Vec<_> = [0.0, 0.01, 0.02, 0.02, 0.01, 0.0]
            .into_iter()
            .map(scale_pose)
            .collect();
        let mut edges = Vec::new();
        for (i, j) in [(0, 1), (0, 2), (1, 2), (3, 4), (3, 5), (4, 5), (0, 5)] {
            edges.push(AlignEdge {
                i,
                j,
                t: Similarity::relative(truth[i], truth[j]).unwrap(),
                rms: 0.1,
                used: 12,
                lever: 100.0,
            });
        }
        let config = SessionAlignConfig {
            cross_neighbor_radius: 0,
            smooth: 0.0,
            ..Default::default()
        };
        for reference_pass in [0, 1] {
            let candidates = cross_candidates(
                &fixture.session,
                &config,
                &edges,
                geometry(),
                reference_pass,
            )
            .unwrap();
            for pair in [(0, 5), (1, 4), (2, 3)] {
                assert!(
                    candidates.contains_key(&pair),
                    "reference pass {reference_pass} must propose {pair:?}"
                );
            }
        }
    }

    #[test]
    fn session_align_production_pair_consumers_reuse_original_cfa_and_refuse_flat_source() {
        let fixture = Fixture::new(&[2, 2]);
        let geometry = geometry();
        let config = SessionAlignConfig {
            workers: 2,
            guide_max_side: 256,
            native_tile: 48,
            native_grid: [6, 4],
            native_radius: 4,
            native_margin: 24,
            native_iterations: 4,
            smooth: 0.0,
            ..Default::default()
        };
        config.validate().unwrap();
        let truth = [
            Similarity::IDENTITY,
            Similarity::from_params(SimilarityParams {
                ax: 2.4,
                ay: -1.7,
                g: 0.001,
                rot: -0.0005,
            }),
            Similarity::from_params(SimilarityParams {
                ax: -3.2,
                ay: 2.1,
                g: -0.001,
                rot: 0.0004,
            }),
            Similarity::IDENTITY,
        ];
        // Only one CFA frame fits. All pair loads must round-trip the disk cache;
        // the deliberately non-RAW identities make accidental decode a failure.
        let mut sources = SourceCache::new(
            &fixture.root.join("cache"),
            &fixture.session,
            8 * geometry.pixels(),
        )
        .unwrap();
        for (i, &pose) in truth.iter().enumerate() {
            let _ = sources
                .store_original(
                    &fixture.identities[i],
                    &fixture.frame(i, geometry, pose, i == 3),
                )
                .unwrap();
        }
        let inputs = PlaneInputs {
            session: &fixture.session,
            identities: &fixture.identities,
            geometry,
            factor: 2,
            guide_config: config.estimator(true),
            contrast_scale: Vec::new(),
        };
        let guide_geometry = PlaneGeometry {
            width: 256,
            height: 192,
        };
        let mut guides = BoundedPlanes::new(4 * guide_bytes(guide_geometry).unwrap());
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(2)
            .build()
            .unwrap();
        let mut pairs = BTreeMap::new();
        add_pair(&mut pairs, 0, 1, PairPurpose::IntraPass);
        add_pair(&mut pairs, 0, 2, PairPurpose::CrossProbe);
        add_pair(&mut pairs, 2, 3, PairPurpose::IntraPass);
        let seeds = measure_guides(&pairs, &inputs, &mut sources, &mut guides, 2, &pool).unwrap();
        assert_eq!(
            seeds.iter().filter(|m| m.edge.is_some()).count(),
            2,
            "{:?}",
            seeds.iter().map(|m| &m.receipt).collect::<Vec<_>>()
        );
        assert!(!seeds[2].receipt.accepted);
        let mut native = BoundedPlanes::new(8 * geometry.pixels());
        let measured = measure_native(
            &seeds,
            &inputs,
            &mut sources,
            &mut native,
            &config,
            1,
            &pool,
        )
        .unwrap();
        assert_eq!(measured.len(), 2);
        let edges: Vec<_> = measured
            .iter()
            .map(|m| m.edge.expect("textured native pair"))
            .collect();
        for edge in &edges {
            let expected = Similarity::relative(truth[edge.i], truth[edge.j]).unwrap();
            assert!(
                edge.t.corner_err(expected, geometry) < 0.12,
                "native pair {:?} is misplaced: {}",
                (edge.i, edge.j),
                edge.t.corner_err(expected, geometry)
            );
        }
        let placement = solve_global_in_tracks(
            &edges,
            4,
            &config.solver(geometry),
            1,
            &[vec![0, 1], vec![2, 3]],
        )
        .unwrap();
        assert!(
            placement[3].is_none(),
            "flat disconnected frame must stay refused"
        );
        let anchor = placement[1].unwrap().invert().unwrap();
        for i in 0..3 {
            assert!(
                anchor
                    .then(placement[i].unwrap())
                    .corner_err(Similarity::relative(truth[1], truth[i]).unwrap(), geometry)
                    < 0.2
            );
        }
        assert_eq!(sources.stats().decodes, 0);
        assert!(sources.stats().disk_hits >= 3);
        assert!(sources.stats().peak_resident_cfa_bytes <= sources.budget_bytes());
        assert!(native.peak <= native.budget && guides.peak <= guides.budget);
    }

    fn envelope_fixture(fixture: &Fixture, config: &SessionAlignConfig) -> SessionAlignment {
        let binding = binding(
            &fixture.session,
            &fixture.identities,
            config,
            Resampler::CatmullRom,
        )
        .unwrap();
        let (reference_pass, reference_frame) = reference(&fixture.session);
        let memory = memory_plan(
            config,
            fixture.session.len(),
            fixture.session.passes.len(),
            4 << 20,
            4 << 20,
            geometry(),
        )
        .unwrap();
        let report = SessionAlignmentReport {
            generation: GENERATION.into(),
            binding_sha256: binding_digest(&binding).unwrap(),
            primary_pass: fixture.session.primary_pass_index(),
            reference_pass,
            reference_frame,
            geometry_plane_pixels: [512, 384],
            sensor_pixels_per_plane_pixel: 2,
            guide_factor: 1,
            frames: fixture.session.len(),
            measured_edges: 0,
            components: fixture.session.len(),
            cycle_rank: 0,
            anchor_component_cycle_rank: 0,
            passes: fixture
                .session
                .passes
                .iter()
                .enumerate()
                .map(|(pass_index, pass)| {
                    let placed = usize::from(pass.global_range.contains(&reference_frame));
                    PassAlignmentReport {
                        pass_index,
                        name: pass.name.clone(),
                        frames: pass.global_range.len(),
                        placed,
                        refused: pass.global_range.len() - placed,
                        measured_intra_edges: 0,
                        measured_cross_edges: 0,
                        intra_components: pass.global_range.len(),
                        intra_cycle_rank: 0,
                        wide_baseline: false,
                        cross_support_ratio: None,
                        relative_scale: None,
                        geometry_consistent: true,
                        contrast_scale: 1.0,
                        geometric_residual: None,
                        cross_photometric_spread: None,
                        cross_photometric_residual: None,
                        log_brightness_range: None,
                    }
                })
                .collect(),
            edges: vec![],
            focus_candidates: vec![],
            memory,
            source_cache_peak_bytes: 0,
            source_decodes: 0,
            source_disk_hits: 0,
            elapsed_seconds: 0.0,
            wide_baseline: Vec::new(),
            frame_photometry: None,
            photometric_edges: Vec::new(),
        };
        let map = WarpMap::new(
            Provenance {
                stack: StackIdentity::from_paths("fixture", &fixture.session.paths()).unwrap(),
                strategy: GENERATION.into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: reference_frame,
                note: "test fixture only".into(),
            },
            geometry(),
            Resampler::CatmullRom,
            (0..fixture.session.len())
                .map(|i| {
                    if i == reference_frame {
                        FrameWarp::Placed(Similarity::IDENTITY)
                    } else {
                        FrameWarp::Refused("test refusal".into())
                    }
                })
                .collect(),
        );
        SessionAlignment {
            map,
            report,
            pair_candidates: vec![],
            binding,
        }
    }

    #[test]
    fn session_align_envelope_binds_layout_sources_settings_and_exact_map_without_clobber() {
        let fixture = Fixture::new(&[2, 2]);
        let config = SessionAlignConfig::default();
        let alignment = envelope_fixture(&fixture, &config);
        let output = fixture.root.join("alignment.json");
        alignment.save(&output, &fixture.session).unwrap();
        let original = fs::read(&output).unwrap();
        let loaded = SessionAlignment::load(
            &output,
            &fixture.session,
            &fixture.identities,
            &config,
            Resampler::CatmullRom,
        )
        .unwrap();
        assert_eq!(loaded.map, alignment.map);
        let mut poisoned: serde_json::Value = serde_json::from_slice(&original).unwrap();
        poisoned["report"]["focus_candidates"] = serde_json::json!([{
            "i":999999,"j":888888,"mutual_nearest":true,"log_scale_gap":0.0,
            "allowed_log_scale_gap":1.0,"candidate_same_focus":true,"validated_same_focus":true
        }]);
        fs::write(&output, serde_json::to_vec(&poisoned).unwrap()).unwrap();
        let repaired = SessionAlignment::load(
            &output,
            &fixture.session,
            &fixture.identities,
            &config,
            Resampler::CatmullRom,
        )
        .unwrap();
        assert!(
            repaired.pair_candidates.is_empty(),
            "serialized report cannot introduce source indices or validate focus"
        );
        fs::write(&output, &original).unwrap();
        assert!(alignment.save(&output, &fixture.session).is_err());
        assert_eq!(fs::read(&output).unwrap(), original);
        assert!(
            alignment
                .save(
                    &fixture.session.passes[0].directories[0].join("forbidden.json"),
                    &fixture.session
                )
                .is_err()
        );
        let changed = SessionAlignConfig {
            workers: config.workers % 1024 + 1,
            ..config.clone()
        };
        assert!(
            SessionAlignment::load(
                &output,
                &fixture.session,
                &fixture.identities,
                &changed,
                Resampler::CatmullRom
            )
            .is_err()
        );
        let mut identities = fixture.identities.clone();
        identities[0].sha256 = "e".repeat(64);
        assert!(
            SessionAlignment::load(
                &output,
                &fixture.session,
                &identities,
                &config,
                Resampler::CatmullRom
            )
            .is_err()
        );
        let mut session = fixture.session.clone();
        session.spec.primary_pass = Some(1);
        assert!(
            SessionAlignment::load(
                &output,
                &session,
                &fixture.identities,
                &config,
                Resampler::CatmullRom
            )
            .is_err()
        );
        let mut envelope: serde_json::Value = serde_json::from_slice(&original).unwrap();
        envelope["warpmap"] =
            serde_json::Value::String(format!("{} ", envelope["warpmap"].as_str().unwrap()));
        fs::write(&output, serde_json::to_vec(&envelope).unwrap()).unwrap();
        assert!(
            SessionAlignment::load(
                &output,
                &fixture.session,
                &fixture.identities,
                &config,
                Resampler::CatmullRom
            )
            .is_err()
        );
    }

    #[test]
    fn session_align_concurrent_publication_has_one_complete_winner() {
        let fixture = Fixture::new(&[1]);
        let barrier = Arc::new(Barrier::new(2));
        let destination = fixture.root.join("published.json");
        let mut handles = Vec::new();
        for i in 0..2 {
            let temporary = fixture.root.join(format!("writer-{i}.partial"));
            let payload = vec![b'a' + i; 8192];
            fs::write(&temporary, &payload).unwrap();
            let barrier = Arc::clone(&barrier);
            let destination = destination.clone();
            handles.push(std::thread::spawn(move || {
                barrier.wait();
                (
                    publish_without_replace(&temporary, &destination).is_ok(),
                    payload,
                )
            }));
        }
        let results: Vec<_> = handles
            .into_iter()
            .map(|handle| handle.join().unwrap())
            .collect();
        assert_eq!(results.iter().filter(|(ok, _)| *ok).count(), 1);
        assert_eq!(
            fs::read(destination).unwrap(),
            results.into_iter().find(|(ok, _)| *ok).unwrap().1
        );
    }
}

#[cfg(test)]
#[test]
fn cache_identity_ignores_line_endings() {
    assert_eq!(&*source_text(b"a\r\nb\n\rc"), b"a\nb\n\rc");
    assert!(matches!(source_text(b"a\nb"), std::borrow::Cow::Borrowed(_)));
}
