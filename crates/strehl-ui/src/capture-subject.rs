//! Where the next stack goes (owner feedback, 2026-11-22: "the default
//! subject for capture is i guess the most recent subject? i think it should
//! actually be a new one by default and force a new name. I've forgotten
//! twice now to create a new subject and the stack went to the wrong
//! subject, when it should have been new.").
//!
//! A capture starts a new subject unless an existing one is chosen on
//! purpose: picked from the subject field's list, or asked for from the
//! Library ("New stack of this subject", "Shoot again"). Typing a name makes
//! it a new subject again. Until the new subject has a name of its own, or
//! the chosen subject is still in the library, Start and Schedule wait
//! (`preflight::start_blockers`). Once a capture has taken the names, the
//! plan clears them for the next one. Test shots, calibrations and surveys
//! make no stack and do not ask.
use super::preflight::{Blocker, Check, Fix};
use crate::workspace_history::NodeId;

/// The longest subject name the catalog accepts.
const MAX_NAME_CHARS: usize = 160;

/// A subject in the catalog, as the plan offers it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct SubjectChoice {
    pub id: NodeId,
    pub name: String,
    /// Its collection and stacks: "Bugs · 2 stacks".
    pub detail: String,
}

/// Where the next stack goes, from the plan's subject field.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum Destination {
    /// Nothing typed and nothing chosen.
    Unnamed,
    /// A new subject of this name.
    New(String),
    /// The name typed is an existing subject's, which was not chosen.
    Taken(String),
    /// Not a name the catalog accepts.
    Invalid(String),
    /// An existing subject, chosen on purpose.
    Existing(SubjectChoice),
    /// The chosen subject has left the library.
    Gone(String),
}

impl Destination {
    /// Whether a stack can start with it.
    pub(crate) fn ready(&self) -> bool {
        matches!(self, Self::New(_) | Self::Existing(_))
    }
}

/// Where a capture started now would go.
pub(crate) fn destination(
    typed: &str,
    chosen: Option<NodeId>,
    subjects: &[SubjectChoice],
) -> Destination {
    let name = typed.trim();
    if let Some(id) = chosen {
        return match subjects.iter().find(|s| s.id == id) {
            Some(subject) => Destination::Existing(subject.clone()),
            None => Destination::Gone(name.to_owned()),
        };
    }
    if name.is_empty() {
        return Destination::Unnamed;
    }
    if name.chars().count() > MAX_NAME_CHARS || name.chars().any(char::is_control) {
        return Destination::Invalid(format!(
            "Use a subject name of at most {MAX_NAME_CHARS} characters, without control characters"
        ));
    }
    // Compared without allocating: this runs for every Start check.
    let same = |other: &str| {
        other
            .trim()
            .chars()
            .flat_map(char::to_lowercase)
            .eq(name.chars().flat_map(char::to_lowercase))
    };
    match subjects.iter().find(|s| same(&s.name)) {
        Some(existing) => Destination::Taken(existing.name.clone()),
        None => Destination::New(name.to_owned()),
    }
}

/// The plan's one line under the names: where the stack goes, or what to
/// do first. `home` is where a new subject is made.
pub(crate) fn sentence(destination: &Destination, home: &str) -> String {
    match destination {
        Destination::Unnamed => {
            "Name the new subject this stack starts, or choose an existing one".into()
        }
        Destination::New(name) => {
            format!("Goes to a new subject, \u{201c}{name}\u{201d}, in {home}")
        }
        Destination::Taken(name) => format!(
            "\u{201c}{name}\u{201d} is already a subject: choose it from the list to add this \
             stack to it, or name a new one"
        ),
        Destination::Invalid(why) => why.clone(),
        Destination::Existing(subject) => {
            if subject.detail.is_empty() {
                format!("Adds a stack to \u{201c}{}\u{201d}", subject.name)
            } else {
                format!(
                    "Adds a stack to \u{201c}{}\u{201d} · {}",
                    subject.name, subject.detail
                )
            }
        }
        Destination::Gone(name) => format!(
            "\u{201c}{name}\u{201d} is no longer in the library: choose another subject or \
             name a new one"
        ),
    }
}

/// Start's blocker for the subject, when it is not ready.
pub(crate) fn blocker(destination: &Destination) -> Option<Blocker> {
    if destination.ready() {
        return None;
    }
    Some(Blocker {
        check: Check::Subject,
        chip: "Subject",
        sentence: sentence(destination, ""),
        fix: Some(Fix::NameSubject),
    })
}

#[cfg(test)]
#[path = "capture-subject-tests.rs"]
mod tests;
