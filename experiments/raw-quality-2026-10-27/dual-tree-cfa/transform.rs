// Independently written from the published filter facts pinned in design.md.
// No toolbox implementation or coefficient asset was consulted.
use rayon::prelude::*;

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct Complex {
    pub re: f32,
    pub im: f32,
}
#[derive(Clone, Debug)]
pub(crate) struct ComplexBand {
    pub level: usize,
    pub direction: usize,
    pub width: usize,
    pub height: usize,
    pub values: Vec<Complex>,
}
#[derive(Clone, Debug)]
pub(crate) struct Coefficients {
    pub bands: Vec<ComplexBand>,
    pub low: [Vec<f32>; 4],
}
#[derive(Clone, Debug)]
pub(crate) struct Plan {
    pub input_width: usize,
    pub input_height: usize,
    pub padded_width: usize,
    pub padded_height: usize,
    pub levels: usize,
}
impl Plan {
    pub(crate) fn new(width: usize, height: usize) -> Result<Self> {
        ensure!(
            width > 0 && height > 0 && width <= 4096 && height <= 4096,
            "bounded dual-tree phase extent"
        );
        Ok(Self {
            input_width: width,
            input_height: height,
            padded_width: 2 * width.div_ceil(128) * 128,
            padded_height: 2 * height.div_ceil(128) * 128,
            levels: 7,
        })
    }
    fn validate(&self) -> Result<()> {
        let expected = Self::new(self.input_width, self.input_height)?;
        ensure!(
            self.padded_width == expected.padded_width
                && self.padded_height == expected.padded_height
                && self.levels == 7,
            "modified dual-tree plan"
        );
        Ok(())
    }
    pub(crate) fn band_shapes(&self) -> Vec<(usize, usize)> {
        (0..self.levels)
            .map(|k| (self.padded_width >> (k + 1), self.padded_height >> (k + 1)))
            .collect()
    }
}

