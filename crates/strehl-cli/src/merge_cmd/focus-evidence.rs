//! `strehl stack --focus-evidence`: focus evidence for an ordinary stack
//! (implementation plan E5, P8). Off by default.
//!
//! After the photograph and any linear master are written, the stack's RAWs
//! are read again through the shared focus pass ([`crate::focus_pass`], the
//! pass multi-stack sessions use) at the render's own alignment, analysis
//! domain and injected noise model. The full-resolution field is reduced to a
//! compact per-area field on the evidence file's level-0 lattice and appended
//! to the run's `evidence.strehl` (created when the desktop's progress did not
//! create one):
//!
//! - kind 4, focus depth: per area, the median measured acquisition ordinal
//!   of its usable pixels, quantised `0..=254` over `[0, frames - 1]`; 255
//!   where none of the area is usable. An order of planes, not a measured
//!   distance. A reader draws an area only when enough of it is usable
//!   (the summary's flag uses [`MIN_AREA_SHARE`]).
//! - kind 5, focus share: per area, the share of its pixels with usable
//!   evidence (`FocusEvidence::usable`), `0..=255` over `[0, 1]`.
//! - kind 6, focus summary: whether the field is usable and, if not, why.
//!
//! An area is lattice cell `(i, j)` of `[w, h]`: analysis-domain pixels
//! `x` in `[i W / w, (i + 1) W / w)` and `y` likewise.
//!
//! The pass reads the RAWs and the alignment and writes only the evidence
//! file: the photograph's bytes are those of a render without it (checked by
//! hash with it on, off and as a placebo, engineering ledger rule 26). The
//! placebo (`STREHL_FOCUS_EVIDENCE=placebo`) runs the whole pass and writes
//! nothing.
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc;

use anyhow::{Result, bail};
use strehl_core::focus_evidence::FocusEvidence;
use strehl_core::noise::NoiseModel;
use strehl_core::pyramid::LevelSize;
use strehl_core::warpmap::WarpMap;

use super::{MergeOptions, PyramidDomain};
use crate::focus_pass::{FocusFrames, FocusPass};
use crate::session_sampling::SamplingDomain;
use crate::ui_progress::EvidenceKind;

/// The environment switch for harnesses: `on`, `off` (the default) or
/// `placebo`. `--focus-evidence` wins.
pub(super) const ENV: &str = "STREHL_FOCUS_EVIDENCE";
/// The pass's memory reservation limit in GiB (default
/// [`DEFAULT_MEMORY_GIB`], the multi-stack sessions' default limit).
pub(super) const MEMORY_ENV: &str = "STREHL_FOCUS_EVIDENCE_MEMORY_GIB";
const DEFAULT_MEMORY_GIB: f64 = 16.0;
/// The smallest share of an area's pixels with usable evidence for the field
/// to count the area as drawn (the summary's flag; readers may ask more).
pub(crate) const MIN_AREA_SHARE: f32 = 0.25;
/// The depth byte of an area with no usable pixel.
pub(crate) const NO_DEPTH: u8 = 255;
/// The summary record's format.
const SUMMARY_FORMAT: u8 = 1;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum Mode {
    Off,
    On,
    Placebo,
}

/// `--focus-evidence` was given (set once, before the render).
static REQUESTED: AtomicBool = AtomicBool::new(false);

pub(crate) fn request() {
    REQUESTED.store(true, Ordering::Relaxed);
}

pub(super) fn mode() -> Result<Mode> {
    if REQUESTED.load(Ordering::Relaxed) {
        return Ok(Mode::On);
    }
    Ok(match std::env::var(ENV).ok().as_deref() {
        None | Some("") | Some("off") | Some("0") => Mode::Off,
        Some("on") | Some("1") => Mode::On,
        Some("placebo") => Mode::Placebo,
        Some(other) => bail!("{ENV}={other}: use on, off or placebo"),
    })
}

/// Why a field is not usable (the summary's code).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u16)]
pub(crate) enum Reason {
    None = 0,
    TooFewFrames = 1,
    NoAlignment = 2,
    Memory = 3,
    Failed = 4,
    NothingUsable = 5,
}

/// What the render hands the pass: the frames, their placements and the
/// grids, as the fold used them.
pub(super) struct Inputs {
    pub paths: Vec<PathBuf>,
    pub map: Option<WarpMap>,
    pub domain: PyramidDomain,
    pub sizes: Vec<LevelSize>,
    pub noise: NoiseModel,
}

