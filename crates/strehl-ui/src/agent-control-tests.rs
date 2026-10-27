use super::*;
use crate::agent_interface::{AgentBridge, AgentImage};
use serde_json::{Value, json};
use std::{
    io::Cursor,
    thread,
    time::{Duration, Instant},
};

struct Captured {
    status: Option<i32>,
    output: Vec<u8>,
    errors: Vec<u8>,
}

fn invoke(args: Vec<OsString>, input: impl Read) -> Captured {
    let mut output = Vec::new();
    let mut errors = Vec::new();
    let status = run_control(args, input, &mut output, &mut errors);
    Captured {
        status,
        output,
        errors,
    }
}

fn arguments(values: &[&str]) -> Vec<OsString> {
    values.iter().map(OsString::from).collect()
}

fn session_arguments(bridge: &AgentBridge) -> Vec<OsString> {
    vec![
        "--control".into(),
        "--session".into(),
        bridge.descriptor_path().as_os_str().to_owned(),
    ]
}

fn exchange(
    bridge: &AgentBridge,
    args: Vec<OsString>,
    input: Vec<u8>,
    respond: impl FnOnce(&AgentRequest) -> AgentReply,
) -> Captured {
    // Exercise the real capability mailbox and worker; mock only the app's
    // command handler, which normally runs on its UI thread.
    let client = thread::spawn(move || invoke(args, Cursor::new(input)));
    let deadline = Instant::now() + Duration::from_secs(4);
    let incoming = loop {
        if let Some(incoming) = bridge.try_next() {
            break incoming;
        }
        assert!(
            Instant::now() < deadline,
            "Control request was not delivered"
        );
        thread::sleep(Duration::from_millis(5));
    };
    let reply = respond(&incoming.request);
    incoming.reply(reply);
    let result = client.join().unwrap();
    assert!(
        bridge.try_next().is_none(),
        "One-shot client sent another request"
    );
    result
}

struct Unreadable;
impl Read for Unreadable {
    fn read(&mut self, _: &mut [u8]) -> io::Result<usize> {
        panic!("This mode must not read standard input")
    }
}

#[test]
fn other_modes_and_help_do_not_connect_or_read_stdin() {
    for args in [vec![], arguments(&["--mcp", "--session", "unused"])] {
        let result = invoke(args, Unreadable);
        assert_eq!(result.status, None);
        assert!(result.output.is_empty() && result.errors.is_empty());
    }
    let result = invoke(arguments(&["--control", "--help"]), Unreadable);
    assert_eq!(result.status, Some(0));
    assert_eq!(result.output, HELP.as_bytes());
    assert!(result.errors.is_empty());
}

#[test]
fn invalid_arguments_fail_before_transport_or_stdin() {
    for tail in [
        vec![],
        vec!["--session"],
        vec!["--session", "--request", "-"],
        vec!["--session", ""],
        vec!["--request", "-"],
        vec!["--session", "x", "--request"],
        vec!["--session", "x", "--session", "y"],
        vec!["--session", "x", "--request", "-", "--request", "-"],
        vec!["--session", "x", "extra"],
        vec!["--session", "x", "--unknown"],
        vec!["--session", "x", "--help"],
        vec!["--help", "--session", "x"],
        vec!["--help", "extra"],
    ] {
        let mut args = arguments(&["--control"]);
        args.extend(arguments(&tail));
        let result = invoke(args, Unreadable);
        assert_eq!(result.status, Some(2), "arguments: {tail:?}");
        assert!(result.output.is_empty());
        assert!(!result.errors.is_empty());
    }
}

#[test]
fn request_input_is_exactly_one_strict_json_object() {
    for input in [
        "",
        "{",
        "[]",
        r#"{"command":{"operation":"snapshot"}} {"command":{"operation":"snapshot"}}"#,
        r#"{"command":{"operation":"snapshot"},"extra":true}"#,
        r#"{"command":{"operation":"snapshot","extra":true}}"#,
        r#"{"command":{"operation":"snapshot"},"command":{"operation":"undo"}}"#,
    ] {
        let result = invoke(
            arguments(&["--control", "--session", "unused", "--request", "-"]),
            input.as_bytes(),
        );
        assert_eq!(result.status, Some(2), "input: {input:?}");
        assert!(result.output.is_empty());
        assert!(!result.errors.is_empty());
    }
}

#[test]
fn request_limit_stops_reading_after_one_extra_byte() {
    let mut input = Cursor::new(vec![b' '; MAX_REQUEST_BYTES + 500]);
    let error = read_bounded(&mut input).unwrap_err();
    assert_eq!(error.0, 2);
    assert_eq!(input.position(), MAX_REQUEST_BYTES as u64 + 1);
    assert_eq!(
        read_bounded(Cursor::new(vec![b' '; MAX_REQUEST_BYTES]))
            .unwrap()
            .len(),
        MAX_REQUEST_BYTES
    );
}

