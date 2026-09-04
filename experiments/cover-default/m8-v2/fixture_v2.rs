//! Synthetic producer-only M8-v2 fixtures.
//!
//! Commission this from an injected private archive by copying this file to
//! `crates/strehl-cli/examples/m8_fixture_v2.rs` and running:
//!
//! ```text
//! cargo run -p strehl-cli --example m8_fixture_v2 -- commission TRACE_DIR
//! ```
//!
//! The fixture calls the archived `strehl_core::align::Resampler` directly and
//! uses the injected producer's real atomic block writer. It emits inputs,
//! transforms, metadata, and gathered values only. It contains no hull,
//! tolerance, violation count, contributor set, or expected checker verdict.

#[allow(dead_code)]
#[path = "../src/m8_trace_v2.rs"]
mod m8_trace_v2;

use std::path::{Path, PathBuf};

use anyhow::{Result, bail, ensure};
use m8_trace_v2::{ValueBlock, write_value_block};
use strehl_core::align::{Cx, PlaneRef, Resampler, Similarity};
use strehl_core::noise::Levels;
use strehl_core::plane::PlaneGeometry;
use strehl_raw::{Frame, Region};

const SOURCE_WIDTH: usize = 24;
const SOURCE_HEIGHT: usize = 20;
const DESTINATION_WIDTH: usize = 12;
const DESTINATION_HEIGHT: usize = 10;
const BLACK_WHITE_RANGE: f32 = 14_848.0;

#[allow(clippy::too_many_arguments)]
fn gather(
    source: &[f32],
    source_width: usize,
    source_height: usize,
    destination_width: usize,
    destination_height: usize,
    site_x: usize,
    site_y: usize,
    transform: Similarity,
    resampler: Resampler,
) -> Vec<f32> {
    let source =
        PlaneRef::new(source, source_width, source_height).expect("fixture source geometry");
    let (cx, cy) = (
        destination_width as f64 * 0.5,
        destination_height as f64 * 0.5,
    );
    let (ox, oy) = (site_x as f64 * 0.5, site_y as f64 * 0.5);
    let mut destination = vec![f32::NAN; destination_width * destination_height];
    for y in 0..destination_height {
        for x in 0..destination_width {
            let (sx, sy) = transform.apply_at(x as f64 + ox, y as f64 + oy, cx, cy);
            if let Some(value) = resampler.sample_checked(source, 2.0 * sx, 2.0 * sy) {
                destination[y * destination_width + x] = value;
            }
        }
    }
    destination
}

fn texture(seed: u32) -> Vec<f32> {
    (0..SOURCE_HEIGHT)
        .flat_map(|y| {
            (0..SOURCE_WIDTH).map(move |x| {
                let mixed = (x as u32)
                    .wrapping_mul(17)
                    .wrapping_add((y as u32).wrapping_mul(29))
                    .wrapping_add((x as u32).wrapping_mul(y as u32).wrapping_mul(7))
                    .wrapping_add(seed)
                    % 4093;
                mixed as f32 / 128.0
            })
        })
        .collect()
}

fn channel_for_site(site_x: usize, site_y: usize) -> usize {
    match (site_x, site_y) {
        (0, 0) => 0,
        (1, 0) | (0, 1) => 1,
        (1, 1) => 2,
        _ => unreachable!("2x2 CFA site"),
    }
}

fn gain_for_channel(channel: usize) -> f32 {
    match channel {
        0 => 2.0,
        1 => 1.0,
        2 => 1.5,
        _ => unreachable!("RGB channel"),
    }
}

#[allow(clippy::too_many_arguments)]
fn emit(
    root: &Path,
    frame_path: &str,
    source: &[f32],
    destination: &[f32],
    site_x: usize,
    site_y: usize,
    channel: usize,
    transform: Similarity,
    recorded_resampler: Resampler,
) -> Result<()> {
    let completed = write_value_block(
        root,
        &ValueBlock {
            resampler: recorded_resampler,
            source_width: SOURCE_WIDTH,
            source_height: SOURCE_HEIGHT,
            destination_width: DESTINATION_WIDTH,
            destination_height: DESTINATION_HEIGHT,
            site_x,
            site_y,
            channel,
            transform,
            cx: DESTINATION_WIDTH as f64 * 0.5,
            cy: DESTINATION_HEIGHT as f64 * 0.5,
            black_white_range: BLACK_WHITE_RANGE,
            site_gain: gain_for_channel(channel),
            frame_path,
            source,
            destination,
        },
    )?;
    println!("{}", completed.display());
    Ok(())
}

