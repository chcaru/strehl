//! Plan Q7: is the picture still? About 20 s of magnified live view,
//! every frame registered against the first, tells the sway in sensor
//! pixels, its axis and frequency, and the longest exposure that keeps the
//! blur under a quarter of a pixel (MEASURED in the close-tile test: at the
//! lens's closest focus the picture swayed 0.5 px along one axis at about
//! 2.6 Hz, and the finished 1/4 s tile lost a third of its fine detail
//! along it).
//!
//! Registration: a whole-pixel search on a 2x reduced crop, then
//! Lucas-Kanade refinement at full resolution (translation only; the
//! magnified picture moves rigidly: its quadrants agreed to 0.2 px).

use crate::capture_client::Snapshot;

/// One live frame's centre crop, as luma.
#[derive(Clone, Debug)]
pub(crate) struct Crop {
    pub seconds: f64,
    pub side: usize,
    pub luma: Vec<f32>,
}

/// The crop side, in live pixels.
pub(crate) const CROP: usize = 320;
/// How long the check watches.
pub(crate) const WATCH_SECONDS: f64 = 20.0;
/// The largest blur, in sensor pixels, an exposure may add.
const BLUR_LIMIT: f64 = 0.25;

/// The centre `CROP` x `CROP` of an RGB(A) live frame, as luma; `None`
/// when the frame is smaller.
pub(crate) fn crop(width: usize, height: usize, rgba: &[u8], seconds: f64) -> Option<Crop> {
    if width < CROP || height < CROP || rgba.len() < width * height * 4 {
        return None;
    }
    let (x0, y0) = ((width - CROP) / 2, (height - CROP) / 2);
    let mut luma = Vec::with_capacity(CROP * CROP);
    for y in y0..y0 + CROP {
        for x in x0..x0 + CROP {
            let i = (y * width + x) * 4;
            luma.push(
                0.2126 * f32::from(rgba[i])
                    + 0.7152 * f32::from(rgba[i + 1])
                    + 0.0722 * f32::from(rgba[i + 2]),
            );
        }
    }
    Some(Crop {
        seconds,
        side: CROP,
        luma,
    })
}

fn at(img: &[f32], side: usize, x: f32, y: f32) -> f32 {
    let x = x.clamp(0.0, (side - 1) as f32 - 1e-3);
    let y = y.clamp(0.0, (side - 1) as f32 - 1e-3);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let (fx, fy) = (x - x0 as f32, y - y0 as f32);
    let i = y0 * side + x0;
    let top = img[i] * (1.0 - fx) + img[i + 1] * fx;
    let bottom = img[i + side] * (1.0 - fx) + img[i + side + 1] * fx;
    top * (1.0 - fy) + bottom * fy
}

/// Where `moving` sits against `reference`, in pixels: `moving(x) ≈
/// reference(x - shift)`.
pub(crate) fn register(reference: &Crop, moving: &Crop) -> Option<(f64, f64)> {
    let side = reference.side;
    if side != moving.side || side < 64 {
        return None;
    }
    // Whole pixels on a 2x reduction, within ±8 live px.
    let half = side / 2;
    let reduce = |img: &[f32]| -> Vec<f32> {
        (0..half * half)
            .map(|i| {
                let (x, y) = (2 * (i % half), 2 * (i / half));
                0.25 * (img[y * side + x]
                    + img[y * side + x + 1]
                    + img[(y + 1) * side + x]
                    + img[(y + 1) * side + x + 1])
            })
            .collect()
    };
    let (a, b) = (reduce(&reference.luma), reduce(&moving.luma));
    let reach = 4i32;
    let margin = reach as usize;
    let mut best = (f64::INFINITY, 0i32, 0i32);
    for dy in -reach..=reach {
        for dx in -reach..=reach {
            let mut sum = 0.0f64;
            for y in margin..half - margin {
                let row_a = y * half;
                let row_b = (y as i32 + dy) as usize * half;
                for x in margin..half - margin {
                    let d = a[row_a + x] - b[row_b + (x as i32 + dx) as usize];
                    sum += f64::from(d * d);
                }
            }
            if sum < best.0 {
                best = (sum, dx, dy);
            }
        }
    }
    let (mut sx, mut sy) = (2.0 * best.1 as f32, 2.0 * best.2 as f32);
    // Lucas-Kanade on the full crop, inside a margin the shift cannot leave.
    let r = &reference.luma;
    let m = &moving.luma;
    let edge = 12usize;
    for _ in 0..6 {
        let (mut gxx, mut gxy, mut gyy, mut bx, mut by) = (0.0f64, 0.0, 0.0, 0.0, 0.0);
        for y in edge..side - edge {
            for x in edge..side - edge {
                let gx = 0.5 * (r[y * side + x + 1] - r[y * side + x - 1]);
                let gy = 0.5 * (r[(y + 1) * side + x] - r[(y - 1) * side + x]);
                let diff = at(m, side, x as f32 + sx, y as f32 + sy) - r[y * side + x];
                let (gx, gy, diff) = (f64::from(gx), f64::from(gy), f64::from(diff));
                gxx += gx * gx;
                gxy += gx * gy;
                gyy += gy * gy;
                bx += gx * diff;
                by += gy * diff;
            }
        }
        let det = gxx * gyy - gxy * gxy;
        if det.abs() < 1e-9 {
            return None;
        }
        let ux = (gyy * bx - gxy * by) / det;
        let uy = (gxx * by - gxy * bx) / det;
        sx -= ux as f32;
        sy -= uy as f32;
        if ux.abs() + uy.abs() < 1e-3 {
            break;
        }
    }
    Some((f64::from(sx), f64::from(sy)))
}

