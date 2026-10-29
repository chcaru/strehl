use super::*;
use crate::{session_reconstruction_sampling::RegionSampler, session_sampling::SamplingDomain};
use strehl_core::{
    align::{Cx, Resampler, Similarity},
    noise::Levels,
    plane::QuadSource,
};

const LEVELS: Levels = Levels {
    black: 512.,
    white: 16000.,
};
fn calibration() -> Calibration {
    Calibration {
        noise: [PlaneNoise {
            gain_dn_per_e: 1.,
            read_noise_e: 8.,
            levels: LEVELS,
        }; 4],
        gain: 1.,
    }
}
fn noise(seed: &mut u64) -> f32 {
    let mut sum = -6.;
    for _ in 0..12 {
        *seed = seed
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        sum += (*seed >> 40) as f32 / (1u32 << 24) as f32;
    }
    sum
}
fn field(
    planes: &[Vec<f32>; 4],
    guide_planes: &[Vec<f32>; 3],
    g: PlaneGeometry,
    c: Calibration,
) -> Vec<f32> {
    let coords: Vec<_> = (3..g.height - 3)
        .flat_map(|y| (3..g.width - 3).map(move |x| [x as f64, y as f64]))
        .collect();
    let expected: Vec<_> = coords
        .iter()
        .map(|p| std::array::from_fn(|ch| interp(&guide_planes[ch], g, p[0], p[1])))
        .collect();
    confidences(
        planes,
        c,
        Guide {
            geometry: g,
            planes: guide_planes,
            coords: &coords,
            expected: &expected,
            calibrations: &[calibration(); 2],
        },
    )
}

#[test]
fn session_reconstruction_rgb_motion_flat_noise_and_exposure_null_first() {
    let g = PlaneGeometry {
        width: 64,
        height: 64,
    };
    let expected = [400., 900., 300.];
    let guide = expected.map(|v| vec![v; g.pixels()]);
    let mut seed = 718901;
    let c = calibration();
    let planes = std::array::from_fn(|ch| {
        let value = expected[if ch == 3 { 1 } else { ch }];
        (0..g.pixels())
            .map(|_| value + noise(&mut seed) * c.noise[ch].variance(value).sqrt())
            .collect()
    });
    let supported = field(&planes, &guide, g, c);
    assert!(
        supported.iter().all(|v| *v > 0.),
        "known independent flat noise was refused"
    );
    let half: [Vec<f32>; 4] =
        std::array::from_fn(|ch| vec![expected[if ch == 3 { 1 } else { ch }] * 0.5; g.pixels()]);
    assert!(
        field(&half, &guide, g, Calibration { gain: 2., ..c })
            .iter()
            .all(|v| *v == 1.)
    );
    for color in [0, 2] {
        let mut changed = planes.clone();
        for v in &mut changed[color] {
            *v += 400.;
        }
        assert!(
            field(&changed, &guide, g, c).iter().all(|v| *v == 0.),
            "isolated color{color} change survived"
        );
        // Causal foil: neither changed original color changes the old green-only check.
        assert_eq!(changed[1], planes[1]);
        assert_eq!(changed[3], planes[3]);
    }
    let mut noisier_green = c;
    noisier_green.noise[3].read_noise_e = 100.;
    let mut noisy = planes.clone();
    noisy[3] = (0..g.pixels())
        .map(|_| 900. + noise(&mut seed) * noisier_green.noise[3].variance(900.).sqrt())
        .collect();
    assert!(
        field(&noisy, &guide, g, noisier_green)
            .iter()
            .all(|v| *v > 0.)
    );
}

struct Raw {
    data: Vec<u16>,
    g: PlaneGeometry,
}
impl QuadSource for Raw {
    fn geometry(&self) -> PlaneGeometry {
        self.g
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let start = 4 * y * self.g.width;
        (
            &self.data[start..start + 2 * self.g.width],
            &self.data[start + 2 * self.g.width..start + 4 * self.g.width],
        )
    }
}
fn original(pull: Similarity, appearance: [f64; 3]) -> Raw {
    let g = PlaneGeometry {
        width: 80,
        height: 80,
    };
    let mut data = Vec::with_capacity(4 * g.pixels());
    for y in 0..2 * g.height {
        for x in 0..2 * g.width {
            let px = x as f64 - 2. * pull.b.re;
            let py = y as f64 - 2. * pull.b.im;
            let value = match (x % 2, y % 2) {
                (0, 0) => 2400. + 1200. * ((px + 0.4 * py - 100.) / 6.).tanh() + appearance[0],
                (1, 1) => 1700. - 700. * ((px - 0.3 * py - 50.) / 7.).tanh() + appearance[2],
                _ => 1800. + appearance[1],
            };
            data.push((512. + value).round() as u16);
        }
    }
    Raw { data, g }
}
#[test]
fn session_reconstruction_rgb_motion_corrected_original_colored_edge_and_changed_color() {
    let truth = Similarity {
        a: Cx::new(1., 0.),
        b: Cx::new(0.31, -0.21),
    };
    let guide_raw = original(Similarity::IDENTITY, [0.; 3]);
    let domain = SamplingDomain {
        full: guide_raw.g,
        x: 16,
        y: 16,
        width: 48,
        height: 48,
    };
    let mut sampler = RegionSampler::new(domain, 2 << 20).unwrap();
    let g = PlaneGeometry {
        width: 48,
        height: 48,
    };
    let reference = sampler
        .gather_pulls(
            &guide_raw,
            LEVELS,
            [Similarity::IDENTITY; 3],
            Resampler::CatmullRom,
        )
        .unwrap();
    let mut guide = std::array::from_fn(|_| vec![0.; g.pixels()]);
    let mut scratch = vec![0.; g.pixels()];
    let mut green_plane = vec![0.; g.pixels()];
    green(&reference.planes, &mut green_plane);
    for (ch, out) in guide.iter_mut().enumerate() {
        box_mean(
            if ch == 1 {
                &green_plane
            } else {
                &reference.planes[ch]
            },
            g,
            3,
            &mut scratch,
            out,
        );
    }
    let reference_greens = [reference.planes[1].clone(), reference.planes[3].clone()];
    let target = original(truth, [0.; 3]);
    // The producer consumes the returned correction, with a nonzero displacement
    // relative to the independently saved guide. Green is deliberately textureless.
    let measured = sampler
        .gather_pulls(&target, LEVELS, [truth; 3], Resampler::CatmullRom)
        .unwrap();
    let accepted = field(&measured.planes, &guide, g, calibration());
    assert!(
        accepted.iter().all(|v| *v > 0.95),
        "unchanged colored edge was rejected"
    );
    for color in [0, 2] {
        let mut appearance = [0.; 3];
        appearance[color] = 1500.;
        let changed = original(truth, appearance);
        let measured = sampler
            .gather_pulls(&changed, LEVELS, [truth; 3], Resampler::CatmullRom)
            .unwrap();
        assert!(
            field(&measured.planes, &guide, g, calibration())
                .iter()
                .all(|v| *v == 0.)
        );
        for (before, after) in reference_greens
            .iter()
            .zip([&measured.planes[1], &measured.planes[3]])
        {
            assert!(before.iter().zip(after).all(|(a, b)| (a - b).abs() < 0.001));
        }
    }
}
