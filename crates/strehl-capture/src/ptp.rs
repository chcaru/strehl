//! Original, bounded Sony Camera Remote Command PTP 3 client.
//! Wire definitions: owner's 2.02 reference pp. 43–49, 110–120, 460–463,
//! 567–568, 645–646 and 691. This is a separate exclusive USB owner, not an
//! SDK property-code extension. The first qualified model is ILCE-7CR.
#![cfg_attr(not(target_os = "linux"), allow(dead_code, unused_imports))]
use anyhow::{Context, Result, bail, ensure};
use base64::Engine;
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    fs::OpenOptions,
    io::{BufRead, Write},
    path::{Path, PathBuf},
    thread,
    time::{Duration, Instant},
};

const META_LIMIT: usize = 16 * 1024 * 1024;
pub const MEMBER_LIMIT: u64 = 160 * 1024 * 1024;

trait Link {
    fn write(&mut self, bytes: &[u8]) -> Result<()>;
    fn read(&mut self, bytes: &mut [u8]) -> Result<usize>;
    fn event(&mut self) -> Result<Option<Vec<u8>>>;
}

struct Ptp<L> {
    link: L,
    tx: u32,
    buffer: Vec<u8>,
    cursor: usize,
    poisoned: bool,
}
impl<L: Link> Ptp<L> {
    fn new(link: L) -> Self {
        Self {
            link,
            tx: 0,
            buffer: Vec::new(),
            cursor: 0,
            poisoned: false,
        }
    }
    fn take(&mut self, count: usize, output: &mut impl Write) -> Result<()> {
        let mut remaining = count;
        while remaining != 0 {
            if self.cursor == self.buffer.len() {
                self.buffer.resize(1024 * 1024, 0);
                let n = self.link.read(&mut self.buffer)?;
                ensure!(
                    n > 0 && n <= self.buffer.len(),
                    "Empty/invalid USB data transfer"
                );
                self.buffer.truncate(n);
                self.cursor = 0;
            }
            let n = remaining.min(self.buffer.len() - self.cursor);
            output.write_all(&self.buffer[self.cursor..self.cursor + n])?;
            self.cursor += n;
            remaining -= n;
        }
        Ok(())
    }
    fn command(&mut self, op: u16, args: &[u32], outgoing: Option<&[u8]>) -> Result<Vec<u8>> {
        let mut bytes = Vec::new();
        self.stream(op, args, outgoing, META_LIMIT, &mut bytes)?;
        Ok(bytes)
    }
    fn stream(
        &mut self,
        op: u16,
        args: &[u32],
        outgoing: Option<&[u8]>,
        bound: usize,
        output: &mut impl Write,
    ) -> Result<usize> {
        ensure!(
            !self.poisoned,
            "USB transaction uncertain; close the session, never retry the shutter"
        );
        self.poisoned = true;
        ensure!(args.len() <= 5, "Too many PTP parameters");
        let tx = self.tx;
        self.tx = self
            .tx
            .checked_add(1)
            .context("PTP transaction counter exhausted")?;
        let mut packet = header(12 + args.len() * 4, 1, op, tx);
        for arg in args {
            packet.extend(arg.to_le_bytes());
        }
        self.link.write(&packet)?;
        if let Some(data) = outgoing {
            ensure!(data.len() <= META_LIMIT, "Oversized outgoing property");
            let mut packet = header(12 + data.len(), 2, op, tx);
            packet.extend(data);
            self.link.write(&packet)?;
        }
        let mut size = 0;
        let mut seen_data = false;
        loop {
            let mut h = Vec::with_capacity(12);
            self.take(12, &mut h)?;
            let mut r = Reader::new(&h);
            let length = r.number(4)? as usize;
            let kind = r.number(2)?;
            let code = r.number(2)?;
            let received_tx = r.number(4)?;
            ensure!(
                length >= 12 && received_tx == u64::from(tx),
                "Invalid PTP container length or transaction"
            );
            if kind == 2 {
                ensure!(
                    !seen_data && code == u64::from(op) && outgoing.is_none(),
                    "Unexpected PTP data phase"
                );
                size = length - 12;
                ensure!(size <= bound, "PTP payload exceeds reserved bound");
                self.take(size, output)?;
                seen_data = true;
            } else {
                ensure!(
                    kind == 3 && length <= 32 && (length - 12).is_multiple_of(4),
                    "Invalid PTP response"
                );
                self.take(length - 12, &mut std::io::sink())?;
                // A complete explicit rejection leaves the transport synchronized.
                self.poisoned = false;
                ensure!(
                    code == 0x2001,
                    "PTP operation 0x{op:04x} rejected: 0x{code:04x}"
                );
                return Ok(size);
            }
        }
    }
    fn properties(&mut self) -> Result<Properties> {
        parse_properties(&self.command(0x9209, &[0, 1], None)?)
    }
    fn events(&mut self) -> Result<Vec<(u16, u32)>> {
        let mut events = Vec::new();
        for _ in 0..512 {
            let Some(b) = self.link.event()? else {
                return Ok(events);
            };
            events.extend(parse_events(&b)?);
        }
        bail!("Camera event flood; capture stopped")
    }
}
fn parse_events(bytes: &[u8]) -> Result<Vec<(u16, u32)>> {
    let mut result = Vec::new();
    let mut r = Reader::new(bytes);
    while r.cursor < bytes.len() {
        let length = r.number(4)? as usize;
        ensure!(
            (12..=32).contains(&length) && (length - 12).is_multiple_of(4),
            "Malformed PTP event length"
        );
        ensure!(r.number(2)? == 4, "Malformed PTP event type");
        let code = r.number(2)? as u16;
        r.number(4)?;
        let args = r.take(length - 12)?;
        let arg = if args.len() >= 4 {
            u32::from_le_bytes(args[..4].try_into()?)
        } else {
            0
        };
        result.push((code, arg));
    }
    Ok(result)
}
fn interrupt_bytes(code: i32, count: i32, mut bytes: Vec<u8>) -> Result<Option<Vec<u8>>> {
    // libusb timeouts can still contain transferred bytes. The event parser
    // validates complete containers; never discard an arrived focus result.
    if code == -7 && count == 0 {
        return Ok(None);
    }
    ensure!(
        matches!(code, 0 | -7) && count >= 12 && count as usize <= bytes.len(),
        "USB event read failed: {code}, {count} bytes"
    );
    bytes.truncate(count as usize);
    Ok(Some(bytes))
}

