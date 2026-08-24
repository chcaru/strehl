//! M93 — gating the focus election.
//!
//! `robust.rs` is included by path rather than as `strehl_core::robust`,
//! because wiring it into `lib.rs` is a shared registration point that belongs
//! to the orchestrator (discipline 588; M85 committing M86's `pub mod align;`
//! line is the recorded near-miss). The module is written with no `crate::`
//! references so that the two inclusion routes are equivalent, and the wiring
//! patch is given verbatim in `docs/research/M93-election-gate.md` §10.
#[path = "../../strehl-core/src/robust.rs"]
mod robust;

fn main() -> anyhow::Result<()> {
    println!("m93-election: placeholder");
    let _ = robust::weight(0.0);
    Ok(())
}
