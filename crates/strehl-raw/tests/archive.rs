use std::path::{Path, PathBuf};

#[test]
fn archived_raws_are_discoverable() {
    assert!(
        strehl_raw::validate_raw_paths(&["stack/frame.ARW".into(), "stack/frame.ARW.straw".into()])
            .is_err()
    );
    assert!(
        strehl_raw::validate_raw_paths(&["stack/frame.ARW".into(), "other/frame.ARW.straw".into()])
            .is_ok()
    );
    for name in [
        "frame-000001.ARW",
        "frame-000001.ARW.straw",
        "frame.ARW.STRAW",
    ] {
        assert!(strehl_raw::is_raw_path(Path::new(name)));
    }
    assert!(!strehl_raw::is_raw_path(Path::new("manifest.json")));
    assert!(!strehl_raw::is_raw_path(Path::new(
        "frame.ARW.straw.partial"
    )));
}

#[test]
#[ignore = "Read-only real capture comparison: set STREHL_ARCHIVE_RAW and STREHL_ARCHIVE_PACKED"]
fn full_cfa_and_metadata_equal_original() {
    let original = PathBuf::from(std::env::var_os("STREHL_ARCHIVE_RAW").unwrap());
    let archived = PathBuf::from(std::env::var_os("STREHL_ARCHIVE_PACKED").unwrap());
    assert_eq!(
        strehl_raw_codec::archive::read_original(&archived).unwrap(),
        std::fs::read(&original).unwrap()
    );
    let a = strehl_raw::decode(&original).unwrap();
    let b = strehl_raw::decode(&archived).unwrap();
    assert_eq!(a.data, b.data);
    assert_eq!(a.active, b.active);
    assert_eq!(a.stride, b.stride);
    assert_eq!(a.buffer_height, b.buffer_height);
    assert_eq!(a.iso, b.iso);
    assert_eq!(a.camera, b.camera);
    assert_eq!(format!("{:?}", a.levels), format!("{:?}", b.levels));
    assert_eq!(format!("{:?}", a.wb_coeffs), format!("{:?}", b.wb_coeffs));
    assert_eq!(a.xyz_to_cam_rgbe, b.xyz_to_cam_rgbe);
    assert_eq!(
        strehl_raw::identity(&original),
        strehl_raw::identity(&archived)
    );
    // The specialized hidden readers still support only the measured A7C II layout.
    // Preserve their full result, including an explicit unsupported-camera error.
    assert_eq!(
        format!("{:?}", strehl_raw::sony_focus::read(&original)),
        format!("{:?}", strehl_raw::sony_focus::read(&archived))
    );
    assert_eq!(
        format!("{:?}", strehl_raw::sony_optical::read(&original)),
        format!("{:?}", strehl_raw::sony_optical::read(&archived))
    );
    println!(
        "Verified all {} CFA samples, geometry, levels, colour and Sony metadata",
        a.data.len()
    );
}
