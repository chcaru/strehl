use anyhow::{Context, Result, bail, ensure};
use base64::Engine;
use image::RgbImage;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    io::{BufRead, BufReader, Write},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, Stdio},
    sync::{Arc, mpsc},
    thread,
    time::{Duration, Instant},
};

pub struct Preview {
    pub frame: u64,
    pub rgb: RgbImage,
    pub jpeg: Option<Arc<Vec<u8>>>,
}

pub trait Camera: Send {
    fn identity(&self) -> Value;
    fn status(&mut self) -> Result<Value>;
    fn configure(&mut self) -> Result<()>;
    fn set_pixel_shift(&mut self, shots: usize) -> Result<()> {
        ensure!(
            shots == 1,
            "Pixel shift is not supported by this camera backend"
        );
        Ok(())
    }
    /// Fresh whole-stack storage admission, before any lens or shutter action.
    fn prepare_stack(&mut self, _frames: usize, _max_raw_bytes: u64) -> Result<()> {
        Ok(())
    }
    fn focus(&mut self, target: u16, settle_ms: u32) -> Result<Value>;
    fn capture(&mut self, timeout_s: u32) -> Result<Value>;
    fn preview(&mut self) -> Result<Preview>;
    fn magnify(&mut self, ratio_tenths: u32, x: u16, y: u16) -> Result<()>;
    fn disconnect(&mut self) -> Result<Value>;
    fn sync_journal(&mut self, _directory: &Path) -> Result<()> {
        Ok(())
    }
    fn prepare_capture(&mut self) -> Result<bool> {
        Ok(true)
    }
    fn finish_transfers(&mut self) -> Result<()> {
        Ok(())
    }
}

pub fn property(status: &Value, name: &str) -> Option<u64> {
    status.get("properties")?.get(name)?.get("value")?.as_u64()
}

pub struct Native {
    child: Option<Child>,
    input: Option<ChildStdin>,
    replies: mpsc::Receiver<Result<Value>>,
    hello: Value,
    poisoned: bool,
    executable: PathBuf,
    release_reply: Option<Value>,
    host_mode: bool,
}

