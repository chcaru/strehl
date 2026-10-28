// Root-built non-native diagnostic: unchanged twelve-plane fusion-order operator.
use super::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Write},
    time::SystemTime,
};
use strehl_core::pyramid::{Fallback, Hull};

const ORDER_SHA: &str = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f";
const MAP_SHA: &str = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225";
const RGB_SHA: &str = "5dc571cce0d9e310f1f06b6e7f3c78faae8fb4ee4f12c94ff76d1d0c0e3fb655";
const LINEAR_SHA: &str = "8f3d9ec977f06d8fd44e070f27ab97e398611436cef17271fa6b889067ea1960";
const SENSOR_SHA: &str = "fa5825b834121b28547fc6e2154623740a24acc4e1616915c1c197bc90be2b02";
const SIDECAR_SHA: &str = "e22ad2fad5ac7307a4560ccee4b0ad232edf1dc9449fdce7057022bff9341f21";
const CFA_PAYLOAD_SHA: &str = "1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0";
const RGB_PIXELS_SHA: &str = "f98cb4d9bc281eb9f28f4e618878607d7e7317eeb7ac20b349f35dfee81c280c";
const LINEAR_PIXELS_SHA: &str = "ee2b711bc36e48b9913531e1c615bd265ad06fd395a74f6224ca94392e32be09";
const CROP: [usize; 4] = [34, 23, 3448, 2298];
const NAMES: [&str; 2] = ["baseline", "candidate"];
const MATRIX: [[f32; 3]; 3] = [
    [0.746, -0.2365, -0.0588],
    [-0.5687, 1.3442, 0.2474],
    [-0.0624, 0.1156, 0.6584],
];

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct FileBinding {
    path: PathBuf,
    sha256: String,
    bytes: u64,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    phase: String,
    out_dir: PathBuf,
    expected_test_executable_sha256: String,
    input_order: FileBinding,
    held_rgb16: FileBinding,
    held_linear: FileBinding,
    held_sensor: FileBinding,
    held_sensor_sidecar: FileBinding,
    warp_map: FileBinding,
}
fn digest(h: Sha256) -> String {
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn sha(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(digest(h))
}
fn hash_string(s: &str) -> bool {
    s.len() == 64
        && s.bytes()
            .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v))
}
fn check_file(b: &FileBinding) -> Result<()> {
    ensure!(
        b.path.is_absolute() && b.bytes > 0 && hash_string(&b.sha256),
        "invalid file binding"
    );
    ensure!(
        std::fs::metadata(&b.path)?.len() == b.bytes && sha(&b.path)? == b.sha256,
        "bound file differs: {}",
        b.path.display()
    );
    Ok(())
}
fn file_record(path: &Path) -> Result<Value> {
    Ok(json!({"path":path,"sha256":sha(path)?,"bytes":std::fs::metadata(path)?.len()}))
}
fn save(path: &Path, value: &Value) -> Result<()> {
    let data = serde_json::to_vec_pretty(value)?;
    ensure!(
        data.len() <= 4 << 20,
        "diagnostic JSON exceeds4MiB; no truncation permitted"
    );
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    f.write_all(&data)?;
    f.write_all(b"\n")?;
    Ok(())
}
fn stamp(path: &Path) -> Result<(u64, SystemTime)> {
    let m = std::fs::metadata(path)?;
    Ok((m.len(), m.modified()?))
}
fn f32_hash(values: &[f32]) -> String {
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in values.chunks(bytes.len() / 4) {
        for (dst, v) in bytes.chunks_exact_mut(4).zip(chunk) {
            dst.copy_from_slice(&v.to_bits().to_le_bytes());
        }
        h.update(&bytes[..4 * chunk.len()]);
    }
    digest(h)
}
fn active_hash(frame: &Frame) -> String {
    let mut h = Sha256::new();
    let mut row = vec![0u8; 2 * frame.active.width];
    for y in 0..frame.active.height {
        for (dst, v) in row.chunks_exact_mut(2).zip(frame.active_row(y)) {
            dst.copy_from_slice(&v.to_le_bytes());
        }
        h.update(&row);
    }
    digest(h)
}
fn exact_display(path: &Path) -> Result<strehl_edit::DisplayBaseline> {
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?;
    ensure!(
        d.dimensions()? == (6896, 4596) && d.colortype()? == tiff::ColorType::RGB(32),
        "held linear type/extent"
    );
    let desc = d.get_tag_ascii_string(tiff::tags::Tag::ImageDescription)?;
    let line = desc
        .lines()
        .find_map(|s| s.strip_prefix("DisplayBaseline: "))
        .context("held DisplayBaseline absent")?;
    let v: strehl_edit::DisplayBaseline = serde_json::from_str(line)?;
    ensure!(
        [
            v.black.to_bits(),
            v.white.to_bits(),
            v.contrast.to_bits(),
            v.exposure_gain.to_bits()
        ] == [3111042816, 1049352204, 1057803469, 1065353216],
        "held display bits differ"
    );
    Ok(v)
}
fn material_metadata(path: &Path) -> Result<Value> {
    use tiff::tags::Tag;
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?;
    let description = d.get_tag_ascii_string(Tag::ImageDescription)?;
    let icc = d.get_tag_u8_vec(Tag::IccProfile)?;
    ensure!(!icc.is_empty(), "ICC absent");
    let mut h = Sha256::new();
    h.update(&icc);
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
    Ok(json!({"description":description,"icc_sha256":digest(h),"material_tags":tags}))
}
fn pixel_hash(path: &Path, float: bool) -> Result<String> {
    let mut limits = tiff::decoder::Limits::default();
    limits.decoding_buffer_size = 6896 * 4596 * 3 * 4;
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?.with_limits(limits);
    ensure!(
        d.dimensions()? == (6896, 4596)
            && d.colortype()? == tiff::ColorType::RGB(if float { 32 } else { 16 }),
        "RGB master type/extent"
    );
    let hash = match d.read_image()? {
        tiff::decoder::DecodingResult::F32(v) if float => {
            ensure!(
                v.len() == 6896 * 4596 * 3 && v.iter().all(|v| v.is_finite()),
                "finite complete float image required"
            );
            f32_hash(&v)
        }
        tiff::decoder::DecodingResult::U16(v) if !float => {
            ensure!(v.len() == 6896 * 4596 * 3, "complete RGB16 required");
            let mut h = Sha256::new();
            let mut bytes = vec![0u8; 65536];
            for chunk in v.chunks(bytes.len() / 2) {
                for (dst, v) in bytes.chunks_exact_mut(2).zip(chunk) {
                    dst.copy_from_slice(&v.to_le_bytes());
                }
                h.update(&bytes[..2 * chunk.len()]);
            }
            digest(h)
        }
        _ => anyhow::bail!("RGB master sample storage differs"),
    };
    ensure!(!d.more_images(), "one TIFF page required");
    Ok(hash)
}
fn validate_frame(f: &Frame, full: PlaneGeometry) -> Result<()> {
    ensure!(
        f.camera == "ILCE-7CM2"
            && f.iso == Some(100.0)
            && f.levels
                == Levels {
                    black: 512.0,
                    white: 15360.0
                }
            && f.geometry() == full
            && f.active.width == 7032
            && f.active.height == 4688
            && f.wb_coeffs[..3] == [1637.0 / 1024.0, 1.0, 2774.0 / 1024.0]
            && f.xyz_to_cam_rgb() == Some(MATRIX),
        "held source metadata changed"
    );
    Ok(())
}
struct OneSource<'a> {
    frame: &'a Frame,
    index: usize,
}
impl PyramidFrameSource for OneSource<'_> {
    fn len(&self) -> usize {
        299
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        ensure!(index == self.index, "unexpected original decode request");
        Ok(self.frame.clone())
    }
}
fn write_baseline(
    out: &Path,
    name: &str,
    planes: &[Vec<f32>],
    levels: Levels,
    wb: [f32; 4],
    dev: &image_out::Develop,
) -> Result<Value> {
    let (w, h) = (2 * CROP[2], 2 * CROP[3]);
    ensure!(
        planes.len() == 4
            && planes
                .iter()
                .all(|p| p.len() == CROP[2] * CROP[3] && p.iter().all(|v| v.is_finite())),
        "finite four-plane result required"
    );
    let cfa = out.join(format!("{name}-cfa-dn.f32le"));
    let mut f = BufWriter::new(OpenOptions::new().write(true).create_new(true).open(&cfa)?);
    let mut row = vec![0u8; 4 * w];
    for y in 0..h {
        for x in 0..w {
            let value = planes[2 * (y % 2) + x % 2][(y / 2) * CROP[2] + x / 2];
            row[4 * x..4 * x + 4].copy_from_slice(&value.to_le_bytes());
        }
        f.write_all(&row)?;
    }
    f.flush()?;
    drop(f);
    let gains = [wb[0] / wb[1], 1.0, 1.0, wb[2] / wb[1]];
    let mut mosaic = vec![0.0f32; w * h];
    mosaic.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
        for (x, v) in row.iter_mut().enumerate() {
            let c = 2 * (y % 2) + x % 2;
            // Preserve the exact commissioned native writer multiplication order.
            *v = planes[c][(y / 2) * CROP[2] + x / 2].max(0.0) * gains[c] * 1.0 / levels.range();
        }
    });
    let master = out.join(format!("{name}-master.tiff"));
    let linear = out.join(format!("{name}-linear.tiff"));
    image_out::write_demosaiced_with_master(&master, w, h, &mosaic, dev, Some(&linear), None)?;
    drop(mosaic);
    Ok(
        json!({"name":name,"cfa":file_record(&cfa)?,"rgb16":file_record(&master)?,
        "linear_rgb32":file_record(&linear)?,"entire_output":true,
        "cfa_format":"headerless RGGB f32LE, black-subtracted DN, native6896x4596",
        "linear_semantics":"post camera highlight/matrix development, pre tone; BT.709/D65; not invertible original camera RGB",
        "camera_rgb":null,"camera_rgb_reason":"not exposed by unchanged commissioned writer; no inverse conversion"}),
    )
}

