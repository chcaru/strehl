//! RAW decode, and packing the active area into the layout the kernel reads.
//!
//! Backed by `rawler`, which is **LGPL-2.1**: we link it, we do not read it.
//!
//! Project rule 7: `rawler` returns 7168x5120 for the A7C II but fills only the
//! 7032x4688 active area, and the rest is synthetic zeros. Every buffer this
//! module hands out contains the active area **and nothing else**, so no
//! statistic downstream can accidentally measure padding.

use std::path::{Path, PathBuf};

use rawler::decoders::RawDecodeParams;
use rawler::rawsource::RawSource;

use crate::cpu::PlaneGeometry;

/// One decoded frame, packed.
///
/// `words[y * row_words + j]` holds active samples `x = 2j` (low 16 bits) and
/// `x = 2j + 1` (high 16 bits) of active row `y`. On a little-endian host the
/// same allocation reinterprets as `&[u16]` of the packed active area, which is
/// what the CPU reference reads, so CPU and GPU are provably fed identical
/// bytes.
pub struct PackedFrame {
    pub words: Vec<u32>,
    pub active_w: usize,
    pub active_h: usize,
    pub row_words: usize,
    pub black: f32,
    pub white: f32,
    pub iso: Option<f32>,
    pub camera: String,
    pub path: PathBuf,
}

impl PackedFrame {
    pub fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: self.active_w / 2,
            height: self.active_h / 2,
        }
    }
    pub fn samples(&self) -> &[u16] {
        bytemuck::cast_slice(&self.words)
    }
    pub fn bytes(&self) -> usize {
        self.words.len() * 4
    }
}

pub fn decode(path: &Path) -> Result<PackedFrame, String> {
    let source = RawSource::new(path).map_err(|e| format!("{}: {e}", path.display()))?;
    let params = RawDecodeParams::default();
    let img = rawler::decode(&source, &params).map_err(|e| format!("{}: {e:?}", path.display()))?;

    let iso = rawler::get_decoder(&source)
        .and_then(|d| d.raw_metadata(&source, &params))
        .ok()
        .and_then(|m| m.exif.iso_speed_ratings.map(u32::from).or(m.exif.iso_speed))
        .map(|v| v as f32);

    let pattern = img.camera.cfa.name.clone();
    if pattern != "RGGB" {
        return Err(format!("{}: CFA {pattern} is not RGGB", path.display()));
    }
    let data = match img.data {
        rawler::RawImageData::Integer(d) => d,
        rawler::RawImageData::Float(_) => return Err(format!("{}: float RAW", path.display())),
    };
    let (ax, ay, aw, ah) = match img.active_area {
        Some(r) => (r.p.x, r.p.y, r.d.w, r.d.h),
        None => return Err(format!("{}: no active area declared", path.display())),
    };
    // Even dimensions only: a partial quad has no plane pixel.
    let aw = aw & !1;
    let ah = ah & !1;
    let stride = img.width;
    let black = img
        .blacklevel
        .levels
        .first()
        .map(|r| r.n as f32 / r.d as f32)
        .unwrap_or(0.0);
    let white = img.whitelevel.0.first().copied().unwrap_or(u16::MAX as u32) as f32;

    let row_words = aw / 2;
    let mut words = vec![0u32; row_words * ah];
    for y in 0..ah {
        let src = &data[(ay + y) * stride + ax..(ay + y) * stride + ax + aw];
        let dst = &mut words[y * row_words..(y + 1) * row_words];
        for (j, o) in dst.iter_mut().enumerate() {
            *o = src[2 * j] as u32 | ((src[2 * j + 1] as u32) << 16);
        }
    }

    Ok(PackedFrame {
        words,
        active_w: aw,
        active_h: ah,
        row_words,
        black,
        white,
        iso,
        camera: img.clean_model.clone(),
        path: path.to_path_buf(),
    })
}

/// Every `.ARW` in a directory, sorted, read-only.
pub fn list_arw(dir: &Path, limit: Option<usize>) -> Result<Vec<PathBuf>, String> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .map_err(|e| format!("{}: {e}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    v.sort();
    if let Some(n) = limit {
        v.truncate(n);
    }
    if v.is_empty() {
        return Err(format!("{}: no .ARW files", dir.display()));
    }
    Ok(v)
}
