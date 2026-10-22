use super::*;
use crate::learned_profile::IDENTITY_MATRIX;

fn table_data(permutation: [usize; 3]) -> Vec<f32> {
    let mut values = Vec::new();
    for c in permutation {
        for r in 0..2 {
            for g in 0..2 {
                for b in 0..2 {
                    values.push([r, g, b][c] as f32);
                }
            }
        }
    }
    values
}

fn fixture() -> (FrozenProfileDescriptor, FrozenProfileData) {
    let table = TableDescriptor {
        size: 2,
        source_to_table: [[1., 0.2, 0.], [0., 1., 0.], [0., 0., 1.]],
        encoding: TableEncoding::Power { gamma: 2.2 },
        gamut_extension: true,
    };
    (
        FrozenProfileDescriptor {
            identities: AssetIdentities {
                contract_id: "strehl/test-contract-v1".into(),
                contract_sha256: [1; 32],
                model_sha256: [2; 32],
                input_sha256: [3; 32],
                source_sha256: [4; 32],
            },
            origin: ProfileOrigin {
                full_size: [800, 600],
                region: Some(RegionOrigin {
                    id: "insect wing".into(),
                    bounds: [200, 150, 600, 450],
                }),
            },
            gain: GainDescriptor {
                dimensions: [2, 2, 2],
                origin_yx: [0., 0.],
                spacing_yx: [1., 1.],
                input_weights: [0.2, 0.5, 0.1, 0.1, 0.1],
                gamma: 1.3,
            },
            tables: [
                Some(table),
                None,
                Some(TableDescriptor {
                    size: 2,
                    source_to_table: IDENTITY_MATRIX,
                    encoding: TableEncoding::Srgb,
                    gamut_extension: true,
                }),
            ],
            linear_709_to_rimm: [[1., 0.1, 0.], [0., 1., 0.], [0., 0., 1.]],
            pre_gain_scale: 0.9,
            tone_curve: ToneDescriptor::PiecewiseLinear {
                knots: vec![[0., 0.], [0.5, 0.4], [1., 1.]],
            },
            masks: [
                Some(MaskDescriptor {
                    size: [2, 2],
                    origin_xy: [0.25, 0.25],
                    extent_xy: [0.5, 0.5],
                }),
                Some(MaskDescriptor {
                    size: [1, 1],
                    origin_xy: [0., 0.],
                    extent_xy: [1., 1.],
                }),
            ],
        },
        FrozenProfileData {
            gain: vec![0.8, 0.9, 1., 1.1, 1.2, 1.3, 1.4, 1.5],
            tables: [
                Some(table_data([2, 0, 1])),
                None,
                Some(table_data([0, 1, 2])),
            ],
            masks: [Some(vec![0., 0.4, 0.6, 1.]), Some(vec![0.25])],
        },
    )
}

fn asset() -> FrozenLearnedAsset {
    let (descriptor, data) = fixture();
    FrozenLearnedAsset::freeze(descriptor, data).unwrap()
}

fn error(bytes: &[u8]) -> String {
    FrozenLearnedAsset::decode(bytes)
        .err()
        .expect("invalid asset accepted")
        .to_string()
}

fn resign(bytes: &mut [u8]) {
    let digest_at = bytes.len() - 32;
    let digest = Sha256::digest(&bytes[..digest_at]);
    bytes[digest_at..].copy_from_slice(&digest);
}

fn payload_offset(bytes: &[u8]) -> usize {
    20 + u32::from_le_bytes(bytes[12..16].try_into().unwrap()) as usize
}

// Construct an envelope independently of the production encoder so malformed
// but correctly hashed metadata reaches semantic validation, not only SHA-256.
fn replace_header(bytes: &[u8], header: &[u8]) -> Vec<u8> {
    let mut result = bytes[..20].to_vec();
    result[12..16].copy_from_slice(&(header.len() as u32).to_le_bytes());
    result.extend_from_slice(header);
    result.extend_from_slice(&bytes[payload_offset(bytes)..bytes.len() - 32]);
    result.extend_from_slice(&[0; 32]);
    resign(&mut result);
    result
}

