//! The Capture station composed (Studio 2, 7.4): the pre-flight strip, the
//! canvas (live view, or the capture in flight), the focus rail, the
//! inspector (the plan, or the health column) and glance mode, each drawn
//! into the slot the shell gives it, with the user's intents applied to the
//! camera through the workspace's own checks.
//!
//! Calls for the shell, in its frame slots:
//! `station_strip`, `station_canvas`, `station_rail`, `station_inspector`,
//! and `station_glance` over the whole window while `glance_open()`;
//! `station_hints()` for the hint bar; `take_open_rig()` for what belongs
//! to the shell.
//! Until the shell is merged, `STREHL_CAPTURE_STATION=1` lays the station
//! out inside today's Capture tab (`show_station`).
use std::{
    path::PathBuf,
    sync::Arc,
    time::{Duration, Instant, SystemTime},
};

use eframe::egui::{self, Rect, TextureHandle, TextureOptions, Ui};
use strehl_capture::session::Command;

use super::{
    CaptureWorkspace, Confirm,
    flight::{self, FlightInputs, FlightIntent},
    glance::{self, GlanceInputs, Next},
    live::{LiveIntent, LiveView},
    plan::{CalibrationView, PlanInputs, PlanIntent, PlanView, Switches, TestShotView},
    plane_view::{self, PlaneInputs, PlaneView},
    planes::PlaneDeck,
    preflight::{self, Fix},
    rail::{FlightTicks, FocusRail, RailInputs, RailIntent},
    style::CapturePalette,
    subject::{self, Destination, SubjectChoice},
    test_shot::TestShot,
    tools::Calibration,
};
use crate::capture_client::{Connection, Snapshot, host::HostPhase};
use crate::draft_preview::{ProofEvent, ProofJob, ProofUpdate};
use crate::workspace_history::NodeId;

/// What the flight ticks depend on: the plan, the counts and the
/// checker's published progress.
type TicksKey = ((u16, u16, u16), (u64, Option<u64>, u64), Option<usize>);

/// How long a dragged bound may take to be reached and marked.
const MARK_AT_TIMEOUT: Duration = Duration::from_secs(20);

/// The proof of the capture being written.
struct ProofState {
    run: PathBuf,
    job: ProofJob,
    latest: Option<Box<ProofUpdate>>,
    texture: Option<(u64, TextureHandle)>,
    error: Option<String>,
}

/// A dragged bound: focus moves there, then it is marked.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct MarkAt {
    pub start: bool,
    pub to: u16,
    pub since: Instant,
}

/// The station's views and their state.
#[derive(Default)]
pub(crate) struct Station {
    pub palette: CapturePalette,
    pub plan: PlanView,
    rail: FocusRail,
    pub live: LiveView,
    pub glance: bool,
    proof: Option<ProofState>,
    pub mark_at: Option<MarkAt>,
    /// Bounds still to move to and mark after `mark_at` (plan S4).
    pub mark_queue: Vec<(bool, u16)>,
    /// The flight rail's ticks and what they were built from.
    ticks: Option<(TicksKey, Arc<FlightTicks>)>,
    rig_requested: bool,
    /// The in-flight view's state (the feed's row positions).
    pub flight: flight::FlightView,
    /// What retakes cost the capture, and the time left as shown.
    retake_clock: flight::RetakeClock,
    left_clock: flight::LeftClock,
    left: Option<f64>,
    /// The phase seen at the last poll, and whether the capture that ended
    /// is shown for review (the flight view, until Back to planning).
    was_capturing: bool,
    pub review: bool,
    /// When the reviewed capture was seen to end.
    ended_at: Option<SystemTime>,
    pub calibrated_at: Option<SystemTime>,
    recover_open: bool,
    settings_open: bool,
    /// The catalog's subjects, for the plan's subject field, and the
    /// catalog revision they were read at.
    pub(super) subjects: Vec<SubjectChoice>,
    subjects_revision: Option<u64>,
    /// Where a new subject is made ("Bugs"), for the plan's line.
    pub(super) subject_home: String,
    /// The names the plan gave captures, by run folder (newest last).
    named_runs: std::collections::VecDeque<(PathBuf, RunNames)>,
    /// The run that took the plan's names; they are cleared for the next
    /// capture once it is over.
    names_taken_by: Option<PathBuf>,
    /// A fixture's subject choice, made once the catalog's subjects arrive
    /// (`plan+existing`, `plan+taken`; offscreen pictures only).
    fixture_subject: Option<&'static str>,
    /// A fixture's automatic selection (`plan+survey`), shown instead of
    /// the station's own.
    fixture_auto: Option<super::live::AutoView>,
    /// The plane view's data (one deck a run, kept for its review) and
    /// state, and the window's presenter its textures are uploaded with.
    planes: Option<PlaneDeck>,
    pub plane_view: PlaneView,
    presenter: Option<crate::hdr_display::PhotoPresenter>,
    /// The checker's journal of a fixture (`--capture-fixture`).
    fixture_progress: Option<Arc<super::follow::Progress>>,
    /// Retakes this desktop asked for (h-retake), shown as asked until the
    /// plane's next try is checked or the host no longer holds them.
    asked: Vec<AskedRetake>,
}

/// A retake asked for by hand: the plane, its tries when asked, when, and
/// the capture (sequence) it was asked of.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct AskedRetake {
    pub plane: u64,
    pub tries: u32,
    pub at: Instant,
    pub sequence: Option<u64>,
}

/// How long a retake asked for is shown as asked without the host saying
/// so: the state is polled five times a second, a request answered in well
/// under a second.
const ASKED_GRACE: Duration = Duration::from_secs(3);

/// The planes asked to be retaken and not taken yet, ascending: the host's
/// (queued, or in its retakes after the capture) and this desktop's own
/// requests until the plane's next try is checked or, the host no longer
/// running, holding nothing for it (h-retake).
pub(crate) fn retakes_in_hand(
    s: &Snapshot,
    asked: &[AskedRetake],
    progress: Option<&super::follow::Progress>,
    now: Instant,
) -> Vec<u64> {
    let mut planes = s.host.retakes_in_hand();
    let tries = |plane: u64| {
        progress
            .and_then(|p| {
                p.feed
                    .iter()
                    .rev()
                    .find(|i| i.plane == plane)
                    .map(|i| i.attempt)
            })
            .unwrap_or(0)
    };
    for a in asked {
        let same_run = a.sequence == s.host.sequence_id;
        let untaken = tries(a.plane) <= a.tries;
        let held = s.host.phase.capturing() || now.duration_since(a.at) < ASKED_GRACE;
        if same_run && untaken && held {
            planes.push(a.plane);
        }
    }
    planes.sort_unstable();
    planes.dedup();
    planes
}

/// The names the plan gave one capture.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct RunNames {
    pub subject: String,
    pub stack: String,
    /// The existing subject chosen on purpose, if one was.
    pub chosen: Option<NodeId>,
}

/// Which screen the station shows.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum StationMode {
    Plan,
    Flight,
}

/// The hint bar's keys and its right-hand note.
#[allow(dead_code)]
pub(crate) struct StationHints {
    pub keys: Vec<(&'static str, &'static str)>,
    pub note: String,
}

impl CaptureWorkspace {
    fn station_snapshot(&self) -> Snapshot {
        self.connection
            .as_ref()
            .map(Connection::snapshot)
            .unwrap_or_default()
    }

    /// The palette the screens draw with (the shell's tokens).
    pub fn set_palette(&mut self, palette: CapturePalette) {
        self.station.palette = palette;
    }

    /// Zooms the depth rail to focus units `lo` to `hi` (`--capture-rail-view`).
    pub fn set_rail_view(&mut self, lo: u16, hi: u16) {
        self.station
            .rail
            .set_view(Some(super::rail::RailView::of((lo, hi))));
    }

    /// The catalog's subjects, offered by the plan's subject field.
    pub fn set_subjects(&mut self, subjects: Vec<SubjectChoice>) {
        if let Some(first) = subjects.first()
            && let Some(how) = self.station.fixture_subject.take()
        {
            let plan = &mut self.station.plan;
            if how == "existing" {
                plan.subject = first.name.clone();
                plan.chosen = Some(first.id);
            } else {
                plan.subject = first.name.to_lowercase();
                plan.chosen = None;
            }
        }
        self.station.subjects = subjects;
    }

    /// Where a new subject is made, named for the plan ("Bugs").
    pub fn set_subject_home(&mut self, home: &str) {
        if self.station.subject_home != home {
            home.clone_into(&mut self.station.subject_home);
        }
    }

    /// Where a capture started now would go (`capture-subject.rs`).
    pub(crate) fn plan_destination(&self) -> Destination {
        subject::destination(
            &self.station.plan.subject,
            self.station.plan.chosen,
            &self.station.subjects,
        )
    }

