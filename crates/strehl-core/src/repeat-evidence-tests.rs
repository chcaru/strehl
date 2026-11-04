use super::*;
use crate::{align::Cx, noise::Levels};
use std::cell::Cell;

struct Raw {
    pixels: Vec<u16>,
    reads: Cell<usize>,
}
impl Raw {
    fn new(f: impl Fn(usize, usize) -> u16) -> Self {
        Self {
            pixels: (0..128 * 128).map(|i| f(i % 128, i / 128)).collect(),
            reads: Cell::new(0),
        }
    }
}
impl QuadSource for Raw {
    fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: 64,
            height: 64,
        }
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        self.reads.set(self.reads.get() + 1);
        (
            &self.pixels[y * 256..y * 256 + 128],
            &self.pixels[y * 256 + 128..y * 256 + 256],
        )
    }
}
fn view(raw: &Raw, plane: CfaPlane) -> OriginalView<'_> {
    OriginalView {
        acquisition_id: [7; 32],
        source: raw,
        plane,
        color_pull: Similarity {
            a: Cx::new(1., 0.),
            b: Cx::new(0., 0.),
        },
        noise: PlaneNoise {
            gain_dn_per_e: 1.,
            read_noise_e: 2.,
            levels: Levels {
                black: 1000.,
                white: 16000.,
            },
        },
        gain: 1.,
    }
}
const ID: [FilterTap; 1] = [FilterTap {
    offset_sensor: [0., 0.],
    weight: 1.,
}];
fn gather(v: &OriginalView<'_>, center: [f64; 2], filters: &[&[FilterTap]]) -> Observation {
    observe(
        v,
        v.source.geometry(),
        center,
        filters,
        Kernel::CatmullRom,
        1 << 20,
        |_| Some(0.),
    )
    .unwrap()
}

#[test]
fn four_original_sites_are_distinct_and_negative_signals_are_preserved() {
    let raw = Raw::new(|x, y| 996 + (x % 2 + 2 * (y % 2)) as u16);
    for plane in CfaPlane::ALL {
        let (x, y) = plane.rggb_offset();
        let got = gather(&view(&raw, plane), [64. + x as f64, 64. + y as f64], &[&ID]);
        assert_eq!(got.taps.len(), 1);
        assert_eq!(got.values[0], -4. + (x + 2 * y) as f32);
        assert_eq!(got.covariance[0][0], 4.);
        assert_eq!(got.taps[0].site.quad, [32, 32]);
    }
}

#[test]
fn catmull_half_phase_has_signed_taps_and_analytic_variance() {
    let raw = Raw::new(|_, _| 1100);
    let got = gather(&view(&raw, CfaPlane::R), [65., 65.], &[&ID]);
    assert_eq!(got.taps.len(), 16);
    assert!(got.taps.iter().any(|t| t.band_weights[0] < 0.));
    assert_eq!(got.values[0], 100.);
    assert_eq!(got.covariance[0][0], 4. * (41_f32 / 64.).powi(2));
}

#[test]
fn overlapping_filtered_interpolants_are_coalesced_before_variance() {
    let raw = Raw::new(|_, _| 1100);
    // A SENSOR-step-one filter overlaps original same-color interpolation taps.
    let filter: Vec<_> = [1., 4., 6., 4., 1.]
        .into_iter()
        .enumerate()
        .map(|(x, w)| FilterTap {
            offset_sensor: [x as f64 - 2., 0.],
            weight: w / 16.,
        })
        .collect();
    let got = gather(&view(&raw, CfaPlane::R), [64., 64.], &[&filter]);
    let expected = [-1., 12., 42., 12., -1.].map(|x| x / 64.);
    assert_eq!(got.taps.len(), 5);
    for (tap, w) in got.taps.iter().zip(expected) {
        assert_eq!(tap.band_weights[0], w);
    }
    assert_eq!(got.covariance[0][0], 4. * 1027. / 2048.);
    // Treating the five interpolants as independent gives another answer.
    let false_variance =
        4. * (1. / 256. + 16. / 256. * 41. / 64. + 36. / 256. + 16. / 256. * 41. / 64. + 1. / 256.);
    assert!((false_variance - got.covariance[0][0]).abs() > 0.5);
}

#[test]
fn all_bands_partition_identity_and_keep_signed_cross_covariance() {
    let raw = Raw::new(|x, y| 1000 + ((x * 13 + y * 7) % 800) as u16);
    let bands = binomial_bands();
    let negative_identity = [FilterTap {
        offset_sensor: [0., 0.],
        weight: -1.,
    }];
    let got = gather(
        &view(&raw, CfaPlane::G2),
        [63., 66.],
        &[&bands[0], &bands[1], &bands[2], &ID, &negative_identity],
    );
    assert!((got.values[0] + got.values[1] + got.values[2] - got.values[3]).abs() < 0.001);
    assert_eq!(got.covariance[3][4], -got.covariance[3][3]);
    assert!(got.covariance[3][4] < 0.);
    for a in 0..5 {
        for b in 0..5 {
            let expected: f32 = got
                .taps
                .iter()
                .map(|t| t.band_weights[a] * t.band_weights[b] * 4.)
                .sum();
            assert_eq!(got.covariance[a][b], expected);
            assert_eq!(got.covariance[a][b], got.covariance[b][a]);
        }
    }
}

