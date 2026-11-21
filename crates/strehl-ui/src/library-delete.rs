//! Deleting a removed library entry's files, on workers: first measured for
//! the confirmation (sizes, counts, folders, room in the Recycle Bin), then
//! deleted. Only what `Catalog::owned_files` attributed is touched, and each
//! folder is checked again just before it goes.
//!
//! - **Renders** are Strehl's job folders (`strehl-<millis>-<pid>-<n>`),
//!   deleted whole.
//! - **Sources** are the photographs the stack recorded. In a capture folder
//!   the receiver made (`manifest.json` and `events.jsonl`) the capture's own
//!   records and `frame-*` files go too, and only once the capture has its
//!   `result.json`: a capture without one may still be receiving from the
//!   camera, and the Pi reconnects to a missing folder only when the run
//!   finished (`strehl-capture` `recover_journal`). Anything else in a source
//!   folder stays, and so does the folder.
//!
//! A category goes to the Recycle Bin only when the bin of every volume it
//! touches is on and can hold all of it; otherwise it is deleted permanently,
//! and the confirmation says so before anything happens.
use crate::{
    display_path::display_path,
    workspace_history::{FileCategory, NodeId, OwnedFiles, Refusal, path_within},
};
use std::{
    collections::BTreeMap,
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, AtomicUsize, Ordering},
};

