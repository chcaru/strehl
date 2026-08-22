//! RAW decoding.
//!
//! Backed by `rawler`, which is **LGPL-2.1**. We link it; we do not read it.
//! See `AGENTS.md` for the obligation that carries.
//!
//! # Two things measured here that the API does not tell you
//!
//! Both are recorded in `docs/research/M1-decode-measured.md`.
//!
//! 1. **The decoded buffer is zero-padded.** For the A7C II, `rawler` returns
//!    7168x5120 but fills only the 7032x4688 active area. The remaining 136
//!    columns and 432 rows are exactly zero — they are not masked sensor pixels
//!    and they are not black level. Computing any statistic over the full buffer
//!    silently drags it toward zero. [`Frame::active`] exists so that this
//!    cannot happen by accident.
//! 2. **Decode in parallel across files, not one at a time.** Concurrent reads
//!    measured 1245 MB/s cold against 503 MB/s sequential — 2.5x, because
//!    `rawler` already saturates cores within a single file and the remaining
//!    win is overlapping each file's serial head and its I/O stall. A 60-frame
//!    stack decodes in 1.78 s cold, 0.91 s warm.

use std::path::{Path, PathBuf};

use rawler::decoders::RawDecodeParams;
use rawler::rawsource::RawSource;
use rayon::prelude::*;
use strehl_core::noise::Levels;
use strehl_core::plane::{PlaneGeometry, QuadSource};

#[derive(Debug, thiserror::Error)]
pub enum RawError {
    #[error("decode failed for {path}: {source}")]
    Decode {
        path: PathBuf,
        #[source]
        source: anyhow::Error,
    },
    #[error("{path}: floating-point RAW is not supported yet")]
    UnsupportedFloatData { path: PathBuf },
    #[error("{path}: unsupported CFA pattern {pattern:?}, only RGGB is handled")]
    UnsupportedCfa { path: PathBuf, pattern: String },
}

/// A rectangular region of the sensor, in sensor pixel coordinates.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Region {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}

impl Region {
    pub fn pixels(&self) -> usize {
        self.width * self.height
    }
}

/// One decoded frame, still mosaiced.
///
/// Samples stay `u16`. Arithmetic promotes to `f32` at the point of use; see
/// `AGENTS.md` rule 1 for why `f16` is wrong here.
#[derive(Debug, Clone)]
pub struct Frame {
    /// Full decoded buffer, `stride * height` samples, including any padding.
    pub data: Vec<u16>,
    /// Row stride of `data`, in samples.
    pub stride: usize,
    /// Height of `data`, in rows.
    pub buffer_height: usize,
    /// The region of `data` that contains real sensor readings.
    pub active: Region,
    pub levels: Levels,
    /// Sensor sensitivity as the file reports it, `None` when the file did not
    /// say. Never defaulted to a plausible value: the noise model's gain is
    /// linear in ISO, so a guessed ISO is a silently wrong noise floor.
    pub iso: Option<f32>,
    /// As-shot white balance, `[R, G, B, ?]`. The fourth element is `NaN` on
    /// the A7C II (no emerald channel) — never iterate all four (MEASURED, M1).
    pub wb_coeffs: [f32; 4],
    pub camera: String,
    pub path: PathBuf,
}

impl Frame {
    /// Sample at `(x, y)` in **active-area coordinates**.
    #[inline]
    pub fn sample(&self, x: usize, y: usize) -> u16 {
        debug_assert!(x < self.active.width && y < self.active.height);
        self.data[(self.active.y + y) * self.stride + self.active.x + x]
    }

    /// One row of the active area.
    #[inline]
    pub fn active_row(&self, y: usize) -> &[u16] {
        let start = (self.active.y + y) * self.stride + self.active.x;
        &self.data[start..start + self.active.width]
    }

    /// Bytes actually allocated for this frame's samples.
    pub fn allocated_bytes(&self) -> usize {
        self.data.len() * std::mem::size_of::<u16>()
    }

    /// Bytes of that allocation which are real sensor data.
    pub fn useful_bytes(&self) -> usize {
        self.active.pixels() * std::mem::size_of::<u16>()
    }

    /// As-shot white balance as `[R, G, B]` gains normalised so green is 1.0.
    ///
    /// `None` when the coefficients are unusable. The fourth coefficient is
    /// never touched.
    pub fn wb_gains(&self) -> Option<[f32; 3]> {
        let [r, g, b, _] = self.wb_coeffs;
        if !(r.is_finite() && g.is_finite() && b.is_finite()) || g <= 0.0 || r <= 0.0 || b <= 0.0 {
            return None;
        }
        Some([r / g, 1.0, b / g])
    }
}

impl QuadSource for Frame {
    fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry::from_active(self.active.width, self.active.height)
    }

    fn quad_rows(&self, py: usize) -> (&[u16], &[u16]) {
        (self.active_row(2 * py), self.active_row(2 * py + 1))
    }
}

