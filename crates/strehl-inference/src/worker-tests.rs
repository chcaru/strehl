use super::*;
use crate::{ContractIdentity, HEADS, PackageManifest, sha256};
use std::sync::{
    atomic::AtomicUsize,
    mpsc::{self, Receiver, Sender},
};
use std::time::Duration;

const WAIT: Duration = Duration::from_secs(10);

fn package() -> PredictorPackage {
    let model = b"test-only fake backend package";
    let identity = PackageIdentity {
        model: ContractIdentity {
            id: "test-model".into(),
            sha256: sha256(model),
        },
        input: ContractIdentity {
            id: "test-input".into(),
            sha256: [2; 32],
        },
        render: ContractIdentity {
            id: "test-render".into(),
            sha256: [3; 32],
        },
    };
    let manifest = PackageManifest::fixed(identity.clone(), model.len() as u64);
    PredictorPackage::from_bytes(&serde_json::to_vec(&manifest).unwrap(), model, &[identity])
        .unwrap()
}
fn request(index: u64) -> InferenceRequest {
    let mut values = vec![0.0; crate::fields::INPUT_VALUES];
    values[0] = index as f32 / 10.0;
    InferenceRequest {
        input_contract: package().manifest().identity.input.clone(),
        identity: RequestIdentity {
            source_sha256: [index as u8; 32],
            full_size: [7032, 4688],
            revision: index,
            scope: Some(format!("region-{index}")),
        },
        input: PreparedInput::from_values(values).unwrap(),
    }
}
fn output(marker: f32) -> Vec<OutputTensor> {
    HEADS
        .iter()
        .enumerate()
        .map(|(i, (_, shape))| OutputTensor {
            shape: shape.to_vec(),
            values: vec![
                if i == 0 || i == 5 {
                    1.0
                } else if i == 4 || i == 9 {
                    marker
                } else {
                    0.5
                };
                shape.iter().product()
            ],
        })
        .collect()
}

enum Action {
    Success,
    Error,
    Panic,
    Invalid,
}
#[derive(Default)]
struct Counters {
    loads: AtomicUsize,
    drops: AtomicUsize,
    active: AtomicUsize,
    peak: AtomicUsize,
}
struct Running(Arc<Counters>);
impl Drop for Running {
    fn drop(&mut self) {
        self.0.active.fetch_sub(1, Ordering::SeqCst);
    }
}
struct Controlled {
    counters: Arc<Counters>,
    started: Sender<u64>,
    release: Arc<Mutex<Receiver<Action>>>,
}
impl Drop for Controlled {
    fn drop(&mut self) {
        self.counters.drops.fetch_add(1, Ordering::SeqCst);
    }
}
impl Backend for Controlled {
    fn run(&mut self, input: &PreparedInput, _: &Cancellation) -> Result<Vec<OutputTensor>> {
        let marker = (input.values()[0] * 10.0).round() as u64;
        let active = self.counters.active.fetch_add(1, Ordering::SeqCst) + 1;
        self.counters.peak.fetch_max(active, Ordering::SeqCst);
        let _running = Running(Arc::clone(&self.counters));
        self.started.send(marker).unwrap();
        // Deliberately ignore cancellation until this synchronous call returns.
        let action = self.release.lock().unwrap().recv_timeout(WAIT).unwrap();
        match action {
            Action::Success => Ok(output(marker as f32)),
            Action::Error => anyhow::bail!("planted backend error"),
            Action::Panic => panic!("planted backend panic"),
            Action::Invalid => {
                let mut values = output(marker as f32);
                values[2].values[0] = f32::NAN;
                Ok(values)
            }
        }
    }
}
struct Harness {
    service: InferenceService,
    started: Receiver<u64>,
    release: Sender<Action>,
    notices: Receiver<()>,
    counters: Arc<Counters>,
}
fn harness() -> Harness {
    let counters = Arc::new(Counters::default());
    let worker_counts = Arc::clone(&counters);
    let (start_tx, started) = mpsc::channel();
    let (release, release_rx) = mpsc::channel();
    let releases = Arc::new(Mutex::new(release_rx));
    let (wake_tx, notices) = mpsc::channel();
    let service = InferenceService::with_notification(
        package(),
        move |_, cancel| {
            cancel.check()?;
            worker_counts.loads.fetch_add(1, Ordering::SeqCst);
            Ok(Box::new(Controlled {
                counters: Arc::clone(&worker_counts),
                started: start_tx.clone(),
                release: Arc::clone(&releases),
            }))
        },
        move || {
            let _ = wake_tx.send(());
        },
    )
    .unwrap();
    Harness {
        service,
        started,
        release,
        notices,
        counters,
    }
}
fn completion(h: &Harness) -> Completion {
    h.notices.recv_timeout(WAIT).unwrap();
    h.service.try_take().expect("wake must follow publication")
}

