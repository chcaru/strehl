//! Scratch-only timers for the performance investigation (outputs/a7cr-perf-2).
//! Included into each crate by path; every crate keeps its own event list and
//! appends it to the file named by `STREHL_TP_OUT` when `dump` is called.
//! Without that variable nothing is recorded.
#![allow(dead_code)]
use std::sync::{Mutex, OnceLock};
use std::time::{Instant, SystemTime, UNIX_EPOCH};

pub struct Event {
    pub start: f64,
    pub dur: f64,
    pub name: &'static str,
    pub arg: u64,
    pub thread: String,
}

static EVENTS: Mutex<Vec<Event>> = Mutex::new(Vec::new());

pub fn on() -> bool {
    static ON: OnceLock<bool> = OnceLock::new();
    *ON.get_or_init(|| std::env::var_os("STREHL_TP_OUT").is_some())
}

pub fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0.0, |d| d.as_secs_f64())
}

pub fn record(name: &'static str, arg: u64, start: f64, dur: f64) {
    if !on() {
        return;
    }
    let thread = std::thread::current().name().unwrap_or("").to_string();
    if let Ok(mut e) = EVENTS.lock() {
        e.push(Event {
            start,
            dur,
            name,
            arg,
            thread,
        });
    }
}

pub struct Span {
    name: &'static str,
    arg: u64,
    start: f64,
    t: Instant,
}

pub fn span(name: &'static str, arg: u64) -> Span {
    Span {
        name,
        arg,
        start: if on() { now() } else { 0.0 },
        t: Instant::now(),
    }
}

impl Span {
    pub fn secs(&self) -> f64 {
        self.t.elapsed().as_secs_f64()
    }
}

impl Drop for Span {
    fn drop(&mut self) {
        record(self.name, self.arg, self.start, self.t.elapsed().as_secs_f64());
    }
}

/// A sum of many short intervals, recorded as one event when dropped.
pub struct Sum {
    name: &'static str,
    arg: u64,
    start: f64,
    pub total: f64,
}

pub fn sum(name: &'static str, arg: u64) -> Sum {
    Sum {
        name,
        arg,
        start: if on() { now() } else { 0.0 },
        total: 0.0,
    }
}

impl Sum {
    pub fn add<R>(&mut self, f: impl FnOnce() -> R) -> R {
        let t = Instant::now();
        let r = f();
        self.total += t.elapsed().as_secs_f64();
        r
    }
}

impl Drop for Sum {
    fn drop(&mut self) {
        record(self.name, self.arg, self.start, self.total);
    }
}

pub fn dump(tag: &str) {
    use std::io::Write;
    let Some(path) = std::env::var_os("STREHL_TP_OUT") else {
        return;
    };
    let events = match EVENTS.lock() {
        Ok(mut e) => std::mem::take(&mut *e),
        Err(_) => return,
    };
    let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(path) else {
        return;
    };
    let mut out = String::new();
    for e in &events {
        out.push_str(&format!(
            "{tag},{:.6},{:.6},{},{},{}\n",
            e.start, e.dur, e.name, e.arg, e.thread
        ));
    }
    let _ = f.write_all(out.as_bytes());
}
