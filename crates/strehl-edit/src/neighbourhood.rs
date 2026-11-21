//! The neighbourhood stage: heals, then backdrop clean-up, on the master's
//! linear samples before the per-pixel development.
//!
//! Every output pixel is a function of the samples within `halo()` of it
//! (edges repeated), evaluated in a fixed order, so a patch computed with its
//! halo is bit-identical to the same pixels of a whole-photograph pass. The
//! export and `render_display_region_mode` both use `Neighbourhood::region`.
//!
//! Supports are fixed fractions of the photograph's long edge, so a preview
//! raster and the master see the same physical neighbourhood: the backdrop
//! key averages over about 1/3000 of the long edge and the backdrop smooths
//! over about 1/800 (2 and 9 px on a 7032 px master).
use crate::{Backdrop, DevelopmentRecipe, Heal, LinearImage, recipe::luma};
use rayon::prelude::*;

const KEY_FRACTION: f64 = 1.0 / 3000.0;
const SMOOTH_FRACTION: f64 = 1.0 / 800.0;
/// Inner part of a heal at full strength; the rest is a smooth edge.
const HEAL_FEATHER: f32 = 0.3;
/// The ring that matches source tone to destination, in radii.
const HEAL_RING: [f64; 2] = [1.05, 1.35];
const BAND_ROWS: usize = 256;

struct PreparedHeal {
    centre: [f64; 2],
    radius: [f64; 2],
    offset: [i64; 2],
    gain: [f32; 3],
    lo: [i64; 2],
    hi: [i64; 2],
}

/// The stage prepared for one image (photograph or preview raster).
pub struct Neighbourhood<'a> {
    image: &'a LinearImage,
    heals: Vec<PreparedHeal>,
    backdrop: Option<(Backdrop, usize, usize)>,
}

impl<'a> Neighbourhood<'a> {
    pub fn new(image: &'a LinearImage, recipe: &DevelopmentRecipe) -> Self {
        let long = f64::from(image.width.max(image.height));
        let heals = recipe
            .heals
            .iter()
            .filter(|h| h.enabled)
            .map(|h| prepare_heal(image, h))
            .collect();
        let backdrop = recipe.backdrop.filter(|b| b.enabled).map(|b| {
            (
                b,
                (long * KEY_FRACTION).round().max(1.0) as usize,
                (long * SMOOTH_FRACTION).round().max(1.0) as usize,
            )
        });
        Self {
            image,
            heals,
            backdrop,
        }
    }

    pub fn is_identity(&self) -> bool {
        self.heals.is_empty() && self.backdrop.is_none()
    }

    /// Source pixels each output pixel depends on, beyond heal source lookups
    /// (which read the master directly, at any distance).
    pub fn halo(&self) -> u32 {
        self.backdrop.map_or(0, |(_, k, s)| (k + s) as u32)
    }

    #[inline]
    fn raw(&self, x: i64, y: i64) -> [f32; 3] {
        let x = x.clamp(0, i64::from(self.image.width) - 1) as usize;
        let y = y.clamp(0, i64::from(self.image.height) - 1) as usize;
        let i = (y * self.image.width as usize + x) * 3;
        let p = &self.image.pixels[i..i + 3];
        [p[0], p[1], p[2]]
    }

    /// Healed sample at a (clamped) pixel. Heals read their source from the
    /// unhealed master and apply in list order.
    #[inline]
    fn healed(&self, x: i64, y: i64) -> [f32; 3] {
        let x = x.clamp(0, i64::from(self.image.width) - 1);
        let y = y.clamp(0, i64::from(self.image.height) - 1);
        let mut v = self.raw(x, y);
        for heal in &self.heals {
            if x < heal.lo[0] || x > heal.hi[0] || y < heal.lo[1] || y > heal.hi[1] {
                continue;
            }
            let dx = (x as f64 + 0.5 - heal.centre[0]) / heal.radius[0];
            let dy = (y as f64 + 0.5 - heal.centre[1]) / heal.radius[1];
            let w = crate::recipe::feathered_weight(1.0 - dx.hypot(dy) as f32, HEAL_FEATHER);
            if w <= 0.0 {
                continue;
            }
            let s = self.raw(x + heal.offset[0], y + heal.offset[1]);
            for c in 0..3 {
                v[c] += (s[c] * heal.gain[c] - v[c]) * w;
            }
        }
        v
    }

