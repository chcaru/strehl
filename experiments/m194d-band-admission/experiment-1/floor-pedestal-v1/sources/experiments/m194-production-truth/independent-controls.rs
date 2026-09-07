//! Independent M194 path controls. Fixture API is test-only; production merge
//! arithmetic is never reimplemented here. See independent-preregister.md.

use super::*;

// Independent fixture: 104 x 76 plane sites, even sensor origin (6,2), odd
// padded stride 223, distinct green sites, a coordinate ramp plus an off-axis
// checker patch. No product interpolation generates these input samples.
fn independent_frames(n: usize, flat: bool) -> Vec<Frame> {
    (0..n)
        .map(|k| {
            let mut f = fixture_frame(208, 152, k);
            f.active.x = 6;
            f.active.y = 2;
            f.stride = 223;
            f.buffer_height = 159;
            f.data = vec![65500; f.stride * f.buffer_height];
            f.levels = Levels {
                black: 256.0,
                white: 12000.0,
            };
            f.wb_coeffs = [1.4, 1.0, 0.65, f32::NAN];
            for y in 0..152 {
                for x in 0..208 {
                    let qx = x / 2;
                    let qy = y / 2;
                    let site = (y % 2) * 2 + x % 2;
                    let pattern = if flat {
                        0
                    } else {
                        3 * qx
                            + 7 * qy
                            + ((qx * 13 + qy * 19 + k * 47) % 101)
                            + if qx > 24 && qx < 75 && qy > 17 && qy < 57 {
                                900 * ((qx / 3 + qy / 5 + k) % 2)
                            } else {
                                0
                            }
                    };
                    // A physically flat color has equal green-site means. The
                    // structured arm deliberately separates them to test both.
                    let site_base = if flat {
                        [900, 1700, 1700, 4500][site]
                    } else {
                        [900, 1700, 2900, 4500][site]
                    };
                    f.data[(y + f.active.y) * f.stride + x + f.active.x] =
                        256 + site_base + pattern as u16;
                }
            }
            f
        })
        .collect()
}

fn independent_track(n: usize) -> Vec<FrameWarp> {
    (0..n)
        .map(|k| {
            let t = k as f64 / (n - 1) as f64;
            FrameWarp::Placed(Similarity::from_params(SimilarityParams {
                ax: -1.2 * t + 0.9 * t * (1.0 - t),
                ay: 0.7 * t - 1.3 * t * (1.0 - t),
                g: -0.003 * t + 0.017 * t * (1.0 - t),
                rot: -0.002 * t,
            }))
        })
        .collect()
}

fn independent_crop() -> align_cmd::CropRect {
    align_cmd::CropRect {
        x: 5,
        y: 3,
        width: 88,
        height: 64,
    }
}

fn independent_expected(frame: &Frame, qx: usize, qy: usize) -> [u16; 3] {
    let at = |dx, dy| {
        f64::from(
            frame.data
                [(frame.active.y + 2 * qy + dy) * frame.stride + frame.active.x + 2 * qx + dx],
        ) - 256.0
    };
    let values = [at(0, 0) * 1.4, (at(1, 0) + at(0, 1)) / 2.0, at(1, 1) * 0.65];
    values.map(|v| (v / 11744.0 * 65535.0).round() as u16)
}

fn independent_near(actual: &[u16], expected: &[u16], tolerance: u16) {
    assert_eq!(actual.len(), expected.len());
    let maximum = actual
        .iter()
        .zip(expected)
        .map(|(a, b)| a.abs_diff(*b))
        .max()
        .unwrap();
    assert!(
        maximum <= tolerance,
        "independent DN oracle max error {maximum} > {tolerance}"
    );
}

fn independent_gray(path: &Path) -> (u32, u32, Vec<u16>) {
    let mut d = tiff::decoder::Decoder::new(fs::File::open(path).unwrap()).unwrap();
    let (w, h) = d.dimensions().unwrap();
    let tiff::decoder::DecodingResult::U16(p) = d.read_image().unwrap() else {
        panic!("not u16");
    };
    assert_eq!(p.len(), (w * h) as usize);
    (w, h, p)
}