fn commission(root: &Path) -> Result<()> {
    let base = texture(11);

    // A fixed vertical 0/1 step sampled at t=0.5. Production Catmull-Rom's
    // weights make the exact observed extrema -0.0625 and 1.0625.
    let mut step = vec![0.0f32; SOURCE_WIDTH * SOURCE_HEIGHT];
    for y in 0..SOURCE_HEIGHT {
        for x in 10..SOURCE_WIDTH {
            step[y * SOURCE_WIDTH + x] = 1.0;
        }
    }
    let half_phase = Similarity {
        a: Cx::ONE,
        b: Cx::new(0.25, 0.0),
    };
    let hard_step = gather(
        &step,
        SOURCE_WIDTH,
        SOURCE_HEIGHT,
        DESTINATION_WIDTH,
        DESTINATION_HEIGHT,
        0,
        0,
        half_phase,
        Resampler::CatmullRom,
    );
    let finite: Vec<f32> = hard_step
        .iter()
        .copied()
        .filter(|value| value.is_finite())
        .collect();
    let observed_min = finite.iter().copied().fold(f32::INFINITY, f32::min);
    let observed_max = finite.iter().copied().fold(f32::NEG_INFINITY, f32::max);
    ensure!(
        observed_min.to_bits() == (-0.0625f32).to_bits()
            && observed_max.to_bits() == 1.0625f32.to_bits(),
        "archived production Catmull-Rom did not reproduce fixed t=0.5 extrema"
    );
    emit(
        root,
        "fixtures/hard-step.arw",
        &step,
        &hard_step,
        0,
        0,
        0,
        half_phase,
        Resampler::CatmullRom,
    )?;

    let copy = gather(
        &base,
        SOURCE_WIDTH,
        SOURCE_HEIGHT,
        DESTINATION_WIDTH,
        DESTINATION_HEIGHT,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    );
    ensure!(
        copy[3 * DESTINATION_WIDTH + 3].to_bits() == base[6 * SOURCE_WIDTH + 6].to_bits(),
        "identity Catmull-Rom anchor was not an exact copy"
    );
    emit(
        root,
        "fixtures/exact-copy.arw",
        &base,
        &copy,
        0,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    )?;

    let bilinear_transform = Similarity {
        a: Cx::ONE,
        b: Cx::new(0.25, 0.125),
    };
    let bilinear = gather(
        &base,
        SOURCE_WIDTH,
        SOURCE_HEIGHT,
        DESTINATION_WIDTH,
        DESTINATION_HEIGHT,
        0,
        0,
        bilinear_transform,
        Resampler::Bilinear,
    );
    ensure!(
        bilinear.iter().any(|value| value.is_finite()),
        "fractional bilinear fixture has no finite samples"
    );
    emit(
        root,
        "fixtures/fractional-bilinear.arw",
        &base,
        &bilinear,
        0,
        0,
        0,
        bilinear_transform,
        Resampler::Bilinear,
    )?;

    let transforms = [
        (
            "scale",
            Similarity {
                a: Cx::new(1.015625, 0.0),
                b: Cx::ZERO,
            },
        ),
        (
            "rotation",
            Similarity {
                a: Cx::new(0.999_550_033_748_987_5, 0.029_995_500_202_495_66),
                b: Cx::ZERO,
            },
        ),
        (
            "translation",
            Similarity {
                a: Cx::ONE,
                b: Cx::new(0.375, -0.3125),
            },
        ),
        (
            "both-axes",
            Similarity {
                a: Cx::new(0.9921875, -0.0234375),
                b: Cx::new(-0.34375, 0.28125),
            },
        ),
    ];
    for (name, transform) in transforms {
        let destination = gather(
            &base,
            SOURCE_WIDTH,
            SOURCE_HEIGHT,
            DESTINATION_WIDTH,
            DESTINATION_HEIGHT,
            0,
            0,
            transform,
            Resampler::CatmullRom,
        );
        emit(
            root,
            &format!("fixtures/transform-{name}.arw"),
            &base,
            &destination,
            0,
            0,
            0,
            transform,
            Resampler::CatmullRom,
        )?;
    }

    for (site_x, site_y, name) in [(0, 0, "r"), (1, 0, "g1"), (0, 1, "g2"), (1, 1, "b")] {
        let channel = channel_for_site(site_x, site_y);
        let destination = gather(
            &base,
            SOURCE_WIDTH,
            SOURCE_HEIGHT,
            DESTINATION_WIDTH,
            DESTINATION_HEIGHT,
            site_x,
            site_y,
            Similarity::IDENTITY,
            Resampler::CatmullRom,
        );
        emit(
            root,
            &format!("fixtures/cfa-{name}.arw"),
            &base,
            &destination,
            site_x,
            site_y,
            channel,
            Similarity::IDENTITY,
            Resampler::CatmullRom,
        )?;
    }

    let boundary_transform = Similarity {
        a: Cx::ONE,
        b: Cx::new(-0.75, 0.625),
    };
    let boundary = gather(
        &base,
        SOURCE_WIDTH,
        SOURCE_HEIGHT,
        DESTINATION_WIDTH,
        DESTINATION_HEIGHT,
        0,
        0,
        boundary_transform,
        Resampler::CatmullRom,
    );
    ensure!(
        boundary.iter().any(|value| value.is_nan())
            && boundary.iter().any(|value| value.is_finite()),
        "boundary fixture must contain both gathered and invalid samples"
    );
    emit(
        root,
        "fixtures/boundary.arw",
        &base,
        &boundary,
        0,
        0,
        0,
        boundary_transform,
        Resampler::CatmullRom,
    )?;

    let mut nan_source = base.clone();
    nan_source[6 * SOURCE_WIDTH + 6] = f32::from_bits(0x7fc1_2345);
    let nan_destination = gather(
        &nan_source,
        SOURCE_WIDTH,
        SOURCE_HEIGHT,
        DESTINATION_WIDTH,
        DESTINATION_HEIGHT,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    );
    emit(
        root,
        "fixtures/source-nan-payload.arw",
        &nan_source,
        &nan_destination,
        0,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    )?;

    // Same basename and site, different full paths: filenames must not collide.
    for parent in ["left", "right"] {
        emit(
            root,
            &format!("fixtures/{parent}/repeated.arw"),
            &base,
            &copy,
            0,
            0,
            0,
            Similarity::IDENTITY,
            Resampler::CatmullRom,
        )?;
    }

    // Metadata/value plants remain value-only. Their interpretation belongs to
    // the independent checker, not to this producer.
    emit(
        root,
        "plants/wrong-kernel.arw",
        &base,
        &copy,
        0,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::Bilinear,
    )?;
    let recorded_transform = Similarity {
        a: Cx::new(f64::from_bits(Similarity::IDENTITY.a.re.to_bits() ^ 1), 0.0),
        b: Cx::ZERO,
    };
    emit(
        root,
        "plants/wrong-transform-bit.arw",
        &base,
        &copy,
        0,
        0,
        0,
        recorded_transform,
        Resampler::CatmullRom,
    )?;
    let wrong_plane = texture(2_001);
    emit(
        root,
        "plants/wrong-source-plane.arw",
        &wrong_plane,
        &copy,
        0,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    )?;
    emit(
        root,
        "plants/wrong-cfa-channel.arw",
        &base,
        &copy,
        0,
        0,
        2,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    )?;
    let mut finite_as_nan = copy.clone();
    finite_as_nan[3 * DESTINATION_WIDTH + 3] = f32::NAN;
    emit(
        root,
        "plants/finite-as-nan.arw",
        &base,
        &finite_as_nan,
        0,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    )?;
    let mut invalid_as_finite = copy.clone();
    invalid_as_finite[0] = 123.25;
    emit(
        root,
        "plants/invalid-as-finite.arw",
        &base,
        &invalid_as_finite,
        0,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    )?;

    Ok(())
}