#[test]
fn lazy_runtime_reused_and_result_retains_all_identities_and_raw_values() {
    let h = harness();
    assert_eq!(h.counters.loads.load(Ordering::SeqCst), 0);
    for index in [1, 2] {
        let job = request(index);
        let expected_input = job.input.digest();
        let expected_request = job.identity.clone();
        let ticket = h.service.submit(job).unwrap();
        assert_eq!(h.started.recv_timeout(WAIT).unwrap(), index);
        h.release.send(Action::Success).unwrap();
        let done = completion(&h);
        assert_eq!(done.ticket, ticket);
        assert_eq!(done.request, expected_request);
        let result = done.result.unwrap();
        assert_eq!(result.request, expected_request);
        assert_eq!(result.package, package().manifest().identity);
        assert_eq!(result.package_sha256, package().digest());
        assert_eq!(result.input_sha256, expected_input);
        assert_eq!(result.fields.values(4).unwrap(), &[index as f32]);
        assert!(h.service.try_take().is_none());
    }
    assert_eq!(h.counters.loads.load(Ordering::SeqCst), 1);
    h.service.join().unwrap();
    assert_eq!(h.counters.drops.load(Ordering::SeqCst), 1);
    assert_eq!(h.counters.peak.load(Ordering::SeqCst), 1);
}

#[test]
fn replacement_never_runs_discarded_queue_and_cancelled_call_retains_lane() {
    let h = harness();
    let first = h.service.submit(request(1)).unwrap();
    assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 1);
    let discarded = h.service.submit(request(2)).unwrap();
    let last = h.service.submit(request(3)).unwrap();
    {
        let state = h.service.shared.lock();
        assert_eq!(state.active.as_ref().unwrap().0, first);
        assert!(state.active.as_ref().unwrap().1.is_cancelled());
        assert_eq!(state.pending.as_ref().unwrap().ticket, last);
    }
    assert_eq!(h.counters.active.load(Ordering::SeqCst), 1);
    assert!(h.started.try_recv().is_err());
    h.service.cancel(discarded); // A delayed cancellation must not cancel request 3.
    h.release.send(Action::Success).unwrap();
    assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 3);
    h.release.send(Action::Success).unwrap();
    let done = completion(&h);
    assert_eq!(done.ticket, last);
    assert_eq!(done.result.unwrap().fields.values(4).unwrap(), &[3.0]);
    assert_eq!(
        h.counters.loads.load(Ordering::SeqCst),
        1,
        "cancel after healthy call should retain runtime"
    );
    assert_eq!(h.counters.peak.load(Ordering::SeqCst), 1);
    assert!(
        h.notices.try_recv().is_err(),
        "stale work must not notify a completion"
    );
    h.service.join().unwrap();
}

#[test]
fn explicit_cancel_removes_queued_job_and_shutdown_drains_without_publication() {
    let h = harness();
    h.service.submit(request(1)).unwrap();
    assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 1);
    let queued = h.service.submit(request(2)).unwrap();
    h.service.cancel(queued);
    assert!(h.service.shared.lock().pending.is_none());
    h.service.close();
    assert!(h.service.submit(request(3)).is_err());
    assert_eq!(h.counters.active.load(Ordering::SeqCst), 1);
    h.release.send(Action::Success).unwrap();
    h.service.join().unwrap();
    assert_eq!(h.counters.active.load(Ordering::SeqCst), 0);
    assert_eq!(h.counters.drops.load(Ordering::SeqCst), 1);
    assert!(h.started.try_recv().is_err());
    assert!(h.notices.try_recv().is_err());
}