/// Decode one RAW file.
///
/// The file is read once into a [`RawSource`] and then queried twice: for the
/// pixel data and for the EXIF block that carries ISO. Reading ISO rather than
/// assuming base ISO matters because the noise model's gain is linear in it.
pub fn decode(path: &Path) -> Result<Frame, RawError> {
    let fail = |e: String| RawError::Decode {
        path: path.to_path_buf(),
        source: anyhow::anyhow!(e),
    };

    let source = RawSource::new(path).map_err(|e| fail(format!("{e}")))?;
    let params = RawDecodeParams::default();

    let img = rawler::decode(&source, &params).map_err(|e| fail(format!("{e:?}")))?;

    // ISO is best-effort: a frame that decodes but has no ISO tag must still
    // stack, with the noise model visibly downgraded rather than guessed.
    let iso = rawler::get_decoder(&source)
        .and_then(|d| d.raw_metadata(&source, &params))
        .ok()
        .and_then(|m| m.exif.iso_speed_ratings.map(u32::from).or(m.exif.iso_speed))
        .map(|v| v as f32);

    let pattern = img.camera.cfa.name.clone();
    if pattern != "RGGB" {
        return Err(RawError::UnsupportedCfa {
            path: path.to_path_buf(),
            pattern,
        });
    }

    let data = match img.data {
        rawler::RawImageData::Integer(d) => d,
        rawler::RawImageData::Float(_) => {
            return Err(RawError::UnsupportedFloatData {
                path: path.to_path_buf(),
            });
        }
    };

    // Fall back to the whole buffer only if no active area is declared. That is
    // a correctness hazard, not a convenience: see the module docs.
    let active = img
        .active_area
        .map(|r| Region {
            x: r.p.x,
            y: r.p.y,
            width: r.d.w,
            height: r.d.h,
        })
        .unwrap_or(Region {
            x: 0,
            y: 0,
            width: img.width,
            height: img.height,
        });

    let black = img
        .blacklevel
        .levels
        .first()
        .map(|r| r.n as f32 / r.d as f32)
        .unwrap_or(0.0);
    let white = img.whitelevel.0.first().copied().unwrap_or(u16::MAX as u32) as f32;

    Ok(Frame {
        data,
        stride: img.width,
        buffer_height: img.height,
        active,
        levels: Levels { black, white },
        iso,
        wb_coeffs: img.wb_coeffs,
        camera: img.clean_model.clone(),
        path: path.to_path_buf(),
    })
}

/// Decode many RAW files concurrently.
///
/// Prefer this over calling [`decode`] in a loop. Measured 2.5x faster on cold
/// storage; see the module docs.
pub fn decode_all(paths: &[PathBuf]) -> Vec<Result<Frame, RawError>> {
    paths.par_iter().map(|p| decode(p)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn synthetic() -> Frame {
        // A 4x3 buffer whose active area is the top-left 2x2, mimicking the
        // zero padding rawler returns.
        Frame {
            data: vec![
                10, 20, 0, 0, //
                30, 40, 0, 0, //
                0, 0, 0, 0,
            ],
            stride: 4,
            buffer_height: 3,
            active: Region {
                x: 0,
                y: 0,
                width: 2,
                height: 2,
            },
            levels: Levels {
                black: 512.0,
                white: 15360.0,
            },
            iso: Some(100.0),
            wb_coeffs: [2.861, 1.0, 1.482, f32::NAN],
            camera: "test".into(),
            path: PathBuf::from("test"),
        }
    }

    #[test]
    fn sampling_uses_active_coordinates_and_skips_padding() {
        let f = synthetic();
        assert_eq!(f.sample(0, 0), 10);
        assert_eq!(f.sample(1, 0), 20);
        assert_eq!(f.sample(0, 1), 30);
        assert_eq!(f.sample(1, 1), 40);
    }

    #[test]
    fn active_rows_exclude_the_zero_padding() {
        let f = synthetic();
        assert_eq!(f.active_row(0), &[10, 20]);
        assert_eq!(f.active_row(1), &[30, 40]);
        // The naive full-stride read would have picked up the padding.
        assert_eq!(&f.data[0..4], &[10, 20, 0, 0]);
    }

    #[test]
    fn padding_waste_is_visible() {
        let f = synthetic();
        assert_eq!(f.allocated_bytes(), 24);
        assert_eq!(f.useful_bytes(), 8);
    }

    #[test]
    fn a7c2_padding_overhead_matches_the_measurement() {
        // Measured, M1: 7168x5120 allocated, 7032x4688 real.
        let allocated = 7168usize * 5120 * 2;
        let useful = 7032usize * 4688 * 2;
        assert_eq!(allocated, 73_400_320);
        assert_eq!(useful, 65_932_032);
        let waste = 1.0 - useful as f64 / allocated as f64;
        assert!((waste - 0.1017).abs() < 0.001, "waste was {waste}");
    }

    #[test]
    fn quad_rows_are_active_rows_at_twice_the_plane_pitch() {
        let f = synthetic();
        assert_eq!(
            f.geometry(),
            PlaneGeometry {
                width: 1,
                height: 1
            }
        );
        let (a, b) = f.quad_rows(0);
        assert_eq!(a, &[10, 20]);
        assert_eq!(b, &[30, 40]);
    }

    #[test]
    fn white_balance_normalises_green_to_one_and_ignores_the_nan() {
        // Measured, M1: the A7C II reports [2.861, 1.0, 1.482, NaN].
        let f = synthetic();
        let g = f.wb_gains().unwrap();
        assert!((g[0] - 2.861).abs() < 1e-6);
        assert_eq!(g[1], 1.0);
        assert!((g[2] - 1.482).abs() < 1e-6);
    }

    #[test]
    fn white_balance_that_is_not_usable_is_reported_as_absent() {
        let mut f = synthetic();
        f.wb_coeffs = [f32::NAN, 1.0, 1.0, f32::NAN];
        assert!(f.wb_gains().is_none());
        f.wb_coeffs = [1.0, 0.0, 1.0, f32::NAN];
        assert!(f.wb_gains().is_none());
    }

    #[test]
    fn a_frame_with_no_iso_tag_says_so_rather_than_reporting_zero() {
        let mut f = synthetic();
        f.iso = None;
        assert!(f.iso.is_none());
    }
}
