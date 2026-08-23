//! Probes of workstream E §F5.3's own sketch, run against a compiler.
//!
//! §F5.3 option A gives this as the calibration routine:
//!
//! ```text
//! fn calibrate(op: &dyn FocusMeasure, cfg: &FieldConfig) -> f32 {
//!     let field = cfg.run(op, &unit_noise_plane(512, 512), &unit_sigma_model());
//!     interior_sd(&field, cfg.support_radius())
//! }
//! ```
//!
//! Two things in those two lines are wrong, and this example measures how
//! wrong. Nothing here asserts; it prints, so that the report quotes numbers
//! rather than opinions.
//!
//! ```text
//! cargo run -p strehl-plugin --release --example f5-design-probes
//! ```

use strehl_core::focus::{SUPPORT_RADIUS, WINDOW_RADIUS};
use strehl_core::merge::FOCUS_NOISE_SD;
use strehl_core::plane::PlaneGeometry;
use strehl_plugin::reference::{SumModifiedLaplacian, Tenengrad};
use strehl_plugin::{
    CalibrationPlan, FieldConfig, FieldWorkspace, FocusMeasure, NoiseSource, calibrate,
    unit_sigma_model,
};

/// Interior mean and sample SD at an arbitrary margin, so the sketch's margin
/// can be compared against the correct one on the same field.
fn interior_sd_at(field: &[f32], g: PlaneGeometry, margin: usize) -> (f64, usize) {
    let mut v = Vec::new();
    for y in margin..g.height - margin {
        for x in margin..g.width - margin {
            v.push(f64::from(field[y * g.width + x]));
        }
    }
    let mean = v.iter().sum::<f64>() / v.len() as f64;
    let var = v.iter().map(|q| (q - mean).powi(2)).sum::<f64>() / (v.len() - 1) as f64;
    (var.sqrt(), v.len())
}

fn probe_margin(op: &dyn FocusMeasure, label: &str) {
    let cfg = FieldConfig::SHIPPED;
    let g = PlaneGeometry {
        width: 512,
        height: 512,
    };
    let noise = unit_sigma_model();
    let mut ws = FieldWorkspace::new(g);
    let mut plane = vec![0.0f32; g.pixels()];

    let correct = cfg.calibration_margin(op);
    let sketch = op.support_radius(); // what §F5.3 passes: cfg.support_radius()

    let (mut c_acc, mut s_acc, mut z_acc) = (0.0f64, 0.0f64, 0.0f64);
    let seeds = CalibrationPlan::host_default().seeds;
    for &s in &seeds {
        NoiseSource::SplitMixBoxMuller.fill(s, &mut plane);
        let field = ws.run(op, cfg, &plane, &noise);
        c_acc += interior_sd_at(field, g, correct).0;
        s_acc += interior_sd_at(field, g, sketch).0;
        z_acc += interior_sd_at(field, g, 0).0;
    }
    let n = seeds.len() as f64;
    let (c, s, z) = (c_acc / n, s_acc / n, z_acc / n);
    println!(
        "  {label:<10} margin {correct:>2} (correct) -> {c:.6e}   \
         margin {sketch:>2} (F5.3 sketch) -> {s:.6e}  [{:+.2}%]   \
         margin  0 -> {z:.6e}  [{:+.2}%]",
        (s / c - 1.0) * 100.0,
        (z / c - 1.0) * 100.0
    );
}

