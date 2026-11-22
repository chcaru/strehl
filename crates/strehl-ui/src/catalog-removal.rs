//! Taking stacks and subjects out of the library and putting them back (undo),
//! merging subjects, and which files on disk a catalog entry owns.
//!
//! Removal is a catalog edit: a stack leaves with its renders' records, the
//! versions developed from them and those versions' exports, so the catalog
//! still validates and the next load does not bring the renders back as
//! "Imported stacks". `RemovedRecords` keeps everything that left, with its
//! place, so undo restores the catalog exactly.
//!
//! `owned_files` names, from the catalog's own records and without touching
//! the disk, the files a removed entry may delete: its render folders (job
//! folders Strehl created) and its recorded source photographs. Anything it
//! cannot attribute to the entry alone is refused with a reason. Measuring and
//! deleting is `library-delete.rs`, on a worker.
use super::subjects::{job_process, path_key};
use super::{Catalog, NodeId, NodeKind, PhotoExport, PhotoVersion, ProjectNode, Run};
use std::{
    collections::{HashMap, HashSet},
    path::{Path, PathBuf},
};

/// Everything `Catalog::remove_nodes` took out, each with its index, so
/// `restore_nodes` puts the catalog back as it was.
#[derive(Clone, Debug)]
pub(crate) struct RemovedRecords {
    pub nodes: Vec<(usize, ProjectNode)>,
    pub runs: Vec<(usize, Run)>,
    pub versions: Vec<(usize, PhotoVersion)>,
    pub exports: Vec<(usize, PhotoExport)>,
    pub export_directories: Vec<(PathBuf, PathBuf)>,
    pub photo_descriptions: Vec<(PathBuf, String)>,
    pub selected: Option<NodeId>,
}
impl RemovedRecords {
    pub(crate) fn ids(&self) -> Vec<NodeId> {
        self.nodes.iter().map(|(_, node)| node.id).collect()
    }
    pub(crate) fn stacks(&self) -> usize {
        self.nodes
            .iter()
            .filter(|(_, n)| n.kind == NodeKind::Stack)
            .count()
    }
    pub(crate) fn subjects(&self) -> usize {
        self.nodes
            .iter()
            .filter(|(_, n)| n.kind == NodeKind::Subject)
            .count()
    }
}

/// The stacks and subjects a removal takes, expanded: a subject brings all
/// of its stacks.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct RemovalScope {
    pub subjects: Vec<NodeId>,
    pub stacks: Vec<NodeId>,
}
impl RemovalScope {
    pub(crate) fn ids(&self) -> Vec<NodeId> {
        self.subjects.iter().chain(&self.stacks).copied().collect()
    }
    pub(crate) fn is_empty(&self) -> bool {
        self.subjects.is_empty() && self.stacks.is_empty()
    }
}

/// What leaves the library with a scope, counted from the catalog.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct RemovalCounts {
    pub subjects: usize,
    pub stacks: usize,
    pub renders: usize,
    pub versions: usize,
    pub exports: usize,
}

/// Which kind of file a deletion would touch.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(crate) enum FileCategory {
    /// Strehl's own render folders (`strehl-<millis>-<pid>-<n>`).
    Renders,
    /// The source photographs the stack recorded.
    Sources,
}

/// A render folder Strehl created for one of the removed stacks.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct OwnedRender {
    pub stack: NodeId,
    pub directory: PathBuf,
}
/// One removed stack's recorded photographs, all inside `folder`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct OwnedSources {
    pub stack: NodeId,
    pub name: String,
    pub folder: PathBuf,
    pub files: Vec<PathBuf>,
    /// The catalog's recorded bytes (the measurement reads the disk).
    pub recorded_bytes: u64,
}
/// A file or folder of a removed entry that will not be deleted, and why.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct Refusal {
    pub category: FileCategory,
    /// The stack's name.
    pub name: String,
    pub path: PathBuf,
    pub reason: String,
}

/// The files a removal could delete, attributed from catalog records alone.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct OwnedFiles {
    pub renders: Vec<OwnedRender>,
    pub sources: Vec<OwnedSources>,
    pub refused: Vec<Refusal>,
    /// Exports of the removed versions written inside a render folder: they
    /// go with it.
    pub exports_inside: usize,
    /// Exports written elsewhere: never deleted.
    pub exports_kept: usize,
}

