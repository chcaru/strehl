//! Catalog format 2: subjects. A subject is one specimen or object and holds
//! the stacks photographed of it: Collection (project) > folder* > subject >
//! stack. Subjects, their metadata and the migration that introduces them are
//! catalog edits only; nothing on disk moves.
#![cfg_attr(
    not(test),
    allow(
        dead_code,
        reason = "the library station (P4 UI) calls these model APIs; tests cover them until then"
    )
)]
use super::{
    CATALOG_FORMAT, Catalog, MAX_CATALOG_BYTES, NodeId, NodeKind, ProjectNode, Run, SourceIdentity,
    StackDraft, read_catalog_bytes, source_identities, timestamp,
};
use crate::jobs;
use serde::{Deserialize, Serialize};
use std::{
    collections::{HashMap, HashSet},
    ffi::{OsStr, OsString},
    io::Write,
    path::{Path, PathBuf},
};

pub(super) const MAX_NOTES_CHARS: usize = 4000;
const MAX_TEXT_CHARS: usize = 160;
const MAX_PATH_CHARS: usize = 4096;
/// The status a reconciled run carries after its desktop was hard-killed.
pub(crate) const INTERRUPTED: &str = "Interrupted";

/// What a subject knows beyond its name. Its notes are the node's `notes`,
/// shared by every node kind and already part of undo.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct SubjectMeta {
    /// The representative photograph, usually a render's output.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub hero: Option<PathBuf>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub optics: Option<Optics>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub scale: Option<ScaleCalibration>,
    /// Unix seconds.
    pub created: u64,
}
impl SubjectMeta {
    pub(crate) fn new(created: u64) -> Self {
        Self {
            hero: None,
            optics: None,
            scale: None,
            created,
        }
    }
    pub(crate) fn validate(&self) -> anyhow::Result<()> {
        if let Some(hero) = &self.hero {
            let length = hero.as_os_str().len();
            anyhow::ensure!(
                length > 0 && length <= MAX_PATH_CHARS,
                "Choose an existing photograph for the subject"
            );
        }
        if let Some(optics) = &self.optics {
            optics.validate()?;
        }
        if let Some(scale) = &self.scale {
            scale.validate()?;
        }
        Ok(())
    }
}

/// Typed by the owner; nothing in the RAW records magnification (D12).
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Optics {
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub camera: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub lens: String,
}
impl Optics {
    fn validate(&self) -> anyhow::Result<()> {
        short_text(&self.camera, "Camera")?;
        short_text(&self.lens, "Lens")
    }
}

/// Micrometres per pixel at the sensor, for a scale bar and a step size in
/// micrometres. A per-lens calibration, never read from the RAW (D12).
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ScaleCalibration {
    pub um_per_px: f64,
    pub source: ScaleSource,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub(crate) enum ScaleSource {
    /// Measured on a reference such as a stage micrometre slide.
    Measured {
        #[serde(default, skip_serializing_if = "String::is_empty")]
        slide: String,
    },
    /// Entered once: the optical magnification and the sensor's pixel pitch.
    Entered { magnification: f64, pitch_um: f64 },
}
impl ScaleCalibration {
    pub(crate) fn measured(um_per_px: f64, slide: &str) -> anyhow::Result<Self> {
        let scale = Self {
            um_per_px,
            source: ScaleSource::Measured {
                slide: slide.trim().to_owned(),
            },
        };
        scale.validate()?;
        Ok(scale)
    }
    pub(crate) fn entered(magnification: f64, pitch_um: f64) -> anyhow::Result<Self> {
        let scale = Self {
            um_per_px: pitch_um / magnification,
            source: ScaleSource::Entered {
                magnification,
                pitch_um,
            },
        };
        scale.validate()?;
        Ok(scale)
    }
    pub(crate) fn validate(&self) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.um_per_px.is_finite() && self.um_per_px > 0.0 && self.um_per_px <= 1.0e6,
            "Scale must be a positive number of micrometres per pixel"
        );
        match &self.source {
            ScaleSource::Measured { slide } => short_text(slide, "Slide"),
            ScaleSource::Entered {
                magnification,
                pitch_um,
            } => {
                anyhow::ensure!(
                    magnification.is_finite() && *magnification > 0.0 && *magnification <= 1000.0,
                    "Magnification must be between 0 and 1000"
                );
                anyhow::ensure!(
                    pitch_um.is_finite() && *pitch_um > 0.0 && *pitch_um <= 100.0,
                    "Pixel pitch must be between 0 and 100 micrometres"
                );
                let derived = pitch_um / magnification;
                anyhow::ensure!(
                    (self.um_per_px - derived).abs() <= derived * 1.0e-9,
                    "An entered scale is the pixel pitch divided by the magnification"
                );
                Ok(())
            }
        }
    }
}

/// A partial edit: `None` leaves a field alone; `Some(None)` clears it.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct SubjectEdit {
    pub notes: Option<String>,
    pub hero: Option<Option<PathBuf>>,
    pub optics: Option<Option<Optics>>,
    pub scale: Option<Option<ScaleCalibration>>,
}

