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
    collections::BTreeMap,
    fs,
    io::Write,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::{Duration, Instant},
};

/// A run whose records have not changed for this long, with the camera not
/// capturing, is no longer followed.
pub(crate) const ABANDONED: Duration = Duration::from_secs(600);
const POLL: Duration = Duration::from_millis(500);

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
}

/// Reads the checker's journal: one JSON line per plane, a later line for a
/// plane replacing an earlier one, as the engine reads it when it resumes.
pub(crate) fn progress(journal: &str) -> Progress {
    let mut planes = BTreeMap::new();
    for line in journal.lines() {
        if let Ok(v) = serde_json::from_str::<Value>(line)
            && let Some(plane) = v["plane"].as_u64()
        {
            planes.insert(plane, v);
        }
    }
    let mut p = Progress::default();
    for v in planes.values() {
        let verdict = v["verdict"].as_str().unwrap_or("");
        if verdict != "incomplete" {
            p.checked += 1;
        }
        if verdict == "pass" {
            p.passed += 1;
        } else if verdict != "decoded" {
            p.attention += 1;
        }
        if v["retake"] == true
            && let Some(target) = v["target"].as_u64()
        {
            p.retake.push(target);
        }
        p.align_pairs += v["align_pairs"].as_u64().unwrap_or(0);
    }
    p.retake.sort_unstable();
    p
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
    journal: PathBuf,
    lock: PathBuf,
    pub log: PathBuf,
    child: Option<crate::jobs::OwnedChild>,
    /// Another process (another Strehl window, or `strehl follow`) holds the
    /// run's lock: this one only shows its progress.
    pub observing: bool,
    pub state: State,
    pub progress: Progress,
    journal_len: Option<u64>,
    polled: Option<Instant>,
    pub started: Instant,
    /// Set once the finished capture was offered to Projects.
    pub offered: bool,
}

/// The engine invocation: `follow <run>` with the desktop's shared cache and
/// none of the inherited `STREHL_*` overrides, as renders are configured, so
/// the measurements are keyed exactly as the closing render looks them up.
pub(crate) fn command(engine: &Path, run: &Path, cache: &Path) -> Result<Command> {
    let mut command = crate::engine::command(engine)?;
    command.arg("follow").arg(run);
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
    pub fn start(engine: &Path, run: &Path) -> Result<Self> {
        let cache = strehl_cli::default_cache_root();
        fs::create_dir_all(&cache).context("Creating the engine cache")?;
        let journal = strehl_cli::follow_journal_path(&cache, run)
            .context("Locating the capture checker's journal")?;
        let lock = strehl_cli::follow_lock_path(&journal);
        let log = journal.with_extension("log");
        let mut follower = Self {
            run: run.to_owned(),
            journal,
            lock,
            log,
            child: None,
            observing: false,
            state: State::Running,
            progress: Progress::default(),
            journal_len: None,
            polled: None,
            started: Instant::now(),
            offered: false,
        };
        if locked_elsewhere(&follower.lock) {
            // The other checker's own window opens the finished capture.
            follower.observing = true;
            follower.offered = true;
            follower.read_journal();
            return Ok(follower);
        }
        let log = &follower.log;
        let mut command = command(engine, run, &cache)?;
        let mut out = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(log)
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
        follower.read_journal();
        Ok(follower)
    }

    pub fn running(&self) -> bool {
        self.state == State::Running
    }

    /// Reads new journal lines and notices the checker's exit. Cheap enough
    /// for every frame: it does real work at most twice a second.
    pub fn poll(&mut self) {
        if self.polled.is_some_and(|t| t.elapsed() < POLL) {
            return;
        }
        self.polled = Some(Instant::now());
        if self.observing {
            self.read_journal();
            if self.running() && !locked_elsewhere(&self.lock) {
                self.state = State::Stopped("Checked by another Strehl window or process".into());
            }
            return;
        }
        // The exit is read first so the journal read after it is complete.
        let exited = self
            .child
            .as_mut()
            .map(|child| child.0.try_wait())
            .transpose();
        self.read_journal();
        match exited {
            Ok(Some(Some(status))) => {
                self.child = None;
                self.journal_len = None;
                self.read_journal();
                self.state = if status.success() {
                    State::Finished
                } else {
                    State::Failed(
                        last_error(&self.log)
                            .unwrap_or_else(|| format!("The capture checker stopped ({status})")),
                    )
                };
            }
            Ok(_) => {}
            Err(e) => {
                self.child = None;
                self.state = State::Failed(format!("Checking the capture checker: {e}"));
            }
        }
    }

    /// Ends the checker; its journal keeps every plane checked so far.
    pub fn stop(&mut self, reason: &str) {
        // Dropping the owned child ends it and waits.
        self.child = None;
        if self.running() {
            self.state = State::Stopped(reason.into());
        }
    }

    fn read_journal(&mut self) {
        let len = fs::metadata(&self.journal).map(|m| m.len()).ok();
        if len.is_none() || len == self.journal_len {
            return;
        }
        if let Ok(text) = fs::read_to_string(&self.journal) {
            self.progress = progress(&text);
            self.journal_len = len;
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
            "checked":self.progress.checked,"passed":self.progress.passed,
            "attention":self.progress.attention,"retake_positions":self.progress.retake,
            "align_pairs":self.progress.align_pairs})
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
        assert_eq!(
            progress(&journal),
            Progress {
                checked: 4,
                passed: 2,
                attention: 2,
                retake: vec![90, 110],
                align_pairs: 6,
            }
        );
        assert_eq!(progress(""), Progress::default());
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
        assert_eq!(&args[args.len() - 2..], ["follow", "run-folder"]);
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
