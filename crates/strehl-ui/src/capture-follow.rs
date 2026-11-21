//! Stacking during capture.
//!
//! While a capture is being written to this PC, the engine's `follow` checks
//! each focal plane as soon as every one of its RAWs has a durable receipt:
//! it decodes the plane, checks a four-shot group exactly as the stack will,
//! and measures the plane's alignment pairs. Those measurements go to the
//! shared engine cache (the group and alignment-edge journals), so the stack
//! that closes the capture reads them instead of measuring again, and its
//! photograph is the one an offline stack of the same folder makes.
//!
//! The checker runs in its own process at below-normal priority, so the
//! receiver, the camera link and this window keep the machine first. Its
//! per-plane journal (also in the cache) is the progress shown here, and lets
//! a restarted checker resume.
use anyhow::{Context, Result};
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet, HashSet},
    fs,
    io::{Read, Seek, SeekFrom, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::{
        Arc, Mutex,
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    time::{Duration, Instant},
};

/// A run whose records have not changed for this long, with the camera not
/// capturing, is no longer followed.
pub(crate) const ABANDONED: Duration = Duration::from_secs(600);
/// With error correction the camera host holds focus until a group's check
/// arrives, so the journal is read often and the checker polls quickly.
const POLL: Duration = Duration::from_millis(200);
const FOLLOW_INTERVAL_MS: &str = "250";

/// The most planes whose journal lines [`Progress::planes`] keeps: above a
/// 6,000-plane stack. Beyond it the lowest planes are dropped first; the
/// counts still cover every plane.
pub(crate) const MAX_PLANE_RECORDS: usize = 8192;
/// The most journal bytes one poll reads. A plane's line is under 2 KiB,
/// so a restarted desktop catches up with a long run in a few seconds while
/// no frame waits on a large read.
const JOURNAL_STEP: u64 = 64 * 1024;

/// What the checker has recorded for a run so far.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct Progress {
    /// Focal planes checked (decoded, and for four-shot groups measured).
    pub checked: usize,
    /// Four-shot groups the stack will assemble.
    pub passed: usize,
    /// Planes the stack will not assemble as recorded: a group it demotes, a
    /// plane that failed to decode, or (once the capture ended) one whose
    /// RAWs never all arrived.
    pub attention: usize,
    /// Focus positions of the planes worth taking again, ascending.
    pub retake: Vec<u64>,
    /// Alignment pairs measured while capturing.
    pub align_pairs: u64,
    /// Planes taken again during the capture (error correction).
    pub retaken: usize,
    /// The planes taken again (more than one group recorded).
    pub retaken_planes: BTreeSet<u64>,
    /// Each plane's last journal line, by plane: its `verdict`, `reason`,
    /// `retake`, `target`, `group_id`, member `names`, `seconds` and
    /// `align_seconds` as the engine wrote them. The newest
    /// [`MAX_PLANE_RECORDS`] planes.
    pub planes: BTreeMap<u64, Value>,
}

/// For the in-flight screen's last planes and rail (Studio 2, 7.4).
#[allow(dead_code)]
impl Progress {
    /// The journal line of `plane`, if kept.
    pub fn plane(&self, plane: u64) -> Option<&Value> {
        self.planes.get(&plane)
    }
    /// The newest `n` planes (highest plane numbers), newest first.
    pub fn latest(&self, n: usize) -> impl Iterator<Item = (&u64, &Value)> {
        self.planes.iter().rev().take(n)
    }
}

/// What one plane's last line adds to the counts.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct Counted {
    checked: bool,
    passed: bool,
    attention: bool,
    /// The plane's focus position, when it is worth taking again.
    retake: Option<u64>,
    align_pairs: u64,
}

impl Counted {
    fn of(v: &Value) -> Self {
        let verdict = v["verdict"].as_str().unwrap_or("");
        Self {
            checked: verdict != "incomplete",
            passed: verdict == "pass",
            attention: verdict != "pass" && verdict != "decoded",
            retake: v["target"].as_u64().filter(|_| v["retake"] == true),
            align_pairs: v["align_pairs"].as_u64().unwrap_or(0),
        }
    }
}