/// The records a Strehl capture folder holds beside its RAWs.
const CAPTURE_RECORDS: [&str; 4] = [
    "manifest.json",
    "events.jsonl",
    "result.json",
    "transfer-receipts.jsonl",
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Disposal {
    RecycleBin,
    Permanent,
}

/// One volume's Recycle Bin, as Windows reports it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct BinRoom {
    /// "D:"
    pub volume: String,
    /// Its maximum size; `None` when Windows does not say.
    pub capacity: Option<u64>,
    /// What it holds now.
    pub used: u64,
    /// The bin is off for this volume ("Don't move files to the Recycle Bin").
    pub disabled: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct MeasuredRender {
    pub stack: NodeId,
    pub directory: PathBuf,
    pub bytes: u64,
    pub files: usize,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct MeasuredSources {
    pub stack: NodeId,
    pub name: String,
    pub folder: PathBuf,
    /// Owned files found on disk: recorded photographs, and in a capture
    /// folder its records and `frame-*` files.
    pub files: Vec<PathBuf>,
    pub bytes: u64,
    /// Recorded photographs found.
    pub photographs: usize,
    /// Recorded photographs no longer there.
    pub missing: usize,
    /// A capture folder the receiver made.
    pub capture: bool,
    /// Entries in the folder that are not the stack's: they stay.
    pub others: usize,
}
/// One category's totals and how it would be deleted.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct CategoryMeasure {
    pub bytes: u64,
    pub files: usize,
    pub folders: usize,
    pub disposal: Disposal,
    /// The bins of the volumes it touches.
    pub bins: Vec<BinRoom>,
    /// Why it cannot go to the Recycle Bin, if it cannot.
    pub permanent_because: Option<String>,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct DeleteMeasure {
    pub renders: Vec<MeasuredRender>,
    pub sources: Vec<MeasuredSources>,
    /// Folders the catalog attributed that the disk does not allow: missing,
    /// a capture without its result, the capture being written.
    pub refused: Vec<Refusal>,
    pub render_total: CategoryMeasure,
    pub source_total: CategoryMeasure,
}

/// What the deletion must leave alone however the catalog reads.
#[derive(Clone, Debug, Default)]
pub(crate) struct Guard {
    /// The capture folder the receiver is writing now.
    pub capturing: Option<PathBuf>,
}

/// Measure what `owned` would delete. Reads the disk; run it on a worker.
pub(crate) fn measure(owned: &OwnedFiles, guard: &Guard, cancelled: &AtomicBool) -> DeleteMeasure {
    let mut refused = owned.refused.clone();
    let mut renders = Vec::new();
    for render in &owned.renders {
        if cancelled.load(Ordering::Relaxed) {
            break;
        }
        match std::fs::symlink_metadata(&render.directory) {
            Ok(meta) if meta.is_dir() && !meta.file_type().is_symlink() => {
                let (bytes, files) = folder_size(&render.directory, cancelled);
                renders.push(MeasuredRender {
                    stack: render.stack,
                    directory: render.directory.clone(),
                    bytes,
                    files,
                });
            }
            _ => refused.push(Refusal {
                category: FileCategory::Renders,
                name: String::new(),
                path: render.directory.clone(),
                reason: "already gone from disk".into(),
            }),
        }
    }
    let mut sources = Vec::new();
    for claim in &owned.sources {
        if cancelled.load(Ordering::Relaxed) {
            break;
        }
        match measure_sources(claim, guard) {
            Ok(measured) => sources.push(measured),
            Err(reason) => refused.push(Refusal {
                category: FileCategory::Sources,
                name: claim.name.clone(),
                path: claim.folder.clone(),
                reason,
            }),
        }
    }
    let render_total = category(
        renders
            .iter()
            .map(|r| (r.directory.as_path(), r.bytes, r.files)),
    );
    let source_total = category(
        sources
            .iter()
            .map(|s| (s.folder.as_path(), s.bytes, s.files.len())),
    );
    DeleteMeasure {
        renders,
        sources,
        refused,
        render_total,
        source_total,
    }
}

fn measure_sources(
    claim: &crate::workspace_history::OwnedSources,
    guard: &Guard,
) -> Result<MeasuredSources, String> {
    let folder = &claim.folder;
    match std::fs::symlink_metadata(folder) {
        Ok(meta) if meta.is_dir() && !meta.file_type().is_symlink() => {}
        Ok(_) => return Err("not a folder".into()),
        Err(_) => return Err("its folder is gone".into()),
    }
    let capture = is_capture_folder(folder);
    if capture {
        if guard
            .capturing
            .as_deref()
            .is_some_and(|c| path_within(c, folder) && path_within(folder, c))
        {
            return Err("this capture is being written now".into());
        }
        if !folder.join("result.json").is_file() {
            return Err(
                "this capture has no result yet: the camera may still send photographs to it"
                    .into(),
            );
        }
    }
    let recorded: std::collections::HashSet<String> = claim
        .files
        .iter()
        .filter_map(|p| p.file_name())
        .map(|n| n.to_string_lossy().to_lowercase())
        .collect();
    let mut files = Vec::new();
    let mut bytes = 0;
    let mut photographs = 0;
    let mut others = 0;
    let entries =
        std::fs::read_dir(folder).map_err(|e| format!("its folder cannot be read: {e}"))?;
    for entry in entries.flatten() {
        let name = entry.file_name().to_string_lossy().to_lowercase();
        let Ok(kind) = entry.file_type() else {
            others += 1;
            continue;
        };
        let is_recorded = recorded.contains(&name);
        let owned = kind.is_file() && (is_recorded || (capture && capture_owned(&name)));
        if owned {
            bytes += entry.metadata().map_or(0, |m| m.len());
            photographs += usize::from(is_recorded);
            files.push(entry.path());
        } else {
            others += 1;
        }
    }
    files.sort();
    Ok(MeasuredSources {
        stack: claim.stack,
        name: claim.name.clone(),
        folder: folder.clone(),
        missing: claim.files.len().saturating_sub(photographs),
        files,
        bytes,
        photographs,
        capture,
        others,
    })
}

/// A folder the capture receiver made for one run.
pub(crate) fn is_capture_folder(folder: &Path) -> bool {
    folder.join("manifest.json").is_file() && folder.join("events.jsonl").is_file()
}
/// Files of a capture folder that belong to the capture (lowercase name).
fn capture_owned(name: &str) -> bool {
    CAPTURE_RECORDS.contains(&name) || name.starts_with("frame-")
}

fn folder_size(folder: &Path, cancelled: &AtomicBool) -> (u64, usize) {
    let mut pending = vec![folder.to_path_buf()];
    let (mut bytes, mut files) = (0, 0);
    while let Some(at) = pending.pop() {
        if cancelled.load(Ordering::Relaxed) {
            break;
        }
        let Ok(entries) = std::fs::read_dir(&at) else {
            continue;
        };
        for entry in entries.flatten() {
            let Ok(meta) = entry.path().symlink_metadata() else {
                continue;
            };
            if meta.is_dir() && !meta.file_type().is_symlink() {
                pending.push(entry.path());
            } else {
                bytes += meta.len();
                files += 1;
            }
        }
    }
    (bytes, files)
}

/// Totals, and whether every volume's bin can take its share.
fn category<'a>(items: impl Iterator<Item = (&'a Path, u64, usize)>) -> CategoryMeasure {
    let mut volumes: BTreeMap<String, (PathBuf, u64)> = BTreeMap::new();
    let (mut bytes, mut files, mut folders) = (0, 0, 0);
    for (path, b, f) in items {
        bytes += b;
        files += f;
        folders += 1;
        let volume = volume_of(path);
        let slot = volumes
            .entry(volume)
            .or_insert_with(|| (path.to_path_buf(), 0));
        slot.1 += b;
    }
    let rooms: Vec<(BinRoom, u64)> = volumes
        .iter()
        .map(|(volume, (path, share))| {
            let room = bin_room(path).unwrap_or(BinRoom {
                volume: volume.clone(),
                capacity: None,
                used: 0,
                disabled: false,
            });
            (room, *share)
        })
        .collect();
    let (disposal, permanent_because) = disposal_for(&rooms);
    CategoryMeasure {
        bytes,
        files,
        folders,
        disposal,
        bins: rooms.into_iter().map(|(room, _)| room).collect(),
        permanent_because,
    }
}

