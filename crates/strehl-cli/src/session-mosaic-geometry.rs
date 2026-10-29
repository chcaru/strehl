//! Source-bound focus-aware mosaic geometry. Intensity guides are diagnostics
//! used to nominate native measurements; they never become output pixels.

use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;
use strehl_core::plane::PlaneGeometry;

use crate::session_input::{ResolvedSession, SessionSpec, SourceIdentity};

#[path = "session-mosaic-roles.rs"]
pub mod roles;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MosaicGeometryConfig {
    pub guide_max_side: usize,
    pub maximum_features: usize,
    pub descriptor_ratio: f32,
    pub feature_separation: usize,
    pub descriptor_radius: usize,
    pub holdout_block_guide_pixels: usize,
    /// Explicit FIT-only frozen stage-two reservation plan. Absent preserves
    /// the original block partition; plans never relax native residual bars.
    #[serde(default)]
    pub role_plan: Option<Box<roles::FrozenRolePlan>>,
    pub minimum_pair_matches: usize,
    pub coarse_residual_guide_pixels: f64,
    pub native_tile: usize,
    /// Fixed five-tap binomial filter on the native grid, diagnostics opt-in.
    #[serde(default)]
    pub native_lowpass: bool,
    /// Experimental local affine image remeasurement; ordinary alignment is unaffected.
    #[serde(default)]
    pub native_affine: bool,
    /// Diagnostic robust coherent-tile subset; center and LOO checks still apply.
    #[serde(default)]
    pub native_affine_robust: bool,
    pub native_search_radius: i32,
    pub native_minimum_peak: f32,
    pub maximum_native_residual: f64,
    pub maximum_reciprocal_error: f64,
    pub mesh_cell_quad_pixels: usize,
    pub max_canvas_pixels: usize,
    pub max_canvas_side: usize,
}
impl Default for MosaicGeometryConfig {
    fn default() -> Self {
        Self {
            guide_max_side: 1024,
            maximum_features: 2000,
            descriptor_ratio: 0.75,
            feature_separation: 8,
            descriptor_radius: 12,
            holdout_block_guide_pixels: 128,
            role_plan: None,
            minimum_pair_matches: 8,
            coarse_residual_guide_pixels: 6.0,
            native_tile: 32,
            native_lowpass: false,
            native_affine: false,
            native_affine_robust: false,
            native_search_radius: 8,
            native_minimum_peak: 0.75,
            maximum_native_residual: 0.5,
            maximum_reciprocal_error: 0.5,
            mesh_cell_quad_pixels: 512,
            max_canvas_pixels: 200_000_000,
            max_canvas_side: 32_768,
        }
    }
}
impl MosaicGeometryConfig {
    pub(super) fn role_work_bytes(&self) -> Result<usize> {
        self.role_plan
            .as_ref()
            .map_or(Ok(0), |p| p.plan.working_reservation_bytes())
    }
    pub fn validate(&self) -> Result<()> {
        ensure!(
            (64..=2048).contains(&self.guide_max_side)
                && (8..=10_000).contains(&self.maximum_features)
                && self.descriptor_ratio.is_finite()
                && self.descriptor_ratio > 0.0
                && self.descriptor_ratio < 1.0
                && (4..=64).contains(&self.feature_separation)
                && (4..=32).contains(&self.descriptor_radius)
                && self.holdout_block_guide_pixels >= 4 * self.descriptor_radius
                && self.minimum_pair_matches >= 4
                && self.coarse_residual_guide_pixels.is_finite()
                && self.coarse_residual_guide_pixels > 0.0
                && (16..=128).contains(&self.native_tile)
                && (1..=32).contains(&self.native_search_radius)
                && self.native_minimum_peak.is_finite()
                && self.native_minimum_peak > 0.0
                && self.native_minimum_peak < 1.0
                && self.maximum_native_residual.is_finite()
                && self.maximum_native_residual > 0.0
                && self.maximum_reciprocal_error.is_finite()
                && self.maximum_reciprocal_error > 0.0
                && self.mesh_cell_quad_pixels >= 32
                && self.max_canvas_pixels > 0
                && self.max_canvas_side > 0,
            "invalid mosaic geometry configuration"
        );
        if let Some(plan) = &self.role_plan {
            plan.verify()?;
        }
        Ok(())
    }