/// Reads the checker's journal as it grows: one JSON line per checked
/// group, a later line for a plane (its retake) replacing an earlier one, as
/// the stack uses the plane's last group. Only complete lines are taken; a
/// line still being written is kept and read again with its end. The
/// [`Progress`] is kept up to date line by line: reading a new line costs
/// the same at plane 10 as at plane 6,000.
#[derive(Default)]
pub(crate) struct JournalReader {
    /// Bytes of the journal consumed.
    offset: u64,
    /// The start of a line whose end has not been written yet.
    partial: Vec<u8>,
    progress: Progress,
    /// Every plane's contribution to the counts (small; never dropped).
    counted: BTreeMap<u64, Counted>,
    /// The groups recorded per plane: more than one means it was retaken.
    groups: BTreeMap<u64, BTreeSet<String>>,
}

impl JournalReader {
    /// Takes the next bytes of the journal; returns the complete lines read,
    /// parsed (the caller relays their verdicts).
    pub fn feed(&mut self, bytes: &[u8]) -> Vec<Value> {
        self.offset += bytes.len() as u64;
        self.partial.extend_from_slice(bytes);
        let Some(end) = self.partial.iter().rposition(|b| *b == b'\n') else {
            return Vec::new();
        };
        let rest = self.partial.split_off(end + 1);
        let complete = std::mem::replace(&mut self.partial, rest);
        let lines: Vec<Value> = complete
            .split(|b| *b == b'\n')
            .filter_map(|line| serde_json::from_slice::<Value>(line).ok())
            .collect();
        self.take(&lines);
        lines
    }
    /// The last line, once the journal is known to be finished, even without
    /// its newline.
    pub fn flush(&mut self) -> Vec<Value> {
        let line = std::mem::take(&mut self.partial);
        let lines: Vec<Value> = serde_json::from_slice::<Value>(&line)
            .ok()
            .into_iter()
            .collect();
        self.take(&lines);
        lines
    }
    fn take(&mut self, lines: &[Value]) {
        let p = &mut self.progress;
        let mut retakes_changed = false;
        for v in lines {
            let Some(plane) = v["plane"].as_u64() else {
                continue;
            };
            if let Some(group) = v["group_id"].as_str() {
                let groups = self.groups.entry(plane).or_default();
                if groups.insert(group.to_owned()) && groups.len() == 2 {
                    p.retaken += 1;
                    p.retaken_planes.insert(plane);
                }
            }
            let new = Counted::of(v);
            let old = self.counted.insert(plane, new).unwrap_or_default();
            p.checked = p.checked + usize::from(new.checked) - usize::from(old.checked);
            p.passed = p.passed + usize::from(new.passed) - usize::from(old.passed);
            p.attention = p.attention + usize::from(new.attention) - usize::from(old.attention);
            p.align_pairs = p.align_pairs + new.align_pairs - old.align_pairs;
            retakes_changed |= new.retake != old.retake;
            p.planes.insert(plane, v.clone());
            if p.planes.len() > MAX_PLANE_RECORDS {
                p.planes.pop_first();
            }
        }
        if retakes_changed {
            p.retake = self.counted.values().filter_map(|c| c.retake).collect();
            p.retake.sort_unstable();
        }
    }
    pub fn offset(&self) -> u64 {
        self.offset
    }
    /// The counts over every plane read, and the newest planes' lines.
    pub fn progress(&self) -> &Progress {
        &self.progress
    }
}

