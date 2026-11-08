//! Active-time countdown: camera cadence, not exposure time alone.
use std::time::{Duration, Instant};

pub fn shutter_seconds(value: u64) -> Option<f64> {
    if value == 0 || value >= u64::from(u32::MAX) {
        return None;
    }
    let numerator = value >> 16;
    let denominator = value & 0xffff;
    (numerator > 0 && denominator > 0).then(|| numerator as f64 / denominator as f64)
}

pub fn initial_cycle(shutter: u64, settle_ms: u32) -> Option<Duration> {
    // A rough allowance for focus, status, shutter acknowledgement and SD write.
    // Real completed cycles replace this guess; it is not a hardware calibration.
    Some(Duration::from_secs_f64(
        shutter_seconds(shutter)? + f64::from(settle_ms) / 1000.0 + 1.0,
    ))
}

pub fn initial_setup(settle_ms: u32) -> Duration {
    Duration::from_millis(u64::from(settle_ms) + 1000)
}

pub fn format_duration(duration: Duration) -> String {
    let secs = duration.as_secs() + u64::from(duration.subsec_nanos() > 0);
    if secs >= 3600 {
        format!("{}h {:02}m {:02}s", secs / 3600, secs / 60 % 60, secs % 60)
    } else {
        format!("{}m {:02}s", secs / 60, secs % 60)
    }
}

#[derive(Clone, Debug)]
pub struct RunTiming {
    active_since: Option<Instant>,
    accrued: Duration,
    last_cycle: Duration,
    setup: Duration,
    cycle: Duration,
    measured: Duration,
    pub completed: usize,
    pub total: usize,
    pub finished: bool,
    approach_complete: bool,
}

impl RunTiming {
    pub fn new(total: usize, cycle: Duration, setup: Duration, now: Instant) -> Self {
        Self {
            active_since: Some(now),
            accrued: Duration::ZERO,
            last_cycle: Duration::ZERO,
            setup,
            cycle,
            measured: Duration::ZERO,
            completed: 0,
            total,
            finished: false,
            approach_complete: false,
        }
    }
    pub fn elapsed(&self, now: Instant) -> Duration {
        self.accrued
            + self
                .active_since
                .map(|start| now.saturating_duration_since(start))
                .unwrap_or_default()
    }
    pub fn pause(&mut self, now: Instant) {
        self.accrued = self.elapsed(now);
        self.active_since = None;
    }
    pub fn resume(&mut self, now: Instant) {
        if !self.finished && self.active_since.is_none() {
            self.active_since = Some(now);
        }
    }
    pub fn approached(&mut self, now: Instant) {
        self.approach_complete = true;
        self.last_cycle = self.elapsed(now);
    }
    pub fn complete_cycle(&mut self, now: Instant) {
        let elapsed = self.elapsed(now);
        self.measured += elapsed.saturating_sub(self.last_cycle);
        self.last_cycle = elapsed;
        self.completed += 1;
        self.cycle = self.measured.div_f64(self.completed as f64);
    }
    pub fn finish(&mut self, now: Instant) {
        self.pause(now);
        self.finished = true;
    }
    pub fn remaining(&self, now: Instant) -> Duration {
        if self.completed >= self.total {
            return Duration::ZERO;
        }
        let pending = self.cycle.mul_f64((self.total - self.completed) as f64)
            + if self.approach_complete {
                Duration::ZERO
            } else {
                self.setup
            };
        pending.saturating_sub(self.elapsed(now).saturating_sub(self.last_cycle))
    }
    pub fn label(&self, now: Instant, paused: bool) -> String {
        let elapsed = format_duration(self.elapsed(now));
        if self.finished {
            return format!("Active time {elapsed}");
        }
        if self.completed >= self.total {
            return format!("Elapsed {elapsed} · Finishing…");
        }
        let remaining = self.remaining(now);
        let remaining = if remaining.is_zero() {
            "Updating estimate…".to_owned()
        } else {
            format!("~{} remaining", format_duration(remaining))
        };
        format!(
            "{} {elapsed} · {remaining}{}",
            if paused {
                "Paused · active time"
            } else {
                "Elapsed"
            },
            if self.completed == 0 {
                " · initial estimate"
            } else {
                ""
            },
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sdk_fraction_and_long_duration_estimates() {
        assert_eq!(shutter_seconds((15 << 16) | 10), Some(1.5));
        assert_eq!(shutter_seconds((1 << 16) | 1000), Some(0.001));
        for invalid in [0, u64::from(u32::MAX), 1 << 16, 10, u64::MAX] {
            assert_eq!(shutter_seconds(invalid), None);
        }
        assert_eq!(
            initial_cycle((1 << 16) | 2, 500),
            Some(Duration::from_secs(2))
        );
        assert_eq!(
            format_duration(Duration::from_millis(3_600_001)),
            "1h 00m 01s"
        );
    }

    #[test]
    fn observed_cadence_excludes_approach_and_pauses() {
        let t = Instant::now();
        let seconds = Duration::from_secs;
        let mut run = RunTiming::new(5, seconds(4), seconds(2), t);
        assert_eq!(run.remaining(t), seconds(22));
        run.approached(t + seconds(2));
        run.complete_cycle(t + seconds(12)); // Actual 10 s cycle replaces 4 s guess.
        assert_eq!(run.remaining(t + seconds(12)), seconds(40));
        run.pause(t + seconds(15));
        assert_eq!(run.elapsed(t + seconds(115)), seconds(15));
        assert_eq!(run.remaining(t + seconds(115)), seconds(37));
        run.resume(t + seconds(115));
        run.complete_cycle(t + seconds(122));
        assert_eq!(run.elapsed(t + seconds(122)), seconds(22));
        assert_eq!(run.remaining(t + seconds(122)), seconds(30));
        run.finish(t + seconds(125));
        assert_eq!(run.elapsed(t + seconds(225)), seconds(25));
        run.resume(t + seconds(225));
        assert_eq!(run.elapsed(t + seconds(325)), seconds(25));
    }

    #[test]
    fn overrun_never_claims_completion_and_final_cycle_is_zero() {
        let t = Instant::now();
        let mut run = RunTiming::new(1, Duration::from_secs(1), Duration::ZERO, t);
        run.approached(t);
        assert!(
            run.label(t + Duration::from_secs(20), false)
                .contains("Updating estimate")
        );
        run.complete_cycle(t + Duration::from_secs(21));
        assert!(run.remaining(t + Duration::from_secs(21)).is_zero());
        assert!(
            run.label(t + Duration::from_secs(21), false)
                .contains("Finishing")
        );
        run.finish(t + Duration::from_secs(22));
        assert_eq!(
            run.label(t + Duration::from_secs(99), false),
            "Active time 0m 22s"
        );
    }
}
