//! Agent catalog commands for format 2: subjects. In-memory catalog only.
use super::*;
use crate::agent_interface::AgentRequest;
use crate::workspace_history::{NodeKind, Optics, Run, StackDraft};

fn app() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default(); // In-memory catalog; never save the real one.
    app
}
fn command(value: serde_json::Value) -> AgentCommand {
    serde_json::from_value(value).unwrap()
}
fn saved_run(directory: &str, status: &str) -> Run {
    serde_json::from_value(json!({
        "directory": directory, "source": "/captures/weevil/100MSDCF",
        "output": format!("{directory}/photograph.tiff"), "log": format!("{directory}/render.log"),
        "label": "render", "created": 10, "status": status, "frames": 2,
        "settings": crate::jobs::RenderSettings::default(),
        "exposure": null, "gate": null, "workers": 4
    }))
    .unwrap()
}

#[test]
fn subject_commands_parse_strictly_and_keep_absent_distinct_from_null_across_the_bridge() {
    for value in [
        json!({"operation":"create_subject","name":"Weevil"}),
        json!({"operation":"create_subject","name":"Weevil","parent_id":1,"kind":"x"}),
        json!({"operation":"move_node","id":2}),
        json!({"operation":"set_subject_meta","id":2,"colour":"red"}),
        json!({"operation":"set_subject_meta","id":2,"optics":{"camera":"A","mount":"E"}}),
        json!({"operation":"set_subject_meta","id":2,"hero_run":{"stack_id":3}}),
    ] {
        assert!(
            serde_json::from_value::<AgentCommand>(value.clone()).is_err(),
            "{value}"
        );
    }
    let absent = command(json!({"operation":"set_subject_meta","id":2}));
    let cleared = command(
        json!({"operation":"set_subject_meta","id":2,"optics":null,"scale":null,"hero_run":null}),
    );
    let set = command(json!({"operation":"set_subject_meta","id":2,
        "optics":{"camera":"ILCE-7CR"},
        "scale":{"um_per_px":1.88,"source":{"kind":"entered","magnification":2.0,"pitch_um":3.76}},
        "hero_run":{"stack_id":3,"run_index":0}}));
    // The MCP process forwards commands serialized; the meaning must survive.
    for original in [absent, cleared, set] {
        let forwarded: AgentCommand =
            serde_json::from_value(serde_json::to_value(&original).unwrap()).unwrap();
        assert_eq!(format!("{forwarded:?}"), format!("{original:?}"));
    }
    match command(json!({"operation":"set_subject_meta","id":2,"optics":null})) {
        AgentCommand::SetSubjectMeta {
            optics,
            scale,
            hero_run,
            notes,
            ..
        } => {
            assert_eq!(optics, Some(None), "null clears");
            assert!(
                scale.is_none() && hero_run.is_none() && notes.is_none(),
                "absent keeps"
            );
        }
        _ => unreachable!(),
    }
    let contradictory = command(json!({"operation":"set_subject_meta","id":2,
        "scale":{"um_per_px":3.0,"source":{"kind":"entered","magnification":2.0,"pitch_um":3.76}}}));
    assert!(contradictory.validate().is_err());
    assert!(
        AgentRequest {
            expected_revision: None,
            command: command(json!({"operation":"move_node","id":2,"parent_id":1})),
        }
        .validate()
        .is_err(),
        "catalog edits need a fresh revision"
    );
}

