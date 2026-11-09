//! Decode RAW frames ahead of the pyramid fold on dedicated threads.
//!
//! # Why
//!
//! `strehl_raw::decode` is single-threaded and costs about 177 ms per 33 MP
//! frame on one core, while everything after it in frame preparation is
//! data-parallel. With two frames prepared at a time, that serial decode sat at
//! the head of every frame's critical path with most of the machine idle. A
//! small pool of decoder threads now keeps a bounded window of upcoming frames
//! decoded, in the order the fold will ask for them.
//!
//! # Why the output cannot change
//!
//! Decoding is a pure function of the file. The fold still asks for each frame
//! by index and receives exactly what [`PyramidFrameSource::decode`] would have
//! returned, error included, and it still folds in index order. Only *when* the
//! decode happened moves. A frame outside the plan is decoded on demand, as
//! before.
//!
//! # Memory
//!
//! At most `window` frames are claimed and not yet taken by the fold, those
//! being decoded included: with GPU preparation on 32 logical cores, 16
//! decoders and a window of 18, about 1.3 GB at 33 MP. Sample buffers of
//! frames the fold has finished with wait for the next decodes (at most
//! `window` of them; each frame the fold takes lets one more decode claim
//! one).

use std::collections::BTreeMap;
use std::sync::{Condvar, Mutex};

use anyhow::Result;
use strehl_raw::Frame;

use super::PyramidFrameSource;

/// Decoder threads. Four keeps one decoded frame ready per ~45 ms, faster than
/// the fold consumes them, without competing much with the data-parallel pool.
pub(super) const DECODERS: usize = 4;

/// Override the decoder thread count (1..=64). Scheduling only: decoding is a
/// pure function of the file.
pub const DECODERS_ENV: &str = "STREHL_DECODE_THREADS";

/// Decoder threads for a render. When the GPU prepares frames the CPU's
/// data-parallel work mostly leaves, and decoding becomes the fold's limit:
/// then use half the logical cores, at least [`DECODERS`] and at most 16.
/// Sony's lossless files decode on one thread each (`strehl_raw`'s own
/// decoder, ~60 ms per 33 MP frame alone, ~85 ms with eight at once), so the
/// thread count is the decoding parallelism. MEASURED on bug-7 (RTX 5090,
/// 32 logical cores): 8 threads left the fold waiting ~11 ms per frame for
/// decodes, 16 left it waiting on the GPU. Decoding is a pure function of the
/// file, so the count cannot change output (see the module docs).
pub(super) fn decoders(gpu_prep: bool) -> usize {
    if let Some(n) = std::env::var(DECODERS_ENV)
        .ok()
        .and_then(|v| v.trim().parse::<usize>().ok())
        .filter(|n| (1..=64).contains(n))
    {
        return n;
    }
    if !gpu_prep {
        return DECODERS;
    }
    let cores = std::thread::available_parallelism().map_or(DECODERS, |n| n.get());
    (cores / 2).clamp(DECODERS, 16)
}

/// Wraps a frame source, serving planned indices from decode-ahead threads.
pub(super) struct DecodeAhead<'s, S: PyramidFrameSource> {
    inner: &'s S,
    /// Plan position of each frame index, `None` when not planned.
    position: Vec<Option<usize>>,
    plan: Vec<usize>,
    window: usize,
    state: Mutex<State>,
    changed: Condvar,
}

#[derive(Default)]
struct State {
    /// Next plan position a decoder may claim.
    claimed: usize,
    /// Planned frames handed to the fold so far.
    taken: usize,
    ready: BTreeMap<usize, Result<Frame>>,
    /// Frames the fold has finished with, freed by the decoders.
    retired: Vec<Frame>,
    /// Sample buffers of frames the fold has finished with, at most `window`,
    /// which the next decodes write into instead of new memory
    /// (`PyramidFrameSource::decode_reusing`).
    spare: Vec<Vec<u16>>,
    stop: bool,
}

impl<'s, S: PyramidFrameSource> DecodeAhead<'s, S> {
    /// `plan` lists frame indices in the order the fold will request them.
    /// `window` bounds how far decoding may run ahead of the fold; it must be
    /// at least the number of frames the fold prepares concurrently, or a
    /// consumer could wait on a frame no decoder is allowed to claim.
    pub(super) fn new(inner: &'s S, plan: Vec<usize>, window: usize) -> Self {
        let mut position = vec![None; inner.len()];
        for (p, &index) in plan.iter().enumerate() {
            position[index] = Some(p);
        }
        Self {
            inner,
            position,
            plan,
            window: window.max(1),
            state: Mutex::new(State::default()),
            changed: Condvar::new(),
        }
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, State> {
        self.state.lock().unwrap_or_else(|e| e.into_inner())
    }

    /// One decoder thread's loop: claim the next planned frame when the window
    /// allows, decode it outside the lock, publish it.
    pub(super) fn run_decoder(&self) {
        loop {
            let (index, spare) = {
                let mut st = self.lock();
                loop {
                    if !st.retired.is_empty() {
                        let retired = std::mem::take(&mut st.retired);
                        drop(st);
                        drop(retired);
                        st = self.lock();
                        continue;
                    }
                    if st.stop || st.claimed >= self.plan.len() {
                        return;
                    }
                    if st.claimed < st.taken + self.window {
                        break;
                    }
                    st = self.changed.wait(st).unwrap_or_else(|e| e.into_inner());
                }
                let index = self.plan[st.claimed];
                st.claimed += 1;
                (index, st.spare.pop())
            };
            // A panic here must still publish a result: the fold is waiting for
            // this index and would otherwise wait forever instead of failing.
            let frame = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| match spare {
                Some(buffer) => self.inner.decode_reusing(index, buffer),
                None => self.inner.decode(index),
            }))
            .unwrap_or_else(|_| Err(anyhow::anyhow!("decoding frame {index} panicked")));
            let mut st = self.lock();
            st.ready.insert(index, frame);
            drop(st);
            self.changed.notify_all();
        }
    }

    /// Stop the decoder threads; frames not yet taken are dropped.
    pub(super) fn stop(&self) {
        let mut st = self.lock();
        st.stop = true;
        st.ready.clear();
        drop(st);
        self.changed.notify_all();
    }
}

