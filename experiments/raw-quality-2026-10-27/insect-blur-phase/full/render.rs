// Root-built, root-run diagnostic. Three maps, unchanged normal consumer/writer.
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
const NAMES: [&str; 3] = ["baseline", "p1", "p2"];
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
struct MapBinding {
    name: String,
    path: PathBuf,
    sha256: String,
    bytes: u64,
}
impl MapBinding {
    fn file(&self) -> FileBinding {
        FileBinding {
            path: self.path.clone(),
            sha256: self.sha256.clone(),
            bytes: self.bytes,
        }
    }
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    out_dir: PathBuf,
    expected_test_executable_sha256: String,
    input_order: FileBinding,
    held_rgb16: FileBinding,
    held_linear: FileBinding,
    held_sensor: FileBinding,
    held_sensor_sidecar: FileBinding,
    maps: Vec<MapBinding>,
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
fn write_result(
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

fn run() -> Result<()> {
    let total = Instant::now();
    let cfg_path = PathBuf::from(
        std::env::var_os("STREHL_INSECT_BLUR_PHASE_RENDER_CONFIG")
            .context("render config required")?,
    );
    ensure!(
        cfg_path.is_absolute() && std::fs::metadata(&cfg_path)?.len() <= 65536,
        "bounded absolute config required"
    );
    let cfg_binding = file_record(&cfg_path)?;
    let config: Config = serde_json::from_slice(&std::fs::read(&cfg_path)?)?;
    ensure!(
        config.schema == 1 && hash_string(&config.expected_test_executable_sha256),
        "schema/executable binding"
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
        "test executable changed"
    );
    for (binding, expected) in [
        (&config.input_order, ORDER_SHA),
        (&config.held_rgb16, RGB_SHA),
        (&config.held_linear, LINEAR_SHA),
        (&config.held_sensor, SENSOR_SHA),
        (&config.held_sensor_sidecar, SIDECAR_SHA),
    ] {
        ensure!(binding.sha256 == expected, "held input hash substituted");
        check_file(binding)?;
    }
    ensure!(
        config.maps.len() == 3 && config.maps.iter().zip(NAMES).all(|(m, n)| m.name == n),
        "exact baseline/p1/p2 map order required"
    );
    ensure!(config.maps[0].sha256 == MAP_SHA, "baseline map changed");
    for map in &config.maps {
        check_file(&map.file())?;
    }
    ensure!(
        std::env::var_os("STREHL_WARPMAP").is_some_and(
            |p| PathBuf::from(p).canonicalize().ok() == config.maps[0].path.canonicalize().ok()
        ),
        "isolated baseline STREHL_WARPMAP required"
    );
    for key in [
        "STREHL_FIX_CA",
        "STREHL_DEFECT",
        "STREHL_FINE_SUPPORT",
        "STREHL_TEMPORAL_ENERGY",
        "STREHL_SPATIAL_NOISE_FLOOR",
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
            && std::env::var("STREHL_GPU_GATHER").as_deref() == Ok("off")
            && std::env::var("STREHL_DIRECT_PLANES").as_deref() == Ok("off")
            && std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
            && std::env::var_os("STREHL_GATE_FLOOR_SCALE").is_none()
            && matches!(
                std::env::var("STREHL_DEMOSAIC").as_deref(),
                Err(std::env::VarError::NotPresent) | Ok("malvar")
            ),
        "fixed normal consumer environment"
    );
    ensure!(
        align_cmd::fullres_gather_enabled()
            && gatefloor::enabled()
            && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Off
            && !align_cmd::native_gpu_integration::gpu_gather_enabled()?
            && strehl_core::pyramid::fine_support_candidate::environment_mode()
                == strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "held CPU full-res remosaic/extract and canonical measured noise floor required"
    );
    let order: Vec<Value> = serde_json::from_slice(&std::fs::read(&config.input_order.path)?)?;
    ensure!(order.len() == 299, "exact299 originals required");
    let paths = order
        .iter()
        .map(|v| {
            v["path"]
                .as_str()
                .map(PathBuf::from)
                .context("original path")
        })
        .collect::<Result<Vec<_>>>()?;
    let source_dir = paths[0].parent().context("source parent")?.canonicalize()?;
    let before = paths.iter().map(|p| stamp(p)).collect::<Result<Vec<_>>>()?;
    for (i, (path, item)) in paths.iter().zip(&order).enumerate() {
        ensure!(
            path.is_absolute()
                && path.parent().context("original parent")?.canonicalize()? == source_dir
                && path.file_name().and_then(|v| v.to_str())
                    == Some(format!("DSC{:05}.ARW", i + 1).as_str())
                && item["index"].as_u64() == Some(i as u64)
                && item["bytes"].as_u64() == Some(before[i].0)
                && item["mtime_ns"].as_u64()
                    == Some(
                        before[i]
                            .1
                            .duration_since(SystemTime::UNIX_EPOCH)?
                            .as_nanos() as u64
                    )
                && item["sha256"].as_str() == Some(sha(path)?.as_str()),
            "original order/identity differs at{i}"
        );
    }
    for map in &config.maps {
        ensure!(
            !map.path.canonicalize()?.starts_with(&source_dir),
            "map must be outside read-only capture"
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
    let identity = StackIdentity::from_entries("107MSDCF", &entries);
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
    let mut maps = Vec::new();
    let mut support = Vec::new();
    for binding in &config.maps {
        let map = WarpMap::load(&binding.path)?;
        map.provenance().stack.check(&identity)?;
        ensure!(
            map.len() == 299
                && map.placed_count() == 299
                && map.geometry() == full
                && map.provenance().reference == 149
                && map.resampler() == Resampler::CatmullRom,
            "map population/gauge/resampler differs"
        );
        let supported = (0..299)
            .map(|i| {
                Ok(phase_packed_rgb::full_stack::full_source_supported(
                    map.placement(i)?,
                    full,
                    crop,
                    None,
                ))
            })
            .collect::<Result<Vec<_>>>()?;
        support.push(json!({"name":binding.name,"supported_by_source":supported,"all_supported":supported.iter().all(|v|*v)}));
        maps.push(map);
    }
    std::fs::create_dir(&config.out_dir)?;
    save(
        &config.out_dir.join("support.json"),
        &json!({"fixed_crop_quad_xywh":CROP,"arms":support,"post_crop_used":false}),
    )?;
    ensure!(
        support.iter().all(|v| v["all_supported"] == true),
        "candidate source support refused; support evidence retained"
    );
    for path in &paths {
        let id = strehl_raw::identity(path);
        ensure!(
            strehl_core::optics::profile_for_capture_env(id.model.as_deref(), id.lens_type3)?
                .is_none(),
            "CA profile unexpectedly active"
        );
    }
    let merge_cfg = MergeConfig::default();
    ensure!(
        merge_cfg.bands == 7
            && merge_cfg.gate == 2.0
            && merge_cfg.exponent == 2.0
            && merge_cfg.sharpen_per_octave == 1.4
            && merge_cfg.select == SelectMode::SoftPower
            && merge_cfg.admission == AdmissionMode::HardFloor
            && merge_cfg.base == BaseBand::Mean
            && merge_cfg.mean_coarse == 0
            && merge_cfg.hull == Hull::InputRange
            && merge_cfg.fallback == Fallback::Mean
            && merge_cfg.significance_scale == 0.0,
        "held normal merge defaults changed"
    );
    let display = exact_display(&config.held_linear.path)?;
    let held_material = material_metadata(&config.held_rgb16.path)?;
    let held_linear_material = material_metadata(&config.held_linear.path)?;
    ensure!(
        pixel_hash(&config.held_rgb16.path, false)? == RGB_PIXELS_SHA
            && pixel_hash(&config.held_linear.path, true)? == LINEAR_PIXELS_SHA,
        "held complete pixel identity differs"
    );
    let pool = ThreadPoolBuilder::new().num_threads(4).build()?;
    let decode_start = Instant::now();
    let first = strehl_raw::decode(&paths[0])?;
    let first_decode_seconds = decode_start.elapsed().as_secs_f64();
    validate_frame(&first, full)?;
    let levels = first.levels;
    let wb = first.wb_coeffs;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    ensure!(
        noise.is_trustworthy() && noise.prnu().is_none(),
        "one trustworthy injected temporal noise model required"
    );
    let plan =
        phase_packed_rgb::full_stack::chunk_plan(full, first.allocated_bytes(), 299, merge_cfg);
    ensure!(
        plan.canonical_chunks == 4 && plan.per_chunk == 75,
        "four held arithmetic chunks required"
    );
    let environment = std::env::vars()
        .filter(|(k, _)| k.starts_with("STREHL_") || k == "RAYON_NUM_THREADS")
        .collect::<std::collections::BTreeMap<_, _>>();
    save(
        &config.out_dir.join("started.json"),
        &json!({"schema":1,"configuration":config,"config_binding":cfg_binding,
        "test_executable":file_record(&exe)?,"environment":environment,"normal_config":format!("{merge_cfg:?}"),
        "plan":plan,"levels":[levels.black,levels.white],"wb_bits":wb.map(f32::to_bits),"noise":format!("{noise:?}"),
        "display":display,"matrix_bits":MATRIX.map(|r|r.map(f32::to_bits)),"native_dimensions":[6896,4596],
        "crop_quad_xywh":CROP,"canonical_noise_probes_preserved":true,"extra_green_phase_probes":0,"gather_backend":"cpu","quality_claim":false}),
    )?;
    let domain = PyramidDomain::cropped(full, crop)?;
    let mut workers: Vec<BandWorker> = (0..3).map(|_| BandWorker::new(domain, merge_cfg)).collect();
    let mut totals: [Option<BandMerge>; 3] = std::array::from_fn(|_| None);
    let sizes = level_sizes(crop.width, crop.height, merge_cfg.bands);
    let mut first = Some(first);
    let mut frames = Vec::new();
    let processing_start = Instant::now();
    pool.install(||->Result<()> {
        for chunk_start in (0..299).step_by(plan.per_chunk) {
            let end=(chunk_start+plan.per_chunk).min(299);
            for index in chunk_start..end {
                let t=Instant::now(); let dt=Instant::now();
                let frame=match first.take() {Some(v)=>v,None=>strehl_raw::decode(&paths[index])?};
                let decode_seconds=if index==0 {first_decode_seconds} else {dt.elapsed().as_secs_f64()};
                validate_frame(&frame,full)?; let active=active_hash(&frame);
                let source=OneSource {frame:&frame,index}; let mut arms=Vec::new();
                for arm in 0..3 {
                    let started=Instant::now();
                    ensure!(workers[arm].fold(&source,index,levels,&noise,Some(&maps[arm]),None)?,"{} refused source{index}",NAMES[arm]);
                    arms.push(json!({"name":NAMES[arm],"fold_seconds":started.elapsed().as_secs_f64(),
                        "canonical_beta_bits":workers[arm].beta.iter().map(|v|v.to_bits()).collect::<Vec<_>>() }));
                }
                ensure!(active_hash(&frame)==active,"decoded active CFA changed");
                frames.push(json!({"index":index,"native_decode_count":1,"active_u16_sha256":active,"decode_seconds":decode_seconds,"arms":arms}));
                eprintln!("BIPC_RENDER {}/299 index {} {:.3}s elapsed {:.3}s",index+1,index,t.elapsed().as_secs_f64(),total.elapsed().as_secs_f64());
            }
            for arm in 0..3 {
                phase_packed_rgb::full_stack::absorb_chunk(&mut totals[arm],&mut workers[arm].merge,crop.width,crop.height,4,merge_cfg);
                if end<299 {workers[arm].reset_chunk();}
            }
        }
        Ok(())
    })?;
    let processing_seconds = processing_start.elapsed().as_secs_f64();
    drop(workers);
    save(
        &config.out_dir.join("frames.json"),
        &json!({"frames":frames,"count":299,"decode_count":299,"map_order":NAMES}),
    )?;
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
    let finish_start = Instant::now();
    let mut outputs = Vec::new();
    for arm in 0..3 {
        let merge = totals[arm].take().context("missing complete arm")?;
        let averaged = merge.averaged_fraction();
        let planes = pool.install(|| merge.finish(&mut Workspace::new(&sizes)));
        drop(merge);
        let mut file =
            pool.install(|| write_result(&config.out_dir, NAMES[arm], &planes, levels, wb, &dev))?;
        drop(planes);
        let rgb = config.out_dir.join(format!("{}-master.tiff", NAMES[arm]));
        let linear = config.out_dir.join(format!("{}-linear.tiff", NAMES[arm]));
        let rgb_hash = pixel_hash(&rgb, false)?;
        let linear_hash = pixel_hash(&linear, true)?;
        let material = material_metadata(&rgb)?;
        let linear_material = material_metadata(&linear)?;
        file["pixel_hashes"] = json!({"rgb16":rgb_hash,"linear_rgb32":linear_hash});
        file["material_metadata"] = material.clone();
        file["linear_material_metadata"] = linear_material.clone();
        file["averaged_fractions"] = json!(averaged);
        save(
            &config.out_dir.join(format!("{}-receipt.json", NAMES[arm])),
            &file,
        )?;
        if arm == 0 {
            let exact = file["cfa"]["sha256"] == CFA_PAYLOAD_SHA
                && rgb_hash == RGB_PIXELS_SHA
                && linear_hash == LINEAR_PIXELS_SHA;
            let metadata_exact =
                material == held_material && linear_material == held_linear_material;
            save(
                &config.out_dir.join("baseline-identity.json"),
                &json!({"exact":exact,"material_metadata_exact":metadata_exact,
                "actual":file,"held_pixel_hashes":{"cfa":CFA_PAYLOAD_SHA,"rgb16":RGB_PIXELS_SHA,"linear_rgb32":LINEAR_PIXELS_SHA},
                "scope":"complete299 normal consumer; fixed held crop and development; TIFF file hashes may differ"}),
            )?;
            ensure!(
                exact && metadata_exact,
                "baseline parity failed; finite outputs retained, no candidate admission"
            );
        } else {
            ensure!(
                material == held_material && linear_material == held_linear_material,
                "candidate development metadata changed"
            );
        }
        outputs.push(file);
    }
    let finish_seconds = finish_start.elapsed().as_secs_f64();
    for (i, path) in paths.iter().enumerate() {
        ensure!(
            stamp(path)? == before[i] && order[i]["sha256"].as_str() == Some(sha(path)?.as_str()),
            "original source changed"
        );
    }
    for b in [
        &config.input_order,
        &config.held_rgb16,
        &config.held_linear,
        &config.held_sensor,
        &config.held_sensor_sidecar,
    ] {
        check_file(b)?;
    }
    for m in &config.maps {
        check_file(&m.file())?;
    }
    ensure!(
        file_record(&cfg_path)? == cfg_binding
            && sha(&exe)? == config.expected_test_executable_sha256,
        "config/executable changed"
    );
    let mut receipt = json!({"schema":1,"status":"COMPLETE299_INSECT_PHASE_MAP_RENDERS","all_frames_completed":true,
        "frames":299,"native_decode_count":299,"arms":outputs,"native_dimensions":[6896,4596],"crop_quad_xywh":CROP,
        "native_crop_origin":[68,46],"reference":149,"resampler":"catmull-rom","maps":config.maps,
        "baseline_identity_exact":true,"baseline_material_metadata_exact":true,"all_arm_development_identical":true,
        "canonical_noise_probes_preserved":true,"extra_green_phase_probes":0,"gather_backend":"cpu",
        "normal_fold_count":897,"arithmetic_chunks":[75,75,75,74]});
    let extra = json!({"configuration":config,"config_binding":cfg_binding,"test_executable":file_record(&exe)?,
        "frame_receipts":file_record(&config.out_dir.join("frames.json"))?,"support":file_record(&config.out_dir.join("support.json"))?,
        "baseline_identity":file_record(&config.out_dir.join("baseline-identity.json"))?,
        "all299_original_bytes_and_metadata_unchanged":true,"all_bound_inputs_unchanged":true,
        "first_decode_seconds":first_decode_seconds,"processing_seconds":processing_seconds,"finish_seconds":finish_seconds,
        "total_seconds":total.elapsed().as_secs_f64(),"peak_memory":"root terminal job accounting required",
        "quality_claim":false,"photographic_admission":false,"physical_placement_claim":false,
        "consumer_scope":"legacy per-source MHC/Catmull remosaic followed by canonical RAW pyramid; geometry-only workflow comparison",
        "camera_rgb_saved":false,"camera_rgb_reason":"actual writer does not expose it; no developed-linear inverse conversion"});
    receipt
        .as_object_mut()
        .unwrap()
        .extend(extra.as_object().unwrap().clone());
    save(&config.out_dir.join("receipt.json"), &receipt)?;
    Ok(())
}

#[test]
#[ignore = "root scheduled complete299 three-map photographic comparison"]
fn render_complete_weevil_phase_maps() -> Result<()> {
    run()
}
