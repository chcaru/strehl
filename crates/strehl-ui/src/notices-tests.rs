use super::*;
use std::time::Duration;

#[test]
fn the_list_is_bounded_and_newest_first() {
    let mut notices = Notices::default();
    for index in 0..CAPACITY + 10 {
        notices.push(Severity::Info, Source::App, format!("notice {index}"), None);
    }
    assert_eq!(notices.len(), CAPACITY);
    assert_eq!(
        notices.iter().next().unwrap().text,
        format!("notice {}", CAPACITY + 9)
    );
    assert_eq!(notices.iter().last().unwrap().text, "notice 10");
}

#[test]
fn a_repeated_notice_refreshes_instead_of_stacking() {
    let mut notices = Notices::default();
    let first = notices.push(Severity::Failure, Source::Stack, "Engine missing", None);
    notices.mark_all_read();
    let again = notices.push(Severity::Failure, Source::Stack, "Engine missing", None);
    assert_eq!(first, again);
    assert_eq!(notices.len(), 1);
    assert_eq!(notices.unread(), 1, "a repeat is news again");
}

#[test]
fn legacy_errors_become_failures_and_clearing_them_resolves_the_notice() {
    let mut notices = Notices::default();
    let start = notices.revision();
    notices.observe(Source::Stack, None);
    assert_eq!(notices.revision(), start, "nothing to observe");
    notices.observe(Source::Stack, Some("The engine stopped"));
    notices.observe(Source::Stack, Some("The engine stopped"));
    assert_eq!(notices.len(), 1, "an unchanged error is one notice");
    let failure = notices.newest_unread_failure().unwrap();
    assert_eq!(failure.text, "The engine stopped");
    assert_eq!(failure.action, Some(Action::OpenLog));
    // Another source's error is tracked separately.
    notices.observe(Source::Capture, Some("Pi offline"));
    assert_eq!(
        notices.newest_unread_failure().unwrap().source,
        Source::Capture
    );
    notices.observe(Source::Capture, None);
    assert_eq!(
        notices.newest_unread_failure().unwrap().text,
        "The engine stopped",
        "a cleared error no longer shows in the top bar"
    );
    assert!(notices.iter().any(|n| n.text == "Pi offline" && n.resolved));
    notices.mark_all_read();
    assert!(notices.newest_unread_failure().is_none());
    assert_eq!(notices.unread(), 0);
}

#[test]
fn a_dismissed_notice_leaves_the_list_and_the_snapshot() {
    let mut notices = Notices::default();
    let id = notices.push(Severity::Done, Source::Export, "Exported weevil.avif", None);
    notices.push(Severity::Warning, Source::Capture, "USB 2.0 link", None);
    let snapshot = notices.snapshot();
    assert_eq!(snapshot.as_array().unwrap().len(), 2);
    assert_eq!(snapshot[0]["severity"], "warning");
    assert_eq!(snapshot[1]["source"], "Export");
    notices.dismiss(id);
    assert_eq!(notices.len(), 1);
    assert!(notices.iter().all(|n| n.id != id));
}

#[test]
fn ages_read_like_the_project_explorer() {
    let now = SystemTime::UNIX_EPOCH + Duration::from_secs(1_000_000);
    for (seconds, expected) in [
        (5, "just now"),
        (125, "2m ago"),
        (7300, "2h ago"),
        (200_000, "2d ago"),
    ] {
        assert_eq!(ago(now - Duration::from_secs(seconds), now), expected);
    }
}