#[test]
fn panic_error_and_invalid_fields_discard_runtime_and_next_request_recovers() {
    for action in [Action::Panic, Action::Error, Action::Invalid] {
        let h = harness();
        h.service.submit(request(1)).unwrap();
        assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 1);
        h.release.send(action).unwrap();
        assert!(completion(&h).result.is_err());
        assert_eq!(h.counters.drops.load(Ordering::SeqCst), 1);
        let ticket = h.service.submit(request(2)).unwrap();
        assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 2);
        h.release.send(Action::Success).unwrap();
        let done = completion(&h);
        assert_eq!(done.ticket, ticket);
        assert!(done.result.is_ok());
        assert_eq!(h.counters.loads.load(Ordering::SeqCst), 2);
        assert_eq!(h.counters.peak.load(Ordering::SeqCst), 1);
        h.service.join().unwrap();
    }
}

#[test]
fn stale_panic_and_error_cannot_replace_newer_request() {
    for action in [Action::Panic, Action::Error, Action::Invalid] {
        let h = harness();
        h.service.submit(request(1)).unwrap();
        assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 1);
        let latest = h.service.submit(request(2)).unwrap();
        h.release.send(action).unwrap();
        assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 2);
        h.release.send(Action::Success).unwrap();
        let done = completion(&h);
        assert_eq!(done.ticket, latest);
        assert!(done.result.is_ok());
        assert!(h.notices.try_recv().is_err());
        assert_eq!(h.counters.peak.load(Ordering::SeqCst), 1);
        h.service.join().unwrap();
    }
}

#[test]
fn factory_panic_or_error_does_not_strand_lane() {
    for panic in [false, true] {
        let calls = Arc::new(AtomicUsize::new(0));
        let worker_calls = Arc::clone(&calls);
        let (wake, notices) = mpsc::channel();
        struct Immediate;
        impl Backend for Immediate {
            fn run(&mut self, _: &PreparedInput, _: &Cancellation) -> Result<Vec<OutputTensor>> {
                Ok(output(7.0))
            }
        }
        let service = InferenceService::with_notification(
            package(),
            move |_, _| {
                if worker_calls.fetch_add(1, Ordering::SeqCst) == 0 {
                    if panic {
                        panic!("planted factory panic");
                    }
                    anyhow::bail!("planted factory error");
                }
                Ok(Box::new(Immediate))
            },
            move || {
                let _ = wake.send(());
            },
        )
        .unwrap();
        service.submit(request(1)).unwrap();
        notices.recv_timeout(WAIT).unwrap();
        assert!(service.try_take().unwrap().result.is_err());
        let latest = service.submit(request(2)).unwrap();
        notices.recv_timeout(WAIT).unwrap();
        let done = service.try_take().unwrap();
        assert_eq!(done.ticket, latest);
        assert!(done.result.is_ok());
        assert_eq!(calls.load(Ordering::SeqCst), 2);
        service.join().unwrap();
    }
}

#[test]
fn completed_old_result_is_removed_on_new_submission() {
    let h = harness();
    h.service.submit(request(1)).unwrap();
    assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 1);
    h.release.send(Action::Success).unwrap();
    h.notices.recv_timeout(WAIT).unwrap();
    let latest = h.service.submit(request(2)).unwrap();
    assert!(
        h.service.try_take().is_none(),
        "unconsumed previous completion must be invalidated"
    );
    assert_eq!(h.started.recv_timeout(WAIT).unwrap(), 2);
    h.release.send(Action::Success).unwrap();
    assert_eq!(completion(&h).ticket, latest);
    h.service.join().unwrap();
}

#[test]
fn incompatible_input_contract_is_rejected_without_starting_runtime() {
    let h = harness();
    for change_name in [true, false] {
        let mut wrong = request(1);
        if change_name {
            wrong.input_contract.id.push('x');
        } else {
            wrong.input_contract.sha256[0] ^= 1;
        }
        assert!(h.service.submit(wrong).is_err());
    }
    assert_eq!(h.counters.loads.load(Ordering::SeqCst), 0);
    assert!(h.service.shared.lock().pending.is_none());
    h.service.join().unwrap();
}