impl Native {
    pub fn group_stream(&self) -> bool {
        self.hello["group_stream_protocol"] == 1
    }
    pub fn raw_format(&self) -> &'static str {
        if self.group_stream() {
            "uncompressed"
        } else {
            "lossless-l"
        }
    }
    pub fn shots_per_plane(&self) -> usize {
        if self.hello["group_stream_protocol"] == 1 && self.hello["pixel_shift_shots"] == 4 {
            4
        } else {
            1
        }
    }
    pub fn capture_files(
        &mut self,
        timeout_s: u32,
        ready: &mut dyn FnMut(Value) -> Result<()>,
    ) -> Result<Value> {
        if !self.group_stream() {
            let response = self.capture(timeout_s)?;
            ready(response.clone())?;
            return Ok(response);
        }
        ensure!(
            !self.poisoned,
            "Bridge state is uncertain; reconnect after inspection"
        );
        let input = self.input.as_mut().context("Bridge input is closed")?;
        if let Err(error) = writeln!(input, "capture-host\t{timeout_s}").and_then(|_| input.flush())
        {
            self.poisoned = true;
            return Err(error).context("Write group command; it was not retried");
        }
        let shots = self.shots_per_plane();
        let mut count = 0;
        let mut failure = None;
        loop {
            let reply = self.receive(u64::from(timeout_s) + 20)?;
            if reply["event"] == "raw-ready" {
                count += 1;
                // Always drain the camera's current group. If queue persistence
                // fails, completed RAM files remain and no next release is sent.
                if count > shots {
                    failure = Some(anyhow::anyhow!("Unexpected extra group member"));
                } else if let Err(error) = ready(reply) {
                    failure = Some(error);
                }
            } else {
                if let Some(error) = failure {
                    return Err(error);
                }
                ensure!(
                    count == shots
                        && reply["completion"] == "ptp-group-complete"
                        && reply["pixel_shift_shots"] == shots
                        && reply["group_idle"] == true
                        && reply["buffer_empty"] == true
                        && reply["files"].as_array().is_some_and(|a| a.len() == shots),
                    "Capture group did not complete; no shutter retry"
                );
                return Ok(reply);
            }
        }
    }
    pub fn connect(executable: &Path) -> Result<Self> {
        Self::connect_mode(executable, None)
    }
    pub fn connect_host(executable: &Path, ram_directory: &Path) -> Result<Self> {
        Self::connect_mode(executable, Some(ram_directory))
    }
    fn connect_mode(executable: &Path, ram_directory: Option<&Path>) -> Result<Self> {
        ensure!(
            executable.is_file(),
            "Sony bridge is missing: {}. Extract the complete portable ZIP.",
            executable.display()
        );
        let executable = executable
            .canonicalize()
            .context("Resolve Sony bridge path")?;
        let mut cmd = Command::new(&executable);
        if let Some(directory) = ram_directory {
            cmd.arg("serve-host").arg(directory);
        } else {
            cmd.arg("serve");
        }
        cmd.current_dir(executable.parent().context("Bridge has no parent folder")?)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
        }
        let mut child = cmd.spawn().context("Launch Sony SDK bridge")?;
        let input = child.stdin.take();
        let output = child.stdout.take().context("Bridge stdout unavailable")?;
        let (tx, replies) = mpsc::sync_channel(2);
        thread::spawn(move || {
            let mut reader = BufReader::new(output);
            loop {
                let result = read_reply(&mut reader);
                let failed = result.is_err();
                if tx.send(result).is_err() || failed {
                    break;
                }
            }
        });
        // The Worker owns this process before the first SDK reply is read.
        // A failed handshake must retain that owner until release completes.
        Ok(Self {
            child: Some(child),
            input,
            replies,
            hello: Value::Null,
            poisoned: false,
            executable: executable.to_owned(),
            release_reply: None,
            host_mode: ram_directory.is_some(),
        })
    }
    fn receive(&mut self, timeout_s: u64) -> Result<Value> {
        let reply = match self.replies.recv_timeout(Duration::from_secs(timeout_s)) {
            Ok(Ok(value)) => value,
            Ok(Err(error)) => {
                self.poisoned = true;
                return Err(error);
            }
            Err(error) => {
                self.poisoned = true;
                bail!(
                    "Camera bridge did not reply ({error}). No command was retried; inspect the camera before reconnecting."
                );
            }
        };
        ensure!(
            reply["ok"].as_bool() == Some(true),
            "{}",
            reply["error"]
                .as_str()
                .unwrap_or("Camera returned an invalid response")
        );
        Ok(reply)
    }
    fn call(&mut self, command: &str, timeout_s: u64) -> Result<Value> {
        ensure!(
            !self.poisoned,
            "Bridge state is uncertain; reconnect after inspecting the camera"
        );
        let input = self.input.as_mut().context("Bridge input is closed")?;
        if let Err(error) = writeln!(input, "{command}").and_then(|_| input.flush()) {
            self.poisoned = true;
            return Err(error).context("Write camera command; it was not retried");
        }
        self.receive(timeout_s)
    }
    fn set(&mut self, name: &str, value: u64) -> Result<()> {
        self.call(&format!("set\t{name}\t{value}"), 15)
            .with_context(|| format!("Configure {name}"))?;
        Ok(())
    }
}

pub fn read_reply(reader: &mut impl BufRead) -> Result<Value> {
    const MAX: u64 = 24 * 1024 * 1024;
    let mut line = Vec::new();
    std::io::Read::take(reader, MAX + 1).read_until(b'\n', &mut line)?;
    ensure!(
        !line.is_empty(),
        "Sony bridge exited; inspect USB connection and the Sony USB driver"
    );
    ensure!(
        line.len() as u64 <= MAX && line.last() == Some(&b'\n'),
        "Oversized or incomplete camera reply"
    );
    serde_json::from_slice(&line).context("Invalid camera reply JSON")
}

