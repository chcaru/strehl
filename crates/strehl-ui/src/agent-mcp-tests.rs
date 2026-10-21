use super::*;

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
    assert_eq!(replies[1]["result"]["tools"].as_array().unwrap().len(), 4);
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
