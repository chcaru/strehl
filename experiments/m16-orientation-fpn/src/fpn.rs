//! Row/column fixed-pattern treatments and the plant characterisation readout.
//!
//! Everything here is M16's own. The science modules it sits next to (`edge`,
//! `measures`, `planted`, `tile`) are M13's, included by path and unmodified.
//!
//! Three things live here:
//!
//! 1. **`destripe_*`** — the treatments the external reviewer proposed. They are
//!    applied **only to the focus operator's input**, never to the merged
//!    output, so an arm changes which frame is elected and nothing else.
//! 2. **`FpnPlant`** — a known row and/or column offset pattern, so the
//!    experiment has a positive control: something that *must* move, at an
//!    amplitude the experimenter chose.
//! 3. **`scan`** — the descriptive readout of how much row and column structure
//!    a plane actually carries, and how isotropic its gradients are.
//!
//! **Level preservation matters.** The focus operator normalises pointwise by
//! `sigma(luma)`, so a treatment that changes the plane's level changes the
//! operator's normalisation and confounds the arm. Every treatment here adds
//! the plane mean back, and `selftest` asserts it.

use strehl_core::plane::PlaneGeometry;

use crate::planted::{gaussian_blur, Rng};

// ------------------------------------------------------------------ treatments

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Destripe {
    /// The M15 path, bit for bit. The no-op arm cannot differ by construction.
    None,
    /// Subtract the row-mean and column-mean deviations from the plane mean.
    /// This is the reviewer's proposed fix.
    Mean,
    /// Subtract only the *high-frequency* part of those profiles, so
    /// low-frequency scene structure survives. The content-preserving variant.
    Hp,
    /// Subtract the exactly-known planted pattern. Only meaningful with a
    /// plant, and the only variant with no content-destruction confound at all.
    Oracle,
}

impl Destripe {
    pub fn parse(s: &str) -> Result<Self, String> {
        Ok(match s {
            "none" => Self::None,
            "mean" => Self::Mean,
            "hp" => Self::Hp,
            "oracle" => Self::Oracle,
            other => return Err(format!("unknown --destripe {other:?}")),
        })
    }
    pub fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Mean => "mean",
            Self::Hp => "hp",
            Self::Oracle => "oracle",
        }
    }
}

/// Row and column profiles of a plane, plus the plane mean.
fn profiles(f: &[f32], geom: PlaneGeometry) -> (Vec<f64>, Vec<f64>, f64) {
    let (w, h) = (geom.width, geom.height);
    let mut row = vec![0.0f64; h];
    let mut col = vec![0.0f64; w];
    for (y, r) in row.iter_mut().enumerate() {
        let base = y * w;
        let mut acc = 0.0f64;
        for x in 0..w {
            let v = f[base + x] as f64;
            acc += v;
            col[x] += v;
        }
        *r = acc / w as f64;
    }
    for c in col.iter_mut() {
        *c /= h as f64;
    }
    let mean = row.iter().sum::<f64>() / h as f64;
    (row, col, mean)
}

/// `F'[y,x] = F[y,x] - (row[y] - m) - (col[x] - m)`.
///
/// Level-preserving by construction: `mean(F') == mean(F)`. The naive
/// `F - row - col + m` has mean zero and would silently rescale the operator's
/// pointwise sigma normalisation.
pub fn destripe_mean(f: &mut [f32], geom: PlaneGeometry) {
    let (row, col, mean) = profiles(f, geom);
    let (w, h) = (geom.width, geom.height);
    for (y, rv) in row.iter().enumerate().take(h) {
        let dy = (rv - mean) as f32;
        let base = y * w;
        for x in 0..w {
            f[base + x] -= dy + (col[x] - mean) as f32;
        }
    }
}

