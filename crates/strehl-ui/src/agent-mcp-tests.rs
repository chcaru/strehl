use super::*;

fn measured_recipe() -> Value {
    measured_recipe_version(1)
}

fn measured_recipe_version(version: u32) -> Value {
    let field = |scope: Value| {
        json!({"version":version,"target_region":scope,"parameters":{},"amount":0.6,
        "bounds":[[0,0],[1,1]],"width":20,"height":20,"levels":33,"log_min":-8,"log_max":2,
        "tone_ev":format!("f32hex:{}","3e4ccccd".repeat(20*20*33)),
        "color_gain":format!("f32hex:{}","3f800000".repeat(20*20*if version == 2 {33} else {1})),
        "delivery_ceiling":4,"centering_ev":0})
    };
    json!({"regions":[{"id":"r","name":"Reflection","shape":{"kind":"rectangle","min":[0.2,0.2],"max":[0.8,0.8]},"feather":0.3,"enabled":true}],
        "spatial":[field(Value::Null),field(json!("r"))]})
}

#[test]
fn signature_v2_fields_round_trip_with_all_controls_and_luminance_colors() {
    let mut recipe = measured_recipe_version(2);
    let parameters = strehl_edit::AdaptiveParameters {
        tone_range: strehl_edit::AdaptiveToneRange::Midtones,
        ..strehl_edit::AdaptiveParameters::signature()
    };
    let parameters = serde_json::to_value(parameters).unwrap();
    for field in recipe["spatial"].as_array_mut().unwrap() {
        field["parameters"] = parameters.clone();
        // Distinct coefficients catch accidental truncation to one value per
        // spatial cell or implicit reconstruction as a v1 treatment.
        field["color_gain"] = json!(format!(
            "f32hex:{}",
            "3f8000003f8ccccd3f99999a".repeat(20 * 20 * 33 / 3)
        ));
    }
    let native: strehl_edit::DevelopmentRecipe = serde_json::from_value(recipe.clone()).unwrap();
    native.validate().unwrap();
    assert_eq!(native.spatial[0].version, 2);
    assert_eq!(native.spatial[0].color_gain.len(), 20 * 20 * 33);
    assert_ne!(
        native.spatial[0].color_gain[0],
        native.spatial[0].color_gain[1]
    );

    let advertised = spatial_schema();
    let fields = &advertised["properties"];
    assert!(
        fields["version"]["enum"]
            .as_array()
            .unwrap()
            .contains(&json!(2))
    );
    let serialized = serde_json::to_value(&native.spatial[0]).unwrap();
    let color = serialized["color_gain"].as_str().unwrap();
    assert!(
        color.len() > 3207,
        "fixture must fail the retired v1 schema"
    );
    assert!(color.len() <= fields["color_gain"]["maxLength"].as_u64().unwrap() as usize);
    let controls = &fields["parameters"]["properties"];
    for (name, value) in serialized["parameters"].as_object().unwrap() {
        let schema = &controls[name];
        assert!(
            schema.is_object(),
            "native control {name} is absent from MCP"
        );
        if let Some(allowed) = schema["enum"].as_array() {
            assert!(allowed.contains(value));
        } else {
            let number = value.as_f64().unwrap();
            assert!(number >= schema["minimum"].as_f64().unwrap());
            assert!(number <= schema["maximum"].as_f64().unwrap());
        }
    }

    let lines = [
        initialize(),
        json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
        json!({"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"strehl_command",
            "arguments":{"expected_revision":12,"command":{"operation":"set_develop","recipe":recipe}}}}),
    ];
    let wire = lines
        .iter()
        .map(Value::to_string)
        .collect::<Vec<_>>()
        .join("\n")
        + "\n";
    assert!(wire.len() < MAX_REQUEST_BYTES);
    let mut calls = 0;
    let mut output = Vec::new();
    serve(std::io::Cursor::new(wire), &mut output, |request| {
        request.check_revision(12).unwrap();
        let AgentCommand::SetDevelop { recipe: received } = request.command else {
            panic!("wrong operation")
        };
        assert_eq!(received, native);
        calls += 1;
        AgentReply::success(json!({"applied":true}))
    })
    .unwrap();
    assert_eq!(calls, 1);
    let reply: Value = serde_json::from_str(
        std::str::from_utf8(&output)
            .unwrap()
            .lines()
            .last()
            .unwrap(),
    )
    .unwrap();
    assert_eq!(reply["result"]["structuredContent"]["applied"], true);
}

