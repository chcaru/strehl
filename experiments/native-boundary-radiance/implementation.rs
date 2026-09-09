// Experimental local two-layer affine radiance reconstruction. No truth radiance enters.
use anyhow::{Result, ensure};
include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/native-boundary-radiance/source-hook.rs"));

pub(crate) const NEIGHBOUR_RADIUS: usize = 2;
pub(crate) const MIN_OBSERVATIONS: usize = 12;
pub(crate) const MIN_NORMALIZED_PIVOT: f32 = 1.0e-4;

#[derive(Clone, Debug)]
pub(crate) struct NormalSystem {
    normal: [[f32; 6]; 6],
    rhs: [f32; 6],
    yy: f32,
    origin: f32,
    minimum_variance: f32,
    observations: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Refusal {
    InsufficientObservations,
    RankDeficient,
    NonFinite,
    NegativeEstimate,
    ExcessVariance,
}

#[derive(Clone, Debug)]
pub(crate) struct Fit {
    pub(crate) coefficients: [f32; 6],
    pub(crate) value: f32,
    pub(crate) variance: f32,
    pub(crate) normalized_residual: f32,
    pub(crate) min_pivot: f32,
    pub(crate) observations: usize,
}

impl NormalSystem {
    pub(crate) fn new() -> Self {
        Self {
            normal: [[0.0; 6]; 6],
            rhs: [0.0; 6],
            yy: 0.0,
            origin: 0.0,
            minimum_variance: f32::INFINITY,
            observations: 0,
        }
    }

    pub(crate) fn add(&mut self, row: [f32; 6], value: f32, variance: f32) -> bool {
        if !row.iter().all(|v| v.is_finite()) || !value.is_finite()
            || !variance.is_finite() || variance <= 0.0
        {
            return false;
        }
        let mut next = self.clone();
        if next.observations == 0 {
            next.origin = value;
        }
        // Intercept centering preserves the model and avoids subtracting large
        // nearly equal residual sums for RAW values thousands of DN above black.
        let y = value - next.origin * (row[0] + row[3]);
        let weight = 1.0 / variance;
        for i in 0..6 {
            next.rhs[i] += weight * row[i] * y;
            for j in 0..6 {
                next.normal[i][j] += weight * row[i] * row[j];
            }
        }
        next.yy += weight * y * y;
        if !next.normal.iter().flatten().chain(next.rhs.iter()).all(|v| v.is_finite())
            || !next.yy.is_finite()
        {
            return false;
        }
        next.minimum_variance = next.minimum_variance.min(variance);
        next.observations += 1;
        *self = next;
        true
    }

