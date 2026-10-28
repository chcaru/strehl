// Test-only literal CUDA consumer transport. No RAW decode, gather or noise model
// lives in Python. Root owns the inherited Windows job and every execution.
use super::dual_tree_cfa::{Arm, Coefficients, Comparison, Complex, ComplexBand, Finished, Plan};
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Write},
    process::{Child, ChildStdin, ChildStdout, Command, Stdio},
    sync::atomic::{AtomicUsize, Ordering as AtomicOrdering},
};
use strehl_core::align::Similarity;

const DEVICE_BYTES: u64 = 24u64 << 30;
const HEADER_BYTES: usize = 262144;
const CPU_TRANSFORM_SHA: &str = "d49b6fe8ae336e2e25c3df506e38756201ad86ac7365543037b1390bc9598c65";
const CPU_CONSUMER_SHA: &str = "eb6a51dbee5e65af9aec06c8e9e8a12dc4d29784572caa835c522df4029391e6";
static WORKER_SERIAL: AtomicUsize = AtomicUsize::new(0);

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct GpuConfig {
    schema: u32,
    python: PathBuf,
    python_sha256: String,
    server: PathBuf,
    server_sha256: String,
    out_dir: PathBuf,
    device_limit_bytes: u64,
}
fn bridge_digest(h: Sha256) -> String {
    h.finalize().iter().map(|x| format!("{x:02x}")).collect()
}
fn bridge_hash(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut bytes)?;
        if n == 0 {
            break;
        }
        h.update(&bytes[..n]);
    }
    Ok(bridge_digest(h))
}
fn bridge_record(path: &Path) -> Result<Value> {
    Ok(json!({"path":path,"bytes":std::fs::metadata(path)?.len(),"sha256":bridge_hash(path)?}))
}
fn bridge_save(path: &Path, value: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, value)?;
    writeln!(f)?;
    Ok(())
}
fn bridge_floats_hash(values: &[f32]) -> String {
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in values.chunks(bytes.len() / 4) {
        for (b, x) in bytes.chunks_exact_mut(4).zip(chunk) {
            b.copy_from_slice(&x.to_bits().to_le_bytes());
        }
        h.update(&bytes[..4 * chunk.len()]);
    }
    bridge_digest(h)
}
fn bridge_guard(plan: &Plan, cfg: MergeConfig, wb: [f32; 4]) -> Result<()> {
    let expected = Plan::new(plan.input_width, plan.input_height)?;
    ensure!(
        plan.padded_width == expected.padded_width
            && plan.padded_height == expected.padded_height
            && plan.levels == 7,
        "literal CPU plan required"
    );
    ensure!(
        cfg.bands == 7
            && cfg.gate == 2.
            && cfg.exponent == 2.
            && cfg.sharpen_per_octave == 1.4
            && cfg.select == SelectMode::SoftPower
            && cfg.admission == AdmissionMode::HardFloor
            && cfg.base == BaseBand::Mean
            && cfg.fallback == strehl_core::pyramid::Fallback::Mean
            && cfg.hull == strehl_core::pyramid::Hull::InputRange
            && cfg.mean_coarse == 0
            && cfg.significance_scale == 0.,
        "literal CPU merge defaults required"
    );
    ensure!(
        wb[..3].iter().all(|x| x.is_finite() && *x > 0.),
        "finite first three WB coefficients"
    );
    Ok(())
}
fn bridge_planes(planes: &[Vec<f32>], plan: &Plan) -> Result<()> {
    ensure!(
        planes.len() == 4
            && planes
                .iter()
                .all(|p| p.len() == plan.input_width * plan.input_height
                    && p.iter().all(|x| x.is_finite())),
        "complete finite four-phase field"
    );
    Ok(())
}
#[cfg(windows)]
fn inherited_job(child: &Child) -> Result<Value> {
    use std::os::windows::io::AsRawHandle;
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetCurrentProcess() -> *mut std::ffi::c_void;
        fn IsProcessInJob(
            process: *mut std::ffi::c_void,
            job: *mut std::ffi::c_void,
            result: *mut i32,
        ) -> i32;
    }
    let mut parent = 0;
    let mut member = 0;
    unsafe {
        ensure!(
            IsProcessInJob(GetCurrentProcess(), std::ptr::null_mut(), &mut parent) != 0,
            "parent job query failed"
        );
        ensure!(
            IsProcessInJob(child.as_raw_handle(), std::ptr::null_mut(), &mut member) != 0,
            "child job query failed"
        );
    }
    ensure!(
        parent != 0 && member != 0,
        "GPU worker requires root-owned inherited Windows job"
    );
    Ok(
        json!({"parent_in_job":true,"child_in_job":true,"creation_flags":"CREATE_NO_WINDOW; no breakaway/detach","child_pid":child.id()}),
    )
}
#[cfg(not(windows))]
fn inherited_job(_child: &Child) -> Result<Value> {
    bail!("this bounded observation requires the root Windows job")
}