/// `child` is `parent` or lies below it (comparable keys, no I/O).
pub(crate) fn path_within(child: &Path, parent: &Path) -> bool {
    let (child, parent) = (path_key(child), path_key(parent));
    if parent.is_empty() {
        return false;
    }
    child == parent
        || child
            .strip_prefix(&parent)
            .is_some_and(|rest| rest.starts_with(['\\', '/']))
}
/// `child` lies strictly below `parent`.
fn strictly_within(child: &Path, parent: &Path) -> bool {
    path_within(child, parent) && path_key(child) != path_key(parent)
}
/// `path_within` on keys already computed.
fn key_within(child: &str, parent: &str) -> bool {
    !parent.is_empty()
        && (child == parent
            || child
                .strip_prefix(parent)
                .is_some_and(|rest| rest.starts_with(['\\', '/'])))
}

impl Catalog {
    /// Subjects and stacks named by `ids`, a subject with all its stacks.
    /// Other kinds and unknown ids are ignored.
    pub(crate) fn removal_scope(&self, ids: &[NodeId]) -> RemovalScope {
        let mut scope = RemovalScope::default();
        let mut seen = HashSet::new();
        for &id in ids {
            let Some(node) = self.node(id) else {
                continue;
            };
            match node.kind {
                NodeKind::Subject => {
                    if seen.insert(id) {
                        scope.subjects.push(id);
                    }
                    for stack in self.stacks_of(id) {
                        if seen.insert(stack) {
                            scope.stacks.push(stack);
                        }
                    }
                }
                NodeKind::Stack => {
                    if seen.insert(id) {
                        scope.stacks.push(id);
                    }
                }
                NodeKind::Project | NodeKind::Folder => {}
            }
        }
        scope
    }

    /// Keep `kept` stacks out of a scope; a subject that would still hold one
    /// of them stays too.
    pub(crate) fn scope_without(&self, scope: &RemovalScope, kept: &[NodeId]) -> RemovalScope {
        let stacks: Vec<NodeId> = scope
            .stacks
            .iter()
            .copied()
            .filter(|id| !kept.contains(id))
            .collect();
        let subjects = scope
            .subjects
            .iter()
            .copied()
            .filter(|&subject| {
                self.stacks_of(subject)
                    .iter()
                    .all(|stack| stacks.contains(stack))
            })
            .collect();
        RemovalScope { subjects, stacks }
    }

    /// What leaves the library with `scope`.
    pub(crate) fn removal_counts(&self, scope: &RemovalScope) -> RemovalCounts {
        let directories: HashSet<&Path> = scope
            .stacks
            .iter()
            .filter_map(|id| self.node(*id))
            .flat_map(|node| node.revisions.iter().map(PathBuf::as_path))
            .collect();
        let versions: HashSet<&str> = self
            .photo_versions
            .iter()
            .filter(|v| self.version_leaves(v, &scope.stacks, &directories))
            .map(|v| v.id.as_str())
            .collect();
        RemovalCounts {
            subjects: scope.subjects.len(),
            stacks: scope.stacks.len(),
            renders: self
                .runs
                .iter()
                .filter(|r| directories.contains(r.directory.as_path()))
                .count(),
            versions: versions.len(),
            exports: self
                .photo_exports
                .iter()
                .filter(|e| versions.contains(e.version.as_str()))
                .count(),
        }
    }

    fn version_leaves(
        &self,
        version: &PhotoVersion,
        stacks: &[NodeId],
        directories: &HashSet<&Path>,
    ) -> bool {
        version.owner.stack.is_some_and(|s| stacks.contains(&s))
            || version
                .owner
                .run
                .as_ref()
                .is_some_and(|run| directories.contains(run.as_path()))
    }

