//! Experimental spatial correction of the existing pyramid noise floor.
//!
//! For identity sampling, transports independent input variance through the
//! complete band and energy operators, anchored to their unit-variance response.
//! With resampling this is a heteroscedastic approximation: the existing measured
//! frame beta remains the absolute covariance normalization. It is not exact
//! arbitrary-warp covariance propagation. Only the first two bands are changed.
//! Compiled only with `spatial-noise-floor`; runtime default is off.
use crate::pyramid::LevelSize;
use rayon::prelude::*;
use std::collections::BTreeMap;

const K: [f32; 5] = [0.0625, 0.25, 0.375, 0.25, 0.0625];
const MAX_BANDS: usize = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Mode {
    #[default]
    Off,
    On,
    Shift,
    /// Cheap comparator: smooth the existing Gaussian variance at each band.
    Smooth,
}
impl Mode {
    pub fn from_environment() -> Self {
        match std::env::var("STREHL_SPATIAL_NOISE_FLOOR") {
            Err(std::env::VarError::NotPresent) => Self::Off,
            Ok(value) if value == "off" || value == "0" => Self::Off,
            Ok(value) if value == "on" || value == "1" => Self::On,
            Ok(value) if value == "shift" => Self::Shift,
            Ok(value) if value == "smooth" => Self::Smooth,
            value => {
                panic!("invalid STREHL_SPATIAL_NOISE_FLOOR: {value:?}; use off/on/shift/smooth")
            }
        }
    }
}

#[derive(Debug, Clone)]
struct Row(Vec<(usize, f32)>);
impl Row {
    fn sum(&self) -> f32 {
        self.0.iter().map(|(_, weight)| weight).sum()
    }
}
fn clamp(i: isize, n: usize) -> usize {
    i.clamp(0, n as isize - 1) as usize
}
fn combine<'a>(rows: impl IntoIterator<Item = (&'a Row, f32)>) -> Row {
    let mut sums = BTreeMap::<usize, f32>::new();
    for (row, weight) in rows {
        for &(i, value) in &row.0 {
            *sums.entry(i).or_default() += weight * value;
        }
    }
    Row(sums.into_iter().filter(|(_, v)| *v != 0.0).collect())
}
fn product(a: &Row, b: &Row) -> Row {
    let (mut i, mut j) = (0, 0);
    let mut out = Vec::new();
    while i < a.0.len() && j < b.0.len() {
        match a.0[i].0.cmp(&b.0[j].0) {
            std::cmp::Ordering::Less => i += 1,
            std::cmp::Ordering::Greater => j += 1,
            std::cmp::Ordering::Equal => {
                out.push((a.0[i].0, a.0[i].1 * b.0[j].1));
                i += 1;
                j += 1;
            }
        }
    }
    Row(out)
}
fn axis(n: usize, bands: usize) -> Vec<[Vec<Row>; 3]> {
    let mut gaussian = vec![(0..n).map(|i| Row(vec![(i, 1.0)])).collect::<Vec<_>>()];
    for k in 0..bands {
        let prev = &gaussian[k];
        let next =
            (0..prev.len().div_ceil(2))
                .map(|x| {
                    combine(K.iter().enumerate().map(|(t, &w)| {
                        (&prev[clamp(2 * x as isize + t as isize - 2, prev.len())], w)
                    }))
                })
                .collect();
        gaussian.push(next);
    }
    let mut out = Vec::new();
    for k in 0..bands {
        let g = &gaussian[k];
        let coarse = &gaussian[k + 1];
        let h: Vec<_> =
            (0..g.len())
                .map(|x| {
                    let phase: &[(isize, f32)] = if x % 2 == 0 {
                        &[(-1, 0.125), (0, 0.75), (1, 0.125)]
                    } else {
                        &[(0, 0.5), (1, 0.5)]
                    };
                    combine(phase.iter().map(|&(delta, w)| {
                        (&coarse[clamp((x / 2) as isize + delta, coarse.len())], w)
                    }))
                })
                .collect();
        let raw: [Vec<Row>; 3] = std::array::from_fn(|term| {
            g.iter()
                .zip(&h)
                .map(|(g, h)| match term {
                    0 => product(g, g),
                    1 => product(h, h),
                    _ => product(g, h),
                })
                .collect()
        });
        // S is linear on coefficient variance. Fold its weights into each
        // product row after combining original-source aliases and squaring.
        out.push(std::array::from_fn(|term| {
            (0..g.len())
                .map(|x| {
                    combine(K.iter().enumerate().map(|(t, &w)| {
                        (&raw[term][clamp(x as isize + t as isize - 2, g.len())], w)
                    }))
                })
                .collect()
        }));
    }
    out
}