pub(crate) struct DebugArray {
    pub name: String,
    pub values: Vec<f32>,
}
struct Wire {
    child: Child,
    input: BufWriter<ChildStdin>,
    output: BufReader<ChildStdout>,
    plan: Plan,
    debug: bool,
    folder: PathBuf,
    config_path: PathBuf,
    config_sha: String,
    config: GpuConfig,
    job: Value,
    startup: Value,
    source_ids: Vec<usize>,
    sent_bytes: u64,
    received_bytes: u64,
    exchange_seconds: f64,
    closed: bool,
}
impl Drop for Wire {
    fn drop(&mut self) {
        if !self.closed {
            let _ = self.child.kill();
            let _ = self.child.wait();
        }
    }
}
impl Wire {
    fn new(
        plan: Plan,
        cfg: MergeConfig,
        wb: [f32; 4],
        debug: bool,
        floor_foil: bool,
    ) -> Result<Self> {
        bridge_guard(&plan, cfg, wb)?;
        ensure!(!floor_foil || debug, "floor foil is debug-only");
        ensure!(
            !debug || (plan.input_width <= 128 && plan.input_height <= 128),
            "bounded debug extent"
        );
        let config_path = PathBuf::from(
            std::env::var_os("STREHL_DUAL_TREE_CFA_GPU_CONFIG")
                .context("explicit GPU config required")?,
        );
        let config_sha = bridge_hash(&config_path)?;
        let config: GpuConfig = serde_json::from_slice(&std::fs::read(&config_path)?)?;
        let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .canonicalize()?;
        ensure!(
            config.schema == 1
                && config.device_limit_bytes == DEVICE_BYTES
                && config.python.is_absolute()
                && config.server.is_absolute()
                && config.out_dir.is_absolute()
                && config.out_dir.is_dir()
                && config
                    .out_dir
                    .canonicalize()?
                    .starts_with(root.join("outputs").canonicalize()?),
            "strict GPU config scope"
        );
        ensure!(
            bridge_hash(&config.python)? == config.python_sha256
                && bridge_hash(&config.server)? == config.server_sha256,
            "frozen worker/interpreter changed"
        );
        let folder = config.out_dir.join(format!(
            "gpu-worker-{:04}",
            WORKER_SERIAL.fetch_add(1, AtomicOrdering::SeqCst)
        ));
        std::fs::create_dir(&folder)?;
        let stderr = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(folder.join("server.log"))?;
        let mut command = Command::new(&config.python);
        command
            .args(["-I", "-B", "-X", "faulthandler"])
            .arg(&config.server)
            .arg("--receipt")
            .arg(folder.join("server-receipt.json"))
            .arg("--device-limit-bytes")
            .arg(DEVICE_BYTES.to_string())
            .env("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
            .env("OMP_NUM_THREADS", "1")
            .env("MKL_NUM_THREADS", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(stderr);
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW, never BREAKAWAY.
        }
        let mut child = command.spawn()?;
        let job = match inherited_job(&child) {
            Ok(v) => v,
            Err(e) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(e);
            }
        };
        let input =
            BufWriter::with_capacity(1 << 20, child.stdin.take().context("GPU child stdin")?);
        let output =
            BufReader::with_capacity(1 << 20, child.stdout.take().context("GPU child stdout")?);
        let mut wire = Self {
            child,
            input,
            output,
            plan,
            debug,
            folder,
            config_path,
            config_sha,
            config,
            job,
            startup: Value::Null,
            source_ids: Vec::new(),
            sent_bytes: 0,
            received_bytes: 0,
            exchange_seconds: 0.,
            closed: false,
        };
        let start = Instant::now();
        wire.header(&json!({"op":"start","schema":1,"width":wire.plan.input_width,"height":wire.plan.input_height,
            "wb":&wb[..3],"exponents":(0..7).map(|k|cfg.exponent_at(k,7)).collect::<Vec<_>>(),
            "device_limit_bytes":DEVICE_BYTES,"debug":debug,"floor_foil":floor_foil,
            "cpu_transform_sha256":CPU_TRANSFORM_SHA,"cpu_consumer_sha256":CPU_CONSUMER_SHA}))?;
        wire.startup = wire.response("start")?;
        ensure!(
            wire.startup["schema"] == 1
                && wire.startup["floats"] == 0
                && wire.startup["server_sha256"] == wire.config.server_sha256
                && wire.startup["runtime"]["backend"] == "torch-cuda-f32"
                && wire.startup["runtime"]["cpu_transform_sha256"] == CPU_TRANSFORM_SHA
                && wire.startup["runtime"]["cpu_consumer_sha256"] == CPU_CONSUMER_SHA
                && wire.startup["band_shapes"] == json!(wire.shapes()),
            "literal CUDA startup identity/shape"
        );
        wire.exchange_seconds += start.elapsed().as_secs_f64();
        bridge_save(
            &wire.folder.join("bridge-started.json"),
            &json!({
            "python":bridge_record(&wire.config.python)?,"server":bridge_record(&wire.config.server)?,
            "config":bridge_record(&wire.config_path)?,"job":wire.job,"startup":wire.startup,
            "width":wire.plan.input_width,"height":wire.plan.input_height,"debug":debug,"floor_foil":floor_foil,
            "device_limit_bytes":DEVICE_BYTES,"admission":false}),
        )?;
        Ok(wire)
    }
    fn header(&mut self, value: &Value) -> Result<()> {
        let bytes = serde_json::to_vec(value)?;
        ensure!(
            !bytes.is_empty() && bytes.len() <= HEADER_BYTES,
            "bounded GPU request header"
        );
        self.input.write_all(&(bytes.len() as u32).to_le_bytes())?;
        self.input.write_all(&bytes)?;
        self.input.flush()?;
        self.sent_bytes += 4 + bytes.len() as u64;
        Ok(())
    }
    fn response(&mut self, op: &str) -> Result<Value> {
        let mut size = [0; 4];
        self.output.read_exact(&mut size)?;
        let n = u32::from_le_bytes(size) as usize;
        ensure!(n > 0 && n <= HEADER_BYTES, "bounded GPU response header");
        let mut bytes = vec![0; n];
        self.output.read_exact(&mut bytes)?;
        self.received_bytes += 4 + n as u64;
        let v: Value = serde_json::from_slice(&bytes)?;
        ensure!(
            v["ok"] == true && v["op"] == op,
            "GPU worker refused/misordered {op}: {v}"
        );
        Ok(v)
    }
    fn send(&mut self, values: &[f32]) -> Result<()> {
        ensure!(values.iter().all(|v| v.is_finite()), "finite f32 payload");
        let mut bytes = vec![0u8; 65536];
        for chunk in values.chunks(bytes.len() / 4) {
            for (b, x) in bytes.chunks_exact_mut(4).zip(chunk) {
                b.copy_from_slice(&x.to_bits().to_le_bytes());
            }
            self.input.write_all(&bytes[..chunk.len() * 4])?;
        }
        self.sent_bytes += 4 * values.len() as u64;
        Ok(())
    }
    fn send_four(&mut self, p: &[Vec<f32>]) -> Result<()> {
        bridge_planes(p, &self.plan)?;
        for v in p {
            self.send(v)?;
        }
        self.input.flush()?;
        Ok(())
    }
    fn read(&mut self, n: usize) -> Result<Vec<f32>> {
        // Maximum response is the four complete output arms, delivered a plane
        // at a time. Debug coefficient vectors are bounded independently.
        ensure!(
            n <= 16 * self.plan.padded_width * self.plan.padded_height,
            "bounded worker float response"
        );
        let mut values = Vec::with_capacity(n);
        let mut bytes = vec![0u8; 65536];
        while values.len() < n {
            let count = (n - values.len()).min(bytes.len() / 4);
            self.output.read_exact(&mut bytes[..4 * count])?;
            for b in bytes[..4 * count].chunks_exact(4) {
                let v = f32::from_le_bytes(b.try_into().unwrap());
                ensure!(v.is_finite(), "nonfinite GPU output");
                values.push(v);
            }
        }
        self.received_bytes += 4 * n as u64;
        Ok(values)
    }
    fn finish_process(&mut self, response: &Value) -> Result<Value> {
        ensure!(self.child.wait()?.success(), "GPU worker exit failure");
        let mut extra = [0; 1];
        ensure!(
            self.output.read(&mut extra)? == 0,
            "unexpected trailing GPU protocol bytes"
        );
        ensure!(
            bridge_hash(&self.config_path)? == self.config_sha
                && bridge_hash(&self.config.python)? == self.config.python_sha256
                && bridge_hash(&self.config.server)? == self.config.server_sha256,
            "worker dependencies changed"
        );
        let receipt_path = self.folder.join("server-receipt.json");
        let server: Value = serde_json::from_slice(&std::fs::read(&receipt_path)?)?;
        ensure!(
            server["status"] == "COMPLETE_DUAL_TREE_CUDA_WORKER"
                && server["complete"] == true
                && server["backend"] == "torch-cuda-f32"
                && server["source_count"] == self.source_ids.len()
                && server["source_ids"] == json!(self.source_ids)
                && server["device_limit_bytes"] == DEVICE_BYTES
                && server["server_sha256"] == self.config.server_sha256,
            "terminal GPU worker census/status"
        );
        for key in ["peak_allocated_bytes", "peak_reserved_bytes"] {
            ensure!(
                server[key].as_u64().is_some_and(|n| n <= DEVICE_BYTES),
                "GPU device cap report {key}"
            );
        }
        let receipt = json!({"status":"COMPLETE_DUAL_TREE_CUDA_BRIDGE","complete":true,"source_ids":self.source_ids,
            "source_count":self.source_ids.len(),"server_receipt":bridge_record(&receipt_path)?,"server":server,
            "response":response,"job":self.job,"child_exit_success":true,"child_exit_code":0,
            "parent_in_job":true,"child_in_job":true,"bindings_unchanged":true,"dependencies_unchanged":true,
            "probe_draws_total":16*self.source_ids.len(),
            "python":bridge_record(&self.config.python)?,"server_source":bridge_record(&self.config.server)?,
            "config":bridge_record(&self.config_path)?,"sent_bytes":self.sent_bytes,"received_bytes":self.received_bytes,
            "exchange_seconds":self.exchange_seconds,"device_limit_bytes":DEVICE_BYTES,"admission":false,"quality_claim":false});
        bridge_save(&self.folder.join("bridge-receipt.json"), &receipt)?;
        self.closed = true;
        Ok(receipt)
    }
    fn shapes(&self) -> Vec<[usize; 2]> {
        self.plan
            .band_shapes()
            .into_iter()
            .map(|(w, h)| [w, h])
            .collect()
    }
    fn coefficient_floats(&self) -> usize {
        self.plan
            .band_shapes()
            .iter()
            .map(|(w, h)| 12 * w * h)
            .sum()
    }
    fn low_floats(&self) -> usize {
        4 * (self.plan.padded_width >> 7) * (self.plan.padded_height >> 7)
    }
}

