// Independent old scalar consumer and exact scheduling controls; root executes.
use crate::align_cmd::{writeback_fullres_site, WarpWriteback};
use strehl_core::plane::PlaneGeometry;

#[allow(clippy::too_many_arguments)]
fn old_scalar(data: &mut [u16], stride: usize, active: (usize, usize), g: PlaneGeometry,
              site: (usize, usize), dst: &[f32], cover: &[bool], inv: f32, black: f32) -> usize {
    let black_dn = black.round().clamp(0.0, u16::MAX as f32) as u16;
    let mut count = 0;
    for py in 0..g.height {
        let row = (active.1 + 2 * py + site.1) * stride + active.0 + site.0;
        let lo = py * g.width;
        for px in 0..g.width {
            data[row + 2 * px] = if cover[lo + px] {
                count += 1;
                (dst[lo + px] * inv + black).round().clamp(0.0, u16::MAX as f32) as u16
            } else { black_dn };
        }
    }
    count
}

pub(super) fn direct_controls() -> usize {
    // Quad width/height, active x/y, right/bottom padding, odd active tail.
    let layouts = [(1, 1, 0, 0, 0, 0, 0), (2, 3, 1, 2, 4, 3, 1),
                   (17, 9, 3, 1, 5, 4, 1), (64, 47, 2, 5, 11, 3, 0)];
    let values = [f32::NEG_INFINITY, -1.0e8, -512.75, -1.5, -0.5, -0.0,
                  0.0, 0.5, 1.5, 65534.5, 65535.5, 1.0e8, f32::INFINITY,
                  f32::from_bits(0x7fc01234), f32::from_bits(0xffc00001)];
    let mut comparisons = 0;
    let (mut saw_nan_covered, mut saw_nan_uncovered, mut saw_signed_zero,
         mut saw_low_clip, mut saw_high_clip, mut saw_padding, mut saw_tail,
         mut saw_multiline) = (false, false, false, false, false, false, false, false);
    for threads in [1, 2, 8] {
        let pool = rayon::ThreadPoolBuilder::new().num_threads(threads).build().unwrap();
        for (layout, &(gw, gh, ax, ay, right, bottom, tail)) in layouts.iter().enumerate() {
            let g = PlaneGeometry { width: gw, height: gh };
            let stride = ax + 2 * gw + tail + right;
            let rows = ay + 2 * gh + tail + bottom;
            let before: Vec<u16> = (0..stride * rows).map(|i| 60000 + (i % 997) as u16).collect();
            let dst: Vec<f32> = (0..g.pixels()).map(|i| values[(7 * i + layout) % values.len()]).collect();
            saw_padding |= ax > 0 && ay > 0 && right > 0 && bottom > 0;
            saw_tail |= tail == 1;
            saw_multiline |= gh > 1;
            saw_signed_zero |= dst.iter().any(|v| v.to_bits() == (-0.0f32).to_bits());
            for black in [-1.5, 0.5, 512.25, 65535.5] {
                for inv in [1.0, 1.3] {
                    for cover_arm in 0..3 {
                        let cover: Vec<bool> = (0..g.pixels()).map(|i| match cover_arm {
                            0 => true, 1 => false, _ => (i * 5 + 3) % 7 >= 2,
                        }).collect();
                        saw_nan_covered |= dst.iter().zip(&cover).any(|(v, c)| v.is_nan() && *c);
                        saw_nan_uncovered |= dst.iter().zip(&cover).any(|(v, c)| v.is_nan() && !*c);
                        for site in [(0, 0), (1, 0), (0, 1), (1, 1)] {
                            let mut expected = before.clone();
                            let expected_count = old_scalar(&mut expected, stride, (ax, ay), g, site, &dst, &cover, inv, black);
                            assert_eq!(expected_count, cover.iter().filter(|c| **c).count());
                            for py in 0..gh {
                                for px in 0..gw {
                                    let i = (ay + 2 * py + site.1) * stride + ax + 2 * px + site.0;
                                    saw_low_clip |= cover[py * gw + px] && expected[i] == 0;
                                    saw_high_clip |= cover[py * gw + px] && expected[i] == u16::MAX;
                                }
                            }
                            for mode in [WarpWriteback::Serial, WarpWriteback::Parallel] {
                                let mut actual = before.clone();
                                let count = pool.install(|| writeback_fullres_site(&mut actual, stride, (ax, ay), g, site,
                                    &dst, &cover, inv, black, mode));
                                assert_eq!(count, expected_count, "coverage threads={threads} layout={layout} site={site:?} arm={cover_arm} mode={mode:?}");
                                assert_eq!(actual, expected, "whole storage threads={threads} layout={layout} site={site:?} arm={cover_arm} black={black} inv={inv} mode={mode:?}");
                                for y in 0..rows {
                                    for x in 0..stride {
                                        let touched = x >= ax + site.0 && y >= ay + site.1 &&
                                            x < ax + 2 * gw && y < ay + 2 * gh &&
                                            (x - ax - site.0) % 2 == 0 && (y - ay - site.1) % 2 == 0;
                                        if !touched { assert_eq!(actual[y * stride + x], before[y * stride + x], "untouched storage {x},{y}"); }
                                    }
                                }
                                #[cfg(feature = "native-direct-planes")]
                                pool.install(|| super::native_direct_planes_independent_tests::check_writeback_case(
                                    &expected, stride, (ax, ay), g, site, &dst, &cover, inv, black, mode));
                                comparisons += 1;
                            }
                        }
                    }
                }
            }
        }
    }
    assert_eq!(comparisons, 2304);
    assert!(saw_nan_covered && saw_nan_uncovered && saw_signed_zero && saw_low_clip && saw_high_clip && saw_padding && saw_tail && saw_multiline,
        "required arithmetic/layout control was not exercised");

    // Independently specified IEEE round/clamp/cast cases; covered NaN counts.
    let src = [f32::NEG_INFINITY, -65536.0, -0.5, -0.0, 0.0, 0.5, 1.5, 65534.5, 65535.5, f32::INFINITY, f32::NAN];
    let literal: [u16; 11] = [0, 0, 0, 0, 0, 1, 2, 65535, 65535, 65535, 0];
    let g = PlaneGeometry { width: src.len(), height: 1 };
    for mode in [WarpWriteback::Serial, WarpWriteback::Parallel] {
        let mut actual = vec![4321; 4 * g.width];
        let count = writeback_fullres_site(&mut actual, 2 * g.width, (0, 0), g, (1, 1), &src, &vec![true; src.len()], 1.0, 0.0, mode);
        assert_eq!(count, 11, "covered NaN must still contribute to integer coverage");
        for (x, expected) in literal.iter().enumerate() { assert_eq!(actual[2 * g.width + 1 + 2 * x], *expected); }
    }

    // Wrong stride and wrong phase preserve counts but must fail whole storage.
    let g = PlaneGeometry { width: 17, height: 9 };
    let (stride, active) = (43, (3, 1));
    let before: Vec<u16> = (0..stride * 24).map(|i| 50000 + (i % 787) as u16).collect();
    let dst: Vec<f32> = (0..g.pixels()).map(|i| 1000.0 + i as f32 * 3.0).collect();
    let cover = vec![true; g.pixels()];
    let mut right = before.clone();
    let count = old_scalar(&mut right, stride, active, g, (0, 0), &dst, &cover, 1.0, 512.25);
    let mut bad_stride = before.clone();
    let mut bad_phase = before.clone();
    assert_eq!(old_scalar(&mut bad_stride, 2 * g.width, active, g, (0, 0), &dst, &cover, 1.0, 512.25), count);
    assert_eq!(old_scalar(&mut bad_phase, stride, active, g, (1, 0), &dst, &cover, 1.0, 512.25), count);
    assert_ne!(right, bad_stride, "wrong-stride destroyer lost power");
    assert_ne!(right, bad_phase, "wrong-phase destroyer lost power");
    let j = g.width + 3;
    let mut flipped = cover.clone();
    flipped[j] = false;
    let target = (active.1 + 2) * stride + active.0 + 6;
    for mode in [WarpWriteback::Serial, WarpWriteback::Parallel] {
        let mut changed = before.clone();
        let got = writeback_fullres_site(&mut changed, stride, active, g, (0, 0), &dst, &flipped, 1.0, 512.25, mode);
        assert_eq!(got + 1, count, "flipped coverage bit did not reduce the actual count");
        assert_eq!(changed[target], 512, "uncovered destination did not receive rounded black");
        assert_ne!(right[target], changed[target], "coverage destroyer lost pixel power");
        assert_ne!(right, changed, "coverage destroyer lost whole-buffer power");
    }
    comparisons
}

#[test]
fn independent_parallel_writeback_controls() {
    let comparisons = direct_controls();
    super::native_green_probe_independent_tests::run_for_writeback_controls();
    let dir = std::path::PathBuf::from(std::env::var_os("STREHL_GREEN_PROBE_OUTPUT").unwrap());
    let result = serde_json::json!({
        "schema":"native-parallel-writeback-independent-v1",
        "requested_writeback":std::env::var("STREHL_WARP_WRITEBACK").unwrap_or_else(|_| "parallel-default".into()),
        "direct_comparisons":comparisons,
        "threads":[1,2,8],
        "literal_round_clamp_cast":true,
        "wrong_stride_phase_and_coverage_controls_live":true,
        "scope":"exact generated destination scheduling controls plus retained actual green/beta/whole/crop controls; no speed or calibration claim"
    });
    std::fs::write(dir.join("writeback-result.json"), serde_json::to_vec_pretty(&result).unwrap()).unwrap();
    println!("NATIVE_PARALLEL_WRITEBACK comparisons={comparisons} threads=1/2/8 literal-quantization=true covered-NaN-count=true wrong-stride/phase/coverage-live=true");
}
