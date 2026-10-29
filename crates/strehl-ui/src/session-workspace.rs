//! Saved opt-in session recipes. Ordinary stack recipes retain `None`.
use crate::{jobs::StackScan, workspace_history::SourceIdentity};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
pub(crate) use strehl_cli::session_input::{PassSpec, SessionMode, SessionSpec};
#[path = "session-summary.rs"]
mod summary;
pub(crate) use summary::SessionSummary;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct SessionDraft {
    pub manifest: SessionSpec,
    pub memory_limit_gib: f64,
    #[serde(default)]
    pub precision_weights: bool,
    #[serde(default)]
    pub contribution_maps: bool,
    #[serde(default)]
    pub focus_evidence: bool,
    #[serde(default)]
    pub reproducibility: bool,
    #[serde(default)]
    pub original_cfa_reconstruction: bool,
    /// A scan snapshot, replaced only by an explicit source/layout reload.
    #[serde(default)]
    pub sources: Vec<SourceIdentity>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub(crate) struct CaptureGroup {
    pub pass_index: usize,
    pub name: String,
    pub range: std::ops::Range<usize>,
    pub segment_ends: Vec<usize>,
    pub primary: bool,
}

impl SessionDraft {
    pub(crate) fn from_directory(directory: PathBuf) -> Self {
        let name = directory
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned();
        Self {
            manifest: SessionSpec {
                passes: vec![PassSpec {
                    name,
                    directories: vec![directory],
                }],
                ..Default::default()
            },
            memory_limit_gib: 16.0,
            precision_weights: false,
            contribution_maps: false,
            focus_evidence: false,
            reproducibility: false,
            original_cfa_reconstruction: false,
            sources: Vec::new(),
        }
    }
    pub(crate) fn validate(&self) -> Result<()> {
        self.manifest.validate()?;
        ensure!(
            !self.precision_weights
                || precision_available(self.manifest.mode, self.manifest.passes.len()),
            "Precision weighting needs at least two repeated or exposure passes"
        );
        ensure!(
            !(self.contribution_maps || self.focus_evidence)
                || !managed_evidence(self.manifest.mode),
            "Mosaics and independent views manage their own focus evidence"
        );
        ensure!(
            !self.reproducibility
                || reproducibility_available(self.manifest.mode, self.manifest.passes.len()),
            "Automatic comparison needs two combine, interleaved, repeat or layer passes"
        );
        ensure!(
            !self.original_cfa_reconstruction || reconstruction_available(self.manifest.mode),
            "Original-CFA reconstruction is available for combine, interleaved, repeated and exposure passes",
        );
        ensure!(
            self.manifest.passes.len() <= 64,
            "A desktop session supports at most 64 passes"
        );
        ensure!(
            self.memory_limit_gib.is_finite() && (1.0..=4096.0).contains(&self.memory_limit_gib),
            "Session RAM budget must be between 1 and 4096 GiB"
        );
        ensure!(
            self.manifest
                .passes
                .iter()
                .all(|pass| pass.directories.iter().all(|path| path.is_absolute())),
            "Desktop session source directories must be absolute"
        );
        Ok(())
    }
    /// Apply only after an explicit mode/layout edit. Saved jobs are immutable.
    pub(crate) fn normalize_mode_options(&mut self) {
        if managed_evidence(self.manifest.mode) {
            self.manifest.primary_pass = None;
            self.contribution_maps = false;
            self.focus_evidence = false;
        }
        if !reconstruction_available(self.manifest.mode) {
            self.original_cfa_reconstruction = false;
        }
        if !precision_available(self.manifest.mode, self.manifest.passes.len()) {
            self.precision_weights = false;
        }
        if !reproducibility_available(self.manifest.mode, self.manifest.passes.len()) {
            self.reproducibility = false;
        }
    }

    pub(crate) fn groups(&self, scan: &StackScan) -> Result<Vec<CaptureGroup>> {
        let mut cursor = 0;
        let mut groups = Vec::new();
        for (index, pass) in self.manifest.passes.iter().enumerate() {
            let start = cursor;
            let mut segment_ends = Vec::new();
            for directory in &pass.directories {
                let before = cursor;
                while cursor < scan.frames.len()
                    && scan.frames[cursor].path.parent() == Some(directory.as_path())
                {
                    cursor += 1;
                }
                ensure!(
                    cursor > before,
                    "Session source segment differs from the imported scan"
                );
                segment_ends.push(cursor);
            }
            groups.push(CaptureGroup {
                pass_index: index,
                name: pass.name.clone(),
                range: start..cursor,
                segment_ends,
                primary: self.manifest.primary_pass == Some(index),
            });
        }
        ensure!(
            cursor == scan.frames.len(),
            "Imported source count differs from the session layout"
        );
        Ok(groups)
    }
    pub(crate) fn move_pass(&mut self, from: usize, to: usize) {
        self.manifest.passes.swap(from, to);
        self.manifest.primary_pass = self.manifest.primary_pass.map(|index| {
            if index == from {
                to
            } else if index == to {
                from
            } else {
                index
            }
        });
    }
    pub(crate) fn remove_pass(&mut self, index: usize) {
        self.manifest.passes.remove(index);
        self.manifest.primary_pass = self.manifest.primary_pass.and_then(|primary| {
            if primary == index {
                None
            } else {
                Some(primary - usize::from(primary > index))
            }
        });
        self.normalize_mode_options();
    }
    pub(crate) fn first_directory(&self) -> &Path {
        &self.manifest.passes[0].directories[0]
    }
}

pub(crate) const MODES: [SessionMode; 7] = [
    SessionMode::Combine,
    SessionMode::Interleave,
    SessionMode::Repeat,
    SessionMode::Hdr,
    SessionMode::Layers,
    SessionMode::Mosaic,
    SessionMode::IndependentViews,
];

pub(crate) fn output_prefix(mode: SessionMode) -> Option<&'static str> {
    match mode {
        SessionMode::Layers => Some("layer"),
        SessionMode::IndependentViews => Some("view"),
        _ => None,
    }
}