    /// Stage output for the pixel rectangle `[x0, y0, x1, y1)`, interleaved RGB.
    pub fn region(&self, rect: [u32; 4]) -> Vec<f32> {
        let [x0, y0, x1, y1] = rect.map(i64::from);
        let width = (x1 - x0).max(0) as usize;
        let height = (y1 - y0).max(0) as usize;
        let mut out = vec![0.0f32; width * height * 3];
        if width == 0 || height == 0 {
            return out;
        }
        let Some((backdrop, key, smooth)) = self.backdrop else {
            out.par_chunks_mut(width * 3)
                .enumerate()
                .for_each(|(row, line)| {
                    for col in 0..width {
                        let v = self.healed(x0 + col as i64, y0 + row as i64);
                        line[col * 3..col * 3 + 3].copy_from_slice(&v);
                    }
                });
            return out;
        };
        for (band, chunk) in out.chunks_mut(BAND_ROWS * width * 3).enumerate() {
            let top = y0 + (band * BAND_ROWS) as i64;
            let rows = chunk.len() / (width * 3);
            self.backdrop_band(chunk, [x0, top], [width, rows], backdrop, key, smooth);
        }
        out
    }

    fn backdrop_band(
        &self,
        out: &mut [f32],
        origin: [i64; 2],
        size: [usize; 2],
        backdrop: Backdrop,
        key: usize,
        smooth: usize,
    ) {
        let halo = key + smooth;
        let ew = size[0] + 2 * halo;
        let eh = size[1] + 2 * halo;
        let ex = origin[0] - halo as i64;
        let ey = origin[1] - halo as i64;
        // Healed samples and their placed light over the band and its halo.
        let mut healed = vec![0.0f32; ew * eh * 3];
        let mut light = vec![0.0f32; ew * eh];
        healed
            .par_chunks_mut(ew * 3)
            .zip(light.par_chunks_mut(ew))
            .enumerate()
            .for_each(|(row, (line, lum))| {
                for col in 0..ew {
                    let v = self.healed(ex + col as i64, ey + row as i64);
                    line[col * 3..col * 3 + 3].copy_from_slice(&v);
                    let placed = self.image.baseline.map_or(v, |b| b.place(v));
                    lum[col] = luma(placed);
                }
            });
        // Backdrop membership from the light's (2k+1)^2 mean, on the band
        // grown by the smoothing radius. Sums run in a fixed order per pixel.
        let mw = size[0] + 2 * smooth;
        let mh = size[1] + 2 * smooth;
        let mut across = vec![0.0f32; mw * eh];
        across
            .par_chunks_mut(mw)
            .enumerate()
            .for_each(|(row, line)| {
                let src = &light[row * ew..(row + 1) * ew];
                for (col, v) in line.iter_mut().enumerate() {
                    *v = src[col..col + 2 * key + 1].iter().sum();
                }
            });
        let area = ((2 * key + 1) * (2 * key + 1)) as f32;
        let mut member = vec![0.0f32; mw * mh];
        member
            .par_chunks_mut(mw)
            .enumerate()
            .for_each(|(row, line)| {
                for (col, m) in line.iter_mut().enumerate() {
                    let sum: f32 = (0..2 * key + 1).map(|k| across[(row + k) * mw + col]).sum();
                    *m = backdrop.membership(sum / area);
                }
            });
        // Normalized convolution: a smoothed backdrop from backdrop pixels only.
        let side = 2 * smooth + 1;
        let mut weighted = vec![0.0f32; size[0] * mh * 4];
        weighted
            .par_chunks_mut(size[0] * 4)
            .enumerate()
            .for_each(|(row, line)| {
                for col in 0..size[0] {
                    let mut acc = [0.0f32; 4];
                    for k in 0..side {
                        let m = member[row * mw + col + k];
                        let h = (row + key) * ew + col + k + key;
                        let v = &healed[h * 3..h * 3 + 3];
                        acc[0] += m * v[0];
                        acc[1] += m * v[1];
                        acc[2] += m * v[2];
                        acc[3] += m;
                    }
                    line[col * 4..col * 4 + 4].copy_from_slice(&acc);
                }
            });
        out.par_chunks_mut(size[0] * 3)
            .enumerate()
            .for_each(|(row, line)| {
                for col in 0..size[0] {
                    let h = (row + halo) * ew + col + halo;
                    let v = &healed[h * 3..h * 3 + 3];
                    let m = member[(row + smooth) * mw + col + smooth];
                    let o = &mut line[col * 3..col * 3 + 3];
                    o.copy_from_slice(v);
                    if m <= 0.0 {
                        continue;
                    }
                    if backdrop.key == crate::BackdropKey::Dark {
                        // Clean to black, by membership.
                        for c in 0..3 {
                            o[c] = v[c] * (1.0 - m);
                        }
                        continue;
                    }
                    let mut acc = [0.0f32; 4];
                    for k in 0..side {
                        let s = &weighted[((row + k) * size[0] + col) * 4..][..4];
                        for c in 0..4 {
                            acc[c] += s[c];
                        }
                    }
                    if acc[3] > 0.0 {
                        for c in 0..3 {
                            o[c] = v[c] + (acc[c] / acc[3] - v[c]) * m;
                        }
                    }
                }
            });
    }
}