// Bal2012 Table1, tap indices0..9, local a/b convention.
const FIRST_LOW: [[f32; 10]; 2] = [
    [
        0.,
        -0.08838834,
        0.08838834,
        0.69587998,
        0.69587998,
        0.08838834,
        -0.08838834,
        0.01122679,
        0.01122679,
        0.,
    ],
    [
        0.01122679,
        0.01122679,
        -0.08838834,
        0.08838834,
        0.69587998,
        0.69587998,
        0.08838834,
        -0.08838834,
        0.,
        0.,
    ],
];
const FIRST_HIGH: [[f32; 10]; 2] = [
    [
        0.,
        -0.01122679,
        0.01122679,
        0.08838834,
        0.08838834,
        -0.69587998,
        0.69587998,
        -0.08838834,
        -0.08838834,
        0.,
    ],
    [
        0.,
        0.,
        -0.08838834,
        -0.08838834,
        0.69587998,
        -0.69587998,
        0.08838834,
        0.08838834,
        0.01122679,
        -0.01122679,
    ],
];
// Kingsbury2001 Table2 HL, coefficients of z^-n for n=-6..7.
const Q14: [f32; 14] = [
    0.00325314,
    -0.00388321,
    0.03466035,
    -0.03887280,
    -0.11720389,
    0.27529538,
    0.75614564,
    0.56881042,
    0.01186609,
    -0.10671180,
    0.02382538,
    0.01702522,
    -0.00543948,
    -0.00455690,
];
#[derive(Clone)]
struct Filters {
    first_index: isize,
    low: Vec<f32>,
    high: Vec<f32>,
}
fn filters(level: usize, tree: usize) -> Filters {
    if level == 0 {
        return Filters {
            first_index: 0,
            low: FIRST_LOW[tree].to_vec(),
            high: FIRST_HIGH[tree].to_vec(),
        };
    }
    let mut low = Vec::with_capacity(14);
    let mut high = Vec::with_capacity(14);
    for j in 0..14 {
        let n = j as isize - 6;
        let alternating = if n.rem_euclid(2) == 0 { 1. } else { -1. };
        if tree == 0 {
            low.push(Q14[j]);
            high.push(alternating * Q14[13 - j]);
        } else {
            low.push(Q14[13 - j]);
            high.push(-alternating * Q14[j]);
        }
    }
    Filters {
        first_index: -6,
        low,
        high,
    }
}
fn reflected(t: usize, length: usize) -> usize {
    let r = t % (2 * length);
    if r < length { r } else { 2 * length - 1 - r }
}
fn extend(input: &[f32], p: &Plan) -> Vec<f32> {
    let mw = p.padded_width / 2;
    let mh = p.padded_height / 2;
    let mut output = vec![0.; p.padded_width * p.padded_height];
    // Reflect to the multiple128 core, then mirror that core. This composition
    // deliberately differs from reflecting the original straight to2M/2N.
    output
        .par_chunks_mut(p.padded_width)
        .enumerate()
        .for_each(|(y, row)| {
            let sy = reflected(reflected(y, mh), p.input_height);
            for (x, value) in row.iter_mut().enumerate() {
                let sx = reflected(reflected(x, mw), p.input_width);
                *value = input[sy * p.input_width + sx];
            }
        });
    output
}
fn analysis_indices(length: usize, f: &Filters) -> Vec<usize> {
    (0..length / 2)
        .flat_map(|m| {
            (0..f.low.len()).map(move |j| {
                (2 * m as isize - f.first_index - j as isize).rem_euclid(length as isize) as usize
            })
        })
        .collect()
}
fn split_x(input: &[f32], w: usize, h: usize, f: &Filters) -> (Vec<f32>, Vec<f32>) {
    let nw = w / 2;
    let taps = f.low.len();
    let ix = analysis_indices(w, f);
    let mut low = vec![0.; nw * h];
    let mut high = vec![0.; nw * h];
    // Four real trees are the parallel work units; each kernel's accumulation
    // order is serial and fixed. Avoid nested per-source parallelism.
    for y in 0..h {
        for x in 0..nw {
            let mut a = 0.0f32;
            let mut b = 0.0f32;
            for j in 0..taps {
                let v = input[y * w + ix[x * taps + j]];
                a += f.low[j] * v;
                b += f.high[j] * v;
            }
            low[y * nw + x] = a;
            high[y * nw + x] = b;
        }
    }
    (low, high)
}
fn split_y(input: &[f32], w: usize, h: usize, f: &Filters) -> (Vec<f32>, Vec<f32>) {
    let nh = h / 2;
    let taps = f.low.len();
    let iy = analysis_indices(h, f);
    let mut low = vec![0.; w * nh];
    let mut high = vec![0.; w * nh];
    for y in 0..nh {
        // Contiguous x loop permits SIMD without changing tap accumulation.
        for j in 0..taps {
            let src = &input[iy[y * taps + j] * w..][..w];
            let dst = y * w;
            for x in 0..w {
                low[dst + x] += f.low[j] * src[x];
                high[dst + x] += f.high[j] * src[x];
            }
        }
    }
    (low, high)
}
fn join_y(low: &[f32], high: &[f32], w: usize, h: usize, f: &Filters) -> Vec<f32> {
    let output_h = 2 * h;
    let mut out = vec![0.; w * output_h];
    for y in 0..output_h {
        for j in 0..f.low.len() {
            let v = y as isize + f.first_index + j as isize;
            if v.rem_euclid(2) != 0 {
                continue;
            }
            let sy = (v / 2).rem_euclid(h as isize) as usize;
            for x in 0..w {
                out[y * w + x] += f.low[j] * low[sy * w + x] + f.high[j] * high[sy * w + x];
            }
        }
    }
    out
}
fn join_x(low: &[f32], high: &[f32], w: usize, h: usize, f: &Filters) -> Vec<f32> {
    let ow = 2 * w;
    let mut out = vec![0.; ow * h];
    for y in 0..h {
        for x in 0..ow {
            let mut value = 0.0f32;
            for j in 0..f.low.len() {
                let v = x as isize + f.first_index + j as isize;
                if v.rem_euclid(2) != 0 {
                    continue;
                }
                let sx = (v / 2).rem_euclid(w as isize) as usize;
                value += f.low[j] * low[y * w + sx] + f.high[j] * high[y * w + sx];
            }
            out[y * ow + x] = value;
        }
    }
    out
}
struct RealTree {
    details: Vec<[Vec<f32>; 3]>,
    low: Vec<f32>,
}
fn real_forward(input: &[f32], p: &Plan, tx: usize, ty: usize) -> RealTree {
    let mut current = input.to_vec();
    let (mut w, mut h) = (p.padded_width, p.padded_height);
    let mut details = Vec::with_capacity(p.levels);
    for k in 0..p.levels {
        let (xl, xh) = split_x(&current, w, h, &filters(k, tx));
        drop(current);
        let (ll, lh) = split_y(&xl, w / 2, h, &filters(k, ty));
        drop(xl);
        let (hl, hh) = split_y(&xh, w / 2, h, &filters(k, ty));
        current = ll;
        details.push([lh, hl, hh]);
        w /= 2;
        h /= 2;
    }
    RealTree {
        details,
        low: current,
    }
}
fn validate_coefficients(c: &Coefficients, p: &Plan) -> Result<()> {
    ensure!(c.bands.len() == 6 * p.levels, "dual-tree band count");
    for (index, b) in c.bands.iter().enumerate() {
        let k = index / 6;
        ensure!(
            b.level == k
                && b.direction == index % 6
                && b.width == p.padded_width >> (k + 1)
                && b.height == p.padded_height >> (k + 1)
                && b.values.len() == b.width * b.height
                && b.values
                    .iter()
                    .all(|v| v.re.is_finite() && v.im.is_finite()),
            "dual-tree coefficient shape/nonfinite"
        );
    }
    let n = (p.padded_width >> p.levels) * (p.padded_height >> p.levels);
    ensure!(
        c.low
            .iter()
            .all(|a| a.len() == n && a.iter().all(|v| v.is_finite())),
        "dual-tree lowpass shape/nonfinite"
    );
    Ok(())
}
pub(crate) fn forward_phase(input: &[f32], plan: &Plan) -> Result<Coefficients> {
    plan.validate()?;
    ensure!(
        input.len() == plan.input_width * plan.input_height && input.iter().all(|v| v.is_finite()),
        "dual-tree input shape/nonfinite"
    );
    let extended = extend(input, plan);
    let trees = (0..4usize)
        .into_par_iter()
        .map(|tree| real_forward(&extended, plan, tree / 2, tree % 2))
        .collect::<Vec<_>>();
    drop(extended);
    let mut iter = trees.into_iter();
    let aa = iter.next().unwrap();
    let ab = iter.next().unwrap();
    let ba = iter.next().unwrap();
    let bb = iter.next().unwrap();
    let low = [aa.low, ab.low, ba.low, bb.low];
    let mut bands = Vec::with_capacity(6 * plan.levels);
    let s = std::f32::consts::FRAC_1_SQRT_2;
    for (level, (((a, b), c), d)) in aa
        .details
        .into_iter()
        .zip(ab.details)
        .zip(ba.details)
        .zip(bb.details)
        .enumerate()
    {
        let width = plan.padded_width >> (level + 1);
        let height = plan.padded_height >> (level + 1);
        for (group, (((a, b), c), d)) in a.into_iter().zip(b).zip(c).zip(d).enumerate() {
            let mut plus = Vec::with_capacity(a.len());
            let mut minus = Vec::with_capacity(a.len());
            for j in 0..a.len() {
                plus.push(Complex {
                    re: (a[j] - d[j]) * s,
                    im: (b[j] + c[j]) * s,
                });
                minus.push(Complex {
                    re: (a[j] + d[j]) * s,
                    im: (b[j] - c[j]) * s,
                });
            }
            bands.push(ComplexBand {
                level,
                direction: 2 * group,
                width,
                height,
                values: plus,
            });
            bands.push(ComplexBand {
                level,
                direction: 2 * group + 1,
                width,
                height,
                values: minus,
            });
        }
    }
    let out = Coefficients { bands, low };
    validate_coefficients(&out, plan)?;
    Ok(out)
}
fn unpack(c: &Coefficients, level: usize, tree: usize) -> [Vec<f32>; 3] {
    let s = std::f32::consts::FRAC_1_SQRT_2;
    std::array::from_fn(|group| {
        c.bands[6 * level + 2 * group]
            .values
            .iter()
            .zip(&c.bands[6 * level + 2 * group + 1].values)
            .map(|(p, m)| match tree {
                0 => (p.re + m.re) * s,
                1 => (p.im + m.im) * s,
                2 => (p.im - m.im) * s,
                3 => (m.re - p.re) * s,
                _ => unreachable!(),
            })
            .collect()
    })
}
fn real_inverse(c: &Coefficients, p: &Plan, tree: usize) -> Vec<f32> {
    let mut current = c.low[tree].clone();
    for k in (0..p.levels).rev() {
        let w = p.padded_width >> (k + 1);
        let h = p.padded_height >> (k + 1);
        let [lh, hl, hh] = unpack(c, k, tree);
        let xl = join_y(&current, &lh, w, h, &filters(k, tree % 2));
        let xh = join_y(&hl, &hh, w, h, &filters(k, tree % 2));
        current = join_x(&xl, &xh, w, 2 * h, &filters(k, tree / 2));
    }
    current
}
pub(crate) fn inverse_phase(c: &Coefficients, plan: &Plan) -> Result<Vec<f32>> {
    plan.validate()?;
    validate_coefficients(c, plan)?;
    let trees = (0..4usize)
        .into_par_iter()
        .map(|tree| real_inverse(c, plan, tree))
        .collect::<Vec<_>>();
    let mut out = vec![0.; plan.input_width * plan.input_height];
    for y in 0..plan.input_height {
        for x in 0..plan.input_width {
            let j = y * plan.padded_width + x;
            out[y * plan.input_width + x] =
                ((trees[0][j] + trees[1][j]) + (trees[2][j] + trees[3][j])) * 0.25;
        }
    }
    ensure!(
        out.iter().all(|v| v.is_finite()),
        "dual-tree nonfinite inverse"
    );
    Ok(out)
}