fn header(length: usize, kind: u16, code: u16, tx: u32) -> Vec<u8> {
    let mut v = Vec::with_capacity(length.min(4096));
    v.extend((length as u32).to_le_bytes());
    v.extend(kind.to_le_bytes());
    v.extend(code.to_le_bytes());
    v.extend(tx.to_le_bytes());
    v
}

struct Reader<'a> {
    bytes: &'a [u8],
    cursor: usize,
}
impl<'a> Reader<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }
    fn take(&mut self, count: usize) -> Result<&'a [u8]> {
        let end = self
            .cursor
            .checked_add(count)
            .context("Dataset length overflow")?;
        let bytes = self
            .bytes
            .get(self.cursor..end)
            .context("Truncated PTP dataset")?;
        self.cursor = end;
        Ok(bytes)
    }
    fn number(&mut self, width: usize) -> Result<u64> {
        ensure!(width <= 8, "Unsupported numeric width");
        let mut v = [0; 8];
        v[..width].copy_from_slice(self.take(width)?);
        Ok(u64::from_le_bytes(v))
    }
    fn value(&mut self, ty: u16) -> Result<Value> {
        if ty == 0xffff {
            let n = self.number(1)? as usize;
            let b = self.take(n * 2)?;
            let words: Vec<u16> = b
                .as_chunks::<2>()
                .0
                .iter()
                .map(|c| u16::from_le_bytes([c[0], c[1]]))
                .collect();
            return Ok(json!(String::from_utf16(&words)?.trim_end_matches('\0')));
        }
        if ty & 0x4000 != 0 {
            let n = self.number(4)? as usize;
            ensure!(
                n <= 65536 && ty & !0x4000 <= 10,
                "Oversized/invalid PTP array"
            );
            return (0..n)
                .map(|_| self.value(ty & !0x4000))
                .collect::<Result<Vec<_>>>()
                .map(Value::Array);
        }
        ensure!((1..=10).contains(&ty), "Unknown PTP datatype 0x{ty:x}");
        let width = 1usize << ((ty - 1) / 2);
        if width == 16 {
            return Ok(json!(
                self.take(width)?
                    .iter()
                    .map(|b| format!("{b:02x}"))
                    .collect::<String>()
            ));
        }
        let n = self.number(width)?;
        Ok(if ty % 2 == 1 {
            json!(((n << (64 - width * 8)) as i64) >> (64 - width * 8))
        } else {
            json!(n)
        })
    }
}
#[derive(Clone, Debug)]
struct Property {
    ty: u16,
    writable: bool,
    enabled: u8,
    value: Value,
    form: u8,
    allowed: Vec<Value>,
}
type Properties = BTreeMap<u16, Property>;
fn parse_properties(bytes: &[u8]) -> Result<Properties> {
    let mut r = Reader::new(bytes);
    let count = r.number(8)?;
    ensure!(count <= 4096, "Too many properties");
    let mut properties = BTreeMap::new();
    for _ in 0..count {
        let code = r.number(2)? as u16;
        let ty = r.number(2)? as u16;
        let writable = r.number(1)? == 1;
        let enabled = r.number(1)? as u8;
        r.value(ty)?;
        let value = r.value(ty)?;
        let form = r.number(1)? as u8;
        let mut allowed = Vec::new();
        match form {
            0 => (),
            1 => {
                for _ in 0..3 {
                    allowed.push(r.value(ty)?);
                }
            }
            2 => {
                let n = r.number(2)?;
                for _ in 0..n {
                    allowed.push(r.value(ty)?);
                }
                let n = r.number(2)?;
                for _ in 0..n {
                    r.value(ty)?;
                }
            }
            _ => bail!("Unknown PTP property form"),
        }
        ensure!(
            properties
                .insert(
                    code,
                    Property {
                        ty,
                        writable,
                        enabled,
                        value,
                        form,
                        allowed
                    }
                )
                .is_none(),
            "Duplicate property"
        );
    }
    ensure!(r.cursor == bytes.len(), "Trailing property dataset bytes");
    Ok(properties)
}
fn value(p: &Properties, code: u16) -> Result<u64> {
    let property = p
        .get(&code)
        .with_context(|| format!("Camera lacks property 0x{code:04x}"))?;
    ensure!(
        property.enabled != 0,
        "Camera property 0x{code:04x} is unavailable"
    );
    property.value.as_u64().context("Non-numeric property")
}
fn valid_setting(p: &Property, n: u64, magnifier: bool) -> Result<()> {
    ensure!(
        p.writable && p.enabled == 1 && matches!(p.ty, 2 | 4 | 6 | 8),
        "Camera setting is read-only in this mode"
    );
    if p.form == 1 {
        let v = p
            .allowed
            .iter()
            .map(|v| v.as_u64().context("Invalid unsigned range"))
            .collect::<Result<Vec<_>>>()?;
        ensure!(
            v.len() == 3
                && n >= v[0]
                && n <= v[1]
                && (v[2] == 0 || (n - v[0]).is_multiple_of(v[2])),
            "Setting outside advertised range"
        );
    } else if p.form == 2 {
        ensure!(
            p.allowed
                .iter()
                .any(|v| v.as_u64().is_some_and(|v| if magnifier {
                    v >> 32 == n >> 32
                } else {
                    v == n
                })),
            "Setting outside advertised choices"
        );
    }
    Ok(())
}
fn live_jpeg(bytes: &[u8]) -> Result<&[u8]> {
    let mut r = Reader::new(bytes);
    let offset = r.number(4)? as usize;
    let size = r.number(4)? as usize;
    ensure!(offset >= 16 && size >= 4, "Invalid preview offsets");
    let end = offset
        .checked_add(size)
        .context("Preview length overflow")?;
    let jpeg = bytes.get(offset..end).context("Preview outside payload")?;
    ensure!(jpeg.starts_with(&[0xff, 0xd8]), "Invalid preview JPEG");
    Ok(jpeg)
}
fn object_info(bytes: &[u8]) -> Result<(usize, String, u64)> {
    let mut r = Reader::new(bytes);
    r.number(4)?;
    let format = r.number(2)?;
    r.number(2)?;
    let size = r.number(4)? as usize;
    r.take(36)?;
    let sequence = r.number(4)?;
    let name = r
        .value(0xffff)?
        .as_str()
        .context("Invalid object filename")?
        .to_owned();
    ensure!(
        format == 0xb101 && name.to_ascii_lowercase().ends_with(".arw"),
        "Expected Sony RAW, received {name}"
    );
    ensure!(
        (1024..=MEMBER_LIMIT as usize).contains(&size),
        "A7CR RAW exceeds reserved member size"
    );
    Ok((size, name, sequence))
}

