//! Bounded decode-to-fold handoff.
//!
//! A zero-capacity channel is deliberate. Once the consumer receives frame
//! `k`, the producer may decode frame `k + 1` while `k` is folded, but it
//! cannot hand that next frame off until the consumer is ready. Therefore one
//! chunk can own at most the frame being folded plus one producer-held decoded
//! frame, independent of stack depth.

use std::sync::mpsc::sync_channel;

/// Produce and consume `len` ordered items through a rendezvous channel.
///
/// The producer runs on a scoped OS thread. The consumer stays on its caller's
/// thread, which lets the pyramid worker keep its large accumulator in place
/// while decode overlaps it. A consumer error drops the receiver before the
/// producer is joined, so a producer blocked in `send` wakes rather than
/// hanging the error path.
pub(super) fn rendezvous<T, E, Produce, Consume>(
    len: usize,
    mut produce: Produce,
    mut consume: Consume,
) -> Result<(), E>
where
    T: Send,
    E: Send,
    Produce: FnMut(usize) -> Result<T, E> + Send,
    Consume: FnMut(usize, T) -> Result<(), E>,
{
    std::thread::scope(|scope| {
        let (sender, receiver) = sync_channel(0);
        let producer = scope.spawn(move || {
            for index in 0..len {
                let item = produce(index)?;
                if sender.send((index, item)).is_err() {
                    // The consumer already returned its own error. There is no
                    // receiver to report another value to, and send's failure
                    // is the cancellation signal rather than a second error.
                    return Ok(());
                }
            }
            Ok(())
        });

        let consumed = (|| {
            while let Ok((index, item)) = receiver.recv() {
                consume(index, item)?;
            }
            Ok(())
        })();
        drop(receiver);

        let produced = match producer.join() {
            Ok(result) => result,
            Err(payload) => std::panic::resume_unwind(payload),
        };
        consumed?;
        produced
    })
}

#[cfg(test)]
mod tests {
    use super::rendezvous;
    use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
    use std::sync::{Arc, mpsc};
    use std::time::{Duration, Instant};

    fn raise_max(maximum: &AtomicUsize, value: usize) {
        let mut old = maximum.load(Ordering::SeqCst);
        while value > old {
            match maximum.compare_exchange(old, value, Ordering::SeqCst, Ordering::SeqCst) {
                Ok(_) => break,
                Err(actual) => old = actual,
            }
        }
    }

    #[test]
    fn preserves_order_and_consumes_every_item_once() {
        let mut seen = Vec::new();
        rendezvous(
            64,
            |index| Ok::<_, &'static str>(index * 3),
            |index, value| {
                seen.push((index, value));
                Ok(())
            },
        )
        .unwrap();

        assert_eq!(
            seen,
            (0..64).map(|index| (index, index * 3)).collect::<Vec<_>>()
        );
    }

    #[test]
    fn overlaps_one_item_ahead_but_never_two() {
        let produced = Arc::new(AtomicUsize::new(0));
        let consumed = Arc::new(AtomicUsize::new(0));
        let maximum_live = Arc::new(AtomicUsize::new(0));
        let second_started = Arc::new(AtomicBool::new(false));

        let p_produced = Arc::clone(&produced);
        let p_consumed = Arc::clone(&consumed);
        let p_maximum = Arc::clone(&maximum_live);
        let p_second = Arc::clone(&second_started);
        let c_consumed = Arc::clone(&consumed);
        let c_second = Arc::clone(&second_started);

        rendezvous(
            32,
            move |index| {
                if index == 1 {
                    p_second.store(true, Ordering::SeqCst);
                }
                let now = p_produced.fetch_add(1, Ordering::SeqCst) + 1;
                let live = now - p_consumed.load(Ordering::SeqCst);
                raise_max(&p_maximum, live);
                Ok::<_, &'static str>(index)
            },
            move |index, value| {
                assert_eq!(index, value);
                if index == 0 {
                    let deadline = Instant::now() + Duration::from_secs(1);
                    while !c_second.load(Ordering::SeqCst) && Instant::now() < deadline {
                        std::thread::yield_now();
                    }
                    assert!(
                        c_second.load(Ordering::SeqCst),
                        "the producer did not begin item 1 while item 0 was consumed"
                    );
                }
                c_consumed.fetch_add(1, Ordering::SeqCst);
                Ok(())
            },
        )
        .unwrap();

        assert_eq!(produced.load(Ordering::SeqCst), 32);
        assert_eq!(consumed.load(Ordering::SeqCst), 32);
        assert_eq!(
            maximum_live.load(Ordering::SeqCst),
            2,
            "serial consumption owns one item, so more than two live items \
             means the producer got more than one item ahead"
        );
    }

    #[test]
    fn propagates_a_producer_error() {
        let mut seen = Vec::new();
        let error = rendezvous(
            8,
            |index| {
                if index == 3 {
                    Err("producer")
                } else {
                    Ok(index)
                }
            },
            |_, value| {
                seen.push(value);
                Ok(())
            },
        )
        .unwrap_err();

        assert_eq!(error, "producer");
        assert_eq!(seen, vec![0, 1, 2]);
    }

    #[test]
    fn propagates_a_consumer_error_without_hanging() {
        let (sender, receiver) = mpsc::channel();
        let handle = std::thread::spawn(move || {
            let result = rendezvous(
                100,
                |index| Ok::<_, &'static str>(index),
                |index, _| {
                    if index == 2 { Err("consumer") } else { Ok(()) }
                },
            );
            sender.send(result).unwrap();
        });

        let result = receiver
            .recv_timeout(Duration::from_secs(2))
            .expect("consumer failure left the producer blocked in send");
        assert_eq!(result.unwrap_err(), "consumer");
        handle.join().unwrap();
    }
}