/// Reads a whole journal (see [`JournalReader`]).
#[cfg(test)]
pub(crate) fn progress(journal: &str) -> Progress {
    let mut reader = JournalReader::default();
    reader.feed(journal.as_bytes());
    reader.flush();
    reader.progress
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum State {
    Running,
    /// Every recorded plane is checked and the capture has ended.
    Finished,
    Failed(String),
    Stopped(String),
}

pub(crate) struct Follower {
    pub run: PathBuf,
    pub log: PathBuf,
    child: Option<crate::jobs::OwnedChild>,
    /// Another process (another Strehl window, or `strehl follow`) holds the
    /// run's lock: this one only shows its progress.
    pub observing: bool,
    pub state: State,
    /// The journal reader thread's output (spec 5.2: the UI thread reads no
    /// file while a capture is followed).
    shared: Arc<ReaderShared>,
    progress: Arc<Progress>,
    revision: u64,
    /// The checker's exit, once seen; the state follows when the reader has
    /// read the journal to its end.
    exit: Option<std::process::ExitStatus>,
    polled: Option<Instant>,
    pub started: Instant,
    /// Set once the finished capture was offered to Projects.
    pub offered: bool,
    /// Error correction: each checked group's verdict goes to this PC's
    /// receiver, where the camera host reads it.
    relaying: bool,
}

/// What the journal reader thread publishes.
#[derive(Default)]
struct Published {
    progress: Arc<Progress>,
    revision: u64,
    /// The checker exited and its journal was read to the end.
    drained: bool,
    /// The engine's own error line, read from its log after it exited.
    error: Option<String>,
    /// Observing: the other checker's lock was released.
    released: bool,
}

#[derive(Default)]
struct ReaderShared {
    out: Mutex<Published>,
    /// Set by the UI when the checker exited: read to the end, then stop.
    exited: AtomicBool,
    /// Set when the follower is stopped or dropped.
    stop: AtomicBool,
}

/// The paths the reader thread needs.
struct ReaderPaths {
    journal: PathBuf,
    lock: PathBuf,
    log: PathBuf,
    observing: bool,
}

/// Hands the new groups' verdicts to the relay (error correction).
fn send_verdicts(
    relay: &Option<mpsc::Sender<Vec<Value>>>,
    relayed: &mut HashSet<String>,
    lines: Vec<Value>,
) {
    let Some(relay) = relay else { return };
    let fresh: Vec<Value> = lines
        .into_iter()
        .filter_map(verdict)
        .filter(|v| relayed.insert(v["group_id"].as_str().unwrap_or_default().to_owned()))
        .collect();
    if !fresh.is_empty() {
        let _ = relay.send(fresh);
    }
}

/// Reads the journal as it grows, relays verdicts and watches the lock, on
/// its own thread. Publishes a new progress whenever lines arrive.
fn reader_thread(
    paths: ReaderPaths,
    shared: Arc<ReaderShared>,
    relay: Option<mpsc::Sender<Vec<Value>>>,
) {
    let mut reader = JournalReader::default();
    let mut relayed = HashSet::new();
    let mut revision = 0u64;
    loop {
        if shared.stop.load(Ordering::SeqCst) {
            return;
        }
        let exited = shared.exited.load(Ordering::SeqCst);
        let before = reader.offset();
        loop {
            let (lines, more) = read_chunk(&paths.journal, &mut reader);
            send_verdicts(&relay, &mut relayed, lines);
            if !more {
                break;
            }
        }
        let mut changed = reader.offset() != before;
        if exited {
            let last = reader.flush();
            send_verdicts(&relay, &mut relayed, last);
            revision += 1;
            let mut out = shared.out.lock().unwrap();
            out.progress = Arc::new(reader.progress().clone());
            out.revision = revision;
            out.error = last_error(&paths.log);
            out.drained = true;
            return;
        }
        let released = paths.observing && !locked_elsewhere(&paths.lock);
        if released {
            changed = true;
        }
        if changed {
            revision += 1;
            let mut out = shared.out.lock().unwrap();
            out.progress = Arc::new(reader.progress().clone());
            out.revision = revision;
            out.released = released;
        }
        if released {
            return;
        }
        std::thread::sleep(POLL);
    }
}

/// Reads up to [`JOURNAL_STEP`] new bytes of `journal` into `reader`;
/// returns the complete lines read and whether more remain. A journal
/// shorter than what was read (rewritten) is read again from its start.
fn read_chunk(journal: &Path, reader: &mut JournalReader) -> (Vec<Value>, bool) {
    let Some(len) = fs::metadata(journal).map(|m| m.len()).ok() else {
        return (Vec::new(), false);
    };
    if len < reader.offset() {
        *reader = JournalReader::default();
    }
    if len == reader.offset() {
        return (Vec::new(), false);
    }
    let Ok(mut file) = fs::File::open(journal) else {
        return (Vec::new(), false);
    };
    let mut chunk = Vec::new();
    if file.seek(SeekFrom::Start(reader.offset())).is_err()
        || file
            .take(JOURNAL_STEP.min(len - reader.offset()))
            .read_to_end(&mut chunk)
            .is_err()
        || chunk.is_empty()
    {
        return (Vec::new(), false);
    }
    let lines = reader.feed(&chunk);
    (lines, reader.offset() < len)
}

/// The journal lines the camera host needs, keyed by group: the checker's
/// verdict on each checked group.
#[cfg(test)]
pub(crate) fn verdicts(journal: &str) -> Vec<Value> {
    journal
        .lines()
        .filter_map(|line| serde_json::from_str::<Value>(line).ok())
        .filter_map(verdict)
        .collect()
}

/// One journal line's verdict for the camera host, if it checked a group.
fn verdict(v: Value) -> Option<Value> {
    (v["group_id"].is_string() && v["verdict"].is_string()).then(|| {
        json!({"group_id":v["group_id"],"plane":v["plane"],"verdict":v["verdict"],
            "retake":v["retake"] == true,"reason":v["reason"]})
    })
}

/// Posts verdicts in order, retrying briefly: the camera host waits for them.
fn relay_thread(config: crate::capture_client::Config, run: String) -> mpsc::Sender<Vec<Value>> {
    let (sender, receiver) = mpsc::channel::<Vec<Value>>();
    let _ = std::thread::Builder::new()
        .name("strehl-verdict-relay".into())
        .spawn(move || {
            for batch in receiver {
                for attempt in 0..10 {
                    match crate::capture_client::post_verdicts(&config, &run, &batch) {
                        Ok(()) => break,
                        Err(_) if attempt < 9 => std::thread::sleep(Duration::from_millis(200)),
                        Err(_) => {}
                    }
                }
            }
        });
    sender
}

/// The engine invocation: `follow <run>` with the desktop's shared cache and
/// none of the inherited `STREHL_*` overrides, as renders are configured, so
/// the measurements are keyed exactly as the closing render looks them up.
pub(crate) fn command(engine: &Path, run: &Path, cache: &Path) -> Result<Command> {
    let mut command = crate::engine::command(engine)?;
    command
        .args(["follow", "--interval-ms", FOLLOW_INTERVAL_MS])
        .arg(run);
    crate::jobs::remove_experimental_overrides(&mut command, std::env::vars_os());
    command.env("STREHL_CACHE_DIR", cache);
    command.env_remove("RAYON_NUM_THREADS");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS
        command.creation_flags(0x0800_0000 | 0x0000_4000);
    }
    Ok(command)
}

