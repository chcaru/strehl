//! Include as `align_cmd::cfa_integration_tests` with direct-cfa-gather enabled.
//! Generated storage fixtures only: no decoder, private RAW, or env mutation.
//! These are integration/correctness controls, not photographic-quality evidence.

use std::path::PathBuf;

use strehl_core::align::{Cx, Resampler, Similarity};
use strehl_core::noise::Levels;
use strehl_core::optics::{A7C2_FE100GM_2XTC_X4CPL, OpticalProfile};
use strehl_core::plane::PlaneGeometry;
use strehl_core::warpmap::{FrameWarp, Provenance, StackIdentity, WarpMap};
use strehl_raw::{Frame, Region};

use super::{CropRect, WarpScratch, direct_cfa, writeback_fullres_site};

const GEOM: PlaneGeometry = PlaneGeometry {
    width: 48,
    height: 40,
};

fn fixture() -> Frame {
    let active = Region {
        x: 5,
        y: 3,
        width: 2 * GEOM.width,
        height: 2 * GEOM.height,
    };
    let stride = active.width + 17;
    let buffer_height = active.height + 11;
    // Padding has a large phase-dependent color and must neither be read nor written.
    let mut data: Vec<u16> = (0..stride * buffer_height)
        .map(|i| [61_001, 62_003, 63_007, 64_009][(i / stride % 2) * 2 + i % 2])
        .collect();
    for y in 0..active.height {
        for x in 0..active.width {
            let phase = (y % 2) * 2 + x % 2;
            let mut hash = (x as u32 + 37)
                .wrapping_mul(0x9e37_79b9)
                .wrapping_add((y as u32 + 17).wrapping_mul(0x85eb_ca6b))
                .wrapping_add((phase as u32).wrapping_mul(0xc2b2_ae35));
            hash ^= hash >> 16;
            hash = hash.wrapping_mul(0x27d4_eb2d);
            hash ^= hash >> 15;
            // Distinct nonperiodic G1/G2 values, with real samples below black.
            let value = if (x + 7 * y) % 11 == 0 {
                (hash % 400) as u16
            } else {
                (900 + hash % 11_000 + phase as u32 * 700) as u16
            };
            data[(active.y + y) * stride + active.x + x] = value;
        }
    }
    Frame {
        data,
        stride,
        buffer_height,
        active,
        levels: Levels {
            black: 512.0,
            white: 16_383.0,
        },
        iso: Some(100.0),
        wb_coeffs: [2.0, 1.0, 4.0, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "generated RGGB integration fixture".into(),
        path: PathBuf::from("__strehl_generated_cfa_fixture_does_not_exist__.ARW"),
    }
}

fn channel(dx: usize, dy: usize) -> usize {
    match (dx, dy) {
        (0, 0) => 0,
        (1, 1) => 2,
        _ => 1,
    }
}

// Independent continuous Keys basis: no call to the production lattice view,
// coefficient generator, complex transform, or CA composition implementation.
fn keys(distance: f64) -> f64 {
    let d = distance.abs();
    if d < 1.0 {
        1.5 * d * d * d - 2.5 * d * d + 1.0
    } else if d < 2.0 {
        -0.5 * d * d * d + 2.5 * d * d - 4.0 * d + 2.0
    } else {
        0.0
    }
}

fn reference_sample(frame: &Frame, ci: usize, x: f64, y: f64) -> Option<f64> {
    if !x.is_finite()
        || !y.is_finite()
        || x < 0.0
        || y < 0.0
        || x > (frame.active.width - 1) as f64
        || y > (frame.active.height - 1) as f64
    {
        return None;
    }
    let mut value = 0.0;
    // Enumerate physical sensels, rather than enumerating the production u/v stencil.
    for sy in y.floor() as i64 - 4..=y.floor() as i64 + 4 {
        for sx in x.floor() as i64 - 4..=x.floor() as i64 + 4 {
            let phase = (sx.rem_euclid(2), sy.rem_euclid(2));
            let same_color = match ci {
                0 => phase == (0, 0),
                1 => phase.0 != phase.1,
                2 => phase == (1, 1),
                _ => unreachable!(),
            };
            if !same_color {
                continue;
            }
            let (dx, dy) = (sx as f64 - x, sy as f64 - y);
            let weight = if ci == 1 {
                keys((dx + dy) * 0.5) * keys((dx - dy) * 0.5)
            } else {
                keys(dx * 0.5) * keys(dy * 0.5)
            };
            if weight == 0.0 {
                continue;
            }
            if sx < 0
                || sy < 0
                || sx >= frame.active.width as i64
                || sy >= frame.active.height as i64
            {
                return None;
            }
            value += weight * f64::from(frame.sample(sx as usize, sy as usize));
        }
    }
    Some(value)
}

fn literal_pull(
    t: Similarity,
    px: usize,
    py: usize,
    phase: (usize, usize),
    ca: Option<&OpticalProfile>,
) -> (f64, f64) {
    let (cx, cy) = (GEOM.width as f64 * 0.5, GEOM.height as f64 * 0.5);
    let (dx, dy) = phase;
    let (x, y) = (
        px as f64 + dx as f64 * 0.5 - cx,
        py as f64 + dy as f64 * 0.5 - cy,
    );
    let mut sx = t.a.re * x - t.a.im * y + t.b.re;
    let mut sy = t.a.im * x + t.a.re * y + t.b.im;
    if let Some(profile) = ca {
        let eps = match channel(dx, dy) {
            0 => Some(profile.eps_r),
            2 => profile.eps_b,
            _ => None,
        };
        if let Some(eps) = eps {
            sx = (1.0 + eps) * sx + profile.translation.0;
            sy = (1.0 + eps) * sy + profile.translation.1;
        }
    }
    (2.0 * (sx + cx), 2.0 * (sy + cy))
}

struct Run {
    frame: Frame,
    coverage: f64,
    negative_samples: usize,
}

fn gather<const GREEN_ONLY: bool>(
    source: &Frame,
    t: Similarity,
    ca: Option<&OpticalProfile>,
) -> Run {
    let mut frame = source.clone();
    let mut scratch = WarpScratch::new(GEOM);
    let mut negative_samples = 0;
    let coverage = direct_cfa::warp::<GREEN_ONLY, _>(
        &mut frame,
        t,
        GEOM,
        Resampler::CatmullRom,
        &mut scratch,
        |frame, phase, values, covered, inv, black, mode| {
            let ci = channel(phase.0, phase.1);
            assert_eq!(black, 512.0);
            assert_eq!(inv, [0.5, 1.0, 0.25][ci]);
            for py in 0..GEOM.height {
                for px in 0..GEOM.width {
                    let index = py * GEOM.width + px;
                    let (sx, sy) = literal_pull(t, px, py, phase, ca);
                    let expected = reference_sample(source, ci, sx, sy);
                    assert_eq!(
                        covered[index],
                        expected.is_some(),
                        "coverage phase={phase:?} at ({px},{py}), source ({sx},{sy})"
                    );
                    if let Some(expected) = expected {
                        let actual = f64::from(values[index] * inv + black);
                        assert!(
                            (actual - expected).abs() < 0.05,
                            "DN phase={phase:?} at ({px},{py}): {actual} vs {expected}"
                        );
                        negative_samples += usize::from(values[index] < 0.0);
                    } else {
                        assert!(values[index].is_nan());
                    }
                }
            }
            let count = writeback_fullres_site(
                &mut frame.data,
                frame.stride,
                (frame.active.x, frame.active.y),
                GEOM,
                phase,
                values,
                covered,
                inv,
                black,
                mode,
            );
            assert_eq!(count, covered.iter().filter(|&&v| v).count());
            for py in 0..GEOM.height {
                for px in 0..GEOM.width {
                    let (sx, sy) = literal_pull(t, px, py, phase, ca);
                    let expected = reference_sample(source, ci, sx, sy)
                        .unwrap_or(f64::from(black))
                        .round()
                        .clamp(0.0, f64::from(u16::MAX));
                    let written = frame.sample(2 * px + phase.0, 2 * py + phase.1);
                    // f32 arithmetic can cross a half-DN rounding boundary.
                    assert!((f64::from(written) - expected).abs() <= 1.0);
                }
            }
            Ok(count)
        },
        ca,
    )
    .unwrap();
    for y in 0..frame.buffer_height {
        for x in 0..frame.stride {
            if x < frame.active.x
                || x >= frame.active.x + frame.active.width
                || y < frame.active.y
                || y >= frame.active.y + frame.active.height
            {
                assert_eq!(
                    frame.data[y * frame.stride + x],
                    source.data[y * frame.stride + x],
                    "padding changed at ({x},{y})"
                );
            }
        }
    }
    Run {
        frame,
        coverage,
        negative_samples,
    }
}

#[test]
fn cfa_identity_sink_preserves_low_dn_active_origin_and_padding() {
    let source = fixture();
    let full = gather::<false>(&source, Similarity::IDENTITY, None);
    assert_eq!(full.frame.data, source.data);
    assert_eq!(full.coverage, 1.0);
    assert!(
        full.negative_samples > 500,
        "fixture must exercise signed below-black values"
    );
}

#[test]
fn cfa_fractional_pull_sink_matches_physical_sensel_oracle_and_green_only() {
    let source = fixture();
    let t = Similarity {
        a: Cx::new(1.017, 0.009),
        b: Cx::new(0.231, -0.347),
    };
    let profile = OpticalProfile {
        eps_r: 0.012,
        eps_b: Some(-0.009),
        translation: (0.11, -0.08),
        ..A7C2_FE100GM_2XTC_X4CPL
    };
    let full = gather::<false>(&source, t, Some(&profile));
    let greens = gather::<true>(&source, t, Some(&profile));
    assert!(full.coverage > 0.7 && full.coverage < 1.0);
    assert!(greens.coverage > 0.7 && greens.coverage < 1.0);
    let mut changed_green = 0;
    for y in 0..source.active.height {
        for x in 0..source.active.width {
            if x % 2 != y % 2 {
                assert_eq!(greens.frame.sample(x, y), full.frame.sample(x, y));
                changed_green +=
                    usize::from(full.frame.sample(x, y).abs_diff(source.sample(x, y)) > 100);
            } else {
                assert_eq!(greens.frame.sample(x, y), source.sample(x, y));
            }
        }
    }
    assert!(
        changed_green > 2_000,
        "identity is not an acceptable fractional-pull placebo"
    );
    // Causal foils: reversing the translation or omitting the physical phase
    // must predict observably different sensels on this nonperiodic input.
    let wrong = Similarity {
        b: Cx::new(-t.b.re, -t.b.im),
        ..t
    };
    let mut wrong_pull = 0;
    let mut wrong_phase = 0;
    for py in 5..GEOM.height - 5 {
        for px in 5..GEOM.width - 5 {
            let (x, y) = literal_pull(t, px, py, (1, 0), None);
            let target = reference_sample(&source, 1, x, y).unwrap();
            let (x, y) = literal_pull(wrong, px, py, (1, 0), None);
            wrong_pull +=
                usize::from((target - reference_sample(&source, 1, x, y).unwrap()).abs() > 100.0);
            let (x, y) = literal_pull(t, px, py, (0, 0), None);
            wrong_phase +=
                usize::from((target - reference_sample(&source, 1, x, y).unwrap()).abs() > 100.0);
        }
    }
    assert!(wrong_pull > 900 && wrong_phase > 900);
}

fn map(warps: Vec<FrameWarp>, resampler: Resampler) -> WarpMap {
    WarpMap::new(
        Provenance {
            stack: StackIdentity::from_entries("generated-cfa", &[("generated.ARW", 0)]),
            strategy: "integration-control".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "generated geometry; no photographic measurement".into(),
        },
        GEOM,
        resampler,
        warps,
    )
}

#[test]
fn cfa_resolved_domain_refuses_missing_unplaced_kernel_and_expanded_support() {
    // Read but never mutate settings. The scheduler must use a clean process.
    assert!(
        matches!(
            std::env::var("STREHL_FIX_CA").as_deref(),
            Err(std::env::VarError::NotPresent) | Ok("off")
        ),
        "run with STREHL_FIX_CA unset/off; synthetic paths carry no gear identity"
    );
    let source = fixture();
    let paths = [source.path.clone()];
    let rect = CropRect {
        x: 2,
        y: 2,
        width: GEOM.width - 4,
        height: GEOM.height - 4,
    };
    let missing = direct_cfa::validate_domain(&paths, None, rect)
        .unwrap_err()
        .to_string();
    assert!(missing.contains("requires resolved alignment"));
    let identity = map(
        vec![FrameWarp::Placed(Similarity::IDENTITY)],
        Resampler::CatmullRom,
    );
    direct_cfa::validate_domain(&paths, Some(&identity), rect).unwrap();
    let wrong_kernel = map(
        vec![FrameWarp::Placed(Similarity::IDENTITY)],
        Resampler::Bilinear,
    );
    assert!(
        direct_cfa::validate_domain(&paths, Some(&wrong_kernel), rect)
            .unwrap_err()
            .to_string()
            .contains("Catmull-Rom")
    );
    let unplaced = map(
        vec![FrameWarp::Refused("deliberate foil".into())],
        Resampler::CatmullRom,
    );
    assert!(
        direct_cfa::validate_domain(&paths, Some(&unplaced), rect)
            .unwrap_err()
            .to_string()
            .contains("unplaced frame")
    );
    assert!(
        direct_cfa::validate_domain(&[], Some(&identity), rect)
            .unwrap_err()
            .to_string()
            .contains("count mismatch")
    );
    assert!(
        direct_cfa::validate_domain(&paths, Some(&identity), CropRect::whole(GEOM))
            .unwrap_err()
            .to_string()
            .contains("conservative support")
    );
    let profile = OpticalProfile {
        eps_r: 0.08,
        eps_b: None,
        translation: (0.0, 0.0),
        ..A7C2_FE100GM_2XTC_X4CPL
    };
    // Actual sampler with supplied CA: the previously supported red crop corner
    // loses source taps. Metadata lookup is deliberately not faked by this test.
    let expanded = gather::<false>(&source, Similarity::IDENTITY, Some(&profile));
    assert_eq!(expanded.frame.sample(4, 4), 512);
    assert_ne!(source.sample(4, 4), 512);
    assert!(expanded.coverage < 1.0);
    // Inject equivalent red geometry at the map boundary. This checks the actual
    // domain guard, but does not claim coverage of its file-to-CA lookup branch.
    let expanded_map = map(
        vec![FrameWarp::Placed(Similarity {
            a: Cx::real(1.08),
            b: Cx::ZERO,
        })],
        Resampler::CatmullRom,
    );
    assert!(
        direct_cfa::validate_domain(&paths, Some(&expanded_map), rect)
            .unwrap_err()
            .to_string()
            .contains("conservative support")
    );
}