struct Camera<L> {
    ptp: Ptp<L>,
    ram: PathBuf,
    saved: Vec<(u16, u64)>,
    frame: u64,
    group: u64,
    uncertain: bool,
    configured: bool,
    shots: usize,
}
impl<L: Link> Camera<L> {
    fn open(link: L, ram: PathBuf) -> Result<Self> {
        let mut ptp = Ptp::new(link);
        ptp.command(0x1002, &[1], None)?;
        for phase in [1, 2] {
            ptp.command(0x9201, &[phase, 0, 0], None)?;
        }
        let mut ext = Vec::new();
        for _ in 0..30 {
            ext = ptp.command(0x9202, &[0x12c, 1], None)?;
            if !ext.is_empty() {
                break;
            }
            thread::sleep(Duration::from_millis(100));
        }
        ensure!(
            ext.len() >= 2 && u16::from_le_bytes([ext[0], ext[1]]) == 0x12c,
            "Camera did not negotiate Sony PTP 3"
        );
        ptp.command(0x9201, &[3, 0, 0], None)?;
        Ok(Self {
            ptp,
            ram,
            saved: vec![],
            frame: 0,
            group: 0,
            uncertain: false,
            configured: false,
            shots: 4,
        })
    }
    fn set(&mut self, code: u16, n: u64, save: bool) -> Result<()> {
        let p = self.ptp.properties()?;
        let current = value(&p, code)?;
        if current == n && code != 0xe042 {
            return Ok(());
        }
        let prop = p.get(&code).context("Missing setting")?;
        valid_setting(prop, n, code == 0xd254)?;
        if save && !self.saved.iter().any(|s| s.0 == code) {
            self.saved.push((code, current));
        }
        let width = 1usize << ((prop.ty - 1) / 2);
        self.ptp.command(
            0x9205,
            &[u32::from(code), 1],
            Some(&n.to_le_bytes()[..width]),
        )?;
        if code != 0xe042 {
            let end = Instant::now() + Duration::from_secs(3);
            loop {
                if value(&self.ptp.properties()?, code)? == n {
                    break;
                }
                ensure!(
                    Instant::now() < end,
                    "Setting 0x{code:04x} did not read back"
                );
                thread::sleep(Duration::from_millis(40));
            }
        }
        Ok(())
    }
    fn idle(p: &Properties) -> Result<()> {
        ensure!(
            value(p, 0xd23c)? == 0 && value(p, 0xd215)? == 0,
            "Camera group or download buffer is not idle"
        );
        Ok(())
    }
    fn configure(&mut self) -> Result<Value> {
        ensure!(!self.uncertain, "Previous capture is uncertain");
        let p = self.ptp.properties()?;
        Self::idle(&p)?;
        ensure!(
            value(&p, 0xd239)? == 1,
            "Enable Pixel Shift Multi Shoot. on the camera: 4 images, shortest interval, then reconnect"
        );
        value(&p, 0xe043)?; // Require genuine current-focus readback.
        self.set(0x500a, 1, true)?; // MF
        self.set(0xd222, 1, true)?; // Host only
        self.set(0xd23a, 4, true)?; // Public protocol allows writes 1 and 4 only.
        self.set(0xd23b, 65535, true)?;
        let p = self.ptp.properties()?;
        self.mode(&p)?;
        self.configured = true;
        Ok(json!({"ok":true,"pixel_shift_shots":4}))
    }
    fn set_pixel_shift(&mut self, shots: usize) -> Result<Value> {
        ensure!(self.configured && !self.uncertain, "Camera is not ready");
        ensure!(matches!(shots, 1 | 4), "Select one or four RAWs per plane");
        Self::idle(&self.ptp.properties()?)?;
        self.set(0xd23a, shots as u64, true)?;
        if shots == 4 {
            self.set(0xd23b, 65535, true)?;
        }
        // Keep the lossless transport's known uncompressed sensor representation.
        self.set(0xd288, 5, true)?;
        self.shots = shots;
        let p = self.ptp.properties()?;
        self.mode(&p)?;
        self.status()
    }
    fn mode(&self, p: &Properties) -> Result<()> {
        if self.shots == 4 {
            ensure!(
                value(p, 0xd239)? == 1 && value(p, 0xd23b)? == 65535,
                "Four-shot interval/mode changed; no shutter was sent"
            );
        }
        for (code, n) in [
            (0x500a, 1),
            (0xd222, 1),
            (0xd253, 1),
            (0xd288, 5),
            (0xd23a, self.shots as u64),
            (0x5013, 1),
        ] {
            ensure!(
                value(p, code)? == n,
                "Capture mode invariant 0x{code:04x} changed; no shutter was sent"
            );
        }
        Ok(())
    }
    fn status(&mut self) -> Result<Value> {
        let p = self.ptp.properties()?;
        let mut result = serde_json::Map::new();
        for (code, name) in [
            (0x500a, "FocusMode"),
            (0xe042, "FocusPositionSetting"),
            (0xe043, "FocusPositionCurrentValue"),
            (0x5013, "DriveMode"),
            (0xd222, "StillImageStoreDestination"),
            (0xd253, "FileType"),
            (0xd288, "RAW_FileCompressionType"),
            (0x5007, "FNumber"),
            (0xd20d, "ShutterSpeed"),
            (0xd21e, "IsoSensitivity"),
            (0x500e, "ExposureProgramMode"),
            (0x5001, "BatteryRemain"),
            (0xd221, "LiveViewStatus"),
            (0xd254, "Focus_Magnifier_Setting"),
            (0xd239, "PixelShiftMode"),
            (0xd23a, "PixelShiftShots"),
            (0xd23b, "PixelShiftInterval"),
            (0xd23c, "PixelShiftStatus"),
            (0xd23d, "PixelShiftProgress"),
            (0xd215, "ShootingFileInfo"),
            (0xd214, "PredictedMaximumFileSize"),
        ] {
            if let Some(v) = p.get(&code).filter(|p| p.enabled != 0) {
                result.insert(name.into(), json!({"value":v.value,"writable":v.writable && v.enabled==1,"allowed":v.allowed}));
            }
        }
        Ok(
            json!({"ok":true,"model":"ILCE-7CR","pixel_shift_shots":value(&p,0xd23a)?,"pixel_shift_options":[1,4],"raw_max_bytes":MEMBER_LIMIT,"properties":result}),
        )
    }
    fn focus(&mut self, target: u16, settle: u32) -> Result<Value> {
        ensure!(
            self.configured && !self.uncertain && (100..=30000).contains(&settle),
            "Focus unavailable or invalid settling delay"
        );
        let p = self.ptp.properties()?;
        Self::idle(&p)?;
        self.mode(&p)?;
        let before = value(&p, 0xe043)?;
        self.ptp.events()?;
        // Target-setting readback is NOT current lens position. Always use E043.
        if before != u64::from(target) {
            self.set(0xe042, target.into(), false)?;
        }
        let deadline =
            Instant::now() + Duration::from_secs(10) + Duration::from_millis(settle.into());
        let mut stable = None;
        let mut result_event = None;
        loop {
            for (code, result) in self.ptp.events()? {
                if code == 0xc218 {
                    ensure!(result == 1, "Camera rejected focus movement: {result}");
                    result_event = Some(result);
                }
            }
            let p = self.ptp.properties()?;
            let actual = value(&p, 0xe043)?;
            if actual == u64::from(target) {
                let since = stable.get_or_insert_with(Instant::now);
                if since.elapsed() >= Duration::from_millis(u64::from(settle).max(200)) {
                    break;
                }
            } else {
                stable = None;
            }
            ensure!(
                Instant::now() < deadline,
                "Focus did not reach and hold target {target}; no exposure"
            );
            thread::sleep(Duration::from_millis(40));
        }
        Ok(
            json!({"ok":true,"before":before,"requested":target,"readback":target,"completion":if result_event.is_some(){"event-and-stable-readback"}else{"stable-current-readback"},"focus_result_event":result_event,"settle_ms":settle,"pixel_shift_shots":self.shots}),
        )
    }
    fn preview(&mut self) -> Result<Value> {
        ensure!(
            value(&self.ptp.properties()?, 0xd221)? == 1,
            "Live preview temporarily unavailable"
        );
        if self.frame == 0 {
            self.ptp.command(0x1008, &[0xffffc002], None)?;
        }
        let data = self.ptp.command(0x1009, &[0xffffc002], None)?;
        let jpeg = live_jpeg(&data)?;
        self.frame += 1;
        Ok(
            json!({"ok":true,"frame":self.frame,"jpeg":base64::engine::general_purpose::STANDARD.encode(jpeg)}),
        )
    }
    fn button(&mut self, code: u32, down: bool) -> Result<()> {
        self.ptp.command(
            0x9207,
            &[code, 1],
            Some(&(if down { 2u16 } else { 1u16 }).to_le_bytes()),
        )?;
        Ok(())
    }
    fn capture(
        &mut self,
        timeout: u32,
        emit: &mut impl FnMut(Value) -> Result<()>,
    ) -> Result<Value> {
        ensure!(
            self.configured && !self.uncertain && (5..=3600).contains(&timeout),
            "Capture unavailable or invalid timeout"
        );
        let p = self.ptp.properties()?;
        Self::idle(&p)?;
        self.mode(&p)?;
        ensure!(
            value(&p, 0x500e)? == 1
                && value(&p, 0xd20d)? != 0
                && value(&p, 0xd21e)? & 0xffffff != 0xffffff,
            "Use manual timed exposure and fixed ISO"
        );
        ensure!(
            fs2::available_space(&self.ram)? >= MEMBER_LIMIT * self.shots as u64 + 4 * 1024 * 1024,
            "Insufficient reserved group RAM"
        );
        let focus = value(&p, 0xe043)?;
        self.ptp.events()?;
        self.group += 1;
        let group = format!("ptp-{}-{}", std::process::id(), self.group);
        let started = Instant::now();
        let mut files = Vec::new();
        let mut progress = Vec::new();
        self.uncertain = true; // Set BEFORE any shutter transition. Never retry it.
        self.button(0xd2c1, true)?;
        thread::sleep(Duration::from_millis(200));
        let release = self.button(0xd2c2, true);
        // Balanced button-up commands are cleanup, never another exposure.
        let up2 = self.button(0xd2c2, false);
        let up1 = self.button(0xd2c1, false);
        release?;
        up2?;
        up1?;
        let mut idle_since = None;
        loop {
            self.ptp.events()?;
            let p = self.ptp.properties()?;
            self.mode(&p)?;
            ensure!(
                value(&p, 0xe043)? == focus,
                "Focus changed within pixel-shift group"
            );
            let active = value(&p, 0xd23c)?;
            let member = value(&p, 0xd23d)?;
            let ready = value(&p, 0xd215)?;
            if progress.len() < 4096
                && progress.last().is_none_or(|v: &Value| {
                    v["active"] != active || v["member"] != member || v["buffer"] != ready
                })
            {
                progress.push(json!({"seconds":started.elapsed().as_secs_f64(),"active":active,"member":member,"buffer":ready}));
            }
            if ready & 0x8000 != 0 && ready & 0x7fff != 0 {
                ensure!(
                    files.len() < self.shots,
                    "Unexpected extra RAW; inspect camera buffer before reconnecting"
                );
                let (expected, name, sequence) =
                    object_info(&self.ptp.command(0x1008, &[0xffffc001], None)?)?;
                let path = self.ram.join(format!("{group}-{:02}.ARW", files.len() + 1));
                let mut file = OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .open(&path)?;
                let bytes = self
                    .ptp
                    .stream(0x1009, &[0xffffc001], None, expected, &mut file)?;
                file.flush()?;
                drop(file);
                ensure!(
                    bytes == expected,
                    "Incomplete RAW body retained; never replay shutter"
                );
                let item = json!({"ok":true,"event":"raw-ready","destination":"host-ram","completion":"ptp-object-complete","raw_compression":"uncompressed","path":path,"bytes":bytes,"group_id":group,"member_index":files.len()+1,"members":self.shots,"camera_name":name,"camera_sequence":sequence,"focus":focus,"seconds":started.elapsed().as_secs_f64()});
                files.push(item.clone());
                emit(item)?;
                idle_since = None;
            } else if files.len() == self.shots && active == 0 && ready == 0 {
                if idle_since.get_or_insert_with(Instant::now).elapsed()
                    >= Duration::from_millis(250)
                {
                    break;
                }
            } else {
                idle_since = None;
            }
            ensure!(
                started.elapsed() < Duration::from_secs(timeout.into()),
                "Capture group incomplete or timed out; files retained, shutter never retried"
            );
            thread::sleep(Duration::from_millis(25));
        }
        self.uncertain = false;
        Ok(
            json!({"ok":true,"destination":"host-ram","completion":"ptp-group-complete","raw_compression":"uncompressed","pixel_shift_shots":self.shots,"group_id":group,"focus":focus,"group_idle":true,"buffer_empty":true,"files":files,"progress":progress,"seconds":started.elapsed().as_secs_f64()}),
        )
    }
    fn close(&mut self) -> Result<Value> {
        let mut errors = Vec::new();
        if !self.uncertain && !self.ptp.poisoned {
            for (code, n) in self.saved.clone().into_iter().rev() {
                if let Err(e) = self.set(code, n, false) {
                    errors.push(format!("0x{code:04x}: {e:#}"));
                }
            }
        } else {
            errors.push(
                "Uncertain operation: settings and focus left untouched for inspection".into(),
            );
        }
        if !self.ptp.poisoned {
            self.ptp.command(0x1003, &[], None)?;
        }
        Ok(json!({"ok":true,"restored":errors.is_empty(),"warnings":errors}))
    }
}

