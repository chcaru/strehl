use super::*;

fn mutation(command: AgentCommand) -> AgentRequest {
    AgentRequest {
        expected_revision: Some(7),
        command,
    }
}

#[test]
fn mutations_need_a_fresh_revision_and_unknown_operations_fail_closed() {
    let request = mutation(AgentCommand::StartStack {});
    assert!(request.check_revision(7).is_ok());
    assert!(request.check_revision(8).is_err());
    assert!(
        AgentRequest {
            expected_revision: None,
            command: AgentCommand::StartStack {}
        }
        .validate()
        .is_err()
    );
    for value in [
        json!({"expected_revision":7,"command":{"operation":"shell","command":"whoami"}}),
        json!({"expected_revision":7,"command":{"operation":"start_stack","shell":"whoami"}}),
        json!({"expected_revision":7,"command":{"operation":"start_stack"},"unexpected":true}),
    ] {
        assert!(serde_json::from_value::<AgentRequest>(value).is_err());
    }
    assert!(
        AgentRequest {
            expected_revision: None,
            command: AgentCommand::Snapshot {}
        }
        .check_revision(99)
        .is_ok()
    );
}

#[test]
fn real_settings_reject_unsafe_values_and_permit_explicit_default_reset() {
    let valid = json!({"pyramid_gate":2.0,"exposure_ev":null,"workers":4,"binned":false,"resampler":"clamped-catmull"});
    assert!(validate_settings(&serde_json::from_value(valid).unwrap()).is_ok());
    for invalid in [
        json!({"workers":0}),
        json!({"workers":99999}),
        json!({"workers":2.5}),
        json!({"pyramid_bands":0}),
        json!({"pyramid_bands":13}),
        json!({"pyramid_bands":2.5}),
        json!({"confidence_map":1}),
        json!({"resampler":"shell"}),
        json!({"secret":2}),
        json!({"pyramid_gate":-0.5}),
        json!({"binned":null}),
        json!({"exposure_ev":20}),
        json!({}),
    ] {
        assert!(
            validate_settings(&serde_json::from_value(invalid.clone()).unwrap()).is_err(),
            "{invalid}"
        );
    }
}

#[test]
fn region_requests_are_bounded_and_geometry_is_shared_with_development() {
    let region = Region::Ellipse {
        center: [0.4, 0.5],
        radius: [0.1, 0.2],
    };
    let command = AgentCommand::Probe {
        region: region.clone(),
        max_sources: 12,
    };
    assert!(command.validate().is_ok());
    assert!(region.contains([0.4, 0.5]));
    assert!(!region.contains([0.1, 0.2]));
    assert_eq!(serde_json::to_value(&region).unwrap()["kind"], "ellipse");
    assert!(
        AgentCommand::Probe {
            region: region.clone(),
            max_sources: 33
        }
        .validate()
        .is_err()
    );
    assert!(
        AgentCommand::Preview {
            target: PreviewTarget::Final,
            region: Some(region),
            max_side: 4096
        }
        .validate()
        .is_err()
    );
    assert!(
        AgentCommand::Probe {
            region: Region::Rectangle {
                min: [0.7, 0.2],
                max: [0.2, 0.8]
            },
            max_sources: 1
        }
        .validate()
        .is_err()
    );
    assert!(
        AgentCommand::Probe {
            region: Region::Ellipse {
                center: [f32::NAN, 0.5],
                radius: [0.1, 0.2]
            },
            max_sources: 1
        }
        .validate()
        .is_err()
    );
}

#[test]
fn develop_requests_validate_the_engine_recipe_including_region_adjustments() {
    let mut recipe = strehl_edit::DevelopmentRecipe::default();
    recipe.global.exposure = 2.0;
    assert!(
        mutation(AgentCommand::SetDevelop {
            recipe: recipe.clone()
        })
        .validate()
        .is_ok()
    );
    recipe.global.exposure = 20.0;
    assert!(
        mutation(AgentCommand::SetDevelop { recipe })
            .validate()
            .is_err()
    );
    assert!(
        serde_json::from_value::<AgentCommand>(json!({
            "operation":"set_develop","recipe":{"global":{"adobe_private_profile":"something"}}
        }))
        .is_err()
    );
}