fn short_text(text: &str, label: &str) -> anyhow::Result<()> {
    anyhow::ensure!(
        text.chars().count() <= MAX_TEXT_CHARS && !text.chars().any(char::is_control),
        "{label}: keep it within {MAX_TEXT_CHARS} characters, on one line"
    );
    Ok(())
}

/// Sony names the folders it writes `100MSDCF`, `101MSDCF`, …: a camera
/// folder names the card, not what was photographed.
pub(crate) fn is_camera_folder(name: &str) -> bool {
    let bytes = name.as_bytes();
    bytes.len() == 8
        && bytes[..3].iter().all(u8::is_ascii_digit)
        && bytes[3..].eq_ignore_ascii_case(b"MSDCF")
}

/// The name a new stack of `source` starts with: a camera folder takes its
/// parent folder's name (`D:\bug-3\107MSDCF` gives `bug-3`), anything else its
/// own. A card's `DCIM` and a drive root name nothing, so they are skipped.
pub(crate) fn default_stack_name(source: &Path) -> String {
    let own = source.file_name().map(OsStr::to_string_lossy);
    if let Some(own) = &own
        && is_camera_folder(own)
        && let Some(parent) = meaningful_parent(source)
    {
        return parent;
    }
    own.map(|name| clean_name(&name))
        .filter(|name| !name.is_empty())
        .unwrap_or_else(|| "Capture stack".into())
}
fn meaningful_parent(source: &Path) -> Option<String> {
    let name = clean_name(&source.parent()?.file_name()?.to_string_lossy());
    (!name.is_empty() && !name.eq_ignore_ascii_case("DCIM")).then_some(name)
}
/// A valid catalog name: control characters become spaces, 160 characters at most.
fn clean_name(name: &str) -> String {
    let name: String = name
        .chars()
        .map(|c| if c.is_control() { ' ' } else { c })
        .collect();
    name.trim()
        .chars()
        .take(MAX_TEXT_CHARS)
        .collect::<String>()
        .trim()
        .to_owned()
}
/// Comparable folder identity: verbatim prefix removed, and on Windows
/// separators unified and case folded.
pub(super) fn path_key(path: &Path) -> String {
    let text = path.to_string_lossy();
    let text = if let Some(rest) = text.strip_prefix(r"\\?\UNC\") {
        format!(r"\\{rest}")
    } else {
        text.strip_prefix(r"\\?\").unwrap_or(&text).to_owned()
    };
    let text = if cfg!(windows) {
        text.replace('/', "\\").to_lowercase()
    } else {
        text
    };
    text.trim_end_matches(['\\', '/']).to_owned()
}
/// The migration's grouping key and subject name for one stack. A camera
/// folder groups by the folder above it; anything else by its own source
/// folder, so stacks of the same folder share a subject.
fn grouping(node: &ProjectNode) -> (String, String) {
    let source = node
        .stack
        .as_ref()
        .map_or(Path::new(""), |draft| draft.source.as_path());
    let camera = is_camera_folder(&node.name)
        || source
            .file_name()
            .is_some_and(|name| is_camera_folder(&name.to_string_lossy()));
    if camera
        && let Some(parent) = source.parent()
        && let Some(name) = meaningful_parent(source)
    {
        return (path_key(parent), name);
    }
    if source.as_os_str().is_empty() {
        return (format!("stack:{}", node.id), node.name.clone());
    }
    (path_key(source), node.name.clone())
}

/// One subject's worth of folders to import, one stack per folder.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct ImportGroup {
    /// The subject's suggested name: the camera folders' parent, else the folder.
    pub subject: String,
    pub folders: Vec<PathBuf>,
}

/// Folders dropped or picked together, grouped like the migration groups
/// stacks: camera folders by the folder above them, any other folder alone.
/// Duplicates collapse; groups keep the first folder's order and list their
/// folders by name. Pure: the importer scans and validates each folder.
pub(crate) fn import_plan(folders: &[PathBuf]) -> Vec<ImportGroup> {
    let mut groups: Vec<(String, ImportGroup)> = Vec::new();
    let mut seen = HashSet::new();
    for folder in folders {
        if folder.as_os_str().is_empty() || !seen.insert(path_key(folder)) {
            continue;
        }
        let camera = folder
            .file_name()
            .is_some_and(|name| is_camera_folder(&name.to_string_lossy()));
        let (key, subject) = match (camera, folder.parent(), meaningful_parent(folder)) {
            (true, Some(parent), Some(name)) => (path_key(parent), name),
            _ => (path_key(folder), default_stack_name(folder)),
        };
        match groups.iter_mut().find(|(k, _)| *k == key) {
            Some((_, group)) => group.folders.push(folder.clone()),
            None => groups.push((
                key,
                ImportGroup {
                    subject,
                    folders: vec![folder.clone()],
                },
            )),
        }
    }
    groups
        .into_iter()
        .map(|(_, mut group)| {
            group.folders.sort();
            group
        })
        .collect()
}

