//! Fixed experimental temporal energy transport through the ordinary merge.
//!
//! The ring contains statistical energy/complete-floor fields only. Original
//! source planes are supplied again when a ready center is folded. No aligned
//! image or coefficient-pyramid frame volume is retained. This is not a depth
//! estimator and does not couple different spatial frequency bands.
use super::{
    AdmissionMode, BandMerge, BaseBand, Fallback, FrameWorkspace, LevelSize, MergeObserver,
    SelectMode,
};
use std::collections::VecDeque;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    Off,
    On,
    /// Spatially misregister only neighbor support by eight level-0 pixels.
    /// Neighbor(y,x) reads neighbor(y,(x+shift)%width), circularly within a row.
    /// This is a causal placebo, not a temporal permutation.
    ShiftNeighbors,
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct Binding {
    source_index: usize,
    fingerprint: [u64; 2],
    sizes: Vec<LevelSize>,
    config: String,
}
#[derive(Debug, Clone)]
pub struct Band {
    pub size: LevelSize,
    pub energy: Vec<f32>,
    /// Absolute floor gate*beta_i*V_i, already including beta exactly once.
    pub floor: Vec<f32>,
}
#[derive(Debug, Clone)]
pub struct Guide {
    binding: Binding,
    bands: Vec<Band>,
}
impl Guide {
    pub fn source_index(&self) -> usize {
        self.binding.source_index
    }
    pub fn bands(&self) -> &[Band] {
        &self.bands
    }
    fn validate(&self) {
        assert!(!self.binding.sizes.is_empty(), "missing guide geometry");
        assert_eq!(
            self.bands.len(),
            (self.binding.sizes.len() - 1).min(2),
            "missing guide bands"
        );
        for (k, band) in self.bands.iter().enumerate() {
            assert_eq!(band.size, self.binding.sizes[k]);
            assert_eq!(band.energy.len(), band.size.pixels());
            assert_eq!(band.floor.len(), band.size.pixels());
            assert!(
                band.energy
                    .iter()
                    .chain(&band.floor)
                    .all(|v| v.is_finite() && *v >= 0.0),
                "invalid guide values"
            );
        }
    }
}
#[derive(Debug, Clone)]
pub struct Ready {
    binding: Binding,
    mode: Mode,
    /// None means use the original path, not a copied unfiltered guide.
    bands: Option<Vec<Band>>,
    neighbors: Option<[usize; 2]>,
}
impl Ready {
    fn original(guide: &Guide, mode: Mode) -> Self {
        Self {
            binding: guide.binding.clone(),
            mode,
            bands: None,
            neighbors: None,
        }
    }
    pub fn source_index(&self) -> usize {
        self.binding.source_index
    }
    pub fn mode(&self) -> Mode {
        self.mode
    }
    pub fn is_original(&self) -> bool {
        self.bands.is_none()
    }
    pub fn bands(&self) -> Option<&[Band]> {
        self.bands.as_deref()
    }
    pub fn neighbor_indices(&self) -> Option<[usize; 2]> {
        self.neighbors
    }
    pub(super) fn band(&self, k: usize) -> Option<&Band> {
        self.bands.as_ref().and_then(|b| b.get(k))
    }
}

