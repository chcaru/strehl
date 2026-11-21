//! Region-only repair (E4) against the full render with the same repair, on
//! the production writer and a generated stack.
use super::*;
use crate::merge_cmd::{RegionOnly, ca_refine};
use strehl_edit::{Adjustments, DevelopmentRecipe, RegionAdjustment, RegionShape, SourceRange};

fn frames() -> Vec<Frame> {
    (0..6)
        .map(|k| {
            let mut frame = fixture_frame(128, 96, k * 13);
            frame.xyz_to_cam_rgbe = [
                [0.64, 0.25, 0.10],
                [0.20, 0.73, 0.08],
                [0.05, 0.13, 0.92],
                [0.0; 3],
            ];
            frame
        })
        .collect()
}

/// A depth-brush stroke, soft-edged, taking frames 2 and 3 only.
fn stroke() -> RegionAdjustment {
    RegionAdjustment {
        id: "brush".into(),
        name: "Leg joint".into(),
        note: String::new(),
        shape: RegionShape::stroke_from_path(
            &(0..120)
                .map(|k| {
                    let t = k as f32 / 119.0;
                    [0.2 + 0.55 * t, 0.45 + 0.2 * (t * 5.0).sin()]
                })
                .collect::<Vec<_>>(),
            [0.07, 0.09],
        ),
        feather: 0.5,
        enabled: true,
        adjustments: Adjustments::default(),
        source_range: Some(SourceRange { first: 2, last: 3 }),
    }
}

fn saved(dir: &Path, regions: Vec<RegionAdjustment>) -> PathBuf {
    let recipe = DevelopmentRecipe {
        regions,
        ..Default::default()
    };
    let path = dir.join("recipe.json");
    fs::write(&path, serde_json::to_vec_pretty(&recipe).unwrap()).unwrap();
    path
}

fn render(
    dir: &Path,
    name: &str,
    recipe: Option<&Path>,
    original: Option<RegionOnly>,
) -> Result<(PathBuf, PathBuf)> {
    let mut opts = fixture_options(dir.join(format!("{name}.tiff")));
    opts.pyramid = MergeConfig {
        bands: 3,
        ..Default::default()
    };
    opts.srgb = true;
    opts.space = image_out::OutputSpace::Srgb;
    opts.linear_master = Some(dir.join(format!("{name}-master.tiff")));
    opts.region_recipe = recipe.map(Path::to_path_buf);
    opts.region_only = original;
    run_fixture(&opts, &FixtureSource::new(frames()), None, None)?;
    Ok((opts.linear_master.unwrap(), opts.out.unwrap()))
}

/// Per output pixel, from the recipe alone: does its 5 x 5 stencil meet a
/// site the region reaches at all, and is every site in it fully covered?
fn stencils(region: &RegionAdjustment, w: usize, h: usize) -> (Vec<bool>, Vec<bool>) {
    let (gw, gh) = (w / 2, h / 2);
    // The engine's site centres: (2x + cx) / 2W + 0.25 / W, with 2x + cx
    // the output column, and the same for rows.
    let weight = |x: usize, y: usize| {
        let uv = [
            x as f32 / (2 * gw) as f32 + 0.25 / gw as f32,
            y as f32 / (2 * gh) as f32 + 0.25 / gh as f32,
        ];
        region.shape.weight(uv, region.feather)
    };
    let site: Vec<f32> = (0..w * h).map(|i| weight(i % w, i / w)).collect();
    let mut touched = vec![false; w * h];
    let mut exact = vec![false; w * h];
    for y in 0..h {
        for x in 0..w {
            let around = (y.saturating_sub(2)..=(y + 2).min(h - 1)).flat_map(|yy| {
                (x.saturating_sub(2)..=(x + 2).min(w - 1)).map(move |xx| yy * w + xx)
            });
            let weights: Vec<f32> = around.map(|i| site[i]).collect();
            touched[y * w + x] = weights.iter().any(|&v| v > 0.0);
            exact[y * w + x] = weights.iter().all(|&v| v >= 1.0);
        }
    }
    (touched, exact)
}