#[test]
fn independent_m194_cfa_coordinates_and_crop() {
    let dir = work_dir("independent-coordinates");
    let frames = independent_frames(1, false);
    let mut opts = fixture_options(dir.join("whole.tif"));
    opts.demosaic = false;
    let source = FixtureSource::new(frames.clone());
    run_fixture(&opts, &source, None, None).unwrap();
    assert_eq!(source.counts(), [1]);
    let whole_bytes = fs::read(opts.out.as_ref().unwrap()).unwrap();
    let whole = read_tiff(opts.out.as_ref().unwrap());
    assert_eq!((whole.0, whole.1), (104, 76));
    // Camera-native TIFFs record package version only, even when demosaiced.
    // ICC-bearing colorimetric TIFFs carry the build stamp (checked below).
    // Measurement lineage comes from the separately recorded binary.
    assert_eq!(
        whole.3.trim_end_matches('\0'),
        concat!("strehl ", env!("CARGO_PKG_VERSION"))
    );
    let mut expected = Vec::new();
    for y in 0..76 {
        for x in 0..104 {
            expected.extend(independent_expected(&frames[0], x, y));
        }
    }
    independent_near(&whole.2, &expected, 1);
    assert_ne!(
        independent_expected(&frames[0], 5, 3),
        independent_expected(&frames[0], 0, 0)
    );
    let mut padding = frames.clone();
    for y in 0..padding[0].buffer_height {
        for x in 0..padding[0].stride {
            if !(6..214).contains(&x) || !(2..154).contains(&y) {
                let i = y * padding[0].stride + x;
                padding[0].data[i] = 17;
            }
        }
    }
    opts.out = Some(dir.join("padding-placebo.tif"));
    run_fixture(&opts, &FixtureSource::new(padding), None, None).unwrap();
    assert_eq!(whole_bytes, fs::read(opts.out.as_ref().unwrap()).unwrap());
    let crop = independent_crop();
    opts.out = Some(dir.join("crop.tif"));
    run_fixture(&opts, &FixtureSource::new(frames.clone()), None, Some(crop)).unwrap();
    let cropped = read_tiff(opts.out.as_ref().unwrap());
    assert_eq!((cropped.0, cropped.1), (88, 64));
    let mut crop_expected = Vec::new();
    for y in 3..67 {
        for x in 5..93 {
            crop_expected.extend(independent_expected(&frames[0], x, y));
        }
    }
    independent_near(&cropped.2, &crop_expected, 1);
    opts.demosaic = true;
    opts.out = Some(dir.join("demosaic.tif"));
    run_fixture(&opts, &FixtureSource::new(frames.clone()), None, Some(crop)).unwrap();
    let demosaic = read_tiff(opts.out.as_ref().unwrap());
    assert_eq!((demosaic.0, demosaic.1), (176, 128));
    assert_eq!(
        demosaic.3.trim_end_matches('\0'),
        whole.3.trim_end_matches('\0')
    );
    // MHC interpolates missing channels; the known R and B photosites remain
    // independently checkable, avoiding a copied demosaic oracle.
    for qy in 4..60 {
        for qx in 4..84 {
            let e = independent_expected(&frames[0], qx + 5, qy + 3);
            let r = demosaic.2[(2 * qy * 176 + 2 * qx) * 3];
            let b = demosaic.2[((2 * qy + 1) * 176 + 2 * qx + 1) * 3 + 2];
            independent_near(&[r, b], &[e[0], e[2]], 1);
        }
    }
    println!(
        "M194 INDEPENDENT coordinates: 7904 full + 5632 crop RGB sites; known R/B demosaic; padding placebo PASS {}",
        dir.display()
    );
}

struct IndependentDelegate<'a>(&'a FixtureSource);
impl PyramidFrameSource for IndependentDelegate<'_> {
    fn len(&self) -> usize {
        self.0.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        self.0.decode(index)
    }
}

