use crate::{
    ContractIdentity, Digest, OutputTensor, PackageIdentity, PredictorPackage, PreparedInput,
    RawFields,
};
use anyhow::{Result, ensure};
use std::{
    panic::{AssertUnwindSafe, catch_unwind},
    sync::{
        Arc, Condvar, Mutex, MutexGuard,
        atomic::{AtomicBool, Ordering},
    },
    thread::{self, JoinHandle},
};

#[derive(Clone, Default)]
pub struct Cancellation(Arc<AtomicBool>);
impl Cancellation {
    pub fn is_cancelled(&self) -> bool {
        self.0.load(Ordering::Relaxed)
    }
    pub fn check(&self) -> Result<()> {
        ensure!(!self.is_cancelled(), "Inference cancelled");
        Ok(())
    }
    fn cancel(&self) {
        self.0.store(true, Ordering::Relaxed);
    }
}

/// Backends are created and retained on the worker. A synchronous backend may not
/// stop mid-call; the lane stays occupied until it returns, even after cancellation.
pub trait Backend {
    fn run(&mut self, input: &PreparedInput, cancelled: &Cancellation)
    -> Result<Vec<OutputTensor>>;
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RequestIdentity {
    pub source_sha256: Digest,
    pub full_size: [u32; 2],
    /// Caller-owned revision, in addition to the service's monotonic ticket.
    pub revision: u64,
    /// User editing scope; never interpreted as a semantic input mask.
    pub scope: Option<String>,
}

pub struct InferenceRequest {
    pub identity: RequestIdentity,
    /// The preparer's declared contract, checked against the retained package.
    pub input_contract: ContractIdentity,
    pub input: PreparedInput,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Ticket(u64);
impl Ticket {
    pub fn generation(self) -> u64 {
        self.0
    }
}

pub struct InferenceResult {
    pub request: RequestIdentity,
    pub package: PackageIdentity,
    pub package_sha256: Digest,
    pub input_sha256: Digest,
    pub fields: RawFields,
}

pub struct Completion {
    pub ticket: Ticket,
    pub request: RequestIdentity,
    pub result: std::result::Result<InferenceResult, String>,
}

struct Job {
    ticket: Ticket,
    request: InferenceRequest,
    cancelled: Cancellation,
}
#[derive(Default)]
struct State {
    closed: bool,
    generation: u64,
    current: Option<Ticket>,
    pending: Option<Job>,
    active: Option<(Ticket, Cancellation)>,
    completion: Option<Completion>,
}
#[derive(Default)]
struct Shared {
    state: Mutex<State>,
    available: Condvar,
}
impl Shared {
    fn lock(&self) -> MutexGuard<'_, State> {
        self.state
            .lock()
            .unwrap_or_else(|poison| poison.into_inner())
    }
}

/// One worker, one retained runtime, one replaceable pending input and one latest
/// completion. Submission only moves immutable handles; validate/prepare inputs
/// and load packages elsewhere on a worker. Pan/zoom/Amount must reuse frozen fields.
pub struct InferenceService {
    shared: Arc<Shared>,
    worker: Option<JoinHandle<()>>,
    input_contract: ContractIdentity,
}

impl InferenceService {
    pub fn start(
        package: PredictorPackage,
        factory: impl FnMut(&PredictorPackage, &Cancellation) -> Result<Box<dyn Backend>>
        + Send
        + 'static,
    ) -> Result<Self> {
        Self::with_notification(package, factory, || {})
    }

    /// Notification occurs only after a current completion is available. It runs on
    /// the worker, outside the state lock. A late wake is harmless: poll by ticket.
    pub fn with_notification(
        package: PredictorPackage,
        factory: impl FnMut(&PredictorPackage, &Cancellation) -> Result<Box<dyn Backend>>
        + Send
        + 'static,
        notify: impl Fn() + Send + 'static,
    ) -> Result<Self> {
        let shared = Arc::new(Shared::default());
        let work = Arc::clone(&shared);
        let input_contract = package.manifest().identity.input.clone();
        let worker = thread::Builder::new()
            .name("strehl-predictor".into())
            .spawn(move || worker_loop(work, package, factory, notify))?;
        Ok(Self {
            shared,
            worker: Some(worker),
            input_contract,
        })
    }

