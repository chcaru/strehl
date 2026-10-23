//! Immutable, opt-in development snapshots for an explicitly SDR scene branch.
//!
//! Construction binds an owning image/source digest, a complete recipe and an
//! exact frozen asset before any pixel job starts. It installs no recipe field,
//! application default, model, file loader or export path. The source digest is
//! provenance supplied by the image owner, not inferred from the asset or path.
//!
//! Absent, disabled and zero-Amount treatments call the existing image helpers
//! directly. Active SDR applies scene(raw, full-image UV), then the existing
//! manual/region/spatial recipe, then per-channel 0..1 clipping. No legacy
//! baseline placement/contrast is applied to that candidate. Intermediate
//! Amounts blend it with the decoded COMPLETE existing SDR display in linear
//! BT.709; zero and one take their direct endpoints. Active HDR is unsupported.
//!
//! Cloning and Amount changes share the image, recipe and prepared fields. Pixel
//! jobs perform no resolution, I/O, field preparation or image-sized allocation.
//! Region outputs belong to the caller and must be published only after success.
use crate::learned_asset::{AssetDigest, AssetIdentities};
use crate::learned_scene::{PreparedSceneSdrProfile, SCENE_SDR_LINEAR_V1};
use crate::learned_scene_asset::FrozenSceneAsset;
use crate::learned_store::{AssetKey, ExpectedAsset};
use crate::{DevelopmentRecipe, DisplayRegionRequest, ImageOrigin, LinearImage};
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use std::sync::{
    Arc,
    atomic::{AtomicBool, AtomicU64, Ordering},
};

static NEXT_SNAPSHOT: AtomicU64 = AtomicU64::new(1);

/// Process-local completion token. Clones share it; new preparations and Amount
/// changes receive a new token even when a path or UI revision counter repeats.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct DevelopmentSnapshotId(u64);

fn next_id() -> Result<DevelopmentSnapshotId> {
    NEXT_SNAPSHOT
        .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |v| v.checked_add(1))
        .map(DevelopmentSnapshotId)
        .map_err(|_| anyhow::anyhow!("Development snapshot identifiers exhausted"))
}

/// Whole-photograph SDR intent, deliberately outside serialized recipes. The
/// source digest and photograph extent come separately from the owning image.
/// This type accepts only the fixed `SCENE_SDR_LINEAR_V1` render contract.
#[derive(Clone, Debug)]
pub struct SceneTreatmentReference {
    pub key: AssetKey,
    pub contract_sha256: AssetDigest,
    pub model_sha256: AssetDigest,
    pub input_sha256: AssetDigest,
    pub enabled: bool,
    pub amount: f32,
}

#[derive(Clone)]
pub struct PreparedSdrDevelopment {
    id: DevelopmentSnapshotId,
    image: Arc<LinearImage>,
    source_sha256: AssetDigest,
    recipe: Arc<DevelopmentRecipe>,
    treatment: Option<SceneTreatmentReference>,
    // Retained at Amount zero after an active preparation, so moving back needs
    // neither a store lookup nor another field construction.
    asset: Option<Arc<FrozenSceneAsset>>,
    prepared: Option<Arc<PreparedSceneSdrProfile>>,
}

fn check_cancelled(cancelled: &AtomicBool) -> Result<()> {
    ensure!(!cancelled.load(Ordering::Relaxed), "Development cancelled");
    Ok(())
}

fn validate_amount(amount: f32) -> Result<()> {
    ensure!(
        amount.is_finite() && (0.0..=1.0).contains(&amount),
        "Scene Amount must be in 0..1"
    );
    Ok(())
}