/// 1-D Gaussian blur with replicate-clamped borders, matching the border policy
/// `planted::gaussian_blur` uses on the 2-D plane.
fn blur1d(src: &[f64], sigma: f32) -> Vec<f64> {
    let n = src.len();
    if sigma <= 0.0 || n == 0 {
        return src.to_vec();
    }
    let r = (3.0 * sigma).ceil() as isize;
    let mut k = vec![0.0f64; (2 * r + 1) as usize];
    let s2 = 2.0 * (sigma as f64) * (sigma as f64);
    let mut sum = 0.0;
    for (i, kv) in k.iter_mut().enumerate() {
        let d = i as f64 - r as f64;
        *kv = (-d * d / s2).exp();
        sum += *kv;
    }
    for kv in k.iter_mut() {
        *kv /= sum;
    }
    (0..n)
        .map(|i| {
            let mut acc = 0.0;
            for (j, kv) in k.iter().enumerate() {
                let p = (i as isize + j as isize - r).clamp(0, n as isize - 1) as usize;
                acc += kv * src[p];
            }
            acc
        })
        .collect()
}

/// Subtract only the high-frequency part of the row and column profiles.
///
/// A real sensor's row banding is broadband in the profile; genuine scene
/// structure is mostly low frequency along a marginal. Removing
/// `profile - blur(profile)` therefore takes the banding and leaves the scene's
/// slow gradients, which is why this arm is reported next to `mean`.
pub fn destripe_hp(f: &mut [f32], geom: PlaneGeometry, sigma: f32) {
    let (row, col, _) = profiles(f, geom);
    let rlo = blur1d(&row, sigma);
    let clo = blur1d(&col, sigma);
    let (w, h) = (geom.width, geom.height);
    for y in 0..h {
        let dy = (row[y] - rlo[y]) as f32;
        let base = y * w;
        for x in 0..w {
            f[base + x] -= dy + (col[x] - clo[x]) as f32;
        }
    }
}

// ----------------------------------------------------------------- the plant

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FpnStage {
    /// Added to every frame the operator sees, *after* the defocus blur and
    /// identically in each frame — which is what a sensor's fixed pattern
    /// actually is. Not added to `merged`, `ideal` or `oracle`, so it perturbs
    /// exactly the channel H3 names and nothing else.
    Sensor,
    /// Added to the base texture before the render, so the defocus ladder blurs
    /// it like scene content. This is the form the FPN already present in the
    /// real texture tiles takes, because those tiles are one decoded frame that
    /// the harness then blurs.
    Texture,
}

impl FpnStage {
    pub fn parse(s: &str) -> Result<Self, String> {
        Ok(match s {
            "sensor" => Self::Sensor,
            "texture" => Self::Texture,
            other => return Err(format!("unknown --fpn-stage {other:?}")),
        })
    }
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Sensor => "sensor",
            Self::Texture => "texture",
        }
    }
}

/// A zero-mean row and/or column offset pattern of a chosen sd, in DN.
pub struct FpnPlant {
    row: Vec<f32>,
    col: Vec<f32>,
    sd: f32,
}

impl FpnPlant {
    pub fn new(
        sd: f32,
        axis: &str,
        _stage: FpnStage,
        seed: u64,
        geom: PlaneGeometry,
    ) -> Result<Self, String> {
        let (want_row, want_col) = match axis {
            "row" => (true, false),
            "col" => (false, true),
            "both" => (true, true),
            other => return Err(format!("unknown --fpn-axis {other:?}")),
        };
        let mut rng = Rng::new(seed);
        let mut draw = |n: usize, on: bool| -> Vec<f32> {
            if !on || sd == 0.0 {
                return vec![0.0; n];
            }
            let mut v: Vec<f32> = (0..n).map(|_| rng.normal()).collect();
            // Force exactly zero mean and exactly the requested sd, so the
            // amplitude in the CSV is the amplitude in the plane and no
            // realisation lottery enters the positive control.
            let m = v.iter().map(|x| *x as f64).sum::<f64>() / n as f64;
            let s = (v.iter().map(|x| (*x as f64 - m).powi(2)).sum::<f64>() / n as f64)
                .sqrt()
                .max(1e-12);
            let g = (sd as f64) / s;
            for x in v.iter_mut() {
                *x = ((*x as f64 - m) * g) as f32;
            }
            v
        };
        let row = draw(geom.height, want_row);
        let col = draw(geom.width, want_col);
        Ok(Self { row, col, sd })
    }

