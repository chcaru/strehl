//! Time left for a render (plan 6.6 step 6, 3 item 8). The engine already
//! prints its stage timings; this reads them without engine changes:
//!
//! ```text
//! frames          : 299 from …  (first decode 0.05 s)
//! alignment       : ON (sidecar), …, 0.0 s
//! folded          : 299 / 299 frames in 155.3 s (0.52 s per frame, …)
//! collapse+write  : 1.9 s
//! total           : 157.3 s
//! ```
//!
//! While a render runs, `frame-finished` events are timestamped as they
//! arrive and give the live rate; before enough have arrived, the previous
//! render of the same stack (its `render.log`, read on a worker) seeds it.
//! A log can hold more than one pass (a quick preview fold, then the full
//! one): a new `strehl stack` header or `stage name=read` starts a pass.
use anyhow::Result;
use std::{
    collections::VecDeque,
    io::{Read, Seek, SeekFrom},
    path::Path,
    sync::atomic::{AtomicBool, Ordering},
    time::{Duration, Instant},
};

/// The bytes read from the end of a previous `render.log`: its summary
/// lines sit within the last few hundred KB even for a 1.3 GB log.
const SEED_TAIL: u64 = 1024 * 1024;
/// Live rate: the newest frame receipts kept.
const SAMPLES: usize = 48;
/// Live rate is trusted after this many frames over at least this long.
const MIN_FRAMES: usize = 8;
const MIN_SPAN: Duration = Duration::from_secs(1);

/// One pass's stage timings, as far as its log has printed them.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct StageTimes {
    pub frames: Option<usize>,
    pub first_decode: Option<f64>,
    pub alignment: Option<f64>,
    /// (folded, of, seconds, seconds per frame)
    pub folded: Option<(usize, usize, f64, f64)>,
    pub collapse_write: Option<f64>,
    pub total: Option<f64>,
}
impl StageTimes {
    /// A pass that folded every frame and finished.
    pub(crate) fn complete(&self) -> bool {
        self.total.is_some()
            && self
                .folded
                .is_some_and(|(done, of, ..)| done == of && of > 0)
    }
    /// Seconds per folded frame.
    pub(crate) fn per_frame(&self) -> Option<f64> {
        let (done, _, seconds, per_frame) = self.folded?;
        (done > 0)
            .then(|| seconds / done as f64)
            .filter(|v| v.is_finite() && *v > 0.0)
            .or(Some(per_frame).filter(|v| v.is_finite() && *v > 0.0))
    }
    /// A whole render of `planes` at this pass's rates (seconds).
    pub(crate) fn estimate(&self, planes: usize) -> Option<f64> {
        let fold = self.per_frame()? * planes as f64;
        Some(fold + self.alignment.unwrap_or(0.0) + self.collapse_write.unwrap_or(0.0))
    }
    fn ingest(&mut self, line: &str) -> bool {
        let Some((key, value)) = line.split_once(':') else {
            return false;
        };
        let value = value.trim();
        match key.trim_end() {
            "frames" => {
                self.frames = value.split_whitespace().next().and_then(|n| n.parse().ok());
                self.first_decode = value
                    .rsplit_once("(first decode ")
                    .and_then(|(_, rest)| seconds_prefix(rest));
            }
            "alignment" => self.alignment = trailing_seconds(value),
            "folded" => {
                // "299 / 299 frames in 155.3 s (0.52 s per frame, …)"
                let mut words = value.split_whitespace();
                let done = words.next().and_then(|n| n.parse().ok());
                let of = words.nth(1).and_then(|n| n.parse().ok());
                let seconds = value
                    .split_once(" frames in ")
                    .and_then(|(_, rest)| seconds_prefix(rest));
                let per_frame = value
                    .split_once('(')
                    .and_then(|(_, rest)| seconds_prefix(rest));
                if let (Some(done), Some(of), Some(seconds)) = (done, of, seconds) {
                    self.folded = Some((done, of, seconds, per_frame.unwrap_or(f64::NAN)));
                }
            }
            "collapse+write" => self.collapse_write = seconds_prefix(value),
            "total" => self.total = seconds_prefix(value),
            _ => return false,
        }
        true
    }
}
/// "155.3 s …" → 155.3
fn seconds_prefix(text: &str) -> Option<f64> {
    let (number, rest) = text.trim_start().split_once(' ')?;
    rest.starts_with('s')
        .then(|| number.parse::<f64>().ok())
        .flatten()
        .filter(|v| v.is_finite() && *v >= 0.0)
}
/// "…, 0.0 s" → 0.0
fn trailing_seconds(text: &str) -> Option<f64> {
    let text = text.trim_end().strip_suffix(" s")?;
    text.rsplit([' ', ','])
        .next()?
        .parse::<f64>()
        .ok()
        .filter(|v| v.is_finite() && *v >= 0.0)
}
fn starts_pass(line: &str) -> bool {
    line.starts_with("strehl stack --")
        || line.starts_with("STREHL_UI_PROGRESS event=stage name=read ")
}

