// Test-only renderer factorial; include inside image_out after root review.
// The unchanged current writer remains the control. No environment tuning.
use super::*;
use std::sync::{atomic::{AtomicBool, AtomicU8, Ordering}, Mutex};

#[derive(Clone, Copy, Debug, Eq, PartialEq, serde::Serialize)]
#[serde(rename_all = "kebab-case")]
pub(crate) enum Arm { Current, SensorRolloffOff, Shoulder, Both }
impl Arm {
    pub(crate) fn name(self) -> &'static str {
        match self { Self::Current => "current", Self::SensorRolloffOff => "sensor-rolloff-off",
            Self::Shoulder => "shoulder", Self::Both => "both" }
    }
    fn code(self) -> u8 { match self { Self::Current => 0, Self::SensorRolloffOff => 1,
        Self::Shoulder => 2, Self::Both => 3 } }
    fn from_code(v: u8) -> Self { match v { 0 => Self::Current, 1 => Self::SensorRolloffOff,
        2 => Self::Shoulder, 3 => Self::Both, _ => unreachable!("invalid renderer arm") } }
}

pub(crate) const SHOULDER_KNEE: f32 = 0.75;

/// One fixed C1 shoulder: identity through .75, positive derivative above it,
/// asymptotic to 1. Floating output can reach 1 by rounding at extreme inputs;
/// this is not a guarantee to recover arbitrarily overexposed information.
pub(crate) fn shoulder_luminance(y: f32) -> f32 {
    if y <= SHOULDER_KNEE { y } else {
        SHOULDER_KNEE + (1.0 - SHOULDER_KNEE)
            * (-(-(y - SHOULDER_KNEE) / (1.0 - SHOULDER_KNEE)).exp_m1())
    }
}

/// Common linear-light gain, before the existing gamut decision. No spatial
/// filtering, local contrast normalization, or channel-specific shoulder.
pub(crate) fn shoulder_rgb(v: [f32; 3]) -> [f32; 3] {
    let y = luma709(v);
    if y <= SHOULDER_KNEE { return v; }
    let gain = shoulder_luminance(y) / y;
    [v[0] * gain, v[1] * gain, v[2] * gain]
}

fn candidate_pixel(lin: [f32; 3], dev: &Develop, arm: Arm) -> [u16; 3] {
    assert!(arm != Arm::Current && dev.srgb && dev.tone.is_some() && dev.matrix.is_some(),
        "diagnostic renderer requires resolved colorimetric photographic development");
    let r = dev.matrix.as_ref().unwrap();
    let mut v = if matches!(arm, Arm::SensorRolloffOff | Arm::Both) {
        // Only the existing chroma desaturation is disabled. The original
        // pinned-sample handling and actual matrix are explicitly retained.
        color::apply(r.matrix(), r.clip_highlights(lin))
    } else { r.develop(lin) };
    let tone = dev.tone.as_ref().unwrap();
    let gain = tone.gain(luma709(v)) * dev.exposure_gain;
    v = [v[0] * gain, v[1] * gain, v[2] * gain];
    if matches!(arm, Arm::Shoulder | Arm::Both) { v = shoulder_rgb(v); }
    v = gamut_map(v);
    let mut out = [0u16; 3];
    for c in 0..3 {
        let x = s_curve(color::srgb_encode(v[c]), tone.contrast);
        out[c] = (x * u16::MAX as f32 + 0.5) as u16;
    }
    out
}

/// Independent controls use this explicit arm API without global overrides.
/// The Current arm invokes the actual production function, not a reimplementation.
pub(crate) fn pixel(lin: [f32; 3], dev: &Develop, arm: Arm) -> [u16; 3] {
    assert_eq!(MODE.load(Ordering::Acquire), 0, "explicit controls during an active override");
    if arm == Arm::Current { super::develop_pixel(lin, dev) }
    else { candidate_pixel(lin, dev, arm) }
}

#[derive(Clone, Debug, Eq, PartialEq, serde::Serialize)]
pub(crate) struct Resolved {
    pub tone_bits: Option<[u32; 3]>, pub exposure_gain_bits: u32,
    pub srgb: bool, pub wants_tone: bool,
    pub matrix_bits: Option<[[u32; 3]; 3]>,
    pub ceiling_bits: Option<[u32; 3]>, pub sensor_top_bits: Option<u32>,
}
impl Resolved {
    fn from_dev(dev: &Develop) -> Self {
        Self { tone_bits: dev.tone.map(|t| [t.black.to_bits(), t.white.to_bits(), t.contrast.to_bits()]),
            exposure_gain_bits: dev.exposure_gain.to_bits(), srgb: dev.srgb, wants_tone: dev.wants_tone,
            matrix_bits: dev.matrix.as_ref().map(|r| r.matrix().map(|row| row.map(f32::to_bits))),
            ceiling_bits: dev.matrix.as_ref().map(|r| r.ceiling().map(f32::to_bits)),
            sensor_top_bits: dev.matrix.as_ref().map(|r| r.top().to_bits()) }
    }
}

// Test-only process-global dispatch is serialized for the complete write. The
// per-pixel hook is one atomic read; resolved metadata is recorded once per write.
static RUN: Mutex<()> = Mutex::new(());
static MODE: AtomicU8 = AtomicU8::new(0);
static ACTIVE: AtomicBool = AtomicBool::new(false);
static RESOLVED: Mutex<Option<Resolved>> = Mutex::new(None);
struct Reset;
impl Drop for Reset { fn drop(&mut self) { MODE.store(0, Ordering::Release); ACTIVE.store(false, Ordering::Release); } }

pub(crate) fn with_arm<T>(arm: Arm, write: impl FnOnce() -> anyhow::Result<T>) -> anyhow::Result<(T, Resolved)> {
    let _lock = RUN.try_lock().map_err(|_| anyhow::anyhow!("renderer already active or lock poisoned"))?;
    anyhow::ensure!(!ACTIVE.load(Ordering::Acquire), "nested diagnostic render");
    *RESOLVED.lock().map_err(|_| anyhow::anyhow!("resolved metadata lock poisoned"))? = None;
    let _reset = Reset;
    ACTIVE.store(true, Ordering::Release); MODE.store(arm.code(), Ordering::Release);
    let output = write()?;
    let resolved = RESOLVED.lock().map_err(|_| anyhow::anyhow!("resolved metadata lock poisoned"))?
        .take().ok_or_else(|| anyhow::anyhow!("actual writer did not record resolved development"))?;
    Ok((output, resolved))
}

/// Hook at the start of the actual image_out::develop_pixel. None is a literal
/// bypass, including the Current/observer-only arm.
pub(crate) fn override_pixel(lin: [f32; 3], dev: &Develop) -> Option<[u16; 3]> {
    let arm = Arm::from_code(MODE.load(Ordering::Acquire));
    (arm != Arm::Current).then(|| candidate_pixel(lin, dev, arm))
}

/// Hook immediately after resolve_tone in write_demosaiced. This observes the
/// actual unmodified auto-tone policy; variants never affect tone_from_mosaic.
pub(crate) fn record_resolved(dev: &Develop) {
    if !ACTIVE.load(Ordering::Acquire) { return; }
    let value = Resolved::from_dev(dev);
    let mut slot = RESOLVED.lock().expect("resolved metadata poisoned");
    assert!(slot.is_none(), "diagnostic arm made more than one output write");
    *slot = Some(value);
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/highlight-rendering/independent-controls.rs"));
}