impl Follower {
    /// `relay`: the capture settings naming this PC's receiver, to hand each
    /// verdict to the camera host (error correction).
    pub fn start(
        engine: &Path,
        run: &Path,
        relay: Option<crate::capture_client::Config>,
    ) -> Result<Self> {
        let cache = strehl_cli::default_cache_root();
        fs::create_dir_all(&cache).context("Creating the engine cache")?;
        let journal = strehl_cli::follow_journal_path(&cache, run)
            .context("Locating the capture checker's journal")?;
        let lock = strehl_cli::follow_lock_path(&journal);
        let log = journal.with_extension("log");
        let observing = locked_elsewhere(&lock);
        let mut follower = Self {
            run: run.to_owned(),
            log: log.clone(),
            child: None,
            observing,
            state: State::Running,
            shared: Arc::new(ReaderShared::default()),
            progress: Arc::new(Progress::default()),
            revision: 0,
            exit: None,
            polled: None,
            started: Instant::now(),
            // The other checker's own window opens the finished capture.
            offered: observing,
            relaying: false,
        };
        let mut relay_sender = None;
        if !observing {
            let mut command = command(engine, run, &cache)?;
            let mut out = fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&log)
                .with_context(|| format!("Opening {}", log.display()))?;
            writeln!(
                out,
                "\nStrehl desktop: following {}\nProgram: {:?}\nArguments: {:?}\nInherited STREHL_* overrides removed; STREHL_CACHE_DIR set to the shared engine cache {}.",
                run.display(),
                command.get_program(),
                command.get_args().collect::<Vec<_>>(),
                cache.display()
            )?;
            command
                .stdin(Stdio::null())
                .stdout(out.try_clone()?)
                .stderr(out);
            let child = command
                .spawn()
                .context("Starting the engine's capture checker")?;
            follower.child = Some(crate::jobs::OwnedChild(child));
            relay_sender = relay
                .zip(run.file_name().and_then(|n| n.to_str()))
                .map(|(config, name)| relay_thread(config, name.to_owned()));
            follower.relaying = relay_sender.is_some();
        }
        let paths = ReaderPaths {
            journal,
            lock,
            log,
            observing,
        };
        let shared = follower.shared.clone();
        std::thread::Builder::new()
            .name("strehl-follow-journal".into())
            .spawn(move || reader_thread(paths, shared, relay_sender))
            .context("Starting the journal reader")?;
        Ok(follower)
    }

    pub fn running(&self) -> bool {
        self.state == State::Running
    }

    /// What the checker has recorded so far, with each plane's journal line.
    pub fn progress(&self) -> &Progress {
        &self.progress
    }

    /// The same, shared: a clone costs one reference count, not the planes.
    pub fn progress_arc(&self) -> Arc<Progress> {
        self.progress.clone()
    }

    /// Takes the reader thread's newest progress and notices the checker's
    /// exit. Reads no file: a lock and a process status only, at most five
    /// times a second.
    pub fn poll(&mut self) {
        if self.polled.is_some_and(|t| t.elapsed() < POLL) {
            return;
        }
        self.polled = Some(Instant::now());
        let (drained, released, error) = {
            let out = self.shared.out.lock().unwrap();
            if out.revision != self.revision {
                self.progress = out.progress.clone();
                self.revision = out.revision;
            }
            (out.drained, out.released, out.error.clone())
        };
        if self.observing {
            if self.running() && released {
                self.state = State::Stopped("Checked by another Strehl window or process".into());
            }
            return;
        }
        if self.exit.is_none() {
            match self
                .child
                .as_mut()
                .map(|child| child.0.try_wait())
                .transpose()
            {
                Ok(Some(Some(status))) => {
                    self.child = None;
                    self.exit = Some(status);
                    self.shared.exited.store(true, Ordering::SeqCst);
                }
                Ok(_) => {}
                Err(e) => {
                    self.child = None;
                    self.shared.stop.store(true, Ordering::SeqCst);
                    self.state = State::Failed(format!("Checking the capture checker: {e}"));
                }
            }
        }
        if let Some(status) = self.exit
            && drained
            && self.running()
        {
            self.state = if status.success() {
                State::Finished
            } else {
                State::Failed(
                    error.unwrap_or_else(|| format!("The capture checker stopped ({status})")),
                )
            };
        }
    }

    /// Ends the checker; its journal keeps every plane checked so far.
    pub fn stop(&mut self, reason: &str) {
        // Dropping the owned child ends it and waits.
        self.child = None;
        self.shared.stop.store(true, Ordering::SeqCst);
        if self.running() {
            self.state = State::Stopped(reason.into());
        }
    }

    pub fn public(&self) -> Value {
        let (state, message) = match &self.state {
            State::Running => ("running", None),
            State::Finished => ("finished", None),
            State::Failed(m) => ("failed", Some(m)),
            State::Stopped(m) => ("stopped", Some(m)),
        };
        json!({"run":self.run,"state":state,"message":message,"log":self.log,"observing":self.observing,
            "seconds":self.started.elapsed().as_secs_f64(),
            "checked":self.progress().checked,"passed":self.progress().passed,
            "attention":self.progress().attention,"retake_positions":self.progress().retake,
            "align_pairs":self.progress().align_pairs,"retaken":self.progress().retaken,
            "planes_kept":self.progress().planes.len(),
            "relaying_verdicts":self.relaying})
    }
}

