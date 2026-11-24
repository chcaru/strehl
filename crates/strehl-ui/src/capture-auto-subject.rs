//! Plan S2/S3 in the Capture station: the subject found automatically from
//! the live frames the bounds survey shows while it sweeps focus (a loose
//! first outline, no RAW), re-thresholded with Sensitivity, Grow and Buffer
//! from the stored evidence without new frames. The precise outline from
//! RAW planes is `strehl subject` (engine).

use std::sync::Arc;

use strehl_capture::model::Subject;
use strehl_core::subject::{self, Evidence, LiveFrame, Params, Quiet, Selection};

use crate::capture_client::{Snapshot, host::HostPhase};
use crate::jobs::{Task, spawn_task};

/// Frames kept from one survey (each halved to about 512 px wide).
const MAX_FRAMES: usize = 64;

/// One survey frame: RGB8 at half the live view's size, and its focus.
struct Frame {
    rgb: Vec<u8>,
    width: usize,
    height: usize,
    position: f64,
}

/// The live frames of the latest bounds survey.
#[derive(Default)]
pub(crate) struct SurveyFrames {
    frames: Vec<Frame>,
    last: Option<u64>,
    scanning: bool,
}

impl SurveyFrames {
    pub fn len(&self) -> usize {
        self.frames.len()
    }

    /// Keeps each new preview while the host surveys; a new survey starts
    /// a new set.
    pub fn observe(&mut self, s: &Snapshot) {
        let scanning = s.host.phase == HostPhase::Scanning;
        if scanning && !self.scanning {
            self.frames.clear();
            self.last = None;
        }
        self.scanning = scanning;
        if !scanning || self.frames.len() >= MAX_FRAMES {
            return;
        }
        let (Some((generation, image)), Some(position)) = (&s.preview, s.host.position) else {
            return;
        };
        if self.last == Some(*generation) {
            return;
        }
        self.last = Some(*generation);
        let [w, h] = image.size;
        let (hw, hh) = (w / 2, h / 2);
        if hw < 64 || hh < 64 {
            return;
        }
        // Halved by 2 x 2 means: the evidence cells are 4 px of this.
        let mut rgb = Vec::with_capacity(hw * hh * 3);
        for y in 0..hh {
            for x in 0..hw {
                for c in 0..3 {
                    let sum: u32 = [(0, 0), (1, 0), (0, 1), (1, 1)]
                        .iter()
                        .map(|(dx, dy)| {
                            let p = image.pixels[(2 * y + dy) * w + 2 * x + dx];
                            u32::from([p.r(), p.g(), p.b()][c])
                        })
                        .sum();
                    rgb.push(((sum + 2) / 4) as u8);
                }
            }
        }
        self.frames.push(Frame {
            rgb,
            width: hw,
            height: hh,
            position: f64::from(position),
        });
    }
}

/// The sensor's active area in pixels, when the camera is known.
pub(crate) fn active_px(model: Option<&str>) -> [u32; 2] {
    match model {
        Some("ILCE-7CM2") => [7008, 4672],
        _ => [9504, 6336],
    }
}

/// The automatic selection: running, or found with its evidence kept for
/// the sliders.
#[derive(Default)]
pub(crate) enum AutoSubject {
    #[default]
    Idle,
    Running(Task<(Arc<Evidence>, Quiet, Selection)>),
    Ready {
        evidence: Arc<Evidence>,
        quiet: Quiet,
        selection: Box<Selection>,
        /// The selection has not been given to the host yet.
        unsent: bool,
    },
    Failed(String),
}

impl AutoSubject {
    pub fn running(&self) -> bool {
        matches!(self, Self::Running(_))
    }

    /// Finds the subject in the survey's frames.
    pub fn start(&mut self, frames: &SurveyFrames, active: [u32; 2]) -> anyhow::Result<()> {
        anyhow::ensure!(!self.running(), "The subject is being found");
        anyhow::ensure!(
            frames.len() >= 5,
            "Survey first: Auto reads the live frames the survey shows as it sweeps focus"
        );
        let owned: Vec<(Vec<u8>, usize, usize, f64)> = frames
            .frames
            .iter()
            .map(|f| (f.rgb.clone(), f.width, f.height, f.position))
            .collect();
        *self = Self::Running(spawn_task("strehl-auto-subject", move |_| {
            let live: Vec<LiveFrame<'_>> = owned
                .iter()
                .map(|(rgb, width, height, _)| LiveFrame {
                    rgb,
                    width: *width,
                    height: *height,
                })
                .collect();
            let positions: Vec<f64> = owned.iter().map(|f| f.3).collect();
            let evidence = subject::live_view_evidence(&live, Some(&positions), active);
            let quiet = subject::quiet(&evidence);
            let selection = subject::select(&evidence, &quiet, &Params::live());
            Ok((Arc::new(evidence), quiet, selection))
        }));
        Ok(())
    }

