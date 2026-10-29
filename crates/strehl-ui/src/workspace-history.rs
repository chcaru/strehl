//! Virtual project organization and retained run evidence. Renaming or moving
//! an object changes only the catalog; source photographs and outputs stay put.
use crate::{
    jobs::{self, RenderSettings, Task},
    pipeline::PipelineProgress,
    workspace_layout::WorkspaceLayout,
};
use serde::{Deserialize, Serialize};
use std::{
    cell::RefCell,
    collections::{BTreeMap, HashSet},
    io::{Read, Write},
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};
#[path = "photo-history.rs"]
pub(crate) mod photographs;
pub(crate) use photographs::{PhotoExport, PhotoOwner, PhotoVersion};

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) struct SourceIdentity {
    pub path: PathBuf,
    pub bytes: u64,
    pub modified_ns: Option<u128>,
}
pub(crate) fn source_identities(stack: &jobs::StackScan) -> Vec<SourceIdentity> {
    stack
        .frames
        .iter()
        .map(|frame| SourceIdentity {
            path: frame.path.clone(),
            bytes: frame.bytes,
            modified_ns: std::fs::metadata(&frame.path)
                .ok()
                .and_then(|meta| meta.modified().ok())
                .and_then(|time| time.duration_since(UNIX_EPOCH).ok())
                .map(|time| time.as_nanos()),
        })
        .collect()
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct Run {
    pub directory: PathBuf,
    pub source: PathBuf,
    pub output: PathBuf,
    pub log: PathBuf,
    pub label: String,
    pub created: u64,
    pub status: String,
    pub frames: usize,
    #[serde(default)]
    pub sources: Vec<SourceIdentity>,
    pub settings: RenderSettings,
    pub exposure: Option<f32>,
    pub gate: Option<f32>,
    pub workers: usize,
    #[serde(default)]
    pub pinned: bool,
    #[serde(default)]
    pub imported: Option<crate::session_import::ImportedSession>,
}
impl Run {
    pub(crate) fn output_directory(&self) -> PathBuf {
        if self.imported.is_some() {
            self.directory.clone()
        } else {
            self.directory.join("session-output")
        }
    }
    pub(crate) fn owns_output(&self, output: &Path) -> bool {
        self.output == output
            || self.settings.session.as_ref().is_some_and(|session| {
                crate::session_workspace::output_prefix(session.manifest.mode).is_some_and(
                    |prefix| {
                        (0..session.manifest.passes.len()).any(|index| {
                            self.output_directory()
                                .join(format!("{prefix}-{:02}", index + 1))
                                .join("photograph.tiff")
                                == output
                        })
                    },
                )
            })
    }
    pub fn matches_scan(&self, stack: &jobs::StackScan) -> bool {
        !self.sources.is_empty()
            && self.frames
                == self
                    .settings
                    .frame_limit
                    .map_or(stack.frames.len(), |limit| limit.min(stack.frames.len()))
            && self.sources.len() == stack.frames.len()
            && self
                .sources
                .iter()
                .zip(source_identities(stack))
                .all(|(a, b)| {
                    a.path == b.path && a.bytes == b.bytes && a.modified_ns == b.modified_ns
                })
    }
}
pub(crate) type NodeId = u64;
const MAX_CATALOG_BYTES: usize = 32 * 1024 * 1024;
const MAX_PROJECT_NODES: usize = 16_384;
const MAX_TREE_DEPTH: usize = 64;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub(crate) enum NodeKind {
    Project,
    Folder,
    Stack,
}

/// The next render's editable recipe. A completed Run retains its own copy,
/// so changing this recipe never changes the explanation of an older TIFF.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct StackDraft {
    pub source: PathBuf,
    #[serde(default)]
    pub sources: Vec<SourceIdentity>,
    pub settings: RenderSettings,
    pub exposure: Option<f32>,
    pub gate: Option<f32>,
    pub workers: usize,
}
impl StackDraft {
    pub fn from_run(run: &Run) -> Self {
        Self {
            source: run.source.clone(),
            sources: run.sources.clone(),
            settings: run.settings.clone(),
            exposure: run.exposure,
            gate: run.gate,
            workers: run.workers,
        }
    }
    pub fn from_scan(
        stack: &jobs::StackScan,
        settings: RenderSettings,
        exposure: Option<f32>,
        gate: Option<f32>,
        workers: usize,
    ) -> Self {
        Self {
            source: stack.directory.clone(),
            sources: source_identities(stack),
            settings,
            exposure,
            gate,
            workers,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct ProjectNode {
    pub id: NodeId,
    pub parent: Option<NodeId>,
    pub name: String,
    pub kind: NodeKind,
    #[serde(default)]
    pub notes: String,
    #[serde(default = "expanded_by_default")]
    pub expanded: bool,
    #[serde(default)]
    pub stack: Option<StackDraft>,
    /// Oldest to newest. The directory is the revision identity, never its name.
    #[serde(default)]
    pub revisions: Vec<PathBuf>,
}
fn expanded_by_default() -> bool {
    true
}

#[derive(Default, Serialize, Deserialize)]
#[serde(default)]
pub(crate) struct Catalog {
    pub layout: WorkspaceLayout,
    pub runs: Vec<Run>,
    pub nodes: Vec<ProjectNode>,
    pub selected: Option<NodeId>,
    pub photo_versions: Vec<PhotoVersion>,
    pub photo_exports: Vec<PhotoExport>,
    /// Explicit alternate destinations, keyed by the photograph, not a stack's RAW folder.
    pub export_directories: BTreeMap<PathBuf, PathBuf>,
    next_node_id: NodeId,
    #[serde(skip)]
    pub path: Option<PathBuf>,
    #[serde(skip)]
    pub load_error: Option<String>,
    #[serde(skip)]
    disk_bytes: RefCell<Option<Vec<u8>>>,
}
impl Catalog {
    pub fn load(path: Option<PathBuf>) -> Self {
        let mut load_error = None;
        let mut disk_bytes = None;
        let mut catalog = path
            .as_deref()
            .and_then(|p| {
                // Keep the project library separate from older desktops: their
                // legacy workspace saves do not know about virtual folders.
                // Fallback is only for a missing new file, never a damaged one.
                let source = if !p.exists() && p.file_name().is_some_and(|n| n == "projects.json") {
                    p.with_file_name("workspace.json")
                } else {
                    p.to_path_buf()
                };
                if !source.exists() {
                    return None;
                }
                match read_catalog_bytes(&source, MAX_CATALOG_BYTES).and_then(|bytes| {
                    let mut catalog: Self = serde_json::from_slice(&bytes)?;
                    catalog.validate()?;
                    catalog.migrate_runs()?;
                    if source == p {
                        disk_bytes = Some(bytes);
                    }
                    Ok(catalog)
                }) {
                    Ok(catalog) => Some(catalog),
                    Err(error) => {
                        load_error = Some(format!(
                            "Projects could not be read; original retained: {error}"
                        ));
                        None
                    }
                }
            })
            .unwrap_or_default();
        catalog.path = path;
        catalog.load_error = load_error;
        catalog.disk_bytes = RefCell::new(disk_bytes);
        catalog.layout.sanitize();
        catalog
    }
    pub fn save(&self) -> anyhow::Result<()> {
        self.save_with_limit(MAX_CATALOG_BYTES)
    }
    fn save_with_limit(&self, limit: usize) -> anyhow::Result<()> {
        let Some(path) = &self.path else {
            return Ok(());
        };
        anyhow::ensure!(
            self.load_error.is_none(),
            "Unreadable workspace is preserved; choose a new catalog before saving"
        );
        self.validate()?;
        let parent = path
            .parent()
            .ok_or_else(|| anyhow::anyhow!("Catalog has no parent"))?;
        std::fs::create_dir_all(parent)?;
        let lock = std::fs::OpenOptions::new()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .open(path.with_extension("lock"))?;
        lock.try_lock()
            .map_err(|e| anyhow::anyhow!("Another Strehl window is saving Projects; retry: {e}"))?;
        let actual = if path.exists() {
            Some(read_catalog_bytes(path, MAX_CATALOG_BYTES)?)
        } else {
            None
        };
        anyhow::ensure!(
            actual.as_ref() == self.disk_bytes.borrow().as_ref(),
            "Projects changed in another window. Your changes remain in this window; reload before replacing the saved library"
        );
        let temporary = path.with_extension(format!("{}.tmp", std::process::id()));
        let bytes = serde_json::to_vec_pretty(self)?;
        anyhow::ensure!(bytes.len() <= limit, "Workspace exceeds size limit");
        let result = (|| {
            let mut file = std::fs::File::create(&temporary)?;
            file.write_all(&bytes)?;
            file.sync_all()?;
            drop(file);
            // rename replaces the destination atomically on the supported platforms.
            std::fs::rename(&temporary, path)?;
            anyhow::Ok(())
        })();
        if result.is_err() {
            let _ = std::fs::remove_file(&temporary);
        }
        result?;
        *self.disk_bytes.borrow_mut() = Some(bytes);
        Ok(())
    }
    /// Explicit conflict recovery preserves this window before loading another
    /// window's library. Immutable recipe payloads are never removed.
    pub(crate) fn recover_and_reload(&mut self) -> anyhow::Result<PathBuf> {
        let path = self
            .path
            .clone()
            .ok_or_else(|| anyhow::anyhow!("No project storage folder is available"))?;
        let parent = path
            .parent()
            .ok_or_else(|| anyhow::anyhow!("Projects path has no parent"))?;
        std::fs::create_dir_all(parent)?;
        let bytes = serde_json::to_vec_pretty(self)?;
        anyhow::ensure!(
            bytes.len() <= MAX_CATALOG_BYTES,
            "Projects recovery exceeds size limit"
        );
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).map_err(|e| anyhow::anyhow!("Recovery identity: {e}"))?;
        let suffix = nonce.iter().map(|b| format!("{b:02x}")).collect::<String>();
        let recovery = parent.join(format!("projects-recovery-{suffix}.json"));
        let mut file = std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&recovery)?;
        file.write_all(&bytes)?;
        file.sync_all()?;
        drop(file);
        let loaded = Self::load(Some(path));
        anyhow::ensure!(
            loaded.load_error.is_none(),
            "Current Projects cannot be read; your recovery is saved at {}",
            recovery.display()
        );
        *self = loaded;
        Ok(recovery)
    }

    /// Legacy recent-run insertion. Revisions attached to a project are always
    /// retained; the old 128-entry cap applies only to unattached recent runs.
    pub fn add(&mut self, run: Run) {
        self.runs.retain(|old| old.directory != run.directory);
        self.runs.insert(0, run);
        let linked: HashSet<&Path> = self
            .nodes
            .iter()
            .flat_map(|n| n.revisions.iter().map(PathBuf::as_path))
            .collect();
        while self.runs.len() > 128 {
            let disposable = |(index, run): &(usize, &Run)| {
                *index > 0 && !linked.contains(run.directory.as_path())
            };
            let index = self
                .runs
                .iter()
                .enumerate()
                .rfind(|entry| disposable(entry) && !entry.1.pinned)
                .or_else(|| self.runs.iter().enumerate().rfind(disposable))
                .map(|(index, _)| index);
            if let Some(index) = index {
                self.runs.remove(index);
            } else {
                break;
            }
        }
    }
    pub fn finish(&mut self, directory: &Path, status: &str) {
        if let Some(run) = self.runs.iter_mut().find(|r| r.directory == directory) {
            run.status = status.into();
        }
    }
    pub fn node(&self, id: NodeId) -> Option<&ProjectNode> {
        self.nodes.iter().find(|node| node.id == id)
    }
    pub fn node_mut(&mut self, id: NodeId) -> Option<&mut ProjectNode> {
        self.nodes.iter_mut().find(|node| node.id == id)
    }
    pub fn selected_container(&self) -> Option<NodeId> {
        let node = self.node(self.selected?)?;
        if node.kind == NodeKind::Stack {
            node.parent
        } else {
            Some(node.id)
        }
    }
    pub fn stack_for_run(&self, directory: &Path) -> Option<NodeId> {
        self.nodes
            .iter()
            .find(|node| {
                node.kind == NodeKind::Stack && node.revisions.iter().any(|r| r == directory)
            })
            .map(|n| n.id)
    }
    pub fn latest_run(&self, id: NodeId) -> Option<&Run> {
        let directory = self.node(id)?.revisions.last()?;
        self.runs.iter().find(|run| &run.directory == directory)
    }
    pub fn photo_owner(&self, output: &Path) -> PhotoOwner {
        let run = self
            .runs
            .iter()
            .find(|run| run.owns_output(output))
            .and_then(|run| {
                self.stack_for_run(&run.directory)
                    .map(|stack| (stack, run.directory.clone()))
            });
        PhotoOwner {
            stack: run.as_ref().map(|r| r.0),
            run: run.map(|r| r.1),
            output: output.to_path_buf(),
        }
    }
    pub fn history_root(&self) -> Option<PathBuf> {
        self.path
            .as_ref()?
            .parent()
            .map(|p| p.join("photo-history"))
    }
    pub fn add_photo_version(&mut self, version: PhotoVersion) -> anyhow::Result<()> {
        self.validate_photo_owner(&version.owner)?;
        anyhow::ensure!(
            photographs::valid_id(&version.id),
            "Invalid version identity"
        );
        photographs::checked_name(&version.name)?;
        if let Some(saved) = self.photo_versions.iter().find(|v| v.id == version.id) {
            anyhow::ensure!(
                saved == &version,
                "A version identity cannot acquire different photo edits"
            );
            return Ok(());
        }
        anyhow::ensure!(
            self.photo_versions.len() < 8192
                && self
                    .photo_versions
                    .iter()
                    .filter(|v| v.owner.output == version.owner.output)
                    .count()
                    < 256,
            "Photograph version limit reached"
        );
        self.photo_versions.push(version);
        Ok(())
    }
    pub fn rename_photo_version(&mut self, id: &str, name: &str) -> anyhow::Result<()> {
        let name = photographs::checked_name(name)?;
        self.photo_versions
            .iter_mut()
            .find(|v| v.id == id)
            .ok_or_else(|| anyhow::anyhow!("Version no longer exists"))?
            .name = name;
        Ok(())
    }
    pub fn add_photo_export(&mut self, export: PhotoExport) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.photo_versions.iter().any(|v| v.id == export.version),
            "Export version is missing"
        );
        anyhow::ensure!(photographs::valid_id(&export.id), "Invalid export identity");
        if let Some(saved) = self.photo_exports.iter().find(|e| e.id == export.id) {
            anyhow::ensure!(saved == &export, "An export identity cannot change");
            return Ok(());
        }
        anyhow::ensure!(
            self.photo_exports.len() < 16384,
            "Export history limit reached"
        );
        export.settings.validate()?;
        self.photo_exports.push(export);
        Ok(())
    }
    fn validate_photo_owner(&self, owner: &PhotoOwner) -> anyhow::Result<()> {
        anyhow::ensure!(
            !owner.output.as_os_str().is_empty(),
            "Photograph path is empty"
        );
        match (owner.stack, owner.run.as_ref()) {
            (Some(stack), Some(directory)) => anyhow::ensure!(
                self.stack_for_run(directory) == Some(stack)
                    && self
                        .runs
                        .iter()
                        .any(|r| &r.directory == directory && r.owns_output(&owner.output)),
                "Photograph version belongs to a different stack or render"
            ),
            (None, None) => anyhow::ensure!(
                self.photo_owner(&owner.output).stack.is_none(),
                "Captured photograph is missing its stack identity"
            ),
            _ => anyhow::bail!("Photograph stack and render identity must agree"),
        }
        Ok(())
    }
    pub fn create_project(&mut self, name: &str) -> anyhow::Result<NodeId> {
        self.insert_node(None, name, NodeKind::Project, None)
    }
    pub fn create_folder(&mut self, parent: NodeId, name: &str) -> anyhow::Result<NodeId> {
        self.check_container(parent)?;
        self.insert_node(Some(parent), name, NodeKind::Folder, None)
    }
    pub fn create_stack(
        &mut self,
        parent: NodeId,
        name: &str,
        draft: StackDraft,
    ) -> anyhow::Result<NodeId> {
        self.check_container(parent)?;
        self.insert_node(Some(parent), name, NodeKind::Stack, Some(draft))
    }
    pub fn rename(&mut self, id: NodeId, name: &str) -> anyhow::Result<()> {
        let name = checked_name(name)?;
        let node = self
            .node_mut(id)
            .ok_or_else(|| anyhow::anyhow!("Object no longer exists"))?;
        node.name = name;
        Ok(())
    }
    pub fn move_node(&mut self, id: NodeId, parent: Option<NodeId>) -> anyhow::Result<()> {
        self.can_move(id, parent)?;
        self.node_mut(id).unwrap().parent = parent;
        if let Some(parent) = parent {
            self.node_mut(parent).unwrap().expanded = true;
        }
        Ok(())
    }
    pub fn can_move(&self, id: NodeId, parent: Option<NodeId>) -> anyhow::Result<()> {
        let node = self
            .node(id)
            .ok_or_else(|| anyhow::anyhow!("Object no longer exists"))?;
        if node.kind == NodeKind::Project {
            anyhow::ensure!(parent.is_none(), "Projects remain at the top level");
            return Ok(());
        }
        let parent = parent.ok_or_else(|| anyhow::anyhow!("Choose a project or folder"))?;
        self.check_container(parent)?;
        let mut at = Some(parent);
        let mut depth = 0;
        while let Some(ancestor) = at {
            anyhow::ensure!(
                ancestor != id,
                "A folder cannot contain itself or its parent"
            );
            depth += 1;
            anyhow::ensure!(depth < MAX_TREE_DEPTH, "Folder nesting limit reached");
            at = self.node(ancestor).and_then(|n| n.parent);
        }
        // Moving a populated branch must keep every descendant within the same
        // depth limit, rather than accepting a tree the next load would reject.
        for child in &self.nodes {
            let mut relative = 0;
            let mut at = Some(child.id);
            while let Some(ancestor) = at {
                if ancestor == id {
                    anyhow::ensure!(
                        depth + relative < MAX_TREE_DEPTH,
                        "Folder nesting limit reached"
                    );
                    break;
                }
                relative += 1;
                anyhow::ensure!(relative <= MAX_TREE_DEPTH, "Invalid folder tree");
                at = self.node(ancestor).and_then(|n| n.parent);
            }
        }
        Ok(())
    }
    pub fn update_stack_draft(&mut self, id: NodeId, draft: StackDraft) -> anyhow::Result<()> {
        let node = self
            .node_mut(id)
            .ok_or_else(|| anyhow::anyhow!("Stack no longer exists"))?;
        anyhow::ensure!(node.kind == NodeKind::Stack, "Choose a stack");
        node.stack = Some(draft);
        Ok(())
    }
    pub(crate) fn import_completed_run(
        &mut self,
        parent: Option<NodeId>,
        run: Run,
    ) -> anyhow::Result<NodeId> {
        anyhow::ensure!(
            run.imported.is_some() && run.status == "Saved",
            "Only verified completed imports enter this path"
        );
        let rollback = (
            self.nodes.clone(),
            self.runs.clone(),
            self.next_node_id,
            self.selected,
        );
        let result = (|| {
            let parent = match parent {
                Some(id) => {
                    self.check_container(id)?;
                    id
                }
                None => self.create_project("Imported CLI sessions")?,
            };
            let id = self.create_stack(
                parent,
                &run.label.chars().take(120).collect::<String>(),
                StackDraft::from_run(&run),
            )?;
            self.add_revision(id, run)?;
            self.selected = Some(id);
            Ok(id)
        })();
        if result.is_err() {
            (self.nodes, self.runs, self.next_node_id, self.selected) = rollback;
        }
        result
    }
    pub fn add_revision(&mut self, id: NodeId, run: Run) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.node(id).is_some_and(|n| n.kind == NodeKind::Stack),
            "Choose a stack"
        );
        anyhow::ensure!(
            self.stack_for_run(&run.directory)
                .is_none_or(|owner| owner == id),
            "This revision belongs to another stack"
        );
        let existing = self
            .runs
            .iter()
            .find(|saved| saved.directory == run.directory);
        if let Some(saved) = existing {
            anyhow::ensure!(
                saved.source == run.source
                    && saved.output == run.output
                    && saved.log == run.log
                    && saved.created == run.created
                    && saved.frames == run.frames
                    && saved.sources == run.sources
                    && saved.settings == run.settings
                    && saved.exposure == run.exposure
                    && saved.gate == run.gate
                    && saved.workers == run.workers
                    && saved.imported == run.imported,
                "A saved revision cannot acquire a different recipe or source"
            );
        }
        let already_saved = existing.is_some();
        let node = self.node_mut(id).unwrap();
        if !node.revisions.contains(&run.directory) {
            node.revisions.push(run.directory.clone());
        }
        // An idempotent delivery must not erase a user's title/pin or roll a
        // completed status back to Rendering. Finish updates status separately.
        if !already_saved {
            self.add(run);
        }
        Ok(())
    }
    /// A readable breadcrumb also makes duplicate names safe in the move menu.
    pub fn breadcrumb(&self, id: NodeId) -> String {
        let mut names = Vec::new();
        let mut at = Some(id);
        while let Some(id) = at {
            let Some(node) = self.node(id) else {
                break;
            };
            names.push(node.name.as_str());
            if names.len() >= MAX_TREE_DEPTH {
                break;
            }
            at = node.parent;
        }
        names.reverse();
        names.join(" / ")
    }
    fn check_container(&self, id: NodeId) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.node(id).is_some_and(|n| n.kind != NodeKind::Stack),
            "Choose a project or folder"
        );
        Ok(())
    }
    fn insert_node(
        &mut self,
        parent: Option<NodeId>,
        name: &str,
        kind: NodeKind,
        stack: Option<StackDraft>,
    ) -> anyhow::Result<NodeId> {
        anyhow::ensure!(
            self.nodes.len() < MAX_PROJECT_NODES,
            "Workspace object limit reached"
        );
        let name = checked_name(name)?;
        let max_id = self.nodes.iter().map(|n| n.id).max().unwrap_or(0);
        let id = self
            .next_node_id
            .max(max_id)
            .checked_add(1)
            .ok_or_else(|| anyhow::anyhow!("Object identity limit reached"))?;
        if let Some(parent) = parent {
            let mut depth = 1;
            let mut at = Some(parent);
            while let Some(ancestor) = at {
                depth += 1;
                anyhow::ensure!(depth <= MAX_TREE_DEPTH, "Folder nesting limit reached");
                at = self.node(ancestor).and_then(|n| n.parent);
            }
        }
        self.next_node_id = id;
        self.nodes.push(ProjectNode {
            id,
            parent,
            name,
            kind,
            notes: String::new(),
            expanded: true,
            stack,
            revisions: Vec::new(),
        });
        if let Some(parent) = parent {
            self.node_mut(parent).unwrap().expanded = true;
        }
        self.selected = Some(id);
        Ok(id)
    }
    fn migrate_runs(&mut self) -> anyhow::Result<()> {
        let unlinked: Vec<Run> = self
            .runs
            .iter()
            .rev()
            .filter(|run| self.stack_for_run(&run.directory).is_none())
            .cloned()
            .collect();
        if unlinked.is_empty() {
            return Ok(());
        }
        let project = self.create_project("Imported stacks")?;
        for run in unlinked {
            let stack = self
                .nodes
                .iter()
                .find(|node| {
                    node.parent == Some(project)
                        && node.stack.as_ref().is_some_and(|s| s.source == run.source)
                })
                .map(|n| n.id);
            let draft = StackDraft::from_run(&run);
            let id = match stack {
                Some(id) => {
                    self.update_stack_draft(id, draft)?;
                    id
                }
                None => {
                    let name = run
                        .source
                        .file_name()
                        .and_then(|s| s.to_str())
                        .filter(|s| !s.trim().is_empty())
                        .unwrap_or("Capture stack");
                    self.create_stack(project, &name.chars().take(160).collect::<String>(), draft)?
                }
            };
            self.node_mut(id)
                .unwrap()
                .revisions
                .push(run.directory.clone());
        }
        self.selected = Some(project);
        Ok(())
    }
    fn validate(&self) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.nodes.len() <= MAX_PROJECT_NODES,
            "Workspace object limit reached"
        );
        let mut ids = HashSet::new();
        let mut revisions = HashSet::new();
        let mut runs = HashSet::new();
        for run in &self.runs {
            anyhow::ensure!(
                runs.insert(run.directory.as_path()),
                "Duplicate run identity"
            );
        }
        for node in &self.nodes {
            anyhow::ensure!(
                node.id != 0 && ids.insert(node.id),
                "Duplicate or invalid object identity"
            );
            checked_name(&node.name)?;
            anyhow::ensure!(
                (node.kind == NodeKind::Stack) == node.stack.is_some(),
                "Invalid stack recipe"
            );
            anyhow::ensure!(
                node.kind == NodeKind::Stack || node.revisions.is_empty(),
                "Only stacks contain render revisions"
            );
            if node.kind == NodeKind::Project {
                anyhow::ensure!(node.parent.is_none(), "Project must be at top level");
            } else {
                self.check_container(
                    node.parent
                        .ok_or_else(|| anyhow::anyhow!("Object has no project"))?,
                )?;
            }
            let mut visited = HashSet::new();
            let mut at = Some(node.id);
            while let Some(ancestor) = at {
                anyhow::ensure!(visited.insert(ancestor), "Folder cycle detected");
                anyhow::ensure!(
                    visited.len() <= MAX_TREE_DEPTH,
                    "Folder nesting limit reached"
                );
                at = self
                    .node(ancestor)
                    .ok_or_else(|| anyhow::anyhow!("Folder parent missing"))?
                    .parent;
            }
            for revision in &node.revisions {
                anyhow::ensure!(runs.contains(revision.as_path()), "Revision record missing");
                anyhow::ensure!(
                    revisions.insert(revision.as_path()),
                    "Revision has multiple owners"
                );
            }
        }
        anyhow::ensure!(
            self.selected.is_none_or(|id| self.node(id).is_some()),
            "Selected object missing"
        );
        anyhow::ensure!(
            self.photo_versions.len() <= 8192
                && self.photo_exports.len() <= 16384
                && self.export_directories.len() <= 8192,
            "Photograph history exceeds its limit"
        );
        let mut version_ids = HashSet::new();
        let mut counts = std::collections::HashMap::<&Path, usize>::new();
        for version in &self.photo_versions {
            self.validate_photo_owner(&version.owner)?;
            photographs::checked_name(&version.name)?;
            anyhow::ensure!(
                photographs::valid_id(&version.id)
                    && version_ids.insert(&version.id)
                    && version.loaded_sha256.len() == 64
                    && version.decoded_source.sha256.len() == 64
                    && version.photo.sha256.len() == 64
                    && version.photo.sha256.bytes().all(|b| b.is_ascii_hexdigit())
                    && version.photo.dimensions.iter().all(|n| *n > 0),
                "Invalid photograph version record"
            );
            let count = counts.entry(&version.owner.output).or_default();
            *count += 1;
            anyhow::ensure!(*count <= 256, "Photograph version limit reached");
        }
        let mut export_ids = HashSet::new();
        for export in &self.photo_exports {
            anyhow::ensure!(
                photographs::valid_id(&export.id)
                    && export_ids.insert(&export.id)
                    && version_ids.contains(&export.version)
                    && !export.path.as_os_str().is_empty()
                    && export.sha256.len() == 64
                    && export.sha256.bytes().all(|b| b.is_ascii_hexdigit()),
                "Invalid photograph export record"
            );
            export.settings.validate()?;
        }
        Ok(())
    }
}
fn read_catalog_bytes(path: &Path, limit: usize) -> anyhow::Result<Vec<u8>> {
    let file = std::fs::File::open(path)?;
    anyhow::ensure!(
        file.metadata()?.len() <= limit as u64,
        "Workspace exceeds size limit"
    );
    let mut bytes = Vec::new();
    // The extra byte also detects growth after the metadata read, without
    // reading an unbounded or concurrently replaced workspace into memory.
    file.take(limit.saturating_add(1) as u64)
        .read_to_end(&mut bytes)?;
    anyhow::ensure!(bytes.len() <= limit, "Workspace exceeds size limit");
    Ok(bytes)
}