#[test]
fn independent_m194_delegate_and_live_inputs() {
    let dir = work_dir("independent-live");
    let frames = independent_frames(5, false);
    let track = independent_track(5);
    let crop = independent_crop();
    let mut opts = fixture_options(dir.join("baseline.tif"));
    let direct = FixtureSource::new(frames.clone());
    run_fixture(&opts, &direct, Some(track.clone()), Some(crop)).unwrap();
    let baseline = fs::read(opts.out.as_ref().unwrap()).unwrap();
    let pixels = read_tiff(opts.out.as_ref().unwrap()).2;
    assert_eq!(direct.counts(), vec![1; 5]);
    let delegate_source = FixtureSource::new(frames.clone());
    opts.out = Some(dir.join("delegate.tif"));
    run_fixture_from(
        &opts,
        &frames,
        &IndependentDelegate(&delegate_source),
        Some(track.clone()),
        Some(crop),
    )
    .unwrap();
    assert_eq!(baseline, fs::read(opts.out.as_ref().unwrap()).unwrap());
    assert_eq!(delegate_source.counts(), vec![1; 5]);
    let mut changed_frames = frames.clone();
    for y in 44..94 {
        for x in 68..132 {
            let f = &mut changed_frames[2];
            f.data[(y + f.active.y) * f.stride + x + f.active.x] += 3000;
        }
    }
    let changed = FixtureSource::new(changed_frames);
    opts.out = Some(dir.join("changed-input.tif"));
    run_fixture(&opts, &changed, Some(track.clone()), Some(crop)).unwrap();
    assert_eq!(changed.counts()[2], 1);
    assert_ne!(pixels, read_tiff(opts.out.as_ref().unwrap()).2);
    let mut changed_track = track.clone();
    changed_track[2] = FrameWarp::Placed(Similarity::from_params(SimilarityParams {
        ax: -3.25,
        ay: 2.5,
        g: -0.015,
        rot: 0.006,
    }));
    assert_eq!(track[0], changed_track[0]);
    assert_eq!(track[4], changed_track[4]);
    assert_ne!(track[2], changed_track[2]);
    let FrameWarp::Placed(mid) = track[2] else {
        panic!("interior not placed");
    };
    let FrameWarp::Placed(last) = track[4] else {
        panic!("endpoint not placed");
    };
    assert!(
        (mid.to_params().g - last.to_params().g / 2.0).abs() > 0.004,
        "no curvature"
    );
    opts.out = Some(dir.join("changed-interior-track.tif"));
    run_fixture(
        &opts,
        &FixtureSource::new(frames.clone()),
        Some(changed_track),
        Some(crop),
    )
    .unwrap();
    assert_ne!(pixels, read_tiff(opts.out.as_ref().unwrap()).2);
    opts.out = Some(dir.join("identity.tif"));
    run_fixture(
        &opts,
        &FixtureSource::new(frames.clone()),
        Some(vec![FrameWarp::Placed(Similarity::IDENTITY); 5]),
        Some(crop),
    )
    .unwrap();
    assert_ne!(pixels, read_tiff(opts.out.as_ref().unwrap()).2);
    opts.srgb = true;
    opts.space = image_out::OutputSpace::Srgb;
    opts.out = Some(dir.join("display.tif"));
    let mut display_frames = frames;
    // Explicit invertible synthetic characterisation commissions the matrix,
    // ICC and Software branch; it is not a measured camera characterisation.
    for f in &mut display_frames {
        f.xyz_to_cam_rgbe = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0; 3]];
    }
    run_fixture(
        &opts,
        &FixtureSource::new(display_frames),
        Some(track),
        Some(crop),
    )
    .unwrap();
    let display = read_tiff(opts.out.as_ref().unwrap());
    assert_eq!((display.0, display.1), (176, 128));
    assert_ne!(pixels, display.2);
    assert_eq!(display.3.trim_end_matches('\0'), crate::SOFTWARE);
    let mut tagged =
        tiff::decoder::Decoder::new(fs::File::open(opts.out.as_ref().unwrap()).unwrap()).unwrap();
    assert!(tagged.get_tag(tiff::tags::Tag::IccProfile).is_ok());
    println!(
        "M194 INDEPENDENT live source/delegate/interior curve/identity/display PASS {}",
        dir.display()
    );
}

