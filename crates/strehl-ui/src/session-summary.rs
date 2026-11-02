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
    /// Best result photographs of passes it did not blend.
    pub alternatives: Vec<SummaryAlternative>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SummaryAlternative {
    pub pass: String,
    pub reason: String,
    pub photograph: PathBuf,
}

#[derive(Deserialize)]
struct CompletionAlternative {
    directory: String,
    pass: String,
    reason: String,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SummaryPass {
    pub name: String,
    pub range: std::ops::Range<usize>,
    pub placed: Option<usize>,
    /// Best result: what this pass contributed, from the saved plan and
    /// render report.
    pub contribution: Option<PassContribution>,
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PassContribution {
    /// Short role and outcome, e.g. "Lighting layer · averaged in".
    pub label: String,
    pub used: bool,
    /// Measured detail, e.g. alignment and coverage.
    pub detail: Option<String>,
    /// The planner's full reason.
    pub reason: Option<String>,
}

#[derive(Deserialize)]
struct Plan {
    passes: Vec<PlanPass>,
}
#[derive(Deserialize)]
struct PlanPass {
    pass: usize,
    role: String,
    reason: Option<String>,
}
#[derive(Deserialize, Default)]
struct RenderReport {
    #[serde(default)]
    lighting_fusion: Option<Fusion>,
    #[serde(default)]
    lighting_groups: Vec<GroupSummary>,
    #[serde(default)]
    detached_layers: Vec<DetachedReport>,
    /// Set when the photograph was built on another view than the planned
    /// anchor's (more passes agreed with it).
    #[serde(default)]
    view_anchor_pass: Option<usize>,
}
#[derive(Deserialize)]
struct DetachedReport {
    pass: String,
    #[serde(default)]
    placement: Option<Placement>,
    #[serde(default)]
    error: Option<String>,
}
#[derive(Deserialize)]
struct Placement {
    scale: f64,
    rotation_deg: f64,
    accepted: bool,
}
#[derive(Deserialize)]
struct Fusion {
    layers: Vec<FusionLayer>,
}
#[derive(Deserialize)]
struct FusionLayer {
    group: usize,
    outcome: String,
    residual_before: Option<Residual>,
    residual_after: Option<Residual>,
    coverage: Option<f64>,
    agreement: Option<f64>,
    sharp_fraction: Option<f64>,
}
#[derive(Deserialize)]
struct Residual {
    median_px: f64,
}
#[derive(Deserialize)]
struct GroupSummary {
    #[serde(default)]
    passes: Vec<String>,
}

/// Contribution of each pass from a saved Best result plan; `None` when the
/// directory holds no plan (other modes or older results).
pub(crate) fn contributions(output: &Path, names: &[String]) -> Option<Vec<PassContribution>> {
    let plan: Plan = read(&output.join("plan.json")).ok()?;
    let report: RenderReport = read(&output.join("render-report.json")).unwrap_or_default();
    let layer_of = |name: &str| -> Option<&FusionLayer> {
        let group = report
            .lighting_groups
            .iter()
            .enumerate()
            .skip(1)
            .find(|(_, g)| g.passes.len() == 1 && g.passes[0] == name)?
            .0;
        report
            .lighting_fusion
            .as_ref()?
            .layers
            .iter()
            .find(|l| l.group == group)
    };
    let mut out = vec![None; names.len()];
    for p in &plan.passes {
        let Some(name) = names.get(p.pass) else {
            continue;
        };
        let percent = |v: f64| format!("{:.0}%", 100.0 * v);
        let view = report.view_anchor_pass;
        let (label, used, detail) = match p.role.as_str() {
            _ if view == Some(p.pass) => (
                "Primary reference · the view most passes share".to_owned(),
                true,
                None,
            ),
            "anchor" if view.is_some() => (
                "Not used: shows another view of the subject".to_owned(),
                false,
                None,
            ),
            "anchor" => (
                "Primary reference · framing and colour".to_owned(),
                true,
                None,
            ),
            "combine" => ("Combined".to_owned(), true, None),
            "exposure_normalized" => ("Combined · exposure corrected".to_owned(), true, None),
            role @ ("lighting_layer" | "pose_layer" | "detached_layer") => {
                let kind = match role {
                    "pose_layer" => "Pose layer",
                    "detached_layer" => "Detached layer",
                    _ => "Lighting layer",
                };
                let detached = report.detached_layers.iter().find(|d| &d.pass == name);
                let placed = detached
                    .and_then(|d| d.placement.as_ref())
                    .filter(|p| p.accepted)
                    .map(|p| format!("placed x{:.2} at {:.0}°", p.scale, p.rotation_deg));
                match layer_of(name) {
                    Some(l) if l.outcome == "superposed" => {
                        let mut parts: Vec<String> = placed.into_iter().collect();
                        if let (Some(a), Some(b)) = (&l.residual_before, &l.residual_after) {
                            parts.push(format!(
                                "aligned {:.1} → {:.1} px",
                                a.median_px, b.median_px
                            ));
                        }
                        if let Some(s) = l.sharp_fraction {
                            parts.push(format!("sharp {}", percent(s)));
                        }
                        if let Some(c) = l.coverage {
                            parts.push(format!("covers {}", percent(c)));
                        }
                        if let Some(a) = l.agreement {
                            parts.push(format!("matches {}", percent(a)));
                        }
                        (
                            format!("{kind} · averaged in"),
                            true,
                            Some(parts.join(" · ")),
                        )
                    }
                    Some(l) if l.outcome == "appearance_differs" => (
                        format!("{kind} · not used: colour differs (another lighting)"),
                        false,
                        None,
                    ),
                    Some(l) if l.outcome == "defocused" => {
                        (format!("{kind} · not used: out of focus"), false, None)
                    }
                    Some(_) => (format!("{kind} · not used: no usable overlap"), false, None),
                    None => match detached {
                        Some(d) if d.error.is_some() => (
                            format!("{kind} · not used: could not be stacked on its own"),
                            false,
                            d.error.clone(),
                        ),
                        Some(_) => (
                            format!("{kind} · not used: not found on the primary"),
                            false,
                            None,
                        ),
                        None => (format!("{kind} · not used"), false, None),
                    },
                }
            }
            _ => ("Not used".to_owned(), false, None),
        };
        out[p.pass] = Some(PassContribution {
            label,
            used,
            detail,
            reason: p.reason.clone(),
        });
    }
    out.into_iter().collect()
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
    #[serde(default)]
    alternatives: Vec<CompletionAlternative>,
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
                    contribution: None,
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
            alternatives: Vec::new(),
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
            summary.alternatives = completion
                .alternatives
                .iter()
                .filter(|a| {
                    // Only plain sibling directories of this result.
                    !a.directory.is_empty()
                        && a.directory
                            .chars()
                            .all(|c| c.is_ascii_alphanumeric() || c == '-')
                })
                .map(|a| SummaryAlternative {
                    pass: a.pass.clone(),
                    reason: a.reason.clone(),
                    photograph: output.join(&a.directory).join("photograph.tiff"),
                })
                .filter(|a| a.photograph.is_file())
                .collect();
            let names: Vec<String> = summary.passes.iter().map(|p| p.name.clone()).collect();
            if let Some(list) = contributions(&output, &names) {
                for (pass, mut contribution) in summary.passes.iter_mut().zip(list) {
                    if !contribution.used
                        && contribution.detail.is_none()
                        && summary.alternatives.iter().any(|a| a.pass == pass.name)
                    {
                        contribution.detail =
                            Some("Saved as its own photograph (see Also saved)".to_owned());
                    }
                    pass.contribution = Some(contribution);
                }
            }
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn contributions_label_each_pass_from_plan_and_report() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(
            dir.path().join("plan.json"),
            r#"{"passes":[
                {"pass":0,"role":"anchor","reason":null},
                {"pass":1,"role":"lighting_layer","reason":"other lighting"},
                {"pass":2,"role":"lighting_layer","reason":null},
                {"pass":3,"role":"detached_layer","reason":"not joined"}
            ]}"#,
        )
        .unwrap();
        std::fs::write(
            dir.path().join("render-report.json"),
            r#"{"lighting_groups":[{"passes":["a"]},{"passes":["b"]},{"passes":["c"]}],
                "lighting_fusion":{"layers":[
                    {"group":1,"outcome":"superposed","residual_before":{"median_px":0.8},
                     "residual_after":{"median_px":0.1},"coverage":0.54,"agreement":null,"sharp_fraction":0.99},
                    {"group":2,"outcome":"defocused","residual_before":null,"residual_after":null,
                     "coverage":null,"agreement":null,"sharp_fraction":null}]},
                "detached_layers":[{"pass":"d","placement":null,"error":"too few frames"}]}"#,
        )
        .unwrap();
        let names: Vec<String> = ["a", "b", "c", "d"].map(String::from).to_vec();
        let got = contributions(dir.path(), &names).expect("plan present");
        assert_eq!(got[0].label, "Primary reference · framing and colour");
        assert!(got[0].used);
        assert_eq!(got[1].label, "Lighting layer · averaged in");
        assert_eq!(
            got[1].detail.as_deref(),
            Some("aligned 0.8 → 0.1 px · sharp 99% · covers 54%")
        );
        assert_eq!(got[1].reason.as_deref(), Some("other lighting"));
        assert_eq!(got[2].label, "Lighting layer · not used: out of focus");
        assert!(!got[2].used);
        assert_eq!(
            got[3].label,
            "Detached layer · not used: could not be stacked on its own"
        );
        assert_eq!(got[3].detail.as_deref(), Some("too few frames"));
        // No plan: other modes and older results show no contributions.
        let empty = tempfile::tempdir().unwrap();
        assert!(contributions(empty.path(), &names).is_none());
    }
}
