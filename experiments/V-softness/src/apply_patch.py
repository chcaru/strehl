"""Surgical restore of the noise-driven window shrink, in the PINNED copy only.

Restores ONLY the r_noise term deleted by 57e4554. Leaves from_silhouettes,
the may_collapse veto, FLOOR_Q, conf and regularise_guided exactly as 57e4554
left them. Both arms live in ONE binary behind V_RESTORE_SHRINK so no build
can drift underneath the comparison.
"""
import sys
from pathlib import Path

TREE = Path(r"C:\dev\strehl-out\V-shrink\tree")

def patch(relpath, anchor, replacement):
    p = TREE / relpath
    src = p.read_text(encoding="utf-8")
    n = src.count(anchor)
    if n != 1:
        sys.exit(f"ANCHOR NOT UNIQUE in {relpath}: found {n} occurrences of:\n{anchor!r}")
    p.write_text(src.replace(anchor, replacement, 1), encoding="utf-8")
    print(f"  patched {relpath}  (anchor matched exactly once)")

NEWFN = '''
    /// V-SOFTNESS: [`Self::from_silhouettes`] with the noise-driven window
    /// shrink restored, and nothing else changed.
    ///
    /// `radius(p) = min(r_noise(p), r_geom(p))`. The geometric cap, the
    /// `may_collapse` veto, `FLOOR_Q`, `conf` and `regularise_guided` are
    /// untouched, so this is the shrink term alone rather than a revert of
    /// 57e4554.
    #[must_use]
    pub fn from_silhouettes_shrink(
        excess: &[f32],
        guide: &[u16],
        may_collapse: &[bool],
        geom: PlaneGeometry,
        tau: f32,
        margin: f32,
    ) -> Self {
        assert_eq!(excess.len(), geom.pixels());
        assert_eq!(guide.len(), geom.pixels());
        assert_eq!(may_collapse.len(), geom.pixels());
        assert!(tau > 0.0, "tau must be positive, got {tau}");
        assert!(margin > 0.0, "margin must be positive, got {margin}");
        let px = geom.pixels();
        let mut scratch = vec![0.0f32; px];

        // --- r_noise: the smallest radius whose noise floor still resolves
        // this pixel's through-focus peak. Ascending, first hit wins.
        let sd_at = |r: usize| {
            crate::merge::FOCUS_NOISE_SD * (2 * WINDOW_RADIUS + 1) as f32 / (2 * r + 1) as f32
        };
        let need: Vec<f32> = LEVEL_RADII
            .iter()
            .map(|&r| margin * core::f32::consts::SQRT_2 * sd_at(r))
            .collect();
        let mut level = vec![FULL_LEVEL; px];
        for i in 0..px {
            for (l, n) in need.iter().enumerate() {
                if excess[i] >= *n {
                    level[i] = l as u8;
                    break;
                }
            }
        }

        // --- r_geom: identical to from_silhouettes, including the veto.
        let mut w: Vec<f32> = guide.iter().map(|&k| f32::from(k)).collect();
        let decided: Vec<f32> = w.iter().copied().filter(|v| *v < 65535.0).collect();
        let fill = if decided.is_empty() {
            0.0
        } else {
            decided.iter().sum::<f32>() / decided.len() as f32
        };
        for v in w.iter_mut() {
            if *v >= 65535.0 {
                *v = fill;
            }
        }
        let mut smooth = vec![0.0f32; px];
        box_mean(&w, geom, SPECKLE_RADIUS, &mut scratch, &mut smooth);

        let mut hi = smooth.clone();
        let mut lo = smooth;
        let mut capped = vec![false; px];
        let mut prev = 0usize;
        for (l, &r) in LEVEL_RADII.iter().enumerate() {
            box_extremum(&mut hi, geom, r - prev, &mut scratch, true);
            box_extremum(&mut lo, geom, r - prev, &mut scratch, false);
            prev = r;
            for i in 0..px {
                if !capped[i] && may_collapse[i] && hi[i] - lo[i] > tau {
                    capped[i] = true;
                    // .min() is the half 57e4554 removed with the term.
                    level[i] = level[i].min(l.saturating_sub(1) as u8);
                }
            }
        }
        Self { geom, level }
    }
'''

# 1. add the function immediately after from_silhouettes returns.
patch(
    "crates/strehl-core/src/edgeaware.rs",
    """                if !capped[i] && may_collapse[i] && hi[i] - lo[i] > tau {
                    capped[i] = true;
                    level[i] = l.saturating_sub(1) as u8;
                }
            }
        }
        Self { geom, level }
    }
""",
    """                if !capped[i] && may_collapse[i] && hi[i] - lo[i] > tau {
                    capped[i] = true;
                    level[i] = l.saturating_sub(1) as u8;
                }
            }
        }
        Self { geom, level }
    }
""" + NEWFN,
)

# 2. env-gated A/B at the single call site, inside run_estimator.
patch(
    "crates/strehl-cli/src/merge_cmd.rs",
    "            let scale = edgeaware::SelectionScale::from_silhouettes(&guide, &may, geom, tau);",
    """            let v_restore = std::env::var("V_RESTORE_SHRINK")
                .map(|v| v.trim() == "1")
                .unwrap_or(false);
            let scale = if v_restore {
                eprintln!(
                    "V-SOFTNESS      : ARM B -- noise-driven window shrink RESTORED, \\
                     margin {:.1} sigma; everything else as 57e4554 left it",
                    strehl_core::merge::DEFAULT_GATE
                );
                edgeaware::SelectionScale::from_silhouettes_shrink(
                    &excess,
                    &guide,
                    &may,
                    geom,
                    tau,
                    strehl_core::merge::DEFAULT_GATE,
                )
            } else {
                eprintln!("V-SOFTNESS      : ARM A -- shipped rule, no shrink");
                edgeaware::SelectionScale::from_silhouettes(&guide, &may, geom, tau)
            };""",
)
print("patch applied")