#[test]
fn independent_m194_refusal_and_errors() {
    let dir = work_dir("independent-refusals");
    let frames = independent_frames(5, false);
    let crop = independent_crop();
    let mut opts = fixture_options(dir.join("decode-failure.tif"));
    let mut source = FixtureSource::new(frames.clone());
    source.fail_at = Some(1);
    let err = run_fixture(&opts, &source, None, Some(crop)).unwrap_err();
    assert!(format!("{err:#}").contains("index 1, call 1"));
    assert_eq!(source.counts()[1], 1);
    assert!(!opts.out.as_ref().unwrap().exists());
    let mut malformed = frames.clone();
    malformed[3].levels.white += 1.0;
    opts.out = Some(dir.join("levels-failure.tif"));
    assert!(
        format!(
            "{:#}",
            run_fixture(&opts, &FixtureSource::new(malformed), None, Some(crop)).unwrap_err()
        )
        .contains("stack was calibrated")
    );
    assert!(!opts.out.as_ref().unwrap().exists());
    let mut count = FixtureSource::new(frames.clone());
    count.declared_len -= 1;
    assert!(
        run_fixture(&opts, &count, None, None)
            .unwrap_err()
            .to_string()
            .contains("source count")
    );
    assert_eq!(count.counts(), vec![0; 5]);
    let mut track = independent_track(5);
    track[2] = FrameWarp::Refused("independent deliberate unplaced interior".into());
    opts.out = Some(dir.join("partial.tif"));
    opts.confidence_map = Some(dir.join("partial-confidence.tif"));
    let source = FixtureSource::new(frames.clone());
    run_fixture(&opts, &source, Some(track.clone()), Some(crop)).unwrap();
    assert_eq!(source.counts(), vec![2; 5]); // Decode precedes placement refusal.
    let bytes = fs::read(opts.out.as_ref().unwrap()).unwrap();
    let confidence = fs::read(opts.confidence_map.as_ref().unwrap()).unwrap();
    let mut changed = frames.clone();
    changed[2].data.fill(11900);
    opts.out = Some(dir.join("refused-frame-placebo.tif"));
    opts.confidence_map = Some(dir.join("refused-frame-placebo-confidence.tif"));
    run_fixture(&opts, &FixtureSource::new(changed), Some(track), Some(crop)).unwrap();
    assert_eq!(bytes, fs::read(opts.out.as_ref().unwrap()).unwrap());
    assert_eq!(
        confidence,
        fs::read(opts.confidence_map.as_ref().unwrap()).unwrap()
    );
    opts.out = Some(dir.join("all-refused.tif"));
    opts.confidence_map = None;
    let source = FixtureSource::new(frames);
    let err = run_fixture(
        &opts,
        &source,
        Some(vec![FrameWarp::Refused("all refused control".into()); 5]),
        Some(crop),
    )
    .unwrap_err();
    assert!(format!("{err:#}").contains("every frame was refused"));
    assert_eq!(source.counts(), vec![1; 5]);
    assert!(!opts.out.as_ref().unwrap().exists());
    println!(
        "M194 INDEPENDENT decode/levels/count/all-refused errors; refused-frame fold+confidence placebo PASS {}",
        dir.display()
    );
}

#[test]
fn independent_m194_malformed_decoded_storage() {
    let dir = work_dir("independent-storage");
    let frames = independent_frames(2, false);
    let mut opts = fixture_options(dir.join("valid.tif"));
    run_fixture(&opts, &FixtureSource::new(frames.clone()), None, None).unwrap();
    let baseline = fs::read(opts.out.as_ref().unwrap()).unwrap();
    // Odd trailing sensels are an existing floor-to-plane contract. They may
    // be present without changing the consumed grid or legitimate padding.
    let mut odd_tail = frames.clone();
    odd_tail[1].active.width += 1;
    odd_tail[1].active.height += 1;
    opts.out = Some(dir.join("odd-tail.tif"));
    run_fixture_from(&opts, &frames, &FixtureSource::new(odd_tail), None, None).unwrap();
    assert_eq!(baseline, fs::read(opts.out.as_ref().unwrap()).unwrap());
    for case in [
        "zero-stride",
        "truncated-storage",
        "smaller-active",
        "overflow-x",
        "overflow-y",
        "active-past-stride",
        "zero-active",
        "overflow-storage",
    ] {
        let mut malformed = frames.clone();
        let f = &mut malformed[1];
        match case {
            "zero-stride" => f.stride = 0,
            "truncated-storage" => {
                f.data.pop();
            }
            "smaller-active" => f.active.width -= 2,
            "overflow-x" => f.active.x = usize::MAX,
            "overflow-y" => f.active.y = usize::MAX,
            "active-past-stride" => f.active.x = f.stride - 1,
            "zero-active" => f.active.width = 0,
            "overflow-storage" => {
                f.stride = usize::MAX;
                f.buffer_height = 2;
            }
            _ => unreachable!(),
        }
        opts.out = Some(dir.join(format!("{case}.tif")));
        let source = FixtureSource::new(malformed);
        let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            run_fixture_from(&opts, &frames, &source, None, None)
        }));
        let err = outcome
            .unwrap_or_else(|_| panic!("{case} panicked instead of returning Err"))
            .expect_err(case);
        assert_eq!(source.counts()[1], 1);
        assert!(!opts.out.as_ref().unwrap().exists());
        println!("M194 INDEPENDENT malformed {case}: refused {err:#}");
    }
    println!(
        "M194 INDEPENDENT storage: 8 malformed sources refused + odd-tail byte placebo PASS {}",
        dir.display()
    );
}

