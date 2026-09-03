//! Render only a warp sidecar's registered reference frame through the full
//! stack's production coverage placement.
//!
//! This is a measurement instrument for the COVER slide-series audit, not a
//! product path. It deliberately has no merge, election, pyramid, defect
//! correction, restoration, exposure, colour matrix, or transfer curve. The
//! coverage mode and sidecar are explicit command-line operands so neither can
//! be selected implicitly from the environment.

#[allow(dead_code)]
#[path = "../src/align_cmd.rs"]
mod align_cmd;
#[allow(dead_code)]
#[path = "../src/image_out.rs"]
mod image_out;

/// Required by the `#[path]`-included image writer. Measurement TIFFs use the
/// writer's stable measurement stamp rather than this experimental build stamp.
const SOFTWARE: &str = concat!(
    "strehl cover-reference (examples/, measurement-only) ",
    env!("CARGO_PKG_VERSION")
);

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail, ensure};
use strehl_core::align::{Resampler, Similarity};
use strehl_core::noise::Levels;
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::warpmap::{FrameWarp, StackIdentity, WarpMap};

const USAGE: &str = "usage: cover-reference <DIR> <WARPMAP> <crop|scale> <OUT.tiff>";

#[derive(Debug, PartialEq, Eq)]
struct Args {
    dir: PathBuf,
    warpmap: PathBuf,
    mode: align_cmd::CoverMode,
    out: PathBuf,
}

fn parse_args_from(args: impl IntoIterator<Item = String>) -> Result<Args> {
    let args: Vec<String> = args.into_iter().collect();
    ensure!(
        args.len() == 4,
        "{USAGE}\nexpected exactly four operands, found {}",
        args.len()
    );
    let mode = match args[2].as_str() {
        "crop" => align_cmd::CoverMode::Crop,
        "scale" => align_cmd::CoverMode::Scale,
        other => {
            bail!("{USAGE}\ncoverage mode must be exactly \"crop\" or \"scale\", found {other:?}")
        }
    };
    let out = PathBuf::from(&args[3]);
    ensure!(
        out.extension()
            .and_then(|s| s.to_str())
            .map(|s| s.eq_ignore_ascii_case("tiff"))
            .unwrap_or(false),
        "{USAGE}\noutput must have a .tiff extension"
    );
    Ok(Args {
        dir: PathBuf::from(&args[0]),
        warpmap: PathBuf::from(&args[1]),
        mode,
        out,
    })
}

fn parse_args() -> Result<Args> {
    parse_args_from(std::env::args().skip(1))
}

/// List every ARW and surface directory-entry errors instead of silently
/// turning an unreadable entry into a shorter stack.
fn raw_paths(dir: &Path) -> Result<Vec<PathBuf>> {
    let entries = std::fs::read_dir(dir).with_context(|| format!("reading {}", dir.display()))?;
    let mut paths = Vec::new();
    for entry in entries {
        let entry = entry.with_context(|| format!("listing {}", dir.display()))?;
        let path = entry.path();
        let is_arw = path
            .extension()
            .and_then(|s| s.to_str())
            .map(|s| s.eq_ignore_ascii_case("arw"))
            .unwrap_or(false);
        if is_arw
            && entry
                .file_type()
                .with_context(|| format!("reading file type for {}", path.display()))?
                .is_file()
        {
            paths.push(path);
        }
    }
    paths.sort();
    ensure!(!paths.is_empty(), "no .ARW frames in {}", dir.display());
    Ok(paths)
}

fn stack_name(dir: &Path) -> String {
    dir.file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| dir.display().to_string())
}

fn fnv1a64(bytes: &[u8]) -> u64 {
    const OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
    const PRIME: u64 = 0x0000_0100_0000_01b3;
    bytes.iter().fold(OFFSET, |hash, byte| {
        (hash ^ u64::from(*byte)).wrapping_mul(PRIME)
    })
}

/// Equality of values is not enough here: `-0.0 == 0.0`, but the registered
/// gate asks for the exact serialized f64 identity.
fn is_exact_identity(t: Similarity) -> bool {
    t.a.re.to_bits() == 1.0f64.to_bits()
        && t.a.im.to_bits() == 0.0f64.to_bits()
        && t.b.re.to_bits() == 0.0f64.to_bits()
        && t.b.im.to_bits() == 0.0f64.to_bits()
}