impl PreparedSdrDevelopment {
    /// Resolve once, before rendering. A store-backed caller can pass a closure
    /// around `load_scene`; a cache can return the same immutable Arc. The result
    /// is independently checked here even if that resolver omits validation.
    /// The resolver is never called for absent/disabled/zero-Amount intent.
    pub fn prepare(
        image: Arc<LinearImage>,
        source_sha256: AssetDigest,
        recipe: DevelopmentRecipe,
        treatment: Option<SceneTreatmentReference>,
        cancelled: &AtomicBool,
        resolve: impl FnOnce(AssetKey, &ExpectedAsset, &AtomicBool) -> Result<Arc<FrozenSceneAsset>>,
    ) -> Result<Self> {
        check_cancelled(cancelled)?;
        image.validate()?;
        recipe.validate()?;
        if let Some(reference) = &treatment {
            validate_amount(reference.amount)?;
        }
        let mut asset = None;
        if let Some(reference) = treatment.as_ref().filter(|r| r.enabled && r.amount > 0.) {
            ensure!(
                image.origin == ImageOrigin::SceneLinear,
                "Active scene development requires a scene-linear master"
            );
            // Existing inactive preview behavior can show pending restack edits.
            // An active learned treatment must bind the actual reconstructed source.
            image.validate_source_repairs(&recipe)?;
            let expected = ExpectedAsset {
                identities: AssetIdentities {
                    contract_id: SCENE_SDR_LINEAR_V1.into(),
                    contract_sha256: reference.contract_sha256,
                    model_sha256: reference.model_sha256,
                    input_sha256: reference.input_sha256,
                    source_sha256,
                },
                full_size: [image.width, image.height],
            };
            check_cancelled(cancelled)?;
            let resolved = resolve(reference.key, &expected, cancelled)
                .context("Resolving active SDR scene treatment")?;
            ensure!(
                resolved.digest() == reference.key.digest(),
                "Scene asset does not match requested content key"
            );
            expected.verify_scene(&resolved)?;
            ensure!(
                resolved.descriptor().origin.region.is_none(),
                "Scene development requires whole-photograph analysis"
            );
            asset = Some(resolved);
        }
        check_cancelled(cancelled)?;
        let prepared = asset.as_ref().map(|a| a.prepared());
        Ok(Self {
            id: next_id()?,
            image,
            source_sha256,
            recipe: Arc::new(recipe),
            treatment,
            asset,
            prepared,
        })
    }

    pub fn id(&self) -> DevelopmentSnapshotId {
        self.id
    }
    pub fn image(&self) -> &Arc<LinearImage> {
        &self.image
    }
    pub fn source_sha256(&self) -> AssetDigest {
        self.source_sha256
    }
    pub fn full_size(&self) -> [u32; 2] {
        [self.image.width, self.image.height]
    }
    pub fn recipe(&self) -> &DevelopmentRecipe {
        &self.recipe
    }
    pub fn treatment(&self) -> Option<&SceneTreatmentReference> {
        self.treatment.as_ref()
    }
    pub fn is_active(&self) -> bool {
        self.treatment
            .as_ref()
            .is_some_and(|r| r.enabled && r.amount > 0.)
    }

    /// Same bytes at the same path do not make a newly loaded image instance the
    /// original job source. UI completion checks should also compare `id()`.
    pub fn matches_source(&self, image: &Arc<LinearImage>, source_sha256: AssetDigest) -> bool {
        Arc::ptr_eq(&self.image, image) && self.source_sha256 == source_sha256
    }

    /// Lightweight slider update, without I/O, field construction or allocation.
    /// An initially disabled/zero unresolved reference needs explicit `prepare`
    /// before enabling a positive Amount. Existing resolved fields survive zero.
    pub fn with_amount(&self, amount: f32) -> Result<Self> {
        validate_amount(amount)?;
        let reference = self
            .treatment
            .as_ref()
            .context("No scene treatment reference")?;
        ensure!(
            !reference.enabled || amount == 0. || self.asset.is_some(),
            "Scene asset is unresolved; prepare explicitly before activation"
        );
        let mut result = self.clone();
        result.treatment.as_mut().unwrap().amount = amount;
        result.id = next_id()?;
        Ok(result)
    }

    fn source_pixel(&self, i: usize) -> Result<([f32; 3], [f32; 2])> {
        ensure!(
            i < self.image.pixels.len() / 3,
            "Development pixel exceeds source extent"
        );
        let p = &self.image.pixels[i * 3..i * 3 + 3];
        Ok((
            [p[0], p[1], p[2]],
            [
                ((i % self.image.width as usize) as f32 + 0.5) / self.image.width as f32,
                ((i / self.image.width as usize) as f32 + 0.5) / self.image.height as f32,
            ],
        ))
    }

