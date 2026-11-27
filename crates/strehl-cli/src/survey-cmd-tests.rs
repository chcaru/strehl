//! Synthetic checks of `strehl survey`'s arithmetic: frames built with known
//! ratios, bodies and glints.

use super::*;
use strehl_core::noise::Levels;

const BLACK: f32 = 512.0;
const WHITE: f32 = 16383.0;
const W: usize = 256;
const H: usize = 192;

fn view(data: &[u16]) -> CfaView<'_> {
    CfaView {
        data,
        stride: W,
        x0: 0,
        y0: 0,
        width: W,
        height: H,
        black: BLACK,
        white: WHITE,
    }
}

/// A smooth body between 0.10 and 0.30 of full scale (long), with texture.
fn body_share(x: usize, y: usize) -> f64 {
    let t = ((x * 7919 + y * 104_729) % 97) as f64 / 97.0;
    0.10 + 0.15 * (x as f64 / W as f64) + 0.05 * t
}

fn dn(share: f64) -> u16 {
    (f64::from(BLACK) + share * f64::from(WHITE - BLACK))
        .round()
        .clamp(0.0, f64::from(WHITE)) as u16
}

/// Long and short frames: `glints` at `glint` times the long full scale.
fn frames(ratio: f64, glints: &[(usize, usize)], glint: f64) -> (Vec<u16>, Vec<u16>) {
    let mut long = vec![0u16; W * H];
    let mut short = vec![0u16; W * H];
    for y in 0..H {
        for x in 0..W {
            let r = if glints.contains(&(x, y)) {
                glint
            } else {
                body_share(x, y)
            };
            long[y * W + x] = dn(r);
            short[y * W + x] = dn(r * ratio);
        }
    }
    (long, short)
}

fn noise() -> NoiseModel {
    profile::noise_model_for(
        "synthetic",
        Some(100.0),
        Levels {
            black: BLACK,
            white: WHITE,
        },
    )
}

const LONG: u64 = 0x10004; // 1/4
const SHORT: u64 = 0x1003c; // 1/60

fn pair(focus: u64, long: &[u16], short: &[u16], ratio_hint: f64) -> PairResult {
    let mask = SiteMask::all([W, H]);
    let (vl, vs) = (view(long), view(short));
    let lp = long_pass(&vl, &mask);
    let n = noise();
    let var = |c: usize, s: f32| n.variance(plane_of(c), s);
    let ratio = measure_ratio(&vl, &vs, &var);
    let used = ratio.ratio.unwrap_or(ratio_hint);
    let v: Vec<(f64, u64)> = {
        let mut v = as_values(&lp.hist[1], BLACK, WHITE - BLACK, 1.0);
        v.sort_by(|a, b| a.0.total_cmp(&b.0));
        v
    };
    let p99 = weighted_percentile(&v, 0.99).unwrap();
    let sigma = |c: usize, s: f32| n.sigma(plane_of(c), s);
    let cut = set_aside_cut([p99 * f64::from(WHITE - BLACK); 3], used, &sigma);
    let pass = pair_pass(&vl, &vs, &mask, used, cut);
    PairResult {
        focus,
        long_code: LONG,
        short_code: SHORT,
        ratio,
        used,
        pass,
        long_hist: lp.hist,
        pinned_long: lp.pinned,
        noise: n,
    }
}

#[test]
fn shutter_codes() {
    assert_eq!(code_seconds(0x10004), Some(0.25));
    assert_eq!(code_seconds(851_978), Some(1.3));
    assert_eq!(code_seconds(0), None);
    assert_eq!(code_seconds(0xffff_ffff), None);
    assert_eq!(effective_seconds(1.0 / 60.0), 1.0 / 64.0);
    assert!((effective_seconds(1.3) - 2f64.powf(1.0 / 3.0)).abs() < 1e-12);
    assert!((effective_seconds(1.0 / 3.0) - 2f64.powf(-5.0 / 3.0)).abs() < 1e-12);
    assert_eq!(effective_seconds(0.25), 0.25);
    assert_eq!(code_label(0x1003c), "1/60");
    assert_eq!(code_label(851_978), "1.3");
    let offered = [0x1003c, 0x10004, 851_978, 655_370, 0x10028, 0];
    assert_eq!(nearest_code(&offered, 1.2), Some(851_978));
    assert_eq!(nearest_code(&offered, 0.26), Some(0x10004));
    assert_eq!(longest_within(&offered, 1.2), Some(655_370));
    assert_eq!(longest_within(&offered, 0.25), Some(0x10004));
    assert_eq!(longest_within(&offered, 0.001), None);
    assert_eq!(nearest_code(&[], 1.0), None);
}

