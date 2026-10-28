//! Vendor-neutral, local collaboration. The UI owns every operation; this
//! module never opens an arbitrary image, executes a shell, or calls a model.
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::collections::BTreeMap;

#[path = "agent-control.rs"]
mod control;
pub(crate) use control::run_control_from_args;

#[path = "agent-bridge.rs"]
mod bridge;
#[path = "agent-mcp.rs"]
mod mcp;
pub(crate) use bridge::{AgentBridge, IncomingRequest, resolve_granted_path};
pub(crate) use mcp::run_mcp_from_args;

pub(crate) const MAX_RECIPE_BYTES: usize = 2 * 1024 * 1024;
// The recipe sidecar has a fixed 2 MiB budget. Leave a bounded allowance for
// JSON-RPC/request metadata; never grow the mailbox based on caller input.
pub(crate) const MAX_REQUEST_BYTES: usize = MAX_RECIPE_BYTES + 64 * 1024;
pub(crate) const MAX_REPLY_BYTES: usize = 8 * 1024 * 1024;
pub(crate) const MAX_PREVIEW_SIDE: u32 = 1024;
pub(crate) const PROTOCOL_VERSION: &str = "2025-11-25";

pub(crate) use strehl_edit::RegionShape as Region;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum IssueKind {
    OcclusionHalo,
    BrightSpot,
    Alignment,
    Noise,
    Colour,
    Exposure,
    FocusGap,
    Other,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Annotation {
    pub id: String,
    pub label: String,
    pub kind: IssueKind,
    pub region: Region,
    #[serde(default)]
    pub note: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub(crate) enum PreviewTarget {
    Final,
    Source { frame: usize },
    Diagnostic { name: String, level: usize },
}

/// JSON scalars only. Null restores the engine's default for optional fields.
/// Unknown keys are rejected before the request reaches the UI.
pub(crate) type SettingsPatch = BTreeMap<String, Value>;

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CatalogSessionPass {
    pub name: String,
    /// Existing catalog stacks, in continuation order; no arbitrary filesystem paths.
    pub stack_ids: Vec<u64>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(crate) enum AdaptiveDevelopIntent {
    #[default]
    Balance,
    Highlights,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "operation", rename_all = "snake_case", deny_unknown_fields)]
pub(crate) enum AgentCommand {
    Snapshot {},
    /// Inspect one imported source without selecting it or opening a report.
    Metadata {
        frame: usize,
    },
    /// Save and close an idle headless workspace; completion is process exit.
    Shutdown {},
    Probe {
        region: Region,
        #[serde(default = "default_sources")]
        max_sources: usize,
    },
    Preview {
        target: PreviewTarget,
        #[serde(default)]
        region: Option<Region>,
        #[serde(default = "default_side")]
        max_side: u32,
    },
    SelectStack {
        id: u64,
    },
    SelectRun {
        stack_id: u64,
        run_index: usize,
    },
    SelectSource {
        frame: usize,
    },
    SetSettings {
        patch: SettingsPatch,
    },
    /// The application's editing module validates the entire recipe atomically.
    SetDevelop {
        recipe: strehl_edit::DevelopmentRecipe,
    },
    /// Portable manual controls; measured fields and region geometry survive.
    SetAdjustments {
        adjustments: strehl_edit::Adjustments,
        #[serde(default)]
        region_id: Option<String>,
    },
    /// Explicitly remove the measured Adaptive treatment in one scope.
    ClearAdaptive {
        #[serde(default)]
        region_id: Option<String>,
    },
    /// Queue a bounded scene analysis and apply its editable suggested controls.
    AdaptiveDevelop {
        strength: f32,
        #[serde(default)]
        intent: AdaptiveDevelopIntent,
    },
    Annotate {
        annotation: Annotation,
    },
    RemoveAnnotation {
        id: String,
    },
    SetView {
        center: [f32; 2],
        zoom: f32,
    },
    StartStack {},
    CancelStack {},
    /// The destination is the app's selected export folder; never an arbitrary path.
    SaveEditVersion {
        name: String,
    },
    RestoreEditVersion {
        id: String,
    },
    Export {
        file_name: String,
        format: String,
        #[serde(default)]
        color_space: Option<strehl_edit::OutputColorSpace>,
        #[serde(default)]
        hdr: Option<bool>,
        #[serde(default)]
        quality: Option<u8>,
        #[serde(default)]
        speed: Option<u8>,
    },
    Undo {},
    Redo {},
    CreateProject {
        name: String,
        #[serde(default)]
        parent_id: Option<u64>,
    },
    RenameNode {
        id: u64,
        name: String,
    },
    /// A grant identifies a folder explicitly shared by the human in Strehl.
    ImportStack {
        grant_id: String,
        relative_path: String,
        name: String,
        #[serde(default)]
        parent_id: Option<u64>,
    },
    /// Compose already imported catalog stacks into ordered pass segments.
    CreateSession {
        name: String,
        passes: Vec<CatalogSessionPass>,
        mode: strehl_cli::session_input::SessionMode,
        #[serde(default)]
        primary_pass: Option<usize>,
        memory_limit_gib: f64,
        #[serde(default)]
        parent_id: Option<u64>,
    },
    ImportPreset {
        grant_id: String,
        relative_path: String,
    },
    /// A suggestion is visible in-app and does not change the photograph.
    Suggest {
        title: String,
        rationale: String,
        #[serde(default)]
        region: Option<Region>,
    },
}

fn default_sources() -> usize {
    12
}
fn default_side() -> u32 {
    768
}

impl AgentCommand {
    pub(crate) fn is_read_only(&self) -> bool {
        matches!(
            self,
            Self::Snapshot {} | Self::Metadata { .. } | Self::Probe { .. } | Self::Preview { .. }
        )
    }

    pub(crate) fn validate(&self) -> Result<(), String> {
        match self {
            // The current imported bracket bounds this zero-based index at dispatch.
            // No caller-supplied source or output path is accepted.
            Self::Metadata { .. } => Ok(()),
            Self::Probe {
                region,
                max_sources,
            } => {
                region.validate().map_err(|e| e.to_string())?;
                ensure((1..=32).contains(max_sources), "max_sources must be 1..32")
            }
            Self::Preview {
                target,
                region,
                max_side,
            } => {
                ensure(
                    (64..=MAX_PREVIEW_SIDE).contains(max_side),
                    "max_side must be 64..1024",
                )?;
                if let Some(region) = region {
                    region.validate().map_err(|e| e.to_string())?;
                }
                if let PreviewTarget::Diagnostic { name, level } = target {
                    ensure(
                        [
                            "admission",
                            "fallback",
                            "confidence",
                            "detail",
                            "coverage",
                            "alignment",
                        ]
                        .contains(&name.as_str()),
                        "Unknown diagnostic surface",
                    )?;
                    ensure(*level <= 11, "Diagnostic level must be 0..11")?;
                }
                Ok(())
            }
            Self::SetSettings { patch } => validate_settings(patch),
            Self::SetDevelop { recipe } => {
                recipe.validate().map_err(|e| e.to_string())?;
                // Match the durable sidecar representation, not compact wire
                // JSON: indentation can dominate a large polygon recipe.
                let bytes = serde_json::to_vec_pretty(recipe).map_err(|e| e.to_string())?;
                ensure(
                    bytes.len() <= MAX_RECIPE_BYTES,
                    "Recipe exceeds the 2 MiB limit",
                )
            }
            Self::SetAdjustments {
                adjustments,
                region_id,
            } => {
                adjustments.validate().map_err(|e| e.to_string())?;
                validate_region_id(region_id)
            }
            Self::ClearAdaptive { region_id } => validate_region_id(region_id),
            Self::AdaptiveDevelop { strength, .. } => ensure(
                strength.is_finite() && (0.0..=1.0).contains(strength),
                "Adaptive amount must be between 0 and 1",
            ),
            Self::Annotate { annotation } => {
                identifier(&annotation.id)?;
                text_bound(&annotation.label, 120, false)?;
                text_bound(&annotation.note, 4000, true)?;
                annotation.region.validate().map_err(|e| e.to_string())
            }
            Self::RemoveAnnotation { id } => identifier(id),
            Self::SetView { center, zoom } => ensure(
                center
                    .iter()
                    .all(|v| v.is_finite() && (0.0..=1.0).contains(v))
                    && zoom.is_finite()
                    && (1.0..=8.0).contains(zoom),
                "View center must be normalized and zoom must be 1..8",
            ),
            Self::SaveEditVersion { name } => ensure(
                !name.trim().is_empty()
                    && name.trim().chars().count() <= 120
                    && name.len() <= 384
                    && !name.chars().any(char::is_control),
                "Version name must be 1..120 characters without control characters",
            ),
            Self::RestoreEditVersion { id } => ensure(
                id.len() == 32
                    && id
                        .bytes()
                        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)),
                "Use the exact saved version ID from photo_history.versions",
            ),
            Self::Export {
                file_name,
                format,
                color_space,
                hdr,
                quality,
                speed,
            } => {
                safe_file_name(file_name)?;
                resolve_export_settings(format, *color_space, *hdr, *quality, *speed, None)
                    .map(|_| ())
            }
            Self::CreateProject { name, .. } | Self::RenameNode { name, .. } => {
                text_bound(name, 160, false)
            }
            Self::ImportStack {
                grant_id,
                relative_path,
                name,
                ..
            } => {
                identifier(grant_id)?;
                safe_relative_path(relative_path)?;
                text_bound(name, 160, false)
            }
            Self::ImportPreset {
                grant_id,
                relative_path,
            } => {
                identifier(grant_id)?;
                safe_relative_path(relative_path)
            }
            Self::CreateSession {
                name,
                passes,
                primary_pass,
                memory_limit_gib,
                ..
            } => {
                text_bound(name, 160, false)?;
                ensure(
                    !passes.is_empty() && passes.len() <= 64,
                    "Use 1..64 explicit passes",
                )?;
                ensure(
                    primary_pass.is_none_or(|index| index < passes.len()),
                    "Primary pass is outside the session",
                )?;
                ensure(
                    memory_limit_gib.is_finite() && (1.0..=4096.0).contains(memory_limit_gib),
                    "RAM budget must be 1..4096 GiB",
                )?;
                for pass in passes {
                    text_bound(&pass.name, 160, false)?;
                    ensure(
                        !pass.stack_ids.is_empty() && pass.stack_ids.len() <= 256,
                        "Each pass needs 1..256 existing source stacks",
                    )?;
                }
                Ok(())
            }
            Self::Suggest {
                title,
                rationale,
                region,
            } => {
                text_bound(title, 160, false)?;
                text_bound(rationale, 8000, false)?;
                if let Some(region) = region {
                    region.validate().map_err(|e| e.to_string())?;
                }
                Ok(())
            }
            _ => Ok(()),
        }
    }
}

