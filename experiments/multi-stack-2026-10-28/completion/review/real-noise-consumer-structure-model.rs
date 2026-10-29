//! Research observer: fixed Q=[0,4,8], V=[1,5,9], no R/M selection.
use anyhow::{Result, ensure};
use serde_json::{Value, json};
use strehl_core::{CfaPlane, noise::NoiseModel};
pub const SIDE: usize = 128;
pub const N: usize = SIDE * SIDE;
pub const LIMIT: f64 = 1.35;
pub type Planes = [Vec<f32>; 4];
type Field = [Vec<f64>; 4];
fn field() -> Field {
    std::array::from_fn(|_| vec![0.; N])
}
pub fn q_weights(t: f64) -> [f64; 3] {
    [
        (t - 4.) * (t - 8.) / 32.,
        -t * (t - 8.) / 16.,
        t * (t - 4.) / 32.,
    ]
}
fn quadratic(coeff: [f64; 3], t: f64) -> f64 {
    let z = (t - 4.) / 4.;
    coeff[0] + z * coeff[1] + z * z * coeff[2]
}
/// Three derived temporal coefficient fields; no retained aligned source volume.
/// Beta fields contain only known original-tap squared norms, not image values.
pub struct Gate {
    coefficients: [Field; 3],
    q_beta: [Field; 3],
    v_beta: [Field; 3],
    residual: [Field; 3],
    valid: Vec<bool>,
    q_seen: [bool; 3],
    v_seen: [bool; 3],
}
impl Gate {
    pub fn new() -> Self {
        Self {
            coefficients: std::array::from_fn(|_| field()),
            q_beta: std::array::from_fn(|_| field()),
            v_beta: std::array::from_fn(|_| field()),
            residual: std::array::from_fn(|_| field()),
            valid: vec![true; N],
            q_seen: [false; 3],
            v_seen: [false; 3],
        }
    }
    fn check(planes: &Planes, support: &[bool], beta: &Field, gain: f32) -> Result<()> {
        ensure!(
            gain.is_finite() && gain > 0. && support.len() == N,
            "observer shape/gain"
        );
        ensure!(
            planes
                .iter()
                .all(|p| p.len() == N && p.iter().all(|v| v.is_finite()))
                && beta
                    .iter()
                    .all(|p| p.len() == N && p.iter().all(|v| v.is_finite() && *v > 0.)),
            "observer samples/beta"
        );
        Ok(())
    }
    pub fn q(
        &mut self,
        j: usize,
        planes: &Planes,
        support: &[bool],
        beta: &Field,
        gain: f32,
    ) -> Result<()> {
        Self::check(planes, support, beta, gain)?;
        ensure!(
            j < 3 && !self.q_seen[j] && !self.v_seen.iter().any(|v| *v),
            "Q role/order"
        );
        let weights = [[0., -0.5, 0.5], [1., 0., -1.], [0., 0.5, 0.5]][j];
        for c in 0..4 {
            for i in 0..N {
                let x = f64::from(planes[c][i]) * f64::from(gain);
                for (k, w) in weights.iter().enumerate() {
                    self.coefficients[k][c][i] += w * x;
                }
                self.q_beta[j][c][i] = beta[c][i];
                self.valid[i] &= support[i];
            }
        }
        self.q_seen[j] = true;
        Ok(())
    }
    pub fn v(
        &mut self,
        j: usize,
        planes: &Planes,
        support: &[bool],
        beta: &Field,
        gain: f32,
    ) -> Result<()> {
        Self::check(planes, support, beta, gain)?;
        ensure!(
            j < 3 && !self.v_seen[j] && self.q_seen.iter().all(|v| *v),
            "V role/order"
        );
        let t = [1., 5., 9.][j];
        for c in 0..4 {
            for i in 0..N {
                let coef = std::array::from_fn(|k| self.coefficients[k][c][i]);
                self.residual[j][c][i] =
                    f64::from(planes[c][i]) * f64::from(gain) - quadratic(coef, t);
                self.v_beta[j][c][i] = beta[c][i];
                self.valid[i] &= support[i];
            }
        }
        self.v_seen[j] = true;
        Ok(())
    }
    pub fn finish(&self, noise: &NoiseModel, gain: f32) -> Result<Vec<Value>> {
        ensure!(
            self.q_seen.iter().chain(&self.v_seen).all(|v| *v),
            "missing Q/V role"
        );
        let mut rows = Vec::new();
        for ty in [16, 48, 80] {
            for tx in [16, 48, 80] {
                for c in 0..4 {
                    let mut energy = 0.;
                    let mut signed = [0.; 3];
                    let mut supported = 0;
                    for y in ty..ty + 32 {
                        for x in tx..tx + 32 {
                            let i = y * SIDE + x;
                            if !self.valid[i] {
                                continue;
                            }
                            let coeff = std::array::from_fn(|k| self.coefficients[k][c][i]);
                            // Local-constant per-tap signal approximation, from Q only. The
                            // same-photon plug-in denominator is commissioned, not exact.
                            let variance = |t: f64, beta: f64| {
                                let expected =
                                    (quadratic(coeff, t) / f64::from(gain)).max(0.) as f32;
                                f64::from(noise.plane(CfaPlane::ALL[c]).variance(expected))
                                    * f64::from(gain).powi(2)
                                    * beta
                            };
                            let qv: [f64; 3] = std::array::from_fn(|j| {
                                variance([0., 4., 8.][j], self.q_beta[j][c][i])
                            });
                            let h = [q_weights(1.), q_weights(5.), q_weights(9.)];
                            let matrix = std::array::from_fn(|a| {
                                std::array::from_fn(|b| {
                                    (0..3).map(|j| h[a][j] * h[b][j] * qv[j]).sum::<f64>()
                                        + if a == b {
                                            variance([1., 5., 9.][a], self.v_beta[a][c][i])
                                        } else {
                                            0.
                                        }
                                })
                            });
                            let r = std::array::from_fn(|j| self.residual[j][c][i]);
                            energy += mahalanobis(matrix, r)? / 3.;
                            for j in 0..3 {
                                signed[j] += r[j];
                            }
                            supported += 1;
                        }
                    }
                    let n = supported.max(1) as f64;
                    rows.push(json!({"tile_quad":[tx,ty,32,32],"color":c,"supported":supported,"energy":energy/n,"signed_validation_residual_dn":signed.map(|v|v/n),"accepted":supported==1024 && energy/n<=LIMIT}));
                }
            }
        }
        Ok(rows)
    }
}
pub fn mahalanobis(a: [[f64; 3]; 3], r: [f64; 3]) -> Result<f64> {
    let scale = a[0][0].max(a[1][1]).max(a[2][2]);
    ensure!(scale.is_finite() && scale > 0., "invalid covariance scale");
    let mut l = [[0f64; 3]; 3];
    for i in 0..3 {
        for j in 0..=i {
            let s = a[i][j] - (0..j).map(|k| l[i][k] * l[j][k]).sum::<f64>();
            if i == j {
                ensure!(s.is_finite() && s > 1e-12 * scale, "invalid covariance");
                l[i][j] = s.sqrt();
            } else {
                l[i][j] = s / l[j][j];
            }
        }
    }
    let mut z = [0.; 3];
    for i in 0..3 {
        z[i] = (r[i] - (0..i).map(|j| l[i][j] * z[j]).sum::<f64>()) / l[i][i];
    }
    Ok(z.iter().map(|v| v * v).sum())
}
#[test]
fn covariance_whitening_independent_diagonal() {
    assert!(
        (mahalanobis([[4., 0., 0.], [0., 9., 0.], [0., 0., 16.]], [2., 3., 4.]).unwrap() - 3.)
            .abs()
            < 1e-12
    );
    assert!(mahalanobis([[0.; 3]; 3], [0.; 3]).is_err());
}

#[test]
fn covariance_offdiagonal_direction_and_singularity() {
    let c = [[1., 0.9, 0.9], [0.9, 1., 0.9], [0.9, 0.9, 1.]];
    let aligned = mahalanobis(c, [1., 1., 1.]).unwrap();
    let contrary = mahalanobis(c, [1., -1., 0.]).unwrap();
    assert!((aligned - 3. / 2.8).abs() < 1e-12);
    assert!((contrary - 20.).abs() < 1e-11);
    assert!(contrary > aligned * 10.); // Diagonal-only inversion would miss this.
    assert!(
        mahalanobis(
            [[1., 1., 1.], [1., 1. + 1e-15, 1.], [1., 1., 1. + 1e-15]],
            [0.; 3]
        )
        .is_err()
    );
}
