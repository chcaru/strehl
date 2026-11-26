//! Plan Q7: is the picture still? About 20 s of magnified live view, every
//! frame registered against the first, tells how far the picture moves over
//! a given time in sensor pixels, its slow drift, the axis it moves along,
//! and the longest exposure that keeps the blur under a quarter of a pixel.
//!
//! What was measured on the rig (2026-11-25, a backlit slide at lens
//! position 43,453, three 25 s live series and 48 RAW shots at 1/100 s that
//! freeze the picture, `experiments` notes in the owner's sway record):
//!
//! - The picture does not oscillate: it wanders. Its spectrum falls from the
//!   lowest frequencies up, so a single "frequency" is meaningless (the old
//!   check always found the bottom of its search, 0.1 Hz) and so was the
//!   exposure limit it derived from one. The limit now comes from how far
//!   the picture actually moved over each time span (`moves`): an exposure
//!   of T seconds blurs by about half the rms movement over T (ARGUED: a
//!   steady drift spreads a point over 0.29 of its movement, a fast sway
//!   over 0.71).
//! - Slow drift is reported apart, in px a minute: 1-2 px a minute after
//!   the light came on, 0.26 px later. It moves whole planes, which the
//!   stack's alignment absorbs, and hardly blurs one exposure.
//! - The old check registered the centre 320 x 320 of the frame only. When
//!   that patch held little detail it disagreed with the whole frame by
//!   0.8 px rms and reported 1.05 px where the frame moved 0.49. Now the
//!   whole frame is registered, with a gain and an offset (live view changes
//!   brightness by up to 11 % from frame to frame), and a frame whose four
//!   quarters disagree is left out.
//! - Live view moved about twice as far up-down as the frozen RAWs over the
//!   same time spans (0.30-0.64 against 0.16-0.20 px within 0.4-2.4 s) and
//!   as far side to side (0.15-0.31 against 0.15-0.21). The check reports
//!   what live view shows, so it errs on the cautious side up-down. Cause
//!   not established (lens or body stabilisation is a candidate).

use crate::capture_client::Snapshot;

/// One live frame as luma, the whole picture.
#[derive(Clone, Debug)]
pub(crate) struct Frame {
    pub seconds: f64,
    pub width: usize,
    pub height: usize,
    pub luma: Vec<u8>,
}

/// How long the check watches.
pub(crate) const WATCH_SECONDS: f64 = 20.0;
/// The largest blur, in sensor pixels, an exposure may add.
const BLUR_LIMIT: f64 = 0.25;
/// Blur over an exposure as a share of the rms movement over its length
/// (see the module notes).
const BLUR_SHARE: f64 = 0.5;
/// A frame whose quarters disagree with the whole by more than this, in
/// live pixels, is left out.
const QUARTER_TOLERANCE: f64 = 0.5;
/// The smallest live frame the check registers.
const MIN_SIDE: usize = 128;
/// Time spans the movement is measured over, seconds.
const SPANS: [f64; 10] = [0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0];

/// An RGB(A) live frame (4 bytes a pixel) as luma; `None` when too small.
pub(crate) fn frame(width: usize, height: usize, rgba: &[u8], seconds: f64) -> Option<Frame> {
    if width < MIN_SIDE || height < MIN_SIDE || rgba.len() < width * height * 4 {
        return None;
    }
    let luma = rgba
        .as_chunks::<4>()
        .0
        .iter()
        .take(width * height)
        .map(|p| {
            (0.2126 * f32::from(p[0]) + 0.7152 * f32::from(p[1]) + 0.0722 * f32::from(p[2]))
                .round()
                .clamp(0.0, 255.0) as u8
        })
        .collect();
    Some(Frame {
        seconds,
        width,
        height,
        luma,
    })
}

impl Frame {
    #[inline]
    fn at(&self, x: usize, y: usize) -> f64 {
        f64::from(self.luma[y * self.width + x])
    }
    /// Bilinear sample; `None` outside the frame.
    #[inline]
    fn sample(&self, x: f64, y: f64) -> Option<f64> {
        if !(x >= 0.0 && y >= 0.0) {
            return None;
        }
        let (x0, y0) = (x.floor() as usize, y.floor() as usize);
        if x0 + 1 >= self.width || y0 + 1 >= self.height {
            return None;
        }
        let (fx, fy) = (x - x0 as f64, y - y0 as f64);
        let top = self.at(x0, y0) * (1.0 - fx) + self.at(x0 + 1, y0) * fx;
        let bottom = self.at(x0, y0 + 1) * (1.0 - fx) + self.at(x0 + 1, y0 + 1) * fx;
        Some(top * (1.0 - fy) + bottom * fy)
    }
}

