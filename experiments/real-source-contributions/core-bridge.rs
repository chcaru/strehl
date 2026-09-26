// Read-only access to the actual cached decomposition and corrected accumulator.
// No independently reconstructed focus/noise/gather quantities are exposed.
use super::{AdmissionMode, BandMerge, BaseBand, Fallback, FrameWorkspace, Hull, SelectMode};

pub const NUMERATOR_SCALE: f32 = super::SOFT_NUMERATOR_SCALE;
pub fn supported(merge: &BandMerge) {
    assert!(merge.planes == 4 && merge.cfg.select == SelectMode::SoftPower
        && merge.cfg.fallback == Fallback::Mean && merge.cfg.base == BaseBand::Mean
        && merge.cfg.hull == Hull::InputRange && merge.cfg.admission == AdmissionMode::HardFloor);
}
pub fn coefficients(ws: &FrameWorkspace, k: usize) -> [&[f32]; 4] {
    assert!(ws.plane.valid && ws.plane.pyramids.len() == 4);
    std::array::from_fn(|c| ws.plane.pyramids[c].level(k))
}
/// den, corrected scaled num[4], unweighted sum[4], resolved coefficient[4].
pub fn state(merge: &BandMerge, k: usize, j: usize) -> [f32; 13] {
    supported(merge);
    assert!(merge.frames > 0);
    let d = merge.den[k][j];
    let mut out = [0.0; 13];
    out[0] = d;
    for c in 0..4 {
        let n = merge.num[k * 4 + c][j];
        let u = merge.usum[k * 4 + c][j];
        out[1 + c] = n;
        out[5 + c] = u;
        out[9 + c] = if d > 0.0 { super::resolve_soft_numerator(n,d) }
            else { u * (1.0 / merge.frames as f32) };
    }
    out
}
pub fn hull(merge: &BandMerge, j: usize) -> [[f32; 2]; 4] {
    supported(merge);
    std::array::from_fn(|c| [merge.lo[c][j],merge.hi[c][j]])
}
