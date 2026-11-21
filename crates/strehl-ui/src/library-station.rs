//! The Library station (plan 7.3): subjects as cards with a picture and their
//! lifecycle, the "needs you" lists, collections and storage, the capture on
//! the rig, search, sort and folder drops. Self-contained: the shell passes
//! the catalog, a revision, the preview service and a palette, and routes the
//! returned `LibraryIntent`. Nothing here edits the catalog.
//!
//! Per frame the station does no work proportional to the catalog: the model
//! is rebuilt only when the catalog revision changes, the visible list only
//! when the model, filter, search or sort change, and only the grid rows in
//! view (plus one screen of prefetch) are laid out.
#![allow(
    dead_code,
    reason = "the Library station is composed into the shell in P4 stage 2"
)]
use crate::{
    jobs::Task,
    library_paint::{self as paint, ButtonStyle, Glyph, LibraryPalette, Mark},
    library_previews::{LibraryPreviews, TILE_SIDE},
    workspace_history::{
        Catalog, ImportGroup, NextStep, NodeId, NodeKind, SourcesState, StepState, SubjectEdit,
        SubjectSummary, import_plan, sources_state, timestamp,
    },
    workspace_icons::Icon,
};
use eframe::egui::{
    self, Align2, Color32, CornerRadius, Key, Pos2, Rect, Sense, TextureHandle, Ui, Vec2,
};
use std::{
    collections::HashMap,
    path::{Path, PathBuf},
    sync::mpsc,
};

pub(crate) const SIDE_WIDTH: f32 = 232.0;
const PAD_X: f32 = 26.0;
const PAD_TOP: f32 = 20.0;
const MIN_CARD: f32 = 240.0;
const GAP_X: f32 = 16.0;
const GAP_Y: f32 = 22.0;
const PICTURE: f32 = 172.0;
const CARD: f32 = 239.0;
const LIST_ROW: f32 = 76.0;
const SCROLL_GUTTER: f32 = 10.0;
fn columns_for(width: f32) -> usize {
    (((width + GAP_X) / (MIN_CARD + GAP_X)).floor() as usize).clamp(1, 8)
}

/// What the user asked for; the shell routes it. Shared with the subject page.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum LibraryIntent {
    OpenSubject(NodeId),
    OpenStack(NodeId),
    /// A render of a stack, by its run directory.
    OpenRender {
        stack: NodeId,
        run: PathBuf,
    },
    OpenVersion(String),
    OpenCapture,
    /// Capture a new stack: into a collection, or of a known subject.
    NewStackFromCamera {
        collection: Option<NodeId>,
        subject: Option<NodeId>,
    },
    /// Ask the shell for folders to import (a picker).
    PickFolders {
        collection: Option<NodeId>,
        subject: Option<NodeId>,
    },
    /// One stack per folder; into `subject` when given, else one subject per
    /// group in `collection`.
    ImportFolders {
        collection: Option<NodeId>,
        subject: Option<NodeId>,
        groups: Vec<ImportGroup>,
    },
    /// "Locate…" for a stack whose sources moved.
    Locate(NodeId),
    /// Open Capture with this stack's bounds, step, exposure and light.
    ShootAgain(NodeId),
    RevealPath(PathBuf),
    Rename(NodeId),
    /// Save the subject page's edits (through the undo journal).
    EditSubject {
        id: NodeId,
        name: String,
        edit: SubjectEdit,
    },
    NewCollection,
    ReviewStorage,
    /// Back from a subject to the library.
    Back,
}