#[test]
fn independent_m194_confidence_source_and_null() {
    let dir = work_dir("independent-confidence");
    let debug = std::env::var("STREHL_CONFIDENCE_DEBUG").ok();
    for flat in [false, true] {
        let label = if flat { "null" } else { "texture" };
        let frames = independent_frames(5, flat);
        assert!(frames.iter().all(|f| !f.path.exists()));
        let mut opts = fixture_options(dir.join(format!("{label}-off.tif")));
        let source = FixtureSource::new(frames.clone());
        run_fixture(&opts, &source, None, None).unwrap();
        assert_eq!(source.counts(), vec![1; 5]);
        let bytes = fs::read(opts.out.as_ref().unwrap()).unwrap();
        if flat {
            let p = read_tiff(opts.out.as_ref().unwrap()).2;
            let first = &p[(40 * 208 + 40) * 3..(40 * 208 + 40) * 3 + 3];
            assert!(
                first[0] != first[1] && first[1] != first[2],
                "null lost distinct CFA colors"
            );
            for y in 8..144 {
                for x in 8..200 {
                    independent_near(&p[(y * 208 + x) * 3..(y * 208 + x) * 3 + 3], first, 1);
                }
            }
        }
        opts.out = Some(dir.join(format!("{label}-on.tif")));
        opts.confidence_map = Some(dir.join(format!("{label}-confidence.tif")));
        let source = FixtureSource::new(frames.clone());
        run_fixture(&opts, &source, None, None).unwrap();
        assert_eq!(source.counts(), vec![2; 5]);
        assert_eq!(bytes, fs::read(opts.out.as_ref().unwrap()).unwrap());
        let c = independent_gray(opts.confidence_map.as_ref().unwrap());
        assert_eq!((c.0, c.1), (104, 76));
        if let Some(debug_dir) = &debug {
            for name in ["dmin", "dsharp", "spread", "centrality", "withinfrac"] {
                let path = Path::new(debug_dir).join(format!("{name}.tiff"));
                let g = independent_gray(&path);
                assert_eq!((g.0, g.1), (104, 76));
                if name == "centrality" {
                    assert_eq!(c.2, g.2);
                }
                fs::copy(&path, dir.join(format!("{label}-debug-{name}.tif"))).unwrap();
            }
        }
        let mut fail = FixtureSource::new(frames);
        fail.fail_on_call = Some((3, 2));
        opts.out = Some(dir.join(format!("{label}-observer-failure.tif")));
        opts.confidence_map = Some(dir.join(format!("{label}-observer-failure-confidence.tif")));
        let err = run_fixture(&opts, &fail, None, None).unwrap_err();
        assert!(format!("{err:#}").contains("index 3, call 2"));
        assert_eq!(fail.counts()[3], 2);
        assert!(!opts.out.as_ref().unwrap().exists());
        assert!(!opts.confidence_map.as_ref().unwrap().exists());
    }
    println!(
        "M194 INDEPENDENT confidence + null, second-pass failure, debug={} PASS {}",
        debug.is_some(),
        dir.display()
    );
}