fn validate_region_id(id: &Option<String>) -> Result<(), String> {
    if let Some(id) = id {
        ensure(
            !id.is_empty() && id.len() <= 128 && !id.chars().any(char::is_control),
            "region_id must be a nonempty region ID of at most 128 bytes",
        )?;
    }
    Ok(())
}

/// Missing options use the same defaults as the human Export pane. Only an
/// omitted HDR flag adapts to the input; an explicit unsupported HDR request is
/// rejected rather than silently becoming SDR.
pub(crate) fn resolve_export_settings(
    format: &str,
    color_space: Option<strehl_edit::OutputColorSpace>,
    hdr: Option<bool>,
    quality: Option<u8>,
    speed: Option<u8>,
    origin: Option<strehl_edit::ImageOrigin>,
) -> Result<strehl_edit::ExportSettings, String> {
    use strehl_edit::{ExportFormat, ExportSettings, ImageOrigin};
    let format = match format {
        "avif" => ExportFormat::Avif,
        "tiff" => ExportFormat::Tiff,
        "png" => ExportFormat::Png,
        "jpeg" => ExportFormat::Jpeg,
        _ => return Err("Format must be avif, tiff, png or jpeg".into()),
    };
    let defaults = ExportSettings::default();
    let settings = ExportSettings {
        format,
        color_space: color_space.unwrap_or(defaults.color_space),
        hdr: hdr.unwrap_or(
            format == ExportFormat::Avif && origin != Some(ImageOrigin::DisplayReferred),
        ),
        quality: quality.unwrap_or(defaults.quality),
        speed: speed.unwrap_or(defaults.speed),
    };
    settings.validate().map_err(|e| e.to_string())?;
    ensure(
        !settings.hdr || origin != Some(ImageOrigin::DisplayReferred),
        "HDR export requires a scene-linear master. This photograph is SDR; request hdr:false to preserve its actual range.",
    )?;
    Ok(settings)
}