#[test]
fn v2_layout_unknown_versions_and_invalid_adaptive_controls_never_dispatch() {
    let valid = measured_recipe_version(2);
    let native: strehl_edit::DevelopmentRecipe = serde_json::from_value(valid.clone()).unwrap();
    native.validate().unwrap();
    let mut invalid = Vec::new();
    for (key, value) in [
        ("version", json!(3)),
        ("version", json!(1)), // v2 colors under a v1 declaration
        (
            "color_gain",
            json!(format!("f32hex:{}", "3f800000".repeat(20 * 20))),
        ),
        (
            "color_gain",
            json!(format!("f32hex:{}", "7fc00000".repeat(20 * 20 * 33))),
        ),
    ] {
        let mut recipe = valid.clone();
        recipe["spatial"][0][key] = value;
        invalid.push(recipe);
    }
    for (key, value) in [
        ("tone_range", json!("skin")),
        ("shadow_protection", json!(-0.01)),
        ("highlight_compression", json!(1.01)),
        ("presence", json!(1.01)),
        ("invented_control", json!(0.5)),
    ] {
        let mut recipe = valid.clone();
        recipe["spatial"][0]["parameters"][key] = value;
        invalid.push(recipe);
    }
    let mut protocol = Protocol::default();
    ready(&mut protocol);
    for recipe in invalid {
        let call = json!({"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"strehl_command",
            "arguments":{"expected_revision":12,"command":{"operation":"set_develop","recipe":recipe}}}});
        let reply = protocol
            .handle(&serde_json::to_vec(&call).unwrap(), &mut |_| {
                panic!("invalid v2 treatment dispatched")
            })
            .unwrap();
        assert_eq!(reply["result"]["isError"], true);
    }
}

#[test]
fn bounded_measured_recipe_round_trips_over_actual_ndjson_transport() {
    let recipe = measured_recipe();
    let lines = [
        initialize(),
        json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
        json!({"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"strehl_command",
            "arguments":{"expected_revision":12,"command":{"operation":"set_develop","recipe":recipe}}}}),
    ];
    let wire = lines
        .iter()
        .map(Value::to_string)
        .collect::<Vec<_>>()
        .join("\n")
        + "\n";
    assert!(wire.len() > 128 * 1024, "must reject the old transport cap");
    assert!(wire.len() < MAX_REQUEST_BYTES);
    let mut output = Vec::new();
    let mut called = false;
    serve(std::io::Cursor::new(wire), &mut output, |request| {
        request.check_revision(12).unwrap();
        let AgentCommand::SetDevelop { recipe: received } = request.command else {
            panic!("wrong operation")
        };
        received.validate().unwrap();
        assert_eq!(
            serde_json::to_value(received).unwrap()["spatial"][0]["tone_ev"],
            recipe["spatial"][0]["tone_ev"]
        );
        called = true;
        AgentReply::success(json!({"applied":true}))
    })
    .unwrap();
    assert!(called);
    let reply: Value = serde_json::from_str(
        std::str::from_utf8(&output)
            .unwrap()
            .lines()
            .last()
            .unwrap(),
    )
    .unwrap();
    assert_eq!(reply["result"]["structuredContent"]["applied"], true);
}

