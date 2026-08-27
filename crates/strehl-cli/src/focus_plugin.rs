//! The seam that makes `strehl-plugin` reachable from the shipping binary.
//!
//! # What was wrong
//!
//! `crates/strehl-plugin` is 3,282 lines of contribution surface whose central
//! idea is that [`FocusMeasure`](strehl_plugin::measure::FocusMeasure) has no
//! method reporting a noise standard deviation: the **host** measures it at
//! registration, so an operator carrying a wrong constant is unrepresentable
//! rather than merely detectable. Facts 583, 632 and 662 record that
//! `strehl-cli` did not depend on the crate at all. A contributor could write
//! an operator, register it, have it correctly calibrated -- and `strehl stack`
//! would never call it. That is the project's *headline* architectural
//! requirement ("pluggable by design") going unmet by a dependency edge.
//!
//! This module is that edge. It is deliberately thin: everything interesting
//! stays in `strehl-plugin`, and the only judgement made here is the mapping
//! from a command-line string to a registered operator.
//!
//! # What `--focus` costs, and why it is not free
//!
//! Registration **calibrates**, and calibration is a measurement, not a table
//! lookup: [`CalibrationPlan::host_default`] draws 12 seeds of a 512x512 noise
//! plane per operator and runs the operator over each. That is roughly 60 ms
//! per operator on this machine, so building the whole seven-operator registry
//! costs about half a second. The registry is therefore built **lazily** and
//! only when a focus-plugin surface is actually used -- the default path never
//! constructs one, never draws a seed, and never pays the millisecond.
//!
//! That laziness is also what protects the byte-freezes. If the default path
//! touched the calibrator, the default constant would become a *measured*
//! quantity, and the measured Tenengrad SD is `1.521126e-2` against the
//! compiled-in `1.5214e-2` -- close (`k` = 0.9998) but **not equal**. Fact 631
//! is the standing reason that "close" is not good enough to substitute:
//! rescaling a gate does not reproduce another operator's decisions, so `t/k`
//! prices a miscalibration and must never be used to undo one. The default
//! keeps its own constant, bit-for-bit; `--focus` gets the measured one.

use std::sync::Arc;

use anyhow::{Context, Result, anyhow, bail};

use strehl_core::focus::{FieldConfig, FocusMeasure, window_radius};
use strehl_plugin::calibrate::CalibrationPlan;
use strehl_plugin::reference::survey;
use strehl_plugin::registry::{Registered, Registry};

/// Build the reference registry, **measuring** every operator on the way in.
///
/// The seven operators are exactly [`strehl_plugin::reference::survey`] at the
/// host window radius -- resolved through [`window_radius`] rather than the
/// `WINDOW_RADIUS` constant, so that `STREHL_WINDOW_RADIUS` moves the plugin
/// operators and the shipped one together. It was not always so: before
/// BUILD-PLUGIN the plugin crate's `Tenengrad::shipped()` read the constant
/// while `FocusField::compute` called `window_radius()`, which made the crate's
/// bit-identity claim silently conditional on that variable being unset.
///
/// # Errors
///
/// If the calibrator's own self-check fails, or if any operator is refused --
/// a degenerate operator (constant response, non-finite response) is an error
/// here rather than an entry with a plausible-looking constant beside it.
pub fn reference_registry() -> Result<Registry> {
    let mut registry = Registry::new(FieldConfig::SHIPPED, CalibrationPlan::host_default())
        .map_err(|e| anyhow!("focus plugin calibrator failed its own self-check: {e}"))?;
    for op in survey(window_radius()) {
        let id = op.id().to_string();
        let arc: Arc<dyn FocusMeasure> = Arc::from(op);
        registry
            .register(arc)
            .with_context(|| format!("registering focus operator `{id}`"))?;
    }
    Ok(registry)
}

/// Resolve a `--focus` name against the registry, or explain what was on offer.
///
/// # Errors
///
/// On an unknown name. The message lists the registered ids, because the
/// failure this whole module exists to prevent is a flag that is accepted and
/// silently ignored -- and a typo that fell back to the default would be
/// exactly that failure wearing a different hat.
pub fn resolve<'r>(registry: &'r Registry, name: &str) -> Result<&'r Registered> {
    registry.get(name).ok_or_else(|| {
        anyhow!(
            "unknown focus operator `{name}`; registered: {}\n\
             (run `strehl focus list` for their host-measured noise scales)",
            registry.ids().join(", ")
        )
    })
}

/// The id of the operator the default path runs.
///
/// Naming it is not decoration. `--focus tenengrad-w13` and the default are
/// **not** the same computation even though they are the same operator: the
/// default uses the compiled-in `FOCUS_NOISE_SD`, the flag uses the measured
/// one, and they differ in the fourth significant figure. A user who wants the
/// default must omit the flag; a user who passes the default's name explicitly
/// is asking for the measured constant and gets it.
#[must_use]
pub fn shipped_id() -> String {
    format!("tenengrad-w{}", window_radius())
}

/// `strehl focus list` -- every registered operator with its measured scale.
///
/// # Errors
///
/// If the registry cannot be built.
pub fn list(gate: f32) -> Result<()> {
    if !(gate > 0.0 && gate.is_finite()) {
        bail!("gate must be finite and positive for the tolerance column, got {gate}");
    }
    let registry = reference_registry()?;
    let plan = registry.plan();
    let shipped = shipped_id();

    println!(
        "focus operators, calibrated by the host at registration \
         ({} seeds x {}x{} plane, margin {} px)",
        plan.seeds.len(),
        plan.side,
        plan.side,
        registry
            .get(&shipped)
            .map_or(0, |r| r.calibration().margin())
    );
    println!(
        "the noise sd is MEASURED here, not declared by the operator: \
         `FocusMeasure` has no method that could declare it"
    );
    println!();
    println!(
        "{:<24} {:>14} {:>12} {:>9} {:>14} {:>6}",
        "id", "noise sd", "rel sem", "k", &format!("tol @ gate {gate}"), "halo"
    );
    for id in registry.ids() {
        let entry = registry
            .get(id)
            .expect("id came from this registry's own list");
        let cal = entry.calibration();
        let marker = if id == shipped { "  <- default" } else { "" };
        println!(
            "{:<24} {:>14.6e} {:>11.3}% {:>9.4} {:>14.6e} {:>6}{}",
            id,
            cal.response_sd(),
            100.0 * cal.relative_sem(),
            cal.k_against_host_constant(),
            entry.unnormalised_tolerance(gate),
            entry.plugin_halo(),
            marker
        );
    }
    println!();
    println!(
        "`k` is the ratio of the host's compiled-in FOCUS_NOISE_SD to the \
         measured scale. Fact 631: k PRICES a miscalibration, it does not undo \
         one -- two operators at the same gate disagree on the winner over up \
         to 71.5% of pixels, and no rescaling of the gate recovers that."
    );
    Ok(())
}
