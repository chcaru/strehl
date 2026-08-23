//! CPU reference — **copied verbatim in behaviour** from `crates/strehl-core` at
//! commit `037d966e03f7931d6b2311585dc3147ee1d9233b`, so that this experiment
//! never depends on the workspace crate and never edits it.
//!
//! Sources copied: `boxfilter.rs` (`box_mean`), `focus.rs` (`FocusField`,
//! `INNER_RADIUS`, `OUTER_RADIUS`, `SIGMA_EPS`), `plane.rs` (`PlaneGeometry`,
//! `green_luma`), `noise.rs` (`PlaneNoise`, `NoiseModel::green_luma_sigma`),
//! `stack.rs` (`Selection::beats`, `Selection::fold`), `profile.rs` (the A7C II
//! constants).
//!
//! The one deliberate change is the input adapter: this crate feeds the plane
//! from a packed active-area buffer rather than from `strehl_raw::Frame`. The
//! packed buffer contains **only** the 7032x4688 active area, so project rule 7
//! is satisfied structurally: there is no padding in the buffer to measure.
//!
//! `exact_focus_f64` is **not** a copy. It is an independent, deliberately naive
//! f64 gather written from the documented border policy, and it exists so that
//! CPU-f32 and GPU-f32 can each be scored against arithmetic truth rather than
//! against each other.

/// Inner box radius: a 3x3 mean. (`focus.rs`)
pub const INNER_RADIUS: usize = 1;
/// Outer box radius: a 7x7 mean. (`focus.rs`)
pub const OUTER_RADIUS: usize = 3;
/// Divisor floor, in DN. (`focus.rs`)
pub const SIGMA_EPS: f32 = 1e-3;

/// Sony A7C II. (`profile.rs`)
pub const GAIN_DIVISOR: f32 = 436.8;
pub const READ_NOISE_E_LOW: f32 = 4.20;
pub const READ_NOISE_E_HIGH: f32 = 1.47;
pub const SECOND_BASE_ISO: f32 = 400.0;

pub fn gain_dn_per_e(iso: f32) -> f32 {
    iso / GAIN_DIVISOR
}