    /// Whether the subject names were read before catalog `revision`;
    /// records it as read.
    pub fn subjects_stale(&mut self, revision: u64) -> bool {
        let stale = self.station.subjects_revision != Some(revision);
        self.station.subjects_revision = Some(revision);
        stale
    }

    /// Records the plan's names for the capture in `run` (the newest 16).
    #[cfg(test)]
    pub(crate) fn remember_names(&mut self, run: PathBuf, subject: String, stack: String) {
        self.remember_run(
            run,
            RunNames {
                subject,
                stack,
                chosen: None,
            },
        );
    }
    pub(crate) fn remember_run(&mut self, run: PathBuf, names: RunNames) {
        self.station.named_runs.push_back((run, names));
        if self.station.named_runs.len() > 16 {
            self.station.named_runs.pop_front();
        }
    }

    /// The rail's mesh builds and the live view's texture uploads so far
    /// (performance checks: pointer motion must not add to either).
    #[allow(dead_code)]
    pub(crate) fn station_counters(&self) -> (u64, u64) {
        (self.station.rail.rebuilds, self.station.live.uploads)
    }

    /// The plan's subject and stack names as typed (the shell's breadcrumb).
    pub fn plan_names(&self) -> (&str, &str) {
        (
            self.station.plan.subject.trim(),
            self.station.plan.stack_name.trim(),
        )
    }

    /// A new stack asked for from a subject in the Library: the plan names
    /// that subject, chosen on purpose.
    pub fn set_plan_subject(&mut self, id: NodeId, subject: &str) {
        self.station.plan.subject = subject.to_owned();
        self.station.plan.chosen = Some(id);
    }

    /// A new stack into a new subject ("New subject > From the camera"):
    /// the plan's subject is cleared, to be named.
    pub fn clear_plan_subject(&mut self) {
        self.station.plan.subject.clear();
        self.station.plan.chosen = None;
    }

    /// A new capture from nothing (owner feedback, 2026-11-23: after a
    /// capture there was no way back to a clean plan short of restarting).
    /// Ends the review of the last capture and clears what belonged to it
    /// and its subject: the test shot, the step calibration (unless
    /// `keep_calibration`: "Shoot again" frames the same subject), the plan's
    /// names, a typed step and an open comparison. A host that offers it
    /// also forgets the bounds' marks, the subject box and the survey.
    /// The rig's settings (exposure, step, settle, retakes, power) stay.
    /// Nothing that is running is touched: a test shot or calibration in
    /// progress, the capture's checker and stacking go on.
    pub fn new_capture(&mut self, keep_calibration: bool) {
        let s = self.station_snapshot();
        if s.host.phase.capturing() {
            return;
        }
        let station = &mut self.station;
        station.review = false;
        station.ended_at = None;
        station.plane_view.follow();
        station.planes = None;
        station.proof = None;
        station.mark_at = None;
        station.mark_queue.clear();
        station.asked.clear();
        station.names_taken_by = None;
        station.plan.subject.clear();
        station.plan.chosen = None;
        station.plan.stack_name.clear();
        station.plan.custom_step.clear();
        station.plan.guide = None;
        if !self.test_shot.running() {
            self.test_shot = super::test_shot::TestShot::Idle;
            self.test_shot_exposure = None;
        }
        if !keep_calibration && !self.calibrating() {
            self.calibration = super::tools::Calibration::Idle;
            self.station.calibrated_at = None;
        }
        self.error = None;
        self.pending_subject = None;
        self.pending_highlight = None;
        if s.host.capabilities.new_plan && s.fresh() && !s.host.phase.active() {
            self.command(&s, Command::NewPlan {});
        }
    }

    /// Plan X5: a highlight pass over the ended capture's planes whose
    /// highlights pinned: at the plan's highlight shutter (two stops shorter
    /// where its group still pinned), else four stops under the base.
    fn highlight_pass(&mut self, s: &Snapshot) {
        let Some(progress) = self.station_progress() else {
            return;
        };
        let Some(e) = s.host.exposure.as_ref() else {
            self.error = Some("The camera reports no exposure".into());
            return;
        };
        let base = e.shutter.unwrap_or(0);
        let planned = s
            .host
            .plan
            .as_ref()
            .and_then(|p| p.highlight)
            .map(|h| h.shutter);
        let (unheld, _) = progress.unheld_highlights();
        let shorter = progress.highlights_still_pinned();
        let mut sent = false;
        for (planes, shutter) in [
            (
                unheld
                    .into_iter()
                    .filter(|p| !shorter.contains(p))
                    .collect::<Vec<_>>(),
                planned.or_else(|| super::plan::shorter_shutter(&e.shutter_options, base, 4.0)),
            ),
            (
                shorter,
                planned
                    .and_then(|h| super::plan::shorter_shutter(&e.shutter_options, h, 2.0))
                    .or_else(|| super::plan::shorter_shutter(&e.shutter_options, base, 6.0)),
            ),
        ] {
            let Some(shutter) = shutter.filter(|_| !planes.is_empty()) else {
                continue;
            };
            // One pass at a time: the second is asked for once the first ends.
            if sent {
                self.follow_note = Some(
                    "A shorter pass is still due on planes whose highlight groups pinned; ask again once this pass ends."
                        .into(),
                );
                break;
            }
            self.command(
                s,
                Command::QueuePass {
                    planes,
                    tier: "highlight".into(),
                    shutter,
                },
            );
            sent = true;
        }
    }

    /// The camera host's state as this desktop has it.
    pub(crate) fn snapshot_typed(&self) -> Snapshot {
        self.station_snapshot()
    }

    /// Plan R3: a pass of another exposure over planes of the host's latest
    /// capture, once it has ended.
    pub(crate) fn queue_pass(
        &mut self,
        planes: Vec<u64>,
        tier: &str,
        shutter: u64,
    ) -> anyhow::Result<()> {
        let s = self.station_snapshot();
        anyhow::ensure!(
            s.host.capabilities.exposure_tiers,
            "This camera host cannot take passes; update the Pi's Strehl"
        );
        let request = s.request(Command::QueuePass {
            planes,
            tier: tier.into(),
            shutter,
        })?;
        self.submit(request)
    }

    /// Plan R3: retakes of the host's latest capture's planes after it.
    pub(crate) fn queue_retakes_after(&mut self, planes: Vec<u64>) -> anyhow::Result<()> {
        let s = self.station_snapshot();
        anyhow::ensure!(
            s.host.takes_manual_retakes(),
            "This camera host cannot take retakes by hand; update the Pi's Strehl"
        );
        let request = s.request(Command::QueueRetakes { planes })?;
        self.submit(request)
    }

