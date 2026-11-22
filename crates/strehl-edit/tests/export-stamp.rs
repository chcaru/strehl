//! Every exported file says it was made with Strehl, whatever the settings say
//! and whether or not it carries a date (owner, 2026-11-22: "is there a way to
//! stamp the image as being generated with Strehl? this wouldn't be
//! configurable. every image would get it"). Each file is read back container
//! by container (`common`), not through the writer's own code. An empty field
//! writes nothing.
mod common;

use common::{Said, said};
use std::{path::Path, sync::atomic::AtomicBool};
use strehl_edit::*;

fn photograph() -> LinearImage {
    LinearImage {
        width: 48,
        height: 32,
        pixels: (0..48 * 32)
            .flat_map(|i| {
                let (x, y) = ((i % 48) as f32, (i / 48) as f32);
                [0.02 + 0.02 * x, 0.05 + 0.03 * y, 0.3]
            })
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

/// Every format and range the export writes, with its file extension.
fn outputs() -> Vec<(&'static str, ExportSettings)> {
    let sdr = |format| ExportSettings {
        format,
        color_space: OutputColorSpace::Srgb,
        hdr: false,
        quality: 90,
        speed: 10,
        ..Default::default()
    };
    vec![
        ("tiff", sdr(ExportFormat::Tiff)),
        (
            "tiff",
            ExportSettings {
                embed_recipe: true,
                ..sdr(ExportFormat::Tiff)
            },
        ),
        ("png", sdr(ExportFormat::Png)),
        ("jpg", sdr(ExportFormat::Jpeg)),
        ("avif", sdr(ExportFormat::Avif)),
        (
            "avif",
            ExportSettings {
                hdr: true,
                color_space: OutputColorSpace::Rec2020,
                ..sdr(ExportFormat::Avif)
            },
        ),
        // A resize and sharpening take the staged path, not the fused one.
        (
            "jpg",
            ExportSettings {
                resize: Some(Resize {
                    long_edge: 24,
                    filter: ResizeFilter::Mitchell,
                }),
                sharpen: Some(OutputSharpening::default()),
                ..sdr(ExportFormat::Jpeg)
            },
        ),
        (
            "png",
            ExportSettings {
                resize: Some(Resize {
                    long_edge: 24,
                    filter: ResizeFilter::Mitchell,
                }),
                ..sdr(ExportFormat::Png)
            },
        ),
    ]
}

fn write(
    dir: &Path,
    name: &str,
    settings: &ExportSettings,
    date: Option<ExportDateTime>,
) -> (std::path::PathBuf, ExportReport) {
    let path = dir.join(name);
    let report = export_image_with(
        &path,
        &photograph(),
        &DevelopmentRecipe::default(),
        settings,
        &ExportExtras {
            date_time: date,
            ..Default::default()
        },
        &AtomicBool::new(false),
    )
    .unwrap();
    (path, report)
}

/// The containers each format names Strehl in.
fn expected_software(extension: &str) -> Vec<(&'static str, String)> {
    let strehl = CREATOR_TOOL.to_owned();
    match extension {
        "tiff" => vec![("tiff", "Strehl development v1".to_owned())],
        "png" => vec![("png-text", strehl.clone()), ("xmp", strehl)],
        "jpg" => vec![("exif", strehl.clone()), ("xmp", strehl)],
        "avif" => vec![("exif", strehl)],
        other => panic!("{other}"),
    }
}

#[test]
fn every_format_names_strehl_without_text_or_date() {
    assert_eq!(CREATOR_TOOL, "Strehl");
    let dir = tempfile::tempdir().unwrap();
    for (i, (extension, settings)) in outputs().iter().enumerate() {
        let name = format!("bare-{i}.{extension}");
        let (path, report) = write(dir.path(), &name, settings, None);
        let read = said(&path);
        assert_eq!(
            read,
            Said {
                software: expected_software(extension),
                ..Default::default()
            },
            "{name}: {settings:?}"
        );
        // The report says which containers were written.
        let stamped = match *extension {
            "tiff" if settings.embed_recipe => vec!["recipe"],
            "tiff" => vec![],
            "png" => vec!["png-text", "xmp"],
            "jpg" => vec!["exif", "xmp"],
            _ => vec!["exif"],
        };
        assert_eq!(report.metadata, stamped, "{name}");
    }
}

#[test]
fn every_format_names_strehl_beside_the_text_and_date() {
    let dir = tempfile::tempdir().unwrap();
    let date = ExportDateTime::from_unix_seconds(1_793_781_369, 60);
    for (i, (extension, settings)) in outputs().iter().enumerate() {
        let mut settings = settings.clone();
        settings.metadata = ExportMetadata {
            artist: "Chris Caruso".into(),
            copyright: "© 2026 Chris Caruso".into(),
            description: "Weevil on moss".into(),
        };
        let name = format!("words-{i}.{extension}");
        let (path, _) = write(dir.path(), &name, &settings, Some(date));
        let read = said(&path);
        assert!(read.dated, "{name}");
        let mut software = expected_software(extension);
        if *extension == "tiff" {
            // The TIFF's XMP packet carries the creator tool as well.
            software.push(("xmp", CREATOR_TOOL.to_owned()));
        }
        assert_eq!(read.software, software, "{name}");
        // Each container that holds a field says it (Exif and TIFF ASCII
        // fields write the copyright sign as "(c)").
        for artist in &read.artist {
            assert_eq!(artist, "Chris Caruso", "{name}");
        }
        for copyright in &read.copyright {
            assert!(
                copyright == "© 2026 Chris Caruso" || copyright == "(c) 2026 Chris Caruso",
                "{name}: {copyright}"
            );
        }
        for description in &read.description {
            assert_eq!(description, "Weevil on moss", "{name}");
        }
        assert!(
            !read.artist.is_empty() && !read.copyright.is_empty(),
            "{name}"
        );
        if *extension != "tiff" {
            assert!(!read.description.is_empty(), "{name}");
        }
    }
}

#[test]
fn an_empty_field_writes_nothing() {
    let dir = tempfile::tempdir().unwrap();
    for (i, (extension, settings)) in outputs().iter().enumerate() {
        let mut settings = settings.clone();
        settings.metadata = ExportMetadata {
            artist: String::new(),
            copyright: "© 2026 Chris Caruso".into(),
            description: String::new(),
        };
        let name = format!("copyright-{i}.{extension}");
        let (path, _) = write(dir.path(), &name, &settings, None);
        let read = said(&path);
        assert!(read.artist.is_empty(), "{name}: {read:?}");
        assert!(read.description.is_empty(), "{name}: {read:?}");
        assert!(!read.copyright.is_empty(), "{name}: {read:?}");
        assert!(!read.dated, "{name}");
        assert!(
            read.software.iter().all(|(_, s)| s.starts_with("Strehl")),
            "{name}: {read:?}"
        );
    }
}

/// The scene-linear master keeps its own Software tag, which names Strehl.
#[test]
fn the_linear_master_names_strehl() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("master.tiff");
    save_linear_tiff(&path, &photograph()).unwrap();
    assert_eq!(
        said(&path).software,
        vec![("tiff", "Strehl scene-linear master v1".to_owned())]
    );
}

/// The reader is not fooled: a file whose stamp was removed reads as unstamped.
#[test]
fn the_read_back_sees_a_missing_stamp() {
    let dir = tempfile::tempdir().unwrap();
    let settings = &outputs()[2].1; // PNG
    let (path, _) = write(dir.path(), "x.png", settings, None);
    let bytes = std::fs::read(&path).unwrap();
    let mut stripped = bytes[..8].to_vec();
    for (kind, data) in common::png_chunks(&bytes) {
        if &kind == b"tEXt" || &kind == b"iTXt" {
            continue;
        }
        stripped.extend_from_slice(&(data.len() as u32).to_be_bytes());
        stripped.extend_from_slice(&kind);
        stripped.extend_from_slice(&data);
        stripped.extend_from_slice(&[0; 4]); // CRC is not read back
    }
    let control = dir.path().join("control.png");
    std::fs::write(&control, stripped).unwrap();
    assert!(said(&control).software.is_empty());
}
