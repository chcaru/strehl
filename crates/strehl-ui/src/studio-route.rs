//! Navigation (implementation plan 6.2): one route instead of four
//! overlapping variables.
//!
//! While the stations still draw today's panes, the route is the source of
//! truth and a one-way adapter writes today's `Sidebar` / `process_view`
//! flags from it, so every pane, test and agent command that reads those
//! flags keeps working. Older code that still *writes* them (an agent's
//! `OpenCapture`, opening a photograph in Edit, a finished stack) is adopted
//! at the next sync: the route follows, then the adapter writes the flags
//! back. Navigation always syncs first, so an explicit choice wins over a flag
//! changed earlier in the same frame.
use super::workspace::Sidebar;
use crate::workspace_history::NodeId;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

/// The five stations across the top bar, in lifecycle order.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum Station {
    #[default]
    Library,
    Capture,
    Stack,
    Develop,
    Export,
}
impl Station {
    pub(crate) const ALL: [Self; 5] = [
        Self::Library,
        Self::Capture,
        Self::Stack,
        Self::Develop,
        Self::Export,
    ];
    /// 1 to 5, as printed before the label.
    pub(crate) fn number(self) -> u8 {
        match self {
            Self::Library => 1,
            Self::Capture => 2,
            Self::Stack => 3,
            Self::Develop => 4,
            Self::Export => 5,
        }
    }
    pub(crate) fn from_number(number: u8) -> Option<Self> {
        Self::ALL.into_iter().find(|s| s.number() == number)
    }
    pub(crate) fn label(self) -> &'static str {
        match self {
            Self::Library => "Library",
            Self::Capture => "Capture",
            Self::Stack => "Stack",
            Self::Develop => "Develop",
            Self::Export => "Export",
        }
    }
    /// Capture, Stack, Develop and Export carry a state mark; the Library
    /// does not.
    pub(crate) fn has_state(self) -> bool {
        self != Self::Library
    }
}

/// What a library view lists (P4 builds the views; the shell keeps them).
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Need {
    /// Captured, not stacked yet.
    Stacking,
    /// A render with checks that need a look.
    Checking,
    /// Rendered, not developed yet.
    Developing,
}
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum LibraryView {
    #[default]
    All,
    Collection(NodeId),
    NeedsYou(Need),
}
#[allow(dead_code)] // Part of the Studio 2 API for the station agents (P3 to P7).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum CaptureMode {
    #[default]
    Plan,
    Flight,
    Glance,
}
/// The Stack station shows the photograph with its checks, or the engine room.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum Room {
    #[default]
    Photograph,
    Engine,
}

/// Where the desktop is. `stack` and `render` name the open document; they
/// are optional because today a bracket can be open before it is saved as a
/// stack, and a photograph can be opened on its own.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum Route {
    Library(LibraryView),
    Subject(NodeId),
    Capture(CaptureMode),
    Stack {
        stack: Option<NodeId>,
        render: Option<PathBuf>,
        room: Room,
    },
    Develop {
        stack: Option<NodeId>,
        render: Option<PathBuf>,
    },
    Export {
        stack: Option<NodeId>,
        render: Option<PathBuf>,
    },
}
impl Default for Route {
    fn default() -> Self {
        Self::Library(LibraryView::All)
    }
}
impl Route {
    pub(crate) fn station(&self) -> Station {
        match self {
            Self::Library(_) | Self::Subject(_) => Station::Library,
            Self::Capture(_) => Station::Capture,
            Self::Stack { .. } => Station::Stack,
            Self::Develop { .. } => Station::Develop,
            Self::Export { .. } => Station::Export,
        }
    }
    /// The route opened by a station's button, for the given document.
    pub(crate) fn for_station(
        station: Station,
        stack: Option<NodeId>,
        render: Option<PathBuf>,
    ) -> Self {
        match station {
            Station::Library => Self::Library(LibraryView::All),
            Station::Capture => Self::Capture(CaptureMode::Plan),
            Station::Stack => Self::Stack {
                stack,
                render,
                room: Room::Photograph,
            },
            Station::Develop => Self::Develop { stack, render },
            Station::Export => Self::Export { stack, render },
        }
    }
    pub(crate) fn room(&self) -> Option<Room> {
        match self {
            Self::Stack { room, .. } => Some(*room),
            _ => None,
        }
    }
    /// Its `--route` name and agent snapshot key.
    pub(crate) fn key(&self) -> &'static str {
        match self {
            Self::Library(_) => "library",
            Self::Subject(_) => "subject",
            Self::Capture(_) => "capture",
            Self::Stack {
                room: Room::Engine, ..
            } => "engine",
            Self::Stack { .. } => "stack",
            Self::Develop { .. } => "develop",
            Self::Export { .. } => "export",
        }
    }
    fn document(&self) -> Option<(Option<NodeId>, Option<&Path>)> {
        match self {
            Self::Stack { stack, render, .. }
            | Self::Develop { stack, render }
            | Self::Export { stack, render } => Some((*stack, render.as_deref())),
            _ => None,
        }
    }
    /// Follow the open document without allocating when it is unchanged.
    fn follow_document(&mut self, active: Option<NodeId>, result: Option<&Path>) {
        if self
            .document()
            .is_none_or(|current| current == (active, result))
        {
            return;
        }
        match self {
            Self::Stack { stack, render, .. }
            | Self::Develop { stack, render }
            | Self::Export { stack, render } => {
                *stack = active;
                *render = result.map(Path::to_path_buf);
            }
            _ => {}
        }
    }
}

