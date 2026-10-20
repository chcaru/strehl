//! Bounded CPU-frame observations. No timers, files, or extra repaints.
use serde_json::{Value, json};
use std::collections::VecDeque;

const CAPACITY: usize = 256;

#[derive(Default)]
pub(super) struct FramePerformance {
    count: u64,
    samples: VecDeque<[f64; 3]>,
}

impl FramePerformance {
    pub fn record(&mut self, update_seconds: f64, previous_cpu_seconds: Option<f32>) {
        self.count += 1;
        if self.samples.len() == CAPACITY {
            self.samples.pop_front();
        }
        self.samples.push_back([
            self.count as f64,
            update_seconds * 1000.0,
            previous_cpu_seconds.map_or(-1.0, |value| value as f64 * 1000.0),
        ]);
    }

    pub fn snapshot(&self) -> Value {
        let summarize = |column: usize| {
            let mut sorted = self
                .samples
                .iter()
                .map(|row| row[column])
                .filter(|value| value.is_finite() && *value >= 0.0)
                .collect::<Vec<_>>();
            sorted.sort_unstable_by(f64::total_cmp);
            if sorted.is_empty() {
                return Value::Null;
            }
            json!({
                "p50_ms":sorted[(sorted.len()-1)/2],
                "p95_ms":sorted[((sorted.len()-1) as f64 * 0.95).ceil() as usize],
                "max_ms":sorted[sorted.len()-1]
            })
        };
        json!({
            "frames":self.count,
            "window":self.samples.len(),
            "update":summarize(1),
            "framework_cpu":summarize(2),
            "samples":self.samples,
            "columns":["frame","update_ms","previous_frame_cpu_ms"],
            "meaning":"CPU work for rendered frames, including renderer submission in framework_cpu; excludes vsync wait. Not GPU duration or input-to-photon latency. -1 means unavailable."
        })
    }
}