/// The running capture, as the shell describes it.
#[derive(Clone)]
pub(crate) struct RigCapture {
    pub subject: Option<NodeId>,
    pub stack: Option<NodeId>,
    /// "Blue weevil · Dorsal · 2.8×"
    pub title: String,
    /// "Capturing plane 61 of 96 · 3 min 18 s left · …"
    pub detail: String,
    /// 0..=1
    pub progress: f32,
    pub picture: Option<TextureHandle>,
}
/// The capture volume, measured by the shell off the UI thread.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct StorageCard {
    /// "D:"
    pub volume: String,
    pub free: u64,
    pub total: u64,
    /// Finished stacks compaction could shrink, and the bytes it would free.
    pub compactable: Option<(usize, u64)>,
}
pub(crate) struct LibraryInputs<'a> {
    pub catalog: &'a Catalog,
    /// Changes whenever the catalog does (for example `Catalog::generation`).
    pub revision: u64,
    pub previews: &'a mut LibraryPreviews,
    pub palette: &'a LibraryPalette,
    pub rig: Option<&'a RigCapture>,
    pub storage: Option<&'a StorageCard>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub(crate) enum LibraryFilter {
    #[default]
    All,
    OnRig,
    ToStack,
    ToCheck,
    ToDevelop,
    Exported,
    Collection(NodeId),
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub(crate) enum LibrarySort {
    #[default]
    Recent,
    Name,
    Size,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub(crate) enum LibraryView {
    #[default]
    Grid,
    List,
}

/// One subject as the grid shows it, derived once per catalog revision.
#[derive(Clone, Debug)]
pub(crate) struct SubjectCard {
    pub id: NodeId,
    pub name: String,
    /// Project and folders above the subject, outermost first.
    pub ancestors: Vec<NodeId>,
    pub stacks: Vec<NodeId>,
    pub renders: usize,
    /// Recorded source bytes of its stacks (the catalog's record; no I/O).
    pub source_bytes: u64,
    /// Newest render, version or export, else the subject's creation.
    pub last: u64,
    pub summary: SubjectSummary,
    /// Picture candidates, best first: (path, is a camera source). A view
    /// shows the first that loads.
    pub pictures: Vec<(PathBuf, bool)>,
    search: String,
    sort_name: String,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct CollectionEntry {
    pub id: NodeId,
    pub name: String,
    pub subjects: usize,
}
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct NeedsYou {
    pub to_stack: usize,
    pub to_check: usize,
    pub to_develop: usize,
    pub exported: usize,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct ModelKey {
    revision: u64,
    nodes: usize,
    runs: usize,
    versions: usize,
    exports: usize,
}
impl ModelKey {
    fn of(catalog: &Catalog, revision: u64) -> Self {
        Self {
            revision,
            nodes: catalog.nodes.len(),
            runs: catalog.runs.len(),
            versions: catalog.photo_versions.len(),
            exports: catalog.photo_exports.len(),
        }
    }
}
pub(crate) struct LibraryModel {
    key: ModelKey,
    pub cards: Vec<SubjectCard>,
    pub collections: Vec<CollectionEntry>,
    pub stacks: usize,
    pub renders: usize,
    pub source_bytes: u64,
    pub needs: NeedsYou,
}
impl LibraryModel {
    pub(crate) fn build(catalog: &Catalog, revision: u64, now: u64) -> Self {
        let index = catalog.library_index();
        let mut children: HashMap<NodeId, Vec<NodeId>> = HashMap::new();
        for node in &catalog.nodes {
            if let Some(parent) = node.parent {
                children.entry(parent).or_default().push(node.id);
            }
        }
        let by_id: HashMap<NodeId, &crate::workspace_history::ProjectNode> =
            catalog.nodes.iter().map(|n| (n.id, n)).collect();
        let runs: HashMap<&Path, &crate::workspace_history::Run> = catalog
            .runs
            .iter()
            .map(|r| (r.directory.as_path(), r))
            .collect();
        let mut cards = Vec::new();
        let mut needs = NeedsYou::default();
        let (mut stacks_total, mut renders_total, mut bytes_total) = (0, 0, 0u64);
        for node in catalog.nodes.iter().filter(|n| n.kind == NodeKind::Subject) {
            let summary = index.subjects.get(&node.id).copied().unwrap_or_default();
            let stacks: Vec<NodeId> = children
                .get(&node.id)
                .map(|ids| {
                    ids.iter()
                        .copied()
                        .filter(|id| by_id.get(id).is_some_and(|n| n.kind == NodeKind::Stack))
                        .collect()
                })
                .unwrap_or_default();
            let mut ancestors = Vec::new();
            let mut at = node.parent;
            while let Some(id) = at {
                if ancestors.len() > 64 {
                    break;
                }
                ancestors.push(id);
                at = by_id.get(&id).and_then(|n| n.parent);
            }
            ancestors.reverse();
            let source_bytes: u64 = stacks
                .iter()
                .filter_map(|id| by_id.get(id)?.stack.as_ref())
                .map(|draft| draft.sources.iter().map(|s| s.bytes).sum::<u64>())
                .sum();
            let meta = node.subject.as_ref();
            // The chosen picture, then the newest stacks' renders, then sources.
            let mut by_activity = stacks.clone();
            by_activity.sort_by_key(|id| {
                std::cmp::Reverse(index.stacks.get(id).map_or(0, |life| life.last_activity))
            });
            let mut pictures: Vec<(PathBuf, bool)> = meta
                .and_then(|m| m.hero.clone())
                .map(|hero| (hero, false))
                .into_iter()
                .collect();
            for stack in &by_activity {
                let Some(node) = by_id.get(stack) else {
                    continue;
                };
                pictures.extend(
                    node.revisions
                        .iter()
                        .rev()
                        .filter_map(|dir| runs.get(dir.as_path()))
                        .filter(|run| run.status == "Saved")
                        .take(2)
                        .map(|run| (run.output.clone(), false)),
                );
            }
            for stack in &by_activity {
                if let Some(first) = by_id
                    .get(stack)
                    .and_then(|n| n.stack.as_ref())
                    .and_then(|d| d.sources.first())
                {
                    pictures.push((first.path.clone(), true));
                }
            }
            pictures.truncate(6);
            let last = if summary.last_activity > 0 {
                summary.last_activity
            } else {
                meta.map_or(0, |m| m.created)
            };
            let mut search = format!("{}\n{}", node.name, node.notes);
            if let Some(optics) = meta.and_then(|m| m.optics.as_ref()) {
                search.push('\n');
                search.push_str(&optics.camera);
                search.push('\n');
                search.push_str(&optics.lens);
            }
            for stack in &stacks {
                if let Some(stack) = by_id.get(stack) {
                    search.push('\n');
                    search.push_str(&stack.name);
                }
            }
            search.push('\n');
            search.push_str(&searchable_dates(last, now));
            needs.to_stack += usize::from(summary.to_stack > 0);
            needs.to_check += usize::from(summary.to_check > 0);
            needs.to_develop += usize::from(summary.to_develop > 0);
            needs.exported += usize::from(summary.exported > 0);
            stacks_total += stacks.len();
            renders_total += summary.renders;
            bytes_total += source_bytes;
            cards.push(SubjectCard {
                id: node.id,
                sort_name: node.name.to_lowercase(),
                name: node.name.clone(),
                ancestors,
                stacks,
                renders: summary.renders,
                source_bytes,
                last,
                summary,
                pictures,
                search: search.to_lowercase(),
            });
        }
        let collections = catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Project)
            .map(|project| CollectionEntry {
                id: project.id,
                name: project.name.clone(),
                subjects: cards
                    .iter()
                    .filter(|card| card.ancestors.first() == Some(&project.id))
                    .count(),
            })
            .collect();
        Self {
            key: ModelKey::of(catalog, revision),
            cards,
            collections,
            stacks: stacks_total,
            renders: renders_total,
            source_bytes: bytes_total,
            needs,
        }
    }
    /// Indices of the cards a filter, search and sort show, in order.
    pub(crate) fn select(
        &self,
        filter: LibraryFilter,
        query: &str,
        sort: LibrarySort,
        rig_subject: Option<NodeId>,
    ) -> Vec<usize> {
        let words: Vec<String> = query.split_whitespace().map(str::to_lowercase).collect();
        let mut chosen: Vec<usize> = self
            .cards
            .iter()
            .enumerate()
            .filter(|(_, card)| match filter {
                LibraryFilter::All => true,
                LibraryFilter::OnRig => rig_subject == Some(card.id),
                LibraryFilter::ToStack => card.summary.to_stack > 0,
                LibraryFilter::ToCheck => card.summary.to_check > 0,
                LibraryFilter::ToDevelop => card.summary.to_develop > 0,
                LibraryFilter::Exported => card.summary.exported > 0,
                LibraryFilter::Collection(id) => card.ancestors.contains(&id),
            })
            .filter(|(_, card)| words.iter().all(|word| card.search.contains(word)))
            .map(|(index, _)| index)
            .collect();
        let cards = &self.cards;
        match sort {
            // The subject on the rig is the most recent of all.
            LibrarySort::Recent => chosen.sort_by(|&a, &b| {
                let now = |i: usize| rig_subject == Some(cards[i].id);
                now(b)
                    .cmp(&now(a))
                    .then_with(|| cards[b].last.cmp(&cards[a].last))
                    .then_with(|| cards[a].sort_name.cmp(&cards[b].sort_name))
            }),
            LibrarySort::Name => chosen.sort_by(|&a, &b| {
                cards[a]
                    .sort_name
                    .cmp(&cards[b].sort_name)
                    .then(cards[a].id.cmp(&cards[b].id))
            }),
            LibrarySort::Size => chosen.sort_by(|&a, &b| {
                cards[b]
                    .source_bytes
                    .cmp(&cards[a].source_bytes)
                    .then_with(|| cards[a].sort_name.cmp(&cards[b].sort_name))
            }),
        }
        chosen
    }
}
fn searchable_dates(unix: u64, now: u64) -> String {
    use chrono::{Local, TimeZone};
    let Some(at) = Local.timestamp_opt(unix as i64, 0).single() else {
        return String::new();
    };
    format!(
        "{} {} {}",
        paint::day(unix, now),
        at.format("%Y-%m-%d %B %b %Y"),
        at.format("%-d %B")
    )
}

/// Which stacks' sources were found where the catalog records them, checked
/// on a worker once per catalog revision (one directory listing per folder).
#[derive(Default)]
struct SourcesCheck {
    key: Option<ModelKey>,
    task: Option<Task<HashMap<NodeId, SourcesState>>>,
    states: HashMap<NodeId, SourcesState>,
}
impl SourcesCheck {
    fn refresh(&mut self, catalog: &Catalog, key: ModelKey, ctx: &egui::Context) {
        if let Some(task) = &self.task {
            match task.receiver.try_recv() {
                Ok(Ok(states)) => {
                    self.states = states;
                    self.task = None;
                }
                Ok(Err(_)) | Err(mpsc::TryRecvError::Disconnected) => self.task = None,
                Err(mpsc::TryRecvError::Empty) => {}
            }
        }
        if self.key == Some(key) {
            return;
        }
        self.key = Some(key);
        if let Some(old) = self.task.take() {
            old.cancel();
        }
        // Cloned once per revision; the listing runs off the UI thread and the
        // previous answer stays on screen until the new one arrives.
        let drafts: Vec<(NodeId, crate::workspace_history::StackDraft)> = catalog
            .nodes
            .iter()
            .filter_map(|n| Some((n.id, n.stack.clone()?)))
            .collect();
        let notify = ctx.clone();
        self.task = Some(crate::jobs::spawn_notifying_task(
            "strehl-library-sources",
            move |cancelled| {
                let mut states = HashMap::new();
                for (id, draft) in drafts {
                    anyhow::ensure!(
                        !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                        "Sources check cancelled"
                    );
                    states.insert(id, sources_state(&draft));
                }
                Ok(states)
            },
            move || notify.request_repaint(),
        ));
    }
    fn moved(&self, stack: NodeId) -> bool {
        matches!(
            self.states.get(&stack),
            Some(SourcesState::Missing | SourcesState::Partial { .. })
        )
    }
}

/// Counters for tests and the performance notes.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct LibraryStats {
    pub model_builds: u64,
    pub list_builds: u64,
    /// Cards (or list rows) laid out in the last frame.
    pub cards_painted: usize,
    /// Tiles requested ahead of the view in the last frame.
    pub prefetched: usize,
}

type ListKey = (ModelKey, LibraryFilter, String, LibrarySort, Option<NodeId>);

#[derive(Default)]
pub(crate) struct LibraryStation {
    pub filter: LibraryFilter,
    pub query: String,
    pub sort: LibrarySort,
    pub view: LibraryView,
    /// Keyboard selection.
    pub selected: Option<NodeId>,
    model: Option<LibraryModel>,
    list: Option<(ListKey, Vec<usize>)>,
    sources: SourcesCheck,
    menu_open: bool,
    last_offset: f32,
    scrolling_up: bool,
    stats: LibraryStats,
}

impl LibraryStation {
    pub(crate) fn stats(&self) -> LibraryStats {
        self.stats
    }
    pub(crate) fn model(&self) -> Option<&LibraryModel> {
        self.model.as_ref()
    }
    /// The cards shown, in order (after the last `show`).
    pub(crate) fn visible(&self) -> Vec<NodeId> {
        match (&self.model, &self.list) {
            (Some(model), Some((_, list))) => list.iter().map(|&i| model.cards[i].id).collect(),
            _ => Vec::new(),
        }
    }
    /// The latest sources check, for the subject page.
    pub(crate) fn sources(&self) -> &HashMap<NodeId, SourcesState> {
        &self.sources.states
    }
    /// Keep the sources check current while a subject page, not the grid,
    /// is on screen (cheap when nothing changed: a key comparison).
    pub(crate) fn check_sources(&mut self, catalog: &Catalog, revision: u64, ctx: &egui::Context) {
        self.sources
            .refresh(catalog, ModelKey::of(catalog, revision), ctx);
    }
    /// A sources check is running.
    pub(crate) fn sources_pending(&self) -> bool {
        self.sources.task.is_some()
    }
    #[cfg(test)]
    pub(crate) fn set_sources(&mut self, states: HashMap<NodeId, SourcesState>) {
        self.sources.states = states;
    }

    fn refresh(
        &mut self,
        catalog: &Catalog,
        revision: u64,
        rig: Option<NodeId>,
        ctx: &egui::Context,
    ) {
        let key = ModelKey::of(catalog, revision);
        if self.model.as_ref().is_none_or(|m| m.key != key) {
            self.model = Some(LibraryModel::build(catalog, revision, timestamp()));
            self.stats.model_builds += 1;
        }
        self.sources.refresh(catalog, key, ctx);
        let list_key: ListKey = (key, self.filter, self.query.clone(), self.sort, rig);
        if self.list.as_ref().is_none_or(|(k, _)| *k != list_key) {
            let model = self.model.as_ref().unwrap();
            let list = model.select(self.filter, &self.query, self.sort, rig);
            self.list = Some((list_key, list));
            self.stats.list_builds += 1;
        }
    }

    pub(crate) fn show(&mut self, ui: &mut Ui, inputs: LibraryInputs<'_>) -> Option<LibraryIntent> {
        let LibraryInputs {
            catalog,
            revision,
            previews,
            palette,
            rig,
            storage,
        } = inputs;
        let ctx = ui.ctx().clone();
        previews.poll(&ctx);
        let rig_subject = rig.and_then(|r| r.subject);
        self.refresh(catalog, revision, rig_subject, &ctx);
        let area = ui.max_rect();
        let painter = ui.painter_at(area);
        painter.rect_filled(area, CornerRadius::ZERO, palette.bg);
        let side = Rect::from_min_size(area.min, Vec2::new(SIDE_WIDTH, area.height()));
        let main = Rect::from_min_max(Pos2::new(side.right(), area.top()), area.max);
        let mut intent = None;
        let now = timestamp();
        intent = intent.or(self.side_list(ui, side, palette, rig, storage));
        intent = intent.or(self.header(ui, main, palette));
        let mut top = main.top() + PAD_TOP + 28.0 + 18.0;
        if let Some(rig) = rig {
            let strip = Rect::from_min_size(
                Pos2::new(main.left() + PAD_X, top),
                Vec2::new(main.width() - 2.0 * PAD_X, 88.0),
            );
            intent = intent.or(rig_strip(ui, strip, rig, palette));
            top = strip.bottom() + 18.0;
        }
        let grid = Rect::from_min_max(
            Pos2::new(main.left() + PAD_X, top),
            Pos2::new(main.right() - PAD_X, main.bottom()),
        );
        intent = intent.or(self.grid(ui, grid, previews, palette, rig, now));
        intent = intent.or(self.menu(ui, palette));
        intent = intent.or(self.keys(ui));
        intent = intent.or(self.drops(ui, main, palette));
        intent
    }

    fn side_list(
        &mut self,
        ui: &mut Ui,
        side: Rect,
        palette: &LibraryPalette,
        rig: Option<&RigCapture>,
        storage: Option<&StorageCard>,
    ) -> Option<LibraryIntent> {
        let painter = ui.painter().clone();
        painter.rect_filled(side, CornerRadius::ZERO, palette.panel);
        paint::vline(
            &painter,
            side.right() - 1.0,
            side.top()..=side.bottom(),
            palette.line,
        );
        let model = self.model.as_ref()?;
        let needs = model.needs;
        let mut y = side.top() + 16.0;
        let caption = |y: f32, label: &str| {
            paint::caps(
                &painter,
                Pos2::new(side.left() + 16.0, y),
                Align2::LEFT_TOP,
                label,
                10.5,
                palette.ink_3,
            );
        };
        caption(y, "Library");
        y += 22.0;
        enum Lead {
            Icon(Icon),
            Glyph(Glyph),
            Mark(Mark),
        }
        let mut chosen = None;
        let mut intent = None;
        let row = |ui: &mut Ui,
                   y: &mut f32,
                   id: &str,
                   lead: Lead,
                   label: &str,
                   count: Option<usize>,
                   on: bool,
                   accent: bool|
         -> bool {
            let rect = Rect::from_min_size(
                Pos2::new(side.left(), *y),
                Vec2::new(side.width() - 1.0, 30.0),
            );
            *y += 30.0;
            let response = ui.interact(rect, ui.id().with(("library-nav", id)), Sense::click());
            if on {
                painter.rect_filled(rect, CornerRadius::ZERO, palette.raised);
                painter.rect_filled(
                    Rect::from_min_size(rect.min, Vec2::new(2.0, rect.height())),
                    CornerRadius::ZERO,
                    palette.accent,
                );
            }
            let ink = if on || response.hovered() {
                palette.ink
            } else {
                palette.ink_2
            };
            let lead_at = Pos2::new(rect.left() + 23.0, rect.center().y);
            match lead {
                Lead::Icon(icon) => crate::workspace_icons::paint(
                    &painter,
                    lead_at,
                    15.0,
                    icon,
                    if accent { palette.accent } else { ink },
                ),
                Lead::Glyph(glyph) => paint::glyph(&painter, lead_at, glyph, ink),
                Lead::Mark(kind) => paint::mark(&painter, lead_at, kind, palette),
            }
            paint::text(
                &painter,
                Pos2::new(rect.left() + 41.0, rect.center().y),
                Align2::LEFT_CENTER,
                label,
                13.0,
                ink,
                Some(rect.width() - 90.0),
            );
            if let Some(count) = count {
                paint::text(
                    &painter,
                    Pos2::new(rect.right() - 16.0, rect.center().y),
                    Align2::RIGHT_CENTER,
                    &count.to_string(),
                    12.0,
                    if accent {
                        palette.accent
                    } else {
                        palette.ink_3
                    },
                    None,
                );
            }
            response.clicked()
        };
        let filter = self.filter;
        if row(
            ui,
            &mut y,
            "all",
            Lead::Glyph(Glyph::Grid),
            "All subjects",
            Some(model.cards.len()),
            filter == LibraryFilter::All,
            false,
        ) {
            chosen = Some(LibraryFilter::All);
        }
        if row(
            ui,
            &mut y,
            "rig",
            Lead::Icon(Icon::Camera),
            "On the rig",
            Some(usize::from(rig.is_some())),
            filter == LibraryFilter::OnRig,
            rig.is_some(),
        ) {
            chosen = Some(LibraryFilter::OnRig);
        }
        y += 14.0;
        caption(y, "Needs you");
        y += 22.0;
        for (id, mark_kind, label, count, value) in [
            (
                "to-stack",
                Mark::Idle,
                "To stack",
                needs.to_stack,
                LibraryFilter::ToStack,
            ),
            (
                "to-check",
                Mark::Warn,
                "To check",
                needs.to_check,
                LibraryFilter::ToCheck,
            ),
            (
                "to-develop",
                Mark::Run,
                "To develop",
                needs.to_develop,
                LibraryFilter::ToDevelop,
            ),
            (
                "exported",
                Mark::Ok,
                "Exported",
                needs.exported,
                LibraryFilter::Exported,
            ),
        ] {
            if row(
                ui,
                &mut y,
                id,
                Lead::Mark(mark_kind),
                label,
                Some(count),
                filter == value,
                false,
            ) {
                chosen = Some(value);
            }
        }
        y += 14.0;
        caption(y, "Collections");
        y += 22.0;
        // Bounded by the side's height; a long list ends before the storage card.
        let limit = side.bottom() - 190.0;
        for collection in &model.collections {
            if y + 30.0 > limit {
                break;
            }
            let value = LibraryFilter::Collection(collection.id);
            if row(
                ui,
                &mut y,
                &format!("collection-{}", collection.id),
                Lead::Icon(Icon::Folder),
                &collection.name,
                Some(collection.subjects),
                filter == value,
                false,
            ) {
                chosen = Some(value);
            }
        }
        if y + 30.0 <= limit
            && row(
                ui,
                &mut y,
                "new-collection",
                Lead::Icon(Icon::Add),
                "New collection",
                None,
                false,
                false,
            )
        {
            intent = Some(LibraryIntent::NewCollection);
        }
        if let Some(filter) = chosen {
            self.filter = filter;
        }
        let review = storage_card(ui, side, model.source_bytes, storage, palette);
        intent.or(review)
    }

    fn header(
        &mut self,
        ui: &mut Ui,
        main: Rect,
        palette: &LibraryPalette,
    ) -> Option<LibraryIntent> {
        let painter = ui.painter().clone();
        let model = self.model.as_ref()?;
        let list = self.list.as_ref().map_or(&[][..], |(_, l)| l.as_slice());
        let center_y = main.top() + PAD_TOP + 14.0;
        let mut x = main.left() + PAD_X;
        let title = match self.filter {
            LibraryFilter::All => "All subjects".to_owned(),
            LibraryFilter::OnRig => "On the rig".into(),
            LibraryFilter::ToStack => "To stack".into(),
            LibraryFilter::ToCheck => "To check".into(),
            LibraryFilter::ToDevelop => "To develop".into(),
            LibraryFilter::Exported => "Exported".into(),
            LibraryFilter::Collection(id) => model
                .collections
                .iter()
                .find(|c| c.id == id)
                .map_or_else(|| "Collection".into(), |c| c.name.clone()),
        };
        x = paint::text(
            &painter,
            Pos2::new(x, center_y),
            Align2::LEFT_CENTER,
            &title,
            22.0,
            palette.ink,
            Some(320.0),
        )
        .right()
            + 14.0;
        let (stacks, renders) = list.iter().fold((0, 0), |(s, r), &i| {
            (s + model.cards[i].stacks.len(), r + model.cards[i].renders)
        });
        let counts = format!(
            "{} · {} · {}",
            paint::plural(list.len(), "subject", "subjects"),
            paint::plural(stacks, "stack", "stacks"),
            paint::plural(renders, "render", "renders"),
        );
        x = paint::text(
            &painter,
            Pos2::new(x, center_y),
            Align2::LEFT_CENTER,
            &counts,
            13.0,
            palette.ink_2,
            None,
        )
        .right()
            + 14.0;
        // The right-hand controls, laid out from the right edge.
        let right = main.right() - PAD_X;
        let new_label = "New subject";
        let new_width = paint::button_width(&painter, new_label, true, false) + 22.0;
        let new_rect = Rect::from_min_size(
            Pos2::new(right - new_width, center_y - 14.0),
            Vec2::new(new_width, 28.0),
        );
        // The label sits left of the menu arrow, which is part of the button.
        let arrow = Rect::from_min_max(
            Pos2::new(new_rect.right() - 22.0, new_rect.top()),
            new_rect.max,
        );
        let new = paint::button(
            ui,
            Rect::from_min_max(new_rect.min, Pos2::new(arrow.left(), new_rect.bottom())),
            "new-subject",
            new_label,
            Some(Icon::Add),
            ButtonStyle::Primary,
            palette,
        );
        painter.rect_filled(arrow, CornerRadius::ZERO, palette.accent);
        crate::workspace_icons::paint(
            &painter,
            Pos2::new(arrow.center().x - 2.0, arrow.center().y),
            12.0,
            Icon::Down,
            palette.accent_ink,
        );
        let arrow_clicked = ui
            .interact(arrow, ui.id().with("new-subject-arrow"), Sense::click())
            .clicked();
        if new.clicked() || arrow_clicked {
            self.menu_open = !self.menu_open;
        }
        ui.ctx()
            .data_mut(|d| d.insert_temp(menu_anchor_id(), new_rect));
        let views_left = new_rect.left() - 14.0 - 2.0 * 34.0;
        let (_, view_clicked) = view_toggle(
            ui,
            Pos2::new(views_left, center_y - 12.0),
            self.view,
            palette,
        );
        if let Some(view) = view_clicked {
            self.view = view;
        }
        let sort_labels = ["Recent", "Name", "Size"];
        let sort_width: f32 = sort_labels
            .iter()
            .map(|l| {
                paint::galley(&painter, l, 12.0, Color32::WHITE, None)
                    .size()
                    .x
                    + 20.0
            })
            .sum();
        let sort_left = views_left - 14.0 - sort_width;
        let selected = match self.sort {
            LibrarySort::Recent => 0,
            LibrarySort::Name => 1,
            LibrarySort::Size => 2,
        };
        let (_, sort_clicked) = paint::segments(
            ui,
            Pos2::new(sort_left, center_y - 12.0),
            "library-sort",
            &sort_labels,
            selected,
            palette,
        );
        if let Some(index) = sort_clicked {
            self.sort = [LibrarySort::Recent, LibrarySort::Name, LibrarySort::Size][index];
        }
        let search = Rect::from_min_size(
            Pos2::new(sort_left - 14.0 - 290.0, center_y - 14.0),
            Vec2::new(290.0, 28.0),
        );
        // The legend sits between the counts and the search when it fits.
        if search.left() - x > 330.0 {
            let mut lx = x;
            for label in ["captured", "stacked", "developed", "exported"] {
                painter.rect_filled(
                    Rect::from_min_size(Pos2::new(lx, center_y - 1.5), Vec2::new(14.0, 3.0)),
                    CornerRadius::ZERO,
                    palette.ok,
                );
                lx = paint::text(
                    &painter,
                    Pos2::new(lx + 19.0, center_y),
                    Align2::LEFT_CENTER,
                    label,
                    11.5,
                    palette.ink_3,
                    None,
                )
                .right()
                    + 14.0;
            }
        }
        paint::hline(
            &painter,
            search.left()..=search.right(),
            search.bottom() - 1.0,
            palette.line_2,
        );
        paint::glyph(
            &painter,
            Pos2::new(search.left() + 9.0, search.center().y),
            Glyph::Search,
            palette.ink_3,
        );
        let field = Rect::from_min_max(
            Pos2::new(search.left() + 24.0, search.top() + 4.0),
            Pos2::new(search.right(), search.bottom() - 3.0),
        );
        ui.put(
            field,
            egui::TextEdit::singleline(&mut self.query)
                .id_salt("library-search")
                .frame(false)
                .font(paint::font(13.0))
                .text_color(palette.ink)
                .hint_text(
                    egui::RichText::new("Search names, notes, lenses, dates").color(palette.ink_3),
                )
                .desired_width(field.width()),
        );
        None
    }

    fn menu(&mut self, ui: &mut Ui, palette: &LibraryPalette) -> Option<LibraryIntent> {
        if !self.menu_open {
            return None;
        }
        let anchor: Rect = ui.ctx().data(|d| d.get_temp(menu_anchor_id()))?;
        let size = Vec2::new(220.0, 74.0);
        let rect = Rect::from_min_size(
            Pos2::new(anchor.right() - size.x, anchor.bottom() + 4.0),
            size,
        );
        let collection = match self.filter {
            LibraryFilter::Collection(id) => Some(id),
            _ => None,
        };
        let mut intent = None;
        let area = egui::Area::new(egui::Id::new("library-new-subject-menu"))
            .order(egui::Order::Foreground)
            .fixed_pos(rect.min)
            .show(ui.ctx(), |ui| {
                let (frame, _) = ui.allocate_exact_size(size, Sense::hover());
                let painter = ui.painter();
                painter.rect_filled(frame, CornerRadius::ZERO, palette.panel);
                paint::inset(painter, frame, palette.line_2);
                for (index, (icon, label)) in [
                    (Icon::Camera, "From the camera"),
                    (Icon::Folder, "From folders…"),
                ]
                .into_iter()
                .enumerate()
                {
                    let item = Rect::from_min_size(
                        frame.min + Vec2::new(1.0, 1.0 + index as f32 * 36.0),
                        Vec2::new(frame.width() - 2.0, 36.0),
                    );
                    let response =
                        ui.interact(item, ui.id().with(("library-new", index)), Sense::click());
                    if response.hovered() {
                        ui.painter()
                            .rect_filled(item, CornerRadius::ZERO, palette.raised);
                    }
                    crate::workspace_icons::paint(
                        ui.painter(),
                        Pos2::new(item.left() + 18.0, item.center().y),
                        15.0,
                        icon,
                        palette.ink_2,
                    );
                    paint::text(
                        ui.painter(),
                        Pos2::new(item.left() + 36.0, item.center().y),
                        Align2::LEFT_CENTER,
                        label,
                        13.0,
                        palette.ink,
                        None,
                    );
                    if response.clicked() {
                        intent = Some(if index == 0 {
                            LibraryIntent::NewStackFromCamera {
                                collection,
                                subject: None,
                            }
                        } else {
                            LibraryIntent::PickFolders {
                                collection,
                                subject: None,
                            }
                        });
                    }
                }
            });
        let outside = ui.input(|i| {
            i.pointer.any_click()
                && i.pointer
                    .interact_pos()
                    .is_some_and(|p| !area.response.rect.contains(p) && !anchor.contains(p))
        }) || ui.input(|i| i.key_pressed(Key::Escape));
        if intent.is_some() || outside {
            self.menu_open = false;
        }
        intent
    }

    fn grid(
        &mut self,
        ui: &mut Ui,
        grid: Rect,
        previews: &mut LibraryPreviews,
        palette: &LibraryPalette,
        rig: Option<&RigCapture>,
        now: u64,
    ) -> Option<LibraryIntent> {
        let (Some(model), Some((list_key, list))) = (&self.model, &self.list) else {
            return None;
        };
        if grid.width() <= 0.0 || grid.height() <= 0.0 {
            return None;
        }
        let epoch = {
            use std::hash::{Hash, Hasher};
            let mut hash = std::collections::hash_map::DefaultHasher::new();
            (list_key.1, &list_key.2, list_key.3).hash(&mut hash);
            list_key.0.revision.hash(&mut hash);
            hash.finish() & 0xffff_ffff
        };
        // Leave the scroll bar its own gutter.
        let usable = grid.width() - SCROLL_GUTTER;
        let (columns, card_width, pitch) = match self.view {
            LibraryView::Grid => {
                let columns = columns_for(usable);
                let width = (usable - GAP_X * (columns as f32 - 1.0)) / columns as f32;
                (columns, width, CARD + GAP_Y)
            }
            LibraryView::List => (1, usable, LIST_ROW),
        };
        let rows = list.len().div_ceil(columns);
        let height = match self.view {
            LibraryView::Grid => CARD,
            LibraryView::List => LIST_ROW,
        };
        let mut intent = None;
        let mut painted = 0;
        let mut prefetched = 0;
        let rig_subject = rig.and_then(|r| r.subject);
        let selected = self.selected;
        let view = self.view;
        let sources = &self.sources;
        let mut offset = self.last_offset;
        ui.scope_builder(egui::UiBuilder::new().max_rect(grid), |ui| {
            egui::ScrollArea::vertical()
                .id_salt("library-grid")
                .auto_shrink([false, false])
                .show_viewport(ui, |ui, viewport| {
                    ui.set_height(rows as f32 * pitch);
                    let origin = ui.min_rect().min;
                    offset = viewport.min.y;
                    let first = (viewport.min.y / pitch).floor().max(0.0) as usize;
                    let last = ((viewport.max.y / pitch).ceil() as usize).min(rows);
                    let screen = last.saturating_sub(first).max(1);
                    for row in first..last {
                        for column in 0..columns {
                            let Some(&index) = list.get(row * columns + column) else {
                                break;
                            };
                            let card = &model.cards[index];
                            let rect = Rect::from_min_size(
                                Pos2::new(
                                    origin.x + column as f32 * (card_width + GAP_X),
                                    origin.y + row as f32 * pitch,
                                ),
                                Vec2::new(card_width, height),
                            );
                            let texture = previews.first_tile(
                                &card.pictures,
                                TILE_SIDE,
                                (epoch << 20) | row as u64,
                            );
                            let moved = card.stacks.iter().copied().find(|&s| sources.moved(s));
                            let state = CardState {
                                capturing: rig_subject == Some(card.id),
                                moved,
                                selected: selected == Some(card.id),
                                now,
                            };
                            let found = match view {
                                LibraryView::Grid => {
                                    paint_card(ui, rect, card, texture.as_ref(), state, palette)
                                }
                                LibraryView::List => {
                                    paint_row(ui, rect, card, texture.as_ref(), state, palette)
                                }
                            };
                            intent = intent.take().or(found);
                            painted += 1;
                        }
                    }
                    // One screen ahead, in the direction of travel.
                    let ahead = if self.scrolling_up {
                        first.saturating_sub(screen)..first
                    } else {
                        last..(last + screen).min(rows)
                    };
                    for row in ahead {
                        for column in 0..columns {
                            let Some(&index) = list.get(row * columns + column) else {
                                break;
                            };
                            let pictures = &model.cards[index].pictures;
                            if let Some((path, source)) = pictures
                                .iter()
                                .find(|(path, source)| !previews.failed(path, *source, TILE_SIDE))
                            {
                                previews.prefetch(
                                    path,
                                    *source,
                                    TILE_SIDE,
                                    (epoch << 20) | row as u64,
                                );
                                prefetched += 1;
                            }
                        }
                    }
                });
        });
        if offset < self.last_offset {
            self.scrolling_up = true;
        } else if offset > self.last_offset {
            self.scrolling_up = false;
        }
        self.last_offset = offset;
        self.stats.cards_painted = painted;
        self.stats.prefetched = prefetched;
        if let Some(LibraryIntent::OpenSubject(id)) = &intent {
            self.selected = Some(*id);
        }
        intent
    }

    fn keys(&mut self, ui: &mut Ui) -> Option<LibraryIntent> {
        if ui.ctx().wants_keyboard_input() || self.menu_open {
            return None;
        }
        let (left, right, up, down, enter, rename) = ui.input(|i| {
            (
                i.key_pressed(Key::ArrowLeft),
                i.key_pressed(Key::ArrowRight),
                i.key_pressed(Key::ArrowUp),
                i.key_pressed(Key::ArrowDown),
                i.key_pressed(Key::Enter),
                i.key_pressed(Key::F2),
            )
        });
        if !(left || right || up || down || enter || rename) {
            return None;
        }
        // Only a key press walks the list.
        let visible = self.visible();
        if visible.is_empty() {
            return None;
        }
        let columns = match self.view {
            LibraryView::Grid => {
                columns_for(ui.max_rect().width() - SIDE_WIDTH - 2.0 * PAD_X - SCROLL_GUTTER)
            }
            LibraryView::List => 1,
        };
        let at = self
            .selected
            .and_then(|id| visible.iter().position(|&v| v == id));
        let step = |at: Option<usize>, delta: isize| {
            let at = at.map_or(0, |a| a as isize + delta);
            at.clamp(0, visible.len() as isize - 1) as usize
        };
        let moved_to = if right {
            Some(step(at, 1))
        } else if left {
            Some(step(at, -1))
        } else if down {
            Some(step(at, columns as isize))
        } else if up {
            Some(step(at, -(columns as isize)))
        } else {
            None
        };
        if let Some(to) = moved_to {
            self.selected = Some(visible[to]);
        }
        let selected = self.selected.filter(|id| visible.contains(id))?;
        if enter {
            Some(LibraryIntent::OpenSubject(selected))
        } else if rename {
            Some(LibraryIntent::Rename(selected))
        } else {
            None
        }
    }

    fn drops(
        &mut self,
        ui: &mut Ui,
        main: Rect,
        palette: &LibraryPalette,
    ) -> Option<LibraryIntent> {
        let (hovering, dropped) = ui.input(|i| {
            (
                !i.raw.hovered_files.is_empty(),
                i.raw
                    .dropped_files
                    .iter()
                    .filter_map(|file| file.path.clone())
                    .collect::<Vec<_>>(),
            )
        });
        if hovering {
            let painter = ui.painter();
            paint::outline(painter, main.shrink(6.0), 1.5, palette.accent);
            paint::caps(
                painter,
                Pos2::new(main.center().x, main.bottom() - 28.0),
                Align2::CENTER_CENTER,
                "Drop folders to make subjects · one stack per folder",
                11.0,
                palette.accent,
            );
        }
        // Event-time checks only: which dropped paths are folders.
        let folders: Vec<PathBuf> = dropped.into_iter().filter(|p| p.is_dir()).collect();
        if folders.is_empty() {
            return None;
        }
        let collection = match self.filter {
            LibraryFilter::Collection(id) => Some(id),
            _ => None,
        };
        Some(LibraryIntent::ImportFolders {
            collection,
            subject: None,
            groups: import_plan(&folders),
        })
    }
}

fn menu_anchor_id() -> egui::Id {
    egui::Id::new("library-new-subject-anchor")
}

fn view_toggle(
    ui: &mut Ui,
    origin: Pos2,
    view: LibraryView,
    palette: &LibraryPalette,
) -> (Rect, Option<LibraryView>) {
    let painter = ui.painter().clone();
    let mut clicked = None;
    for (index, (glyph, value)) in [
        (Glyph::Grid, LibraryView::Grid),
        (Glyph::List, LibraryView::List),
    ]
    .into_iter()
    .enumerate()
    {
        let cell = Rect::from_min_size(
            origin + Vec2::new(index as f32 * 34.0, 0.0),
            Vec2::new(34.0, 24.0),
        );
        let response = ui.interact(cell, ui.id().with(("library-view", index)), Sense::click());
        let on = view == value;
        if on {
            painter.rect_filled(cell, CornerRadius::ZERO, palette.control);
            painter.rect_filled(
                Rect::from_min_max(Pos2::new(cell.left(), cell.bottom() - 1.5), cell.max),
                CornerRadius::ZERO,
                palette.accent,
            );
        }
        if index > 0 {
            paint::vline(
                &painter,
                cell.left(),
                cell.top()..=cell.bottom(),
                palette.line_2,
            );
        }
        paint::glyph(
            &painter,
            cell.center(),
            glyph,
            if on || response.hovered() {
                palette.ink
            } else {
                palette.ink_3
            },
        );
        if response.clicked() {
            clicked = Some(value);
        }
    }
    let outer = Rect::from_min_size(origin, Vec2::new(68.0, 24.0));
    paint::inset(&painter, outer, palette.line_2);
    (outer, clicked)
}

fn storage_card(
    ui: &mut Ui,
    side: Rect,
    strehl_bytes: u64,
    storage: Option<&StorageCard>,
    palette: &LibraryPalette,
) -> Option<LibraryIntent> {
    let painter = ui.painter().clone();
    let left = side.left() + 16.0;
    let right = side.right() - 17.0;
    let top = side.bottom() - 158.0;
    paint::hline(&painter, left..=right, top, palette.line);
    let mut y = top + 22.0;
    paint::glyph(&painter, Pos2::new(left + 6.0, y), Glyph::Disk, palette.ink);
    match storage {
        Some(card) => {
            paint::text(
                &painter,
                Pos2::new(left + 22.0, y),
                Align2::LEFT_CENTER,
                &format!("{} {} free", card.volume, paint::bytes(card.free)),
                13.0,
                palette.ink,
                None,
            );
            paint::text(
                &painter,
                Pos2::new(right, y),
                Align2::RIGHT_CENTER,
                &format!("of {}", paint::bytes(card.total)),
                12.0,
                palette.ink_3,
                None,
            );
            y += 20.0;
            let meter = Rect::from_min_max(Pos2::new(left, y), Pos2::new(right, y + 4.0));
            painter.rect_filled(meter, CornerRadius::ZERO, palette.line_2);
            let total = card.total.max(1) as f32;
            let used = (card.total.saturating_sub(card.free)) as f32 / total;
            let ours = (strehl_bytes as f32 / total).min(used);
            painter.rect_filled(
                Rect::from_min_size(meter.min, Vec2::new(meter.width() * ours, 4.0)),
                CornerRadius::ZERO,
                palette.accent,
            );
            painter.rect_filled(
                Rect::from_min_size(
                    Pos2::new(meter.left() + meter.width() * ours, meter.top()),
                    Vec2::new(meter.width() * (used - ours).max(0.0), 4.0),
                ),
                CornerRadius::ZERO,
                palette.ink_3,
            );
            y += 18.0;
        }
        None => {
            paint::text(
                &painter,
                Pos2::new(left + 22.0, y),
                Align2::LEFT_CENTER,
                "Disk space is being measured",
                12.5,
                palette.ink_3,
                None,
            );
            y += 22.0;
        }
    }
    painter.rect_filled(
        Rect::from_center_size(Pos2::new(left + 4.0, y), Vec2::splat(8.0)),
        CornerRadius::ZERO,
        palette.accent,
    );
    let legend = paint::text(
        &painter,
        Pos2::new(left + 12.0, y),
        Align2::LEFT_CENTER,
        &format!("Strehl sources {}", paint::bytes(strehl_bytes)),
        12.0,
        palette.ink_2,
        None,
    );
    if storage.is_some() {
        painter.rect_filled(
            Rect::from_center_size(Pos2::new(legend.right() + 14.0, y), Vec2::splat(8.0)),
            CornerRadius::ZERO,
            palette.ink_3,
        );
        paint::text(
            &painter,
            Pos2::new(legend.right() + 22.0, y),
            Align2::LEFT_CENTER,
            "other",
            12.0,
            palette.ink_2,
            None,
        );
    }
    y += 16.0;
    if let Some((stacks, bytes)) = storage.and_then(|s| s.compactable) {
        let note = format!(
            "Compacting {} would free about {}.",
            paint::plural(stacks, "finished stack", "finished stacks"),
            paint::bytes(bytes)
        );
        y += paint::paragraph(
            &painter,
            Pos2::new(left, y),
            &note,
            12.5,
            palette.ink,
            right - left,
            2,
        );
    }
    let label = "Review storage…";
    let width = paint::button_width(&painter, label, false, true);
    let button = Rect::from_min_size(
        Pos2::new(left, (y + 8.0).min(side.bottom() - 36.0)),
        Vec2::new(width, 22.0),
    );
    paint::button(
        ui,
        button,
        "review-storage",
        label,
        None,
        ButtonStyle::Outline,
        palette,
    )
    .clicked()
    .then_some(LibraryIntent::ReviewStorage)
}

fn rig_strip(
    ui: &mut Ui,
    strip: Rect,
    rig: &RigCapture,
    palette: &LibraryPalette,
) -> Option<LibraryIntent> {
    let painter = ui.painter().clone();
    let response = ui.interact(strip, ui.id().with("library-rig-strip"), Sense::click());
    paint::hline(
        &painter,
        strip.left()..=strip.right(),
        strip.top(),
        palette.line,
    );
    paint::hline(
        &painter,
        strip.left()..=strip.right(),
        strip.bottom() - 1.0,
        palette.line,
    );
    let picture = Rect::from_min_size(
        Pos2::new(strip.left(), strip.top() + 12.0),
        Vec2::new(96.0, 64.0),
    );
    painter.rect_filled(picture, CornerRadius::ZERO, palette.raised);
    if let Some(texture) = &rig.picture {
        LibraryPreviews::paint_cover(&painter, picture, texture);
    }
    let x = picture.right() + 16.0;
    let tag = paint::tag(
        &painter,
        Pos2::new(x, strip.top() + 30.0),
        "On the rig now",
        palette.accent,
    );
    paint::text(
        &painter,
        Pos2::new(tag.right() + 8.0, strip.top() + 30.0),
        Align2::LEFT_CENTER,
        &rig.title,
        15.0,
        palette.ink,
        Some(strip.right() - tag.right() - 160.0),
    );
    paint::text(
        &painter,
        Pos2::new(x, strip.top() + 50.0),
        Align2::LEFT_CENTER,
        &rig.detail,
        12.5,
        palette.ink_2,
        Some(strip.right() - x - 160.0),
    );
    let bar = Rect::from_min_size(Pos2::new(x, strip.top() + 64.0), Vec2::new(520.0, 2.0));
    painter.rect_filled(bar, CornerRadius::ZERO, palette.line_2);
    painter.rect_filled(
        Rect::from_min_size(
            bar.min,
            Vec2::new(520.0 * rig.progress.clamp(0.0, 1.0), 2.0),
        ),
        CornerRadius::ZERO,
        palette.ok,
    );
    let label = "Open capture";
    let width = paint::button_width(&painter, label, false, false);
    let button = Rect::from_min_size(
        Pos2::new(strip.right() - width, strip.center().y - 14.0),
        Vec2::new(width, 28.0),
    );
    let open = paint::button(
        ui,
        button,
        "rig-open",
        label,
        None,
        ButtonStyle::Outline,
        palette,
    );
    (open.clicked() || response.clicked()).then_some(LibraryIntent::OpenCapture)
}

#[derive(Clone, Copy)]
struct CardState {
    capturing: bool,
    moved: Option<NodeId>,
    selected: bool,
    now: u64,
}

/// The four bars' colours and the next-step words for a subject.
pub(crate) fn subject_progress(
    summary: &SubjectSummary,
    moved: bool,
    palette: &LibraryPalette,
) -> ([Color32; 4], String) {
    let next = summary.next_step();
    let current = match next {
        NextStep::Stack | NextStep::Check | NextStep::Wait => Some(1),
        NextStep::Develop => Some(2),
        NextStep::Export => Some(3),
        NextStep::Done => None,
    };
    let mut colors = [palette.line_2; 4];
    for (index, step) in summary.steps.iter().enumerate() {
        colors[index] = match step {
            StepState::Done => palette.ok,
            StepState::NeedsLook => palette.warn,
            StepState::Running => palette.accent,
            StepState::NotYet if current == Some(index) && summary.stacks > 0 => palette.accent,
            StepState::NotYet => palette.line_2,
        };
    }
    if summary.stacks == 0 {
        colors = [palette.line_2; 4];
    }
    let words = if moved {
        "locate the sources…".to_owned()
    } else if summary.stacks == 0 {
        "no stacks yet".into()
    } else {
        match next {
            NextStep::Check => format!("{} to check", summary.to_check),
            NextStep::Wait => "stacking…".into(),
            NextStep::Stack if summary.steps[1] == StepState::NotYet => "not stacked yet".into(),
            NextStep::Stack => format!("{} to stack", summary.to_stack),
            NextStep::Develop => "develop next".into(),
            NextStep::Export => "export next".into(),
            NextStep::Done => paint::plural(summary.exports, "export", "exports"),
        }
    };
    (colors, words)
}

fn card_badge(card: &SubjectCard, state: CardState) -> Option<(Option<Mark>, String, bool)> {
    if state.capturing {
        Some((None, "Capturing".into(), true))
    } else if state.moved.is_some() {
        Some((Some(Mark::Bad), "Sources moved".into(), false))
    } else if card.summary.to_check > 0 {
        Some((
            Some(Mark::Warn),
            format!("{} to check", card.summary.to_check),
            false,
        ))
    } else if card.summary.to_stack > 0 && card.summary.stacks > 0 {
        Some((None, format!("{} to stack", card.summary.to_stack), false))
    } else {
        None
    }
}
fn card_meta(card: &SubjectCard, state: CardState) -> String {
    let mut meta = paint::plural(card.stacks.len(), "stack", "stacks");
    let day = paint::day(card.last, state.now);
    if !day.is_empty() {
        meta.push_str(" · ");
        meta.push_str(&day);
    }
    meta.push_str(" · ");
    if state.moved.is_some() {
        meta.push_str("results kept");
    } else {
        meta.push_str(&paint::bytes(card.source_bytes));
    }
    meta
}

fn paint_card(
    ui: &mut Ui,
    rect: Rect,
    card: &SubjectCard,
    texture: Option<&TextureHandle>,
    state: CardState,
    palette: &LibraryPalette,
) -> Option<LibraryIntent> {
    if !ui.is_rect_visible(rect) {
        return None;
    }
    let response = ui.interact(
        rect,
        ui.id().with(("library-card", card.id)),
        Sense::click(),
    );
    let painter = ui.painter().clone();
    let picture = Rect::from_min_size(rect.min, Vec2::new(rect.width(), PICTURE));
    painter.rect_filled(picture, CornerRadius::ZERO, palette.raised);
    if let Some(texture) = texture {
        LibraryPreviews::paint_cover(&painter, picture, texture);
    }
    if state.capturing {
        paint::outline(&painter, picture, 1.5, palette.accent);
    } else if response.hovered() || state.selected {
        paint::outline(
            &painter,
            picture,
            1.0,
            if state.selected {
                palette.ink
            } else {
                palette.ink_3
            },
        );
    }
    if let Some((mark, label, accent)) = card_badge(card, state) {
        paint::badge(
            &painter,
            picture.left_bottom(),
            mark,
            &label,
            accent,
            palette,
        );
    }
    let mut y = picture.bottom() + 9.0;
    paint::text(
        &painter,
        Pos2::new(rect.left(), y),
        Align2::LEFT_TOP,
        &card.name,
        13.5,
        palette.ink,
        Some(rect.width()),
    );
    y += 19.0;
    paint::text(
        &painter,
        Pos2::new(rect.left(), y),
        Align2::LEFT_TOP,
        &card_meta(card, state),
        12.0,
        palette.ink_3,
        Some(rect.width()),
    );
    y += 24.0;
    let (colors, words) = subject_progress(&card.summary, state.moved.is_some(), palette);
    let bars = paint::life_bars(&painter, Pos2::new(rect.left(), y), colors);
    let words_rect = paint::text(
        &painter,
        Pos2::new(rect.left() + bars + 10.0, y + 1.5),
        Align2::LEFT_CENTER,
        &words,
        11.5,
        palette.ink_3,
        Some(rect.width() - bars - 10.0),
    );
    if let Some(stack) = state.moved
        && locate_link(ui, &painter, words_rect, card.id, palette)
    {
        return Some(LibraryIntent::Locate(stack));
    }
    (response.clicked() || response.double_clicked()).then_some(LibraryIntent::OpenSubject(card.id))
}

/// "locate the sources…" as a link; true when clicked.
fn locate_link(
    ui: &mut Ui,
    painter: &egui::Painter,
    words: Rect,
    card: NodeId,
    palette: &LibraryPalette,
) -> bool {
    let link = ui.interact(
        words.expand(3.0),
        ui.id().with(("library-locate", card)),
        Sense::click(),
    );
    if link.hovered() {
        paint::hline(
            painter,
            words.left()..=words.right(),
            words.bottom(),
            palette.ink_3,
        );
    }
    link.clicked()
}

fn paint_row(
    ui: &mut Ui,
    rect: Rect,
    card: &SubjectCard,
    texture: Option<&TextureHandle>,
    state: CardState,
    palette: &LibraryPalette,
) -> Option<LibraryIntent> {
    if !ui.is_rect_visible(rect) {
        return None;
    }
    let rect = Rect::from_min_size(rect.min, Vec2::new(rect.width(), LIST_ROW));
    let response = ui.interact(rect, ui.id().with(("library-row", card.id)), Sense::click());
    let painter = ui.painter().clone();
    if response.hovered() || state.selected {
        painter.rect_filled(rect, CornerRadius::ZERO, palette.raised);
    }
    paint::hline(
        &painter,
        rect.left()..=rect.right(),
        rect.top(),
        palette.line,
    );
    let picture = Rect::from_min_size(rect.min + Vec2::new(0.0, 6.0), Vec2::new(96.0, 64.0));
    painter.rect_filled(picture, CornerRadius::ZERO, palette.raised);
    if let Some(texture) = texture {
        LibraryPreviews::paint_cover(&painter, picture, texture);
    }
    if state.capturing {
        paint::outline(&painter, picture, 1.5, palette.accent);
    }
    let x = picture.right() + 16.0;
    paint::text(
        &painter,
        Pos2::new(x, rect.top() + 26.0),
        Align2::LEFT_CENTER,
        &card.name,
        13.5,
        palette.ink,
        Some(320.0),
    );
    paint::text(
        &painter,
        Pos2::new(x, rect.top() + 47.0),
        Align2::LEFT_CENTER,
        &card_meta(card, state),
        12.0,
        palette.ink_3,
        Some(320.0),
    );
    let (colors, words) = subject_progress(&card.summary, state.moved.is_some(), palette);
    let life_x = x + 340.0;
    let bars = paint::life_bars(&painter, Pos2::new(life_x, rect.top() + 36.0), colors);
    let words_rect = paint::text(
        &painter,
        Pos2::new(life_x + bars + 10.0, rect.top() + 37.5),
        Align2::LEFT_CENTER,
        &words,
        11.5,
        palette.ink_3,
        Some(240.0),
    );
    if let Some(stack) = state.moved
        && locate_link(ui, &painter, words_rect, card.id, palette)
    {
        return Some(LibraryIntent::Locate(stack));
    }
    if let Some((mark, label, accent)) = card_badge(card, state) {
        paint::badge(
            &painter,
            Pos2::new(rect.right() - 200.0, rect.top() + 46.0),
            mark,
            &label,
            accent,
            palette,
        );
    }
    response
        .clicked()
        .then_some(LibraryIntent::OpenSubject(card.id))
}

#[cfg(test)]
#[path = "library-station-tests.rs"]
pub(crate) mod tests;

#[cfg(test)]
#[path = "library-visual-tests.rs"]
pub(crate) mod visual_tests;