impl Catalog {
    /// Every stack outside a subject joins one: an existing subject in the
    /// same container whose stacks share its grouping key, else a new one
    /// placed where the stack sits. Selection and expansion are kept. Runs,
    /// recipes, versions and exports are untouched. Idempotent.
    pub(super) fn migrate_subjects(&mut self) -> anyhow::Result<()> {
        let orphans: Vec<NodeId> = self
            .nodes
            .iter()
            .filter(|node| {
                node.kind == NodeKind::Stack
                    && node
                        .parent
                        .and_then(|parent| self.node(parent))
                        .is_some_and(|parent| parent.kind != NodeKind::Subject)
            })
            .map(|node| node.id)
            .collect();
        if orphans.is_empty() {
            return Ok(());
        }
        let selected = self.selected;
        let expanded: Vec<(NodeId, bool)> = self.nodes.iter().map(|n| (n.id, n.expanded)).collect();
        let mut subjects: HashMap<(NodeId, String), NodeId> = HashMap::new();
        for node in &self.nodes {
            if node.kind != NodeKind::Stack {
                continue;
            }
            if let Some(subject) = node.parent.and_then(|id| self.node(id))
                && subject.kind == NodeKind::Subject
                && let Some(container) = subject.parent
            {
                subjects
                    .entry((container, grouping(node).0))
                    .or_insert(subject.id);
            }
        }
        let mut created_here = HashSet::new();
        for id in orphans {
            let node = self.node(id).unwrap();
            let container = node.parent.unwrap();
            let (key, name) = grouping(node);
            // The stack's own record: its first render, or when its photographs
            // were written, whichever is earlier. Never the time of migration:
            // a stack nobody rendered would otherwise date its subject "today".
            let first_run = node
                .revisions
                .iter()
                .filter_map(|directory| self.runs.iter().find(|r| &r.directory == directory))
                .map(|run| run.created)
                .filter(|&created| created > 0)
                .chain(node.stack.as_ref().and_then(recorded_capture))
                .min();
            let subject = match subjects.get(&(container, key.clone())) {
                Some(&subject) => {
                    if created_here.contains(&subject)
                        && let Some(first_run) = first_run
                        && let Some(meta) = self.node_mut(subject).unwrap().subject.as_mut()
                    {
                        meta.created = if meta.created == 0 {
                            first_run
                        } else {
                            meta.created.min(first_run)
                        };
                    }
                    subject
                }
                None => {
                    let name = if name.trim().is_empty() {
                        "Subject".to_owned()
                    } else {
                        name
                    };
                    let subject =
                        self.insert_node(Some(container), &name, NodeKind::Subject, None)?;
                    // 0 when nothing is recorded: the subject shows no date.
                    self.node_mut(subject).unwrap().subject =
                        Some(SubjectMeta::new(first_run.unwrap_or(0)));
                    // Sit where the first stack sat, so the tree keeps its order.
                    let from = self.nodes.iter().position(|n| n.id == subject).unwrap();
                    let to = self.nodes.iter().position(|n| n.id == id).unwrap();
                    let moved = self.nodes.remove(from);
                    self.nodes.insert(to, moved);
                    created_here.insert(subject);
                    subjects.insert((container, key), subject);
                    subject
                }
            };
            self.node_mut(id).unwrap().parent = Some(subject);
        }
        self.selected = selected;
        for (id, open) in expanded {
            if let Some(node) = self.node_mut(id) {
                node.expanded = open;
            }
        }
        // One more level must still fit the depth and object limits.
        self.validate()
    }

    pub fn create_subject(&mut self, parent: NodeId, name: &str) -> anyhow::Result<NodeId> {
        self.check_parent(NodeKind::Subject, parent)?;
        let id = self.insert_node(Some(parent), name, NodeKind::Subject, None)?;
        self.node_mut(id).unwrap().subject = Some(SubjectMeta::new(timestamp()));
        Ok(id)
    }

    /// Validates the whole edit before changing anything.
    pub fn set_subject_meta(&mut self, id: NodeId, edit: SubjectEdit) -> anyhow::Result<()> {
        let node = self
            .node(id)
            .ok_or_else(|| anyhow::anyhow!("Subject no longer exists"))?;
        anyhow::ensure!(node.kind == NodeKind::Subject, "Choose a subject");
        let mut meta = node
            .subject
            .clone()
            .unwrap_or_else(|| SubjectMeta::new(timestamp()));
        if let Some(notes) = &edit.notes {
            anyhow::ensure!(
                notes.chars().count() <= MAX_NOTES_CHARS,
                "Keep notes within {MAX_NOTES_CHARS} characters"
            );
        }
        if let Some(hero) = edit.hero {
            meta.hero = hero;
        }
        if let Some(optics) = edit.optics {
            meta.optics = optics.map(|o| Optics {
                camera: o.camera.trim().to_owned(),
                lens: o.lens.trim().to_owned(),
            });
        }
        if let Some(scale) = edit.scale {
            meta.scale = scale;
        }
        meta.validate()?;
        let node = self.node_mut(id).unwrap();
        node.subject = Some(meta);
        if let Some(notes) = edit.notes {
            node.notes = notes;
        }
        Ok(())
    }