#[derive(Debug, Clone)]
struct Band {
    size: LevelSize,
    x: [Vec<Row>; 3],
    y: [Vec<Row>; 3],
    unit_x: [Vec<f32>; 3],
    unit_y: [Vec<f32>; 3],
}
#[derive(Debug, Clone)]
pub struct Plan {
    source: LevelSize,
    bands: Vec<Band>,
}
impl Plan {
    pub fn new(sizes: &[LevelSize]) -> Self {
        assert!(!sizes.is_empty());
        let source = sizes[0];
        assert!(source.width > 0 && source.height > 0);
        for pair in sizes.windows(2) {
            assert_eq!(pair[0].reduced(), pair[1]);
        }
        let count = (sizes.len() - 1).min(MAX_BANDS);
        let xs = axis(source.width, count);
        let ys = axis(source.height, count);
        let bands = xs
            .into_iter()
            .zip(ys)
            .enumerate()
            .map(|(k, (x, y))| {
                let unit_x = std::array::from_fn(|t| x[t].iter().map(Row::sum).collect());
                let unit_y = std::array::from_fn(|t| y[t].iter().map(Row::sum).collect());
                Band {
                    size: sizes[k],
                    x,
                    y,
                    unit_x,
                    unit_y,
                }
            })
            .collect();
        Self { source, bands }
    }
    /// Effective variance, retaining the existing absolute frame-beta scale.
    /// Returns an empty vector in Off, otherwise the first one or two bands.
    pub fn transport(&self, variance: &[f32], mode: Mode) -> Vec<Vec<f32>> {
        let mut output = Vec::new();
        let mut scratch = Vec::new();
        self.transport_into(variance, mode, &mut output, &mut scratch);
        output
    }
    fn transport_into(
        &self,
        variance: &[f32],
        mode: Mode,
        output: &mut Vec<Vec<f32>>,
        scratch: &mut Vec<f32>,
    ) {
        if mode == Mode::Off {
            output.clear();
            return;
        }
        assert_eq!(variance.len(), self.source.pixels());
        assert!(
            variance.iter().all(|v| v.is_finite() && *v >= 0.0),
            "spatial noise floor needs finite nonnegative injected variance"
        );
        output.resize_with(self.bands.len(), Vec::new);
        let constant = variance
            .iter()
            .all(|v| v.to_bits() == variance[0].to_bits());
        if mode == Mode::Smooth && !constant {
            let mut current = variance.to_vec();
            for (k, band) in self.bands.iter().enumerate() {
                output[k].clone_from(&current);
                smooth5_field(&mut output[k], band.size, scratch);
                if k + 1 < self.bands.len() {
                    let mut next = vec![0.0; band.size.reduced().pixels()];
                    scratch.resize(band.size.pixels(), 0.0);
                    crate::pyramid::reduce(&current, band.size, &mut next, scratch);
                    current = next;
                }
            }
            return;
        }
        for (band, out) in self.bands.iter().zip(output) {
            out.resize(band.size.pixels(), 0.0);
            // Explicit constant contract, including f32 rounding: this preserves
            // every existing absolute beta and border approximation bitwise.
            if constant {
                out.fill(variance[0]);
                continue;
            }
            out.fill(0.0);
            scratch.resize(self.source.height * band.size.width, 0.0);
            for term in 0..3 {
                scratch
                    .par_chunks_mut(band.size.width)
                    .enumerate()
                    .for_each(|(y, row)| {
                        for (x, value) in row.iter_mut().enumerate() {
                            *value = band.x[term][x]
                                .0
                                .iter()
                                .map(|&(sx, w)| {
                                    let sx = if mode == Mode::Shift {
                                        (sx + 1) % self.source.width
                                    } else {
                                        sx
                                    };
                                    w * variance[y * self.source.width + sx]
                                })
                                .sum();
                        }
                    });
                out.par_chunks_mut(band.size.width)
                    .enumerate()
                    .for_each(|(y, row)| {
                        for (x, value) in row.iter_mut().enumerate() {
                            let response: f32 = band.y[term][y]
                                .0
                                .iter()
                                .map(|&(sy, w)| w * scratch[sy * band.size.width + x])
                                .sum();
                            if term < 2 {
                                *value += response;
                            } else {
                                let positive = *value;
                                let difference = positive - 2.0 * response;
                                assert!(
                                    difference.is_finite()
                                        && difference >= -2e-5 * positive.max(1e-20),
                                    "spatial variance cancellation exceeded rounding tolerance"
                                );
                                *value = difference.max(0.0);
                            }
                        }
                    });
            }
            out.par_chunks_mut(band.size.width)
                .enumerate()
                .for_each(|(y, row)| {
                    for (x, value) in row.iter_mut().enumerate() {
                        let normalizer = band.unit_x[0][x] * band.unit_y[0][y]
                            + band.unit_x[1][x] * band.unit_y[1][y]
                            - 2.0 * band.unit_x[2][x] * band.unit_y[2][y];
                        assert!(
                            normalizer.is_finite() && normalizer > 0.0,
                            "invalid unit-variance response"
                        );
                        *value /= normalizer;
                        assert!(
                            value.is_finite() && *value >= 0.0,
                            "invalid normalized spatial variance"
                        );
                    }
                });
        }
    }
}

