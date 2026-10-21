//! Independent close arbitration: overlapping wait reasons and a real worker
//! failure, with no disk/catalog writes and no user window.
use super::*;

fn isolated_app() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default();
    app.editor = Default::default();
    app
}

fn has_command(output: &egui::FullOutput, close: bool) -> bool {
    output.viewport_output[&egui::ViewportId::ROOT]
        .commands
        .iter()
        .any(|command| {
            if close {
                matches!(command, egui::ViewportCommand::Close)
            } else {
                matches!(command, egui::ViewportCommand::CancelClose)
            }
        })
}

#[test]
fn encoding_failure_after_history_wait_cancels_every_close_reason() {
    let mut app = isolated_app();
    app.close_after_photo_history = true;
    app.close_after_presets = true;
    app.close_after_export = true;
    app.editor.error = Some("deliberate encoder failure after version preparation".into());
    let ctx = egui::Context::default();
    let output = ctx.run(Default::default(), |ctx| app.handle_close(ctx));
    assert!(has_command(&output, false));
    assert!(!has_command(&output, true));
    assert!(!app.close_after_photo_history && !app.close_after_presets && !app.close_after_export);
    for _ in 0..3 {
        let output = ctx.run(Default::default(), |ctx| app.handle_close(ctx));
        assert!(
            !has_command(&output, true),
            "a leftover wait reason closed on the next frame"
        );
    }
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Export));
    assert!(
        app.editor
            .error
            .as_deref()
            .unwrap()
            .contains("deliberate encoder")
    );
}

#[test]
fn close_waits_for_history_and_surfaces_worker_failure_instead_of_silently_closing() {
    for fail in [false, true] {
        let mut app = isolated_app();
        let (release, wait) = mpsc::channel::<()>();
        app.photo_history.pending = Some(Pending {
            durable: true,
            guard: None,
            task: jobs::spawn_task("history-close-review", move |_| {
                wait.recv()?;
                anyhow::ensure!(!fail, "deliberate history write failure");
                Ok(Prepared::Opened)
            }),
        });
        app.close_after_photo_history = true;
        let ctx = egui::Context::default();
        let pending = ctx.run(Default::default(), |ctx| app.handle_close(ctx));
        assert!(has_command(&pending, false));
        assert!(!has_command(&pending, true));
        assert!(
            app.photo_history.pending.is_some(),
            "worker must actually be held"
        );
        release.send(()).unwrap();
        let deadline = std::time::Instant::now() + Duration::from_secs(2);
        let terminal = loop {
            let output = ctx.run(Default::default(), |ctx| app.handle_close(ctx));
            if app.photo_history.pending.is_none() {
                break output;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "worker never delivered"
            );
            std::thread::sleep(Duration::from_millis(5));
        };
        if fail {
            assert!(has_command(&terminal, false));
            assert!(!has_command(&terminal, true));
            assert!(app.photo_history.failed_operation);
            assert!(
                app.editor
                    .error
                    .as_deref()
                    .unwrap()
                    .contains("deliberate history write failure")
            );
            assert!(
                app.flush_photo_history(&ctx).is_err(),
                "failure cannot masquerade as durable completion"
            );
        } else {
            assert!(
                has_command(&terminal, true),
                "a successful worker must permit closing"
            );
        }
    }
    // Synchronous input feedback is not a failed persistence task.
    let mut app = isolated_app();
    app.photo_history.error = Some("Use a nonempty version name".into());
    app.close_after_photo_history = true;
    let ctx = egui::Context::default();
    let output = ctx.run(Default::default(), |ctx| app.handle_close(ctx));
    assert!(has_command(&output, true));
}
