// EXPERIMENT ONLY: compiled solely by the m194h-pedestal-causality feature.
// Called by the actual BandMerge; no alternate merge/collapse implementation.
use super::*;
use std::collections::BTreeSet;
use std::sync::atomic::{AtomicU64, Ordering};

pub const TRACE_WORD_CAP: usize = 32 * 1024;
pub const FORMAT_VERSION: u32 = 1;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Arm { H, P, P0 }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Observation { Off, On, Placebo }
impl Arm {
    pub fn name(self) -> &'static str { match self { Self::H => "H", Self::P => "P", Self::P0 => "P0" } }
    pub fn admission(self) -> AdmissionMode { if self == Self::H { AdmissionMode::HardFloor } else { AdmissionMode::FloorPedestalV1 } }
}
impl Observation {
    pub fn name(self) -> &'static str { match self { Self::Off => "off", Self::On => "on", Self::Placebo => "placebo" } }
}

#[derive(Debug)]
pub struct Snapshot {
    pub arm: Arm,
    pub observation: Observation,
    pub production: bool,
    pub sizes: Vec<LevelSize>,
    pub support: Vec<Vec<usize>>,
    // TLV u32 stream. Each record is tag, payload_word_count, payload words.
    // Floats are original f32 bits. No decimal round trip occurs in the core.
    pub words: Vec<u32>,
    pub frames: usize,
    pub band_calls: usize,
    pub base_calls: usize,
    pub resolved_calls: usize,
    pub pre_hull_calls: usize,
    pub post_hull_calls: usize,
    pub absorb_calls: usize,
    pub reset_calls: usize,
    pub observer_records: usize,
    pub placebo_records: usize,
    pub complete: bool,
}
struct Active { id: u64, value: Snapshot, next_band: usize }
static ACTIVE: Mutex<Option<Active>> = Mutex::new(None);
static NEXT: AtomicU64 = AtomicU64::new(1);
fn active() -> std::sync::MutexGuard<'static, Option<Active>> {
    // A caught, experiment-local assertion must not prevent RAII restoration.
    ACTIVE.lock().unwrap_or_else(std::sync::PoisonError::into_inner)
}

// Exact nonzero dependency indices of expand_tap, retaining clamped aliases
// once. The independent checker derives influence coefficients separately.
fn predecessors(x: usize, n: usize) -> Vec<usize> {
    let c = x / 2;
    let mut out = if x % 2 == 0 {
        vec![c.saturating_sub(1), c, (c + 1).min(n - 1)]
    } else { vec![c, (c + 1).min(n - 1)] };
    out.sort_unstable(); out.dedup(); out
}
fn inverse_support(sizes: &[LevelSize], roots: BTreeSet<usize>) -> Vec<Vec<usize>> {
    let mut out = vec![roots.into_iter().collect::<Vec<_>>()];
    for k in 1..sizes.len() {
        let fine = sizes[k - 1]; let coarse = sizes[k];
        let mut sites = BTreeSet::new();
        for &j in &out[k - 1] {
            for y in predecessors(j / fine.width, coarse.height) {
                for x in predecessors(j % fine.width, coarse.width) {
                    sites.insert(y * coarse.width + x);
                }
            }
        }
        out.push(sites.into_iter().collect());
    }
    assert!(out.iter().all(|v| v.len() <= 128), "M194h support cap");
    out
}
fn production_support() -> (Vec<LevelSize>, Vec<Vec<usize>>) {
    let sizes = level_sizes(150, 113, 3);
    assert_eq!(sizes.len(), 4);
    // Full 5x5 native MHC envelopes, then a conservative all-four-plane union.
    // Original native coordinates minus the admitted crop offset (10,8).
    let mut roots = BTreeSet::new();
    for (x, y) in [(192usize, 96usize), (195, 105)] {
        for ny in y-2..=y+2 { for nx in x-2..=x+2 {
            roots.insert((ny / 2) * 150 + nx / 2);
        }}
    }
    let support = inverse_support(&sizes, roots); (sizes, support)
}

