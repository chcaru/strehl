//! Isolated runtime compatibility measurement. No application integration,
//! photograph decoding, teacher assets, or inferred rendering semantics.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Read, path::Path, time::Instant};
use tract::prelude::*;

const INPUT_SHAPE: [usize; 4] = [1, 5, 384, 512];
const INPUT_BYTES: usize = 5 * 384 * 512 * 4;
const MAX_MODEL_BYTES: u64 = 256 * 1024 * 1024;
const OUTPUTS: [(&str, &[usize]); 10] = [
    ("pgtm", &[1, 16, 96, 128]),
    ("rgbt_0", &[1, 3, 32, 32, 32]),
    ("rgbt_1", &[1, 3, 32, 32, 32]),
    ("rgbt_2", &[1, 3, 32, 32, 32]),
    ("exposure", &[1, 1]),
    ("pgtm_hdr", &[1, 16, 96, 128]),
    ("rgbt_0_hdr", &[1, 3, 32, 32, 32]),
    ("rgbt_1_hdr", &[1, 3, 32, 32, 32]),
    ("rgbt_2_hdr", &[1, 3, 32, 32, 32]),
    ("exposure_hdr", &[1, 1]),
];

fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn bounded_read(path: &Path, limit: u64) -> Result<Vec<u8>> {
    let file = fs::File::open(path).with_context(|| format!("Opening {}", path.display()))?;
    ensure!(
        file.metadata()?.len() <= limit,
        "Input exceeds its byte limit"
    );
    let mut bytes = Vec::new();
    file.take(limit + 1).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() as u64 <= limit,
        "Input grew beyond its byte limit"
    );
    Ok(bytes)
}

fn fact_shape(fact: &Fact) -> Result<Vec<usize>> {
    ensure!(
        fact.datum_type()? == DatumType::F32,
        "Expected FP32 model fact"
    );
    (0..fact.rank()?)
        .map(|axis| Ok(usize::try_from(fact.dim(axis)?.to_int64()?)?))
        .collect()
}

fn validate_input(bytes: &[u8]) -> Result<()> {
    ensure!(
        bytes.len() == INPUT_BYTES,
        "Input must be exact FP32 [1,5,384,512]"
    );
    ensure!(
        bytes.chunks_exact(4).all(|chunk| {
            let value = f32::from_le_bytes(chunk.try_into().unwrap());
            value.is_finite() && (0.0..=1.0).contains(&value)
        }),
        "Input contains nonfinite or out-of-range values"
    );
    Ok(())
}

fn load_model(bytes: &[u8], is_onnx: bool) -> Result<Model> {
    if is_onnx {
        #[cfg(feature = "onnx")]
        return tract::onnx()?.load_buffer(bytes)?.into_model();
        #[cfg(not(feature = "onnx"))]
        anyhow::bail!("This binary excludes the ONNX parser; supply a translated NNEF .tar asset");
    }
    let mut framework = tract::nnef()?;
    // These register runtime operators in NNEF. They do not pull in the ONNX
    // file parser (tract-onnx); tract-onnx-opl remains necessary for Resize etc.
    framework.enable_onnx()?;
    framework.enable_tract_extra()?;
    framework.load_buffer(bytes)
}

fn validate_outputs(outputs: &[Tensor]) -> Result<Vec<String>> {
    ensure!(
        outputs.len() == OUTPUTS.len(),
        "Expected ten output tensors"
    );
    let mut hashes = Vec::with_capacity(OUTPUTS.len());
    for (output, (name, shape)) in outputs.iter().zip(OUTPUTS) {
        ensure!(
            output.datum_type()? == DatumType::F32,
            "{name}: expected FP32"
        );
        ensure!(output.shape()? == shape, "{name}: incorrect output shape");
        let values = output.as_slice::<f32>()?;
        ensure!(
            values.iter().all(|v| v.is_finite()),
            "{name}: nonfinite output"
        );
        if name.starts_with("pgtm") {
            ensure!(values.iter().all(|v| *v > 0.0), "{name}: nonpositive gain");
        } else if name.starts_with("rgbt") {
            ensure!(
                values.iter().all(|v| (-2e-6..=1.0 + 2e-6).contains(v)),
                "{name}: color table outside bounded output contract"
            );
        }
        hashes.push(digest(output.as_bytes()?.2));
    }
    Ok(hashes)
}