fn validate_map(map: &WarpMap, identity: &StackIdentity, paths: &[PathBuf]) -> Result<usize> {
    map.check_stack(identity)
        .context("the explicit sidecar does not identify the full sorted stack")?;
    ensure!(
        map.len() == paths.len(),
        "sidecar has {} frame records but the full sorted stack has {} files",
        map.len(),
        paths.len()
    );
    let reference = map.provenance().reference;
    ensure!(
        reference < paths.len(),
        "sidecar reference {reference} is out of range for {} frames",
        paths.len()
    );
    ensure!(
        map.resampler() == Resampler::CatmullRom,
        "sidecar resampler is {:?}; this measurement requires Catmull-Rom and refuses an override",
        map.resampler()
    );
    ensure!(
        map.placed_count() == paths.len() && map.refused_count() == 0,
        "sidecar is incomplete: {} placed / {} refused for {} frames; this measurement drops none",
        map.placed_count(),
        map.refused_count(),
        paths.len()
    );
    ensure!(
        map.geometry().width > 0 && map.geometry().height > 0,
        "sidecar has empty plane geometry {}x{}",
        map.geometry().width,
        map.geometry().height
    );
    for (index, warp) in map.warps().iter().enumerate() {
        match warp {
            FrameWarp::Placed(t) => {
                let p = t.to_params();
                ensure!(
                    [p.ax, p.ay, p.g, p.rot].iter().all(|v| v.is_finite()),
                    "sidecar placement {index} is not finite: {p:?}"
                );
            }
            FrameWarp::Refused(reason) => {
                bail!("sidecar frame {index} was refused: {reason}");
            }
        }
    }
    let reference_placement = map
        .placement(reference)
        .context("reading the registered reference placement")?;
    ensure!(
        is_exact_identity(reference_placement),
        "sidecar reference {reference} is not exact serialized f64 identity: {:?}",
        reference_placement.to_params()
    );
    Ok(reference)
}

fn validate_rect(rect: align_cmd::CropRect, full: PlaneGeometry) -> Result<()> {
    ensure!(
        rect.width > 0 && rect.height > 0,
        "coverage produced an empty crop rectangle"
    );
    ensure!(
        rect.x <= full.width
            && rect.y <= full.height
            && rect.width <= full.width - rect.x
            && rect.height <= full.height - rect.y,
        "crop rectangle {}x{} at ({}, {}) is outside the {}x{} plane",
        rect.width,
        rect.height,
        rect.x,
        rect.y,
        full.width,
        full.height
    );
    Ok(())
}

/// Map one output-quad address through the integer Crop rectangle. This is the
/// same addressing rule as `merge_cmd::write_merged`; no sample is copied,
/// interpolated, or re-based by the crop itself.
fn crop_source_index(output_index: usize, rect: align_cmd::CropRect, full: PlaneGeometry) -> usize {
    debug_assert!(output_index < rect.width * rect.height);
    (output_index / rect.width + rect.y) * full.width + output_index % rect.width + rect.x
}

/// The byte-frozen measurement encoder from `merge_cmd::write_merged`, with
/// `srgb == false`: black subtraction and non-negative clamp happen before
/// this function, then WB/range, upper clamp, scale, and round-to-nearest.
fn encode_value(value: f32, gain: f32, range: f32) -> u16 {
    let value = (value * gain / range).min(1.0);
    (value * u16::MAX as f32 + 0.5) as u16
}

fn encode_quad(samples: [u16; 4], levels: Levels, gains: [f32; 3]) -> [u16; 3] {
    let [r, g1, g2, b] = samples.map(f32::from);
    let black = levels.black;
    let range = levels.range();
    let red = (r - black).max(0.0);
    // Match the pyramid/reference path this instrument isolates: load_frame
    // black-subtracts and clamps each CFA plane before forming green luma.
    // Doing it after the mean would agree on ordinary samples but move a quad
    // with one green site below black.
    let green = 0.5 * ((g1 - black).max(0.0) + (g2 - black).max(0.0));
    let blue = (b - black).max(0.0);
    [
        encode_value(red, gains[0], range),
        encode_value(green, gains[1], range),
        encode_value(blue, gains[2], range),
    ]
}

