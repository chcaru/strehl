use super::*;

fn outputs() -> Vec<OutputTensor> {
    HEADS
        .iter()
        .enumerate()
        .map(|(i, (_, shape))| OutputTensor {
            shape: shape.to_vec(),
            values: vec![if i == 0 || i == 5 { 1.0 } else { 0.25 }; shape.iter().product()],
        })
        .collect()
}

#[test]
fn input_is_exact_fp32_and_hashes_little_endian_bits() {
    let mut values = vec![0.0; INPUT_VALUES];
    values[0] = -0.0;
    values[5] = 0.125;
    values[INPUT_VALUES - 1] = 1.0;
    let bytes: Vec<u8> = values.iter().flat_map(|v: &f32| v.to_le_bytes()).collect();
    let a = PreparedInput::from_values(values).unwrap();
    let b = PreparedInput::from_le_bytes(&bytes).unwrap();
    assert_eq!(a.digest(), sha256(&bytes));
    assert_eq!(a.digest(), b.digest());
    assert_eq!(a.values()[0].to_bits(), (-0.0f32).to_bits());
    assert_eq!(a.values()[5], 0.125);
}

#[test]
fn input_rejects_length_nonfinite_and_out_of_range() {
    assert!(PreparedInput::from_values(vec![0.0; INPUT_VALUES - 1]).is_err());
    assert!(PreparedInput::from_le_bytes(&[0; 3]).is_err());
    for bad in [f32::NAN, f32::INFINITY, -0.001, 1.001] {
        let mut values = vec![0.5; INPUT_VALUES];
        values[INPUT_VALUES - 1] = bad;
        assert!(PreparedInput::from_values(values).is_err());
        let mut bytes = vec![0; INPUT_VALUES * 4];
        bytes[INPUT_VALUES * 4 - 4..].copy_from_slice(&bad.to_le_bytes());
        assert!(PreparedInput::from_le_bytes(&bytes).is_err());
    }
}

#[test]
fn raw_fields_retain_bits_and_do_not_interpret_scalar_units() {
    let mut data = outputs();
    data[4].values[0] = -123.75;
    data[9].values[0] = f32::MAX;
    data[1].values[1] = -0.0;
    let expected = sha256(&(-123.75f32).to_le_bytes());
    let result = RawFields::validate(data).unwrap();
    assert_eq!(result.values(4).unwrap(), &[-123.75]);
    assert_eq!(result.values(9).unwrap(), &[f32::MAX]);
    assert_eq!(result.values(1).unwrap()[1].to_bits(), (-0.0f32).to_bits());
    assert_eq!(result.digests()[4], expected);
    assert!(result.values(10).is_none());
}

#[test]
fn every_head_rejects_nonfinite_and_malformed_extent() {
    for slot in 0..HEADS.len() {
        let mut a = outputs();
        a[slot].values[0] = f32::NAN;
        assert!(RawFields::validate(a).is_err(), "nonfinite slot {slot}");
        let mut b = outputs();
        b[slot].shape.push(1);
        assert!(RawFields::validate(b).is_err(), "shape slot {slot}");
        let mut c = outputs();
        c[slot].values.pop();
        assert!(RawFields::validate(c).is_err(), "length slot {slot}");
    }
    let mut missing = outputs();
    missing.pop();
    assert!(RawFields::validate(missing).is_err());
    assert!(RawFields::validate(Vec::new()).is_err());
}

#[test]
fn gains_and_luts_enforce_declared_numerical_ranges() {
    for slot in [0, 5] {
        for bad in [0.0, -1.0, f32::INFINITY] {
            let mut data = outputs();
            data[slot].values[17] = bad;
            assert!(RawFields::validate(data).is_err());
        }
    }
    for slot in [1, 2, 3, 6, 7, 8] {
        for bad in [-0.001, 1.001] {
            let mut data = outputs();
            data[slot].values[17] = bad;
            assert!(RawFields::validate(data).is_err());
        }
    }
}