impl<S: PyramidFrameSource> PyramidFrameSource for DecodeAhead<'_, S> {
    #[cfg(feature = "research-lens-warp")]
    fn lens_pull(&self, index: usize) -> Result<Option<&crate::lens_research::FramePull>> {
        self.inner.lens_pull(index)
    }
    #[cfg(feature = "research-lens-warp")]
    fn lens_envelope(&self) -> Option<&serde_json::Value> {
        self.inner.lens_envelope()
    }
    fn len(&self) -> usize {
        self.inner.len()
    }
    #[cfg(feature = "gpu")]
    fn retire(&self, frame: Frame) {
        let mut st = self.lock();
        if st.stop || st.claimed >= self.plan.len() {
            // No decoder is left to reuse or free it.
            drop(st);
            drop(frame);
            return;
        }
        if st.spare.len() < self.window {
            // The next decode writes into this buffer: no new 73 MB
            // allocation, so none of its pages fault in again.
            let Frame { data, .. } = frame;
            st.spare.push(data);
            drop(st);
            return;
        }
        st.retired.push(frame);
        drop(st);
        self.changed.notify_all();
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        if self.position.get(index).copied().flatten().is_none() {
            return self.inner.decode(index);
        }
        let mut st = self.lock();
        loop {
            if let Some(frame) = st.ready.remove(&index) {
                st.taken += 1;
                drop(st);
                self.changed.notify_all();
                return frame;
            }
            if st.stop {
                drop(st);
                return self.inner.decode(index);
            }
            st = self.changed.wait(st).unwrap_or_else(|e| e.into_inner());
        }
    }
    #[cfg(feature = "native-green-cue")]
    fn green_cue_enabled(&self) -> bool {
        self.inner.green_cue_enabled()
    }
    #[cfg(all(test, feature = "native-direct-planes"))]
    fn observe_direct_inputs(
        &self,
        index: usize,
        planes: &[Vec<f32>],
        luma: &[f32],
        beta: Option<&[f32]>,
    ) -> Result<()> {
        self.inner.observe_direct_inputs(index, planes, luma, beta)
    }
    #[cfg(all(test, feature = "native-direct-planes"))]
    fn observe_direct_collapsed(&self, planes: &[Vec<f32>]) -> Result<()> {
        self.inner.observe_direct_collapsed(planes)
    }
    #[cfg(feature = "native-boundary-radiance")]
    fn boundary_config(&self) -> Option<super::native_boundary_radiance::Configuration> {
        self.inner.boundary_config()
    }
    #[cfg(feature = "native-boundary-radiance")]
    fn observe_boundary(&self, index: usize, frame: &Frame) -> Result<()> {
        self.inner.observe_boundary(index, frame)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering::SeqCst};

    /// A source whose "frames" are errors naming their index, so results can
    /// be checked without RAW files, and which counts the decodes it served.
    struct Counting {
        n: usize,
        decoded: AtomicUsize,
        panic_at: Option<usize>,
    }

    impl PyramidFrameSource for Counting {
        fn len(&self) -> usize {
            self.n
        }
        fn decode(&self, index: usize) -> Result<Frame> {
            assert!(Some(index) != self.panic_at, "planted decoder panic");
            self.decoded.fetch_add(1, SeqCst);
            Err(anyhow::anyhow!("frame {index}"))
        }
    }

    #[test]
    fn planned_frames_arrive_in_order_within_the_window_and_others_on_demand() {
        let src = Counting {
            n: 50,
            decoded: AtomicUsize::new(0),
            panic_at: None,
        };
        let plan: Vec<usize> = (0..50).filter(|i| i % 3 != 1).collect();
        let window = 5;
        let ahead = DecodeAhead::new(&src, plan.clone(), window);
        std::thread::scope(|scope| {
            for _ in 0..DECODERS {
                scope.spawn(|| ahead.run_decoder());
            }
            for (taken, &index) in plan.iter().enumerate() {
                let got = ahead.decode(index).unwrap_err().to_string();
                assert_eq!(got, format!("frame {index}"));
                // Decoding never runs more than `window` frames past the fold.
                assert!(src.decoded.load(SeqCst) <= taken + 1 + window);
            }
            // An index outside the plan is decoded on demand.
            assert_eq!(ahead.decode(1).unwrap_err().to_string(), "frame 1");
            ahead.stop();
        });
        assert_eq!(src.decoded.load(SeqCst), plan.len() + 1);
    }

    #[test]
    fn a_panicking_decode_is_an_error_for_that_frame_not_a_hang() {
        let src = Counting {
            n: 12,
            decoded: AtomicUsize::new(0),
            panic_at: Some(7),
        };
        let plan: Vec<usize> = (0..12).collect();
        let ahead = DecodeAhead::new(&src, plan.clone(), 4);
        std::thread::scope(|scope| {
            for _ in 0..DECODERS {
                scope.spawn(|| ahead.run_decoder());
            }
            for &index in &plan {
                let got = ahead.decode(index).unwrap_err().to_string();
                if index == 7 {
                    assert_eq!(got, "decoding frame 7 panicked");
                } else {
                    assert_eq!(got, format!("frame {index}"));
                }
            }
            ahead.stop();
        });
    }
}