/// Every pass in `text`, oldest first.
pub(crate) fn passes(text: &str) -> Vec<StageTimes> {
    let mut passes: Vec<StageTimes> = Vec::new();
    let mut current = StageTimes::default();
    let mut seen = false;
    for line in text.lines() {
        if starts_pass(line) && seen {
            passes.push(current);
            current = StageTimes::default();
            seen = false;
        }
        seen |= current.ingest(line);
    }
    if seen {
        passes.push(current);
    }
    passes
}
/// The newest complete pass of a previous render: the seed for its stack.
pub(crate) fn seed_from(text: &str) -> Option<StageTimes> {
    passes(text).into_iter().rev().find(StageTimes::complete)
}
/// Read the end of a previous `render.log` (on a worker).
pub(crate) fn read_seed(log: &Path, cancelled: &AtomicBool) -> Result<Option<StageTimes>> {
    let mut file = std::fs::File::open(log)?;
    let length = file.metadata()?.len();
    file.seek(SeekFrom::Start(length.saturating_sub(SEED_TAIL)))?;
    let mut bytes = Vec::with_capacity(length.min(SEED_TAIL) as usize);
    file.take(SEED_TAIL).read_to_end(&mut bytes)?;
    anyhow::ensure!(!cancelled.load(Ordering::Relaxed), "Cancelled");
    let text = String::from_utf8_lossy(&bytes);
    // The first line of a tail may be cut; the summary lines are whole.
    let start = if length > SEED_TAIL {
        text.find('\n').map_or(text.len(), |at| at + 1)
    } else {
        0
    };
    Ok(seed_from(&text[start..]))
}
/// `read_seed` on a worker that wakes the UI when it is done.
pub(crate) fn spawn_seed(
    log: std::path::PathBuf,
    ctx: eframe::egui::Context,
) -> crate::jobs::Task<Option<StageTimes>> {
    crate::jobs::spawn_notifying_task(
        "strehl-render-eta-seed",
        move |cancelled| read_seed(&log, &cancelled),
        move || ctx.request_repaint(),
    )
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum Phase {
    #[default]
    Preparing,
    Merge,
    Writing,
    Done,
}

/// Time left for the render in flight. Feed it every log chunk as it
/// arrives (`ingest`): it reads only lines with the prefixes it needs.
#[derive(Clone, Debug, Default)]
pub(crate) struct EtaTracker {
    seed: Option<StageTimes>,
    pass: StageTimes,
    phase: Phase,
    total: Option<usize>,
    processed: usize,
    samples: VecDeque<(Instant, usize)>,
    writing_since: Option<Instant>,
}
impl EtaTracker {
    pub(crate) fn new(seed: Option<StageTimes>) -> Self {
        Self {
            seed,
            ..Self::default()
        }
    }
    pub(crate) fn set_seed(&mut self, seed: Option<StageTimes>) {
        self.seed = seed;
    }
    pub(crate) fn seed(&self) -> Option<StageTimes> {
        self.seed
    }
    #[cfg(test)]
    pub(crate) fn phase(&self) -> Phase {
        self.phase
    }
    #[cfg(test)]
    pub(crate) fn processed(&self) -> (usize, Option<usize>) {
        (self.processed, self.total)
    }
    pub(crate) fn ingest(&mut self, chunk: &str, now: Instant) {
        for line in chunk.lines() {
            if let Some(event) = line.strip_prefix("STREHL_UI_PROGRESS event=") {
                self.event(event, now);
            } else if starts_pass(line) {
                self.restart();
            } else if line.starts_with("total           :") {
                self.pass.ingest(line);
                if self.pass.complete() {
                    self.phase = Phase::Done;
                }
            } else if line.len() > 16 && line.as_bytes()[16] == b':' {
                self.pass.ingest(line);
            }
        }
    }
    fn restart(&mut self) {
        let seed = self.seed;
        *self = Self::new(seed);
    }
    fn event(&mut self, event: &str, now: Instant) {
        let field = |name: &str| {
            event
                .split_whitespace()
                .find_map(|word| word.strip_prefix(name)?.strip_prefix('='))
        };
        if event.starts_with("stage name=read ") {
            self.restart();
        } else if event.starts_with("stage ") {
            match field("name") {
                Some("merge") => {
                    self.phase = Phase::Merge;
                    self.total = field("total").and_then(|n| n.parse().ok()).or(self.total);
                }
                Some("render") => {
                    self.phase = Phase::Writing;
                    self.writing_since = Some(now);
                }
                _ => {}
            }
        } else if event.starts_with("frame-finished ") {
            if let Some(processed) = field("processed").and_then(|n| n.parse::<usize>().ok()) {
                self.processed = self.processed.max(processed);
                if self.samples.len() == SAMPLES {
                    self.samples.pop_front();
                }
                self.samples.push_back((now, self.processed));
            }
            self.total = field("total").and_then(|n| n.parse().ok()).or(self.total);
            if self.phase == Phase::Preparing {
                self.phase = Phase::Merge;
            }
        }
    }
    /// Seconds per frame measured from receipts, once trustworthy.
    pub(crate) fn live_rate(&self) -> Option<f64> {
        let (first, last) = (self.samples.front()?, self.samples.back()?);
        let frames = last.1.saturating_sub(first.1);
        let span = last.0.saturating_duration_since(first.0);
        (frames >= MIN_FRAMES && span >= MIN_SPAN).then(|| span.as_secs_f64() / frames as f64)
    }
    /// Time left now, or None while nothing supports an estimate.
    pub(crate) fn eta(&self, now: Instant) -> Option<Duration> {
        let tail = self.seed.and_then(|s| s.collapse_write).unwrap_or(0.0);
        let seconds = match self.phase {
            Phase::Done => 0.0,
            Phase::Writing => {
                let spent = self
                    .writing_since
                    .map_or(0.0, |at| now.saturating_duration_since(at).as_secs_f64());
                (self.seed?.collapse_write? - spent).max(0.0)
            }
            Phase::Merge => {
                let total = self.total?;
                let rate = match self.live_rate() {
                    Some(rate) => rate,
                    None => self.seed?.per_frame()?,
                };
                let since_last = self.samples.back().map_or(0.0, |(at, _)| {
                    now.saturating_duration_since(*at).as_secs_f64()
                });
                let remaining = total.saturating_sub(self.processed) as f64 * rate;
                (remaining - since_last).max(0.0) + tail
            }
            Phase::Preparing => self.seed?.estimate(self.total.or(self.seed?.frames)?)?,
        };
        Some(Duration::from_secs_f64(seconds))
    }
}

/// "25 s", "1 min", "3 min 18 s", "1 h 04 min".
pub(crate) fn spoken(duration: Duration) -> String {
    let seconds = duration.as_secs_f64().round() as u64;
    if seconds < 60 {
        format!("{seconds} s")
    } else if seconds < 600 {
        let (m, s) = (seconds / 60, seconds % 60);
        if s == 0 {
            format!("{m} min")
        } else {
            format!("{m} min {s} s")
        }
    } else if seconds < 3600 {
        format!("{} min", (seconds + 30) / 60)
    } else {
        let minutes = (seconds + 30) / 60;
        format!("{} h {:02} min", minutes / 60, minutes % 60)
    }
}

#[cfg(test)]
#[path = "render-eta-tests.rs"]
mod tests;