    /// The subject directly holding `stack`; none for a format-1 placement.
    pub fn subject_of(&self, stack: NodeId) -> Option<NodeId> {
        let node = self.node(stack).filter(|n| n.kind == NodeKind::Stack)?;
        self.node(node.parent?)
            .filter(|parent| parent.kind == NodeKind::Subject)
            .map(|parent| parent.id)
    }

    /// The subject's stacks in catalog order (oldest first).
    pub fn stacks_of(&self, subject: NodeId) -> Vec<NodeId> {
        self.nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Stack && n.parent == Some(subject))
            .map(|n| n.id)
            .collect()
    }

    /// A render of `stack` by its position in the stack's revisions.
    pub fn revision(&self, stack: NodeId, index: usize) -> Option<&Run> {
        let directory = self.node(stack)?.revisions.get(index)?;
        self.runs.iter().find(|run| &run.directory == directory)
    }

    /// Where one stack stands, from the catalog alone (no I/O).
    pub fn stack_lifecycle(&self, stack: NodeId) -> Option<StackLifecycle> {
        let node = self.node(stack).filter(|n| n.kind == NodeKind::Stack)?;
        let runs: Vec<&Run> = node
            .revisions
            .iter()
            .filter_map(|directory| self.runs.iter().find(|r| &r.directory == directory))
            .collect();
        let mut versions = HashSet::new();
        let mut usage = Usage::default();
        for version in &self.photo_versions {
            if version.owner.stack == Some(stack) {
                versions.insert(version.id.as_str());
                usage.version(version.created);
            }
        }
        for export in &self.photo_exports {
            if versions.contains(export.version.as_str()) {
                usage.export(export.created);
            }
        }
        let captured = node.stack.as_ref().and_then(recorded_capture).unwrap_or(0);
        Some(StackLifecycle::from_parts(&runs, usage, captured))
    }

    /// One subject's stacks combined, from the catalog alone (no I/O).
    pub fn subject_summary(&self, subject: NodeId) -> Option<SubjectSummary> {
        self.node(subject).filter(|n| n.kind == NodeKind::Subject)?;
        let mut summary = SubjectSummary::default();
        for stack in self.stacks_of(subject) {
            if let Some(lifecycle) = self.stack_lifecycle(stack) {
                summary.add(&lifecycle);
            }
        }
        Some(summary)
    }

    /// Every stack's lifecycle and every subject's summary in one pass over
    /// the catalog, for a library grid that rebuilds it once per catalog change.
    pub fn library_index(&self) -> LibraryIndex {
        let runs: HashMap<&Path, &Run> = self
            .runs
            .iter()
            .map(|run| (run.directory.as_path(), run))
            .collect();
        let mut usage: HashMap<NodeId, Usage> = HashMap::new();
        let mut version_stack: HashMap<&str, NodeId> = HashMap::new();
        for version in &self.photo_versions {
            if let Some(stack) = version.owner.stack {
                version_stack.insert(version.id.as_str(), stack);
                usage.entry(stack).or_default().version(version.created);
            }
        }
        for export in &self.photo_exports {
            if let Some(stack) = version_stack.get(export.version.as_str()) {
                usage.entry(*stack).or_default().export(export.created);
            }
        }
        let mut index = LibraryIndex::default();
        for node in &self.nodes {
            match node.kind {
                NodeKind::Stack => {
                    let revisions: Vec<&Run> = node
                        .revisions
                        .iter()
                        .filter_map(|directory| runs.get(directory.as_path()).copied())
                        .collect();
                    let lifecycle = StackLifecycle::from_parts(
                        &revisions,
                        usage.get(&node.id).copied().unwrap_or_default(),
                        node.stack.as_ref().and_then(recorded_capture).unwrap_or(0),
                    );
                    index.stacks.insert(node.id, lifecycle);
                }
                NodeKind::Subject => {
                    index.subjects.entry(node.id).or_default();
                }
                NodeKind::Project | NodeKind::Folder => {}
            }
        }
        for node in &self.nodes {
            if node.kind == NodeKind::Stack
                && let Some(parent) = node.parent
                && let Some(summary) = index.subjects.get_mut(&parent)
            {
                summary.add(&index.stacks[&node.id]);
            }
        }
        index
    }

    /// Whether the stack's recorded sources are where the catalog says. Cheap:
    /// one directory listing per source folder, names only; never hashes or
    /// opens a file. Cache the answer; do not call it on every paint.
    pub fn sources_present(&self, stack: NodeId) -> Option<SourcesState> {
        let draft = self.node(stack)?.stack.as_ref()?;
        Some(sources_state(draft))
    }

    /// "Locate…": point the stack and its renders at `new_dir` when that folder
    /// holds the same sources, by name and size, and nothing else the stack
    /// would read. Scans the folder like opening a stack does (blocking).
    pub fn relocate_stack(
        &mut self,
        stack: NodeId,
        new_dir: &Path,
    ) -> anyhow::Result<RelocateReport> {
        self.relocation_source(stack)?;
        let scan = jobs::scan_stack(new_dir.to_path_buf())
            .receiver
            .recv()
            .map_err(|_| {
                anyhow::anyhow!(
                    "Reading {} stopped",
                    crate::display_path::display_path(new_dir)
                )
            })?
            .map_err(anyhow::Error::msg)?;
        self.relocate_stack_to_scan(stack, &scan)
    }

    /// The pure half of `relocate_stack`, for a scan made off the UI thread.
    /// Refuses with a `RelocateMismatch` and changes nothing unless every
    /// recorded source of the stack's folder is in the scan with its size, and
    /// the scan holds no other frame.
    pub fn relocate_stack_to_scan(
        &mut self,
        stack: NodeId,
        scan: &jobs::StackScan,
    ) -> anyhow::Result<RelocateReport> {
        let old = self.relocation_source(stack)?;
        let old_key = path_key(&old);
        let in_old = |path: &Path| path.parent().is_some_and(|dir| path_key(dir) == old_key);
        let node = self.node(stack).unwrap();
        let draft = node.stack.as_ref().unwrap();
        let fresh: HashMap<OsString, SourceIdentity> = source_identities(scan)
            .into_iter()
            .filter_map(|identity| Some((identity.path.file_name()?.to_owned(), identity)))
            .collect();
        let mut mismatch = RelocateMismatch {
            directory: scan.directory.clone(),
            ..RelocateMismatch::default()
        };
        let mut check = |identity: &SourceIdentity| {
            if !in_old(&identity.path) {
                return;
            }
            let name = identity.path.file_name().unwrap_or_default();
            match fresh.get(name) {
                None => mismatch.missing.push(name.to_string_lossy().into_owned()),
                Some(found) if found.bytes != identity.bytes => mismatch.resized.push((
                    name.to_string_lossy().into_owned(),
                    identity.bytes,
                    found.bytes,
                )),
                Some(_) => {}
            }
        };
        let recorded: HashSet<&OsStr> = draft
            .sources
            .iter()
            .filter(|identity| in_old(&identity.path))
            .filter_map(|identity| identity.path.file_name())
            .collect();
        anyhow::ensure!(
            !recorded.is_empty(),
            "This stack has no record of its sources to match; open the folder as a new stack"
        );
        draft.sources.iter().for_each(&mut check);
        let runs: Vec<usize> = node
            .revisions
            .iter()
            .filter_map(|directory| self.runs.iter().position(|r| &r.directory == directory))
            .collect();
        for &index in &runs {
            self.runs[index].sources.iter().for_each(&mut check);
        }
        for name in fresh.keys() {
            if !recorded.contains(name.as_os_str()) {
                mismatch
                    .unexpected
                    .push(name.to_string_lossy().into_owned());
            }
        }
        mismatch.missing.sort();
        mismatch.missing.dedup();
        mismatch.resized.sort();
        mismatch.resized.dedup();
        mismatch.unexpected.sort();
        if !mismatch.is_empty() {
            return Err(anyhow::Error::new(mismatch));
        }
        let mut modified_changed = 0;
        let mut sources = 0;
        let repoint = |identity: &mut SourceIdentity| -> Option<bool> {
            if !in_old(&identity.path) {
                return None;
            }
            let found = &fresh[identity.path.file_name()?];
            let changed = identity.modified_ns != found.modified_ns;
            identity.path.clone_from(&found.path);
            identity.modified_ns = found.modified_ns;
            Some(changed)
        };
        let draft = self.node_mut(stack).unwrap().stack.as_mut().unwrap();
        draft.source.clone_from(&scan.directory);
        for identity in &mut draft.sources {
            if let Some(changed) = repoint(identity) {
                sources += 1;
                modified_changed += usize::from(changed);
            }
        }
        for &index in &runs {
            let run = &mut self.runs[index];
            if path_key(&run.source) == old_key {
                run.source.clone_from(&scan.directory);
            }
            for identity in &mut run.sources {
                repoint(identity);
            }
        }
        Ok(RelocateReport {
            directory: scan.directory.clone(),
            sources,
            runs: runs.len(),
            modified_changed,
        })
    }
    fn relocation_source(&self, stack: NodeId) -> anyhow::Result<PathBuf> {
        let node = self
            .node(stack)
            .ok_or_else(|| anyhow::anyhow!("Stack no longer exists"))?;
        let draft = node
            .stack
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Choose a stack"))?;
        let session = draft.settings.session.is_some()
            || node.revisions.iter().any(|directory| {
                self.runs
                    .iter()
                    .any(|r| &r.directory == directory && r.settings.session.is_some())
            });
        anyhow::ensure!(
            !session,
            "This stack combines several capture folders; Locate handles a stack of one folder"
        );
        Ok(draft.source.clone())
    }

    /// A hard-killed desktop leaves its run "Stacking". Call once at start,
    /// after loading: such runs become "Interrupted" unless a live job owns
    /// them, either one of `active` or another running Strehl window, known by
    /// the process id in the job folder's name. Returns how many changed; the
    /// next save writes them.
    pub fn reconcile_interrupted_runs(&mut self, active: &[&Path]) -> usize {
        let own = std::process::id();
        let mut changed = 0;
        for run in &mut self.runs {
            if RunState::of(&run.status) != RunState::Stacking
                || active.contains(&run.directory.as_path())
            {
                continue;
            }
            if job_process(&run.directory)
                .is_some_and(|pid| pid != own && process_alive(pid, run.created))
            {
                continue;
            }
            run.status = INTERRUPTED.into();
            changed += 1;
        }
        changed
    }
}