#[test]
fn malformed_spatial_coefficients_and_portable_operations_never_dispatch() {
    let mut protocol = Protocol::default();
    ready(&mut protocol);
    let mut invalid = Vec::new();
    for (key, value) in [
        ("tone_ev", json!("f32hex:7fc00000")),
        ("tone_ev", json!("f32hex:00000000")),
        ("width", json!(21)),
        ("color_gain", json!("arbitrary-buffer")),
    ] {
        let mut recipe = measured_recipe();
        recipe["spatial"][0][key] = value;
        invalid.push(json!({"operation":"set_develop","recipe":recipe}));
    }
    invalid.extend([
        json!({"operation":"set_adjustments","adjustments":{"exposure":9}}),
        json!({"operation":"set_adjustments","adjustments":{"spatial":[]}}),
        json!({"operation":"clear_adaptive","region_id":""}),
    ]);
    for command in invalid {
        let call = json!({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"strehl_command",
            "arguments":{"expected_revision":12,"command":command}}});
        let result = protocol
            .handle(&serde_json::to_vec(&call).unwrap(), &mut |_| {
                panic!("invalid command dispatched")
            })
            .unwrap();
        assert_eq!(result["result"]["isError"], true);
    }
}

#[test]
fn schema_exposes_portable_controls_and_bounded_measured_spatial_data() {
    let registry = tool_definitions();
    let tool = registry
        .as_array()
        .unwrap()
        .iter()
        .find(|tool| tool["name"] == "strehl_command")
        .unwrap();
    let options = tool["inputSchema"]["properties"]["command"]["oneOf"]
        .as_array()
        .unwrap();
    let command = |name: &str| {
        options
            .iter()
            .find(|option| option["properties"]["operation"]["const"] == name)
            .unwrap()
    };
    let spatial = &command("set_develop")["properties"]["recipe"]["properties"]["spatial"];
    assert_eq!(spatial["maxItems"], 6);
    assert_eq!(
        spatial["items"]["properties"]["tone_ev"]["maxLength"],
        105607
    );
    assert_eq!(
        spatial["items"]["properties"]["color_gain"]["maxLength"],
        105607
    );
    assert!(
        spatial["description"]
            .as_str()
            .unwrap()
            .contains("preserves")
    );
    assert_eq!(
        command("set_adjustments")["required"],
        json!(["operation", "adjustments"])
    );
    assert!(command("clear_adaptive")["properties"]["region_id"].is_object());
}

#[test]
fn export_schema_advertises_the_same_formats_and_optional_delivery_settings() {
    let registry = tool_definitions();
    let tool = registry
        .as_array()
        .unwrap()
        .iter()
        .find(|tool| tool["name"] == "strehl_command")
        .unwrap();
    let options = tool["inputSchema"]["properties"]["command"]["oneOf"]
        .as_array()
        .unwrap();
    let export = options
        .iter()
        .find(|option| option["properties"]["operation"]["const"] == "export")
        .unwrap();
    assert_eq!(
        export["properties"]["format"]["enum"],
        json!(["avif", "tiff", "png", "jpeg"])
    );
    assert_eq!(
        export["properties"]["color_space"]["enum"],
        json!(["srgb", "display_p3", "rec2020"])
    );
    assert_eq!(export["properties"]["quality"]["maximum"], 100);
    assert_eq!(export["properties"]["speed"]["maximum"], 10);
    assert_eq!(
        export["required"],
        json!(["operation", "file_name", "format"])
    );
}

fn initialize() -> Value {
    json!({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"independent-test-client","version":"1"}
    }})
}
fn ready(protocol: &mut Protocol) {
    let mut unexpected = |_| panic!("initialization must not execute application commands");
    let reply = protocol
        .handle(&serde_json::to_vec(&initialize()).unwrap(), &mut unexpected)
        .unwrap();
    assert_eq!(reply["result"]["protocolVersion"], "2025-11-25");
    assert!(
        protocol
            .handle(
                br#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#,
                &mut unexpected
            )
            .is_none()
    );
}

