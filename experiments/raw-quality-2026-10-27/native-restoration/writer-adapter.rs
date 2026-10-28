use super::*;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Write},
    path::{Path, PathBuf},
    time::{Instant, SystemTime},
};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    out_dir: PathBuf,
    expected_test_executable_sha256: String,
}
const MATRIX: [[f32; 3]; 3] = [
    [0.746, -0.2365, -0.0588],
    [-0.5687, 1.3442, 0.2474],
    [-0.0624, 0.1156, 0.6584],
];
fn digest(h: Sha256) -> String {
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
pub(super) fn sha(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut b = vec![0; 1 << 20];
    loop {
        let n = f.read(&mut b)?;
        if n == 0 {
            break;
        }
        h.update(&b[..n]);
    }
    Ok(digest(h))
}
pub(super) fn save(path: &Path, v: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, v)?;
    writeln!(f)?;
    Ok(())
}
fn stamp(path: &Path) -> Result<(u64, SystemTime)> {
    let m = std::fs::metadata(path)?;
    Ok((m.len(), m.modified()?))
}
fn record(path: &Path) -> Result<Value> {
    Ok(json!({"path":path,"bytes":std::fs::metadata(path)?.len(),"sha256":sha(path)?}))
}
fn pixel_hash(path: &Path, w: usize, h: usize, float: bool) -> Result<String> {
    let mut limits = tiff::decoder::Limits::default();
    limits.decoding_buffer_size = w * h * 3 * 4;
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?.with_limits(limits);
    ensure!(
        d.dimensions()? == (w as u32, h as u32)
            && d.colortype()? == tiff::ColorType::RGB(if float { 32 } else { 16 }),
        "complete RGB geometry/type"
    );
    let mut hash = Sha256::new();
    let mut bytes = vec![0; 65536];
    match d.read_image()? {
        tiff::decoder::DecodingResult::F32(v) if float => {
            ensure!(
                v.len() == w * h * 3 && v.iter().all(|x| x.is_finite()),
                "complete finite float payload"
            );
            for chunk in v.chunks(bytes.len() / 4) {
                for (b, x) in bytes.chunks_exact_mut(4).zip(chunk) {
                    b.copy_from_slice(&x.to_bits().to_le_bytes());
                }
                hash.update(&bytes[..4 * chunk.len()]);
            }
        }
        tiff::decoder::DecodingResult::U16(v) if !float => {
            ensure!(v.len() == w * h * 3, "complete RGB16 payload");
            for chunk in v.chunks(bytes.len() / 2) {
                for (b, x) in bytes.chunks_exact_mut(2).zip(chunk) {
                    b.copy_from_slice(&x.to_le_bytes());
                }
                hash.update(&bytes[..2 * chunk.len()]);
            }
        }
        _ => bail!("wrong sample storage"),
    }
    ensure!(!d.more_images(), "single image required");
    Ok(digest(hash))
}
fn material(path: &Path) -> Result<Value> {
    use tiff::tags::Tag;
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?;
    let description = d.get_tag_ascii_string(Tag::ImageDescription)?;
    let icc = d.get_tag_u8_vec(Tag::IccProfile)?;
    ensure!(!icc.is_empty(), "ICC required");
    let mut hash = Sha256::new();
    hash.update(&icc);
    let mut tags = std::collections::BTreeMap::new();
    for tag in [
        Tag::BitsPerSample,
        Tag::PhotometricInterpretation,
        Tag::SamplesPerPixel,
        Tag::SampleFormat,
        Tag::Orientation,
        Tag::XResolution,
        Tag::YResolution,
        Tag::ResolutionUnit,
    ] {
        tags.insert(format!("{tag:?}"), format!("{:?}", d.get_tag(tag).ok()));
    }
    Ok(json!({"description":description,"icc_sha256":digest(hash),"material_tags":tags}))
}
fn display(path: &Path) -> Result<strehl_edit::DisplayBaseline> {
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?;
    let text = d.get_tag_ascii_string(tiff::tags::Tag::ImageDescription)?;
    let line = text
        .lines()
        .find_map(|x| x.strip_prefix("DisplayBaseline: "))
        .context("display baseline absent")?;
    let v: strehl_edit::DisplayBaseline = serde_json::from_str(line)?;
    ensure!(
        [v.black, v.white, v.contrast, v.exposure_gain]
            .iter()
            .all(|x| x.is_finite())
            && v.white > v.black
            && v.contrast == 0.55
            && v.exposure_gain == 1.,
        "held development"
    );
    Ok(v)
}
fn read_planes(path: &Path, w: usize, h: usize, tiff: bool) -> Result<Vec<Vec<f32>>> {
    let mut planes = vec![vec![0.; w * h / 4]; 4];
    let mut f = BufReader::new(File::open(path)?);
    if tiff {
        // This exact observer format is CFA Photometric=32803, not Gray.
        // Its whole-file hash is already pinned; independently check the
        // numeric header and payload hash, without reinterpreting its CFA tag.
        ensure!(
            (w, h) == (6896, 4596) && std::fs::metadata(path)?.len() == 126776356,
            "bound observer geometry/length"
        );
        let mut header = [0u8; 292];
        f.read_exact(&mut header)?;
        ensure!(
            &header[..8] == b"II\x2a\x00\x08\x00\x00\x00"
                && u16::from_le_bytes(header[8..10].try_into().unwrap()) == 15
                && header[190..194] == [0, 0, 0, 0],
            "single little-endian observer IFD"
        );
        let tags = header[10..190]
            .chunks_exact(12)
            .map(|e| {
                (
                    u16::from_le_bytes(e[..2].try_into().unwrap()),
                    (
                        u16::from_le_bytes(e[2..4].try_into().unwrap()),
                        u32::from_le_bytes(e[4..8].try_into().unwrap()),
                        u32::from_le_bytes(e[8..12].try_into().unwrap()),
                    ),
                )
            })
            .collect::<std::collections::BTreeMap<_, _>>();
        for (tag, value) in [
            (256, (4, 1, 6896)),
            (257, (4, 1, 4596)),
            (258, (3, 1, 32)),
            (259, (3, 1, 1)),
            (262, (3, 1, 32803)),
            (273, (4, 1, 292)),
            (277, (3, 1, 1)),
            (278, (4, 1, 4596)),
            (279, (4, 1, 126776064)),
            (284, (3, 1, 1)),
            (339, (3, 1, 3)),
            (33421, (3, 2, 0x0002_0002)),
            (33422, (1, 4, 0x0201_0100)),
        ] {
            ensure!(
                tags.get(&tag) == Some(&value),
                "observer TIFF tag {tag} changed"
            );
        }
    } else {
        ensure!(
            std::fs::metadata(path)?.len() == (w * h * 4) as u64,
            "exact sensor payload length"
        );
    }
    let mut hash = Sha256::new();
    let mut row = vec![0; w * 4];
    for y in 0..h {
        f.read_exact(&mut row)?;
        hash.update(&row);
        for x in 0..w {
            planes[2 * (y % 2) + x % 2][(y / 2) * (w / 2) + x / 2] =
                f32::from_le_bytes(row[4 * x..4 * x + 4].try_into().unwrap());
        }
    }
    ensure!(
        digest(hash)
            == if tiff {
                "1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0"
            } else {
                "a66b19086695e343c3f794964a9cc07a0ef44012aa3b4c9c183675c21f5669be"
            },
        "exact original CFA payload binding"
    );
    let mut tail = [0u8; 1];
    ensure!(f.read(&mut tail)? == 0, "trailing sensor bytes");
    ensure!(
        planes.iter().flatten().all(|x| x.is_finite()),
        "finite input CFA required"
    );
    Ok(planes)
}
fn write_result(
    out: &Path,
    name: &str,
    planes: &[Vec<f32>],
    w: usize,
    h: usize,
    origin: [usize; 2],
    gain: [f32; 3],
    dev: &image_out::Develop,
) -> Result<Value> {
    let sensor = out.join(format!("{name}-sensor.f32le"));
    let mut f = BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&sensor)?,
    );
    let mut row = vec![0; w * 4];
    let mut mosaic = vec![0.; w * h];
    let gains = [gain[0], gain[1], gain[1], gain[2]];
    let levels = Levels {
        black: 512.,
        white: 15360.,
    };
    for y in 0..h {
        for x in 0..w {
            let p = 2 * (y % 2) + x % 2;
            let v = planes[p][(y / 2) * (w / 2) + x / 2];
            row[4 * x..4 * x + 4].copy_from_slice(&v.to_bits().to_le_bytes());
            mosaic[y * w + x] = v.max(0.) * gains[p] * 1.0 / levels.range();
        }
        f.write_all(&row)?;
    }
    f.flush()?;
    drop(f);
    save(
        &out.join(format!("{name}-sensor.json")),
        &json!({"format":"row-major RGGB signed f32 LE black-subtracted DN","width":w,"height":h,"active_native_origin":origin,"before":["WB","MHC","development"],"payload":record(&sensor)?}),
    )?;
    let rgb = out.join(format!("{name}-master.tiff"));
    let linear = out.join(format!("{name}-linear.tiff"));
    image_out::write_demosaiced_with_master(&rgb, w, h, &mosaic, dev, Some(&linear), None)?;
    drop(mosaic);
    Ok(
        json!({"sensor":record(&sensor)?,"rgb16":record(&rgb)?,"linear":record(&linear)?,"rgb16_pixels_sha256":pixel_hash(&rgb,w,h,false)?,"linear_pixels_sha256":pixel_hash(&linear,w,h,true)?,"entire_output":true}),
    )
}
pub(super) fn run(flat: bool) -> Result<()> {
    let start = Instant::now();
    ensure!(
        matches!(
            std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).as_deref(),
            Err(std::env::VarError::NotPresent) | Ok("malvar")
        ),
        "fixed MHC required"
    );
    let config_path = PathBuf::from(
        std::env::var_os("STREHL_NATIVE_RESTORATION_CONFIG").context("config required")?,
    );
    let config: Config = serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(
        config.schema == 1
            && sha(&std::env::current_exe()?)? == config.expected_test_executable_sha256,
        "schema/build binding"
    );
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?;
    ensure!(
        config.out_dir.is_absolute()
            && !config.out_dir.exists()
            && config
                .out_dir
                .parent()
                .context("output parent")?
                .canonicalize()?
                .starts_with(repo.join("outputs").canonicalize()?),
        "fresh workspace output required"
    );
    let (
        w,
        h,
        origin,
        gain,
        sensor,
        sidecar,
        held_rgb,
        held_linear,
        sensor_sha,
        sidecar_sha,
        rgb_sha,
        linear_sha,
    ) = if flat {
        let current =
            repo.join("outputs/raw-quality-2026-10-27/reconstruction-photo-full-1/output");
        let base = repo.join("outputs/raw-quality-2026-10-26/flat-1s-baseline");
        (
            6932,
            4620,
            [50, 34],
            [1076994048u32, 1065353216, 1069719552].map(f32::from_bits),
            current.join("baseline-sensor.f32le"),
            current.join("baseline-sensor.json"),
            base.join("stack-master.tiff"),
            base.join("linear-master.tiff"),
            "a66b19086695e343c3f794964a9cc07a0ef44012aa3b4c9c183675c21f5669be",
            "5b5f3c387c64b73b7ca7c39d34f1c06c72729b03be253e604effa31d330ef1b1",
            "01e576315fdf8242b9d008c06a0ad9b52f837f84d8d28e05d59d13b97379dbdc",
            "51fd1f3e281c10def359af38a2064055de11b8788ff5ce7c0428d9e5a9e417ab",
        )
    } else {
        let base = repo.join("outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off");
        (
            6896,
            4596,
            [68, 46],
            [1637.0 / 1024., 1., 2774.0 / 1024.],
            base.join("sensor-master.tiff"),
            base.join("sensor-master.tiff.json"),
            base.join("stack-master.tiff"),
            base.join("linear-master.tiff"),
            "fa5825b834121b28547fc6e2154623740a24acc4e1616915c1c197bc90be2b02",
            "e22ad2fad5ac7307a4560ccee4b0ad232edf1dc9449fdce7057022bff9341f21",
            "5dc571cce0d9e310f1f06b6e7f3c78faae8fb4ee4f12c94ff76d1d0c0e3fb655",
            "8f3d9ec977f06d8fd44e070f27ab97e398611436cef17271fa6b889067ea1960",
        )
    };
    let inputs = [
        (&sensor, sensor_sha),
        (&sidecar, sidecar_sha),
        (&held_rgb, rgb_sha),
        (&held_linear, linear_sha),
    ];
    let before = inputs
        .iter()
        .map(|(p, expected)| {
            ensure!(
                sha(p)? == *expected,
                "input binding changed: {}",
                p.display()
            );
            stamp(p)
        })
        .collect::<Result<Vec<_>>>()?;
    let tone = display(&held_linear)?;
    if flat {
        ensure!(
            [tone.black, tone.white, tone.contrast].map(f32::to_bits)
                == [1007739294, 1052551964, 1057803469],
            "flat tone bits"
        );
    }
    let levels = Levels {
        black: 512.,
        white: 15360.,
    };
    let matrix = color::camera_to_srgb(MATRIX)
        .context("matrix")?
        .with_saturation(levels, gain, 1.);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone {
        black: tone.black,
        white: tone.white,
        contrast: tone.contrast,
    });
    dev.exposure_gain = tone.exposure_gain;
    let planes = read_planes(&sensor, w, h, !flat)?;
    let off = apply(&planes, w / 2, h / 2, Correction::Off)?;
    ensure!(
        planes
            .iter()
            .zip(&off)
            .all(|(a, b)| a.iter().zip(b).all(|(x, y)| x.to_bits() == y.to_bits())),
        "literal no-op mismatch"
    );
    std::fs::create_dir(&config.out_dir)?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let baseline =
        pool.install(|| write_result(&config.out_dir, "baseline", &off, w, h, origin, gain, &dev))?;
    drop(off);
    ensure!(
        baseline["rgb16_pixels_sha256"] == pixel_hash(&held_rgb, w, h, false)?
            && baseline["linear_pixels_sha256"] == pixel_hash(&held_linear, w, h, true)?,
        "NO-OP FULL PIXEL IDENTITY FAILED"
    );
    ensure!(
        material(&config.out_dir.join("baseline-master.tiff"))? == material(&held_rgb)?
            && material(&config.out_dir.join("baseline-linear.tiff"))? == material(&held_linear)?,
        "NO-OP MATERIAL METADATA IDENTITY FAILED"
    );
    save(
        &config.out_dir.join("noop-verified.json"),
        &json!({"baseline_pixel_golden_exact":true,"baseline_material_metadata_golden_exact":true,"sensor_off_bit_exact":true,"baseline":baseline}),
    )?;
    let correction_start = Instant::now();
    let candidate = pool.install(|| apply(&planes, w / 2, h / 2, Correction::Bounded))?;
    let correction_seconds = correction_start.elapsed().as_secs_f64();
    let changed = planes
        .iter()
        .zip(&candidate)
        .map(|(a, b)| {
            a.iter()
                .zip(b)
                .filter(|(a, b)| a.to_bits() != b.to_bits())
                .count()
        })
        .collect::<Vec<_>>();
    let output = pool.install(|| {
        write_result(
            &config.out_dir,
            "candidate",
            &candidate,
            w,
            h,
            origin,
            gain,
            &dev,
        )
    })?;
    ensure!(
        material(&config.out_dir.join("candidate-master.tiff"))? == material(&held_rgb)?
            && material(&config.out_dir.join("candidate-linear.tiff"))? == material(&held_linear)?,
        "paired material metadata changed"
    );
    for ((p, expected), original) in inputs.iter().zip(&before) {
        ensure!(
            stamp(p)? == *original && sha(p)? == *expected,
            "retained input changed"
        );
    }
    let mut receipt = json!({"schema":1,"status":"COMPLETE_NATIVE_RESTORATION_DIAGNOSTIC","dataset":if flat {"flat"}else{"weevil"},"admission":false,"quality_claim":false,"source_count":if flat{60}else{299},"source_count_meaning":"saved-master lineage; no fresh source replay","native_dimensions":[w,h],"active_native_origin":origin,"crop_quad_xywh":[origin[0]/2,origin[1]/2,w/2,h/2],"baseline_pixel_golden_exact":true,"baseline_material_metadata_golden_exact":true,"pair_material_metadata_exact":true,"sensor_off_bit_exact":true,"noop_rgb16_pixel_exact":true,"noop_linear_pixel_exact":true,"retained_input_bytes_and_metadata_unchanged":true,"RAW_reads":0,"original_RAW_read_or_written":false,"baseline":baseline,"candidate":output,"changed_sensor_samples_per_phase":changed});
    let more = json!({"operator":"x + clamp(2*(B*x-B*B*x),min3x3(x)-x,max3x3(x)-x); final f32 support cap","phase_pitch_native_pixels":2,"boundary":"reflect without repeating endpoint","shared_color_or_source_election":false,"single_frame_noise_reference":{"gain_dn_per_e":0.22893773,"read_noise_e":4.2,"black":512,"white":15360,"iso":100,"prnu":null,"used_for_operator_gate":false,"merged_variance_claim":false},"development":{"wb_gains":gain,"matrix":MATRIX,"tone":tone},"worker_count":4,"correction_seconds":correction_seconds,"total_seconds":start.elapsed().as_secs_f64(),"config":record(&config_path)?,"build":record(&std::env::current_exe()?)?,"retained_input_bindings":inputs.iter().map(|(p,_)|record(p)).collect::<Result<Vec<_>>>()?});
    receipt
        .as_object_mut()
        .unwrap()
        .extend(more.as_object().unwrap().clone());
    save(&config.out_dir.join("receipt.json"), &receipt)?;
    eprintln!(
        "complete {} contrast observation in {:.3}s; no quality admission",
        if flat { "flat" } else { "weevil" },
        start.elapsed().as_secs_f64()
    );
    Ok(())
}
