//! Where the next stack goes: a new subject unless one is chosen on purpose,
//! and Start's blocker until the subject is ready.
use super::*;

fn choices() -> Vec<SubjectChoice> {
    vec![
        SubjectChoice {
            id: 7,
            name: "Blue weevil".into(),
            detail: "Bugs · 2 stacks".into(),
        },
        SubjectChoice {
            id: 9,
            name: "bug-3".into(),
            detail: "Imported stacks · 2 stacks".into(),
        },
    ]
}

#[test]
fn a_capture_starts_a_new_subject_unless_one_is_chosen_on_purpose() {
    let subjects = choices();
    assert_eq!(destination("", None, &subjects), Destination::Unnamed);
    assert_eq!(destination("   ", None, &subjects), Destination::Unnamed);
    assert_eq!(
        destination(" Harvestman ", None, &subjects),
        Destination::New("Harvestman".into())
    );
    // Typing an existing subject's name is not choosing it.
    assert_eq!(
        destination("BLUE WEEVIL", None, &subjects),
        Destination::Taken("Blue weevil".into())
    );
    assert_eq!(
        destination("Blue weevil", Some(7), &subjects),
        Destination::Existing(subjects[0].clone())
    );
    assert_eq!(
        destination("Moth", Some(42), &subjects),
        Destination::Gone("Moth".into()),
        "a chosen subject that left the library"
    );
    assert!(matches!(
        destination(&"x".repeat(161), None, &subjects),
        Destination::Invalid(_)
    ));
    assert!(matches!(
        destination("Moth\u{7}", None, &subjects),
        Destination::Invalid(_)
    ));
}

#[test]
fn start_waits_until_the_subject_is_named_or_chosen_and_says_where_it_goes() {
    let subjects = choices();
    for (typed, chosen) in [("", None), ("bug-3", None), ("Moth", Some(42))] {
        let found = blocker(&destination(typed, chosen, &subjects)).expect(typed);
        assert_eq!(found.check, Check::Subject);
        assert_eq!(found.fix, Some(Fix::NameSubject));
        assert!(!found.sentence.is_empty());
    }
    assert!(blocker(&destination("Moth", None, &subjects)).is_none());
    assert!(blocker(&destination("bug-3", Some(9), &subjects)).is_none());
    assert_eq!(
        sentence(&destination("Moth", None, &subjects), "Bugs"),
        "Goes to a new subject, \u{201c}Moth\u{201d}, in Bugs"
    );
    assert_eq!(
        sentence(&destination("Blue weevil", Some(7), &subjects), "Bugs"),
        "Adds a stack to \u{201c}Blue weevil\u{201d} · Bugs · 2 stacks"
    );
    assert!(
        sentence(&destination("blue weevil", None, &subjects), "Bugs")
            .contains("choose it from the list")
    );
}

/// What the subject check costs each Start check, with a large library.
/// Release: `cargo test --release -p strehl-ui -- --ignored benchmark_destination --nocapture`.
#[test]
#[ignore = "explicit timing of the subject check"]
fn benchmark_destination_with_two_thousand_subjects() {
    let subjects: Vec<SubjectChoice> = (0..2000)
        .map(|i| SubjectChoice {
            id: i,
            name: format!("Subject {i:04}"),
            detail: "Bugs · 1 stack".into(),
        })
        .collect();
    let started = std::time::Instant::now();
    let mut ready = 0;
    for _ in 0..1000 {
        ready +=
            usize::from(std::hint::black_box(destination("Harvestman", None, &subjects)).ready());
    }
    let each = started.elapsed().as_secs_f64() * 1e6 / 1000.0;
    assert_eq!(ready, 1000);
    eprintln!("subject check, 2,000 subjects, a new name (every subject compared): {each:.1} µs");
}
