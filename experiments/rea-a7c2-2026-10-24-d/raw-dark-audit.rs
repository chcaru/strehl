//! Bounded RAW-dark diagnostic; requires an explicit source directory.
//! No decoder implementation is used as an implementation reference.
//! One original u16 frame at a time; f32 black subtraction; f64 analysis moments.
use anyhow::{Context, Result, ensure};
use std::env;
use std::fmt::Write as _;
use std::fs::{self, File};
use std::io::{BufWriter, Write as _};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;
use strehl_core::CfaPlane;
use strehl_core::noise::Provenance;
use strehl_core::profile::noise_model_for;

const COUNT: usize = 20;
const SIDE: usize = 512;
const ROIS: [(usize, usize); 4] = [(512, 512), (5600, 512), (512, 3500), (3000, 1800)];
// Raster RGGB order, deliberately distinct from CfaPlane::ALL's enum order.
const PHASES: [CfaPlane; 4] = [CfaPlane::R, CfaPlane::G1, CfaPlane::G2, CfaPlane::B];
const NAMES: [&str; 4] = ["R", "G1", "G2", "B"];

#[derive(Clone, Copy, Default)]
struct Moment {
    n: usize,
    mean: f64,
    m2: f64,
}
impl Moment {
    fn add(&mut self, x: f64) {
        self.n += 1;
        let d = x - self.mean;
        self.mean += d / self.n as f64;
        self.m2 += d * (x - self.mean);
    }
    fn variance(&self) -> f64 {
        assert!(self.n > 1);
        self.m2 / (self.n - 1) as f64
    }
}

#[derive(Clone, Copy, Default)]
struct Counts {
    zero: usize,
    below_black: usize,
    at_black: usize,
    at_or_above_white: usize,
}

