use super::*;

/// Explicit v24 browser reference: same candidate/crop policy, full existing
/// JPEG decoder, then the original Triangle resize. No reduced-IDCT or cache.
fn full_decode_reference(path: &Path, max_side: u32) -> Result<PreviewImage> {
    let cancelled = AtomicBool::new(false);
    let mut file = File::open(path)?;
    let file_len = file.metadata()?.len();
    let candidates = jpeg_candidates(&mut file, file_len, &cancelled)?;
    let sized = sized_candidates(&mut file, file_len, candidates, &cancelled)?;
    let (candidates, source_size) = rank_candidates(sized, false, true, max_side)?;
    let mut read_bytes = 0;
    let mut last_error = None;
    for candidate in candidates.into_iter().take(MAX_JPEG_ATTEMPTS) {
        read_bytes += candidate.length;
        if read_bytes > MAX_TOTAL_JPEG_BYTES {
            break;
        }
        let mut bytes = vec![0; candidate.length as usize];
        read_at(
            &mut file,
            file_len,
            candidate.offset,
            &mut bytes,
            &cancelled,
        )?;
        match decode_jpeg(&bytes) {
            Ok(image) => {
                let image = orient(image, candidate.orientation);
                let decoded_size = [image.width(), image.height()];
                ensure!(
                    compatible_aspect(decoded_size, source_size),
                    "reference crop mismatch"
                );
                let reduced = decoded_size.iter().any(|&side| side > max_side);
                let image = if reduced {
                    image.resize(max_side, max_side, FilterType::Triangle)
                } else {
                    image
                };
                let rgba = image.into_rgba8();
                return Ok(PreviewImage {
                    path: path.to_path_buf(),
                    source_size,
                    size: [rgba.width() as usize, rgba.height() as usize],
                    rgba: rgba.into_raw(),
                    is_overview: reduced || decoded_size != source_size,
                });
            }
            Err(error) => last_error = Some(error),
        }
    }
    bail!("Reference JPEG failed: {last_error:?}")
}

#[test]
#[ignore = "explicit whole-preview before/after visual export on an owned twelve-RAW sample"]
fn export_real_source_preview_pairs() {
    let source = PathBuf::from(std::env::var_os("STREHL_UI_BENCH_SOURCE").expect("source folder"));
    let output = PathBuf::from(
        std::env::var_os("STREHL_UI_COMPARE_OUTPUT").expect("owned image output directory"),
    );
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    assert!(
        output.is_absolute() && output.starts_with(workspace.join("outputs")),
        "comparison exports belong inside this workspace's owned outputs"
    );
    assert!(
        !output
            .components()
            .any(|c| c == std::path::Component::ParentDir)
    );
    let mut files: Vec<_> = std::fs::read_dir(&source)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("arw")))
        .collect();
    files.sort();
    assert_eq!(files.len(), 12, "only the named compact sample is allowed");
    std::fs::create_dir_all(&output).unwrap();
    let mut receipts = Vec::new();
    for index in [0, 11] {
        let before = full_decode_reference(&files[index], 1920).unwrap();
        let after =
            load_browser(&files[index], 1920, false, true, &AtomicBool::new(false)).unwrap();
        assert_eq!(before.path, after.path);
        assert_eq!(
            before.source_size, after.source_size,
            "original display aperture must survive reduced IDCT"
        );
        assert_eq!(
            before.size, after.size,
            "before/after images must depict the same fitted rectangle"
        );
        assert_eq!(before.is_overview, after.is_overview);
        let before_path = output.join(format!("source-{:03}-v24-reference.png", index + 1));
        let after_path = output.join(format!("source-{:03}-v25-scaled.png", index + 1));
        for (path, image) in [(&before_path, &before), (&after_path, &after)] {
            image::save_buffer(
                path,
                &image.rgba,
                image.size[0] as u32,
                image.size[1] as u32,
                image::ColorType::Rgba8,
            )
            .unwrap();
        }
        receipts.push(serde_json::json!({"source":files[index],"frame":index,
            "aperture":after.source_size,"pixels":after.size,"reference":before_path,"candidate":after_path,
            "whole_preview_review_required":true,"photographic_quality_claim":false}));
    }
    let report = output.join("comparison.json");
    std::fs::write(report, serde_json::to_vec_pretty(&receipts).unwrap()).unwrap();
    println!("{}", serde_json::to_string_pretty(&receipts).unwrap());
}