pub fn read_noise_e(iso: f32) -> f32 {
    if iso >= SECOND_BASE_ISO {
        READ_NOISE_E_HIGH
    } else {
        READ_NOISE_E_LOW
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PlaneGeometry {
    pub width: usize,
    pub height: usize,
}

impl PlaneGeometry {
    pub const fn pixels(&self) -> usize {
        self.width * self.height
    }
    pub const fn index(&self, px: usize, py: usize) -> usize {
        py * self.width + px
    }
}

/// `noise.rs`: `sigma^2(S) = g*S + (RN_e*g)^2`, per plane; green luma averages
/// two independent greens, so `Var(L) = (Var(G1) + Var(G2)) / 4`.
///
/// The f32 operation order is preserved exactly, because this is the sequence
/// the WGSL kernel has to reproduce.
#[derive(Debug, Clone, Copy)]
pub struct Noise {
    pub gain_dn_per_e: f32,
    pub read_noise_e: f32,
}

impl Noise {
    pub fn variance(&self, signal_dn: f32) -> f32 {
        let s = signal_dn.max(0.0);
        let read_dn = self.read_noise_e * self.gain_dn_per_e;
        self.gain_dn_per_e * s + read_dn * read_dn
    }
    pub fn green_luma_sigma(&self, luma_dn: f32) -> f32 {
        let v = self.variance(luma_dn) + self.variance(luma_dn);
        (0.25 * v).sqrt()
    }
}

// ---------------------------------------------------------------------------
// boxfilter.rs
// ---------------------------------------------------------------------------

pub fn box_mean(src: &[f32], geom: PlaneGeometry, radius: usize, scratch: &mut [f32], dst: &mut [f32]) {
    let (w, h) = (geom.width, geom.height);
    assert_eq!(src.len(), geom.pixels());
    assert_eq!(scratch.len(), geom.pixels());
    assert_eq!(dst.len(), geom.pixels());
    if w == 0 || h == 0 {
        return;
    }
    horizontal_sums(src, w, h, radius, scratch);
    vertical_means(scratch, w, h, radius, dst);
}

fn horizontal_sums(src: &[f32], w: usize, h: usize, radius: usize, scratch: &mut [f32]) {
    for y in 0..h {
        let row = &src[y * w..(y + 1) * w];
        let out = &mut scratch[y * w..(y + 1) * w];
        let mut sum: f64 = row[..(radius + 1).min(w)].iter().map(|v| *v as f64).sum();
        for x in 0..w {
            out[x] = sum as f32;
            let entering = x + 1 + radius;
            if entering < w {
                sum += row[entering] as f64;
            }
            if x >= radius {
                sum -= row[x - radius] as f64;
            }
        }
    }
}

fn vertical_means(sums: &[f32], w: usize, h: usize, radius: usize, dst: &mut [f32]) {
    let counts: Vec<f64> = (0..w)
        .map(|x| {
            let x0 = x.saturating_sub(radius);
            let x1 = (x + radius).min(w - 1);
            (x1 - x0 + 1) as f64
        })
        .collect();

    let mut column = vec![0.0f64; w];
    for y in 0..(radius + 1).min(h) {
        for (x, c) in column.iter_mut().enumerate() {
            *c += sums[y * w + x] as f64;
        }
    }

    for y in 0..h {
        let y0 = y.saturating_sub(radius);
        let y1 = (y + radius).min(h - 1);
        let ny = (y1 - y0 + 1) as f64;
        let out = &mut dst[y * w..(y + 1) * w];
        for (x, o) in out.iter_mut().enumerate() {
            *o = (column[x] / (counts[x] * ny)) as f32;
        }
        let entering = y + 1 + radius;
        if entering < h {
            for (x, c) in column.iter_mut().enumerate() {
                *c += sums[entering * w + x] as f64;
            }
        }
        if y >= radius {
            let leaving = y - radius;
            for (x, c) in column.iter_mut().enumerate() {
                *c -= sums[leaving * w + x] as f64;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// focus.rs
// ---------------------------------------------------------------------------

pub struct FocusField {
    geom: PlaneGeometry,
    focus: Vec<f32>,
    outer: Vec<f32>,
    scratch: Vec<f32>,
}

impl FocusField {
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            focus: vec![0.0; geom.pixels()],
            outer: vec![0.0; geom.pixels()],
            scratch: vec![0.0; geom.pixels()],
        }
    }

    /// Same as `strehl-core`, but with the radii parameterised so that a second
    /// focus measure (a wider ring) can be priced on the same code path.
    pub fn compute_radii(&mut self, luma: &[f32], noise: &Noise, inner_r: usize, outer_r: usize) {
        assert_eq!(luma.len(), self.geom.pixels());
        box_mean(luma, self.geom, inner_r, &mut self.scratch, &mut self.focus);
        box_mean(luma, self.geom, outer_r, &mut self.scratch, &mut self.outer);
        for ((focus, outer), l) in self.focus.iter_mut().zip(&self.outer).zip(luma) {
            let ring = (*focus - *outer).abs();
            let sigma = noise.green_luma_sigma(*l).max(SIGMA_EPS);
            *focus = ring / sigma;
        }
    }

    pub fn compute(&mut self, luma: &[f32], noise: &Noise) {
        self.compute_radii(luma, noise, INNER_RADIUS, OUTER_RADIUS)
    }

    pub fn values(&self) -> &[f32] {
        &self.focus
    }
}

// ---------------------------------------------------------------------------
// plane.rs — green luma from a packed active-area buffer
// ---------------------------------------------------------------------------

/// Black-subtracted `L = (G1 + G2) / 2` at plane resolution, RGGB.
///
/// `active` is the packed active area, `active_w` samples per row. There is no
/// padding in it (rule 7).
pub fn green_luma(active: &[u16], active_w: usize, geom: PlaneGeometry, black: f32, dst: &mut [f32]) {
    assert_eq!(dst.len(), geom.pixels());
    for py in 0..geom.height {
        let row0 = &active[(2 * py) * active_w..(2 * py + 1) * active_w];
        let row1 = &active[(2 * py + 1) * active_w..(2 * py + 2) * active_w];
        let out = &mut dst[py * geom.width..(py + 1) * geom.width];
        for (px, o) in out.iter_mut().enumerate() {
            // G1 is (1, 0) in the quad, G2 is (0, 1).
            let g1 = (row0[2 * px + 1] as f32 - black).max(0.0);
            let g2 = (row1[2 * px] as f32 - black).max(0.0);
            *o = 0.5 * (g1 + g2);
        }
    }
}

// ---------------------------------------------------------------------------
// stack.rs — the argmax fold, i.e. the merge this experiment fuses with
// ---------------------------------------------------------------------------

pub const NO_FRAME: u16 = u16::MAX;

pub struct Selection {
    pub geom: PlaneGeometry,
    pub focus: Vec<f32>,
    pub index: Vec<u16>,
    pub w0: Vec<u32>,
    pub w1: Vec<u32>,
    pub frames: u32,
}

impl Selection {
    pub fn new(geom: PlaneGeometry) -> Self {
        let n = geom.pixels();
        Self {
            geom,
            focus: vec![f32::NEG_INFINITY; n],
            index: vec![NO_FRAME; n],
            w0: vec![0; n],
            w1: vec![0; n],
            frames: 0,
        }
    }

    #[inline]
    pub fn beats(focus: f32, index: u16, cur_focus: f32, cur_index: u16) -> bool {
        focus > cur_focus || (focus == cur_focus && index < cur_index)
    }

    /// Fold one frame in. `words` is the packed active area as u32 quad words,
    /// `row_words` words per active row.
    pub fn fold(&mut self, frame_index: u16, words: &[u32], row_words: usize, focus: &[f32]) {
        assert_eq!(focus.len(), self.geom.pixels());
        let w = self.geom.width;
        for py in 0..self.geom.height {
            let r0 = (2 * py) * row_words;
            let r1 = (2 * py + 1) * row_words;
            let base = py * w;
            for px in 0..w {
                let i = base + px;
                let f = focus[i];
                if Self::beats(f, frame_index, self.focus[i], self.index[i]) {
                    self.focus[i] = f;
                    self.index[i] = frame_index;
                    self.w0[i] = words[r0 + px];
                    self.w1[i] = words[r1 + px];
                }
            }
        }
        self.frames += 1;
    }

    pub fn absorb(&mut self, other: &Selection) {
        for i in 0..self.geom.pixels() {
            if Self::beats(other.focus[i], other.index[i], self.focus[i], self.index[i]) {
                self.focus[i] = other.focus[i];
                self.index[i] = other.index[i];
                self.w0[i] = other.w0[i];
                self.w1[i] = other.w1[i];
            }
        }
        self.frames += other.frames;
    }
}

// ---------------------------------------------------------------------------
// The independent f64 reference. NOT a copy of anything.
// ---------------------------------------------------------------------------

/// Naive clamped-window gather in f64, then the focus value in f64.
///
/// Written from the border policy stated in `boxfilter.rs`'s module docs — the
/// window is intersected with the plane and the mean is taken over what
/// survives — not from its implementation. This is arithmetic truth for the
/// ring value; only the final division by sigma uses the same f32 noise
/// expression, because that expression *is* the definition.
pub fn exact_focus_f64(luma: &[f32], geom: PlaneGeometry, noise: &Noise, inner_r: usize, outer_r: usize) -> Vec<f64> {
    let (w, h) = (geom.width, geom.height);
    let mean = |px: usize, py: usize, r: usize| -> f64 {
        let x0 = px.saturating_sub(r);
        let x1 = (px + r).min(w - 1);
        let y0 = py.saturating_sub(r);
        let y1 = (py + r).min(h - 1);
        let mut sum = 0.0f64;
        let mut n = 0u32;
        for yy in y0..=y1 {
            for xx in x0..=x1 {
                sum += luma[yy * w + xx] as f64;
                n += 1;
            }
        }
        sum / n as f64
    };
    let mut out = vec![0.0f64; geom.pixels()];
    for py in 0..h {
        for px in 0..w {
            let i = py * w + px;
            let ring = (mean(px, py, inner_r) - mean(px, py, outer_r)).abs();
            // sigma in f64, from the same model.
            let s = (luma[i] as f64).max(0.0);
            let g = noise.gain_dn_per_e as f64;
            let read_dn = noise.read_noise_e as f64 * g;
            let var = g * s + read_dn * read_dn;
            let sigma = (0.25 * (var + var)).sqrt().max(SIGMA_EPS as f64);
            out[i] = ring / sigma;
        }
    }
    out
}