/// The ratio is measured from the frames, not taken from the codes: a
/// light 3 % dimmer in the short frame reads as such.
#[test]
fn ratio_is_measured() {
    let true_ratio = 0.0625 * 0.97;
    let (long, short) = frames(true_ratio, &[], 0.0);
    let n = noise();
    let var = |c: usize, s: f32| n.variance(plane_of(c), s);
    let m = measure_ratio(&view(&long), &view(&short), &var);
    let r = m.ratio.unwrap();
    assert!((r / true_ratio - 1.0).abs() < 0.01, "{r} vs {true_ratio}");
    assert!(m.cells >= crate::exposure_ratio::MIN_CELLS);
    for c in m.per_colour {
        assert!((c.unwrap() / true_ratio - 1.0).abs() < 0.01);
    }
    // A flat dark frame gives no measurement.
    let dark = vec![BLACK as u16; W * H];
    assert_eq!(measure_ratio(&view(&dark), &view(&dark), &var).ratio, None);
}

/// Glints at 3x the long full scale: pinned in the long frame, read from
/// the short one, set aside from the body; the advice follows.
#[test]
fn census_of_glints() {
    let glints = [(40, 40), (41, 40), (100, 120), (200, 60), (201, 61)];
    let ratio = 0.0625;
    let (long, short) = frames(ratio, &glints, 3.0);
    let p = pair(25_000, &long, &short, ratio);
    assert_eq!(p.pinned_long, glints.len() as u64);
    let offered = [
        0x10004u64, 393_226, 851_978, 655_370, 0x10028, 0x1001e, 0x1003c, 0x100fa,
    ];
    let r = census(&[p], (BLACK, WHITE), LONG, &offered).unwrap();
    // The body excludes the glints (and their two-pixel surround) and tops
    // out near the scene's 0.30.
    assert!(r.body.top < 0.31 && r.body.top > 0.25, "{}", r.body.top);
    assert!(r.body.set_aside_sites >= glints.len() as u64);
    assert!(r.body.set_aside_sites <= 25 * glints.len() as u64);
    // The census top is the glint, within the short frame's quantisation.
    assert!((r.census.top - 3.0).abs() < 0.02, "{}", r.census.top);
    assert_eq!(r.census.highlight_sites, glints.len() as u64);
    assert!(r.census.highlights);
    assert_eq!(r.census.pinned_short_sites, 0);
    assert_eq!(
        r.census.pinned_long_per_position[0].predicted,
        glints.len() as u64
    );
    assert!((r.ratio.measured.unwrap() / ratio - 1.0).abs() < 0.01);
    assert!((r.ratio.commanded - 1.0 / 16.0).abs() < 1e-12);
    assert!((r.ratio.commanded_marked - 1.0 / 15.0).abs() < 1e-12);
    let a = &r.advice;
    assert_eq!(a.suggested, "highlight_pass");
    assert!((a.highlight_pass.base_s - 0.25 * 0.8 / r.body.top).abs() < 1e-9);
    assert!((a.highlight_pass.short_s - 0.25 * 0.8 / (2.0 * r.census.top)).abs() < 1e-9);
    assert!((a.protect.s - 0.25 / (2.0 * r.census.top)).abs() < 1e-9);
    // Protection never exceeds its time; accept pins every glint.
    let pc = a.protect.code.unwrap();
    assert!(code_effective(pc).unwrap() <= a.protect.s);
    assert_eq!(a.accept.code, a.highlight_pass.base_code);
    assert!((a.accept.pinned_sites_per_plane - glints.len() as f64).abs() < 1e-9);
}

/// A body without highlights reports none and suggests one exposure.
#[test]
fn no_highlights() {
    let (long, short) = frames(0.0625, &[], 0.0);
    let p = pair(25_000, &long, &short, 0.0625);
    let r = census(&[p], (BLACK, WHITE), LONG, &[]).unwrap();
    assert_eq!(r.census.highlight_sites, 0);
    assert!(!r.census.highlights);
    assert_eq!(r.census.pinned_long_per_position[0].pinned, 0);
    assert_eq!(r.advice.suggested, "accept");
    assert_eq!(r.advice.accept.code, None);
    assert_eq!(r.advice.accept.pinned_sites_per_plane, 0.0);
    // The top of the census is the body's own top.
    assert!(r.census.top < 2.0 * r.body.top);
}

