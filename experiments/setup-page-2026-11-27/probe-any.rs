//! What the linked decoder reports for any maker's RAW file, before Strehl's
//! own gates (`.arw` only, RGGB only). Read-only.
//!
//! `cargo run --release -p strehl-raw --example setup-probe-any -- FILE...`
//!
//! Per file: maker and model as the decoder cleans them, the CFA pattern at
//! the buffer origin and at the active-area origin, sizes, every black and
//! white level entry, white balance, colour matrices, and the data's own
//! range (minimum, the top value, how many samples sit on it, percentiles).
use rawler::decoders::RawDecodeParams;
use rawler::rawsource::RawSource;
use serde_json::{Value, json};
use std::path::Path;

fn probe(path: &Path) -> Value {
    let source = match RawSource::new(path) {
        Ok(s) => s,
        Err(e) => return json!({"file": path.display().to_string(), "error": format!("open: {e}")}),
    };
    let params = RawDecodeParams::default();
    let img = match rawler::decode(&source, &params) {
        Ok(i) => i,
        Err(e) => {
            return json!({"file": path.display().to_string(), "error": format!("decode: {e:?}")});
        }
    };
    let meta = rawler::get_decoder(&source)
        .and_then(|d| d.raw_metadata(&source, &params))
        .ok();
    let iso = meta
        .as_ref()
        .and_then(|m| m.exif.iso_speed_ratings.map(u32::from).or(m.exif.iso_speed));
    let lens = meta.as_ref().and_then(|m| m.exif.lens_model.clone());
    let fnumber = meta
        .as_ref()
        .and_then(|m| m.exif.fnumber.map(|r| r.n as f64 / r.d as f64));
    let exposure = meta
        .as_ref()
        .and_then(|m| m.exif.exposure_time.map(|r| r.n as f64 / r.d as f64));
    let black: Vec<f64> = img
        .blacklevel
        .levels
        .iter()
        .map(|r| r.n as f64 / r.d as f64)
        .collect();
    let white: Vec<u32> = img.whitelevel.0.clone();
    let pattern = img.camera.cfa.name.clone();
    let (w, h, cpp) = (img.width, img.height, img.cpp);
    let active = img.active_area.map(|r| [r.p.x, r.p.y, r.d.w, r.d.h]);
    let crop = img.crop_area.map(|r| [r.p.x, r.p.y, r.d.w, r.d.h]);
    let mut out = json!({
        "file": path.file_name().unwrap().to_string_lossy(),
        "make": img.clean_make, "model": img.clean_model,
        "raw_make": img.make, "raw_model": img.model,
        "cfa_at_buffer_origin": pattern,
        "width": w, "height": h, "cpp": cpp, "bps": img.bps,
        "active_area": active, "crop_area": crop,
        "black": black, "white": white,
        "wb": img.wb_coeffs,
        "matrices": img.color_matrix.keys().map(|k| format!("{k:?}")).collect::<Vec<_>>(),
        "iso": iso, "lens": lens, "fnumber": fnumber, "exposure_s": exposure,
    });
    // The pattern at the active-area origin: shift the 2x2 name by the offset.
    if let (Some(a), true) = (active, pattern.len() == 4) {
        let p: Vec<char> = pattern.chars().collect();
        let at = |x: usize, y: usize| p[(y % 2) * 2 + (x % 2)];
        let shifted: String = [(0, 0), (1, 0), (0, 1), (1, 1)]
            .iter()
            .map(|(dx, dy)| at(a[0] + dx, a[1] + dy))
            .collect();
        out["cfa_at_active_origin"] = json!(shifted);
    }
    match &img.data {
        rawler::RawImageData::Integer(d) => {
            let mut hist = vec![0u64; 65536];
            for &v in d {
                hist[v as usize] += 1;
            }
            let n = d.len() as u64;
            let min = hist.iter().position(|&c| c > 0).unwrap_or(0);
            let max = hist.iter().rposition(|&c| c > 0).unwrap_or(0);
            let pct = |q: f64| {
                let want = (n as f64 * q) as u64;
                let mut acc = 0u64;
                for (v, &c) in hist.iter().enumerate() {
                    acc += c;
                    if acc >= want {
                        return v;
                    }
                }
                65535
            };
            // Codes in use between the 1st and 99th percentile: a comb (lossy
            // curve, a scaled 12-bit file) shows as a share well under 1.
            let (lo, hi) = (pct(0.01), pct(0.99));
            let used = hist[lo..=hi].iter().filter(|&&c| c > 0).count();
            out["data"] = json!({
                "samples": n, "min": min, "max": max, "at_max": hist[max],
                "p0.1": pct(0.001), "p50": pct(0.5), "p99.9": pct(0.999),
                "codes_used_p1_p99": used as f64 / ((hi - lo + 1) as f64),
            });
        }
        rawler::RawImageData::Float(_) => {
            out["data"] = json!("float");
        }
    }
    out
}

fn main() {
    let mut all = Vec::new();
    for a in std::env::args().skip(1) {
        let v = probe(Path::new(&a));
        println!("{}", serde_json::to_string(&v).unwrap());
        all.push(v);
    }
    eprintln!("{} files", all.len());
}