/// `[x0, y0, x1, y1)` in live pixels.
type Region = [usize; 4];

/// Gauss-Newton on `moving(x + d) * 1 ~ gain * reference(x) + offset` over
/// `region` (every second pixel each way), from `d`. Returns the shift, or
/// `None` when the region holds no usable structure.
fn refine(
    reference: &Frame,
    moving: &Frame,
    region: Region,
    mut d: (f64, f64),
    iterations: usize,
) -> Option<(f64, f64)> {
    for _ in 0..iterations {
        // Normal equations of [gx, gy, r, 1] against m, symmetric 4 x 4.
        let mut a = [[0f64; 4]; 4];
        let mut b = [0f64; 4];
        let mut n = 0usize;
        for y in (region[1].max(1)..region[3].min(reference.height - 1)).step_by(2) {
            for x in (region[0].max(1)..region[2].min(reference.width - 1)).step_by(2) {
                let Some(m) = moving.sample(x as f64 + d.0, y as f64 + d.1) else {
                    continue;
                };
                let r = reference.at(x, y);
                let gx = 0.5 * (reference.at(x + 1, y) - reference.at(x - 1, y));
                let gy = 0.5 * (reference.at(x, y + 1) - reference.at(x, y - 1));
                let row = [gx, gy, r, 1.0];
                for ((ai, bi), ri) in a.iter_mut().zip(b.iter_mut()).zip(row) {
                    for (aij, rj) in ai.iter_mut().zip(row) {
                        *aij += ri * rj;
                    }
                    *bi += ri * m;
                }
                n += 1;
            }
        }
        if n < 64 {
            return None;
        }
        let sol = solve4(a, b)?;
        if sol[2].is_nan() || sol[2].abs() <= 1e-6 {
            return None;
        }
        // m(x) = moving(x + d) = gain * reference(x + e) + offset with
        // e = d - d*: the gradient terms hold gain * e.
        let step = (sol[0] / sol[2], sol[1] / sol[2]);
        d = (d.0 - step.0, d.1 - step.1);
        if step.0.abs() + step.1.abs() < 1e-3 {
            break;
        }
        if d.0.abs() > 64.0 || d.1.abs() > 64.0 {
            return None;
        }
    }
    Some(d)
}

/// Gaussian elimination with partial pivoting on a 4 x 4 system.
fn solve4(mut a: [[f64; 4]; 4], mut b: [f64; 4]) -> Option<[f64; 4]> {
    for c in 0..4 {
        let p = (c..4).max_by(|&i, &j| a[i][c].abs().total_cmp(&a[j][c].abs()))?;
        if a[p][c].abs() < 1e-12 {
            return None;
        }
        a.swap(c, p);
        b.swap(c, p);
        let pivot = a[c];
        let pb = b[c];
        for (row, br) in a.iter_mut().zip(b.iter_mut()).skip(c + 1) {
            let f = row[c] / pivot[c];
            for (x, p) in row.iter_mut().zip(pivot).skip(c) {
                *x -= f * p;
            }
            *br -= f * pb;
        }
    }
    let mut x = [0f64; 4];
    for c in (0..4).rev() {
        let s: f64 = (c + 1..4).map(|k| a[c][k] * x[k]).sum();
        x[c] = (b[c] - s) / a[c][c];
    }
    x.iter().all(|v| v.is_finite()).then_some(x)
}