#[test]
fn frozen_heterogeneous_original_noise_and_radiometric_gain_are_used_exactly() {
    let raw = Raw::new(|_, _| 1100);
    let mut v = view(&raw, CfaPlane::B);
    let base = observe(
        &v,
        raw.geometry(),
        [62.3, 65.1],
        &[&ID],
        Kernel::CatmullRom,
        1 << 20,
        |s| Some((s.quad[0] + 3 * s.quad[1]) as f32),
    )
    .unwrap();
    v.gain = 2.5;
    let scaled = observe(
        &v,
        raw.geometry(),
        [62.3, 65.1],
        &[&ID],
        Kernel::CatmullRom,
        1 << 20,
        |s| Some((s.quad[0] + 3 * s.quad[1]) as f32),
    )
    .unwrap();
    assert!((scaled.values[0] - base.values[0] * 2.5).abs() < 0.001);
    assert!((scaled.covariance[0][0] - base.covariance[0][0] * 6.25).abs() < 0.001);
    for t in &base.taps {
        assert_eq!(
            t.variance_dn2,
            4. + (t.site.quad[0] + 3 * t.site.quad[1]) as f32
        );
    }
}

#[test]
fn cancellation_removes_clipped_missing_and_unknown_dependencies() {
    let raw = Raw::new(|_, _| 16000);
    let cancel = [
        FilterTap {
            offset_sensor: [-1000., 0.],
            weight: 1.,
        },
        FilterTap {
            offset_sensor: [-1000., 0.],
            weight: -1.,
        },
    ];
    let got = observe(
        &view(&raw, CfaPlane::R),
        raw.geometry(),
        [64., 64.],
        &[&cancel],
        Kernel::CatmullRom,
        1 << 20,
        |_| panic!("cancelled dependency queried"),
    )
    .unwrap();
    assert_eq!(got.values[0], 0.);
    assert_eq!(got.covariance[0][0], 0.);
    assert!(got.taps.is_empty());
    assert_eq!(raw.reads.get(), 0);
    assert!(matches!(
        observe(
            &view(&raw, CfaPlane::R),
            raw.geometry(),
            [64., 64.],
            &[&ID],
            Kernel::CatmullRom,
            1 << 20,
            |_| Some(0.)
        ),
        Err(Refusal::Clipped)
    ));
}

#[test]
fn support_identity_overlap_and_unknown_are_explicit() {
    let raw = Raw::new(|_, _| 1100);
    let a = gather(&view(&raw, CfaPlane::R), [64., 64.], &[&ID]);
    let b = gather(&view(&raw, CfaPlane::R), [65., 65.], &[&ID]);
    assert!(a.shares_original_samples(&b));
    let separate = gather(&view(&raw, CfaPlane::R), [96., 96.], &[&ID]);
    assert!(!a.shares_original_samples(&separate));
    let green = gather(&view(&raw, CfaPlane::G1), [65., 64.], &[&ID]);
    assert!(!a.shares_original_samples(&green));
    let mut other = view(&raw, CfaPlane::R);
    other.acquisition_id = [8; 32];
    assert!(!a.shares_original_samples(&gather(&other, [64., 64.], &[&ID])));
    assert!(matches!(
        observe(
            &other,
            raw.geometry(),
            [64., 64.],
            &[&ID],
            Kernel::CatmullRom,
            1 << 20,
            |_| None
        ),
        Err(Refusal::UnknownExpectedSignal)
    ));
    assert!(matches!(
        observe(
            &other,
            raw.geometry(),
            [-4., 64.],
            &[&ID],
            Kernel::CatmullRom,
            1 << 20,
            |_| Some(0.)
        ),
        Err(Refusal::MissingSupport)
    ));
}

