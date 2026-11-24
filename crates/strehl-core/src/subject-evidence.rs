//! Through-focus evidence on the cell grid (plan S2 steps 1-4).
//!
//! Per frame: the squared 4-neighbour Laplacian of one green site plane,
//! averaged over 8 px cells and divided by what the injected noise model says
//! sensor noise alone gives at the cell's level, then a 3 x 3 cell mean.
//! Over frames: one magnification rate about the frame centre registers the
//! planes, a three-plane running mean along focus, and the largest value is
//! the cell's focus evidence; where it peaks is the cell's sharpest plane.

use rayon::prelude::*;

use super::outline::Source;

/// Sensor pixels per RAW evidence cell: 4 x 4 samples of one green site plane.
pub const RAW_CELL_PX: usize = 8;

/// One RAW exposure's active area, as stored: `u16` CFA, RGGB at the active
/// origin (the engine's convention, `strehl_core::pixel_shift::cfa_colour`).
#[derive(Clone, Copy, Debug)]
pub struct CfaView<'a> {
    pub data: &'a [u16],
    /// Row stride of `data`, in samples.
    pub stride: usize,
    /// Active area origin and size inside `data`.
    pub x0: usize,
    pub y0: usize,
    pub width: usize,
    pub height: usize,
    pub black: f32,
    pub white: f32,
}

/// One frame reduced to the cell grid.
#[derive(Clone, Debug)]
pub struct FrameCells {
    pub cols: usize,
    pub rows: usize,
    /// Fine-detail energy in units of its expected value under noise alone,
    /// after the 3 x 3 cell mean.
    pub energy: Vec<f32>,
    /// Mean level, as a share of black..white (RAW) or linear luma (live view).
    pub level: Vec<f32>,
}

/// Variance in DN^2 of one green sample at a black-subtracted signal (DN):
/// the injected noise model, e.g. `NoiseModel::variance(CfaPlane::G1, s)`.
pub type Variance<'a> = &'a (dyn Fn(f32) -> f32 + Sync);

/// A 3 x 3 mean with the edge cell repeated (scipy's `reflect` at radius 1).
pub(crate) fn box3(v: &[f32], cols: usize, rows: usize) -> Vec<f32> {
    let mut out = vec![0.0f32; v.len()];
    out.par_chunks_mut(cols).enumerate().for_each(|(y, row)| {
        let ys = [y.saturating_sub(1), y, (y + 1).min(rows - 1)];
        for (x, o) in row.iter_mut().enumerate() {
            let xs = [x.saturating_sub(1), x, (x + 1).min(cols - 1)];
            let mut s = 0.0f32;
            for &yy in &ys {
                for &xx in &xs {
                    s += v[yy * cols + xx];
                }
            }
            *o = s / 9.0;
        }
    });
    out
}

