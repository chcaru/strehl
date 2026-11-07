//! Run the desktop's adaptive (spatial) analysis headlessly and write the
//! resulting development recipe, for `strehl develop --recipe`.
//!
//! usage: iq-adaptive-recipe MASTER.tif OUT.json [key=value ...]
//! keys: balance local_contrast color shadow_protection highlight_compression
//!       presence glint_compression (all 0..1; unset keys take the defaults).
use strehl_edit::{AdaptiveIntent, AdaptiveParameters, DevelopmentRecipe, analyze_adaptive_with_parameters, load_tiff};

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let image = load_tiff(std::path::Path::new(&a[1])).expect("load master");
    let mut p = AdaptiveParameters::default();
    for kv in &a[3..] {
        let (k, v) = kv.split_once('=').expect("key=value");
        let v: f32 = v.parse().expect("number");
        match k {
            "balance" => p.balance = v,
            "local_contrast" => p.local_contrast = v,
            "color" => p.color = v,
            "shadow_protection" => p.shadow_protection = v,
            "highlight_compression" => p.highlight_compression = v,
            "presence" => p.presence = v,
            "glint_compression" => p.glint_compression = v,
            other => panic!("unknown key {other}"),
        }
    }
    let s = analyze_adaptive_with_parameters(&image, &DevelopmentRecipe::default(), None, AdaptiveIntent::Balance, p)
        .expect("analyze");
    for c in &s.changes {
        eprintln!("{}: {} -> {}", c.control, c.before, c.after);
    }
    std::fs::write(&a[2], serde_json::to_string_pretty(&s.suggested).unwrap()).unwrap();
}