/// The whole-pixel shift of `moving` against `reference`: sum of squared
/// differences of 4x-reduced, mean-removed frames within +-`reach` reduced
/// pixels.
fn coarse(reference: &Frame, moving: &Frame, reach: i64) -> (f64, f64) {
    let reduce = |f: &Frame| -> (Vec<f64>, usize, usize) {
        let (w, h) = (f.width / 4, f.height / 4);
        let mut v = vec![0f64; w * h];
        for y in 0..h {
            for x in 0..w {
                let mut s = 0.0;
                for j in 0..4 {
                    for i in 0..4 {
                        s += f.at(4 * x + i, 4 * y + j);
                    }
                }
                v[y * w + x] = s / 16.0;
            }
        }
        let mean = v.iter().sum::<f64>() / v.len().max(1) as f64;
        v.iter_mut().for_each(|p| *p -= mean);
        (v, w, h)
    };
    let (a, w, h) = reduce(reference);
    let (b, _, _) = reduce(moving);
    let m = reach as usize + 1;
    let mut best = (f64::INFINITY, 0i64, 0i64);
    for dy in -reach..=reach {
        for dx in -reach..=reach {
            let mut s = 0.0;
            for y in m..h.saturating_sub(m) {
                let yb = (y as i64 + dy) as usize;
                for x in m..w.saturating_sub(m) {
                    let e = b[yb * w + (x as i64 + dx) as usize] - a[y * w + x];
                    s += e * e;
                }
            }
            if s < best.0 {
                best = (s, dx, dy);
            }
        }
    }
    (4.0 * best.1 as f64, 4.0 * best.2 as f64)
}

/// Where `moving` sits against `reference`, in live pixels: `moving(x) ~
/// reference(x - shift)`. `None` when it cannot be registered or its four
/// quarters disagree with the whole by more than [`QUARTER_TOLERANCE`].
pub(crate) fn register(reference: &Frame, moving: &Frame) -> Option<(f64, f64)> {
    if reference.width != moving.width || reference.height != moving.height {
        return None;
    }
    let (w, h) = (reference.width, reference.height);
    let margin = (w.min(h) / 16).max(8);
    let whole = [margin, margin, w - margin, h - margin];
    let start = coarse(reference, moving, 6);
    let d = refine(reference, moving, whole, start, 12)?;
    let (cx, cy) = (w / 2, h / 2);
    for q in [
        [margin, margin, cx, cy],
        [cx, margin, w - margin, cy],
        [margin, cy, cx, h - margin],
        [cx, cy, w - margin, h - margin],
    ] {
        if let Some(e) = refine(reference, moving, q, d, 6)
            && ((e.0 - d.0).abs() > QUARTER_TOLERANCE || (e.1 - d.1).abs() > QUARTER_TOLERANCE)
        {
            return None;
        }
    }
    Some(d)
}

/// What the check found, in sensor pixels.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Stillness {
    /// Frames watched, and those registered.
    pub frames: usize,
    pub used: usize,
    pub seconds: f64,
    /// Slow drift, px a minute (a straight line through the positions).
    pub drift_per_minute: f64,
    /// Per time span (s): the rms movement over it, in px, both axes.
    pub moves: Vec<(f64, f64)>,
    /// The rms movement over about a second, along x and y.
    pub second: [f64; 2],
    /// The axis most of the short-term movement is along, degrees from the
    /// picture's horizontal.
    pub axis_degrees: f64,
    /// The longest exposure whose blur stays under a quarter pixel: `None`
    /// when even the shortest span measured blurs more; at most the longest
    /// span measured.
    pub longest_seconds: Option<f64>,
    pub sensor_px_per_live_px: f64,
}

/// rms of `positions[j] - positions[i]` over pairs whose time apart lies
/// within 20 % of `span`, per axis and in all, with the pair count.
fn movement(t: &[f64], p: &[(f64, f64)], span: f64) -> Option<(f64, f64, f64, usize)> {
    let (mut sx, mut sy, mut n) = (0.0, 0.0, 0usize);
    for i in 0..t.len() {
        for j in i + 1..t.len() {
            let dt = t[j] - t[i];
            if dt > 1.2 * span {
                break;
            }
            if dt >= 0.8 * span {
                let (dx, dy) = (p[j].0 - p[i].0, p[j].1 - p[i].1);
                sx += dx * dx;
                sy += dy * dy;
                n += 1;
            }
        }
    }
    (n >= 5).then(|| {
        let (x, y) = ((sx / n as f64).sqrt(), (sy / n as f64).sqrt());
        (x, y, x.hypot(y), n)
    })
}

