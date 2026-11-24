//! The subject of a capture, found automatically (plan S2,
//! `docs/proposals/2026-11-subject-highlights-and-detail-plan.md`).
//!
//! - [`raw_frame_cells`] per RAW exposure, with the injected noise model
//!   passed as a variance function; [`assemble`] over the planes; then
//!   [`quiet`] once and [`select`] per slider setting (re-thresholding reads
//!   only the stored [`Evidence`]).
//! - [`live_view_subject`] does the same on live-view JPEG frames for a loose
//!   first outline.
//! - [`outline`]: rings normalised to the active area and their raster.
//!
//! Ported from the prototype `experiments/subject-highlights-detail-2026-11-23/
//! subject-mask.py` and `live-mask.py`; deviations are listed in
//! `experiments/subject-highlights-detail-2026-11-23/impl/mask/results.md`.

#[path = "subject-evidence.rs"]
pub mod evidence;
#[path = "subject-live.rs"]
pub mod live;
#[path = "subject-morph.rs"]
mod morph;
#[path = "subject-outline.rs"]
pub mod outline;
#[path = "subject-select.rs"]
pub mod select;
#[path = "subject-trace.rs"]
mod trace;

pub use evidence::{
    CfaView, Evidence, Fitted, FrameCells, Layout, PlaneRef, RAW_CELL_PX, Registration, assemble,
    raw_frame_cells,
};
pub use live::{LiveFrame, live_frame_cells, live_view_evidence, live_view_subject};
pub use outline::{MAX_RING_POINTS, Ring, Source, ThresholdKind, rasterize, ring_area};
pub use select::{Depth, Params, Quiet, Selection, Stats, quiet, select};

/// Layout of RAW evidence over an active area of `width` x `height` sensor
/// pixels: 8 px cells, normalised to the active area.
pub fn raw_layout(width: usize, height: usize) -> Layout {
    Layout {
        source: Source::Raw,
        cell_px: RAW_CELL_PX as f32,
        cell_norm: [
            RAW_CELL_PX as f64 / width as f64,
            RAW_CELL_PX as f64 / height as f64,
        ],
        active_px: [width as u32, height as u32],
    }
}

#[cfg(test)]
#[path = "subject-tests.rs"]
mod tests;