#[test]
fn reopen_retains_content_identity_and_pixel_results() {
    let original = asset();
    let bytes = original.encode().unwrap();
    assert_eq!(&bytes[..8], b"STRHLPF\0");
    assert_eq!(&bytes[8..12], &[1, 0, 0, 0]);
    assert_eq!(bytes.len(), original.encoded_len());
    assert_eq!(original.content_id().len(), 64);
    let reopened = FrozenLearnedAsset::decode(&bytes).unwrap();
    assert_eq!(original.digest(), reopened.digest());
    assert_eq!(original.descriptor(), reopened.descriptor());
    assert_eq!(bytes, reopened.encode().unwrap());
    assert!(Arc::ptr_eq(
        &original.prepared(),
        &original.clone().prepared()
    ));
    let before = original.prepared();
    let after = reopened.prepared();
    let mut saw_nonidentity = false;
    let mut saw_spatial_difference = false;
    let mut previous = None;
    for uv in [[0.1, 0.2], [0.375, 0.375], [0.5, 0.5], [0.9, 0.8]] {
        let weights = original.semantic_weights(uv).unwrap();
        assert_eq!(weights, reopened.semantic_weights(uv).unwrap());
        let spatial = before
            .apply_pixel([0.2, 0.4, 0.7], uv, weights, 1.)
            .unwrap();
        saw_spatial_difference |= previous.is_some_and(|old| old != spatial);
        previous = Some(spatial);
        for pixel in [[-0.1, 0.35, 1.2], [0.2, 0.4, 0.7]] {
            let first = before.apply_pixel(pixel, uv, weights, 1.).unwrap();
            let second = after.apply_pixel(pixel, uv, weights, 1.).unwrap();
            assert_eq!(first.map(f32::to_bits), second.map(f32::to_bits));
            saw_nonidentity |= first != pixel;
        }
    }
    assert!(saw_nonidentity, "fixture must exercise an actual treatment");
    assert!(
        saw_spatial_difference,
        "fixture must exercise varying fields"
    );
}

#[test]
fn float_payload_retains_signed_zero_and_subnormal_bits() {
    let (mut descriptor, mut data) = fixture();
    descriptor.gain.origin_yx[0] = -0.;
    data.gain[0] = -0.;
    data.gain[1] = f32::from_bits(1);
    data.tables[0].as_mut().unwrap()[0] = -0.;
    data.tables[0].as_mut().unwrap()[1] = f32::from_bits(2);
    data.masks[0].as_mut().unwrap()[0] = -0.;
    data.masks[0].as_mut().unwrap()[1] = f32::from_bits(3);
    let frozen = FrozenLearnedAsset::freeze(descriptor, data).unwrap();
    let bytes = frozen.encode().unwrap();
    let payload = payload_offset(&bytes);
    for (index, bits) in [
        (0, 0x80000000u32),
        (1, 1),
        (8, 0x80000000),
        (9, 2),
        (56, 0x80000000),
        (57, 3),
    ] {
        assert_eq!(
            &bytes[payload + index * 4..payload + (index + 1) * 4],
            &bits.to_le_bytes()
        );
    }
    let reopened = FrozenLearnedAsset::decode(&bytes).unwrap();
    assert_eq!(
        reopened.descriptor().gain.origin_yx[0].to_bits(),
        (-0.0f32).to_bits()
    );
    assert_eq!(bytes, reopened.encode().unwrap());
    let input = [-0., -0.1, 2.4];
    assert_eq!(
        reopened
            .prepared()
            .apply_pixel(input, [0.5; 2], [0.; 2], 0.)
            .unwrap()
            .map(f32::to_bits),
        input.map(f32::to_bits)
    );
}

