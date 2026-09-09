// Independent fixed source-transfer controls. Root executes; this author does not.
use serde_json::{json, Value};
use std::collections::BTreeSet;

fn number(row: &Value, key: &str) -> f64 {
    let value = row[key].as_f64().unwrap_or_else(|| panic!("missing numeric {key}"));
    assert!(value.is_finite(), "nonfinite {key}");
    value
}
fn label<'a>(row: &'a Value, key: &str) -> &'a str {
    row[key].as_str().unwrap_or_else(|| panic!("missing label {key}"))
}

// Paired observations mean the SAME source noise draw in corrected/off arms.
// The subject is Var(corrected)-Var(off), not Var(corrected-off).
pub(super) fn decide(rows: &[Value]) -> Value {
    assert_eq!(rows.len(), 32, "fixed 8 cells x 2 bands x 2 regions");
    let mut seen = BTreeSet::new();
    let mut failures = Vec::new();
    let mut unresolved = Vec::new();
    let mut checked = Vec::new();
    let mut wrong_rejections = 0;
    for row in rows {
        let mapping = label(row, "mapping");
        let field = label(row, "field");
        let component = label(row, "component");
        let region = label(row, "region");
        let band = row["band"].as_u64().unwrap();
        assert!(["identity", "warp"].contains(&mapping));
        assert!(["flat", "textured"].contains(&field));
        assert!(["shot", "read"].contains(&component));
        assert!(["core", "adjacent"].contains(&region));
        assert!(band <= 1);
        assert_eq!(row["n"].as_u64(), Some(64));
        let key = format!("{mapping}/{field}/{component}/band-{band}/{region}");
        assert!(seen.insert(key.clone()), "duplicate {key}");
        let off = number(row, "measured_off");
        let corrected = number(row, "measured_corrected");
        let delta = number(row, "delta");
        let se = number(row, "se");
        assert!(off >= 0.0 && corrected >= 0.0 && se >= 0.0);
        assert!((delta - (corrected - off)).abs() <= 1e-8 * (1.0 + off + corrected),
            "reported delta is not difference of variances: {key}");
        let pred_off = number(row, "predicted_off");
        let pred_corrected = number(row, "predicted_corrected");
        let pred_wrong = number(row, "predicted_wrong");
        assert!(pred_off >= 0.0 && pred_corrected >= 0.0 && pred_wrong >= 0.0);
        let prediction = pred_corrected - pred_off;
        let wrong = pred_wrong - pred_off;
        let tau = (0.10 * delta.abs()).max(3.0 * se).max(0.002 * off);
        let error = (prediction - delta).abs();
        let wrong_error = (wrong - delta).abs();
        if region == "core" && !(delta > 0.0 && 3.0 * se <= 0.25 * delta) {
            unresolved.push(format!("{key}: positive increment not resolved to fixed precision"));
        }
        if error > tau { failures.push(format!("{key}: local-delta prediction outside tolerance")); }
        let wrong_required = mapping == "identity" && field == "flat" && region == "core";
        if wrong_required {
            if wrong_error > tau { wrong_rejections += 1; }
            else { unresolved.push(format!("{key}: nominated wrong factor was not rejected")); }
        }
        checked.push(json!({"key":key,"delta":delta,"se":se,"tau":tau,
            "prediction_delta":prediction,"absolute_error":error,
            "wrong_delta":wrong,"wrong_absolute_error":wrong_error,
            "wrong_rejection_required":wrong_required,"baseline_floor_bias":pred_off-off}));
    }
    assert_eq!(seen.len(), 32);
    let status = if !unresolved.is_empty() { "INCONCLUSIVE" }
        else if !failures.is_empty() { "REJECT" } else { "PASS" };
    json!({"status":status,"rows":checked,"candidate_failures":failures,
        "unresolved_power":unresolved,"required_wrong_rejections":4,
        "observed_wrong_rejections":wrong_rejections,
        "scope":"fixed software transfer only; no calibration, native quality or default claim"})
}

