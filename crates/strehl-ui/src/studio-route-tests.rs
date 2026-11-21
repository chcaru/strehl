use super::*;

fn synced(navigator: &mut Navigator, sidebar: Option<Sidebar>, process_view: bool) -> Legacy {
    let (mut s, mut p) = (sidebar, process_view);
    navigator.sync(&mut s, &mut p, None, None);
    (s, p)
}

#[test]
fn every_route_writes_the_flags_todays_panes_read() {
    let render = Some(PathBuf::from("run/stack.tiff"));
    for (route, tab, expected) in [
        (
            Route::Library(LibraryView::All),
            StackTab::Adjust,
            Some(Sidebar::Projects),
        ),
        (Route::Subject(7), StackTab::Adjust, Some(Sidebar::Projects)),
        (
            Route::Capture(CaptureMode::Plan),
            StackTab::Adjust,
            Some(Sidebar::Capture),
        ),
        (
            Route::for_station(Station::Stack, Some(3), render.clone()),
            StackTab::Adjust,
            Some(Sidebar::Adjust),
        ),
        (
            Route::for_station(Station::Stack, Some(3), render.clone()),
            StackTab::Review,
            Some(Sidebar::Review),
        ),
        (
            Route::Develop {
                stack: Some(3),
                render: render.clone(),
            },
            StackTab::Adjust,
            Some(Sidebar::Edit),
        ),
        (
            Route::Export {
                stack: Some(3),
                render: render.clone(),
            },
            StackTab::Adjust,
            Some(Sidebar::Export),
        ),
    ] {
        let mut navigator = Navigator::default();
        navigator.go(route.clone());
        navigator.set_stack_tab(tab);
        for process_view in [true, false] {
            assert_eq!(
                navigator.legacy(process_view),
                (expected, true),
                "{route:?} opens its pane in the process view"
            );
        }
    }
    // The engine room hides the sidebar and keeps the workbench diagnostics.
    let mut navigator = Navigator::default();
    navigator.go(LaunchRoute::Engine.route(None, None));
    assert_eq!(navigator.legacy(true), (None, true));
    assert_eq!(navigator.legacy(false), (None, false));
}

#[test]
fn drawers_open_over_the_station_and_leave_its_flags() {
    let mut navigator = Navigator::default();
    navigator.go(Route::Develop {
        stack: None,
        render: None,
    });
    navigator.toggle_drawer(Drawer::Agent);
    // Develop keeps editing under the drawer.
    assert_eq!(navigator.legacy(true).0, Some(Sidebar::Edit));
    assert_eq!(navigator.drawer, Some(Drawer::Agent));
    assert_eq!(navigator.station(), Station::Develop);
    navigator.toggle_drawer(Drawer::Agent);
    assert_eq!(navigator.legacy(true).0, Some(Sidebar::Edit));
    navigator.toggle_drawer(Drawer::Activity);
    navigator.go(Route::Library(LibraryView::All));
    assert_eq!(
        navigator.drawer, None,
        "choosing a station closes the drawer"
    );
}

#[test]
fn flags_written_by_older_code_are_adopted_then_rewritten() {
    let mut navigator = Navigator::default();
    assert_eq!(
        synced(&mut navigator, Some(Sidebar::Projects), true),
        (Some(Sidebar::Projects), true)
    );
    // An agent's OpenCapture.
    assert_eq!(
        synced(&mut navigator, Some(Sidebar::Capture), true),
        (Some(Sidebar::Capture), true)
    );
    assert_eq!(navigator.station(), Station::Capture);
    // Opening a photograph in Edit.
    synced(&mut navigator, Some(Sidebar::Edit), true);
    assert_eq!(navigator.station(), Station::Develop);
    // The agent pane opens over Develop, which keeps its flags.
    assert_eq!(
        synced(&mut navigator, Some(Sidebar::Agent), true),
        (Some(Sidebar::Edit), true)
    );
    assert_eq!(
        (navigator.station(), navigator.drawer),
        (Station::Develop, Some(Drawer::Agent))
    );
    // Review becomes the Stack station's Review tab.
    synced(&mut navigator, Some(Sidebar::Review), true);
    assert_eq!(
        (navigator.station(), navigator.stack_tab, navigator.drawer),
        (Station::Stack, StackTab::Review, None)
    );
    // A hidden sidebar or a dropped image is the engine room.
    assert_eq!(synced(&mut navigator, None, true), (None, true));
    assert_eq!(navigator.route().room(), Some(Room::Engine));
    synced(&mut navigator, Some(Sidebar::Adjust), true);
    assert_eq!(navigator.route().room(), Some(Room::Photograph));
    assert_eq!(
        synced(&mut navigator, Some(Sidebar::Projects), false),
        (None, false)
    );
    assert_eq!(navigator.route().key(), "engine");
}

