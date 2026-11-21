//! The subject page (plan 7.3): one specimen with all of its stacks, each
//! stack's life on one line, the lineage from renders to versions to exports,
//! and a journal. Self-contained like the Library station: it reads the
//! catalog and returns `LibraryIntent`s; editing the subject is an intent too.
#![allow(
    dead_code,
    reason = "the subject page is composed into the shell in P4 stage 2"
)]
use crate::{
    library_paint::{self as paint, ButtonStyle, Glyph, LibraryPalette, Mark},
    library_previews::{LibraryPreviews, TILE_SIDE},
    library_station::{LibraryIntent, RigCapture},
    workspace_history::{
        Catalog, ImportGroup, NodeId, NodeKind, Optics, PhotoVersion, RunState, ScaleCalibration,
        ScaleSource, SourcesState, StackLifecycle, StepState, SubjectEdit, SubjectMeta, timestamp,
    },
    workspace_icons::Icon,
};
use eframe::egui::{
    self, Align2, Color32, CornerRadius, Pos2, Rect, Sense, TextureHandle, Ui, Vec2,
};
use std::{
    collections::HashMap,
    path::{Path, PathBuf},
};

pub(crate) const LEFT_WIDTH: f32 = 500.0;
const ROW: f32 = 116.0;
const LINEAGE: f32 = 158.0;
const JOURNAL_ROW: f32 = 34.0;
const MAX_JOURNAL: usize = 40;

pub(crate) struct SubjectInputs<'a> {
    pub catalog: &'a Catalog,
    /// Changes whenever the catalog does (for example `Catalog::generation`).
    pub revision: u64,
    pub subject: NodeId,
    pub previews: &'a mut LibraryPreviews,
    pub palette: &'a LibraryPalette,
    pub rig: Option<&'a RigCapture>,
    /// The Library's sources check (`LibraryStation::sources`).
    pub sources: &'a HashMap<NodeId, SourcesState>,
    /// Depth signatures from the Stack station: one value per plane.
    pub signatures: Option<&'a HashMap<NodeId, Vec<f32>>>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum StackOrder {
    #[default]
    Newest,
    Name,
}

