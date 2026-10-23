use super::*;
use crate::learned_asset::{FrozenLearnedAsset, RegionOrigin};
use crate::learned_profile::{IDENTITY_MATRIX, ProfileRegion};
use std::sync::atomic::AtomicBool;

pub(crate) fn fixture() -> (FrozenSceneDescriptor, FrozenSceneData) {
    let table: Vec<_> = (0..3)
        .flat_map(|c| {
            (0..2).flat_map(move |r| {
                (0..2).flat_map(move |g| {
                    (0..2).map(move |b| [r, g, b][[2, 0, 1][c]] as f32 * [0.6, 0.9, 0.8][c])
                })
            })
        })
        .collect();
    (
        FrozenSceneDescriptor {
            identities: AssetIdentities {
                contract_id: SCENE_SDR_LINEAR_V1.into(),
                contract_sha256: [1; 32],
                model_sha256: [2; 32],
                input_sha256: [3; 32],
                source_sha256: [4; 32],
            },
            origin: ProfileOrigin {
                full_size: [7, 5],
                region: None,
            },
            gain: GainDescriptor {
                dimensions: [2, 2, 2],
                origin_yx: [0.; 2],
                spacing_yx: [1.; 2],
                input_weights: [0.2, 0.3, 0.4, 0., 0.1],
                gamma: 1.3,
            },
            table: TableDescriptor {
                size: 2,
                source_to_table: IDENTITY_MATRIX,
                encoding: TableEncoding::Power { gamma: 2.2 },
                gamut_extension: true,
            },
            linear_709_to_working: [[1., 0.25, 0.], [0., 1., 0.], [0., 0., 1.]],
            working_to_linear_709: [[1., -0.25, 0.], [0., 1., 0.], [0., 0., 1.]],
            gain_query_scale: 2.,
            exposure_scale: 0.5,
        },
        FrozenSceneData {
            gain: vec![0.6, 0.7, 0.8, 0.9, 1., 1.1, 1.2, 1.3],
            table,
        },
    )
}

fn asset() -> FrozenSceneAsset {
    let (d, p) = fixture();
    FrozenSceneAsset::freeze(d, p).unwrap()
}
fn resign(bytes: &mut [u8]) {
    let n = bytes.len() - 32;
    let hash = Sha256::digest(&bytes[..n]);
    bytes[n..].copy_from_slice(&hash);
}
fn payload_offset(bytes: &[u8]) -> usize {
    20 + u32::from_le_bytes(bytes[12..16].try_into().unwrap()) as usize
}
fn replace_header(bytes: &[u8], header: &[u8]) -> Vec<u8> {
    let mut result = bytes[..20].to_vec();
    result[12..16].copy_from_slice(&(header.len() as u32).to_le_bytes());
    result.extend_from_slice(header);
    result.extend_from_slice(&bytes[payload_offset(bytes)..]);
    resign(&mut result);
    result
}

#[test]
fn reopen_keeps_exact_fields_prepared_pixels_and_shared_immutable_handles() {
    let (d, data) = fixture();
    let independent = PreparedSceneSdrProfile::new(
        GainMap::new(
            data.gain.clone().into(),
            GainMapParameters {
                dimensions: d.gain.dimensions,
                origin_yx: d.gain.origin_yx,
                spacing_yx: d.gain.spacing_yx,
                input_weights: d.gain.input_weights,
                gamma: d.gain.gamma,
            },
        )
        .unwrap(),
        ColorLut::new(
            d.table.size,
            data.table.clone().into(),
            d.table.source_to_table,
            ColorEncoding::Power { gamma: 2.2 },
            true,
        )
        .unwrap(),
        d.parameters(),
    )
    .unwrap();
    let frozen = FrozenSceneAsset::freeze(d.clone(), data).unwrap();
    let bytes = frozen.encode().unwrap();
    let loaded = FrozenSceneAsset::decode(&bytes).unwrap();
    assert_eq!(bytes, loaded.encode().unwrap());
    assert_eq!(loaded.descriptor(), &d);
    assert_eq!(loaded.digest(), frozen.digest());
    assert_eq!(loaded.encoded_len(), bytes.len());
    assert_eq!(loaded.content_id().len(), 64);
    assert!(Arc::ptr_eq(&loaded.prepared(), &loaded.clone().prepared()));
    let input: Vec<_> = (0..35)
        .flat_map(|i| [i as f32 / 19. - 0.25, (i % 3) as f32 * 0.4, 0.7])
        .collect();
    let region = ProfileRegion {
        full_size: [7, 5],
        origin: [0, 0],
        size: [7, 5],
    };
    let mut before = vec![0.; input.len()];
    let mut after = before.clone();
    independent
        .render_region(&input, &mut before, region, &AtomicBool::new(false))
        .unwrap();
    loaded
        .prepared()
        .render_region(&input, &mut after, region, &AtomicBool::new(false))
        .unwrap();
    assert_eq!(
        before.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
        after.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
    );
    let mut changed = d;
    changed.exposure_scale = 1.;
    let (_, data) = fixture();
    let other = FrozenSceneAsset::freeze(changed, data).unwrap();
    assert_ne!(other.digest(), frozen.digest());
    assert_ne!(
        other
            .prepared()
            .develop_pixel([0.2, 0.4, 0.8], [0.3, 0.7])
            .unwrap(),
        loaded
            .prepared()
            .develop_pixel([0.2, 0.4, 0.8], [0.3, 0.7])
            .unwrap()
    );
}