#[test]
fn handshake_and_tool_registry_work_over_real_ndjson_stream() {
    let lines = [
        initialize(),
        json!({"jsonrpc":"2.0","method":"notifications/initialized"}),
        json!({"jsonrpc":"2.0","id":2,"method":"tools/list"}),
        json!({"jsonrpc":"2.0","id":"state","method":"tools/call","params":{"name":"strehl_snapshot","arguments":{}}}),
    ];
    let wire = lines
        .iter()
        .map(Value::to_string)
        .collect::<Vec<_>>()
        .join("\n")
        + "\n";
    let mut output = Vec::new();
    let mut executions = 0;
    serve(std::io::Cursor::new(wire), &mut output, |request| {
        assert!(matches!(request.command, AgentCommand::Snapshot {}));
        executions += 1;
        AgentReply::success(json!({"revision":17,"status":"complete"}))
    })
    .unwrap();
    let replies = std::str::from_utf8(&output)
        .unwrap()
        .lines()
        .map(|s| serde_json::from_str::<Value>(s).unwrap())
        .collect::<Vec<_>>();
    assert_eq!(replies.len(), 3);
    assert_eq!(executions, 1);
    assert_eq!(replies[1]["result"]["tools"].as_array().unwrap().len(), 6);
    assert_eq!(replies[2]["result"]["structuredContent"]["revision"], 17);
    assert_eq!(replies[2]["id"], "state");
}

