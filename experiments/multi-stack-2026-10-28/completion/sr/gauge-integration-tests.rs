//! Integration witness against the production NativeSampler and stored WarpMap
//! gauge. The polynomial source is populated directly at original sensor sites.
use strehl_cli::session_sampling::{NativeSampler, SamplingDomain};
use strehl_core::reconstruction::{channel_pulls, sensor_pull};
use strehl_core::{
    CfaPlane,
    align::{Cx, Resampler, Similarity},
    noise::Levels,
    optics::{A7C2_FE100GM_2XTC_X4CPL, OpticalProfile},
    plane::{PlaneGeometry, QuadSource},
};
struct Padded {
    geom: PlaneGeometry,
    stride: usize,
    origin: [usize; 2],
    pixels: Vec<u16>,
}
impl QuadSource for Padded {
    fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let i = (self.origin[1] + 2 * y) * self.stride + self.origin[0];
        let n = 2 * self.geom.width;
        (
            &self.pixels[i..i + n],
            &self.pixels[i + self.stride..i + self.stride + n],
        )
    }
}
#[test]
fn production_native_sampler_witnesses_all_sites_scale_rotation_optics_and_crop() {
    let g = PlaneGeometry {
        width: 64,
        height: 48,
    };
    let origin = [7, 11];
    let stride = 2 * g.width + 16;
    let mut raw = Padded {
        geom: g,
        stride,
        origin,
        pixels: vec![65535; stride * (2 * g.height + 19)],
    };
    for y in 0..2 * g.height {
        for x in 0..2 * g.width {
            let c = match (x % 2, y % 2) {
                (0, 0) => 0,
                (1, 0) => 1,
                (1, 1) => 2,
                _ => 3,
            };
            raw.pixels[(origin[1] + y) * stride + origin[0] + x] =
                (512 + 1000 * (c + 1) + 3 * (origin[0] + x) + 5 * (origin[1] + y)) as u16;
        }
    }
    let domain = SamplingDomain {
        full: g,
        x: 17,
        y: 13,
        width: 12,
        height: 10,
    };
    let levels = Levels {
        black: 512.,
        white: 16000.,
    };
    let profile = OpticalProfile {
        eps_r: 0.12,
        eps_b: Some(-0.08),
        translation: (0.4, -0.3),
        ..A7C2_FE100GM_2XTC_X4CPL
    };
    let maps = [
        Similarity::IDENTITY,
        Similarity {
            a: Cx::new(1.08, 0.),
            b: Cx::new(0., 0.),
        },
        Similarity {
            a: Cx::new(1.03, 0.07),
            b: Cx::new(0.31, -0.43),
        },
    ];
    let mut sampler = NativeSampler::new(domain).unwrap();
    let mut wrong_gauge_witness = 0f64;
    for placement in maps {
        for optical in [None, Some(&profile)] {
            let pulls = channel_pulls(placement, optical);
            let sampled = sampler
                .gather(&raw, levels, placement, optical, Resampler::Bilinear)
                .unwrap();
            for (ci, plane) in CfaPlane::ALL.into_iter().enumerate() {
                let (dx, dy) = plane.rggb_offset();
                let color = match ci {
                    0 => 0,
                    2 => 2,
                    _ => 1,
                };
                let t = pulls[color];
                for y in 0..domain.height {
                    for x in 0..domain.width {
                        let i = y * domain.width + x;
                        assert!(sampled.support[i]);
                        let p = [
                            (2 * (domain.x + x) + dx) as f64,
                            (2 * (domain.y + y) + dy) as f64,
                        ];
                        let source = sensor_pull(t, g, p);
                        let expected = 1000. * (ci + 1) as f64
                            + 3. * (source[0] + origin[0] as f64)
                            + 5. * (source[1] + origin[1] as f64);
                        assert!(
                            (f64::from(sampled.planes[ci][i]) - expected).abs() < 0.002,
                            "native witness c={ci},p={p:?},value={},expected={expected}",
                            sampled.planes[ci][i]
                        );
                        let inverse = sensor_pull(t.invert().unwrap(), g, source);
                        assert!((inverse[0] - p[0]).hypot(inverse[1] - p[1]) < 1e-10);
                        let wrong = t.apply_at(
                            (p[0] - 0.5) * 0.5,
                            (p[1] - 0.5) * 0.5,
                            (g.width - 1) as f64 * 0.5,
                            (g.height - 1) as f64 * 0.5,
                        );
                        let wrong_value = 1000. * (ci + 1) as f64
                            + 3. * (2. * wrong.0 + 0.5 + origin[0] as f64)
                            + 5. * (2. * wrong.1 + 0.5 + origin[1] as f64);
                        wrong_gauge_witness =
                            wrong_gauge_witness.max((wrong_value - expected).abs());
                    }
                }
            }
        }
    }
    assert!(
        wrong_gauge_witness > 0.5,
        "integration witness must fail the original centre error"
    );
}