#[test]
fn projects_written_with_a_document_open_means_its_stack_station() {
    let mut navigator = Navigator::default();
    synced(&mut navigator, Some(Sidebar::Projects), true);
    assert_eq!(
        navigator.station(),
        Station::Library,
        "nothing open: the Library"
    );
    // A finished capture is imported: older code resets to Projects.
    navigator.document_open = true;
    synced(&mut navigator, Some(Sidebar::Edit), true);
    synced(&mut navigator, Some(Sidebar::Projects), true);
    assert_eq!(navigator.station(), Station::Stack);
    // The owner can still choose the Library with a document open.
    navigator.go(Route::Library(LibraryView::All));
    let written = synced(&mut navigator, Some(Sidebar::Adjust), true);
    assert_eq!(written, (Some(Sidebar::Projects), true));
    synced(&mut navigator, written.0, written.1);
    assert_eq!(navigator.station(), Station::Library);
    // Work done from the project tree drawer leaves it open.
    navigator.go(Route::for_station(Station::Stack, None, None));
    let written = synced(&mut navigator, Some(Sidebar::Projects), true);
    navigator.toggle_drawer(Drawer::Projects);
    let written = synced(&mut navigator, written.0, written.1);
    assert_eq!(written, (Some(Sidebar::Adjust), true));
    synced(&mut navigator, Some(Sidebar::Projects), false);
    assert_eq!(navigator.drawer, Some(Drawer::Projects));
    assert_eq!(navigator.station(), Station::Stack);
}

#[test]
fn an_explicit_navigation_wins_over_flags_changed_earlier_in_the_frame() {
    let mut navigator = Navigator::default();
    navigator.go(Route::Develop {
        stack: None,
        render: None,
    });
    let (mut sidebar, mut process_view) = (None, true);
    navigator.sync(&mut sidebar, &mut process_view, None, None);
    // Opening a stack resets the old flags to Projects, then the shell
    // navigates to the Stack station as the owner asked.
    sidebar = Some(Sidebar::Projects);
    navigator.sync(&mut sidebar, &mut process_view, Some(4), None);
    navigator.go(Route::for_station(Station::Stack, Some(4), None));
    navigator.sync(&mut sidebar, &mut process_view, Some(4), None);
    assert_eq!(navigator.station(), Station::Stack);
    assert_eq!(sidebar, Some(Sidebar::Adjust));
    // The next frame, with no further writes, keeps it.
    navigator.sync(&mut sidebar, &mut process_view, Some(4), None);
    assert_eq!(navigator.station(), Station::Stack);
}

#[test]
fn the_route_follows_the_open_document_and_counts_real_changes() {
    let mut navigator = Navigator::default();
    // The first sync adopts whatever the flags say; then navigate.
    let (mut sidebar, mut process_view) = (Some(Sidebar::Projects), true);
    navigator.sync(&mut sidebar, &mut process_view, None, None);
    navigator.go(Route::for_station(Station::Stack, None, None));
    navigator.sync(&mut sidebar, &mut process_view, None, None);
    let revision = navigator.revision();
    let path = PathBuf::from("run/stack.tiff");
    navigator.sync(&mut sidebar, &mut process_view, Some(9), Some(&path));
    assert_eq!(
        navigator.route(),
        &Route::Stack {
            stack: Some(9),
            render: Some(path.clone()),
            room: Room::Photograph
        }
    );
    for _ in 0..3 {
        navigator.sync(&mut sidebar, &mut process_view, Some(9), Some(&path));
    }
    assert_eq!(
        navigator.revision(),
        revision,
        "syncing alone is not a change"
    );
    navigator.set_room(Room::Engine);
    assert_eq!(navigator.revision(), revision + 1);
    navigator.set_room(Room::Engine);
    assert_eq!(navigator.revision(), revision + 1);
}

#[test]
fn launch_route_names_parse_and_open_their_stations() {
    for (name, key, station) in [
        ("library", "library", Station::Library),
        ("Subject", "library", Station::Library),
        ("capture", "capture", Station::Capture),
        ("stack", "stack", Station::Stack),
        ("ENGINE", "engine", Station::Stack),
        ("develop", "develop", Station::Develop),
        ("export", "export", Station::Export),
    ] {
        let route = LaunchRoute::parse(name).unwrap().route(None, None);
        assert_eq!((route.key(), route.station()), (key, station), "{name}");
    }
    assert_eq!(LaunchRoute::Subject.route(Some(5), None).key(), "subject");
    assert_eq!(LaunchRoute::parse("projects"), None);
    for station in Station::ALL {
        assert_eq!(Station::from_number(station.number()), Some(station));
    }
    assert!(!Station::Library.has_state() && Station::Export.has_state());
}