#[test]
fn region_only_keeps_the_original_outside_and_matches_the_full_repair_inside() {
    let dir = work_dir("region-only");
    let (a_master, a_photo) = render(&dir, "original", None, None).unwrap();
    let recipe = saved(&dir, vec![stroke()]);
    let (b_master, _) = render(&dir, "full", Some(&recipe), None).unwrap();
    let (c_master, c_photo) = render(
        &dir,
        "region",
        Some(&recipe),
        Some(RegionOnly {
            master: a_master.clone(),
            photo: a_photo.clone(),
        }),
    )
    .unwrap();
    let a = strehl_edit::load_tiff(&a_master).unwrap();
    let b = strehl_edit::load_tiff(&b_master).unwrap();
    let c = strehl_edit::load_tiff(&c_master).unwrap();
    let (w, h) = (a.width as usize, a.height as usize);
    let (touched, exact) = stencils(&stroke(), w, h);
    let (_, _, a_rgb, _) = read_tiff(&a_photo);
    let (_, _, c_rgb, _) = read_tiff(&c_photo);
    let (mut kept, mut same, mut ring, mut worst) = (0, 0, 0, 0.0f32);
    let mut changed = 0;
    for i in 0..w * h {
        fn px(img: &strehl_edit::LinearImage, i: usize) -> &[f32] {
            &img.pixels[3 * i..3 * i + 3]
        }
        if !touched[i] {
            kept += 1;
            for k in 0..3 {
                assert_eq!(
                    px(&c, i)[k].to_bits(),
                    px(&a, i)[k].to_bits(),
                    "master pixel {i} outside"
                );
            }
            assert_eq!(
                c_rgb[3 * i..3 * i + 3],
                a_rgb[3 * i..3 * i + 3],
                "photo pixel {i} outside"
            );
            continue;
        }
        if px(&c, i) != px(&a, i) {
            changed += 1;
        }
        if exact[i] {
            same += 1;
            for k in 0..3 {
                assert_eq!(
                    px(&c, i)[k].to_bits(),
                    px(&b, i)[k].to_bits(),
                    "master pixel {i} inside"
                );
            }
        } else {
            ring += 1;
            // Against the pixel's largest channel: a near-black channel of a
            // bright pixel is not where an error shows.
            let scale = px(&b, i).iter().fold(1e-3f32, |m, v| m.max(v.abs()));
            for k in 0..3 {
                worst = worst.max((px(&c, i)[k] - px(&b, i)[k]).abs() / scale);
            }
        }
    }
    assert!(
        kept > 1000 && same > 200 && ring > 500,
        "{kept} {same} {ring}"
    );
    assert!(changed > 500, "the repair changed {changed} pixels");
    assert!(
        worst < 1e-5,
        "ring differs from the full repair by {worst:e} of the pixel's largest channel"
    );
    assert_eq!(c.baseline, a.baseline, "the tone is the original's");
    let applied: DevelopmentRecipe = serde_json::from_slice(&fs::read(&recipe).unwrap()).unwrap();
    assert_eq!(c.baked_recipe.as_ref(), Some(&applied));
    assert_eq!(b.baked_recipe.as_ref(), Some(&applied));
}