    /// Take stacks and subjects out of the library with their renders'
    /// records, versions and exports. A subject must leave with all of its
    /// stacks. Validates the result; on any refusal nothing changes.
    pub(crate) fn remove_nodes(&mut self, ids: &[NodeId]) -> anyhow::Result<RemovedRecords> {
        let ids: HashSet<NodeId> = ids.iter().copied().collect();
        anyhow::ensure!(!ids.is_empty(), "Choose what to remove");
        for &id in &ids {
            let node = self
                .node(id)
                .ok_or_else(|| anyhow::anyhow!("That item is no longer in the library"))?;
            anyhow::ensure!(
                matches!(node.kind, NodeKind::Stack | NodeKind::Subject),
                "Only subjects and stacks can be removed here"
            );
        }
        if let Some(child) = self
            .nodes
            .iter()
            .find(|n| n.parent.is_some_and(|p| ids.contains(&p)) && !ids.contains(&n.id))
        {
            anyhow::bail!("\"{}\" would be left without its subject", child.name);
        }
        let directories: HashSet<PathBuf> = self
            .nodes
            .iter()
            .filter(|n| ids.contains(&n.id))
            .flat_map(|n| n.revisions.iter().cloned())
            .collect();
        let stacks: Vec<NodeId> = self
            .nodes
            .iter()
            .filter(|n| ids.contains(&n.id) && n.kind == NodeKind::Stack)
            .map(|n| n.id)
            .collect();
        let directory_refs: HashSet<&Path> = directories.iter().map(PathBuf::as_path).collect();
        let leaving_versions: HashSet<String> = self
            .photo_versions
            .iter()
            .filter(|v| self.version_leaves(v, &stacks, &directory_refs))
            .map(|v| v.id.clone())
            .collect();
        let outputs: HashSet<PathBuf> = self
            .runs
            .iter()
            .filter(|r| directories.contains(&r.directory))
            .map(|r| r.output.clone())
            .collect();
        let mut records = RemovedRecords {
            nodes: Vec::new(),
            runs: Vec::new(),
            versions: Vec::new(),
            exports: Vec::new(),
            export_directories: Vec::new(),
            photo_descriptions: Vec::new(),
            selected: self.selected,
        };
        records.nodes = take_where(&mut self.nodes, |n| ids.contains(&n.id));
        records.runs = take_where(&mut self.runs, |r| directories.contains(&r.directory));
        records.versions = take_where(&mut self.photo_versions, |v| {
            leaving_versions.contains(&v.id)
        });
        records.exports = take_where(&mut self.photo_exports, |e| {
            leaving_versions.contains(&e.version)
        });
        let keys: Vec<PathBuf> = self
            .export_directories
            .keys()
            .filter(|k| outputs.contains(*k))
            .cloned()
            .collect();
        for key in keys {
            if let Some(value) = self.export_directories.remove(&key) {
                records.export_directories.push((key, value));
            }
        }
        let keys: Vec<PathBuf> = self
            .photo_descriptions
            .keys()
            .filter(|k| outputs.contains(*k))
            .cloned()
            .collect();
        for key in keys {
            if let Some(value) = self.photo_descriptions.remove(&key) {
                records.photo_descriptions.push((key, value));
            }
        }
        if self.selected.is_some_and(|id| ids.contains(&id)) {
            // The nearest container that stays, else nothing.
            let mut at = records.selected;
            while let Some(id) = at {
                if self.node(id).is_some() {
                    break;
                }
                at = records
                    .nodes
                    .iter()
                    .find(|(_, n)| n.id == id)
                    .and_then(|(_, n)| n.parent);
            }
            self.selected = at;
        }
        if let Err(error) = self.validate() {
            self.put_back(&records);
            return Err(error);
        }
        Ok(records)
    }