/// The process id in a job folder named `strehl-<millis>-<pid>-<sequence>`.
pub(super) fn job_process(directory: &Path) -> Option<u32> {
    let name = directory.file_name()?.to_str()?;
    let mut parts = name.strip_prefix("strehl-")?.split('-');
    parts.next()?.parse::<u128>().ok()?;
    let pid = parts.next()?.parse::<u32>().ok()?;
    parts.next()?.parse::<u64>().ok()?;
    parts.next().is_none().then_some(pid)
}

/// Whether `pid` is running and started no later than `since` (Unix seconds),
/// so a reused id does not keep a dead window's run "Stacking". Where the
/// answer is unknown it is yes: leaving a run "Stacking" is the safe mistake.
#[cfg(windows)]
pub(super) fn process_alive(pid: u32, since: u64) -> bool {
    use windows_sys::Win32::{
        Foundation::{CloseHandle, ERROR_ACCESS_DENIED, FILETIME, GetLastError},
        System::Threading::{
            GetExitCodeProcess, GetProcessTimes, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION,
        },
    };
    const STILL_ACTIVE: u32 = 259;
    // SAFETY: plain value arguments; the returned handle is checked and closed.
    let handle = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid) };
    if handle.is_null() {
        // Another account's process exists but cannot be queried.
        // SAFETY: reads this thread's last-error value.
        return unsafe { GetLastError() } == ERROR_ACCESS_DENIED;
    }
    let mut code = 0u32;
    let mut times = [FILETIME::default(); 4];
    // SAFETY: `handle` is open; each pointer is a live local of the declared type.
    let running = unsafe { GetExitCodeProcess(handle, &mut code) } != 0 && code == STILL_ACTIVE;
    // SAFETY: as above; four distinct FILETIME outputs.
    let timed = unsafe {
        let [created, exited, kernel, user] = &mut times;
        GetProcessTimes(handle, created, exited, kernel, user)
    } != 0;
    // SAFETY: closes the handle opened above exactly once.
    unsafe { CloseHandle(handle) };
    let ticks = (u64::from(times[0].dwHighDateTime) << 32) | u64::from(times[0].dwLowDateTime);
    let started = (ticks / 10_000_000).saturating_sub(11_644_473_600);
    running && (!timed || started <= since.saturating_add(2))
}
#[cfg(all(not(windows), target_os = "linux"))]
pub(super) fn process_alive(pid: u32, _since: u64) -> bool {
    Path::new("/proc").join(pid.to_string()).exists()
}
#[cfg(all(unix, not(target_os = "linux")))]
pub(super) fn process_alive(pid: u32, _since: u64) -> bool {
    // No /proc: ask `ps`, once per run left "Stacking" at start.
    std::process::Command::new("ps")
        .args(["-p", &pid.to_string()])
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map_or(true, |status| status.success())
}
#[cfg(not(any(windows, unix)))]
pub(super) fn process_alive(_pid: u32, _since: u64) -> bool {
    true
}