/// The latest finished render's inputs. A render that retries (an optical
/// restoration that measured no depth), refines its lateral colour or folds
/// twice (calibrated fusion) replaces them, so the pass runs once, for the
/// render that wrote the photograph.
static PENDING: Mutex<Option<Inputs>> = Mutex::new(None);

pub(super) fn remember(inputs: Inputs) {
    *PENDING.lock().unwrap_or_else(|e| e.into_inner()) = Some(inputs);
}

/// The compact field and its summary.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Compact {
    pub lattice: [usize; 2],
    pub frames: usize,
    /// Areas whose share reaches [`MIN_AREA_SHARE`].
    pub drawn: usize,
    /// Per area, row-major: the depth byte (or [`NO_DEPTH`]).
    pub depth: Vec<u8>,
    /// Per area: the usable share byte.
    pub share: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Summary {
    pub usable: bool,
    pub reason: Reason,
    pub text: String,
    pub frames: usize,
    pub field: [usize; 2],
    pub usable_pixels: usize,
    pub covered_pixels: usize,
    pub seconds: f32,
    pub reservation_bytes: u64,
    /// Pixels with each refusal flag set (`strehl_core::focus_evidence`
    /// bits 1, 2, 4 ... 64, in that order): why the others are not usable.
    pub flag_pixels: [usize; 7],
}

impl Summary {
    fn refused(reason: Reason, text: String, frames: usize, field: [usize; 2]) -> Self {
        Self {
            usable: false,
            reason,
            text,
            frames,
            field,
            usable_pixels: 0,
            covered_pixels: 0,
            seconds: 0.0,
            reservation_bytes: 0,
            flag_pixels: [0; 7],
        }
    }

    /// The kind-6 payload: `u8 format, u8 usable, u16 reason, u32 frames,
    /// u32 field width, u32 field height, u32 usable pixels, u32 covered
    /// pixels, f32 seconds, u64 reservation bytes, 7 x u32 pixels per refusal
    /// flag, u16 text bytes`, then the reason as UTF-8 (at most 1,024
    /// bytes).
    pub(crate) fn bytes(&self) -> Vec<u8> {
        let mut text = self.text.as_bytes();
        if text.len() > 1024 {
            let mut end = 1024;
            while !self.text.is_char_boundary(end) {
                end -= 1;
            }
            text = &text[..end];
        }
        let mut out = vec![SUMMARY_FORMAT, u8::from(self.usable)];
        out.extend((self.reason as u16).to_le_bytes());
        for value in [
            self.frames,
            self.field[0],
            self.field[1],
            self.usable_pixels,
            self.covered_pixels,
        ] {
            out.extend((value.min(u32::MAX as usize) as u32).to_le_bytes());
        }
        out.extend(self.seconds.to_le_bytes());
        out.extend(self.reservation_bytes.to_le_bytes());
        for count in self.flag_pixels {
            out.extend((count.min(u32::MAX as usize) as u32).to_le_bytes());
        }
        out.extend((text.len() as u16).to_le_bytes());
        out.extend_from_slice(text);
        out
    }
}

/// Reduce the full-resolution field to `lattice` areas.
pub(crate) fn compact(field: &FocusEvidence, lattice: [usize; 2]) -> Compact {
    let [w, h] = lattice;
    let (width, height) = (field.geometry.width, field.geometry.height);
    let frames = field.frames.len();
    let top = (frames.max(2) - 1) as f32;
    let mut depth = vec![NO_DEPTH; w * h];
    let mut share = vec![0u8; w * h];
    let mut ordinals = Vec::new();
    let mut drawn = 0;
    for j in 0..h {
        let (y0, y1) = (j * height / h, (j + 1) * height / h);
        for i in 0..w {
            let (x0, x1) = (i * width / w, (i + 1) * width / w);
            ordinals.clear();
            for y in y0..y1 {
                let row = y * width;
                for x in x0..x1 {
                    let ordinal = field.ordinal[row + x];
                    if field.usable[row + x] && ordinal.is_finite() {
                        ordinals.push(ordinal);
                    }
                }
            }
            let pixels = (y1 - y0) * (x1 - x0);
            if pixels == 0 {
                continue;
            }
            let fraction = ordinals.len() as f32 / pixels as f32;
            // Any usable pixel keeps a nonzero share, as it keeps a depth.
            let byte = (fraction * 255.0).round() as u8;
            share[j * w + i] = if ordinals.is_empty() { 0 } else { byte.max(1) };
            if !ordinals.is_empty() {
                drawn += usize::from(fraction >= MIN_AREA_SHARE);
                let middle = ordinals.len() / 2;
                let (_, median, _) = ordinals.select_nth_unstable_by(middle, f32::total_cmp);
                depth[j * w + i] = ((*median / top).clamp(0.0, 1.0) * 254.0).round() as u8;
            }
        }
    }
    Compact {
        lattice,
        frames,
        drawn,
        depth,
        share,
    }
}