    /// Encoded SDR display; exact existing path at zero and direct candidate at one.
    pub fn display_pixel(&self, i: usize) -> Result<[f32; 3]> {
        let (raw, uv) = self.source_pixel(i)?;
        self.display_sample(raw, uv)
    }

    /// Existing extended development is available ONLY for the bypass state.
    /// Refuses active learned HDR instead of silently exporting a different view.
    pub fn developed_pixel(&self, i: usize) -> Result<[f32; 3]> {
        ensure!(
            !self.is_active(),
            "Active scene treatment is SDR-only; learned HDR development is unsupported"
        );
        let (raw, uv) = self.source_pixel(i)?;
        let developed = self.image.developed_sample(raw, uv, &self.recipe);
        ensure!(
            developed.iter().all(|v| v.is_finite()),
            "Nonfinite developed sample"
        );
        Ok(developed)
    }

    fn candidate_sample(&self, raw: [f32; 3], uv: [f32; 2]) -> Result<[f32; 3]> {
        let prepared = self
            .prepared
            .as_ref()
            .context("Unresolved scene treatment")?;
        let scene = prepared.develop_pixel(raw, uv)?;
        let edited = self.recipe.apply_pixel(scene, uv);
        ensure!(
            edited.iter().all(|v| v.is_finite()),
            "Nonfinite learned development sample"
        );
        Ok(edited.map(|v| v.clamp(0., 1.)))
    }

    fn sdr_linear_sample(&self, raw: [f32; 3], uv: [f32; 2]) -> Result<[f32; 3]> {
        if !self.is_active() {
            return Ok(self.display_sample(raw, uv)?.map(crate::color::decode_srgb));
        }
        let candidate = self.candidate_sample(raw, uv)?;
        let amount = self.treatment.as_ref().unwrap().amount;
        if amount == 1. {
            return Ok(candidate);
        }
        let baseline = self
            .image
            .display_sample(raw, uv, &self.recipe)
            .map(crate::color::decode_srgb);
        let result = std::array::from_fn(|c| baseline[c] * (1. - amount) + candidate[c] * amount);
        ensure!(
            result.iter().all(|v| v.is_finite()),
            "Nonfinite SDR development blend"
        );
        Ok(result)
    }

    fn display_sample(&self, raw: [f32; 3], uv: [f32; 2]) -> Result<[f32; 3]> {
        if !self.is_active() {
            let display = self.image.display_sample(raw, uv, &self.recipe);
            ensure!(
                display.iter().all(|v| v.is_finite()),
                "Nonfinite SDR display sample"
            );
            return Ok(display);
        }
        Ok(self
            .sdr_linear_sample(raw, uv)?
            .map(crate::image::srgb_encode))
    }

    /// Integer full-image footprint and power-of-two stride, matching existing
    /// viewport sampling. Stride one is native; larger strides develop an area
    /// average at its full-image footprint center. Nonlinear development of that
    /// average is an explicit coarse approximation, not averaged developed RGB.
    pub fn region_size(&self, region: DisplayRegionRequest) -> Result<[u32; 2]> {
        ensure!(
            region.stride.is_power_of_two()
                && region.min[0] < region.max[0]
                && region.min[1] < region.max[1]
                && region.max[0] <= self.image.width
                && region.max[1] <= self.image.height,
            "Invalid development region"
        );
        Ok(
            [region.max[0] - region.min[0], region.max[1] - region.min[1]]
                .map(|n| n.div_ceil(region.stride)),
        )
    }

    pub fn render_region_sdr8(
        &self,
        region: DisplayRegionRequest,
        output: &mut [u8],
        cancelled: &AtomicBool,
    ) -> Result<()> {
        self.render_region(region, output, cancelled, |raw, uv| {
            Ok(self
                .display_sample(raw, uv)?
                .map(|v| (v * 255. + 0.5) as u8))
        })
    }

