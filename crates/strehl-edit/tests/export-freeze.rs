//! Byte freeze for exports and recipe files that use no P7 option.
//! The hashes were recorded by this file at commit 61effa01b, before the P7
//! export split. Failure witness: any change to development, encoding or
//! serialization of an option-free export makes a hash differ.
//!
//! Since h-develop (2026-11-22) every PNG, JPEG and AVIF also names Strehl
//! (`metadata.rs`). The stamp is purely additive, and this file proves it:
//! the stamp's chunks (PNG) and segments (JPEG) are removed, and an AVIF is
//! rebuilt from its own AV1 payload and colour properties without the Exif
//! item, and the result must still hash to the 61effa01b bytes. TIFFs carried
//! their stamp (Software) already and are compared whole.
mod common;

use sha2::{Digest, Sha256};
use std::sync::atomic::AtomicBool;
use strehl_edit::*;

/// The file as it was before the stamp, after checking that the stamp is
/// there and says Strehl.
fn unstamped(name: &str, bytes: &[u8]) -> Vec<u8> {
    if name.contains("-Tiff") || name == "coverage-Tiff" {
        return bytes.to_vec();
    }
    if name.contains("-Png") || name == "coverage-Png" {
        let mut out = bytes[..8].to_vec();
        let (mut software, mut xmp) = (false, false);
        let mut at = 8;
        while at < bytes.len() {
            let n = u32::from_be_bytes(bytes[at..at + 4].try_into().unwrap()) as usize;
            let chunk = &bytes[at..at + 12 + n];
            let (kind, data) = (&chunk[4..8], &chunk[8..8 + n]);
            if kind == b"tEXt" && data == b"Software\0Strehl" {
                software = true;
            } else if kind == b"iTXt" && data.starts_with(b"XML:com.adobe.xmp\0") {
                let text = std::str::from_utf8(&data[22..]).unwrap();
                assert!(text.contains("<xmp:CreatorTool>Strehl</xmp:CreatorTool>"));
                xmp = true;
            } else {
                out.extend_from_slice(chunk);
            }
            at += 12 + n;
        }
        assert!(software && xmp, "{name} is not stamped");
        return out;
    }
    if name.contains("-Jpeg") {
        let mut out = bytes[..2].to_vec();
        let (mut exif, mut xmp) = (false, false);
        let mut at = 2;
        loop {
            let marker = bytes[at + 1];
            let n = u16::from_be_bytes([bytes[at + 2], bytes[at + 3]]) as usize;
            let segment = &bytes[at..at + 2 + n];
            let payload = &segment[4..];
            if marker == 0xe1 && payload.starts_with(b"Exif\0\0") {
                assert_eq!(
                    common::ifd_ascii(&payload[6..]),
                    vec![(305, "Strehl".into())]
                );
                exif = true;
            } else if marker == 0xe1 && payload.starts_with(b"http://ns.adobe.com/xap/1.0/\0") {
                let text = std::str::from_utf8(&payload[29..]).unwrap();
                assert!(text.contains("<xmp:CreatorTool>Strehl</xmp:CreatorTool>"));
                xmp = true;
            } else {
                out.extend_from_slice(segment);
            }
            at += 2 + n;
            if marker == 0xda {
                out.extend_from_slice(&bytes[at..]);
                break;
            }
        }
        assert!(exif && xmp, "{name} is not stamped");
        return out;
    }
    assert!(name.contains("-Avif"), "{name}");
    let avif = common::read_avif(bytes);
    assert_eq!(
        common::ifd_ascii(avif.exif_tiff().expect("an Exif item")),
        vec![(305, "Strehl".into())],
        "{name}"
    );
    use avif_serialize::{Aviffy, constants as c};
    let hdr = name.ends_with("-true");
    let (primaries, matrix) = if name.contains("-Rec2020-") {
        (c::ColorPrimaries::Bt2020, c::MatrixCoefficients::Bt2020Ncl)
    } else if name.contains("-DisplayP3-") {
        (c::ColorPrimaries::DisplayP3, c::MatrixCoefficients::Bt709)
    } else {
        (c::ColorPrimaries::Bt709, c::MatrixCoefficients::Bt709)
    };
    let transfer = if hdr {
        c::TransferCharacteristics::Smpte2084
    } else {
        c::TransferCharacteristics::Srgb
    };
    let colr = avif.colr.expect("colour properties");
    assert_eq!(
        colr,
        (primaries as u16, transfer as u16, matrix as u16, true),
        "{name}"
    );
    let mut container = Aviffy::new();
    container
        .set_color_primaries(primaries)
        .set_transfer_characteristics(transfer)
        .set_matrix_coefficients(matrix)
        .set_full_color_range(true)
        .set_chroma_subsampling((false, false));
    if hdr {
        let (max, average) = avif.clli.expect("an HDR file states its light level");
        container.set_content_light_level(max, average);
    }
    let payload = avif.item(b"av01").expect("the image item");
    container.to_vec(payload, None, avif.size[0], avif.size[1], 10)
}

