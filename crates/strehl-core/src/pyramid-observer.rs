//! Read-only views at existing pyramid-fold boundaries. Observers return no
//! values to the merge and never allocate full-size diagnostic buffers.

use super::{BandMerge, Fallback, LevelSize, SelectMode, resolve_soft_numerator};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FoldPhase {
    PyramidStarted,
    PyramidReady,
    FocusStarted(usize),
    FoldStarted(usize),
    FoldFinished(usize),
}

pub struct BandObservation<'a> {
    pub level: usize,
    pub size: LevelSize,
    /// Smoothed squared Laplacian coefficients actually used by the gate.
    /// Absent for the base residual, which has no independent focus election.
    pub energy: Option<&'a [f32]>,
    pub variance: Option<&'a [f32]>,
    /// The same gate*beta multiplier read by the numerical loop.
    pub floor_multiplier: f32,
    pub weights: &'a [f32],
}

pub trait MergeObserver: Send + Sync {
    fn phase(&self, phase: FoldPhase);
    fn band(&self, band: BandObservation<'_>);
}

/// A borrowed view of already-folded data. Coefficients are resolved using the
/// same mode/fallback as finish, without constructing a reconstruction. Values
/// remain per-band coefficients; they are not a developed photograph.
pub struct AccumulatorObservation<'a> {
    merge: &'a BandMerge,
    /// Optional disjoint later chunk, combined in canonical left-to-right
    /// order without mutating either accumulator or allocating their grids.
    other: Option<&'a BandMerge>,
    pub level: usize,
    pub size: LevelSize,
    pub frames: usize,
}

impl AccumulatorObservation<'_> {
    pub fn averaging(&self, index: usize) -> bool {
        self.denominator(index) <= 0.0
    }

    fn denominator(&self, index: usize) -> f32 {
        let first = self.merge.den[self.level][index];
        self.other
            .map_or(first, |other| match self.merge.cfg.select {
                SelectMode::SoftPower => first + other.den[self.level][index],
                SelectMode::HardMax => first.max(other.den[self.level][index]),
            })
    }

    pub fn coefficient(&self, index: usize) -> f32 {
        let resolve = |plane: usize| {
            let merge = self.merge;
            let slot = self.level * merge.planes + plane;
            let den = self.denominator(index);
            if den > 0.0 {
                return match merge.cfg.select {
                    SelectMode::SoftPower => {
                        let numerator = self.other.map_or(merge.num[slot][index], |other| {
                            merge.num[slot][index] + other.num[slot][index]
                        });
                        resolve_soft_numerator(numerator, den)
                    }
                    SelectMode::HardMax => self.other.map_or(merge.num[slot][index], |other| {
                        if other.best[self.level][index] > merge.best[self.level][index] {
                            other.num[slot][index]
                        } else {
                            merge.num[slot][index]
                        }
                    }),
                };
            }
            let inv_n = 1.0 / self.frames as f32;
            let mean = || {
                self.other.map_or(merge.usum[slot][index], |other| {
                    merge.usum[slot][index] + other.usum[slot][index]
                }) * inv_n
            };
            match merge.cfg.fallback {
                Fallback::Mean => mean(),
                Fallback::Power => {
                    let key = self.other.map_or(merge.fkey[self.level][index], |other| {
                        merge.fkey[self.level][index] + other.fkey[self.level][index]
                    });
                    if key > 0.0 {
                        self.other.map_or(merge.fval[slot][index], |other| {
                            merge.fval[slot][index] + other.fval[slot][index]
                        }) / key
                    } else {
                        mean()
                    }
                }
                _ => {
                    let slots = merge.cfg.fallback_slots();
                    let count = slots.min(self.frames).max(1) as f32;
                    let base = index * slots;
                    if let Some(other) = self.other {
                        // Match absorb's descending-run merge, including ties
                        // preferring the canonical earlier accumulator.
                        let (mut a, mut b) = (0, 0);
                        let mut sum = 0.0;
                        for _ in 0..slots {
                            let take_b = a >= slots
                                || (b < slots
                                    && other.fkey[self.level][base + b]
                                        > merge.fkey[self.level][base + a]);
                            if take_b {
                                sum += other.fval[slot][base + b];
                                b += 1;
                            } else {
                                sum += merge.fval[slot][base + a];
                                a += 1;
                            }
                        }
                        sum / count
                    } else {
                        merge.fval[slot][base..base + slots].iter().sum::<f32>() / count
                    }
                }
            }
        };
        if self.merge.planes >= 3 {
            0.5 * (resolve(1) + resolve(2))
        } else {
            resolve(0)
        }
    }
}

impl BandMerge {
    pub fn observe_accumulator(&self, mut observe: impl FnMut(AccumulatorObservation<'_>)) {
        if self.frames == 0 {
            return;
        }
        for (level, size) in self.sizes.iter().copied().enumerate() {
            observe(AccumulatorObservation {
                merge: self,
                other: None,
                level,
                size,
                frames: self.frames as usize,
            });
        }
    }

    /// Observe the exact unresolved union of a canonical prefix and a disjoint
    /// in-progress chunk. This performs absorb's scalar arithmetic on demand;
    /// it does not absorb, clone, reconstruct, or alter either merge. The view
    /// is before finish's hull bounds. The caller must supply disjoint frames
    /// in the same order used by its eventual canonical reduction.
    pub fn observe_accumulator_with(
        &self,
        other: &BandMerge,
        mut observe: impl FnMut(AccumulatorObservation<'_>),
    ) {
        assert_eq!(
            self.sizes, other.sizes,
            "cannot observe a differently shaped merge"
        );
        assert_eq!(
            self.planes, other.planes,
            "cannot observe different plane counts"
        );
        assert_eq!(
            self.cfg.select, other.cfg.select,
            "cannot observe different selection modes"
        );
        assert_eq!(
            self.cfg.admission, other.cfg.admission,
            "cannot observe different admission modes"
        );
        assert_eq!(
            self.cfg.fallback, other.cfg.fallback,
            "cannot observe different fallbacks"
        );
        assert_eq!(
            self.cfg.fallback_slots(),
            other.cfg.fallback_slots(),
            "cannot observe different fallback slot counts"
        );
        let frames = self.frames as usize + other.frames as usize;
        if frames == 0 {
            return;
        }
        for (level, size) in self.sizes.iter().copied().enumerate() {
            observe(AccumulatorObservation {
                merge: self,
                other: Some(other),
                level,
                size,
                frames,
            });
        }
    }
}

#[cfg(test)]
#[path = "pyramid-observer-tests.rs"]
mod tests;