/// When a stack's photographs were written, in Unix seconds: the newest
/// modification time the catalog recorded for them (no I/O). `None` when the
/// recipe records none.
pub(crate) fn recorded_capture(draft: &StackDraft) -> Option<u64> {
    draft
        .sources
        .iter()
        .filter_map(|s| s.modified_ns)
        .max()
        .map(|ns| (ns / 1_000_000_000) as u64)
        .filter(|&seconds| seconds > 0)
}

/// `Catalog::sources_present` for a recipe already cloned off the UI thread.
pub(crate) fn sources_state(draft: &StackDraft) -> SourcesState {
    if draft.sources.is_empty() {
        return if draft.source.is_dir() {
            SourcesState::Unrecorded
        } else {
            SourcesState::Missing
        };
    }
    let mut folders: HashMap<&Path, HashSet<&OsStr>> = HashMap::new();
    for identity in &draft.sources {
        if let (Some(folder), Some(name)) = (identity.path.parent(), identity.path.file_name()) {
            folders.entry(folder).or_default().insert(name);
        }
    }
    let expected: usize = folders.values().map(HashSet::len).sum();
    let mut found = 0;
    let mut listed = false;
    for (folder, names) in &folders {
        let Ok(entries) = std::fs::read_dir(folder) else {
            continue;
        };
        listed = true;
        found += entries
            .flatten()
            .filter(|entry| {
                names.contains(entry.file_name().as_os_str())
                    && entry.file_type().is_ok_and(|kind| !kind.is_dir())
            })
            .count();
    }
    if found == expected {
        SourcesState::Present
    } else if !listed {
        SourcesState::Missing
    } else {
        SourcesState::Partial { found, expected }
    }
}

