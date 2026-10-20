//! Opt-in, line-oriented observations for the desktop's live pipeline view.
//!
//! This observer receives identities and results at existing operation boundaries.
//! It owns no image data and supplies no value back to the processing pipeline.
//! Output equality must be checked with cold-cache enabled/disabled/placebo
//! render hashes using `scripts/verify-ui-progress.py`.

use std::sync::{Mutex, OnceLock};

#[path = "ui-diagnostics.rs"]
mod diagnostics;
pub(crate) use diagnostics::FrameTap;

const ENV: &str = "STREHL_UI_PROGRESS";

pub(crate) struct Progress {
    enabled: bool,
    total: usize,
    counts: Mutex<Counts>,
    confidence: Mutex<Counts>,
    alignment: Mutex<AlignmentCounts>,
    diagnostics: Mutex<diagnostics::DiagnosticCounts>,
    #[cfg(test)]
    capture: Option<std::sync::Arc<Mutex<Vec<String>>>>,
}

const MAX_PHASE_SNAPSHOTS: usize = 512;

#[derive(Default, Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct AlignmentCounts {
    pub planes: usize,
    pub pyramids: usize,
    pub pairs_started: usize,
    pub pairs: usize,
    pub accepted: usize,
    pub current_pair: Option<[usize; 2]>,
}

#[derive(Default)]
struct Counts {
    processed: usize,
    accepted: usize,
}

impl Progress {
    pub(crate) fn new(total: usize) -> Self {
        static ENABLED: OnceLock<bool> = OnceLock::new();
        let enabled = *ENABLED.get_or_init(|| enabled_value(std::env::var(ENV).ok().as_deref()));
        Self {
            enabled,
            total,
            counts: Mutex::new(Counts::default()),
            confidence: Mutex::new(Counts::default()),
            alignment: Mutex::new(AlignmentCounts::default()),
            diagnostics: Mutex::new(diagnostics::DiagnosticCounts::default()),
            #[cfg(test)]
            capture: None,
        }
    }

    pub(crate) fn observer(&self) -> Option<&Self> {
        self.enabled.then_some(self)
    }

    /// Actual source-constrained reconstruction, separate from the original
    /// global admission diagnostics. No image data returns to the worker.
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn source_repair(
        &self,
        region: usize,
        regions: usize,
        first: usize,
        last: usize,
        index: usize,
        completed: usize,
        accepted: usize,
        state: &str,
    ) {
        if self.enabled {
            self.emit(format!(
                "event=source-repair region={region} regions={regions} first={first} last={last} \
                 index={index} completed={completed} accepted={accepted} total={} state={state}",
                last - first + 1,
            ));
        }
    }

    #[cfg(test)]
    pub(crate) fn captured_enabled(enabled: bool) -> (Self, std::sync::Arc<Mutex<Vec<String>>>) {
        let (mut p, lines) = Self::captured(0);
        p.enabled = enabled;
        (p, lines)
    }

    fn emit(&self, fields: String) {
        #[cfg(test)]
        if let Some(lines) = &self.capture {
            lines
                .lock()
                .expect("progress capture lock poisoned")
                .push(format!("STREHL_UI_PROGRESS {fields}"));
            return;
        }
        eprintln!("STREHL_UI_PROGRESS {fields}");
    }

    pub(crate) fn alignment_phase(&self, name: &str, total: usize) {
        if self.enabled {
            self.emit(format!(
                "event=align-phase name={name} total={total} frames={}",
                self.total
            ));
        }
    }

    pub(crate) fn alignment_plane_started(&self, index: usize) {
        if self.enabled {
            self.emit(format!(
                "event=align-plane-start index={index} total={} frames={}",
                self.total, self.total
            ));
        }
    }

    pub(crate) fn alignment_plane_finished(&self, index: usize) {
        if self.enabled {
            let mut counts = self
                .alignment
                .lock()
                .expect("alignment progress lock poisoned");
            counts.planes += 1;
            self.emit(format!(
                "event=align-plane index={index} completed={} total={} frames={}",
                counts.planes, self.total, self.total
            ));
        }
    }

