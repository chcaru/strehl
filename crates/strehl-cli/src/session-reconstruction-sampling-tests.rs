use super::*;
use crate::session_sampling::NativeSampler;
use std::cell::Cell;
use strehl_core::{align::Cx, optics::A7C2_FE100GM_2XTC_X4CPL};
const LEVELS: Levels = Levels {
    black: 512.,
    white: 16000.,
};
const RESAMPLERS: [Resampler; 6] = [
    Resampler::Nearest,
    Resampler::Bilinear,
    Resampler::CatmullRom,
    Resampler::ClampedCatmullRom,
    Resampler::Lanczos2,
    Resampler::Lanczos3,
];
struct Raw {
    geometry: PlaneGeometry,
    stride: usize,
    data: Vec<u16>,
    rows: Cell<usize>,
}
impl Raw {
    fn new(width: usize, height: usize) -> Self {
        let stride = 2 * width + 15;
        let mut out = Self {
            geometry: PlaneGeometry { width, height },
            stride,
            data: vec![65535; stride * (2 * height + 13)],
            rows: Cell::new(0),
        };
        for y in 0..height {
            for x in 0..width {
                for c in 0..4 {
                    out.set(
                        c,
                        x,
                        y,
                        (300 + (x * 139 + y * 79 + c * 1317) % 12000) as u16,
                    );
                }
            }
        }
        out
    }
    fn set(&mut self, c: usize, x: usize, y: usize, value: u16) {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        self.data[(5 + 2 * y + dy) * self.stride + 7 + 2 * x + dx] = value;
    }
}
impl QuadSource for Raw {
    fn geometry(&self) -> PlaneGeometry {
        self.geometry
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        self.rows.set(self.rows.get() + 1);
        let start = (5 + 2 * y) * self.stride + 7;
        (
            &self.data[start..start + 2 * self.geometry.width],
            &self.data[start + self.stride..start + self.stride + 2 * self.geometry.width],
        )
    }
}
fn equal(a: &SampledCfa, b: &SampledCfa) {
    assert_eq!(a.coverage, b.coverage, "coverage");
    assert_eq!(a.clipped, b.clipped, "clip footprint");
    assert_eq!(a.support, b.support, "support");
    for c in 0..4 {
        for i in 0..a.planes[c].len() {
            assert_eq!(
                a.planes[c][i].to_bits(),
                b.planes[c][i].to_bits(),
                "CFA{c} pixel{i}: {} != {}",
                a.planes[c][i],
                b.planes[c][i]
            );
        }
    }
}
#[test]
fn session_region_sampling_matches_native_bits_for_gauge_optics_crops_and_boundaries() {
    let mut raw = Raw::new(129, 97);
    for c in 0..4 {
        for (x, y) in [(0, 0), (20, 23), (63, 49), (125, 93)] {
            raw.set(c, x, y, 16000);
        }
    }
    let profile = OpticalProfile {
        eps_r: 0.012,
        eps_b: Some(-0.008),
        translation: (0.4, -0.3),
        ..A7C2_FE100GM_2XTC_X4CPL
    };
    let transforms = [
        Similarity::IDENTITY,
        Similarity {
            a: Cx::new(1., 0.),
            b: Cx::new(0.5, 0.25),
        },
        Similarity {
            a: Cx::new(0.97, 0.06),
            b: Cx::new(3.125, -2.75),
        },
        Similarity {
            a: Cx::new(1.08, -0.017),
            b: Cx::new(-5., 3.),
        },
    ];
    let domains = [
        SamplingDomain::full(raw.geometry),
        SamplingDomain {
            full: raw.geometry,
            x: 19,
            y: 21,
            width: 17,
            height: 11,
        },
        SamplingDomain {
            full: raw.geometry,
            x: 118,
            y: 85,
            width: 11,
            height: 12,
        },
    ];
    for domain in domains {
        for resampler in RESAMPLERS {
            for placement in transforms {
                for optics in [None, Some(&profile)] {
                    let mut native = NativeSampler::new(domain).unwrap();
                    let mut region = RegionSampler::new(domain, 4 << 20).unwrap();
                    let a = native
                        .gather(&raw, LEVELS, placement, optics, resampler)
                        .unwrap();
                    let b = region
                        .gather(&raw, LEVELS, placement, optics, resampler)
                        .unwrap();
                    equal(a, b);
                }
            }
        }
    }
}
#[test]
fn session_region_sampling_preserves_small_plane_fallback_and_far_outside_coverage() {
    for width in 1..=8 {
        for height in 1..=8 {
            let raw = Raw::new(width, height);
            let domain = SamplingDomain::full(raw.geometry);
            for resampler in RESAMPLERS {
                for shift in [0., 0.25, -0.5, 10000.] {
                    let t = Similarity {
                        a: Cx::new(1., 0.),
                        b: Cx::new(shift, shift),
                    };
                    let mut native = NativeSampler::new(domain).unwrap();
                    let mut region = RegionSampler::new(domain, 65536).unwrap();
                    equal(
                        native.gather(&raw, LEVELS, t, None, resampler).unwrap(),
                        region.gather(&raw, LEVELS, t, None, resampler).unwrap(),
                    );
                }
            }
        }
    }
}
#[test]
fn session_region_sampling_composed_color_pulls_match_each_native_operator() {
    let raw = Raw::new(80, 72);
    let domain = SamplingDomain {
        full: raw.geometry,
        x: 22,
        y: 26,
        width: 12,
        height: 9,
    };
    let pulls = [
        Similarity {
            a: Cx::new(1.03, 0.02),
            b: Cx::new(0.125, -0.5),
        },
        Similarity {
            a: Cx::new(0.98, -0.01),
            b: Cx::new(0.5, 0.25),
        },
        Similarity {
            a: Cx::new(1.01, 0.03),
            b: Cx::new(-1.25, 0.375),
        },
    ];
    for resampler in RESAMPLERS {
        let mut region = RegionSampler::new(domain, 1 << 20).unwrap();
        let actual = region.gather_pulls(&raw, LEVELS, pulls, resampler).unwrap();
        for (ci, color) in CfaPlane::ALL.into_iter().enumerate() {
            let mut native = NativeSampler::new(domain).unwrap();
            let expected = native
                .gather(&raw, LEVELS, cfa_pull(pulls, color), None, resampler)
                .unwrap();
            assert_eq!(
                actual.planes[ci]
                    .iter()
                    .map(|x| x.to_bits())
                    .collect::<Vec<_>>(),
                expected.planes[ci]
                    .iter()
                    .map(|x| x.to_bits())
                    .collect::<Vec<_>>()
            );
        }
    }
}
#[test]
fn session_region_sampling_budget_preflights_and_never_scans_full_source() {
    let raw = Raw::new(1024, 768);
    let domain = SamplingDomain {
        full: raw.geometry,
        x: 510,
        y: 380,
        width: 16,
        height: 12,
    };
    let pulls = [Similarity::IDENTITY; 3];
    let expected = reservation_bytes(domain, pulls).unwrap();
    assert!(expected < 16 * 1024);
    let mut region = RegionSampler::new(domain, expected - 1).unwrap();
    assert!(
        region
            .gather_pulls(&raw, LEVELS, pulls, Resampler::Lanczos3)
            .is_err()
    );
    assert_eq!(
        raw.rows.get(),
        0,
        "budget must refuse before reading source"
    );
    let mut region = RegionSampler::new(domain, expected).unwrap();
    region
        .gather_pulls(&raw, LEVELS, pulls, Resampler::Lanczos3)
        .unwrap();
    assert_eq!(region.peak_reserved_bytes(), expected);
    assert!(raw.rows.get() <= 4 * (domain.height + 10));
    assert!(RegionSampler::new(domain, 1).is_err());
    assert!(
        reservation_bytes(
            domain,
            [Similarity {
                a: Cx::new(f64::NAN, 0.),
                b: Cx::new(0., 0.)
            }; 3]
        )
        .is_err()
    );
    assert!(
        reservation_bytes(
            SamplingDomain {
                width: usize::MAX,
                ..domain
            },
            pulls
        )
        .is_err()
    );
}
#[test]
fn session_region_sampling_fractional_phase_is_exact_far_from_array_origin() {
    let mut raw = Raw::new(4099, 41);
    raw.set(2, 4079, 23, 16000);
    let domain = SamplingDomain {
        full: raw.geometry,
        x: 4072,
        y: 17,
        width: 12,
        height: 10,
    };
    for phase in [0., f64::EPSILON, 0.125, 0.5, 0.9999999999999] {
        for resampler in RESAMPLERS {
            let t = Similarity {
                a: Cx::new(1.00001, 0.00003),
                b: Cx::new(phase, -phase),
            };
            let mut native = NativeSampler::new(domain).unwrap();
            let mut region = RegionSampler::new(domain, 1 << 20).unwrap();
            equal(
                native.gather(&raw, LEVELS, t, None, resampler).unwrap(),
                region.gather(&raw, LEVELS, t, None, resampler).unwrap(),
            );
        }
    }
}
