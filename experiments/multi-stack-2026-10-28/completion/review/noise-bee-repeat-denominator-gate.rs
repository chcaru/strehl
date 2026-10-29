//! EXPERIMENT ONLY denominator ablation; frozen production observer file is unchanged.
//! Same residuals/beta; replace ONLY denominator signal and/or known synthetic rounding variance.
use super::temporal::{Times, prediction, weights, whitened_energy};
use anyhow::{Result, ensure};
use serde_json::{Value, json};
use strehl_core::{CfaPlane, noise::NoiseModel};

pub const SIDE: usize = 128;
const N: usize = SIDE * SIDE;
pub type Planes = [Vec<f32>; 4];
pub type Norms = [Vec<f64>; 4];
fn field() -> Norms {
    std::array::from_fn(|_| vec![0.; N])
}

pub struct Gate {
    times: Times,
    // Derived intercept and change, not an aligned source-frame volume.
    coefficients: [Norms; 2],
    q_norms: [Norms; 2],
    v_norms: [Norms; 2],
    residuals: [Norms; 2],
    valid: Vec<bool>,
    seen_q: [bool; 2],
    seen_v: [bool; 2],
}

impl Gate {
    pub fn new(times: Times) -> Result<Self> {
        times.validate().map_err(anyhow::Error::msg)?;
        Ok(Self {
            times,
            coefficients: [field(), field()],
            q_norms: [field(), field()],
            v_norms: [field(), field()],
            residuals: [field(), field()],
            valid: vec![true; N],
            seen_q: [false; 2],
            seen_v: [false; 2],
        })
    }
    fn check(p: &Planes, s: &[bool], b: &Norms) -> Result<()> {
        ensure!(
            s.len() == N
                && p.iter()
                    .all(|a| a.len() == N && a.iter().all(|x| x.is_finite()))
                && b.iter()
                    .all(|a| a.len() == N && a.iter().all(|x| x.is_finite() && *x > 0.)),
            "observer inputs"
        );
        Ok(())
    }
    pub fn q(&mut self, j: usize, p: &Planes, s: &[bool], b: &Norms) -> Result<()> {
        Self::check(p, s, b)?;
        ensure!(
            j < 2 && !self.seen_q[j] && !self.seen_v.iter().any(|v| *v),
            "Q order"
        );
        for c in 0..4 {
            for i in 0..N {
                let x = f64::from(p[c][i]);
                if j == 0 {
                    self.coefficients[0][c][i] += x;
                    self.coefficients[1][c][i] -= x;
                } else {
                    self.coefficients[1][c][i] += x;
                }
                self.q_norms[j][c][i] = b[c][i];
                self.valid[i] &= s[i];
            }
        }
        self.seen_q[j] = true;
        Ok(())
    }
    fn expected(&self, c: usize, i: usize, time: f64) -> Result<f64> {
        let h = weights(self.times.q, time).map_err(anyhow::Error::msg)?;
        Ok(self.coefficients[0][c][i] + h[1] * self.coefficients[1][c][i])
    }
    pub fn v(&mut self, j: usize, p: &Planes, s: &[bool], b: &Norms) -> Result<()> {
        Self::check(p, s, b)?;
        ensure!(
            j < 2 && !self.seen_v[j] && self.seen_q.iter().all(|v| *v),
            "V order"
        );
        for c in 0..4 {
            for i in 0..N {
                self.residuals[j][c][i] =
                    f64::from(p[c][i]) - self.expected(c, i, self.times.v[j])?;
                self.v_norms[j][c][i] = b[c][i];
                self.valid[i] &= s[i];
            }
        }
        self.seen_v[j] = true;
        Ok(())
    }
    pub fn finish(
        &self,
        noise: &NoiseModel,
        limit: f64,
        oracle_level: Option<f64>,
        rounding_variance: f64,
    ) -> Result<Vec<Value>> {
        ensure!(
            rounding_variance.is_finite() && rounding_variance >= 0.,
            "rounding variance"
        );
        ensure!(
            limit.is_finite() && limit > 0. && self.seen_q.iter().chain(&self.seen_v).all(|v| *v),
            "gate incomplete/limit"
        );
        let mut rows = Vec::new();
        for ty in [16, 48, 80] {
            for tx in [16, 48, 80] {
                for c in 0..4 {
                    let mut energy = 0.;
                    let mut signed = [0.; 2];
                    let mut slope = 0.;
                    let mut slope2 = 0.;
                    let mut supported = 0;
                    for y in ty..ty + 32 {
                        for x in tx..tx + 32 {
                            let i = y * SIDE + x;
                            if !self.valid[i] {
                                continue;
                            }
                            let variance = |time: f64, beta: f64| -> Result<f64> {
                                let expected = oracle_level
                                    .unwrap_or(self.expected(c, i, time)?)
                                    .max(0.) as f32;
                                Ok((f64::from(noise.plane(CfaPlane::ALL[c]).variance(expected))
                                    + rounding_variance)
                                    * beta)
                            };
                            let qv = [
                                variance(self.times.q[0], self.q_norms[0][c][i])?,
                                variance(self.times.q[1], self.q_norms[1][c][i])?,
                            ];
                            let vv = [
                                variance(self.times.v[0], self.v_norms[0][c][i])?,
                                variance(self.times.v[1], self.v_norms[1][c][i])?,
                            ];
                            let cov = self.times.covariance(qv, vv).map_err(anyhow::Error::msg)?;
                            let r = [self.residuals[0][c][i], self.residuals[1][c][i]];
                            energy += whitened_energy(cov, r).map_err(anyhow::Error::msg)?;
                            signed[0] += r[0];
                            signed[1] += r[1];
                            let change =
                                self.coefficients[1][c][i] / (self.times.q[1] - self.times.q[0]);
                            slope += change;
                            slope2 += change * change;
                            supported += 1;
                        }
                    }
                    let n = supported.max(1) as f64;
                    rows.push(json!({"tile_quad":[tx,ty,32,32],"color":c,"supported":supported,
                "energy":energy/n,"signed_validation_residual_dn":signed.map(|x|x/n),
                "q_signed_slope_dn_per_second":slope/n,"q_rms_slope_dn_per_second":(slope2/n).sqrt(),
                "accepted":supported==1024 && energy/n<=limit}));
                }
            }
        }
        Ok(rows)
    }
}

// Keep reference interpolation in the same module-facing contract as the gate;
// it uses R values only after a complete Q/V mask has been frozen.
pub fn reference_at(times: Times, reference: [f64; 2], measurement: usize) -> Result<f64> {
    ensure!(measurement < 2, "measurement index");
    Ok(prediction(
        reference,
        weights(times.r, times.m[measurement]).map_err(anyhow::Error::msg)?,
    ))
}