#[test]
fn malformed_calls_never_reach_the_application() {
    let mut protocol = Protocol::default();
    let mut never = |_| panic!("malformed requests must not execute");
    let before = protocol
        .handle(
            br#"{"jsonrpc":"2.0","id":2,"method":"tools/list"}"#,
            &mut never,
        )
        .unwrap();
    assert_eq!(before["error"]["code"], -32002);
    ready(&mut protocol);
    for message in [
        br#"not json"#.as_slice(),
        br#"[{"jsonrpc":"2.0","id":2,"method":"ping"}]"#,
        br#"{"jsonrpc":"1.0","id":2,"method":"ping"}"#,
        br#"{"jsonrpc":"2.0","id":null,"method":"ping"}"#,
        br#"{"jsonrpc":"2.0","id":2.5,"method":"ping"}"#,
        br#"{"jsonrpc":"2.0","id":2,"method":"tools/call","params":[]}"#,
    ] {
        assert!(
            protocol
                .handle(message, &mut never)
                .unwrap()
                .get("error")
                .is_some()
        );
    }
    for arguments in [
        json!({"command":{"operation":"start_stack"}}),
        json!({"expected_revision":2,"command":{"operation":"shell","path":"C:\\private"}}),
        json!({"expected_revision":2,"command":{"operation":"set_settings","patch":{"workers":0}}}),
        json!({"expected_revision":2,"command":{"operation":"export","file_name":"../secret.tif","format":"tiff"}}),
        json!({"expected_revision":2,"command":{"operation":"adaptive_develop","strength":1,"intent":"invent_texture"}}),
    ] {
        let call = json!({"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"strehl_command","arguments":arguments}});
        assert_eq!(
            protocol
                .handle(&serde_json::to_vec(&call).unwrap(), &mut never)
                .unwrap()["result"]["isError"],
            true
        );
    }
}

#[test]
fn unsupported_protocol_is_counteroffered_and_uninitialized_modern_calls_fail() {
    let mut protocol = Protocol::default();
    let mut never = |_| panic!("not a UI call");
    let mut init = initialize();
    init["params"]["protocolVersion"] = json!("2026-07-28");
    assert_eq!(
        protocol
            .handle(&serde_json::to_vec(&init).unwrap(), &mut never)
            .unwrap()["result"]["protocolVersion"],
        PROTOCOL_VERSION
    );
    let mut protocol = Protocol::default();
    assert_eq!(protocol.handle(br#"{"jsonrpc":"2.0","id":3,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28"}}}"#,&mut never).unwrap()["error"]["code"], -32002);
}

#[test]
fn oversized_input_is_drained_and_following_ping_survives() {
    let mut input = vec![b'x'; MAX_REQUEST_BYTES + 1024];
    input.extend_from_slice(b"\n{\"jsonrpc\":\"2.0\",\"id\":44,\"method\":\"ping\"}\n");
    let mut output = Vec::new();
    serve(std::io::Cursor::new(input), &mut output, |_| {
        panic!("no command expected")
    })
    .unwrap();
    let lines = std::str::from_utf8(&output)
        .unwrap()
        .lines()
        .collect::<Vec<_>>();
    assert_eq!(lines.len(), 2);
    assert_eq!(
        serde_json::from_str::<Value>(lines[0]).unwrap()["error"]["code"],
        -32700
    );
    assert_eq!(serde_json::from_str::<Value>(lines[1]).unwrap()["id"], 44);
}

#[test]
fn image_reply_uses_mcp_image_content_and_tool_errors_keep_request_identity() {
    let reply = AgentReply::image(
        json!({"space":"output"}),
        super::super::AgentImage {
            mime_type: "image/png".into(),
            data: "YWJj".into(),
        },
    )
    .into_tool_result();
    assert_eq!(reply["content"][1]["type"], "image");
    assert_eq!(reply["content"][1]["mimeType"], "image/png");
    assert_eq!(reply["structuredContent"]["space"], "output");
    let mut protocol = Protocol::default();
    ready(&mut protocol);
    let r = protocol.handle(br#"{"jsonrpc":"2.0","id":"a","method":"tools/call","params":{"name":"strehl_snapshot"}}"#,
        &mut |_| AgentReply::error("No open stack")).unwrap();
    assert_eq!(r["id"], "a");
    assert_eq!(r["result"]["isError"], true);
    assert!(r.get("error").is_none());
}

#[test]
fn metadata_and_shutdown_tools_dispatch_typed_requests_with_distinct_revision_rules() {
    let definitions = tool_definitions();
    let find = |name: &str| {
        definitions
            .as_array()
            .unwrap()
            .iter()
            .find(|tool| tool["name"] == name)
            .unwrap()
    };
    assert_eq!(find("strehl_metadata")["annotations"]["readOnlyHint"], true);
    assert_eq!(
        find("strehl_metadata")["inputSchema"]["required"],
        json!(["frame"])
    );
    assert_eq!(
        find("strehl_shutdown")["annotations"]["readOnlyHint"],
        false
    );
    assert_eq!(
        find("strehl_shutdown")["inputSchema"]["required"],
        json!(["expected_revision"])
    );

    let mut protocol = Protocol::default();
    ready(&mut protocol);
    for (name, arguments) in [
        ("strehl_metadata", json!({"frame":109})),
        ("strehl_shutdown", json!({"expected_revision":7})),
    ] {
        let call = json!({"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":name,"arguments":arguments}});
        let mut dispatched = false;
        let reply = protocol
            .handle(
                &serde_json::to_vec(&call).unwrap(),
                &mut |request: AgentRequest| {
                    match request.command {
                        AgentCommand::Metadata { frame } => {
                            assert_eq!(frame, 109);
                            assert!(request.expected_revision.is_none());
                            request.check_revision(99).unwrap();
                        }
                        AgentCommand::Shutdown {} => {
                            assert_eq!(request.expected_revision, Some(7));
                            request.check_revision(7).unwrap();
                            assert!(request.check_revision(8).is_err());
                        }
                        _ => panic!("wrong typed operation"),
                    }
                    dispatched = true;
                    AgentReply::success(json!({"accepted":true}))
                },
            )
            .unwrap();
        assert!(dispatched);
        assert_eq!(reply["result"]["structuredContent"]["accepted"], true);
    }
}

#[test]
fn invalid_metadata_and_shutdown_arguments_do_not_dispatch() {
    let mut protocol = Protocol::default();
    ready(&mut protocol);
    let mut never = |_| panic!("invalid metadata/shutdown request dispatched");
    for (name, arguments) in [
        ("strehl_metadata", json!({})),
        ("strehl_metadata", json!({"frame":-1})),
        ("strehl_metadata", json!({"frame":1.5})),
        ("strehl_metadata", json!({"frame":0,"path":"private.ARW"})),
        ("strehl_metadata", json!({"frame":0,"operation":"shutdown"})),
        ("strehl_shutdown", json!({})),
        ("strehl_shutdown", json!({"expected_revision":-1})),
        ("strehl_shutdown", json!({"expected_revision":1.5})),
        (
            "strehl_shutdown",
            json!({"expected_revision":7,"force":true}),
        ),
    ] {
        let call = json!({"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":name,"arguments":arguments}});
        let reply = protocol
            .handle(&serde_json::to_vec(&call).unwrap(), &mut never)
            .unwrap();
        assert_eq!(reply["result"]["isError"], true, "{call}");
    }
}
