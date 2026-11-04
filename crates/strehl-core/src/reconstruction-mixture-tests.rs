//! Data-dependent hull acceptance is explicitly separated from pre-admission h²v.
use super::*;
#[test]
fn a05_flat_antithetic_monte_carlo_exercises_coherent_hull_fallback_mean() {
    let pn = noise(0.25, 8.);
    let scene = |_| [256.; 3];
    let maps: Vec<_> = grid(4)
        .into_iter()
        .map(|mut t| {
            t.b.re = -t.b.re;
            t.b.im = -t.b.im;
            [t; 3]
        })
        .collect();
    let fields = Fields::new(1);
    let mut accepted = 0usize;
    let mut rejected = 0usize;
    let mut hull = 0usize;
    let mut sums = [0f64; 3];
    let mut count = 0usize;
    let mut asymmetric_pairs = 0;
    // This deliberately raises only the *test's* constant-relative variance
    // ceiling to expose hull mixtures under one-sided support. Production's
    // default1.25 ceiling has a separate actual-CFA negative control.
    let config = Config {
        model: RegressionModel::LocalAffine,
        sigma_sensor: 1.,
        max_variance_ratio: 100.,
        ..Config::default()
    };
    for origin in [[1.25; 2], [0.25; 2], [-0.25; 2]] {
        let l = OutputLattice {
            width: 1,
            height: 1,
            origin_sensor: origin,
            ..default_lattice()
        };
        let guide = Guide::new(l, &scene, [256.; 3]);
        for seed in 0..128 {
            let mut raws: Vec<_> = maps
                .iter()
                .enumerate()
                .map(|(i, t)| {
                    raw(
                        l.full,
                        *t,
                        1.,
                        &scene,
                        pn,
                        Some((seed * 137 + i * 977 + 31991) as u64),
                        65535,
                    )
                })
                .collect();
            let mut admissions = [false; 2];
            for (sign, admission) in admissions.iter_mut().enumerate() {
                if sign == 1 {
                    for r in &mut raws {
                        for y in 0..2 * r.geom.height {
                            for x in 0..2 * r.geom.width {
                                let i = (r.oy + y) * r.stride + r.ox + x;
                                r.data[i] = (1536_i32 - i32::from(r.data[i])) as u16;
                            }
                        }
                    }
                }
                let views = views(&raws, &maps, &vec![1.; maps.len()], pn, &fields);
                let result = reconstruct_tile(l, &views, guide.view(), config).unwrap();
                let coherent = result.reason[0].iter().all(|r| *r == Reason::Reconstructed);
                *admission = coherent;
                hull += usize::from(result.reason[0].contains(&Reason::KernelOvershoot));
                accepted += usize::from(coherent);
                rejected += usize::from(!coherent);
                for (c, sum) in sums.iter_mut().enumerate() {
                    *sum += if coherent {
                        f64::from(result.rgb[0][c])
                    } else {
                        256.
                    };
                }
                count += 1;
            }
            asymmetric_pairs += usize::from(admissions[0] != admissions[1]);
        }
    }
    eprintln!(
        "flat coherent hull mixture: accepted{accepted}, native fallback{rejected}, hull-triggered{hull}, antithetic asymmetric pairs{asymmetric_pairs}, means{:?}; no mixture-variance claim",
        sums.map(|v| v / count as f64)
    );
    assert!(
        accepted > 0 && rejected > 0 && hull > 0,
        "fixture did not exercise both coherent output arms"
    );
    assert!(
        asymmetric_pairs <= 3,
        "unexpected numerical asymmetry in flat hull gate"
    );
    for sum in sums {
        assert!((sum / count as f64 - 256.).abs() < 0.03);
    }
}