/// A body near black (a backdrop) is noise against its own percentiles: it
/// is neither set aside nor counted as highlights, and one exposure is
/// suggested.
#[test]
fn dark_body_has_no_highlights() {
    let n = noise();
    let s0 = f64::from(n.sigma(CfaPlane::G1, 0.0));
    // Bounded noise: the sum of four uniforms, at most two deviations.
    let wobble = |i: usize, salt: usize| -> f64 {
        (0..4)
            .map(|k| ((i * 2_654_435_761 + (k + salt) * 40_503) % 1000) as f64 / 1000.0 - 0.5)
            .sum::<f64>()
            * s0
    };
    let level = f64::from(WHITE - BLACK) * 0.0005;
    let mut long = vec![0u16; W * H];
    let mut short = vec![0u16; W * H];
    for (i, (l, s)) in long.iter_mut().zip(short.iter_mut()).enumerate() {
        *l = (f64::from(BLACK) + level + wobble(i, 1)).round() as u16;
        *s = (f64::from(BLACK) + level * 0.0625 + wobble(i, 7)).round() as u16;
    }
    let p = pair(25_000, &long, &short, 0.0625);
    assert!(p.ratio.ratio.is_none(), "nothing is well exposed in both");
    let r = census(&[p], (BLACK, WHITE), LONG, &[]).unwrap();
    assert!(
        r.body.set_aside_sites < (W * H / 100) as u64,
        "{} set aside",
        r.body.set_aside_sites
    );
    assert_eq!(r.census.highlight_sites, 0);
    assert_eq!(r.advice.suggested, "accept");
    // Accepting at a long exposure extrapolates the long frame, not the
    // short frame's noise: nothing pins.
    assert_eq!(r.advice.accept.pinned_sites_per_plane, 0.0);
}

/// Hot pixels add the same DN to both frames: bright in the short frame
/// against its ratio, they do not scale with exposure, and the long frame
/// does not confirm them.
#[test]
fn fixed_pattern_is_not_radiance() {
    let hot = [(30usize, 30usize), (150, 100), (220, 170)];
    let (mut long, mut short) = frames(0.0625, &[], 0.0);
    for &(x, y) in &hot {
        long[y * W + x] += 600;
        short[y * W + x] += 600;
    }
    let p = pair(25_000, &long, &short, 0.0625);
    assert!(p.pass.unconfirmed >= hot.len() as u64);
    let r = census(&[p], (BLACK, WHITE), LONG, &[]).unwrap();
    assert_eq!(r.census.highlight_sites, 0);
    assert!(!r.census.highlights);
    assert!(r.census.top < 0.31, "{}", r.census.top);
    assert_eq!(r.advice.suggested, "accept");
}

/// Pooled statistics do not depend on the order of the pairs.
#[test]
fn census_is_order_free() {
    let (l1, s1) = frames(0.0625, &[(10, 10)], 2.0);
    let (l2, s2) = frames(0.0600, &[(90, 90), (91, 90)], 4.0);
    let a = pair(100, &l1, &s1, 0.0625);
    let b = pair(200, &l2, &s2, 0.06);
    let ab = census(&[a.clone(), b.clone()], (BLACK, WHITE), LONG, &[]).unwrap();
    let ba = census(&[b, a], (BLACK, WHITE), LONG, &[]).unwrap();
    assert_eq!(ab.body, ba.body);
    assert_eq!(ab.census.tails, ba.census.tails);
    assert_eq!(ab.census.highlight_sites, ba.census.highlight_sites);
    assert_eq!(ab.advice, ba.advice);
    assert!((ab.census.top - 4.0).abs() < 0.03, "{}", ab.census.top);
}

fn shot(focus: u64, shutter: u64, order: usize) -> Shot {
    Shot {
        plane: order as u64 + 1,
        focus,
        shutter,
        iso: Some(100),
        tier: "base".into(),
        path: PathBuf::from(format!("frame-{order}.ARW")),
        order,
    }
}