impl Camera for Native {
    fn identity(&self) -> Value {
        json!({"backend":if self.group_stream() {"sony-ptp3"}else{"sony-sdk-2.02"}, "hello":self.hello, "bridge_name":self.executable.file_name(),
            "bridge_sha256":std::fs::read(&self.executable).ok().map(|bytes|Sha256::digest(bytes).iter().map(|b|format!("{b:02x}")).collect::<String>()),
            "pixel_shift_supported_by_this_backend":self.group_stream(),
            "pixel_shift_shots":self.shots_per_plane()})
    }
    fn status(&mut self) -> Result<Value> {
        let status = self.call("status", 20)?;
        if self.group_stream() {
            let shots = status["pixel_shift_shots"]
                .as_u64()
                .context("Missing pixel-shift count")?;
            ensure!(
                matches!(shots, 1 | 4),
                "Unsupported pixel-shift count; select one or four"
            );
            self.hello["pixel_shift_shots"] = json!(shots);
        }
        Ok(status)
    }
    fn configure(&mut self) -> Result<()> {
        if self.hello.is_null() {
            self.hello = self.receive(35)?;
        }
        ensure!(
            self.hello["capture_protocol"] == 2 && self.hello["live_view_protocol"] == 1,
            "This bridge predates the live-view capture app. Extract the entire new ZIP."
        );
        ensure!(
            !self.host_mode || self.hello["host_pipeline_protocol"] == 1,
            "This Sony bridge does not support the bounded RAW queue. Install the matching Pi bridge and controller together."
        );
        if self.group_stream() {
            ensure!(
                self.host_mode,
                "A7CR PTP capture requires the RAM-to-PC receiver"
            );
            self.call("configure", 20)?;
            return Ok(());
        }
        // A connected callback can precede the SDK's property cache becoming
        // readable. Wait using read-only queries before any setting writes.
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            let status = self.status()?;
            let required = [
                "StillImageStoreDestination",
                "DriveMode",
                "FocusMode",
                "FileType",
            ];
            let missing: Vec<_> = required
                .into_iter()
                .filter(|name| property(&status, name).is_none())
                .collect();
            if missing.is_empty() {
                break;
            }
            ensure!(
                Instant::now() < deadline,
                "Camera settings did not become readable: {}",
                missing.join(", ")
            );
            thread::sleep(Duration::from_millis(100));
        }
        // Host mode is explicit and requires the Linux bridge's checked tmpfs path.
        self.set(
            "StillImageStoreDestination",
            if self.host_mode { 1 } else { 2 },
        )?;
        self.set("DriveMode", 1)?;
        self.set("FocusMode", 1)?;
        self.set("FileType", 2)?;
        if self.host_mode {
            self.set("RAW_FileCompressionType", 5)?;
        }
        self.call("liveview\t1", 15)?;
        // Optional quality setting is capability-gated; absence does not block MF.
        let status = self.status()?;
        if status["properties"]["LiveView_Image_Quality"]["writable"] == true
            && status["properties"]["LiveView_Image_Quality"]["allowed"]
                .as_array()
                .is_some_and(|a| a.contains(&json!(1)))
        {
            self.set("LiveView_Image_Quality", 1)?;
        }
        ensure!(
            property(&status, "FocusPositionCurrentValue").is_some(),
            "Camera does not expose absolute focus; check the electronic lens and MF mode"
        );
        Ok(())
    }
    fn set_pixel_shift(&mut self, shots: usize) -> Result<()> {
        ensure!(
            self.group_stream() && matches!(shots, 1 | 4),
            "Pixel-shift selection unavailable"
        );
        let status = self.call(&format!("pixel-shift\t{shots}"), 20)?;
        ensure!(
            status["pixel_shift_shots"] == shots,
            "Capture mode did not read back"
        );
        self.hello["pixel_shift_shots"] = json!(shots);
        Ok(())
    }
    fn focus(&mut self, target: u16, settle_ms: u32) -> Result<Value> {
        let value = self.call(
            &format!("focus\t{target}\t{settle_ms}"),
            15 + u64::from(settle_ms).div_ceil(1000),
        )?;
        ensure!(
            value["readback"].as_u64() == Some(u64::from(target)),
            "Focus did not read back the requested position; capture stopped"
        );
        Ok(value)
    }
    fn capture(&mut self, timeout_s: u32) -> Result<Value> {
        self.call(
            &if self.host_mode {
                format!("capture-host\t{timeout_s}")
            } else {
                format!("capture\t1\t{timeout_s}")
            },
            u64::from(timeout_s) + 20,
        )
    }
    fn preview(&mut self) -> Result<Preview> {
        let response = self.call("preview", 15)?;
        decode_preview(&response)
    }
    fn magnify(&mut self, ratio_tenths: u32, x: u16, y: u16) -> Result<()> {
        self.call(&format!("magnify\t{ratio_tenths}\t{x}\t{y}"), 15)?;
        Ok(())
    }
    fn disconnect(&mut self) -> Result<Value> {
        if self.input.is_some() {
            // Closing stdin also releases a poisoned protocol after its current
            // operation finishes. Never kill a bridge during an uncertain shot.
            let result = self.call("quit", 50);
            self.input.take();
            self.release_reply = Some(match result {
                Ok(reply) => reply,
                Err(error) => json!({"restored":false,"reason":format!("{error:#}")}),
            });
        }
        if let Some(child) = self.child.as_mut() {
            let end = Instant::now() + Duration::from_secs(5);
            while child.try_wait()?.is_none() {
                ensure!(
                    Instant::now() < end,
                    "Camera bridge is still finishing its previous operation. Wait for the camera/card to become idle, then retry reconnect. No replacement connection was opened."
                );
                thread::sleep(Duration::from_millis(50));
            }
            self.child.take();
        }
        Ok(self.release_reply.clone().unwrap_or_else(
            || json!({"restored":false,"reason":"Connection was already released"}),
        ))
    }
}

