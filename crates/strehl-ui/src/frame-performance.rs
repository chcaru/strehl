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
    pub fn record(&mut self, frame: u64, update_seconds: f64, previous_cpu_seconds: Option<f32>) {
        // egui can repeat App::update to settle a layout. Charge every pass to
        // its one frame; eframe's previous-frame CPU value must be sampled once.
        if let Some(last) = self.samples.back_mut()
            && last[0] == frame as f64
        {
            last[1] += update_seconds * 1000.0;
            return;
        }
        self.count += 1;
        if self.samples.len() == CAPACITY {
            self.samples.pop_front();
        }
        self.samples.push_back([
            frame as f64,
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
            "meaning":"One observation per egui frame. update_ms sums repeated layout passes; framework_cpu samples the previous frame once and includes renderer submission. Excludes vsync wait. Not GPU duration or input-to-photon latency. -1 means unavailable."
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn repeated_layout_passes_sum_update_work_without_counting_duplicate_frames() {
        let mut observations = FramePerformance::default();
        observations.record(12, 0.001, Some(0.004));
        observations.record(12, 0.002, Some(0.004));
        observations.record(13, 0.005, Some(0.006));
        let value = observations.snapshot();
        assert_eq!(value["frames"], 2);
        assert_eq!(value["window"], 2);
        assert_eq!(value["samples"][0][0], 12.0);
        assert_eq!(value["samples"][0][1], 3.0);
        assert_eq!(value["samples"][1][1], 5.0);
        assert_eq!(value["update"]["max_ms"], 5.0);
        assert!((value["framework_cpu"]["max_ms"].as_f64().unwrap() - 6.0).abs() < 1e-5);
    }
}
