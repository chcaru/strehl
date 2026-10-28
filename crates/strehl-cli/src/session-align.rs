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
    algorithm.update(include_bytes!("session-align.rs"));
    algorithm.update(include_bytes!("../../strehl-core/src/align.rs"));
    algorithm.update(include_bytes!("../../strehl-core/src/plane.rs"));
    algorithm.update(include_bytes!("../../strehl-core/src/warpmap.rs"));
    algorithm.update(include_bytes!("../../strehl-raw/src/lib.rs"));
    algorithm.update(include_bytes!("../../../Cargo.lock"));
    algorithm.update(include_bytes!("session-cache.rs"));
    algorithm.update(include_bytes!("session-input.rs"));
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
                    && matches!(edge.stage.as_str(), "guide" | "native")
                    && seen.insert((edge.i, edge.j, edge.stage.as_str())),
                "alignment edge report has invalid or duplicate indices"
            );
            let intra = session.frames[edge.i].pass_index == session.frames[edge.j].pass_index;
            ensure!(
                (edge.purpose == PairPurpose::IntraPass) == intra,
                "alignment edge purpose disagrees with its pass indices"
            );
            if edge.accepted && edge.stage == "native" {
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
}

impl PlaneInputs<'_> {
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
        let guide = Guide {
            data,
            geometry,
            pyramid,
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
                    let cfg = &inputs.guide_config;
                    let result = match tile_grid(
                        reference,
                        cfg.fine_tile,
                        cfg.fine_grid.0,
                        cfg.fine_grid.1,
                        cfg.margin,
                    ) {
                        Some(spots) => align_pair(
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
                        ),
                        None => Err(AlignFailure::GridTooSmall),
                    };
                    let (receipt, edge) = receipt(
                        *i,
                        *j,
                        *purpose,
                        "guide",
                        &result,
                        inputs.geometry,
                        inputs.factor,
                    );
                    PairMeasurement { receipt, edge }
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
            measurement
                .edge
                .map(|edge| (edge, measurement.receipt.purpose))
        })
        .collect();
    let mut measured = Vec::with_capacity(pairs.len());
    let cfg = config.estimator(false);
    for batch in pairs.chunks(workers) {
        let mut jobs = Vec::with_capacity(batch.len());
        for &(edge, purpose) in batch {
            jobs.push((
                edge,
                purpose,
                inputs.native(edge.i, sources, planes)?,
                inputs.native(edge.j, sources, planes)?,
            ));
        }
        let mut results = pool.install(|| {
            jobs.par_iter()
                .map(|(edge, purpose, a, b)| {
                    let reference = PlaneRef::from_geometry(&a.data, a.geometry)
                        .expect("constructed native plane");
                    let moving = PlaneRef::from_geometry(&b.data, b.geometry)
                        .expect("constructed native plane");
                    let result = match tile_grid(
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
                    };
                    let (receipt, edge) = receipt(
                        edge.i,
                        edge.j,
                        *purpose,
                        "native",
                        &result,
                        inputs.geometry,
                        1,
                    );
                    PairMeasurement { receipt, edge }
                })
                .collect::<Vec<_>>()
        });
        measured.append(&mut results);
    }
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
    let inputs = PlaneInputs {
        session,
        identities,
        geometry,
        factor,
        guide_config: config.estimator(true),
    };
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
        let _ = inputs.guide(i, cache, &mut guides)?;
        if (i + 1) % 100 == 0 {
            eprintln!(
                "session alignment: prepared {}/{} original CFA sources",
                i + 1,
                session.len()
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
    let initial_edges: Vec<_> = guide_measurements.iter().filter_map(|m| m.edge).collect();
    let mut candidates =
        cross_candidates(session, config, &initial_edges, geometry, reference_pass)?;
    candidates.retain(|pair, _| !initial.contains_key(pair));
    eprintln!(
        "session alignment: measuring {} additional cross-pass guide candidates",
        candidates.len()
    );
    guide_measurements.extend(measure_guides(
        &candidates,
        &inputs,
        cache,
        &mut guides,
        memory.guide_workers,
        &pool,
    )?);
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
            let cross = edges
                .iter()
                .filter(|edge| {
                    pass.global_range.contains(&edge.i) != pass.global_range.contains(&edge.j)
                })
                .count();
            PassAlignmentReport {
                pass_index: index,
                name: pass.name.clone(),
                frames: pass.global_range.len(),
                placed,
                refused: pass.global_range.len() - placed,
                measured_intra_edges: intra_edges.len(),
                measured_cross_edges: cross,
                intra_components: intra_stats.components,
                intra_cycle_rank: intra_stats.cycle_rank,
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