/// Evidence of one RAW exposure. `variance` is the injected noise model.
///
/// The Laplacian is taken on the first green site of each 2 x 2 cell (two
/// sensor pixels apart, unblurred), with the plane's edge sample repeated
/// beyond its border. Its variance under independent noise is 20 times one
/// sample's, so a cell's energy is divided by `20 * variance(level)`. The
/// level is the mean of both green sites over the cell's 8 x 8 pixels.
pub fn raw_frame_cells(v: &CfaView<'_>, variance: Variance<'_>) -> FrameCells {
    const B: usize = RAW_CELL_PX / 2;
    let (hw, hh) = (v.width / 2, v.height / 2);
    let (cols, rows) = (hw / B, hh / B);
    let range = (v.white - v.black).max(1.0);
    // First green (x odd, y even) and second green (x even, y odd).
    let g1 = |i: usize, j: usize| -> f32 {
        f32::from(v.data[(v.y0 + 2 * j) * v.stride + v.x0 + 2 * i + 1]) - v.black
    };
    let g2 = |i: usize, j: usize| -> f32 {
        f32::from(v.data[(v.y0 + 2 * j + 1) * v.stride + v.x0 + 2 * i]) - v.black
    };
    let mut energy = vec![0.0f32; cols * rows];
    let mut level = vec![0.0f32; cols * rows];
    energy
        .par_chunks_mut(cols)
        .zip(level.par_chunks_mut(cols))
        .enumerate()
        .for_each(|(cy, (erow, lrow))| {
            let mut esum = vec![0.0f32; cols];
            let mut lsum = vec![0.0f32; cols];
            for j in cy * B..(cy + 1) * B {
                let (jm, jp) = (j.saturating_sub(1), (j + 1).min(hh - 1));
                for (cx, (e, l)) in esum.iter_mut().zip(lsum.iter_mut()).enumerate() {
                    for i in cx * B..(cx + 1) * B {
                        let (im, ip) = (i.saturating_sub(1), (i + 1).min(hw - 1));
                        let c = g1(i, j);
                        let lap = g1(im, j) + g1(ip, j) + g1(i, jm) + g1(i, jp) - 4.0 * c;
                        *e += lap * lap;
                        *l += c + g2(i, j);
                    }
                }
            }
            let n = (B * B) as f32;
            for cx in 0..cols {
                let mean_dn = lsum[cx] / (2.0 * n);
                let expected = 20.0 * variance(mean_dn).max(1e-6);
                erow[cx] = esum[cx] / n / expected;
                lrow[cx] = mean_dn / range;
            }
        });
    FrameCells {
        cols,
        rows,
        energy: box3(&energy, cols, rows),
        level,
    }
}

/// A plane the evidence came from.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PlaneRef {
    /// The capture's plane ordinal.
    pub ordinal: u64,
    /// Its focus position (motor units), when recorded. Registration spans
    /// fall back to plane indices when positions are missing.
    pub position: Option<f64>,
}

/// How the planes are registered to one another.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Registration {
    /// Fit one magnification rate from the frames themselves (needs at least
    /// [`MIN_REGISTER_PLANES`] planes; fewer are not registered).
    Fit,
    /// A known rate, in parts per million of magnification per focus unit
    /// (from the alignment or a survey).
    Rate(f64),
    Off,
}

/// Fewer planes than this are not registered by fit (as the prototype).
pub const MIN_REGISTER_PLANES: usize = 8;

/// The fitted or given registration.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Fitted {
    /// Magnification change per focus unit (per plane when positions are
    /// unknown), ppm.
    pub ppm_per_unit: f64,
    /// For a fit: the scale that maps plane `n * 3 / 4` onto plane `n / 4`
    /// and the correlation it reached.
    pub scale: Option<f64>,
    pub correlation: Option<f64>,
}

/// Where the evidence is laid on the sensor.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Layout {
    pub source: Source,
    /// Sensor pixels per cell.
    pub cell_px: f32,
    /// One cell's size in normalised active-area units.
    pub cell_norm: [f64; 2],
    pub active_px: [u32; 2],
}

/// Everything selection needs; re-thresholding reads only this.
#[derive(Clone, Debug)]
pub struct Evidence {
    pub cols: usize,
    pub rows: usize,
    pub layout: Layout,
    pub planes: Vec<PlaneRef>,
    /// The plane index whose geometry the grid is in.
    pub reference: usize,
    pub registration: Option<Fitted>,
    /// Per cell: the largest three-plane mean of noise-normalised energy.
    pub focus: Vec<f32>,
    /// Per cell: index into `planes` where that largest value lies (the
    /// coarse depth map).
    pub depth: Vec<u16>,
    /// Per cell: median level over the planes.
    pub level: Vec<f32>,
}

impl Evidence {
    /// The sharpest plane's ordinal for a cell.
    pub fn sharpest_plane(&self, cell: usize) -> u64 {
        self.planes[self.depth[cell] as usize].ordinal
    }
}

