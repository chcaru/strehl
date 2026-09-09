// Independent fixed M194b consumer evidence predicates; root executes.
use crate::align_cmd::DirectPlaneMode;

pub(super) fn assert_render_evidence(mode: DirectPlaneMode, observer: bool,
    actual_hits: usize, probe_hits: usize, input_captures: usize,
    collapsed_captures: usize, collapsed_values: usize) -> anyhow::Result<()> {
    if !observer {
        anyhow::ensure!(actual_hits == 0 && probe_hits == 0 && input_captures == 0
            && collapsed_captures == 0 && collapsed_values == 0,
            "observer-off placebo retained a counter or value capture");
        return Ok(());
    }
    anyhow::ensure!(input_captures == 9,
        "fixed nine-frame consumer must capture every consumed input exactly once");
    anyhow::ensure!(collapsed_captures == 1 && collapsed_values == 4 * 142 * 106,
        "fixed cropped four-plane consumer must capture one complete collapsed result");
    if mode == DirectPlaneMode::Off {
        anyhow::ensure!(actual_hits == 0 && probe_hits == 0,
            "original mode entered a direct actual/probe branch");
    } else {
        anyhow::ensure!(actual_hits > 0 && probe_hits > 0,
            "direct mode did not exercise BOTH actual-frame and synthetic-probe branches");
    }
    Ok(())
}