#[test]
fn accepted_signed_zero_and_subnormal_payload_bits_survive() {
    let (d, mut data) = fixture();
    data.gain[0] = -0.;
    data.gain[1] = f32::from_bits(1);
    data.table[0] = -0.;
    data.table[1] = f32::from_bits(1);
    let encoded = FrozenSceneAsset::freeze(d, data).unwrap().encode().unwrap();
    let p = payload_offset(&encoded);
    assert_eq!(&encoded[p..p + 4], &(-0.0f32).to_le_bytes());
    assert_eq!(&encoded[p + 4..p + 8], &1u32.to_le_bytes());
    assert_eq!(
        FrozenSceneAsset::decode(&encoded)
            .unwrap()
            .encode()
            .unwrap(),
        encoded
    );
}

#[test]
fn malformed_metadata_is_refused_before_decoded_field_allocation() {
    type DescriptorMutation = Box<dyn Fn(&mut FrozenSceneDescriptor)>;
    let mutations: Vec<DescriptorMutation> = vec![
        Box::new(|d| d.identities.contract_id = "strehl.scene-sdr-linear.v2".into()),
        Box::new(|d| {
            d.origin.region = Some(RegionOrigin {
                id: "region".into(),
                bounds: [0, 0, 2, 2],
            })
        }),
        Box::new(|d| d.origin.full_size = [0, 5]),
        Box::new(|d| d.gain.dimensions = [u32::MAX, 2, 2]),
        Box::new(|d| d.gain.dimensions = [64, 512, 512]),
        Box::new(|d| d.gain.spacing_yx[0] = 0.),
        Box::new(|d| d.gain.gamma = 0.),
        Box::new(|d| d.gain_query_scale = 0.),
        Box::new(|d| d.exposure_scale = 257.),
        Box::new(|d| d.working_to_linear_709[0][0] = 2.),
        Box::new(|d| d.table.size = 33),
        Box::new(|d| d.table.source_to_table = [[0.; 3]; 3]),
        Box::new(|d| d.table.encoding = TableEncoding::Power { gamma: 0. }),
    ];
    let encoded = asset().encode().unwrap();
    for mutate in mutations {
        let (mut d, data) = fixture();
        mutate(&mut d);
        let altered = replace_header(&encoded, &serde_json::to_vec(&d).unwrap());
        assert!(
            FrozenSceneAsset::decode(&altered).is_err(),
            "metadata accepted: {d:?}"
        );
        assert!(FrozenSceneAsset::freeze(d, data).is_err());
    }
    for (field, value) in [
        ("gain_query_scale", f32::NAN),
        ("exposure_scale", f32::INFINITY),
    ] {
        let (mut d, data) = fixture();
        if field == "gain_query_scale" {
            d.gain_query_scale = value;
        } else {
            d.exposure_scale = value;
        }
        assert!(FrozenSceneAsset::freeze(d, data).is_err());
    }
}

#[test]
fn canonical_header_duplicate_unknown_counts_and_every_envelope_layer_are_checked() {
    let encoded = asset().encode().unwrap();
    for n in 0..encoded.len() {
        assert!(FrozenSceneAsset::decode(&encoded[..n]).is_err());
    }
    for i in [
        0,
        8,
        10,
        12,
        16,
        25,
        payload_offset(&encoded),
        encoded.len() - 1,
    ] {
        let mut changed = encoded.clone();
        changed[i] ^= 1;
        assert!(FrozenSceneAsset::decode(&changed).is_err());
        if i < payload_offset(&encoded) {
            resign(&mut changed);
            assert!(FrozenSceneAsset::decode(&changed).is_err());
        }
    }
    // A payload bit change with a recomputed digest may be another VALID asset.
    // The corrupt unresigned case above must fail; the re-signed field case is
    // checked against the content key by storage, not against a publisher here.
    let header = std::str::from_utf8(&encoded[20..payload_offset(&encoded)]).unwrap();
    for altered in [
        format!(" {}", header),
        format!("{{\"unexpected\":0,{}", &header[1..]),
        format!("{{\"exposure_scale\":0.5,{}", &header[1..]),
    ] {
        assert!(FrozenSceneAsset::decode(&replace_header(&encoded, altered.as_bytes())).is_err());
    }
    let mut trailing = encoded.clone();
    trailing.push(0);
    assert!(FrozenSceneAsset::decode(&trailing).is_err());
    for index in [12, 16] {
        let mut changed = encoded.clone();
        changed[index..index + 4].copy_from_slice(&u32::MAX.to_le_bytes());
        resign(&mut changed);
        assert!(FrozenSceneAsset::decode(&changed).is_err());
    }
}