/// Separable Gaussian with scipy's defaults (radius `4 sigma + 0.5`,
/// `reflect` edges).
pub(crate) fn gaussian(v: &[f32], cols: usize, rows: usize, sigma: f32) -> Vec<f32> {
    let r = (4.0 * sigma + 0.5) as isize;
    let mut k: Vec<f32> = (-r..=r)
        .map(|i| (-0.5 * (i as f32 / sigma).powi(2)).exp())
        .collect();
    let s: f32 = k.iter().sum();
    k.iter_mut().for_each(|x| *x /= s);
    let reflect = |i: isize, n: usize| -> usize {
        let n = n as isize;
        let mut i = i;
        loop {
            if i < 0 {
                i = -i - 1;
            } else if i >= n {
                i = 2 * n - i - 1;
            } else {
                return i as usize;
            }
        }
    };
    let mut tmp = vec![0.0f32; v.len()];
    tmp.par_chunks_mut(cols).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            *o = k
                .iter()
                .enumerate()
                .map(|(t, w)| w * v[y * cols + reflect(x as isize + t as isize - r, cols)])
                .sum();
        }
    });
    let mut out = vec![0.0f32; v.len()];
    out.par_chunks_mut(cols).enumerate().for_each(|(y, row)| {
        for (x, o) in row.iter_mut().enumerate() {
            *o = k
                .iter()
                .enumerate()
                .map(|(t, w)| w * tmp[reflect(y as isize + t as isize - r, rows) * cols + x])
                .sum();
        }
    });
    out
}

/// Bilinear resampling about the grid centre by `scale` (edge values
/// repeated), as the prototype's `map_coordinates(order=1, mode='nearest')`.
pub(crate) fn rescale(v: &[f32], cols: usize, rows: usize, scale: f64) -> Vec<f32> {
    let (cx, cy) = ((cols as f64 - 1.0) / 2.0, (rows as f64 - 1.0) / 2.0);
    let mut out = vec![0.0f32; v.len()];
    out.par_chunks_mut(cols).enumerate().for_each(|(y, row)| {
        let sy = (cy + (y as f64 - cy) / scale).clamp(0.0, rows as f64 - 1.0);
        let y0 = (sy.floor() as usize).min(rows - 1);
        let y1 = (y0 + 1).min(rows - 1);
        let fy = (sy - y0 as f64) as f32;
        for (x, o) in row.iter_mut().enumerate() {
            let sx = (cx + (x as f64 - cx) / scale).clamp(0.0, cols as f64 - 1.0);
            let x0 = (sx.floor() as usize).min(cols - 1);
            let x1 = (x0 + 1).min(cols - 1);
            let fx = (sx - x0 as f64) as f32;
            let a = v[y0 * cols + x0] * (1.0 - fx) + v[y0 * cols + x1] * fx;
            let b = v[y1 * cols + x0] * (1.0 - fx) + v[y1 * cols + x1] * fx;
            *o = a * (1.0 - fy) + b * fy;
        }
    });
    out
}

fn correlation(a: &[f32], b: &[f32], cols: usize, rows: usize, margin: usize) -> f64 {
    let (mut n, mut sa, mut sb, mut saa, mut sbb, mut sab) = (0.0f64, 0.0, 0.0, 0.0, 0.0, 0.0);
    for y in margin..rows.saturating_sub(margin) {
        for x in margin..cols.saturating_sub(margin) {
            let (p, q) = (f64::from(a[y * cols + x]), f64::from(b[y * cols + x]));
            n += 1.0;
            sa += p;
            sb += q;
            saa += p * p;
            sbb += q * q;
            sab += p * q;
        }
    }
    let va = saa - sa * sa / n;
    let vb = sbb - sb * sb / n;
    if va <= 0.0 || vb <= 0.0 {
        return 0.0;
    }
    (sab - sa * sb / n) / (va * vb).sqrt()
}

/// Smoothing and border margin (cells) of the registration fit per source.
fn fit_shape(source: Source) -> (f32, usize) {
    match source {
        Source::Raw => (3.0, 20),
        Source::LiveView => (2.0, 8),
    }
}