/// The motion's description from shifts in live pixels at times `t`
/// (seconds, increasing).
pub(crate) fn describe(
    t: &[f64],
    shifts: &[(f64, f64)],
    sensor_px_per_live_px: f64,
    frames: usize,
) -> Option<Stillness> {
    if t.len() < 8 || t.len() != shifts.len() {
        return None;
    }
    let k = sensor_px_per_live_px;
    let p: Vec<(f64, f64)> = shifts.iter().map(|s| (s.0 * k, s.1 * k)).collect();
    let n = t.len() as f64;
    let span = t[t.len() - 1] - t[0];
    // Straight-line drift.
    let tm = t.iter().sum::<f64>() / n;
    let stt: f64 = t.iter().map(|v| (v - tm) * (v - tm)).sum();
    let slope = |axis: usize| -> f64 {
        let v: Vec<f64> = p
            .iter()
            .map(|q| if axis == 0 { q.0 } else { q.1 })
            .collect();
        let vm = v.iter().sum::<f64>() / n;
        t.iter()
            .zip(&v)
            .map(|(a, b)| (a - tm) * (b - vm))
            .sum::<f64>()
            / stt.max(1e-12)
    };
    let drift_per_minute = 60.0 * slope(0).hypot(slope(1));
    let mut moves = Vec::new();
    let mut longest = None;
    let mut blurred = false;
    let mut previous: Option<(f64, f64)> = None;
    for &s in &SPANS {
        if s > 0.5 * span {
            break;
        }
        let Some((_, _, all, _)) = movement(t, &p, s) else {
            continue;
        };
        moves.push((s, all));
        let blur = BLUR_SHARE * all;
        if !blurred {
            if blur <= BLUR_LIMIT {
                longest = Some(s);
            } else {
                blurred = true;
                // Between the last span under the limit and this one.
                if let Some((s0, b0)) = previous {
                    let f = ((BLUR_LIMIT / b0).ln() / (blur / b0).ln()).clamp(0.0, 1.0);
                    longest = Some(s0 * (s / s0).powf(f));
                }
            }
        }
        previous = Some((s, blur));
    }
    // Short-term movement and its axis, over about a second.
    let (second, axis_degrees) = match movement(t, &p, 1.0) {
        Some((x, y, _, _)) => {
            // Principal axis of the one-second differences.
            let (mut sxx, mut syy, mut sxy) = (0.0, 0.0, 0.0);
            for i in 0..t.len() {
                for j in i + 1..t.len() {
                    let dt = t[j] - t[i];
                    if dt > 1.2 {
                        break;
                    }
                    if dt >= 0.8 {
                        let (dx, dy) = (p[j].0 - p[i].0, p[j].1 - p[i].1);
                        sxx += dx * dx;
                        syy += dy * dy;
                        sxy += dx * dy;
                    }
                }
            }
            ([x, y], (0.5 * (2.0 * sxy).atan2(sxx - syy)).to_degrees())
        }
        None => ([f64::NAN; 2], 0.0),
    };
    if moves.is_empty() {
        return None;
    }
    Some(Stillness {
        frames,
        used: t.len(),
        seconds: span,
        drift_per_minute,
        moves,
        second,
        axis_degrees,
        longest_seconds: longest,
        sensor_px_per_live_px: k,
    })
}

/// Sensor pixels a live pixel spans: the sensor's width over the live
/// frame's width, over the magnification (the camera's ratio is ten times
/// it). MEASURED on the A7CR: unmagnified, 9.285 sensor px a live px of a
/// 1024 px frame; at 9.3x, about one.
pub(crate) fn sensor_px_per_live_px(sensor_width: f64, live_width: f64, ratio: u32) -> f64 {
    let magnification = (f64::from(ratio) / 10.0).max(1.0);
    sensor_width / live_width.max(1.0) / magnification
}

/// The active width of a camera's RAW, when known.
pub(crate) fn sensor_width(model: Option<&str>) -> Option<f64> {
    match model? {
        "ILCE-7CR" => Some(9504.0),
        "ILCE-7CM2" => Some(7008.0),
        _ => None,
    }
}

fn exposure_text(t: f64) -> String {
    if t >= 1.0 {
        format!("{t:.1} s")
    } else {
        format!("1/{:.0} s", (1.0 / t).ceil())
    }
}

