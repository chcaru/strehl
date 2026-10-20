//! Shared, versioned development recipes. Image data remains linear f32 until export.
//! These controls are Strehl's rendering operators, not Adobe's proprietary process.

mod avif;
mod icc;
mod image;
mod publish;
mod recipe;
mod xmp;

pub use avif::{HdrExportReport, export_hdr_avif};
pub use image::{
    DisplayBaseline, ImageOrigin, LinearImage, load_tiff, save_linear_tiff, save_sdr_tiff,
};
pub use recipe::{
    Adjustments, DevelopmentRecipe, HdrSettings, RegionAdjustment, RegionShape, SourceRange,
};
pub use xmp::{XmpImport, import_xmp};