/// One process-wide, explicitly armed experiment. No environment fallback.
/// The ignored bridge runs one render in the process; ordinary builds omit it.
pub struct Session { id: u64, armed: bool }
impl Session {
    pub fn production(arm: Arm, observation: Observation) -> Self {
        let (sizes, support) = production_support();
        Self::start(arm, observation, true, sizes, support)
    }
    #[cfg(test)]
    fn component(arm: Arm, observation: Observation) -> Self {
        let sizes = level_sizes(80, 64, 3);
        let support = inverse_support(&sizes, BTreeSet::from([24 * 80 + 32]));
        Self::start(arm, observation, false, sizes, support)
    }
    fn start(arm: Arm, observation: Observation, production: bool, sizes: Vec<LevelSize>, support: Vec<Vec<usize>>) -> Self {
        let mut slot = active(); assert!(slot.is_none(), "M194h concurrent session");
        let id = NEXT.fetch_add(1, Ordering::Relaxed);
        *slot = Some(Active { id, next_band: 0, value: Snapshot {
            arm, observation, production, sizes, support, words: Vec::new(),
            frames: 0, band_calls: 0, base_calls: 0, resolved_calls: 0,
            pre_hull_calls: 0, post_hull_calls: 0, absorb_calls: 0, reset_calls: 0,
            observer_records: 0, placebo_records: 0, complete: false,
        }});
        Self { id, armed: true }
    }
    /// Also returns a retained incomplete prefix after an unsuccessful render.
    pub fn take(mut self) -> Snapshot {
        let mut slot = active();
        assert_eq!(slot.as_ref().map(|s| s.id), Some(self.id));
        let mut state = slot.take().unwrap(); self.armed = false;
        let v = &mut state.value;
        v.complete = v.frames == 5 && state.next_band == 0 && v.band_calls == 15
            && v.base_calls == 5 && v.resolved_calls == 16
            && v.pre_hull_calls == 4 && v.post_hull_calls == 4;
        std::mem::replace(v, empty_snapshot())
    }
}
fn empty_snapshot() -> Snapshot {
    Snapshot { arm: Arm::H, observation: Observation::Off, production: false,
        sizes: Vec::new(), support: Vec::new(), words: Vec::new(), frames: 0,
        band_calls: 0, base_calls: 0, resolved_calls: 0, pre_hull_calls: 0,
        post_hull_calls: 0, absorb_calls: 0, reset_calls: 0,
        observer_records: 0, placebo_records: 0, complete: false }
}
impl Drop for Session {
    fn drop(&mut self) { if self.armed {
        let mut slot = active();
        if slot.as_ref().is_some_and(|s| s.id == self.id) { *slot = None; }
    }}
}
fn record(v: &mut Snapshot, tag: u32, payload: &[u32]) {
    match v.observation {
        Observation::Off => {},
        Observation::Placebo => { std::hint::black_box((tag, payload)); v.placebo_records += 1; },
        Observation::On => {
            assert!(v.words.len() + payload.len() + 2 <= TRACE_WORD_CAP, "M194h trace capacity");
            v.words.push(tag); v.words.push(payload.len() as u32);
            v.words.extend_from_slice(payload); v.observer_records += 1;
        }
    }
}
fn validate_merge(v: &Snapshot, merge: &BandMerge) {
    assert_eq!(merge.sizes, v.sizes, "M194h actual quad grid");
    assert_eq!(merge.planes, 4, "M194h four CFA planes");
    let c = merge.cfg;
    assert!(c.admission == v.arm.admission() && c.bands == 3
        && c.select == SelectMode::SoftPower && c.base == BaseBand::Mean
        && c.fallback == Fallback::Mean && c.mean_coarse == 0
        && c.significance_scale == 0.0 && c.hull == Hull::InputRange,
        "M194h unsupported consumer configuration");
}
fn bits(v: f32) -> u32 { assert!(v.is_finite(), "M194h nonfinite operand"); v.to_bits() }

