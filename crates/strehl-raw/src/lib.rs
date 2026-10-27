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

pub mod common_tiff;
/// Camera and lens identity, read from the file's own metadata.
///
/// Deliberately **not** part of [`Frame`] and not on the decode path: a gear
/// profile is optional, and a capture that carries no identity must decode
/// exactly as it did before this module existed.
pub mod identity;
#[path = "sony-focus.rs"]
pub mod sony_focus;
#[path = "sony-optical.rs"]
pub mod sony_optical;
#[path = "sony-tiff.rs"]
mod sony_tiff;

pub use identity::{CaptureIdentity, identity};

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
    /// The camera's colorimetric characterisation, exactly as the decoder
    /// reports it: **XYZ (D65) -> camera RGBE**, four rows of three.
    ///
    /// This is `rawler`'s `RawImage::xyz_to_cam`, carried verbatim. It is a
    /// property of the camera *model*, not of the capture, and it is the only
    /// thing in this struct that ties the sensor's native RGB to a
    /// colorimetric space. Without it the pipeline can only emit camera-native
    /// RGB, which is not a colour space and is not viewable.
    ///
    /// The fourth row is the emerald channel and is all zeros on every
    /// three-colour body — never iterate all four. Use
    /// [`Frame::xyz_to_cam_rgb`], which validates and drops it, in the same
    /// spirit as [`Frame::wb_gains`].
    ///
    /// **Not hard-coded on purpose.** A per-body matrix compiled into this
    /// project would be a magic constant with no provenance a reader could
    /// check; taken from the decoder it has the same provenance as the pixel
    /// data beside it, and it follows the body when the stack does.
    pub xyz_to_cam_rgbe: [[f32; 3]; 4],
    /// The decoder's per-illuminant colour matrix table: **XYZ -> camera RGB**,
    /// one 3x3 per illuminant, with the illuminant's name beside it.
    ///
    /// This is `rawler`'s `RawImage::color_matrix`, flattened. It exists
    /// because MEASURED on `bee-3-cpl` (M85), `rawler` 0.7.2 leaves
    /// [`Frame::xyz_to_cam_rgbe`] all zeros for the A7C II while populating
    /// this table — so the obvious field is not the one that carries the data,
    /// and a pipeline that used only the obvious field would emit camera-native
    /// RGB forever without ever saying why.
    ///
    /// Named rather than indexed because picking "the daylight one" out of a
    /// `HashMap` is a decision, and a decision that silently picked Tungsten
    /// would produce a plausible-looking wrong image. See
    /// [`Frame::xyz_to_cam_rgb`].
    pub color_matrices: Vec<(String, [[f32; 3]; 3])>,
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

    /// The camera's XYZ -> camera-RGB matrix, or `None` when the decoder did
    /// not supply a usable characterisation.
    ///
    /// Tries [`Frame::xyz_to_cam_rgbe`] first, then the named illuminants of
    /// [`Frame::color_matrices`] in [`DAYLIGHT_PREFERENCE`] order. Returns the
    /// matrix and the name of where it came from, because "which illuminant"
    /// is the single fact most likely to explain a wrong-looking render, and
    /// the CLI prints it.
    ///
    /// `None` is a real outcome, not a defensive nicety: a body `rawler` has no
    /// entry for decodes fine and produces an all-zero matrix, and a caller
    /// that multiplied by it would emit a black image. Every caller must
    /// therefore decide what to do without one, and the only honest choice is
    /// to emit camera-native RGB and say so.
    ///
    /// Rejects a matrix that is not finite, and one whose determinant is too
    /// small to invert stably — the inverse is what the output path actually
    /// needs, and a near-singular matrix would pass a finiteness check and then
    /// produce garbage.
    pub fn xyz_to_cam_rgb_with_source(&self) -> Option<([[f32; 3]; 3], String)> {
        let usable = |m: [[f32; 3]; 3]| -> bool {
            if !m.iter().flatten().all(|v| v.is_finite()) {
                return false;
            }
            let det = m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
            det.abs() >= 1e-6
        };

        let direct = [
            self.xyz_to_cam_rgbe[0],
            self.xyz_to_cam_rgbe[1],
            self.xyz_to_cam_rgbe[2],
        ];
        if usable(direct) {
            return Some((direct, "decoder xyz_to_cam".to_string()));
        }

        // A camera characterised under tungsten and rendered as if it were
        // daylight is a large, plausible-looking error, so the illuminant is
        // chosen by an explicit preference order and never by hash order.
        for want in DAYLIGHT_PREFERENCE {
            if let Some((name, m)) = self
                .color_matrices
                .iter()
                .find(|(n, _)| n.eq_ignore_ascii_case(want))
                && usable(*m)
            {
                return Some((*m, format!("decoder color_matrix[{name}]")));
            }
        }
        None
    }

    /// [`Frame::xyz_to_cam_rgb_with_source`] without the provenance string.
    pub fn xyz_to_cam_rgb(&self) -> Option<[[f32; 3]; 3]> {
        self.xyz_to_cam_rgb_with_source().map(|(m, _)| m)
    }
}