/// The Recycle Bin only when the bin of every volume is on and can hold that
/// volume's share; otherwise permanent, and why.
pub(crate) fn disposal_for(rooms: &[(BinRoom, u64)]) -> (Disposal, Option<String>) {
    if rooms.is_empty() {
        return (Disposal::Permanent, None);
    }
    for (room, share) in rooms {
        let why = if room.disabled {
            Some(format!("the Recycle Bin is off for {}", room.volume))
        } else {
            match room.capacity {
                None => Some(format!(
                    "Windows does not report a Recycle Bin for {}",
                    room.volume
                )),
                Some(capacity) if *share > capacity => Some(format!(
                    "larger than the Recycle Bin on {} (it holds {})",
                    room.volume,
                    crate::library_paint::bytes(capacity)
                )),
                Some(_) => None,
            }
        };
        if why.is_some() {
            return (Disposal::Permanent, why);
        }
    }
    (Disposal::RecycleBin, None)
}

/// "D:" for a local path, the share for a UNC path.
fn volume_of(path: &Path) -> String {
    match path.components().next() {
        Some(std::path::Component::Prefix(prefix)) => display_path(Path::new(prefix.as_os_str()))
            .trim_end_matches('\\')
            .to_uppercase(),
        _ => "/".into(),
    }
}

/// What to delete: the measured items of the chosen categories.
#[derive(Clone, Debug, Default)]
pub(crate) struct DeletePlan {
    pub renders: Vec<MeasuredRender>,
    pub render_disposal: Option<Disposal>,
    pub sources: Vec<MeasuredSources>,
    pub source_disposal: Option<Disposal>,
}
impl DeletePlan {
    pub(crate) fn is_empty(&self) -> bool {
        self.renders.is_empty() && self.sources.is_empty()
    }
    /// Folders and source folders, for progress.
    pub(crate) fn items(&self) -> usize {
        self.renders.len() + self.sources.len()
    }
}
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct DeleteReport {
    pub files: usize,
    pub bytes: u64,
    pub recycled: usize,
    pub folders_removed: usize,
    /// Source folders left in place because something else is in them.
    pub folders_kept: Vec<PathBuf>,
    /// What could not be deleted, and why.
    pub failed: Vec<String>,
}

