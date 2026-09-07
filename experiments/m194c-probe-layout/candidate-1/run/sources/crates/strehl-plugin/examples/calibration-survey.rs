//! The fact-439 survey, re-measured by this crate's own calibrator.
//!
//! Prints the host-measured noise scale for each of the seven textbook focus
//! operators, and the effective gate a plugin would silently run at if it
//! inherited the host's compiled-in `FOCUS_NOISE_SD` instead of being measured.
//!
//! ```text
//! cargo run -p strehl-plugin --release --example calibration-survey
//! cargo run -p strehl-plugin --release --example calibration-survey -- reference
//! ```
//!
//! `reference` uses [`CalibrationPlan::reference`] (2048^2 x 8 seeds), the
//! configuration `experiments/m43-plugin-seam/02b-operator-noise-spread.py`
//! used. The default is [`CalibrationPlan::host_default`] (512^2 x 12 seeds),
//! the configuration a host would actually pay for at registration.

use std::time::Instant;

use strehl_core::focus::WINDOW_RADIUS;
use strehl_core::merge::FOCUS_NOISE_SD;
use strehl_plugin::{CalibrationPlan, FieldConfig, calibrate, reference::survey};

fn main() {
    let reference = std::env::args().any(|a| a == "reference");
    let plan = if reference {
        CalibrationPlan::reference()
    } else {
        CalibrationPlan::host_default()
    };
    let cfg = FieldConfig::SHIPPED;

    println!(
        "plan: {} x {} plane, {} seeds, {:?}",
        plan.side,
        plan.side,
        plan.seeds.len(),
        plan.source
    );
    println!(
        "config: operator -> own box window r{WINDOW_RADIUS} -> host regulariser r{}",
        cfg.regulariser_radius()
    );
    println!("host compiled-in FOCUS_NOISE_SD = {FOCUS_NOISE_SD:e}\n");
    println!(
        "{:<22} {:>12} {:>12} {:>8} {:>10} {:>9}",
        "operator", "measured sd", "sem", "k", "gate@1.0", "ms/seed"
    );
    println!("{}", "-".repeat(78));

    for op in survey(WINDOW_RADIUS) {
        let t0 = Instant::now();
        match calibrate(op.as_ref(), cfg, &plan) {
            Ok(c) => {
                let ms = t0.elapsed().as_secs_f64() * 1e3 / plan.seeds.len() as f64;
                let k = c.k_against_host_constant();
                println!(
                    "{:<22} {:>12.6e} {:>12.2e} {:>8.4} {:>10.4} {:>9.2}",
                    op.id(),
                    c.response_sd(),
                    c.sem(),
                    k,
                    1.0 / k,
                    ms
                );
            }
            Err(e) => println!("{:<22} REFUSED: {e}", op.id()),
        }
    }

    println!(
        "\nk is the measured scale divided by the host's compiled-in constant. \
         `gate@1.0` is\nthe effective gate an operator would run at if it \
         inherited that constant instead\nof being measured -- fact 438: nothing \
         in the log, the exit code or the\ncalibration block would change."
    );
}