/// The plan's line for a result.
pub(crate) fn sentence(s: &Stillness) -> String {
    let second = s.second[0].hypot(s.second[1]);
    let drift = format!("drift {:.1} px a minute", s.drift_per_minute);
    let settling = if s.drift_per_minute > 1.0 {
        " Still settling (a light switched on warms the rig for some minutes): check again before a long stack."
    } else {
        ""
    };
    let skipped = if s.used < s.frames {
        format!(
            " {} of {} live frames left out.",
            s.frames - s.used,
            s.frames
        )
    } else {
        String::new()
    };
    if second.is_finite() && second < 0.1 {
        return format!(
            "Still: the picture moves {second:.2} px within a second; {drift}.{settling}{skipped}"
        );
    }
    let axis = if (s.axis_degrees.abs() - 90.0).abs() < 30.0 {
        "mostly up-down"
    } else if s.axis_degrees.abs() < 30.0 {
        "mostly side to side"
    } else {
        "diagonally"
    };
    let moves = if second.is_finite() {
        format!("Moves {second:.2} px within a second, {axis}; {drift}.")
    } else {
        format!("{}; {drift}.", axis[..1].to_uppercase() + &axis[1..])
    };
    let shortest = s.moves.first().map_or(0.2, |m| m.0);
    let limit = match s.longest_seconds {
        Some(t) if s.moves.last().is_some_and(|m| (m.0 - t).abs() < 1e-9) => format!(
            " Exposures up to at least {} keep the blur under a quarter pixel.",
            exposure_text(t)
        ),
        Some(t) => format!(
            " Exposures up to {} keep the blur under a quarter pixel.",
            exposure_text(t)
        ),
        None => format!(
            " It moves more than half a pixel within {}: shorter exposures, or a stiffer rig, are needed.",
            exposure_text(shortest)
        ),
    };
    format!("{moves}{limit}{settling}{skipped}")
}

/// The check as it runs: the magnifier set, the live frames watched, the
/// motion measured off the UI thread, then the magnifier put back.
#[derive(Default)]
pub(crate) enum StillnessCheck {
    #[default]
    Idle,
    Magnifying {
        ratio: u32,
        before: u32,
        at: (u16, u16),
        deadline: std::time::Instant,
    },
    Watching {
        ratio: u32,
        before: u32,
        at: (u16, u16),
        since: std::time::Instant,
        last: Option<u64>,
        live_width: usize,
        frames: Vec<Frame>,
    },
    Measuring {
        task: crate::jobs::Task<Option<Stillness>>,
    },
    Done(Stillness),
    Failed(String),
}

/// How long the camera may take to set its magnifier.
const MAGNIFY_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(10);