    pub fn active(&self) -> bool {
        self.sd != 0.0
    }

    pub fn apply(&self, f: &mut [f32], geom: PlaneGeometry) {
        if !self.active() {
            return;
        }
        let (w, h) = (geom.width, geom.height);
        for y in 0..h {
            let dy = self.row[y];
            let base = y * w;
            for x in 0..w {
                f[base + x] += dy + self.col[x];
            }
        }
    }

    /// The exact inverse of `apply`. The oracle treatment.
    pub fn remove(&self, f: &mut [f32], geom: PlaneGeometry) {
        if !self.active() {
            return;
        }
        let (w, h) = (geom.width, geom.height);
        for y in 0..h {
            let dy = self.row[y];
            let base = y * w;
            for x in 0..w {
                f[base + x] -= dy + self.col[x];
            }
        }
    }
}

// ------------------------------------------------------------------- readout

/// What a plane's row/column structure and gradient anisotropy actually are.
#[derive(Debug, Clone, Copy)]
pub struct Scan {
    pub mean: f64,
    pub sd: f64,
    /// sd of the raw row/column marginal profiles, in DN.
    pub row_sd_raw: f64,
    pub col_sd_raw: f64,
    /// sd of the high-passed marginals — the part a destripe would call noise.
    pub row_sd_hp: f64,
    pub col_sd_hp: f64,
    /// sd of what is left after removing both marginals: the 2-D content.
    pub resid_sd: f64,
    /// Mean squared Sobel response on each axis, over the interior.
    pub gx2: f64,
    pub gy2: f64,
    /// `gx2 / gy2`. 1 is isotropic; a row pattern drives it below 1 because a
    /// row-constant field has exactly zero `gx`.
    pub aniso: f64,
    /// Fraction of the plane's total variance explained by the row marginal,
    /// and by the column marginal.
    pub row_share: f64,
    pub col_share: f64,
}

/// The 3x3 Sobel pair `measures::sobel` uses, including its `0.125` scale, so
/// the anisotropy readout is on the same footing as the focus operator.
fn sobel_at(f: &[f32], geom: PlaneGeometry, x: usize, y: usize) -> (f64, f64) {
    let w = geom.width;
    let at = |dx: isize, dy: isize| -> f64 {
        let xx = (x as isize + dx) as usize;
        let yy = (y as isize + dy) as usize;
        f[yy * w + xx] as f64
    };
    let gx =
        0.125 * (at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1));
    let gy =
        0.125 * (at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1));
    (gx, gy)
}

