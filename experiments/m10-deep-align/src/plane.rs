//! Green-luma CFA plane extraction and the two resamplers the harness needs.
//!
//! Ported unchanged in behaviour from `experiments/m3-drift`, so that M10's
//! edges are produced by the same estimator that produced M3's and M6's
//! numbers. `experiments/m3-drift` is under another agent's hand and is not
//! edited here; M9's precedent (`experiments/m9-support/src/measures.rs`) is to
//! keep a milestone's variants inside its own crate.

use rayon::prelude::*;
use std::path::Path;

pub struct Plane {
    pub d: Vec<f32>,
    pub w: usize,
    pub h: usize,
}

impl Plane {
    /// Half-diagonal of the plane: the radius of the plane corner from the
    /// plane centre. Every corner-error figure in M10 is quoted at this radius.
    pub fn corner_radius(&self) -> f64 {
        ((self.w as f64).powi(2) + (self.h as f64).powi(2)).sqrt() * 0.5
    }
}

/// Black-subtracted green luma at CFA plane resolution (active area / 2).
///
/// RGGB: within each 2x2 quad, G1 is at (1,0) and G2 at (0,1). AGENTS.md rule 7
/// -- the decoded buffer is zero-padded to 7168x5120 and only the active area
/// is real, so the active rectangle is taken from the decoder, never assumed.
pub fn green_plane(path: &Path) -> Result<Plane, String> {
    let img = rawler::decode_file(path).map_err(|e| format!("{e:?}"))?;
    let data = match img.data {
        rawler::RawImageData::Integer(d) => d,
        rawler::RawImageData::Float(_) => return Err("float raw".into()),
    };
    let stride = img.width;
    let (ax, ay, aw, ah) = img
        .active_area
        .map(|r| (r.p.x, r.p.y, r.d.w, r.d.h))
        .unwrap_or((0, 0, img.width, img.height));
    let black = img
        .blacklevel
        .levels
        .first()
        .map(|r| r.n as f32 / r.d as f32)
        .unwrap_or(0.0);

    let (pw, ph) = (aw / 2, ah / 2);
    let mut out = vec![0f32; pw * ph];
    for py in 0..ph {
        let r0 = (ay + 2 * py) * stride + ax;
        let r1 = (ay + 2 * py + 1) * stride + ax;
        for px in 0..pw {
            let g1 = data[r0 + 2 * px + 1] as f32 - black;
            let g2 = data[r1 + 2 * px] as f32 - black;
            out[py * pw + px] = 0.5 * (g1 + g2);
        }
    }
    Ok(Plane {
        d: out,
        w: pw,
        h: ph,
    })
}

pub fn downsample(p: &Plane, f: usize) -> Plane {
    let (w, h) = (p.w / f, p.h / f);
    let mut out = vec![0f32; w * h];
    let inv = 1.0 / (f * f) as f32;
    out.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            let mut s = 0f32;
            for dy in 0..f {
                let base = (y * f + dy) * p.w + x * f;
                for dx in 0..f {
                    s += p.d[base + dx];
                }
            }
            *o = s * inv;
        }
    });
    Plane { d: out, w, h }
}

pub fn bilinear(p: &Plane, x: f32, y: f32) -> f32 {
    let x = x.clamp(0.0, (p.w - 2) as f32);
    let y = y.clamp(0.0, (p.h - 2) as f32);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let (fx, fy) = (x - x0 as f32, y - y0 as f32);
    let i = y0 * p.w + x0;
    let a = p.d[i] * (1.0 - fx) + p.d[i + 1] * fx;
    let b = p.d[i + p.w] * (1.0 - fx) + p.d[i + p.w + 1] * fx;
    a * (1.0 - fy) + b * fy
}