#[cfg(windows)]
fn memory() -> Value {
    use windows_sys::Win32::System::{
        ProcessStatus::{GetProcessMemoryInfo, PROCESS_MEMORY_COUNTERS},
        Threading::GetCurrentProcess,
    };
    // The API fills a correctly sized, integer-only structure synchronously.
    let mut counters: PROCESS_MEMORY_COUNTERS = unsafe { std::mem::zeroed() };
    counters.cb = std::mem::size_of::<PROCESS_MEMORY_COUNTERS>() as u32;
    let size = counters.cb;
    let okay = unsafe { GetProcessMemoryInfo(GetCurrentProcess(), &mut counters, size) };
    if okay == 0 {
        return Value::Null;
    }
    json!({
        "working_set_bytes":counters.WorkingSetSize,
        "peak_working_set_bytes":counters.PeakWorkingSetSize,
        "pagefile_usage_bytes":counters.PagefileUsage,
        "peak_pagefile_usage_bytes":counters.PeakPagefileUsage,
        "source":"GetProcessMemoryInfo; peak is process lifetime, not phase-local"
    })
}

#[cfg(target_os = "linux")]
fn memory() -> Value {
    let Ok(status) = fs::read_to_string("/proc/self/status") else {
        return Value::Null;
    };
    let read = |key: &str| -> Option<u64> {
        status.lines().find_map(|line| {
            line.strip_prefix(key)?
                .split_whitespace()
                .next()?
                .parse::<u64>()
                .ok()
                .map(|v| v * 1024)
        })
    };
    json!({"working_set_bytes":read("VmRSS:"),"peak_working_set_bytes":read("VmHWM:"),
        "source":"/proc/self/status; peak is process lifetime, not phase-local"})
}

#[cfg(not(any(windows, target_os = "linux")))]
fn memory() -> Value {
    Value::Null
}