fn checked_name(name: &str) -> anyhow::Result<String> {
    let name = name.trim();
    anyhow::ensure!(!name.is_empty(), "Give this object a name");
    anyhow::ensure!(
        name.chars().count() <= 160,
        "Keep names within 160 characters"
    );
    anyhow::ensure!(
        !name.chars().any(char::is_control),
        "Names cannot contain control characters"
    );
    Ok(name.to_owned())
}
pub(crate) fn timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
pub(crate) fn default_path() -> Option<PathBuf> {
    if cfg!(test) {
        return None;
    }
    std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("XDG_STATE_HOME").map(PathBuf::from))
        .or_else(|| std::env::var_os("HOME").map(|p| PathBuf::from(p).join(".local/state")))
        .map(|p| p.join("Strehl/projects.json"))
}
pub(crate) fn reopen(run: Run) -> Task<(Run, PipelineProgress)> {
    jobs::spawn_task("strehl-reopen", move |cancelled| {
        if let Some(provenance) = &run.imported {
            crate::session_import::verify(&run.directory, provenance, &cancelled)?;
            let mut progress = PipelineProgress::default();
            progress.mark_complete();
            return Ok((run, progress));
        }
        let mut file = std::fs::File::open(&run.log)?;
        anyhow::ensure!(
            file.metadata()?.len() <= 512 * 1024 * 1024,
            "Saved activity exceeds the replay limit"
        );
        let mut progress = PipelineProgress::default();
        let mut decoder = crate::pipeline::Utf8LogDecoder::default();
        let mut buffer = [0u8; 32768];
        loop {
            anyhow::ensure!(
                !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                "Replay cancelled"
            );
            let count = file.read(&mut buffer)?;
            progress.ingest(&decoder.decode(&buffer[..count], count == 0));
            if count == 0 {
                break;
            }
        }
        progress.finish();
        if run.status == "Saved" {
            anyhow::ensure!(
                run.output.is_file(),
                "The saved TIFF is missing: {}",
                run.output.display()
            );
            anyhow::ensure!(
                progress.output_geometry.is_some(),
                "The saved activity has no completed TIFF receipt"
            );
        }
        match run.status.as_str() {
            "Saved" => progress.mark_complete(),
            "Cancelled" => progress.mark_cancelled(),
            _ => progress.mark_failed(),
        }
        Ok((run, progress))
    })
}
#[cfg(test)]
#[path = "workspace-history-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "workspace-history-review-tests.rs"]
mod review_tests;

#[cfg(test)]
#[path = "project-catalog-tests.rs"]
mod project_tests;
