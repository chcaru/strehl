"""Clear the five clippy lints on the M96 instrument, and add its test module.

Each replacement is anchored on a unique full string and the script hard-errors
if an anchor does not match exactly once, so a silent miss cannot happen
(discipline: a green control is a claim about the instrument).
"""

import pathlib

P = pathlib.Path("crates/strehl-cli/examples/m96-election-margin.rs")
s = P.read_text(encoding="utf-8")

EDITS = [
    (
        """        for x in 0..=r.min(w - 1) {
            acc += f64::from(row[x]);
        }""",
        """        for v in row.iter().take(r.min(w - 1) + 1) {
            acc += f64::from(*v);
        }""",
    ),
    (
        """            for i in 0..px {
                let d = (f64::from(vol.reg[k - 2][i]) - 4.0 * f64::from(vol.reg[k - 1][i])
                    + 6.0 * f64::from(vol.reg[k][i])
                    - 4.0 * f64::from(vol.reg[k + 1][i])
                    + f64::from(vol.reg[k + 2][i]))
                    / 6.0;
                d4_sq[i] += d * d;
            }""",
        """            for (i, acc) in d4_sq.iter_mut().enumerate() {
                let d = (f64::from(vol.reg[k - 2][i]) - 4.0 * f64::from(vol.reg[k - 1][i])
                    + 6.0 * f64::from(vol.reg[k][i])
                    - 4.0 * f64::from(vol.reg[k + 1][i])
                    + f64::from(vol.reg[k + 2][i]))
                    / 6.0;
                *acc += d * d;
            }""",
    ),
    (
        """    let label = args
        .tag
        .is_empty()
        .then(|| {
            dir.file_name()
                .map(|s| s.to_string_lossy().to_string())
                .unwrap_or_else(|| "stack".into())
        })
        .unwrap_or_else(|| args.tag.clone());""",
        """    let label = if args.tag.is_empty() {
        dir.file_name()
            .map(|s| s.to_string_lossy().to_string())
            .unwrap_or_else(|| "stack".into())
    } else {
        args.tag.clone()
    };""",
    ),
    (
        """        let mut rho_map = vec![0.0f32; px];
        for i in 0..px {
            let w = i32::from(e.win_idx[i]);
            let a = (i32::from(e.hi[SHIPPED][i]) - w).abs();
            let b = (w - i32::from(e.lo[SHIPPED][i])).abs();
            rho_map[i] = a.max(b) as f32 / (vol.frames() - 1).max(1) as f32;
        }""",
        """        let mut rho_map = vec![0.0f32; px];
        for (i, m) in rho_map.iter_mut().enumerate() {
            let w = i32::from(e.win_idx[i]);
            let a = (i32::from(e.hi[SHIPPED][i]) - w).abs();
            let b = (w - i32::from(e.lo[SHIPPED][i])).abs();
            *m = a.max(b) as f32 / (vol.frames() - 1).max(1) as f32;
        }""",
    ),
    (
        """        let mut qmap = vec![0.0f32; px];
        for i in 0..px {
            let den = e.win_val[i] - e.min_val[i];
            qmap[i] = if e.far[D8][i].is_finite() && den > 0.0 {
                (e.win_val[i] - e.far[D8][i]) / den
            } else {
                0.0
            };
        }""",
        """        let mut qmap = vec![0.0f32; px];
        for (i, m) in qmap.iter_mut().enumerate() {
            let den = e.win_val[i] - e.min_val[i];
            *m = if e.far[D8][i].is_finite() && den > 0.0 {
                (e.win_val[i] - e.far[D8][i]) / den
            } else {
                0.0
            };
        }""",
    ),
]

for old, new in EDITS:
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"anchor matched {n} times, refusing:\n{old[:90]}")
    s = s.replace(old, new)