fn encode_binned(
    frame: &strehl_raw::Frame,
    full: PlaneGeometry,
    rect: align_cmd::CropRect,
    gains: [f32; 3],
) -> Vec<u16> {
    let mut rgb = vec![0u16; rect.width * rect.height * 3];
    let (pixels, _) = rgb.as_chunks_mut::<3>();
    for (output_index, pixel) in pixels.iter_mut().enumerate() {
        let source_index = crop_source_index(output_index, rect, full);
        let (qx, qy) = (source_index % full.width, source_index / full.width);
        *pixel = encode_quad(
            [
                frame.sample(2 * qx, 2 * qy),
                frame.sample(2 * qx + 1, 2 * qy),
                frame.sample(2 * qx, 2 * qy + 1),
                frame.sample(2 * qx + 1, 2 * qy + 1),
            ],
            frame.levels,
            gains,
        );
    }
    rgb
}

/// Pin the two environment-sensitive decisions inside the required production
/// warp call. Coverage itself is never read from the environment.
fn pin_warp_environment() {
    // SAFETY: this is called at the start of `run`, before raw decode, Rayon,
    // or any other worker can exist. The values remain fixed until process exit.
    unsafe {
        std::env::set_var(strehl_core::optics::CA_ENV, "off");
        std::env::set_var(align_cmd::FULLRES_ENV, "1");
        std::env::set_var(align_cmd::ALIGN_ENV, "");
    }
}

