//! Depth signatures (plan 7.3): each saved render's depth rail, pooled to at
//! most 128 values, for the Library's list rows and the subject page's stack
//! rows.
//!
//! The definition is the rail's own, at its default detail size (level 0,
//! the finest): per plane, the share of sampled sites whose noise gate
//! admitted that plane. The values come from replaying the run as a reopen
//! does (the log, then its `evidence.strehl`) into a `PipelineProgress` and
//! running `DepthRail::update` on it, so a signature matches the Stack
//! station's rail for the same render. Planes are pooled by the ratio of
//! sums, as the rail pools its columns. A column with no observed plane is
//! stored as a negative value: nothing is drawn there, never an observed
//! zero. A run whose log and file carry no per-plane evidence (older GPU
//! renders, imported sessions) has no signature and shows none.
//!
//! Work: one replay at a time on a worker, only for rows the Library or a
//! subject page painted, never while a stack renders. Results are cached by
//! run folder in `depth-signatures.json` beside the catalog (bounded; never
//! in a run or capture folder); a saved run's log does not change.
use crate::depth_rail::{DepthRail, evidence_revision};
use crate::jobs::{self, Task};
use crate::pipeline::{PipelineProgress, Utf8LogDecoder};
use crate::workspace_history::{Catalog, NodeId, NodeKind};
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

pub(crate) const FILE_NAME: &str = "depth-signatures.json";
/// The most values one signature keeps (a 230-px spark pools further).
pub(crate) const MAX_VALUES: usize = 128;
/// The rail's default detail size.
const LEVEL: usize = 0;
const FORMAT: u32 = 1;
const MAX_ENTRIES: usize = 4096;
const MAX_FILE_BYTES: u64 = 16 << 20;
/// Rows asked for and not yet computed; older requests fall off.
const MAX_WANTED: usize = 64;
/// The cache is written at most this often.
const SAVE_EVERY: Duration = Duration::from_secs(5);

/// One render's signature. Empty `values`: the run carries no per-plane
/// evidence, so there is nothing to show (and nothing to compute again).
#[derive(Clone, Debug, Default, PartialEq, Serialize, Deserialize)]
pub(crate) struct Signature {
    pub planes: usize,
    pub values: Vec<f32>,
}

/// The replay a reopen does, bounded the same way: a log without an
/// evidence file is read up to 512 MiB, one with it up to 4 GiB.
pub(crate) fn compute(directory: &Path, log: &Path, cancelled: &AtomicBool) -> Result<Signature> {
    let mut file = std::fs::File::open(log)?;
    let limit: u64 = if directory.join(crate::evidence_file::FILE_NAME).is_file() {
        4 << 30
    } else {
        512 << 20
    };
    if file.metadata()?.len() > limit {
        return Ok(Signature::default());
    }
    let mut progress = PipelineProgress::default();
    let mut decoder = Utf8LogDecoder::default();
    let mut buffer = vec![0u8; 1 << 16];
    loop {
        anyhow::ensure!(!cancelled.load(Ordering::Relaxed), "Cancelled");
        let count = file.read(&mut buffer)?;
        progress.ingest(&decoder.decode(&buffer[..count], count == 0));
        if count == 0 {
            break;
        }
    }
    progress.finish();
    if let Some((name, version)) = progress.evidence_file.clone()
        && version == crate::evidence_file::VERSION
        && let Some(path) = crate::evidence_file::named_path(directory, &name)
        && path.is_file()
    {
        // A damaged file costs the signature its maps, as it costs a reopen.
        let _ = crate::evidence_file::read_into(&path, cancelled, |header, record| {
            progress.ingest_evidence(header, record)
        });
        anyhow::ensure!(!cancelled.load(Ordering::Relaxed), "Cancelled");
    }
    Ok(from_progress(&progress))
}

