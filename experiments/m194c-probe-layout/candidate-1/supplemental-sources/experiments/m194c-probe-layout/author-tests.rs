use super::*;
use crate::merge_cmd::PyramidDomain;
use std::path::PathBuf;
use strehl_core::align::SimilarityParams;
use strehl_core::noise::Levels;
use strehl_core::plane::PlaneGeometry;
use strehl_raw::Region;

mod legacy {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m194c-probe-layout/legacy-fill-noise.rs"
    ));

    pub(super) fn fill(data: &mut [u16], level: f64, sigma: f64, index: usize) {
        fill_noise(data, level, sigma, index);
    }
}

fn frame(full: PlaneGeometry, origin: [usize; 2], pad: [usize; 2], tail: [usize; 2]) -> Frame {
    let active_width = 2 * full.width + tail[0];
    let active_height = 2 * full.height + tail[1];
    let stride = origin[0] + active_width + pad[0];
    let buffer_height = origin[1] + active_height + pad[1];
    Frame {
        data: vec![65000; stride * buffer_height],
        stride,
        buffer_height,
        active: Region {
            x: origin[0],
            y: origin[1],
            width: active_width,
            height: active_height,
        },
        levels: Levels {
            black: 512.0,
            white: 15360.0,
        },
        iso: Some(160.0),
        wb_coeffs: [4.0 / 3.0, 1.0, 5.0 / 3.0, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "M194c known synthetic probe".into(),
        path: PathBuf::from("M194C-NO-SUCH-RAW.ARW"),
    }
}

fn consumed(frame: &Frame, full: PlaneGeometry) -> Vec<u16> {
    let mut out = Vec::new();
    for y in 0..2 * full.height {
        for x in 0..2 * full.width {
            out.push(frame.data[(frame.active.y + y) * frame.stride + frame.active.x + x]);
        }
    }
    out
}

fn assert_untouched_outside(frame: &Frame, full: PlaneGeometry) {
    let mut outside = 0;
    for y in 0..frame.buffer_height {
        for x in 0..frame.stride {
            let inside = (frame.active.x..frame.active.x + 2 * full.width).contains(&x)
                && (frame.active.y..frame.active.y + 2 * full.height).contains(&y);
            if !inside {
                assert_eq!(
                    frame.data[y * frame.stride + x],
                    65000,
                    "outside ({x},{y}) overwritten"
                );
                outside += 1;
            }
        }
    }
    assert!(outside > 0, "poison control must contain unused samples");
}

#[test]
fn m194c_sampler_matches_legacy_packed_and_rejects_storage_addressing() {
    for full in [
        PlaneGeometry {
            width: 37,
            height: 25,
        },
        PlaneGeometry {
            width: 160,
            height: 120,
        },
    ] {
        for index in [0, 1, 4, 17] {
            let mut packed = frame(full, [0, 0], [0, 0], [0, 0]);
            let mut expected = packed.data.clone();
            legacy::fill(&mut expected, 2512.0, 40.0, index);
            fill_probe_noise(&mut packed, full, 2512.0, 40.0, index).unwrap();
            assert_eq!(packed.data, expected, "packed RNG lineage changed");
            for (origin, pad, tail) in [
                ([2, 4], [5, 3], [0, 0]),
                ([7, 3], [12, 8], [0, 0]),
                ([1, 5], [9, 6], [1, 1]),
                ([0, 0], [0, 0], [1, 1]),
            ] {
                let mut relocated = frame(full, origin, pad, tail);
                let mut old = relocated.clone();
                legacy::fill(&mut old.data, 2512.0, 40.0, index);
                assert_ne!(
                    consumed(&old, full),
                    expected,
                    "old addressing failure was not exercised"
                );
                fill_probe_noise(&mut relocated, full, 2512.0, 40.0, index).unwrap();
                assert_eq!(
                    consumed(&relocated, full),
                    expected,
                    "layout changed consumed probe"
                );
                assert_untouched_outside(&relocated, full);
            }
        }
    }
}

#[test]
fn m194c_sampler_seed_and_quantization_are_live() {
    let full = PlaneGeometry {
        width: 53,
        height: 39,
    };
    let mut a = frame(full, [3, 1], [4, 7], [1, 1]);
    let mut b = a.clone();
    fill_probe_noise(&mut a, full, 2512.0, 40.0, 3).unwrap();
    fill_probe_noise(&mut b, full, 2512.0, 40.0, 4).unwrap();
    assert_ne!(consumed(&a, full), consumed(&b, full));
    let mut low = a.clone();
    let mut high = a.clone();
    fill_probe_noise(&mut low, full, -5.0, 40.0, 3).unwrap();
    fill_probe_noise(&mut high, full, 65540.0, 40.0, 3).unwrap();
    for (f, level) in [(&low, -5.0), (&high, 65540.0)] {
        let mut expected = vec![0; 4 * full.pixels()];
        legacy::fill(&mut expected, level, 40.0, 3);
        assert_eq!(consumed(f, full), expected);
        assert_untouched_outside(f, full);
    }
    assert!(consumed(&low, full).contains(&0));
    assert!(consumed(&high, full).contains(&u16::MAX));
}

#[test]
fn m194c_sampler_refuses_malformed_storage_before_writing() {
    let full = PlaneGeometry {
        width: 31,
        height: 27,
    };
    let valid = frame(full, [2, 4], [5, 3], [0, 0]);
    let mut cases = Vec::new();
    let mut short = valid.clone();
    short.data.pop();
    cases.push(short);
    let mut wrong_geometry = valid.clone();
    wrong_geometry.active.width -= 2;
    cases.push(wrong_geometry);
    let mut overflow = valid.clone();
    overflow.active.x = usize::MAX;
    cases.push(overflow);
    for mut bad in cases {
        let before = bad.data.clone();
        assert!(fill_probe_noise(&mut bad, full, 2512.0, 40.0, 0).is_err());
        assert_eq!(bad.data, before);
    }
}

fn beta(
    frame: &Frame,
    domain: PyramidDomain,
    bands: usize,
    index: usize,
    t: Similarity,
) -> Vec<u32> {
    let mut probe = Probe::new(domain, bands);
    let mut scratch = WarpScratch::new(domain.full);
    probe
        .measure(frame, index, t, Resampler::CatmullRom, &mut scratch)
        .unwrap();
    probe.last().iter().map(|v| v.to_bits()).collect()
}

#[test]
#[ignore = "run-controls.py isolates fullres and plane gather environments"]
fn m194c_actual_probe_is_invariant_to_layout_in_each_gather() {
    assert_eq!(std::env::var("STREHL_M194C").as_deref(), Ok("1"));
    assert!(matches!(
        std::env::var("STREHL_FULLRES_GATHER").as_deref(),
        Ok("0" | "1")
    ));
    assert_eq!(std::env::var("STREHL_FIX_CA").as_deref(), Ok("off"));
    assert!(std::env::var("STREHL_GATE_FLOOR").is_err());
    assert!(std::env::var("STREHL_GATE_FLOOR_SCALE").is_err());
    let full = PlaneGeometry {
        width: 160,
        height: 120,
    };
    let packed = frame(full, [0, 0], [0, 0], [0, 0]);
    let domains = [
        PyramidDomain::whole(full),
        PyramidDomain::cropped(
            full,
            align_cmd::CropRect {
                x: 9,
                y: 7,
                width: 142,
                height: 106,
            },
        )
        .unwrap(),
    ];
    let mut saw_finite = false;
    let mut saw_empty = false;
    let scales: Vec<_> = [0.0_f64, 2.0, 4.0, 6.0, 8.0]
        .iter()
        .map(|j| {
            let d = j - 4.0;
            1.0 + 0.001 * d + 0.00013 * d * d
        })
        .collect();
    assert!((scales[2] - (scales[0] + scales[4]) / 2.0).abs() > 0.001);
    for domain in domains {
        for bands in [1, 3, 5, 7] {
            for (index, scale) in scales.iter().enumerate() {
                let g = scale - 1.0;
                let t = Similarity::from_params(SimilarityParams {
                    ax: -11.5 * g,
                    ay: 9.5 * g,
                    g,
                    rot: 0.0,
                });
                let expected = beta(&packed, domain, bands, index, t);
                saw_empty |= expected.is_empty();
                saw_finite |= expected.iter().any(|v| f32::from_bits(*v).is_finite());
                assert!(expected.iter().all(|v| f32::from_bits(*v).is_finite()));
                for (origin, pad, tail) in [([2, 4], [5, 3], [0, 0]), ([7, 3], [12, 8], [1, 1])] {
                    let alternate = frame(full, origin, pad, tail);
                    assert_eq!(beta(&alternate, domain, bands, index, t), expected);
                }
            }
        }
    }
    let tiny = PlaneGeometry {
        width: 12,
        height: 10,
    };
    let tiny_frame = frame(tiny, [1, 3], [7, 5], [1, 1]);
    let tiny_beta = beta(
        &tiny_frame,
        PyramidDomain::whole(tiny),
        3,
        0,
        Similarity::IDENTITY,
    );
    assert!(tiny_beta.is_empty());
    // Direct pooling-helper refusal, not a normally reachable measured level.
    assert_eq!(
        pooled_mean_square(
            &[0.0; 120],
            LevelSize {
                width: 12,
                height: 10
            }
        ),
        None
    );
    assert!(saw_finite && saw_empty);
    let d = PyramidDomain::whole(full);
    let identity = beta(&packed, d, 3, 0, Similarity::IDENTITY);
    assert_ne!(
        identity,
        beta(&packed, d, 3, 1, Similarity::IDENTITY),
        "seed did not affect finite probe"
    );
    let t = Similarity::from_params(SimilarityParams {
        ax: 0.17,
        ay: -0.29,
        g: 0.0021,
        rot: 0.0,
    });
    assert_ne!(
        identity,
        beta(&packed, d, 3, 0, t),
        "warp did not affect finite probe"
    );
}