fn same_planes(a: &[Vec<f32>], b: &[Vec<f32>]) -> bool {
    a.len() == b.len()
        && a.iter().zip(b).all(|(a, b)| {
            a.len() == b.len() && a.iter().zip(b).all(|(x, y)| x.to_bits() == y.to_bits())
        })
}
fn u16_hash(v: &[u16]) -> String {
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in v.chunks(bytes.len() / 2) {
        for (dst, v) in bytes.chunks_exact_mut(2).zip(chunk) {
            dst.copy_from_slice(&v.to_le_bytes());
        }
        h.update(&bytes[..2 * chunk.len()]);
    }
    digest(h)
}
fn write_f32(path: &Path, v: &[f32]) -> Result<Value> {
    ensure!(
        v.iter().all(|v| v.is_finite()),
        "finite f32 output required"
    );
    let mut f = BufWriter::new(OpenOptions::new().write(true).create_new(true).open(path)?);
    let mut bytes = vec![0u8; 65536];
    for chunk in v.chunks(bytes.len() / 4) {
        for (dst, v) in bytes.chunks_exact_mut(4).zip(chunk) {
            dst.copy_from_slice(&v.to_le_bytes());
        }
        f.write_all(&bytes[..4 * chunk.len()])?;
    }
    f.flush()?;
    drop(f);
    file_record(path)
}
fn write_known_cfa(path: &Path, planes: &[Vec<f32>]) -> Result<Value> {
    let (w, h) = (2 * CROP[2], 2 * CROP[3]);
    ensure!(
        planes.len() >= 4
            && planes[..4]
                .iter()
                .all(|p| p.len() == CROP[2] * CROP[3] && p.iter().all(|v| v.is_finite())),
        "finite known4 output required"
    );
    let mut f = BufWriter::new(OpenOptions::new().write(true).create_new(true).open(path)?);
    let mut row = vec![0u8; 4 * w];
    for y in 0..h {
        for x in 0..w {
            row[4 * x..4 * x + 4].copy_from_slice(
                &planes[2 * (y % 2) + x % 2][(y / 2) * CROP[2] + x / 2].to_le_bytes(),
            );
        }
        f.write_all(&row)?;
    }
    f.flush()?;
    drop(f);
    file_record(path)
}
fn write_arm(
    out: &Path,
    name: &str,
    planes: &[Vec<f32>],
    levels: Levels,
    wb: [f32; 4],
    dev: &image_out::Develop,
    checkpoint: bool,
) -> Result<Value> {
    ensure!(
        (name == "baseline" && planes.len() == 4) || (name == "candidate" && planes.len() == 12),
        "arm/plane count"
    );
    let (w, h) = (2 * CROP[2], 2 * CROP[3]);
    let master = out.join(format!("{name}-master.tiff"));
    let linear = out.join(format!("{name}-linear.tiff"));
    let camera = phase_packed_rgb::camera_rgb(planes, CROP[2], CROP[3], levels, wb)?;
    ensure!(
        camera.len() == w * h * 3 && camera.iter().all(|v| v.is_finite()),
        "finite complete camera RGB"
    );
    let camera_file = write_f32(
        &out.join(format!("{name}-camera-rgb-normalized.f32le")),
        &camera,
    )?;
    let mut developed = vec![0u16; camera.len()];
    developed
        .par_chunks_mut(3)
        .zip(camera.par_chunks(3))
        .for_each(|(out, p)| {
            out.copy_from_slice(&image_out::develop_pixel([p[0], p[1], p[2]], dev))
        });
    let expected_rgb = u16_hash(&developed);
    let matrix = dev.matrix.context("held camera matrix")?;
    let mut linear_pixels = vec![0.0f32; camera.len()];
    linear_pixels
        .par_chunks_mut(3)
        .zip(camera.par_chunks(3))
        .for_each(|(out, p)| out.copy_from_slice(&matrix.develop([p[0], p[1], p[2]])));
    ensure!(
        linear_pixels.iter().all(|v| v.is_finite()),
        "finite developed linear RGB"
    );
    let expected_linear = f32_hash(&linear_pixels);
    drop(camera);
    let mut record = if name == "baseline" {
        drop(developed);
        drop(linear_pixels);
        // The normal writer independently performs final MHC. Full readback
        // below checks the exposed camera-RGB helper against that actual path.
        write_baseline(out, name, planes, levels, wb, dev)?
    } else {
        image_out::write_rgb16_described(&master, w as u32, h as u32, &developed, dev)?;
        drop(developed);
        let tone = dev.tone.context("fixed tone")?;
        let image = strehl_edit::LinearImage {
            width: w as u32,
            height: h as u32,
            pixels: linear_pixels,
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: Some(strehl_edit::DisplayBaseline {
                black: tone.black,
                white: tone.white,
                contrast: tone.contrast,
                exposure_gain: dev.exposure_gain,
            }),
            baked_recipe: None,
        };
        strehl_edit::save_linear_tiff(&linear, &image)?;
        drop(image);
        json!({"name":name,"cfa":write_known_cfa(&out.join(format!("{name}-cfa-dn.f32le")),planes)?,
            "rgb16":file_record(&master)?,"linear_rgb32":file_record(&linear)?,"entire_output":true,
            "cfa_format":"known4 only, headerless native RGGB f32LE black-subtracted DN; equal to baseline",
            "linear_semantics":"post camera highlight/matrix development, pre tone; BT.709/D65"})
    };
    ensure!(
        pixel_hash(&master, false)? == expected_rgb
            && pixel_hash(&linear, true)? == expected_linear,
        "actual cameraRGB/native writer readback parity failed"
    );
    let oracle = if checkpoint {
        let path = out.join(format!("{name}-predecessor-writer.tiff"));
        let crop = align_cmd::CropRect {
            x: CROP[0],
            y: CROP[1],
            width: CROP[2],
            height: CROP[3],
        };
        phase_packed_rgb::full_stack::write_planes(&path, planes, crop, levels, wb, dev)?;
        ensure!(
            pixel_hash(&path, false)? == expected_rgb,
            "unchanged predecessor writer differs"
        );
        file_record(&path)?
    } else {
        Value::Null
    };
    record["camera_rgb"] = camera_file;
    record["camera_rgb_reason"] = Value::Null;
    record["camera_rgb_semantics"] = json!(
        "HWC f32LE, max0 per collapsed plane then WB/range normalized; baseline final MHC may produce signed estimates; not original signedDN or inverse-developed data"
    );
    record["final_mhc_stage_applied"] = json!(name == "baseline");
    record["pixel_hashes"] = json!({"rgb16":expected_rgb,"linear_rgb32":expected_linear});
    record["material_metadata"] = material_metadata(&master)?;
    record["linear_material_metadata"] = material_metadata(&linear)?;
    record["writer_camera_path_parity_exact"] = json!(true);
    record["predecessor_writer_checkpoint"] = oracle;
    record["collapsed_plane_hashes"] =
        json!(planes.iter().map(|p| f32_hash(p)).collect::<Vec<_>>());
    Ok(record)
}

