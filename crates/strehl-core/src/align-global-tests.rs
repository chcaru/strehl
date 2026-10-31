use super::*;

const W: usize = 480;
const H: usize = 320;

fn hash(x: i64, y: i64, salt: u64) -> f64 {
    let mut h = (x as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15)
        ^ (y as u64).wrapping_mul(0xC2B2_AE3D_27D4_EB4F)
        ^ salt.wrapping_mul(0x1656_67B1_9E37_79F9);
    h ^= h >> 31;
    h = h.wrapping_mul(0xBF58_476D_1CE4_E5B9);
    h ^= h >> 29;
    (h >> 11) as f64 / (1u64 << 53) as f64
}

/// Smooth, aperiodic multi-octave value noise defined on the whole plane.
fn scene(x: f64, y: f64, salt: u64) -> f64 {
    let mut value = 0.0;
    for (octave, (spacing, weight)) in [(29.0, 1.0), (11.0, 0.6), (5.0, 0.35)]
        .into_iter()
        .enumerate()
    {
        let (u, v) = (x / spacing, y / spacing);
        let (i, j) = (u.floor() as i64, v.floor() as i64);
        let (fx, fy) = (u - i as f64, v - j as f64);
        let s = |t: f64| t * t * (3.0 - 2.0 * t);
        let salt = salt * 7 + octave as u64;
        let a = hash(i, j, salt) * (1.0 - s(fx)) + hash(i + 1, j, salt) * s(fx);
        let b = hash(i, j + 1, salt) * (1.0 - s(fx)) + hash(i + 1, j + 1, salt) * s(fx);
        value += weight * (a * (1.0 - s(fy)) + b * s(fy));
    }
    1000.0 * value
}

/// Render a plane whose centred pixel z shows the scene at `truth^-1(z)`,
/// so `truth` maps reference-centred to this plane's centred coordinates.
fn render(truth: Similarity, salt: u64, gain: f64, offset: f64) -> Vec<f32> {
    let inverse = truth.invert().unwrap();
    let centre = Cx::new(W as f64 * 0.5, H as f64 * 0.5);
    let mut data = vec![0.0f32; W * H];
    for y in 0..H {
        for x in 0..W {
            let p = inverse.apply(Cx::new(x as f64, y as f64) - centre);
            data[y * W + x] = (gain * scene(p.re, p.im, salt) + offset) as f32;
        }
    }
    data
}

fn plane(data: &[f32]) -> PlaneRef<'_> {
    PlaneRef::new(data, W, H).unwrap()
}

/// Close-up `scale` centred on reference point `x0`, rotated by `degrees`.
fn closeup(scale: f64, degrees: f64, x0: Cx) -> Similarity {
    let r = degrees.to_radians();
    let a = Cx::new(scale * r.cos(), scale * r.sin());
    Similarity { a, b: -(a * x0) }
}

/// Maximum disagreement in moving px over reference points near `x0`.
fn error(estimate: Similarity, truth: Similarity, x0: Cx, radius: f64) -> f64 {
    [
        (-1.0, -1.0),
        (1.0, -1.0),
        (-1.0, 1.0),
        (1.0, 1.0),
        (0.0, 0.0),
    ]
    .into_iter()
    .map(|(dx, dy)| {
        let p = x0 + Cx::new(dx * radius, dy * radius);
        (estimate.apply(p) - truth.apply(p)).abs()
    })
    .fold(0.0, f64::max)
}

fn best(reference: &[f32], moving: &[f32]) -> GlobalCandidate {
    let found = global_similarity_candidates(
        plane(reference),
        plane(moving),
        &GlobalSearchConfig::default(),
    );
    assert!(!found.is_empty(), "no candidate");
    assert!(found.windows(2).all(|w| w[0].ncc >= w[1].ncc));
    found[0]
}

