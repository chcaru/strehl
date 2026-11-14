//! Conservative admission: no assumed compression ratio or reclaimable files.
use anyhow::{Result, ensure};
use serde_json::Value;

pub const HEADROOM: u64 = 512 * 1024 * 1024;
// Codec framing is <= 13,328 bytes; also allow archive headers and receipts.
pub const PER_FILE_OVERHEAD: u64 = 64 * 1024;

pub fn raw_limit(status: &Value) -> u64 {
    status["raw_max_bytes"]
        .as_u64()
        .filter(|n| (1024..=crate::transport::MAX_RAW).contains(n))
        .unwrap_or(crate::transport::MAX_RAW)
}
pub fn required(frames: usize, raw_bytes: u64) -> Result<u64> {
    ensure!(
        frames > 0 && (1024..=crate::transport::MAX_RAW).contains(&raw_bytes),
        "Invalid storage estimate"
    );
    (frames as u64)
        .checked_mul(raw_bytes + PER_FILE_OVERHEAD)
        .and_then(|n| n.checked_add(HEADROOM))
        .ok_or_else(|| anyhow::anyhow!("Storage estimate overflow"))
}
pub fn check(free: Option<u64>, frames: usize, raw_bytes: u64) -> Result<u64> {
    let needed = required(frames, raw_bytes)?;
    let free =
        free.ok_or_else(|| anyhow::anyhow!("Cannot verify free space on the PC capture disk"))?;
    ensure!(
        free >= needed,
        "Stack needs up to {:.2} GB including headroom; only {:.2} GB is free. Shorten the stack or choose another disk",
        needed as f64 / 1e9,
        free as f64 / 1e9
    );
    Ok(needed)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn four_shots_and_incompressible_data_must_fit_before_capture() {
        let raw = crate::ptp::MEMBER_LIMIT;
        let single = required(900, raw).unwrap();
        let four = required(3600, raw).unwrap();
        assert_eq!(four - HEADROOM, 4 * (single - HEADROOM));
        assert!(check(Some(single), 3600, raw).is_err());
        assert!(check(Some(four - 1), 3600, raw).is_err());
        assert!(check(None, 3600, raw).is_err());
        assert_eq!(check(Some(four), 3600, raw).unwrap(), four);
    }
}