fn smooth5_field(field: &mut [f32], size: LevelSize, scratch: &mut Vec<f32>) {
    scratch.resize(size.pixels(), 0.0);
    scratch
        .par_chunks_mut(size.width)
        .enumerate()
        .for_each(|(y, row)| {
            for (x, out) in row.iter_mut().enumerate() {
                *out = K
                    .iter()
                    .enumerate()
                    .map(|(t, &weight)| {
                        weight
                            * field[y * size.width + clamp(x as isize + t as isize - 2, size.width)]
                    })
                    .sum();
            }
        });
    field
        .par_chunks_mut(size.width)
        .enumerate()
        .for_each(|(y, row)| {
            for (x, out) in row.iter_mut().enumerate() {
                *out = K
                    .iter()
                    .enumerate()
                    .map(|(t, &weight)| {
                        weight
                            * scratch
                                [clamp(y as isize + t as isize - 2, size.height) * size.width + x]
                    })
                    .sum();
            }
        });
}

/// Optional per-worker state. Off allocates no plan, fields or scratch. It is
/// excluded from legacy chunk planning so enabling an experiment cannot change
/// arithmetic grouping. Active extra storage is about 2.25 input planes plus
/// short per-axis rows; this is not a claim about process peak memory.
#[derive(Debug, Clone, Default)]
pub(crate) struct Scratch {
    mode_override: Option<Mode>,
    plan: Option<Plan>,
    fields: Vec<Vec<f32>>,
    scratch: Vec<f32>,
}
impl Scratch {
    #[cfg(feature = "temporal-energy")]
    pub(crate) fn is_off(&self) -> bool {
        self.mode_override.unwrap_or_else(Mode::from_environment) == Mode::Off
    }
    pub(crate) fn set_mode(&mut self, mode: Mode) {
        self.mode_override = Some(mode);
    }
    pub(crate) fn prepare(&mut self, variance: &[f32], sizes: &[LevelSize]) {
        let mode = self.mode_override.unwrap_or_else(Mode::from_environment);
        if mode == Mode::Off {
            self.fields.clear();
            return;
        }
        let constant = variance.first().is_some_and(|first| {
            first.is_finite()
                && *first >= 0.0
                && variance.iter().all(|v| v.to_bits() == first.to_bits())
        });
        // Preserve the actual Gaussian pyramid's f32 constant response, not
        // merely its real-arithmetic identity: even tap sums can round.
        if constant {
            self.fields.clear();
            return;
        }
        let plan = self.plan.get_or_insert_with(|| Plan::new(sizes));
        assert_eq!(plan.source, sizes[0]);
        plan.transport_into(variance, mode, &mut self.fields, &mut self.scratch);
    }
    pub(crate) fn level(&self, k: usize) -> Option<&[f32]> {
        self.fields.get(k).map(Vec::as_slice)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pyramid::level_sizes;
    #[test]
    fn disabled_does_not_validate_or_allocate_transport() {
        let p = Plan::new(&level_sizes(32, 31, 3));
        assert!(p.transport(&[], Mode::Off).is_empty());
    }
    #[test]
    fn constant_variance_is_preserved_bitwise_on_all_phases_and_borders() {
        let sizes = level_sizes(33, 31, 3);
        let p = Plan::new(&sizes);
        for v in [0.0, 0.1, 17.0, 6400.0] {
            for mode in [Mode::On, Mode::Shift, Mode::Smooth] {
                let result = p.transport(&vec![v; sizes[0].pixels()], mode);
                assert_eq!(result.len(), 2);
                for (k, field) in result.iter().enumerate() {
                    assert_eq!(field.len(), sizes[k].pixels());
                    assert!(field.iter().all(|x| x.to_bits() == v.to_bits()));
                }
            }
        }
    }
    #[test]
    fn constant_consumer_keeps_original_gaussian_variance_bits() {
        let sizes = level_sizes(33, 31, 3);
        for mode in [Mode::On, Mode::Shift, Mode::Smooth] {
            let mut state = Scratch::default();
            state.set_mode(mode);
            state.prepare(&vec![0.1; sizes[0].pixels()], &sizes);
            assert!(state.plan.is_none());
            assert!(state.level(0).is_none() && state.level(1).is_none());
        }
    }
    #[test]
    fn shifted_variance_is_an_effective_negative_control() {
        let sizes = level_sizes(32, 32, 3);
        let p = Plan::new(&sizes);
        let mut v = vec![1.0; 1024];
        v[16 * 32 + 16] = 100.0;
        let a = p.transport(&v, Mode::On);
        let b = p.transport(&v, Mode::Shift);
        assert!(a[0].iter().zip(&b[0]).any(|(a, b)| (a - b).abs() > 1.0));
        assert!(a.iter().flatten().all(|x| x.is_finite() && *x >= 0.0));
    }
}