/// The first format-2 save over a format-1 file keeps its exact bytes as
/// `<stem>.v1-backup-<unix>.json` beside it, read back and parsed before the
/// catalog is replaced. Any failure removes the partial copy and saves nothing.
pub(super) fn write_legacy_backup(path: &Path, original: &[u8]) -> anyhow::Result<PathBuf> {
    let parent = path
        .parent()
        .ok_or_else(|| anyhow::anyhow!("Projects path has no parent"))?;
    let stem = path
        .file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "projects".into());
    let unix = timestamp();
    for attempt in 0..64u32 {
        let name = if attempt == 0 {
            format!("{stem}.v1-backup-{unix}.json")
        } else {
            format!("{stem}.v1-backup-{unix}-{attempt}.json")
        };
        let backup = parent.join(name);
        let mut file = match std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&backup)
        {
            Ok(file) => file,
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => {
                return Err(anyhow::anyhow!(
                    "Backing up Projects before the format {CATALOG_FORMAT} upgrade: {error}; nothing was saved"
                ));
            }
        };
        let written = file
            .write_all(original)
            .and_then(|()| file.sync_all())
            .map_err(anyhow::Error::from);
        drop(file);
        if let Err(error) = written.and_then(|()| verify_legacy_backup(&backup, original)) {
            let _ = std::fs::remove_file(&backup);
            return Err(anyhow::anyhow!(
                "Backing up Projects before the format {CATALOG_FORMAT} upgrade: {error:#}; nothing was saved"
            ));
        }
        return Ok(backup);
    }
    anyhow::bail!(
        "Could not name a Projects backup beside {}; nothing was saved",
        crate::display_path::display_path(path)
    )
}
fn verify_legacy_backup(backup: &Path, original: &[u8]) -> anyhow::Result<()> {
    let bytes = read_catalog_bytes(backup, MAX_CATALOG_BYTES)?;
    anyhow::ensure!(
        bytes == original,
        "the backup does not match the library it copies"
    );
    let catalog: Catalog = serde_json::from_slice(&bytes)?;
    anyhow::ensure!(
        catalog.format < CATALOG_FORMAT,
        "the backup is not a format-1 library"
    );
    catalog.validate()
}

/// A run's recorded status, read leniently: older builds wrote "Rendering".
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) enum RunState {
    Stacking,
    Saved,
    Cancelled,
    Failed,
    Interrupted,
    Unknown,
}
impl RunState {
    pub(crate) fn of(status: &str) -> Self {
        match status {
            "Stacking" | "Rendering" => Self::Stacking,
            "Saved" => Self::Saved,
            "Cancelled" => Self::Cancelled,
            "Failed" => Self::Failed,
            INTERRUPTED => Self::Interrupted,
            _ => Self::Unknown,
        }
    }
}

/// One lifecycle step, in the stations' four states. Ordered so that the
/// strongest state across a subject's stacks is the maximum.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub(crate) enum StepState {
    #[default]
    NotYet,
    NeedsLook,
    Running,
    Done,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) enum NextStep {
    /// Not stacked yet.
    Stack,
    /// The latest render failed, was cancelled or was interrupted.
    Check,
    /// A render is running.
    Wait,
    Develop,
    Export,
    Done,
}

#[derive(Clone, Copy, Debug, Default)]
struct Usage {
    versions: usize,
    exports: usize,
    last: u64,
}
impl Usage {
    fn version(&mut self, created: u64) {
        self.versions += 1;
        self.last = self.last.max(created);
    }
    fn export(&mut self, created: u64) {
        self.exports += 1;
        self.last = self.last.max(created);
    }
}

/// Where a stack stands: captured, stacked, developed, exported.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct StackLifecycle {
    pub captured: StepState,
    pub stacked: StepState,
    pub developed: StepState,
    pub exported: StepState,
    /// The newest render's state.
    pub latest: Option<RunState>,
    pub renders: usize,
    pub saved_renders: usize,
    pub versions: usize,
    pub exports: usize,
    /// Newest render, version or export, in Unix seconds; 0 when none.
    pub last_activity: u64,
    /// When its photographs were written (`recorded_capture`); 0 when the
    /// catalog records no time.
    pub captured_at: u64,
}
impl StackLifecycle {
    fn from_parts(runs: &[&Run], usage: Usage, captured_at: u64) -> Self {
        let latest = runs.last().map(|run| RunState::of(&run.status));
        let stacked = match latest {
            None => StepState::NotYet,
            Some(RunState::Stacking) => StepState::Running,
            Some(RunState::Saved) => StepState::Done,
            Some(_) => StepState::NeedsLook,
        };
        let done = |count: usize| {
            if count > 0 {
                StepState::Done
            } else {
                StepState::NotYet
            }
        };
        Self {
            captured: StepState::Done,
            stacked,
            developed: done(usage.versions),
            exported: done(usage.exports),
            latest,
            renders: runs.len(),
            saved_renders: runs
                .iter()
                .filter(|run| RunState::of(&run.status) == RunState::Saved)
                .count(),
            versions: usage.versions,
            exports: usage.exports,
            last_activity: runs
                .iter()
                .map(|run| run.created)
                .max()
                .unwrap_or(0)
                .max(usage.last),
            captured_at,
        }
    }
    /// The stack's own newest date: activity, else its capture; 0 unknown.
    pub(crate) fn last_dated(&self) -> u64 {
        self.last_activity.max(self.captured_at)
    }
    pub(crate) fn steps(&self) -> [StepState; 4] {
        [self.captured, self.stacked, self.developed, self.exported]
    }
    /// "Needs a look": the latest render failed, was cancelled or interrupted.
    pub(crate) fn needs_a_look(&self) -> bool {
        self.stacked == StepState::NeedsLook
    }
    pub(crate) fn next_step(&self) -> NextStep {
        match self.stacked {
            StepState::NotYet => NextStep::Stack,
            StepState::NeedsLook => NextStep::Check,
            StepState::Running => NextStep::Wait,
            StepState::Done if self.developed != StepState::Done => NextStep::Develop,
            StepState::Done if self.exported != StepState::Done => NextStep::Export,
            StepState::Done => NextStep::Done,
        }
    }
}