    pub(crate) fn alignment_pyramid_finished(&self, index: usize) {
        if self.enabled {
            let mut counts = self
                .alignment
                .lock()
                .expect("alignment progress lock poisoned");
            counts.pyramids += 1;
            self.emit(format!(
                "event=align-pyramid index={index} completed={} total={} frames={}",
                counts.pyramids, self.total, self.total
            ));
        }
    }

    pub(crate) fn alignment_pair_started(&self, i: usize, j: usize, total: usize) {
        if self.enabled {
            let mut counts = self
                .alignment
                .lock()
                .expect("alignment progress lock poisoned");
            counts.pairs_started += 1;
            if snapshot(counts.pairs_started, total) {
                counts.current_pair = Some([i, j]);
                self.emit(format!(
                    "event=align-pair-start i={i} j={j} started={} total={total} frames={}",
                    counts.pairs_started, self.total
                ));
            }
        }
    }

    pub(crate) fn alignment_pair_finished(&self, i: usize, j: usize, accepted: bool, total: usize) {
        if self.enabled {
            // Count and emit under one lock so parallel workers cannot print
            // an older completion after a newer one. Refused attempts count.
            let mut counts = self
                .alignment
                .lock()
                .expect("alignment progress lock poisoned");
            counts.pairs += 1;
            counts.accepted += usize::from(accepted);
            let displayed_finished = counts.current_pair == Some([i, j]);
            if displayed_finished {
                counts.current_pair = None;
            }
            // Also retire each displayed comparison even between aggregate
            // snapshots. This adds at most one finish per sampled start.
            if snapshot(counts.pairs, total) || displayed_finished {
                self.emit(format!(
                    "event=align-pair i={i} j={j} completed={} accepted={} total={total} frames={}",
                    counts.pairs, counts.accepted, self.total
                ));
            }
        }
    }

    pub(crate) fn alignment_result(
        &self,
        source: &str,
        reference: usize,
        placed: usize,
        refused: usize,
    ) {
        if self.enabled {
            self.emit(format!("event=align-result source={source} reference={reference} placed={placed} refused={refused} total={} frames={}", self.total, self.total));
        }
    }

    #[cfg(test)]
    pub(crate) fn captured(total: usize) -> (Self, std::sync::Arc<Mutex<Vec<String>>>) {
        let capture = std::sync::Arc::new(Mutex::new(Vec::new()));
        (
            Self {
                enabled: true,
                total,
                counts: Mutex::new(Counts::default()),
                confidence: Mutex::new(Counts::default()),
                alignment: Mutex::new(AlignmentCounts::default()),
                diagnostics: Mutex::new(diagnostics::DiagnosticCounts::default()),
                capture: Some(std::sync::Arc::clone(&capture)),
            },
            capture,
        )
    }

    #[cfg(test)]
    pub(crate) fn alignment_counts(&self) -> AlignmentCounts {
        *self.alignment.lock().unwrap()
    }

    pub(crate) fn stage(&self, name: &str) {
        if self.enabled {
            eprintln!(
                "STREHL_UI_PROGRESS event=stage name={name} total={}",
                self.total
            );
        }
    }

    pub(crate) fn frame_started(&self, index: usize) {
        if self.enabled {
            self.emit(format!(
                "event=frame-started index={index} total={}",
                self.total
            ));
        }
    }

    pub(crate) fn confidence_started(&self) {
        if self.enabled {
            *self
                .confidence
                .lock()
                .expect("confidence progress lock poisoned") = Counts::default();
            self.emit(format!(
                "event=confidence-pass state=started completed=0 compared=0 total={}",
                self.total
            ));
        }
    }

    /// Completion includes refused load attempts; only mapped frames reached
    /// the green-luma comparison. Emit under one lock in parallel chunk order.
    pub(crate) fn confidence_frame_finished(&self, index: usize, mapped: bool) {
        if self.enabled {
            let mut counts = self
                .confidence
                .lock()
                .expect("confidence progress lock poisoned");
            counts.processed += 1;
            counts.accepted += usize::from(mapped);
            self.emit(format!("event=confidence-frame index={index} completed={} compared={} mapped={mapped} total={}", counts.processed, counts.accepted, self.total));
        }
    }