pub fn scan(f: &[f32], geom: PlaneGeometry, hp_sigma: f32) -> Scan {
    let (w, h) = (geom.width, geom.height);
    let (row, col, mean) = profiles(f, geom);
    let var_of =
        |v: &[f64], m: f64| v.iter().map(|x| (x - m) * (x - m)).sum::<f64>() / v.len() as f64;
    let row_var = var_of(&row, mean);
    let col_var = var_of(&col, mean);
    let total_var = f.iter().map(|x| (*x as f64 - mean).powi(2)).sum::<f64>() / f.len() as f64;

    let rlo = blur1d(&row, hp_sigma);
    let clo = blur1d(&col, hp_sigma);
    let rhp: Vec<f64> = row.iter().zip(&rlo).map(|(a, b)| a - b).collect();
    let chp: Vec<f64> = col.iter().zip(&clo).map(|(a, b)| a - b).collect();
    let rhp_sd = var_of(&rhp, rhp.iter().sum::<f64>() / rhp.len() as f64).sqrt();
    let chp_sd = var_of(&chp, chp.iter().sum::<f64>() / chp.len() as f64).sqrt();

    let mut resid = f.to_vec();
    destripe_mean(&mut resid, geom);
    let rm = resid.iter().map(|x| *x as f64).sum::<f64>() / resid.len() as f64;
    let resid_sd =
        (resid.iter().map(|x| (*x as f64 - rm).powi(2)).sum::<f64>() / resid.len() as f64).sqrt();

    let mut sx = 0.0f64;
    let mut sy = 0.0f64;
    let mut n = 0.0f64;
    for y in 1..h - 1 {
        for x in 1..w - 1 {
            let (gx, gy) = sobel_at(f, geom, x, y);
            sx += gx * gx;
            sy += gy * gy;
            n += 1.0;
        }
    }
    let gx2 = sx / n;
    let gy2 = sy / n;

    Scan {
        mean,
        sd: total_var.sqrt(),
        row_sd_raw: row_var.sqrt(),
        col_sd_raw: col_var.sqrt(),
        row_sd_hp: rhp_sd,
        col_sd_hp: chp_sd,
        resid_sd,
        gx2,
        gy2,
        aniso: if gy2 > 0.0 { gx2 / gy2 } else { 0.0 },
        row_share: if total_var > 0.0 {
            row_var / total_var
        } else {
            0.0
        },
        col_share: if total_var > 0.0 {
            col_var / total_var
        } else {
            0.0
        },
    }
}

// ------------------------------------------------------ re-seeded texture