    /// Undo of `remove_nodes`: everything back in its place. Refuses (and
    /// changes nothing) if an id or render identity is taken meanwhile.
    pub(crate) fn restore_nodes(&mut self, records: &RemovedRecords) -> anyhow::Result<()> {
        for (_, node) in &records.nodes {
            anyhow::ensure!(
                self.node(node.id).is_none(),
                "\"{}\" is already in the library",
                node.name
            );
        }
        for (_, run) in &records.runs {
            anyhow::ensure!(
                !self.runs.iter().any(|r| r.directory == run.directory),
                "A render of \"{}\" is already in the library",
                run.label
            );
        }
        self.put_back(records);
        if let Err(error) = self.validate() {
            let ids = records.ids();
            self.nodes.retain(|n| !ids.contains(&n.id));
            let runs: HashSet<&Path> = records
                .runs
                .iter()
                .map(|(_, r)| r.directory.as_path())
                .collect();
            self.runs.retain(|r| !runs.contains(r.directory.as_path()));
            let versions: HashSet<&str> = records
                .versions
                .iter()
                .map(|(_, v)| v.id.as_str())
                .collect();
            self.photo_versions
                .retain(|v| !versions.contains(v.id.as_str()));
            self.photo_exports
                .retain(|e| !versions.contains(e.version.as_str()));
            for (key, _) in &records.export_directories {
                self.export_directories.remove(key);
            }
            for (key, _) in &records.photo_descriptions {
                self.photo_descriptions.remove(key);
            }
            return Err(error);
        }
        Ok(())
    }

    fn put_back(&mut self, records: &RemovedRecords) {
        put_where(&mut self.nodes, &records.nodes);
        put_where(&mut self.runs, &records.runs);
        put_where(&mut self.photo_versions, &records.versions);
        put_where(&mut self.photo_exports, &records.exports);
        for (key, value) in &records.export_directories {
            self.export_directories.insert(key.clone(), value.clone());
        }
        for (key, value) in &records.photo_descriptions {
            self.photo_descriptions.insert(key.clone(), value.clone());
        }
        if records.selected.is_some_and(|id| self.node(id).is_some()) {
            self.selected = records.selected;
        }
    }

    /// Merge `others` into `into`: their stacks move to it, their notes are
    /// appended, and optics, scale and picture fill what `into` lacks. The
    /// emptied subjects are returned for the caller to remove (through the
    /// undo journal). Nothing changes on a refusal.
    pub(crate) fn merge_subjects(
        &mut self,
        into: NodeId,
        others: &[NodeId],
    ) -> anyhow::Result<Vec<NodeId>> {
        let target = self
            .node(into)
            .filter(|n| n.kind == NodeKind::Subject)
            .ok_or_else(|| anyhow::anyhow!("Choose the subject to merge into"))?;
        let mut notes = target.notes.clone();
        let mut meta = target
            .subject
            .clone()
            .ok_or_else(|| anyhow::anyhow!("Invalid subject record"))?;
        let mut merged = Vec::new();
        let mut moves = Vec::new();
        for &other in others {
            if other == into || merged.contains(&other) {
                continue;
            }
            let node = self
                .node(other)
                .filter(|n| n.kind == NodeKind::Subject)
                .ok_or_else(|| anyhow::anyhow!("Only subjects can be merged"))?;
            let theirs = node.notes.trim();
            if !theirs.is_empty() && !notes.contains(theirs) {
                if !notes.trim().is_empty() {
                    notes.push_str("\n\n");
                }
                notes.push_str(theirs);
            }
            if let Some(other_meta) = &node.subject {
                if meta.hero.is_none() {
                    meta.hero.clone_from(&other_meta.hero);
                }
                if meta.optics.is_none() {
                    meta.optics.clone_from(&other_meta.optics);
                }
                if meta.scale.is_none() {
                    meta.scale.clone_from(&other_meta.scale);
                }
                if other_meta.created > 0
                    && (meta.created == 0 || other_meta.created < meta.created)
                {
                    meta.created = other_meta.created;
                }
            }
            moves.extend(self.stacks_of(other));
            merged.push(other);
        }
        anyhow::ensure!(!merged.is_empty(), "Choose subjects to merge");
        anyhow::ensure!(
            notes.chars().count() <= super::subjects::MAX_NOTES_CHARS,
            "The merged notes would exceed {} characters",
            super::subjects::MAX_NOTES_CHARS
        );
        for &stack in &moves {
            self.can_move(stack, Some(into))?;
        }
        for &stack in &moves {
            self.node_mut(stack).unwrap().parent = Some(into);
        }
        let node = self.node_mut(into).unwrap();
        node.notes = notes;
        node.subject = Some(meta);
        Ok(merged)
    }

