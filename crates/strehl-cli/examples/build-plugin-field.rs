//! BUILD-PLUGIN arm 1 — **falsify `strehl-plugin`'s bit-identity claim on real
//! frames**, before anything is built on top of it.
//!
//! Run:
//! ```text
//! cargo run --release -p strehl-cli --example build-plugin-field -- <stack-dir> [frames]
//! ```
//!
//! **Reads only.** Nothing is written anywhere.
//!
//! # The claim under test
//!
//! `strehl-plugin/src/field.rs` says its pipeline is *"bit-identical to
//! [`strehl_core::focus::FocusField::compute`] followed by the merge's
//! regulariser"*. The crate pins that with two in-crate tests — but both run on
//! **synthetic** 97x71 and 101x83 planes filled from its own Box-Muller source
//! and put on a 3000 +/- 400 DN pedestal. Neither is a real capture, neither is
//! at the shipped plane geometry, and neither uses a profile-derived noise
//! model. AGENTS rule 34: a plant that supplies its own constants cannot detect
//! those constants being wrong.
//!
//! So this runs the same comparison on **real decoded frames**, at the sensor's
//! real active-area geometry, through `profile::noise_model_for` at the frame's
//! own ISO — the exact objects `merge_cmd.rs` hands to `FocusField::compute`.
//! It reports the number of differing samples and the largest absolute
//! difference; anything other than `0 / 0` refutes the claim.
//!
//! # The second arm: does the SHIPPED default survive the environment override?
//!
//! `FocusField::compute` resolves its radius through
//! [`strehl_core::focus::window_radius`], which honours `STREHL_WINDOW_RADIUS`.
//! `Tenengrad::shipped()` reads the `WINDOW_RADIUS` **constant**. Under an
//! override the two are different operators, so the identity is conditional on
//! an environment variable neither crate mentions. Arm 2 reports the radius
//! actually in force beside the constant so the condition is visible rather
//! than assumed.
//!
//! # The third arm: the host measures, and the measurements differ
//!
//! Calibrates every reference operator through the **shipping binary's own**
//! dependency graph — not through `strehl-plugin`'s example, which proves
//! nothing about `strehl stack`. Prints each operator's host-measured response
//! SD, its `k` against the compiled-in constant, and the tolerance a `--gate 4`
//! would produce under it.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use anyhow::{Context, Result, bail};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::focus::{FocusField, WINDOW_RADIUS, window_radius};
use strehl_core::merge::{DEFAULT_GATE, FOCUS_NOISE_SD, REGULARISER_RADIUS, regularise};
use strehl_core::noise::NoiseModel;
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;
use strehl_plugin::reference::{Tenengrad, survey};
use strehl_plugin::{CalibrationPlan, FieldConfig, FieldWorkspace, FocusMeasure, Registry};