fn run(args: Args) -> Result<()> {
    pin_warp_environment();

    let paths = raw_paths(&args.dir)?;
    println!("cover-reference -- measurement-only reference render");
    println!(
        "source          : {}",
        args.dir
            .canonicalize()
            .unwrap_or_else(|_| args.dir.clone())
            .display()
    );
    println!("frames          : {} (full sorted .ARW stack)", paths.len());
    for (index, path) in paths.iter().enumerate() {
        let bytes = std::fs::metadata(path)
            .with_context(|| format!("reading metadata for {}", path.display()))?
            .len();
        println!(
            "  [{index:03}] {:<24} {bytes} bytes",
            path.file_name()
                .map(|s| s.to_string_lossy())
                .unwrap_or_default()
        );
    }

    let identity = StackIdentity::from_paths(&stack_name(&args.dir), &paths)
        .context("constructing identity of the full sorted stack")?;
    let sidecar_bytes = std::fs::read(&args.warpmap)
        .with_context(|| format!("reading explicit sidecar {}", args.warpmap.display()))?;
    let sidecar_text = std::str::from_utf8(&sidecar_bytes)
        .with_context(|| format!("{} is not UTF-8", args.warpmap.display()))?;
    let map = WarpMap::from_text(sidecar_text)
        .with_context(|| format!("parsing explicit sidecar {}", args.warpmap.display()))?;
    let reference = validate_map(&map, &identity, &paths)?;
    let original_geom = map.geometry();
    let original_provenance = map.provenance().clone();

    println!(
        "stack identity  : {:016x} ({} frames; exact match)",
        identity.digest, identity.frames
    );
    println!("sidecar        : {}", args.warpmap.display());
    println!(
        "sidecar hash    : fnv1a64 {:016x} ({} bytes)",
        fnv1a64(&sidecar_bytes),
        sidecar_bytes.len()
    );
    println!(
        "sidecar source  : {:?}, strategy {:?}",
        original_provenance.stack.name, original_provenance.strategy
    );
    println!(
        "solve quality   : held-out {:?} plane px, cycle floor {:?} plane px",
        original_provenance.heldout_px, original_provenance.cycle_floor_px
    );
    println!(
        "reference       : [{reference}] {} (exact serialized f64 identity)",
        paths[reference]
            .file_name()
            .map(|s| s.to_string_lossy())
            .unwrap_or_default()
    );
    println!(
        "registration    : {} placed / {} refused; Catmull-Rom",
        map.placed_count(),
        map.refused_count()
    );
    println!(
        "plane geometry  : {} x {} quads",
        original_geom.width, original_geom.height
    );
    println!(
        "cover mode      : {} (explicit CLI operand; {} is not read)",
        args.mode.name(),
        align_cmd::COVER_ENV
    );

    // This is intentionally the production function and the full N-placement
    // map. Only after all identity/reference/resampler/refusal gates pass may it
    // derive the placement used below.
    let (covered_map, fit) = align_cmd::cover_or_explain(map, args.mode);
    let (k, rect) = match (args.mode, fit) {
        (align_cmd::CoverMode::Crop, align_cmd::CoverFit::Cropped { k, rect }) => (k, rect),
        (align_cmd::CoverMode::Scale, align_cmd::CoverFit::Scaled(k)) => {
            (k, align_cmd::CropRect::whole(original_geom))
        }
        (_, align_cmd::CoverFit::Uncovered) => {
            bail!("production coverage could not fit a fully covered output")
        }
        (mode, other) => {
            bail!("production coverage returned {other:?} for explicit mode {mode:?}")
        }
    };
    ensure!(
        k.is_finite() && k > 0.0 && k <= 1.0,
        "production coverage returned invalid k={k:?}"
    );
    validate_rect(rect, original_geom)?;
    match args.mode {
        align_cmd::CoverMode::Crop => println!(
            "coverage        : k={k:.17}; integer crop {} x {} at ({}, {})",
            rect.width, rect.height, rect.x, rect.y
        ),
        align_cmd::CoverMode::Scale => println!(
            "coverage        : k={k:.17}; full {} x {} geometry emitted",
            original_geom.width, original_geom.height
        ),
        align_cmd::CoverMode::Skip => unreachable!("the parser does not admit Skip"),
    }

    // Decode exactly one file, after coverage has consumed the full map.
    let mut frame = strehl_raw::decode(&paths[reference])
        .with_context(|| format!("decoding fixed reference {}", paths[reference].display()))?;
    ensure!(
        frame.geometry() == original_geom,
        "reference decodes to {}x{} quads but sidecar declares {}x{}",
        frame.geometry().width,
        frame.geometry().height,
        original_geom.width,
        original_geom.height
    );
    let levels = frame.levels;
    let range = levels.range();
    ensure!(range > 0.0, "white level is not above black level");
    let wb = frame.wb_gains();
    let gains = wb.unwrap_or([1.0, 1.0, 1.0]);
    println!(
        "levels          : black {} white {} range {} (f32)",
        levels.black, levels.white, range
    );
    println!(
        "white balance   : raw [{}, {}, {}, {}], resolved [{}, {}, {}]{}",
        frame.wb_coeffs[0],
        frame.wb_coeffs[1],
        frame.wb_coeffs[2],
        frame.wb_coeffs[3],
        gains[0],
        gains[1],
        gains[2],
        if wb.is_some() {
            ""
        } else {
            " (unusable metadata: unity fallback)"
        }
    );
    println!(
        "warp policy     : production warp_frame_in_place, full-resolution gather, Catmull-Rom; lateral CA forced off"
    );

    let reference_placement = covered_map
        .placement(reference)
        .context("reading covered reference placement")?;
    let mut scratch = align_cmd::WarpScratch::new(original_geom);
    let covered_fraction = align_cmd::warp_frame_in_place(
        &mut frame,
        reference_placement,
        original_geom,
        Resampler::CatmullRom,
        &mut scratch,
    )
    .context("warping the fixed reference on full plane geometry")?;
    if args.mode == align_cmd::CoverMode::Scale {
        ensure!(
            covered_fraction == 1.0,
            "scaled reference placement covered only {:.9}% of the full output",
            covered_fraction * 100.0
        );
    }
    println!(
        "warp coverage   : {:.9}% of the full plane before integer output addressing",
        covered_fraction * 100.0
    );

    let rgb = encode_binned(&frame, original_geom, rect, gains);
    let output_geom = rect.geometry();
    let dev = image_out::Develop::measurement(false);
    image_out::write_rgb16_described(
        &args.out,
        output_geom.width as u32,
        output_geom.height as u32,
        &rgb,
        &dev,
    )?;
    println!(
        "wrote           : {} ({} x {}, RGB16, camera-native linear, one 2x2 quad per pixel)",
        args.out.display(),
        output_geom.width,
        output_geom.height
    );
    println!(
        "not applied     : merge/pyramid/election, defect, CA, restoration, exposure, colour matrix, transfer curve"
    );
    Ok(())
}