/// The RAWs in the order the pass asks for them, decoded one ahead on a
/// thread of their own (decoding is a pure function of the file).
struct RawFrames<'a> {
    paths: &'a [PathBuf],
    order: std::collections::VecDeque<usize>,
    ahead: mpsc::Receiver<(usize, Result<strehl_raw::Frame>)>,
}

impl FocusFrames for RawFrames<'_> {
    type Source = strehl_raw::Frame;
    fn load(&mut self, global_index: usize) -> Result<strehl_raw::Frame> {
        if self.order.front() == Some(&global_index)
            && let Ok((index, frame)) = self.ahead.recv()
        {
            self.order.pop_front();
            if index == global_index {
                return frame;
            }
        }
        // Out of the planned order: decode here.
        Ok(strehl_raw::decode(&self.paths[global_index])?)
    }
}

fn budget_bytes() -> Result<usize> {
    let gib = match std::env::var(MEMORY_ENV) {
        Ok(value) => value
            .parse::<f64>()
            .ok()
            .filter(|v| v.is_finite() && (1.0..=4096.0).contains(v))
            .ok_or_else(|| anyhow::anyhow!("{MEMORY_ENV}={value}: use GiB in 1..4096"))?,
        Err(_) => DEFAULT_MEMORY_GIB,
    };
    Ok((gib * (1u64 << 30) as f64) as usize)
}

/// The pass over `inputs`, or why it did not run.
fn measure(inputs: &Inputs) -> std::result::Result<FocusPass, Box<Summary>> {
    let domain = SamplingDomain {
        full: inputs.domain.full,
        x: inputs.domain.rect.x,
        y: inputs.domain.rect.y,
        width: inputs.domain.rect.width,
        height: inputs.domain.rect.height,
    };
    let field = [domain.width, domain.height];
    let frames = inputs.paths.len();
    let refuse = |reason, text: String| Box::new(Summary::refused(reason, text, frames, field));
    if frames < 3 {
        return Err(refuse(
            Reason::TooFewFrames,
            format!("{frames} frames; focus evidence needs at least three"),
        ));
    }
    let Some(map) = &inputs.map else {
        return Err(refuse(
            Reason::NoAlignment,
            "the stack was not aligned".into(),
        ));
    };
    let failed = |e: anyhow::Error| refuse(Reason::Failed, format!("{e:#}"));
    if map.resampler() == strehl_core::align::Resampler::ClampedCatmullRom {
        return Err(refuse(
            Reason::Failed,
            "focus evidence requires a linear resampler".into(),
        ));
    }
    let budget = budget_bytes().map_err(failed)?;
    let reserved = crate::focus_pass::reservation_bytes(domain, frames).map_err(failed)?;
    if reserved > budget {
        let gib = |n: usize| n as f64 / (1u64 << 30) as f64;
        return Err(refuse(
            Reason::Memory,
            format!(
                "needs {:.2} GiB; {MEMORY_ENV} allows {:.2} GiB",
                gib(reserved),
                gib(budget)
            ),
        ));
    }
    let sweep: Vec<usize> = (0..frames).collect();
    // Each placed frame twice: the anchor pass, then the shape pass.
    let placed: Vec<usize> = sweep
        .iter()
        .copied()
        .filter(|&i| map.warps()[i].placed().is_some())
        .collect();
    let order: Vec<usize> = placed.iter().chain(&placed).copied().collect();
    let (send, ahead) = mpsc::sync_channel(2);
    let paths = inputs.paths.clone();
    let planned = order.clone();
    let decoder = std::thread::spawn(move || {
        for index in planned {
            let frame = strehl_raw::decode(&paths[index]).map_err(anyhow::Error::from);
            if send.send((index, frame)).is_err() {
                break;
            }
        }
    });
    let mut source = RawFrames {
        paths: &inputs.paths,
        order: order.into(),
        ahead,
    };
    let result = crate::focus_pass::compute(
        &mut source,
        &sweep,
        map,
        domain,
        &inputs.noise,
        None,
        budget,
        "focus evidence  :",
    );
    drop(source);
    let _ = decoder.join();
    result.map_err(failed)
}

