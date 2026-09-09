// Thin test-only adapter around the original M194b source and production consumer.
use super::*;
use crate::align_cmd::DirectPlaneMode;
use std::sync::Mutex;

pub(super) struct Configuration { pub mode: DirectPlaneMode, pub label: String, pub observer: bool }
impl Configuration {
    pub(super) fn load() -> Result<Self> {
        ensure!(!cfg!(feature = "native-boundary-radiance"), "direct bridge requires a build without the boundary-radiance adapter");
        let label = std::env::var("STREHL_DIRECT_PLANES").context("direct bridge requires explicit STREHL_DIRECT_PLANES")?;
        let mode = align_cmd::direct_plane_mode()?;
        ensure!(matches!(label.as_str(), "off" | "rounded" | "float"), "invalid direct mode");
        let observer = match env("DIRECT_OBSERVER")?.as_str() {
            "on" => true, "off" => false, _ => bail!("DIRECT_OBSERVER must be on or off"),
        };
        ensure!(std::env::var(format!("{PREFIX}DIAGNOSTIC")).is_err()
            && std::env::var(format!("{PREFIX}CONFIDENCE")).is_err()
            && env("SUBSET")? == "all", "direct bridge fixes all nine frames without extra diagnostics/confidence");
        Ok(Self { mode, label, observer })
    }
    pub(super) fn bind(&self, inputs: &Inputs, plan: &mut Value) -> Result<()> {
        let m = &inputs.manifest;
        let selected = match (m.scene.as_str(), m.noise_enabled, m.repeat) {
            ("flat" | "plane" | "color", false, None) => true,
            ("flat", true, Some(seed)) => [701,709,719,727,733,739,743,751].contains(&seed),
            _ => false,
        };
        ensure!(selected, "manifest is outside fixed direct-plane population");
        ensure!(self.observer || (self.mode == DirectPlaneMode::Off && m.scene == "flat" && !m.noise_enabled),
            "observer-off placebo is only the flat/noise-off off-mode fixture");
        plan["schema"] = json!("native-direct-planes-consumer-plan-v1");
        plan["direct_planes_mode"] = json!(self.label);
        plan["direct_planes_observer"] = json!(self.observer);
        Ok(())
    }
}

#[derive(Default)]
struct Record { inputs: BTreeMap<usize,Value>, collapsed: Vec<Value> }
pub(super) struct Trace { enabled: bool, record: Mutex<Record> }
fn values(label: &str, input: &[f32]) -> Value {
    let mut h = Sha256::new();
    for value in input { h.update(value.to_bits().to_le_bytes()); }
    json!({"label":label,"values":input.len(),"sha256_f32_le":hex(&h.finalize()),
        "finite_values":input.iter().filter(|v|v.is_finite()).count(),
        "fractional_values":input.iter().filter(|v|v.is_finite() && v.fract()!=0.0).count()})
}
fn planes(input: &[Vec<f32>]) -> Value {
    json!(input.iter().enumerate().map(|(i,p)| values(["R","G1","G2","B"][i],p)).collect::<Vec<_>>())
}
impl Trace {
    pub(super) fn new(enabled: bool) -> Self { Self { enabled, record: Mutex::new(Record::default()) } }
    pub(super) fn inputs(&self, index: usize, p: &[Vec<f32>], luma: &[f32], beta: Option<&[f32]>) -> Result<()> {
        if !self.enabled { return Ok(()); }
        ensure!(p.len()==4, "observed inputs must have four planes");
        let value = json!({"original_index":index,"planes":planes(p),"luma":values("luma",luma),
            "beta":beta.map(|v|values("beta",v))});
        ensure!(self.record.lock().map_err(|_|anyhow::anyhow!("direct trace poisoned"))?.inputs.insert(index,value).is_none(),
            "duplicate direct input observation");
        Ok(())
    }
    pub(super) fn collapsed(&self, p: &[Vec<f32>]) -> Result<()> {
        if !self.enabled { return Ok(()); }
        ensure!(p.len()==4, "observed collapse must have four planes");
        self.record.lock().map_err(|_|anyhow::anyhow!("direct trace poisoned"))?.collapsed.push(planes(p));
        Ok(())
    }
    pub(super) fn receipt(&self, config: &Configuration, before: (usize,usize), domain: PyramidDomain) -> Result<Value> {
        let after = align_cmd::direct_plane_hits();
        align_cmd::direct_plane_observer(false);
        let (actual,probe) = (after.0-before.0,after.1-before.1);
        let record = self.record.lock().map_err(|_|anyhow::anyhow!("direct trace poisoned"))?;
        let count = record.collapsed.iter().flat_map(|p|p.as_array().into_iter().flatten())
            .map(|p|p["values"].as_u64().unwrap_or(0) as usize).sum();
        controls::assert_render_evidence(config.mode,config.observer,actual,probe,
            record.inputs.len(),record.collapsed.len(),count)?;
        Ok(json!({"observer_enabled":config.observer,"actual_direct_calls":actual,"probe_direct_calls":probe,
            "dimensions_quad":[domain.rect.width,domain.rect.height],"site_order":["R","G1","G2","B"],
            "input_captures":record.inputs.len(),"inputs":record.inputs.values().collect::<Vec<_>>(),
            "collapsed_captures":record.collapsed.len(),"collapsed":record.collapsed,
            "hash_encoding":"ordered IEEE754 f32 bits, little endian; labels/dimensions in receipt"}))
    }
}
mod controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/native-direct-planes/bridge-controls.rs"));
}