    pub(crate) fn confidence_finished(&self) {
        if self.enabled {
            let counts = self
                .confidence
                .lock()
                .expect("confidence progress lock poisoned");
            self.emit(format!(
                "event=confidence-pass state=finished completed={} compared={} total={}",
                counts.processed, counts.accepted, self.total
            ));
        }
    }

    pub(crate) fn frame_finished(&self, index: usize, accepted: bool) {
        if self.enabled {
            let (processed, accepted) = self.observe(accepted);
            self.emit(format!(
                "event=frame-finished index={index} processed={processed} accepted={accepted} total={}",
                self.total
            ));
        }
    }

    fn observe(&self, accepted: bool) -> (usize, usize) {
        // Both values describe the same completed set. Independent atomics
        // could expose accepted > processed while another worker was between
        // increments, yielding an impossible event that the viewer rejects.
        let mut counts = self.counts.lock().expect("progress counter lock poisoned");
        if accepted {
            counts.accepted += 1;
        }
        counts.processed += 1;
        (counts.processed, counts.accepted)
    }
}

fn enabled_value(value: Option<&str>) -> bool {
    value == Some("1")
}

fn snapshot(completed: usize, total: usize) -> bool {
    completed == 1
        || completed == total
        || completed.is_multiple_of(total.div_ceil(MAX_PHASE_SNAPSHOTS).max(1))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Barrier;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use strehl_core::pyramid::MergeObserver;

    #[test]
    fn every_frame_keeps_its_alignment_and_merge_steps_above_the_pair_snapshot_budget() {
        // 1,025 inputs exercise the old stride-three frame suppression.
        // Pair fits have a separate, intentionally bounded event budget.
        let (progress, lines) = Progress::captured(1025);
        for index in 0..1025 {
            progress.alignment_plane_started(index);
            progress.alignment_plane_finished(index);
            progress.alignment_pyramid_finished(index);
            progress.frame_started(index);
            progress.merge_step(index, "decode", None, "started");
            progress.merge_step(index, "decode", None, "finished");
            FrameTap::new(&progress, index, 1)
                .phase(strehl_core::pyramid::FoldPhase::FoldFinished(0));
            progress.frame_finished(index, true);
        }
        let lines = lines.lock().unwrap();
        let mut events = std::collections::BTreeMap::new();
        let mut decode = std::collections::BTreeMap::new();
        for line in &*lines {
            let fields: std::collections::BTreeMap<_, _> = line
                .split_whitespace()
                .filter_map(|field| field.split_once('='))
                .collect();
            let index: usize = fields["index"].parse().unwrap();
            *events.entry((fields["event"], index)).or_insert(0) += 1;
            if fields["event"] == "merge-step" && fields["name"] == "decode" {
                *decode.entry((index, fields["state"])).or_insert(0) += 1;
            }
        }
        for index in 0..1025 {
            for event in [
                "align-plane-start",
                "align-plane",
                "align-pyramid",
                "frame-started",
                "frame-finished",
                "band-work",
            ] {
                assert_eq!(
                    events.get(&(event, index)),
                    Some(&1),
                    "{event} for frame{index} cannot be sampled away"
                );
            }
            for state in ["started", "finished"] {
                assert_eq!(decode.get(&(index, state)), Some(&1));
            }
        }
        assert!(lines.iter().any(|line| {
            line.contains("event=band-work index=1024 level=0 completed=1025 total=1025")
        }));
    }

    #[test]
    fn alignment_snapshots_are_bounded_and_include_the_actual_last_operation() {
        let bounded = |count: usize| count <= MAX_PHASE_SNAPSHOTS + 2;
        for total in [1, 3, 512, 513, 10_000, 1_000_000] {
            let emitted: Vec<_> = (1..=total).filter(|&done| snapshot(done, total)).collect();
            assert!(
                bounded(emitted.len()),
                "{total} operations emitted {} snapshots",
                emitted.len()
            );
            assert_eq!(emitted.first(), Some(&1));
            assert_eq!(emitted.last(), Some(&total));
        }
        assert!(
            !bounded(10_000),
            "An unthrottled producer must fail the event-budget criterion"
        );
        let (mut disabled, lines) = Progress::captured(3);
        disabled.enabled = false;
        assert!(disabled.observer().is_none());
        disabled.alignment_phase("pairs", 3);
        disabled.alignment_pair_started(0, 1, 3);
        disabled.alignment_pair_finished(0, 1, true, 3);
        disabled.alignment_result("solved", 1, 3, 0);
        disabled.confidence_started();
        disabled.confidence_frame_finished(0, true);
        disabled.confidence_frame_finished(1, false);
        disabled.confidence_finished();
        assert!(lines.lock().unwrap().is_empty());
        assert_eq!(disabled.alignment_counts(), AlignmentCounts::default());
        let confidence = disabled.confidence.lock().unwrap();
        assert_eq!((confidence.processed, confidence.accepted), (0, 0));
    }

    #[test]
    fn opt_in_has_an_inert_placebo_and_refusals_count_as_processed_only() {
        assert!(enabled_value(Some("1")));
        for value in [None, Some("0"), Some("placebo"), Some("")] {
            assert!(!enabled_value(value));
        }
        let observer = Progress {
            enabled: true,
            total: 3,
            counts: Mutex::new(Counts::default()),
            confidence: Mutex::new(Counts::default()),
            alignment: Mutex::new(AlignmentCounts::default()),
            diagnostics: Mutex::new(diagnostics::DiagnosticCounts::default()),
            capture: None,
        };
        assert_eq!(observer.observe(true), (1, 1));
        assert_eq!(observer.observe(false), (2, 1));
        assert_eq!(observer.observe(true), (3, 2));
    }

    #[test]
    fn concurrent_observations_keep_coherent_counts_with_real_refusals() {
        const WORKERS: usize = 4;
        const PER_WORKER: usize = 240;
        const TOTAL: usize = WORKERS * PER_WORKER;
        let observer = Progress {
            enabled: true,
            total: TOTAL,
            counts: Mutex::new(Counts::default()),
            confidence: Mutex::new(Counts::default()),
            alignment: Mutex::new(AlignmentCounts::default()),
            diagnostics: Mutex::new(diagnostics::DiagnosticCounts::default()),
            capture: None,
        };
        let ready = AtomicUsize::new(0);
        let start = Barrier::new(WORKERS + 1);
        let mut snapshots = std::thread::scope(|scope| {
            let workers: Vec<_> = (0..WORKERS)
                .map(|worker| {
                    let observer = &observer;
                    let ready = &ready;
                    let start = &start;
                    scope.spawn(move || {
                        ready.fetch_add(1, Ordering::SeqCst);
                        start.wait();
                        (0..PER_WORKER)
                            .map(|index| {
                                // Every worker supplies both accepted and
                                // refused frames; exactly one third refuse.
                                let snapshot = observer.observe((worker + index) % 3 != 0);
                                assert!(snapshot.1 <= snapshot.0);
                                assert!(snapshot.0 <= TOTAL);
                                snapshot
                            })
                            .collect::<Vec<_>>()
                    })
                })
                .collect();
            start.wait();
            assert_eq!(
                ready.load(Ordering::SeqCst),
                WORKERS,
                "all four live workers must rendezvous before observations start"
            );
            workers
                .into_iter()
                .flat_map(|worker| worker.join().unwrap())
                .collect::<Vec<_>>()
        });
        snapshots.sort_unstable();
        assert_eq!(snapshots.len(), TOTAL);
        assert!(
            snapshots
                .iter()
                .enumerate()
                .all(|(index, snapshot)| snapshot.0 == index + 1),
            "every operation must appear exactly once in the processed count"
        );
        assert_eq!(snapshots.last(), Some(&(TOTAL, 640)));
        let counts = observer.counts.lock().unwrap();
        assert_eq!((counts.processed, counts.accepted), (TOTAL, 640));
    }
}