pub(super) fn begin_frame(merge: &BandMerge, frame_beta: Option<&[f32]>) {
    let mut slot = active(); let Some(s) = slot.as_mut() else { return };
    validate_merge(&s.value, merge);
    assert!(s.next_band == 0 && s.value.base_calls == s.value.frames && s.value.frames < 5 && s.value.resolved_calls == 0, "M194h frame lifecycle");
    s.value.frames += 1;
    let mut row = vec![(s.value.frames - 1) as u32, merge.frames, frame_beta.map_or(0, |x| x.len()) as u32,
        bits(merge.cfg.gate), bits(merge.cfg.exponent), bits(merge.cfg.sharpen_per_octave)];
    for k in 0..3 { row.push(bits(BandMerge::beta_for(&merge.gain, frame_beta, k))); }
    record(&mut s.value, 1, &row);
}
/// The sole counterfactual arithmetic: preserve the already computed P weight
/// above F, and zero precisely E<=F. H/P do not rewrite any weight.
fn cutoff(arm: Arm, energy: f32, floor: f32, weight: &mut f32) {
    if arm == Arm::P0 && energy <= floor { *weight = 0.0; }
}
pub(super) fn band(merge: &BandMerge, k: usize, planes: &[&[f32]], cache: &mut PlaneCache,
    energy: &[f32], variance: &[f32], beta: f32, weights: &mut [f32]) {
    let mut slot = active(); let Some(s) = slot.as_mut() else { return };
    validate_merge(&s.value, merge);
    assert!(s.value.frames > 0 && s.next_band == k && k < 3, "M194h band lifecycle");
    let gate = merge.cfg.gate;
    if s.value.arm == Arm::P0 {
        for ((w, &e), &v) in weights.iter_mut().zip(energy).zip(variance) {
            cutoff(Arm::P0, e, gate * beta * v.max(0.0), w);
        }
    }
    s.next_band += 1; s.value.band_calls += 1;
    if s.value.observation == Observation::Off { return; }
    cache.ensure(planes, &merge.sizes);
    let p = merge.cfg.exponent_at(k, 3);
    for j in s.value.support[k].clone() {
        let e = energy[j]; let f = gate * beta * variance[j].max(0.0);
        let h = select_weight((e-f).max(0.0), f, p, 0.0);
        let pw = pedestal_weight(e, f, p);
        let mut row = vec![(s.value.frames - 1) as u32, k as u32, j as u32,
            bits(e), bits(f), bits(h), bits(pw), bits(weights[j]), u32::from(e > f)];
        for c in 0..4 { row.push(bits(cache.pyramids[c].level(k)[j])); }
        record(&mut s.value, 2, &row);
    }
}
pub(super) fn base(merge: &BandMerge, planes: &[&[f32]], cache: &mut PlaneCache) {
    let mut slot = active(); let Some(s) = slot.as_mut() else { return };
    assert_eq!(s.next_band, 3, "M194h base lifecycle");
    s.next_band = 0; s.value.base_calls += 1;
    if s.value.observation == Observation::Off { return; }
    cache.ensure(planes, &merge.sizes);
    for j in s.value.support[3].clone() {
        let mut row = vec![(s.value.frames - 1) as u32, j as u32];
        for c in 0..4 { row.push(bits(cache.pyramids[c].level(3)[j])); }
        record(&mut s.value, 3, &row);
    }
}
pub(super) fn resolved(merge: &BandMerge, plane: usize, k: usize, values: &[f32]) {
    let mut slot = active(); let Some(s) = slot.as_mut() else { return };
    validate_merge(&s.value, merge);
    assert!(s.value.frames == 5 && merge.frames == 5 && s.next_band == 0
        && s.value.resolved_calls == plane * 4 + k, "M194h resolved lifecycle");
    s.value.resolved_calls += 1;
    if s.value.observation == Observation::Off { return; }
    let i = k * 4 + plane;
    for j in s.value.support[k].clone() {
        record(&mut s.value, 4, &[plane as u32, k as u32, j as u32,
            bits(merge.num[i][j]), bits(merge.den[k][j]), bits(merge.usum[i][j]),
            bits(values[j]), u32::from(merge.den[k][j] <= 0.0)]);
    }
}
pub(super) fn pre_hull(merge: &BandMerge, plane: usize, values: &[f32]) {
    let mut slot = active(); let Some(s) = slot.as_mut() else { return };
    assert_eq!(s.value.pre_hull_calls, plane, "M194h pre-hull order");
    s.value.pre_hull_calls += 1;
    if s.value.observation == Observation::Off { return; }
    for j in s.value.support[0].clone() {
        record(&mut s.value, 5, &[plane as u32, j as u32, bits(values[j]), bits(merge.lo[plane][j]), bits(merge.hi[plane][j])]);
    }
}
pub(super) fn post_hull(plane: usize, values: &[f32]) {
    let mut slot = active(); let Some(s) = slot.as_mut() else { return };
    assert_eq!(s.value.post_hull_calls, plane, "M194h post-hull order");
    s.value.post_hull_calls += 1;
    if s.value.observation == Observation::Off { return; }
    for j in s.value.support[0].clone() { record(&mut s.value, 6, &[plane as u32, j as u32, bits(values[j])]); }
}
pub(super) fn absorb(a: &BandMerge, b: &BandMerge) {
    let mut slot = active(); let Some(s) = slot.as_mut() else { return };
    validate_merge(&s.value, a); validate_merge(&s.value, b);
    s.value.absorb_calls += 1;
    record(&mut s.value, 7, &[a.frames, b.frames]);
}
pub(super) fn reset(merge: &BandMerge) {
    let mut slot = active(); let Some(s) = slot.as_mut() else { return };
    validate_merge(&s.value, merge); s.value.reset_calls += 1;
    record(&mut s.value, 8, &[merge.frames]);
}
/// Powered metadata predicate on actual captured partition rows, shared with
/// the component controls. Independent verification does not trust this helper.
pub fn partition_rows_valid(snapshot: &Snapshot) -> bool {
    let mut at = 0; let mut seen = 0;
    while at < snapshot.words.len() {
        if at + 2 > snapshot.words.len() { return false; }
        let tag = snapshot.words[at]; let n = snapshot.words[at+1] as usize; at += 2;
        if at + n > snapshot.words.len() { return false; }
        let r = &snapshot.words[at..at+n]; at += n;
        if tag == 2 {
            if n != 13 { return false; }
            let e = f32::from_bits(r[3]); let f = f32::from_bits(r[4]);
            if !e.is_finite() || !f.is_finite() || r[8] != u32::from(e > f) { return false; }
            let expected = match snapshot.arm { Arm::H => r[5], Arm::P => r[6], Arm::P0 => if e <= f { 0 } else { r[6] } };
            if r[7] != expected { return false; }
            seen += 1;
        }
    }
    seen > 0
}

#[cfg(test)]
mod controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/m194h-pedestal-causality/component-controls.rs"));
}
