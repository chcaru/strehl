//! A new subject from the Library (owner feedback, 2026-11-22: "i would like
//! a way to create a new empty subject right there, without choosing
//! anything. this would allow me to move stacks around if needed").
//!
//! One modal names it. The name is required and may not be the name of a
//! subject already in the library (ignoring case); the dialog says where the
//! subject goes and lets the collection be changed. The same dialog names
//! the new subject of "Move to subject > New subject…", which moves the
//! chosen stacks into it. Either is one entry of the project journal
//! (`ProjectExplorer::organize_creating`): Ctrl Z takes the subject out of
//! the library again (and moves the stacks back), Ctrl Shift Z redoes it.
use super::studio_route::{LibraryView as RouteLibraryView, Route};
use super::*;
use crate::{
    library_paint::plural,
    library_station::LibraryFilter,
    notices::Severity,
    studio_theme, studio_widgets as w,
    workspace_history::{Catalog, NodeId, NodeKind},
};

/// The naming of a new subject, open until it is made or cancelled.
#[derive(Clone, Debug, PartialEq)]
pub(super) struct NewSubjectDraft {
    pub name: String,
    /// The collection or folder it goes in; None when the library has no
    /// collection yet (one named "Library" is made with it).
    pub container: Option<NodeId>,
    /// Stacks that move into it when it is made.
    pub stacks: Vec<NodeId>,
    pub focus: bool,
}

/// Where a new subject goes by default: the collection being viewed, else
/// the folder of the first stack's subject (a move), else the collection of
/// the subject under the keyboard cursor, else the first collection.
pub(super) fn default_container(
    catalog: &Catalog,
    viewing: Option<NodeId>,
    stacks: &[NodeId],
    cursor: Option<NodeId>,
) -> Option<NodeId> {
    let container = |id: NodeId| {
        catalog
            .node(id)
            .is_some_and(|n| matches!(n.kind, NodeKind::Project | NodeKind::Folder))
    };
    let parent_of = |id: NodeId| catalog.node(id).and_then(|n| n.parent);
    viewing
        .filter(|&id| container(id))
        .or_else(|| {
            let subject = catalog.subject_of(*stacks.first()?)?;
            parent_of(subject).filter(|&id| container(id))
        })
        .or_else(|| parent_of(cursor?).filter(|&id| container(id)))
        .or_else(|| {
            catalog
                .nodes
                .iter()
                .find(|n| n.parent.is_none() && n.kind == NodeKind::Project)
                .map(|n| n.id)
        })
}

/// The collections a new subject may go in: every top-level collection,
/// plus `current` when it is a folder inside one.
fn homes(catalog: &Catalog, current: Option<NodeId>) -> Vec<(NodeId, String)> {
    let mut homes: Vec<(NodeId, String)> = catalog
        .nodes
        .iter()
        .filter(|n| n.parent.is_none() && n.kind == NodeKind::Project)
        .map(|n| (n.id, n.name.clone()))
        .collect();
    if let Some(node) = current.and_then(|id| catalog.node(id))
        && !homes.iter().any(|(id, _)| *id == node.id)
    {
        homes.push((node.id, node.name.clone()));
    }
    homes
}

impl StrehlApp {
    /// Open the naming of a new subject: empty (`stacks` empty) or for the
    /// stacks to move into it.
    pub(super) fn library_new_subject(&mut self, collection: Option<NodeId>, stacks: Vec<NodeId>) {
        let viewing = collection.or(match self.library.station.filter {
            LibraryFilter::Collection(id) => Some(id),
            _ => None,
        });
        let container = default_container(
            &self.catalog,
            viewing,
            &stacks,
            self.library.station.selected,
        );
        self.library.new_subject = Some(NewSubjectDraft {
            name: String::new(),
            container,
            stacks,
            focus: true,
        });
    }