fn decode_preview(response: &Value) -> Result<Preview> {
    let jpeg = base64::engine::general_purpose::STANDARD
        .decode(response["jpeg"].as_str().context("Missing preview")?)?;
    let mut decoder =
        image::ImageReader::with_format(std::io::Cursor::new(&jpeg), image::ImageFormat::Jpeg);
    let mut limits = image::Limits::default();
    limits.max_image_width = Some(8192);
    limits.max_image_height = Some(8192);
    limits.max_alloc = Some(128 * 1024 * 1024);
    decoder.limits(limits);
    let rgb = decoder.decode().context("Decode live-view JPEG")?.to_rgb8();
    Ok(Preview {
        frame: response["frame"]
            .as_u64()
            .context("Missing preview frame number")?,
        rgb,
        jpeg: Some(Arc::new(jpeg)),
    })
}
impl Drop for Native {
    fn drop(&mut self) {
        self.input.take(); // EOF: finish an in-flight operation, then release safely.
        if let Some(mut child) = self.child.take() {
            // No forced termination during an uncertain exposure. This owned
            // reaper does not issue camera commands or hold the UI thread.
            thread::spawn(move || {
                let _ = child.wait();
            });
        }
    }
}

/// Explicit simulator; never selected as a fallback for a failed camera.
pub struct Demo {
    pub shots: usize,
    pub position: u16,
    pub frame: u64,
    pub remaining: u64,
    pub delay_ms: u64,
    pub fail_capture: bool,
    pub fail_preview: bool,
    pub fail_focus_after: Option<u32>,
    pub focus_calls: u32,
}
impl Default for Demo {
    fn default() -> Self {
        Self {
            shots: 1,
            position: 60627,
            frame: 0,
            remaining: 9000,
            delay_ms: 120,
            fail_capture: false,
            fail_preview: false,
            fail_focus_after: None,
            focus_calls: 0,
        }
    }
}
impl Camera for Demo {
    fn identity(&self) -> Value {
        json!({"backend":"simulator", "camera":"DEMO · no camera connected"})
    }
    fn status(&mut self) -> Result<Value> {
        let mut props = serde_json::Map::new();
        for (name, value) in [
            ("FocusPositionCurrentValue", u64::from(self.position)),
            ("MediaSLOT1_RemainingNumber", self.remaining),
            ("BatteryRemain", 87),
            ("USBPowerSupply", 2),
            ("StillImageStoreDestination", 2),
            ("FNumber", 560),
            ("IsoSensitivity", 100),
            ("FocusMode", 1),
            ("ExposureProgramMode", 1),
            ("ShutterSpeed", (1 << 16) | 5),
        ] {
            props.insert(
                name.into(),
                json!({"value":value,"readable":true,"writable":false}),
            );
        }
        Ok(json!({"properties":props,"pixel_shift_shots":self.shots,"pixel_shift_options":[1,4]}))
    }
    fn configure(&mut self) -> Result<()> {
        Ok(())
    }
    fn set_pixel_shift(&mut self, shots: usize) -> Result<()> {
        ensure!(matches!(shots, 1 | 4), "Unsupported simulated mode");
        self.shots = shots;
        Ok(())
    }
    fn focus(&mut self, target: u16, _settle_ms: u32) -> Result<Value> {
        ensure!(
            !self.fail_focus_after.is_some_and(|n| self.focus_calls >= n),
            "Simulated failure to get focus information"
        );
        self.focus_calls += 1;
        thread::sleep(Duration::from_millis(self.delay_ms.min(60)));
        let before = self.position;
        self.position = target;
        Ok(json!({"requested":target,"before":before,"readback":target,"completion":"simulated"}))
    }
    fn capture(&mut self, _timeout_s: u32) -> Result<Value> {
        thread::sleep(Duration::from_millis(self.delay_ms));
        ensure!(
            !self.fail_capture,
            "Simulated acknowledgement loss after release"
        );
        ensure!(self.remaining >= self.shots as u64, "Simulated card full");
        self.remaining -= self.shots as u64;
        Ok(
            json!({"captured_events":1,"pixel_shift_shots":self.shots,"destination":"memory-card","completion":"camera-events-and-card-idle","simulated":true,"card_state":"not-writing","bracket_idle":true,"files":[],"file_verification":"not-performed"}),
        )
    }
    fn preview(&mut self) -> Result<Preview> {
        ensure!(!self.fail_preview, "Simulated invalid live-view JPEG");
        self.frame += 1;
        Ok(Preview {
            frame: self.frame,
            rgb: demo_image(self.position, 960, 640),
            jpeg: None,
        })
    }
    fn magnify(&mut self, _: u32, _: u16, _: u16) -> Result<()> {
        Ok(())
    }
    fn disconnect(&mut self) -> Result<Value> {
        Ok(json!({"restored":true,"simulated":true}))
    }
}