fn quote(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c < ' ' => {
                write!(out, "\\u{:04x}", c as u32).unwrap();
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

fn stamp(path: &Path) -> Result<(u64, u128)> {
    let m = fs::metadata(path)?;
    Ok((
        m.len(),
        m.modified()?.duration_since(UNIX_EPOCH)?.as_nanos(),
    ))
}

fn fresh_output(path: &Path, source: &Path) -> Result<PathBuf> {
    ensure!(path.is_absolute(), "output must be absolute");
    ensure!(
        !path.exists(),
        "output must be fresh, not an existing directory"
    );
    let parent = path
        .parent()
        .context("output needs a parent")?
        .canonicalize()?;
    let leaf = path
        .file_name()
        .context("output needs a final directory name")?;
    let out = parent.join(leaf);
    let src = source
        .canonicalize()?
        .to_string_lossy()
        .to_ascii_lowercase();
    let dst = out.to_string_lossy().to_ascii_lowercase();
    ensure!(
        dst != src && !dst.starts_with(&(src + std::path::MAIN_SEPARATOR_STR)),
        "output inside capture corpus refused"
    );
    fs::create_dir(&out)?;
    Ok(out)
}

// Exact small arithmetic controls execute before any decode when root runs the example.
fn commission() -> Result<()> {
    let mut a = Moment::default();
    let mut shifted = Moment::default();
    let mut twice = Moment::default();
    for x in [0.0, 1.0, 2.0, 3.0] {
        a.add(x);
        shifted.add(x + 500.0); // A stable pixel offset must cancel temporally.
        twice.add(2.0 * x);
    }
    ensure!(
        (a.variance() - 5.0 / 3.0).abs() < 1e-12,
        "sample variance divisor control"
    );
    ensure!(
        (shifted.variance() - a.variance()).abs() < 1e-12,
        "fixed offset must cancel"
    );
    ensure!(
        (twice.variance() / a.variance() - 4.0).abs() < 1e-12,
        "variance scales quadratically"
    );
    ensure!(
        (twice.variance().sqrt() / a.variance().sqrt() - 2.0).abs() < 1e-12,
        "sigma scales linearly"
    );
    let mut flat = [Moment::default(); 2];
    for _ in 0..COUNT {
        flat[0].add(400.0);
        flat[1].add(600.0);
    }
    ensure!(
        flat.iter().all(|m| m.variance() == 0.0),
        "stable spatial pattern is not temporal noise"
    );
    ensure!(
        flat[0].mean != flat[1].mean,
        "fixed-pattern foil lacks spatial structure"
    );
    ensure!(
        quote("a\\b\n\"") == "\"a\\\\b\\n\\\"\"",
        "JSON escape control"
    );
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<_> = env::args_os().collect();
    if args.len() == 2 && args[1].to_str() == Some("--commission-only") {
        commission()?;
        println!("REA_DARK_AUDIT_COMMISSION_PASS (no files decoded)");
        return Ok(());
    }
    ensure!(
        args.len() == 5
            && args[1].to_str() == Some("--source")
            && args[3].to_str() == Some("--out"),
        "usage: rea-dark-audit --source <existing-directory> --out <fresh-absolute-directory> | --commission-only"
    );
    commission()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(1)
        .build_global()?;
    ensure!(rayon::current_num_threads() == 1, "one worker required");
    let source = Path::new(&args[2]);
    ensure!(source.is_dir(), "--source must be an existing directory");
    let out = fresh_output(Path::new(&args[4]), source)?;
    fs::write(out.join("run-status.txt"), "STARTED_NOT_COMPLETE\n")?;
    let mut frame_means = BufWriter::new(File::create(out.join("frame-means.csv"))?);
    writeln!(
        frame_means,
        "source_number,roi_index,phase,mean_signed_dn,mean_code_dn"
    )?;
    let mut moments = vec![vec![Moment::default(); SIDE * SIDE]; ROIS.len()];
    let mut counts = [[Counts::default(); 4]; 4];
    let mut mean_series = [[Moment::default(); 4]; 4];
    let mut frames = Vec::new();
    let mut first_identity = None;
    let mut first_model = None;
    let mut first_descriptor = String::new();

    for index in 0..COUNT {
        let number = index + 3;
        let path = source.join(format!("DSC{number:05}.ARW"));
        let before = stamp(&path)?;
        let frame =
            strehl_raw::decode(&path).with_context(|| format!("decode {}", path.display()))?;
        ensure!(
            stamp(&path)? == before,
            "input metadata changed while decoding"
        );
        ensure!(
            frame.data.len()
                == frame
                    .stride
                    .checked_mul(frame.buffer_height)
                    .context("buffer size overflow")?,
            "buffer dimensions disagree"
        );
        ensure!(
            frame
                .active
                .x
                .checked_add(frame.active.width)
                .is_some_and(|x| x <= frame.stride)
                && frame
                    .active
                    .y
                    .checked_add(frame.active.height)
                    .is_some_and(|y| y <= frame.buffer_height),
            "active area outside storage"
        );
        ensure!(
            (frame.active.width, frame.active.height) == (7032, 4688),
            "active dimensions do not match the frozen dark-output gauge"
        );
        ensure!(
            frame.active.x % 2 == 0 && frame.active.y % 2 == 0,
            "active origin changes declared RGGB parity"
        );
        ensure!(
            frame.levels.black.is_finite()
                && frame.levels.white.is_finite()
                && frame.levels.white > frame.levels.black,
            "invalid decoder levels"
        );
        let iso = frame
            .iso
            .context("ISO absent; refuse a guessed noise model")?;
        ensure!(iso.is_finite() && iso > 0.0, "invalid ISO");
        let model = noise_model_for(&frame.camera, frame.iso, frame.levels);
        ensure!(
            model.provenance == Provenance::Profile,
            "profile unavailable; fallback model refused"
        );
        let identity = (
            frame.camera.clone(),
            iso.to_bits(),
            frame.levels.black.to_bits(),
            frame.levels.white.to_bits(),
            frame.active,
            frame.stride,
            frame.buffer_height,
        );
        if let Some(first) = &first_identity {
            ensure!(
                first == &identity,
                "camera/ISO/levels/decoded gauge changed across the fixed block"
            );
        } else {
            first_identity = Some(identity);
            first_model = Some(model.clone());
        }
        for phase in PHASES {
            let p = model.plane(phase);
            ensure!(
                p.sigma(0.0).is_finite() && p.sigma(0.0) > 0.0,
                "invalid zero-signal profile sigma"
            );
            ensure!(
                p == first_model.as_ref().unwrap().plane(phase),
                "noise profile changed across block"
            );
        }
        let a = frame.active;
        let descriptor = format!(
            "{{\"source_number\":{number},\"path\":{},\"file_bytes\":{},\"modified_unix_ns\":{},\"camera\":{},\"iso\":{iso},\"black_dn\":{},\"white_dn\":{},\"active_in_buffer_xywh\":[{},{},{},{}],\"buffer_stride_samples\":{},\"buffer_height_rows\":{},\"buffer_margins_ltrb\":[{},{},{},{}]}}",
            quote(&path.to_string_lossy()),
            before.0,
            before.1,
            quote(&frame.camera),
            frame.levels.black,
            frame.levels.white,
            a.x,
            a.y,
            a.width,
            a.height,
            frame.stride,
            frame.buffer_height,
            a.x,
            a.y,
            frame.stride - a.x - a.width,
            frame.buffer_height - a.y - a.height
        );
        let mut roi_descriptors = Vec::new();
        for (r, &(x, y)) in ROIS.iter().enumerate() {
            ensure!(
                x + SIDE <= a.width && y + SIDE <= a.height,
                "ROI {r} outside decoded active area"
            );
            let mut per_frame = [Moment::default(); 4];
            let mut original = if index == 0 {
                Some(Vec::with_capacity(SIDE * SIDE * 2))
            } else {
                None
            };
            for yy in 0..SIDE {
                let row_start = (a.y + y + yy) * frame.stride + a.x + x;
                for xx in 0..SIDE {
                    let code = frame.data[row_start + xx];
                    let phase = ((y + yy) & 1) * 2 + ((x + xx) & 1);
                    let signal = f32::from(code) - frame.levels.black; // Signed; no input clamp.
                    moments[r][yy * SIDE + xx].add(f64::from(signal));
                    per_frame[phase].add(f64::from(signal));
                    let c = &mut counts[r][phase];
                    c.zero += usize::from(code == 0);
                    c.below_black += usize::from(f32::from(code) < frame.levels.black);
                    c.at_black += usize::from(f32::from(code) == frame.levels.black);
                    c.at_or_above_white += usize::from(f32::from(code) >= frame.levels.white);
                    if let Some(bytes) = &mut original {
                        bytes.extend_from_slice(&code.to_le_bytes());
                    }
                }
            }
            for phase in 0..4 {
                let m = per_frame[phase].mean;
                mean_series[r][phase].add(m);
                writeln!(
                    frame_means,
                    "{number},{r},{},{:.12},{:.12}",
                    NAMES[phase],
                    m,
                    m + f64::from(frame.levels.black)
                )?;
            }
            if let Some(bytes) = original {
                let name = format!("first-roi-{r}.u16le");
                fs::write(out.join(&name), &bytes)?;
                roi_descriptors.push(format!("{{\"index\":{r},\"active_xywh\":[{x},{y},{SIDE},{SIDE}],\"file\":{},\"bytes\":{},\"dtype\":\"uint16-little-endian\",\"row_order\":\"C\"}}", quote(&name), bytes.len()));
            }
        }
        if index == 0 {
            first_descriptor = format!(
                "{{\"schema\":\"rea-raw-dark-first-source-v1\",\"frame\":{descriptor},\"roi_gauge\":\"active-relative native sensor pixels; RGGB at active (0,0)\",\"margin_note\":\"buffer margins include decoder storage padding and are not asserted optical sensor margins\",\"rois\":[{}]}}\n",
                roi_descriptors.join(",")
            );
            fs::write(out.join("first-source.json"), &first_descriptor)?;
        }
        frames.push(descriptor);
        frame_means.flush()?;
        eprintln!(
            "REA_DARK_AUDIT_FRAME {}/{} {}",
            index + 1,
            COUNT,
            path.display()
        );
        // Frame drops here: no decoded or aligned frame volume is retained.
    }
    let model = first_model.context("no completed sources")?;
    let black = f64::from(model.plane(CfaPlane::R).levels.black);
    let mut rows = Vec::new();
    for (r, &(x, y)) in ROIS.iter().enumerate() {
        let mut spatial_means = [Moment::default(); 4];
        let mut variance_sum = [0.0f64; 4];
        for yy in 0..SIDE {
            for xx in 0..SIDE {
                let phase = ((y + yy) & 1) * 2 + ((x + xx) & 1);
                let m = moments[r][yy * SIDE + xx];
                ensure!(m.n == COUNT, "incomplete pixel population");
                let v = m.variance();
                ensure!(v.is_finite() && v >= 0.0, "invalid temporal variance");
                variance_sum[phase] += v;
                spatial_means[phase].add(m.mean);
            }
        }
        for phase in 0..4 {
            let sm = spatial_means[phase];
            ensure!(sm.n == SIDE * SIDE / 4, "phase population changed");
            let variance = variance_sum[phase] / sm.n as f64;
            let sigma = variance.sqrt();
            let predicted = f64::from(model.sigma(PHASES[phase], 0.0));
            let pn = model.plane(PHASES[phase]);
            let common = mean_series[r][phase].variance();
            let fraction = if variance > 0.0 {
                format!("{}", common / variance)
            } else {
                "null".to_string()
            };
            let c = counts[r][phase];
            rows.push(format!(
                "{{\"roi_index\":{r},\"active_xywh\":[{x},{y},{SIDE},{SIDE}],\"phase\":{},\"pixels\":{},\"frames\":{COUNT},\"temporal_df_per_pixel\":{},\"temporal_variance_mean_dn2\":{variance},\"temporal_sigma_rms_dn\":{sigma},\"profile_sigma_zero_dn\":{predicted},\"sigma_ratio_to_profile_zero\":{},\"variance_ratio_to_profile_zero\":{},\"mean_signed_dark_dn\":{},\"mean_raw_code_dn\":{},\"spatial_sd_of_temporal_means_dn\":{},\"frame_roi_mean_variance_dn2\":{common},\"common_mode_variance_fraction\":{fraction},\"gain_dn_per_e\":{},\"read_noise_e\":{},\"zero_code_samples\":{},\"below_black_samples\":{},\"equal_black_samples\":{},\"at_or_above_white_samples\":{}}}",
                quote(NAMES[phase]), sm.n, COUNT - 1, sigma / predicted, variance / predicted.powi(2),
                sm.mean, sm.mean + black, sm.variance().sqrt(), pn.gain_dn_per_e, pn.read_noise_e,
                c.zero, c.below_black, c.at_black, c.at_or_above_white));
        }
    }
    let summary = format!(
        "{{\n\"schema\":\"rea-raw-dark-audit-v1\",\"status\":\"COMPLETE\",\"sources\":{COUNT},\"workers\":1,\"commission\":\"PASS\",\"input_content_sha256\":\"not computed by this example; join root capture receipt; size/mtime checked around decode\",\"model_source\":\"public noise_model_for(camera, iso, decoder levels), Profile required\",\"noise_quantity\":\"sqrt(mean over pixels of unbiased per-pixel temporal variance), DN, same RGGB phase\",\"stable_fpn\":\"per-pixel temporal centering excludes stable additive offsets; spatial SD of means is separate and includes finite-repeat noise\",\"drift\":\"no per-frame level subtraction; common temporal changes remain; frame-mean variance is diagnostic, not removed\",\"calibration_reuse\":\"118MSDCF belongs to the M4 dark calibration corpus used for the read floor; this is a like-unit consistency check, not independent calibration validation\",\"limitations\":[\"sigma(0) does not model extra dark current if mean signal is nonzero\",\"no shot-noise, developed-RGB, gather-covariance, FPN-removal or quality claim\",\"no fitted/replaced noise model or outlier rejection\"],\"frames\":[{}],\"rows\":[{}]\n}}\n",
        frames.join(","),
        rows.join(",")
    );
    ensure!(
        frames.len() == COUNT && rows.len() == ROIS.len() * 4 && !first_descriptor.is_empty(),
        "incomplete audit"
    );
    fs::write(out.join("summary.json"), summary)?;
    fs::write(out.join("run-status.txt"), "COMPLETE\n")?;
    println!("REA_DARK_AUDIT_COMPLETE {}", out.display());
    Ok(())
}
