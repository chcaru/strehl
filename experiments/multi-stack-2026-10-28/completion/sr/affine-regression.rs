//! Streaming f32 local-affine moments. No source pixel storage or fitted noise.
//! Conditional variance assumes frozen weights and independent original samples.
#[derive(Clone, Copy, Debug)]
pub struct Moments {
    // Symmetric order00,01,02,11,12,22.
    normal: [f32; 6],
    rhs: [f32; 3],
    noise: [f32; 6],
    minimum: f32,
    maximum: f32,
    count: usize,
}
impl Default for Moments {
    fn default() -> Self {
        Self {
            normal: [0.; 6],
            rhs: [0.; 3],
            noise: [0.; 6],
            minimum: f32::INFINITY,
            maximum: f32::NEG_INFINITY,
            count: 0,
        }
    }
}
#[derive(Clone, Copy, Debug)]
pub struct Estimate {
    pub value: f32,
    pub variance: f32,
    pub row: [f32; 3],
    pub sample_centroid: [f32; 2],
    pub minimum_relative_pivot: f32,
    pub observed_range: [f32; 2],
    pub samples: usize,
}
impl Estimate {
    /// Signed influence of the exact original sample. A second bounded gather
    /// may measure |h|-weighted phase support without storing a sample volume.
    pub fn influence(self, delta: [f32; 2], weight: f32) -> f32 {
        weight * (self.row[0] + self.row[1] * delta[0] + self.row[2] * delta[1])
    }
    pub fn within_observed_hull(self) -> bool {
        self.value >= self.observed_range[0] && self.value <= self.observed_range[1]
    }
}
impl Moments {
    pub fn add(
        &mut self,
        delta: [f32; 2],
        value: f32,
        weight: f32,
        variance: f32,
    ) -> Result<(), &'static str> {
        if !delta
            .iter()
            .chain([&value, &weight, &variance])
            .all(|v| v.is_finite())
            || weight < 0.
            || variance < 0.
        {
            return Err("invalid affine observation");
        }
        if weight == 0. {
            return Ok(());
        }
        let [x, y] = delta;
        let vv = [1., x, y, x * x, x * y, y * y];
        let noise_weight = weight * weight * variance;
        for k in 0..6 {
            self.normal[k] += weight * vv[k];
            self.noise[k] += noise_weight * vv[k];
        }
        for (k, v) in [1., x, y].into_iter().enumerate() {
            self.rhs[k] += weight * v * value;
        }
        self.minimum = self.minimum.min(value);
        self.maximum = self.maximum.max(value);
        self.count += 1;
        Ok(())
    }
    /// Solve the normalized3x3 moment matrix by Cholesky. The pivot cut is a
    /// numerical rank guard in physical sensor units, not a resolution claim.
    pub fn solve(self, minimum_relative_pivot: f32) -> Option<Estimate> {
        if !minimum_relative_pivot.is_finite()
            || minimum_relative_pivot <= 0.
            || self.count < 3
            || self.normal[0] <= 0.
        {
            return None;
        }
        let w = self.normal[0];
        let m = self.normal.map(|v| v / w);
        if !m
            .iter()
            .chain(self.rhs.iter())
            .chain(self.noise.iter())
            .all(|v| v.is_finite())
        {
            return None;
        }
        let xx = m[3] - m[1] * m[1];
        if xx <= minimum_relative_pivot {
            return None;
        }
        let l11 = xx.sqrt();
        let l21 = (m[4] - m[1] * m[2]) / l11;
        let yy = m[5] - m[2] * m[2] - l21 * l21;
        if yy <= minimum_relative_pivot {
            return None;
        }
        let l22 = yy.sqrt();
        let y1 = -m[1] / l11;
        let y2 = -(m[2] + l21 * y1) / l22;
        let z2 = y2 / l22;
        let z1 = (y1 - l21 * z2) / l11;
        let z0 = 1. - m[1] * z1 - m[2] * z2;
        let row = [z0 / w, z1 / w, z2 / w];
        let value = row[0] * self.rhs[0] + row[1] * self.rhs[1] + row[2] * self.rhs[2];
        let [a, b, c] = row;
        let v = self.noise;
        let variance = a * a * v[0]
            + 2. * a * b * v[1]
            + 2. * a * c * v[2]
            + b * b * v[3]
            + 2. * b * c * v[4]
            + c * c * v[5];
        if !value.is_finite()
            || !variance.is_finite()
            || variance < 0.
            || !row.iter().all(|v| v.is_finite())
        {
            return None;
        }
        Some(Estimate {
            value,
            variance,
            row,
            sample_centroid: [m[1], m[2]],
            minimum_relative_pivot: xx.min(yy),
            observed_range: [self.minimum, self.maximum],
            samples: self.count,
        })
    }
}
#[cfg(test)]
#[path = "affine-regression-tests.rs"]
mod tests;