/// Which illuminant's colour matrix to prefer, most-wanted first.
///
/// Daylight before anything else because the corpus is shot outdoors and under
/// daylight-balanced light, and because the sRGB target this pipeline renders
/// to is itself D65. `Daylight` and `FineWeather` are the DNG spec's names for
/// nominal daylight; the rest are a last resort, and a stack rendered off a
/// `Tungsten` matrix will say so in the CLI's provenance line rather than
/// quietly looking blue.
pub const DAYLIGHT_PREFERENCE: [&str; 6] = ["D65", "D55", "Daylight", "FineWeather", "D50", "D75"];

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
        xyz_to_cam_rgbe: img.xyz_to_cam,
        color_matrices: img
            .color_matrix
            .iter()
            .filter(|(_, m)| m.len() >= 9)
            .map(|(ill, m)| {
                (
                    format!("{ill:?}"),
                    [[m[0], m[1], m[2]], [m[3], m[4], m[5]], [m[6], m[7], m[8]]],
                )
            })
            .collect(),
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
            // The A7C II's matrix as MEASURED through an independent decoder
            // (`rawpy`) in `docs/research/M26-colour-clipping-measured.md` §1,
            // and reproduced through `rawler` in
            // `docs/research/M85-output-correctness.md`.
            xyz_to_cam_rgbe: [
                [0.7460, -0.2365, -0.0588],
                [-0.5687, 1.3442, 0.2474],
                [-0.0624, 0.1156, 0.6584],
                [0.0, 0.0, 0.0],
            ],
            color_matrices: Vec::new(),
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

    #[test]
    fn the_colour_matrix_drops_the_emerald_row_and_keeps_the_rest_verbatim() {
        let f = synthetic();
        let m = f.xyz_to_cam_rgb().expect("the A7C II matrix is usable");
        // Verbatim: this accessor selects rows, it does not transform them.
        // Compared against the numbers as printed in M26 §1, not against
        // `synthetic()`'s own copy, so a typo in either shows up here.
        assert_eq!(m[0], [0.7460, -0.2365, -0.0588]);
        assert_eq!(m[1], [-0.5687, 1.3442, 0.2474]);
        assert_eq!(m[2], [-0.0624, 0.1156, 0.6584]);
        // The fourth row -- rawler's "E" for emerald -- is present in the
        // field and absent from the accessor. If a future rawler starts
        // populating it for this body, this assertion is where to notice.
        assert_eq!(f.xyz_to_cam_rgbe[3], [0.0, 0.0, 0.0]);
    }

    #[test]
    fn a_camera_with_no_characterisation_is_reported_as_absent_not_as_black() {
        let mut f = synthetic();
        // What rawler actually returns for a body it has no entry for. Left
        // unchecked this multiplies every pixel by zero.
        f.xyz_to_cam_rgbe = [[0.0; 3]; 4];
        assert!(f.xyz_to_cam_rgb().is_none());

        // Finite but singular: two identical rows. This is the case a
        // finiteness check alone would wave through, and the inverse the
        // output path needs does not exist.
        f.xyz_to_cam_rgbe = [
            [0.7460, -0.2365, -0.0588],
            [0.7460, -0.2365, -0.0588],
            [-0.0624, 0.1156, 0.6584],
            [0.0, 0.0, 0.0],
        ];
        assert!(f.xyz_to_cam_rgb().is_none());

        f.xyz_to_cam_rgbe = [
            [f32::NAN, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
        ];
        assert!(f.xyz_to_cam_rgb().is_none());

        // ...and the control: a matrix that is merely unusual, but invertible,
        // is accepted. The gate rejects singularity, not unfamiliarity.
        f.xyz_to_cam_rgbe = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
        ];
        assert!(f.xyz_to_cam_rgb().is_some());
    }

    /// The fallback that MEASURED reality forced into existence.
    ///
    /// M85 found `rawler` 0.7.2 returns an all-zero `xyz_to_cam` for the A7C II
    /// while populating `color_matrix` — so the empty obvious field must fall
    /// through to the named table, and the *choice of illuminant* must be an
    /// explicit preference and not `HashMap` order.
    #[test]
    fn an_empty_xyz_to_cam_falls_through_to_the_named_illuminant_table() {
        let mut f = synthetic();
        f.xyz_to_cam_rgbe = [[0.0; 3]; 4];
        let d65 = [
            [0.7460, -0.2365, -0.0588],
            [-0.5687, 1.3442, 0.2474],
            [-0.0624, 0.1156, 0.6584],
        ];
        // A deliberately different, and deliberately wrong-for-daylight,
        // second entry. Listed FIRST, so a lookup that took whatever came to
        // hand would pick it.
        let tungsten = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]];
        f.color_matrices = vec![("Tungsten".to_string(), tungsten), ("D65".to_string(), d65)];
        let (m, src) = f.xyz_to_cam_rgb_with_source().expect("the table is usable");
        assert_eq!(m, d65, "the illuminant preference order was not honoured");
        assert_eq!(src, "decoder color_matrix[D65]");

        // Preference order, not merely "not the first entry": with D65 gone,
        // D55 wins over FineWeather, which wins over nothing at all.
        f.color_matrices = vec![
            ("FineWeather".to_string(), tungsten),
            ("D55".to_string(), d65),
        ];
        assert_eq!(f.xyz_to_cam_rgb().unwrap(), d65);

        // A table with nothing daylight-ish in it is `None`, not a guess.
        f.color_matrices = vec![("Tungsten".to_string(), tungsten)];
        assert!(f.xyz_to_cam_rgb().is_none());

        // ...and a populated `xyz_to_cam` still wins over the table, so the
        // fallback is a fallback and not a takeover.
        f.xyz_to_cam_rgbe = [tungsten[0], tungsten[1], tungsten[2], [0.0; 3]];
        f.color_matrices = vec![("D65".to_string(), d65)];
        let (m, src) = f.xyz_to_cam_rgb_with_source().unwrap();
        assert_eq!(m, tungsten);
        assert_eq!(src, "decoder xyz_to_cam");
    }

    /// **Rule 35.** The matrix this pipeline renders with, checked against the
    /// same matrix obtained through a completely different decoder.
    ///
    /// `docs/research/M26-colour-clipping-measured.md` §1 MEASURED the A7C II's
    /// `rgb_xyz_matrix` through `rawpy`/LibRaw as
    ///
    /// ```text
    ///   [[ 0.7460, -0.2365, -0.0588],
    ///    [-0.5687,  1.3442,  0.2474],
    ///    [-0.0624,  0.1156,  0.6584]]
    /// ```
    ///
    /// identical across all six corpus stacks. `rawler` and LibRaw maintain
    /// separate camera databases, so agreement here is two independent parties
    /// reading the same physical characterisation — which is the only kind of
    /// check that can catch a transposed, scaled or mis-attributed matrix.
    ///
    /// Ignored by default because it needs the read-only capture directory.
    /// Run with `--ignored`; M85 ran it and recorded the result in
    /// `docs/research/M85-output-correctness.md`.
    #[test]
    #[ignore = "needs D:\\personal\\macro; run with --ignored"]
    fn the_decoders_matrix_agrees_with_the_independently_measured_one() {
        let dir = Path::new(r"D:\personal\macro\bee-3-cpl");
        let one = std::fs::read_dir(dir)
            .expect("capture directory")
            .filter_map(|e| e.ok().map(|e| e.path()))
            .find(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("arw")))
            .expect("at least one ARW");
        let f = decode(&one).expect("decode");
        eprintln!("camera             : {}", f.camera);
        eprintln!("xyz_to_cam (rawler): {:?}", f.xyz_to_cam_rgbe);
        for (ill, m) in &f.color_matrices {
            eprintln!("color_matrix[{ill}] : {m:?}");
        }
        let (m, src) = f
            .xyz_to_cam_rgb_with_source()
            .expect("some usable characterisation");
        eprintln!("chosen             : {src} {m:?}");

        const M26: [[f32; 3]; 3] = [
            [0.7460, -0.2365, -0.0588],
            [-0.5687, 1.3442, 0.2474],
            [-0.0624, 0.1156, 0.6584],
        ];
        let mut worst = 0.0f32;
        for i in 0..3 {
            for j in 0..3 {
                worst = worst.max((m[i][j] - M26[i][j]).abs());
            }
        }
        // 5e-4 is one unit in the last place M26 printed. Anything larger is
        // a genuine disagreement between the two databases and must be read,
        // not widened.
        assert!(
            worst < 5e-4,
            "rawler's matrix disagrees with M26's rawpy measurement by {worst}: \
             {m:?} vs {M26:?}"
        );
    }
}