/// The rail's series for `progress`, pooled.
pub(crate) fn from_progress(progress: &PipelineProgress) -> Signature {
    let Some(planes) = progress.frames_total.filter(|&n| n > 0) else {
        return Signature::default();
    };
    let mut rail = DepthRail::default();
    rail.update(
        &progress.admission_archive,
        &progress.sampled_mask_history,
        planes,
        LEVEL,
        evidence_revision(progress),
    );
    let columns = planes.min(MAX_VALUES);
    let mut values = Vec::with_capacity(columns);
    let mut any = false;
    for column in 0..columns {
        let (mut admitted, mut observed) = (0.0f64, 0.0f64);
        for plane in column * planes / columns..(column + 1) * planes / columns {
            if let Some(evidence) = rail.evidence(plane).filter(|e| e.observed > 0.0) {
                admitted += f64::from(evidence.admitted);
                observed += f64::from(evidence.observed);
            }
        }
        if observed > 0.0 {
            any = true;
            values.push((admitted / observed) as f32);
        } else {
            values.push(-1.0);
        }
    }
    if !any {
        values.clear();
    }
    Signature { planes, values }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct Entry {
    signature: Signature,
    /// Unix seconds; the oldest entries leave first.
    computed: u64,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Stored {
    format: u32,
    #[serde(default)]
    runs: Vec<(PathBuf, Entry)>,
}

/// The cache file's contents, or empty when it is missing, unreadable or
/// from a newer format (left as it is until the next save replaces it).
fn load(path: &Path) -> HashMap<PathBuf, Entry> {
    let read = || -> Result<HashMap<PathBuf, Entry>> {
        let file = std::fs::File::open(path)?;
        anyhow::ensure!(file.metadata()?.len() <= MAX_FILE_BYTES, "too large");
        let stored: Stored = serde_json::from_reader(std::io::BufReader::new(file))?;
        anyhow::ensure!(stored.format == FORMAT, "format {}", stored.format);
        Ok(stored.runs.into_iter().take(MAX_ENTRIES).collect())
    };
    read().unwrap_or_default()
}

fn save(path: &Path, entries: &HashMap<PathBuf, Entry>) -> Result<()> {
    let mut runs: Vec<(PathBuf, Entry)> = entries
        .iter()
        .map(|(path, entry)| (path.clone(), entry.clone()))
        .collect();
    runs.sort_by(|a, b| b.1.computed.cmp(&a.1.computed).then(a.0.cmp(&b.0)));
    let bytes = serde_json::to_vec(&Stored {
        format: FORMAT,
        runs,
    })?;
    let temporary = path.with_extension("json.tmp");
    {
        let mut file = std::fs::File::create(&temporary)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
    }
    std::fs::rename(&temporary, path)?;
    Ok(())
}

/// What a frame's rows ask for: the signature maps and the work behind them.
#[derive(Default)]
pub(crate) struct DepthSignatures {
    /// Beside the catalog; None for offscreen pictures and in tests.
    path: Option<PathBuf>,
    loading: Option<Task<HashMap<PathBuf, Entry>>>,
    loaded: bool,
    entries: HashMap<PathBuf, Entry>,
    revision: u64,
    dirty: bool,
    saved: Option<Instant>,
    saving: Option<Task<()>>,
    wanted: VecDeque<(PathBuf, PathBuf)>,
    task: Option<(PathBuf, Task<Signature>)>,
    /// Per catalog revision: each stack's and each subject's newest saved
    /// render (folder, log), and the signatures shown for them.
    key: Option<(u64, u64)>,
    stack_run: HashMap<NodeId, (PathBuf, PathBuf)>,
    subject_run: HashMap<NodeId, (PathBuf, PathBuf)>,
    stacks: HashMap<NodeId, Vec<f32>>,
    subjects: HashMap<NodeId, Vec<f32>>,
    /// Replays started (tests and the notes).
    pub computed: u64,
}

impl DepthSignatures {
    /// Read the cache beside the catalog on a worker; `None` keeps it in
    /// memory. Rows asked for before this stay asked for.
    pub(crate) fn open(&mut self, path: Option<PathBuf>) {
        self.loading = path
            .clone()
            .map(|path| jobs::spawn_task("strehl-depth-signatures", move |_| Ok(load(&path))));
        self.loaded = self.loading.is_none();
        self.path = path;
    }
    /// A cache opened at `path` (tests).
    #[cfg(test)]
    pub(crate) fn opened_at(path: Option<PathBuf>) -> Self {
        let mut signatures = Self::default();
        signatures.open(path);
        signatures
    }
    /// Whether `open` has been called.
    pub(crate) fn opened(&self) -> bool {
        self.loaded || self.loading.is_some()
    }
    pub(crate) fn path_beside(catalog: &Path) -> Option<PathBuf> {
        catalog.parent().map(|dir| dir.join(FILE_NAME))
    }

    /// Signatures by stack (its newest saved render) and by subject (its
    /// newest saved render among its stacks). Rebuilt when the catalog
    /// revision or the cache changes; O(1) otherwise.
    pub(crate) fn refresh(&mut self, catalog: &Catalog, revision: u64) {
        let key = (revision, self.revision);
        if self.key == Some(key) {
            return;
        }
        if self.key.is_none_or(|old| old.0 != revision) {
            self.index(catalog);
        }
        self.key = Some(key);
        let value = |run: &(PathBuf, PathBuf)| {
            self.entries
                .get(&run.0)
                .map(|entry| &entry.signature.values)
                .filter(|values| !values.is_empty())
                .cloned()
        };
        self.stacks = self
            .stack_run
            .iter()
            .filter_map(|(id, run)| Some((*id, value(run)?)))
            .collect();
        self.subjects = self
            .subject_run
            .iter()
            .filter_map(|(id, run)| Some((*id, value(run)?)))
            .collect();
    }

    fn index(&mut self, catalog: &Catalog) {
        let mut owner: HashMap<&Path, NodeId> = HashMap::new();
        for node in catalog.nodes.iter().filter(|n| n.kind == NodeKind::Stack) {
            for directory in &node.revisions {
                owner.insert(directory.as_path(), node.id);
            }
        }
        let subject_of = |mut id: NodeId| {
            for _ in 0..64 {
                let node = catalog.node(id)?;
                if node.kind == NodeKind::Subject {
                    return Some(node.id);
                }
                id = node.parent?;
            }
            None
        };
        let mut newest: HashMap<NodeId, (u64, PathBuf, PathBuf)> = HashMap::new();
        for run in catalog
            .runs
            .iter()
            .filter(|run| run.status == "Saved" && run.imported.is_none())
        {
            let Some(&stack) = owner.get(run.directory.as_path()) else {
                continue;
            };
            let slot = newest
                .entry(stack)
                .or_insert((0, PathBuf::new(), PathBuf::new()));
            if run.created >= slot.0 {
                *slot = (run.created, run.directory.clone(), run.log.clone());
            }
        }
        self.stack_run.clear();
        self.subject_run.clear();
        let mut subject_created: HashMap<NodeId, u64> = HashMap::new();
        for (stack, (created, directory, log)) in newest {
            if let Some(subject) = subject_of(stack)
                && subject_created.get(&subject).is_none_or(|&c| created >= c)
            {
                subject_created.insert(subject, created);
                self.subject_run
                    .insert(subject, (directory.clone(), log.clone()));
            }
            self.stack_run.insert(stack, (directory, log));
        }
    }

    pub(crate) fn stacks(&self) -> &HashMap<NodeId, Vec<f32>> {
        &self.stacks
    }
    pub(crate) fn subjects(&self) -> &HashMap<NodeId, Vec<f32>> {
        &self.subjects
    }

    /// Ask for the signatures of rows on screen. O(rows).
    pub(crate) fn want_stacks(&mut self, stacks: impl IntoIterator<Item = NodeId>) {
        for id in stacks {
            if let Some(run) = self.stack_run.get(&id).cloned() {
                self.want(run);
            }
        }
    }
    pub(crate) fn want_subjects(&mut self, subjects: impl IntoIterator<Item = NodeId>) {
        for id in subjects {
            if let Some(run) = self.subject_run.get(&id).cloned() {
                self.want(run);
            }
        }
    }
    fn want(&mut self, run: (PathBuf, PathBuf)) {
        if self.entries.contains_key(&run.0)
            || self.task.as_ref().is_some_and(|(d, _)| *d == run.0)
            || self.wanted.iter().any(|(d, _)| *d == run.0)
        {
            return;
        }
        if self.wanted.len() == MAX_WANTED {
            self.wanted.pop_back();
        }
        self.wanted.push_front(run);
    }

    /// Collect finished work and start the next replay when `allowed` (no
    /// stack rendering, Quiet not holding). Returns whether anything changed.
    pub(crate) fn poll(&mut self, allowed: bool, unix: u64) -> bool {
        let mut changed = false;
        if let Some(task) = &self.loading
            && let Ok(result) = task.receiver.try_recv()
        {
            self.loading = None;
            self.loaded = true;
            for (path, entry) in result.unwrap_or_default() {
                self.entries.entry(path).or_insert(entry);
            }
            self.revision += 1;
            changed = true;
        }
        if let Some((_, task)) = &self.task {
            match task.receiver.try_recv() {
                Ok(result) => {
                    let (directory, _) = self.task.take().unwrap();
                    // A failed read (a moved or deleted run) shows nothing
                    // and is not retried this session.
                    let signature = result.unwrap_or_default();
                    self.insert(directory, signature, unix);
                    changed = true;
                }
                Err(std::sync::mpsc::TryRecvError::Disconnected) => self.task = None,
                Err(std::sync::mpsc::TryRecvError::Empty) => {}
            }
        }
        if !allowed && let Some((_, task)) = self.task.take() {
            // A stack started: give the machine back; the row asks again.
            task.cancel();
        }
        if allowed
            && self.loaded
            && self.task.is_none()
            && let Some((directory, log)) = self.wanted.pop_front()
        {
            self.computed += 1;
            let folder = directory.clone();
            let task = jobs::spawn_task("strehl-depth-signature", move |cancelled| {
                compute(&folder, &log, &cancelled)
            });
            self.task = Some((directory, task));
        }
        if self.dirty
            && self.task.is_none()
            && self.saved.is_none_or(|at| at.elapsed() >= SAVE_EVERY)
        {
            self.save();
        }
        changed
    }
    fn insert(&mut self, directory: PathBuf, signature: Signature, unix: u64) {
        self.entries.insert(
            directory,
            Entry {
                signature,
                computed: unix,
            },
        );
        if self.entries.len() > MAX_ENTRIES
            && let Some(oldest) = self
                .entries
                .iter()
                .min_by_key(|(_, entry)| entry.computed)
                .map(|(path, _)| path.clone())
        {
            self.entries.remove(&oldest);
        }
        self.revision += 1;
        self.dirty = self.path.is_some();
    }
    /// Write the cache on a worker (on the throttle from `poll`).
    pub(crate) fn save(&mut self) {
        if self.saving.as_ref().is_some_and(|task| {
            matches!(
                task.receiver.try_recv(),
                Err(std::sync::mpsc::TryRecvError::Empty)
            )
        }) {
            // One write at a time; this one follows it.
            self.dirty = true;
            return;
        }
        self.saving = None;
        self.saved = Some(Instant::now());
        self.dirty = false;
        if let Some(path) = self.path.clone()
            && self.loaded
        {
            let entries = self.entries.clone();
            self.saving = Some(jobs::spawn_task(
                "strehl-depth-signatures-save",
                move |_| save(&path, &entries),
            ));
        }
    }
    /// Work in flight or waiting (offscreen readiness and tests).
    pub(crate) fn pending(&self) -> bool {
        self.loading.is_some() || self.task.is_some() || !self.wanted.is_empty()
    }
    /// Wait for a save in flight (tests).
    #[cfg(test)]
    pub(crate) fn flush(&mut self) {
        if let Some(task) = self.saving.take() {
            let _ = task.receiver.recv();
        }
    }
}

#[cfg(test)]
#[path = "depth-signature-tests.rs"]
mod tests;