fn race(root: &Path) -> Result<()> {
    let source = texture(71);
    let destination = gather(
        &source,
        SOURCE_WIDTH,
        SOURCE_HEIGHT,
        DESTINATION_WIDTH,
        DESTINATION_HEIGHT,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    );
    emit(
        root,
        "fixtures/concurrent/shared.arw",
        &source,
        &destination,
        0,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    )
}

fn synthetic_frame(path: &str) -> Frame {
    Frame {
        data: vec![512; SOURCE_WIDTH * SOURCE_HEIGHT],
        stride: SOURCE_WIDTH,
        buffer_height: SOURCE_HEIGHT,
        active: Region {
            x: 0,
            y: 0,
            width: SOURCE_WIDTH,
            height: SOURCE_HEIGHT,
        },
        levels: Levels {
            black: 512.0,
            white: 15_360.0,
        },
        iso: Some(100.0),
        wb_coeffs: [2.0, 1.0, 1.5, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "synthetic-m8-v2".to_owned(),
        path: PathBuf::from(path),
    }
}

fn trace_site_case(root: &Path, channel: usize) -> Result<()> {
    let configured = std::env::var_os("STREHL_M8_V2_TRACE_DIR")
        .map(PathBuf::from)
        .ok_or_else(|| anyhow::anyhow!("trace-site requires STREHL_M8_V2_TRACE_DIR"))?;
    ensure!(
        configured == root,
        "trace-site argument and STREHL_M8_V2_TRACE_DIR differ"
    );
    let source = texture(313);
    let destination = gather(
        &source,
        SOURCE_WIDTH,
        SOURCE_HEIGHT,
        DESTINATION_WIDTH,
        DESTINATION_HEIGHT,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::CatmullRom,
    );
    m8_trace_v2::trace_site(
        &synthetic_frame("fixtures/trace-site-wrapper.arw"),
        0,
        0,
        PlaneGeometry {
            width: DESTINATION_WIDTH,
            height: DESTINATION_HEIGHT,
        },
        Similarity::IDENTITY,
        DESTINATION_WIDTH as f64 * 0.5,
        DESTINATION_HEIGHT as f64 * 0.5,
        channel,
        gain_for_channel(channel),
        Resampler::CatmullRom,
        &source,
        &destination,
    )
}

fn gate_off(root: &Path) -> Result<()> {
    ensure!(
        std::env::var_os("STREHL_M8_V2_TRACE_DIR").is_none(),
        "gate-off requires STREHL_M8_V2_TRACE_DIR to be absent"
    );
    ensure!(!root.exists(), "gate-off sentinel path already exists");
    m8_trace_v2::trace_site(
        &synthetic_frame("fixtures/gate-off.arw"),
        9,
        9,
        PlaneGeometry {
            width: DESTINATION_WIDTH,
            height: DESTINATION_HEIGHT,
        },
        Similarity::IDENTITY,
        0.0,
        0.0,
        99,
        f32::NAN,
        Resampler::Nearest,
        &[],
        &[],
    )?;
    ensure!(
        !root.exists(),
        "disabled trace unexpectedly touched the filesystem"
    );
    Ok(())
}

fn invalid_payload(root: &Path) -> Result<()> {
    let source = texture(991);
    let destination = vec![0.0; DESTINATION_WIDTH * DESTINATION_HEIGHT];
    emit(
        root,
        "fixtures/invalid-payload.arw",
        &source,
        &destination,
        0,
        0,
        0,
        Similarity::IDENTITY,
        Resampler::Nearest,
    )
}

fn usage() -> &'static str {
    "usage: m8_fixture_v2 \
     <commission|race|trace-site|trace-site-wrong-channel|gate-off|invalid-payload> \
     <trace-directory>"
}

fn main() -> Result<()> {
    let mut args = std::env::args_os();
    let _program = args.next();
    let Some(command) = args.next() else {
        bail!(usage());
    };
    let Some(root) = args.next() else {
        bail!(usage());
    };
    ensure!(
        args.next().is_none(),
        "unexpected extra argument; {}",
        usage()
    );
    match command.to_string_lossy().as_ref() {
        "commission" => commission(Path::new(&root)),
        "race" => race(Path::new(&root)),
        "trace-site" => trace_site_case(Path::new(&root), 0),
        "trace-site-wrong-channel" => trace_site_case(Path::new(&root), 2),
        "gate-off" => gate_off(Path::new(&root)),
        "invalid-payload" => invalid_payload(Path::new(&root)),
        other => bail!("unknown command {other:?}; {}", usage()),
    }
}
