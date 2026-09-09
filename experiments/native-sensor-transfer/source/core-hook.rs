// Experiment-owned passive observer. Included only with native-sensor-transfer.
// No filesystem, decoder, kernel, cache preparation, or mutation of supplied data.
use super::{AdmissionMode, BandMerge, BaseBand, Pyramid, SelectMode};
use std::sync::{Mutex, OnceLock};
use std::sync::atomic::{AtomicU64, Ordering};

pub const SIDES: [usize; 5] = [128, 64, 32, 16, 8];
const MAX_WORDS: usize = 200_000;
const NONE: u32 = u32::MAX;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode { Off, On, Placebo }
impl Mode {
    pub fn code(self) -> u32 { match self { Self::Off => 0, Self::On => 1, Self::Placebo => 2 } }
}
#[derive(Debug)]
pub struct Field {
    pub tag: u32,
    pub level: u32,
    pub plane: u32,
    pub words: Vec<u32>,
}
#[derive(Debug)]
pub struct Snapshot {
    pub identity: [u32; 3], // invocation, original ordinal, route
    pub mode: Mode,
    pub fields: Vec<Field>,
    pub band_visits: usize,
    pub plane_visits: usize,
}
struct Active { id: u64, snapshot: Snapshot, words: usize, begun: bool }
static ACTIVE: OnceLock<Mutex<Option<Active>>> = OnceLock::new();
static NEXT: AtomicU64 = AtomicU64::new(1);
fn state() -> &'static Mutex<Option<Active>> { ACTIVE.get_or_init(|| Mutex::new(None)) }
pub struct Session { id: u64, ended: bool }
pub fn begin(mode: Mode, invocation: u32, original: u32, route: u32) -> Session {
    assert!(invocation < 9 && original < 27 && route < 2, "native observer identity");
    let mut slot = state().lock().expect("native observer lock");
    assert!(slot.is_none(), "native observer nested session");
    let id = NEXT.fetch_add(1, Ordering::Relaxed);
    *slot = Some(Active { id, words: 0, begun: false, snapshot: Snapshot {
        identity: [invocation, original, route], mode, fields: Vec::new(),
        band_visits: 0, plane_visits: 0,
    }});
    Session { id, ended: false }
}
impl Session {
    pub fn finish(mut self) -> Snapshot {
        let mut slot = state().lock().expect("native observer lock");
        assert_eq!(slot.as_ref().map(|a| a.id), Some(self.id), "native observer ownership");
        let a = slot.take().expect("native observer missing session");
        if a.snapshot.mode != Mode::Off {
            assert!(a.begun, "native observer frame not visited");
            assert_eq!(a.snapshot.band_visits, 5, "native observer band population");
            assert_eq!(a.snapshot.plane_visits, 5, "native observer plane population");
            assert_eq!(a.snapshot.fields.len(), 46, "native observer record population");
        } else {
            assert!(a.snapshot.fields.is_empty(), "off observer retained fields");
        }
        self.ended = true;
        a.snapshot
    }
}
impl Drop for Session {
    fn drop(&mut self) {
        if self.ended { return; }
        if let Ok(mut slot) = state().lock() {
            if slot.as_ref().map(|a| a.id) == Some(self.id) { *slot = None; }
        }
    }
}
impl Active {
    fn put(&mut self, tag: u32, level: u32, plane: u32, words: Vec<u32>) {
        self.words = self.words.checked_add(words.len()).expect("observer extent overflow");
        assert!(self.words <= MAX_WORDS && self.snapshot.fields.len() < 64, "observer extent");
        self.snapshot.fields.push(Field { tag, level, plane, words });
    }
    fn array(&mut self, tag: u32, k: usize, plane: u32, values: &[f32]) {
        let n = SIDES[k] * SIDES[k];
        let words = if self.snapshot.mode == Mode::Placebo {
            vec![0; n] // Same allocation/touch extent; values are never inspected.
        } else {
            assert_eq!(values.len(), n, "observer actual array shape");
            values.iter().map(|v| v.to_bits()).collect()
        };
        self.put(tag, k as u32, plane, words);
    }
}
pub(super) fn begin_frame(merge: &BandMerge, beta: Option<&[f32]>) {
    let mut slot = state().lock().expect("native observer lock");
    let Some(a) = slot.as_mut() else { return; };
    if a.snapshot.mode == Mode::Off { return; }
    assert!(!a.begun, "observer repeated frame");
    a.begun = true;
    if a.snapshot.mode == Mode::Placebo {
        a.put(1, NONE, NONE, vec![0; 18]);
        a.put(2, NONE, NONE, vec![0; if a.snapshot.identity[2] == 0 { 0 } else { 3 }]);
        return;
    }
    assert_eq!(merge.planes, 4, "observer CFA plane count");
    assert_eq!(merge.sizes.len(), 5, "observer depth");
    for (s, side) in merge.sizes.iter().zip(SIDES) {
        assert_eq!((s.width, s.height), (side, side), "observer crop levels");
    }
    let c = &merge.cfg;
    assert_eq!(c.bands, 7, "observer requested bands");
    assert_eq!(c.select, SelectMode::SoftPower, "observer selection");
    assert_eq!(c.admission, AdmissionMode::HardFloor, "observer admission");
    assert_eq!(c.base, BaseBand::Mean, "observer base");
    assert_eq!(c.mean_coarse, 0, "observer bypass");
    let b = beta.unwrap_or(&[]);
    assert_eq!(b.len(), if a.snapshot.identity[2] == 0 { 0 } else { 3 }, "observer beta prefix");
    assert!(b.iter().all(|v| v.is_finite()), "observer finite supplied beta");
    a.put(1, NONE, NONE, vec![
        merge.frames as u32, c.bands as u32, 4, c.gate.to_bits(),
        c.exponent.to_bits(), c.sharpen_per_octave.to_bits(),
        c.mean_coarse as u32, c.hull_lambda.to_bits(), c.hull_low_only as u32,
        c.fallback_k as u32, c.fallback_power.to_bits(), c.hull_from_level as u32,
        c.significance_scale.to_bits(), 0, 0, 0, 0, 0,
    ]);
    a.put(2, NONE, NONE, b.iter().map(|v| v.to_bits()).collect());
}
pub(super) fn band(
    merge: &BandMerge, k: usize, averaged: bool, beta: Option<&[f32]>,
    luma: &[f32], variance: &[f32], energy: &[f32], weight: &[f32],
) {
    let mut slot = state().lock().expect("native observer lock");
    let Some(a) = slot.as_mut() else { return; };
    if a.snapshot.mode == Mode::Off { return; }
    assert!(a.begun && k < 4 && a.snapshot.band_visits == k, "observer band order");
    let context = if a.snapshot.mode == Mode::Placebo { vec![0; 9] } else {
        let selected = BandMerge::beta_for(&merge.gain, beta, k);
        vec![0, averaged as u32, beta.is_some_and(|b| k < b.len()) as u32,
            selected.to_bits(), merge.gain.beta(k).to_bits(), merge.cfg.gate.to_bits(),
            merge.cfg.exponent_at(k, 4).to_bits(), merge.cfg.significance_scale.to_bits(),
            (super::significance_floor(merge.cfg.gate) * merge.cfg.significance_scale).to_bits()]
    };
    a.put(3, k as u32, NONE, context);
    a.array(10, k, NONE, luma);
    a.array(11, k, NONE, variance);
    a.array(12, k, NONE, energy);
    a.array(13, k, NONE, weight);
    a.snapshot.band_visits += 1;
}
pub(super) fn base(merge: &BandMerge, k: usize, luma: &[f32], variance: &[f32], weight: &[f32]) {
    let mut slot = state().lock().expect("native observer lock");
    let Some(a) = slot.as_mut() else { return; };
    if a.snapshot.mode == Mode::Off { return; }
    assert!(a.begun && k == 4 && a.snapshot.band_visits == 4, "observer base order");
    let context = if a.snapshot.mode == Mode::Placebo { vec![0; 9] } else {
        assert_eq!(merge.cfg.base, BaseBand::Mean, "observer actual base");
        vec![1, 1, 0, 0, 0, 0, 0, 0, 0] // Explicit base bypass, no gate/beta assertion.
    };
    a.put(3, k as u32, NONE, context);
    a.array(10, k, NONE, luma);
    a.array(11, k, NONE, variance);
    a.array(13, k, NONE, weight);
    a.snapshot.band_visits += 1;
}
pub(super) fn coefficients(k: usize, pyramids: &[Pyramid]) {
    let mut slot = state().lock().expect("native observer lock");
    let Some(a) = slot.as_mut() else { return; };
    if a.snapshot.mode == Mode::Off { return; }
    assert!(a.begun && k < 5 && a.snapshot.plane_visits == k &&
        a.snapshot.band_visits == k + 1, "observer coefficient order");
    if a.snapshot.mode == Mode::On {
        assert_eq!(pyramids.len(), 4, "observer existing coefficient population");
        for (p, pyramid) in pyramids.iter().enumerate() {
            a.array(20, k, p as u32, pyramid.level(k));
        }
    } else {
        for p in 0..4 { a.array(20, k, p, &[]); }
    }
    a.snapshot.plane_visits += 1;
}
