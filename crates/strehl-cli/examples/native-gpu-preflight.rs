//! Constructor-only commissioning; no descriptor, image or RAW work is dispatched.
#[cfg(feature = "native-gpu-gather")]
fn main() {
    use serde_json::json;
    use strehl_native_gpu_gather::{GpuGather, Schedule};
    let result = std::panic::catch_unwind(|| -> Result<serde_json::Value, String> {
        let gpu = GpuGather::new_with_schedule(Schedule::Device256)?;
        if gpu.compilation.original_sha256 != "41658a89bd9b17c73b0f452b48bde689679e4ecc50774872ebfff0171cdb6560"
            || gpu.compilation.submitted_sha256 != "a7dce2107ce7713ac4d9cd961dd44e303bd69b37c2d2ca7029f20aa1f131de9d" {
            return Err("protected f32 gather shader changed".into());
        }
        let coordinates = gpu.coordinate_compilation.as_ref().ok_or("coordinate report absent")?;
        Ok(json!({"status":"COORDINATE_PIPELINE_READY","adapter":gpu.adapter,
            "backend":gpu.backend,"device_type":gpu.device_type,"schedule":format!("{:?}",gpu.schedule()),
            "hardware":coordinates.hardware,"gather_compilation":gpu.compilation,
            "coordinate_compilation":coordinates,
            "scope":"constructor and pipeline creation only; no descriptors/images/RAW dispatched"}))
    });
    let (report, success) = match result {
        Ok(Ok(report)) => (report, true),
        Ok(Err(error)) => (json!({"status":"COORDINATE_PIPELINE_FAILED","error":error}), false),
        Err(payload) => {
            let error = payload.downcast_ref::<String>().cloned()
                .or_else(||payload.downcast_ref::<&str>().map(|s|(*s).to_owned()))
                .unwrap_or_else(||"non-string panic".into());
            (json!({"status":"COORDINATE_PIPELINE_FAILED","panic":error}), false)
        }
    };
    println!("{report}");
    if !success { std::process::exit(1); }
}

#[cfg(not(feature = "native-gpu-gather"))]
fn main() {
    eprintln!("native-gpu-preflight requires the native-gpu-gather feature");
    std::process::exit(2);
}

#[cfg(feature = "native-gpu-gather")]
#[test]
fn coordinate_pipeline_preflight() {
    main();
}