fn hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

fn scene() -> LinearImage {
    LinearImage {
        width: 64,
        height: 40,
        pixels: (0..64 * 40)
            .flat_map(|i| {
                let (x, y) = ((i % 64) as f32, (i / 64) as f32);
                let r = 0.002 + 0.03 * x + 0.4 * ((x * 0.7).sin() * (y * 0.3).cos()).abs();
                let g = 0.01 + 0.02 * y + 0.2 * ((x + y) * 0.21).sin().abs();
                let b = -0.01 + 0.05 * ((x * y) % 7.0);
                [r, g, b]
            })
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

fn placed() -> LinearImage {
    LinearImage {
        baseline: Some(DisplayBaseline {
            black: 0.004,
            white: 1.4,
            contrast: 0.55,
            exposure_gain: 1.3,
            shoulder: None,
        }),
        ..scene()
    }
}

fn display() -> LinearImage {
    let mut image = scene();
    image.origin = ImageOrigin::DisplayReferred;
    image.pixels.iter_mut().for_each(|v| *v = v.clamp(0.0, 1.0));
    image
}

fn region(id: &str, shape: RegionShape, exposure: f32, enabled: bool) -> RegionAdjustment {
    RegionAdjustment {
        id: id.into(),
        name: format!("Region {id}"),
        note: String::new(),
        shape,
        feather: 0.4,
        enabled,
        adjustments: Adjustments {
            exposure,
            saturation: 20.0,
            temperature: -15.0,
            ..Default::default()
        },
        source_range: None,
    }
}

fn edited() -> DevelopmentRecipe {
    DevelopmentRecipe {
        global: Adjustments {
            exposure: 0.4,
            contrast: 18.0,
            highlights: -30.0,
            shadows: 25.0,
            whites: 5.0,
            blacks: -8.0,
            vibrance: 12.0,
            saturation: 6.0,
            temperature: 9.0,
            tint: -4.0,
        },
        regions: vec![
            region(
                "e",
                RegionShape::Ellipse {
                    center: [0.3, 0.4],
                    radius: [0.2, 0.3],
                },
                0.8,
                true,
            ),
            region(
                "r",
                RegionShape::Rectangle {
                    min: [0.55, 0.1],
                    max: [0.95, 0.6],
                },
                -0.7,
                true,
            ),
            region(
                "p",
                RegionShape::Polygon {
                    points: vec![[0.1, 0.9], [0.5, 0.55], [0.8, 0.95]],
                },
                1.2,
                true,
            ),
            region(
                "off",
                RegionShape::Ellipse {
                    center: [0.5, 0.5],
                    radius: [0.5, 0.5],
                },
                3.0,
                false,
            ),
        ],
        ..Default::default()
    }
}

fn settings(format: ExportFormat, color_space: OutputColorSpace, hdr: bool) -> ExportSettings {
    let mut settings: ExportSettings = serde_json::from_value(serde_json::json!({
        "format": format,
        "color_space": color_space,
        "hdr": hdr,
        "quality": 90,
        "speed": 10,
    }))
    .unwrap();
    // Before P7 every TIFF carried the recipe; the freeze pins that behaviour.
    if format == ExportFormat::Tiff {
        settings = with_recipe_switch(settings);
    }
    settings
}

/// The pre-P7 TIFF always carried the recipe; P7 made it a switch (off).
fn with_recipe_switch(mut settings: ExportSettings) -> ExportSettings {
    settings.embed_recipe = true;
    settings
}

fn cases() -> Vec<(String, Vec<u8>)> {
    let dir = tempfile::tempdir().unwrap();
    let mut out = Vec::new();
    let images = [
        ("scene", scene()),
        ("placed", placed()),
        ("display", display()),
    ];
    let recipes = [
        ("neutral", DevelopmentRecipe::default()),
        ("edited", edited()),
    ];
    let spaces = [
        OutputColorSpace::Srgb,
        OutputColorSpace::DisplayP3,
        OutputColorSpace::Rec2020,
    ];
    for (image_name, image) in &images {
        for (recipe_name, recipe) in &recipes {
            for space in spaces {
                let mut formats = vec![
                    (ExportFormat::Tiff, false),
                    (ExportFormat::Png, false),
                    (ExportFormat::Jpeg, false),
                    (ExportFormat::Avif, false),
                ];
                if image.origin == ImageOrigin::SceneLinear {
                    formats.push((ExportFormat::Avif, true));
                }
                for (format, hdr) in formats {
                    let name = format!("{image_name}-{recipe_name}-{space:?}-{format:?}-{hdr}");
                    let path = dir.path().join(&name);
                    export_image(
                        &path,
                        image,
                        recipe,
                        &settings(format, space, hdr),
                        &AtomicBool::new(false),
                    )
                    .unwrap();
                    out.push((name, std::fs::read(&path).unwrap()));
                }
            }
        }
    }
    let mask: Vec<u8> = (0..64 * 40)
        .map(|i| {
            if (i % 64) < 50 && (i / 64) > 3 {
                255
            } else {
                0
            }
        })
        .collect();
    for format in [ExportFormat::Tiff, ExportFormat::Png] {
        let name = format!("coverage-{format:?}");
        let path = dir.path().join(&name);
        export_image_with_coverage(
            &path,
            &scene(),
            &edited(),
            &settings(format, OutputColorSpace::Srgb, false),
            &AtomicBool::new(false),
            Some(&mask),
        )
        .unwrap();
        out.push((name, std::fs::read(&path).unwrap()));
    }
    out
}

/// Recorded at 61effa01b. AVIF fixtures are one 64x64 superblock, so the
/// encoder's tile count (thread-dependent) cannot change them.
const FROZEN: &[(&str, &str)] = &[
    (
        "scene-neutral-Srgb-Tiff-false",
        "4f671781ee8e81396aa37ea28d259a47aabc7e0535509c0c1623fee1a709a72d",
    ),
    (
        "scene-neutral-Srgb-Png-false",
        "68ec909874f1e9252e512c284e9b240f67ea0f503185072a10fd2ce2212e9015",
    ),
    (
        "scene-neutral-Srgb-Jpeg-false",
        "8362c0b0c65e2a8a53ac6ea633052be17ce2dd497c533f395178d4e6b14d740a",
    ),
    (
        "scene-neutral-Srgb-Avif-false",
        "a42813fb215da8c81fce5eb73e30e25728d30ce419c28517179363ed66d31ca4",
    ),
    (
        "scene-neutral-Srgb-Avif-true",
        "11d34d27f30e30664acc42de94beab8adf84aebc6cfd1aa7daa305bd6d942cca",
    ),
    (
        "scene-neutral-DisplayP3-Tiff-false",
        "ee9df65c677f1b8fbce14e63e59802a57e1cf573d62ae5411831d8b538564322",
    ),
    (
        "scene-neutral-DisplayP3-Png-false",
        "1b49a84ae1d01f845cfec54cd5efe9b182151883e25b12bca8acbc461754b71d",
    ),
    (
        "scene-neutral-DisplayP3-Jpeg-false",
        "a546812385a72c7056bff550dd544db42a3f20b15a9e9aae578798860a6e8efe",
    ),
    (
        "scene-neutral-DisplayP3-Avif-false",
        "1e6735625b673d3688bf07dbd4d8168bce4fc27260cee076029732aad2d99953",
    ),
    (
        "scene-neutral-DisplayP3-Avif-true",
        "978c4f6c916e8cb9e06c1ae7a6a3902992861d5e773f2e641248faa5a4f02eb0",
    ),
    (
        "scene-neutral-Rec2020-Tiff-false",
        "ec14782d282485e65424cbb90ee3a9cee3548312c6adfb60eefd109f13304a6b",
    ),
    (
        "scene-neutral-Rec2020-Png-false",
        "f80aa68c08aaa905cce90d2f700867d08f670843175351a56e733df3377bd19e",
    ),
    (
        "scene-neutral-Rec2020-Jpeg-false",
        "c0fac5ea07a2c525f5f18c921cd17ee0135fab9fb13c3714ea33a07a36529ebc",
    ),
    (
        "scene-neutral-Rec2020-Avif-false",
        "52d526ec66889f54372c3e5044cffb11ee1313633e2dabc2f137c9dfdf859d10",
    ),
    (
        "scene-neutral-Rec2020-Avif-true",
        "8b874b6416a5e0de25c3c54553724d5bc0d2df332fd519abd5372122ed9b231f",
    ),
    (
        "scene-edited-Srgb-Tiff-false",
        "f374a02276fc18bb6ec65ae3d2ebad1f9c0214df93a766e4ecd4f90292e5292d",
    ),
    (
        "scene-edited-Srgb-Png-false",
        "d073770e3c5d218c941c43dc39cb976f50638ca987f74448f2afc76192c11c4b",
    ),
    (
        "scene-edited-Srgb-Jpeg-false",
        "2d3812a95b500e955b0290dc4e0f2ad2374f1bd36abc58a1c11a99ec9cc00595",
    ),
    (
        "scene-edited-Srgb-Avif-false",
        "2ac29d02649bea4b7a8caca0e09d41216fcb58b456ab11b62530d3430e454917",
    ),
    (
        "scene-edited-Srgb-Avif-true",
        "bc6447fddf79ecd0ca5d2a4c75542990d966815a900038cd3d3be3bdef4cf5aa",
    ),
    (
        "scene-edited-DisplayP3-Tiff-false",
        "7b263f74f67c45c0dacac3e79a4c48c08f9a99c4f49c3a69460dd7f92b7fe97c",
    ),
    (
        "scene-edited-DisplayP3-Png-false",
        "e06412bdee060dd002188250b37ff2bda38c95a2062e8bdbf88e356b62406be5",
    ),
    (
        "scene-edited-DisplayP3-Jpeg-false",
        "16edaf1195eb4ff9643c200b3ca3e2a858e8df13ad93b93c885146c45e7e415f",
    ),
    (
        "scene-edited-DisplayP3-Avif-false",
        "72ef62f6ea2999b2d09fb975e15e4acacff66f9d4042b361a4839b25982a29c0",
    ),
    (
        "scene-edited-DisplayP3-Avif-true",
        "1a275574c4f46ce1d7174c269769037423f46a2d72a9841a00fc2891d49a749b",
    ),
    (
        "scene-edited-Rec2020-Tiff-false",
        "a01219445fe85772a0229b81c96b3a48b96aa5619f0cae4b70c4c16ef305edd6",
    ),
    (
        "scene-edited-Rec2020-Png-false",
        "db2f5b62354676c0395a1d4fa1e012b55e5a6a4cac960240d2ce979b8cd6b44e",
    ),
    (
        "scene-edited-Rec2020-Jpeg-false",
        "f138972284d6b4bb8324072a3f6ab7df6c8f8b79e6d2bfbfb0dd32dfc7232f83",
    ),
    (
        "scene-edited-Rec2020-Avif-false",
        "b93e2f68adc44f45c968b3718305dc4afd71dc5be29a35280c00bfd68d8b65e6",
    ),
    (
        "scene-edited-Rec2020-Avif-true",
        "ad4109aed2ef705fcb05e4f121e25f8d5b655bf9380dd085e65b939dd7502ad8",
    ),
    (
        "placed-neutral-Srgb-Tiff-false",
        "5483d7b2e13a2b0c166dda0fc107978acd1d07d5d8082ff3a69451040977f727",
    ),
    (
        "placed-neutral-Srgb-Png-false",
        "17fcc27da6bce74418a431d08aeb2cdebe620eb29789e14b805859459d3d422c",
    ),
    (
        "placed-neutral-Srgb-Jpeg-false",
        "ecf1fb36d9ef9be4811106e07c2bbd6d7eb9abf95e2cead2829bd7ef290de454",
    ),
    (
        "placed-neutral-Srgb-Avif-false",
        "ad8c56f0e06e71817a817ffb8d0fb630198876ff23bd9618dfcdd282f9266075",
    ),
    (
        "placed-neutral-Srgb-Avif-true",
        "1aa463f233fcde20df6bb1e45f147c345b1463ab8bcf097caae64771d023ce59",
    ),
    (
        "placed-neutral-DisplayP3-Tiff-false",
        "5a6ce451b50825e3c354ec069ffb8af74afa89e9d39c5ff742b7290529c138b9",
    ),
    (
        "placed-neutral-DisplayP3-Png-false",
        "b063b02c6c52e9236551a63fda79842542c463e213b0f93c3e4b725b92249117",
    ),
    (
        "placed-neutral-DisplayP3-Jpeg-false",
        "56b2a12ab6a8f3d093d9ee07a70f1285c67dc3c8f53a97e979546b3ead5084b4",
    ),
    (
        "placed-neutral-DisplayP3-Avif-false",
        "e41c4ca0a30f3ad81788f451f95a18bfd11373e24cf5fa90985449c01522b99a",
    ),
    (
        "placed-neutral-DisplayP3-Avif-true",
        "abab91640386d65fffb27485d91e492a7f33d42215a65a797a8f2df76d0b9f6c",
    ),
    (
        "placed-neutral-Rec2020-Tiff-false",
        "cc88f976d7531a976b049884e2a821b22926f55c4b89facfba0d04a2ec8d8a43",
    ),
    (
        "placed-neutral-Rec2020-Png-false",
        "26fbed15f10988defe93ba5fe99450ffcd50f7e357ec35d554d9b815d3cd170f",
    ),
    (
        "placed-neutral-Rec2020-Jpeg-false",
        "dfb0817c82440f42a3ba1c9532d00ebffa2b77ddd010ef0f2ef9961dae97f3b7",
    ),
    (
        "placed-neutral-Rec2020-Avif-false",
        "06d5c871b1f42ff2b8f4d8061d4593b7dc5ca74ae5470dbda8073b94a45ec700",
    ),
    (
        "placed-neutral-Rec2020-Avif-true",
        "72818cda96e4bb3dd3bce7f8e3bd6647fc089e555f32dc49fec8ad4d2b375896",
    ),
    (
        "placed-edited-Srgb-Tiff-false",
        "e73122d0c9593cdce747b439791fe9f6149177469e7d9d938b00c39cff62d319",
    ),
    (
        "placed-edited-Srgb-Png-false",
        "3cbaf2c3d479ec263ef3737976006cdebd6199bb3f8743044bc8001b0a9271f9",
    ),
    (
        "placed-edited-Srgb-Jpeg-false",
        "1bcc388c20a7007d215785663b9436c085eaae9c5a79a5cb0403430a53ea11da",
    ),
    (
        "placed-edited-Srgb-Avif-false",
        "bc39a59a2e27652c1eba174e211650fca6078b9d46920b75fd794628867461fa",
    ),
    (
        "placed-edited-Srgb-Avif-true",
        "4e392ed6154548e8ffb10b3a7c604e1a08342e06650252edc149db0d27121019",
    ),
    (
        "placed-edited-DisplayP3-Tiff-false",
        "f1bfa2948a6fbe10c3b14271306ffaf23d06a66fe285cfe5b1757d94c019f83a",
    ),
    (
        "placed-edited-DisplayP3-Png-false",
        "07c5c2f51c92780459cafa7cf14ca9a5ab1c75ee76f659e604d8b517a1b36a93",
    ),
    (
        "placed-edited-DisplayP3-Jpeg-false",
        "cc76c39dde56300739acf6c504aea94bf73e8a8412b38cf05093da2afff3e0c7",
    ),
    (
        "placed-edited-DisplayP3-Avif-false",
        "1f94e5ec6a55015b06e266d847b11d8c1ad6592a3cca1fdb42bed5a27ffb149d",
    ),
    (
        "placed-edited-DisplayP3-Avif-true",
        "4d399c84f36515a8a8bd5453daa1d43580eeb09a31e20d076c0f92ed5d60a585",
    ),
    (
        "placed-edited-Rec2020-Tiff-false",
        "a03bb64d80f9fab9ebd4394f2b312ec710273380c7c9dd3485cf7cbfd6128d27",
    ),
    (
        "placed-edited-Rec2020-Png-false",
        "d9e2f6fa272756fd46fd0a4a4c2e89ed09aef7f1bf9bb27fd71cad521e1d8b86",
    ),
    (
        "placed-edited-Rec2020-Jpeg-false",
        "310596f2a7453cba4f97d44a1e2dedd7f99eb638b5f077fb70939bb2a4f83ccb",
    ),
    (
        "placed-edited-Rec2020-Avif-false",
        "2b8d90528a5d3b36faa736c82c35dcdfd613c0502f2c5edb4b3338a2fdac7aa5",
    ),
    (
        "placed-edited-Rec2020-Avif-true",
        "ff7a116c58fe7dc7db7a458c17317460f91a67b4196dbcf6dba24c1baa73e977",
    ),
    (
        "display-neutral-Srgb-Tiff-false",
        "4f671781ee8e81396aa37ea28d259a47aabc7e0535509c0c1623fee1a709a72d",
    ),
    (
        "display-neutral-Srgb-Png-false",
        "68ec909874f1e9252e512c284e9b240f67ea0f503185072a10fd2ce2212e9015",
    ),
    (
        "display-neutral-Srgb-Jpeg-false",
        "8362c0b0c65e2a8a53ac6ea633052be17ce2dd497c533f395178d4e6b14d740a",
    ),
    (
        "display-neutral-Srgb-Avif-false",
        "a42813fb215da8c81fce5eb73e30e25728d30ce419c28517179363ed66d31ca4",
    ),
    (
        "display-neutral-DisplayP3-Tiff-false",
        "ee9df65c677f1b8fbce14e63e59802a57e1cf573d62ae5411831d8b538564322",
    ),
    (
        "display-neutral-DisplayP3-Png-false",
        "1b49a84ae1d01f845cfec54cd5efe9b182151883e25b12bca8acbc461754b71d",
    ),
    (
        "display-neutral-DisplayP3-Jpeg-false",
        "a546812385a72c7056bff550dd544db42a3f20b15a9e9aae578798860a6e8efe",
    ),
    (
        "display-neutral-DisplayP3-Avif-false",
        "1e6735625b673d3688bf07dbd4d8168bce4fc27260cee076029732aad2d99953",
    ),
    (
        "display-neutral-Rec2020-Tiff-false",
        "ec14782d282485e65424cbb90ee3a9cee3548312c6adfb60eefd109f13304a6b",
    ),
    (
        "display-neutral-Rec2020-Png-false",
        "f80aa68c08aaa905cce90d2f700867d08f670843175351a56e733df3377bd19e",
    ),
    (
        "display-neutral-Rec2020-Jpeg-false",
        "c0fac5ea07a2c525f5f18c921cd17ee0135fab9fb13c3714ea33a07a36529ebc",
    ),
    (
        "display-neutral-Rec2020-Avif-false",
        "52d526ec66889f54372c3e5044cffb11ee1313633e2dabc2f137c9dfdf859d10",
    ),
    (
        "display-edited-Srgb-Tiff-false",
        "f3fecd8d54f8b00bba0f0b1e07cbd154a88b6a3f8ed15bb9bc1757b091964274",
    ),
    (
        "display-edited-Srgb-Png-false",
        "c3964b6a71daf23c65ae1a12ef94dac7ff5bd625971fb26f79b46fb1826094cc",
    ),
    (
        "display-edited-Srgb-Jpeg-false",
        "0b38dc2598715473a506e76d712989dc044140c055e71ccaef3965a357442ec3",
    ),
    (
        "display-edited-Srgb-Avif-false",
        "3fec11e1540df78ed320ccab25d0d6a23c6afaa6ace8fd4167b1a5d1f67c7a1f",
    ),
    (
        "display-edited-DisplayP3-Tiff-false",
        "9047bf705644daf40517c524b48621ef8726f618ea79234c9d2b9dfa00e7dc85",
    ),
    (
        "display-edited-DisplayP3-Png-false",
        "66370696f56899a1f89561601cce23d7b89daece11ce0993ff4de2d0fa6a7840",
    ),
    (
        "display-edited-DisplayP3-Jpeg-false",
        "19f11d144570e8bdacf9a79dc7deff0147fbaf50181272af337317ee12d7f842",
    ),
    (
        "display-edited-DisplayP3-Avif-false",
        "468cdd97ccc161f5cd16a371b819f5404df090fd9cb0ac8a3e37f6864af56883",
    ),
    (
        "display-edited-Rec2020-Tiff-false",
        "9d22fa1ab5b11a5f2bef5ebb7a2d1bc71d93e87bda05bdc9bd20df9154379f8e",
    ),
    (
        "display-edited-Rec2020-Png-false",
        "dd51e7bbd434bef8971d227349800ca107682de1147c6ceae18071bbdb3a607e",
    ),
    (
        "display-edited-Rec2020-Jpeg-false",
        "750624b94f45e7c4ef00e31dce4a11b5a796c88f1d18d6482a8b71d55529487b",
    ),
    (
        "display-edited-Rec2020-Avif-false",
        "073196295dbfdc847c415698671dcae3a2d66c92dd17e32543332720f25bde73",
    ),
    (
        "coverage-Tiff",
        "1f0987da01b86d1143ab2063f58331d41c6007a1d73a261e890d2c39a98de92e",
    ),
    (
        "coverage-Png",
        "fdd4b33b9129b9ea3a3d12d9d652bf5b89491d87dd284f4260f5af629d1409c8",
    ),
];

#[test]
fn option_free_exports_are_byte_identical_to_the_pre_p7_build() {
    let actual = cases();
    assert_eq!(actual.len(), FROZEN.len(), "fixture set changed");
    for ((name, bytes), (frozen_name, frozen)) in actual.iter().zip(FROZEN) {
        assert_eq!(name, frozen_name);
        assert_eq!(
            &hex(&unstamped(name, bytes)),
            frozen,
            "{name} changed bytes"
        );
    }
}

#[test]
fn option_free_recipe_serialization_is_frozen() {
    // Compact and pretty JSON of an option-free recipe, recorded at 61effa01b.
    let compact = [NEUTRAL_JSON, EDITED_JSON];
    let pretty = [
        "f37631d0499ab07ddbec763359de6cbf6ee97257f85d92f5764a31c4a9853918",
        "11d49f478e72c63a4750a38f7bb41e40a1129841cde2f33219b44441da0a3f10",
    ];
    for (i, recipe) in [DevelopmentRecipe::default(), edited()].iter().enumerate() {
        assert_eq!(serde_json::to_string(recipe).unwrap(), compact[i]);
        assert_eq!(hex(&serde_json::to_vec_pretty(recipe).unwrap()), pretty[i]);
        let read: DevelopmentRecipe = serde_json::from_str(compact[i]).unwrap();
        assert_eq!(&read, recipe);
        assert!(!recipe.uses_finishing());
    }
}

const NEUTRAL_JSON: &str = r#"{"version":1,"global":{"exposure":0.0,"contrast":0.0,"highlights":0.0,"shadows":0.0,"whites":0.0,"blacks":0.0,"vibrance":0.0,"saturation":0.0,"temperature":0.0,"tint":0.0},"regions":[],"hdr":{"reference_white_nits":203.0,"peak_nits":1000.0,"quality":100,"speed":6}}"#;
const EDITED_JSON: &str = r#"{"version":1,"global":{"exposure":0.4,"contrast":18.0,"highlights":-30.0,"shadows":25.0,"whites":5.0,"blacks":-8.0,"vibrance":12.0,"saturation":6.0,"temperature":9.0,"tint":-4.0},"regions":[{"id":"e","name":"Region e","note":"","shape":{"kind":"ellipse","center":[0.3,0.4],"radius":[0.2,0.3]},"feather":0.4,"enabled":true,"adjustments":{"exposure":0.8,"contrast":0.0,"highlights":0.0,"shadows":0.0,"whites":0.0,"blacks":0.0,"vibrance":0.0,"saturation":20.0,"temperature":-15.0,"tint":0.0}},{"id":"r","name":"Region r","note":"","shape":{"kind":"rectangle","min":[0.55,0.1],"max":[0.95,0.6]},"feather":0.4,"enabled":true,"adjustments":{"exposure":-0.7,"contrast":0.0,"highlights":0.0,"shadows":0.0,"whites":0.0,"blacks":0.0,"vibrance":0.0,"saturation":20.0,"temperature":-15.0,"tint":0.0}},{"id":"p","name":"Region p","note":"","shape":{"kind":"polygon","points":[[0.1,0.9],[0.5,0.55],[0.8,0.95]]},"feather":0.4,"enabled":true,"adjustments":{"exposure":1.2,"contrast":0.0,"highlights":0.0,"shadows":0.0,"whites":0.0,"blacks":0.0,"vibrance":0.0,"saturation":20.0,"temperature":-15.0,"tint":0.0}},{"id":"off","name":"Region off","note":"","shape":{"kind":"ellipse","center":[0.5,0.5],"radius":[0.5,0.5]},"feather":0.4,"enabled":false,"adjustments":{"exposure":3.0,"contrast":0.0,"highlights":0.0,"shadows":0.0,"whites":0.0,"blacks":0.0,"vibrance":0.0,"saturation":20.0,"temperature":-15.0,"tint":0.0}}],"hdr":{"reference_white_nits":203.0,"peak_nits":1000.0,"quality":100,"speed":6}}"#;