/// What the check found, in sensor pixels.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Stillness {
    pub frames: usize,
    pub seconds: f64,
    /// Motion about the slow drift, rms along the picture's x and y.
    pub rms: [f64; 2],
    /// The axis most of it is along: degrees from the picture's horizontal.
    pub axis_degrees: f64,
    /// The 95th percentile of the distance from the drift line.
    pub p95: f64,
    /// The slow drift over the watch.
    pub drift: f64,
    /// The strongest frequency of the motion along its axis.
    pub hertz: Option<f64>,
    /// The longest exposure whose blur stays under a quarter pixel.
    pub longest_seconds: Option<f64>,
    pub sensor_px_per_live_px: f64,
}

/// Quadratic trend of `v` over `t` (least squares), evaluated at `t`.
fn trend(t: &[f64], v: &[f64]) -> Vec<f64> {
    let n = t.len() as f64;
    let t0 = t.iter().sum::<f64>() / n;
    let ts: Vec<f64> = t.iter().map(|x| x - t0).collect();
    let s = |p: i32| ts.iter().map(|x| x.powi(p)).sum::<f64>();
    let sv = |p: i32| ts.iter().zip(v).map(|(x, y)| x.powi(p) * y).sum::<f64>();
    let m = [[n, s(1), s(2)], [s(1), s(2), s(3)], [s(2), s(3), s(4)]];
    let r = [sv(0), sv(1), sv(2)];
    let det3 = |m: [[f64; 3]; 3]| {
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    };
    let d = det3(m);
    if d.abs() < 1e-12 {
        let mean = v.iter().sum::<f64>() / n;
        return vec![mean; v.len()];
    }
    let solve = |k: usize| {
        let mut c = m;
        for (row, value) in c.iter_mut().zip(r) {
            row[k] = value;
        }
        det3(c) / d
    };
    let (a, b, c) = (solve(0), solve(1), solve(2));
    ts.iter().map(|x| a + b * x + c * x * x).collect()
}