#[test]
fn global_search_recovers_a_rotated_close_up_and_its_inverse() {
    let x0 = Cx::new(40.0, -20.0);
    let truth = closeup(2.6, 4.0, x0);
    let reference = render(Similarity::IDENTITY, 1, 1.0, 0.0);
    let moving = render(truth, 1, 1.0, 0.0);
    let found = best(&reference, &moving);
    assert!(found.ncc > 0.9, "ncc {}", found.ncc);
    assert!((found.transform.scale() / truth.scale() - 1.0).abs() < 0.03);
    assert!((found.transform.rotation() - truth.rotation()).abs() < 2f64.to_radians());
    let e = error(found.transform, truth, x0, 30.0);
    assert!(e < 8.0, "close-up error {e} moving px");

    // Reference is the close-up: the search must recover the inverse map.
    let inverse = truth.invert().unwrap();
    let found = best(&moving, &reference);
    assert!(found.ncc > 0.9, "ncc {}", found.ncc);
    let e = error(found.transform, inverse, Cx::new(0.0, 0.0), 60.0);
    assert!(e < 4.0, "inverse error {e} moving px");
}

#[test]
fn global_search_recovers_partial_overlap_translation_with_gain_change() {
    let truth = Similarity {
        a: Cx::new(
            1.18 * (-2f64).to_radians().cos(),
            1.18 * (-2f64).to_radians().sin(),
        ),
        b: Cx::new(-95.0, 48.0),
    };
    let reference = render(Similarity::IDENTITY, 2, 1.0, 0.0);
    let moving = render(truth, 2, 0.4, 50.0);
    let found = best(&reference, &moving);
    assert!(found.ncc > 0.9, "ncc {}", found.ncc);
    let centre_of_overlap = truth.invert().unwrap().apply(Cx::new(0.0, 0.0));
    let e = error(
        found.transform,
        truth,
        centre_of_overlap * Cx::real(0.5),
        50.0,
    );
    assert!(e < 4.0, "partial-overlap error {e} moving px");
}

#[test]
fn global_search_scores_an_unrelated_scene_far_below_a_true_pair() {
    let reference = render(Similarity::IDENTITY, 3, 1.0, 0.0);
    let related = render(closeup(1.5, 0.0, Cx::new(10.0, 10.0)), 3, 1.0, 0.0);
    let unrelated = render(Similarity::IDENTITY, 99, 1.0, 0.0);
    let true_ncc = best(&reference, &related).ncc;
    let false_ncc = best(&reference, &unrelated).ncc;
    assert!(true_ncc > 0.9, "true {true_ncc}");
    assert!(false_ncc < 0.6, "unrelated {false_ncc}");
}

#[test]
fn global_search_refuses_invalid_bounds_and_flat_planes() {
    let reference = render(Similarity::IDENTITY, 4, 1.0, 0.0);
    let flat = vec![100.0f32; W * H];
    assert!(
        global_similarity_candidates(
            plane(&reference),
            plane(&flat),
            &GlobalSearchConfig::default()
        )
        .is_empty()
    );
    let bad = GlobalSearchConfig {
        max_scale: 0.5,
        ..GlobalSearchConfig::default()
    };
    assert!(global_similarity_candidates(plane(&reference), plane(&reference), &bad).is_empty());
}

#[test]
fn fft_round_trip_and_circular_correlation_match_direct_sums() {
    let fft = Fft2::new(8, 4);
    let a: Vec<f64> = (0..32).map(|i| hash(i, 0, 5) - 0.5).collect();
    let b: Vec<f64> = (0..32).map(|i| hash(i, 1, 5) - 0.5).collect();
    let spectrum = |v: &[f64]| {
        let mut buffer: Vec<C> = v.iter().map(|&re| C { re, im: 0.0 }).collect();
        fft.forward(&mut buffer);
        buffer
    };
    let (sa, sb) = (spectrum(&a), spectrum(&b));
    let mut back = sa.clone();
    fft.inverse(&mut back);
    assert!(
        back.iter()
            .zip(&a)
            .all(|(x, y)| (x.re - y).abs() < 1e-12 && x.im.abs() < 1e-12)
    );
    let mut corr: Vec<C> = sa.iter().zip(&sb).map(|(x, y)| x.conj().mul(*y)).collect();
    fft.inverse(&mut corr);
    for dy in 0..4 {
        for dx in 0..8 {
            let mut direct = 0.0;
            for y in 0..4 {
                for x in 0..8 {
                    direct += a[y * 8 + x] * b[((y + dy) % 4) * 8 + (x + dx) % 8];
                }
            }
            assert!((corr[dy * 8 + dx].re - direct).abs() < 1e-12);
        }
    }
}
