use super::*;
use std::io::{Cursor, Read};

fn identity(model: &[u8]) -> PackageIdentity {
    PackageIdentity {
        model: ContractIdentity {
            id: "test-model-v1".into(),
            sha256: sha256(model),
        },
        input: ContractIdentity {
            id: "test-input-v1".into(),
            sha256: [2; 32],
        },
        render: ContractIdentity {
            id: "test-render-v1".into(),
            sha256: [3; 32],
        },
    }
}
fn fixture() -> (Vec<u8>, Vec<u8>, PackageIdentity) {
    let model = b"test-only fake model; never a graph".to_vec();
    let allowed = identity(&model);
    let manifest =
        serde_json::to_vec(&PackageManifest::fixed(allowed.clone(), model.len() as u64)).unwrap();
    (manifest, model, allowed)
}

#[test]
fn immutable_package_keeps_exact_bytes_and_metadata_identity() {
    let (manifest, mut model, allowed) = fixture();
    let package = PredictorPackage::from_bytes(&manifest, &model, &[allowed.clone()]).unwrap();
    let saved = package.model_bytes().to_vec();
    model[0] ^= 1;
    assert_eq!(package.model_bytes(), saved);
    assert_eq!(package.manifest().identity, allowed);
    let pretty = serde_json::to_vec_pretty(package.manifest()).unwrap();
    let reopened = PredictorPackage::read(
        pretty.len() as u64,
        &mut Cursor::new(&pretty),
        saved.len() as u64,
        &mut Cursor::new(&saved),
        &[allowed],
    )
    .unwrap();
    assert_eq!(package.digest(), reopened.digest());
    assert_eq!(package.model_bytes(), reopened.model_bytes());
}

#[test]
fn trust_requires_exact_model_input_and_render_identity_not_claimed_support() {
    let (header, bytes, allowed) = fixture();
    assert!(PredictorPackage::from_bytes(&header, &bytes, &[]).is_err());
    for member in 0..6 {
        let mut wrong = allowed.clone();
        match member {
            0 => wrong.model.id.push('x'),
            1 => wrong.model.sha256[0] ^= 1,
            2 => wrong.input.id.push('x'),
            3 => wrong.input.sha256[0] ^= 1,
            4 => wrong.render.id.push('x'),
            _ => wrong.render.sha256[0] ^= 1,
        }
        assert!(
            PredictorPackage::from_bytes(&header, &bytes, &[wrong]).is_err(),
            "identity member {member}"
        );
    }
    // A self-consistent newly hashed model remains unapproved.
    let changed = b"another fake model";
    let new_manifest = PackageManifest::fixed(identity(changed), changed.len() as u64);
    assert!(
        PredictorPackage::from_bytes(
            &serde_json::to_vec(&new_manifest).unwrap(),
            changed,
            &[allowed]
        )
        .is_err()
    );
}

#[test]
fn truncated_surplus_tampered_and_malformed_objects_fail() {
    let (header, bytes, allowed) = fixture();
    let allow = [allowed];
    for cut in [0, 1, bytes.len() - 1] {
        assert!(PredictorPackage::from_bytes(&header, &bytes[..cut], &allow).is_err());
    }
    let mut changed = bytes.clone();
    changed[0] ^= 1;
    assert!(PredictorPackage::from_bytes(&header, &changed, &allow).is_err());
    changed = bytes.clone();
    changed.push(0);
    assert!(PredictorPackage::from_bytes(&header, &changed, &allow).is_err());
    for malformed in [b"{".as_slice(), b"null", &header[..header.len() - 1]] {
        assert!(PredictorPackage::from_bytes(malformed, &bytes, &allow).is_err());
    }
    let duplicate = String::from_utf8(header.clone())
        .unwrap()
        .replacen("{", "{\"version\":1,", 1);
    assert!(PredictorPackage::from_bytes(duplicate.as_bytes(), &bytes, &allow).is_err());
    let unknown =
        String::from_utf8(header.clone())
            .unwrap()
            .replacen("{", "{\"surprise\":true,", 1);
    assert!(PredictorPackage::from_bytes(unknown.as_bytes(), &bytes, &allow).is_err());
    for body in [&bytes[..bytes.len() - 1], changed.as_slice()] {
        assert!(
            PredictorPackage::read(
                header.len() as u64,
                &mut Cursor::new(&header),
                bytes.len() as u64,
                &mut Cursor::new(body),
                &allow
            )
            .is_err()
        );
    }
}

#[test]
fn fixed_tensor_contract_rejects_shape_order_dtype_and_versions() {
    let (header, bytes, allowed) = fixture();
    let original: PackageManifest = serde_json::from_slice(&header).unwrap();
    for case in 0..10 {
        let mut m = original.clone();
        match case {
            0 => m.version = 2,
            1 => m.format = "onnx".into(),
            2 => m.tensor_contract.push('x'),
            3 => m.input.shape[1] = 3,
            4 => m.outputs.swap(1, 2),
            5 => m.outputs[0].shape[2] = 95,
            6 => m.outputs[4].dtype = "float16".into(),
            7 => {
                m.outputs.pop();
            }
            8 => m.model_bytes = 0,
            _ => m.model_bytes = MAX_MODEL_BYTES as u64 + 1,
        }
        assert!(
            PredictorPackage::from_bytes(
                &serde_json::to_vec(&m).unwrap(),
                &bytes,
                std::slice::from_ref(&allowed)
            )
            .is_err(),
            "case {case}"
        );
    }
}

struct NeverRead;
impl Read for NeverRead {
    fn read(&mut self, _: &mut [u8]) -> std::io::Result<usize> {
        panic!("oversize input must be rejected before reading/allocating")
    }
}

#[test]
fn declared_oversize_rejected_before_any_payload_read() {
    let (_, _, allowed) = fixture();
    for (a, b) in [
        (MAX_MANIFEST_BYTES as u64 + 1, 10),
        (10, MAX_MODEL_BYTES as u64 + 1),
        (0, 10),
        (10, 0),
    ] {
        assert!(
            PredictorPackage::read(
                a,
                &mut NeverRead,
                b,
                &mut NeverRead,
                std::slice::from_ref(&allowed)
            )
            .is_err()
        );
    }
    let (header, bytes, _) = fixture();
    let mut m: PackageManifest = serde_json::from_slice(&header).unwrap();
    m.model_bytes += 1;
    let h = serde_json::to_vec(&m).unwrap();
    assert!(
        PredictorPackage::read(
            h.len() as u64,
            &mut Cursor::new(&h),
            bytes.len() as u64,
            &mut NeverRead,
            &[allowed]
        )
        .is_err()
    );
}