    pub fn submit(&self, request: InferenceRequest) -> Result<Ticket> {
        ensure!(
            request.input_contract == self.input_contract,
            "Prepared input contract differs from the predictor package"
        );
        ensure!(
            request
                .identity
                .full_size
                .iter()
                .all(|n| (1..=1_048_576).contains(n)),
            "Invalid source dimensions"
        );
        ensure!(
            request.identity.scope.as_ref().is_none_or(|s| !s.is_empty()
                && s.len() <= 128
                && !s.chars().any(char::is_control)),
            "Invalid request scope"
        );
        let mut state = self.shared.lock();
        ensure!(!state.closed, "Inference service is closed");
        let generation = state
            .generation
            .checked_add(1)
            .ok_or_else(|| anyhow::anyhow!("Inference generation exhausted"))?;
        let ticket = Ticket(generation);
        state.generation = generation;
        state.current = Some(ticket);
        state.completion = None;
        if let Some((_, token)) = &state.active {
            token.cancel();
        }
        // The replaced request has never owned the runtime lane.
        if let Some(previous) = state.pending.take() {
            previous.cancelled.cancel();
        }
        state.pending = Some(Job {
            ticket,
            request,
            cancelled: Cancellation::default(),
        });
        self.shared.available.notify_one();
        Ok(ticket)
    }

    /// Cancels only this ticket, so delayed callers cannot cancel a newer request.
    pub fn cancel(&self, ticket: Ticket) {
        let mut state = self.shared.lock();
        if state.current != Some(ticket) {
            return;
        }
        state.current = None;
        state.completion = None;
        if let Some((active, token)) = &state.active {
            if *active == ticket {
                token.cancel();
            }
        }
        if state
            .pending
            .as_ref()
            .is_some_and(|job| job.ticket == ticket)
        {
            if let Some(job) = state.pending.take() {
                job.cancelled.cancel();
            }
        }
    }

    pub fn try_take(&self) -> Option<Completion> {
        let mut state = self.shared.lock();
        let result = state.completion.take()?;
        (state.current == Some(result.ticket) && !state.closed).then_some(result)
    }

    /// Nonblocking shutdown. An in-flight backend call retains its lane and runtime
    /// until it returns; it can no longer publish or start queued work.
    pub fn close(&self) {
        let mut state = self.shared.lock();
        state.closed = true;
        state.current = None;
        state.completion = None;
        if let Some((_, token)) = &state.active {
            token.cancel();
        }
        if let Some(job) = state.pending.take() {
            job.cancelled.cancel();
        }
        self.shared.available.notify_one();
    }

    /// Explicit blocking drain for tests/process shutdown, never a UI-frame action.
    pub fn join(mut self) -> thread::Result<()> {
        self.close();
        self.worker.take().unwrap().join()
    }
}
impl Drop for InferenceService {
    fn drop(&mut self) {
        self.close();
    }
}

fn worker_loop(
    shared: Arc<Shared>,
    package: PredictorPackage,
    mut factory: impl FnMut(&PredictorPackage, &Cancellation) -> Result<Box<dyn Backend>>,
    notify: impl Fn(),
) {
    let mut backend: Option<Box<dyn Backend>> = None;
    loop {
        let job = {
            let mut state = shared.lock();
            while !state.closed && state.pending.is_none() {
                state = shared
                    .available
                    .wait(state)
                    .unwrap_or_else(|p| p.into_inner());
            }
            if state.closed {
                return;
            }
            let job = state.pending.take().unwrap();
            state.active = Some((job.ticket, job.cancelled.clone()));
            job
        };
        let mut discard_on_error = false;
        let outcome = catch_unwind(AssertUnwindSafe(|| -> Result<InferenceResult> {
            job.cancelled.check()?;
            if backend.is_none() {
                backend = Some(factory(&package, &job.cancelled)?);
            }
            job.cancelled.check()?;
            discard_on_error = true;
            let outputs = backend
                .as_mut()
                .unwrap()
                .run(&job.request.input, &job.cancelled)?;
            discard_on_error = false;
            job.cancelled.check()?;
            discard_on_error = true;
            let fields = RawFields::validate(outputs)?;
            discard_on_error = false;
            job.cancelled.check()?;
            Ok(InferenceResult {
                request: job.request.identity.clone(),
                package: package.manifest().identity.clone(),
                package_sha256: package.digest(),
                input_sha256: job.request.input.digest(),
                fields,
            })
        }));
        let result = match outcome {
            Ok(Ok(result)) => Ok(result),
            Ok(Err(error)) => {
                // Cancellation after a successful synchronous call does not poison
                // the retained model; actual backend/field errors do discard it.
                if discard_on_error {
                    backend = None;
                }
                Err(format!("{error:#}"))
            }
            Err(_) => {
                // An unwound backend may have partial internal state. Discard it
                // before accepting a later request; never reuse it after a panic.
                backend = None;
                Err("Predictor backend panicked; runtime discarded".into())
            }
        };
        let published = {
            let mut state = shared.lock();
            state.active = None;
            if !state.closed && state.current == Some(job.ticket) && !job.cancelled.is_cancelled() {
                state.completion = Some(Completion {
                    ticket: job.ticket,
                    request: job.request.identity,
                    result,
                });
                true
            } else {
                false
            }
        };
        if published {
            // A faulty notification must not strand a healthy runtime or its lane.
            let _ = catch_unwind(AssertUnwindSafe(&notify));
        }
    }
}

#[cfg(test)]
#[path = "worker-tests.rs"]
mod tests;