pub(crate) struct Accumulator {
    wire: Wire,
    last_debug: Option<Vec<DebugArray>>,
}
impl Accumulator {
    pub(crate) fn new(plan: Plan, cfg: MergeConfig, wb: [f32; 4]) -> Result<Self> {
        Ok(Self {
            wire: Wire::new(plan, cfg, wb, false, false)?,
            last_debug: None,
        })
    }
    pub(crate) fn new_debug(
        plan: Plan,
        cfg: MergeConfig,
        wb: [f32; 4],
        floor_foil: bool,
    ) -> Result<Self> {
        Ok(Self {
            wire: Wire::new(plan, cfg, wb, true, floor_foil)?,
            last_debug: None,
        })
    }
    pub(crate) fn take_debug_arrays(&mut self) -> Result<Vec<DebugArray>> {
        self.last_debug
            .take()
            .context("no completed debug source stage")
    }
    pub(crate) fn add_source(
        &mut self,
        frame: &Frame,
        source_id: usize,
        known4: &[Vec<f32>],
        noise: &NoiseModel,
        gather: impl Fn(&Frame) -> Result<Vec<Vec<f32>>>,
    ) -> Result<Value> {
        bridge_planes(known4, &self.wire.plan)?;
        ensure!(
            source_id < 299
                && self.wire.source_ids.len() < 299
                && !self.wire.source_ids.contains(&source_id),
            "unique original source ordinal"
        );
        validate_pyramid_frame(frame, frame.geometry(), source_id)?;
        let original_hash = shared_source_field::hash16(&frame.data);
        let known_hashes = known4
            .iter()
            .map(|v| bridge_floats_hash(v))
            .collect::<Vec<_>>();
        let started = Instant::now();
        let floats = 4 * self.wire.plan.input_width * self.wire.plan.input_height;
        self.last_debug = None;
        let io = Instant::now();
        self.wire
            .header(&json!({"op":"source","index":source_id,"floats":floats}))?;
        self.wire.send_four(known4)?;
        let signal = self.wire.response("source")?;
        ensure!(signal["index"] == source_id, "signal ordinal");
        let mut io_seconds = io.elapsed().as_secs_f64();
        let noise_start = Instant::now();
        let variance = boundary_cfa_wavelet::original_variances(frame, noise)?;
        let variance_hash = bridge_floats_hash(&variance);
        let seeds: [usize; 16] =
            std::array::from_fn(|draw| boundary_cfa_wavelet::probe_seed(source_id, draw));
        let variance_seconds = noise_start.elapsed().as_secs_f64();
        let mut draw_rows = Vec::new();
        let mut probe_prepare_seconds = 0.;
        for (draw, &seed) in seeds.iter().enumerate() {
            let prepare = Instant::now();
            let noisy = boundary_cfa_wavelet::noisy_source(frame, &variance, seed)?;
            let planes = gather(&noisy)?;
            drop(noisy);
            bridge_planes(&planes, &self.wire.plan)?;
            let seconds = prepare.elapsed().as_secs_f64();
            probe_prepare_seconds += seconds;
            let io = Instant::now();
            self.wire
                .header(&json!({"op":"probe","index":source_id,"draw":draw,"floats":floats}))?;
            self.wire.send_four(&planes)?;
            drop(planes);
            let reply = self.wire.response("probe")?;
            ensure!(
                reply["index"] == source_id && reply["draw"] == draw,
                "probe ordinal/order"
            );
            let transfer = io.elapsed().as_secs_f64();
            io_seconds += transfer;
            draw_rows.push(json!({"draw":draw,"seed":seed,"prepare_and_actual_gather_seconds":seconds,"wire_and_synchronized_cuda_seconds":transfer,"worker":reply}));
        }
        drop(variance);
        let io = Instant::now();
        self.wire
            .header(&json!({"op":"end-source","index":source_id}))?;
        let response = self.wire.response("end-source")?;
        ensure!(response["index"] == source_id, "end-source ordinal");
        if self.wire.debug {
            let scalar: usize = self
                .wire
                .plan
                .band_shapes()
                .iter()
                .map(|(w, h)| 6 * w * h)
                .sum();
            let expected = [
                ("energy", scalar),
                ("floor", scalar),
                ("raw_weights", scalar),
                (
                    "signal_coefficients_phase0",
                    self.wire.coefficient_floats() + self.wire.low_floats(),
                ),
            ];
            let arrays = response["arrays"]
                .as_array()
                .context("debug stage arrays")?;
            ensure!(arrays.len() == expected.len(), "debug stage count");
            let total: usize = expected.iter().map(|(_, n)| *n).sum();
            ensure!(response["floats"] == total, "debug stage payload count");
            for (a, (name, n)) in arrays.iter().zip(expected) {
                ensure!(
                    a["name"] == name && a["floats"] == n,
                    "debug stage order/shape"
                );
            }
            let mut values = Vec::new();
            for (name, n) in expected {
                values.push(DebugArray {
                    name: name.into(),
                    values: self.wire.read(n)?,
                });
            }
            self.last_debug = Some(values);
        } else {
            ensure!(response["floats"] == 0, "no full-source debug payload");
        }
        io_seconds += io.elapsed().as_secs_f64();
        self.wire.exchange_seconds += io_seconds;
        ensure!(
            shared_source_field::hash16(&frame.data) == original_hash
                && known4
                    .iter()
                    .map(|v| bridge_floats_hash(v))
                    .collect::<Vec<_>>()
                    == known_hashes,
            "source or gathered input mutated"
        );
        self.wire.source_ids.push(source_id);
        let wire_response = response;
        let mut response = wire_response["source_evidence"].clone();
        ensure!(
            response.is_object()
                && response["source_index"] == source_id
                && response["probe_pairs"] == 8
                && response["probe_draws"] == 16,
            "worker actual-source census"
        );
        response["gpu_wire_response"] = wire_response;
        response["original_unchanged"] = json!(true);
        response["source_sha256"] = json!(original_hash);
        response["known4_sha256"] = json!(known_hashes);
        response["original_variance_sha256"] = json!(variance_hash);
        response["probe_seeds"] = json!(seeds);
        response["probe_receipts"] = json!(draw_rows);
        response["original_variance_seconds"] = json!(variance_seconds);
        response["probe_prepare_and_gather_seconds"] = json!(probe_prepare_seconds);
        response["wire_and_synchronized_cuda_seconds"] = json!(io_seconds);
        response["source_seconds"] = json!(started.elapsed().as_secs_f64());
        response["worker_directory"] = json!(self.wire.folder);
        Ok(response)
    }
    pub(crate) fn finish(mut self) -> Result<Finished> {
        ensure!(!self.wire.source_ids.is_empty(), "no sources consumed");
        let start = Instant::now();
        self.wire
            .header(&json!({"op":"finish","source_ids":self.wire.source_ids}))?;
        let response = self.wire.response("finish")?;
        let n = self.wire.plan.input_width * self.wire.plan.input_height;
        ensure!(
            response["floats"] == 16 * n
                && response["source_count"] == self.wire.source_ids.len()
                && response["source_ids"] == json!(self.wire.source_ids),
            "complete final GPU census/payload"
        );
        let mut arms = Vec::new();
        for _ in 0..4 {
            let mut planes = Vec::new();
            for _ in 0..4 {
                planes.push(self.wire.read(n)?);
            }
            arms.push(planes);
        }
        self.wire.exchange_seconds += start.elapsed().as_secs_f64();
        let bridge = self.wire.finish_process(&response)?;
        let mut evidence = response["evidence"].clone();
        ensure!(
            evidence.is_object()
                && evidence["source_count"] == self.wire.source_ids.len()
                && evidence["source_ids"] == json!(self.wire.source_ids),
            "worker final evidence census"
        );
        evidence["gpu_wire_response"] = response;
        evidence["gpu_bridge"] = bridge;
        evidence["admission"] = json!(false);
        evidence["quality_claim"] = json!(false);
        let mut arms = arms.into_iter();
        Ok(Finished {
            planes4: arms.next().unwrap(),
            pre_hull_planes4: arms.next().unwrap(),
            uniform_planes4: arms.next().unwrap(),
            mean_planes4: arms.next().unwrap(),
            evidence,
        })
    }
}