#[test]
fn region_only_refuses_an_original_of_another_size_or_without_a_tone() {
    let dir = work_dir("region-only-refusals");
    let recipe = saved(&dir, vec![stroke()]);
    // Another geometry: a 64 x 48 stack's master.
    let mut small = fixture_options(dir.join("small.tiff"));
    small.srgb = true;
    small.space = image_out::OutputSpace::Srgb;
    small.linear_master = Some(dir.join("small-master.tiff"));
    small.pyramid = MergeConfig {
        bands: 3,
        ..Default::default()
    };
    let little: Vec<_> = (0..2)
        .map(|k| {
            let mut f = fixture_frame(64, 48, k);
            f.xyz_to_cam_rgbe = frames()[0].xyz_to_cam_rgbe;
            f
        })
        .collect();
    run_fixture(&small, &FixtureSource::new(little), None, None).unwrap();
    let error = render(
        &dir,
        "mismatch",
        Some(&recipe),
        Some(RegionOnly {
            master: small.linear_master.clone().unwrap(),
            photo: small.out.clone().unwrap(),
        }),
    )
    .unwrap_err();
    assert!(format!("{error:#}").contains("this render"), "{error:#}");
    // No region with a source range: nothing to rebuild.
    let (a_master, a_photo) = render(&dir, "original", None, None).unwrap();
    let mut plain = stroke();
    plain.source_range = None;
    let plain = saved(&dir, vec![plain]);
    let error = render(
        &dir,
        "plain",
        Some(&plain),
        Some(RegionOnly {
            master: a_master,
            photo: a_photo,
        }),
    )
    .unwrap_err();
    assert!(format!("{error:#}").contains("source range"), "{error:#}");
}

#[test]
fn the_ca_refinement_is_read_back_from_a_render_log() {
    // The weevil run's own lines (2026-11-04 build): rounded, then applied.
    let old = "collapse+write  : 1.1 s\n\
        CA refinement   : measured red t (+0.010, -0.027) px, scale +444.6 ppm (198 of 198 tiles, rms 0.177 px)\n\
        \x20                 measured blue t (-0.036, +0.058) px, scale -194.0 ppm (197 of 198 tiles, rms 0.119 px)\n\
        \x20                 APPLIED on top of the profile for the render below\n\
        lateral CA      : CORRECTING\n";
    let reused = ca_refine::parse_reused(old.as_bytes()).unwrap();
    assert!(!reused.exact);
    let r = reused.refinement.unwrap();
    assert_eq!(r.red.translation, (0.010, -0.027));
    assert!((r.red.scale - 444.6e-6).abs() < 1e-12);
    assert_eq!(r.blue.translation, (-0.036, 0.058));
    assert!((r.blue.scale + 194.0e-6).abs() < 1e-12);
    // This build adds the exact line, which wins over the rounded ones.
    let exact = strehl_core::optics::CaRefinement {
        red: strehl_core::optics::ChannelRefinement {
            scale: 4.4461234567891e-4,
            translation: (0.010_234_567_8, -0.027_111_222_333),
        },
        blue: strehl_core::optics::ChannelRefinement {
            scale: -1.9401e-4,
            translation: (-0.0361, 0.058_000_000_1),
        },
    };
    let new = format!(
        "{}{}\nlateral CA      : CORRECTING\n",
        old.lines().take(4).collect::<Vec<_>>().join("\n") + "\n",
        ca_refine::exact_line(&exact)
    );
    let reused = ca_refine::parse_reused(new.as_bytes()).unwrap();
    assert!(reused.exact);
    assert_eq!(reused.refinement, Some(exact));
    // Refused by its bounds, or never measured: reused as none.
    let refused = "CA refinement   : measured red t (+2.0, 0.0) px, scale +9000.0 ppm (1 of 1 tiles, rms 0.1 px)\n\
        \x20                 measured blue t (0.0, 0.0) px, scale 0.0 ppm (1 of 1 tiles, rms 0.1 px)\n\
        \x20                 NOT APPLIED -- beyond the bounds (1000 ppm, 1.5 px)\n";
    assert_eq!(
        ca_refine::parse_reused(refused.as_bytes())
            .unwrap()
            .refinement,
        None
    );
    let none = "lateral CA      : off\nwrote           : x.tiff\n";
    assert_eq!(
        ca_refine::parse_reused(none.as_bytes()).unwrap().refinement,
        None
    );
    // An applied refinement the log never stated is an error, not a guess.
    let broken = "CA refinement   : measured red t (+0.010, -0.027) px, scale +444.6 ppm (1 of 1 tiles, rms 0.1 px)\n\
        \x20                 APPLIED on top of the profile for the render below\n";
    assert!(ca_refine::parse_reused(broken.as_bytes()).is_err());
}