impl StillnessCheck {
    pub fn running(&self) -> bool {
        matches!(
            self,
            Self::Magnifying { .. } | Self::Watching { .. } | Self::Measuring { .. }
        )
    }
    pub fn stage(&self) -> &'static str {
        match self {
            Self::Idle => "idle",
            Self::Magnifying { .. } => "magnifying",
            Self::Watching { .. } => "watching",
            Self::Measuring { .. } => "measuring",
            Self::Done(..) => "done",
            Self::Failed(_) => "failed",
        }
    }
    /// The plan's line.
    pub fn line(&self, now: std::time::Instant) -> Option<String> {
        match self {
            Self::Idle => None,
            Self::Magnifying { .. } => Some("Stillness: setting the magnifier…".into()),
            Self::Watching { since, .. } => Some(format!(
                "Stillness: watching the magnified picture, {:.0} of {:.0} s. Keep the room still.",
                now.saturating_duration_since(*since).as_secs_f64(),
                WATCH_SECONDS
            )),
            Self::Measuring { .. } => Some("Stillness: measuring…".into()),
            Self::Done(s) => Some(sentence(s)),
            Self::Failed(why) => Some(format!("Stillness: {why}")),
        }
    }

    /// Starts: the camera's largest magnifier over the subject box. Returns
    /// the magnifier command to send.
    pub fn start(&mut self, s: &Snapshot) -> anyhow::Result<(u32, u16, u16)> {
        anyhow::ensure!(!self.running(), "The stillness check is running");
        let host = &s.host;
        anyhow::ensure!(
            s.fresh() && host.connected && host.editable && !host.phase.active(),
            "Connect a ready camera first"
        );
        anyhow::ensure!(
            host.preview.available,
            "The stillness check needs the live view"
        );
        let ratio = host
            .magnifier_ratios
            .iter()
            .copied()
            .max()
            .filter(|r| *r > 10)
            .ok_or_else(|| anyhow::anyhow!("This camera offers no magnifier"))?;
        let (cx, cy) = host
            .roi
            .as_ref()
            .map_or((0.5, 0.5), |r| (r.x + 0.5 * r.width, r.y + 0.5 * r.height));
        let at = (
            (cx.clamp(0.0, 1.0) * 639.0).round() as u16,
            (cy.clamp(0.0, 1.0) * 479.0).round() as u16,
        );
        let before = host.magnifier_current.unwrap_or(0).min(u64::from(u32::MAX)) as u32;
        *self = Self::Magnifying {
            ratio,
            before,
            at,
            deadline: std::time::Instant::now() + MAGNIFY_TIMEOUT,
        };
        Ok((ratio, at.0, at.1))
    }

    /// Stops; returns the magnifier to put back, if one was changed.
    pub fn stop(&mut self) -> Option<(u32, u16, u16)> {
        let back = match self {
            Self::Magnifying { before, at, .. } | Self::Watching { before, at, .. } => {
                Some((*before, at.0, at.1))
            }
            _ => None,
        };
        *self = Self::Failed("stopped".into());
        back
    }

    /// Advances with the host's state; returns a magnifier command to send
    /// (the magnifier put back once the watch ends).
    pub fn poll(&mut self, s: &Snapshot, now: std::time::Instant) -> Option<(u32, u16, u16)> {
        let host = &s.host;
        match self {
            Self::Magnifying {
                ratio,
                before,
                at,
                deadline,
            } => {
                if host.magnifier_current == Some(u64::from(*ratio)) {
                    *self = Self::Watching {
                        ratio: *ratio,
                        before: *before,
                        at: *at,
                        since: now,
                        last: s.preview.as_ref().map(|(g, _)| *g),
                        live_width: 0,
                        frames: Vec::new(),
                    };
                } else if now >= *deadline {
                    let back = (*before, at.0, at.1);
                    *self = Self::Failed("the camera did not set its magnifier".into());
                    return Some(back);
                }
                None
            }
            Self::Watching {
                ratio,
                before,
                at,
                since,
                last,
                live_width,
                frames,
            } => {
                let elapsed = now.saturating_duration_since(*since).as_secs_f64();
                if let Some((generation, image)) = &s.preview
                    && Some(*generation) != *last
                {
                    *last = Some(*generation);
                    let [w, h] = image.size;
                    let rgba: Vec<u8> = image
                        .pixels
                        .iter()
                        .flat_map(|p| [p.r(), p.g(), p.b(), 255])
                        .collect();
                    if let Some(f) = frame(w, h, &rgba, elapsed) {
                        frames.push(f);
                        *live_width = w;
                    }
                }
                if host.phase.active() || !host.connected {
                    let back = (*before, at.0, at.1);
                    *self = Self::Failed("the camera became busy".into());
                    return Some(back);
                }
                if elapsed < WATCH_SECONDS {
                    return None;
                }
                let back = (*before, at.0, at.1);
                let frames = std::mem::take(frames);
                let k = sensor_width(host.camera_model.as_deref())
                    .map(|sensor| sensor_px_per_live_px(sensor, *live_width as f64, *ratio));
                *self = match k {
                    _ if frames.len() < 8 => {
                        Self::Failed("too few live frames arrived to measure".into())
                    }
                    None => {
                        Self::Failed("this camera's sensor width is not known to the check".into())
                    }
                    Some(k) => Self::Measuring {
                        task: crate::jobs::spawn_task("strehl-stillness", move |_| {
                            let reference = &frames[0];
                            let mut t = Vec::with_capacity(frames.len());
                            let mut shifts = Vec::with_capacity(frames.len());
                            for f in &frames {
                                if let Some(shift) = register(reference, f) {
                                    t.push(f.seconds);
                                    shifts.push(shift);
                                }
                            }
                            Ok(describe(&t, &shifts, k, frames.len()))
                        }),
                    },
                };
                Some(back)
            }
            Self::Measuring { task } => {
                match task.receiver.try_recv() {
                    Ok(Ok(Some(found))) => {
                        *self = Self::Done(found);
                    }
                    Ok(Ok(None)) => {
                        *self = Self::Failed("the live frames could not be registered".into());
                    }
                    Ok(Err(e)) => *self = Self::Failed(e),
                    Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                        *self = Self::Failed("the measurement stopped".into());
                    }
                    Err(std::sync::mpsc::TryRecvError::Empty) => {}
                }
                None
            }
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A textured live frame shifted by `(dx, dy)`, with a gain and an
    /// offset; `flat_centre` blanks the middle third (the old check's patch).
    fn scene(
        w: usize,
        h: usize,
        dx: f64,
        dy: f64,
        gain: f64,
        offset: f64,
        flat_centre: bool,
    ) -> Frame {
        let luma = (0..w * h)
            .map(|i| {
                let (px, py) = ((i % w) as f64, (i / w) as f64);
                let (x, y) = (px - dx, py - dy);
                let mut v = 100.0
                    + 40.0 * (x * 0.21).sin() * (y * 0.17).cos()
                    + 25.0 * ((x + 2.0 * y) * 0.11).sin()
                    + 15.0 * ((3.0 * x - y) * 0.07).cos();
                // The flat patch belongs to the scene: it moves with it.
                let centre = x > w as f64 / 3.0
                    && x < 2.0 * w as f64 / 3.0
                    && y > h as f64 / 3.0
                    && y < 2.0 * h as f64 / 3.0;
                if flat_centre && centre {
                    v = 120.0;
                }
                (v * gain + offset).round().clamp(0.0, 255.0) as u8
            })
            .collect();
        Frame {
            seconds: 0.0,
            width: w,
            height: h,
            luma,
        }
    }

    /// Sub-pixel and whole-pixel shifts are found to a few hundredths,
    /// through a brightness change, and with a featureless centre (where
    /// the old 320 px centre patch went wrong on the rig).
    #[test]
    fn registration_finds_shifts_through_brightness_changes_and_a_flat_centre() {
        let (w, h) = (512, 340);
        for flat in [false, true] {
            let reference = scene(w, h, 0.0, 0.0, 1.0, 0.0, flat);
            for (dx, dy, g, o) in [
                (0.3, -0.45, 1.0, 0.0),
                (2.6, 1.2, 0.9, 6.0),
                (-5.4, 3.1, 1.08, -4.0),
                (0.0, 0.0, 0.95, 0.0),
                (13.2, -9.7, 1.0, 0.0),
            ] {
                let moving = scene(w, h, dx, dy, g, o, flat);
                let (x, y) = register(&reference, &moving).expect("registers");
                assert!(
                    (x - dx).abs() < 0.05 && (y - dy).abs() < 0.05,
                    "flat {flat}: {dx},{dy} -> {x},{y}"
                );
            }
        }
    }

    /// A frame that does not move rigidly (one quarter moved apart) is left
    /// out rather than averaged in.
    #[test]
    fn a_frame_whose_quarters_disagree_is_left_out() {
        let (w, h) = (512, 340);
        let reference = scene(w, h, 0.0, 0.0, 1.0, 0.0, false);
        let mut moving = scene(w, h, 0.4, 0.2, 1.0, 0.0, false);
        let shifted = scene(w, h, 3.4, 2.2, 1.0, 0.0, false);
        for y in 0..h / 2 {
            for x in 0..w / 2 {
                moving.luma[y * w + x] = shifted.luma[y * w + x];
            }
        }
        assert!(register(&reference, &moving).is_none());
    }

    fn times() -> Vec<f64> {
        (0..124).map(|i| i as f64 / 6.2).collect()
    }

    /// A fast sway of 0.5 px rms up-down blurs any exposure the live view
    /// can time: it says so, and gives no exposure limit.
    #[test]
    fn a_fast_sway_reads_as_blurring_every_exposure() {
        let t = times();
        let amp = 0.5 * std::f64::consts::SQRT_2;
        let shifts: Vec<(f64, f64)> = t
            .iter()
            .map(|t| (0.0, amp * (std::f64::consts::TAU * 2.6 * t).sin()))
            .collect();
        let s = describe(&t, &shifts, 1.0, t.len()).unwrap();
        assert!(s.longest_seconds.is_none(), "{s:?}");
        assert!((s.axis_degrees.abs() - 90.0).abs() < 5.0, "{s:?}");
        let line = sentence(&s);
        assert!(
            line.contains("up-down") && line.contains("more than half a pixel"),
            "{line}"
        );
    }

    /// A slow wander and a steady drift: the drift is reported in px a
    /// minute, and the exposure limit is where the movement reaches half a
    /// pixel (blur a quarter).
    #[test]
    fn drift_and_wander_give_a_drift_rate_and_an_exposure_limit() {
        let t = times();
        // 1.2 px a minute along x, and a random walk of 0.12 px a step on y.
        let mut walk = 0.0f64;
        let mut seed = 12345u64;
        let shifts: Vec<(f64, f64)> = t
            .iter()
            .map(|t| {
                seed = seed
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1442695040888963407);
                let u = ((seed >> 11) as f64 / (1u64 << 53) as f64) - 0.5;
                walk += 0.12 * u * 3.46;
                (0.02 * t, walk)
            })
            .collect();
        let s = describe(&t, &shifts, 1.0, t.len()).unwrap();
        assert!((s.drift_per_minute - 1.2).abs() < 0.6, "{s:?}");
        let limit = s.longest_seconds.expect("a limit");
        // Movement over the limit is about half a pixel.
        let (lo, hi) = s
            .moves
            .windows(2)
            .find(|w| w[0].0 <= limit && limit <= w[1].0)
            .map(|w| (w[0].1, w[1].1))
            .expect("bracketed");
        assert!(lo <= 0.5 + 1e-9 && hi >= 0.5 - 1e-9, "{s:?}");
        assert!(sentence(&s).contains("a minute"), "{}", sentence(&s));
    }

    /// A still series reads as still.
    #[test]
    fn a_still_series_reads_still() {
        let t = times();
        let shifts: Vec<(f64, f64)> = t.iter().map(|t| (0.001 * t, 0.0)).collect();
        let s = describe(&t, &shifts, 1.0, t.len()).unwrap();
        assert!(sentence(&s).starts_with("Still"), "{}", sentence(&s));
        assert!(s.longest_seconds.is_some_and(|l| l >= 5.0), "{s:?}");
    }

    #[test]
    fn live_pixels_scale_to_sensor_pixels() {
        let k = sensor_px_per_live_px(9504.0, 1024.0, 93);
        assert!((k - 0.998).abs() < 0.01, "{k}");
        assert!((sensor_px_per_live_px(9504.0, 1024.0, 0) - 9.28).abs() < 0.01);
    }

    /// Plan Q7's gate on the rig's own frames: `STREHL_RIG_STILL` names a
    /// folder of magnified live-view JPEGs `still-<seconds>.jpg` and its
    /// `still.json` (`ratio`). Prints what the check would say.
    #[test]
    #[ignore = "needs the rig's frames (STREHL_RIG_STILL)"]
    fn stillness_on_the_rigs_frames() {
        let Some(folder) = std::env::var_os("STREHL_RIG_STILL").map(std::path::PathBuf::from)
        else {
            return;
        };
        let ratio: serde_json::Value =
            serde_json::from_slice(&std::fs::read(folder.join("still.json")).unwrap()).unwrap();
        let ratio = ratio["ratio"].as_u64().unwrap() as u32;
        let mut files: Vec<_> = std::fs::read_dir(&folder)
            .unwrap()
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.extension().is_some_and(|e| e == "jpg"))
            .collect();
        files.sort();
        let mut frames = Vec::new();
        let mut width = 0;
        for f in &files {
            let t: f64 = f
                .file_stem()
                .unwrap()
                .to_string_lossy()
                .trim_start_matches("still-")
                .parse()
                .unwrap();
            let img = image::open(f).unwrap().to_rgba8();
            width = img.width() as usize;
            frames
                .push(frame(img.width() as usize, img.height() as usize, img.as_raw(), t).unwrap());
        }
        frames.sort_by(|a, b| a.seconds.total_cmp(&b.seconds));
        let (mut t, mut shifts) = (Vec::new(), Vec::new());
        for f in &frames {
            if let Some(shift) = register(&frames[0], f) {
                t.push(f.seconds);
                shifts.push(shift);
            }
        }
        let k = sensor_px_per_live_px(9504.0, width as f64, ratio);
        let found = describe(&t, &shifts, k, frames.len()).unwrap();
        println!(
            "{} frames, {} registered, {:.3} sensor px a live px",
            frames.len(),
            t.len(),
            k
        );
        println!("{found:?}");
        println!("{}", sentence(&found));
    }
}
