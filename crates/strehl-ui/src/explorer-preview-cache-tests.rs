use super::*;

#[test]
fn warm_cache_restores_pixels_and_rejects_same_size_timestamp_replacement() {
    let root = tempfile::tempdir().unwrap();
    let source = root.path().join("source.png");
    let cache = root.path().join("cache");
    let save = |color| {
        image::RgbImage::from_pixel(33, 23, image::Rgb(color))
            .save(&source)
            .unwrap()
    };
    save([211, 12, 31]);
    let modified = fs::metadata(&source).unwrap().modified().unwrap();
    let a = load_file(&source, false, Some(&cache), &AtomicBool::new(false)).unwrap();
    let warm = load_file(&source, false, Some(&cache), &AtomicBool::new(false)).unwrap();
    assert_eq!(a.rgba, warm.rgba);
    let first_identity = file_identity(&source, false).unwrap();
    save([12, 211, 31]);
    File::options()
        .write(true)
        .open(&source)
        .unwrap()
        .set_modified(modified)
        .unwrap();
    let second_identity = file_identity(&source, false).unwrap();
    assert_ne!(
        first_identity, second_identity,
        "source bookends must detect a replacement even with restored timestamp"
    );
    let b = load_file(&source, false, Some(&cache), &AtomicBool::new(false)).unwrap();
    assert_ne!(a.rgba, b.rgba);
    assert_eq!(&b.rgba[..3], &[12, 211, 31]);
    let stale = cache.join(format!("{second_identity}.preview"));
    fs::write(&stale, [0xff; 9]).unwrap();
    let rescued = load_file(&source, false, Some(&cache), &AtomicBool::new(false)).unwrap();
    assert_eq!(
        rescued.rgba, b.rgba,
        "a corrupt cache must safely rebuild from the photograph"
    );
}

#[test]
fn cache_rejects_wrong_identity_and_malformed_allocation_before_pixels() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("cache.preview");
    let image = PreviewImage {
        path: "source".into(),
        source_size: [3, 2],
        size: [3, 2],
        rgba: vec![71; 24],
        is_overview: true,
    };
    write(&path, "correct", &image).unwrap();
    assert!(read(&path, Path::new("source"), "wrong").is_err());
    assert_eq!(
        read(&path, Path::new("source"), "correct").unwrap().rgba,
        image.rgba
    );
    let header = serde_json::to_vec(&Header {
        format: FORMAT,
        identity: "correct".into(),
        source_size: [1, 1],
        size: [usize::MAX, 1],
    })
    .unwrap();
    let mut bytes = (header.len() as u32).to_le_bytes().to_vec();
    bytes.extend(header);
    fs::write(&path, bytes).unwrap();
    assert!(read(&path, Path::new("source"), "correct").is_err());
}

#[test]
fn immutable_version_thumbnail_is_available_without_reopening_large_source() {
    let root = tempfile::tempdir().unwrap();
    let source = root.path().join("source.tiff");
    let image = LinearImage {
        width: 24,
        height: 16,
        pixels: vec![0.15; 24 * 16 * 3],
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    };
    strehl_edit::save_linear_tiff(&source, &image).unwrap();
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = 1.4;
    let version = photographs::save_version(
        root.path(),
        photographs::PhotoOwner {
            stack: None,
            run: None,
            output: source.clone(),
        },
        "Bright",
        recipe.clone(),
        &image,
        &source,
        &AtomicBool::new(false),
    )
    .unwrap();
    fs::remove_file(&source).unwrap();
    let thumbnail = load_version(root.path(), &version).unwrap();
    assert_eq!(
        thumbnail.rgba,
        render(&source, &image, &recipe, [24, 16]).unwrap().rgba
    );
    let mut renamed = version.clone();
    renamed.name = "Renamed".into();
    assert_eq!(
        load_version(root.path(), &renamed).unwrap().rgba,
        thumbnail.rgba
    );
    let mut different = version;
    different.loaded_sha256 = "0".repeat(64);
    assert!(
        load_version(root.path(), &different).is_err(),
        "a saved thumbnail must not bind to other loaded pixels"
    );
}

#[test]
#[ignore = "read-only local photograph timing; set STREHL_EXPLORER_BENCH to a TIFF"]
fn measure_explorer_cold_and_warm_navigation_derivatives() {
    let source = PathBuf::from(
        std::env::var_os("STREHL_EXPLORER_BENCH").expect("set STREHL_EXPLORER_BENCH"),
    );
    let root = tempfile::tempdir().unwrap();
    let cancelled = AtomicBool::new(false);
    let mut cold = Vec::new();
    let mut warm = Vec::new();
    let mut original = Vec::new();
    for pass in 0..4 {
        let run = |kind: usize| {
            let start = std::time::Instant::now();
            let preview = match kind {
                0 => load_file(&source, false, None, &cancelled).unwrap(),
                1 => load_file(&source, false, Some(root.path()), &cancelled).unwrap(),
                _ => super::super::load_preview(source.clone(), SIDE)
                    .receiver
                    .recv()
                    .unwrap()
                    .unwrap(),
            };
            assert!(preview.rgba.len() > 4 && preview.size.iter().all(|&n| n <= SIDE as usize));
            start.elapsed().as_secs_f64() * 1000.0
        };
        if pass % 2 == 0 {
            original.push(run(2));
            cold.push(run(0));
        } else {
            cold.push(run(0));
            original.push(run(2));
        }
        load_file(&source, false, Some(root.path()), &cancelled).unwrap();
        warm.push(run(1));
    }
    println!(
        "explorer-thumbnail-timing {}",
        serde_json::json!({"source":source,"side":SIDE,"scope":"OS cache uncontrolled; first derivative versus retained derivative; four alternating full-decoder comparisons; worker only, excludes UI/GPU","old_full_decode_ms":original,"new_uncached_ms":cold,"new_disk_cached_ms":warm})
    );
}