#[cfg(target_os = "linux")]
mod usb {
    use super::*;
    use libloading::Library;
    use std::ffi::{c_int, c_uchar, c_uint, c_void};
    type Transfer =
        unsafe extern "C" fn(*mut c_void, c_uchar, *mut u8, c_int, *mut c_int, c_uint) -> c_int;
    pub struct Usb {
        _lib: Library,
        context: *mut c_void,
        device: *mut c_void,
        bulk: Transfer,
        interrupt: Transfer,
        release: unsafe extern "C" fn(*mut c_void, c_int) -> c_int,
        close: unsafe extern "C" fn(*mut c_void),
        exit: unsafe extern "C" fn(*mut c_void),
    }
    impl Usb {
        pub fn open() -> Result<Self> {
            let mut matches = 0;
            for e in std::fs::read_dir("/sys/bus/usb/devices")? {
                let p = e?.path();
                if std::fs::read_to_string(p.join("idVendor"))
                    .unwrap_or_default()
                    .trim()
                    == "054c"
                    && std::fs::read_to_string(p.join("idProduct"))
                        .unwrap_or_default()
                        .trim()
                        == "0e88"
                {
                    matches += 1;
                }
            }
            ensure!(
                matches == 1,
                "Connect exactly one ILCE-7CR in USB Remote Shoot; found {matches}"
            );
            // libusb public C ABI; function pointers remain valid while _lib lives.
            unsafe {
                let lib = Library::new("libusb-1.0.so.0")?;
                let init: libloading::Symbol<unsafe extern "C" fn(*mut *mut c_void) -> c_int> =
                    lib.get(b"libusb_init\0")?;
                let open: libloading::Symbol<
                    unsafe extern "C" fn(*mut c_void, u16, u16) -> *mut c_void,
                > = lib.get(b"libusb_open_device_with_vid_pid\0")?;
                let claim: libloading::Symbol<unsafe extern "C" fn(*mut c_void, c_int) -> c_int> =
                    lib.get(b"libusb_claim_interface\0")?;
                let release = *lib.get::<unsafe extern "C" fn(*mut c_void, c_int) -> c_int>(
                    b"libusb_release_interface\0",
                )?;
                let close = *lib.get::<unsafe extern "C" fn(*mut c_void)>(b"libusb_close\0")?;
                let exit = *lib.get::<unsafe extern "C" fn(*mut c_void)>(b"libusb_exit\0")?;
                let bulk = *lib.get::<Transfer>(b"libusb_bulk_transfer\0")?;
                let interrupt = *lib.get::<Transfer>(b"libusb_interrupt_transfer\0")?;
                let mut context = std::ptr::null_mut();
                ensure!(init(&mut context) == 0, "Initialize libusb failed");
                let device = open(context, 0x054c, 0x0e88);
                if device.is_null() {
                    exit(context);
                    bail!("Open A7CR USB failed; check udev permissions and USB mode");
                }
                if claim(device, 0) != 0 {
                    close(device);
                    exit(context);
                    bail!("Camera USB interface busy; close other camera clients");
                }
                Ok(Self {
                    _lib: lib,
                    context,
                    device,
                    bulk,
                    interrupt,
                    release,
                    close,
                    exit,
                })
            }
        }
    }
    impl Link for Usb {
        fn write(&mut self, b: &[u8]) -> Result<()> {
            let mut n = 0;
            // libusb takes a mutable pointer for both directions; OUT does not modify it.
            let code = unsafe {
                (self.bulk)(
                    self.device,
                    2,
                    b.as_ptr().cast_mut(),
                    b.len().try_into()?,
                    &mut n,
                    5000,
                )
            };
            ensure!(
                code == 0 && n as usize == b.len(),
                "USB write failed: {code}, {n} bytes"
            );
            Ok(())
        }
        fn read(&mut self, b: &mut [u8]) -> Result<usize> {
            let mut n = 0;
            let code = unsafe {
                (self.bulk)(
                    self.device,
                    0x81,
                    b.as_mut_ptr(),
                    b.len().try_into()?,
                    &mut n,
                    10000,
                )
            };
            ensure!(code == 0 && n >= 0, "USB read failed: {code}, {n} bytes");
            Ok(n as usize)
        }
        fn event(&mut self) -> Result<Option<Vec<u8>>> {
            let mut b = vec![0; 64];
            let mut n = 0;
            let code =
                unsafe { (self.interrupt)(self.device, 0x83, b.as_mut_ptr(), 64, &mut n, 10) };
            interrupt_bytes(code, n, b)
        }
    }
    impl Drop for Usb {
        fn drop(&mut self) {
            unsafe {
                (self.release)(self.device, 0);
                (self.close)(self.device);
                (self.exit)(self.context);
            }
        }
    }
    pub fn check_ram(path: &Path) -> Result<PathBuf> {
        let path = path.canonicalize()?;
        ensure!(
            path == Path::new("/run/strehl-raw"),
            "Use the dedicated /run/strehl-raw mount"
        );
        let mounts = std::fs::read_to_string("/proc/mounts")?;
        ensure!(
            mounts.lines().any(|line| {
                let p: Vec<_> = line.split_whitespace().collect();
                p.len() >= 4
                    && p[1] == "/run/strehl-raw"
                    && p[2] == "tmpfs"
                    && p[3].split(',').any(|v| v == "noswap")
            }),
            "RAW mount must be tmpfs,noswap"
        );
        ensure!(
            std::fs::read_to_string("/proc/swaps")?.lines().count() == 1,
            "Disable swap for RAM-only RAW capture"
        );
        Ok(path)
    }
}

