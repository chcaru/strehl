// Same source field; only the explicitly bounded source capacity is extended.
use super::*;
include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/chip-shared-source-observation/costs.rs"));

pub(crate) fn scalar_volume_pair_bytes(width:usize,height:usize,frames:usize)->Result<usize> {
    volume_len(width,height,frames)?.checked_mul(std::mem::size_of::<f32>())
        .and_then(|bytes|bytes.checked_mul(2)).context("paired scalar volume byte overflow")
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/chip-shared-source-observation/independent-controls.rs"));
}
mod full {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/chip-shared-source-observation/full-adapter.rs"));
}