#[test]
fn bounded_validation_precedes_source_or_guide_reads() {
    let raw = Raw::new(|_, _| 1100);
    let v = view(&raw, CfaPlane::R);
    assert!(matches!(
        observe(
            &v,
            raw.geometry(),
            [64., 64.],
            &[&ID],
            Kernel::CatmullRom,
            1,
            |_| panic!("budget must fail before guide read")
        ),
        Err(Refusal::Budget)
    ));
    let oversized = [ID[0]; 257];
    assert!(matches!(
        observe(
            &v,
            raw.geometry(),
            [64., 64.],
            &[&oversized],
            Kernel::CatmullRom,
            usize::MAX,
            |_| panic!("invalid filter must fail before read")
        ),
        Err(Refusal::InvalidInput)
    ));
    assert_eq!(raw.reads.get(), 0);
    let wrong_shape = PlaneGeometry {
        width: 128,
        height: 32,
    };
    assert!(matches!(
        observe(
            &v,
            wrong_shape,
            [64., 64.],
            &[&ID],
            Kernel::CatmullRom,
            1 << 20,
            |_| panic!("wrong full gauge must fail before read")
        ),
        Err(Refusal::InvalidInput)
    ));
    let needed = gather(&v, [64., 64.], &[&ID]).reservation_bytes;
    raw.reads.set(0);
    assert!(matches!(
        observe(
            &v,
            raw.geometry(),
            [64., 64.],
            &[&ID],
            Kernel::CatmullRom,
            needed - 1,
            |_| panic!("below budget must fail before read")
        ),
        Err(Refusal::Budget)
    ));
    assert_eq!(raw.reads.get(), 0);
    assert!(
        observe(
            &v,
            raw.geometry(),
            [64., 64.],
            &[&ID],
            Kernel::CatmullRom,
            needed,
            |_| Some(0.)
        )
        .is_ok()
    );
}

#[test]
fn clipped_negative_taps_and_partial_rows_cannot_be_hidden() {
    let mut raw = Raw::new(|_, _| 1100);
    let baseline = gather(&view(&raw, CfaPlane::R), [65., 65.], &[&ID]);
    let negative = baseline
        .taps
        .iter()
        .find(|t| t.band_weights[0] < 0.)
        .unwrap()
        .site;
    raw.pixels[negative.quad[1] * 256 + negative.quad[0] * 2] = 16000;
    assert!(matches!(
        observe(
            &view(&raw, CfaPlane::R),
            raw.geometry(),
            [65., 65.],
            &[&ID],
            Kernel::CatmullRom,
            1 << 20,
            |_| Some(0.)
        ),
        Err(Refusal::Clipped)
    ));
    struct Partial;
    impl QuadSource for Partial {
        fn geometry(&self) -> PlaneGeometry {
            PlaneGeometry {
                width: 64,
                height: 64,
            }
        }
        fn quad_rows(&self, _: usize) -> (&[u16], &[u16]) {
            (&[1100], &[1100])
        }
    }
    let mut v = view(&raw, CfaPlane::R);
    v.source = &Partial;
    assert!(matches!(
        observe(
            &v,
            raw.geometry(),
            [64., 64.],
            &[&ID],
            Kernel::CatmullRom,
            1 << 20,
            |_| Some(0.)
        ),
        Err(Refusal::MissingSupport)
    ));
}

#[test]
fn odd_sensor_center_color_translation_scale_rotation_use_full_gauge() {
    let raw = Raw::new(|x, y| 1000 + (2 * x + 3 * y) as u16);
    for plane in CfaPlane::ALL {
        let mut v = view(&raw, plane);
        v.color_pull = Similarity {
            a: Cx::new(1.002, 0.013),
            b: Cx::new(0.37, -0.21),
        };
        let center = [55.3, 71.9];
        let got = gather(&v, center, &[&ID]);
        // Independent physical-sensor transform about (full_width+.5,full_height+.5).
        let x = center[0] - 64.5;
        let y = center[1] - 64.5;
        let sx = 64.5 + 1.002 * x - 0.013 * y + 2. * 0.37;
        let sy = 64.5 + 0.013 * x + 1.002 * y - 2. * 0.21;
        assert!((got.values[0] - (2. * sx + 3. * sy) as f32).abs() < 0.001);
    }
}

#[test]
fn independent_original_noise_matches_composed_multiband_covariance() {
    let mut raw = Raw::new(|_, _| 1000);
    let bands = binomial_bands();
    let filters = [&bands[0][..], &bands[1][..], &bands[2][..]];
    let predicted = gather(&view(&raw, CfaPlane::R), [64.4, 65.2], &filters);
    let mut state = 0x9e3779b97f4a7c15_u64;
    let mut sums = [0_f64; 3];
    let mut products = [[0_f64; 3]; 3];
    let count = 8192;
    for _ in 0..count {
        for tap in &predicted.taps {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            let [x, y] = tap.site.quad;
            raw.pixels[y * 256 + x * 2] = if state & 1 == 0 { 998 } else { 1002 };
        }
        let got = gather(&view(&raw, CfaPlane::R), [64.4, 65.2], &filters);
        for a in 0..3 {
            sums[a] += got.values[a] as f64;
            for (b, product) in products[a].iter_mut().enumerate() {
                *product += (got.values[a] * got.values[b]) as f64;
            }
        }
    }
    for a in 0..3 {
        for b in 0..3 {
            let empirical =
                products[a][b] / count as f64 - sums[a] * sums[b] / (count as f64).powi(2);
            assert!(
                (empirical - predicted.covariance[a][b] as f64).abs() < 0.04,
                "band {a},{b}: {empirical} versus {}",
                predicted.covariance[a][b]
            );
        }
    }
}
