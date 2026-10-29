//! Immutable baseline development shared by photograph consumers.
//!
//! This seam carries no learned intent and cannot attach an asset. Introducing
//! that capability requires all consumers, including version persistence and
//! HDR/AVIF delivery, to honor or explicitly refuse the prepared treatment.
//! Construction never hashes or scans pixels; the owning Arc identifies the
//! loaded instance while the token distinguishes recipe generations.
use anyhow::Result;
use std::{
    path::Path,
    sync::{
        Arc,
        atomic::{AtomicBool, AtomicU64, Ordering},
    },
};
use strehl_edit::{DevelopmentRecipe, ExportReport, ExportSettings, LinearImage};

static NEXT_TOKEN: AtomicU64 = AtomicU64::new(1);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct DevelopmentToken(u64);

#[derive(Clone)]
pub(crate) struct DevelopmentJob {
    token: DevelopmentToken,
    image: Arc<LinearImage>,
    overview: Arc<LinearImage>,
    recipe: Arc<DevelopmentRecipe>,
    coverage: Option<Arc<crate::photo_coverage::Coverage>>,
}

impl DevelopmentJob {
    pub(crate) fn new(
        image: Arc<LinearImage>,
        overview: Arc<LinearImage>,
        recipe: DevelopmentRecipe,
    ) -> Self {
        let token = NEXT_TOKEN
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |v| v.checked_add(1))
            .expect("Development job identifiers exhausted");
        Self {
            token: DevelopmentToken(token),
            image,
            overview,
            recipe: Arc::new(recipe),
            coverage: None,
        }
    }

    pub(crate) fn native(image: Arc<LinearImage>, recipe: DevelopmentRecipe) -> Self {
        Self::new(image.clone(), image, recipe)
    }

    pub(crate) fn with_coverage(
        mut self,
        coverage: Option<Arc<crate::photo_coverage::Coverage>>,
    ) -> Self {
        self.coverage = coverage;
        self
    }
    pub(crate) fn coverage(&self) -> Option<&crate::photo_coverage::Coverage> {
        self.coverage.as_deref()
    }

    pub(crate) fn token(&self) -> DevelopmentToken {
        self.token
    }
    pub(crate) fn image(&self, coarse: bool) -> &Arc<LinearImage> {
        if coarse { &self.overview } else { &self.image }
    }
    pub(crate) fn recipe(&self) -> &DevelopmentRecipe {
        &self.recipe
    }
    pub(crate) fn matches_source(&self, image: &Arc<LinearImage>) -> bool {
        Arc::ptr_eq(&self.image, image)
    }

    pub(crate) fn export(
        &self,
        path: &Path,
        settings: &ExportSettings,
        cancelled: &AtomicBool,
    ) -> Result<ExportReport> {
        strehl_edit::export_image_with_coverage(
            path,
            &self.image,
            &self.recipe,
            settings,
            cancelled,
            self.coverage.as_ref().map(|mask| mask.values.as_ref()),
        )
    }

    pub(crate) fn thumbnail(&self, side: u32) -> Result<(u32, u32, Vec<u8>)> {
        let (width, height, mut rgb) =
            self.image
                .render_region_sdr8(&self.recipe, [0., 0.], [1., 1.], side)?;
        if let Some(coverage) = &self.coverage {
            coverage.apply_rgb([width, height], &mut rgb);
        }
        Ok((width, height, rgb))
    }
}

#[cfg(test)]
#[path = "development-job-tests.rs"]
mod tests;