/// A `--route` launch request, applied once the document is open.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum LaunchRoute {
    Library,
    Subject,
    Capture,
    Stack,
    Engine,
    Develop,
    Export,
}
impl LaunchRoute {
    pub(crate) const NAMES: &'static str = "library|subject|capture|stack|engine|develop|export";
    pub(crate) fn parse(value: &str) -> Option<Self> {
        Some(match value.trim().to_ascii_lowercase().as_str() {
            "library" => Self::Library,
            "subject" => Self::Subject,
            "capture" => Self::Capture,
            "stack" => Self::Stack,
            "engine" => Self::Engine,
            "develop" => Self::Develop,
            "export" => Self::Export,
            _ => return None,
        })
    }
    /// Subjects arrive with catalog format 2 (P4); until then a subject
    /// route opens the Library with the open stack selected.
    pub(crate) fn route(self, stack: Option<NodeId>, render: Option<PathBuf>) -> Route {
        match self {
            Self::Library => Route::Library(LibraryView::All),
            Self::Subject => stack.map_or(Route::Library(LibraryView::All), Route::Subject),
            Self::Capture => Route::Capture(CaptureMode::Plan),
            Self::Stack => Route::for_station(Station::Stack, stack, render),
            Self::Engine => Route::Stack {
                stack,
                render,
                room: Room::Engine,
            },
            Self::Develop => Route::Develop { stack, render },
            Self::Export => Route::Export { stack, render },
        }
    }
}

/// The Stack inspector's tabs while it shows today's Adjust and Review panes.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum StackTab {
    #[default]
    Adjust,
    Review,
}
/// Panes that are not stations. They open in the inspector over any
/// station, from the brand menu, the activity tray or the palette.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Drawer {
    Agent,
    Activity,
}
impl Drawer {
    pub(crate) fn label(self) -> &'static str {
        match self {
            Self::Agent => "Agent",
            Self::Activity => "Activity log",
        }
    }
}

type Legacy = (Option<Sidebar>, bool);

/// The route, per-station view state and the adapter's memory.
#[derive(Default)]
pub(crate) struct Navigator {
    route: Route,
    pub stack_tab: StackTab,
    pub drawer: Option<Drawer>,
    /// The flags the adapter last wrote; a difference means old code wrote.
    applied: Option<Legacy>,
    revision: u64,
}
impl Navigator {
    pub(crate) fn route(&self) -> &Route {
        &self.route
    }
    pub(crate) fn station(&self) -> Station {
        self.route.station()
    }
    /// Changes whenever the route, tab or drawer changes.
    pub(crate) fn revision(&self) -> u64 {
        self.revision
    }