#[test]
fn agent_creates_moves_and_describes_subjects_through_the_undo_journal() {
    let mut app = app();
    // Stacks and renders arrive outside the journal (and reset it), so the
    // fixture's evidence exists before the first agent edit.
    let project = app.catalog.create_project("Bugs").unwrap();
    let other = app
        .catalog
        .create_subject(project, "Orange weevil")
        .unwrap();
    let run = saved_run("/out/strehl-1-1-1", "Saved");
    let stack = app
        .catalog
        .create_stack(other, "Dorsal", StackDraft::from_run(&run))
        .unwrap();
    app.catalog.add_revision(stack, run).unwrap();
    let failed = saved_run("/out/strehl-2-1-2", "Failed");
    app.catalog.add_revision(stack, failed).unwrap();
    let subject = app
        .apply_agent_command(command(
            json!({"operation":"create_subject","name":"Blue weevil","parent_id":project}),
        ))
        .unwrap()["id"]
        .as_u64()
        .unwrap();

    assert!(
        app.apply_agent_command(command(
            json!({"operation":"move_node","id":subject,"parent_id":other})
        ))
        .is_err(),
        "a subject holds stacks only"
    );
    assert!(
        app.apply_agent_command(command(json!({"operation":"set_subject_meta","id":subject,
            "hero_run":{"stack_id":stack,"run_index":0}})))
            .is_err(),
        "the picture comes from this subject's own stacks"
    );
    app.apply_agent_command(command(
        json!({"operation":"move_node","id":stack,"parent_id":subject}),
    ))
    .unwrap();
    assert_eq!(app.catalog.subject_of(stack), Some(subject));
    assert!(
        app.apply_agent_command(command(json!({"operation":"set_subject_meta","id":subject,
            "hero_run":{"stack_id":stack,"run_index":1}})))
            .is_err(),
        "a failed render is not a picture"
    );
    app.apply_agent_command(command(json!({"operation":"set_subject_meta","id":subject,
        "notes":"Found on the oak.",
        "optics":{"camera":"ILCE-7CR","lens":"90mm macro"},
        "scale":{"um_per_px":0.94,"source":{"kind":"measured","slide":"0.01 mm"}},
        "hero_run":{"stack_id":stack,"run_index":0}})))
        .unwrap();
    let node = app.catalog.node(subject).unwrap();
    assert_eq!(node.notes, "Found on the oak.");
    let meta = node.subject.clone().unwrap();
    assert_eq!(
        meta.hero.as_deref(),
        Some(Path::new("/out/strehl-1-1-1/photograph.tiff"))
    );
    assert_eq!(
        meta.optics.as_ref().map(|o| o.lens.as_str()),
        Some("90mm macro")
    );

    let snapshot = app.agent_snapshot();
    let projects = snapshot["projects"].as_array().unwrap();
    let described = projects.iter().find(|p| p["id"] == subject).unwrap();
    assert_eq!(
        described["kind"], "Subject",
        "projects[].kind stays, with a new value"
    );
    assert_eq!(described["parent"], project);
    assert_eq!(described["subject"]["optics"]["camera"], "ILCE-7CR");
    assert_eq!(described["subject"]["scale"]["source"]["kind"], "measured");
    let stack_entry = projects.iter().find(|p| p["id"] == stack).unwrap();
    assert_eq!(stack_entry["kind"], "Stack");
    assert!(stack_entry["subject"].is_null());

    app.apply_agent_command(command(
        json!({"operation":"set_subject_meta","id":subject,"optics":null}),
    ))
    .unwrap();
    assert!(
        app.catalog
            .node(subject)
            .unwrap()
            .subject
            .as_ref()
            .unwrap()
            .optics
            .is_none()
    );
    assert!(app.project_explorer.undo(&mut app.catalog));
    assert_eq!(
        app.catalog
            .node(subject)
            .unwrap()
            .subject
            .as_ref()
            .unwrap()
            .optics,
        Some(Optics {
            camera: "ILCE-7CR".into(),
            lens: "90mm macro".into()
        }),
        "agent edits share the human's undo"
    );
    let mut undone = 1;
    while app.project_explorer.undo(&mut app.catalog) {
        undone += 1;
    }
    assert_eq!(
        undone, 4,
        "clear, describe, move and create were all undone"
    );
    assert_eq!(
        app.catalog.subject_of(stack),
        Some(other),
        "the move was undone"
    );
    assert!(
        app.catalog
            .nodes
            .iter()
            .any(|n| n.id == subject && n.kind == NodeKind::Subject),
        "undoing its creation never deletes a subject"
    );
    assert!(
        app.catalog
            .node(app.catalog.node(stack).unwrap().parent.unwrap())
            .is_some()
    );
}
