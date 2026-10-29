// Exact frozen qualification prefix; only inner-doc markers converted to comments.
#![allow(dead_code, unused_imports)]
// Source-only qualification for real temporal comparisons, before output noise.
// Streaming one original through bounded existing native-CFA gathers; no volume.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path};
use strehl_cli::{
    session_cache::SourceCache,
    session_input::{ResolvedSession, SourceIdentity},
    session_reconstruction_sampling::RegionSampler,
    session_sampling::SamplingDomain,
};
use strehl_core::{
    CfaPlane,
    boxfilter::box_mean,
    noise::{Levels, NoiseModel, PlaneNoise, Provenance},
    optics::profile_for_capture_env,
    plane::QuadSource,
    warpmap::WarpMap,
};

const SIDE: usize = 128;
// Narrow-focus follow-up after the archived20-step scope refused all36 tiles.
// Guides/validation bracket both withheld measurements; no output-noise value
// was consulted. Only two temporal replicates are available in this scope.
const GUIDES: [usize; 5] = [26, 28, 30, 32, 34];
const VALIDATE: [usize; 2] = [27, 33];
const MEASURE: [usize; 2] = [29, 31];
const TILES: [(usize, usize); 9] = [
    (16, 16),
    (48, 16),
    (80, 16),
    (16, 48),
    (48, 48),
    (80, 48),
    (16, 80),
    (48, 80),
    (80, 80),
];
type Planes = [Vec<f32>; 4];
fn zero() -> Planes {
    std::array::from_fn(|_| vec![0.; SIDE * SIDE])
}
fn sha(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect()
}
fn read(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}
fn write(path: &Path, value: &Value) -> Result<()> {
    let mut file = fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)?;
    serde_json::to_writer_pretty(&mut file, value)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    Ok(())
}
fn quantile(mut values: Vec<f32>, q: f32) -> f32 {
    values.sort_by(f32::total_cmp);
    values[((values.len() - 1) as f32 * q) as usize]
}
fn smooth(values: &Planes) -> Planes {
    let mut out = zero();
    let mut scratch = vec![0.; SIDE * SIDE];
    for c in 0..4 {
        box_mean(
            &values[c],
            strehl_core::plane::PlaneGeometry {
                width: SIDE,
                height: SIDE,
            },
            2,
            &mut scratch,
            &mut out[c],
        );
    }
    out
}
struct Qualification {
    sum: Planes,
    min: Planes,
    max: Planes,
    validation_min: Planes,
    validation_max: Planes,
    means: Vec<[[f32; 4]; 9]>,
    valid: Vec<bool>,
    guides: usize,
    validations: usize,
}
impl Qualification {
    fn new() -> Self {
        Self {
            sum: zero(),
            min: std::array::from_fn(|_| vec![f32::INFINITY; SIDE * SIDE]),
            max: std::array::from_fn(|_| vec![f32::NEG_INFINITY; SIDE * SIDE]),
            validation_min: std::array::from_fn(|_| vec![f32::INFINITY; SIDE * SIDE]),
            validation_max: std::array::from_fn(|_| vec![f32::NEG_INFINITY; SIDE * SIDE]),
            means: Vec::new(),
            valid: vec![true; SIDE * SIDE],
            guides: 0,
            validations: 0,
        }
    }
    fn observe(&mut self, source: &Planes, support: &[bool], validation: bool) {
        let image = smooth(source);
        let mut means = [[0.; 4]; 9];
        for c in 0..4 {
            for i in 0..SIDE * SIDE {
                if validation {
                    self.validation_min[c][i] = self.validation_min[c][i].min(image[c][i]);
                    self.validation_max[c][i] = self.validation_max[c][i].max(image[c][i]);
                } else {
                    self.sum[c][i] += image[c][i];
                    self.min[c][i] = self.min[c][i].min(image[c][i]);
                    self.max[c][i] = self.max[c][i].max(image[c][i]);
                }
            }
        }
        for (tile, &(x, y)) in TILES.iter().enumerate() {
            for c in 0..4 {
                let mut total = 0.;
                for yy in y..y + 32 {
                    for xx in x..x + 32 {
                        total += image[c][yy * SIDE + xx];
                    }
                }
                means[tile][c] = total / 1024.;
            }
        }
        for y in 2..SIDE - 2 {
            for x in 2..SIDE - 2 {
                self.valid[y * SIDE + x] &=
                    (y - 2..=y + 2).all(|yy| (x - 2..=x + 2).all(|xx| support[yy * SIDE + xx]));
            }
        }
        self.means.push(means);
        if validation {
            self.validations += 1;
        } else {
            self.guides += 1;
        }
    }
    fn result(&self, noise: &NoiseModel, beta: f32) -> Result<Vec<Value>> {
        ensure!(
            self.guides == GUIDES.len() && self.validations == VALIDATE.len(),
            "qualification frame census differs"
        );
        ensure!(
            beta.is_finite() && beta > 0.,
            "invalid source sampling noise transfer"
        );
        let mut rows = Vec::new();
        for (tile, &(x, y)) in TILES.iter().enumerate() {
            let indices: Vec<_> = (y..y + 32)
                .flat_map(|yy| (x..x + 32).map(move |xx| yy * SIDE + xx))
                .collect();
            let support = indices.iter().all(|&i| self.valid[i]);
            let mut accepted = support;
            let mut colors = Vec::new();
            for c in 0..4 {
                let mean: Vec<_> = indices
                    .iter()
                    .map(|&i| self.sum[c][i] / self.guides as f32)
                    .collect();
                let sigma: Vec<_> = mean
                    .iter()
                    .map(|&v| (noise.variance(CfaPlane::ALL[c], v) * beta).sqrt())
                    .collect();
                let range = quantile(
                    indices
                        .iter()
                        .zip(&sigma)
                        .map(|(&i, &s)| (self.max[c][i] - self.min[c][i]) / s)
                        .collect(),
                    0.95,
                );
                let validation = quantile(
                    indices
                        .iter()
                        .zip(&mean)
                        .zip(&sigma)
                        .map(|((&i, &m), &s)| {
                            (self.validation_max[c][i] - m)
                                .abs()
                                .max((self.validation_min[c][i] - m).abs())
                                / s
                        })
                        .collect(),
                    0.95,
                );
                let mean_dn = mean.iter().sum::<f32>() / 1024.;
                let mean_sigma = sigma.iter().sum::<f32>() / 1024.;
                let min_mean = self
                    .means
                    .iter()
                    .map(|m| m[tile][c])
                    .fold(f32::INFINITY, f32::min);
                let max_mean = self
                    .means
                    .iter()
                    .map(|m| m[tile][c])
                    .fold(f32::NEG_INFINITY, f32::max);
                let drift = (max_mean - min_mean) / mean_sigma;
                let gradient = quantile(
                    indices
                        .iter()
                        .zip(&sigma)
                        .map(|(&i, &s)| {
                            let value = self.sum[c][i] / self.guides as f32;
                            let dx = (self.sum[c][i + 1] / self.guides as f32 - value).abs();
                            let dy = (self.sum[c][i + SIDE] / self.guides as f32 - value).abs();
                            dx.max(dy) / s
                        })
                        .collect(),
                    0.95,
                );
                // Two independent validation frames versus a five-frame mean:
                // a 5x5 box gives ~sqrt(1+1/5)/5 = .219 raw-sigma noise.
                // The 95th percentile of max(|Z1|,|Z2|) is about2.49 sigma;
                // .65 leaves finite spatial-sample margin over the .546 null.
                let allowed = mean_dn > 64.
                    && range <= 1.0
                    && validation <= 0.65
                    && drift <= 0.25
                    && gradient <= 0.5;
                accepted &= allowed;
                colors.push(json!({"mean_dn":mean_dn,"mean_sample_sigma":mean_sigma,
                    "guide_range_p95_sigma":range,"validation_p95_sigma":validation,"mean_drift_sigma":drift,
                    "guide_gradient_p95_sigma":gradient,"accepted":allowed}));
            }
            rows.push(json!({"tile":tile,"origin_quad_local":[x,y],"size_quad":32,
                "complete_support":support,"colors":colors,"accepted":accepted}));
        }
        Ok(rows)
    }
}