fn prepare_heal(image: &LinearImage, heal: &Heal) -> PreparedHeal {
    let size = [f64::from(image.width), f64::from(image.height)];
    let centre = [
        f64::from(heal.center[0]) * size[0],
        f64::from(heal.center[1]) * size[1],
    ];
    let radius = [
        (f64::from(heal.radius[0]) * size[0]).max(0.5),
        (f64::from(heal.radius[1]) * size[1]).max(0.5),
    ];
    let offset = [
        (f64::from(heal.source_offset[0]) * size[0]).round() as i64,
        (f64::from(heal.source_offset[1]) * size[1]).round() as i64,
    ];
    let lo = [
        (centre[0] - radius[0]).floor() as i64,
        (centre[1] - radius[1]).floor() as i64,
    ];
    let hi = [
        (centre[0] + radius[0]).ceil() as i64,
        (centre[1] + radius[1]).ceil() as i64,
    ];
    // Match the source's tone to the destination's surroundings, per channel,
    // from the ring just outside the spot (light is multiplicative).
    let mut dest = [0.0f64; 3];
    let mut src = [0.0f64; 3];
    let ring_lo = [
        (centre[0] - radius[0] * HEAL_RING[1]).floor() as i64,
        (centre[1] - radius[1] * HEAL_RING[1]).floor() as i64,
    ];
    let ring_hi = [
        (centre[0] + radius[0] * HEAL_RING[1]).ceil() as i64,
        (centre[1] + radius[1] * HEAL_RING[1]).ceil() as i64,
    ];
    let pixel = |x: i64, y: i64| {
        let x = x.clamp(0, i64::from(image.width) - 1) as usize;
        let y = y.clamp(0, i64::from(image.height) - 1) as usize;
        let i = (y * image.width as usize + x) * 3;
        [image.pixels[i], image.pixels[i + 1], image.pixels[i + 2]]
    };
    for y in ring_lo[1]..=ring_hi[1] {
        for x in ring_lo[0]..=ring_hi[0] {
            let d = ((x as f64 + 0.5 - centre[0]) / radius[0])
                .hypot((y as f64 + 0.5 - centre[1]) / radius[1]);
            if !(HEAL_RING[0]..=HEAL_RING[1]).contains(&d) {
                continue;
            }
            let a = pixel(x, y);
            let b = pixel(x + offset[0], y + offset[1]);
            for c in 0..3 {
                dest[c] += f64::from(a[c]);
                src[c] += f64::from(b[c]);
            }
        }
    }
    let gain = std::array::from_fn(|c| {
        if src[c] > 1e-9 && dest[c] > 0.0 {
            (dest[c] / src[c]).clamp(0.25, 4.0) as f32
        } else {
            1.0
        }
    });
    PreparedHeal {
        centre,
        radius,
        offset,
        gain,
        lo,
        hi,
    }
}

impl LinearImage {
    /// The photograph after the neighbourhood stage, for export. Returns a
    /// clone of the samples when the recipe has heals or a backdrop.
    pub(crate) fn with_neighbourhood(&self, recipe: &DevelopmentRecipe) -> Option<LinearImage> {
        if !recipe.has_neighbourhood() {
            return None;
        }
        let stage = Neighbourhood::new(self, recipe);
        Some(LinearImage {
            pixels: stage.region([0, 0, self.width, self.height]),
            ..self.clone_without_pixels()
        })
    }

    fn clone_without_pixels(&self) -> LinearImage {
        LinearImage {
            width: self.width,
            height: self.height,
            pixels: Vec::new(),
            origin: self.origin,
            baseline: self.baseline,
            baked_recipe: self.baked_recipe.clone(),
        }
    }
}
