//! Read retained evidence once; never reinterpret ordinary per-layer progress as a session total.
use super::*;
use anyhow::Context;

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SessionSummary {
    pub mode: SessionMode,
    pub frames: usize,
    pub passes: Vec<SummaryPass>,
    pub primary: Option<usize>,
    pub outputs: Vec<PathBuf>,
    pub completed: bool,
    pub ordinary_delegate: bool,
    pub geometry: Option<SummaryGeometry>,
    pub report_error: Option<String>,
    pub provenance: Option<String>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SummaryPass {
    pub name: String,
    pub range: std::ops::Range<usize>,
    pub placed: Option<usize>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SummaryGeometry {
    pub placed: usize,
    pub refused: usize,
    pub measured_edges: usize,
    pub cycle_rank: usize,
}

#[derive(Deserialize)]
struct Completion {
    schema: String,
    frames: usize,
    passes: usize,
    outputs: usize,
    primary_pass: Option<usize>,
    pipeline: Option<String>,
}
#[derive(Deserialize)]
struct Alignment {
    report: Geometry,
}
#[derive(Deserialize)]
struct Geometry {
    frames: usize,
    measured_edges: usize,
    anchor_component_cycle_rank: usize,
    passes: Vec<GeometryPass>,
}
#[derive(Deserialize)]
struct GeometryPass {
    pass_index: usize,
    frames: usize,
    placed: usize,
    refused: usize,
}

impl SessionSummary {
    pub fn load(directory: &Path, fallback: &SessionDraft) -> Self {
        Self::load_with_provenance(directory, fallback, None)
    }
    pub fn load_imported(directory: &Path, fallback: &SessionDraft, scope: &str) -> Self {
        Self::load_with_provenance(directory, fallback, Some(scope))
    }
    fn load_with_provenance(
        directory: &Path,
        fallback: &SessionDraft,
        scope: Option<&str>,
    ) -> Self {
        let saved: Result<SessionDraft> = if scope.is_some() {
            Ok(fallback.clone())
        } else {
            read(&directory.join("session-recipe.json"))
        };
        let draft = saved.as_ref().unwrap_or(fallback);
        let mut start = 0;
        let passes = draft
            .manifest
            .passes
            .iter()
            .map(|pass| {
                let count = draft
                    .sources
                    .iter()
                    .filter(|source| {
                        source.path.parent().is_some_and(|parent| {
                            pass.directories.iter().any(|path| path == parent)
                        })
                    })
                    .count();
                let range = start..start + count;
                start += count;
                SummaryPass {
                    name: pass.name.clone(),
                    range,
                    placed: None,
                }
            })
            .collect();
        let output = if scope.is_some() {
            directory.to_path_buf()
        } else {
            directory.join("session-output")
        };
        let outputs =
            if let Some(prefix) = crate::session_workspace::output_prefix(draft.manifest.mode) {
                (0..draft.manifest.passes.len())
                    .map(|i| {
                        output
                            .join(format!("{prefix}-{:02}", i + 1))
                            .join("photograph.tiff")
                    })
                    .collect()
            } else {
                vec![output.join("photograph.tiff")]
            };
        let mut summary = Self {
            mode: draft.manifest.mode,
            frames: draft.sources.len(),
            passes,
            primary: draft.manifest.primary_pass,
            outputs,
            completed: false,
            ordinary_delegate: false,
            geometry: None,
            report_error: None,
            provenance: scope.map(str::to_owned),
        };
        let receipt = (|| -> Result<()> {
            saved
                .as_ref()
                .map_err(|error| anyhow::anyhow!(error.to_string()))?;
            ensure!(
                start == summary.frames,
                "Saved source census does not match its pass folders"
            );
            let completion: Completion = read(&output.join("completed.json"))?;
            ensure!(
                completion.schema == "strehl.session-completion.v1"
                    && completion.frames == summary.frames
                    && completion.passes == summary.passes.len()
                    && completion.outputs == summary.outputs.len()
                    && completion.primary_pass == summary.primary,
                "Completion report does not match the saved session"
            );
            summary.completed = true;
            summary.ordinary_delegate =
                completion.pipeline.as_deref() == Some("ordinary-single-pass");
            let alignment = output.join("alignment.json");
            // An exact ordinary single-pass delegate has no joint geometry report.
            if !alignment.exists() {
                return Ok(());
            }
            let geometry: Alignment = read(&alignment)?;
            let geometry = geometry.report;
            ensure!(
                geometry.frames == summary.frames && geometry.passes.len() == summary.passes.len(),
                "Geometry report does not match the saved session"
            );
            let mut placed = 0;
            let mut refused = 0;
            for (i, pass) in geometry.passes.iter().enumerate() {
                ensure!(
                    pass.pass_index == i
                        && pass.frames == summary.passes[i].range.len()
                        && pass.placed.checked_add(pass.refused) == Some(pass.frames),
                    "Geometry pass census is inconsistent"
                );
                placed += pass.placed;
                refused += pass.refused;
            }
            for (pass, report) in summary.passes.iter_mut().zip(&geometry.passes) {
                pass.placed = Some(report.placed);
            }
            summary.geometry = Some(SummaryGeometry {
                placed,
                refused,
                measured_edges: geometry.measured_edges,
                cycle_rank: geometry.anchor_component_cycle_rank,
            });
            Ok(())
        })();
        if let Err(error) = receipt {
            summary.report_error = Some(format!("{error:#}"));
        }
        summary
    }

    pub fn layer(&self, output: Option<&Path>) -> Option<usize> {
        (crate::session_workspace::output_prefix(self.mode).is_some())
            .then(|| {
                self.outputs
                    .iter()
                    .position(|path| Some(path.as_path()) == output)
            })
            .flatten()
    }
}

fn read<T: serde::de::DeserializeOwned>(path: &Path) -> Result<T> {
    let file = std::fs::File::open(path).with_context(|| format!("Reading {}", path.display()))?;
    serde_json::from_reader(std::io::BufReader::new(file))
        .with_context(|| format!("Parsing {}", path.display()))
}
