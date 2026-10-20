use super::*;
use crate::agent_interface::{AgentCommand, AgentReply};
use serde_json::json;

struct Sandbox(PathBuf);
impl Sandbox {
    fn new() -> Self {
        let root =
            std::env::temp_dir().join(format!("strehl-agent-test-{}", random_hex().unwrap()));
        fs::create_dir(&root).unwrap();
        Self(root)
    }
}
impl Drop for Sandbox {
    fn drop(&mut self) {
        // Test-owned fresh directory only. Give the bridge worker time to release.
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn actual_worker_roundtrip_is_bounded_and_stays_off_the_ui_thread() {
    let sandbox = Sandbox::new();
    let bridge = AgentBridge::start(&sandbox.0).unwrap();
    let descriptor = bridge.descriptor_path().to_owned();
    let thread = thread::spawn(move || {
        let client = BridgeClient::connect(&descriptor).unwrap();
        client
            .call(AgentRequest {
                expected_revision: None,
                command: AgentCommand::Snapshot {},
            })
            .unwrap()
    });
    let deadline = Instant::now() + Duration::from_secs(3);
    let incoming = loop {
        if let Some(request) = bridge.try_next() {
            break request;
        }
        assert!(Instant::now() < deadline, "Worker did not deliver request");
        thread::sleep(Duration::from_millis(5));
    };
    assert!(matches!(
        incoming.request.command,
        AgentCommand::Snapshot {}
    ));
    incoming.reply(AgentReply::success(json!({"revision":19})));
    assert_eq!(thread.join().unwrap().data["revision"], 19);
    drop(bridge);
}

#[test]
fn abandoned_reply_pages_cannot_starve_new_requests() {
    let sandbox = Sandbox::new();
    let bridge = AgentBridge::start(&sandbox.0).unwrap();
    let descriptor = bridge.descriptor_path().to_owned();
    let directory = descriptor.parent().unwrap();
    for index in 0..384 {
        // Reply filenames sort before requests on Windows, and none are old
        // enough for cleanup: the scan must advance beyond its first page.
        fs::write(directory.join(format!("reply-{index:064x}.json")), b"{}").unwrap();
    }
    let client = thread::spawn(move || {
        BridgeClient::connect(&descriptor)
            .unwrap()
            .call(AgentRequest {
                expected_revision: None,
                command: AgentCommand::Snapshot {},
            })
            .unwrap()
    });
    let deadline = Instant::now() + Duration::from_secs(4);
    let request = loop {
        if let Some(request) = bridge.try_next() {
            break request;
        }
        assert!(
            Instant::now() < deadline,
            "Abandoned reply pages starved the mailbox"
        );
        thread::sleep(Duration::from_millis(5));
    };
    request.reply(AgentReply::success(json!({"revision":93})));
    assert_eq!(client.join().unwrap().data["revision"], 93);
}

#[test]
fn wrong_capability_malformed_and_expired_messages_cannot_mutate() {
    let sandbox = Sandbox::new();
    let bridge = AgentBridge::start(&sandbox.0).unwrap();
    let dir = bridge.descriptor_path().parent().unwrap();
    let d: Descriptor =
        serde_json::from_slice(&fs::read(bridge.descriptor_path()).unwrap()).unwrap();
    let id = random_hex().unwrap();
    let envelope = Envelope {
        capability: "0".repeat(64),
        id: id.clone(),
        expires_at_ms: now_ms() + REQUEST_LIFETIME_MS,
        request: AgentRequest {
            expected_revision: Some(1),
            command: AgentCommand::StartStack {},
        },
    };
    atomic_new(
        &dir.join(format!("request-{id}.json")),
        &serde_json::to_vec(&envelope).unwrap(),
    )
    .unwrap();
    let expired_id = random_hex().unwrap();
    let expired = Envelope {
        capability: d.capability,
        id: expired_id.clone(),
        expires_at_ms: now_ms().saturating_sub(1),
        request: envelope.request,
    };
    atomic_new(
        &dir.join(format!("request-{expired_id}.json")),
        &serde_json::to_vec(&expired).unwrap(),
    )
    .unwrap();
    let bad_id = random_hex().unwrap();
    atomic_new(
        &dir.join(format!("request-{bad_id}.json")),
        br#"{"not":"a request"}"#,
    )
    .unwrap();
    let deadline = Instant::now() + Duration::from_secs(3);
    while !dir.join(format!("reply-{expired_id}.json")).is_file() {
        assert!(bridge.try_next().is_none(), "Rejected request reached UI");
        assert!(Instant::now() < deadline);
        thread::sleep(Duration::from_millis(5));
    }
    assert!(bridge.try_next().is_none());
    let reply: AgentReply =
        serde_json::from_slice(&fs::read(dir.join(format!("reply-{expired_id}.json"))).unwrap())
            .unwrap();
    assert!(reply.error.unwrap().contains("Expired"));
    assert!(
        !dir.join(format!("reply-{id}.json")).exists(),
        "Unauthorized sender received response"
    );
}

#[test]
fn imports_cannot_escape_a_human_shared_root() {
    let sandbox = Sandbox::new();
    let root = sandbox.0.join("shared");
    fs::create_dir(&root).unwrap();
    fs::write(root.join("preset.xmp"), "test").unwrap();
    fs::write(sandbox.0.join("private.txt"), "private").unwrap();
    assert!(
        resolve_granted_path(&root, "preset.xmp")
            .unwrap()
            .starts_with(root.canonicalize().unwrap())
    );
    assert!(resolve_granted_path(&root, "../private.txt").is_err());
    assert!(resolve_granted_path(&root, "missing.xmp").is_err());
    assert!(resolve_granted_path(&root, sandbox.0.join("private.txt").to_str().unwrap()).is_err());
    #[cfg(unix)]
    {
        std::os::unix::fs::symlink(sandbox.0.join("private.txt"), root.join("escape")).unwrap();
        assert!(resolve_granted_path(&root, "escape").is_err());
    }
}

#[test]
fn private_descriptor_permissions_and_size_limit_are_real() {
    let sandbox = Sandbox::new();
    let bridge = AgentBridge::start(&sandbox.0).unwrap();
    let descriptor = bridge.descriptor_path();
    assert!(BridgeClient::connect(descriptor).is_ok());
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        use windows_sys::Win32::{
            Foundation::LocalFree,
            Security::{
                Authorization::{
                    ConvertSecurityDescriptorToStringSecurityDescriptorW, GetNamedSecurityInfoW,
                    SE_FILE_OBJECT,
                },
                DACL_SECURITY_INFORMATION,
            },
        };
        // Read the OS's actual ACL rather than asserting our input SDDL.
        let path: Vec<u16> = descriptor
            .parent()
            .unwrap()
            .canonicalize()
            .unwrap()
            .as_os_str()
            .encode_wide()
            .chain(Some(0))
            .collect();
        let mut security = std::ptr::null_mut();
        let code = unsafe {
            GetNamedSecurityInfoW(
                path.as_ptr(),
                SE_FILE_OBJECT,
                DACL_SECURITY_INFORMATION,
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                &mut security,
            )
        };
        assert_eq!(code, 0);
        let mut sddl = std::ptr::null_mut();
        let mut length = 0;
        let converted = unsafe {
            ConvertSecurityDescriptorToStringSecurityDescriptorW(
                security,
                1,
                DACL_SECURITY_INFORMATION,
                &mut sddl,
                &mut length,
            )
        };
        assert_ne!(converted, 0);
        let actual = unsafe {
            String::from_utf16_lossy(std::slice::from_raw_parts(sddl, length as usize - 1))
        };
        unsafe {
            LocalFree(sddl.cast());
            LocalFree(security);
        }
        assert!(
            actual.starts_with("D:P"),
            "ACL must block broad inheritance: {actual}"
        );
        assert_eq!(
            actual.matches('(').count(),
            1,
            "Unexpected additional ACL grant: {actual}"
        );
        assert!(
            actual.contains(";;;OW)"),
            "Only the owner should be granted access: {actual}"
        );
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        assert_eq!(
            fs::metadata(descriptor).unwrap().permissions().mode() & 0o777,
            0o600
        );
        assert_eq!(
            fs::metadata(descriptor.parent().unwrap())
                .unwrap()
                .permissions()
                .mode()
                & 0o777,
            0o700
        );
    }
    let too_big = sandbox.0.join("large.json");
    fs::write(&too_big, vec![0_u8; 4097]).unwrap();
    assert!(read_regular_bounded(&too_big, 4096).is_err());
    assert!(read_regular_bounded(&sandbox.0, 4096).is_err());
}

#[test]
fn replayed_authenticated_command_is_delivered_only_once() {
    let sandbox = Sandbox::new();
    let bridge = AgentBridge::start(&sandbox.0).unwrap();
    let d: Descriptor =
        serde_json::from_slice(&fs::read(bridge.descriptor_path()).unwrap()).unwrap();
    let id = random_hex().unwrap();
    let path = bridge
        .descriptor_path()
        .parent()
        .unwrap()
        .join(format!("request-{id}.json"));
    let body = serde_json::to_vec(&Envelope {
        capability: d.capability,
        id,
        expires_at_ms: now_ms() + REQUEST_LIFETIME_MS,
        request: AgentRequest {
            expected_revision: Some(4),
            command: AgentCommand::StartStack {},
        },
    })
    .unwrap();
    atomic_new(&path, &body).unwrap();
    let deadline = Instant::now() + Duration::from_secs(3);
    let first = loop {
        if let Some(request) = bridge.try_next() {
            break request;
        }
        assert!(Instant::now() < deadline);
        thread::sleep(Duration::from_millis(5));
    };
    first.reply(AgentReply::success(json!({"state":"queued"})));
    atomic_new(&path, &body).unwrap();
    let deadline = Instant::now() + Duration::from_secs(1);
    while path.exists() {
        assert!(
            bridge.try_next().is_none(),
            "Replay reached the application"
        );
        assert!(Instant::now() < deadline);
        thread::sleep(Duration::from_millis(5));
    }
    assert!(bridge.try_next().is_none());
}
