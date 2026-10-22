//! Shared, versioned development recipes. Image data remains linear f32 until export.
//! These controls are Strehl's rendering operators, not Adobe's proprietary process.

mod adaptive;
mod avif;
mod color;
#[path = "display-region.rs"]
mod display_region;
mod export;
mod icc;
mod image;
#[path = "learned-asset.rs"]
pub mod learned_asset;
#[path = "learned-profile.rs"]
pub mod learned_profile;
#[path = "learned-scene.rs"]
pub mod learned_scene;
#[path = "learned-scene-asset.rs"]
pub mod learned_scene_asset;
#[path = "learned-store.rs"]
pub mod learned_store;
mod publish;
mod recipe;
mod xmp;

pub use adaptive::{
    AdaptiveChange, AdaptiveIntent, AdaptiveStatistics, AdaptiveSuggestion, HighlightDiagnosis,
    analyze_adaptive, analyze_adaptive_region, analyze_adaptive_with_parameters,
};
pub use avif::{HdrExportReport, export_hdr_avif};
pub use color::OutputColorSpace;
pub use display_region::{DisplayRegion, DisplayRegionRequest};
pub use export::{ExportFormat, ExportReport, ExportSettings, export_image};
pub use image::{
    DisplayBaseline, ImageOrigin, LinearImage, load_tiff, load_tiff_thumbnail, save_linear_tiff,
    save_sdr_tiff,
};
pub use recipe::{
    AdaptiveParameters, AdaptiveToneRange, Adjustments, DevelopmentRecipe, HdrSettings,
    MAX_SPATIAL_TREATMENTS, RegionAdjustment, RegionShape, SourceRange, SpatialTreatment,
};
pub use xmp::{XmpImport, import_xmp};