#[test]
fn default_snapshot_roundtrip_preserves_the_entire_reply() {
    let sandbox = tempfile::tempdir().unwrap();
    let bridge = AgentBridge::start(sandbox.path()).unwrap();
    let reply = AgentReply::image(
        json!({"revision":19,"nested":{"value":[1,2,3]}}),
        AgentImage {
            mime_type: "image/png".into(),
            data: "aGVsbG8=".into(),
        },
    );
    let expected = serde_json::to_value(&reply).unwrap();
    let result = exchange(
        &bridge,
        session_arguments(&bridge),
        b"ignored stdin".to_vec(),
        |request| {
            assert!(matches!(request.command, AgentCommand::Snapshot {}));
            assert_eq!(request.expected_revision, None);
            reply
        },
    );
    assert_eq!(result.status, Some(0));
    assert!(result.errors.is_empty());
    assert_eq!(
        serde_json::from_slice::<Value>(&result.output).unwrap(),
        expected
    );
    assert_eq!(result.output.last(), Some(&b'\n'));
}

#[test]
fn request_file_roundtrip_preserves_the_supplied_mutation_revision() {
    let sandbox = tempfile::tempdir().unwrap();
    let bridge = AgentBridge::start(sandbox.path()).unwrap();
    let request_path = sandbox.path().join("command with spaces.json");
    std::fs::write(
        &request_path,
        br#"{"expected_revision":19,"command":{"operation":"undo"}}"#,
    )
    .unwrap();
    // Option order is immaterial; paths remain OsStrings throughout parsing.
    let args = vec![
        "--control".into(),
        "--request".into(),
        request_path.into_os_string(),
        "--session".into(),
        bridge.descriptor_path().as_os_str().to_owned(),
    ];
    let mut mutations = 0;
    let result = exchange(&bridge, args, Vec::new(), |request| {
        assert!(matches!(request.command, AgentCommand::Undo {}));
        assert_eq!(request.expected_revision, Some(19));
        request.check_revision(19).unwrap();
        mutations += 1;
        AgentReply::success(json!({"revision":20,"changed":true}))
    });
    assert_eq!(mutations, 1);
    assert_eq!(result.status, Some(0));
    assert!(result.errors.is_empty());
    assert_eq!(
        serde_json::from_slice::<AgentReply>(&result.output)
            .unwrap()
            .data["revision"],
        20
    );
}

#[test]
fn stale_revision_is_returned_without_refresh_or_retry() {
    let sandbox = tempfile::tempdir().unwrap();
    let bridge = AgentBridge::start(sandbox.path()).unwrap();
    let mut args = session_arguments(&bridge);
    args.extend(arguments(&["--request", "-"]));
    let mut mutations = 0;
    let result = exchange(
        &bridge,
        args,
        br#"{"expected_revision":18,"command":{"operation":"undo"}}"#.to_vec(),
        |request| {
            assert!(matches!(request.command, AgentCommand::Undo {}));
            assert_eq!(request.expected_revision, Some(18));
            match request.check_revision(19) {
                Ok(()) => {
                    mutations += 1;
                    AgentReply::success(json!({"revision":20}))
                }
                Err(error) => AgentReply::error(error),
            }
        },
    );
    assert_eq!(mutations, 0);
    assert_eq!(result.status, Some(1));
    assert!(result.errors.is_empty());
    let reply: AgentReply = serde_json::from_slice(&result.output).unwrap();
    assert!(reply.error.unwrap().contains("Workspace changed"));
}

#[test]
fn absent_mutation_revision_is_an_operation_error_not_an_implicit_snapshot() {
    let sandbox = tempfile::tempdir().unwrap();
    let bridge = AgentBridge::start(sandbox.path()).unwrap();
    let mut args = session_arguments(&bridge);
    args.extend(arguments(&["--request", "-"]));
    let result = invoke(args, br#"{"command":{"operation":"undo"}}"#.as_slice());
    assert_eq!(result.status, Some(1));
    assert!(result.errors.is_empty());
    let reply: AgentReply = serde_json::from_slice(&result.output).unwrap();
    assert!(reply.error.unwrap().contains("expected_revision"));
    assert!(bridge.try_next().is_none());
}

#[test]
fn unavailable_session_and_request_file_report_to_stderr() {
    let sandbox = tempfile::tempdir().unwrap();
    let args = vec![
        "--control".into(),
        "--session".into(),
        sandbox.path().join("session.json").into_os_string(),
    ];
    let result = invoke(args, Unreadable);
    assert_eq!(result.status, Some(1));
    assert!(result.output.is_empty());
    assert!(
        String::from_utf8(result.errors)
            .unwrap()
            .contains("Cannot connect")
    );

    let result = invoke(
        vec![
            "--control".into(),
            "--session".into(),
            "unused".into(),
            "--request".into(),
            sandbox.path().join("missing.json").into_os_string(),
        ],
        Unreadable,
    );
    assert_eq!(result.status, Some(1));
    assert!(result.output.is_empty());
    assert!(
        String::from_utf8(result.errors)
            .unwrap()
            .contains("Cannot open request")
    );
}