/// Pairs, long frames and the dense cluster, whatever order the journal
/// lists them in; a retake replaces the earlier shot.
#[test]
fn classify_survey() {
    let mut all = Vec::new();
    for (k, f) in [24_000u64, 24_400, 24_800, 25_200].into_iter().enumerate() {
        all.push(shot(f, LONG, 2 * k));
        all.push(shot(f, SHORT, 2 * k + 1));
    }
    for k in 0..6 {
        all.push(shot(24_500 + 8 * k, LONG, 20 + k as usize));
    }
    all.push(shot(24_400, SHORT, 40)); // a retake
    // Long-only positions elsewhere in the range are not the cluster.
    all.push(shot(23_000, LONG, 41));
    all.push(shot(26_000, LONG, 42));
    // A later long shot at a pair's focus: the pair keeps the long shot
    // taken next to its short one.
    all.push(shot(24_800, LONG, 50));
    let plan = classify(&all).unwrap();
    assert_eq!(plan.pairs[2].0.order, 4);
    assert_eq!(plan.long_code, LONG);
    assert_eq!(plan.short_code, Some(SHORT));
    assert_eq!(plan.pairs.len(), 4);
    assert_eq!(plan.pairs[1].1.order, 40);
    assert_eq!(plan.longs.len(), 12);
    assert!(plan.dense_is_cluster);
    assert_eq!(
        plan.dense.iter().map(|s| s.focus).collect::<Vec<_>>(),
        (0..6).map(|k| 24_500 + 8 * k).collect::<Vec<u64>>()
    );
    let mut reversed = all.clone();
    reversed.reverse();
    assert_eq!(classify(&reversed).unwrap(), plan);
    let mut rotated = all.clone();
    rotated.rotate_left(5);
    assert_eq!(classify(&rotated).unwrap(), plan);
    // Without a dense cluster the step uses every long position.
    let pairs_only: Vec<Shot> = all.iter().filter(|s| s.order < 8).cloned().collect();
    let p = classify(&pairs_only).unwrap();
    assert!(!p.dense_is_cluster);
    assert_eq!(p.dense.len(), 4);
}

#[test]
fn spread_keeps_the_ends() {
    let shots: Vec<Shot> = (0..30)
        .map(|k| shot(1000 + 10 * k, LONG, k as usize))
        .collect();
    let s = spread(&shots, 7);
    assert_eq!(s.len(), 7);
    assert_eq!(s[0].focus, 1000);
    assert_eq!(s[6].focus, 1290);
    assert_eq!(spread(&shots[..5], 7).len(), 5);
}

/// The outline scales about the centre with focus by its rate.
#[test]
fn outline_maps_with_focus() {
    let o = Outline {
        rings: vec![vec![[0.25, 0.25], [0.75, 0.25], [0.75, 0.75], [0.25, 0.75]]],
        reference_focus: Some(1000.0),
        ppm_per_unit: Some(-100.0),
    };
    let size = [800, 800];
    let at_ref = o.mask_at(1000.0, size).count();
    let nearer = o.mask_at(0.0, size).count(); // scale exp(0.1)
    let farther = o.mask_at(2000.0, size).count();
    assert_eq!(at_ref, 50 * 50);
    assert!(nearer > at_ref && farther < at_ref);
    let r = (nearer as f64 / at_ref as f64).sqrt();
    assert!((r - 0.1f64.exp()).abs() < 0.03, "{r}");
    // A manifest's plan.subject is read; the host's `rate_ppm` too.
    let v = serde_json::json!({"plan": {"subject": {"rings": o.rings, "reference_focus": 1000, "rate_ppm": -13.0}}});
    let (got, _) = outline_from(&v).unwrap();
    assert_eq!(got.ppm_per_unit, Some(-13.0));
    assert_eq!(got.reference_focus, Some(1000.0));
    assert!(outline_from(&serde_json::json!({"plan": {}})).is_none());
}

/// The step's tile mask restricts the tiles measured.
#[test]
fn step_over_tiles() {
    let positions: Vec<f64> = (0..25).map(|k| 1000.0 + 8.0 * f64::from(k)).collect();
    let sigma = 60.0 / (2.0 * (2.0f64 * 2f64.ln()).sqrt());
    let energies: Vec<Vec<f64>> = positions
        .iter()
        .map(|&p| {
            (0..100)
                .map(|t| {
                    if t < 50 {
                        1.0 + 50.0 * (-(p - 1096.0).powi(2) / (2.0 * sigma * sigma)).exp()
                    } else {
                        1.0
                    }
                })
                .collect()
        })
        .collect();
    let all = step_from(&positions, &energies, &[true; 100], "test".into());
    assert_eq!(all.tiles, 50);
    assert!((all.width.unwrap() - 60.0).abs() < 2.0);
    assert_eq!(all.suggested_step, Some(8));
    let none: Vec<bool> = (0..100).map(|t| t >= 50).collect();
    let flat = step_from(&positions, &energies, &none, "test".into());
    assert_eq!(flat.tiles, 0);
    assert_eq!(flat.width, None);
}