/// A subject's stacks combined, for a library card and the "needs you" lists.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct SubjectSummary {
    pub stacks: usize,
    pub to_stack: usize,
    pub to_check: usize,
    pub stacking: usize,
    pub to_develop: usize,
    pub to_export: usize,
    pub exported: usize,
    pub renders: usize,
    pub versions: usize,
    pub exports: usize,
    pub last_activity: u64,
    /// The newest capture time recorded for its stacks; 0 when none.
    pub captured_at: u64,
    /// The strongest state of each step across the stacks.
    pub steps: [StepState; 4],
}
impl SubjectSummary {
    fn add(&mut self, stack: &StackLifecycle) {
        self.stacks += 1;
        match stack.next_step() {
            NextStep::Stack => self.to_stack += 1,
            NextStep::Check => self.to_check += 1,
            NextStep::Wait => self.stacking += 1,
            NextStep::Develop => self.to_develop += 1,
            NextStep::Export => self.to_export += 1,
            NextStep::Done => {}
        }
        self.exported += usize::from(stack.exported == StepState::Done);
        self.renders += stack.renders;
        self.versions += stack.versions;
        self.exports += stack.exports;
        self.last_activity = self.last_activity.max(stack.last_activity);
        self.captured_at = self.captured_at.max(stack.captured_at);
        for (step, state) in self.steps.iter_mut().zip(stack.steps()) {
            *step = (*step).max(state);
        }
    }
    pub(crate) fn next_step(&self) -> NextStep {
        if self.to_check > 0 {
            NextStep::Check
        } else if self.stacking > 0 {
            NextStep::Wait
        } else if self.to_stack > 0 || self.stacks == 0 {
            NextStep::Stack
        } else if self.to_develop > 0 {
            NextStep::Develop
        } else if self.to_export > 0 {
            NextStep::Export
        } else {
            NextStep::Done
        }
    }
}

#[derive(Clone, Debug, Default)]
pub(crate) struct LibraryIndex {
    pub stacks: HashMap<NodeId, StackLifecycle>,
    pub subjects: HashMap<NodeId, SubjectSummary>,
}

/// Whether a stack's sources are where the catalog records them.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum SourcesState {
    Present,
    /// No recorded source folder can be listed: "sources moved".
    Missing,
    Partial {
        found: usize,
        expected: usize,
    },
    /// An old record without a source list; its folder exists.
    Unrecorded,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct RelocateReport {
    pub directory: PathBuf,
    /// Recorded sources re-pointed in the stack's recipe.
    pub sources: usize,
    /// Renders whose source records were re-pointed.
    pub runs: usize,
    /// Sources whose modification time differs at the new place.
    pub modified_changed: usize,
}

/// Why Locate refused a folder. Nothing was changed.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct RelocateMismatch {
    pub directory: PathBuf,
    pub missing: Vec<String>,
    /// Name, recorded bytes, found bytes.
    pub resized: Vec<(String, u64, u64)>,
    /// Frames the folder holds that the stack does not record.
    pub unexpected: Vec<String>,
}
impl RelocateMismatch {
    fn is_empty(&self) -> bool {
        self.missing.is_empty() && self.resized.is_empty() && self.unexpected.is_empty()
    }
}
impl std::fmt::Display for RelocateMismatch {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        fn some(names: &[String]) -> String {
            let shown: Vec<&str> = names.iter().take(3).map(String::as_str).collect();
            let more = names.len().saturating_sub(shown.len());
            if more > 0 {
                format!("{} and {more} more", shown.join(", "))
            } else {
                shown.join(", ")
            }
        }
        write!(
            f,
            "{} does not hold this stack's sources",
            crate::display_path::display_path(&self.directory)
        )?;
        if !self.missing.is_empty() {
            write!(
                f,
                "; {} recorded missing: {}",
                self.missing.len(),
                some(&self.missing)
            )?;
        }
        if !self.resized.is_empty() {
            let resized: Vec<String> = self
                .resized
                .iter()
                .map(|(name, recorded, found)| format!("{name} ({recorded} → {found} bytes)"))
                .collect();
            write!(f, "; {} differ in size: {}", resized.len(), some(&resized))?;
        }
        if !self.unexpected.is_empty() {
            write!(
                f,
                "; {} not recorded: {}",
                self.unexpected.len(),
                some(&self.unexpected)
            )?;
        }
        write!(f, ". Nothing was changed")
    }
}
impl std::error::Error for RelocateMismatch {}
