//! Destination handling must not replace an explicit user's choice or start
//! writing in the launcher's directory when a user location is unavailable.
use super::*;

#[test]
fn destination_picker_result_is_preserved_across_polling() {
    let files = jobs::tests::TestDirectory::new("chosen-destination");
    let explicit = files.path().join("my-render-folder");
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    let (sender, receiver) = mpsc::sync_channel(1);
    app.dialog = Some(receiver);
    sender
        .send((Dialog::Output, Some(explicit.clone())))
        .unwrap();
    let ctx = egui::Context::default();
    app.poll(&ctx);
    assert_eq!(app.output, explicit);
    assert!(app.dialog.is_none());
    app.poll(&ctx);
    assert_eq!(app.output, explicit);
    assert!(!explicit.exists());
}

#[test]
fn destination_missing_blocks_start_without_creating_a_pending_run() {
    let files = jobs::tests::TestDirectory::new("missing-destination");
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.stack = Some(StackScan {
        directory: files.path().join("source"),
        frames: vec![jobs::FrameFile {
            path: files.path().join("source/photo.arw"),
            bytes: 1,
        }],
        total_bytes: 1,
    });
    app.engine = Some(files.path().join("engine.exe"));
    app.output = PathBuf::new();
    assert_eq!(
        app.stack_start_blocker(),
        Some("Choose an output folder in Adjust > Destination")
    );
    app.start_render();
    assert!(app.job.is_none());
    assert!(app.pending_run.is_none());
    assert!(app.active_stack.is_none());
    assert_eq!(std::fs::read_dir(files.path()).unwrap().count(), 0);
}