fn main() {
    println!(
        "PROBE 1 -- the margin. §F5.3 discards `cfg.support_radius()` from every edge.\n\
         That is the OPERATOR's support ({SUPPORT_RADIUS} for the shipped one). The host \
         regulariser\nadds {} more, and the box filters are replicate-clamped, so the \
         band between\nthe two margins is not stationary and must not be in the sample.\n",
        FieldConfig::SHIPPED.regulariser_radius()
    );
    probe_margin(&Tenengrad::shipped(), "tenengrad");
    probe_margin(&SumModifiedLaplacian::at_radius(WINDOW_RADIUS), "sml");

    println!(
        "\nPROBE 2 -- determinism. §F5.3's sketch calls `unit_noise_plane(512, 512)`\n\
         with no seed and takes ONE plane. Below: the constant this yields for the\n\
         shipped operator on 12 different single planes.\n"
    );
    let cfg = FieldConfig::SHIPPED;
    let op = Tenengrad::shipped();

    // First: what this crate's calibrator does when handed the sketch's plan.
    let one = CalibrationPlan {
        side: 512,
        seeds: vec![0xC0FFEE],
        source: NoiseSource::SplitMixBoxMuller,
    };
    match calibrate(&op, cfg, &one) {
        Ok(c) => println!("  one seed accepted, sd {:e}", c.response_sd()),
        Err(e) => println!("  calibrate() with one plane is REFUSED: {e}"),
    }

    // Then the numbers it refuses to report, measured directly.
    let g = PlaneGeometry {
        width: 512,
        height: 512,
    };
    let noise = unit_sigma_model();
    let mut ws = FieldWorkspace::new(g);
    let mut plane = vec![0.0f32; g.pixels()];
    let margin = cfg.calibration_margin(&op);
    let mut singles = Vec::new();
    for &s in &CalibrationPlan::host_default().seeds {
        NoiseSource::SplitMixBoxMuller.fill(s, &mut plane);
        let field = ws.run(&op, cfg, &plane, &noise);
        singles.push(interior_sd_at(field, g, margin).0);
    }
    let m = singles.iter().sum::<f64>() / singles.len() as f64;
    let sd =
        (singles.iter().map(|q| (q - m).powi(2)).sum::<f64>() / (singles.len() - 1) as f64).sqrt();
    let lo = singles.iter().cloned().fold(f64::INFINITY, f64::min);
    let hi = singles.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    println!(
        "  single-plane constants: mean {m:.6e}  sd {sd:.3e} ({:.2}% of the mean)\n\
         \x20 min {lo:.6e}  max {hi:.6e}  spread {:.2}% of the mean\n\
         \x20 crate constant {FOCUS_NOISE_SD:e}",
        sd / m * 100.0,
        (hi - lo) / m * 100.0
    );
    println!(
        "  => two hosts, or two runs of one host, would compute gates differing by\n\
         \x20    up to {:.2}%. That is non-determinism in registration, which is exactly\n\
         \x20    what §F4's P1 (confluence) forbids.",
        (hi - lo) / m * 100.0
    );

    println!(
        "\nPROBE 3 -- cost. Fact 505's ~1.7 ms per stage was a DERIVED BOUND and it is\n\
         REFUTED: fact 525 measured 5.02 ms per 512^2 plane and 60.3 ms per registration,\n\
         2.95x and 35x the bound, and fact 505's own row says the figure must not be\n\
         quoted. Its CONCLUSION stands -- 60 ms once per operator per host start is not a\n\
         cost worth trading a correctness property for. Compare the numbers below against\n\
         fact 525's 5.02 / 60.3, NOT against 1.7: a run that beats the bound would mean\n\
         this probe had stopped measuring what fact 525 measured.\n"
    );
    for (label, op) in [
        (
            "tenengrad",
            Box::new(Tenengrad::shipped()) as Box<dyn FocusMeasure>,
        ),
        (
            "sml",
            Box::new(SumModifiedLaplacian::at_radius(WINDOW_RADIUS)) as Box<dyn FocusMeasure>,
        ),
    ] {
        let plan = CalibrationPlan::host_default();
        let t0 = std::time::Instant::now();
        let c = calibrate(op.as_ref(), cfg, &plan).expect("calibrates");
        let total = t0.elapsed().as_secs_f64() * 1e3;
        println!(
            "  {label:<10} {:>6.2} ms total for {} seeds = {:>5.2} ms/plane; \
             relative sem {:.3}%",
            total,
            plan.seeds.len(),
            total / plan.seeds.len() as f64,
            c.relative_sem() * 100.0
        );
    }
}