/// The motion's description from shifts in live pixels at times `t`.
pub(crate) fn describe(
    t: &[f64],
    shifts: &[(f64, f64)],
    sensor_px_per_live_px: f64,
) -> Option<Stillness> {
    if t.len() < 8 || t.len() != shifts.len() {
        return None;
    }
    let k = sensor_px_per_live_px;
    let x: Vec<f64> = shifts.iter().map(|s| s.0 * k).collect();
    let y: Vec<f64> = shifts.iter().map(|s| s.1 * k).collect();
    let (tx, ty) = (trend(t, &x), trend(t, &y));
    let rx: Vec<f64> = x.iter().zip(&tx).map(|(a, b)| a - b).collect();
    let ry: Vec<f64> = y.iter().zip(&ty).map(|(a, b)| a - b).collect();
    let n = t.len() as f64;
    let rms = |v: &[f64]| (v.iter().map(|a| a * a).sum::<f64>() / n).sqrt();
    // Principal axis of the residual motion.
    let (sxx, syy, sxy) = rx
        .iter()
        .zip(&ry)
        .fold((0.0, 0.0, 0.0), |(a, b, c), (x, y)| {
            (a + x * x, b + y * y, c + x * y)
        });
    let angle = 0.5 * (2.0 * sxy).atan2(sxx - syy);
    let along: Vec<f64> = rx
        .iter()
        .zip(&ry)
        .map(|(x, y)| x * angle.cos() + y * angle.sin())
        .collect();
    let mut radial: Vec<f64> = rx.iter().zip(&ry).map(|(x, y)| x.hypot(*y)).collect();
    radial.sort_by(f64::total_cmp);
    let p95 = radial[((0.95 * (radial.len() - 1) as f64).round() as usize).min(radial.len() - 1)];
    let span = t[t.len() - 1] - t[0];
    let drift = (tx[tx.len() - 1] - tx[0]).hypot(ty[ty.len() - 1] - ty[0]);
    // The strongest frequency along the axis (a periodogram on the uneven
    // times), up to 0.45 of the frame rate.
    let rate = (t.len() - 1) as f64 / span.max(1e-9);
    let top = (0.45 * rate).min(4.0);
    let mut hertz = None;
    if top > 0.2 {
        let mut best = (0.0f64, 0.0f64);
        let steps = 300;
        for i in 0..=steps {
            let f = 0.1 + (top - 0.1) * i as f64 / steps as f64;
            let w = std::f64::consts::TAU * f;
            let (c, s) = t.iter().zip(&along).fold((0.0, 0.0), |(c, s), (ti, a)| {
                (c + a * (w * ti).cos(), s + a * (w * ti).sin())
            });
            let p = c * c + s * s;
            if p > best.0 {
                best = (p, f);
            }
        }
        hertz = (best.0 > 0.0).then_some(best.1);
    }
    let sigma = rms(&along);
    // A sway of rms sigma at f moves at up to 2 pi f sqrt(2) sigma.
    let longest_seconds = hertz.and_then(|f| {
        let speed = std::f64::consts::TAU * f * std::f64::consts::SQRT_2 * sigma;
        (speed > 1e-9).then(|| BLUR_LIMIT / speed)
    });
    Some(Stillness {
        frames: t.len(),
        seconds: span,
        rms: [rms(&rx), rms(&ry)],
        axis_degrees: angle.to_degrees(),
        p95,
        drift,
        hertz,
        longest_seconds,
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

/// The plan's line for a result.
pub(crate) fn sentence(s: &Stillness) -> String {
    let main = s.rms[0].hypot(s.rms[1]);
    if main < 0.1 {
        return format!(
            "Still: the picture moved {main:.2} px (rms) over {:.0} s; drift {:.1} px.",
            s.seconds, s.drift
        );
    }
    let axis = if (s.axis_degrees.abs() - 90.0).abs() < 30.0 {
        "the picture's vertical"
    } else if s.axis_degrees.abs() < 30.0 {
        "the picture's horizontal"
    } else {
        "a diagonal"
    };
    let along = s.rms[0].max(s.rms[1]);
    let freq = s
        .hertz
        .map(|f| format!(" at {f:.1} Hz"))
        .unwrap_or_default();
    let longest = s
        .longest_seconds
        .map(|t| {
            if t >= 1.0 {
                format!(" Exposures up to {t:.1} s keep the blur under a quarter pixel.")
            } else {
                format!(
                    " Exposures up to 1/{:.0} s keep the blur under a quarter pixel.",
                    (1.0 / t).ceil()
                )
            }
        })
        .unwrap_or_default();
    format!(
        "Sways {along:.2} px (rms) along {axis}{freq}, 95 % within {:.1} px; drift {:.1} px over {:.0} s.{longest}",
        s.p95, s.drift, s.seconds
    )
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
        crops: Vec<Crop>,
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
                        crops: Vec::new(),
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
                crops,
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
                    if let Some(c) = crop(w, h, &rgba, elapsed) {
                        crops.push(c);
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
                let crops = std::mem::take(crops);
                let k = sensor_width(host.camera_model.as_deref())
                    .map(|sensor| sensor_px_per_live_px(sensor, *live_width as f64, *ratio));
                *self = match k {
                    _ if crops.len() < 8 => {
                        Self::Failed("too few live frames arrived to measure".into())
                    }
                    None => {
                        Self::Failed("this camera's sensor width is not known to the check".into())
                    }
                    Some(k) => Self::Measuring {
                        task: crate::jobs::spawn_task("strehl-stillness", move |_| {
                            let reference = &crops[0];
                            let mut t = Vec::with_capacity(crops.len());
                            let mut shifts = Vec::with_capacity(crops.len());
                            for c in &crops {
                                if let Some(shift) = register(reference, c) {
                                    t.push(c.seconds);
                                    shifts.push(shift);
                                }
                            }
                            Ok(describe(&t, &shifts, k))
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

    fn texture(side: usize, dx: f64, dy: f64, seconds: f64) -> Crop {
        let luma = (0..side * side)
            .map(|i| {
                let (x, y) = ((i % side) as f64 - dx, (i / side) as f64 - dy);
                (100.0
                    + 40.0 * (x * 0.21).sin() * (y * 0.17).cos()
                    + 25.0 * ((x + 2.0 * y) * 0.11).sin()
                    + 15.0 * ((3.0 * x - y) * 0.07).cos()) as f32
            })
            .collect();
        Crop {
            seconds,
            side,
            luma,
        }
    }

    /// Sub-pixel shifts are found to a few hundredths, whole pixels too.
    #[test]
    fn registration_finds_sub_pixel_and_whole_pixel_shifts() {
        let reference = texture(CROP, 0.0, 0.0, 0.0);
        for (dx, dy) in [(0.3, -0.45), (2.6, 1.2), (-5.4, 3.1), (0.0, 0.0)] {
            let moving = texture(CROP, dx, dy, 0.1);
            let (x, y) = register(&reference, &moving).unwrap();
            assert!(
                (x - dx).abs() < 0.05 && (y - dy).abs() < 0.05,
                "{dx},{dy} -> {x},{y}"
            );
        }
    }

    /// A 2.6 Hz sway of 0.5 px rms along y with a slow drift reads as that:
    /// axis, size, frequency and a 1/46 s exposure limit; a still
    /// series reads as still.
    #[test]
    fn a_sway_is_described_by_axis_size_and_frequency() {
        let t: Vec<f64> = (0..124).map(|i| i as f64 / 6.2).collect();
        let amp = 0.5 * std::f64::consts::SQRT_2;
        let shifts: Vec<(f64, f64)> = t
            .iter()
            .map(|t| {
                (
                    0.02 * t,
                    amp * (std::f64::consts::TAU * 2.6 * t).sin() + 0.03 * t,
                )
            })
            .collect();
        let s = describe(&t, &shifts, 1.0).unwrap();
        assert!((s.rms[1] - 0.5).abs() < 0.03, "{s:?}");
        assert!(s.rms[0] < 0.02, "{s:?}");
        assert!((s.axis_degrees.abs() - 90.0).abs() < 5.0, "{s:?}");
        assert!((s.hertz.unwrap() - 2.6).abs() < 0.05, "{s:?}");
        let longest = s.longest_seconds.unwrap();
        // 0.25 / (2 pi 2.6 sqrt(2) 0.5) = 1/46 s.
        assert!((longest - 0.0216).abs() < 0.002, "{longest}");
        assert!(sentence(&s).contains("vertical"), "{}", sentence(&s));
        let still: Vec<(f64, f64)> = t.iter().map(|t| (0.01 * t, 0.0)).collect();
        assert!(sentence(&describe(&t, &still, 1.0).unwrap()).starts_with("Still"));
    }

    #[test]
    fn live_pixels_scale_to_sensor_pixels() {
        let k = sensor_px_per_live_px(9504.0, 1024.0, 93);
        assert!((k - 0.998).abs() < 0.01, "{k}");
        assert!((sensor_px_per_live_px(9504.0, 1024.0, 0) - 9.28).abs() < 0.01);
    }
}
