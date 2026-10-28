//! Direct interpolation of measured RGGB sensels, without a source demosaic.
//! Both measured green phases share a rotated quincunx lattice. This changes
//! sampling and noise transport; it is not a claim of photographic improvement.

/// Immutable active-area view. Coordinates use the active area's RGGB origin,
/// independently of its offset in the decoded buffer.
#[derive(Clone, Copy, Debug)]
pub struct ActiveCfa<'a> {
    data: &'a [u16],
    stride: usize,
    start: usize,
    width: i64,
    height: i64,
}

impl<'a> ActiveCfa<'a> {
    /// Validate storage once. Padding is never sampled. Empty or overflowing
    /// extents are refused; odd dimensions are allowed.
    pub fn new(
        data: &'a [u16],
        stride: usize,
        active_x: usize,
        active_y: usize,
        width: usize,
        height: usize,
    ) -> Option<Self> {
        let max_axis = usize::try_from(i64::MAX / 8).unwrap_or(usize::MAX);
        if width == 0 || height == 0 || width > max_axis || height > max_axis {
            return None;
        }
        if active_x.checked_add(width)? > stride {
            return None;
        }
        let start = active_y.checked_mul(stride)?.checked_add(active_x)?;
        let end = start
            .checked_add((height - 1).checked_mul(stride)?)?
            .checked_add(width)?;
        if end > data.len() {
            return None;
        }
        Some(Self {
            data,
            stride,
            start,
            width: width as i64,
            height: height as i64,
        })
    }

    /// Catmull-Rom interpolation of channel 0/1/2 (R/G/B), in raw DN.
    ///
    /// x,y are native-pixel coordinates relative to the active origin. No
    /// black subtraction, white balance, clamp, or private noise estimate is
    /// applied. Cubic interpolation can overshoot. Every nonzero tap must lie
    /// in the actual active area. Exact zero taps do not invalidate measured
    /// boundary samples under an identity pull.
    #[inline]
    pub fn sample_checked(&self, channel: usize, x: f64, y: f64) -> Option<f32> {
        if !x.is_finite()
            || !y.is_finite()
            || x < 0.0
            || y < 0.0
            || x > (self.width - 1) as f64
            || y > (self.height - 1) as f64
        {
            return None;
        }
        let (u, v) = match channel {
            0 => (0.5 * x, 0.5 * y),
            1 => (0.5 * (x + y - 1.0), 0.5 * (x - y - 1.0)),
            2 => (0.5 * (x - 1.0), 0.5 * (y - 1.0)),
            _ => return None,
        };
        let u0 = u.floor() as i64;
        let v0 = v.floor() as i64;
        let wu = catmull_rom_weights((u - u0 as f64) as f32);
        let wv = catmull_rom_weights((v - v0 as f64) as f32);
        let mut sum = 0.0f32;
        for (j, &weight_v) in wv.iter().enumerate() {
            if weight_v == 0.0 {
                continue;
            }
            let tv = v0 + j as i64 - 1;
            let mut row = 0.0f32;
            for (i, &weight_u) in wu.iter().enumerate() {
                if weight_u == 0.0 {
                    continue;
                }
                let tu = u0 + i as i64 - 1;
                let (sx, sy) = match channel {
                    0 => (2 * tu, 2 * tv),
                    1 => (tu + tv + 1, tu - tv),
                    2 => (2 * tu + 1, 2 * tv + 1),
                    _ => unreachable!(),
                };
                if sx < 0 || sy < 0 || sx >= self.width || sy >= self.height {
                    return None;
                }
                let value = self.data[self.start + sy as usize * self.stride + sx as usize];
                row += f32::from(value) * weight_u;
            }
            sum += row * weight_v;
        }
        Some(sum)
    }
}

// Same cubic family and f32 polynomial as align::sample_catmull_rom.
#[inline]
fn catmull_rom_weights(f: f32) -> [f32; 4] {
    let f2 = f * f;
    let f3 = f2 * f;
    [
        -0.5 * f3 + f2 - 0.5 * f,
        1.5 * f3 - 2.5 * f2 + 1.0,
        -1.5 * f3 + 2.0 * f2 + 0.5 * f,
        0.5 * f3 - 0.5 * f2,
    ]
}

