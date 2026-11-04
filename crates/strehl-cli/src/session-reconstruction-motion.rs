//! Coherent RGB appearance admission against independent, frozen guides.
//! This is adaptive support, not an unconditional output-variance estimate.
use super::{green, interp};
use strehl_core::{
    boxfilter::box_mean, noise::PlaneNoise, plane::PlaneGeometry,
    reconstruction::guide_motion_confidence,
};

#[derive(Clone, Copy)]
pub(super) struct Calibration {
    pub noise: [PlaneNoise; 4],
    pub gain: f32,
}
impl Calibration {
    fn variance(self, expected: f32, channel: usize) -> f32 {
        let raw = expected / self.gain;
        // Even with covariance between the greens, Var((G1+G2)/2) is at most
        // max(Var(G1),Var(G2)). Never silently substitute G1 for a noisier G2.
        let variance = if channel == 1 {
            self.noise[1].variance(raw).max(self.noise[3].variance(raw))
        } else {
            self.noise[channel].variance(raw)
        };
        variance * self.gain * self.gain
    }
}
pub(super) struct Guide<'a> {
    pub geometry: PlaneGeometry,
    pub planes: &'a [Vec<f32>; 3],
    pub coords: &'a [[f64; 2]],
    pub expected: &'a [[f32; 3]],
    pub calibrations: &'a [Calibration],
}

pub(super) fn confidences(
    planes: &[Vec<f32>; 4],
    target: Calibration,
    guide: Guide<'_>,
) -> Vec<f32> {
    let g = guide.geometry;
    let mut output = vec![1f32; guide.coords.len()];
    let mut green_plane = vec![0.; g.pixels()];
    let mut scratch = vec![0.; g.pixels()];
    let mut filtered = vec![0.; g.pixels()];
    green(planes, &mut green_plane);
    for (channel, plane) in planes.iter().take(3).enumerate() {
        let values = if channel == 1 { &green_plane } else { plane };
        box_mean(values, g, 3, &mut scratch, &mut filtered);
        for (p, (&[x, y], confidence)) in guide.coords.iter().zip(&mut output).enumerate() {
            let expected = guide.expected[p][channel];
            let measured = interp(&filtered, g, x, y) * target.gain;
            // Retain the conservative unfiltered independent-source bound;
            // filtering must not be represented as extra independent photons.
            let variance = target.variance(expected, channel)
                + guide
                    .calibrations
                    .iter()
                    .map(|c| c.variance(expected, channel))
                    .sum::<f32>()
                    / (guide.calibrations.len() * guide.calibrations.len()) as f32;
            let dx = (interp(&guide.planes[channel], g, x + 1., y)
                - interp(&guide.planes[channel], g, x - 1., y))
                * 0.25;
            let dy = (interp(&guide.planes[channel], g, x, y + 1.)
                - interp(&guide.planes[channel], g, x, y - 1.))
                * 0.25;
            *confidence = confidence.min(guide_motion_confidence(
                measured - expected,
                variance,
                4. * (dx * dx + dy * dy),
                4.,
            ));
        }
    }
    output
}

#[cfg(test)]
#[path = "session-reconstruction-motion-tests.rs"]
mod tests;