/// Assembles evidence from per-frame cells, in focus order.
///
/// # Panics
/// When `frames` is empty, differs in length from `planes`, or the frames'
/// grids differ.
pub fn assemble(
    frames: Vec<FrameCells>,
    planes: Vec<PlaneRef>,
    layout: Layout,
    registration: Registration,
) -> Evidence {
    assert!(!frames.is_empty() && frames.len() == planes.len());
    let (cols, rows) = (frames[0].cols, frames[0].rows);
    assert!(frames.iter().all(|f| f.cols == cols && f.rows == rows));
    let n = frames.len();
    let mid = n / 2;
    let span = |i: usize, j: usize| -> f64 {
        match (planes[i].position, planes[j].position) {
            (Some(a), Some(b)) if (b - a).abs() > 1e-9 => b - a,
            _ => (j as f64) - (i as f64),
        }
    };
    let fitted = match registration {
        Registration::Off => None,
        Registration::Rate(ppm) => Some(Fitted {
            ppm_per_unit: ppm,
            scale: None,
            correlation: None,
        }),
        Registration::Fit if n < MIN_REGISTER_PLANES && layout.source == Source::Raw => None,
        Registration::Fit if n < 3 => None,
        Registration::Fit => {
            let (i, j) = (n / 4, 3 * n / 4);
            let (sigma, margin) = fit_shape(layout.source);
            let a = gaussian(&frames[i].level, cols, rows, sigma);
            let b = gaussian(&frames[j].level, cols, rows, sigma);
            let best = (0..81)
                .into_par_iter()
                .map(|k| {
                    let s = 0.96 + 0.001 * k as f64;
                    (
                        correlation(&a, &rescale(&b, cols, rows, s), cols, rows, margin),
                        s,
                    )
                })
                .reduce(
                    || (f64::NEG_INFINITY, 1.0),
                    |p, q| {
                        if q.0 > p.0 || (q.0 == p.0 && q.1 < p.1) {
                            q
                        } else {
                            p
                        }
                    },
                );
            Some(Fitted {
                ppm_per_unit: 1e6 * best.1.ln() / span(i, j),
                scale: Some(best.1),
                correlation: Some(best.0),
            })
        }
    };
    let mut energy: Vec<Vec<f32>> = Vec::with_capacity(n);
    let mut level: Vec<Vec<f32>> = Vec::with_capacity(n);
    let frames: Vec<(Vec<f32>, Vec<f32>)> = frames
        .into_par_iter()
        .enumerate()
        .map(|(k, f)| {
            let rate = fitted.map_or(0.0, |r| r.ppm_per_unit * 1e-6);
            let s = (-rate * span(mid, k)).exp();
            if (s - 1.0).abs() > 2e-4 {
                (
                    rescale(&f.energy, cols, rows, s),
                    rescale(&f.level, cols, rows, s),
                )
            } else {
                (f.energy, f.level)
            }
        })
        .collect();
    for (e, l) in frames {
        energy.push(e);
        level.push(l);
    }
    let cells = cols * rows;
    let mut focus = vec![0.0f32; cells];
    let mut depth = vec![0u16; cells];
    let mut med = vec![0.0f32; cells];
    focus
        .par_iter_mut()
        .zip(depth.par_iter_mut())
        .zip(med.par_iter_mut())
        .enumerate()
        .for_each_init(
            || vec![0.0f32; n],
            |buf, (c, ((f, d), m))| {
                let mut best = (f32::NEG_INFINITY, 0usize);
                for k in 0..n {
                    let v = if n >= 3 {
                        let (a, b) = (k.saturating_sub(1), (k + 1).min(n - 1));
                        (energy[a][c] + energy[k][c] + energy[b][c]) / 3.0
                    } else {
                        energy[k][c]
                    };
                    if v > best.0 {
                        best = (v, k);
                    }
                    buf[k] = level[k][c];
                }
                *f = best.0;
                *d = best.1 as u16;
                buf.sort_by(f32::total_cmp);
                *m = if n % 2 == 1 {
                    buf[n / 2]
                } else {
                    0.5 * (buf[n / 2 - 1] + buf[n / 2])
                };
            },
        );
    Evidence {
        cols,
        rows,
        layout,
        planes,
        reference: mid,
        registration: fitted,
        focus,
        depth,
        level: med,
    }
}