    /// The reviewed capture, when it was stopped (by hand or by a fault)
    /// and the host lists it with its planes (`verify_stopped`).
    fn stopped_under_review<'a>(
        &self,
        s: &'a Snapshot,
    ) -> Option<&'a crate::capture_client::StoppedCapture> {
        if !self.station.review || s.host.phase.capturing() {
            return None;
        }
        let run = self.station.planes.as_ref().map(|deck| &deck.run)?;
        s.stopped.iter().find(|c| &c.folder == run)
    }

    /// The existing subject chosen in the plan, if one is.
    pub fn plan_chosen(&self) -> Option<NodeId> {
        self.station.plan.chosen
    }

    /// Everything the plan gave the capture in `run`.
    pub fn run_names(&self, run: &std::path::Path) -> Option<RunNames> {
        self.station
            .named_runs
            .iter()
            .rev()
            .find(|(r, _)| r == run)
            .map(|(_, names)| names.clone())
    }

    /// The checker's progress: the follower's, or a fixture's.
    pub(crate) fn station_progress(&self) -> Option<Arc<super::follow::Progress>> {
        self.follower
            .as_ref()
            .map(|f| f.progress_arc())
            .or_else(|| self.station.fixture_progress.clone())
    }

    /// The window's presenter: the plane view uploads its tiles with it,
    /// off the UI thread.
    pub fn set_presenter(&mut self, presenter: Option<&crate::hdr_display::PhotoPresenter>) {
        if self.station.presenter.is_none() {
            self.station.presenter = presenter.cloned();
        }
    }

    /// The plane view's state, the picture it shows and its tiles
    /// (benchmarks).
    #[cfg(test)]
    pub(crate) fn plane_view_parts(
        &mut self,
    ) -> (
        &mut PlaneView,
        Option<Arc<super::planes::PlaneImage>>,
        usize,
        f64,
    ) {
        let image = self
            .station
            .planes
            .as_ref()
            .and_then(|d| d.image().cloned());
        let tiles = self
            .station
            .planes
            .as_ref()
            .map_or(0, PlaneDeck::tile_count);
        let poll = self.station.planes.as_ref().map_or(0.0, |d| d.poll_ms);
        (&mut self.station.plane_view, image, tiles, poll)
    }

    /// Whether the plane view shows what it asked for (offscreen
    /// screenshots wait for it).
    pub fn plane_view_settled(&self) -> bool {
        self.station_mode() != StationMode::Flight
            || self.station.planes.as_ref().is_none_or(PlaneDeck::settled)
    }

    /// Loads a fixture (`--capture-fixture plan|flight|glance`): the
    /// station shows it from a connection that sends nothing.
    pub fn load_fixture(&mut self, name: &str) -> anyhow::Result<()> {
        use super::fixture::{self, Fixture};
        // `plan+rig`, `plan+guide`, `plan+schedule`...: a plan with a panel open.
        let (name, open) = name.split_once('+').unwrap_or((name, ""));
        let which = Fixture::parse(name)
            .ok_or_else(|| anyhow::anyhow!("Use --capture-fixture plan, flight or glance"))?;
        // `flight+long`: a 6,000-plane stack with hundreds of retakes;
        // `flight+done`: the capture ended, under review; `flight+show`: a
        // plane's RAW shown from the feed.
        let long = (which != Fixture::Plan && open == "long").then(fixture::long_progress);
        // `flight+retakes`, `flight+retakes-done` (h-retake): a plane asked
        // to be retaken by hand and a run of one-shot planes.
        let retakes = which != Fixture::Plan && open.starts_with("retakes");
        let open = if open == "retakes-done" { "done" } else { open };
        // `plan+survey`: per-position shutters, an outline with the
        // automatic selection's panel, and a two-shutter survey's result.
        let survey = which == Fixture::Plan && open == "survey";
        let mut snapshot = if survey {
            fixture::survey_snapshot()
        } else {
            fixture::snapshot(which)
        };
        if let Some((_, groups)) = &long {
            fixture::lengthen(&mut snapshot, *groups);
        }
        if retakes {
            fixture::add_retakes(&mut snapshot, open == "done");
        }
        if which != Fixture::Plan && open == "done" {
            fixture::finish(&mut snapshot);
            self.station.review = true;
            self.station.ended_at = Some(SystemTime::now());
        }
        self.connection = Some(Connection::fixture(snapshot));
        if which == Fixture::Plan {
            let trace = fixture::focus_trace(&self.station_snapshot());
            self.station.live.trace.seed(trace);
        }
        self.station.plan.subject = "Blue weevil".into();
        self.station.plan.stack_name = "Dorsal · 2.8×".into();
        self.test_shot = TestShot::Done {
            folder: PathBuf::from("fixture"),
            levels: fixture::test_levels(),
            taken: fixture::earlier(16),
        };
        self.calibration = Calibration::Done(serde_json::json!({"width":50.0,"suggested_step":7,
            "summary":"Detail stays sharp over about 50 focus units."}));
        self.station.calibrated_at = Some(fixture::earlier(14));
        if survey {
            self.calibration = Calibration::Done(fixture::survey_result());
            self.station.live.outline = true;
            self.station.fixture_auto = Some(super::live::AutoView {
                frames: 31,
                running: false,
                line: Some(
                    "Found in 31 frames: 28.7 % of the frame, sharp 37,100 to 37,764".into(),
                ),
                params: Some([4.0, 2.0, 24.0]),
            });
        }
        self.test_shot_exposure = Some((100, 65544));
        // `plan+calibrated`: the pass done, its readout and the Depth lens
        // from RAW; `plan+calibrating`: the survey part-way, the lens from
        // the live sweep (spec 9, S2).
        // `plan+lens-cover|light|glints|still`: calibrated, with that lens on.
        let lens = open.strip_prefix("lens-");
        if which == Fixture::Plan
            && (matches!(open, "calibrated" | "calibrating") || lens.is_some())
        {
            let done = open != "calibrating";
            self.pass = super::measure::Pass {
                stage: if done {
                    super::measure::Stage::Done
                } else {
                    super::measure::Stage::Survey {
                        shutters: (65_537, 65_568),
                        positions: 62,
                    }
                },
                facts: fixture::pass_facts(done),
                started: Some(Instant::now()),
                finished: done.then(|| fixture::earlier(3)),
                ..Default::default()
            };
            if let Some(survey) = self.pass.facts.survey.clone() {
                self.calibration =
                    Calibration::Done(serde_json::json!({"width":45.0,"suggested_step":6,
                    "summary":"Detail stays sharp over about 45 focus units.","survey":survey}));
            }
            self.station.live.lens = match lens {
                Some("cover") => super::live::Lens::Cover,
                Some("light") => super::live::Lens::Light,
                Some("glints") => super::live::Lens::Glints,
                Some("still") => super::live::Lens::Still,
                _ => super::live::Lens::Depth,
            };
            self.station.live.peaking = false;
        }
        self.open_fixture_panel(open);
        // The subject's states (owner feedback, 2026-11-22): unnamed, its
        // list open, an existing subject chosen, or one's name typed.
        match open {
            "unnamed" => self.clear_plan_subject(),
            "subjects" => {
                self.clear_plan_subject();
                self.station.plan.focus_subject = true;
            }
            "existing" | "taken" => {
                self.clear_plan_subject();
                self.station.fixture_subject = Some(if open == "existing" {
                    "existing"
                } else {
                    "taken"
                });
            }
            _ => {}
        }
        if which != Fixture::Plan {
            self.station.fixture_progress = Some(Arc::new(match long {
                Some((progress, _)) => progress,
                None if retakes => fixture::retake_progress(open == "done").0,
                None if open == "done" => fixture::finished_progress().0,
                None => fixture::progress(),
            }));
            let image = fixture::subject_image(960, 640, 0.8);
            let rgba = image.pixels.iter().flat_map(|p| p.to_array()).collect();
            let update = ProofUpdate {
                draft: crate::draft_preview::DraftPreview {
                    image: crate::preview::PreviewImage {
                        path: PathBuf::from("fixture"),
                        source_size: [960, 640],
                        size: [960, 640],
                        rgba,
                        is_overview: true,
                    },
                    source_frames: 61,
                    aligned_frames: 61,
                    skipped_frames: 0,
                    alignment_edges: 0,
                    cycle_rank: 0,
                    reference_frame: 30,
                    warnings: Vec::new(),
                },
                received: 61,
                used: 61,
                stride: 1,
                revision: 1,
            };
            self.station.proof = Some(ProofState {
                run: PathBuf::from("fixture"),
                job: ProofJob::start(),
                latest: Some(Box::new(update)),
                texture: None,
                error: None,
            });
            self.load_fixture_planes(open);
        }
        self.station.glance = which == Fixture::Glance;
        Ok(())
    }

    /// The flight fixtures' planes: a synthetic subject tilted in depth, its
    /// verdicts from the fixture's journal (`flight+show` shows plane 52's
    /// first try, as "Show" in the feed does). With `STREHL_FIXTURE_RUN` (a
    /// capture folder, read only) and `STREHL_FIXTURE_JOURNAL` (a copy of
    /// its checker journal) the planes are that run's RAWs instead.
    fn load_fixture_planes(&mut self, open: &str) {
        use super::planes::FixtureSource;
        let run = std::env::var_os("STREHL_FIXTURE_RUN").map(PathBuf::from);
        let journal = std::env::var_os("STREHL_FIXTURE_JOURNAL")
            .and_then(|j| std::fs::read_to_string(j).ok());
        if let (Some(run), Some(journal)) = (run, journal) {
            let progress = super::follow::progress(&journal);
            let planes = progress.planes.keys().next_back().copied().unwrap_or(0);
            if let Some(c) = self.connection.as_ref() {
                let mut s = c.snapshot();
                let mut state = s.state.clone();
                state["completed"] = serde_json::json!(planes);
                state["total"] = serde_json::json!(planes);
                state["message"] = serde_json::json!(format!("Plane {planes} of {planes}"));
                s.set_state(state);
                self.connection = Some(Connection::fixture(s));
            }
            self.station.fixture_progress = Some(Arc::new(progress));
            // `STREHL_FIXTURE_REPLAY_MS`: its tries arrive one at that pace.
            let replay = std::env::var("STREHL_FIXTURE_REPLAY_MS")
                .ok()
                .and_then(|m| m.parse().ok())
                .map(Duration::from_millis);
            self.station.planes = Some(match replay {
                Some(every) => PlaneDeck::start(
                    run.clone(),
                    Box::new(super::planes::ReplaySource::new(run, 4, every)),
                ),
                None => PlaneDeck::for_run(run, 4),
            });
        } else {
            let progress = self.station.fixture_progress.clone().unwrap_or_default();
            let planes = self.station_snapshot().host.total.max(1);
            // Smaller pictures under test; about a 24 MP sensor otherwise.
            // `STREHL_FIXTURE_SIZE=WxH` sizes them (benchmarks).
            let size = std::env::var("STREHL_FIXTURE_SIZE")
                .ok()
                .and_then(|s| {
                    let (w, h) = s.split_once('x')?;
                    Some([w.parse().ok()?, h.parse().ok()?])
                })
                .unwrap_or(if cfg!(test) { [960, 640] } else { [6000, 4000] });
            let source = FixtureSource::new(&progress, planes, size);
            self.station.planes =
                Some(PlaneDeck::start(PathBuf::from("fixture"), Box::new(source)));
        }
        self.station.plane_view = PlaneView::default();
        // Offscreen checks: `STREHL_FIXTURE_SHOW=<plane>` shows that plane's
        // last try, `STREHL_FIXTURE_ZOOM=<screen px a photosite>,<u>,<v>`
        // zooms about a point.
        if let Some(plane) = std::env::var("STREHL_FIXTURE_SHOW")
            .ok()
            .and_then(|p| p.parse().ok())
        {
            self.station.plane_view.show(plane, None);
        }
        if let Some([z, u, v]) = std::env::var("STREHL_FIXTURE_ZOOM").ok().and_then(|z| {
            let v: Vec<f32> = z.split(',').filter_map(|p| p.trim().parse().ok()).collect();
            <[f32; 3]>::try_from(v).ok()
        }) {
            self.station.plane_view.set_zoom(Some(z), egui::pos2(u, v));
        }
        // A benchmark's baseline: the flight view without the plane view's
        // workers.
        #[cfg(test)]
        if std::env::var_os("STREHL_BENCH_NO_DECK").is_some() {
            self.station.planes = None;
        }
        if open == "show" {
            let first = self
                .station
                .fixture_progress
                .as_ref()
                .and_then(|p| p.feed.iter().find(|i| i.plane == 52))
                .and_then(|i| i.first.clone());
            self.station.plane_view.show(52, first);
        }
    }

    /// Plan, or flight while a capture runs or is paused, and while the
    /// capture that ended is reviewed.
    pub fn station_mode(&self) -> StationMode {
        if (self.station.review || self.station_snapshot().host.phase.capturing())
            && !self.calibrating()
            && !self.test_shot.running()
        {
            StationMode::Flight
        } else {
            StationMode::Plan
        }
    }

    /// Glance mode is open (it covers the window).
    #[allow(dead_code)]
    pub fn glance_open(&self) -> bool {
        self.station.glance
    }

    /// Opens glance mode (the shell's `G`, or the stage-1 preview).
    #[allow(dead_code)]
    pub fn open_glance(&mut self) {
        self.station.glance = true;
    }

    /// The shell's rig popover was asked for from the plan.
    #[allow(dead_code)]
    pub fn take_open_rig(&mut self) -> bool {
        std::mem::take(&mut self.station.rig_requested)
    }

    /// The keys the station answers, for the hint bar.
    #[allow(dead_code)]
    pub fn station_hints(&self) -> StationHints {
        let s = self.station_snapshot();
        let note = if s.fresh() {
            let receiver = if s.receiver["ok"] == true {
                "receiver ready"
            } else {
                "receiver not ready"
            };
            match s.receiver["folder"].as_str().filter(|f| !f.is_empty()) {
                Some(folder) => format!("Camera host online · {receiver} · {folder}"),
                None => format!("Camera host online · {receiver}"),
            }
        } else {
            "Camera host offline".into()
        };
        match self.station_mode() {
            StationMode::Plan => StationHints {
                keys: vec![
                    ("←→", "focus by 1"),
                    ("Shift", "by 16"),
                    ("S", "mark start"),
                    ("E", "mark end"),
                    ("T", "test shot"),
                    ("Enter", "start"),
                    ("Wheel", "rail scale"),
                ],
                note,
            },
            StationMode::Flight if self.station.review => StationHints {
                keys: vec![],
                note: "The capture has ended; New capture for the next stack".into(),
            },
            StationMode::Flight => StationHints {
                keys: vec![
                    ("Space", "pause"),
                    ("G", "glance mode"),
                    ("← →", "planes"),
                    ("End", "newest"),
                ],
                note: "Stop asks first, and keeps the planes already taken".into(),
            },
        }
    }

    /// The retakes' cost, the time left as shown, and the review of a
    /// capture that ended: a capture this desktop watched that completes or
    /// is stopped stays in the flight view, with what happened to every
    /// plane, until Back to planning (or the next capture).
    fn observe_flight(&mut self, s: &Snapshot) {
        let host = &s.host;
        // A test shot or a calibration's survey is not a stack.
        let other = self.test_shot.running()
            || self.calibrating()
            || s.in_progress.as_ref().is_some_and(|r| r.test);
        let station = &mut self.station;
        station.retake_clock.observe(s);
        station.left = station.left_clock.update(
            host.timer
                .as_ref()
                .and_then(|t| t.remaining)
                .filter(|_| host.phase.capturing()),
            host.sequence_id,
            host.phase == HostPhase::Capturing,
            Instant::now(),
        );
        let capturing = host.phase.capturing();
        if capturing {
            station.review = false;
        } else if station.was_capturing
            && matches!(host.phase, HostPhase::Complete | HostPhase::Stopped)
        {
            station.review = true;
            station.ended_at = Some(SystemTime::now());
        }
        station.was_capturing = capturing && !other;
    }

    /// Advances the proof and a dragged bound; called with the other polls.
    pub(super) fn poll_station(&mut self, s: &Snapshot) {
        // The lens and the plan as the host holds them, before painting.
        self.observe_focus(s);
        if let Some(plan) = s.host.plan.clone() {
            self.sync_plan(plan, s.host.plan_revision.unwrap_or(0));
        }
        // A run a tool of this desktop started (a test shot, a calibration's
        // survey, a sequence it stopped following) is not a stack: it takes
        // no names and gets no proof or plane deck (owner, 2026-11-24: the
        // subject name was cleared after Calibrate step).
        let tool = self.not_a_stack(s);
        // The proof follows the capture being written (not a test shot).
        if let Some(run) = s
            .in_progress
            .as_ref()
            .filter(|r| !r.test && !tool && s.host.phase.capturing())
            && self
                .station
                .proof
                .as_ref()
                .is_none_or(|p| p.run != run.folder)
        {
            self.station.proof = Some(ProofState {
                run: run.folder.clone(),
                job: ProofJob::for_run(run.folder.clone(), s.host.shots()),
                latest: None,
                texture: None,
                error: None,
            });
        }
        // So does the plane view's deck, kept after the capture for review.
        if let Some(run) = s
            .in_progress
            .as_ref()
            .filter(|r| !r.test && !tool && s.host.phase.capturing())
            && self
                .station
                .planes
                .as_ref()
                .is_none_or(|d| d.run != run.folder)
        {
            self.station.planes = Some(PlaneDeck::for_run(run.folder.clone(), s.host.shots()));
            self.station.plane_view = PlaneView::default();
        }
        // Back to planning: the deck and its picture (a few hundred MB) go.
        if self.station.planes.is_some() && self.station_mode() == StationMode::Plan {
            self.station.planes = None;
        }
        if let Some(run) = s
            .in_progress
            .as_ref()
            .filter(|r| !r.test && !tool && s.host.phase.capturing())
            && !self
                .station
                .named_runs
                .iter()
                .any(|(r, _)| *r == run.folder)
        {
            let names = RunNames {
                subject: self.station.plan.subject.trim().to_owned(),
                stack: self.station.plan.stack_name.trim().to_owned(),
                chosen: self.station.plan.chosen,
            };
            let folder = run.folder.clone();
            if names != RunNames::default() {
                self.remember_run(folder.clone(), names);
            }
            self.station.names_taken_by = Some(folder);
        }
        if let Some(proof) = &mut self.station.proof {
            match proof.job.poll() {
                Some(ProofEvent::Updated(update)) => {
                    proof.latest = Some(update);
                    proof.error = None;
                }
                Some(ProofEvent::Failed(e)) => proof.error = Some(e),
                None => {}
            }
        }
        self.observe_flight(s);
        // A capture took the names: once it is over (and reviewed), the
        // next one starts from a new, unnamed subject again.
        if self.station.names_taken_by.is_some() && self.station_mode() == StationMode::Plan {
            self.station.names_taken_by = None;
            self.clear_plan_subject();
            self.station.plan.stack_name.clear();
        }
        // A dragged bound: once the lens is there and the camera idle, mark.
        if let Some(at) = self.station.mark_at {
            let host = &s.host;
            if at.since.elapsed() > MARK_AT_TIMEOUT || !s.fresh() {
                self.station.mark_at = None;
                self.station.mark_queue.clear();
                self.error = Some("The bound was not reached; it was not marked".into());
            } else if host.position == Some(at.to)
                && host.editable
                && !s.pending
                && self.focus_pending.is_none()
                && self.focus_flight.is_none()
            {
                self.station.mark_at = None;
                self.command(s, Command::Mark { start: at.start });
            }
        } else if !s.pending
            && s.host.editable
            && let Some((start, to)) = self.station.mark_queue.pop()
        {
            // The next bound of a pair (plan S4's subject bounds).
            self.station.mark_at = Some(MarkAt {
                start,
                to,
                since: Instant::now(),
            });
            if s.host.position != Some(to) {
                self.focus_pending = Some(to);
            }
        }
    }

    fn proof_texture(
        &mut self,
        ctx: &egui::Context,
    ) -> Option<(egui::TextureId, egui::Vec2, String)> {
        let proof = self.station.proof.as_mut()?;
        let update = proof.latest.as_ref()?;
        if proof
            .texture
            .as_ref()
            .is_none_or(|(r, _)| *r != update.revision)
        {
            let image = &update.draft.image;
            let color = egui::ColorImage::from_rgba_unmultiplied(image.size, &image.rgba);
            match &mut proof.texture {
                Some((r, t)) => {
                    t.set(color, TextureOptions::LINEAR);
                    *r = update.revision;
                }
                None => {
                    proof.texture = Some((
                        update.revision,
                        ctx.load_texture("capture-proof", color, TextureOptions::LINEAR),
                    ))
                }
            }
        }
        let (_, t) = proof.texture.as_ref()?;
        let what = if update.stride > 1 {
            format!("planes 1–{}, one in {}", update.received, update.stride)
        } else {
            format!("planes 1–{}", update.received)
        };
        Some((t.id(), t.size_vec2(), what))
    }

    /// The pre-flight strip, in the control strip's slot.
    pub fn station_strip(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let blockers = preflight::start_blockers(&s, self);
        let chips = preflight::strip_chips(&s, &blockers);
        let rows = super::plan::step_rows(
            &s,
            s.host.plan.as_ref().map_or(1, |p| p.step),
            s.host.plan.as_ref().map_or(500, |p| p.settle_ms),
            &self.calibration_result(),
        );
        let summary = super::plan::strip_summary(&s, &rows);
        let palette = self.station.palette;
        if let Some(fix) = preflight::strip_ui(ui, &chips, &blockers, &summary, &palette) {
            self.apply_fix(&s, fix);
        }
    }

    fn calibration_result(&self) -> serde_json::Value {
        match &self.calibration {
            Calibration::Done(v) | Calibration::Restoring { result: v, .. } => v.clone(),
            Calibration::Failed(e) => serde_json::json!({"error":e}),
            _ => serde_json::Value::Null,
        }
    }

    /// The canvas: the live view while planning, the capture in flight.
    pub fn station_canvas(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let palette = self.station.palette;
        self.shown = true;
        // An offscreen screenshot waits for the state that was drawn.
        self.painted_ready = (!s.receiver.is_null() || s.receiver_error.is_some())
            && ((s.observed.is_some() && (s.preview.is_some() || !s.host.preview.available))
                || s.connection_error.is_some()
                || self.config.controller.is_empty());
        self.station_canvas_body(ui, &s, &palette);
        // A focus target from the rail or a dragged bound goes out once the
        // camera is free (the canvas is the station's last slot).
        self.flush_focus(&s);
    }

    fn station_canvas_body(&mut self, ui: &mut Ui, s: &Snapshot, palette: &CapturePalette) {
        let palette = palette.on_canvas();
        match self.station_mode() {
            StationMode::Plan => {
                self.station.live.auto =
                    self.station
                        .fixture_auto
                        .clone()
                        .unwrap_or_else(|| super::live::AutoView {
                            frames: self.survey_frames.len(),
                            running: self.auto_subject.running(),
                            line: self.auto_subject.line(),
                            params: self
                                .auto_subject
                                .params()
                                .map(|p| [p.sensitivity, p.grow, p.buffer_px]),
                        });
                // Spec 6.1: the calibration's depth map, from RAW once the
                // survey is read, else from the live sweep.
                self.station.live.depth = self.depth_map();
                self.station.live.rail_hover = self.station.rail.hover;
                let intents = self.station.live.show(ui, s, &palette);
                for intent in intents {
                    self.apply_live(s, intent);
                }
            }
            StationMode::Flight => {
                let progress = self.station_progress();
                let inputs = self.flight_inputs(s, progress.as_deref());
                let mut view = std::mem::take(&mut self.station.flight);
                let intents = flight::canvas(ui, &inputs, &mut view, &palette);
                let plane_rect = view.plane.unwrap_or(Rect::NOTHING);
                self.station.flight = view;
                // The plane view, in the place the canvas left for it.
                if let Some(deck) = &mut self.station.planes {
                    deck.set_uploader(self.station.presenter.as_ref(), ui.ctx());
                    deck.poll();
                }
                let exposure = s.host.exposure.as_ref().and_then(|e| {
                    let iso = e.iso.map(super::style::iso_label);
                    let shutter = e.shutter.map(super::style::shutter_label);
                    let parts: Vec<String> = [iso, shutter].into_iter().flatten().collect();
                    (!parts.is_empty()).then(|| parts.join(" · "))
                });
                let plane_inputs = PlaneInputs {
                    progress: progress.as_deref(),
                    total: s.host.total,
                    checking: self.follow_enabled,
                    exposure,
                };
                plane_view::panel(
                    ui,
                    plane_rect,
                    self.station.planes.as_mut(),
                    &mut self.station.plane_view,
                    &plane_inputs,
                    &palette,
                );
                for intent in intents {
                    self.apply_flight(s, intent);
                }
                // The time left counts down by the second.
                if s.host.phase == HostPhase::Capturing {
                    ui.ctx().request_repaint_after(Duration::from_millis(250));
                }
            }
        }
    }

    /// The time left as the station shows it (eased, see
    /// `flight::LeftClock`), else the host's estimate: the top bar and the
    /// status line say the same as the flight view.
    pub(crate) fn time_left(&self, s: &Snapshot) -> Option<f64> {
        self.station
            .left
            .or_else(|| s.host.timer.as_ref().and_then(|t| t.remaining))
    }

    /// What the in-flight view shows, but its pictures.
    fn flight_inputs<'a>(
        &self,
        s: &'a Snapshot,
        progress: Option<&'a super::follow::Progress>,
    ) -> FlightInputs<'a> {
        let clock = &self.station.retake_clock;
        FlightInputs {
            s,
            progress,
            checking: self.follow_enabled,
            stack_when_done: self.stack_when_done,
            power_down: s.host.power.as_ref().map(|p| p.manage_stack),
            confirm_stop: self.confirm == Some(Confirm::Stop),
            left: self.station.left,
            retake_cost: clock.cost(progress.map_or(0, |p| p.retakes as u64)),
            plain_pace: clock.plain_pace(),
            ended: self.station.review && !s.host.phase.capturing(),
            highlight_pass: progress
                .filter(|_| {
                    self.station.review
                        && !s.host.phase.capturing()
                        && s.host.capabilities.exposure_tiers
                })
                .map(|p| p.unheld_highlights().0.len() + p.highlights_still_pinned().len())
                .filter(|n| *n > 0),
            stack_stopped: self
                .stopped_under_review(s)
                .map(|run| run.planes.min(run.frames / run.shots_per_plane.max(1)))
                .filter(|planes| *planes >= 2),
            ended_at: self.station.ended_at.map(|t| {
                chrono::DateTime::<chrono::Local>::from(t)
                    .format("%H:%M")
                    .to_string()
            }),
            highlights: self
                .stacked_highlights
                .as_ref()
                .filter(|(dir, _, _)| {
                    s.host.last_receipt_run().is_some_and(|run| {
                        std::fs::canonicalize(&run).ok() == std::fs::canonicalize(dir).ok()
                    })
                })
                .map(|(_, line, all)| (line.clone(), *all)),
            retakes: flight::RetakeInputs {
                in_hand: retakes_in_hand(s, &self.station.asked, progress, Instant::now()),
                step: s.host.plan.as_ref().map(|p| p.step),
                width: self.calibration_result()["width"].as_f64(),
            },
        }
    }

    /// Glance mode, drawn over the whole window (top bar and hint bar
    /// included), as the mockup's bare screen.
    pub fn station_glance_overlay(&mut self, ctx: &egui::Context) {
        let screen = ctx.content_rect();
        egui::Area::new(egui::Id::new("capture-glance"))
            .order(egui::Order::Foreground)
            .fixed_pos(screen.min)
            .show(ctx, |ui| {
                ui.set_min_size(screen.size());
                let mut child = ui.new_child(egui::UiBuilder::new().max_rect(screen));
                self.station_glance(&mut child);
            });
    }

    /// The focus rail, in the rail's slot.
    pub fn station_rail(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let host = &s.host;
        let palette = self.station.palette;
        let flight_mode = self.station_mode() == StationMode::Flight;
        let (start, end) = host.plan_bounds();
        let progress = self.station_progress();
        let ticks = flight_mode.then(|| {
            let step = host.plan.as_ref().map_or(1, |p| p.step);
            // Rebuilt only when a plane's state can have changed.
            let key = (
                (start, end, step),
                (host.completed, host.storage.saved_frames, host.shots()),
                progress.as_ref().map(|p| Arc::as_ptr(p) as usize),
            );
            if self.station.ticks.as_ref().is_none_or(|(k, _)| *k != key) {
                let revision = self.station.ticks.as_ref().map_or(0, |(_, t)| t.revision) + 1;
                let mut ticks = flight::flight_ticks(
                    super::rail::planned(start, end, step),
                    &s,
                    progress.as_deref(),
                );
                ticks.revision = revision;
                self.station.ticks = Some((key, Arc::new(ticks)));
            }
            self.station.ticks.as_ref().map(|(_, t)| t.clone()).unwrap()
        });
        // Spec 6.3: once calibrated, the bars are the subject's tiles in
        // focus by position (the survey's, else the live sweep's peaks), not
        // the host's energy; a broad hump of "sharpness" is not drawn.
        let calibrated = self.rail_samples();
        let survey = match &calibrated {
            Some((_, caption)) => Some(caption.clone()),
            None => {
                (!host.samples.is_empty()).then(|| "survey: where the subject is sharp".to_owned())
            }
        };
        let samples: &[crate::capture_client::host::SurveySample] = match &calibrated {
            Some((samples, _)) => samples,
            None => &host.samples,
        };
        let inputs = RailInputs {
            samples,
            start: host.start_set.then_some(start),
            end: host.end_set.then_some(end),
            step: host.plan.as_ref().map_or(1, |p| p.step),
            lens: self.focus_pending.or(host.position),
            flight: ticks.as_deref(),
            survey,
            // The host's half-height bounds are not offered once calibrated
            // (spec 5.2): the Depth step offers the calibration's.
            can_use_survey: calibrated.is_none()
                && host.suggestion.as_ref().is_some_and(|s| !s.clipped),
            editable: s.fresh() && host.editable && !s.pending && self.focus_flight.is_none(),
            keys: !self.station.glance && !self.schedule_ui.editing(),
            ends: (host.lens_travel.near, host.lens_travel.far),
        };
        let intents = self.station.rail.show(ui, &inputs, &palette);
        for intent in intents {
            self.apply_rail(&s, intent);
        }
    }

    /// The inspector: the plan, or the capture's health while it runs.
    pub fn station_inspector(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let palette = self.station.palette;
        match self.station_mode() {
            StationMode::Plan => {
                let blockers = preflight::start_blockers(&s, self);
                let now = Instant::now();
                let (stage, levels, taken, error) = match &self.test_shot {
                    TestShot::Done { levels, taken, .. } => {
                        ("done", Some(levels.clone()), Some(*taken), None)
                    }
                    TestShot::Failed(e) => ("failed", None, None, Some(e.clone())),
                    other => (other.stage(), None, None, None),
                };
                let inputs = PlanInputs {
                    s: &s,
                    blockers: &blockers,
                    step: self.draft.step,
                    settle_ms: self.draft.settle_ms,
                    calibration: CalibrationView {
                        stage: self.calibration.stage(),
                        gives_up_in: self.calibration.gives_up_in(now),
                        result: self.calibration_result(),
                        finished: self.station.calibrated_at,
                    },
                    pass: super::plan::PassView {
                        proving: self.proof.running(),
                        ..self.pass.view(
                            Instant::now(),
                            self.light_on_for(Instant::now()),
                            s.host.capabilities.exposure_tiers,
                        )
                    },
                    test_shot: TestShotView {
                        stage,
                        levels,
                        exposure: self.test_shot_exposure,
                        taken,
                        error,
                    },
                    subject_depth: self.auto_subject.depth_range(),
                    stillness: (self.stillness.stage(), self.stillness.line(Instant::now())),
                    switches: Switches {
                        check: self.follow_enabled,
                        retake: s.host.error_correction,
                        stack_when_done: self.stack_when_done,
                        power_down: s.host.power.as_ref().map(|p| p.manage_stack),
                    },
                    engine: self.engine.is_some(),
                    subjects: &self.station.subjects,
                    subject_home: &self.station.subject_home,
                };
                let mut intents = self.station.plan.show(ui, &inputs, &palette);
                // The comparison panel ("What changes"), left of the inspector.
                if let Some(mut tab) = self.station.plan.guide {
                    let guide_inputs = super::guide::GuideInputs {
                        s: &s,
                        step: inputs.step,
                        settle_ms: inputs.settle_ms,
                        calibration: &inputs.calibration,
                        test_shot: &inputs.test_shot,
                        editable: s.fresh() && s.host.editable && !s.pending,
                    };
                    let (chosen, close) = super::guide::show_panel(
                        ui.ctx(),
                        ui.max_rect(),
                        &mut tab,
                        &guide_inputs,
                        &palette,
                    );
                    intents.extend(chosen);
                    self.station.plan.guide = (!close).then_some(tab);
                }
                // T takes a test shot; Enter starts a ready plan.
                if !ui.ctx().wants_keyboard_input()
                    && !self.station.glance
                    && !self.schedule_ui.editing()
                {
                    ui.input(|i| {
                        if i.key_pressed(egui::Key::T) {
                            intents.push(PlanIntent::TestShot);
                        }
                        if i.key_pressed(egui::Key::Enter) && blockers.is_empty() {
                            intents.push(PlanIntent::Start);
                        }
                    });
                }
                for intent in intents {
                    // The owner's own choices are held (rule 2): a
                    // calibration's values never replace them.
                    match &intent {
                        PlanIntent::SetStep(_) => self.held.step = true,
                        PlanIntent::UseAdvice { .. } | PlanIntent::SetHighlight(_) => {
                            self.held.exposure = true
                        }
                        _ => {}
                    }
                    self.apply_plan(&s, intent);
                }
            }
            StationMode::Flight => {
                let progress = self.station_progress();
                let inputs = self.flight_inputs(&s, progress.as_deref());
                let intents = flight::inspector(ui, &inputs, &palette);
                for intent in intents {
                    self.apply_flight(&s, intent);
                }
            }
        }
        self.station_windows(ui.ctx(), &s);
    }

    /// Glance mode over the whole window; Escape returns.
    pub fn station_glance(&mut self, ui: &mut Ui) {
        let s = self.station_snapshot();
        let palette = self.station.palette;
        let proof = self.proof_texture(ui.ctx()).map(|(id, size, _)| (id, size));
        let progress = self.station_progress();
        let received = self
            .station
            .proof
            .as_ref()
            .and_then(|p| p.latest.as_ref())
            .map(|u| u.received);
        let caption = [
            self.station.plan.subject.clone(),
            self.station.plan.stack_name.clone(),
            received
                .map(|n| format!("proof from planes 1–{n}"))
                .unwrap_or_default(),
        ]
        .into_iter()
        .filter(|t| !t.is_empty())
        .collect::<Vec<_>>()
        .join(" · ");
        let inputs = GlanceInputs {
            s: &s,
            progress: progress.as_deref(),
            proof,
            caption,
            left: self.station.left,
            next: Next {
                stack: self.follow_enabled && self.stack_when_done,
                power_down: s.host.power.as_ref().is_some_and(|p| p.manage_stack),
            },
        };
        if glance::show(ui, &inputs, &palette) {
            self.station.glance = false;
        }
    }

    /// Recovery and connection settings, opened from a pre-flight fix.
    fn station_windows(&mut self, ctx: &egui::Context, s: &Snapshot) {
        if self.station.recover_open {
            let mut open = true;
            egui::Window::new("Recover the camera")
                .open(&mut open)
                .collapsible(false)
                .resizable(false)
                .show(ctx, |ui| {
                    let failure = s.host.failure.clone();
                    ui.label(
                        failure
                            .as_ref()
                            .and_then(|f| f.message.clone())
                            .unwrap_or_else(|| "The camera needs recovery".into()),
                    );
                    let uncertain = failure.as_ref().is_some_and(|f| f.exposure_uncertain);
                    if uncertain {
                        ui.checkbox(
                            &mut self.acknowledge_uncertain,
                            "I checked the last exposure; recover without replaying it",
                        );
                    }
                    if ui
                        .add_enabled(
                            s.fresh() && !s.pending && (!uncertain || self.acknowledge_uncertain),
                            egui::Button::new("Recover camera"),
                        )
                        .clicked()
                    {
                        self.command(
                            s,
                            Command::Recover {
                                acknowledge_uncertain: self.acknowledge_uncertain,
                            },
                        );
                        self.acknowledge_uncertain = false;
                        self.station.recover_open = false;
                    }
                });
            self.station.recover_open &= open && s.host.failure.is_some();
        }
        if self.station.settings_open {
            let mut open = true;
            egui::Window::new("Captures, storage and connection")
                .open(&mut open)
                .collapsible(false)
                .default_width(360.0)
                .show(ctx, |ui| {
                    egui::ScrollArea::vertical()
                        .max_height(620.0)
                        .show(ui, |ui| {
                            self.connection_ui(ui, s);
                            ui.separator();
                            self.storage_ui(ui, s);
                            ui.separator();
                            self.completed_ui(ui, s, true);
                        });
                });
            self.station.settings_open &= open;
        }
        self.phone_ui(ctx);
        if self.schedule_ui.editing() {
            let blockers = preflight::start_blockers(s, self);
            let timing = self.schedule_timing(s);
            let palette = self.station.palette;
            if let Some(cmd) =
                self.schedule_ui
                    .show(ctx, s, preflight::can_schedule(&blockers), timing, &palette)
            {
                self.command(s, cmd);
            }
        }
    }

    fn apply_fix(&mut self, s: &Snapshot, fix: Fix) {
        match fix {
            Fix::ConnectionSettings => self.station.settings_open = true,
            Fix::ConnectCamera => self.connect_camera(s, Command::Connect {}),
            Fix::RecoverCamera => self.station.recover_open = true,
            Fix::MarkStart => self.command(s, Command::Mark { start: true }),
            Fix::MarkEnd => self.command(s, Command::Mark { start: false }),
            Fix::ApplyEdits => self.send_settings(s, self.draft.step, self.draft.settle_ms),
            Fix::StartReceiver => {
                let result = self.start_receiver();
                self.record(result);
            }
            Fix::StopWaiting => {
                if self.calibrating() {
                    self.stop_calibration();
                }
                if self.test_shot.running() {
                    self.stop_test_shot();
                }
            }
            Fix::NameSubject => self.station.plan.focus_subject = true,
        }
    }

    /// Sends the plan's step and settle as the host's `settings` command.
    fn send_settings(&mut self, s: &Snapshot, step: u16, settle_ms: u32) {
        self.send_plan(s, step, settle_ms, None, None);
    }

    /// The host's `settings` command with the plan's step and settle, and
    /// its approach and exposure timeout unless given.
    fn send_plan(
        &mut self,
        s: &Snapshot,
        step: u16,
        settle_ms: u32,
        approach: Option<u16>,
        capture_timeout_s: Option<u32>,
    ) {
        let Some(plan) = s.host.plan.clone() else {
            return;
        };
        let command = Command::Settings {
            step: step.max(1),
            settle_ms,
            approach: approach.unwrap_or(plan.approach),
            capture_timeout_s: capture_timeout_s.unwrap_or(plan.capture_timeout_s),
        };
        let revision = s.host.plan_revision.unwrap_or(0);
        let result = s.request(command).and_then(|mut r| {
            r.plan_revision = revision;
            self.submit(r)
        });
        if result.is_ok() {
            self.draft.step = step.max(1);
            self.draft.settle_ms = settle_ms;
            self.draft_dirty = false;
        }
        self.record(result);
    }

    pub(super) fn apply_plan(&mut self, s: &Snapshot, intent: PlanIntent) {
        match intent {
            PlanIntent::SetSubject(_) | PlanIntent::SetStackName(_) => {}
            PlanIntent::NewCapture => {
                self.held = Default::default();
                self.new_capture(false)
            }
            PlanIntent::UseAdvice { shutter, highlight } => {
                // The exposure now, its highlight plan once the camera has it.
                let iso = s.host.exposure.as_ref().and_then(|e| e.iso).unwrap_or(100);
                self.command(s, Command::Exposure { iso, shutter });
                if s.host.capabilities.exposure_tiers {
                    self.pending_highlight =
                        Some(highlight.map(|short| strehl_capture::model::Highlight {
                            shutter: short,
                            every: 2,
                            first_plane: 1,
                            last_plane: u32::MAX,
                            shots: s.host.shots() as u8,
                        }));
                }
            }
            PlanIntent::UseSubjectBounds(lo, hi) => {
                // Start, then End: each moved to and marked in turn.
                let (start, end) = s.host.plan_bounds();
                let (first, second) = if start <= end { (lo, hi) } else { (hi, lo) };
                self.station.mark_queue = vec![(false, second)];
                self.station.mark_at = Some(MarkAt {
                    start: true,
                    to: first,
                    since: Instant::now(),
                });
                if s.host.position != Some(first) {
                    self.focus_pending = Some(first);
                }
            }
            PlanIntent::SetHighlight(choice) => {
                let highlight = choice.map(|(every, shutter)| strehl_capture::model::Highlight {
                    shutter,
                    every,
                    first_plane: 1,
                    last_plane: u32::MAX,
                    shots: s.host.shots() as u8,
                });
                self.command(s, Command::Highlight { highlight });
            }
            PlanIntent::CheckStillness => match self.stillness.start(s) {
                Ok((ratio, x, y)) => self.command(s, Command::Magnify { ratio, x, y }),
                Err(e) => self.error = Some(format!("{e:#}")),
            },
            PlanIntent::StopStillness => {
                if let Some((ratio, x, y)) = self.stillness.stop() {
                    self.command(s, Command::Magnify { ratio, x, y });
                }
            }
            PlanIntent::OpenRig => self.station.rig_requested = true,
            PlanIntent::Connect => self.connect_camera(s, Command::Connect {}),
            PlanIntent::Exposure { iso, shutter } => {
                self.held.exposure = true;
                self.command(s, Command::Exposure { iso, shutter })
            }
            PlanIntent::TestShot => {
                if !self.test_shot.running() && !self.calibrating() {
                    let result = self.test_shot();
                    self.record(result);
                }
            }
            PlanIntent::StopTestShot => self.stop_test_shot(),
            PlanIntent::MarkStart => {
                self.held.bounds = true;
                self.command(s, Command::Mark { start: true })
            }
            PlanIntent::MarkEnd => {
                self.held.bounds = true;
                self.command(s, Command::Mark { start: false })
            }
            PlanIntent::Calibrate => {
                let result = self.calibrate_pass();
                self.record(result);
            }
            PlanIntent::StopCalibration => self.stop_calibration(),
            PlanIntent::SearchFurther(at) => {
                let result = self.calibrate_pass_at(Some(at));
                self.record(result);
            }
            PlanIntent::Prove(n) => {
                let result = self.prove(n);
                self.record(result);
            }
            PlanIntent::SetStep(step) => self.send_settings(s, step, self.draft.settle_ms),
            PlanIntent::SetSettle(ms) => self.send_settings(s, self.draft.step, ms),
            PlanIntent::SetApproach(approach) => self.send_plan(
                s,
                self.draft.step,
                self.draft.settle_ms,
                Some(approach),
                None,
            ),
            PlanIntent::SetCaptureTimeout(seconds) => self.send_plan(
                s,
                self.draft.step,
                self.draft.settle_ms,
                None,
                Some(seconds),
            ),
            PlanIntent::SetWarmup(seconds) => self.command(s, Command::SetWarmup { seconds }),
            PlanIntent::UseSurveyBounds => self.command(s, Command::ApplyBounds {}),
            PlanIntent::OpenGuide(tab) => self.station.plan.guide = Some(tab),
            PlanIntent::SetFourShot(four) => self.command(
                s,
                Command::PixelShift {
                    shots: if four { 4 } else { 1 },
                },
            ),
            PlanIntent::SetCheck(on) => self.set_follow(on),
            // The setting travels with the switch: a host given no
            // `max_retakes` goes back to two (h-retake).
            PlanIntent::SetRetake(on) => self.command(
                s,
                Command::ErrorCorrection {
                    enabled: on,
                    max_retakes: s
                        .host
                        .capabilities
                        .max_retakes
                        .then(|| s.host.max_retakes() as u8),
                },
            ),
            PlanIntent::SetMaxRetakes(max) => {
                if s.host.capabilities.max_retakes {
                    self.command(
                        s,
                        Command::ErrorCorrection {
                            enabled: s.host.error_correction == Some(true),
                            max_retakes: Some(max),
                        },
                    )
                }
            }
            PlanIntent::SetStackWhenDone(on) => self.stack_when_done = on,
            PlanIntent::SetPowerDown(on) => self.command(s, Command::PowerPlan { enabled: on }),
            PlanIntent::Start => {
                if preflight::start_blockers(s, self).is_empty() {
                    self.command(s, Command::Start {});
                }
            }
            PlanIntent::Schedule => self.schedule_ui.open(s),
            PlanIntent::OpenSettings => self.station.settings_open = true,
            PlanIntent::Fix(fix) => self.apply_fix(s, fix),
        }
    }

    pub(super) fn apply_rail(&mut self, s: &Snapshot, intent: RailIntent) {
        match intent {
            RailIntent::Jog(delta) => self.command(s, Command::Jog { delta }),
            RailIntent::Focus(target) => self.focus_pending = Some(target),
            RailIntent::MarkStart => self.command(s, Command::Mark { start: true }),
            RailIntent::MarkEnd => self.command(s, Command::Mark { start: false }),
            RailIntent::MoveBound { start, to } => {
                self.station.mark_at = Some(MarkAt {
                    start,
                    to,
                    since: Instant::now(),
                });
                if s.host.position != Some(to) {
                    self.focus_pending = Some(to);
                }
            }
            RailIntent::UseSurveyBounds => self.command(s, Command::ApplyBounds {}),
            RailIntent::SurveyAgain => self.command(s, Command::Survey {}),
        }
    }

    pub(super) fn apply_live(&mut self, s: &Snapshot, intent: LiveIntent) {
        match intent {
            LiveIntent::SetRoi(roi) => self.command(s, Command::Roi { roi }),
            // Plan S1/S3: the outline, or its box on an older host.
            LiveIntent::SetSubject(subject) if s.host.capabilities.subject => {
                self.command(s, Command::Subject { subject })
            }
            LiveIntent::SetSubject(subject) => {
                let roi = subject.map_or_else(strehl_capture::model::Roi::subject, |outline| {
                    outline.bounding_box()
                });
                self.command(s, Command::Roi { roi });
            }
            LiveIntent::ClearOutline => {
                // The automatic selection goes too, with its panel; a new
                // Auto finds it again from the kept survey frames.
                self.auto_subject = Default::default();
                self.station.fixture_auto = None;
                self.apply_live(s, LiveIntent::SetSubject(None));
            }
            LiveIntent::AutoSubject => {
                let active = super::auto_subject::active_px(s.host.camera_model.as_deref());
                if let Err(e) = self.auto_subject.start(&self.survey_frames, active) {
                    self.error = Some(format!("{e:#}"));
                }
            }
            LiveIntent::AutoParams {
                sensitivity,
                grow,
                buffer_px,
            } => self.auto_subject.reselect(strehl_core::subject::Params {
                sensitivity,
                grow,
                buffer_px,
            }),
            LiveIntent::Magnify { ratio, x, y } => {
                self.command(s, Command::Magnify { ratio, x, y })
            }
        }
    }

    pub(super) fn apply_flight(&mut self, s: &Snapshot, intent: FlightIntent) {
        match intent {
            FlightIntent::Pause => self.command(s, Command::Pause {}),
            FlightIntent::Resume => self.command(s, Command::Resume {}),
            FlightIntent::AskStop => self.confirm = Some(Confirm::Stop),
            FlightIntent::Stop => {
                self.confirm = None;
                self.command(s, Command::Stop {});
            }
            FlightIntent::KeepGoing => self.confirm = None,
            FlightIntent::Glance => self.station.glance = true,
            FlightIntent::SetStackWhenDone(on) => self.stack_when_done = on,
            FlightIntent::SetPowerDown(on) => self.command(s, Command::PowerPlan { enabled: on }),
            // "Show" in the feed: that try in the plane view.
            FlightIntent::ShowPlane { plane, raw } => self.station.plane_view.show(plane, raw),
            FlightIntent::QueueRetakes(planes) => self.queue_retakes(s, planes),
            FlightIntent::Done => {
                self.station.review = false;
                self.station.plane_view.follow();
            }
            FlightIntent::NewCapture => self.new_capture(false),
            FlightIntent::HighlightPass => self.highlight_pass(s),
            FlightIntent::StackStopped => {
                // As a finished capture is: opened and stacked, or queued
                // behind a stack being rendered (`capture_finished`).
                if let Some(run) = self.stopped_under_review(s) {
                    self.finished_capture = Some(run.folder.clone());
                    self.follow_note = Some(format!(
                        "Stacking the {} planes taken before the stop.",
                        run.planes
                    ));
                }
            }
        }
    }

    /// Asks the camera host to take `planes` again (h-retake): between the
    /// planes while the capture runs, into its run once it has ended.
    fn queue_retakes(&mut self, s: &Snapshot, planes: Vec<u64>) {
        if planes.is_empty() {
            return;
        }
        if !s.host.takes_manual_retakes() {
            self.error =
                Some("This camera host cannot take retakes by hand; update the Pi's Strehl".into());
            return;
        }
        let progress = self.station_progress();
        let now = Instant::now();
        for &plane in &planes {
            let tries = progress
                .as_ref()
                .and_then(|p| {
                    p.feed
                        .iter()
                        .rev()
                        .find(|i| i.plane == plane)
                        .map(|i| i.attempt)
                })
                .unwrap_or(0);
            self.station.asked.retain(|a| a.plane != plane);
            self.station.asked.push(AskedRetake {
                plane,
                tries,
                at: now,
                sequence: s.host.sequence_id,
            });
        }
        // Old requests of other captures go.
        let sequence = s.host.sequence_id;
        self.station.asked.retain(|a| a.sequence == sequence);
        self.command(s, Command::QueueRetakes { planes });
    }

    /// Stage 1: the station inside today's Capture tab, laid out as the
    /// mockup's frame (control strip, canvas, rail, 348 px inspector), for
    /// checking the screens before the shell composes them.
    pub fn show_station(&mut self, ctx: &egui::Context) {
        self.activate(ctx);
        self.shown = true;
        let s = self.station_snapshot();
        self.observe_focus(&s);
        if let Some(plan) = s.host.plan.clone() {
            self.sync_plan(plan, s.host.plan_revision.unwrap_or(0));
        }
        self.painted_ready = (!s.receiver.is_null() || s.receiver_error.is_some())
            && ((s.observed.is_some() && (s.preview.is_some() || !s.host.preview.available))
                || s.connection_error.is_some()
                || self.config.controller.is_empty());
        egui::CentralPanel::default()
            .frame(egui::Frame::NONE)
            .show(ctx, |ui| {
                let full = ui.max_rect();
                if self.station.glance {
                    self.station_glance(ui);
                    return;
                }
                let insp =
                    Rect::from_min_max(egui::pos2(full.right() - 348.0, full.top()), full.max);
                let main = Rect::from_min_max(full.min, egui::pos2(insp.left(), full.bottom()));
                let flight_mode = self.station_mode() == StationMode::Flight;
                let strip_h = if flight_mode { 0.0 } else { 36.0 };
                let rail_h = if flight_mode { 127.0 } else { 135.0 };
                let strip = Rect::from_min_size(main.min, egui::vec2(main.width(), strip_h));
                let rail =
                    Rect::from_min_max(egui::pos2(main.left(), main.bottom() - rail_h), main.max);
                let canvas = Rect::from_min_max(
                    egui::pos2(main.left(), strip.bottom()),
                    egui::pos2(main.right(), rail.top()),
                );
                if !flight_mode {
                    ui.scope_builder(egui::UiBuilder::new().max_rect(strip), |ui| {
                        self.station_strip(ui)
                    });
                }
                ui.scope_builder(egui::UiBuilder::new().max_rect(canvas), |ui| {
                    self.station_canvas(ui)
                });
                ui.scope_builder(egui::UiBuilder::new().max_rect(rail), |ui| {
                    self.station_rail(ui)
                });
                ui.scope_builder(egui::UiBuilder::new().max_rect(insp), |ui| {
                    self.station_inspector(ui)
                });
            });
        self.flush_focus(&s);
    }
}

/// Records when a calibration finished, for the plan's "Calibrated 21:33".
pub(super) fn note_calibration(station: &mut Station, before: &str, after: &Calibration) {
    if before != "done" && matches!(after, Calibration::Done(_)) {
        station.calibrated_at = Some(SystemTime::now());
    }
}

#[cfg(test)]
#[path = "capture-station-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "capture-retake-station-tests.rs"]
mod retake_station_tests;