#[cfg(test)]
mod tests {
    use super::ActiveCfa;

    fn channel(x: usize, y: usize) -> usize {
        match (x % 2, y % 2) {
            (0, 0) => 0,
            (1, 1) => 2,
            _ => 1,
        }
    }

    #[test]
    fn identity_preserves_every_measured_site_including_active_edges() {
        let (stride, ax, ay, width, height) = (19, 3, 2, 13, 11);
        let mut data = vec![u16::MAX; stride * (ay + height + 2)];
        for y in 0..height {
            for x in 0..width {
                data[(ay + y) * stride + ax + x] = (17 + 89 * y + 53 * x) as u16;
            }
        }
        let source = ActiveCfa::new(&data, stride, ax, ay, width, height).unwrap();
        for y in 0..height {
            for x in 0..width {
                assert_eq!(
                    source.sample_checked(channel(x, y), x as f64, y as f64),
                    Some(f32::from(data[(ay + y) * stride + ax + x])),
                    "measured site ({x},{y})"
                );
            }
        }
    }

    #[test]
    fn independent_channel_affine_fields_survive_fractional_queries() {
        let (width, height) = (31, 27);
        let mut data = vec![0; width * height];
        for y in 0..height {
            for x in 0..width {
                data[y * width + x] = (1000 * (channel(x, y) + 1) + 7 * x + 11 * y) as u16;
            }
        }
        let source = ActiveCfa::new(&data, width, 0, 0, width, height).unwrap();
        for ch in 0..3 {
            for (x, y) in [(8.125, 9.75), (14.5, 17.25), (21.875, 6.375)] {
                let expected = (1000 * (ch + 1)) as f32 + 7.0 * x as f32 + 11.0 * y as f32;
                let value = source.sample_checked(ch, x, y).unwrap();
                assert!(
                    (value - expected).abs() < 0.002,
                    "{ch}: {value} vs {expected}"
                );
            }
        }
    }

    #[test]
    fn missing_support_and_invalid_requests_are_refused() {
        let data = vec![512; 16 * 16];
        let source = ActiveCfa::new(&data, 16, 0, 0, 16, 16).unwrap();
        for ch in 0..3 {
            for (x, y) in [
                (f64::NAN, 8.0),
                (8.0, f64::INFINITY),
                (-0.01, 8.0),
                (16.0, 8.0),
            ] {
                assert!(source.sample_checked(ch, x, y).is_none());
            }
            assert!(source.sample_checked(ch, 0.25, 0.25).is_none());
        }
        assert!(source.sample_checked(3, 8.0, 8.0).is_none());
        assert_eq!(source.sample_checked(0, 0.0, 0.0), Some(512.0));
        assert_eq!(source.sample_checked(1, 1.0, 0.0), Some(512.0));
        assert_eq!(source.sample_checked(2, 15.0, 15.0), Some(512.0));
    }

    #[test]
    fn constructor_rejects_invalid_or_overflowing_extents() {
        let data = [0; 64];
        assert!(ActiveCfa::new(&data, 8, 0, 0, 0, 8).is_none());
        assert!(ActiveCfa::new(&data, 8, 4, 0, 5, 8).is_none());
        assert!(ActiveCfa::new(&data, 8, 0, 1, 8, 8).is_none());
        assert!(ActiveCfa::new(&data, 8, usize::MAX, 0, 2, 2).is_none());
        assert!(ActiveCfa::new(&data, 8, 0, usize::MAX, 2, 2).is_none());
        assert!(ActiveCfa::new(&data, usize::MAX, 0, 0, 2, 3).is_none());
        assert!(ActiveCfa::new(&data, 8, 0, 0, usize::MAX, 1).is_none());
        assert!(ActiveCfa::new(&data, 1, 0, 0, 1, 1).is_some());
    }
}