fn random(state: &mut u64) -> f32 {
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    (((*state >> 40) as u32) as f32 + 0.5) / 16777216.
}
fn gaussian(state: &mut u64) -> f32 {
    (-2. * random(state).ln()).sqrt() * (std::f32::consts::TAU * random(state)).cos()
}
fn model() -> NoiseModel {
    NoiseModel::new(
        [PlaneNoise {
            gain_dn_per_e: 0.229,
            read_noise_e: 4.2,
            levels: Levels {
                black: 512.,
                white: 15360.,
            },
        }; 4],
        100.,
        Provenance::Profile,
    )
}
fn commission() -> Result<Value> {
    // Actual qualification code: flat first, then fixed drift and translated
    // two-dimensional structure. A static field need not be perfectly uniform.
    let noise = model();
    let mut reports = Vec::new();
    for mode in ["flat", "drift", "translated-texture", "defocus"] {
        let mut counts = Vec::new();
        for seed in 0..8 {
            let mut q = Qualification::new();
            let mut state = 1 + 20261028 + seed * 53139;
            for frame in 0..7 {
                let validation = frame >= 5;
                let temporal = if validation {
                    if frame == 5 { 1. } else { -1. }
                } else {
                    (frame as f32 - 2.) / 2.
                };
                let values = std::array::from_fn(|_| {
                    (0..SIDE * SIDE)
                        .map(|i| {
                            let x = (i % SIDE) as f32;
                            let y = (i / SIDE) as f32;
                            let signal = match mode {
                                "drift" => 1200. + temporal * 30.,
                                "translated-texture" => {
                                    1200.
                                        + 100. * ((x + temporal) * 0.5).sin()
                                        + 80. * ((y - temporal) * 0.3).cos()
                                }
                                "defocus" => {
                                    1200.
                                        + (1. - 0.5 * temporal.abs())
                                            * (100. * (x * 0.5).sin() + 80. * (y * 0.3).cos())
                                }
                                _ => 1200.,
                            };
                            signal
                                + gaussian(&mut state) * noise.variance(CfaPlane::R, signal).sqrt()
                        })
                        .collect::<Vec<_>>()
                });
                q.observe(&values, &vec![true; SIDE * SIDE], validation);
            }
            let rows = q.result(&noise, 1.)?;
            if mode == "flat" && seed == 0 {
                println!("flat-first actual gate rows: {}", json!(rows));
            }
            counts.push(rows.iter().filter(|r| r["accepted"] == true).count());
        }
        let total: usize = counts.iter().sum();
        ensure!(
            if mode == "flat" {
                total >= 64
            } else {
                total == 0
            },
            "qualification commissioning failed: {mode} {counts:?}"
        );
        reports.push(json!({"mode":mode,"accepted_by_seed":counts,"total_tiles":72}));
    }
    Ok(
        json!({"flat_first":true,"actual_qualification_function":true,"cases":reports,
        "scope":"Known stationary signal and injected noise commissioning, not real camera noise validation."}),
    )
}

pub(crate) struct Gate(Qualification);
impl Gate {
    pub(crate) fn new() -> Self {
        Self(Qualification::new())
    }
    pub(crate) fn observe(&mut self, planes: &[Vec<f32>; 4], support: &[bool], validation: bool) {
        self.0.observe(planes, support, validation)
    }
    pub(crate) fn result(&self, noise: &NoiseModel) -> Result<Vec<Value>> {
        self.0.result(noise, 1.)
    }
}