    /// Escape closes the dialog and is not also seen by the Library beneath
    /// (which would clear its selection). Call before the Library paints.
    pub(super) fn library_new_subject_keys(&mut self, ctx: &egui::Context) {
        if self.library.new_subject.is_some()
            && ctx.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape))
        {
            self.library.new_subject = None;
        }
    }

    /// The naming dialog, over the Library or a subject page.
    pub(super) fn library_new_subject_window(&mut self, ctx: &egui::Context) {
        let Some(draft) = self.library.new_subject.as_mut() else {
            return;
        };
        let t = studio_theme::tokens(ctx);
        let catalog = &self.catalog;
        let checked = catalog.new_subject_name(&draft.name);
        let homes = homes(catalog, draft.container);
        let stacks: Vec<String> = draft
            .stacks
            .iter()
            .filter_map(|&id| catalog.node(id).map(|n| n.name.clone()))
            .collect();
        let mut make = false;
        let mut cancel = false;
        let frame = egui::Frame::popup(&ctx.style())
            .fill(t.panel)
            .stroke(egui::Stroke::new(1.0_f32, t.line2))
            .inner_margin(egui::Margin::same(22));
        let modal = egui::Modal::new(egui::Id::new("library-new-subject"))
            .frame(frame)
            .backdrop_color(egui::Color32::from_black_alpha(if t.light {
                60
            } else {
                120
            }))
            .show(ctx, |ui| {
                ui.set_width(440.0);
                ui.spacing_mut().item_spacing = egui::vec2(10.0, 8.0);
                w::caps(ui, "New subject");
                let edit = ui.add(
                    egui::TextEdit::singleline(&mut draft.name)
                        .id_salt("library-new-subject-name")
                        .hint_text("Name the subject")
                        .desired_width(f32::INFINITY)
                        .font(egui::FontId::proportional(15.0))
                        .text_color(t.ink)
                        .background_color(t.bg)
                        .margin(egui::Margin::symmetric(9, 6)),
                );
                ui.painter().rect_stroke(
                    edit.rect,
                    0.0,
                    egui::Stroke::new(1.0_f32, t.line2),
                    egui::StrokeKind::Inside,
                );
                if std::mem::take(&mut draft.focus) {
                    edit.request_focus();
                }
                // Why it cannot be made yet: only once something is typed.
                let problem = match &checked {
                    Err(error) if !draft.name.trim().is_empty() => Some(format!("{error:#}")),
                    _ => None,
                };
                ui.label(
                    egui::RichText::new(
                        problem.clone().unwrap_or_else(|| {
                            "A name of its own: no other subject has it.".into()
                        }),
                    )
                    .size(12.0)
                    .color(if problem.is_some() { t.warn } else { t.ink3 }),
                );
                ui.add_space(4.0);
                w::section(ui, "Goes in", |_| {});
                if homes.is_empty() {
                    ui.label(
                        egui::RichText::new("A new collection, \"Library\"")
                            .size(13.0)
                            .color(t.ink2),
                    );
                } else {
                    ui.horizontal_wrapped(|ui| {
                        ui.spacing_mut().item_spacing = egui::vec2(6.0, 6.0);
                        for (id, name) in &homes {
                            let chosen = draft.container == Some(*id);
                            if ui
                                .add(w::Button::new(name).small().selected(chosen))
                                .clicked()
                            {
                                draft.container = Some(*id);
                            }
                        }
                    });
                }
                if !stacks.is_empty() {
                    ui.add_space(4.0);
                    w::section(ui, "Moves into it", |_| {});
                    let mut line = stacks
                        .iter()
                        .take(4)
                        .cloned()
                        .collect::<Vec<_>>()
                        .join(", ");
                    if stacks.len() > 4 {
                        line.push_str(&format!(" and {} more", stacks.len() - 4));
                    }
                    ui.add(
                        egui::Label::new(
                            egui::RichText::new(format!(
                                "{}: {line}",
                                plural(stacks.len(), "stack", "stacks")
                            ))
                            .size(13.0)
                            .color(t.ink),
                        )
                        .wrap(),
                    );
                }
                ui.add_space(10.0);
                ui.horizontal(|ui| {
                    let label = if stacks.is_empty() {
                        "Make subject".to_owned()
                    } else {
                        format!(
                            "Make it and move {}",
                            plural(stacks.len(), "stack", "stacks")
                        )
                    };
                    make |= ui
                        .add(w::Button::primary(&label).enabled(checked.is_ok()))
                        .clicked();
                    cancel |= ui.add(w::Button::quiet("Cancel")).clicked();
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.label(
                            egui::RichText::new("Enter makes it · Ctrl Z takes it back")
                                .size(11.5)
                                .color(t.ink3),
                        );
                    });
                });
                make |= checked.is_ok()
                    && ui.input(|i| i.key_pressed(egui::Key::Enter))
                    && (edit.lost_focus() || !edit.has_focus());
            });
        if modal.should_close() {
            cancel = true;
        }
        if cancel {
            self.library.new_subject = None;
        } else if make {
            let draft = self.library.new_subject.take().unwrap();
            self.library_make_subject(draft);
        }
    }

    /// Make the subject (and move its stacks) as one journal entry.
    pub(super) fn library_make_subject(&mut self, draft: NewSubjectDraft) {
        let NewSubjectDraft {
            name,
            container,
            stacks,
            ..
        } = draft;
        let made = self
            .project_explorer
            .organize_creating(&mut self.catalog, |catalog| {
                let name = catalog.new_subject_name(&name)?;
                let container = match container.filter(|&id| {
                    catalog
                        .node(id)
                        .is_some_and(|n| matches!(n.kind, NodeKind::Project | NodeKind::Folder))
                }) {
                    Some(id) => id,
                    None => catalog.create_project("Library")?,
                };
                let subject = catalog.create_subject(container, &name)?;
                for &stack in &stacks {
                    catalog.can_move(stack, Some(subject))?;
                }
                for &stack in &stacks {
                    catalog.move_node(stack, Some(subject))?;
                }
                Ok((subject, vec![subject]))
            });
        let subject = match made {
            Ok(subject) => subject,
            Err(error) => {
                self.library_notice(Severity::Warning, format!("{error:#}"));
                return;
            }
        };
        self.persist_catalog();
        let name = self
            .catalog
            .node(subject)
            .map(|n| n.name.clone())
            .unwrap_or_default();
        let text = if stacks.is_empty() {
            format!("Made the subject \"{name}\" · Ctrl Z takes it back")
        } else {
            format!(
                "Moved {} to the new subject \"{name}\" · Ctrl Z undoes it",
                plural(stacks.len(), "stack", "stacks")
            )
        };
        self.library_notice(Severity::Done, text);
        // On the grid, the new card is shown and under the keyboard cursor.
        if stacks.is_empty() {
            let station = &mut self.library.station;
            let collection = self
                .catalog
                .node(subject)
                .and_then(|n| n.parent)
                .map(|mut at| {
                    while let Some(parent) = self.catalog.node(at).and_then(|n| n.parent) {
                        at = parent;
                    }
                    at
                });
            if !matches!(station.filter, LibraryFilter::All)
                && collection.is_none_or(|c| station.filter != LibraryFilter::Collection(c))
            {
                station.filter = LibraryFilter::All;
            }
            if !station.query.trim().is_empty()
                && !name
                    .to_lowercase()
                    .contains(&station.query.trim().to_lowercase())
            {
                station.query.clear();
            }
            station.selected = Some(subject);
            if !matches!(self.shell.navigator.route(), Route::Library(_)) {
                self.navigate(Route::Library(RouteLibraryView::All));
            }
        }
    }
}

#[cfg(test)]
#[path = "app-library-subject-tests.rs"]
mod tests;