fn run() -> Result<()> {
    ensure!(
        cfg!(target_endian = "little"),
        "This fixture format requires little-endian host"
    );
    let total = Instant::now();
    let arguments = std::env::args_os().skip(1).collect::<Vec<_>>();
    ensure!(
        (3..=4).contains(&arguments.len()),
        "Usage: strehl-adaptive-native-probe MODEL.onnx|MODEL.tar INPUT.f32 NEW_OUTPUT_DIRECTORY [ROUNDS]"
    );
    let model_path = Path::new(&arguments[0]);
    let input_path = Path::new(&arguments[1]);
    let destination = Path::new(&arguments[2]);
    let rounds = arguments
        .get(3)
        .map(|v| v.to_string_lossy().parse::<usize>())
        .transpose()?
        .unwrap_or(16);
    ensure!((1..=10_000).contains(&rounds), "Rounds must be1..10000");
    ensure!(
        !destination.exists(),
        "Output directory already exists; use a fresh receipt directory"
    );
    let startup_memory = memory();
    let model_bytes = bounded_read(model_path, MAX_MODEL_BYTES)?;
    let model_hash = digest(&model_bytes);
    let input_bytes = bounded_read(input_path, INPUT_BYTES as u64)?;
    validate_input(&input_bytes)?;
    let input_hash = digest(&input_bytes);
    let input = Tensor::from_bytes(DatumType::F32, &INPUT_SHAPE, &input_bytes)?;
    drop(input_bytes);

    let load = Instant::now();
    let is_onnx = model_path
        .extension()
        .is_some_and(|v| v.eq_ignore_ascii_case("onnx"));
    let model = load_model(&model_bytes, is_onnx)?;
    let load_seconds = load.elapsed().as_secs_f64();
    drop(model_bytes);
    ensure!(
        model.input_count()? == 1,
        "Expected exactly one model input"
    );
    ensure!(
        fact_shape(&model.input_fact(0)?)? == INPUT_SHAPE,
        "Wrong model input shape"
    );
    ensure!(
        model.output_count()? == OUTPUTS.len(),
        "Wrong model output count"
    );
    let mut graph_names = Vec::new();
    for (slot, (_, shape)) in OUTPUTS.iter().enumerate() {
        ensure!(
            fact_shape(&model.output_fact(slot)?)? == *shape,
            "Wrong output shape at slot{slot}"
        );
        graph_names.push(model.output_name(slot)?);
    }
    let loaded_memory = memory();
    fs::create_dir(destination)?;
    if is_onnx {
        // Translation stays outside timing. The next process can benchmark this
        // standalone NNEF asset without loading the ONNX import graph again.
        let mut framework = tract::nnef()?;
        framework.enable_onnx()?;
        framework.enable_tract_extra()?;
        framework.write_model_to_tar(destination.join("model.nnef.tar"), &model)?;
    }
    let prepare = Instant::now();
    let runnable = model.into_runnable()?;
    let prepare_seconds = prepare.elapsed().as_secs_f64();
    let prepared_memory = memory();
    let first = Instant::now();
    let outputs = runnable.run([input.clone()])?;
    let first_seconds = first.elapsed().as_secs_f64();
    let reference_hashes = validate_outputs(&outputs)?;
    for _ in 0..2 {
        let warm = runnable.run([input.clone()])?;
        ensure!(
            validate_outputs(&warm)? == reference_hashes,
            "Warm-up changed output bytes"
        );
    }
    let mut timings = Vec::with_capacity(rounds);
    for _ in 0..rounds {
        let started = Instant::now();
        let repeat = runnable.run([input.clone()])?;
        timings.push(started.elapsed().as_secs_f64());
        ensure!(
            validate_outputs(&repeat)? == reference_hashes,
            "Repeated inference changed output bytes"
        );
    }
    let finished_memory = memory();
    let mut records = Vec::new();
    for (slot, (output, (name, shape))) in outputs.iter().zip(OUTPUTS).enumerate() {
        let data = output.as_bytes()?.2;
        let filename = format!("{name}.f32");
        fs::write(destination.join(&filename), data)?;
        let values = output.as_slice::<f32>()?;
        records.push(json!({
            "slot":slot,"name":name,"graph_node_name":graph_names[slot],"shape":shape,
            "dtype":"float32-le","file":filename,"bytes":data.len(),"sha256":reference_hashes[slot],
            "minimum":values.iter().copied().fold(f32::INFINITY,f32::min),
            "maximum":values.iter().copied().fold(f32::NEG_INFINITY,f32::max),
            "mean":values.iter().map(|v|f64::from(*v)).sum::<f64>()/values.len() as f64
        }));
    }
    let mut sorted = timings.clone();
    sorted.sort_by(f64::total_cmp);
    let percentile = |p: f64| sorted[((sorted.len() - 1) as f64 * p).ceil() as usize];
    let executable_bytes = std::env::current_exe()?.metadata()?.len();
    let report = json!({
        "version":1,"runtime":"tract CPU","runtime_version":tract::version(),
        "onnx_parser_compiled":cfg!(feature = "onnx"),
        "model_sha256":model_hash,"model_bytes":model_path.metadata()?.len(),
        "input_sha256":input_hash,"input_shape":INPUT_SHAPE,"input_bytes":INPUT_BYTES,
        "input_contract":"Caller-prepared RGB+two masks in0..1; this probe does not infer color semantics",
        "output_contract":"Fixed output slot order shared by v3/v4 export; graph_node_name is diagnostic only",
        "logical_processors":std::thread::available_parallelism().map_or(1,usize::from),
        "threading":"Tract default executor, no override; not assumed equal to ORT four-thread timings",
        "executable_bytes":executable_bytes,
        "timing_seconds":{"load_and_type":load_seconds,"prepare":prepare_seconds,
            "first_forward":first_seconds,"warm_forwards":timings,"minimum":sorted[0],
            "median":percentile(0.5),"p95":percentile(0.95),"entire_probe":total.elapsed().as_secs_f64()},
        "memory":{"startup":startup_memory,"loaded":loaded_memory,"prepared":prepared_memory,"after_forwards":finished_memory},
        "outputs":records,"repeated_output_sha256_equal":true,
        "limitations":["No photographic rendering or quality test", "No external runtime parity until these files are compared",
            "Forward times exclude validation/checksums/output writes", "Peak memory includes retained reference outputs and graph translation",
            "Process-internal startup measurement excludes OS process launch", "Host contention must be recorded by the invoking benchmark"]
    });
    fs::write(
        destination.join("report.json"),
        serde_json::to_vec_pretty(&report)?,
    )?;
    println!(
        "{}",
        json!({"receipt":destination.join("report.json"),"minimum_ms":sorted[0]*1000.0,
        "median_ms":percentile(0.5)*1000.0,"p95_ms":percentile(0.95)*1000.0,"executable_bytes":executable_bytes})
    );
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error:#}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn truncated_nonfinite_and_out_of_domain_inputs_fail() {
        let mut valid = vec![0u8; INPUT_BYTES];
        assert!(validate_input(&valid).is_ok());
        assert!(validate_input(&valid[..valid.len() - 4]).is_err());
        for value in [f32::NAN, f32::INFINITY, -0.1, 1.01] {
            valid[..4].copy_from_slice(&value.to_le_bytes());
            assert!(validate_input(&valid).is_err());
        }
    }

    #[cfg(not(feature = "onnx"))]
    #[test]
    fn parser_free_build_explicitly_rejects_onnx() {
        let error = load_model(&[], true).unwrap_err().to_string();
        assert!(error.contains("excludes the ONNX parser"), "{error}");
    }
}
