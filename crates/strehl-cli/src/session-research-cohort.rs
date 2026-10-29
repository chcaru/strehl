//! Explicit original-acquisition exclusion for bounded conditional research.
//! This never changes the saved geometry or claims independent placement.
use anyhow::{Context, Result, ensure};
use std::collections::BTreeSet;
use std::ops::Range;

pub(super) struct Cohort {
    pub omitted: BTreeSet<usize>,
    pub retained: Vec<usize>,
    pub mask: Vec<bool>,
}
impl Cohort {
    pub fn new(total: usize, passes: &[Range<usize>], omitted: &[usize]) -> Result<Self> {
        let excluded: BTreeSet<_> = omitted.iter().copied().collect();
        ensure!(
            excluded.len() == omitted.len(),
            "duplicate omitted acquisition"
        );
        ensure!(
            excluded.iter().all(|&i| i < total),
            "omitted acquisition outside census"
        );
        let mask: Vec<_> = (0..total).map(|i| !excluded.contains(&i)).collect();
        if !omitted.is_empty() {
            ensure!(
                total <= 128 && passes.len() == 2,
                "research cohort needs exactly two bounded passes"
            );
            ensure!(
                passes[0].start == 0 && passes[0].end == passes[1].start && passes[1].end == total,
                "research pass ranges must partition the original census"
            );
            for pass in passes {
                ensure!(
                    pass.start < pass.end
                        && pass.end <= total
                        && pass.len() <= 64
                        && mask[pass.start],
                    "research cohort must retain each calibration leader in a bounded pass"
                );
                ensure!(
                    pass.clone().filter(|&i| mask[i]).count() >= 2,
                    "research cohort needs at least two retained originals per pass"
                );
            }
        }
        Ok(Self {
            omitted: excluded,
            retained: (0..total).filter(|&i| mask[i]).collect(),
            mask,
        })
    }
    pub fn require(&self, index: usize) -> Result<()> {
        ensure!(
            self.mask.get(index).copied() == Some(true),
            "omitted acquisition reached pixel consumer"
        );
        Ok(())
    }
    pub fn focus_candidates(
        &self,
        session: &crate::session_input::ResolvedSession,
        alignment: &crate::session_align::SessionAlignment,
        fraction: f64,
    ) -> Result<Vec<crate::session_align::FocusPairCandidate>> {
        ensure!(
            self.mask.len() == session.len() && self.mask.len() == alignment.map.len(),
            "research focus mask differs from source census"
        );
        ensure!(
            fraction.is_finite() && fraction > 0. && fraction <= 0.5,
            "invalid research focus fraction"
        );
        let passes: Vec<_> = session
            .passes
            .iter()
            .map(|p| p.global_range.clone())
            .collect();
        let poses: Vec<_> = alignment.map.warps().iter().map(|p| p.placed()).collect();
        // Keep the production alignment source and its exact saved-map identity
        // unchanged. This research-only adapter must reproduce the loader's full
        // hints exactly before applying a mask; source drift is an error.
        let complete = hints(&passes, &poses, alignment.report.reference_pass, fraction);
        ensure!(
            serde_json::to_value(&complete)? == serde_json::to_value(&alignment.pair_candidates)?,
            "research focus adapter differs from the bound full-cohort production hints"
        );
        masked_hints(
            &passes,
            &poses,
            alignment.report.reference_pass,
            fraction,
            &self.mask,
        )
    }
    pub fn load(
        &self,
        index: usize,
        cache: &mut crate::session_cache::SourceCache,
        source: &crate::session_input::SourceFrame,
        identity: &crate::session_input::SourceIdentity,
    ) -> Result<std::sync::Arc<crate::session_cache::CachedSource>> {
        self.require(index)?;
        if self.omitted.is_empty() {
            Ok(cache.load_or_decode(source, identity)?)
        } else {
            ensure!(
                source.path == identity.path
                    && source.bytes == identity.bytes
                    && source.modified_unix_nanos == identity.modified_unix_nanos,
                "research cohort source identity differs"
            );
            cache.load(identity)?.context("research cohort requires an existing original-CFA cache entry; decoding is disabled")
        }
    }
    pub fn validate_placed(
        &self,
        passes: &[Range<usize>],
        placed: impl Fn(usize) -> bool,
    ) -> Result<()> {
        if !self.omitted.is_empty() {
            for pass in passes {
                ensure!(
                    pass.clone().filter(|&i| self.mask[i] && placed(i)).count() >= 2,
                    "research cohort needs at least two retained placed originals per pass"
                );
            }
        }
        Ok(())
    }
}