#[test]
fn adaptive_intent_defaults_to_balance_and_rejects_unknown_treatments() {
    let original: AgentCommand = serde_json::from_value(json!({
        "operation":"adaptive_develop", "strength":0.5
    }))
    .unwrap();
    assert!(
        matches!(original, AgentCommand::AdaptiveDevelop { intent: AdaptiveDevelopIntent::Balance, strength } if strength == 0.5)
    );
    original.validate().unwrap();
    let highlights: AgentCommand = serde_json::from_value(json!({
        "operation":"adaptive_develop", "strength":1.0,"intent":"highlights"
    }))
    .unwrap();
    assert!(matches!(
        highlights,
        AgentCommand::AdaptiveDevelop {
            intent: AdaptiveDevelopIntent::Highlights,
            ..
        }
    ));
    highlights.validate().unwrap();
    for intent in [
        json!("generate_detail"),
        json!("restore_highlights"),
        json!(1),
        Value::Null,
    ] {
        assert!(
            serde_json::from_value::<AgentCommand>(json!({
                "operation":"adaptive_develop","strength":1.0,"intent":intent
            }))
            .is_err()
        );
    }
}

#[test]
fn export_and_import_never_accept_arbitrary_paths_or_device_names() {
    assert!(safe_file_name("insect-detail.avif").is_ok());
    for name in [
        "../private.png",
        "..\\private.png",
        "/tmp/private",
        "C:\\private",
        "image:secret",
        "CON.tif",
        "NUL .tif",
        "CONOUT$",
        "COM¹.tif",
        "LPT1",
        "photo.",
        "photo ",
        "a/b",
    ] {
        assert!(safe_file_name(name).is_err(), "{name}");
    }
    assert!(safe_relative_path("new-bracket/frames").is_ok());
    for path in [
        "..",
        "../",
        "x/../y",
        "x\\..\\y",
        "//server/share",
        "\\\\server\\share",
        "C:relative",
        "/absolute",
        "a\0b",
    ] {
        assert!(safe_relative_path(path).is_err(), "{path}");
    }
}

#[test]
fn bounded_png_helper_and_base64_have_independent_known_vectors() {
    for (input, expected) in [
        (b"".as_slice(), ""),
        (b"f", "Zg=="),
        (b"fo", "Zm8="),
        (b"foo", "Zm9v"),
        (b"foobar", "Zm9vYmFy"),
    ] {
        assert_eq!(base64(input), expected);
    }
    let image = image::RgbaImage::from_pixel(12, 8, image::Rgba([20, 30, 40, 255]));
    let mut output = std::io::Cursor::new(Vec::new());
    image::DynamicImage::ImageRgba8(image)
        .write_to(&mut output, image::ImageFormat::Png)
        .unwrap();
    let valid = AgentImage::png(output.get_ref()).unwrap();
    assert_eq!(valid.mime_type, "image/png");
    assert!(!valid.data.is_empty());
    let mut too_wide = output.into_inner();
    too_wide[16..20].copy_from_slice(&1025_u32.to_be_bytes());
    assert!(AgentImage::png(&too_wide).is_err());
    assert!(AgentImage::png(b"not an image").is_err());
}

#[test]
fn edit_version_commands_require_valid_names_ids_and_current_revision() {
    for command in [
        AgentCommand::SaveEditVersion {
            name: "Reflection repair".into(),
        },
        AgentCommand::RestoreEditVersion {
            id: "0123456789abcdef0123456789abcdef".into(),
        },
    ] {
        command.validate().unwrap();
        assert!(!command.is_read_only());
        let request = AgentRequest {
            expected_revision: Some(41),
            command,
        };
        assert!(request.check_revision(42).is_err());
        request.check_revision(41).unwrap();
    }
    for name in ["", " ", "bad\nname", &"x".repeat(121)] {
        assert!(
            AgentCommand::SaveEditVersion { name: name.into() }
                .validate()
                .is_err()
        );
    }
    for id in ["../file", "0123456789ABCDEF0123456789ABCDEF", "0123"] {
        assert!(
            AgentCommand::RestoreEditVersion { id: id.into() }
                .validate()
                .is_err()
        );
    }
}

#[test]
fn metadata_is_read_only_but_shutdown_requires_a_current_revision() {
    let read = AgentRequest {
        expected_revision: None,
        command: AgentCommand::Metadata { frame: 109 },
    };
    assert!(read.command.is_read_only());
    assert!(read.validate().is_ok());
    assert!(read.check_revision(12).is_ok());
    for invalid in [
        json!({"operation":"metadata","frame":-1}),
        json!({"operation":"metadata","frame":1.5}),
        json!({"operation":"metadata","frame":0,"path":"private.ARW"}),
        json!({"operation":"metadata","frame":0,"output":"capture"}),
        json!({"operation":"shutdown","force":true}),
    ] {
        assert!(serde_json::from_value::<AgentCommand>(invalid).is_err());
    }
    let mut stop = mutation(AgentCommand::Shutdown {});
    assert!(!stop.command.is_read_only());
    assert!(stop.check_revision(7).is_ok());
    assert!(stop.check_revision(8).is_err());
    stop.expected_revision = None;
    assert!(stop.validate().is_err());
}