/// Delete the plan. Run it on a worker; `done` counts finished items.
pub(crate) fn execute(plan: &DeletePlan, guard: &Guard, done: &AtomicUsize) -> DeleteReport {
    let _com = ComScope::new();
    let mut report = DeleteReport::default();
    if let Some(disposal) = plan.render_disposal {
        let mut recycle = Vec::new();
        for render in &plan.renders {
            let name_ok = render
                .directory
                .file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| n.starts_with("strehl-"));
            let is_folder = std::fs::symlink_metadata(&render.directory)
                .is_ok_and(|m| m.is_dir() && !m.file_type().is_symlink());
            if !(name_ok && is_folder) {
                report.failed.push(format!(
                    "{}: no longer the render folder that was measured",
                    display_path(&render.directory)
                ));
                done.fetch_add(1, Ordering::Relaxed);
                continue;
            }
            match disposal {
                Disposal::RecycleBin => recycle.push(render),
                Disposal::Permanent => {
                    match std::fs::remove_dir_all(&render.directory) {
                        Ok(()) => {
                            report.files += render.files;
                            report.bytes += render.bytes;
                            report.folders_removed += 1;
                        }
                        Err(error) => report
                            .failed
                            .push(format!("{}: {error}", display_path(&render.directory))),
                    }
                    done.fetch_add(1, Ordering::Relaxed);
                }
            }
        }
        if !recycle.is_empty() {
            let paths: Vec<&Path> = recycle.iter().map(|r| r.directory.as_path()).collect();
            match recycle_paths(&paths) {
                Ok(()) => {
                    for render in &recycle {
                        if render.directory.exists() {
                            report.failed.push(format!(
                                "{}: still there after the move to the Recycle Bin",
                                display_path(&render.directory)
                            ));
                        } else {
                            report.files += render.files;
                            report.bytes += render.bytes;
                            report.recycled += render.files;
                            report.folders_removed += 1;
                        }
                    }
                }
                Err(error) => report.failed.push(format!("Renders: {error:#}")),
            }
            done.fetch_add(recycle.len(), Ordering::Relaxed);
        }
    }
    if let Some(disposal) = plan.source_disposal {
        for sources in &plan.sources {
            delete_sources(sources, disposal, guard, &mut report);
            done.fetch_add(1, Ordering::Relaxed);
        }
    }
    report
}

fn delete_sources(
    sources: &MeasuredSources,
    disposal: Disposal,
    guard: &Guard,
    report: &mut DeleteReport,
) {
    let folder = &sources.folder;
    let shown = display_path(folder);
    if sources.capture {
        // Checked again: the capture must still be finished and not the one
        // being written.
        if !folder.join("result.json").is_file()
            || guard
                .capturing
                .as_deref()
                .is_some_and(|c| path_within(c, folder) && path_within(folder, c))
        {
            report.failed.push(format!(
                "{shown}: the capture is not finished; nothing deleted"
            ));
            return;
        }
    }
    let owned: std::collections::HashSet<PathBuf> = sources.files.iter().cloned().collect();
    // What is in the folder now: owned files that are still there, and
    // anything else (which keeps the folder).
    let mut present = Vec::new();
    let mut others = 0;
    match std::fs::read_dir(folder) {
        Ok(entries) => {
            for entry in entries.flatten() {
                let path = entry.path();
                if owned.contains(&path) && entry.file_type().is_ok_and(|k| k.is_file()) {
                    present.push(path);
                } else {
                    others += 1;
                }
            }
        }
        Err(error) => {
            report.failed.push(format!("{shown}: {error}"));
            return;
        }
    }
    let size = |paths: &[PathBuf]| -> u64 {
        paths
            .iter()
            .filter_map(|p| std::fs::metadata(p).ok())
            .map(|m| m.len())
            .sum()
    };
    let bytes = size(&present);
    match disposal {
        Disposal::RecycleBin => {
            // A folder holding nothing else goes as one item, so the Recycle
            // Bin restores it whole.
            let whole = others == 0;
            let targets: Vec<&Path> = if whole {
                vec![folder.as_path()]
            } else {
                present.iter().map(PathBuf::as_path).collect()
            };
            if targets.is_empty() {
                return;
            }
            match recycle_paths(&targets) {
                Ok(()) => {
                    let left = present.iter().filter(|p| p.exists()).count();
                    if left > 0 {
                        report.failed.push(format!(
                            "{shown}: {left} files still there after the move to the Recycle Bin"
                        ));
                    }
                    let gone = present.len() - left;
                    report.files += gone;
                    report.recycled += gone;
                    report.bytes += if left == 0 { bytes } else { 0 };
                    if whole && !folder.exists() {
                        report.folders_removed += 1;
                    } else if !whole {
                        report.folders_kept.push(folder.clone());
                    }
                }
                Err(error) => report.failed.push(format!("{shown}: {error:#}")),
            }
        }
        Disposal::Permanent => {
            let mut failed = 0;
            for path in &present {
                match std::fs::remove_file(path) {
                    Ok(()) => report.files += 1,
                    Err(_) => failed += 1,
                }
            }
            report.bytes += bytes;
            if failed > 0 {
                report
                    .failed
                    .push(format!("{shown}: {failed} files could not be deleted"));
            }
            // Never recursive: the folder goes only if nothing is left in it.
            if others == 0 && failed == 0 && std::fs::remove_dir(folder).is_ok() {
                report.folders_removed += 1;
            } else {
                report.folders_kept.push(folder.clone());
            }
        }
    }
}

