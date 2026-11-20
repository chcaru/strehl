    // ---- EXPERIMENT ONLY (capture-pipeline-2026-11-20): timing primitives. ----
    // Inserted into a copy of `ptp.rs` by `make-lab.py`; never part of the product.
    fn lab_watch(p: &Properties) -> [u64; 5] {
        let get = |code| p.get(&code).and_then(|v| v.value.as_u64()).unwrap_or(u64::MAX);
        [get(0xd23c), get(0xd23d), get(0xd215), get(0xe043), get(0xe042)]
    }
    fn lab_keep() -> &'static std::sync::Mutex<bool> {
        static KEEP: std::sync::Mutex<bool> = std::sync::Mutex::new(false);
        &KEEP
    }
    fn lab_download(&mut self, t0: Instant) -> Result<Value> {
        let began = t0.elapsed().as_secs_f64();
        let (expected, name, sequence) =
            object_info(&self.ptp.command(0x1008, &[0xffffc001], None)?)?;
        let info = t0.elapsed().as_secs_f64();
        self.group += 1;
        let path = self.ram.join(format!("lab-{}-{}.ARW", std::process::id(), self.group));
        let mut file = OpenOptions::new().write(true).create_new(true).open(&path)?;
        let bytes = self.ptp.stream(0x1009, &[0xffffc001], None, expected, &mut file)?;
        file.flush()?;
        drop(file);
        if !*Self::lab_keep().lock().unwrap() {
            std::fs::remove_file(&path)?;
        }
        ensure!(bytes == expected, "Incomplete RAW body");
        Ok(json!({"lab":"download","t":began,"info_t":info,"done_t":t0.elapsed().as_secs_f64(),
            "bytes":bytes,"camera_name":name,"camera_sequence":sequence}))
    }
    fn lab(
        &mut self,
        a: &[&str],
        t0: Instant,
        emit: &mut impl FnMut(Value) -> Result<()>,
    ) -> Result<Value> {
        let now = || t0.elapsed().as_secs_f64();
        match a {
            ["lab-mark", text] => Ok(json!({"lab":"mark","t":now(),"text":text})),
            ["lab-sleep", ms] => {
                thread::sleep(Duration::from_millis(ms.parse()?));
                Ok(json!({"lab":"sleep","t":now()}))
            }
            ["lab-props", count] => {
                let mut ms = Vec::new();
                let mut ev = Vec::new();
                let mut last = [0; 5];
                for _ in 0..count.parse::<usize>()? {
                    let s = Instant::now();
                    let p = self.ptp.properties()?;
                    ms.push(s.elapsed().as_secs_f64() * 1e3);
                    last = Self::lab_watch(&p);
                    let s = Instant::now();
                    self.ptp.events()?;
                    ev.push(s.elapsed().as_secs_f64() * 1e3);
                }
                Ok(json!({"lab":"props","t":now(),"properties_ms":ms,"events_ms":ev,"watch":last}))
            }
            ["lab-allowed", code] => {
                let code = u16::from_str_radix(code, 16)?;
                let p = self.ptp.properties()?;
                let v = p.get(&code).context("Missing property")?;
                Ok(json!({"lab":"allowed","t":now(),"code":format!("{code:04x}"),"type":v.ty,
                    "writable":v.writable,"enabled":v.enabled,"value":v.value,"form":v.form,"allowed":v.allowed}))
            }
            // Raw property write, no readback wait.
            ["lab-set", code, n] => {
                let code = u16::from_str_radix(code, 16)?;
                let n: u64 = n.parse()?;
                let p = self.ptp.properties()?;
                let prop = p.get(&code).context("Missing setting")?;
                let width = 1usize << ((prop.ty - 1) / 2);
                let began = now();
                self.ptp.command(0x9205, &[u32::from(code), 1], Some(&n.to_le_bytes()[..width]))?;
                Ok(json!({"lab":"set","t":began,"done_t":now(),"code":format!("{code:04x}"),"value":n,
                    "before":prop.value,"enabled":prop.enabled,"writable":prop.writable}))
            }
            // Property write with the product's validation, save and readback.
            ["lab-setrb", code, n] => {
                let began = now();
                self.set(u16::from_str_radix(code, 16)?, n.parse()?, true)?;
                Ok(json!({"lab":"setrb","t":began,"done_t":now()}))
            }
            ["lab-shutter", pre_ms, mode] => {
                let began = now();
                let pre: u64 = pre_ms.parse()?;
                match *mode {
                    "s1s2" => {
                        self.button(0xd2c1, true)?;
                        if pre != 0 {
                            thread::sleep(Duration::from_millis(pre));
                        }
                        let release = self.button(0xd2c2, true);
                        let up2 = self.button(0xd2c2, false);
                        let up1 = self.button(0xd2c1, false);
                        release?;
                        up2?;
                        up1?;
                    }
                    "s2" => {
                        let release = self.button(0xd2c2, true);
                        let up2 = self.button(0xd2c2, false);
                        release?;
                        up2?;
                    }
                    _ => bail!("lab-shutter mode"),
                }
                Ok(json!({"lab":"shutter","t":began,"done_t":now(),"mode":mode,"pre_ms":pre}))
            }
            // Move focus by DELTA units from the current lens position; no wait.
            ["lab-jog", delta] => {
                let p = self.ptp.properties()?;
                let from = value(&p, 0xe043)?;
                let target = (from as i64 + delta.parse::<i64>()?) as u64;
                let began = now();
                self.ptp.command(0x9205, &[0xe042, 1], Some(&(target as u16).to_le_bytes()))?;
                self.frame = target;
                Ok(json!({"lab":"jog","t":began,"done_t":now(),"from":from,"target":target,
                    "active":value(&p, 0xd23c)?,"buffer":format!("{:04x}", value(&p, 0xd215)?)}))
            }
            ["lab-download"] => self.lab_download(t0),
            // Keep downloaded RAWs in the RAM folder (on) until `lab-stash` moves them.
            ["lab-keep", on] => {
                *Self::lab_keep().lock().unwrap() = *on == "on";
                Ok(json!({"lab":"keep","t":now(),"on":on}))
            }
            ["lab-stash", dir, prefix] => {
                std::fs::create_dir_all(dir)?;
                let began = now();
                let mut names: Vec<_> = std::fs::read_dir(&self.ram)?
                    .filter_map(|e| e.ok().map(|e| e.path()))
                    .filter(|p| p.file_name().and_then(|n| n.to_str()).is_some_and(|n| n.starts_with("lab-")))
                    .collect();
                names.sort_by_key(|p| std::fs::metadata(p).and_then(|m| m.modified()).ok());
                let mut moved = Vec::new();
                for (i, path) in names.iter().enumerate() {
                    let to = format!("{dir}/{prefix}-{}.ARW", i + 1);
                    std::fs::copy(path, &to)?;
                    std::fs::remove_file(path)?;
                    moved.push(to);
                }
                Ok(json!({"lab":"stash","t":began,"done_t":now(),"files":moved}))
            }
            // Live-view frames as fast as the link gives them for MS, saved with their
            // times; events are logged between frames. JOG_MS after the start the lens is
            // sent DELTA units (0 for no move).
            ["lab-liveview", ms, dir, jog_ms, delta] => {
                let began_all = Instant::now();
                let end = began_all + Duration::from_millis(ms.parse()?);
                let jog_at = began_all + Duration::from_millis(jog_ms.parse()?);
                let delta: i64 = delta.parse()?;
                let mut jogged = delta == 0;
                std::fs::create_dir_all(dir)?;
                self.ptp.command(0x1008, &[0xffffc002], None)?;
                let mut frames = Vec::new();
                while Instant::now() < end {
                    for (code, arg) in self.ptp.events()? {
                        emit(json!({"lab":"event","t":now(),"code":format!("{code:04x}"),"arg":arg}))?;
                    }
                    if !jogged && Instant::now() >= jog_at {
                        let p = self.ptp.properties()?;
                        let from = value(&p, 0xe043)?;
                        let target = (from as i64 + delta) as u64;
                        ensure!(target <= 65535, "lab jog beyond the lens range");
                        let t = now();
                        self.ptp.command(0x9205, &[0xe042, 1], Some(&(target as u16).to_le_bytes()))?;
                        self.frame = target;
                        emit(json!({"lab":"jog","t":t,"done_t":now(),"from":from,"target":target,
                            "active":value(&p, 0xd23c)?,"buffer":format!("{:04x}", value(&p, 0xd215)?)}))?;
                        jogged = true;
                    }
                    let began = now();
                    // The camera refuses a fetch until it has a new frame.
                    let data = match self.ptp.command(0x1009, &[0xffffc002], None) {
                        Ok(data) => data,
                        Err(e) if format!("{e:#}").contains("0x200f") => {
                            thread::sleep(Duration::from_millis(4));
                            continue;
                        }
                        Err(e) => return Err(e),
                    };
                    let jpeg = live_jpeg(&data)?;
                    let name = format!("{dir}/lv-{:05}.jpg", frames.len());
                    std::fs::write(&name, jpeg)?;
                    frames.push(json!([began, now(), jpeg.len()]));
                }
                let p = self.ptp.properties()?;
                Ok(json!({"lab":"liveview","t":now(),"dir":dir,"frames":frames,"focus":value(&p, 0xe043)?}))
            }
            // Poll events and properties for up to MS, logging every change.
            // MODE: auto (download whenever an object is ready) | hold.
            // STOP: none | idle | active0 | ready | focus:N | count:N | ev:c218
            ["lab-watch", ms, mode, stop] => {
                let end = Instant::now() + Duration::from_millis(ms.parse()?);
                let auto = *mode == "auto";
                let mut last = None;
                let mut was_active = false;
                let mut polls = 0u32;
                let mut why = "time";
                let mut counted = 0u32;
                let wanted = stop.strip_prefix("evn:").map(|s| {
                    let (code, n) = s.split_once(':').unwrap_or((s, "1"));
                    (u16::from_str_radix(code, 16).unwrap_or(0), n.parse::<u32>().unwrap_or(1))
                });
                'outer: while Instant::now() < end {
                    for (code, arg) in self.ptp.events()? {
                        emit(json!({"lab":"event","t":now(),"code":format!("{code:04x}"),"arg":arg}))?;
                        if *stop == "ev:c218" && code == 0xc218 {
                            why = "event";
                            break 'outer;
                        }
                        if let Some((want, n)) = wanted
                            && code == want
                        {
                            counted += 1;
                            if counted >= n {
                                why = "event-count";
                                break 'outer;
                            }
                        }
                    }
                    let p = self.ptp.properties()?;
                    polls += 1;
                    let w = Self::lab_watch(&p);
                    if last != Some(w) {
                        emit(json!({"lab":"state","t":now(),"active":w[0],"member":w[1],
                            "buffer":format!("{:04x}", w[2]),"focus":w[3],"focus_setting":w[4]}))?;
                        last = Some(w);
                    }
                    was_active |= w[0] != 0;
                    let ready = w[2] & 0x8000 != 0 && w[2] & 0x7fff != 0;
                    if auto && ready {
                        let d = self.lab_download(t0)?;
                        emit(d)?;
                        continue;
                    }
                    let done = match *stop {
                        "idle" => was_active && w[0] == 0 && w[2] == 0,
                        "active0" => was_active && w[0] == 0,
                        "ready" => ready,
                        "attarget" => w[3] == self.frame,
                        s if s.starts_with("focus:") => w[3] == s[6..].parse::<u64>()?,
                        s if s.starts_with("count:") => w[2] & 0x7fff == s[6..].parse::<u64>()?,
                        _ => false,
                    };
                    if done {
                        why = "stop";
                        break;
                    }
                    thread::sleep(Duration::from_millis(5));
                }
                Ok(json!({"lab":"watch","t":now(),"polls":polls,"ended":why}))
            }
            _ => bail!("Unsupported lab command"),
        }
    }
    // ---- end of experiment code ----