pub(crate) struct DebugWorker {
    wire: Wire,
}
impl DebugWorker {
    pub(crate) fn new(
        plan: Plan,
        cfg: MergeConfig,
        wb: [f32; 4],
        floor_foil: bool,
    ) -> Result<Self> {
        Ok(Self {
            wire: Wire::new(plan, cfg, wb, true, floor_foil)?,
        })
    }
    pub(crate) fn transform(
        &mut self,
        input: &[f32],
        bank_foil: bool,
    ) -> Result<(Coefficients, Vec<f32>, Value)> {
        let n = self.wire.plan.input_width * self.wire.plan.input_height;
        ensure!(input.len() == n, "debug input extent");
        let start = Instant::now();
        self.wire
            .header(&json!({"op":"transform","floats":n,"bank_foil":bank_foil}))?;
        self.wire.send(input)?;
        self.wire.input.flush()?;
        let response = self.wire.response("transform")?;
        let ac = self.wire.coefficient_floats();
        let ll = self.wire.low_floats();
        ensure!(
            response["coefficient_floats"] == ac
                && response["low_floats"] == ll
                && response["inverse_floats"] == n
                && response["floats"] == ac + ll + n
                && response["band_shapes"] == json!(self.wire.shapes()),
            "debug transform shape"
        );
        let coefficients = self.read_coefficients()?;
        let inverse = self.wire.read(n)?;
        self.wire.exchange_seconds += start.elapsed().as_secs_f64();
        Ok((coefficients, inverse, response))
    }
    fn read_coefficients(&mut self) -> Result<Coefficients> {
        let mut bands = Vec::new();
        for (level, (w, h)) in self.wire.plan.band_shapes().into_iter().enumerate() {
            for direction in 0..6 {
                let values = self
                    .wire
                    .read(2 * w * h)?
                    .chunks_exact(2)
                    .map(|p| Complex { re: p[0], im: p[1] })
                    .collect();
                bands.push(ComplexBand {
                    level,
                    direction,
                    width: w,
                    height: h,
                    values,
                });
            }
        }
        let n = self.wire.low_floats() / 4;
        let mut low: [Vec<f32>; 4] = std::array::from_fn(|_| Vec::new());
        for v in &mut low {
            *v = self.wire.read(n)?;
        }
        Ok(Coefficients { bands, low })
    }
    pub(crate) fn inverse(&mut self, coefficients: &Coefficients) -> Result<(Vec<f32>, Value)> {
        ensure!(coefficients.bands.len() == 42, "debug coefficient count");
        let start = Instant::now();
        self.wire.header(
            &json!({"op":"inverse","floats":self.wire.coefficient_floats()+self.wire.low_floats()}),
        )?;
        for (index, band) in coefficients.bands.iter().enumerate() {
            let k = index / 6;
            let w = self.wire.plan.padded_width >> (k + 1);
            let h = self.wire.plan.padded_height >> (k + 1);
            ensure!(
                band.level == k
                    && band.direction == index % 6
                    && band.width == w
                    && band.height == h
                    && band.values.len() == w * h,
                "debug coefficient shape"
            );
            let values = band
                .values
                .iter()
                .flat_map(|z| [z.re, z.im])
                .collect::<Vec<_>>();
            self.wire.send(&values)?;
        }
        for v in &coefficients.low {
            ensure!(v.len() == self.wire.low_floats() / 4, "debug LL extent");
            self.wire.send(v)?;
        }
        self.wire.input.flush()?;
        let response = self.wire.response("inverse")?;
        let n = self.wire.plan.input_width * self.wire.plan.input_height;
        ensure!(response["floats"] == n, "debug inverse size");
        let output = self.wire.read(n)?;
        self.wire.exchange_seconds += start.elapsed().as_secs_f64();
        Ok((output, response))
    }
    pub(crate) fn close(mut self) -> Result<Value> {
        self.wire.header(&json!({"op":"close"}))?;
        let response = self.wire.response("close")?;
        ensure!(response["floats"] == 0, "debug close payload");
        self.wire.finish_process(&response)
    }
}