/// Move files or folders to the Recycle Bin (Windows). Elsewhere: refused.
#[cfg(windows)]
fn recycle_paths(paths: &[&Path]) -> anyhow::Result<()> {
    use windows_sys::Win32::UI::Shell::{
        FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONFIRMATION, FOF_NOERRORUI, FOF_SILENT,
        FOF_WANTNUKEWARNING, SHFILEOPSTRUCTW, SHFileOperationW,
    };
    // A double-NUL-terminated list. The shell does not accept the verbatim
    // `\\?\` prefix the catalog records.
    let mut from: Vec<u16> = Vec::new();
    for path in paths {
        anyhow::ensure!(path.is_absolute(), "Only complete paths can be deleted");
        from.extend(display_path(path).encode_utf16());
        from.push(0);
    }
    from.push(0);
    let mut operation = SHFILEOPSTRUCTW {
        hwnd: std::ptr::null_mut(),
        wFunc: FO_DELETE,
        pFrom: from.as_ptr(),
        pTo: std::ptr::null(),
        // Silent, but if a file could not be recycled after all, Windows asks
        // before destroying it (FOF_WANTNUKEWARNING) rather than doing so.
        fFlags: (FOF_ALLOWUNDO
            | FOF_NOCONFIRMATION
            | FOF_NOERRORUI
            | FOF_SILENT
            | FOF_WANTNUKEWARNING) as u16,
        fAnyOperationsAborted: 0,
        hNameMappings: std::ptr::null_mut(),
        lpszProgressTitle: std::ptr::null(),
    };
    // SAFETY: `from` is a valid double-NUL-terminated UTF-16 list that
    // outlives the call; the other pointers are null as the API allows.
    let code = unsafe { SHFileOperationW(&mut operation) };
    anyhow::ensure!(
        code == 0,
        "Windows could not move them to the Recycle Bin (code {code:#x})"
    );
    anyhow::ensure!(
        operation.fAnyOperationsAborted == 0,
        "The move to the Recycle Bin was stopped; some files were kept"
    );
    Ok(())
}
#[cfg(not(windows))]
fn recycle_paths(_paths: &[&Path]) -> anyhow::Result<()> {
    anyhow::bail!("This system has no Recycle Bin Strehl can use")
}