fn load(path: &Path) -> Result<(Vec<f32>, PlaneGeometry, NoiseModel, Option<f32>)> {
    let frame = strehl_raw::decode(path).with_context(|| format!("decoding {}", path.display()))?;
    let geom = frame.geometry();
    let levels = frame.levels;
    let noise = profile::noise_model_for(&frame.camera, frame.iso, levels);
    let mut luma = vec![0.0f32; geom.pixels()];
    let mut clipped = vec![false; geom.pixels()];
    green_luma_with_clip(&frame, levels.black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
    Ok((luma, geom, noise, frame.iso))
}

/// Differing samples and the largest absolute difference between two fields.
fn diff(a: &[f32], b: &[f32]) -> (usize, f32) {
    let mut n = 0usize;
    let mut worst = 0.0f32;
    for (x, y) in a.iter().zip(b) {
        if x.to_bits() != y.to_bits() {
            n += 1;
            let d = (x - y).abs();
            if d > worst {
                worst = d;
            }
        }
    }
    (n, worst)
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        bail!("usage: build-plugin-field <stack-dir> [frames]");
    }
    let dir = PathBuf::from(&args[1]);
    let want: usize = args.get(2).map_or(Ok(2), |s| s.parse())?;

    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.is_file())
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .is_some_and(|e| e.eq_ignore_ascii_case("arw"))
        })
        .collect();
    paths.sort();
    paths.truncate(want);
    if paths.is_empty() {
        bail!("no .ARW frames under {}", dir.display());
    }

    println!("== arm 2: which operator is `the shipped one` right now ==");
    println!("  WINDOW_RADIUS constant  : {WINDOW_RADIUS}");
    println!("  window_radius() in force: {}", window_radius());
    println!(
        "  STREHL_WINDOW_RADIUS    : {}",
        std::env::var(strehl_core::focus::WINDOW_RADIUS_ENV).unwrap_or_else(|_| "unset".into())
    );
    println!(
        "  Tenengrad::shipped().id(): {}\n",
        Tenengrad::shipped().id()
    );

    println!("== arm 1: bit-identity on REAL frames ==");
    println!("  regulariser radius {REGULARISER_RADIUS}, compiled-in FOCUS_NOISE_SD {FOCUS_NOISE_SD:e}");
    let mut all_identical = true;
    for p in &paths {
        let (luma, geom, noise, iso) = load(p)?;

        // The host, exactly as `merge_cmd::Ctx::field_for` runs it.
        let mut want_field = FocusField::new(geom);
        want_field.compute(&luma, &noise);
        let bare_want = want_field.values().to_vec();
        let mut scratch = vec![0.0f32; geom.pixels()];
        let mut reg_want = vec![0.0f32; geom.pixels()];
        regularise(&bare_want, geom, &mut scratch, &mut reg_want);

        // The plugin pipeline, at the radius actually in force.
        let op = Tenengrad::at_radius(window_radius());
        let mut ws = FieldWorkspace::new(geom);
        let bare_got = ws.run(&op, FieldConfig::BARE, &luma, &noise).to_vec();
        let reg_got = ws.run(&op, FieldConfig::SHIPPED, &luma, &noise).to_vec();

        let (nb, wb) = diff(&bare_got, &bare_want);
        let (nr, wr) = diff(&reg_got, &reg_want);
        all_identical &= nb == 0 && nr == 0;
        println!(
            "  {:<14} {}x{} ISO {:<5} bare: {} differing / {} (worst {:e})   regularised: {} differing (worst {:e})",
            p.file_name().unwrap_or_default().to_string_lossy(),
            geom.width,
            geom.height,
            iso.map_or_else(|| "?".to_string(), |v| format!("{v:.0}")),
            nb,
            geom.pixels(),
            wb,
            nr,
            wr
        );
    }
    println!(
        "  VERDICT: the field.rs bit-identity claim is {} on real frames\n",
        if all_identical {
            "UPHELD"
        } else {
            "REFUTED"
        }
    );

    println!("== arm 3: the host measures every reference operator ==");
    let plan = CalibrationPlan::host_default();
    let mut reg = Registry::new(FieldConfig::SHIPPED, plan)?;
    for op in survey(WINDOW_RADIUS) {
        reg.register(Arc::from(op))?;
    }
    println!(
        "  {:<24}{:>14}{:>13}{:>9}{:>14}",
        "operator", "measured sd", "sem", "k", "tol@gate 4"
    );
    for id in reg.ids() {
        let e = reg.get(id).expect("just listed");
        let c = e.calibration();
        println!(
            "  {:<24}{:>14e}{:>13.2e}{:>9.4}{:>14.6}",
            id,
            c.response_sd(),
            c.sem(),
            c.k_against_host_constant(),
            e.unnormalised_tolerance(DEFAULT_GATE)
        );
    }
    println!(
        "  host constant {FOCUS_NOISE_SD:e} gives tol@gate 4 = {:.6}",
        DEFAULT_GATE * std::f32::consts::SQRT_2 * FOCUS_NOISE_SD
    );

    if !all_identical {
        bail!("bit-identity REFUTED on real frames");
    }
    Ok(())
}