impl Drop for Follower {
    fn drop(&mut self) {
        self.shared.stop.store(true, Ordering::SeqCst);
    }
}

/// Whether a running checker holds the run's lock. A lock that cannot be
/// opened at all is treated as free: starting the checker reports why.
fn locked_elsewhere(lock: &Path) -> bool {
    let Ok(file) = fs::OpenOptions::new()
        .create(true)
        .truncate(false)
        .write(true)
        .open(lock)
    else {
        return false;
    };
    // Released when `file` drops at the end of this call.
    matches!(file.try_lock(), Err(fs::TryLockError::WouldBlock))
}

/// The engine's own error line from the end of the log, if it wrote one.
fn last_error(log: &Path) -> Option<String> {
    let text = fs::read_to_string(log).ok()?;
    let tail: Vec<&str> = text.lines().rev().take(40).collect();
    tail.iter()
        .find_map(|l| l.strip_prefix("Error: "))
        .or_else(|| tail.iter().copied().find(|l| !l.trim().is_empty()))
        .map(|l| l.chars().take(400).collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn progress_counts_planes_as_the_engine_resumes_them() {
        let journal = [
            r#"{"plane":1,"target":100,"verdict":"pass","retake":false,"align_pairs":0}"#,
            r#"{"plane":2,"target":110,"verdict":"demote","reason":"x","retake":true,"align_pairs":1}"#,
            "torn line {",
            r#"{"plane":3,"target":120,"verdict":"failed","retake":true}"#,
            r#"{"plane":3,"target":120,"verdict":"pass","retake":false,"align_pairs":2}"#,
            r#"{"plane":4,"target":90,"verdict":"incomplete","retake":true}"#,
            r#"{"plane":5,"target":130,"verdict":"decoded","retake":false,"align_pairs":3}"#,
        ]
        .join("\n");
        let p = progress(&journal);
        assert_eq!(
            Progress {
                planes: BTreeMap::new(),
                ..p.clone()
            },
            Progress {
                checked: 4,
                passed: 2,
                attention: 2,
                retake: vec![90, 110],
                align_pairs: 6,
                retaken: 0,
                retaken_planes: BTreeSet::new(),
                planes: BTreeMap::new(),
            }
        );
        assert_eq!(progress(""), Progress::default());
        // Each plane keeps its last line, as the stack uses its last group.
        assert_eq!(p.planes.len(), 5);
        assert_eq!(p.plane(3).unwrap()["verdict"], "pass");
        assert_eq!(p.plane(2).unwrap()["reason"], "x");
        let newest: Vec<u64> = p.latest(2).map(|(k, _)| *k).collect();
        assert_eq!(newest, [5, 4]);
    }

    /// Lines arriving in pieces give the same progress as the whole journal;
    /// a torn line waits for its end, and the last line counts once the
    /// journal is finished.
    #[test]
    fn the_journal_reads_incrementally_as_it_is_written() {
        let lines = [
            r#"{"plane":1,"target":100,"group_id":"g1","verdict":"pass","retake":false,"seconds":1.5}"#,
            r#"{"plane":2,"target":110,"group_id":"g2","verdict":"demote","reason":"x","retake":true}"#,
            r#"{"plane":2,"target":110,"group_id":"g2b","verdict":"pass","retake":false}"#,
            r#"{"plane":3,"target":120,"group_id":"g3","verdict":"pass","retake":false}"#,
        ];
        let whole = lines.join("\n");
        let mut reader = JournalReader::default();
        let mut seen = Vec::new();
        for piece in whole.as_bytes().chunks(17) {
            seen.extend(reader.feed(piece));
        }
        assert_eq!(seen.len(), 3, "the last line has no newline yet");
        assert_eq!(reader.progress().checked, 2);
        seen.extend(reader.flush());
        assert_eq!(seen.len(), 4);
        assert_eq!(*reader.progress(), progress(&whole));
        assert_eq!(reader.offset(), whole.len() as u64);
        let p = reader.progress();
        assert_eq!((p.retaken, p.passed), (1, 3));
        assert_eq!(p.retaken_planes.iter().copied().collect::<Vec<_>>(), [2]);
        assert_eq!(p.plane(1).unwrap()["seconds"], 1.5);
        assert_eq!(p.plane(2).unwrap()["group_id"], "g2b");
        // The relayed verdicts are the same whichever way it was read.
        let relayed: Vec<Value> = seen.into_iter().filter_map(verdict).collect();
        assert_eq!(relayed, verdicts(&whole));
    }

    /// The per-plane records are bounded; the counts still cover every plane.
    #[test]
    fn plane_records_are_bounded_and_keep_the_newest() {
        let mut journal = String::new();
        for plane in 1..=(MAX_PLANE_RECORDS as u64 + 10) {
            journal.push_str(&format!(
                "{{\"plane\":{plane},\"target\":{plane},\"verdict\":\"decoded\",\"retake\":false}}\n"
            ));
        }
        let p = progress(&journal);
        assert_eq!(p.checked, MAX_PLANE_RECORDS + 10);
        assert_eq!(p.planes.len(), MAX_PLANE_RECORDS);
        assert!(p.plane(10).is_none() && p.plane(11).is_some());
        assert_eq!(
            *p.planes.keys().next_back().unwrap(),
            MAX_PLANE_RECORDS as u64 + 10
        );
    }

    #[test]
    fn a_retake_replaces_its_plane_and_every_group_is_relayed() {
        let journal = [
            r#"{"plane":1,"target":100,"group_id":"g1","verdict":"pass","retake":false}"#,
            r#"{"plane":2,"target":110,"group_id":"g2","verdict":"demote","reason":"witness tiles disagree locally","retake":true}"#,
            r#"{"plane":2,"target":110,"group_id":"g2b","verdict":"pass","retake":false}"#,
            r#"{"plane":3,"target":120,"verdict":"pass"}"#,
        ]
        .join("\n");
        let p = progress(&journal);
        assert_eq!((p.checked, p.passed, p.attention, p.retaken), (3, 3, 0, 1));
        assert!(p.retake.is_empty(), "the retake passed");
        let v = verdicts(&journal);
        let groups: Vec<_> = v.iter().map(|v| v["group_id"].as_str().unwrap()).collect();
        assert_eq!(
            groups,
            ["g1", "g2", "g2b"],
            "lines without a group are not relayed"
        );
        assert_eq!(v[1]["retake"], true);
        assert_eq!(v[1]["reason"], "witness tiles disagree locally");
    }

    #[test]
    fn checker_runs_follow_with_the_shared_cache_and_no_overrides() {
        let engine = std::env::current_exe().unwrap();
        let cache = Path::new("cache-root");
        // An inherited override is removed whatever its value.
        // SAFETY: test-local variable name, read only by this test.
        unsafe { std::env::set_var("STREHL_FOLLOW_TEST_OVERRIDE", "1") };
        let command = command(&engine, Path::new("run-folder"), cache).unwrap();
        unsafe { std::env::remove_var("STREHL_FOLLOW_TEST_OVERRIDE") };
        let args: Vec<_> = command.get_args().collect();
        assert_eq!(
            &args[args.len() - 4..],
            ["follow", "--interval-ms", FOLLOW_INTERVAL_MS, "run-folder"]
        );
        let envs: BTreeMap<_, _> = command.get_envs().collect();
        assert_eq!(
            envs.get(std::ffi::OsStr::new("STREHL_CACHE_DIR")),
            Some(&Some(cache.as_os_str()))
        );
        assert_eq!(
            envs.get(std::ffi::OsStr::new("STREHL_FOLLOW_TEST_OVERRIDE")),
            Some(&None)
        );
        assert_eq!(
            envs.get(std::ffi::OsStr::new("RAYON_NUM_THREADS")),
            Some(&None)
        );
    }

    /// The journal is read on its own thread: lines appear in the published
    /// progress as they are written, and after the checker's exit the last
    /// line (without its newline) and the engine's error line are read.
    #[test]
    fn the_journal_is_read_off_the_ui_thread() {
        let dir = tempfile::tempdir().unwrap();
        let journal = dir.path().join("run.jsonl");
        let log = dir.path().join("run.log");
        fs::write(&log, "plane 1 : pass\nError: the disk filled\n").unwrap();
        fs::write(&journal, "{\"plane\":1,\"verdict\":\"pass\"}\n").unwrap();
        let shared = Arc::new(ReaderShared::default());
        let paths = ReaderPaths {
            journal: journal.clone(),
            lock: dir.path().join("run.lock"),
            log,
            observing: false,
        };
        let thread_shared = shared.clone();
        let handle = std::thread::spawn(move || reader_thread(paths, thread_shared, None));
        let wait = |want: usize| {
            let end = Instant::now() + Duration::from_secs(10);
            loop {
                let checked = shared.out.lock().unwrap().progress.checked;
                if checked >= want {
                    return checked;
                }
                assert!(Instant::now() < end, "only {checked} planes read");
                std::thread::sleep(Duration::from_millis(20));
            }
        };
        assert_eq!(wait(1), 1);
        let mut f = fs::OpenOptions::new().append(true).open(&journal).unwrap();
        f.write_all(b"{\"plane\":2,\"verdict\":\"pass\"}\n{\"plane\":3,\"verdict\"")
            .unwrap();
        assert_eq!(wait(2), 2, "the torn line waits");
        f.write_all(b":\"decoded\"}").unwrap();
        shared.exited.store(true, Ordering::SeqCst);
        handle.join().unwrap();
        let out = shared.out.lock().unwrap();
        assert!(out.drained);
        assert_eq!(
            out.progress.checked, 3,
            "the last line counts once finished"
        );
        assert_eq!(out.error.as_deref(), Some("the disk filled"));
    }

    #[test]
    fn a_held_run_lock_is_seen_and_a_released_one_is_not() {
        let dir = std::env::temp_dir().join(format!("strehl-follow-lock-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let lock = dir.join("run.lock");
        assert!(!locked_elsewhere(&lock), "a missing lock file is free");
        let held = fs::OpenOptions::new().write(true).open(&lock).unwrap();
        held.try_lock().unwrap();
        assert!(locked_elsewhere(&lock));
        drop(held);
        assert!(!locked_elsewhere(&lock), "the lock ends with its holder");
        fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn last_error_prefers_the_engine_error_line() {
        let dir = std::env::temp_dir().join(format!("strehl-follow-log-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let log = dir.join("follow.log");
        fs::write(
            &log,
            "plane 1 : pass\nError: resolve run\n\nCaused by: gone\n",
        )
        .unwrap();
        assert_eq!(last_error(&log).as_deref(), Some("resolve run"));
        fs::write(&log, "plane 1 : pass\nexit\n\n").unwrap();
        assert_eq!(last_error(&log).as_deref(), Some("exit"));
        fs::remove_dir_all(&dir).unwrap();
    }
}