    /// Sensitivity, Grow and Buffer changed: select again from the kept
    /// evidence (no new frames).
    pub fn reselect(&mut self, params: Params) {
        if let Self::Ready {
            evidence, quiet, ..
        } = self
        {
            let (evidence, quiet) = (Arc::clone(evidence), *quiet);
            *self = Self::Running(spawn_task("strehl-auto-subject", move |_| {
                let selection = subject::select(&evidence, &quiet, &params);
                Ok((evidence, quiet, selection))
            }));
        }
    }

    pub fn poll(&mut self) {
        if let Self::Running(task) = self {
            match task.receiver.try_recv() {
                Ok(Ok((evidence, quiet, selection))) => {
                    *self = Self::Ready {
                        evidence,
                        quiet,
                        selection: Box::new(selection),
                        unsent: true,
                    }
                }
                Ok(Err(e)) => *self = Self::Failed(e),
                Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                    *self = Self::Failed("The search stopped".into())
                }
                Err(std::sync::mpsc::TryRecvError::Empty) => {}
            }
        }
    }

    /// A new selection for the host, once (an empty one clears nothing:
    /// its summary says why).
    pub fn take_unsent(&mut self) -> Option<Subject> {
        let Self::Ready {
            evidence,
            selection,
            unsent,
            ..
        } = self
        else {
            return None;
        };
        if !std::mem::take(unsent) {
            return None;
        }
        to_subject(evidence, selection)
    }

    /// The panel's line: what was found, or why nothing was.
    pub fn line(&self) -> Option<String> {
        match self {
            Self::Idle => None,
            Self::Running(_) => Some("Finding the subject…".into()),
            Self::Ready { selection, .. } => Some(selection.summary.clone()),
            Self::Failed(why) => Some(why.clone()),
        }
    }

    /// Plan S4: the focus range the subject is sharp over (its first and
    /// last sharp frame's focus), ascending.
    pub fn depth_range(&self) -> Option<(u16, u16)> {
        let Self::Ready {
            evidence,
            selection,
            ..
        } = self
        else {
            return None;
        };
        let depth = selection.depth.as_ref()?;
        let at = |i: usize| evidence.planes.get(i)?.position;
        let (a, b) = (at(depth.first)?, at(depth.last)?);
        let (lo, hi) = (a.min(b), a.max(b));
        Some((
            lo.round().clamp(0.0, 65535.0) as u16,
            hi.round().clamp(0.0, 65535.0) as u16,
        ))
    }

    pub fn params(&self) -> Option<Params> {
        match self {
            Self::Ready { selection, .. } => Some(selection.params),
            _ => None,
        }
    }
}

/// The selection as the host's subject: its rings, the reference plane's
/// focus, the magnification rate and how it was made.
pub(crate) fn to_subject(evidence: &Evidence, selection: &Selection) -> Option<Subject> {
    let rings: Vec<Vec<[f32; 2]>> = selection
        .rings
        .iter()
        .filter(|r| r.len() >= 3)
        .take(Subject::MAX_RINGS)
        .map(|r| r.iter().take(Subject::MAX_POINTS).copied().collect())
        .collect();
    if rings.is_empty() {
        return None;
    }
    let reference = evidence.planes.get(evidence.reference);
    let p = &selection.params;
    let subject = Subject {
        rings,
        reference_focus: reference
            .and_then(|r| r.position)
            .map(|v| v.round().clamp(0.0, 65535.0) as u16),
        rate_ppm: evidence.registration.map(|r| r.ppm_per_unit as f32),
        provenance: serde_json::json!({
            "kind": "auto",
            "source": "live view",
            "sensitivity": p.sensitivity,
            "grow": p.grow,
            "buffer_px": p.buffer_px,
            "frames": evidence.planes.len(),
            "area_share": selection.area_share,
        }),
    };
    subject.validate().ok().map(|()| subject)
}

#[cfg(test)]
mod tests {
    use super::*;
    use eframe::egui::{Color32, ColorImage};