    pub(super) fn spatial_role(
        &self,
        guide: &MosaicGuide,
        point: [f64; 2],
        radius: f64,
    ) -> Option<([usize; 2], bool)> {
        let Some(frozen) = &self.role_plan else {
            return matching::reserved_role(point, radius, self.holdout_block_guide_pixels);
        };
        let grid = frozen.plan.grids.get(guide.pass)?;
        if grid.source_size_quad != [guide.source_geometry.width, guide.source_geometry.height]
            || grid.guide_origin_quad != guide.origin
            || grid.guide_step_quad != guide.step
        {
            return None;
        }
        let bounds =
            roles::Rectangle::around(guide.full_point(point), radius * guide.step as f64).ok()?;
        match frozen.plan.classify(guide.pass, bounds)? {
            roles::SpatialRole::Fit => Some((
                point.map(|v| v.max(0.0) as usize / self.holdout_block_guide_pixels),
                false,
            )),
            roles::SpatialRole::Heldout(island) => Some(([island, usize::MAX], true)),
        }
    }
}

pub struct MosaicGuide {
    pub pass: usize,
    pub source_geometry: PlaneGeometry,
    pub geometry: PlaneGeometry,
    /// Box centres in the pass-anchor's full native green-quad coordinates.
    pub origin: [f64; 2],
    pub step: usize,
    pub intensity: Vec<f32>,
    pub covered: Vec<bool>,
    pub focus_ordinal: Vec<f32>,
    pub focus_width: Vec<f32>,
    pub usable_focus: Vec<bool>,
    /// Actual originals contributing to this diagnostic guide pixel; usize::MAX
    /// is not an original and is never exposed as a native measurement source.
    pub source_indices: Vec<[usize; 4]>,
    pub receipt: GuideReceipt,
}
impl MosaicGuide {
    pub fn full_point(&self, point: [f64; 2]) -> [f64; 2] {
        [
            self.origin[0] + self.step as f64 * point[0],
            self.origin[1] + self.step as f64 * point[1],
        ]
    }
    pub fn validate(&self) -> Result<()> {
        let n = self
            .geometry
            .width
            .checked_mul(self.geometry.height)
            .context("guide size overflow")?;
        ensure!(
            self.geometry.width > 0
                && self.geometry.height > 0
                && self.step > 0
                && self.origin.into_iter().all(f64::is_finite)
                && self.source_geometry.width > 0
                && self.source_geometry.height > 0,
            "invalid mosaic guide geometry"
        );
        ensure!(
            [
                self.intensity.len(),
                self.covered.len(),
                self.focus_ordinal.len(),
                self.focus_width.len(),
                self.usable_focus.len(),
                self.source_indices.len()
            ]
            .into_iter()
            .all(|len| len == n),
            "guide buffer length mismatch"
        );
        for i in 0..n {
            ensure!(
                !self.covered[i] || self.intensity[i].is_finite(),
                "nonfinite covered guide intensity"
            );
            ensure!(
                !self.usable_focus[i]
                    || (self.focus_ordinal[i].is_finite()
                        && self.focus_width[i].is_finite()
                        && self.focus_width[i] >= 0.0),
                "invalid usable guide focus"
            );
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GuideReceipt {
    pub pass: usize,
    pub source_geometry: [usize; 2],
    pub guide_geometry: [usize; 2],
    pub origin_quad_pixels: [f64; 2],
    pub step_quad_pixels: usize,
    pub alignment_sha256: String,
    pub focus_evidence_sha256: String,
    pub guide_sha256: String,
    pub covered_pixels: usize,
    pub usable_focus_pixels: usize,
    pub source_contributions: Vec<(usize, usize)>,
    pub reserved_work_bytes: usize,
    pub construction: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MosaicBinding {
    pub version: String,
    pub algorithm_sha256: String,
    pub session: SessionSpec,
    pub sources: Vec<SourceIdentity>,
    pub config: MosaicGeometryConfig,
    pub guide_hashes: Vec<String>,
    pub alignment_hashes: Vec<String>,
    pub focus_hashes: Vec<String>,
}
pub fn binding(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    guides: &[MosaicGuide],
    config: &MosaicGeometryConfig,
) -> Result<MosaicBinding> {
    session.spec.validate()?;
    config.validate()?;
    ensure!(
        session.spec.primary_pass.is_none(),
        "mosaic stitching has no primary pass preference"
    );
    ensure!(
        identities.len() == session.len()
            && guides.len() == session.passes.len()
            && guides.len() >= 2,
        "mosaic source/pass census mismatch"
    );
    for (frame, identity) in session.frames.iter().zip(identities) {
        identity.validate()?;
        identity.check_unchanged()?;
        ensure!(
            frame.path == identity.path
                && frame.bytes == identity.bytes
                && frame.modified_unix_nanos == identity.modified_unix_nanos,
            "mosaic source identity mismatch"
        );
    }
    for (pass, guide) in guides.iter().enumerate() {
        guide.validate()?;
        ensure!(
            guide.pass == pass && guide.receipt.pass == pass,
            "mosaic guides must retain declared pass order"
        );
    }
    if let Some(frozen) = &config.role_plan {
        ensure!(
            guides.len() == 2,
            "native island plan currently requires two independently aligned views"
        );
        for (pass, guide) in guides.iter().enumerate() {
            let grid = &frozen.plan.grids[pass];
            let range = &session.passes[pass].global_range;
            ensure!(
                grid.source_size_quad
                    == [guide.source_geometry.width, guide.source_geometry.height]
                    && grid.guide_origin_quad == guide.origin
                    && grid.guide_step_quad == guide.step
                    && grid.initial_block_guide_pixels == config.holdout_block_guide_pixels
                    && grid.global_source_range == [range.start, range.end],
                "frozen island plan differs from source/pass gauge"
            );
        }
        let mut initial = config.clone();
        initial.role_plan = None;
        let expected = binding(session, identities, guides, &initial)?;
        ensure!(
            frozen.plan.upstream_binding_sha256
                == hex(&Sha256::digest(serde_json::to_vec(&expected)?)),
            "frozen islands belong to different upstream source/map/focus/config evidence"
        );
    }
    let mut algorithm = Sha256::new();
    for source in [
        include_bytes!("session-mosaic-geometry.rs").as_slice(),
        include_bytes!("session-mosaic-roles.rs").as_slice(),
        include_bytes!("session-mosaic-guide.rs").as_slice(),
        include_bytes!("session-mosaic-original-guide.rs").as_slice(),
        include_bytes!("session-mosaic-match.rs").as_slice(),
        include_bytes!("session-mosaic-scale-features.rs").as_slice(),
        include_bytes!("session-mosaic-source-features.rs").as_slice(),
        include_bytes!("session-mosaic-source-selection.rs").as_slice(),
        include_bytes!("session-mosaic-ordinal-seed.rs").as_slice(),
        include_bytes!("session-mosaic-native.rs").as_slice(),
        include_bytes!("session-mosaic-native-trace.rs").as_slice(),
        include_bytes!("session-mosaic-native-filter.rs").as_slice(),
        include_bytes!("session-mosaic-native-affine.rs").as_slice(),
        include_bytes!("session-mosaic-grid.rs").as_slice(),
        include_bytes!("session-mosaic-support.rs").as_slice(),
        include_bytes!("session-mosaic-solve.rs").as_slice(),
        include_bytes!("session-focus.rs").as_slice(),
        include_bytes!("session-cache.rs").as_slice(),
        include_bytes!("session-mapped-sampling.rs").as_slice(),
        include_bytes!("session-sampling.rs").as_slice(),
        include_bytes!("../../strehl-core/src/mosaic.rs").as_slice(),
        include_bytes!("../../strehl-core/src/mosaic-support.rs").as_slice(),
        include_bytes!("../../strehl-core/src/mosaic-fit.rs").as_slice(),
        include_bytes!("../../strehl-core/src/focus-evidence.rs").as_slice(),
        include_bytes!("../../strehl-core/src/plane.rs").as_slice(),
        include_bytes!("../../strehl-core/src/align.rs").as_slice(),
        include_bytes!("../../strehl-raw/src/lib.rs").as_slice(),
        include_bytes!("../../../Cargo.lock").as_slice(),
    ] {
        algorithm.update(source);
    }
    Ok(MosaicBinding {
        version: "strehl.focus-mosaic.v1".into(),
        algorithm_sha256: hex(&algorithm.finalize()),
        session: session.spec.clone(),
        sources: identities.to_vec(),
        config: config.clone(),
        guide_hashes: guides
            .iter()
            .map(|g| g.receipt.guide_sha256.clone())
            .collect(),
        alignment_hashes: guides
            .iter()
            .map(|g| g.receipt.alignment_sha256.clone())
            .collect(),
        focus_hashes: guides
            .iter()
            .map(|g| g.receipt.focus_evidence_sha256.clone())
            .collect(),
    })
}
pub(crate) fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Serialize exact receipts and topology together; publish without replacing a
/// prior result even when another process wins the same destination race.
pub fn save_bound<T: Serialize>(
    path: &Path,
    session: &ResolvedSession,
    binding: &MosaicBinding,
    data: &T,
) -> Result<()> {
    ensure!(
        session.spec == binding.session,
        "mosaic binding belongs to another session"
    );
    let destination = session.ensure_output_outside_sources(path)?;
    let parent = destination
        .parent()
        .context("mosaic envelope has no parent")?;
    std::fs::create_dir_all(parent)?;
    let payload = serde_json::to_value(data)?;
    let digest = hex(&Sha256::digest(serde_json::to_vec(&payload)?));
    let envelope = serde_json::json!({"binding":binding,"payload_sha256":digest,"payload":payload});
    static NEXT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let temporary = destination.with_extension(format!(
        "{}.{}.partial",
        std::process::id(),
        NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
    ));
    session.ensure_output_outside_sources(&temporary)?;
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)?;
    use std::io::Write;
    let written = (|| -> Result<()> {
        serde_json::to_writer(&mut file, &envelope)?;
        file.write_all(b"\n")?;
        file.sync_all()?;
        Ok(())
    })();
    drop(file);
    if let Err(error) = written {
        let _ = std::fs::remove_file(&temporary);
        return Err(error);
    }
    session.ensure_output_outside_sources(&destination)?;
    let publish = std::fs::hard_link(&temporary, &destination);
    let _ = std::fs::remove_file(&temporary);
    publish.context("publish mosaic envelope without replacement")?;
    Ok(())
}
pub fn load_bound<T: serde::de::DeserializeOwned>(
    path: &Path,
    expected: &MosaicBinding,
) -> Result<T> {
    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Envelope {
        binding: MosaicBinding,
        payload_sha256: String,
        payload: serde_json::Value,
    }
    let envelope: Envelope = serde_json::from_slice(&std::fs::read(path)?)?;
    ensure!(
        &envelope.binding == expected,
        "mosaic envelope source/configuration binding changed"
    );
    ensure!(
        hex(&Sha256::digest(serde_json::to_vec(&envelope.payload)?)) == envelope.payload_sha256,
        "mosaic envelope payload checksum mismatch"
    );
    for source in &expected.sources {
        source.validate()?;
        source.check_unchanged()?;
    }
    Ok(serde_json::from_value(envelope.payload)?)
}

#[path = "session-mosaic-guide.rs"]
mod guide;
pub use guide::{build_guide, save_diagnostics};

#[path = "session-mosaic-match.rs"]
mod matching;
pub use matching::{
    CoarseCorrespondence, MatchRole, PairDiscovery, SourceFeatureReceipt, discover_pairs,
    discover_source_pairs, discover_source_pairs_cached,
};

#[path = "session-mosaic-native.rs"]
mod native;
pub use native::{
    NativeCorrespondence, NativeSupportBounds, native_attempted_support,
    refine_explicit_correspondences_cached, refine_native_correspondences,
    refine_native_correspondences_cached,
};

#[path = "session-mosaic-solve.rs"]
mod solve;
pub use solve::{
    MosaicGeometry, MosaicGeometryReport, NativeConstraintSet, independent_native_constraints,
    solve_geometry,
};
