//! Pure geometry for the disabled nonlinear-lens research route.
//!
//! Centers are caller supplied, in full active native photosites. No metadata
//! units or physical calibration are inferred here. Validate an immutable value
//! before using its hot forward/inverse/map methods. Those methods still reject
//! nonfinite points, arithmetic overflow, and points outside the declared disk.

const UNIT: f32 = 1.0 / 16384.0;
const EPS: f32 = f32::EPSILON;

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct RadialCurve {
    pub center: [f32; 2],
    pub reference_radius: f32,
    pub input_scale: f32,
    pub output_scale: f32,
    pub max_input_radius: f32,
    pub knots: [i16; 16],
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct NativeSimilarity {
    pub a: [f32; 2],
    pub b: [f32; 2],
    pub center: [f32; 2],
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct ResearchPull {
    pub anchor: RadialCurve,
    pub source: RadialCurve,
    pub placement: NativeSimilarity,
}

fn finite(p: [f32; 2]) -> bool {
    p.into_iter().all(f32::is_finite)
}

fn norm(p: [f32; 2]) -> f32 {
    p[0].hypot(p[1])
}

fn distance(a: [f32; 2], b: [f32; 2]) -> f32 {
    norm([a[0] - b[0], a[1] - b[1]])
}

fn abs_max(p: [f32; 2]) -> f32 {
    p[0].abs().max(p[1].abs())
}

fn up(x: f32) -> f32 {
    if x.is_nan() || x == f32::INFINITY {
        x
    } else if x == 0.0 {
        f32::from_bits(1)
    } else if x > 0.0 {
        f32::from_bits(x.to_bits() + 1)
    } else {
        f32::from_bits(x.to_bits() - 1)
    }
}

fn down(x: f32) -> f32 {
    -up(-x)
}

fn padded(x: f32, allowance: f32) -> Option<f32> {
    let result = up(x + allowance);
    (result.is_finite() && allowance.is_finite() && allowance >= 0.0).then_some(result)
}

// A local two-part coordinate, never an image/storage type. Retain the small
// rounding residual between geometry stages; every operation is f32.
#[derive(Clone, Copy, Debug)]
struct CoordinatePart {
    high: f32,
    low: f32,
}

impl CoordinatePart {
    fn exact(high: f32) -> Self {
        Self { high, low: 0.0 }
    }

    fn normalized(a: f32, b: f32) -> Self {
        let [high, low] = NativeSimilarity::sum_parts(a, b);
        Self { high, low }
    }

    fn add(self, other: Self) -> Self {
        let [sum, error] = NativeSimilarity::sum_parts(self.high, other.high);
        Self::normalized(sum, error + (self.low + other.low))
    }

    fn subtract_scalar(self, other: f32) -> Self {
        self.add(Self::exact(-other))
    }

    fn multiply(self, factor: f32) -> Self {
        let high = self.high * factor;
        let error = self.high.mul_add(factor, -high);
        Self::normalized(high, self.low.mul_add(factor, error))
    }

    fn rounded(self) -> f32 {
        self.high + self.low
    }

    fn finite(self) -> bool {
        self.high.is_finite() && self.low.is_finite()
    }
}

type CoordinateParts = [CoordinatePart; 2];

fn exact_parts(p: [f32; 2]) -> CoordinateParts {
    p.map(CoordinatePart::exact)
}

fn rounded_parts(p: CoordinateParts) -> [f32; 2] {
    p.map(CoordinatePart::rounded)
}

fn finite_parts(p: CoordinateParts) -> bool {
    p.into_iter().all(CoordinatePart::finite)
}

impl RadialCurve {
    fn rate(&self) -> f32 {
        15.0 * self.input_scale / self.reference_radius
    }

    fn constants_valid(&self) -> bool {
        finite(self.center)
            && [
                self.reference_radius,
                self.input_scale,
                self.output_scale,
                self.max_input_radius,
            ]
            .into_iter()
            .all(|x| x.is_finite() && x > 0.0)
            && self.rate().is_finite()
            && self.rate() > 0.0
            && (self.rate() * self.max_input_radius).is_finite()
    }

    fn identity(&self) -> bool {
        self.input_scale == 1.0 && self.output_scale == 1.0 && self.knots == [0; 16]
    }

    // g(r) = r * (a + b*r) on this segment. The final segment extends.
    fn coefficients(&self, i: usize) -> (f32, f32) {
        let delta = f32::from(self.knots[i + 1]) - f32::from(self.knots[i]);
        let a = self.output_scale * (1.0 + (f32::from(self.knots[i]) - i as f32 * delta) * UNIT);
        let b = self.output_scale * (delta * UNIT) * self.rate();
        (a, b)
    }

    fn segment(&self, r: f32) -> usize {
        ((r * self.rate()).floor() as usize).min(14)
    }

    fn epsilon(&self, r: f32) -> f32 {
        let t = r * self.rate();
        let i = (t.floor() as usize).min(14);
        let k = f32::from(self.knots[i]);
        let delta = f32::from(self.knots[i + 1]) - k;
        (t - i as f32).mul_add(delta, k) * UNIT
    }

    fn gain(&self, r: f32) -> f32 {
        // Keep a positive gain representation for validation and contraction.
        // A delta near -1 alone cannot retain a very small positive gain.
        self.output_scale * (1.0 + self.epsilon(r))
    }

    fn delta_gain(&self, r: f32) -> f32 {
        // s*(1+epsilon)-1, without rounding the near-unit gain first.
        self.output_scale
            .mul_add(self.epsilon(r), self.output_scale - 1.0)
    }

    fn radius_out(&self, r: f32) -> f32 {
        let delta = self.delta_gain(r);
        if delta.abs() <= 0.5 {
            r.mul_add(delta, r)
        } else {
            r * self.gain(r)
        }
    }

    fn radius_residual(&self, r: f32, target: f32) -> f32 {
        let delta = self.delta_gain(r);
        if delta.abs() <= 0.5 {
            r.mul_add(delta, r - target)
        } else {
            self.radius_out(r) - target
        }
    }

    fn segment_range(&self, i: usize, limit: f32) -> Option<(f32, f32)> {
        let lo = i as f32 / self.rate();
        let hi = if i == 14 {
            limit
        } else {
            ((i + 1) as f32 / self.rate()).min(limit)
        };
        (lo <= hi && lo <= limit).then_some((lo, hi))
    }

    // Lower derivative bound, with a rounding guard. Positivity at both ends
    // proves positivity throughout each linear derivative segment, including
    // both one-sided derivatives at knots and the explicitly extended tail.
    fn minimum_derivative(&self) -> Option<f32> {
        let mut minimum = f32::INFINITY;
        for i in 0..15 {
            let Some((lo, hi)) = self.segment_range(i, self.max_input_radius) else {
                continue;
            };
            let (a, b) = self.coefficients(i);
            for r in [lo, hi] {
                let derivative = a + 2.0 * b * r;
                let guard = 64.0 * EPS * (1.0 + a.abs() + (2.0 * b * r).abs());
                let lower = down(derivative - guard);
                if !lower.is_finite()
                    || lower <= 0.0
                    || !self.gain(r).is_finite()
                    || self.gain(r) <= 0.0
                {
                    return None;
                }
                minimum = minimum.min(lower);
            }
        }
        minimum.is_finite().then_some(minimum)
    }

    pub fn validate(&self) -> Result<(), String> {
        if !self.constants_valid() {
            return Err("radial constants must be finite with positive scales/radii".into());
        }
        self.minimum_derivative()
            .ok_or("radial derivative is nonpositive or cannot be certified above roundoff")?;
        let end = self.radius_out(self.max_input_radius);
        if !end.is_finite() || end <= 0.0 || !self.roundoff(self.max_input_radius).is_finite() {
            return Err("radial output domain or error allowance overflows".into());
        }
        let coordinate_bound = abs_max(self.center) + self.max_input_radius.max(end);
        if !coordinate_bound.is_finite() || up(coordinate_bound) - coordinate_bound > 0.001 {
            return Err(
                "native coordinate spacing exceeds the 0.001-pixel accuracy contract".into(),
            );
        }
        Ok(())
    }

    /// Requires successful validation before using this immutable curve.
    pub fn forward(&self, p: [f32; 2]) -> Option<[f32; 2]> {
        if !finite(p) || !self.constants_valid() {
            return None;
        }
        let d = [p[0] - self.center[0], p[1] - self.center[1]];
        let r = norm(d);
        if !r.is_finite() || r > self.max_input_radius {
            return None;
        }
        if self.identity() || r == 0.0 {
            return Some(p);
        }
        let gain = self.gain(r);
        let delta = self.delta_gain(r);
        // The cutoff is a numerical representation choice, not a new curve.
        // Near identity, retain the small displacement instead of subtracting
        // and re-adding the large center. Otherwise retain the gain itself.
        let out = if delta.abs() <= 0.5 {
            [d[0].mul_add(delta, p[0]), d[1].mul_add(delta, p[1])]
        } else {
            [
                d[0].mul_add(gain, self.center[0]),
                d[1].mul_add(gain, self.center[1]),
            ]
        };
        (gain > 0.0 && finite(out)).then_some(out)
    }

    // Locate the monotone segment, solve its quadratic with the stable root,
    // then correct f32 coefficient/evaluation rounding with bounded Newton steps.
    fn inverse_radius(&self, target: f32) -> Option<(f32, f32, f32)> {
        let end = self.radius_out(self.max_input_radius);
        if !target.is_finite() || target < 0.0 || target > end || !end.is_finite() {
            return None;
        }
        if target == 0.0 {
            return Some((0.0, 0.0, 0.0));
        }
        let mut lo_i = 0usize;
        let mut hi_i = 15usize;
        while hi_i - lo_i > 1 {
            let mid = (lo_i + hi_i) / 2;
            let r = (mid as f32 / self.rate()).min(self.max_input_radius);
            if self.radius_out(r) < target {
                lo_i = mid;
            } else {
                hi_i = mid;
            }
        }
        let i = lo_i.min(14);
        let (lo, hi) = self.segment_range(i, self.max_input_radius)?;
        let (a, b) = self.coefficients(i);
        let discriminant = a * a + 4.0 * b * target;
        if !discriminant.is_finite() || discriminant < 0.0 {
            return None;
        }
        let mut r = if b == 0.0 {
            target / a
        } else if a >= 0.0 {
            2.0 * target / (a + discriminant.sqrt())
        } else {
            (-a + discriminant.sqrt()) / (2.0 * b)
        };
        if !r.is_finite() {
            return None;
        }
        r = r.clamp(lo, hi);
        for _ in 0..3 {
            let j = self.segment(r);
            let (aa, bb) = self.coefficients(j);
            let derivative = aa + 2.0 * bb * r;
            if !derivative.is_finite() || derivative <= 0.0 {
                return None;
            }
            let next = (r - self.radius_residual(r, target) / derivative).clamp(lo, hi);
            if !next.is_finite() {
                return None;
            }
            r = next;
        }
        let mut error = self.radius_residual(r, target).abs();
        for candidate in [down(r), up(r)] {
            if candidate >= lo && candidate <= hi {
                let candidate_error = self.radius_residual(candidate, target).abs();
                if candidate_error < error {
                    r = candidate;
                    error = candidate_error;
                }
            }
        }
        (r.is_finite() && r <= self.max_input_radius).then_some((r, lo, hi))
    }

    // Refine the small inverse displacement as its own f32 value. Subtracting
    // two image-scale radii after solving loses the fractional displacement.
    // The same monotone segment bracket and derivative checks still apply.
    fn inverse_offset(&self, target: f32, radius: f32, lo: f32, hi: f32) -> Option<f32> {
        let (lower, upper) = (lo - target, hi - target);
        let residual = |offset: f32| {
            let r = (target + offset).clamp(lo, hi);
            r.mul_add(self.delta_gain(r), offset)
        };
        let mut offset = (radius - target).clamp(lower, upper);
        for _ in 0..3 {
            let r = (target + offset).clamp(lo, hi);
            let (a, b) = self.coefficients(self.segment(r));
            let derivative = a + 2.0 * b * r;
            if !derivative.is_finite() || derivative <= 0.0 {
                return None;
            }
            offset = (offset - residual(offset) / derivative).clamp(lower, upper);
            if !offset.is_finite() {
                return None;
            }
        }
        let mut error = residual(offset).abs();
        for candidate in [down(offset), up(offset)] {
            if candidate >= lower && candidate <= upper {
                let candidate_error = residual(candidate).abs();
                if candidate_error < error {
                    offset = candidate;
                    error = candidate_error;
                }
            }
        }
        (offset.is_finite() && error.is_finite()).then_some(offset)
    }

    /// Inverse of this same forward model, including both declared scales.
    pub fn inverse(&self, p: [f32; 2]) -> Option<[f32; 2]> {
        if !finite(p) || !self.constants_valid() {
            return None;
        }
        let d = [p[0] - self.center[0], p[1] - self.center[1]];
        let target = norm(d);
        if self.identity() {
            return (target <= self.max_input_radius).then_some(p);
        }
        let (radius, lo, hi) = self.inverse_radius(target)?;
        if target == 0.0 {
            return Some(p);
        }
        let out = if ((radius - target) / target).abs() <= 0.5 {
            let delta = self.inverse_offset(target, radius, lo, hi)? / target;
            [d[0].mul_add(delta, p[0]), d[1].mul_add(delta, p[1])]
        } else {
            let scale = radius / target;
            [
                d[0].mul_add(scale, self.center[0]),
                d[1].mul_add(scale, self.center[1]),
            ]
        };
        finite(out).then_some(out)
    }

    // Preserve the final coordinate residual from this inverse. The radius
    // solver, monotone bracket, conditioning branches and domain are unchanged.
    fn inverse_parts(&self, p: [f32; 2]) -> Option<CoordinateParts> {
        if !finite(p) || !self.constants_valid() {
            return None;
        }
        let point = exact_parts(p);
        let d = [
            point[0].subtract_scalar(self.center[0]),
            point[1].subtract_scalar(self.center[1]),
        ];
        let target = norm(rounded_parts(d));
        if self.identity() {
            return (target <= self.max_input_radius).then_some(point);
        }
        let (radius, lo, hi) = self.inverse_radius(target)?;
        if target == 0.0 {
            return Some(point);
        }
        let out = if ((radius - target) / target).abs() <= 0.5 {
            let delta = self.inverse_offset(target, radius, lo, hi)? / target;
            [
                point[0].add(d[0].multiply(delta)),
                point[1].add(d[1].multiply(delta)),
            ]
        } else {
            let scale = radius / target;
            [
                CoordinatePart::exact(self.center[0]).add(d[0].multiply(scale)),
                CoordinatePart::exact(self.center[1]).add(d[1].multiply(scale)),
            ]
        };
        finite_parts(out).then_some(out)
    }

    // Radius/knots/gain remain f32 evaluations of the same declared curve.
    // Round the center-relative vector for hypot, not the absolute point before
    // subtracting its center; retain both coordinate parts in the radial map.
    fn forward_parts(&self, p: CoordinateParts) -> Option<CoordinateParts> {
        if !finite_parts(p) || !self.constants_valid() {
            return None;
        }
        let d = [
            p[0].subtract_scalar(self.center[0]),
            p[1].subtract_scalar(self.center[1]),
        ];
        let r = norm(rounded_parts(d));
        if !r.is_finite() || r > self.max_input_radius {
            return None;
        }
        if self.identity() || r == 0.0 {
            return Some(p);
        }
        let gain = self.gain(r);
        let delta = self.delta_gain(r);
        let out = if delta.abs() <= 0.5 {
            [
                p[0].add(d[0].multiply(delta)),
                p[1].add(d[1].multiply(delta)),
            ]
        } else {
            [
                CoordinatePart::exact(self.center[0]).add(d[0].multiply(gain)),
                CoordinatePart::exact(self.center[1]).add(d[1].multiply(gain)),
            ]
        };
        (gain > 0.0 && finite_parts(out)).then_some(out)
    }

    // Absolute-operation budget, not a cancellation-sensitive relative error:
    // covers subtraction, norm, knot-coordinate/lerp, scale and final addition.
    // 256 eps is deliberately above the <64-operation gamma bound, including
    // one-sided knot selection. Conditioning of the inverse is priced separately.
    fn roundoff(&self, radius: f32) -> f32 {
        let mut largest_k = 0.0f32;
        let mut largest_slope = 0.0f32;
        for i in 0..15 {
            largest_k = largest_k
                .max(f32::from(self.knots[i]).abs())
                .max(f32::from(self.knots[i + 1]).abs());
            largest_slope = largest_slope.max(
                (f32::from(self.knots[i + 1]) - f32::from(self.knots[i])).abs()
                    * self.rate()
                    * UNIT,
            );
        }
        up(256.0
            * EPS
            * (1.0 + abs_max(self.center) + radius)
            * (1.0 + self.output_scale * (1.0 + largest_k * UNIT + 2.0 * largest_slope * radius)))
    }

    // |g(r)-r| is absolute quadratic on each segment. Its extrema occur at
    // segment ends or alpha+2*beta*r=0. Include the stationary point even when
    // outward-rounded segment limits touch it, then inflate for f32 operations.
    fn displacement_bound(&self, limit: f32) -> Option<f32> {
        if !limit.is_finite() || limit < 0.0 || limit > self.max_input_radius {
            return None;
        }
        let mut bound = 0.0f32;
        for i in 0..15 {
            let Some((lo, hi)) = self.segment_range(i, limit) else {
                continue;
            };
            let (a, b) = self.coefficients(i);
            let alpha = a - 1.0;
            for r in [lo, hi] {
                bound = bound.max((r * (alpha + b * r)).abs());
            }
            if b != 0.0 {
                let stationary = -alpha / (2.0 * b);
                if stationary >= down(lo) && stationary <= up(hi) {
                    bound = bound.max((stationary * (alpha + b * stationary)).abs());
                }
            }
        }
        padded(bound, self.roundoff(limit))
    }
}

impl NativeSimilarity {
    pub fn validate(&self) -> Result<(), String> {
        if !finite(self.a)
            || !finite(self.b)
            || !finite(self.center)
            || !norm(self.a).is_finite()
            || norm(self.a) <= 0.0
        {
            Err("native similarity must be finite and nonsingular".into())
        } else {
            Ok(())
        }
    }

    fn identity(&self) -> bool {
        self.a == [1.0, 0.0] && self.b == [0.0, 0.0]
    }

    // Error-free sum decomposition for finite, nonoverflowing intermediates.
    // The correction is arithmetic state only; all values remain f32.
    fn sum_parts(a: f32, b: f32) -> [f32; 2] {
        let sum = a + b;
        let b_virtual = sum - a;
        [sum, (a - (sum - b_virtual)) + (b - b_virtual)]
    }

    fn centered_component(
        center: f32,
        translation: f32,
        weights: [f32; 2],
        offsets: [[f32; 2]; 2],
    ) -> f32 {
        let px = weights[0] * offsets[0][0];
        let py = weights[1] * offsets[1][0];
        let product_error =
            weights[0].mul_add(offsets[0][0], -px) + weights[1].mul_add(offsets[1][0], -py);
        let offset_error = weights[0].mul_add(offsets[0][1], weights[1] * offsets[1][1]);
        let [s0, e0] = Self::sum_parts(px, py);
        let [s1, e1] = Self::sum_parts(s0, translation);
        let [s2, e2] = Self::sum_parts(s1, center);
        s2 + (((e0 + e1) + e2) + (product_error + offset_error))
    }

    pub fn apply(&self, p: [f32; 2]) -> [f32; 2] {
        if self.identity() {
            return p;
        }
        let x = p[0] - self.center[0];
        let y = p[1] - self.center[1];
        let delta_re = self.a[0] - 1.0;
        // Same affine map, with a representation selected for conditioning.
        // Near identity, retain the small displacement and add it to p once.
        // The explicit real-part guard ensures a.re >= 0.5; the centered form
        // retains tiny positive gains that delta_re alone could round away.
        if self.a[0] >= 0.5 && norm([delta_re, self.a[1]]) <= 0.5 {
            let dx = delta_re.mul_add(x, (-self.a[1]).mul_add(y, self.b[0]));
            let dy = delta_re.mul_add(y, self.a[1].mul_add(x, self.b[1]));
            [p[0] + dx, p[1] + dy]
        } else {
            // Keep subtraction/product/addition residuals until the final
            // coordinate rounding. Strong expansion magnifies an early lost
            // fraction even when each individual result is representable.
            let offsets = [
                Self::sum_parts(p[0], -self.center[0]),
                Self::sum_parts(p[1], -self.center[1]),
            ];
            [
                Self::centered_component(
                    self.center[0],
                    self.b[0],
                    [self.a[0], -self.a[1]],
                    offsets,
                ),
                Self::centered_component(
                    self.center[1],
                    self.b[1],
                    [self.a[1], self.a[0]],
                    offsets,
                ),
            ]
        }
    }

    fn apply_parts(&self, p: CoordinateParts) -> CoordinateParts {
        if self.identity() {
            return p;
        }
        let x = p[0].subtract_scalar(self.center[0]);
        let y = p[1].subtract_scalar(self.center[1]);
        [
            x.multiply(self.a[0])
                .add(y.multiply(-self.a[1]))
                .add(CoordinatePart::exact(self.b[0]))
                .add(CoordinatePart::exact(self.center[0])),
            x.multiply(self.a[1])
                .add(y.multiply(self.a[0]))
                .add(CoordinatePart::exact(self.b[1]))
                .add(CoordinatePart::exact(self.center[1])),
        ]
    }

    fn roundoff(&self, point_bound: f32) -> f32 {
        up(64.0
            * EPS
            * (1.0
                + abs_max(self.center)
                + abs_max(self.b)
                + norm(self.a) * (point_bound + abs_max(self.center))))
    }
}

impl ResearchPull {
    pub fn validate(&self) -> Result<(), String> {
        self.anchor.validate()?;
        self.source.validate()?;
        self.placement.validate()
    }

    pub fn map_native(&self, p: [f32; 2]) -> Option<[f32; 2]> {
        let undistorted = self.anchor.inverse(p)?;
        if self.anchor == self.source && self.placement.identity() {
            return Some(p);
        }
        self.source.forward(self.placement.apply(undistorted))
    }

    /// Same inverse-anchor -> placement -> source-forward -> channel-CA model,
    /// preserving local f32 coordinate residuals until the final returned point.
    /// Caller must validate the pull and CA, as for the separate scalar route.
    pub fn map_native_with_ca(&self, p: [f32; 2], ca: NativeSimilarity) -> Option<[f32; 2]> {
        let undistorted = self.anchor.inverse_parts(p)?;
        let source = if self.anchor == self.source && self.placement.identity() {
            exact_parts(p)
        } else {
            self.source
                .forward_parts(self.placement.apply_parts(undistorted))?
        };
        let result = ca.apply_parts(source);
        if !finite_parts(result) {
            return None;
        }
        let point = rounded_parts(result);
        finite(point).then_some(point)
    }

    /// Certify every point of an inclusive rectangle, including post-pull CA.
    /// A conservative false is intentional. Tap support belongs in `margin`.
    pub fn covers(
        &self,
        rect: [f32; 4],
        source_size: [usize; 2],
        margin: f32,
        ca: NativeSimilarity,
    ) -> bool {
        if self.validate().is_err() || ca.validate().is_err()
            || !rect.into_iter().all(f32::is_finite) || rect[0] > rect[2] || rect[1] > rect[3]
            || !margin.is_finite() || margin < 0.0 || source_size.contains(&0)
            // Ensure integer image limits are exactly representable in f32.
            || source_size.into_iter().any(|v| v > (1 << 24))
        {
            return false;
        }
        self.coverage_certificate(rect, source_size, margin, ca)
            .is_some()
    }

    fn coverage_certificate(
        &self,
        rect: [f32; 4],
        size: [usize; 2],
        margin: f32,
        ca: NativeSimilarity,
    ) -> Option<()> {
        let corners = [
            [rect[0], rect[1]],
            [rect[2], rect[1]],
            [rect[0], rect[3]],
            [rect[2], rect[3]],
        ];
        let coordinate_bound = rect.into_iter().map(f32::abs).fold(0.0f32, f32::max);
        let anchor_radius = corners
            .into_iter()
            .map(|p| distance(p, self.anchor.center))
            .fold(0.0f32, f32::max);
        let distance_error = 32.0 * EPS * (1.0 + coordinate_bound + abs_max(self.anchor.center));
        let anchor_out = self.anchor.radius_out(self.anchor.max_input_radius);
        let anchor_error = self.anchor.roundoff(self.anchor.max_input_radius);
        if padded(anchor_radius, distance_error)? > down(anchor_out - anchor_error) {
            return None;
        }
        let minimum_derivative = self.anchor.minimum_derivative()?;
        let inverse_error = anchor_error * (2.0 + 2.0 / minimum_derivative);
        let inverse_displacement = padded(
            self.anchor
                .displacement_bound(self.anchor.max_input_radius)?,
            inverse_error,
        )?;
        let placement_scale = up(norm(self.placement.a));
        let placement_error = 2.0
            * self
                .placement
                .roundoff(coordinate_bound + inverse_displacement);
        let source_base_radius = corners
            .into_iter()
            .map(|p| distance(self.placement.apply(p), self.source.center))
            .fold(0.0f32, f32::max);
        let source_radius = padded(
            source_base_radius,
            placement_scale * inverse_displacement
                + placement_error
                + 32.0 * EPS * (1.0 + source_base_radius + abs_max(self.source.center)),
        )?;
        if source_radius
            > down(
                self.source.max_input_radius - self.source.roundoff(self.source.max_input_radius),
            )
        {
            return None;
        }
        let source_displacement = self.source.displacement_bound(source_radius)?;
        let deviation = padded(
            source_displacement,
            placement_scale * inverse_displacement + placement_error,
        )?;
        let ca_scale = up(norm(ca.a));
        let base_bound = corners
            .into_iter()
            .map(|p| abs_max(self.placement.apply(p)))
            .fold(0.0f32, f32::max);
        let total = padded(
            ca_scale * deviation,
            2.0 * ca.roundoff(base_bound + deviation),
        )?;
        let lower = up(margin + total);
        let upper = [
            down((size[0] - 1) as f32 - margin - total),
            down((size[1] - 1) as f32 - margin - total),
        ];
        if !lower.is_finite() || !finite(upper) || upper[0] < lower || upper[1] < lower {
            return None;
        }
        for p in corners {
            let base = ca.apply(self.placement.apply(p));
            if !finite(base)
                || base[0] < lower
                || base[1] < lower
                || base[0] > upper[0]
                || base[1] > upper[1]
            {
                return None;
            }
        }
        Some(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const ACCURACY: f64 = 0.001; // native Euclidean pixels; never silently relaxed

    fn identity(center: [f32; 2], radius: f32) -> RadialCurve {
        RadialCurve {
            center,
            reference_radius: radius,
            input_scale: 1.0,
            output_scale: 1.0,
            max_input_radius: radius,
            knots: [0; 16],
        }
    }

    fn similarity(center: [f32; 2]) -> NativeSimilarity {
        NativeSimilarity {
            a: [1.0, 0.0],
            b: [0.0, 0.0],
            center,
        }
    }

    // Independent f64 reference: direct interpolation and a bracketed inverse.
    // It does not use candidate coefficients, segment selection or root solver.
    fn reference_forward(c: RadialCurve, p: [f64; 2]) -> [f64; 2] {
        let dx = p[0] - f64::from(c.center[0]);
        let dy = p[1] - f64::from(c.center[1]);
        let t = 15.0 * f64::from(c.input_scale) * dx.hypot(dy) / f64::from(c.reference_radius);
        let i = (t.floor() as usize).min(14);
        let k = f64::from(c.knots[i])
            + (t - i as f64) * f64::from(i32::from(c.knots[i + 1]) - i32::from(c.knots[i]));
        let scale = f64::from(c.output_scale) * (1.0 + k / 16384.0);
        [
            f64::from(c.center[0]) + dx * scale,
            f64::from(c.center[1]) + dy * scale,
        ]
    }

    fn reference_inverse(c: RadialCurve, p: [f64; 2]) -> [f64; 2] {
        let center = c.center.map(f64::from);
        let d = [p[0] - center[0], p[1] - center[1]];
        let target = d[0].hypot(d[1]);
        if target == 0.0 {
            return p;
        }
        let mut lo = 0.0;
        let mut hi = f64::from(c.max_input_radius);
        for _ in 0..100 {
            let mid = (lo + hi) / 2.0;
            let q = reference_forward(c, [center[0] + mid, center[1]]);
            if q[0] - center[0] < target {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        let scale = ((lo + hi) / 2.0) / target;
        [center[0] + d[0] * scale, center[1] + d[1] * scale]
    }

    fn reference_similarity(a: NativeSimilarity, p: [f64; 2]) -> [f64; 2] {
        let x = p[0] - f64::from(a.center[0]);
        let y = p[1] - f64::from(a.center[1]);
        [
            f64::from(a.center[0]) + f64::from(a.a[0]) * x - f64::from(a.a[1]) * y
                + f64::from(a.b[0]),
            f64::from(a.center[1])
                + f64::from(a.a[1]) * x
                + f64::from(a.a[0]) * y
                + f64::from(a.b[1]),
        ]
    }

    fn reference_pull(pull: ResearchPull, p: [f64; 2]) -> [f64; 2] {
        reference_forward(
            pull.source,
            reference_similarity(pull.placement, reference_inverse(pull.anchor, p)),
        )
    }

    fn error(a: [f32; 2], b: [f64; 2]) -> f64 {
        (f64::from(a[0]) - b[0]).hypot(f64::from(a[1]) - b[1])
    }

    #[test]
    fn zero_identity_and_equal_curve_anchor_preserve_coordinates() {
        let zero = identity([3515.5, 2343.5], 6000.0);
        zero.validate().unwrap();
        for p in [
            [0.0, 0.0],
            [3515.5, 2343.5],
            [7031.0, 4687.0],
            [217.5, 811.5],
        ] {
            assert_eq!(zero.forward(p), Some(p));
            assert_eq!(zero.inverse(p), Some(p));
        }
        let mut curve = zero;
        curve.knots = std::array::from_fn(|i| -(i as i16) * 12);
        let pull = ResearchPull {
            anchor: curve,
            source: curve,
            placement: similarity([3516.5, 2344.5]),
        };
        pull.validate().unwrap();
        for p in [[512.0, 480.0], [3515.5, 2343.5], [6400.5, 4000.5]] {
            assert_eq!(pull.map_native(p), Some(p));
        }
    }

    #[test]
    fn independent_reference_knots_tail_scales_and_round_trips() {
        let curve = RadialCurve {
            center: [3515.5, 2343.5],
            reference_radius: 4200.0,
            input_scale: 1.03,
            output_scale: 1.01,
            max_input_radius: 6000.0,
            knots: std::array::from_fn(|i| -2 * (i as i16) * (i as i16)),
        };
        curve.validate().unwrap();
        let mut points = vec![curve.center, [67.5, 120.25], [6900.0, 4600.0]];
        for i in 0..=15 {
            let radius = i as f32 * curve.reference_radius / (15.0 * curve.input_scale);
            for angle in [0.0f32, 0.73, 2.4] {
                points.push([
                    curve.center[0] + radius * angle.cos(),
                    curve.center[1] + radius * angle.sin(),
                ]);
            }
        }
        points.extend([[3515.5 + 5700.0, 2343.5], [3515.5, 2343.5 - 5500.0]]);
        for p in points {
            let mapped = curve.forward(p).unwrap();
            let forward_error = error(mapped, reference_forward(curve, p.map(f64::from)));
            assert!(
                forward_error <= ACCURACY,
                "f32 forward error {forward_error} at {p:?}"
            );
            let inverse = curve.inverse(mapped).unwrap();
            let inverse_error = error(inverse, reference_inverse(curve, mapped.map(f64::from)));
            assert!(
                inverse_error <= ACCURACY,
                "f32 inverse error {inverse_error} at {p:?}"
            );
            let round_trip = error(inverse, p.map(f64::from));
            assert!(
                round_trip <= ACCURACY,
                "round-trip error {round_trip} at {p:?}"
            );
        }
    }

    #[test]
    fn source_anchor_placement_order_is_noncommuting() {
        let mut anchor = identity([64.25, 48.5], 160.0);
        anchor.reference_radius = 80.0;
        anchor.knots = std::array::from_fn(|i| (i as i16) * 30);
        let mut source = anchor;
        source.center = [61.5, 50.25];
        source.knots = std::array::from_fn(|i| -(i as i16) * 20);
        let placement = NativeSimilarity {
            a: [0.996, 0.02],
            b: [2.0, -1.0],
            center: [64.5, 48.5],
        };
        let pull = ResearchPull {
            anchor,
            source,
            placement,
        };
        pull.validate().unwrap();
        let p = [110.5, 70.5];
        let expected = reference_pull(pull, p.map(f64::from));
        assert!(error(pull.map_native(p).unwrap(), expected) <= ACCURACY);
        let wrong = reference_forward(
            source,
            reference_inverse(anchor, reference_similarity(placement, p.map(f64::from))),
        );
        assert!((expected[0] - wrong[0]).hypot(expected[1] - wrong[1]) > 0.01);
    }

    #[test]
    fn refuses_invalid_constants_derivatives_and_domains() {
        let good = identity([0.0, 0.0], 15.0);
        for value in [f32::NAN, f32::INFINITY, 0.0, -1.0] {
            let mut bad = good;
            bad.reference_radius = value;
            assert!(bad.validate().is_err());
            let mut bad = good;
            bad.input_scale = value;
            assert!(bad.validate().is_err());
            let mut bad = good;
            bad.output_scale = value;
            assert!(bad.validate().is_err());
            let mut bad = good;
            bad.max_input_radius = value;
            assert!(bad.validate().is_err());
        }
        let mut bad = good;
        bad.center[0] = f32::NAN;
        assert!(bad.validate().is_err());
        // At this center, representable coordinates are two native pixels apart.
        let mut bad = good;
        bad.center[0] = 16_777_216.0;
        assert!(bad.validate().is_err());
        let mut bad = good;
        bad.knots[15] = -16000;
        assert!(bad.validate().is_err());
        let mut bad = good;
        bad.knots = [-32768; 16];
        assert!(bad.validate().is_err());
        // First 15 knots are valid, but extending the falling final segment folds.
        let mut bad = good;
        bad.knots[15] = -700;
        bad.max_input_radius = 30.0;
        assert!(bad.validate().is_err());
        for p in [[up(15.0), 0.0], [f32::NAN, 0.0], [0.0, f32::INFINITY]] {
            assert!(good.forward(p).is_none());
            assert!(good.inverse(p).is_none());
        }
        assert_eq!(good.forward([15.0, 0.0]), Some([15.0, 0.0]));
        let mut invalid = similarity([0.0, 0.0]);
        invalid.a = [0.0, 0.0];
        assert!(invalid.validate().is_err());
    }

    #[test]
    fn analytic_bound_includes_interior_stationary_point() {
        let mut curve = identity([0.0, 0.0], 1.0);
        curve.reference_radius = 15.0;
        curve.knots[0] = 4096;
        curve.validate().unwrap();
        // g(r)-r = .25*r-.25*r^2 on [0,1]: endpoint-only bound is zero.
        assert_eq!(curve.radius_out(0.0), 0.0);
        assert_eq!(curve.radius_out(1.0) - 1.0, 0.0);
        let interior = curve.forward([0.5, 0.0]).unwrap()[0] - 0.5;
        assert!(interior > 0.06); // explicitly falsifies the endpoint-only bound
        assert!(curve.displacement_bound(1.0).unwrap() >= interior);
    }

    #[test]
    fn coverage_fails_first_then_enumerates_all_sites_phases_and_ca() {
        let mut anchor = identity([64.25, 48.5], 160.0);
        anchor.reference_radius = 80.0;
        anchor.knots = std::array::from_fn(|i| (i as i16) * 4);
        let mut source = anchor;
        source.center = [62.5, 49.25];
        source.knots = std::array::from_fn(|i| -(i as i16) * 3);
        let placement = NativeSimilarity {
            a: [0.999, 0.006],
            b: [0.2, -0.3],
            center: [64.5, 48.5],
        };
        let pull = ResearchPull {
            anchor,
            source,
            placement,
        };
        let ca = NativeSimilarity {
            a: [1.002, 0.001],
            b: [0.05, -0.07],
            center: [64.0, 48.0],
        };
        assert!(!pull.covers([0.0, 0.0, 127.0, 95.0], [128, 96], 2.0, ca));
        let mut admitted = 0;
        for origin_x in 0..2 {
            for origin_y in 0..2 {
                let rect = [
                    24.0 + origin_x as f32,
                    20.0 + origin_y as f32,
                    102.0 + origin_x as f32,
                    74.0 + origin_y as f32,
                ];
                assert!(pull.covers(rect, [128, 96], 2.0, ca));
                admitted += 1;
                let mut phases = [false; 4];
                for y in rect[1] as usize..=rect[3] as usize {
                    for x in rect[0] as usize..=rect[2] as usize {
                        phases[(y % 2) * 2 + x % 2] = true;
                        let p = [x as f32, y as f32];
                        let q = ca.apply(pull.map_native(p).unwrap());
                        assert!((2.0..=125.0).contains(&q[0]) && (2.0..=93.0).contains(&q[1]));
                        let reference =
                            reference_similarity(ca, reference_pull(pull, p.map(f64::from)));
                        assert!(error(q, reference) <= ACCURACY);
                        // Sub-photosite/guide sample phases share this certificate.
                        if x < rect[2] as usize && y < rect[3] as usize {
                            for phase in [[0.5, 0.5], [0.25, 0.75]] {
                                let q = ca.apply(
                                    pull.map_native([p[0] + phase[0], p[1] + phase[1]]).unwrap(),
                                );
                                assert!(
                                    (2.0..=125.0).contains(&q[0]) && (2.0..=93.0).contains(&q[1])
                                );
                            }
                        }
                    }
                }
                assert!(phases.into_iter().all(|v| v));
            }
        }
        assert_eq!(admitted, 4);
        let mut domain_limited = pull;
        domain_limited.source.max_input_radius = 20.0;
        assert!(!domain_limited.covers([24.0, 20.0, 103.0, 75.0], [128, 96], 2.0, ca));
        domain_limited = pull;
        domain_limited.anchor.max_input_radius = 20.0;
        assert!(!domain_limited.covers([24.0, 20.0, 103.0, 75.0], [128, 96], 2.0, ca));
        for rect in [[5.0, 5.0, 4.0, 6.0], [f32::NAN, 5.0, 20.0, 20.0]] {
            assert!(!pull.covers(rect, [128, 96], 2.0, ca));
        }
        assert!(!pull.covers([24.0, 20.0, 103.0, 75.0], [0, 96], 2.0, ca));
        assert!(!pull.covers([24.0, 20.0, 103.0, 75.0], [128, 96], -1.0, ca));
    }

    #[test]
    fn f32_similarity_precision_is_separate_from_legacy_f64() {
        let center = [3516.5, 2344.5];
        let legacy_a = [1.000123456789f64, 0.0007654321];
        let legacy_b = [0.123456789f64, -0.234567891];
        let a = NativeSimilarity {
            a: legacy_a.map(|v| v as f32),
            b: legacy_b.map(|v| v as f32),
            center,
        };
        let zero = identity([3515.5, 2343.5], 6000.0);
        let pull = ResearchPull {
            anchor: zero,
            source: zero,
            placement: a,
        };
        pull.validate().unwrap();
        let p = [6789.5, 4321.5];
        let dx = f64::from(p[0] - center[0]);
        let dy = f64::from(p[1] - center[1]);
        let legacy = [
            f64::from(center[0]) + legacy_a[0] * dx - legacy_a[1] * dy + legacy_b[0],
            f64::from(center[1]) + legacy_a[1] * dx + legacy_a[0] * dy + legacy_b[1],
        ];
        let measured = error(pull.map_native(p).unwrap(), legacy);
        assert!(
            measured > 0.0 && measured <= ACCURACY,
            "precision-only displacement {measured}"
        );
        // An explicit half-pixel center change has a nonzero effect for rotation.
        let shifted = NativeSimilarity {
            center: [3516.0, 2344.0],
            ..a
        };
        assert_ne!(a.apply(p), shifted.apply(p));
    }

    #[test]
    fn displacement_representation_boundaries_keep_nonunit_and_contracted_models() {
        // Both sides of the forward representation cutoff, plus inverse
        // cutoff cases and nonunit input/output scales. No optical calibration.
        for output_scale in [
            down(0.5),
            0.5,
            up(0.5),
            down(1.5),
            1.5,
            up(1.5),
            down(2.0 / 3.0),
            2.0 / 3.0,
            up(2.0 / 3.0),
            down(2.0),
            2.0,
            up(2.0),
            0.25,
            1.03,
        ] {
            for knots in [[0; 16], std::array::from_fn(|i| 2 * i as i16)] {
                let curve = RadialCurve {
                    center: [512.5, 384.5],
                    reference_radius: 600.0,
                    input_scale: 1.07,
                    output_scale,
                    max_input_radius: 900.0,
                    knots,
                };
                curve.validate().unwrap();
                for p in [
                    curve.center,
                    [40.25, 56.75],
                    [1100.0, 700.0],
                    [1312.5, 264.5],
                ] {
                    let q = curve.forward(p).unwrap();
                    assert!(error(q, reference_forward(curve, p.map(f64::from))) <= ACCURACY);
                    let back = curve.inverse(q).unwrap();
                    assert!(error(back, reference_inverse(curve, q.map(f64::from))) <= ACCURACY);
                    assert!(error(back, p.map(f64::from)) <= ACCURACY);
                }
            }
        }
        let mut weak = identity([3515.5, 2343.5], 6000.0);
        weak.knots = [-16383; 16];
        weak.validate().unwrap();
        let p = [3515.75, 2343.5];
        let q = weak.forward(p).unwrap();
        assert_eq!(q, weak.center);
        assert!(error(weak.inverse(q).unwrap(), p.map(f64::from)) > ACCURACY);
    }

    #[test]
    fn retained_tail_failure_uses_the_same_bits_and_extended_domain() {
        // Retained36 plan case6, failed requests13667/13668/13763.
        // These are additional regression witnesses, not a replacement for the
        // unchanged complete generated and retained numeric populations.
        let curve = RadialCurve {
            center: [f32::from_bits(1163638784), f32::from_bits(1158838272)],
            reference_radius: f32::from_bits(1166251193),
            input_scale: 1.0,
            output_scale: 1.0,
            max_input_radius: f32::from_bits(1170562838),
            knots: [
                0, -1, -2, -3, -4, -5, -7, -8, -11, -12, -13, -13, -13, -12, -9, -6,
            ],
        };
        curve.validate().unwrap();
        for bits in [[1175591453, 1167377301], [1175591543, 1167377375]] {
            let p = bits.map(f32::from_bits);
            let q = curve.forward(p).unwrap();
            assert!(error(q, reference_forward(curve, p.map(f64::from))) <= ACCURACY);
            assert!(error(curve.inverse(q).unwrap(), p.map(f64::from)) <= ACCURACY);
        }
        let p = [f32::from_bits(1175597470), f32::from_bits(1167382286)];
        assert!(
            error(
                curve.inverse(p).unwrap(),
                reference_inverse(curve, p.map(f64::from))
            ) <= ACCURACY
        );
    }
}