#[derive(Clone, Debug)]
pub(crate) struct RenderItem {
    /// 1-based, oldest first, as "Render N".
    pub number: usize,
    pub directory: PathBuf,
    pub label: String,
    pub state: RunState,
    pub created: u64,
    pub frames: usize,
    pub output: PathBuf,
    pub versions: Vec<VersionItem>,
}
#[derive(Clone, Debug)]
pub(crate) struct VersionItem {
    pub version: PhotoVersion,
    pub exports: Vec<ExportItem>,
}
#[derive(Clone, Debug)]
pub(crate) struct ExportItem {
    pub path: PathBuf,
    pub name: String,
    pub detail: String,
    pub created: u64,
}
#[derive(Clone, Debug)]
pub(crate) struct StackRow {
    pub id: NodeId,
    pub name: String,
    pub source: PathBuf,
    pub planes: usize,
    pub bytes: u64,
    pub life: StackLifecycle,
    /// Saved renders newest first, then the first source.
    pub pictures: Vec<(PathBuf, bool)>,
    pub renders: Vec<RenderItem>,
    /// Newest render, version or export; else 0.
    pub last: u64,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct JournalLine {
    pub at: u64,
    pub mark: Mark,
    pub text: String,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Key {
    revision: u64,
    subject: NodeId,
    nodes: usize,
    runs: usize,
    versions: usize,
    exports: usize,
}
pub(crate) struct SubjectModel {
    key: Key,
    pub name: String,
    pub collection: Option<String>,
    pub notes: String,
    pub meta: SubjectMeta,
    /// Catalog order (oldest first); the page orders them for display.
    pub stacks: Vec<StackRow>,
    pub journal: Vec<JournalLine>,
    pub bytes: u64,
}
impl SubjectModel {
    pub(crate) fn build(catalog: &Catalog, subject: NodeId, revision: u64) -> Option<Self> {
        let node = catalog
            .node(subject)
            .filter(|n| n.kind == NodeKind::Subject)?;
        let meta = node.subject.clone().unwrap_or_else(|| SubjectMeta::new(0));
        let mut collection = None;
        let mut at = node.parent;
        let mut guard = 0;
        while let Some(id) = at {
            guard += 1;
            let Some(parent) = catalog.node(id).filter(|_| guard < 64) else {
                break;
            };
            collection = Some(parent.name.clone());
            at = parent.parent;
        }
        let mut journal = vec![JournalLine {
            at: meta.created,
            mark: Mark::Plain,
            text: format!("Subject \"{}\" created", node.name),
        }];
        let mut stacks = Vec::new();
        for stack in catalog.stacks_of(subject) {
            let Some(stack_node) = catalog.node(stack) else {
                continue;
            };
            let Some(draft) = stack_node.stack.as_ref() else {
                continue;
            };
            // A stack always has a lifecycle; skip a record that does not.
            let Some(life) = catalog.stack_lifecycle(stack) else {
                continue;
            };
            let mut renders = Vec::new();
            for (index, directory) in stack_node.revisions.iter().enumerate() {
                let Some(run) = catalog.runs.iter().find(|r| &r.directory == directory) else {
                    continue;
                };
                let state = RunState::of(&run.status);
                let versions: Vec<VersionItem> = catalog
                    .photo_versions
                    .iter()
                    .filter(|v| v.owner.run.as_ref() == Some(directory))
                    .map(|version| VersionItem {
                        exports: catalog
                            .photo_exports
                            .iter()
                            .filter(|e| e.version == version.id)
                            .map(|export| ExportItem {
                                name: export
                                    .path
                                    .file_name()
                                    .map(|n| n.to_string_lossy().into_owned())
                                    .unwrap_or_default(),
                                detail: format!(
                                    "{:?}{}",
                                    export.settings.format,
                                    if export.settings.hdr { " · HDR" } else { "" }
                                )
                                .to_uppercase(),
                                path: export.path.clone(),
                                created: export.created,
                            })
                            .collect(),
                        version: version.clone(),
                    })
                    .collect();
                journal.push(JournalLine {
                    at: run.created,
                    mark: match state {
                        RunState::Saved => Mark::Ok,
                        RunState::Stacking => Mark::Run,
                        RunState::Failed => Mark::Bad,
                        _ => Mark::Warn,
                    },
                    text: format!(
                        "Render {} of {}: {} · {} planes{}",
                        index + 1,
                        stack_node.name,
                        match state {
                            RunState::Saved => "saved",
                            RunState::Stacking => "stacking",
                            RunState::Failed => "failed",
                            RunState::Cancelled => "cancelled",
                            RunState::Interrupted => "interrupted",
                            RunState::Unknown => "unknown state",
                        },
                        run.frames,
                        if run.label == stack_node.name || run.label.is_empty() {
                            String::new()
                        } else {
                            format!(" · {}", run.label)
                        }
                    ),
                });
                for item in &versions {
                    journal.push(JournalLine {
                        at: item.version.created,
                        mark: Mark::Ok,
                        text: format!(
                            "Version \"{}\" developed from render {} of {}",
                            item.version.name,
                            index + 1,
                            stack_node.name
                        ),
                    });
                    for export in &item.exports {
                        journal.push(JournalLine {
                            at: export.created,
                            mark: Mark::Ok,
                            text: format!(
                                "Exported {} from version \"{}\"",
                                export.name, item.version.name
                            ),
                        });
                    }
                }
                renders.push(RenderItem {
                    number: index + 1,
                    directory: directory.clone(),
                    label: run.label.clone(),
                    state,
                    created: run.created,
                    frames: run.frames,
                    output: run.output.clone(),
                    versions,
                });
            }
            let mut pictures: Vec<(PathBuf, bool)> = renders
                .iter()
                .rev()
                .filter(|r| r.state == RunState::Saved)
                .take(3)
                .map(|r| (r.output.clone(), false))
                .collect();
            pictures.extend(draft.sources.first().map(|s| (s.path.clone(), true)));
            stacks.push(StackRow {
                id: stack,
                name: stack_node.name.clone(),
                source: draft.source.clone(),
                planes: draft.sources.len(),
                bytes: draft.sources.iter().map(|s| s.bytes).sum(),
                last: life.last_activity,
                life,
                pictures,
                renders,
            });
        }
        journal.retain(|line| line.at > 0);
        journal.sort_by_key(|line| std::cmp::Reverse(line.at));
        journal.truncate(MAX_JOURNAL);
        Some(Self {
            key: Key {
                revision,
                subject,
                nodes: catalog.nodes.len(),
                runs: catalog.runs.len(),
                versions: catalog.photo_versions.len(),
                exports: catalog.photo_exports.len(),
            },
            name: node.name.clone(),
            collection,
            notes: node.notes.clone(),
            bytes: stacks.iter().map(|s| s.bytes).sum(),
            meta,
            stacks,
            journal,
        })
    }
    /// Stack indices in display order.
    pub(crate) fn order(&self, order: StackOrder) -> Vec<usize> {
        let mut indices: Vec<usize> = (0..self.stacks.len()).collect();
        match order {
            // Newest activity first; never-rendered stacks by catalog order, newest last added first.
            StackOrder::Newest => indices.sort_by(|&a, &b| {
                self.stacks[b]
                    .last
                    .cmp(&self.stacks[a].last)
                    .then(b.cmp(&a))
            }),
            StackOrder::Name => indices.sort_by(|&a, &b| {
                self.stacks[a]
                    .name
                    .to_lowercase()
                    .cmp(&self.stacks[b].name.to_lowercase())
            }),
        }
        indices
    }
}

/// The inline editor's fields.
#[derive(Clone, Debug, Default, PartialEq)]
struct Draft {
    name: String,
    notes: String,
    camera: String,
    lens: String,
    entered: bool,
    um_per_px: String,
    slide: String,
    magnification: String,
    pitch_um: String,
    error: Option<String>,
}
impl Draft {
    fn of(model: &SubjectModel) -> Self {
        let optics = model.meta.optics.clone().unwrap_or_default();
        let mut draft = Self {
            name: model.name.clone(),
            notes: model.notes.clone(),
            camera: optics.camera,
            lens: optics.lens,
            ..Default::default()
        };
        if let Some(scale) = &model.meta.scale {
            match &scale.source {
                ScaleSource::Measured { slide } => {
                    draft.um_per_px = format!("{}", scale.um_per_px);
                    draft.slide.clone_from(slide);
                }
                ScaleSource::Entered {
                    magnification,
                    pitch_um,
                } => {
                    draft.entered = true;
                    draft.magnification = format!("{magnification}");
                    draft.pitch_um = format!("{pitch_um}");
                }
            }
        }
        draft
    }
    /// The edit to save, or why not.
    fn edit(&self) -> Result<(String, SubjectEdit), String> {
        let name = self.name.trim();
        if name.is_empty() {
            return Err("Give the subject a name".into());
        }
        let number = |text: &str, what: &str| {
            text.trim()
                .replace(',', ".")
                .parse::<f64>()
                .map_err(|_| format!("{what} must be a number"))
        };
        let scale = if self.entered {
            if self.magnification.trim().is_empty() && self.pitch_um.trim().is_empty() {
                None
            } else {
                Some(
                    ScaleCalibration::entered(
                        number(&self.magnification, "Magnification")?,
                        number(&self.pitch_um, "Pixel pitch")?,
                    )
                    .map_err(|e| e.to_string())?,
                )
            }
        } else if self.um_per_px.trim().is_empty() {
            None
        } else {
            Some(
                ScaleCalibration::measured(number(&self.um_per_px, "Scale")?, &self.slide)
                    .map_err(|e| e.to_string())?,
            )
        };
        let optics =
            (!self.camera.trim().is_empty() || !self.lens.trim().is_empty()).then(|| Optics {
                camera: self.camera.trim().to_owned(),
                lens: self.lens.trim().to_owned(),
            });
        Ok((
            name.to_owned(),
            SubjectEdit {
                notes: Some(self.notes.clone()),
                hero: None,
                optics: Some(optics),
                scale: Some(scale),
            },
        ))
    }
}

/// A depth series' identity (address, length) and the drawn width.
type SparkKey = (usize, usize, u32);

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct SubjectStats {
    pub model_builds: u64,
    pub spark_builds: u64,
    pub rows_painted: usize,
}

#[derive(Default)]
pub(crate) struct SubjectPage {
    pub order: StackOrder,
    /// The stack whose lineage is open.
    pub open: Option<NodeId>,
    focus_render: Option<PathBuf>,
    focus_version: Option<String>,
    editing: Option<Draft>,
    model: Option<SubjectModel>,
    /// Pooled depth signatures: (series identity, width) -> column heights.
    sparks: HashMap<NodeId, (SparkKey, Vec<f32>)>,
    stats: SubjectStats,
}

impl SubjectPage {
    pub(crate) fn stats(&self) -> SubjectStats {
        self.stats
    }
    pub(crate) fn model(&self) -> Option<&SubjectModel> {
        self.model.as_ref()
    }
    pub(crate) fn editing(&self) -> bool {
        self.editing.is_some()
    }

    fn refresh(&mut self, catalog: &Catalog, subject: NodeId, revision: u64) {
        let key = Key {
            revision,
            subject,
            nodes: catalog.nodes.len(),
            runs: catalog.runs.len(),
            versions: catalog.photo_versions.len(),
            exports: catalog.photo_exports.len(),
        };
        if self.model.as_ref().is_some_and(|m| m.key == key) {
            return;
        }
        if self.model.as_ref().is_none_or(|m| m.key.subject != subject) {
            self.open = None;
            self.focus_render = None;
            self.focus_version = None;
            self.editing = None;
            self.sparks.clear();
        }
        self.model = SubjectModel::build(catalog, subject, revision);
        self.stats.model_builds += 1;
        if self.open.is_none() {
            // Open the newest stack that has a render.
            self.open = self.model.as_ref().and_then(|m| {
                m.order(StackOrder::Newest)
                    .into_iter()
                    .map(|i| &m.stacks[i])
                    .find(|s| !s.renders.is_empty())
                    .map(|s| s.id)
            });
        }
    }

    pub(crate) fn show(&mut self, ui: &mut Ui, inputs: SubjectInputs<'_>) -> Option<LibraryIntent> {
        let SubjectInputs {
            catalog,
            revision,
            subject,
            previews,
            palette,
            rig,
            sources,
            signatures,
        } = inputs;
        let ctx = ui.ctx().clone();
        previews.poll(&ctx);
        self.refresh(catalog, subject, revision);
        let area = ui.max_rect();
        ui.painter_at(area)
            .rect_filled(area, CornerRadius::ZERO, palette.bg);
        let left = Rect::from_min_size(area.min, Vec2::new(LEFT_WIDTH, area.height()));
        let right = Rect::from_min_max(Pos2::new(left.right(), area.top()), area.max);
        let Some(model) = self.model.take() else {
            paint::text(
                ui.painter(),
                area.center(),
                Align2::CENTER_CENTER,
                "This subject no longer exists",
                14.0,
                palette.ink_2,
                None,
            );
            return Some(LibraryIntent::Back);
        };
        let mut intent = self.left_column(ui, left, &model, previews, palette);
        let found = self.right_column(
            ui, right, &model, catalog, previews, palette, rig, sources, signatures,
        );
        intent = intent.or(found);
        intent = intent.or(drops(ui, &model, subject));
        if !ui.ctx().wants_keyboard_input()
            && self.editing.is_none()
            && ui.input(|i| i.key_pressed(egui::Key::N))
        {
            intent = intent.or(Some(LibraryIntent::NewStackFromCamera {
                collection: None,
                subject: Some(subject),
            }));
        }
        self.model = Some(model);
        intent
    }

    fn left_column(
        &mut self,
        ui: &mut Ui,
        left: Rect,
        model: &SubjectModel,
        previews: &mut LibraryPreviews,
        palette: &LibraryPalette,
    ) -> Option<LibraryIntent> {
        let painter = ui.painter().clone();
        painter.rect_filled(left, CornerRadius::ZERO, palette.panel);
        paint::vline(
            &painter,
            left.right() - 1.0,
            left.top()..=left.bottom(),
            palette.line,
        );
        let x0 = left.left() + 22.0;
        let x1 = left.right() - 23.0;
        let mut intent = None;
        let back = paint::caps(
            &painter,
            Pos2::new(x0, left.top() + 16.0),
            Align2::LEFT_TOP,
            "‹ Library",
            10.5,
            palette.ink_2,
        );
        if ui
            .interact(
                back.expand(4.0),
                ui.id().with("subject-back"),
                Sense::click(),
            )
            .clicked()
        {
            intent = Some(LibraryIntent::Back);
        }
        let hero = Rect::from_min_size(Pos2::new(x0, left.top() + 42.0), Vec2::new(x1 - x0, 304.0));
        painter.rect_filled(hero, CornerRadius::ZERO, palette.raised);
        // The chosen picture, else the first of the newest stacks' that loads.
        let picture = model
            .meta
            .hero
            .iter()
            .map(|hero| (hero.clone(), false))
            .chain(
                model
                    .order(StackOrder::Newest)
                    .into_iter()
                    .flat_map(|i| model.stacks[i].pictures.iter().cloned()),
            )
            .find(|(path, source)| !previews.failed(path, *source, crate::library_previews::SIDE));
        if let Some((path, source)) = &picture
            && let Some(texture) = previews.file(path, *source)
        {
            LibraryPreviews::paint_cover(&painter, hero, &texture);
        }
        let mut y = hero.bottom() + 14.0;
        if let Some(draft) = self.editing.as_mut() {
            let (save, cancel) = editor(
                ui,
                Rect::from_min_max(Pos2::new(x0, y), Pos2::new(x1, left.bottom() - 60.0)),
                draft,
                palette,
            );
            if cancel {
                self.editing = None;
            } else if save {
                match draft.edit() {
                    Ok((name, edit)) => {
                        intent = intent.or(Some(LibraryIntent::EditSubject {
                            id: model.key.subject,
                            name,
                            edit,
                        }));
                        self.editing = None;
                    }
                    Err(error) => draft.error = Some(error),
                }
            }
        } else {
            let name = paint::text(
                &painter,
                Pos2::new(x0, y + 16.0),
                Align2::LEFT_CENTER,
                &model.name,
                26.0,
                palette.ink,
                Some(x1 - x0 - 140.0),
            );
            if let Some(collection) = &model.collection {
                paint::text(
                    &painter,
                    Pos2::new(name.right() + 10.0, y + 18.0),
                    Align2::LEFT_CENTER,
                    collection,
                    12.0,
                    palette.ink_2,
                    Some((x1 - name.right() - 90.0).max(20.0)),
                );
            }
            let edit = Rect::from_min_size(Pos2::new(x1 - 52.0, y + 5.0), Vec2::new(52.0, 22.0));
            let response = paint::button(
                ui,
                edit,
                "subject-edit",
                "Edit",
                None,
                ButtonStyle::Quiet,
                palette,
            );
            paint::glyph(
                &painter,
                Pos2::new(edit.left() - 2.0, edit.center().y),
                Glyph::Note,
                palette.ink_2,
            );
            if response.clicked() {
                self.editing = Some(Draft::of(model));
            }
            y += 40.0;
            if !model.notes.trim().is_empty() {
                y += paint::paragraph(
                    &painter,
                    Pos2::new(x0, y),
                    model.notes.trim(),
                    13.0,
                    palette.ink_2,
                    x1 - x0,
                    5,
                ) + 12.0;
            }
            y = optics_card(ui, &painter, x0, x1, y, model, palette, &mut self.editing);
            y = disk_card(&painter, x0, x1, y, model, palette);
            let _ = y;
        }
        let bottom = left.bottom() - 16.0 - 28.0;
        let add_label = "Add folders…";
        let add_width = paint::button_width(&painter, add_label, false, false);
        let add = Rect::from_min_size(
            Pos2::new(x1 - add_width, bottom),
            Vec2::new(add_width, 28.0),
        );
        let new = Rect::from_min_max(
            Pos2::new(x0, bottom),
            Pos2::new(add.left() - 8.0, bottom + 28.0),
        );
        let subject = Some(model.key.subject);
        if paint::button(
            ui,
            new,
            "subject-new-stack",
            "New stack of this subject",
            Some(Icon::Camera),
            ButtonStyle::Primary,
            palette,
        )
        .clicked()
        {
            intent = intent.or(Some(LibraryIntent::NewStackFromCamera {
                collection: None,
                subject,
            }));
        }
        if paint::button(
            ui,
            add,
            "subject-add-folders",
            add_label,
            None,
            ButtonStyle::Outline,
            palette,
        )
        .clicked()
        {
            intent = intent.or(Some(LibraryIntent::PickFolders {
                collection: None,
                subject,
            }));
        }
        intent
    }
    #[allow(clippy::too_many_arguments)]
    fn right_column(
        &mut self,
        ui: &mut Ui,
        right: Rect,
        model: &SubjectModel,
        catalog: &Catalog,
        previews: &mut LibraryPreviews,
        palette: &LibraryPalette,
        rig: Option<&RigCapture>,
        sources: &HashMap<NodeId, SourcesState>,
        signatures: Option<&HashMap<NodeId, Vec<f32>>>,
    ) -> Option<LibraryIntent> {
        let painter = ui.painter().clone();
        let x0 = right.left() + 26.0;
        let x1 = right.right() - 26.0;
        let top = right.top() + 18.0;
        let caption = paint::caps(
            &painter,
            Pos2::new(x0, top + 12.0),
            Align2::LEFT_CENTER,
            "Stacks",
            10.5,
            palette.ink_2,
        );
        paint::text(
            &painter,
            Pos2::new(caption.right() + 8.0, top + 12.0),
            Align2::LEFT_CENTER,
            &model.stacks.len().to_string(),
            12.5,
            palette.ink_2,
            None,
        );
        let labels = ["Newest first", "By name"];
        let width: f32 = labels
            .iter()
            .map(|l| {
                paint::galley(&painter, l, 12.0, Color32::WHITE, None)
                    .size()
                    .x
                    + 20.0
            })
            .sum();
        let selected = usize::from(self.order == StackOrder::Name);
        let (_, clicked) = paint::segments(
            ui,
            Pos2::new(x1 - width, top),
            "subject-order",
            &labels,
            selected,
            palette,
        );
        if let Some(index) = clicked {
            self.order = if index == 0 {
                StackOrder::Newest
            } else {
                StackOrder::Name
            };
        }
        let order = model.order(self.order);
        let content_height = order
            .iter()
            .map(|&i| {
                if self.open == Some(model.stacks[i].id) {
                    ROW + LINEAGE
                } else {
                    ROW
                }
            })
            .sum::<f32>()
            + 70.0
            + model.journal.len() as f32 * JOURNAL_ROW
            + 20.0;
        let body = Rect::from_min_max(Pos2::new(x0, top + 38.0), Pos2::new(x1, right.bottom()));
        let mut intent = None;
        let mut painted = 0;
        let now = timestamp();
        let history_root = catalog.history_root();
        ui.scope_builder(egui::UiBuilder::new().max_rect(body), |ui| {
            egui::ScrollArea::vertical()
                .id_salt("subject-stacks")
                .auto_shrink([false, false])
                .show_viewport(ui, |ui, viewport| {
                    ui.set_height(content_height);
                    let origin = ui.min_rect().min;
                    // The scroll bar keeps its own gutter.
                    let width = body.width() - 10.0;
                    let mut y = 0.0;
                    for &index in &order {
                        let stack = &model.stacks[index];
                        let open = self.open == Some(stack.id);
                        let height = if open { ROW + LINEAGE } else { ROW };
                        // Only rows in view are laid out.
                        if y + height >= viewport.min.y && y <= viewport.max.y {
                            let rect = Rect::from_min_size(
                                origin + Vec2::new(0.0, y),
                                Vec2::new(width, height),
                            );
                            let capturing = rig.is_some_and(|r| r.stack == Some(stack.id));
                            let moved = matches!(
                                sources.get(&stack.id),
                                Some(SourcesState::Missing | SourcesState::Partial { .. })
                            );
                            let signature =
                                signatures.and_then(|s| s.get(&stack.id)).map(Vec::as_slice);
                            let found = self.stack_row(
                                ui, rect, stack, previews, palette, capturing, moved, signature,
                                now,
                            );
                            intent = intent.take().or(found);
                            if open {
                                let lineage = Rect::from_min_max(
                                    Pos2::new(rect.left(), rect.top() + ROW),
                                    rect.max,
                                );
                                let found = self.lineage(
                                    ui,
                                    lineage,
                                    stack,
                                    previews,
                                    palette,
                                    history_root.as_deref(),
                                    now,
                                );
                                intent = intent.take().or(found);
                            }
                            painted += 1;
                        }
                        y += height;
                    }
                    paint::hline(
                        ui.painter(),
                        origin.x..=origin.x + width,
                        origin.y + y,
                        palette.line,
                    );
                    y += 26.0;
                    let caption = paint::caps(
                        ui.painter(),
                        Pos2::new(origin.x, origin.y + y),
                        Align2::LEFT_CENTER,
                        "Journal",
                        10.5,
                        palette.ink_2,
                    );
                    paint::text(
                        ui.painter(),
                        Pos2::new(caption.right() + 10.0, origin.y + y),
                        Align2::LEFT_CENTER,
                        "what was done, and with which settings",
                        12.5,
                        palette.ink_2,
                        None,
                    );
                    y += 20.0;
                    paint::hline(
                        ui.painter(),
                        origin.x..=origin.x + width,
                        origin.y + y,
                        palette.line,
                    );
                    for line in &model.journal {
                        if y + JOURNAL_ROW >= viewport.min.y && y <= viewport.max.y {
                            let row = Rect::from_min_size(
                                origin + Vec2::new(0.0, y),
                                Vec2::new(width, JOURNAL_ROW),
                            );
                            paint::text(
                                ui.painter(),
                                Pos2::new(row.left(), row.center().y),
                                Align2::LEFT_CENTER,
                                &paint::moment(line.at, now),
                                12.0,
                                palette.ink_3,
                                Some(104.0),
                            );
                            paint::mark(
                                ui.painter(),
                                Pos2::new(row.left() + 124.0, row.center().y),
                                line.mark,
                                palette,
                            );
                            paint::text(
                                ui.painter(),
                                Pos2::new(row.left() + 140.0, row.center().y),
                                Align2::LEFT_CENTER,
                                &line.text,
                                12.5,
                                palette.ink,
                                Some(width - 140.0),
                            );
                            paint::hline(
                                ui.painter(),
                                row.left()..=row.right(),
                                row.bottom() - 1.0,
                                palette.line,
                            );
                        }
                        y += JOURNAL_ROW;
                    }
                });
        });
        self.stats.rows_painted = painted;
        intent
    }

    #[allow(clippy::too_many_arguments)]
    fn stack_row(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        stack: &StackRow,
        previews: &mut LibraryPreviews,
        palette: &LibraryPalette,
        capturing: bool,
        moved: bool,
        signature: Option<&[f32]>,
        now: u64,
    ) -> Option<LibraryIntent> {
        let row = Rect::from_min_size(rect.min, Vec2::new(rect.width(), ROW));
        let response = ui.interact(row, ui.id().with(("subject-row", stack.id)), Sense::click());
        let painter = ui.painter().clone();
        if response.hovered() {
            painter.rect_filled(row, CornerRadius::ZERO, palette.raised);
        }
        paint::hline(&painter, row.left()..=row.right(), row.top(), palette.line);
        let thumb = Rect::from_min_size(row.min + Vec2::new(0.0, 14.0), Vec2::new(132.0, 88.0));
        painter.rect_filled(thumb, CornerRadius::ZERO, palette.raised);
        if let Some(texture) = previews.first_tile(&stack.pictures, TILE_SIDE, stack.id) {
            LibraryPreviews::paint_cover(&painter, thumb, &texture);
        }
        let button_rect = Rect::from_min_size(
            Pos2::new(row.right() - 112.0, row.center().y - 14.0),
            Vec2::new(112.0, 28.0),
        );
        let size_right = button_rect.left() - 18.0;
        let spark = Rect::from_min_size(
            Pos2::new(size_right - 118.0 - 18.0 - 230.0, row.center().y - 23.0),
            Vec2::new(230.0, 46.0),
        );
        let info_left = thumb.right() + 18.0;
        let info_width = (spark.left() - 18.0 - info_left).max(40.0);
        paint::text(
            &painter,
            Pos2::new(info_left, row.top() + 30.0),
            Align2::LEFT_CENTER,
            &stack.name,
            15.0,
            palette.ink,
            Some(info_width),
        );
        let mut facts = Vec::new();
        let day = paint::day(stack.last, now);
        if !day.is_empty() {
            facts.push(day);
        }
        facts.push(paint::plural(stack.planes, "plane", "planes"));
        facts.push(paint::plural(stack.renders.len(), "render", "renders"));
        paint::text(
            &painter,
            Pos2::new(info_left, row.top() + 50.0),
            Align2::LEFT_CENTER,
            &facts.join(" · "),
            12.5,
            palette.ink_2,
            Some(info_width),
        );
        life_line(
            &painter,
            Pos2::new(info_left, row.top() + 78.0),
            &stack.life,
            capturing,
            palette,
            info_width,
        );
        self.spark(&painter, spark, stack.id, signature, palette);
        paint::text(
            &painter,
            Pos2::new(size_right, row.center().y - 9.0),
            Align2::RIGHT_CENTER,
            &paint::bytes(stack.bytes),
            15.0,
            palette.ink,
            None,
        );
        let mut intent = None;
        if moved {
            let link = paint::text(
                &painter,
                Pos2::new(size_right, row.center().y + 11.0),
                Align2::RIGHT_CENTER,
                "locate sources…",
                12.0,
                palette.bad,
                None,
            );
            if ui
                .interact(
                    link.expand(3.0),
                    ui.id().with(("subject-locate", stack.id)),
                    Sense::click(),
                )
                .clicked()
            {
                intent = Some(LibraryIntent::Locate(stack.id));
            }
        } else {
            paint::text(
                &painter,
                Pos2::new(size_right, row.center().y + 11.0),
                Align2::RIGHT_CENTER,
                "sources",
                12.0,
                palette.ink_3,
                None,
            );
        }
        let (label, action) = if capturing {
            ("Open capture", LibraryIntent::OpenCapture)
        } else {
            ("Open", LibraryIntent::OpenStack(stack.id))
        };
        if paint::button(
            ui,
            button_rect,
            ("subject-open", stack.id),
            label,
            None,
            ButtonStyle::Outline,
            palette,
        )
        .clicked()
        {
            intent = intent.or(Some(action));
        }
        if response.clicked() && intent.is_none() {
            self.open = if self.open == Some(stack.id) {
                None
            } else {
                Some(stack.id)
            };
            self.focus_render = None;
            self.focus_version = None;
        }
        if response.double_clicked() || response.triple_clicked() {
            intent = intent.or(Some(LibraryIntent::OpenStack(stack.id)));
        }
        intent
    }

    /// The depth signature, pooled to at most one column per 2 px and cached
    /// per series identity and width; without a series, a baseline only.
    fn spark(
        &mut self,
        painter: &egui::Painter,
        rect: Rect,
        stack: NodeId,
        series: Option<&[f32]>,
        palette: &LibraryPalette,
    ) {
        paint::hline(
            painter,
            rect.left()..=rect.right(),
            rect.bottom() - 1.0,
            palette.line_2,
        );
        let Some(series) = series.filter(|s| !s.is_empty()) else {
            return;
        };
        let columns = ((rect.width() / 2.0) as usize).clamp(1, series.len());
        let key = (series.as_ptr() as usize, series.len(), rect.width() as u32);
        let cached = self.sparks.get(&stack).is_some_and(|(k, _)| *k == key);
        if !cached {
            let mut pooled = vec![0.0f32; columns];
            for (index, value) in series.iter().enumerate() {
                let column = index * columns / series.len();
                pooled[column] = pooled[column].max(value.max(0.0));
            }
            let peak = pooled
                .iter()
                .copied()
                .fold(0.0f32, f32::max)
                .max(f32::EPSILON);
            pooled.iter_mut().for_each(|v| *v /= peak);
            self.sparks.insert(stack, (key, pooled));
            self.stats.spark_builds += 1;
        }
        let pooled = &self.sparks[&stack].1;
        let step = rect.width() / pooled.len() as f32;
        let color = palette.ok.gamma_multiply(0.75);
        for (index, value) in pooled.iter().enumerate() {
            if *value <= 0.0 {
                continue;
            }
            let x = rect.left() + index as f32 * step;
            let height = (rect.height() - 2.0) * value;
            painter.rect_filled(
                Rect::from_min_max(
                    Pos2::new(x, rect.bottom() - 1.0 - height),
                    Pos2::new(x + (step - 1.0).max(1.0), rect.bottom() - 1.0),
                ),
                CornerRadius::ZERO,
                color,
            );
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn lineage(
        &mut self,
        ui: &mut Ui,
        rect: Rect,
        stack: &StackRow,
        previews: &mut LibraryPreviews,
        palette: &LibraryPalette,
        history_root: Option<&Path>,
        now: u64,
    ) -> Option<LibraryIntent> {
        let painter = ui.painter().clone();
        let mut intent = None;
        let top = rect.top() + 4.0;
        let mut x = rect.left() + 150.0;
        let actions_width = 200.0;
        let limit = rect.right() - actions_width - 14.0;
        let focus = self
            .focus_render
            .clone()
            .filter(|f| stack.renders.iter().any(|r| &r.directory == f))
            .or_else(|| {
                stack
                    .renders
                    .iter()
                    .rev()
                    .find(|r| r.state == RunState::Saved)
                    .or(stack.renders.last())
                    .map(|r| r.directory.clone())
            });
        let item = |ui: &mut Ui,
                    at: Pos2,
                    id: (&str, &str),
                    texture: Option<TextureHandle>,
                    title: &str,
                    small: &str,
                    on: bool| {
            let picture = Rect::from_min_size(at, Vec2::new(104.0, 68.0));
            let whole = Rect::from_min_size(at, Vec2::new(104.0, 104.0));
            let response =
                ui.interact(whole, ui.id().with(("subject-lineage", id)), Sense::click());
            let painter = ui.painter();
            painter.rect_filled(picture, CornerRadius::ZERO, palette.raised);
            if let Some(texture) = &texture {
                LibraryPreviews::paint_cover(painter, picture, texture);
            }
            if on {
                paint::outline(painter, picture, 1.5, palette.accent);
            } else if response.hovered() {
                paint::outline(painter, picture, 1.0, palette.ink_3);
            }
            paint::text(
                painter,
                Pos2::new(at.x, picture.bottom() + 5.0),
                Align2::LEFT_TOP,
                title,
                12.0,
                palette.ink,
                Some(104.0),
            );
            paint::text(
                painter,
                Pos2::new(at.x, picture.bottom() + 21.0),
                Align2::LEFT_TOP,
                small,
                11.0,
                palette.ink_3,
                Some(104.0),
            );
            response
        };
        // Renders: the newest that fit, oldest of them first.
        paint::caps(
            &painter,
            Pos2::new(x, top),
            Align2::LEFT_TOP,
            "Renders",
            10.5,
            palette.ink_3,
        );
        let fit = (((limit - x) * 0.45 + 8.0) / 112.0).floor().max(1.0) as usize;
        let shown: Vec<&RenderItem> = stack
            .renders
            .iter()
            .rev()
            .take(fit.min(4))
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect();
        let group = stack.id ^ 0x5bd1_e995;
        for render in &shown {
            let texture = (render.state == RunState::Saved)
                .then(|| previews.tile(&render.output, false, TILE_SIDE, group))
                .flatten();
            let small = match render.state {
                RunState::Saved => render.label.clone(),
                RunState::Stacking => "stacking…".into(),
                RunState::Failed => "failed".into(),
                RunState::Cancelled => "cancelled".into(),
                RunState::Interrupted => "interrupted".into(),
                RunState::Unknown => "unknown".into(),
            };
            let on = focus.as_ref() == Some(&render.directory);
            let key = render.directory.to_string_lossy();
            let response = item(
                ui,
                Pos2::new(x, top + 22.0),
                ("render", &key),
                texture,
                &format!("Render {}", render.number),
                &small,
                on,
            );
            if response.clicked() {
                self.focus_render = Some(render.directory.clone());
                self.focus_version = None;
            }
            if response.double_clicked() || response.triple_clicked() {
                intent = Some(LibraryIntent::OpenRender {
                    stack: stack.id,
                    run: render.directory.clone(),
                });
            }
            x += 112.0;
        }
        if stack.renders.len() > shown.len() {
            paint::text(
                &painter,
                Pos2::new(x, top + 56.0),
                Align2::LEFT_CENTER,
                &format!("+{} older", stack.renders.len() - shown.len()),
                11.5,
                palette.ink_3,
                None,
            );
            x += 60.0;
        }
        let focused = focus
            .as_ref()
            .and_then(|f| stack.renders.iter().find(|r| &r.directory == f));
        if let Some(render) = focused {
            x += 8.0;
            paint::glyph(
                &painter,
                Pos2::new(x + 20.0, top + 56.0),
                Glyph::Arrow,
                palette.ink_3,
            );
            x += 50.0;
            paint::caps(
                &painter,
                Pos2::new(x, top),
                Align2::LEFT_TOP,
                &format!("Versions of render {}", render.number),
                10.5,
                palette.ink_3,
            );
            let version_focus = self
                .focus_version
                .clone()
                .filter(|id| render.versions.iter().any(|v| &v.version.id == id))
                .or_else(|| render.versions.last().map(|v| v.version.id.clone()));
            if render.versions.is_empty() {
                paint::text(
                    &painter,
                    Pos2::new(x, top + 56.0),
                    Align2::LEFT_CENTER,
                    "None developed yet",
                    12.0,
                    palette.ink_3,
                    None,
                );
                x += 150.0;
            }
            for item_version in render
                .versions
                .iter()
                .rev()
                .take(3)
                .collect::<Vec<_>>()
                .into_iter()
                .rev()
            {
                if x + 104.0 > limit {
                    break;
                }
                let (texture, _) = previews.version(history_root, &item_version.version);
                let on = version_focus.as_deref() == Some(item_version.version.id.as_str());
                let response = item(
                    ui,
                    Pos2::new(x, top + 22.0),
                    ("version", &item_version.version.id),
                    texture,
                    &item_version.version.name,
                    &paint::day(item_version.version.created, now),
                    on,
                );
                if response.clicked() {
                    self.focus_version = Some(item_version.version.id.clone());
                }
                if response.double_clicked() || response.triple_clicked() {
                    intent = Some(LibraryIntent::OpenVersion(item_version.version.id.clone()));
                }
                x += 112.0;
            }
            let version =
                version_focus.and_then(|id| render.versions.iter().find(|v| v.version.id == id));
            if let Some(version) = version
                && x + 160.0 < limit
            {
                x += 8.0;
                paint::glyph(
                    &painter,
                    Pos2::new(x + 20.0, top + 56.0),
                    Glyph::Arrow,
                    palette.ink_3,
                );
                x += 50.0;
                paint::caps(
                    &painter,
                    Pos2::new(x, top),
                    Align2::LEFT_TOP,
                    "Exports",
                    10.5,
                    palette.ink_3,
                );
                if version.exports.is_empty() {
                    paint::text(
                        &painter,
                        Pos2::new(x, top + 56.0),
                        Align2::LEFT_CENTER,
                        "Not exported yet",
                        12.0,
                        palette.ink_3,
                        None,
                    );
                }
                for export in version.exports.iter().rev().take(3) {
                    if x + 104.0 > limit {
                        break;
                    }
                    let texture = previews.tile(&export.path, false, TILE_SIDE, group);
                    let key = export.path.to_string_lossy();
                    let small = format!("{} · {}", export.detail, paint::day(export.created, now));
                    if item(
                        ui,
                        Pos2::new(x, top + 22.0),
                        ("export", &key),
                        texture,
                        &export.name,
                        &small,
                        false,
                    )
                    .clicked()
                    {
                        intent = Some(LibraryIntent::RevealPath(export.path.clone()));
                    }
                    x += 112.0;
                }
            }
        }
        // Actions; "Trim sources" is not built (decision D9).
        let actions = Rect::from_min_size(
            Pos2::new(rect.right() - actions_width, top + 24.0),
            Vec2::new(actions_width, 22.0),
        );
        if paint::button(
            ui,
            actions,
            ("subject-shoot-again", stack.id),
            "Shoot again with these settings",
            None,
            ButtonStyle::Outline,
            palette,
        )
        .clicked()
        {
            intent = Some(LibraryIntent::ShootAgain(stack.id));
        }
        let reveal = actions.translate(Vec2::new(0.0, 28.0));
        if paint::button(
            ui,
            reveal,
            ("subject-reveal", stack.id),
            "Reveal folder",
            None,
            ButtonStyle::Quiet,
            palette,
        )
        .clicked()
        {
            intent = Some(LibraryIntent::RevealPath(stack.source.clone()));
        }
        intent
    }
}

fn life_line(
    painter: &egui::Painter,
    at: Pos2,
    life: &StackLifecycle,
    capturing: bool,
    palette: &LibraryPalette,
    width: f32,
) {
    let next = life.next_step();
    let steps = [
        (
            life.captured,
            "Captured",
            if capturing { "Capturing" } else { "Capture" },
        ),
        (life.stacked, "Stacked", "Stack"),
        (life.developed, "Developed", "Develop"),
        (life.exported, "Exported", "Export"),
    ];
    let current = match next {
        crate::workspace_history::NextStep::Stack | crate::workspace_history::NextStep::Wait => {
            Some(1)
        }
        crate::workspace_history::NextStep::Develop => Some(2),
        crate::workspace_history::NextStep::Export => Some(3),
        _ => None,
    };
    let mut x = at.x;
    for (index, (state, done, todo)) in steps.into_iter().enumerate() {
        if x > at.x + width - 40.0 {
            break;
        }
        if index > 0 {
            paint::hline(painter, x..=x + 14.0, at.y, palette.line_2);
            x += 21.0;
        }
        let (mark, label, ink) = if capturing && index == 0 {
            (Mark::Run, todo.to_owned(), palette.ink)
        } else {
            match state {
                StepState::Done => (Mark::Ok, done.to_owned(), palette.ink_2),
                StepState::NeedsLook => {
                    (Mark::Warn, format!("{done} · needs a look"), palette.ink_2)
                }
                StepState::Running => (
                    Mark::Run,
                    format!("{todo}ing").replace("eing", "ing"),
                    palette.ink,
                ),
                StepState::NotYet if current == Some(index) => {
                    (Mark::Run, format!("{todo} next"), palette.ink)
                }
                StepState::NotYet => (Mark::Idle, todo.to_owned(), palette.ink_3),
            }
        };
        paint::mark(painter, Pos2::new(x + 3.5, at.y), mark, palette);
        x = paint::text(
            painter,
            Pos2::new(x + 13.0, at.y),
            Align2::LEFT_CENTER,
            &label,
            12.0,
            ink,
            None,
        )
        .right()
            + 7.0;
    }
}

#[allow(clippy::too_many_arguments)]
fn optics_card(
    ui: &mut Ui,
    painter: &egui::Painter,
    x0: f32,
    x1: f32,
    mut y: f32,
    model: &SubjectModel,
    palette: &LibraryPalette,
    editing: &mut Option<Draft>,
) -> f32 {
    paint::hline(painter, x0..=x1, y, palette.line);
    y += 12.0;
    paint::caps(
        painter,
        Pos2::new(x0, y),
        Align2::LEFT_TOP,
        "Optics and scale",
        10.5,
        palette.ink_3,
    );
    y += 24.0;
    let optics = model.meta.optics.clone().unwrap_or_default();
    let mut rows: Vec<(&str, String)> = Vec::new();
    if !optics.camera.is_empty() {
        rows.push(("Camera", optics.camera.clone()));
    }
    if !optics.lens.is_empty() {
        rows.push(("Lens", optics.lens.clone()));
    }
    match &model.meta.scale {
        Some(scale) => {
            if let ScaleSource::Entered { magnification, .. } = &scale.source {
                rows.push(("Magnification", format!("{magnification} : 1, entered")));
            }
            rows.push(("Scale", format!("1 px = {:.2} µm", scale.um_per_px)));
        }
        None => rows.push(("Scale", "not calibrated".into())),
    }
    for (label, value) in &rows {
        paint::text(
            painter,
            Pos2::new(x0, y + 8.0),
            Align2::LEFT_CENTER,
            label,
            12.5,
            palette.ink_3,
            None,
        );
        let value_rect = if *label == "Scale" && model.meta.scale.is_some() {
            let tag = paint::caps_galley(painter, "Scale bar ready", 9.5, palette.info)
                .size()
                .x
                + 10.0;
            paint::tag(
                painter,
                Pos2::new(x1 - tag, y + 8.0),
                "Scale bar ready",
                palette.info,
            );
            paint::text(
                painter,
                Pos2::new(x1 - tag - 6.0, y + 8.0),
                Align2::RIGHT_CENTER,
                value,
                12.5,
                palette.ink,
                Some(x1 - x0 - 120.0 - tag),
            )
        } else {
            paint::text(
                painter,
                Pos2::new(x1, y + 8.0),
                Align2::RIGHT_CENTER,
                value,
                12.5,
                if model.meta.scale.is_none() && *label == "Scale" {
                    palette.ink_3
                } else {
                    palette.ink
                },
                Some(x1 - x0 - 120.0),
            )
        };
        let _ = value_rect;
        y += 22.0;
    }
    if model.meta.scale.is_none() || model.meta.optics.is_none() {
        let link = paint::caps(
            painter,
            Pos2::new(x1, y + 8.0),
            Align2::RIGHT_CENTER,
            "Set optics and scale…",
            10.5,
            palette.accent,
        );
        if ui
            .interact(
                link.expand(3.0),
                ui.id().with("subject-set-optics"),
                Sense::click(),
            )
            .clicked()
        {
            *editing = Some(Draft::of(model));
        }
        y += 22.0;
    }
    y + 10.0
}

fn disk_card(
    painter: &egui::Painter,
    x0: f32,
    x1: f32,
    mut y: f32,
    model: &SubjectModel,
    palette: &LibraryPalette,
) -> f32 {
    paint::hline(painter, x0..=x1, y, palette.line);
    y += 12.0;
    paint::caps(
        painter,
        Pos2::new(x0, y),
        Align2::LEFT_TOP,
        "On disk",
        10.5,
        palette.ink_3,
    );
    y += 24.0;
    let renders: usize = model.stacks.iter().map(|s| s.renders.len()).sum();
    for (label, value) in [
        (
            "Sources",
            format!(
                "{} in {}",
                paint::bytes(model.bytes),
                paint::plural(model.stacks.len(), "stack", "stacks")
            ),
        ),
        ("Renders", paint::plural(renders, "render", "renders")),
    ] {
        paint::text(
            painter,
            Pos2::new(x0, y + 8.0),
            Align2::LEFT_CENTER,
            label,
            12.5,
            palette.ink_3,
            None,
        );
        paint::text(
            painter,
            Pos2::new(x1, y + 8.0),
            Align2::RIGHT_CENTER,
            &value,
            12.5,
            palette.ink,
            None,
        );
        y += 22.0;
    }
    y
}

/// The inline editor; returns (save, cancel).
fn editor(ui: &mut Ui, rect: Rect, draft: &mut Draft, palette: &LibraryPalette) -> (bool, bool) {
    let mut save = false;
    let mut cancel = false;
    ui.scope_builder(egui::UiBuilder::new().max_rect(rect), |ui| {
        ui.spacing_mut().item_spacing = Vec2::new(8.0, 6.0);
        let field = |ui: &mut Ui, label: &str, value: &mut String, hint: &str| {
            ui.label(
                egui::RichText::new(label.to_uppercase())
                    .size(10.5)
                    .color(palette.ink_3),
            );
            ui.add(
                egui::TextEdit::singleline(value)
                    .hint_text(hint)
                    .desired_width(rect.width()),
            );
        };
        field(ui, "Name", &mut draft.name, "What was photographed");
        ui.label(egui::RichText::new("NOTES").size(10.5).color(palette.ink_3));
        ui.add(
            egui::TextEdit::multiline(&mut draft.notes)
                .char_limit(4000)
                .desired_rows(3)
                .desired_width(rect.width()),
        );
        field(ui, "Camera", &mut draft.camera, "ILCE-7CR");
        field(
            ui,
            "Lens",
            &mut draft.lens,
            "FE 100mm F2.8 Macro GM + 2× converter",
        );
        ui.horizontal(|ui| {
            ui.label(egui::RichText::new("SCALE").size(10.5).color(palette.ink_3));
            ui.radio_value(&mut draft.entered, false, "Measured on a slide");
            ui.radio_value(&mut draft.entered, true, "Magnification and pixel pitch");
        });
        if draft.entered {
            field(ui, "Magnification", &mut draft.magnification, "2.8");
            field(ui, "Pixel pitch (µm)", &mut draft.pitch_um, "3.76");
        } else {
            field(ui, "Micrometres per pixel", &mut draft.um_per_px, "1.34");
            field(
                ui,
                "Reference",
                &mut draft.slide,
                "0.01 mm stage micrometre",
            );
        }
        if let Some(error) = &draft.error {
            ui.label(egui::RichText::new(error).color(palette.warn));
        }
        ui.horizontal(|ui| {
            save = ui.button("Save").clicked();
            cancel = ui.button("Cancel").clicked();
        });
    });
    if ui.input(|i| i.key_pressed(egui::Key::Escape)) {
        cancel = true;
    }
    (save, cancel)
}

/// Folders dropped on a subject become its stacks, one per folder.
fn drops(ui: &mut Ui, model: &SubjectModel, subject: NodeId) -> Option<LibraryIntent> {
    let dropped: Vec<PathBuf> = ui.input(|i| {
        i.raw
            .dropped_files
            .iter()
            .filter_map(|file| file.path.clone())
            .collect()
    });
    let folders: Vec<PathBuf> = dropped.into_iter().filter(|p| p.is_dir()).collect();
    (!folders.is_empty()).then(|| LibraryIntent::ImportFolders {
        collection: None,
        subject: Some(subject),
        groups: vec![ImportGroup {
            subject: model.name.clone(),
            folders,
        }],
    })
}

#[cfg(test)]
#[path = "subject-page-tests.rs"]
mod tests;