    pub fn render_region_sdr16(
        &self,
        region: DisplayRegionRequest,
        output: &mut [u16],
        cancelled: &AtomicBool,
    ) -> Result<()> {
        self.render_region(region, output, cancelled, |raw, uv| {
            Ok(self
                .display_sample(raw, uv)?
                .map(|v| (v * 65535. + 0.5) as u16))
        })
    }

    /// Linear SDR BT.709 display values, not an HDR output contract.
    pub fn render_region_sdr_linear(
        &self,
        region: DisplayRegionRequest,
        output: &mut [f32],
        cancelled: &AtomicBool,
    ) -> Result<()> {
        self.render_region(region, output, cancelled, |raw, uv| {
            self.sdr_linear_sample(raw, uv)
        })
    }

    /// Exact existing viewport extended values for inactive treatment only.
    /// Display-referred images retain the existing decoded-SDR behavior.
    pub fn render_region_developed(
        &self,
        region: DisplayRegionRequest,
        output: &mut [f32],
        cancelled: &AtomicBool,
    ) -> Result<()> {
        ensure!(
            !self.is_active(),
            "Active scene treatment is SDR-only; learned HDR development is unsupported"
        );
        self.render_region(region, output, cancelled, |raw, uv| {
            let developed = if self.image.origin == ImageOrigin::DisplayReferred {
                self.display_sample(raw, uv)?.map(crate::color::decode_srgb)
            } else {
                self.image.developed_sample(raw, uv, &self.recipe)
            };
            ensure!(
                developed.iter().all(|v| v.is_finite()),
                "Nonfinite developed sample"
            );
            Ok(developed)
        })
    }

    fn render_region<T: Send + Copy>(
        &self,
        region: DisplayRegionRequest,
        output: &mut [T],
        cancelled: &AtomicBool,
        sample: impl Fn([f32; 3], [f32; 2]) -> Result<[T; 3]> + Sync,
    ) -> Result<()> {
        check_cancelled(cancelled)?;
        let size = self.region_size(region)?;
        let count = u64::from(size[0]) * u64::from(size[1]) * 3;
        ensure!(
            output.len() == usize::try_from(count)?,
            "Incorrect development output extent"
        );
        let extent = [region.max[0] - region.min[0], region.max[1] - region.min[1]];
        output
            .par_chunks_mut(size[0] as usize * 3)
            .enumerate()
            .try_for_each(|(y, row)| -> Result<()> {
                check_cancelled(cancelled)?;
                let y0 =
                    region.min[1] + (y as u64 * u64::from(extent[1]) / u64::from(size[1])) as u32;
                let y1 = region.min[1]
                    + ((y as u64 + 1) * u64::from(extent[1]) / u64::from(size[1])) as u32;
                for x in 0..size[0] {
                    if x % 64 == 0 {
                        check_cancelled(cancelled)?;
                    }
                    let x0 = region.min[0]
                        + (u64::from(x) * u64::from(extent[0]) / u64::from(size[0])) as u32;
                    let x1 = region.min[0]
                        + (u64::from(x + 1) * u64::from(extent[0]) / u64::from(size[0])) as u32;
                    let mut raw = [0.0f32; 3];
                    for sy in y0..y1 {
                        if sy % 16 == 0 {
                            check_cancelled(cancelled)?;
                        }
                        for sx in x0..x1 {
                            let at = (sy as usize * self.image.width as usize + sx as usize) * 3;
                            for (c, v) in raw.iter_mut().enumerate() {
                                *v += self.image.pixels[at + c];
                            }
                        }
                    }
                    let samples = ((x1 - x0) * (y1 - y0)) as f32;
                    raw = raw.map(|v| v / samples);
                    ensure!(
                        raw.iter().all(|v| v.is_finite()),
                        "Nonfinite development source sample"
                    );
                    let uv = [
                        (x0 as f32 + x1 as f32) * 0.5 / self.image.width as f32,
                        (y0 as f32 + y1 as f32) * 0.5 / self.image.height as f32,
                    ];
                    row[x as usize * 3..x as usize * 3 + 3].copy_from_slice(&sample(raw, uv)?);
                }
                Ok(())
            })?;
        check_cancelled(cancelled)
    }
}

#[cfg(test)]
#[path = "learned-development-tests.rs"]
mod tests;