#[test]
fn identities_are_bound_to_the_content_without_claiming_authentication() {
    let original = asset();
    assert!(original.matches_source([4; 32], [800, 600]));
    assert!(!original.matches_source([5; 32], [800, 600]));
    assert!(!original.matches_source([4; 32], [600, 800]));
    for slot in 0..4 {
        let (mut descriptor, data) = fixture();
        let identities = &mut descriptor.identities;
        match slot {
            0 => identities.contract_sha256[0] ^= 1,
            1 => identities.model_sha256[0] ^= 1,
            2 => identities.input_sha256[0] ^= 1,
            _ => identities.source_sha256[0] ^= 1,
        }
        let changed = FrozenLearnedAsset::freeze(descriptor, data).unwrap();
        assert_ne!(original.digest(), changed.digest());
        // Metadata is provenance, not an implicit rendering transform.
        let render = |a: &FrozenLearnedAsset| {
            a.prepared()
                .apply_pixel([0.2, 0.4, 0.6], [0.5; 2], [0.2, 0.3], 1.)
                .unwrap()
        };
        assert_eq!(render(&original), render(&changed));
    }
}

#[test]
fn semantic_planes_use_full_image_coordinates_and_pixel_centers() {
    let frozen = asset();
    for (uv, expected) in [
        ([0.375, 0.375], 0.),
        ([0.625, 0.375], 0.4),
        ([0.375, 0.625], 0.6),
        ([0.625, 0.625], 1.),
        ([0.5, 0.5], 0.5),
        ([0.1, 0.5], 0.),
        ([0.75, 0.75], 1.),
    ] {
        let weights = frozen.semantic_weights(uv).unwrap();
        assert!((weights[0] - expected).abs() < 1e-6, "{uv:?}: {weights:?}");
        assert_eq!(weights[1], 0.25);
    }
    // Clearing the provenance ROI must not rebase masks to different pixels.
    let (mut descriptor, data) = fixture();
    descriptor.origin.region = None;
    let whole = FrozenLearnedAsset::freeze(descriptor, data).unwrap();
    assert_eq!(
        frozen.semantic_weights([0.625, 0.375]).unwrap(),
        whole.semantic_weights([0.625, 0.375]).unwrap()
    );
    for uv in [
        [f32::NAN, 0.5],
        [-0.1, 0.5],
        [0.5, 1.1],
        [0., f32::INFINITY],
    ] {
        assert!(frozen.semantic_weights(uv).is_err());
    }
}

#[test]
fn absent_tables_and_masks_reopen_without_implicit_defaults() {
    let (mut descriptor, mut data) = fixture();
    descriptor.tables = [None, None, None];
    descriptor.masks = [None, None];
    descriptor.tone_curve = ToneDescriptor::Identity;
    data.tables = [None, None, None];
    data.masks = [None, None];
    let frozen = FrozenLearnedAsset::freeze(descriptor, data).unwrap();
    let reopened = FrozenLearnedAsset::decode(&frozen.encode().unwrap()).unwrap();
    assert_eq!(reopened.semantic_weights([0.5; 2]).unwrap(), [0.; 2]);
    assert_eq!(reopened.descriptor(), frozen.descriptor());
}

#[test]
fn corruption_at_each_envelope_layer_is_rejected() {
    let bytes = asset().encode().unwrap();
    for index in [20, payload_offset(&bytes), bytes.len() - 1] {
        let mut bad = bytes.clone();
        bad[index] ^= 1;
        assert!(error(&bad).contains("digest"));
    }
    for boundary in [
        0,
        7,
        19,
        20,
        payload_offset(&bytes) - 1,
        payload_offset(&bytes),
        bytes.len() - 32,
        bytes.len() - 1,
    ] {
        assert!(
            FrozenLearnedAsset::decode(&bytes[..boundary]).is_err(),
            "accepted truncation at {boundary}"
        );
    }
    let mut trailing = bytes.clone();
    trailing.push(0);
    assert!(error(&trailing).contains("length"));
    let mut magic = bytes;
    magic[0] ^= 1;
    resign(&mut magic);
    assert!(error(&magic).contains("magic"));
}