    /// A live frame: a finely textured disc (radius 0.2 of the width, at
    /// the centre) whose texture is sharp only near `sharp`, on a dark
    /// backdrop with a little noise.
    fn frame(sharpness: f32, seed: u32) -> ColorImage {
        let (w, h) = (640usize, 426usize);
        let mut state = seed.wrapping_mul(2_654_435_761).max(1);
        let mut noise = || {
            state ^= state << 13;
            state ^= state >> 17;
            state ^= state << 5;
            (state % 7) as f32 - 3.0
        };
        let pixels = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                let (dx, dy) = (x - w as f32 / 2.0, y - h as f32 / 2.0);
                let inside = dx.hypot(dy) < 0.2 * w as f32;
                let texture = if (((x / 2.0) as i32 + (y / 2.0) as i32) % 2) == 0 {
                    1.0
                } else {
                    -1.0
                };
                let v = if inside {
                    120.0 + 70.0 * sharpness * texture
                } else {
                    20.0
                } + noise();
                let v = v.clamp(0.0, 255.0) as u8;
                Color32::from_rgb(v, v, v)
            })
            .collect();
        ColorImage {
            size: [w, h],
            source_size: eframe::egui::vec2(w as f32, h as f32),
            pixels,
        }
    }

    fn snapshot(phase: &str, position: u16, generation: u64, image: ColorImage) -> Snapshot {
        let mut s = Snapshot {
            online: true,
            observed: Some(std::time::Instant::now()),
            ..Default::default()
        };
        s.set_state(
            serde_json::json!({"phase":phase,"connected":true,"position":position,
            "camera_model":"ILCE-7CR"}),
        );
        s.preview = Some((generation, Arc::new(image)));
        s
    }

    /// Plan S2/S3 in the station: the survey's frames are kept while it
    /// sweeps (not before or after), Auto finds the disc in them, and the
    /// outline given to the host surrounds it.
    #[test]
    fn auto_finds_the_subject_in_the_surveys_frames() {
        let mut frames = SurveyFrames::default();
        frames.observe(&snapshot("ready", 100, 1, frame(1.0, 1)));
        assert_eq!(frames.len(), 0, "only while the host surveys");
        for k in 0..15u16 {
            let sharp = (1.0 - (f32::from(k) - 7.0).abs() / 3.0).max(0.0);
            frames.observe(&snapshot(
                "scanning",
                1000 + 10 * k,
                10 + u64::from(k),
                frame(sharp, u32::from(k) + 2),
            ));
            // The same preview twice is kept once.
            frames.observe(&snapshot(
                "scanning",
                1000 + 10 * k,
                10 + u64::from(k),
                frame(sharp, 99),
            ));
        }
        assert_eq!(frames.len(), 15);
        let mut auto = AutoSubject::default();
        auto.start(&frames, active_px(Some("ILCE-7CR"))).unwrap();
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(60);
        while auto.running() && std::time::Instant::now() < deadline {
            std::thread::sleep(std::time::Duration::from_millis(20));
            auto.poll();
        }
        let subject = auto
            .take_unsent()
            .unwrap_or_else(|| panic!("{:?}", auto.line()));
        assert!(auto.take_unsent().is_none(), "given once");
        assert_eq!(subject.provenance["kind"], "auto");
        let ring = &subject.rings[0];
        let (cx, cy) = ring
            .iter()
            .fold((0.0, 0.0), |a, p| (a.0 + p[0], a.1 + p[1]));
        let (cx, cy) = (cx / ring.len() as f32, cy / ring.len() as f32);
        assert!(
            (cx - 0.5).abs() < 0.05 && (cy - 0.5).abs() < 0.05,
            "{cx},{cy}"
        );
        let reach = ring
            .iter()
            .map(|p| ((p[0] - 0.5) * 1.5).hypot(p[1] - 0.5))
            .fold(0.0f32, f32::max);
        // The disc's radius is 0.2 of the width (0.3 of the height); the live
        // outline is loose by its buffer.
        assert!(reach > 0.25 && reach < 0.45, "{reach}");
        assert_eq!(
            subject.reference_focus.map(|f| (1000..=1140).contains(&f)),
            Some(true)
        );
        // A new survey starts a new set.
        frames.observe(&snapshot("ready", 0, 50, frame(0.0, 3)));
        frames.observe(&snapshot("scanning", 0, 51, frame(0.0, 4)));
        assert_eq!(frames.len(), 1);
    }

    /// Plan S2/S3's live Auto on the rig's own sweep: `STREHL_RIG_SWEEP`
    /// names a folder of `live-<focus>.jpg`. The frames are halved as
    /// `SurveyFrames` halves them. Prints the outline's summary.
    #[test]
    #[ignore = "needs the rig's frames (STREHL_RIG_SWEEP)"]
    fn auto_on_the_rigs_sweep() {
        let Some(folder) = std::env::var_os("STREHL_RIG_SWEEP").map(std::path::PathBuf::from)
        else {
            return;
        };
        let mut files: Vec<_> = std::fs::read_dir(&folder)
            .unwrap()
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.extension().is_some_and(|e| e == "jpg"))
            .collect();
        files.sort();
        let mut frames = SurveyFrames::default();
        for (i, f) in files.iter().enumerate() {
            let focus: u16 = f
                .file_stem()
                .unwrap()
                .to_string_lossy()
                .trim_start_matches("live-")
                .parse()
                .unwrap();
            let img = image::open(f).unwrap().to_rgb8();
            let image =
                ColorImage::from_rgb([img.width() as usize, img.height() as usize], img.as_raw());
            frames.observe(&snapshot("scanning", focus, i as u64 + 1, image));
        }
        let started = std::time::Instant::now();
        let mut auto = AutoSubject::default();
        auto.start(&frames, active_px(Some("ILCE-7CR"))).unwrap();
        while auto.running() {
            std::thread::sleep(std::time::Duration::from_millis(20));
            auto.poll();
        }
        println!(
            "{} frames in {:.2} s",
            frames.len(),
            started.elapsed().as_secs_f64()
        );
        println!("{:?}", auto.line());
        println!("depth {:?}", auto.depth_range());
        if let Some(subject) = auto.take_unsent() {
            println!(
                "rings {} points {:?} provenance {}",
                subject.rings.len(),
                subject.rings.iter().map(Vec::len).collect::<Vec<_>>(),
                subject.provenance
            );
        }
    }
}