/// Consume each Ready before pushing further input to retain the bounded-memory
/// contract. At most three input guides are held during push, two afterwards,
/// plus one emitted filtered guide. Cloning for separate fixed control rings is
/// supported; storing a complete stack of Guides/Readies is not the intended API.
pub struct Ring {
    total: usize,
    mode: Mode,
    received: usize,
    finished: bool,
    guides: VecDeque<Guide>,
    schema: Option<(Vec<LevelSize>, String)>,
}
impl Ring {
    pub fn new(total_frames: usize, mode: Mode) -> Self {
        assert!(total_frames > 0 && total_frames <= u32::MAX as usize);
        Self {
            total: total_frames,
            mode,
            received: 0,
            finished: false,
            guides: VecDeque::with_capacity(3),
            schema: None,
        }
    }
    pub fn retained_guides(&self) -> usize {
        self.guides.len()
    }
    pub fn push(&mut self, guide: Guide) -> Option<Ready> {
        assert!(
            !self.finished && self.received < self.total,
            "ring already complete"
        );
        assert_eq!(
            guide.source_index(),
            self.received,
            "nonconsecutive guide source index"
        );
        guide.validate();
        if let Some((sizes, config)) = &self.schema {
            assert_eq!(&guide.binding.sizes, sizes, "mixed guide shapes");
            assert_eq!(&guide.binding.config, config, "mixed guide configurations");
        } else {
            self.schema = Some((guide.binding.sizes.clone(), guide.binding.config.clone()));
        }
        self.received += 1;
        if self.mode == Mode::Off || self.total < 3 {
            return Some(Ready::original(&guide, self.mode));
        }
        let first = self.received == 1;
        self.guides.push_back(guide);
        if first {
            return Some(Ready::original(self.guides.front().unwrap(), self.mode));
        }
        if self.guides.len() < 3 {
            return None;
        }
        assert_eq!(self.guides.len(), 3);
        let (left, center, right) = (&self.guides[0], &self.guides[1], &self.guides[2]);
        let bands = center
            .bands
            .iter()
            .enumerate()
            .map(|(k, c)| {
                let l = &left.bands[k];
                let r = &right.bands[k];
                let shift = if self.mode == Mode::ShiftNeighbors {
                    (8usize.checked_shr(k as u32).unwrap_or(0)).max(1) % c.size.width
                } else {
                    0
                };
                let blend = |a: &[f32], b: &[f32], d: &[f32]| -> Vec<f32> {
                    (0..b.len())
                        .map(|i| {
                            let shifted = (i / c.size.width) * c.size.width
                                + (i % c.size.width + shift) % c.size.width;
                            let (x, y, z) = (a[shifted], b[i], d[shifted]);
                            // Preserve a temporally constant field bitwise; the symmetric
                            // arithmetic is also invariant to reversing source order.
                            if x.to_bits() == y.to_bits() && y.to_bits() == z.to_bits() {
                                y
                            } else {
                                0.5 * y + (0.25 * x + 0.25 * z)
                            }
                        })
                        .collect()
                };
                Band {
                    size: c.size,
                    energy: blend(&l.energy, &c.energy, &r.energy),
                    floor: blend(&l.floor, &c.floor, &r.floor),
                }
            })
            .collect();
        let result = Ready {
            binding: center.binding.clone(),
            mode: self.mode,
            bands: Some(bands),
            neighbors: Some([left.source_index(), right.source_index()]),
        };
        self.guides.pop_front();
        Some(result)
    }
    /// Exactly one terminal call is required. Short/off stacks have no delayed
    /// endpoint. Calling early or twice is a contract error.
    pub fn finish(&mut self) -> Option<Ready> {
        assert!(!self.finished, "ring finished twice");
        assert_eq!(
            self.received, self.total,
            "ring finished before all guides arrived"
        );
        self.finished = true;
        let endpoint = if self.mode != Mode::Off && self.total >= 3 {
            Some(Ready::original(self.guides.back().unwrap(), self.mode))
        } else {
            None
        };
        self.guides.clear();
        endpoint
    }
}

fn fingerprint(
    planes: &[&[f32]],
    luma: &[f32],
    variance: &[f32],
    frame_beta: Option<&[f32]>,
) -> [u64; 2] {
    // Accidental source/cache mismatch guard, not a cryptographic provenance
    // digest. Both source coefficients and statistical inputs are bound by bits.
    let mut hash = [0xcbf29ce484222325u64, 0x9e3779b97f4a7c15];
    let mut word = |v: u64| {
        hash[0] = (hash[0] ^ v).wrapping_mul(0x100000001b3);
        hash[1] = (hash[1] ^ v)
            .rotate_left(27)
            .wrapping_mul(0x94d049bb133111eb);
    };
    word(planes.len() as u64);
    for array in planes.iter().copied().chain([luma, variance]) {
        word(array.len() as u64);
        for v in array {
            word(u64::from(v.to_bits()));
        }
    }
    word(u64::from(frame_beta.is_some()));
    if let Some(beta) = frame_beta {
        word(beta.len() as u64);
        for v in beta {
            word(u64::from(v.to_bits()));
        }
    }
    hash
}
fn incompatible_coefficient_rewriter() -> bool {
    cfg!(feature = "m194h-pedestal-causality") || cfg!(feature = "native-sensor-transfer")
}

