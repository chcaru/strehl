"""Prototype (grounding experiment, not a product change): let highlight fusion take its exposure
ratio from the hand-over sites when the patch fit cannot run.

Applied to a worktree of origin/main; default behaviour is unchanged. With
STREHL_HIGHLIGHT_RATIO=handover a pair whose patch fit is refused is fitted from the sites where
the base's green is at 0.50 to 0.75 of the pin and nothing near is brighter: the median of
(start x companion / base) there, bounded to 0.25 EV, with two interleaved halves required to
agree within 1 %.

  python patch-fusion.py <worktree>
"""
import pathlib
import sys

path = pathlib.Path(sys.argv[1]) / 'crates/strehl-cli/src/highlight-fusion.rs'
text = path.read_text(encoding='utf-8')
assert 'fit_handover' not in text, 'already patched'


def swap(old, new):
    global text
    assert text.count(old) == 1, (text.count(old), old[:60])
    text = text.replace(old, new)


# 1. The hand-over samples become a function both fits can use.
swap('''    let k = f64::from(gain_b);
    // The hand-over: where the base is high but below the ramp, the scaled
    // companion must read what the base reads.
    let (b_lo, b_hi) = (0.50 * full, RAMP_LO * full);
    let rows: Vec<Vec<f32>> = (8..h.saturating_sub(8))
''', '''    let k = f64::from(gain_b);
    let handover = handover_samples(base, companion, bright, maps, k, black, full);
    let handover = (handover.len() >= 50).then(|| {
        let q = |p| f64::from(percentile(&handover, p));
        (q(0.5), 0.7413 * (q(0.75) - q(0.25)), handover.len())
    });
    Ok(PairFit {
        k,
        start,
        commanded,
        correction_ev: f64::from(correction_ev),
        patches: (fit_patches, validation_patches, textured),
        validation,
        handover,
    })
}

/// The hand-over: where the base is high but below the ramp, the scaled
/// companion must read what the base reads. `k` x companion / base, green.
fn handover_samples(
    base: &Assembled<'_>,
    companion: &Assembled<'_>,
    bright: &Bright,
    maps: &[PointMap; 3],
    k: f64,
    black: f32,
    full: f32,
) -> Vec<f32> {
    let lo = (black + RAMP_LO * full) as u16;
    let (w, h) = (bright.w, bright.h);
    let (b_lo, b_hi) = (0.50 * full, RAMP_LO * full);
    let rows: Vec<Vec<f32>> = (8..h.saturating_sub(8))
''')
swap('''        .collect();
    let handover: Vec<f32> = rows.into_iter().flatten().collect();
    let handover = (handover.len() >= 50).then(|| {
        let q = |p| f64::from(percentile(&handover, p));
        (q(0.5), 0.7413 * (q(0.75) - q(0.25)), handover.len())
    });
    Ok(PairFit {
        k,
        start,
        commanded,
        correction_ev: f64::from(correction_ev),
        patches: (fit_patches, validation_patches, textured),
        validation,
        handover,
    })
}
''', '''        .collect();
    rows.into_iter().flatten().collect()
}

/// PROTOTYPE (capture-planning-flow grounding, 2026-11-27): `STREHL_HIGHLIGHT_RATIO=handover`.
pub const RATIO_ENV: &str = "STREHL_HIGHLIGHT_RATIO";

fn handover_mode() -> bool {
    std::env::var(RATIO_ENV).is_ok_and(|v| v.trim() == "handover")
}

/// The ratio from the hand-over sites alone, for a pair the patch fit cannot
/// measure (a dark subject under a deep highlight group has no 64-photosite
/// patch well exposed in both). Bounded as the patch fit is; two interleaved
/// halves of the sites must agree within 1 %.
fn fit_handover(
    base: &Assembled<'_>,
    companion: &Assembled<'_>,
    bright: &Bright,
    maps: &[PointMap; 3],
    start: f64,
    commanded: bool,
    black: f32,
    full: f32,
) -> std::result::Result<PairFit, String> {
    const MIN_SITES: usize = 400;
    let samples = handover_samples(base, companion, bright, maps, start, black, full);
    let samples: Vec<f32> = samples.into_iter().filter(|v| v.is_finite() && *v > 0.0).collect();
    if samples.len() < MIN_SITES {
        return Err(format!(
            "only {} hand-over sites (need {MIN_SITES})",
            samples.len()
        ));
    }
    let median = f64::from(percentile(&samples, 0.5));
    let correction_ev = -median.log2();
    if correction_ev.abs() > f64::from(CORRECTION_LIMIT_EV) {
        return Err(format!(
            "the hand-over sites read {median:.3} of the start: a correction of {correction_ev:+.3} EV, \\
             beyond the {CORRECTION_LIMIT_EV} EV bound"
        ));
    }
    let even: Vec<f32> = samples.iter().copied().step_by(2).collect();
    let odd: Vec<f32> = samples.iter().copied().skip(1).step_by(2).collect();
    let split = (f64::from(percentile(&even, 0.5)) / f64::from(percentile(&odd, 0.5)) - 1.0).abs();
    if split > f64::from(MEDIAN_LIMIT) {
        return Err(format!(
            "two halves of the hand-over sites disagree by {:.2} %",
            100.0 * split
        ));
    }
    let k = start / median;
    let q = |p| f64::from(percentile(&samples, p)) / median;
    Ok(PairFit {
        k,
        start,
        commanded,
        correction_ev,
        patches: (0, 0, 0),
        validation: [split as f32, 0.0, 0.0],
        handover: Some((q(0.5), 0.7413 * (q(0.75) - q(0.25)), samples.len())),
    })
}
''')
# 2. The caller: fall back when the patch fit is refused.
swap('''                start,
                commanded,
                black,
                full,
            );
            pair_fits()''', '''                start,
                commanded,
                black,
                full,
            );
            let f = match f {
                Err(why) if handover_mode() => fit_handover(
                    &base,
                    &comp,
                    bright.as_ref().expect("measured for the fit"),
                    &maps,
                    start,
                    commanded,
                    black,
                    full,
                )
                .map_err(|e| format!("{why}; and by the hand-over sites: {e}")),
                other => other,
            };
            pair_fits()''')
path.write_text(text, encoding='utf-8', newline='\n')
print('patched', path)