fn masked_hints(
    passes: &[Range<usize>],
    poses: &[Option<strehl_core::align::Similarity>],
    reference: usize,
    fraction: f64,
    mask: &[bool],
) -> Result<Vec<crate::session_align::FocusPairCandidate>> {
    ensure!(
        mask.len() == poses.len(),
        "research focus mask length differs"
    );
    let retained: Vec<_> = poses
        .iter()
        .zip(mask)
        .map(|(pose, keep)| if *keep { *pose } else { None })
        .collect();
    Ok(hints(passes, &retained, reference, fraction))
}

// Exact retained-pose version of the existing scale-hint operation. It never
// certifies focus; full-cohort parity above prevents silent algorithm drift.
fn hints(
    passes: &[Range<usize>],
    poses: &[Option<strehl_core::align::Similarity>],
    reference: usize,
    fraction: f64,
) -> Vec<crate::session_align::FocusPairCandidate> {
    fn median(mut values: Vec<f64>) -> Option<f64> {
        values.retain(|v| v.is_finite());
        if values.is_empty() {
            return None;
        }
        values.sort_by(f64::total_cmp);
        let mid = values.len() / 2;
        Some(if values.len() % 2 == 1 {
            values[mid]
        } else {
            0.5 * (values[mid - 1] + values[mid])
        })
    }
    fn nearest(values: &[Option<f64>], range: Range<usize>, target: f64) -> Option<usize> {
        range
            .filter_map(|i| values[i].map(|v| (i, (v - target).abs())))
            .min_by(|a, b| a.1.total_cmp(&b.1).then(a.0.cmp(&b.0)))
            .map(|(i, _)| i)
    }
    let scales: Vec<_> = poses
        .iter()
        .map(|p| p.map(|v| v.a.abs().ln()).filter(|v| v.is_finite()))
        .collect();
    let steps: Vec<_> = passes
        .iter()
        .map(|pass| {
            median(
                pass.clone()
                    .skip(1)
                    .filter_map(|i| Some((scales[i]? - scales[i - 1]?).abs()))
                    .collect(),
            )
            .filter(|&v| v > 1e-9)
        })
        .collect();
    let anchor = passes[reference].clone();
    let mut result = Vec::new();
    for (pass_index, pass) in passes.iter().enumerate() {
        if pass_index == reference {
            continue;
        }
        let allowed = steps[reference]
            .zip(steps[pass_index])
            .map(|(a, b)| fraction * a.min(b));
        let mut pairs = BTreeSet::new();
        for (a, b) in [
            (anchor.clone(), pass.clone()),
            (pass.clone(), anchor.clone()),
        ] {
            for i in a {
                if let Some(j) = scales[i].and_then(|value| nearest(&scales, b.clone(), value)) {
                    pairs.insert((i.min(j), i.max(j)));
                }
            }
        }
        for (i, j) in pairs {
            let (a, b) = if anchor.contains(&i) { (i, j) } else { (j, i) };
            let av = scales[a].expect("candidate scale");
            let bv = scales[b].expect("candidate scale");
            let mutual = nearest(&scales, pass.clone(), av) == Some(b)
                && nearest(&scales, anchor.clone(), bv) == Some(a);
            let gap = (av - bv).abs();
            result.push(crate::session_align::FocusPairCandidate {
                i,
                j,
                mutual_nearest: mutual,
                log_scale_gap: gap,
                allowed_log_scale_gap: allowed,
                candidate_same_focus: mutual && allowed.is_some_and(|bar| gap <= bar),
                validated_same_focus: false,
            });
        }
    }
    result.sort_by_key(|p| (p.i, p.j));
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn research_cohort_hints_have_fixed_oracle_ties_and_ignore_omitted_geometry_poison() {
        use strehl_core::align::{Cx, Similarity};
        let pose = |v: f64| {
            Some(Similarity {
                a: Cx::real(v.exp()),
                b: Cx::ZERO,
            })
        };
        let original: Vec<_> = [0.0, 0.1, 0.2, 0.2, 0.1, 0.0]
            .into_iter()
            .map(pose)
            .collect();
        let full = hints(&[0..3, 3..6], &original, 0, 0.25);
        assert_eq!(
            full.iter()
                .filter(|p| p.candidate_same_focus)
                .map(|p| (p.i, p.j))
                .collect::<Vec<_>>(),
            vec![(0, 5), (1, 4), (2, 3)]
        );
        assert!(full.iter().all(|p| !p.validated_same_focus));
        let mask = [true, true, false, false, true, true];
        let baseline = masked_hints(&[0..3, 3..6], &original, 0, 0.25, &mask).unwrap();
        let mut poisoned = original;
        poisoned[2] = pose(10.);
        poisoned[3] = pose(-10.);
        assert_eq!(
            serde_json::to_value(&baseline).unwrap(),
            serde_json::to_value(masked_hints(&[0..3, 3..6], &poisoned, 0, 0.25, &mask).unwrap())
                .unwrap()
        );
        assert!(masked_hints(&[0..3, 3..6], &poisoned, 0, 0.25, &[true]).is_err());
        assert!(
            baseline
                .iter()
                .all(|p| p.i != 2 && p.j != 3 && p.allowed_log_scale_gap.is_some_and(|r| r < 0.03))
        );
        let flat = vec![pose(0.); 6];
        assert!(
            hints(&[0..3, 3..6], &flat, 0, 0.25)
                .iter()
                .all(|p| p.allowed_log_scale_gap.is_none() && !p.candidate_same_focus)
        );
    }
    #[test]
    fn research_cohort_real_cache_reader_never_opens_omitted_missing_or_poisoned_entries() {
        use crate::session_input::{PassSpec, SessionMode, SessionSpec};
        let root = std::env::temp_dir().join(format!(
            "strehl-cohort-cache-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir(&root).unwrap();
        let mut passes = Vec::new();
        for pass in 0..2 {
            let dir = root.join(format!("pass-{pass}"));
            std::fs::create_dir(&dir).unwrap();
            for i in 0..4 {
                std::fs::write(
                    dir.join(format!("frame-{i}.ARW")),
                    format!("invalid RAW pixel decoder poison {pass}/{i}"),
                )
                .unwrap();
            }
            passes.push(PassSpec {
                name: format!("pass-{pass}"),
                directories: vec![dir],
            });
        }
        let session = SessionSpec {
            mode: SessionMode::Repeat,
            passes,
            ..SessionSpec::default()
        }
        .resolve_from(&root)
        .unwrap();
        let ids = session.hash_sources(true).unwrap();
        let mut cache =
            crate::session_cache::SourceCache::new(&root.join("cache"), &session, 1 << 20).unwrap();
        std::fs::write(
            cache.cache_path(&ids[6]).unwrap(),
            b"invalid cached CFA header",
        )
        .unwrap();
        assert!(cache.load(&ids[2]).unwrap().is_none());
        assert!(cache.load(&ids[6]).is_err()); // This poison fails if a consumer opens it.
        let cohort = Cohort::new(8, &[0..4, 4..8], &[2, 6]).unwrap();
        for index in [2, 6] {
            let error = cohort
                .load(index, &mut cache, &session.frames[index], &ids[index])
                .err()
                .unwrap();
            assert!(error.to_string().contains("omitted acquisition"));
        }
        let error = cohort
            .load(0, &mut cache, &session.frames[0], &ids[0])
            .err()
            .unwrap();
        assert!(error.to_string().contains("decoding is disabled"));
        assert_eq!(cache.stats().decodes, 0);
        drop(cache);
        std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn research_cohort_excludes_poisoned_and_missing_originals_before_consumer_calls() {
        let cohort = Cohort::new(8, &[0..4, 4..8], &[2, 6]).unwrap();
        let mut sources = [
            Some(10.),
            Some(11.),
            None,
            Some(13.),
            Some(14.),
            Some(15.),
            Some(f32::NAN),
            Some(17.),
        ];
        let consume = |source: &[Option<f32>; 8]| {
            cohort
                .retained
                .iter()
                .map(|&i| {
                    cohort.require(i).unwrap();
                    let value = source[i].expect("retained original");
                    assert!(value.is_finite());
                    value
                })
                .collect::<Vec<_>>()
        };
        let before = consume(&sources);
        sources[2] = Some(f32::INFINITY);
        sources[6] = None;
        assert_eq!(consume(&sources), before);
        assert!(cohort.require(2).is_err());
        assert!(cohort.require(6).is_err());
        assert!(cohort.require(8).is_err());
        cohort.validate_placed(&[0..4, 4..8], |_| true).unwrap();
        assert!(
            cohort
                .validate_placed(&[0..4, 4..8], |i| i == 0 || i >= 4)
                .is_err()
        );
    }
    #[test]
    fn research_cohort_empty_is_identity_and_invalid_removals_refuse() {
        let cohort = Cohort::new(8, &[0..4, 4..8], &[]).unwrap();
        assert_eq!(cohort.retained, (0..8).collect::<Vec<_>>());
        assert!(cohort.mask.iter().all(|&v| v));
        for omitted in [&[2, 2][..], &[8], &[0], &[4], &[1, 2, 3]] {
            assert!(Cohort::new(8, &[0..4, 4..8], omitted).is_err());
        }
        assert!(Cohort::new(8, std::slice::from_ref(&(0..8)), &[2]).is_err());
        assert!(Cohort::new(130, &[0..65, 65..130], &[2]).is_err());
    }
}
