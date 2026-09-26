// Test-only access to the current same-level binomial filter; no production change.
use super::LevelSize;

pub fn smooth_membership(values: &[f32], size: LevelSize) -> Vec<f32> {
    assert!(size.width > 0 && size.height > 0 && values.len() == size.pixels());
    assert!(values.iter().all(|v| v.is_finite() && *v >= 0.0));
    let mut out = values.to_vec();
    let mut scratch = vec![0.0; size.pixels() + size.width];
    super::smooth5(&mut out, size, &mut scratch);
    // A constant is an exact fixed point of the mathematical normalized filter.
    // Preserve it literally instead of allowing summation rounding to perturb
    // stationary source preferences (including nondyadic memberships).
    if values.iter().all(|v| v.to_bits() == values[0].to_bits()) {
        out.copy_from_slice(values);
    }
    out
}
