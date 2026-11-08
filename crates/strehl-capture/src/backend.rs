use anyhow::{Context, Result, bail, ensure};
use base64::Engine;
use image::RgbImage;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    io::{BufRead, BufReader, Write},
    path::{Path, PathBuf},
    process::{Child, ChildStdin, Command, Stdio},
    sync::mpsc,
    thread,
    time::Duration,
};

pub struct Preview {
    pub frame: u64,
    pub rgb: RgbImage,
}

pub trait Camera: Send {
    fn identity(&self) -> Value;
    fn status(&mut self) -> Result<Value>;
    fn configure(&mut self) -> Result<()>;
    fn focus(&mut self, target: u16, settle_ms: u32) -> Result<Value>;
    fn capture(&mut self, timeout_s: u32) -> Result<Value>;
    fn preview(&mut self) -> Result<Preview>;
    fn magnify(&mut self, ratio_tenths: u32, x: u16, y: u16) -> Result<()>;
    fn disconnect(&mut self) -> Result<Value>;
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
}

impl Native {
    pub fn connect(executable: &Path) -> Result<Self> {
        ensure!(
            executable.is_file(),
            "Sony bridge is missing: {}. Extract the complete portable ZIP.",
            executable.display()
        );
        let executable = executable
            .canonicalize()
            .context("Resolve Sony bridge path")?;
        let mut cmd = Command::new(&executable);
        cmd.arg("serve")
            .current_dir(executable.parent().context("Bridge has no parent folder")?)
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
        let mut this = Self {
            child: Some(child),
            input,
            replies,
            hello: Value::Null,
            poisoned: false,
            executable: executable.to_owned(),
        };
        this.hello = this.receive(35)?;
        ensure!(
            this.hello["capture_protocol"] == 2 && this.hello["live_view_protocol"] == 1,
            "This bridge predates the live-view capture app. Extract the entire new ZIP."
        );
        Ok(this)
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
        self.call(&format!("set\t{name}\t{value}"), 15)?;
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
        json!({"backend":"sony-sdk-2.02", "hello":self.hello, "bridge_name":self.executable.file_name(),
            "bridge_sha256":std::fs::read(&self.executable).ok().map(|bytes|Sha256::digest(bytes).iter().map(|b|format!("{b:02x}")).collect::<String>()),
            "pixel_shift_supported_by_this_backend":false})
    }
    fn status(&mut self) -> Result<Value> {
        self.call("status", 20)
    }
    fn configure(&mut self) -> Result<()> {
        // Set destination first, before any preview or release; never select HostPC.
        self.set("StillImageStoreDestination", 2)?;
        self.set("DriveMode", 1)?;
        self.set("FocusMode", 1)?;
        self.set("FileType", 2)?;
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
            &format!("capture\t1\t{timeout_s}"),
            u64::from(timeout_s) + 20,
        )
    }
    fn preview(&mut self) -> Result<Preview> {
        let response = self.call("preview", 15)?;
        let jpeg = base64::engine::general_purpose::STANDARD
            .decode(response["jpeg"].as_str().context("Missing preview")?)?;
        let mut decoder =
            image::ImageReader::with_format(std::io::Cursor::new(jpeg), image::ImageFormat::Jpeg);
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
        })
    }
    fn magnify(&mut self, ratio_tenths: u32, x: u16, y: u16) -> Result<()> {
        self.call(&format!("magnify\t{ratio_tenths}\t{x}\t{y}"), 15)?;
        Ok(())
    }
    fn disconnect(&mut self) -> Result<Value> {
        self.call("quit", 50)
    }
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
    pub position: u16,
    pub frame: u64,
    pub remaining: u64,
    pub delay_ms: u64,
    pub fail_capture: bool,
}
impl Default for Demo {
    fn default() -> Self {
        Self {
            position: 60627,
            frame: 0,
            remaining: 9000,
            delay_ms: 120,
            fail_capture: false,
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
        Ok(json!({"properties":props}))
    }
    fn configure(&mut self) -> Result<()> {
        Ok(())
    }
    fn focus(&mut self, target: u16, _settle_ms: u32) -> Result<Value> {
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
        ensure!(self.remaining > 0, "Simulated card full");
        self.remaining -= 1;
        Ok(
            json!({"captured_events":1,"destination":"memory-card","completion":"camera-events-and-card-idle","simulated":true,"card_state":"not-writing","bracket_idle":true,"files":[],"file_verification":"not-performed"}),
        )
    }
    fn preview(&mut self) -> Result<Preview> {
        self.frame += 1;
        Ok(Preview {
            frame: self.frame,
            rgb: demo_image(self.position, 960, 640),
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