#[test]
fn unsupported_versions_flags_and_declared_sizes_fail_with_valid_digests() {
    let bytes = asset().encode().unwrap();
    for (offset, replacement, expected) in [
        (8, vec![2, 0], "version"),
        (10, vec![1, 0], "flags"),
        (
            12,
            (MAX_HEADER_BYTES as u32 + 1).to_le_bytes().to_vec(),
            "bounds",
        ),
        (16, u32::MAX.to_le_bytes().to_vec(), "bounds"),
        (16, 0u32.to_le_bytes().to_vec(), "length"),
    ] {
        let mut bad = bytes.clone();
        bad[offset..offset + replacement.len()].copy_from_slice(&replacement);
        resign(&mut bad);
        assert!(error(&bad).contains(expected), "expected {expected}");
    }
}

#[test]
fn correctly_hashed_invalid_float_data_is_rejected() {
    let bytes = asset().encode().unwrap();
    let payload = payload_offset(&bytes);
    for (index, value) in [
        (0, -0.01),
        (0, f32::NAN),
        (0, f32::INFINITY),
        (8, 1.01),
        (8, -0.01),
        (56, -0.01),
        (56, 1.01),
        (56, f32::NEG_INFINITY),
    ] {
        let mut bad = bytes.clone();
        bad[payload + index * 4..payload + (index + 1) * 4].copy_from_slice(&value.to_le_bytes());
        resign(&mut bad);
        assert!(
            error(&bad).contains("field value"),
            "accepted index {index}, value {value}"
        );
    }
}

#[test]
fn correctly_hashed_descriptor_count_and_canonical_encoding_are_required() {
    let frozen = asset();
    let bytes = frozen.encode().unwrap();
    let mut descriptor = frozen.descriptor().clone();
    descriptor.gain.dimensions = [1, 2, 2];
    let mismatch = replace_header(&bytes, &serde_json::to_vec(&descriptor).unwrap());
    assert!(error(&mismatch).contains("payload size"));
    let pretty = replace_header(
        &bytes,
        &serde_json::to_vec_pretty(frozen.descriptor()).unwrap(),
    );
    assert!(error(&pretty).contains("Noncanonical"));
    let mut value = serde_json::to_value(frozen.descriptor()).unwrap();
    value
        .as_object_mut()
        .unwrap()
        .insert("implicit_exposure".into(), serde_json::json!(1));
    assert!(
        error(&replace_header(
            &bytes,
            &serde_json::to_vec(&value).unwrap()
        ))
        .contains("unknown field")
    );
}