    /// The files the removed `scope` owns on disk, attributed from catalog
    /// records alone (no I/O). A render folder is owned when Strehl created
    /// it (a job folder holding the run's photograph and log) and no record
    /// that stays in the library lies inside it. A stack's sources are owned
    /// when every recorded photograph lies inside its folder and no stack
    /// that stays records a photograph there.
    pub(crate) fn owned_files(&self, scope: &RemovalScope) -> OwnedFiles {
        let leaving: HashSet<NodeId> = scope.stacks.iter().copied().collect();
        let leaving_dirs: HashSet<&Path> = scope
            .stacks
            .iter()
            .filter_map(|id| self.node(*id))
            .flat_map(|n| n.revisions.iter().map(PathBuf::as_path))
            .collect();
        let leaving_versions: HashSet<&str> = self
            .photo_versions
            .iter()
            .filter(|v| self.version_leaves(v, &scope.stacks, &leaving_dirs))
            .map(|v| v.id.as_str())
            .collect();
        // Records that stay, as comparable keys computed once: anything of
        // theirs inside a folder we would delete makes it not ours alone.
        let mut staying_paths: Vec<(String, &str)> = Vec::new();
        let mut staying_folders: HashMap<String, &str> = HashMap::new();
        let mut staying_files: HashMap<String, &str> = HashMap::new();
        for node in &self.nodes {
            if node.kind != NodeKind::Stack || leaving.contains(&node.id) {
                continue;
            }
            if let Some(draft) = &node.stack {
                let folder = path_key(&draft.source);
                staying_folders.insert(folder.clone(), node.name.as_str());
                staying_paths.push((folder, node.name.as_str()));
                for source in &draft.sources {
                    let key = path_key(&source.path);
                    staying_files.insert(key.clone(), node.name.as_str());
                    staying_paths.push((key, node.name.as_str()));
                }
            }
        }
        let owner_of = |run: &Run| {
            self.stack_for_run(&run.directory)
                .and_then(|id| self.node(id))
                .map_or("another render", |n| n.name.as_str())
        };
        let staying_runs: Vec<(String, String, &str)> = self
            .runs
            .iter()
            .filter(|r| !leaving_dirs.contains(r.directory.as_path()))
            .map(|r| (path_key(&r.directory), path_key(&r.output), owner_of(r)))
            .collect();
        let staying_exports: Vec<String> = self
            .photo_exports
            .iter()
            .filter(|e| !leaving_versions.contains(e.version.as_str()))
            .map(|e| path_key(&e.path))
            .collect();
        let staying_export_set: HashSet<&str> =
            staying_exports.iter().map(String::as_str).collect();
        let mut owned = OwnedFiles::default();
        let mut render_dirs: Vec<String> = Vec::new();
        for &stack in &scope.stacks {
            let Some(node) = self.node(stack) else {
                continue;
            };
            for directory in &node.revisions {
                let Some(run) = self.runs.iter().find(|r| &r.directory == directory) else {
                    continue;
                };
                let key = path_key(directory);
                let reason = if run.imported.is_some() {
                    Some("an imported session's folder, not one Strehl created".to_owned())
                } else if !directory.is_absolute() || directory.parent().is_none() {
                    Some("not a complete folder path".to_owned())
                } else if job_process(directory).is_none() {
                    Some("not named like a Strehl render folder".to_owned())
                } else if !strictly_within(&run.output, directory)
                    || !strictly_within(&run.log, directory)
                {
                    Some("its photograph or log lies outside the folder".to_owned())
                } else if let Some((_, name)) = staying_paths
                    .iter()
                    .find(|(path, _)| key_within(path, &key))
                {
                    Some(format!("holds photographs of \"{name}\""))
                } else if let Some((_, _, name)) =
                    staying_runs.iter().find(|(run_dir, output, _)| {
                        key_within(run_dir, &key)
                            || key_within(output, &key)
                            || key_within(&key, run_dir)
                    })
                {
                    Some(format!("shared with a render of \"{name}\""))
                } else if staying_exports.iter().any(|p| key_within(p, &key)) {
                    Some("holds an export of a version that stays".to_owned())
                } else {
                    None
                };
                match reason {
                    Some(reason) => owned.refused.push(Refusal {
                        category: FileCategory::Renders,
                        name: node.name.clone(),
                        path: directory.clone(),
                        reason,
                    }),
                    None => {
                        render_dirs.push(key);
                        owned.renders.push(OwnedRender {
                            stack,
                            directory: directory.clone(),
                        });
                    }
                }
            }
            let Some(draft) = &node.stack else {
                continue;
            };
            let folder = &draft.source;
            let folder_key = path_key(folder);
            let file_keys: Vec<String> = draft.sources.iter().map(|s| path_key(&s.path)).collect();
            let reason = if draft.sources.is_empty() {
                Some("no photographs are recorded for it".to_owned())
            } else if !folder.is_absolute() || folder.parent().is_none() {
                Some("its folder is a drive root or not a complete path".to_owned())
            } else if file_keys
                .iter()
                .any(|k| k == &folder_key || !key_within(k, &folder_key))
            {
                Some("it records photographs outside its folder".to_owned())
            } else if let Some(name) = staying_folders
                .get(&folder_key)
                .or_else(|| file_keys.iter().find_map(|k| staying_files.get(k)))
            {
                Some(format!(
                    "its photographs are also the sources of \"{name}\""
                ))
            } else if let Some((_, _, name)) = staying_runs.iter().find(|(run_dir, output, _)| {
                file_keys
                    .iter()
                    .any(|k| k == output || key_within(k, run_dir))
            }) {
                Some(format!("a render of \"{name}\" uses its photographs"))
            } else if file_keys
                .iter()
                .any(|k| staying_export_set.contains(k.as_str()))
            {
                Some("an export that stays is one of its files".to_owned())
            } else {
                None
            };
            match reason {
                Some(reason) => owned.refused.push(Refusal {
                    category: FileCategory::Sources,
                    name: node.name.clone(),
                    path: folder.clone(),
                    reason,
                }),
                None => owned.sources.push(OwnedSources {
                    stack,
                    name: node.name.clone(),
                    folder: folder.clone(),
                    files: draft.sources.iter().map(|s| s.path.clone()).collect(),
                    recorded_bytes: draft.sources.iter().map(|s| s.bytes).sum(),
                }),
            }
        }
        // Two removed stacks recording the same folder: one claim, once.
        let mut seen: HashMap<String, usize> = HashMap::new();
        let mut merged: Vec<OwnedSources> = Vec::new();
        for claim in std::mem::take(&mut owned.sources) {
            match seen.get(&path_key(&claim.folder)) {
                Some(&at) => {
                    let into = &mut merged[at];
                    let known: HashSet<String> = into.files.iter().map(|p| path_key(p)).collect();
                    for file in claim.files {
                        if !known.contains(&path_key(&file)) {
                            into.files.push(file);
                        }
                    }
                    into.recorded_bytes = into.recorded_bytes.max(claim.recorded_bytes);
                }
                None => {
                    seen.insert(path_key(&claim.folder), merged.len());
                    merged.push(claim);
                }
            }
        }
        owned.sources = merged;
        for export in self
            .photo_exports
            .iter()
            .filter(|e| leaving_versions.contains(e.version.as_str()))
        {
            let key = path_key(&export.path);
            if render_dirs.iter().any(|d| key_within(&key, d)) {
                owned.exports_inside += 1;
            } else {
                owned.exports_kept += 1;
            }
        }
        owned
    }
}

/// Remove the items `take` selects, keeping each one's index.
fn take_where<T>(items: &mut Vec<T>, take: impl Fn(&T) -> bool) -> Vec<(usize, T)> {
    let mut taken = Vec::new();
    let mut kept = Vec::with_capacity(items.len());
    for (index, item) in std::mem::take(items).into_iter().enumerate() {
        if take(&item) {
            taken.push((index, item));
        } else {
            kept.push(item);
        }
    }
    *items = kept;
    taken
}
/// Insert items at the indices `take_where` recorded (ascending), clamped.
fn put_where<T: Clone>(items: &mut Vec<T>, taken: &[(usize, T)]) {
    for (index, item) in taken {
        let at = (*index).min(items.len());
        items.insert(at, item.clone());
    }
}

#[cfg(test)]
#[path = "catalog-removal-tests.rs"]
mod tests;
