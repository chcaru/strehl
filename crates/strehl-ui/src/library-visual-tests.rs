//! The mockup's Library: its subjects, collections and stacks, with synthetic
//! pictures and source folders, for the offscreen pictures checked against
//! the mockup references (plan 10.2). The pictures themselves are rendered
//! through the application's own offscreen path with `--route library` and
//! `--route subject` (`app-station-library-tests.rs`).
use super::tests::{BASE, develop, draft, run};
use super::*;

/// The mockup's subjects, with synthetic pictures under `root`. Every stack's
/// source folder exists there except Peacock ore's, which shows as moved.
pub(crate) fn mockup_catalog(root: &Path) -> (Catalog, NodeId) {
    let pictures = root.join("pictures");
    std::fs::create_dir_all(&pictures).unwrap();
    let mut catalog = Catalog::default();
    let collections: Vec<NodeId> = ["Insects", "Minerals", "Plants and food", "Test targets"]
        .iter()
        .map(|name| catalog.create_project(name).unwrap())
        .collect();
    let subjects = [
        ("Blue weevil", 0, 3, [40, 170, 190]),
        ("Net-patterned beetle", 0, 1, [20, 120, 110]),
        ("White scarab", 0, 2, [200, 200, 195]),
        ("Orange weevil", 0, 1, [200, 130, 40]),
        ("Spotted flower beetle", 0, 2, [60, 140, 90]),
        ("Jewel beetle", 0, 2, [90, 60, 130]),
        ("Green scarab, wing case", 0, 4, [40, 160, 60]),
        ("Speckled weevil", 0, 3, [70, 90, 50]),
        ("Bumblebee", 0, 2, [190, 160, 80]),
        ("Etched garnet", 1, 2, [150, 20, 40]),
        ("Peacock ore", 1, 1, [30, 70, 120]),
        ("Marigold", 2, 1, [230, 170, 30]),
        ("Star sand", 1, 1, [210, 205, 200]),
        ("Chia seeds", 2, 1, [120, 120, 110]),
        ("Decapped chip", 3, 1, [120, 140, 60]),
    ];
    let mut first = 0;
    for (index, (name, collection, stacks, rgb)) in subjects.iter().enumerate() {
        let picture = pictures.join(format!("{index:02}.png"));
        let rgb = *rgb;
        image::RgbImage::from_fn(600, 400, |x, y| {
            let shade = 0.35
                + 0.65
                    * (1.0
                        - ((x as f32 - 300.0).powi(2) + (y as f32 - 200.0).powi(2)).sqrt() / 360.0)
                        .max(0.0);
            image::Rgb(rgb.map(|c| (c as f32 * shade) as u8))
        })
        .save(&picture)
        .unwrap();
        let subject = catalog
            .create_subject(collections[*collection], name)
            .unwrap();
        if index == 0 {
            first = subject;
        }
        for s in 0..*stacks {
            let folder = root.join(format!("captures/{index}/{s}/100MSDCF"));
            if *name != "Peacock ore" {
                std::fs::create_dir_all(&folder).unwrap();
                std::fs::write(folder.join("DSC00001.ARW"), [0_u8; 16]).unwrap();
            }
            let source = folder.to_string_lossy().into_owned();
            let stack = catalog
                .create_stack(
                    subject,
                    [
                        "Dorsal · 2.8×",
                        "Lateral · 2.8×",
                        "Wing case · 5.6×",
                        "Head",
                    ][s % 4],
                    draft(&source, 9_000_000_000 + (index as u64 * 1_300_000_000)),
                )
                .unwrap();
            let created = BASE + (index * 10 + s) as u64 * 86_400;
            let directory = format!("/out/strehl-{index}-{s}-1");
            match (index + s) % 5 {
                0 => {}
                1 => {
                    catalog
                        .add_revision(stack, run(&directory, &source, "Saved", created))
                        .unwrap();
                    catalog
                        .add_revision(
                            stack,
                            run(&format!("{directory}b"), &source, "Failed", created + 60),
                        )
                        .unwrap();
                }
                2 => catalog
                    .add_revision(stack, run(&directory, &source, "Saved", created))
                    .unwrap(),
                _ => {
                    catalog
                        .add_revision(stack, run(&directory, &source, "Saved", created))
                        .unwrap();
                    develop(
                        &mut catalog,
                        stack,
                        &directory,
                        (index * 10 + s) as u64,
                        created,
                    );
                }
            }
        }
        catalog
            .set_subject_meta(
                subject,
                SubjectEdit {
                    hero: Some(Some(picture)),
                    notes: (index == 0).then(|| {
                        "Pinned specimen on a dark field. Dorsal view first, then lateral. Two diffused panels, left one a stop brighter.".to_owned()
                    }),
                    optics: (index == 0).then(|| {
                        Some(crate::workspace_history::Optics {
                            camera: "ILCE-7CR".into(),
                            lens: "FE 100mm F2.8 Macro GM + 2× converter".into(),
                        })
                    }),
                    scale: (index == 0).then(|| {
                        Some(crate::workspace_history::ScaleCalibration::entered(2.8, 3.76).unwrap())
                    }),
                },
            )
            .unwrap();
    }
    (catalog, first)
}