fn main() -> Result<()> {
    run(parse_args()?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::align::{Cx, Similarity};

    #[derive(Debug)]
    struct ErrorStats {
        max: u32,
        rms: f64,
        differing: usize,
    }

    fn error_stats(actual: &[u16], expected: &[u16]) -> ErrorStats {
        assert_eq!(actual.len(), expected.len());
        let mut max = 0u32;
        let mut sum_sq = 0f64;
        let mut differing = 0usize;
        for (&a, &e) in actual.iter().zip(expected) {
            let d = (i32::from(a) - i32::from(e)).unsigned_abs();
            max = max.max(d);
            sum_sq += f64::from(d).powi(2);
            differing += usize::from(d != 0);
        }
        ErrorStats {
            max,
            rms: (sum_sq / actual.len() as f64).sqrt(),
            differing,
        }
    }

    #[test]
    fn cli_is_exactly_four_operands_and_two_modes() {
        let crop =
            parse_args_from(["stack", "full.warpmap.txt", "crop", "out.tiff"].map(String::from))
                .unwrap();
        assert_eq!(crop.mode, align_cmd::CoverMode::Crop);
        let scale =
            parse_args_from(["stack", "full.warpmap.txt", "scale", "out.TIFF"].map(String::from))
                .unwrap();
        assert_eq!(scale.mode, align_cmd::CoverMode::Scale);

        for bad in [
            vec!["stack", "full.warpmap.txt", "off", "out.tiff"],
            vec!["stack", "full.warpmap.txt", "Crop", "out.tiff"],
            vec!["stack", "full.warpmap.txt", "crop", "out.tif"],
            vec!["stack", "full.warpmap.txt", "crop"],
            vec!["stack", "full.warpmap.txt", "crop", "out.tiff", "extra"],
        ] {
            assert!(
                parse_args_from(bad.into_iter().map(String::from)).is_err(),
                "ambiguous invocation was accepted"
            );
        }
    }

    #[test]
    fn exact_identity_rejects_a_signed_zero_bit_change() {
        assert!(is_exact_identity(Similarity::IDENTITY));
        let signed_zero = Similarity {
            a: Cx::new(1.0, 0.0),
            b: Cx::new(-0.0, 0.0),
        };
        assert_eq!(signed_zero, Similarity::IDENTITY);
        assert!(!is_exact_identity(signed_zero));
    }

    #[test]
    fn encoder_fixture_detects_a_plant_an_improvement_and_the_null() {
        let levels = Levels {
            black: 512.0,
            white: 15360.0,
        };
        let expected = [3769, 30005, 19244];
        let encoded = encode_quad([1000, 7310, 7310, 4000], levels, [1.75, 1.0, 1.25]);
        assert_eq!(encoded, expected, "literal RGGB encoder fixture moved");
        assert_eq!(
            encode_quad([512, 256, 768, 512], levels, [1.0, 1.0, 1.0]),
            [0, 565, 0],
            "green must clamp each site before averaging"
        );

        let mut planted = encoded;
        planted[1] ^= 0x8000;
        let plant = error_stats(&planted, &expected);
        assert_eq!(plant.max, 32768);
        assert_eq!(plant.differing, 1);

        planted[1] ^= 0x0001;
        let improved = error_stats(&planted, &expected);
        assert!(improved.max < plant.max);
        assert!(improved.rms < plant.rms);

        planted[1] ^= 0x8001;
        let restored = error_stats(&planted, &expected);
        assert_eq!(restored.max, 0);
        assert_eq!(restored.rms, 0.0);
        assert_eq!(restored.differing, 0);
    }

    #[test]
    fn crop_origin_plant_is_detected_and_correct_addressing_is_the_null() {
        let full = PlaneGeometry {
            width: 12,
            height: 8,
        };
        let rect = align_cmd::CropRect {
            x: 3,
            y: 2,
            width: 5,
            height: 4,
        };
        let wrong = align_cmd::CropRect { x: 4, ..rect };
        // Literal oracle, deliberately not produced by crop_source_index:
        // full-row stride 12, rows 2..=5, columns 3..=7.
        let expected = [
            27, 28, 29, 30, 31, //
            39, 40, 41, 42, 43, //
            51, 52, 53, 54, 55, //
            63, 64, 65, 66, 67,
        ];
        let planted: Vec<u16> = (0..wrong.width * wrong.height)
            .map(|i| crop_source_index(i, wrong, full) as u16)
            .collect();
        let plant = error_stats(&planted, &expected);
        assert!(
            plant.differing * 100 > expected.len(),
            "the one-quad origin plant did not move more than 1% of samples"
        );

        let corrected: Vec<u16> = (0..rect.width * rect.height)
            .map(|i| crop_source_index(i, rect, full) as u16)
            .collect();
        let null = error_stats(&corrected, &expected);
        assert!(null.max < plant.max);
        assert!(null.rms < plant.rms);
        assert!(null.differing < plant.differing);
        assert_eq!(null.max, 0);
        assert_eq!(null.rms, 0.0);
        assert_eq!(null.differing, 0);
    }
}