/// The Recycle Bin of the volume holding `path`.
#[cfg(windows)]
pub(crate) fn bin_room(path: &Path) -> Option<BinRoom> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::{
        Storage::FileSystem::{GetVolumeNameForVolumeMountPointW, GetVolumePathNameW},
        System::Registry::{HKEY_CURRENT_USER, RRF_RT_REG_DWORD, RegGetValueW},
        UI::Shell::{SHQUERYRBINFO, SHQueryRecycleBinW},
    };
    let wide = |text: &std::ffi::OsStr| -> Vec<u16> { text.encode_wide().chain(Some(0)).collect() };
    let shown = display_path(path);
    let target = wide(std::ffi::OsStr::new(&shown));
    let mut root = [0u16; 512];
    // SAFETY: a NUL-terminated path and a writable buffer of the given length.
    if unsafe { GetVolumePathNameW(target.as_ptr(), root.as_mut_ptr(), root.len() as u32) } == 0 {
        return None;
    }
    let root_len = root.iter().position(|&c| c == 0)?;
    let root_text = String::from_utf16_lossy(&root[..root_len]);
    let mut volume = [0u16; 128];
    // SAFETY: `root` is NUL-terminated (a mount point with its trailing
    // backslash); `volume` is writable for its length.
    let named = unsafe {
        GetVolumeNameForVolumeMountPointW(root.as_ptr(), volume.as_mut_ptr(), volume.len() as u32)
    } != 0;
    let mut info = SHQUERYRBINFO {
        cbSize: std::mem::size_of::<SHQUERYRBINFO>() as u32,
        i64Size: 0,
        i64NumItems: 0,
    };
    // SAFETY: `root` is NUL-terminated and `info` has its size set.
    let queried = unsafe { SHQueryRecycleBinW(root.as_ptr(), &mut info) } == 0;
    let mut room = BinRoom {
        volume: root_text.trim_end_matches('\\').to_uppercase(),
        capacity: None,
        used: if queried {
            info.i64Size.max(0) as u64
        } else {
            0
        },
        disabled: false,
    };
    if !named {
        return Some(room);
    }
    let volume_len = volume.iter().position(|&c| c == 0)?;
    let volume_text = String::from_utf16_lossy(&volume[..volume_len]);
    // "\\?\Volume{GUID}\" -> "{GUID}"
    let guid = volume_text
        .trim_end_matches('\\')
        .rsplit_once("Volume")
        .map(|(_, guid)| guid.to_owned())?;
    let key = wide(std::ffi::OsStr::new(&format!(
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\BitBucket\Volume\{guid}"
    )));
    let read = |value: &str| -> Option<u32> {
        let name = wide(std::ffi::OsStr::new(value));
        let mut data = 0u32;
        let mut size = std::mem::size_of::<u32>() as u32;
        // SAFETY: NUL-terminated key and value names; a u32 out-parameter
        // with its size, as RRF_RT_REG_DWORD requires.
        let status = unsafe {
            RegGetValueW(
                HKEY_CURRENT_USER,
                key.as_ptr(),
                name.as_ptr(),
                RRF_RT_REG_DWORD,
                std::ptr::null_mut(),
                (&mut data as *mut u32).cast(),
                &mut size,
            )
        };
        (status == 0).then_some(data)
    };
    room.disabled = read("NukeOnDelete").is_some_and(|v| v != 0);
    // MaxCapacity is in megabytes.
    room.capacity = read("MaxCapacity").map(|mb| u64::from(mb) * 1024 * 1024);
    Some(room)
}
#[cfg(not(windows))]
pub(crate) fn bin_room(_path: &Path) -> Option<BinRoom> {
    None
}

/// The shell's file operations want COM on the calling thread.
struct ComScope(bool);
impl ComScope {
    #[cfg(windows)]
    fn new() -> Self {
        use windows_sys::Win32::System::Com::{COINIT_APARTMENTTHREADED, CoInitializeEx};
        // SAFETY: initialises COM for this worker thread; balanced in Drop.
        let hr = unsafe { CoInitializeEx(std::ptr::null(), COINIT_APARTMENTTHREADED as u32) };
        Self(hr >= 0)
    }
    #[cfg(not(windows))]
    fn new() -> Self {
        Self(false)
    }
}
impl Drop for ComScope {
    fn drop(&mut self) {
        #[cfg(windows)]
        if self.0 {
            // SAFETY: balances the successful CoInitializeEx in `new`.
            unsafe { windows_sys::Win32::System::Com::CoUninitialize() };
        }
    }
}

#[cfg(test)]
#[path = "library-delete-tests.rs"]
mod tests;
