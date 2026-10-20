//! Frozen pre-reuse reconstruction as the independent storage-path reference.
//! These are numerical identity checks, not photographic quality metrics.
use super::*;
use std::hint::black_box;
use std::time::Instant;

fn old_collapse(p: &Pyramid, ws: &mut Workspace) -> Vec<f32> {
    let n = p.levels();
    let mut acc = p.data[n - 1].clone();
    for k in (0..n - 1).rev() {
        let px = p.sizes[k].pixels();
        expand(
            &acc,
            p.sizes[k + 1],
            &mut ws.expanded[..px],
            p.sizes[k],
            &mut ws.scratch,
        );
        acc = ws.expanded[..px].to_vec();
        acc.par_iter_mut()
            .zip(&p.data[k])
            .for_each(|(a, l)| *a += l);
    }
    acc
}

fn old_bounded(m: &BandMerge, p: &Pyramid, c: usize, ws: &mut Workspace) -> Vec<f32> {
    let n = p.levels();
    let mut acc = p.level(n - 1).to_vec();
    if n > 1 {
        m.clamp_level(&mut acc, n - 1, c);
    }
    for k in (0..n - 1).rev() {
        let mut up = vec![0.0; p.sizes[k].pixels()];
        expand(&acc, p.sizes[k + 1], &mut up, p.sizes[k], &mut ws.scratch);
        for (u, b) in up.iter_mut().zip(p.level(k)) {
            *u += b;
        }
        if k > 0 {
            m.clamp_level(&mut up, k, c);
        }
        acc = up;
    }
    acc
}

fn bits_equal(a: &[f32], b: &[f32]) {
    assert_eq!(a.len(), b.len());
    for (i, (a, b)) in a.iter().zip(b).enumerate() {
        assert_eq!(a.to_bits(), b.to_bits(), "sample {i}: {a} != {b}");
    }
}

fn varied_pyramid(w: usize, h: usize, bands: usize) -> Pyramid {
    let mut p = Pyramid::zeros(&level_sizes(w, h, bands));
    for (k, level) in p.data.iter_mut().enumerate() {
        for (i, v) in level.iter_mut().enumerate() {
            // Signed coefficients, dissimilar level magnitudes, and values
            // requiring rounding. A constant-only fixture misses stale tails.
            let signed = ((i * 73 + k * 19) % 107) as f32 - 53.0;
            *v = signed * (1.000_000_1 + k as f32 * 0.071);
        }
    }
    p
}

#[test]
fn recycled_collapse_matches_old_bits_with_odd_sizes_and_dirty_workspaces() {
    rayon::ThreadPoolBuilder::new()
        .num_threads(4)
        .build()
        .unwrap()
        .install(|| {
            for (w, h) in [(1, 1), (7, 11), (64, 48), (65, 49), (511, 257)] {
                for bands in [0, 1, 2, 3, 7] {
                    let p = varied_pyramid(w, h, bands);
                    let mut old_ws = Workspace::new(p.sizes());
                    // Deliberately oversized: output length must remain exact.
                    let mut new_ws = Workspace::new(&level_sizes(w + 3, h + 5, bands));
                    let original = p.data.clone();
                    for repeat in 0..3 {
                        new_ws.expanded.fill(f32::NAN);
                        new_ws.scratch.fill(2000.0 + repeat as f32);
                        bits_equal(&old_collapse(&p, &mut old_ws), &p.collapse(&mut new_ws));
                    }
                    assert_eq!(p.data, original, "reconstruction changed stored bands");
                }
            }
        });
}

#[test]
fn recycled_collapse_preserves_large_workspace_across_small_odd_level_calls() {
    // Independent-review adversary: an odd count of swaps formerly shrank the
    // caller's workspace and made its next full-sized reconstruction panic.
    let large=varied_pyramid(257,193,5);
    let small=varied_pyramid(129,97,3);
    assert_eq!((small.levels()-1)%2,1,"adversary needs an odd number of swaps");
    let mut shared=Workspace::new(large.sizes());
    let mut reference=Workspace::new(large.sizes());
    let original_len=shared.expanded.len();
    for p in [&large,&small,&large,&small,&large] {
        bits_equal(&old_collapse(p,&mut reference),&p.collapse(&mut shared));
        assert_eq!(shared.expanded.len(),original_len,"caller workspace shrank");
    }
}