impl BandMerge {
    /// Bind one empty canonical accumulator to its fixed global source range.
    /// Reset clears this contract; it cannot be changed after a fold begins.
    pub fn set_temporal_source_range(&mut self, range: std::ops::Range<usize>) {
        assert_eq!(
            self.frames, 0,
            "temporal range requires an empty accumulator"
        );
        assert!(
            self.temporal_source_range.is_none(),
            "temporal range already fixed"
        );
        assert!(range.start < range.end && range.end <= u32::MAX as usize);
        self.temporal_source_range = Some(range);
    }
    fn validate_temporal_workspace(&self, ws: &FrameWorkspace) {
        assert_eq!(
            ws.luma.sizes(),
            self.sizes.as_slice(),
            "wrong temporal workspace geometry"
        );
        #[cfg(feature = "spatial-noise-floor")]
        assert!(
            ws.spatial_noise_floor.is_off(),
            "temporal experiment requires spatial floor Off"
        );
    }
    fn temporal_binding(
        &self,
        index: usize,
        planes: &[&[f32]],
        luma: &[f32],
        variance: &[f32],
        beta: Option<&[f32]>,
    ) -> Binding {
        assert!(
            !incompatible_coefficient_rewriter(),
            "temporal experiment cannot combine independent coefficient rewriting features"
        );
        assert_eq!(
            self.cfg.fallback,
            Fallback::Mean,
            "first temporal screen requires unweighted mean fallback"
        );
        #[cfg(feature = "native-correction-variance")]
        assert!(
            super::fine_support_candidate::environment_mode()
                == super::fine_support_candidate::Mode::Off,
            "temporal experiment cannot combine fine-support rewriting"
        );
        assert_eq!(planes.len(), self.planes);
        let pixels = self.sizes[0].pixels();
        assert_eq!(luma.len(), pixels);
        assert_eq!(variance.len(), pixels);
        for p in planes {
            assert_eq!(p.len(), pixels);
            assert!(p.iter().all(|v| v.is_finite()), "nonfinite original source");
        }
        assert!(luma.iter().all(|v| v.is_finite()));
        assert!(variance.iter().all(|v| v.is_finite() && *v >= 0.0));
        if let Some(beta) = beta {
            assert!(beta.iter().all(|v| v.is_finite() && *v >= 0.0));
        }
        assert_eq!(
            self.cfg.select,
            SelectMode::SoftPower,
            "temporal experiment requires the existing soft selector"
        );
        assert_eq!(
            self.cfg.admission,
            AdmissionMode::HardFloor,
            "temporal experiment requires HardFloor"
        );
        assert_eq!(
            self.cfg.base,
            BaseBand::Mean,
            "first temporal screen requires mean base"
        );
        assert!(self.cfg.gate.is_finite() && self.cfg.gate > 0.0);
        Binding {
            source_index: index,
            fingerprint: fingerprint(planes, luma, variance, beta),
            sizes: self.sizes.clone(),
            config: format!("{:?}", self.cfg),
        }
    }
    /// Measure only the guide statistics. Uses the very same producer helpers
    /// as the ordinary fold and never accumulates a source or retains planes.
    pub fn temporal_guide(
        &self,
        source_index: usize,
        planes: &[&[f32]],
        luma: &[f32],
        variance: &[f32],
        frame_beta: Option<&[f32]>,
        ws: &mut FrameWorkspace,
    ) -> Guide {
        self.validate_temporal_workspace(ws);
        let binding = self.temporal_binding(source_index, planes, luma, variance, frame_beta);
        self.build_guide_fields(luma, variance, ws);
        #[cfg(feature = "spatial-noise-floor")]
        assert!(
            ws.spatial_noise_floor.level(0).is_none(),
            "temporal experiment cannot combine an active spatial floor"
        );
        let mut bands = Vec::new();
        for k in 0..(self.sizes.len() - 1).min(2) {
            let size = self.sizes[k];
            let energy = &mut ws.sq[..size.pixels()];
            super::band_energy(ws.luma.level(k), size, energy, &mut ws.smooth_scratch);
            let beta = Self::beta_for(&self.gain, frame_beta, k);
            let floor = ws
                .var
                .level(k)
                .iter()
                .map(|v| super::band_floor(self.cfg.gate, beta, *v))
                .collect();
            bands.push(Band {
                size,
                energy: energy.to_vec(),
                floor,
            });
        }
        let guide = Guide { binding, bands };
        guide.validate();
        guide
    }
    /// Fold a ready original center through the existing merge implementation.
    /// This first research adapter requires serial, exactly-once source order.
    /// The original must be regathered identically to its measured Guide.
    #[allow(clippy::too_many_arguments)]
    pub fn add_frame_with_temporal_guide(
        &mut self,
        source_index: usize,
        planes: &[&[f32]],
        luma: &[f32],
        variance: &[f32],
        frame_beta: Option<&[f32]>,
        ws: &mut FrameWorkspace,
        ready: &Ready,
        observer: Option<&dyn MergeObserver>,
    ) {
        let range = self
            .temporal_source_range
            .clone()
            .unwrap_or(0..u32::MAX as usize);
        assert!(
            source_index < range.end,
            "temporal source exceeds its canonical chunk"
        );
        assert_eq!(
            source_index,
            range.start + self.frames as usize,
            "duplicate or out-of-order temporal fold"
        );
        if ready.bands().is_some() {
            assert!(
                observer.is_none_or(|o| o.supports_absolute_floor()),
                "temporal observer does not support absolute floors"
            );
        }
        self.validate_temporal_workspace(ws);
        let binding = self.temporal_binding(source_index, planes, luma, variance, frame_beta);
        assert_eq!(
            binding, ready.binding,
            "temporal guide is bound to a different original source/configuration"
        );
        if let Some(bands) = ready.bands() {
            assert_eq!(bands.len(), (self.sizes.len() - 1).min(2));
            for (k, b) in bands.iter().enumerate() {
                assert_eq!(b.size, self.sizes[k]);
                assert_eq!(b.energy.len(), b.size.pixels());
                assert_eq!(b.floor.len(), b.size.pixels());
                assert!(
                    b.energy
                        .iter()
                        .chain(&b.floor)
                        .all(|v| v.is_finite() && *v >= 0.0)
                );
            }
        }
        #[cfg(feature = "native-correction-variance")]
        assert!(
            super::fine_support_candidate::environment_mode()
                == super::fine_support_candidate::Mode::Off,
            "temporal experiment cannot combine fine-support rewriting"
        );
        // Invalidate any neighboring source's plane cache before regathered
        // center coefficients are accumulated. No second merger is implemented.
        ws.next_frame();
        self.add_frame_with_gain_impl(
            planes,
            luma,
            variance,
            frame_beta,
            ws,
            #[cfg(feature = "native-green-cue")]
            None,
            #[cfg(feature = "native-correction-variance")]
            super::fine_support_candidate::Mode::Off,
            observer,
            Some(ready),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pyramid::{BandObservation, FoldPhase, MergeConfig, Workspace, level_sizes};
    use std::panic::{AssertUnwindSafe, catch_unwind};
    use std::sync::Mutex;
    fn sample(index: usize, e: f32, f: f32) -> Guide {
        let sizes = level_sizes(16, 16, 1);
        Guide {
            binding: Binding {
                source_index: index,
                fingerprint: [index as u64, 0],
                sizes: sizes.clone(),
                config: "fixed-test".into(),
            },
            bands: vec![Band {
                size: sizes[0],
                energy: vec![e; 256],
                floor: vec![f; 256],
            }],
        }
    }
    fn emitted(values: &[(f32, f32)], mode: Mode) -> Vec<Ready> {
        let mut ring = Ring::new(values.len(), mode);
        let mut out = Vec::new();
        for (i, &(e, f)) in values.iter().enumerate() {
            if let Some(r) = ring.push(sample(i, e, f)) {
                out.push(r);
            }
            assert!(ring.retained_guides() <= 2);
        }
        if let Some(r) = ring.finish() {
            out.push(r);
        }
        out
    }
    #[test]
    fn complete_floor_transport_keeps_heterogeneous_beta_exactly_once() {
        // gate2 * beta[.2,2,10] * V[10,2,.5] = F[4,8,10].
        let out = emitted(&[(12.0, 4.0), (24.0, 8.0), (30.0, 10.0)], Mode::On);
        let b = &out[1].bands().unwrap()[0];
        assert_eq!(b.floor[0], 7.5);
        assert_eq!(b.energy[0], 22.5);
        assert_eq!(b.energy[0] / b.floor[0], 3.0);
        let wrong = 2.0 * 2.0 * (0.25 * 10.0 + 0.5 * 2.0 + 0.25 * 0.5);
        assert!(
            (wrong - b.floor[0]).abs() > 1.0,
            "central-beta-after-V-filter foil accepted"
        );
    }
    #[test]
    fn endpoints_short_stacks_and_off_are_original_exactly_once() {
        for n in [1, 2, 3, 5, 33, 299] {
            for mode in [Mode::Off, Mode::On, Mode::ShiftNeighbors] {
                let out = emitted(&vec![(3.0, 1.0); n], mode);
                assert_eq!(out.len(), n);
                for (i, r) in out.iter().enumerate() {
                    assert_eq!(r.source_index(), i);
                    assert_eq!(
                        r.is_original(),
                        mode == Mode::Off || n < 3 || i == 0 || i == n - 1
                    );
                    if let Some(b) = r.bands() {
                        assert!(b[0].energy.iter().all(|x| x.to_bits() == 3f32.to_bits()));
                    }
                }
            }
        }
    }
    #[test]
    fn reversal_commutes_and_fixed_spatial_neighbor_placebo_has_effect() {
        let values = [
            (1.25, 1.0),
            (30.0, 4.0),
            (0.5, 9.0),
            (60.0, 2.0),
            (3.0, 6.0),
        ];
        let a = emitted(&values, Mode::On);
        let reverse: Vec<_> = values.into_iter().rev().collect();
        let b = emitted(&reverse, Mode::On);
        for i in 1..4 {
            assert_eq!(
                a[i].bands().unwrap()[0].energy,
                b[4 - i].bands().unwrap()[0].energy
            );
            assert_eq!(
                a[i].bands().unwrap()[0].floor,
                b[4 - i].bands().unwrap()[0].floor
            );
        }
        let make = |mode| {
            let mut ring = Ring::new(3, mode);
            let mut left = sample(0, 0.0, 1.0);
            left.bands[0].energy[0] = 16.0;
            let center = sample(1, 0.0, 1.0);
            let mut right = sample(2, 0.0, 1.0);
            right.bands[0].energy[0] = 16.0;
            ring.push(left);
            ring.push(center);
            ring.push(right).unwrap()
        };
        let on = make(Mode::On);
        let shifted = make(Mode::ShiftNeighbors);
        assert_eq!(on.bands().unwrap()[0].energy[0], 8.0);
        assert_eq!(shifted.bands().unwrap()[0].energy[0], 0.0);
        assert_eq!(shifted.bands().unwrap()[0].energy[8], 8.0);
    }
    #[test]
    fn ring_rejects_wrong_index_shape_values_and_lifecycle() {
        assert!(catch_unwind(|| Ring::new(0, Mode::On)).is_err());
        let mut r = Ring::new(3, Mode::On);
        assert!(catch_unwind(AssertUnwindSafe(|| r.push(sample(1, 1.0, 1.0)))).is_err());
        let mut r = Ring::new(3, Mode::Off);
        r.push(sample(0, 1.0, 1.0));
        let mut wrong = sample(1, 1.0, 1.0);
        wrong.binding.config = "other".into();
        assert!(catch_unwind(AssertUnwindSafe(|| r.push(wrong))).is_err());
        let mut r = Ring::new(3, Mode::On);
        r.push(sample(0, 1.0, 1.0));
        let mut wrong = sample(1, 1.0, 1.0);
        wrong.binding.sizes = level_sizes(16, 18, 1);
        wrong.bands[0].size = wrong.binding.sizes[0];
        wrong.bands[0].energy.resize(288, 1.0);
        wrong.bands[0].floor.resize(288, 1.0);
        assert!(catch_unwind(AssertUnwindSafe(|| r.push(wrong))).is_err());
        let mut r = Ring::new(3, Mode::On);
        let mut bad = sample(0, 1.0, 1.0);
        bad.bands[0].floor[0] = f32::NAN;
        assert!(catch_unwind(AssertUnwindSafe(|| r.push(bad))).is_err());
        let mut r = Ring::new(3, Mode::On);
        assert!(catch_unwind(AssertUnwindSafe(|| r.finish())).is_err());
        let mut r = Ring::new(1, Mode::On);
        r.push(sample(0, 1.0, 1.0));
        r.finish();
        assert!(catch_unwind(AssertUnwindSafe(|| r.finish())).is_err());
    }
    type CapturedBand = (usize, Vec<f32>, Vec<f32>);
    #[derive(Default)]
    struct Capture(Mutex<Vec<CapturedBand>>);
    impl MergeObserver for Capture {
        fn supports_absolute_floor(&self) -> bool {
            true
        }
        fn phase(&self, _: FoldPhase) {}
        fn band(&self, b: BandObservation<'_>) {
            if let Some(e) = b.energy {
                let f = if let Some(f) = b.absolute_floor {
                    assert!(b.variance.is_none());
                    assert_eq!(b.floor_multiplier, 1.0);
                    f.to_vec()
                } else {
                    b.variance
                        .unwrap()
                        .iter()
                        .map(|v| b.floor_multiplier * v.max(0.0))
                        .collect()
                };
                self.0.lock().unwrap().push((b.level, e.to_vec(), f));
            }
        }
    }
    fn source(n: usize, index: usize) -> Vec<f32> {
        (0..n)
            .map(|i| 100.0 + ((i * 17 + index * 13) % 29) as f32)
            .collect()
    }
    #[test]
    fn guide_producer_matches_real_observer_and_off_finish_is_bitwise_identical() {
        let cfg = MergeConfig {
            bands: 3,
            ..Default::default()
        };
        let sizes = level_sizes(64, 64, 3);
        let mut a = BandMerge::new(64, 64, 1, cfg);
        let mut b = BandMerge::new(64, 64, 1, cfg);
        let mut wa = FrameWorkspace::new(&sizes, 1);
        let mut wb = FrameWorkspace::new(&sizes, 1);
        let mut ring = Ring::new(5, Mode::Off);
        let variance = vec![9.0; 4096];
        #[cfg(feature = "spatial-noise-floor")]
        {
            wa.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::Off);
            wb.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::Off);
        }
        for i in 0..5 {
            let image = source(4096, i);
            let planes = [image.as_slice()];
            let beta = [0.6, 0.08];
            let guide = b.temporal_guide(i, &planes, &image, &variance, Some(&beta), &mut wb);
            let observed = Capture::default();
            wa.next_frame();
            a.add_frame_with_gain_observed(
                &planes,
                &image,
                &variance,
                Some(&beta),
                &mut wa,
                &observed,
            );
            let captured = observed.0.into_inner().unwrap();
            assert_eq!(captured.len(), 3);
            assert_eq!(guide.bands().len(), 2);
            for (k, g) in guide.bands().iter().enumerate() {
                assert_eq!(captured[k].0, k);
                assert_eq!(captured[k].1, g.energy);
                assert_eq!(captured[k].2, g.floor);
            }
            let ready = ring.push(guide).unwrap();
            b.add_frame_with_temporal_guide(
                i,
                &planes,
                &image,
                &variance,
                Some(&beta),
                &mut wb,
                &ready,
                None,
            );
        }
        assert!(ring.finish().is_none());
        let mut ws = Workspace::new(&sizes);
        let aa = a.finish(&mut ws);
        let bb = b.finish(&mut ws);
        assert_eq!(
            aa[0].iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
            bb[0].iter().map(|v| v.to_bits()).collect::<Vec<_>>()
        );
    }
    #[test]
    fn fold_rejects_wrong_original_and_duplicate_source() {
        let cfg = MergeConfig {
            bands: 1,
            ..Default::default()
        };
        let sizes = level_sizes(32, 32, 1);
        let mut m = BandMerge::new(32, 32, 1, cfg);
        let mut ws = FrameWorkspace::new(&sizes, 1);
        let x = source(1024, 0);
        let v = vec![1.0; 1024];
        let guide = m.temporal_guide(0, &[&x], &x, &v, None, &mut ws);
        let ready = Ready::original(&guide, Mode::Off);
        let mut wrong = x.clone();
        wrong[0] += 1.0;
        assert!(
            catch_unwind(AssertUnwindSafe(|| m.add_frame_with_temporal_guide(
                0,
                &[&wrong],
                &x,
                &v,
                None,
                &mut ws,
                &ready,
                None
            )))
            .is_err()
        );
        let mut wrong_geometry = FrameWorkspace::new(&level_sizes(16, 64, 1), 1);
        assert!(
            catch_unwind(AssertUnwindSafe(|| m.add_frame_with_temporal_guide(
                0,
                &[&x],
                &x,
                &v,
                None,
                &mut wrong_geometry,
                &ready,
                None
            )))
            .is_err()
        );
        m.add_frame_with_temporal_guide(0, &[&x], &x, &v, None, &mut ws, &ready, None);
        assert!(
            catch_unwind(AssertUnwindSafe(|| m.add_frame_with_temporal_guide(
                0,
                &[&x],
                &x,
                &v,
                None,
                &mut ws,
                &ready,
                None
            )))
            .is_err()
        );
    }
    fn isolated_peak(amplitude: f32, variance_value: f32, mode: Mode) -> f32 {
        let cfg = MergeConfig {
            bands: 1,
            exponent: 2.0,
            sharpen_per_octave: 1.0,
            gate: 2.0,
            significance_scale: 0.0,
            mean_coarse: 0,
            ..Default::default()
        };
        let sizes = level_sizes(32, 32, 1);
        let mut merge = BandMerge::new(32, 32, 1, cfg);
        let mut ws = FrameWorkspace::new(&sizes, 1);
        #[cfg(feature = "spatial-noise-floor")]
        ws.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::Off);
        let variance = vec![variance_value; 1024];
        let beta = [1.0];
        let mut ring = Ring::new(5, mode);
        let original = |index| {
            (0..1024)
                .map(|i| {
                    128.0
                        + if index == 2 {
                            if (i % 32 + i / 32) % 2 == 0 {
                                amplitude
                            } else {
                                -amplitude
                            }
                        } else {
                            0.0
                        }
                })
                .collect::<Vec<f32>>()
        };
        for index in 0..5 {
            let image = original(index);
            let guide =
                merge.temporal_guide(index, &[&image], &image, &variance, Some(&beta), &mut ws);
            if let Some(ready) = ring.push(guide) {
                let center = original(ready.source_index());
                merge.add_frame_with_temporal_guide(
                    ready.source_index(),
                    &[&center],
                    &center,
                    &variance,
                    Some(&beta),
                    &mut ws,
                    &ready,
                    None,
                );
            }
        }
        if let Some(ready) = ring.finish() {
            let center = original(ready.source_index());
            merge.add_frame_with_temporal_guide(
                ready.source_index(),
                &[&center],
                &center,
                &variance,
                Some(&beta),
                &mut ws,
                &ready,
                None,
            );
        }
        merge.finish(&mut Workspace::new(&sizes))[0][16 * 32 + 16] - 128.0
    }
    #[test]
    fn actual_consumer_exposes_strong_and_weak_single_frame_peak_losses_at_p2() {
        // Explicit p2 diagnostic, not the seven-band production p8 claim.
        // E=10000 >> F retains about2/3 of a truly isolated source coefficient.
        let baseline = isolated_peak(100.0, 0.001, Mode::Off);
        let filtered = isolated_peak(100.0, 0.001, Mode::On);
        assert!((baseline - 100.0).abs() < 0.001);
        assert!((filtered / baseline - 2.0 / 3.0).abs() < 0.001);
        // E=1, F=.75: original passes, filtered center E=.5 fails. All-source
        // mean fallback then retains only1/5 of this real one-frame signal.
        let baseline = isolated_peak(1.0, 0.375, Mode::Off);
        let filtered = isolated_peak(1.0, 0.375, Mode::On);
        assert!((baseline - 1.0).abs() < 0.001);
        assert!((filtered - 0.2).abs() < 0.001);
    }
    #[test]
    fn non_mean_fallback_is_rejected_before_guide_measurement() {
        let cfg = MergeConfig {
            bands: 1,
            fallback: Fallback::Best,
            ..Default::default()
        };
        let sizes = level_sizes(16, 16, 1);
        let merge = BandMerge::new(16, 16, 1, cfg);
        let mut ws = FrameWorkspace::new(&sizes, 1);
        let image = source(256, 0);
        let variance = vec![1.0; 256];
        assert!(
            catch_unwind(AssertUnwindSafe(|| merge.temporal_guide(
                0,
                &[&image],
                &image,
                &variance,
                None,
                &mut ws
            )))
            .is_err()
        );
    }

    #[test]
    fn canonical_source_ranges_bind_global_identity_and_reset_explicitly() {
        let cfg = MergeConfig {
            bands: 1,
            ..Default::default()
        };
        let sizes = level_sizes(16, 16, 1);
        let mut merge = BandMerge::new(16, 16, 1, cfg);
        let mut ws = FrameWorkspace::new(&sizes, 1);
        #[cfg(feature = "spatial-noise-floor")]
        ws.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::Off);
        let variance = vec![1.0; 256];
        merge.set_temporal_source_range(5..7);
        assert!(catch_unwind(AssertUnwindSafe(|| merge.set_temporal_source_range(5..8))).is_err());
        for index in 5..7 {
            let image = source(256, index);
            let guide = merge.temporal_guide(index, &[&image], &image, &variance, None, &mut ws);
            let ready = Ready::original(&guide, Mode::Off);
            if index == 5 {
                assert!(
                    catch_unwind(AssertUnwindSafe(|| merge.add_frame_with_temporal_guide(
                        0,
                        &[&image],
                        &image,
                        &variance,
                        None,
                        &mut ws,
                        &ready,
                        None
                    )))
                    .is_err()
                );
                assert_eq!(merge.frames(), 0);
            }
            merge.add_frame_with_temporal_guide(
                index,
                &[&image],
                &image,
                &variance,
                None,
                &mut ws,
                &ready,
                None,
            );
        }
        let image = source(256, 7);
        let guide = merge.temporal_guide(7, &[&image], &image, &variance, None, &mut ws);
        let ready = Ready::original(&guide, Mode::Off);
        assert!(
            catch_unwind(AssertUnwindSafe(|| merge.add_frame_with_temporal_guide(
                7,
                &[&image],
                &image,
                &variance,
                None,
                &mut ws,
                &ready,
                None
            )))
            .is_err()
        );
        assert_eq!(merge.frames(), 2);
        assert!(catch_unwind(AssertUnwindSafe(|| merge.set_temporal_source_range(7..8))).is_err());
        merge.reset_for_reuse();
        merge.set_temporal_source_range(7..8);
        merge.add_frame_with_temporal_guide(
            7,
            &[&image],
            &image,
            &variance,
            None,
            &mut ws,
            &ready,
            None,
        );
        assert_eq!(merge.frames(), 1);
    }

    #[test]
    fn unsupported_observer_is_rejected_before_temporal_accumulation() {
        struct Legacy;
        impl MergeObserver for Legacy {
            fn phase(&self, _: FoldPhase) {}
            fn band(&self, _: BandObservation<'_>) {}
        }
        let cfg = MergeConfig {
            bands: 1,
            ..Default::default()
        };
        let sizes = level_sizes(16, 16, 1);
        let mut merge = BandMerge::new(16, 16, 1, cfg);
        let mut ws = FrameWorkspace::new(&sizes, 1);
        #[cfg(feature = "spatial-noise-floor")]
        ws.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::Off);
        let image = source(256, 0);
        let variance = vec![1.0; 256];
        let guide = merge.temporal_guide(0, &[&image], &image, &variance, None, &mut ws);
        let ready = Ready {
            binding: guide.binding,
            mode: Mode::On,
            bands: Some(guide.bands),
            neighbors: Some([0, 2]),
        };
        assert!(
            catch_unwind(AssertUnwindSafe(|| merge.add_frame_with_temporal_guide(
                0,
                &[&image],
                &image,
                &variance,
                None,
                &mut ws,
                &ready,
                Some(&Legacy)
            )))
            .is_err()
        );
        assert_eq!(merge.frames(), 0);
    }

    #[cfg(feature = "spatial-noise-floor")]
    #[test]
    fn regather_workspace_rejects_spatial_mode_even_for_constant_original_endpoint() {
        let cfg = MergeConfig {
            bands: 1,
            ..Default::default()
        };
        let sizes = level_sizes(16, 16, 1);
        let mut merge = BandMerge::new(16, 16, 1, cfg);
        let mut ws = FrameWorkspace::new(&sizes, 1);
        ws.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::Off);
        let image = source(256, 0);
        let variance = vec![1.0; 256];
        let guide = merge.temporal_guide(0, &[&image], &image, &variance, None, &mut ws);
        let ready = Ready::original(&guide, Mode::On);
        let mut other = FrameWorkspace::new(&sizes, 1);
        other.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::On);
        assert!(
            catch_unwind(AssertUnwindSafe(|| merge.add_frame_with_temporal_guide(
                0,
                &[&image],
                &image,
                &variance,
                None,
                &mut other,
                &ready,
                None
            )))
            .is_err()
        );
        assert_eq!(merge.frames(), 0);
        assert!(
            catch_unwind(AssertUnwindSafe(|| merge.temporal_guide(
                0,
                &[&image],
                &image,
                &variance,
                None,
                &mut other
            )))
            .is_err()
        );
    }

    #[test]
    fn temporal_filter_leaves_all_coarse_base_and_source_hull_accumulators_exact() {
        let cfg = MergeConfig {
            bands: 4,
            gate: 2.0,
            significance_scale: 0.0,
            mean_coarse: 0,
            hull: super::super::Hull::PerLevel,
            ..Default::default()
        };
        let sizes = level_sizes(64, 64, 4);
        assert!(sizes.len() > 3);
        let mut legacy = BandMerge::new(64, 64, 4, cfg);
        let mut candidate = BandMerge::new(64, 64, 4, cfg);
        let mut old_ws = FrameWorkspace::new(&sizes, 4);
        let mut new_ws = FrameWorkspace::new(&sizes, 4);
        #[cfg(feature = "spatial-noise-floor")]
        {
            old_ws.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::Off);
            new_ws.set_spatial_noise_floor_mode(crate::spatial_noise_floor::Mode::Off);
        }
        let originals = |index| {
            (0..4)
                .map(|c| source(4096, index + c * 3))
                .collect::<Vec<_>>()
        };
        let variance = vec![3.5; 4096];
        let beta = [0.6, 0.08];
        let mut ring = Ring::new(5, Mode::On);
        for next in 0..=5 {
            let ready = if next < 5 {
                let original = originals(next);
                let refs = original.iter().map(Vec::as_slice).collect::<Vec<_>>();
                let guide = candidate.temporal_guide(
                    next,
                    &refs,
                    &original[1],
                    &variance,
                    Some(&beta),
                    &mut new_ws,
                );
                ring.push(guide)
            } else {
                ring.finish()
            };
            let Some(ready) = ready else {
                continue;
            };
            let original = originals(ready.source_index());
            let refs = original.iter().map(Vec::as_slice).collect::<Vec<_>>();
            old_ws.next_frame();
            legacy.add_frame_with_gain(&refs, &original[1], &variance, Some(&beta), &mut old_ws);
            candidate.add_frame_with_temporal_guide(
                ready.source_index(),
                &refs,
                &original[1],
                &variance,
                Some(&beta),
                &mut new_ws,
                &ready,
                None,
            );
            let bits = |x: &[f32]| x.iter().map(|v| v.to_bits()).collect::<Vec<_>>();
            for k in 2..sizes.len() {
                assert_eq!(bits(&legacy.den[k]), bits(&candidate.den[k]));
                for c in 0..4 {
                    let slot = k * 4 + c;
                    assert_eq!(bits(&legacy.num[slot]), bits(&candidate.num[slot]));
                    assert_eq!(bits(&legacy.usum[slot]), bits(&candidate.usum[slot]));
                }
                if !legacy.dmax.is_empty() {
                    assert_eq!(bits(&legacy.dmax[k]), bits(&candidate.dmax[k]));
                    assert_eq!(legacy.darg[k], candidate.darg[k]);
                    assert_eq!(
                        legacy.dsq[k]
                            .iter()
                            .map(|v| v.to_bits())
                            .collect::<Vec<_>>(),
                        candidate.dsq[k]
                            .iter()
                            .map(|v| v.to_bits())
                            .collect::<Vec<_>>()
                    );
                }
            }
            for (a, b) in legacy
                .lo
                .iter()
                .chain(&legacy.hi)
                .chain(&legacy.lo_lv)
                .chain(&legacy.hi_lv)
                .chain(&legacy.sig_lv)
                .zip(
                    candidate
                        .lo
                        .iter()
                        .chain(&candidate.hi)
                        .chain(&candidate.lo_lv)
                        .chain(&candidate.hi_lv)
                        .chain(&candidate.sig_lv),
                )
            {
                assert_eq!(bits(a), bits(b));
            }
            assert!(legacy.best.is_empty() && candidate.best.is_empty());
            assert!(legacy.fkey.is_empty() && candidate.fkey.is_empty());
            assert!(legacy.fval.is_empty() && candidate.fval.is_empty());
            assert_eq!(legacy.frames(), candidate.frames());
        }
    }
}