fn variance(values: &[f32], omit: Option<usize>) -> f64 {
    let kept: Vec<f64> = values.iter().enumerate().filter(|(i,_)| Some(*i) != omit)
        .map(|(_,v)| f64::from(*v)).collect();
    let mean = kept.iter().sum::<f64>() / kept.len() as f64;
    kept.iter().map(|v| (v-mean)*(v-mean)).sum::<f64>() / (kept.len()-1) as f64
}
fn scalar_oracle(off: &[f32], corrected: &[f32]) -> (f64,f64,f64,f64) {
    assert_eq!(off.len(), corrected.len());
    let n = off.len();
    let a = variance(off,None);
    let b = variance(corrected,None);
    let leave_one: Vec<f64> = (0..n).map(|i|
        variance(corrected,Some(i)) - variance(off,Some(i))).collect();
    let mean = leave_one.iter().sum::<f64>() / n as f64;
    let se = (((n-1) as f64 / n as f64) * leave_one.iter()
        .map(|v| (v-mean)*(v-mean)).sum::<f64>()).sqrt();
    (a,b,b-a,se)
}
fn close(actual: f64, expected: f64, what: &str) {
    assert!((actual-expected).abs() <= 2e-5*(1.0+expected.abs()),
        "{what}: actual={actual} expected={expected}");
}
fn positive_rows() -> Vec<Value> {
    let mut rows = Vec::new();
    for mapping in ["identity","warp"] { for field in ["flat","textured"] {
        for component in ["shot","read"] { for band in 0..2 { for region in ["core","adjacent"] {
            let delta = if region == "core" { 10.0 } else { 0.0 };
            rows.push(json!({"mapping":mapping,"field":field,"component":component,
                "band":band,"region":region,"n":64,"measured_off":100.0,
                "measured_corrected":100.0+delta,"delta":delta,"se":0.01,
                "predicted_off":105.0,"predicted_corrected":105.0+delta,
                "predicted_wrong":105.0+2.0*delta}));
        }}}}
    }
    rows
}

// `measure` MUST adapt the actual ensemble variance/jackknife path to one site.
// Independent literal sums below are an oracle, not an alternate image kernel.
pub(super) fn literal_controls<F>(measure: F) -> Value
where F: Fn(&[f32], &[f32]) -> (f64,f64,f64,f64) {
    let off: Vec<f32> = (0..64).map(|i| ((i*37)%29) as f32 - 14.0).collect();
    let mut cases = Vec::new();
    for (name, corrected) in [
        ("unity",off.clone()),
        ("pure-pedestal",off.iter().map(|v| v+128.0).collect()),
        ("gain-and-pedestal",off.iter().map(|v| 1.0625*v+128.0).collect()),
        ("nonlinear-paired",off.iter().enumerate().map(|(i,v)|
            1.0625*v+((i*11)%7) as f32*0.125+128.0).collect()),
    ] {
        let actual = measure(&off,&corrected);
        let expected = scalar_oracle(&off,&corrected);
        for (a,e,term) in [(actual.0,expected.0,"off"),(actual.1,expected.1,"corrected"),
            (actual.2,expected.2,"delta"),(actual.3,expected.3,"jackknife SE")] {
            close(a,e,&format!("{name}/{term}"));
        }
        if name == "unity" || name == "pure-pedestal" { close(actual.2,0.0,name); }
        if name == "gain-and-pedestal" {
            let difference: Vec<f32> = corrected.iter().zip(&off).map(|(c,u)| c-u).collect();
            let wrong = variance(&difference,None);
            assert!(actual.2 > 20.0*wrong, "paired-difference destroyer lacks power");
        }
        cases.push(json!({"name":name,"off":actual.0,"corrected":actual.1,
            "delta":actual.2,"se":actual.3}));
    }
    let stationary = vec![3500.0_f32;64];
    let moved = vec![3704.5_f32;64];
    let no_noise = measure(&stationary,&moved);
    close(no_noise.0,0.0,"noiseless off");
    close(no_noise.1,0.0,"noiseless corrected");
    close(no_noise.2,0.0,"noiseless delta");
    close(no_noise.3,0.0,"noiseless SE");
    let good = positive_rows();
    assert_eq!(decide(&good)["status"],"PASS");
    // Shared baseline bias (+5 here) must not masquerade as transfer error.
    let mut bad = good.clone();
    bad[0]["predicted_corrected"] = json!(125.0);
    assert_eq!(decide(&bad)["status"],"REJECT");
    let mut weak = good.clone();
    weak[0]["se"] = json!(1.0);
    assert_eq!(decide(&weak)["status"],"INCONCLUSIVE");
    let mut insensitive = good.clone();
    insensitive[0]["predicted_wrong"] = insensitive[0]["predicted_corrected"].clone();
    assert_eq!(decide(&insensitive)["status"],"INCONCLUSIVE");
    let mut absent = good.clone();
    absent[0]["measured_corrected"] = json!(100.0);
    absent[0]["delta"] = json!(0.0);
    absent[0]["predicted_corrected"] = json!(105.0);
    assert_eq!(decide(&absent)["status"],"INCONCLUSIVE");
    json!({"status":"PASS","scalar_cases":cases,"noiseless_power":0.0,
        "live_destroyers":["variance of corrected-minus-off", "wrong delta", "uncertain increment",
            "unrejected wrong factor", "zero core response"],
        "decision_rows":32,"ensemble_observations":64})
}