#[test]
fn recycled_bounded_collapse_matches_every_clamp_placement_and_has_active_bounds() {
    rayon::ThreadPoolBuilder::new()
        .num_threads(2)
        .build()
        .unwrap()
        .install(|| {
            let (w, h, bands, planes) = (65, 49, 3, 2);
            let p = varied_pyramid(w, h, bands);
            let mut active_lower = false;
            let mut active_upper = false;
            for from in [1, 2, 3, 8] {
                for low_only in [false, true] {
                    let cfg = MergeConfig {
                        bands,
                        hull: Hull::PerLevel,
                        hull_from_level: from,
                        hull_low_only: low_only,
                        hull_lambda: 0.6,
                        ..Default::default()
                    };
                    let mut m = BandMerge::new(w, h, planes, cfg);
                    for (i, (lo, (hi, sig))) in m
                        .lo_lv
                        .iter_mut()
                        .zip(m.hi_lv.iter_mut().zip(m.sig_lv.iter_mut()))
                        .enumerate()
                    {
                        lo.fill(-3.0 - i as f32);
                        hi.fill(5.0 + i as f32);
                        sig.fill(0.5);
                    }
                    for c in 0..planes {
                        let mut a = Workspace::new(p.sizes());
                        let mut b = Workspace::new(p.sizes());
                        let raw = p.collapse(&mut a);
                        let old = old_bounded(&m, &p, c, &mut a);
                        for (v, u) in old.iter().zip(&raw) {
                            active_lower |= v > u;
                            active_upper |= v < u;
                        }
                        for _ in 0..3 {
                            b.expanded.fill(f32::NAN);
                            bits_equal(&old, &m.collapse_bounded(&p, c, &mut b));
                        }
                    }
                }
            }
            assert!(active_lower && active_upper, "fixture never exercised both bounds");
        });
}

#[test]
fn recycled_collapse_preserves_impulses_ramps_and_zero_bits() {
    let sizes = level_sizes(129, 97, 4);
    let mut p = Pyramid::zeros(&sizes);
    let mut ws = Workspace::new(&sizes);
    for pattern in 0..4 {
        let src: Vec<f32> = (0..129 * 97)
            .map(|i| match pattern {
                0 => 0.0,
                1 => -0.0,
                2 => if i == 64 * 129 + 47 { 16383.0 } else { 512.0 },
                _ => 512.0 + (i % 129) as f32 * 31.37 + (i / 129) as f32 * 2.11,
            })
            .collect();
        p.build(&src, &mut ws);
        let expected = old_collapse(&p, &mut ws);
        bits_equal(&expected, &p.collapse(&mut ws));
    }
}

#[test]
#[ignore = "manual release-mode benchmark; reports reconstruction only, not stack throughput"]
fn benchmark_recycled_collapse() {
    for threads in [1, 4] {
        rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build()
            .unwrap()
            .install(|| {
                for (w, h) in [(1024, 768), (3516, 2344)] {
                    let p = varied_pyramid(w, h, 7);
                    let mut old_ws = Workspace::new(p.sizes());
                    let mut new_ws = Workspace::new(p.sizes());
                    let expected = old_collapse(&p, &mut old_ws);
                    bits_equal(&expected, &p.collapse(&mut new_ws));
                    for _ in 0..2 {
                        black_box(old_collapse(&p, &mut old_ws));
                        black_box(p.collapse(&mut new_ws));
                    }
                    let mut old = Vec::new();
                    let mut new = Vec::new();
                    // Alternate direction so warm-up/thermal drift does not
                    // systematically favor one implementation.
                    for round in 0..10 {
                        for slot in 0..2 {
                            let is_old = (round + slot) % 2 == 0;
                            let start = Instant::now();
                            if is_old {
                                black_box(old_collapse(&p, &mut old_ws));
                                old.push(start.elapsed().as_secs_f64() * 1000.0);
                            } else {
                                black_box(p.collapse(&mut new_ws));
                                new.push(start.elapsed().as_secs_f64() * 1000.0);
                            }
                        }
                    }
                    println!(
                        "COLLAPSE_BENCH threads={threads} width={w} height={h} old_ms={old:?} new_ms={new:?}"
                    );
                }
            });
    }
}