fn ensure(ok: bool, message: &str) -> Result<(), String> {
    ok.then_some(()).ok_or_else(|| message.to_owned())
}
fn text_bound(s: &str, max: usize, empty: bool) -> Result<(), String> {
    ensure(
        (empty || !s.trim().is_empty()) && s.len() <= max && !s.contains('\0'),
        "Text is empty, too long, or contains a NUL",
    )
}
fn identifier(s: &str) -> Result<(), String> {
    ensure(
        !s.is_empty()
            && s.len() <= 80
            && s.bytes()
                .all(|b| b.is_ascii_alphanumeric() || b"-_".contains(&b)),
        "Identifier must contain 1..80 ASCII letters, digits, hyphens or underscores",
    )
}
pub(crate) fn safe_relative_path(path: &str) -> Result<(), String> {
    ensure(
        path.len() <= 1024
            && !path.is_empty()
            && !path.starts_with(['/', '\\'])
            && !path.contains([':', '\0'])
            && path
                .split(['/', '\\'])
                .all(|part| part != ".." && !part.is_empty()),
        "Use a relative path within a human-shared folder, without parent traversal or a drive prefix",
    )
}
fn safe_file_name(name: &str) -> Result<(), String> {
    safe_relative_path(name)?;
    ensure(
        name.len() <= 200
            && !name.contains(['/', '\\'])
            && !name.ends_with([' ', '.'])
            && !name
                .chars()
                .any(|c| c.is_control() || "<>\"|?*".contains(c))
            && ![
                "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7",
                "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8",
                "LPT9", "CONIN$", "CONOUT$", "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
            ]
            .contains(
                &name
                    .split('.')
                    .next()
                    .unwrap_or("")
                    .trim_end_matches([' ', '.'])
                    .to_ascii_uppercase()
                    .as_str(),
            ),
        "Export needs an ordinary file name, not a path or device name",
    )
}