#[test]
fn correctly_hashed_nonfinite_out_of_range_and_incorrect_field_lengths_fail() {
    let encoded = asset().encode().unwrap();
    let start = payload_offset(&encoded);
    for (offset, values) in [
        (0, vec![f32::NAN, f32::INFINITY, -0.01]),
        (8, vec![f32::NAN, f32::NEG_INFINITY, -0.01, 1.001]),
    ] {
        for value in values {
            let mut changed = encoded.clone();
            let at = start + offset * 4;
            changed[at..at + 4].copy_from_slice(&value.to_le_bytes());
            resign(&mut changed);
            assert!(FrozenSceneAsset::decode(&changed).is_err());
        }
    }
    for shorten_gain in [false, true] {
        let (d, mut data) = fixture();
        if shorten_gain {
            data.gain.pop();
        } else {
            data.table.push(0.5);
        }
        assert!(FrozenSceneAsset::freeze(d, data).is_err());
    }
    let (d, mut data) = fixture();
    data.gain[0] = f32::NAN;
    assert!(FrozenSceneAsset::freeze(d, data).is_err());
    let (d, mut data) = fixture();
    data.table[0] = 1.01;
    assert!(FrozenSceneAsset::freeze(d, data).is_err());
}

pub(crate) fn legacy_wire_fixture() -> Vec<u8> {
    // Independent literal v1 wire descriptor, not serialized through a production
    // descriptor. Retaining it detects changes to old field order/spelling/types.
    let h1 = format!("[{}]", vec!["1"; 32].join(","));
    let h2 = format!("[{}]", vec!["2"; 32].join(","));
    let h3 = format!("[{}]", vec!["3"; 32].join(","));
    let h4 = format!("[{}]", vec!["4"; 32].join(","));
    let header = format!(
        r#"{{"identities":{{"contract_id":"strehl/legacy-wire-fixture-v1","contract_sha256":{h1},"model_sha256":{h2},"input_sha256":{h3},"source_sha256":{h4}}},"origin":{{"full_size":[7,5],"region":null}},"gain":{{"dimensions":[1,1,1],"origin_yx":[0.0,0.0],"spacing_yx":[1.0,1.0],"input_weights":[1.0,0.0,0.0,0.0,0.0],"gamma":1.0}},"tables":[null,null,null],"linear_709_to_rimm":[[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]],"pre_gain_scale":1.0,"tone_curve":{{"kind":"identity"}},"masks":[null,null]}}"#
    );
    let mut bytes = b"STRHLPF\0".to_vec();
    bytes.extend_from_slice(&[1, 0, 0, 0]);
    bytes.extend_from_slice(&(header.len() as u32).to_le_bytes());
    bytes.extend_from_slice(&1u32.to_le_bytes());
    bytes.extend_from_slice(header.as_bytes());
    bytes.extend_from_slice(&1.25f32.to_le_bytes());
    bytes.extend_from_slice(&[0; 32]);
    resign(&mut bytes);
    bytes
}

#[test]
fn literal_legacy_wire_bytes_are_unchanged_and_codecs_never_cross_load() {
    let legacy = legacy_wire_fixture();
    let old = FrozenLearnedAsset::decode(&legacy).unwrap();
    assert_eq!(old.encode().unwrap(), legacy);
    assert!(FrozenSceneAsset::decode(&legacy).is_err());
    let scene = asset().encode().unwrap();
    assert!(FrozenLearnedAsset::decode(&scene).is_err());
    let mut disguised = scene.clone();
    disguised[..8].copy_from_slice(b"STRHLPF\0");
    resign(&mut disguised);
    assert!(FrozenLearnedAsset::decode(&disguised).is_err());
    let mut disguised = legacy;
    disguised[..8].copy_from_slice(MAGIC);
    resign(&mut disguised);
    assert!(FrozenSceneAsset::decode(&disguised).is_err());
}