    pub(crate) fn solve(&self, output_row: [f32; 6]) -> std::result::Result<Fit, Refusal> {
        if self.observations < MIN_OBSERVATIONS {
            return Err(Refusal::InsufficientObservations);
        }
        if !output_row.iter().all(|v| v.is_finite()) {
            return Err(Refusal::NonFinite);
        }
        let mut scale = [0.0f32; 6];
        for i in 0..6 {
            if self.normal[i][i] <= 0.0 {
                return Err(Refusal::RankDeficient);
            }
            scale[i] = self.normal[i][i].sqrt();
        }
        let mut lower = [[0.0f32; 6]; 6];
        let mut min_pivot = f32::INFINITY;
        for i in 0..6 {
            for j in 0..=i {
                let mut v = self.normal[i][j] / (scale[i] * scale[j]);
                for k in 0..j {
                    v -= lower[i][k] * lower[j][k];
                }
                if !v.is_finite() {
                    return Err(Refusal::NonFinite);
                }
                if i == j {
                    min_pivot = min_pivot.min(v);
                    if v < MIN_NORMALIZED_PIVOT {
                        return Err(Refusal::RankDeficient);
                    }
                    lower[i][j] = v.sqrt();
                } else {
                    lower[i][j] = v / lower[j][j];
                }
            }
        }
        let mut b = [0.0f32; 6];
        let mut q = [0.0f32; 6];
        for i in 0..6 {
            b[i] = self.rhs[i] / scale[i];
            q[i] = output_row[i] / scale[i];
        }
        let answer = cholesky_solve(&lower, b);
        let cov_q = cholesky_solve(&lower, q);
        let mut delta = [0.0f32; 6];
        let mut variance = 0.0;
        for i in 0..6 {
            delta[i] = answer[i] / scale[i];
            variance += q[i] * cov_q[i];
        }
        let mut coefficients = delta;
        coefficients[0] += self.origin;
        coefficients[3] += self.origin;
        let mut value = 0.0;
        let mut residual = self.yy;
        for i in 0..6 {
            value += output_row[i] * coefficients[i];
            residual -= 2.0 * delta[i] * self.rhs[i];
            for j in 0..6 {
                residual += delta[i] * self.normal[i][j] * delta[j];
            }
        }
        let normalized_residual = residual / (self.observations - 6) as f32;
        if !coefficients.iter().all(|v| v.is_finite()) || !value.is_finite()
            || !variance.is_finite() || !normalized_residual.is_finite()
        {
            return Err(Refusal::NonFinite);
        }
        if value < 0.0 {
            return Err(Refusal::NegativeEstimate);
        }
        if variance < 0.0 || variance > self.minimum_variance {
            return Err(Refusal::ExcessVariance);
        }
        Ok(Fit { coefficients, value, variance, normalized_residual, min_pivot,
            observations: self.observations })
    }
}

fn cholesky_solve(lower: &[[f32; 6]; 6], rhs: [f32; 6]) -> [f32; 6] {
    let mut x = rhs;
    for i in 0..6 {
        for j in 0..i {
            x[i] -= lower[i][j] * x[j];
        }
        x[i] /= lower[i][i];
    }
    for i in (0..6).rev() {
        for j in i + 1..6 {
            x[i] -= lower[j][i] * x[j];
        }
        x[i] /= lower[i][i];
    }
    x
}

pub(crate) fn apply_estimate(destination: &mut f32, fit: Option<&Fit>) -> bool {
    let Some(fit) = fit else { return false; };
    if !fit.value.is_finite() || fit.value < 0.0 {
        return false;
    }
    *destination = fit.value;
    true
}

pub(crate) fn point_moments(
    normal: [f32; 2], offset: f32, d_f: f32, d_b: f32,
    z: [f32; 2], target: [f32; 2],
) -> [f32; 6] {
    let norm = normal[0].hypot(normal[1]);
    let signed = normal[0] * z[0] + normal[1] * z[1] - offset;
    let mut m = [0.0f32; 2];
    let a = if d_f == 0.0 {
        if signed >= 0.0 { 1.0 } else { 0.0 }
    } else {
        let t = -signed / (d_f.abs() * norm);
        if t <= -1.0 { 1.0 } else if t >= 1.0 { 0.0 } else {
            let root = (1.0 - t * t).sqrt();
            let first = 2.0 * root * root * root / (3.0 * std::f32::consts::PI);
            let direction = d_f.signum() / norm;
            m = [normal[0] * direction * first, normal[1] * direction * first];
            (t.acos() - t * root) / std::f32::consts::PI
        }
    };
    let b = 1.0 - a;
    let x = z[0] - target[0];
    let y = z[1] - target[1];
    [a, x * a + d_f * m[0], y * a + d_f * m[1],
        b, x * b - d_b * m[0], y * b - d_b * m[1]]
}

#[derive(Clone)]
struct Polygon { vertices: [[f32; 2]; 8], len: usize }
impl Polygon {
    fn square() -> Self {
        Self { vertices: [[-0.5,-0.5],[0.5,-0.5],[0.5,0.5],[-0.5,0.5],
            [0.0;2],[0.0;2],[0.0;2],[0.0;2]], len: 4 }
    }
    fn clip(&self, normal: [f32; 2], offset: f32) -> Self {
        let mut out = Self { vertices: [[0.0; 2]; 8], len: 0 };
        if self.len == 0 { return out; }
        let mut previous = self.vertices[self.len - 1];
        let mut dp = normal[0]*previous[0] + normal[1]*previous[1] - offset;
        for &current in &self.vertices[..self.len] {
            let dc = normal[0]*current[0] + normal[1]*current[1] - offset;
            if (dp >= 0.0) != (dc >= 0.0) {
                let t = dp / (dp - dc);
                out.vertices[out.len] = [previous[0]+t*(current[0]-previous[0]),
                    previous[1]+t*(current[1]-previous[1])];
                out.len += 1;
            }
            if dc >= 0.0 {
                out.vertices[out.len] = current;
                out.len += 1;
            }
            previous = current;
            dp = dc;
        }
        out
    }
    fn moments(&self) -> [f32; 3] {
        let mut sums = [0.0f32; 3];
        if self.len < 3 { return sums; }
        for i in 0..self.len {
            let p = self.vertices[i];
            let q = self.vertices[(i + 1) % self.len];
            let cross = p[0]*q[1] - q[0]*p[1];
            sums[0] += cross;
            sums[1] += (p[0]+q[0])*cross;
            sums[2] += (p[1]+q[1])*cross;
        }
        [0.5*sums[0], sums[1]/6.0, sums[2]/6.0]
    }
}

const GL8: [(f32, f32); 8] = [
    (0.0198550718,0.0506142681),(0.1016667613,0.1111905172),
    (0.2372337950,0.1568533229),(0.4082826788,0.1813418917),
    (0.5917173212,0.1813418917),(0.7627662050,0.1568533229),
    (0.8983332387,0.1111905172),(0.9801449282,0.0506142681),
];

pub(crate) fn cell_moments(
    normal: [f32; 2], offset: f32, d_f: f32, d_b: f32,
    source: [f32; 2], target: [f32; 2],
) -> [f32; 6] {
    // Work within a unit square centred at zero, avoiding cancellation from
    // subtracting large absolute polygon-coordinate moments near the boundary.
    let c = offset - normal[0]*source[0] - normal[1]*source[1];
    let relative_target = [target[0]-source[0], target[1]-source[1]];
    let square = Polygon::square();
    let negative = [-normal[0],-normal[1]];
    let width = d_f.abs() * normal[0].hypot(normal[1]);
    let foreground = square.clip(normal, c + width).moments();
    let background = square.clip(negative, width - c).moments();
    let mut out = [foreground[0], foreground[1]-relative_target[0]*foreground[0],
        foreground[2]-relative_target[1]*foreground[0], background[0],
        background[1]-relative_target[0]*background[0],
        background[2]-relative_target[1]*background[0]];
    if d_f == 0.0 { return out; }
    let middle = square.clip(normal, c-width).clip(negative, -c-width);
    if middle.len < 3 { return out; }
    let v0 = middle.vertices[0];
    for triangle in 1..middle.len-1 {
        let a = [middle.vertices[triangle][0]-v0[0],middle.vertices[triangle][1]-v0[1]];
        let b = [middle.vertices[triangle+1][0]-v0[0],middle.vertices[triangle+1][1]-v0[1]];
        let cross = (a[0]*b[1]-a[1]*b[0]).abs();
        for &(r,wr) in &GL8 {
            for &(t,wt) in &GL8 {
                let z = [v0[0]+r*a[0]+(1.0-r)*t*b[0],
                    v0[1]+r*a[1]+(1.0-r)*t*b[1]];
                let row = point_moments(normal,c,d_f,d_b,z,relative_target);
                let weight = wr*wt*cross*(1.0-r);
                for k in 0..6 { out[k] += weight*row[k]; }
            }
        }
    }
    out
}

#[cfg(test)]
mod independent_tests {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/native-boundary-radiance/independent-tests.rs"));
}