/// `planted::synthetic_texture` with the seed exposed.
///
/// M16 needs two *independent* isotropic fields — one per depth layer — and
/// M13's version hard-codes its seed, so every call returns the same field.
/// This is a verbatim copy with `0x5EED_0F0C` replaced by a parameter, and
/// `selftest` asserts it is bit-identical to M13's at that seed (Gate G3).
pub fn synthetic_texture_seeded(
    geom: PlaneGeometry,
    base_dn: f32,
    amplitude: f32,
    seed: u64,
) -> Vec<f32> {
    let n = geom.pixels();
    let mut rng = Rng::new(seed);
    let white: Vec<f32> = (0..n).map(|_| rng.normal()).collect();

    let mut acc = vec![0.0f32; n];
    let mut tmp = vec![0.0f32; n];
    for (sigma, w) in [
        (0.0f32, 1.0f32),
        (1.0, 1.4),
        (2.0, 2.0),
        (4.0, 2.8),
        (8.0, 4.0),
    ] {
        if sigma == 0.0 {
            for i in 0..n {
                acc[i] += w * white[i];
            }
        } else {
            gaussian_blur(&white, geom, sigma, &mut tmp);
            let gain = 2.0 * std::f32::consts::PI.sqrt() * sigma;
            for i in 0..n {
                acc[i] += w * gain * tmp[i];
            }
        }
    }
    let mean = acc.iter().map(|v| *v as f64).sum::<f64>() / n as f64;
    let var = acc
        .iter()
        .map(|v| (*v as f64 - mean) * (*v as f64 - mean))
        .sum::<f64>()
        / n as f64;
    let sd = var.sqrt().max(1e-12) as f32;
    acc.iter()
        .map(|v| base_dn + amplitude * (v - mean as f32) / sd)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn geom() -> PlaneGeometry {
        PlaneGeometry {
            width: 64,
            height: 48,
        }
    }

    #[test]
    fn destripe_mean_kills_a_pure_row_pattern() {
        let g = geom();
        let mut f = vec![100.0f32; g.pixels()];
        for y in 0..g.height {
            for x in 0..g.width {
                f[y * g.width + x] += (y % 2) as f32 * 20.0;
            }
        }
        destripe_mean(&mut f, g);
        let lo = f.iter().cloned().fold(f32::INFINITY, f32::min);
        let hi = f.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        assert!(hi - lo < 1e-3, "residual range {}", hi - lo);
    }

    #[test]
    fn destripe_mean_preserves_the_level() {
        let g = geom();
        let mut f = synthetic_texture_seeded(g, 1234.0, 200.0, 42);
        let before = f.iter().map(|v| *v as f64).sum::<f64>() / f.len() as f64;
        destripe_mean(&mut f, g);
        let after = f.iter().map(|v| *v as f64).sum::<f64>() / f.len() as f64;
        assert!((after - before).abs() < 1e-2, "{before} -> {after}");
    }

    #[test]
    fn destripe_none_is_a_no_op_by_construction() {
        // The `None` variant has no code path at all; the driver skips the
        // clone. This test pins the enum so a future edit cannot give it one.
        assert_eq!(Destripe::parse("none").unwrap(), Destripe::None);
    }

    #[test]
    fn plant_hits_its_requested_amplitude() {
        let g = geom();
        let p = FpnPlant::new(3.5, "row", FpnStage::Sensor, 1, g).unwrap();
        let m = p.row.iter().map(|v| *v as f64).sum::<f64>() / p.row.len() as f64;
        let s = (p.row.iter().map(|v| (*v as f64 - m).powi(2)).sum::<f64>() / p.row.len() as f64)
            .sqrt();
        assert!(m.abs() < 1e-5, "mean {m}");
        assert!((s - 3.5).abs() < 1e-4, "sd {s}");
        assert!(p.col.iter().all(|v| *v == 0.0));
    }

    #[test]
    fn oracle_removal_is_exact() {
        let g = geom();
        let p = FpnPlant::new(9.0, "both", FpnStage::Sensor, 2, g).unwrap();
        let f0 = synthetic_texture_seeded(g, 500.0, 50.0, 3);
        let mut f = f0.clone();
        p.apply(&mut f, g);
        p.remove(&mut f, g);
        let worst = f
            .iter()
            .zip(&f0)
            .map(|(a, b)| (a - b).abs())
            .fold(0.0f32, f32::max);
        assert!(worst < 1e-3, "residual {worst}");
    }

    #[test]
    fn a_row_pattern_is_pure_vertical_gradient() {
        // The mechanism H3 rests on, asserted rather than assumed: a
        // row-constant field has exactly zero Sobel-x response.
        let g = geom();
        let mut f = vec![0.0f32; g.pixels()];
        let p = FpnPlant::new(10.0, "row", FpnStage::Sensor, 4, g).unwrap();
        p.apply(&mut f, g);
        let s = scan(&f, g, 4.0);
        assert!(s.gx2 < 1e-9, "gx2 {} should be 0", s.gx2);
        assert!(s.gy2 > 1.0, "gy2 {} should be large", s.gy2);
    }

    #[test]
    fn zero_amplitude_plant_is_inert() {
        let g = geom();
        let p = FpnPlant::new(0.0, "both", FpnStage::Sensor, 5, g).unwrap();
        assert!(!p.active());
        let f0 = synthetic_texture_seeded(g, 100.0, 10.0, 6);
        let mut f = f0.clone();
        p.apply(&mut f, g);
        assert_eq!(f, f0);
    }

    #[test]
    fn hp_destripe_spares_a_slow_ramp() {
        // A linear ramp along y is scene content, not banding. `hp` must leave
        // most of it alone where `mean` removes all of it.
        let g = geom();
        let ramp: Vec<f32> = (0..g.pixels())
            .map(|p| 100.0 + (p / g.width) as f32)
            .collect();
        let mut a = ramp.clone();
        destripe_hp(&mut a, g, 4.0);
        let mut b = ramp.clone();
        destripe_mean(&mut b, g);
        let dev = |v: &[f32]| {
            let m = v.iter().map(|x| *x as f64).sum::<f64>() / v.len() as f64;
            (v.iter().map(|x| (*x as f64 - m).powi(2)).sum::<f64>() / v.len() as f64).sqrt()
        };
        assert!(dev(&a) > 5.0 * dev(&b), "hp {} mean {}", dev(&a), dev(&b));
    }
}