pub(crate) fn generated_gather(
    frame: &Frame,
    warp: Similarity,
    crop: align_cmd::CropRect,
) -> Result<Vec<Vec<f32>>> {
    ensure!(
        !frame.path.exists() && frame.active.width <= 512 && frame.active.height <= 512,
        "bounded generated source only"
    );
    ensure!(
        align_cmd::fullres_gather_enabled()
            && gatefloor::enabled()
            && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Off
            && !align_cmd::native_gpu_integration::gpu_gather_enabled()?,
        "held CPU remosaic route"
    );
    let identity = strehl_raw::identity(&frame.path);
    ensure!(
        strehl_core::optics::profile_for_capture_env(
            identity.model.as_deref(),
            identity.lens_type3
        )?
        .is_none()
            && phase_packed_rgb::full_stack::full_source_supported(
                warp,
                frame.geometry(),
                crop,
                None
            ),
        "covered CA-off generated pull"
    );
    let mut current = frame.clone();
    let mut planes = vec![vec![0.; crop.width * crop.height]; 4];
    align_cmd::warp_frame_in_place(
        &mut current,
        warp,
        frame.geometry(),
        Resampler::CatmullRom,
        &mut WarpScratch::new(frame.geometry()),
    )?;
    extract_planes(
        &current.data,
        current.stride,
        current.active.x,
        current.active.y,
        current.levels.black,
        PyramidDomain::cropped(frame.geometry(), crop)?,
        &BAND_PLANE_OFFSETS,
        &mut planes,
    )?;
    Ok(planes)
}
fn gpu_arm(
    planes4: Vec<Vec<f32>>,
    crop: align_cmd::CropRect,
    levels: Levels,
    wb: [f32; 4],
) -> Result<Arm> {
    let rgb = super::dual_tree_cfa::camera_rgb(&planes4, crop.width, crop.height, levels, wb)?;
    Ok(Arm { planes4, rgb })
}
fn save_debug_stage(folder: &Path, index: usize, arrays: Vec<DebugArray>) -> Result<Vec<Value>> {
    let mut rows = Vec::new();
    for array in arrays {
        ensure!(
            [
                "energy",
                "floor",
                "raw_weights",
                "signal_coefficients_phase0"
            ]
            .contains(&array.name.as_str()),
            "declared debug array name"
        );
        let path = folder.join(format!("source-{index:03}-{}.f32le", array.name));
        let mut file = BufWriter::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&path)?,
        );
        let mut bytes = vec![0u8; 65536];
        for chunk in array.values.chunks(bytes.len() / 4) {
            for (b, x) in bytes.chunks_exact_mut(4).zip(chunk) {
                b.copy_from_slice(&x.to_bits().to_le_bytes());
            }
            file.write_all(&bytes[..4 * chunk.len()])?;
        }
        file.flush()?;
        drop(file);
        let mut record = bridge_record(&path)?;
        record["name"] = json!(array.name);
        record["floats"] = json!(array.values.len());
        record["layout"] = json!(
            "42 level-major bands; complex signal uses interleaved re/im then four LL trees; other fields scalar"
        );
        record["format"] = json!("f32le");
        rows.push(record);
    }
    Ok(rows)
}
pub(crate) fn compare_generated(
    frames: &[Frame],
    transforms: &[Similarity],
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    cfg: MergeConfig,
) -> Result<Comparison> {
    ensure!(
        !frames.is_empty() && frames.len() <= 8 && frames.len() == transforms.len(),
        "bounded generated source count"
    );
    let first = &frames[0];
    let full = first.geometry();
    let wb = first.wb_coeffs;
    ensure!(
        first.active.width <= 512 && first.active.height <= 512,
        "generated native extent"
    );
    for (index, f) in frames.iter().enumerate() {
        ensure!(
            !f.path.exists()
                && f.geometry() == full
                && f.active == first.active
                && f.stride == first.stride
                && f.levels == first.levels
                && f.camera == first.camera
                && f.iso == first.iso
                && f.wb_coeffs[..3] == wb[..3],
            "generated metadata"
        );
        validate_pyramid_frame(f, full, index)?;
    }
    let entries = frames
        .iter()
        .map(|f| (f.path.to_string_lossy(), f.allocated_bytes() as u64))
        .collect::<Vec<_>>();
    let map = WarpMap::new(
        strehl_core::warpmap::Provenance {
            stack: StackIdentity::from_entries("dual-tree-gpu-generated", &entries),
            strategy: "supplied generated geometry".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "literal six-direction CUDA consumer".into(),
        },
        full,
        Resampler::CatmullRom,
        transforms.iter().copied().map(FrameWarp::Placed).collect(),
    );
    struct Source<'a>(&'a [Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self) -> usize {
            self.0.len()
        }
        fn decode(&self, index: usize) -> Result<Frame> {
            Ok(self.0[index].clone())
        }
    }
    let source = Source(frames);
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    let mut canonical = BandWorker::new(PyramidDomain::cropped(full, crop)?, cfg);
    let mut accumulator =
        Accumulator::new_debug(Plan::new(crop.width, crop.height)?, cfg, wb, false)?;
    let mut gathered0 = None;
    let mut rows = Vec::new();
    for (index, frame) in frames.iter().enumerate() {
        ensure!(
            canonical.fold(&source, index, frame.levels, noise, Some(&map), None)?,
            "canonical generated source refused"
        );
        let check = generated_gather(frame, transforms[index], crop)?;
        ensure!(
            check.len() == 4
                && check
                    .iter()
                    .zip(&canonical.planes)
                    .all(|(a, b)| a.len() == b.len()
                        && a.iter().zip(b).all(|(x, y)| x.to_bits() == y.to_bits())),
            "GPU candidate callback differs from canonical CPU gather"
        );
        drop(check);
        if index == 0 {
            gathered0 = Some(canonical.planes.clone());
        }
        let mut row = accumulator.add_source(frame, index, &canonical.planes, noise, |f| {
            generated_gather(f, transforms[index], crop)
        })?;
        let folder = accumulator.wire.folder.clone();
        row["debug_arrays"] = json!(save_debug_stage(
            &folder,
            index,
            accumulator.take_debug_arrays()?
        )?);
        rows.push(row);
    }
    let finished = accumulator.finish()?;
    let evidence = json!({"frames":rows,"candidate":finished.evidence,
        "canonical_level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "canonical_exponents":(0..sizes.len()-1).map(|k|cfg.exponent_at(k,sizes.len()-1)).collect::<Vec<_>>(),
        "canonical_exponent_bits":(0..sizes.len()-1).map(|k|cfg.exponent_at(k,sizes.len()-1).to_bits()).collect::<Vec<_>>(),
        "candidate_exponent_bits":(0..7).map(|k|cfg.exponent_at(k,7).to_bits()).collect::<Vec<_>>(),
        "generated_basis_only_comparison":false,"candidate_effective_levels":7,"signal_gather_check_exact":true,
        "causal_baseline":"actual unchanged BandWorker and CPU gather; literal CUDA transform consumer",
        "quality_claim":false,"admission":false});
    Ok(Comparison {
        canonical: gpu_arm(
            canonical.merge.finish(&mut Workspace::new(&sizes)),
            crop,
            first.levels,
            wb,
        )?,
        candidate: gpu_arm(finished.planes4, crop, first.levels, wb)?,
        uniform: gpu_arm(finished.uniform_planes4, crop, first.levels, wb)?,
        gathered_source0: gpu_arm(
            gathered0.context("first gathered source")?,
            crop,
            first.levels,
            wb,
        )?,
        pre_hull_planes4: finished.pre_hull_planes4,
        mean_planes4: finished.mean_planes4,
        native_width: 2 * crop.width,
        native_height: 2 * crop.height,
        evidence,
    })
}
