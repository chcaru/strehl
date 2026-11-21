//! Notices (implementation plan 6.6): a bounded list of what happened, with
//! its severity, source and time. The top bar shows the newest unread failure
//! and the activity tray lists them all.
//!
//! About seventy places still write the app's single `status` and `error`
//! strings. Rather than rewrite them all at once, `observe` turns each new
//! error into a failure notice and clears it when the app clears the error;
//! those two strings remain the derived values the agent snapshot reports.
//! New code calls `push` directly.
use serde_json::{Value, json};
use std::{collections::VecDeque, time::SystemTime};

/// At most this many notices are kept; the oldest go first.
pub(crate) const CAPACITY: usize = 64;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Severity {
    Info,
    Done,
    Warning,
    Failure,
}
impl Severity {
    pub(crate) fn key(self) -> &'static str {
        match self {
            Self::Info => "info",
            Self::Done => "done",
            Self::Warning => "warning",
            Self::Failure => "failure",
        }
    }
}

/// Where a notice came from; shown beside it in the tray.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Source {
    App,
    Stack,
    Capture,
    Develop,
    Export,
    Library,
}
impl Source {
    pub(crate) fn label(self) -> &'static str {
        match self {
            Self::App => "Strehl",
            Self::Stack => "Stack",
            Self::Capture => "Capture",
            Self::Develop => "Develop",
            Self::Export => "Export",
            Self::Library => "Library",
        }
    }
}

/// What the notice offers to do next.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum Action {
    /// Open the engine log (the Activity pane).
    OpenLog,
    /// Go to a station by its number, 1 to 5.
    OpenStation(u8),
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Notice {
    pub id: u64,
    pub severity: Severity,
    pub text: String,
    pub source: Source,
    pub time: SystemTime,
    pub action: Option<Action>,
    pub read: bool,
    /// The condition behind a failure has cleared; it stays in the history.
    pub resolved: bool,
}

#[derive(Default)]
pub(crate) struct Notices {
    list: VecDeque<Notice>,
    next: u64,
    revision: u64,
    observed: Vec<(Source, Option<String>)>,
}

impl Notices {
    pub(crate) fn push(
        &mut self,
        severity: Severity,
        source: Source,
        text: impl Into<String>,
        action: Option<Action>,
    ) -> u64 {
        let text = text.into();
        // A repeat of the newest notice refreshes it instead of stacking up.
        if let Some(newest) = self.list.back_mut()
            && newest.text == text
            && newest.severity == severity
            && newest.source == source
            && !newest.resolved
        {
            newest.time = SystemTime::now();
            newest.read = false;
            self.revision += 1;
            return newest.id;
        }
        self.next += 1;
        if self.list.len() == CAPACITY {
            self.list.pop_front();
        }
        self.list.push_back(Notice {
            id: self.next,
            severity,
            text,
            source,
            time: SystemTime::now(),
            action,
            read: false,
            resolved: false,
        });
        self.revision += 1;
        self.next
    }

    /// Follow a legacy error string for one source: a new error becomes a
    /// failure notice; clearing it resolves that notice. Compares only, so it
    /// is cheap to call every frame.
    pub(crate) fn observe(&mut self, source: Source, error: Option<&str>) {
        let slot = match self.observed.iter().position(|(s, _)| *s == source) {
            Some(index) => index,
            None => {
                self.observed.push((source, None));
                self.observed.len() - 1
            }
        };
        if self.observed[slot].1.as_deref() == error {
            return;
        }
        if let Some(previous) = self.observed[slot].1.take() {
            for notice in self.list.iter_mut().rev() {
                if notice.source == source
                    && notice.severity == Severity::Failure
                    && notice.text == previous
                    && !notice.resolved
                {
                    notice.resolved = true;
                    self.revision += 1;
                    break;
                }
            }
        }
        if let Some(error) = error {
            let action = (source == Source::Stack).then_some(Action::OpenLog);
            self.push(Severity::Failure, source, error, action);
            self.observed[slot].1 = Some(error.to_owned());
        }
    }

    /// The newest failure that is unread and still current.
    pub(crate) fn newest_unread_failure(&self) -> Option<&Notice> {
        self.list
            .iter()
            .rev()
            .find(|n| n.severity == Severity::Failure && !n.read && !n.resolved)
    }
    pub(crate) fn unread(&self) -> usize {
        self.list.iter().filter(|n| !n.read).count()
    }
    pub(crate) fn mark_all_read(&mut self) {
        if self.list.iter().any(|n| !n.read) {
            for notice in &mut self.list {
                notice.read = true;
            }
            self.revision += 1;
        }
    }
    pub(crate) fn dismiss(&mut self, id: u64) {
        let before = self.list.len();
        self.list.retain(|n| n.id != id);
        if self.list.len() != before {
            self.revision += 1;
        }
    }
    /// Newest first.
    pub(crate) fn iter(&self) -> impl Iterator<Item = &Notice> {
        self.list.iter().rev()
    }
    pub(crate) fn len(&self) -> usize {
        self.list.len()
    }
    #[cfg(test)]
    pub(crate) fn revision(&self) -> u64 {
        self.revision
    }
    /// Additive `notices` key of the agent snapshot.
    pub(crate) fn snapshot(&self) -> Value {
        Value::Array(
            self.iter()
                .take(16)
                .map(|n| {
                    json!({"id":n.id,"severity":n.severity.key(),"source":n.source.label(),
                        "text":n.text,"read":n.read,"resolved":n.resolved,
                        "time_unix":n.time.duration_since(SystemTime::UNIX_EPOCH).map_or(0, |d| d.as_secs())})
                })
                .collect(),
        )
    }
}

/// How long ago, as the project explorer writes it.
pub(crate) fn ago(time: SystemTime, now: SystemTime) -> String {
    let age = now.duration_since(time).map_or(0, |d| d.as_secs());
    if age < 60 {
        "just now".into()
    } else if age < 3600 {
        format!("{}m ago", age / 60)
    } else if age < 86_400 {
        format!("{}h ago", age / 3600)
    } else {
        format!("{}d ago", age / 86_400)
    }
}

#[cfg(test)]
#[path = "notices-tests.rs"]
mod tests;