TESTS = r'''

#[cfg(test)]
mod tests {
    use super::*;

    /// A hand-built through-focus fibre with a known answer, so the definitions
    /// are checked against arithmetic rather than against themselves.
    fn fibre() -> Vec<f32> {
        // peak at k = 3; a decoy at k = 8 that is close but strictly lower.
        vec![0.10, 0.20, 0.60, 1.00, 0.55, 0.18, 0.12, 0.30, 0.95, 0.25]
    }

    fn m_d(v: &[f32], d: usize) -> Option<f32> {
        let kw = (0..v.len()).max_by(|&a, &b| v[a].partial_cmp(&v[b]).unwrap())?;
        let far = (0..v.len())
            .filter(|&k| k.abs_diff(kw) >= d)
            .map(|k| v[k])
            .fold(f32::NEG_INFINITY, f32::max);
        far.is_finite().then(|| v[kw] - far)
    }

    #[test]
    fn the_trivial_placebo_is_exactly_zero_and_the_ladder_is_monotone() {
        // N4: `d = 0` includes the winner itself, so the margin must be 0 -- not
        // "small", exactly 0. Anything else means the far-set is mis-masked.
        let v = fibre();
        assert_eq!(m_d(&v, 0), Some(0.0));
        // Widening `d` can only remove rivals, so `m_d` is non-decreasing. This
        // is the property the report leans on when it reads the distance ladder.
        let mut prev = f32::NEG_INFINITY;
        for d in 0..v.len() {
            let m = m_d(&v, d).unwrap_or(f32::INFINITY);
            assert!(m >= prev, "m_{d} = {m} < previous {prev}");
            prev = m;
        }
        // The decoy at k = 8 is 5 away from the peak at k = 3, so it is the
        // binding rival at every d <= 5 and vanishes at d = 6.
        assert!((m_d(&v, 1).unwrap() - (1.00 - 0.95)).abs() < 1e-6);
        assert!((m_d(&v, 5).unwrap() - (1.00 - 0.95)).abs() < 1e-6);
        assert!((m_d(&v, 6).unwrap() - (1.00 - 0.20)).abs() < 1e-6);
    }

    /// The measured headline is that `m_1` cannot tell a focus stack from a
    /// shuffled one. That is not an empirical accident, it is algebra: `m_1` is
    /// the gap between the first and second order statistics of the per-pixel
    /// multiset, and permuting the frame axis does not change a multiset.
    #[test]
    fn the_naive_top_two_margin_is_invariant_to_any_frame_permutation() {
        let v = fibre();
        let mut rng = Rng::new(0xC0FF_EE01);
        for _ in 0..64 {
            let mut p = v.clone();
            for i in (1..p.len()).rev() {
                let j = rng.below((i + 1) as u64) as usize;
                p.swap(i, j);
            }
            assert_eq!(m_d(&p, 0), m_d(&v, 0));
            assert_eq!(m_d(&p, 1), m_d(&v, 1));
        }
    }

    /// Power for the test above: the same permutation must move `m_8`, or the
    /// invariance result is vacuous (discipline 594, applied to a unit test).
    #[test]
    fn but_the_distance_ladder_is_not_invariant() {
        let v: Vec<f32> = (0..40).map(|k| 1.0 - (f32::from(k) - 17.0).abs() / 40.0).collect();
        let mut rng = Rng::new(0xC0FF_EE02);
        let mut moved = 0;
        for _ in 0..64 {
            let mut p = v.clone();
            for i in (1..p.len()).rev() {
                let j = rng.below((i + 1) as u64) as usize;
                p.swap(i, j);
            }
            if m_d(&p, 8) != m_d(&v, 8) {
                moved += 1;
            }
        }
        assert!(moved > 32, "m_8 moved in only {moved} of 64 shuffles");
    }

    /// The mirror's comparator must be `FocusStats::beats`, and `--invert-tiebreak`
    /// must actually differ from it -- otherwise `F3` could never fail.
    #[test]
    fn the_tiebreak_plant_really_inverts_the_shipped_rule() {
        assert!(beats(1.0, 5, 0.5, 3, false));
        assert!(beats(1.0, 5, 0.5, 3, true));
        assert!(beats(0.5, 2, 0.5, 7, false), "shipped rule: lower index wins ties");
        assert!(!beats(0.5, 2, 0.5, 7, true), "inverted rule must disagree on ties");
        assert!(!beats(0.5, 9, 0.5, 7, false));
        assert!(beats(0.5, 9, 0.5, 7, true));
    }

    /// `box_mean` is the plant's blur ladder and the detail axis's window, so a
    /// bug in it would corrupt both the positive control and B4. Its mean over a
    /// constant field must be that constant, exactly, including at the borders.
    #[test]
    fn the_box_mean_preserves_a_constant_field_everywhere() {
        let geom = PlaneGeometry::from_active(64, 64);
        let px = geom.pixels();
        let src = vec![7.25f32; px];
        let mut scratch = vec![0.0f32; px];
        let mut dst = vec![0.0f32; px];
        for r in [1usize, 3, 8] {
            box_mean(&src, geom, r, &mut scratch, &mut dst);
            for (i, v) in dst.iter().enumerate() {
                assert!((v - 7.25).abs() < 1e-4, "r={r} i={i} v={v}");
            }
        }
    }
}
'''

if "#[cfg(test)]" in s:
    raise SystemExit("test module already present, refusing to double-append")
s = s.rstrip("\n") + "\n" + TESTS.lstrip("\n")

P.write_text(s, encoding="utf-8", newline="")
print("cleared 5 lints, appended test module")