pub fn serve() -> Result<()> {
    #[cfg(target_os = "linux")]
    {
        let args: Vec<_> = std::env::args().collect();
        ensure!(
            args.len() == 3 && args[1] == "serve-host",
            "Usage: strehl-sony-ptp serve-host /run/strehl-raw"
        );
        let ram = usb::check_ram(Path::new(&args[2]))?;
        let mut camera = Camera::open(usb::Usb::open()?, ram)?;
        let mut emit = |v: Value| -> Result<()> {
            println!("{v}");
            std::io::stdout().flush()?;
            Ok(())
        };
        emit(
            json!({"ok":true,"model":"ILCE-7CR","backend":"sony-ptp3","capture_protocol":2,"live_view_protocol":1,"host_pipeline_protocol":1,"group_stream_protocol":1,"pixel_shift_shots":4,"raw_format":"uncompressed"}),
        )?;
        for line in std::io::stdin().lock().lines() {
            let line = line?;
            let a: Vec<_> = line.split('\t').collect();
            if a[0] == "quit" {
                emit(camera.close()?)?;
                return Ok(());
            }
            let result = (|| -> Result<Value> {
                match a.as_slice() {
                    ["configure"] => camera.configure(),
                    ["status"] => camera.status(),
                    ["pixel-shift", shots] => camera.set_pixel_shift(shots.parse()?),
                    ["preview"] => camera.preview(),
                    ["focus", target, settle] => camera.focus(target.parse()?, settle.parse()?),
                    ["capture-host", timeout] => camera.capture(timeout.parse()?, &mut emit),
                    ["magnify", ratio, x, y] => {
                        let (r, x, y): (u64, u16, u16) = (ratio.parse()?, x.parse()?, y.parse()?);
                        ensure!(
                            r <= u32::MAX.into() && x <= 639 && y <= 479,
                            "Invalid magnifier position"
                        );
                        Camera::<usb::Usb>::idle(&camera.ptp.properties()?)?;
                        camera.set(
                            0xd254,
                            (r << 32) | (u64::from(x) << 16) | u64::from(y),
                            true,
                        )?;
                        Ok(json!({"ok":true}))
                    }
                    _ => bail!("Unsupported PTP bridge command"),
                }
            })();
            emit(result.unwrap_or_else(|e| json!({"ok":false,"error":format!("{e:#}")})))?;
        }
        camera.close()?;
        Ok(())
    }
    #[cfg(not(target_os = "linux"))]
    {
        bail!("The A7CR PTP backend currently runs on Linux USB hosts")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Fake {
        incoming: Vec<u8>,
        cursor: usize,
        writes: Vec<Vec<u8>>,
    }
    impl Link for Fake {
        fn write(&mut self, b: &[u8]) -> Result<()> {
            self.writes.push(b.to_vec());
            Ok(())
        }
        fn read(&mut self, b: &mut [u8]) -> Result<usize> {
            let n = (self.incoming.len() - self.cursor).min(b.len()).min(7);
            b[..n].copy_from_slice(&self.incoming[self.cursor..self.cursor + n]);
            self.cursor += n;
            Ok(n)
        }
        fn event(&mut self) -> Result<Option<Vec<u8>>> {
            Ok(None)
        }
    }
    fn fixture(bytes: Vec<u8>) -> Ptp<Fake> {
        Ptp::new(Fake {
            incoming: bytes,
            cursor: 0,
            writes: vec![],
        })
    }
    #[test]
    fn interrupt_timeout_with_arrived_bytes_keeps_focus_result() {
        let mut b = header(16, 4, 0xc218, u32::MAX);
        b.extend(1u32.to_le_bytes());
        let packet = interrupt_bytes(-7, 16, b.clone()).unwrap().unwrap();
        assert_eq!(parse_events(&packet).unwrap(), vec![(0xc218, 1)]);
        let mut batch = b.clone();
        batch.extend(&b);
        assert_eq!(parse_events(&batch).unwrap().len(), 2);
        assert!(interrupt_bytes(-7, 0, vec![0; 64]).unwrap().is_none());
        assert!(interrupt_bytes(-4, 16, b.clone()).is_err());
        assert!(parse_events(&b[..15]).is_err());
    }
    #[test]
    fn fragmented_usb_and_wrong_transaction_and_size_fail_closed() {
        let mut bytes = header(16, 2, 0x1009, 0);
        bytes.extend([1, 2, 3, 4]);
        bytes.extend(header(12, 3, 0x2001, 0));
        assert_eq!(
            fixture(bytes.clone()).command(0x1009, &[], None).unwrap(),
            vec![1, 2, 3, 4]
        );
        let mut p = fixture(bytes.clone());
        assert!(p.stream(0x1009, &[], None, 3, &mut Vec::new()).is_err());
        assert!(p.poisoned);
        bytes[8] = 1;
        let mut p = fixture(bytes);
        assert!(p.command(0x1009, &[], None).is_err());
        assert!(p.poisoned);
        assert_eq!(p.link.writes.len(), 1);
        assert!(p.command(0x1009, &[], None).is_err());
        assert_eq!(p.link.writes.len(), 1);
    }
    #[test]
    fn properties_and_preview_are_bounded_and_not_assumed_offset_zero() {
        let mut bytes = 1u64.to_le_bytes().to_vec();
        bytes.extend(0xd23au16.to_le_bytes());
        bytes.extend(4u16.to_le_bytes());
        bytes.extend([1, 1]);
        bytes.extend(1u16.to_le_bytes());
        bytes.extend(4u16.to_le_bytes());
        bytes.push(2);
        bytes.extend(2u16.to_le_bytes());
        bytes.extend(1u16.to_le_bytes());
        bytes.extend(4u16.to_le_bytes());
        bytes.extend(0u16.to_le_bytes());
        let p = parse_properties(&bytes).unwrap();
        assert_eq!(value(&p, 0xd23a).unwrap(), 4);
        valid_setting(&p[&0xd23a], 4, false).unwrap();
        assert!(valid_setting(&p[&0xd23a], 16, false).is_err());
        for n in 0..bytes.len() {
            assert!(parse_properties(&bytes[..n]).is_err());
        }
        bytes.push(0);
        assert!(parse_properties(&bytes).is_err());
        let mut b = vec![0; 36];
        b[..4].copy_from_slice(&32u32.to_le_bytes());
        b[4..8].copy_from_slice(&4u32.to_le_bytes());
        b[32..].copy_from_slice(&[255, 216, 255, 217]);
        assert_eq!(live_jpeg(&b).unwrap(), &[255, 216, 255, 217]);
        b[4] = 5;
        assert!(live_jpeg(&b).is_err());
        b[4] = 4;
        b[32] = 0;
        assert!(live_jpeg(&b).is_err());
    }
}