pub(crate) fn validate_settings(patch: &SettingsPatch) -> Result<(), String> {
    ensure(
        !patch.is_empty() && patch.len() <= 16,
        "Provide 1..16 settings",
    )?;
    for (name, value) in patch {
        let range = match name.as_str() {
            "exposure_ev" => Some((-12.0, 12.0, false, true)),
            "pyramid_gate" => Some((0.0, 8.0, false, true)),
            "pyramid_bands" => Some((1.0, 12.0, true, true)),
            "pyramid_exponent" => Some((0.5, 8.0, false, true)),
            "pyramid_sharpen" => Some((1.0, 2.0, false, true)),
            "frame_limit" => Some((1.0, 100_000.0, true, true)),
            "workers" => Some((1.0, 1024.0, true, false)),
            "binned" | "correct_lateral_ca" | "crop_to_coverage" | "auto_exposure"
            | "confidence_map" => {
                ensure(value.is_boolean(), &format!("{name} must be boolean"))?;
                None
            }
            "resampler" => {
                ensure(
                    value.as_str().is_some_and(|s| {
                        [
                            "nearest",
                            "bilinear",
                            "catmull-rom",
                            "clamped-catmull",
                            "lanczos2",
                            "lanczos3",
                        ]
                        .contains(&s)
                    }),
                    "Unknown resampler",
                )?;
                None
            }
            _ => return Err(format!("Unknown setting: {name}")),
        };
        if let Some((min, max, integer, nullable)) = range {
            ensure(
                (nullable && value.is_null())
                    || value.as_f64().is_some_and(|n| {
                        n.is_finite()
                            && n >= min
                            && n <= max
                            && (!integer || value.as_u64().is_some())
                    }),
                &format!("Invalid value for {name}"),
            )?;
        }
    }
    Ok(())
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct AgentRequest {
    #[serde(default)]
    pub expected_revision: Option<u64>,
    pub command: AgentCommand,
}
impl AgentRequest {
    pub(crate) fn validate(&self) -> Result<(), String> {
        self.command.validate()?;
        ensure(
            self.command.is_read_only() || self.expected_revision.is_some(),
            "Mutations require expected_revision from a fresh snapshot",
        )
    }
    pub(crate) fn check_revision(&self, actual: u64) -> Result<(), String> {
        self.validate()?;
        ensure(
            self.command.is_read_only() || self.expected_revision == Some(actual),
            "Workspace changed; read a fresh snapshot and reconsider the command",
        )
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct AgentImage {
    pub mime_type: String,
    pub data: String,
}
impl AgentImage {
    pub(crate) fn png(bytes: &[u8]) -> Result<Self, String> {
        ensure(
            bytes.len() <= 5 * 1024 * 1024
                && bytes.len() >= 24
                && bytes.starts_with(b"\x89PNG\r\n\x1a\n"),
            "Preview must be a bounded PNG",
        )?;
        let width = u32::from_be_bytes(bytes[16..20].try_into().unwrap());
        let height = u32::from_be_bytes(bytes[20..24].try_into().unwrap());
        ensure(
            width > 0 && height > 0 && width.max(height) <= MAX_PREVIEW_SIDE,
            "Preview dimensions exceed 1024 pixels",
        )?;
        Ok(Self {
            mime_type: "image/png".into(),
            data: base64(bytes),
        })
    }
}

fn base64(bytes: &[u8]) -> String {
    const ALPHABET: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut result = String::with_capacity(bytes.len().div_ceil(3) * 4);
    for chunk in bytes.chunks(3) {
        let a = chunk[0] as usize;
        let b = chunk.get(1).copied().unwrap_or(0) as usize;
        let c = chunk.get(2).copied().unwrap_or(0) as usize;
        result.push(ALPHABET[a >> 2] as char);
        result.push(ALPHABET[((a & 3) << 4) | (b >> 4)] as char);
        result.push(if chunk.len() > 1 {
            ALPHABET[((b & 15) << 2) | (c >> 6)] as char
        } else {
            '='
        });
        result.push(if chunk.len() > 2 {
            ALPHABET[c & 63] as char
        } else {
            '='
        });
    }
    result
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct AgentReply {
    pub data: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub image: Option<AgentImage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}
impl AgentReply {
    pub(crate) fn success(data: Value) -> Self {
        Self {
            data,
            image: None,
            error: None,
        }
    }
    pub(crate) fn image(data: Value, image: AgentImage) -> Self {
        Self {
            data,
            image: Some(image),
            error: None,
        }
    }
    pub(crate) fn error(message: impl Into<String>) -> Self {
        Self {
            data: json!({}),
            image: None,
            error: Some(message.into()),
        }
    }
    fn into_tool_result(self) -> Value {
        if let Some(error) = self.error {
            return json!({"isError":true,"content":[{"type":"text","text":error}]});
        }
        let mut content = vec![json!({"type":"text","text":self.data.to_string()})];
        if let Some(image) = self.image {
            content.push(json!({"type":"image","mimeType":image.mime_type,"data":image.data}));
        }
        json!({"isError":false,"content":content,"structuredContent":self.data})
    }
}

#[cfg(test)]
#[path = "agent-interface-tests.rs"]
mod tests;