pub fn demo_image(focus: u16, width: u32, height: u32) -> RgbImage {
    RgbImage::from_fn(width, height, |x, y| {
        let u = x as f32 / width as f32;
        let v = y as f32 / height as f32;
        let dx = (u - 0.5) * 2.0;
        let dy = (v - 0.5) * 2.0;
        if (dx * 1.18).powi(2) + (dy * 1.34).powi(2) > 1.0 {
            return image::Rgb([18, 23, 30]);
        }
        let depth = 60580.0 + u * 100.0 + v * 35.0;
        let amplitude = ((-((f32::from(focus) - depth) / 23.0).powi(2)) * 0.5).exp();
        let pattern =
            (u * 500.0).sin() * (v * 470.0).cos() * 0.5 + (u * 177.0 + v * 245.0).sin() * 0.5;
        let light = 0.62 + 0.27 * amplitude * pattern + 0.08 * (u * 20.0).cos();
        image::Rgb([
            (light * 168.0) as u8,
            (light * 180.0) as u8,
            (light * 130.0) as u8,
        ])
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(windows)]
    #[test]
    fn disconnect_waits_for_owned_bridge_exit_and_can_be_retried() {
        use std::os::windows::process::CommandExt;
        let child = Command::new("powershell.exe")
            .args([
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Start-Sleep -Seconds 6",
            ])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .creation_flags(0x0800_0000)
            .spawn()
            .unwrap();
        let (_, replies) = mpsc::sync_channel(1);
        let mut camera = Native {
            host_mode: false,
            child: Some(child),
            input: None,
            replies,
            hello: Value::Null,
            poisoned: true,
            executable: PathBuf::new(),
            release_reply: Some(json!({"restored":false,"reason":"fixture: uncertain operation"})),
        };
        assert!(
            camera
                .disconnect()
                .unwrap_err()
                .to_string()
                .contains("still finishing")
        );
        assert!(camera.child.as_mut().unwrap().try_wait().unwrap().is_none());
        assert_eq!(camera.disconnect().unwrap()["restored"], false);
        assert!(camera.child.is_none());
    }
    #[test]
    fn real_jpeg_round_trip_uses_camera_decode_path() {
        let image = image::RgbImage::from_pixel(64, 48, image::Rgb([40, 100, 180]));
        let mut jpeg = Vec::new();
        image::codecs::jpeg::JpegEncoder::new(&mut jpeg)
            .encode_image(&image::DynamicImage::ImageRgb8(image))
            .unwrap();
        let response =
            json!({"frame":42,"jpeg":base64::engine::general_purpose::STANDARD.encode(&jpeg)});
        let preview = decode_preview(&response).unwrap();
        assert_eq!((preview.frame, preview.rgb.dimensions()), (42, (64, 48)));
        for (actual, expected) in preview
            .rgb
            .get_pixel(32, 24)
            .0
            .into_iter()
            .zip([40i16, 100, 180])
        {
            assert!((i16::from(actual) - expected).abs() <= 3);
        }
        let bad = json!({"frame":43,"jpeg":base64::engine::general_purpose::STANDARD.encode(b"not JPEG")});
        assert!(decode_preview(&bad).is_err());
        assert!(decode_preview(&json!({"frame":44,"jpeg":"%%%"})).is_err());
    }
    #[test]
    fn protocol_rejects_truncated_or_non_json_replies() {
        assert!(read_reply(&mut std::io::Cursor::new(b"{\"ok\":true}")).is_err());
        assert!(read_reply(&mut std::io::Cursor::new(b"not-json\n")).is_err());
        assert_eq!(
            read_reply(&mut std::io::Cursor::new(b"{\"ok\":false}\n")).unwrap()["ok"],
            false
        );
    }
}
