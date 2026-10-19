//! Independent replay identity checks. Equal frame counts alone are deliberately
//! insufficient: order, path and byte length have distinct negative controls.
use super::*;
use crate::jobs::{FrameFile, StackScan};

fn run() -> Run {
    serde_json::from_value(serde_json::json!({
        "directory": "review-run", "source": "review-source", "output": "review-run/stack.tiff",
        "log": "review-run/activity.log", "label": "Identity witness", "created": 10,
        "status": "Saved", "frames": 3, "settings": RenderSettings::default(),
        "exposure": null, "gate": null, "workers": 2, "pinned": false,
        "sources": [
            {"path": "review-source/first.arw", "bytes": 101},
            {"path": "review-source/second.arw", "bytes": 202},
            {"path": "review-source/last.arw", "bytes": 303}
        ]
    }))
    .unwrap()
}

fn scan() -> StackScan {
    StackScan {
        directory: PathBuf::from("review-source"),
        frames: [("first", 101), ("second", 202), ("last", 303)]
            .map(|(name, bytes)| FrameFile {
                path: PathBuf::from(format!("review-source/{name}.arw")),
                bytes,
            })
            .to_vec(),
        total_bytes: 606,
    }
}

#[test]
fn retained_capture_identity_accepts_only_the_same_ordered_source_manifest() {
    let run = run();
    let original = scan();
    assert!(
        run.matches_scan(&original),
        "fixture must exercise a valid identity match"
    );
    let mut reordered = scan();
    reordered.frames.swap(0, 1);
    assert!(
        !run.matches_scan(&reordered),
        "same files in a changed order must not relabel masks"
    );
    let mut changed_length = scan();
    changed_length.frames[1].bytes += 1;
    assert!(
        !run.matches_scan(&changed_length),
        "changed source bytes are not the archived capture"
    );
    let mut renamed = scan();
    renamed.frames[1].path = PathBuf::from("review-source/replacement.arw");
    assert!(
        !run.matches_scan(&renamed),
        "same count and size cannot prove a replaced capture"
    );
    let mut missing = scan();
    missing.frames.pop();
    assert!(
        !run.matches_scan(&missing),
        "missing capture must preserve diagnostics without a false thumbnail identity"
    );
}

#[test]
fn legacy_or_damaged_manifest_does_not_claim_source_identity_from_count_alone() {
    let mut json = serde_json::to_value(run()).unwrap();
    json.as_object_mut().unwrap().remove("sources");
    let legacy: Run = serde_json::from_value(json.clone()).unwrap();
    assert!(
        !legacy.matches_scan(&scan()),
        "legacy history has no ordered identity witness"
    );
    json["sources"] = serde_json::json!([
        {"path":"review-source/first.arw", "bytes":101},
        {"path":"review-source/second.arw", "bytes":202}
    ]);
    let short: Run = serde_json::from_value(json).unwrap();
    assert!(
        !short.matches_scan(&scan()),
        "partial manifest must not certify the full bracket"
    );
    let mut wrong_count = serde_json::to_value(run()).unwrap();
    wrong_count["frames"] = serde_json::json!(4);
    let inconsistent: Run = serde_json::from_value(wrong_count).unwrap();
    assert!(
        !inconsistent.matches_scan(&scan()),
        "catalog count and manifest disagree"
    );
}
