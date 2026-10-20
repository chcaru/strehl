//! Independently chosen controls: non-neutral colors, concave masks and a
//! crop away from the annotation origin. These do not claim photo quality.
use strehl_edit::*;

fn constant(w: u32, h: u32, rgb: [f32; 3]) -> LinearImage {
    LinearImage {
        width: w,
        height: h,
        pixels: (0..w * h).flat_map(|_| rgb).collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}
fn mask(shape: RegionShape) -> RegionAdjustment {
    RegionAdjustment {
        id: "review".into(),
        name: "review".into(),
        note: String::new(),
        shape,
        feather: 0.0,
        enabled: true,
        adjustments: Adjustments {
            exposure: 1.0,
            ..Default::default()
        },
        source_range: None,
    }
}

#[test]
fn off_center_crop_keeps_concave_region_and_cfa_image_coordinates() {
    let image = constant(80, 48, [0.18, 0.09, 0.045]);
    let shape = RegionShape::Polygon {
        points: vec![
            [0.5, 0.2],
            [0.9, 0.2],
            [0.9, 0.4],
            [0.7, 0.4],
            [0.7, 0.9],
            [0.5, 0.9],
        ],
    };
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(mask(shape));
    let full = image.render_sdr8(&recipe).unwrap();
    let (w, h, crop) = image
        .render_region_sdr8(&recipe, [0.4, 0.25], [1.0, 1.0], 100)
        .unwrap();
    assert_eq!((w, h), (48, 36));
    for y in 0..36usize {
        for x in 0..48usize {
            let a = ((y + 12) * 80 + x + 32) * 3;
            let b = (y * 48 + x) * 3;
            assert_eq!(&crop[b..b + 3], &full[a..a + 3], "crop coordinates {x},{y}");
        }
    }
    let sample = |x: usize, y: usize| full[(y * 80 + x) * 3];
    assert_eq!(sample(45, 30), 162); // +1 stop at linear .18 -> .36.
    assert_eq!(sample(65, 30), 118); // Concavity: outside despite being in bounds.
    assert_eq!(sample(25, 30), 118);
    let mut reverse = recipe.clone();
    let RegionShape::Polygon { points } = &mut reverse.regions[0].shape else {
        unreachable!()
    };
    points.reverse();
    assert_eq!(
        image.render_sdr8(&reverse).unwrap(),
        full,
        "winding must not invert the mask"
    );
}

#[test]
fn repair_provenance_keeps_order_geometry_and_feather_but_allows_tone_edits() {
    let mut recipe = DevelopmentRecipe::default();
    for (id, span, shape) in [
        (
            "rectangle",
            SourceRange { first: 3, last: 7 },
            RegionShape::Rectangle {
                min: [0.2, 0.1],
                max: [0.8, 0.8],
            },
        ),
        (
            "ellipse",
            SourceRange {
                first: 10,
                last: 11,
            },
            RegionShape::Ellipse {
                center: [0.6, 0.4],
                radius: [0.1, 0.2],
            },
        ),
    ] {
        let mut r = mask(shape);
        r.id = id.into();
        r.source_range = Some(span);
        r.feather = 0.35;
        recipe.regions.push(r);
    }
    let mut image = constant(32, 24, [-0.02, 1.4, 0.17]);
    image.baked_recipe = Some(recipe.clone());
    let temp = tempfile::tempdir().unwrap();
    let path = temp.path().join("master.tiff");
    save_linear_tiff(&path, &image).unwrap();
    let image = load_tiff(&path).unwrap();
    image.validate_source_repairs(&recipe).unwrap();
    let mut changed = recipe.clone();
    changed.global.temperature = 30.0;
    changed.regions[0].adjustments.exposure = -0.5;
    changed.regions[0].name = "Renamed, same reconstruction".into();
    image.validate_source_repairs(&changed).unwrap();
    for axis in 0..4 {
        let mut wrong = recipe.clone();
        match axis {
            0 => wrong.regions.swap(0, 1),
            1 => wrong.regions[0].feather = 0.5,
            2 => wrong.regions[0].enabled = false,
            _ => {
                wrong.regions[0].shape = RegionShape::Rectangle {
                    min: [0.1, 0.1],
                    max: [0.8, 0.8],
                }
            }
        }
        assert!(
            image.validate_source_repairs(&wrong).is_err(),
            "wrong repair {axis} accepted"
        );
    }
    assert_eq!(image.pixels[0].to_bits(), (-0.02f32).to_bits());
    assert_eq!(image.pixels[1].to_bits(), 1.4f32.to_bits());
}

#[test]
fn tagged_foreign_rgb_profile_is_refused_instead_of_assumed_srgb() {
    use std::fs::File;
    use tiff::{
        decoder::Decoder,
        encoder::{TiffEncoder, colortype},
        tags::Tag,
    };
    let temp = tempfile::tempdir().unwrap();
    let known = temp.path().join("known.tiff");
    save_sdr_tiff(
        &known,
        &constant(32, 24, [0.18; 3]),
        &DevelopmentRecipe::default(),
    )
    .unwrap();
    let mut decoder = Decoder::new(File::open(&known).unwrap()).unwrap();
    let mut profile = decoder.get_tag_u8_vec(Tag::Unknown(34675)).unwrap();
    // Keep a syntactically intact matrix/TRC ICC but change its colorimetry.
    // This is the kind of input a reader must transform or explicitly refuse.
    let count = u32::from_be_bytes(profile[128..132].try_into().unwrap()) as usize;
    let mut changed = false;
    for i in 0..count {
        let entry = 132 + i * 12;
        if &profile[entry..entry + 4] == b"rXYZ" {
            let offset =
                u32::from_be_bytes(profile[entry + 4..entry + 8].try_into().unwrap()) as usize;
            let x = i32::from_be_bytes(profile[offset + 8..offset + 12].try_into().unwrap());
            profile[offset + 8..offset + 12].copy_from_slice(&(x + 3277).to_be_bytes());
            changed = true;
        }
    }
    assert!(
        changed,
        "foreign-profile adversary failed to change a primary"
    );
    let foreign = temp.path().join("foreign.tiff");
    let mut encoder = TiffEncoder::new(File::create(&foreign).unwrap()).unwrap();
    let mut out = encoder.new_image::<colortype::RGB16>(32, 24).unwrap();
    out.encoder()
        .write_tag(Tag::Unknown(34675), profile.as_slice())
        .unwrap();
    out.write_data(&vec![32000u16; 32 * 24 * 3]).unwrap();
    drop(encoder);
    assert!(
        load_tiff(&foreign).is_err(),
        "foreign ICC was silently interpreted as sRGB"
    );
    assert_eq!(
        load_tiff(&known).unwrap().origin,
        ImageOrigin::DisplayReferred
    );
}
