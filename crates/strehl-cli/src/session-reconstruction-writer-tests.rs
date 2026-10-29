use super::*;
use crate::image_out::session_reconstruction_output::{
    NativeCameraImage, NativeNormalization, NativeReconstruction,
};

#[test]
fn session_reconstruction_writer_noop_preserves_complete_native_files_and_normalization() {
    let root = std::env::temp_dir().join(format!(
        "strehl-native-seam-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&root).unwrap();
    let full = PlaneGeometry {
        width: 71,
        height: 58,
    };
    let domain = PyramidDomain::cropped(
        full,
        align_cmd::CropRect {
            x: 9,
            y: 7,
            width: 41,
            height: 36,
        },
    )
    .unwrap();
    let n = 41 * 36;
    let planes: Vec<Vec<f32>> = (0..4)
        .map(|c| {
            (0..n)
                .map(|i| {
                    700. + 1100. * ((i % 41) as f32 * 0.31 + c as f32).sin()
                        + 500. * ((i / 41) as f32 * 0.2).cos()
                        + if i % 41 > 25 && i / 41 > 20 {
                            13000.
                        } else {
                            0.
                        }
                })
                .collect()
        })
        .collect();
    let levels = Levels {
        black: 512.,
        white: 16383.,
    };
    let wb = Some([2.73, 1., 1.56]);
    let matrix = (
        [
            [0.6743, -0.0734, -0.0666],
            [-0.4295, 1.2897, 0.1517],
            [-0.0419, 0.1267, 0.6315],
        ],
        "test camera matrix".into(),
    );
    let exposure = Exposure::resolve(true, 0.37, false).unwrap();
    let space = image_out::OutputSpace::from_flags(true, false).unwrap();
    let a = root.join("native.tiff");
    let am = root.join("native-master.tiff");
    write_merged_observed(
        Merged::Bands {
            domain,
            planes: &planes,
        },
        levels,
        wb,
        Some(&matrix),
        space,
        true,
        exposure,
        None,
        &a,
        None,
        Some(&am),
        None,
    )
    .unwrap();
    let b = root.join("fallback.tiff");
    let bm = root.join("fallback-master.tiff");
    let mut calls = 0;
    let mut unchanged =
        |image: &mut NativeCameraImage, normalization: NativeNormalization| -> Result<()> {
            calls += 1;
            assert_eq!((image.width, image.height), (82, 72));
            assert_eq!(normalization.white_balance, [2.73, 1., 1.56]);
            assert_eq!(normalization.range, levels.white - levels.black);
            for c in 0..3 {
                assert_eq!(
                    normalization.normalize(123.25, c).to_bits(),
                    (123.25 * normalization.white_balance[c] * normalization.exposure_gain
                        / normalization.range)
                        .to_bits()
                );
            }
            Ok(())
        };
    write_merged_observed_with_reconstruction(
        Merged::Bands {
            domain,
            planes: &planes,
        },
        levels,
        wb,
        Some(&matrix),
        space,
        true,
        exposure,
        None,
        &b,
        None,
        Some(&bm),
        None,
        None,
        Some(NativeReconstruction {
            output_memory_budget: 8 << 20,
            transform: &mut unchanged,
        }),
    )
    .unwrap();
    assert_eq!(calls, 1);
    assert_eq!(std::fs::read(a).unwrap(), std::fs::read(b).unwrap());
    assert_eq!(std::fs::read(am).unwrap(), std::fs::read(bm).unwrap());
    std::fs::remove_dir_all(root).unwrap();
}
