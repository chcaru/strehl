use super::*;
use std::sync::{Mutex, atomic::AtomicUsize};

#[test]
fn completion_notice_observes_published_result_or_disconnect_never_empty() {
    #[derive(Clone, Copy, Debug)]
    enum Outcome {
        Success,
        Error,
        Panic,
        Cancel,
    }
    for outcome in [
        Outcome::Success,
        Outcome::Error,
        Outcome::Panic,
        Outcome::Cancel,
    ] {
        let task_slot: Arc<Mutex<Option<Task<usize>>>> = Arc::new(Mutex::new(None));
        let observer_slot = Arc::clone(&task_slot);
        let notices = Arc::new(AtomicUsize::new(0));
        let observed_notices = Arc::clone(&notices);
        let (release, blocked) = mpsc::channel();
        let (ready, observed) = mpsc::channel();
        let task = spawn_notifying_task(
            "completion-order-control",
            move |_| {
                blocked.recv()?;
                match outcome {
                    Outcome::Success | Outcome::Cancel => Ok(73),
                    Outcome::Error => anyhow::bail!("controlled worker failure"),
                    Outcome::Panic => panic!("controlled worker panic"),
                }
            },
            move || {
                observed_notices.fetch_add(1, Ordering::SeqCst);
                // Read immediately inside the actual notification. Waiting for
                // the result here would conceal a notification-before-send bug.
                let result = observer_slot
                    .lock()
                    .unwrap()
                    .as_ref()
                    .unwrap()
                    .receiver
                    .try_recv();
                let _ = ready.send(result);
            },
        );
        if matches!(outcome, Outcome::Cancel) {
            task.cancel();
        }
        *task_slot.lock().unwrap() = Some(task);
        release.send(()).unwrap();
        let result = observed
            .recv_timeout(Duration::from_secs(5))
            .expect("Worker never notified");
        match outcome {
            Outcome::Success => assert_eq!(result.unwrap().unwrap(), 73),
            Outcome::Error => assert!(
                result
                    .unwrap()
                    .unwrap_err()
                    .contains("controlled worker failure")
            ),
            Outcome::Panic | Outcome::Cancel => assert!(
                matches!(result, Err(mpsc::TryRecvError::Disconnected)),
                "{outcome:?}: sender remained alive at notification: {result:?}"
            ),
        }
        assert_eq!(notices.load(Ordering::SeqCst), 1, "{outcome:?}");
        assert!(
            matches!(
                observed.recv_timeout(Duration::from_millis(10)),
                Err(mpsc::RecvTimeoutError::Disconnected)
            ),
            "A completed worker must retire its notification closure"
        );
    }
}