/// Run the pass for the render that wrote the photograph, if asked, and
/// write its records. A pass that cannot run, or fails, says why in the
/// summary; it never fails the render.
pub(super) fn run_pending(opts: &MergeOptions) -> Result<()> {
    let mode = mode()?;
    let pending = PENDING.lock().unwrap_or_else(|e| e.into_inner()).take();
    let Some(inputs) = pending.filter(|_| mode != Mode::Off) else {
        return Ok(());
    };
    let Some(out) = opts.out.as_deref() else {
        eprintln!("focus evidence  : not run (no --out to write beside)");
        return Ok(());
    };
    eprintln!(
        "focus evidence  : {} frames{}",
        inputs.paths.len(),
        if mode == Mode::Placebo {
            " (placebo: nothing is written)"
        } else {
            ""
        }
    );
    let started = std::time::Instant::now();
    let measured = measure(&inputs);
    let seconds = started.elapsed().as_secs_f32();
    if mode == Mode::Placebo {
        match &measured {
            Ok(pass) => eprintln!(
                "focus evidence  : placebo, {:.1} s, {} usable pixels, nothing written",
                seconds,
                pass.field.usable.iter().filter(|&&u| u).count()
            ),
            Err(summary) => eprintln!("focus evidence  : placebo, {}", summary.text),
        }
        return Ok(());
    }
    let written = write(out, &inputs, measured, seconds);
    match written {
        Ok((path, summary)) => eprintln!(
            "focus evidence  : {} in {:.1} s ({}), {}",
            if summary.usable {
                "usable"
            } else {
                "not usable"
            },
            seconds,
            if summary.text.is_empty() {
                format!(
                    "{} of {} pixels usable",
                    summary.usable_pixels,
                    summary.field[0] * summary.field[1]
                )
            } else {
                summary.text.clone()
            },
            path.display()
        ),
        Err(why) => eprintln!("focus evidence  : not written ({why})"),
    }
    Ok(())
}

fn write(
    out: &Path,
    inputs: &Inputs,
    measured: std::result::Result<FocusPass, Box<Summary>>,
    seconds: f32,
) -> std::result::Result<(PathBuf, Summary), String> {
    let mut summary_out = None;
    let path = crate::ui_progress::write_focus_records(
        out,
        &inputs.sizes,
        inputs.paths.len(),
        |lattice| {
            let mut records = Vec::new();
            let summary = match measured {
                Ok(pass) => {
                    let field = &pass.field;
                    let compact = compact(field, lattice);
                    let usable = compact.drawn > 0;
                    let summary = Summary {
                        usable,
                        reason: if usable {
                            Reason::None
                        } else {
                            Reason::NothingUsable
                        },
                        text: if usable {
                            String::new()
                        } else {
                            format!(
                                "no area has {:.0} % of its pixels usable",
                                MIN_AREA_SHARE * 100.0
                            )
                        },
                        frames: field.frames.len(),
                        field: [field.geometry.width, field.geometry.height],
                        usable_pixels: field.usable.iter().filter(|&&u| u).count(),
                        covered_pixels: field.covered.iter().filter(|&&c| c).count(),
                        seconds,
                        reservation_bytes: pass.reservation_bytes as u64,
                        flag_pixels: std::array::from_fn(|bit| {
                            field.flags.iter().filter(|&&f| f & (1 << bit) != 0).count()
                        }),
                    };
                    let top = (compact.frames.max(2) - 1) as f32;
                    let float = |values: &[u8], max: f32| {
                        [&0f32.to_le_bytes()[..], &max.to_le_bytes(), values].concat()
                    };
                    records.push((EvidenceKind::FocusDepth, float(&compact.depth, top)));
                    records.push((EvidenceKind::FocusShare, float(&compact.share, 1.0)));
                    summary
                }
                Err(summary) => Summary {
                    seconds,
                    ..*summary
                },
            };
            records.insert(0, (EvidenceKind::FocusSummary, summary.bytes()));
            summary_out = Some(summary);
            records
        },
    )?;
    Ok((path, summary_out.expect("records were built")))
}

#[cfg(test)]
#[path = "focus-evidence-tests.rs"]
mod tests;