pub(crate) fn primary_available(mode: SessionMode) -> bool {
    !matches!(mode, SessionMode::Mosaic | SessionMode::IndependentViews)
}

pub(crate) fn managed_evidence(mode: SessionMode) -> bool {
    !primary_available(mode)
}

pub(crate) fn reconstruction_available(mode: SessionMode) -> bool {
    matches!(
        mode,
        SessionMode::Combine | SessionMode::Interleave | SessionMode::Repeat | SessionMode::Hdr
    )
}

pub(crate) fn precision_available(mode: SessionMode, pass_count: usize) -> bool {
    pass_count >= 2 && matches!(mode, SessionMode::Repeat | SessionMode::Hdr)
}

pub(crate) fn reproducibility_available(mode: SessionMode, pass_count: usize) -> bool {
    pass_count >= 2
        && matches!(
            mode,
            SessionMode::Combine
                | SessionMode::Interleave
                | SessionMode::Repeat
                | SessionMode::Layers
        )
}
pub(crate) fn mode_label(mode: SessionMode) -> &'static str {
    match mode {
        SessionMode::Combine => "Combine detail",
        SessionMode::Interleave => "Interleaved focus",
        SessionMode::Repeat => "Repeated captures",
        SessionMode::Hdr => "Exposure range",
        SessionMode::Layers => "Aligned layers",
        SessionMode::Mosaic => "Wider mosaic",
        SessionMode::IndependentViews => "Independent views",
    }
}
pub(crate) fn mode_description(mode: SessionMode) -> &'static str {
    match mode {
        SessionMode::IndependentViews => {
            "Keep each viewpoint in its own coordinates, with a photograph, linear master and focus evidence. No views are joined."
        }
        SessionMode::Combine => "Gather useful detail from related passes of the same subject.",
        SessionMode::Interleave => {
            "Combine complementary focus positions across passes. Each pass keeps its own capture order."
        }
        SessionMode::Repeat => {
            "Test proposed repeats for agreement before combining their observations. Uncertain matches stay separate."
        }
        SessionMode::Hdr => {
            "Use compatible exposure passes to extend highlight and shadow coverage."
        }
        SessionMode::Layers => {
            "Save one aligned photograph and linear master per pass, with a shared frame."
        }
        SessionMode::Mosaic => {
            "Join overlapping views into a wider photograph. Unsupported regions remain transparent."
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) enum SessionChoose {
    Pass,
    Segment(usize),
}

#[derive(Default)]
pub(crate) struct SessionUi {
    pub chooser: Option<SessionChoose>,
    pub groups: Vec<CaptureGroup>,
    pub layers: Vec<PathBuf>,
    pub summary: Option<SessionSummary>,
    pub metadata_start: usize,
    pub metadata_directory: Option<PathBuf>,
    pub pending_name: Option<String>,
}

#[cfg(test)]
#[path = "session-workspace-tests.rs"]
mod tests;