#[test]
fn malformed_metadata_is_rejected_before_field_preparation() {
    let cases: &[(&str, fn(&mut FrozenProfileDescriptor))] = &[
        ("contract", |d| {
            d.identities.contract_id = "../../ambiguous name".into()
        }),
        ("contract", |d| d.identities.contract_id = "a".repeat(129)),
        ("extent", |d| d.origin.full_size = [0, 600]),
        ("extent", |d| d.origin.full_size = [u32::MAX, 600]),
        ("region", |d| {
            d.origin.region.as_mut().unwrap().bounds = [200, 150, 801, 450]
        }),
        ("region", |d| {
            d.origin.region.as_mut().unwrap().bounds = [200, 150, 200, 450]
        }),
        ("gain dimensions", |d| d.gain.dimensions = [u32::MAX; 3]),
        ("sample bound", |d| d.gain.dimensions = [64, 512, 512]),
        ("gain parameters", |d| d.gain.origin_yx[0] = f32::NAN),
        ("gain parameters", |d| {
            d.gain.input_weights[0] = f32::INFINITY
        }),
        ("spacing", |d| d.gain.spacing_yx[0] = 0.),
        ("gamma", |d| d.gain.gamma = -1.),
        ("color matrix", |d| d.linear_709_to_rimm[0][0] = f32::NAN),
        ("pre-gain", |d| d.pre_gain_scale = 0.),
        ("table edge", |d| d.tables[0].as_mut().unwrap().size = 33),
        ("table matrix", |d| {
            d.tables[0].as_mut().unwrap().source_to_table[0][0] = f32::INFINITY
        }),
        ("table gamma", |d| {
            d.tables[0].as_mut().unwrap().encoding = TableEncoding::Power { gamma: 100. }
        }),
        ("knot count", |d| {
            d.tone_curve = ToneDescriptor::PiecewiseLinear {
                knots: vec![[0., 0.]],
            }
        }),
        ("tone ordering", |d| {
            d.tone_curve = ToneDescriptor::PiecewiseLinear {
                knots: vec![[0., 1.], [1., 0.]],
            }
        }),
        ("tone knot", |d| {
            d.tone_curve = ToneDescriptor::PiecewiseLinear {
                knots: vec![[0., 0.], [1., f32::NAN]],
            }
        }),
        ("mask dimensions", |d| {
            d.masks[0].as_mut().unwrap().size = [0, 2]
        }),
        ("sample bound", |d| {
            d.masks[0].as_mut().unwrap().size = [2048, 2048]
        }),
        ("mask bounds", |d| {
            d.masks[0].as_mut().unwrap().origin_xy[0] = -0.1
        }),
        ("mask bounds", |d| {
            d.masks[0].as_mut().unwrap().extent_xy[0] = 1.
        }),
        ("mask bounds", |d| {
            d.masks[0].as_mut().unwrap().extent_xy[0] = f32::NAN
        }),
    ];
    for &(expected, change) in cases {
        let (mut descriptor, data) = fixture();
        change(&mut descriptor);
        let error = FrozenLearnedAsset::freeze(descriptor, data)
            .err()
            .expect("invalid metadata accepted")
            .to_string();
        assert!(error.contains(expected), "expected {expected}; got {error}");
    }
}

#[test]
fn payload_presence_lengths_and_ranges_are_checked_when_freezing() {
    let cases: &[fn(&mut FrozenProfileData)] = &[
        |d| {
            d.gain.pop();
        },
        |d| d.tables[0] = None,
        |d| d.tables[1] = Some(vec![]),
        |d| {
            d.tables[2].as_mut().unwrap().push(0.);
        },
        |d| d.masks[0] = None,
        |d| {
            d.masks[1].as_mut().unwrap().clear();
        },
        |d| d.gain[0] = -1.,
        |d| d.gain[0] = f32::NAN,
        |d| d.tables[0].as_mut().unwrap()[0] = 1.01,
        |d| d.masks[0].as_mut().unwrap()[0] = f32::INFINITY,
    ];
    for change in cases {
        let (descriptor, mut data) = fixture();
        change(&mut data);
        assert!(FrozenLearnedAsset::freeze(descriptor, data).is_err());
    }
}

#[test]
fn metadata_validation_rejects_invalid_matrices_before_field_allocation() {
    let bytes = asset().encode().unwrap();
    for (matrix, expected) in [
        ([[0.; 3]; 3], "Singular"),
        (
            [[1., 0., 0.], [0., 1., 0.], [0., 0., 1e-8]],
            "Ill-conditioned",
        ),
    ] {
        for table_matrix in [false, true] {
            let (mut descriptor, _) = fixture();
            if table_matrix {
                descriptor.tables[0].as_mut().unwrap().source_to_table = matrix;
            } else {
                descriptor.linear_709_to_rimm = matrix;
            }
            // layout() runs before any payload block is decoded or allocated.
            assert!(
                layout(&descriptor)
                    .err()
                    .expect("invalid matrix accepted")
                    .to_string()
                    .contains(expected)
            );
            let bad = replace_header(&bytes, &serde_json::to_vec(&descriptor).unwrap());
            assert!(error(&bad).contains(expected));
        }
    }
}
