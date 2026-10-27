//! Independent shutdown transport checks using the real private mailbox.
use super::*;
use crate::agent_interface::AgentCommand;
use serde_json::json;

fn incoming(bridge: &AgentBridge) -> IncomingRequest {
    let deadline = Instant::now() + Duration::from_secs(3);
    loop {
        if let Some(request) = bridge.try_next() {
            return request;
        }
        assert!(
            Instant::now() < deadline,
            "Mailbox did not deliver the request"
        );
        thread::sleep(Duration::from_millis(2));
    }
}

#[test]
fn completed_shutdown_ack_is_readable_after_bridge_drop_and_capability_revocation() {
    let files = tempfile::tempdir().unwrap();
    let bridge = AgentBridge::start(files.path()).unwrap();
    let descriptor = bridge.descriptor_path().to_owned();
    let client = BridgeClient::connect(&descriptor).unwrap();
    let id = random_hex().unwrap();
    let request = Envelope {
        capability: client.capability.clone(),
        id: id.clone(),
        expires_at_ms: now_ms() + REQUEST_LIFETIME_MS,
        request: AgentRequest {
            expected_revision: Some(12),
            command: AgentCommand::Shutdown {},
        },
    };
    atomic_new(
        &client.directory.join(format!("request-{id}.json")),
        &serde_json::to_vec(&request).unwrap(),
    )
    .unwrap();
    incoming(&bridge).reply(AgentReply::success(json!({"state":"shutdown_accepted"})));
    drop(bridge);
    assert!(!descriptor.exists());
    assert!(BridgeClient::connect(&descriptor).is_err());
    // Deliberately do not consume any response until Drop has joined the worker.
    // This catches the previous cleanup policy that deleted published replies.
    let reply_path = client.directory.join(format!("reply-{id}.json"));
    let reply: AgentReply =
        serde_json::from_slice(&read_regular_bounded(&reply_path, MAX_REPLY_BYTES).unwrap())
            .unwrap();
    assert!(reply.error.is_none());
    assert_eq!(reply.data["state"], "shutdown_accepted");
    fs::remove_file(reply_path).unwrap();
}

#[test]
fn real_client_gets_the_completed_reply_when_server_drops_immediately() {
    let files = tempfile::tempdir().unwrap();
    let bridge = AgentBridge::start(files.path()).unwrap();
    let descriptor = bridge.descriptor_path().to_owned();
    let client = BridgeClient::connect(&descriptor).unwrap();
    let caller = thread::spawn(move || {
        client.call(AgentRequest {
            expected_revision: Some(12),
            command: AgentCommand::Shutdown {},
        })
    });
    incoming(&bridge).reply(AgentReply::success(
        json!({"state":"shutdown_accepted","saved":true}),
    ));
    drop(bridge);
    assert!(!descriptor.exists());
    let reply = caller.join().unwrap().unwrap();
    assert!(reply.error.is_none(), "{:?}", reply.error);
    assert_eq!(reply.data["state"], "shutdown_accepted");
    assert_eq!(reply.data["saved"], true);
}

#[test]
fn dropping_a_session_answers_pending_requests_with_an_error_instead_of_losing_them() {
    let files = tempfile::tempdir().unwrap();
    let bridge = AgentBridge::start(files.path()).unwrap();
    let descriptor = bridge.descriptor_path().to_owned();
    let client = BridgeClient::connect(&descriptor).unwrap();
    let caller = thread::spawn(move || {
        client.call(AgentRequest {
            expected_revision: None,
            command: AgentCommand::Snapshot {},
        })
    });
    let not_answered = incoming(&bridge);
    drop(bridge);
    assert!(!descriptor.exists());
    let reply = caller.join().unwrap().unwrap();
    assert!(
        reply
            .error
            .as_deref()
            .is_some_and(|message| message.contains("disconnected"))
    );
    drop(not_answered);
}