    /// The flags today's panes read, for the current route.
    pub(in crate::app) fn legacy(&self, process_view: bool) -> Legacy {
        let sidebar = match self.drawer {
            Some(Drawer::Agent) => Some(Sidebar::Agent),
            Some(Drawer::Activity) => Some(Sidebar::Activity),
            None => match &self.route {
                Route::Library(_) | Route::Subject(_) => Some(Sidebar::Projects),
                Route::Capture(_) => Some(Sidebar::Capture),
                Route::Stack {
                    room: Room::Engine, ..
                } => None,
                Route::Stack { .. } => Some(match self.stack_tab {
                    StackTab::Adjust => Sidebar::Adjust,
                    StackTab::Review => Sidebar::Review,
                }),
                Route::Develop { .. } => Some(Sidebar::Edit),
                Route::Export { .. } => Some(Sidebar::Export),
            },
        };
        // The engine room also hosts the diagnostic workbench that opens
        // with process_view off (`--draft`, `--workbench`, a dropped image).
        let process_view = process_view || self.route.room() != Some(Room::Engine);
        (sidebar, process_view)
    }

    /// Adopt flags older code wrote since the last sync.
    fn adopt(&mut self, (sidebar, process_view): Legacy) {
        let before = (self.route.clone(), self.stack_tab, self.drawer);
        let (stack, render) = self
            .route
            .document()
            .map_or((None, None), |(s, r)| (s, r.map(Path::to_path_buf)));
        match sidebar {
            Some(Sidebar::Agent) => self.drawer = Some(Drawer::Agent),
            Some(Sidebar::Activity) => self.drawer = Some(Drawer::Activity),
            other => {
                self.drawer = None;
                let station = match other {
                    Some(Sidebar::Projects) => Station::Library,
                    Some(Sidebar::Capture) => Station::Capture,
                    Some(Sidebar::Adjust) => {
                        self.stack_tab = StackTab::Adjust;
                        Station::Stack
                    }
                    Some(Sidebar::Review) => {
                        self.stack_tab = StackTab::Review;
                        Station::Stack
                    }
                    Some(Sidebar::Edit) => Station::Develop,
                    Some(Sidebar::Export) => Station::Export,
                    Some(Sidebar::Agent | Sidebar::Activity) => unreachable!(),
                    None => Station::Stack,
                };
                let engine = other.is_none() || !process_view;
                if station != self.route.station()
                    || engine != (self.route.room() == Some(Room::Engine))
                {
                    self.route = if engine {
                        Route::Stack {
                            stack,
                            render,
                            room: Room::Engine,
                        }
                    } else if station == Station::Library
                        && self.route.station() == Station::Library
                    {
                        self.route.clone()
                    } else {
                        Route::for_station(station, stack, render)
                    };
                }
            }
        }
        if (self.route.clone(), self.stack_tab, self.drawer) != before {
            self.revision += 1;
        }
    }

    /// Run once a frame (and before every navigation): adopt flags written
    /// by older code, write the adapter's flags, and follow the document.
    pub(in crate::app) fn sync(
        &mut self,
        sidebar: &mut Option<Sidebar>,
        process_view: &mut bool,
        active: Option<NodeId>,
        result: Option<&Path>,
    ) {
        let current = (*sidebar, *process_view);
        if self.applied != Some(current) {
            self.adopt(current);
        }
        self.route.follow_document(active, result);
        let wanted = self.legacy(*process_view);
        (*sidebar, *process_view) = wanted;
        self.applied = Some(wanted);
    }

    /// Go somewhere. Closes any drawer: choosing a station means its panes.
    pub(crate) fn go(&mut self, route: Route) {
        if self.route != route || self.drawer.is_some() {
            self.route = route;
            self.drawer = None;
            self.revision += 1;
        }
    }
    pub(crate) fn set_stack_tab(&mut self, tab: StackTab) {
        if self.stack_tab != tab {
            self.stack_tab = tab;
            self.revision += 1;
        }
    }
    pub(crate) fn set_room(&mut self, room: Room) {
        if let Route::Stack { room: current, .. } = &mut self.route
            && *current != room
        {
            *current = room;
            self.revision += 1;
        }
    }
    pub(crate) fn toggle_drawer(&mut self, drawer: Drawer) {
        self.drawer = if self.drawer == Some(drawer) {
            None
        } else {
            Some(drawer)
        };
        self.revision += 1;
    }
    pub(crate) fn close_drawer(&mut self) {
        if self.drawer.take().is_some() {
            self.revision += 1;
        }
    }
}

#[cfg(test)]
#[path = "studio-route-tests.rs"]
mod tests;