fn run(full_run: bool) -> Result<()> {
    let started = Instant::now();
    let cfg_path = PathBuf::from(
        std::env::var_os("STREHL_WEEVIL_FUSION_ORDER_CONFIG")
            .context("fusion-order config required")?,
    );
    ensure!(
        cfg_path.is_absolute() && std::fs::metadata(&cfg_path)?.len() <= 65536,
        "bounded absolute config"
    );
    let cfg_binding = file_record(&cfg_path)?;
    let config: Config = serde_json::from_slice(&std::fs::read(&cfg_path)?)?;
    ensure!(
        config.schema == 1
            && config.phase == (if full_run { "full" } else { "cost" })
            && hash_string(&config.expected_test_executable_sha256),
        "fixed phase/schema/executable"
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
    let exe = std::env::current_exe()?;
    ensure!(
        sha(&exe)? == config.expected_test_executable_sha256,
        "test executable differs"
    );
    for (b, expected) in [
        (&config.input_order, ORDER_SHA),
        (&config.warp_map, MAP_SHA),
        (&config.held_rgb16, RGB_SHA),
        (&config.held_linear, LINEAR_SHA),
        (&config.held_sensor, SENSOR_SHA),
        (&config.held_sensor_sidecar, SIDECAR_SHA),
    ] {
        ensure!(b.sha256 == expected, "held identity substituted");
        check_file(b)?;
    }
    for key in [
        "STREHL_FIX_CA",
        "STREHL_DEFECT",
        "STREHL_FINE_SUPPORT",
        "STREHL_TEMPORAL_ENERGY",
        "STREHL_SPATIAL_NOISE_FLOOR",
        "STREHL_GPU_GATHER",
        "STREHL_DIRECT_PLANES",
    ] {
        ensure!(
            std::env::var(key).as_deref() == Ok("off"),
            "{key}=off required"
        );
    }
    ensure!(
        std::env::var("RAYON_NUM_THREADS").as_deref() == Ok("4")
            && std::env::var("STREHL_PYRAMID_WORKERS").as_deref() == Ok("4")
            && std::env::var("STREHL_PROBE_GATHER").as_deref() == Ok("green")
            && std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
            && std::env::var_os("STREHL_GATE_FLOOR_SCALE").is_none()
            && std::env::var_os("STREHL_ONLY_FRAME").is_none()
            && matches!(
                std::env::var("STREHL_DEMOSAIC").as_deref(),
                Err(std::env::VarError::NotPresent) | Ok("malvar")
            ),
        "held normal environment"
    );
    ensure!(
        align_cmd::fullres_gather_enabled()
            && gatefloor::enabled()
            && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Off
            && !align_cmd::native_gpu_integration::gpu_gather_enabled()?
            && strehl_core::pyramid::fine_support_candidate::environment_mode()
                == strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "literal CPU remosaic/extract required"
    );
    ensure!(
        std::env::var_os("STREHL_WARPMAP")
            .is_some_and(|p| PathBuf::from(p).canonicalize().ok()
                == config.warp_map.path.canonicalize().ok()),
        "isolated held warp map required"
    );
    let order: Vec<Value> = serde_json::from_slice(&std::fs::read(&config.input_order.path)?)?;
    ensure!(order.len() == 299, "exact299 source order");
    let paths = order
        .iter()
        .map(|v| v["path"].as_str().map(PathBuf::from).context("source path"))
        .collect::<Result<Vec<_>>>()?;
    let source_dir = paths[0].parent().context("source folder")?.canonicalize()?;
    ensure!(
        !config
            .warp_map
            .path
            .canonicalize()?
            .starts_with(&source_dir),
        "map inside read-only corpus"
    );
    let before = paths.iter().map(|p| stamp(p)).collect::<Result<Vec<_>>>()?;
    for (i, (path, row)) in paths.iter().zip(&order).enumerate() {
        ensure!(
            path.is_absolute()
                && path.parent().context("source parent")?.canonicalize()? == source_dir
                && path.file_name().and_then(|v| v.to_str())
                    == Some(format!("DSC{:05}.ARW", i + 1).as_str())
                && row["index"].as_u64() == Some(i as u64)
                && row["bytes"].as_u64() == Some(before[i].0)
                && row["mtime_ns"].as_u64()
                    == Some(
                        before[i]
                            .1
                            .duration_since(SystemTime::UNIX_EPOCH)?
                            .as_nanos() as u64
                    )
                && row["sha256"].as_str() == Some(sha(path)?.as_str()),
            "original identity differs at{i}"
        );
    }
    let entries = paths
        .iter()
        .zip(&before)
        .map(|(p, s)| {
            Ok((
                p.file_name()
                    .and_then(|v| v.to_str())
                    .context("filename")?
                    .to_owned(),
                s.0,
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    let map = WarpMap::load(&config.warp_map.path)?;
    map.provenance()
        .stack
        .check(&StackIdentity::from_entries("107MSDCF", &entries))?;
    let full = PlaneGeometry {
        width: 3516,
        height: 2344,
    };
    let crop = align_cmd::CropRect {
        x: CROP[0],
        y: CROP[1],
        width: CROP[2],
        height: CROP[3],
    };
    ensure!(
        map.len() == 299
            && map.placed_count() == 299
            && map.geometry() == full
            && map.provenance().reference == 149
            && map.resampler() == Resampler::CatmullRom,
        "held map contract"
    );
    let mut support = Vec::new();
    for (i, path) in paths.iter().enumerate() {
        let identity = strehl_raw::identity(path);
        ensure!(
            strehl_core::optics::profile_for_capture_env(
                identity.model.as_deref(),
                identity.lens_type3
            )?
            .is_none(),
            "ordinary CA must be off"
        );
        support.push(phase_packed_rgb::full_stack::full_source_supported(
            map.placement(i)?,
            full,
            crop,
            None,
        ));
    }
    std::fs::create_dir(&config.out_dir)?;
    save(
        &config.out_dir.join("support.json"),
        &json!({"all299_twelve_pull_support":support,"crop_quad_xywh":CROP,"inset_added":0}),
    )?;
    ensure!(
        support.iter().all(|v| *v),
        "fixed twelve-pull support refused; no inset repair"
    );
    let cfg = MergeConfig::default();
    ensure!(
        cfg.bands == 7
            && cfg.gate == 2.0
            && cfg.exponent == 2.0
            && cfg.sharpen_per_octave == 1.4
            && cfg.select == SelectMode::SoftPower
            && cfg.admission == AdmissionMode::HardFloor
            && cfg.base == BaseBand::Mean
            && cfg.mean_coarse == 0
            && cfg.hull == Hull::InputRange
            && cfg.fallback == Fallback::Mean
            && cfg.significance_scale == 0.0,
        "held merge defaults"
    );
    let display = exact_display(&config.held_linear.path)?;
    let held_material = material_metadata(&config.held_rgb16.path)?;
    let held_linear_material = material_metadata(&config.held_linear.path)?;
    ensure!(
        pixel_hash(&config.held_rgb16.path, false)? == RGB_PIXELS_SHA
            && pixel_hash(&config.held_linear.path, true)? == LINEAR_PIXELS_SHA,
        "held full baseline changed"
    );
    let indices = if full_run {
        (0..299).collect::<Vec<_>>()
    } else {
        vec![149]
    };
    let clock = Instant::now();
    let first = strehl_raw::decode(&paths[indices[0]])?;
    let first_decode_seconds = clock.elapsed().as_secs_f64();
    validate_frame(&first, full)?;
    let levels = first.levels;
    let wb = first.wb_coeffs;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    ensure!(
        noise.is_trustworthy() && noise.prnu().is_none(),
        "one injected noise model"
    );
    let plan = phase_packed_rgb::full_stack::chunk_plan(full, first.allocated_bytes(), 299, cfg);
    ensure!(
        plan.canonical_chunks == 4 && plan.per_chunk == 75,
        "canonical four-plane chunk plan"
    );
    let pool = ThreadPoolBuilder::new().num_threads(4).build()?;
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    let mut base = BandWorker::new(PyramidDomain::cropped(full, crop)?, cfg);
    let mut packed = BandMerge::new(crop.width, crop.height, 12, cfg);
    let mut packed_ws = FrameWorkspace::new(&sizes, 12);
    let (mut base_total, mut packed_total) = (None, None);
    let mut first = Some(first);
    let mut evidence = Vec::new();
    let environment = std::env::vars()
        .filter(|(k, _)| k.starts_with("STREHL_") || k == "RAYON_NUM_THREADS")
        .collect::<std::collections::BTreeMap<_, _>>();
    save(
        &config.out_dir.join("started.json"),
        &json!({"schema":1,"config":config,"config_binding":cfg_binding,
        "executable":file_record(&exe)?,"environment":environment,"normal_config":format!("{cfg:?}"),"noise":format!("{noise:?}"),
        "plan":plan,"display":display,"levels":[levels.black,levels.white],"wb_bits":wb.map(f32::to_bits),
        "matrix_bits":MATRIX.map(|r|r.map(f32::to_bits)),"scope":"unchanged non-native twelve-plane diagnostic"}),
    )?;
    let processing = Instant::now();
    pool.install(||->Result<()> {
        for (position,&index) in indices.iter().enumerate() {
            let t=Instant::now(); let dt=Instant::now();
            let frame=match first.take() {Some(v)=>v,None=>strehl_raw::decode(&paths[index])?};
            let decode_seconds=if position==0 {first_decode_seconds} else {dt.elapsed().as_secs_f64()};
            validate_frame(&frame,full)?; let active=active_hash(&frame);
            let source=OneSource {frame:&frame,index}; let fold_start=Instant::now();
            ensure!(base.fold(&source,index,levels,&noise,Some(&map),None)?,"canonical source refused");
            let baseline_seconds=fold_start.elapsed().as_secs_f64();
            let extra_start=Instant::now();
            // Checkpoint commissions helper coordinates through actual current CPU
            // consumer. Full run reuses known4 rather than replacing them.
            let gathered=phase_packed_rgb::full_stack::gather_full_source(&frame,map.placement(index)?,full,crop,None,if full_run {4} else {0})?;
            if !full_run {ensure!(same_planes(&gathered[..4],&base.planes),"source149 all12 helper known4 != CPU consumer");}
            let extra=if full_run {gathered.as_slice()} else {&gathered[4..]};
            ensure!(extra.len()==8,"exact missing8 population");
            let refs=base.planes.iter().chain(extra.iter()).map(Vec::as_slice).collect::<Vec<_>>();
            packed_ws.next_frame();
            packed.add_frame_with_gain(&refs,&base.luma,&base.var,(!base.beta.is_empty()).then_some(base.beta.as_slice()),&mut packed_ws);
            let fields=if index==149 {json!({"known4":base.planes.iter().map(|p|f32_hash(p)).collect::<Vec<_>>(),
                "missing8":extra.iter().map(|p|f32_hash(p)).collect::<Vec<_>>(),"guide":f32_hash(&base.luma),"variance":f32_hash(&base.var)})} else {Value::Null};
            let candidate_seconds=extra_start.elapsed().as_secs_f64();
            drop(refs);
            if !full_run {
                let a=base.merge.finish(&mut Workspace::new(&sizes));
                let b=packed.finish(&mut Workspace::new(&sizes));
                ensure!(same_planes(&a,&base.planes) && same_planes(&b[..4],&base.planes),"single-source known4 hull identity");
                ensure!(same_planes(&b[4..],extra),"single-source missing8 hull identity");
            }
            drop(gathered);
            ensure!(active_hash(&frame)==active,"original active CFA mutated");
            evidence.push(json!({"index":index,"native_decode_count":1,"active_u16_sha256":active,"fields":fields,
                "beta_bits":base.beta.iter().map(|v|v.to_bits()).collect::<Vec<_>>(),"decode_seconds":decode_seconds,
                "baseline_seconds":baseline_seconds,"missing8_and_fold_seconds":candidate_seconds}));
            let last=position+1==indices.len();
            if last || (index+1)%plan.per_chunk==0 {
                phase_packed_rgb::full_stack::absorb_chunk(&mut base_total,&mut base.merge,crop.width,crop.height,4,cfg);
                phase_packed_rgb::full_stack::absorb_chunk(&mut packed_total,&mut packed,crop.width,crop.height,12,cfg);
                if !last {base.reset_chunk(); packed.reset_for_reuse();}
            }
            eprintln!("WEEVIL_FUSION {}/{} source{} {:.3}s elapsed {:.3}s",position+1,indices.len(),index,t.elapsed().as_secs_f64(),started.elapsed().as_secs_f64());
        }
        Ok(())
    })?;
    let processing_seconds = processing.elapsed().as_secs_f64();
    drop(base);
    drop(packed);
    drop(packed_ws);
    save(
        &config.out_dir.join("frames.json"),
        &json!({"frames":evidence,"indices":indices,"count":indices.len(),"native_decode_count":indices.len()}),
    )?;
    let base_total = base_total.context("baseline total")?;
    let packed_total = packed_total.context("candidate total")?;
    let averaged = base_total.averaged_fraction();
    let packed_averaged = packed_total.averaged_fraction();
    ensure!(
        averaged.len() == packed_averaged.len()
            && averaged
                .iter()
                .zip(&packed_averaged)
                .all(|(a, b)| a.to_bits() == b.to_bits()),
        "admission changed after chunks"
    );
    let finish = Instant::now();
    let baseline = pool.install(|| base_total.finish(&mut Workspace::new(&sizes)));
    drop(base_total);
    let candidate = pool.install(|| packed_total.finish(&mut Workspace::new(&sizes)));
    drop(packed_total);
    ensure!(
        same_planes(&baseline, &candidate[..4]),
        "collapsed known4 changed"
    );
    let gains = [wb[0] / wb[1], 1.0, wb[2] / wb[1]];
    let matrix = color::camera_to_srgb(MATRIX)
        .context("matrix")?
        .with_saturation(levels, gains, 1.0);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone {
        black: display.black,
        white: display.white,
        contrast: display.contrast,
    });
    dev.exposure_gain = display.exposure_gain;
    let mut outputs = Vec::new();
    for (name, planes) in [(NAMES[0], baseline), (NAMES[1], candidate)] {
        let mut record = pool
            .install(|| write_arm(&config.out_dir, name, &planes, levels, wb, &dev, !full_run))?;
        drop(planes);
        let material_exact = record["material_metadata"] == held_material
            && record["linear_material_metadata"] == held_linear_material;
        record["held_material_metadata_exact"] = json!(material_exact);
        ensure!(material_exact, "held writer metadata changed");
        save(
            &config.out_dir.join(format!("{name}-receipt.json")),
            &record,
        )?;
        if name == "baseline" {
            let exact = record["cfa"]["sha256"] == CFA_PAYLOAD_SHA
                && record["pixel_hashes"]["rgb16"] == RGB_PIXELS_SHA
                && record["pixel_hashes"]["linear_rgb32"] == LINEAR_PIXELS_SHA;
            save(
                &config.out_dir.join("baseline-identity.json"),
                &json!({"complete_golden_required":full_run,
                "exact":if full_run {json!(exact)} else {Value::Null},"material_metadata_exact":material_exact,
                "actual":record,"cost_scope":"source149 only; never compared to complete299 pixel golden"}),
            )?;
            ensure!(
                !full_run || exact,
                "complete held baseline payload parity failed; artifacts retained"
            );
        }
        outputs.push(record);
    }
    ensure!(
        outputs[0]["cfa"]["sha256"] == outputs[1]["cfa"]["sha256"],
        "delivered known4 CFA differs"
    );
    let finish_seconds = finish.elapsed().as_secs_f64();
    for (i, path) in paths.iter().enumerate() {
        ensure!(
            stamp(path)? == before[i] && order[i]["sha256"].as_str() == Some(sha(path)?.as_str()),
            "original bytes/metadata changed"
        );
    }
    for b in [
        &config.input_order,
        &config.warp_map,
        &config.held_rgb16,
        &config.held_linear,
        &config.held_sensor,
        &config.held_sensor_sidecar,
    ] {
        check_file(b)?;
    }
    ensure!(
        file_record(&cfg_path)? == cfg_binding
            && sha(&exe)? == config.expected_test_executable_sha256,
        "config/executable changed"
    );
    let mut receipt = json!({"schema":1,"status":if full_run {"COMPLETE299_WEEVIL_FUSION_ORDER_PAIR"} else {"COMPLETE_WEEVIL_FUSION_ORDER_SOURCE149_CHECKPOINT"},
        "complete":true,"phase":config.phase,"source_count":indices.len(),"indices":indices,"native_decode_count":indices.len(),
        "arms":outputs,"native_dimensions":[6896,4596],"crop_quad_xywh":CROP,"native_crop_origin":[68,46],
        "reference":149,"warp_map":config.warp_map,"resampler":"catmull-rom"});
    let parity = json!({"known4_after_finish_exact":true,"admission_exact":true,"averaged_fractions":averaged,
        "baseline_complete_golden_exact":if full_run {json!(true)} else {Value::Null},"baseline_material_metadata_exact":true,
        "source149_all12_known4_gather_exact":if full_run {Value::Null} else {json!(true)},
        "source149_hull_exact":if full_run {Value::Null} else {json!(true)},"writer_camera_path_parity_exact":true,
        "canonical_noise_probes_preserved":true,"extra_noise_probes":0,"gather_backend":"cpu","direct_planes":"off",
        "canonical_arithmetic_chunks":[75,75,75,74],"native_endpoint_fulfilled":false});
    let evidence = json!({"configuration":config,"config_binding":cfg_binding,"test_executable":file_record(&exe)?,
        "frame_receipts":file_record(&config.out_dir.join("frames.json"))?,"support":file_record(&config.out_dir.join("support.json"))?,
        "baseline_identity":file_record(&config.out_dir.join("baseline-identity.json"))?,
        "all299_original_bytes_and_metadata_unchanged":true,"all_bound_inputs_unchanged":true,
        "first_decode_seconds":first_decode_seconds,"processing_seconds":processing_seconds,"finish_seconds":finish_seconds,
        "total_seconds":started.elapsed().as_secs_f64(),"quality_claim":false,"photographic_admission":false});
    receipt
        .as_object_mut()
        .unwrap()
        .extend(parity.as_object().unwrap().clone());
    receipt
        .as_object_mut()
        .unwrap()
        .extend(evidence.as_object().unwrap().clone());
    receipt["limits"] = json!({"prior_complete_photographic_nulls":["vitamin70","chip299"],"historical_flat_chroma_ratio":1.078951,
        "flat_1p05_pass":false,"cofocused_near_fine_far_coarse_control_qualified":false,
        "camera_rgb":"per-plane max0/WB/range normalised reconstructed estimates; not original signedDN",
        "peak_memory":"root owned-job measurement required","physical_placement_claim":false});
    save(&config.out_dir.join("receipt.json"), &receipt)?;
    Ok(())
}

#[test]
#[ignore = "root scheduled complete-domain source149 commissioning/cost"]
fn source149_checkpoint() -> Result<()> {
    run(false)
}

#[test]
#[ignore = "root scheduled complete299 unchanged twelve-plane photograph"]
fn complete299_pair() -> Result<()> {
    run(true)
}
