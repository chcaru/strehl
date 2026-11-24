//! Local Shelly outlets bound to the rig by device ID. Only the camera worker switches power.
use crate::lan::Lan;
use anyhow::{Context, Result, bail, ensure};
use reqwest::{blocking::Client, redirect::Policy};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    io::Read,
    net::{IpAddr, Ipv4Addr, ToSocketAddrs},
    sync::{
        Arc, Mutex,
        atomic::{AtomicU32, Ordering},
    },
    thread,
    time::{Duration, Instant},
};

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Outlet {
    Light,
    Camera,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Plug {
    pub id: String,
    pub ip: Option<Ipv4Addr>,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PowerConfig {
    pub light: Plug,
    pub camera: Plug,
    #[serde(default = "default_warmup")]
    pub warmup_seconds: u32,
}
fn default_warmup() -> u32 {
    5
}
pub struct RigPower {
    config: PowerConfig,
    warmup: AtomicU32,
    lan: Lan,
    client: Client,
    // Serialize a reading and its publication with a write and its readback.
    // State requests only read the cache, never wait for a plug.
    operation: Mutex<()>,
    readings: Mutex<[Option<(Instant, Value)>; 2]>,
    /// When this controller switched the light on; `None` when it is off or
    /// was found on (how long it has been warm is then unknown).
    light_since: Mutex<Option<Instant>>,
}
impl RigPower {
    pub fn new(config: PowerConfig, lan: Lan) -> Result<Arc<Self>> {
        for plug in [&config.light, &config.camera] {
            ensure!(
                plug.id
                    .strip_prefix("shellyplugusg4-")
                    .is_some_and(|id| id.len() == 12
                        && id
                            .bytes()
                            .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())),
                "Expected a Shelly Plug US Gen4 device ID"
            );
            if let Some(ip) = plug.ip {
                ensure!(
                    ip.is_private() && lan.permits(IpAddr::V4(ip)),
                    "Outlet IP is outside the configured capture LAN"
                );
            }
        }
        ensure!(
            config.light.id != config.camera.id
                && (config.light.ip.is_none() || config.light.ip != config.camera.ip),
            "Light and camera must be different plugs"
        );
        ensure!(
            config.warmup_seconds <= 300,
            "Light warmup exceeds five minutes"
        );
        let rig = Arc::new(Self {
            warmup: AtomicU32::new(config.warmup_seconds),
            config,
            lan,
            client: Client::builder()
                .no_proxy()
                .redirect(Policy::none())
                .retry(reqwest::retry::never())
                .timeout(Duration::from_secs(3))
                .build()?,
            operation: Mutex::new(()),
            readings: Mutex::new([None, None]),
            light_since: Mutex::new(None),
        });
        let weak = Arc::downgrade(&rig);
        thread::Builder::new()
            .name("studio-power-status".into())
            .spawn(move || {
                while let Some(rig) = weak.upgrade() {
                    for device in [Outlet::Light, Outlet::Camera] {
                        let _ = rig.read(device);
                    }
                    drop(rig);
                    thread::sleep(Duration::from_secs(4));
                }
            })?;
        Ok(rig)
    }
    /// How long the light has been on since this controller switched it
    /// on (plan Q3): `None` when it is off, was switched on elsewhere, or
    /// its last reading says off.
    pub fn light_on_for(&self) -> Option<Duration> {
        let since = (*self.light_since.lock().unwrap())?;
        let off = self.readings.lock().unwrap()[Outlet::Light as usize]
            .as_ref()
            .is_some_and(|(_, reading)| reading["on"] == false);
        (!off).then(|| since.elapsed())
    }
    pub fn warmup_seconds(&self) -> u32 {
        self.warmup.load(Ordering::Relaxed)
    }
    pub fn set_warmup(&self, seconds: u32) {
        self.warmup.store(seconds, Ordering::Relaxed);
    }
    pub fn status(&self) -> Value {
        let guard = self.readings.lock().unwrap();
        let sample = |index: usize| match &guard[index] {
            Some((when, value)) if when.elapsed() < Duration::from_secs(20) => value.clone(),
            _ => json!({"error":"Waiting for outlet status"}),
        };
        json!({"light":sample(0),"camera":sample(1),"warmup_seconds":self.warmup_seconds()})
    }
    fn rpc(&self, ip: Ipv4Addr, method: &str, params: Value) -> Result<Value> {
        let response = self
            .client
            .post(format!("http://{ip}/rpc/{method}"))
            .json(&params)
            .send()?
            .error_for_status()?;
        let mut body = Vec::new();
        response.take(8193).read_to_end(&mut body)?;
        ensure!(body.len() <= 8192, "Unexpected outlet reply size");
        let reply: Value = serde_json::from_slice(&body)?;
        ensure!(
            reply.is_object() && reply.get("error").is_none() && reply.get("code").is_none(),
            "Outlet refused {method}"
        );
        Ok(reply)
    }
    fn verify(&self, plug: &Plug, ip: Ipv4Addr) -> Result<()> {
        ensure!(
            ip.is_private() && self.lan.permits(IpAddr::V4(ip)),
            "Outlet is outside the capture LAN"
        );
        let info = self.rpc(ip, "Shelly.GetDeviceInfo", json!({}))?;
        ensure!(
            info["id"] == plug.id && info["model"] == "S4PL-00116US" && info["gen"] == 4,
            "Outlet identity mismatch"
        );
        Ok(())
    }
    fn address(&self, device: Outlet) -> Result<Ipv4Addr> {
        let plug = match device {
            Outlet::Light => &self.config.light,
            Outlet::Camera => &self.config.camera,
        };
        if let Some(ip) = plug.ip
            && self.verify(plug, ip).is_ok()
        {
            return Ok(ip);
        }
        let name = format!("{}.local", plug.id);
        if let Ok(addrs) = (name.as_str(), 80).to_socket_addrs() {
            for a in addrs {
                if let IpAddr::V4(ip) = a.ip()
                    && Some(ip) != plug.ip
                    && self.verify(plug, ip).is_ok()
                {
                    return Ok(ip);
                }
            }
        }
        bail!("Could not verify the configured {device:?} Shelly on the LAN")
    }
    fn reading(&self, ip: Ipv4Addr) -> Result<Value> {
        let value = self.rpc(ip, "Switch.GetStatus", json!({"id":0}))?;
        let on = value["output"]
            .as_bool()
            .context("Missing relay readback")?;
        let watts = value["apower"].as_f64().context("Missing power reading")?;
        ensure!(
            value["id"] == 0 && watts.is_finite(),
            "Invalid switch status"
        );
        Ok(json!({"on":on,"watts":watts,"errors":value["errors"]}))
    }
    fn publish(&self, device: Outlet, result: &Result<Value>) {
        let value = match result {
            Ok(v) => v.clone(),
            Err(e) => json!({"error":format!("{e:#}")}),
        };
        self.readings.lock().unwrap()[if device == Outlet::Light { 0 } else { 1 }] =
            Some((Instant::now(), value));
    }
    pub fn read(&self, device: Outlet) -> Result<Value> {
        let _guard = self.operation.lock().unwrap();
        let result = self.address(device).and_then(|ip| self.reading(ip));
        self.publish(device, &result);
        result
    }
    pub fn set(&self, device: Outlet, on: bool) -> Result<Value> {
        let _guard = self.operation.lock().unwrap();
        let result = (|| {
            let ip = self.address(device)?;
            let before = self.reading(ip)?;
            if on {
                ensure!(
                    before["errors"].as_array().is_none_or(Vec::is_empty),
                    "{device:?} plug reports a protection fault"
                );
            }
            if before["on"] == on {
                return Ok((before, false));
            }
            // A lost write response may already have switched the outlet. Read back without replay.
            let sent = self.rpc(ip, "Switch.Set", json!({"id":0,"on":on}));
            let after = self.reading(ip)?;
            if after["on"] != on {
                sent?;
                bail!("{device:?} outlet did not confirm the requested state");
            }
            Ok((after, true))
        })();
        if device == Outlet::Light {
            let mut since = self.light_since.lock().unwrap();
            match &result {
                Ok((_, true)) if on => *since = Some(Instant::now()),
                Ok(_) if !on => *since = None,
                _ => {}
            }
        }
        let result = result.map(|(reading, _)| reading);
        self.publish(device, &result);
        result
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{Json, Router, http::StatusCode, routing::post};
    use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

    // Route a private, numeric test address into a loopback fixture. No real
    // home network or DNS answer can receive a write in this test.
    #[test]
    fn lost_set_ack_is_read_back_once_and_wrong_identity_cannot_switch() {
        let camera_id = "shellyplugusg4-001122334455";
        let ip = Some(Ipv4Addr::new(10, 42, 17, 22));
        let camera = Plug {
            id: camera_id.into(),
            ip,
        };
        let light = Plug {
            id: "shellyplugusg4-000000000000".into(),
            ip: Some(Ipv4Addr::new(10, 42, 17, 23)),
        };
        let writes = Arc::new(AtomicUsize::new(0));
        let observed = writes.clone();
        let enabled = Arc::new(AtomicBool::new(false));
        let status = enabled.clone();
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        listener.set_nonblocking(true).unwrap();
        let address = listener.local_addr().unwrap();
        let (stop, done) = tokio::sync::oneshot::channel::<()>();
        let server = thread::spawn(move || {
            tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .unwrap()
                .block_on(async move {
                    let app = Router::new()
                        .route(
                            "/rpc/Shelly.GetDeviceInfo",
                            post(move || async move {
                                Json(json!({"id":camera_id,"model":"S4PL-00116US","gen":4}))
                            }),
                        )
                        .route(
                            "/rpc/Switch.GetStatus",
                            post(move || {
                                let on = status.load(Ordering::SeqCst);
                                async move { Json(json!({"id":0,"output":on,"apower":0.0})) }
                            }),
                        )
                        .route(
                            "/rpc/Switch.Set",
                            post(move |Json(p): Json<Value>| {
                                observed.fetch_add(1, Ordering::SeqCst);
                                enabled.store(p["on"].as_bool().unwrap(), Ordering::SeqCst);
                                async { StatusCode::BAD_GATEWAY }
                            }),
                        );
                    axum::serve(tokio::net::TcpListener::from_std(listener).unwrap(), app)
                        .with_graceful_shutdown(async {
                            let _ = done.await;
                        })
                        .await
                        .unwrap();
                });
        });
        let rig = RigPower {
            warmup: AtomicU32::new(1),
            config: PowerConfig {
                light,
                camera,
                warmup_seconds: 1,
            },
            lan: Lan::parse("10.42.17.0/24").unwrap(),
            client: Client::builder()
                .proxy(reqwest::Proxy::all(format!("http://{address}")).unwrap())
                .retry(reqwest::retry::never())
                .build()
                .unwrap(),
            operation: Mutex::new(()),
            readings: Mutex::new([None, None]),
            light_since: Mutex::new(None),
        };
        assert_eq!(rig.set(Outlet::Camera, true).unwrap()["on"], true);
        assert_eq!(rig.set(Outlet::Camera, true).unwrap()["on"], true);
        // Q3: the camera's outlet starts no light timer.
        assert!(rig.light_on_for().is_none());
        assert!(rig.set(Outlet::Light, false).is_err());
        // A refused switch leaves the light's timer as it was.
        assert!(rig.light_on_for().is_none());
        *rig.light_since.lock().unwrap() = Some(Instant::now() - Duration::from_secs(90));
        assert!(rig.light_on_for().unwrap() >= Duration::from_secs(90));
        assert_eq!(writes.load(Ordering::SeqCst), 1);
        drop(rig);
        let _ = stop.send(());
        server.join().unwrap();
    }
}
