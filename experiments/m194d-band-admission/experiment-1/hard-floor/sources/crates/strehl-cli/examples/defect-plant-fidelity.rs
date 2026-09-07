//! P59 -- does the corrector restore what was there, or paint something new?
//!
//! WHAT THE ORCHESTRATOR ASKED, AND WHY THE QUESTION HAD TO BE RE-AIMED
//! ====================================================================
//! The brief said: *"The inpainting must be shown not to invent detail. It
//! gathers from other frames' samples, and those frames are warped. A dust
//! correction that reconstructs plausible texture where there was none is a
//! worse defect than the dust."*
//!
//! That describes a corrector this project does not have. `DefectMap::apply`
//! reads `samples[idx]` and writes `samples[idx]` -- the same index. There is
//! no neighbour term, no interpolation, no inter-frame gather, no patch
//! synthesis. Dust is undone as `restored = (v - black) * gain + black` and a
//! hot pixel as `v - excess_e * gain_dn_per_e`. Both are **per-sample affine
//! maps on the sample's own value.**
//!
//! A per-sample affine map has no source of spatial-frequency content, so it
//! cannot synthesise texture in the sense the brief feared. Stating that is an
//! argument, not a measurement, and this project does not accept arguments --
//! so arm D measures it. But the argument does tell us where to point the
//! instrument, and it is **not** where the brief pointed it.
//!
//! WHERE THE REAL INVENTION RISK LIVES
//! -----------------------------------
//! A gain applied over a disc, with the wrong amplitude, leaves a **disc-shaped
//! step** -- a correction ring where the image previously had nothing. That is
//! genuinely invented structure, it is mid-scale and circular, and it is
//! exactly the artifact a reviewer of a print-quality claim finds in five
//! minutes. It is also a live risk rather than a hypothetical one: SS13.6
//! measured that dust depth is governed by `N(1+m)` and not by the sensor, so a
//! map storing a fixed depth can be wrong by up to **4.3x**. The corrector is
//! therefore expected to be handed the wrong gain in normal use.
//!
//! So: not "does it hallucinate texture" (structurally impossible), but "what
//! does it leave behind when its amplitude is wrong" (structurally guaranteed).
//!
//! CERTIFYING THE SITE CLEAN, WHICH IS A REQUIREMENT AND NOT A FORMALITY
//! ---------------------------------------------------------------------
//! The orchestrator's condition was: plant where the truth is genuinely clean,
//! "or the residual is measured against a reference that already contains what
//! you are testing for."
//!
//! Cleanliness cannot be certified on the subject frame. On a subject, a dark
//! disc and a dark subject feature are the same measurement -- that is the
//! whole reason the flats were shot. So cleanliness is certified **on the
//! flats**, where P11 measured the high-pass separating dust from illumination
//! by **264.9x** (3.6194% -> 0.0137%), and then used on the subject. This is
//! valid for exactly one reason, and it is the reason the entire defect map is
//! valid: **dust is a property of the sensor, not of the scene.** A site clean
//! in sensor coordinates on the flats is clean in sensor coordinates on any
//! capture.
//!
//! The search for a clean site can return **nothing**. If no candidate clears
//! the floors, the run REFUSES and reports no fidelity number at all. A search
//! that cannot fail returns its least-bad candidate and calls it a find.
//!
//! THE ARMS, AND WHY EACH ONE IS PRESENT
//! -------------------------------------
//! * **A -- CHARGE (the RED arm).** Plant, do not correct. The residual must be
//!   LARGE. Without this the suite cannot tell a working corrector from a
//!   metric that reads zero no matter what. A statistic that never charges is
//!   the failure this project has shipped repeatedly.
//!
//! * **B -- FIDELITY (the improvement arm).** Plant, correct with the exact
//!   inverse gain. The residual must collapse to **quantisation only**. Because
//!   the plant is the algebraic inverse of the correction, the expected
//!   residual is not "small" -- it is predictable to within rounding, so any
//!   excess is a real defect rather than a judgement call. Measured against A,
//!   this is the signed improvement arm: the number must move the right way,
//!   which is what separates a blind statistic from a perverse one.
//!
//! * **C -- CONTAINMENT (the null).** Correct with a map naming site X, then
//!   measure at a distant clean site Y. Y must be **bit-identical**. This is
//!   the "does it repaint everywhere" test: a corrector that improves a planted
//!   mote by touching the whole frame would pass A and B and destroy the image.
//!   The requirement is exact equality, not a tolerance, because the corrector
//!   either addresses the named samples or it does not.
//!
//! * **D -- INVENTION.** High-frequency energy inside the corrected disc,
//!   corrected against truth. If the corrector adds spatial structure that the
//!   truth does not contain, this rises. This is the brief's original question,
//!   measured rather than dismissed on the strength of the code reading.
//!
//! * **E -- PERVERSE GUARD.** Plant, then correct with a gain **2x too strong**
//!   -- the realistic failure given SS13.6's 4.3x depth error. The residual must
//!   be WORSE than B. A metric that scores a wrong-amplitude correction at or
//!   better than a right one is perverse, and a suite of degradations alone
//!   cannot detect that. This arm is why the ring statistic exists.
//!
//! WHAT THIS FILE MAY NOT CONCLUDE
//! -------------------------------
//! It measures fidelity against a reference **for a planted mote at a certified
//! clean site**. It says nothing about the two real motes, for which no clean
//! reference exists and none can be constructed. Real-mote improvement is a
//! separate question answered against the print gate, and the second does not
//! inherit the first.

use std::path::{Path, PathBuf};

use strehl_core::defect_map::{Correction, DefectMap, DustQuad, HotFloor};

/// Photosites per quad side. The CFA is a 2x2 Bayer tile and `DustQuad`
/// coordinates name quads, so every quad the map touches is 2x2 photosites.
const QUAD: usize = 2;

/// Planted mote geometry, in QUADS, taken from the real profile in SS3.2: the
/// mapped mote is ~306 um across with a ~51 um edge, and the sensor is
/// 5.10 um per photosite (10.2 um per quad). 306/10.2 = 30 quads across, so
/// radius 15; 51/10.2 = 5 quads of edge.
const PLANT_R: usize = 15;
const PLANT_EDGE: usize = 5;

/// Planted attenuation: the disc transmits this fraction of the light. -4% is
/// the same depth the CPL discriminator planted in SS18, chosen there because
/// it is the depth at which a real mote was detectable, so it is a defect of
/// realistic size rather than a convenient one.
const PLANT_TRANSMISSION: f32 = 0.96;

/// How far a candidate site must sit from any mapped mote, in quads. The real
/// motes are ~15 quads in radius, so 120 is eight radii -- far enough that the
/// planted disc and its measurement annulus cannot overlap a real defect.
const CLEAN_CLEARANCE: usize = 120;

/// A candidate site's own high-pass residual on the flats must be below this
/// fraction to be called clean. The census seed bar is 0.50% (SS3.2 P12, set
/// above the noisiest capture's rms of 0.4882%); this is a quarter of that,
/// because a site used as a fidelity reference must be quieter than the
/// threshold at which the pipeline is willing to call something a defect.
/// Attenuation depth used by the commissioning arms only. Chosen to sit near
/// the real motes' measured depth so the arms exercise the statistic in the
/// regime it will actually be used in, not at an amplitude that would make any
/// statistic look decisive.
const COMMISSION_DEPTH: f32 = 0.04;

const CLEAN_RESIDUAL_MAX: f32 = 0.00125;

/// The measurement annulus must carry real signal. A site sitting in crushed
/// shadow or against clipped highlight cannot test a multiplicative correction:
/// at the black floor every gain returns black, and at white every gain clips.
const SIGNAL_MIN_FRAC: f32 = 0.08;
const SIGNAL_MAX_FRAC: f32 = 0.85;

/// Border to keep the whole measurement region away from the frame edge. SS18
/// paid for this constant: a mote 38 quads from the edge fell inside the band
/// the interior null excluded, and the null was optimistic by 2.1x.
const BORDER: usize = 80;

/// Radius, in quads, of the region residuals are measured over. Larger than
/// `PLANT_R` so the corrected disc AND a ring of untouched surround are both in
/// frame -- a footprint step is only visible if both sides of it are measured.
const MEASURE_R: usize = 25;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let subject = args
        .first()
        .cloned()
        .unwrap_or_else(|| r"D:\personal\macro\coffee-bubbles".to_string());
    let flats = args
        .get(1)
        .cloned()
        .unwrap_or_else(|| r"D:\personal\macro\flat-fields\flat-fields".to_string());
    let flat_limit: usize = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(120);

    println!("{}", "=".repeat(72));
    println!("P59 -- planted-mote fidelity, against a reference only this run holds");
    println!("{}", "=".repeat(72));
    println!("subject : {subject}");
    println!("flats   : {flats}  (first {flat_limit} decodable, for cleanliness only)");
    println!();
    println!("The corrector under test is a PER-SAMPLE AFFINE MAP -- apply() reads");
    println!("and writes the same index, with no neighbour or inter-frame term.");
    println!("So the question is not whether it hallucinates texture. It is what");
    println!("it leaves behind when its amplitude is wrong.");
    println!();

    // ---- the truth frame -------------------------------------------------
    let Some(subject_path) = first_raw(Path::new(&subject)) else {
        println!("REFUSED: no decodable raw in {subject}");
        std::process::exit(2);
    };
    let f = match strehl_raw::decode(&subject_path) {
        Ok(f) => f,
        Err(e) => {
            println!("REFUSED: {} did not decode: {e}", subject_path.display());
            std::process::exit(2);
        }
    };
    let active = (f.active.x, f.active.y, f.active.width, f.active.height);
    let (ax, ay, aw, ah) = active;
    let (black, white) = (f.levels.black, f.levels.white);
    let range = white - black;
    let (qw, qh) = (aw / QUAD, ah / QUAD);
    println!("truth frame  : {}", subject_path.display());
    println!("active       : {aw}x{ah} at ({ax},{ay})  ->  quad grid {qw}x{qh}");
    println!("levels       : black {black} white {white} range {range}");
    println!();

    // ---- certify a clean site, ON THE FLATS ------------------------------
    println!("-- certifying a clean site on the flats (dust is a sensor property) --");
    let fa = accumulate_flats(Path::new(&flats), flat_limit);
    println!("flats        : {}", fa.describe());
    if !fa.partitions() {
        println!("REFUSED: the flat partition does not sum; the census cannot be read");
        std::process::exit(2);
    }
    if fa.used == 0 {
        println!();
        println!("REFUSED: no flat field accumulated, so cleanliness cannot be certified.");
        println!("  Note WHICH count is non-zero above: 0 examined means the directory");
        println!("  held no raws, which is a different failure from every frame being");
        println!("  correctly rejected. Nothing is planted and no number is reported.");
        std::process::exit(2);
    }
    let (field, fqw, fqh) = (fa.field.clone(), fa.qw, fa.qh);

    // --- can a quad index transfer between these two geometries? ----------
    //
    // The first version of this gate refused outright whenever the widths
    // differed, and it fired: the flats decode 3520x2344 quads while this
    // subject decodes 3516x2344. Refusing was the safe reflex but it was not
    // an ANSWER, and the answer turned out to matter -- 11 of the 26 corpus
    // stacks are the wide body, so a rule that cannot cross the two widths
    // cannot test the corrector on 42% of the corpus.
    //
    // P61 measured it instead of guessing. Both bodies report their active
    // area at origin (0,0), so photosite (2*px, 2*py) is the same physical
    // photosite in both; the extra 8 columns extend the RIGHT EDGE ONLY.
    // A quad index therefore transfers unchanged, provided the site lies
    // inside the narrower width. That proviso is the whole content of the
    // gate, so it is enforced below rather than asserted here.
    //
    // What is still refused, and must be: a differing origin (the transfer
    // would silently displace every index) and a differing height (nothing
    // was measured about vertical transfer, and an unmeasured direction is
    // not a safe one).
    if fa.ox != ax as usize || fa.oy != ay as usize {
        println!(
            "REFUSED: flat active origin ({},{}) != subject active origin ({ax},{ay}). \
             A quad index does not transfer across a shifted origin and the plant \
             would land somewhere other than the certified-clean site.",
            fa.ox, fa.oy
        );
        std::process::exit(2);
    }
    if fqh != qh {
        println!(
            "REFUSED: flat quad height {fqh} != subject quad height {qh}. P61 measured \
             the width relationship only; vertical transfer is unmeasured and an \
             unmeasured direction is not a safe one."
        );
        std::process::exit(2);
    }
    // Every index used from here on must be legal in BOTH grids.
    let share_w = fqw.min(qw);
    println!(
        "geometry     : flats {fqw}x{fqh} quads, subject {qw}x{qh} quads, shared origin ({ax},{ay})"
    );
    println!(
        "               -> indices transfer; search bounded to the shared width {share_w} \
         ({} quads dropped from the wider grid)",
        fqw.max(qw) - share_w
    );

    let motes = mapped_motes();
    println!("mapped motes : {} (clearance required: {CLEAN_CLEARANCE} quads)", motes.len());

    // --- commission the cleanliness statistic BEFORE certifying with it ----
    //
    // The single-mean high pass refused all 110,538 candidates at a best of
    // 0.607% against a 0.125% floor, with only 568 excluded by mote
    // clearance. A statistic that rejects every input is not a strict
    // statistic, it is an uncommissioned one. So the field is now split into
    // interleaved halves and only the reproducible residual is believed --
    // and that statistic is commissioned here, with a planted improvement
    // arm as well as a planted defect, before a single site is certified.
    if fa.used_a < 4 || fa.used_b < 4 {
        println!(
            "REFUSED: split halves too small (a={} b={}); the reproducibility \
             statistic cannot be commissioned and therefore cannot be used.",
            fa.used_a, fa.used_b
        );
        std::process::exit(2);
    }
    println!();
    println!("-- commissioning the cleanliness statistic (floor {:.5}%) --", CLEAN_RESIDUAL_MAX * 100.0);
    println!("halves       : a={} frames, b={} frames (interleaved, so cloud drift is shared)", fa.used_a, fa.used_b);
    let (ccx, ccy) = (share_w / 2, fqh / 2);
    let arms = commission_cleanliness(&fa, fqw, fqh, ccx, ccy, COMMISSION_DEPTH, PLANT_R);
    let mut arms_failed = 0usize;
    for a in &arms {
        println!(
            "  {:<38} {:>9.5}%   expect {:<12} {}",
            a.name,
            a.reading * 100.0,
            a.expected,
            if a.pass { "PASS" } else { "FAIL" }
        );
        if !a.pass {
            arms_failed += 1;
        }
    }
    if arms_failed > 0 {
        println!();
        println!(
            "REFUSED: {arms_failed} of {} commissioning arms failed. The cleanliness \
             statistic is not trusted, so no site is certified and no fidelity number \
             is reported.",
            arms.len()
        );
        std::process::exit(4);
    }
    println!("  all {} arms pass -- the statistic reads a planted defect, ignores a", arms.len());
    println!("  non-reproducible one, and scores a repair better than the defect.");
    println!();

    let hp_a = high_pass(&fa.field_a, fqw, fqh, 64);
    let hp_b = high_pass(&fa.field_b, fqw, fqh, 64);
    let rep = reproducible_hp(&hp_a, &hp_b);

    // The subject's own brightness, per quad. Built before the search so that
    // "sensor-clean" and "bright enough to test a multiplicative correction"
    // are one criterion rather than a criterion and a later surprise.
    let (subj_q, subj_qw, _subj_qh) =
        strehl_core::defect_map::quad_mean(&f.data, f.stride, active, black);
    let subj = SubjectSignal {
        q: subj_q,
        stride: subj_qw,
        range,
    };
    let (site_opt, sc) = find_clean_site(&rep, &field, fqw, share_w, fqh, &motes, &subj);
    println!("site search  : {}", sc.describe());
    if !sc.partitions() {
        println!("REFUSED: the site census does not sum; the search cannot be read");
        std::process::exit(3);
    }
    let Some(site) = site_opt else {
        println!();
        println!("REFUSED: no site cleared every floor. Nothing is planted and no");
        println!("  fidelity number is reported. A search that cannot fail returns");
        println!("  its least-bad candidate and calls it a find; this one failed.");
        match sc.best_eligible {
            Some(b) => println!(
                "  Best residual among geometrically-eligible candidates: {:.5}% \
                 against a floor of {:.5}%. The field is dirtier than the floor, \
                 which is a different failure from having no eligible candidate.",
                b * 100.0,
                CLEAN_RESIDUAL_MAX * 100.0
            ),
            None => println!(
                "  No candidate was ever geometrically eligible -- clearance {CLEAN_CLEARANCE} \
                 quads from {} mapped motes excluded the whole scan. The floor was never \
                 consulted, so nothing here says the sensor is dirty.",
                motes.len()
            ),
        }
        std::process::exit(3);
    };
    let (cx, cy) = site;
    println!("clean site   : quad ({cx},{cy})  disc response {:.5}%  (worst single quad in the same region {:.5}%, which is the PRNU the disc average cancels)",
        disc_response(&rep, fqw, cx, cy, PLANT_R) * 100.0,
        worst_quad_residual(&rep, fqw, cx, cy, MEASURE_R) * 100.0);

    // A second certified-clean site, far from the first, for the containment null.
    let (null_opt, nsc) = find_clean_site_excluding(&rep, &field, fqw, share_w, fqh, &motes, &subj, site);
    println!("null search  : {}", nsc.describe());
    let Some(nullsite) = null_opt else {
        println!("REFUSED: no second clean site for the containment null");
        std::process::exit(3);
    };
    println!("null site    : quad ({},{})  (containment arm measures here)", nullsite.0, nullsite.1);

    // ---- signal check at the site, on the SUBJECT ------------------------
    let truth = f.data.clone();
    let sig = mean_signal(&truth, f.stride, active, cx, cy, MEASURE_R, black);
    let sigfrac = sig / range;
    println!("site signal  : {sig:.1} DN = {:.3} of range", sigfrac);
    if !(SIGNAL_MIN_FRAC..=SIGNAL_MAX_FRAC).contains(&sigfrac) {
        println!();
        println!("REFUSED: site signal {sigfrac:.3} outside [{SIGNAL_MIN_FRAC}, {SIGNAL_MAX_FRAC}].");
        println!("  A multiplicative correction cannot be tested at the black floor");
        println!("  (every gain returns black) or against clipping (every gain clips).");
        std::process::exit(3);
    }
    println!();

    // ---- build the arms --------------------------------------------------
    let planted = plant(&truth, f.stride, active, cx, cy, black);
    let map_exact = mote_map(aw, ah, cx, cy, 1.0);
    let map_strong = mote_map(aw, ah, cx, cy, 2.0);

    // Arm F's mote does NOT obey the corrector's model. See `plant_gauss`.
    let planted_g = plant_gauss(&truth, f.stride, active, cx, cy, black);

    let mut a_samples = planted.clone();
    let mut b_samples = planted.clone();
    let mut e_samples = planted.clone();
    let mut c_samples = truth.clone();
    let f0_samples = planted_g.clone();
    let mut f_samples = planted_g.clone();

    let corr = Correction { hot: false, dust: true };
    // `gain_dn_per_e` converts a hot site's stored electron excess to DN. The
    // hot arm is off here, so no code path reads it; passing 1.0 is not a
    // calibration choice, it is an argument to a branch that does not run.
    let g = 1.0;

    let rb = map_exact
        .apply(&mut b_samples, f.stride, active, black, white, g, corr, HotFloor::CENSUS)
        .expect("arm B correction");
    let re = map_strong
        .apply(&mut e_samples, f.stride, active, black, white, g, corr, HotFloor::CENSUS)
        .expect("arm E correction");
    // Arm C applies the SAME map, naming site (cx, cy), to an unplanted frame,
    // then measures at the distant null site. The map is not the variable here;
    // the measurement location is.
    let rc = map_exact
        .apply(&mut c_samples, f.stride, active, black, white, g, corr, HotFloor::CENSUS)
        .expect("arm C correction");
    let rf = map_exact
        .apply(&mut f_samples, f.stride, active, black, white, g, corr, HotFloor::CENSUS)
        .expect("arm F correction");
    let _ = &mut a_samples; // arm A is deliberately uncorrected.

    println!("-- corrector reports (partitioned; the counts must sum) --");
    for (name, r) in [
        ("B exact", &rb),
        ("E 2x-strong", &re),
        ("C containment", &rc),
        ("F mismatch", &rf),
    ] {
        let (sums, _) = r.check_partition();
        println!(
            "  {name:<14} examined {} = corrected {} + no-change {} + clipped {} + outside {}  [{}]",
            r.dust_examined, r.dust_corrected, r.dust_no_change, r.dust_clipped, r.dust_outside,
            if sums { "sums" } else { "DOES NOT SUM" }
        );
        if !sums {
            println!("REFUSED: a corrector report that does not partition cannot be read");
            std::process::exit(4);
        }
    }
    println!();

    // ---- measure ---------------------------------------------------------
    let a_res = rms(&a_samples, &truth, f.stride, active, cx, cy, MEASURE_R);
    let b_res = rms(&b_samples, &truth, f.stride, active, cx, cy, MEASURE_R);
    let e_res = rms(&e_samples, &truth, f.stride, active, cx, cy, MEASURE_R);
    let c_moved = count_moved(&c_samples, &truth, f.stride, active, nullsite.0, nullsite.1, MEASURE_R);

    let a_ring = ring_step(&a_samples, &truth, f.stride, active, cx, cy, black);
    let b_ring = ring_step(&b_samples, &truth, f.stride, active, cx, cy, black);
    let e_ring = ring_step(&e_samples, &truth, f.stride, active, cx, cy, black);
    let f0_res = rms(&f0_samples, &truth, f.stride, active, cx, cy, MEASURE_R);
    let f_res = rms(&f_samples, &truth, f.stride, active, cx, cy, MEASURE_R);
    let f0_ring = ring_step(&f0_samples, &truth, f.stride, active, cx, cy, black);
    let f_ring = ring_step(&f_samples, &truth, f.stride, active, cx, cy, black);

    let t_hf = hf_energy(&truth, f.stride, active, cx, cy, PLANT_R);
    let b_hf = hf_energy(&b_samples, f.stride, active, cx, cy, PLANT_R);
    let e_hf = hf_energy(&e_samples, f.stride, active, cx, cy, PLANT_R);

    println!("{}", "-".repeat(72));
    println!("ARM RESULTS  (residual vs truth, RMS in DN over r={MEASURE_R} quads)");
    println!("{}", "-".repeat(72));
    println!("  A CHARGE       planted, uncorrected   residual {a_res:9.3} DN   ring {a_ring:8.3} DN");
    println!("  B FIDELITY     planted, exact gain    residual {b_res:9.3} DN   ring {b_ring:8.3} DN");
    println!("  E PERVERSE     planted, 2x gain       residual {e_res:9.3} DN   ring {e_ring:8.3} DN");
    println!("  C CONTAINMENT  distant clean site     moved    {c_moved} sample(s)");
    println!("  D INVENTION    HF energy   truth {t_hf:.4}  B {b_hf:.4}  E {e_hf:.4}");
    println!("  F0 MISMATCH    gaussian mote, raw     residual {f0_res:9.3} DN   ring {f0_ring:8.3} DN");
    println!("  F  MISMATCH    gaussian, parabolic fix residual {f_res:8.3} DN   ring {f_ring:8.3} DN");
    println!();

    // ---- verdicts: every arm gated, nothing merely printed ---------------
    let mut pass = 0;
    let mut fail = 0;
    let mut verdicts: Vec<(&str, bool, String)> = Vec::new();

    // A: the metric must charge for an uncorrected planted defect.
    let a_ok = a_res > 4.0 * b_res.max(1e-6) && a_res > 1.0;
    verdicts.push(("A CHARGE", a_ok, format!(
        "{a_res:.3} DN must exceed both 1.0 DN and 4x arm B ({:.3})", 4.0 * b_res)));

    // B: residual must be quantisation-scale. The plant is the algebraic
    // inverse of the correction, so anything beyond rounding is a real defect.
    let b_ok = b_res <= 1.0;
    verdicts.push(("B FIDELITY", b_ok, format!(
        "{b_res:.3} DN must be <= 1.0 DN (quantisation only)")));

    // C: containment is exact, not tolerant.
    let c_ok = c_moved == 0;
    verdicts.push(("C CONTAINMENT", c_ok, format!(
        "{c_moved} samples moved at a site the map does not name; must be exactly 0")));

    // D: the corrector must not add HF the truth does not have.
    let d_ok = b_hf <= t_hf * 1.05;
    verdicts.push(("D INVENTION", d_ok, format!(
        "B HF {b_hf:.4} must be <= truth HF x1.05 ({:.4})", t_hf * 1.05)));

    // E: a wrong-amplitude correction must score WORSE than a right one.
    let e_ok = e_res > b_res && e_ring > b_ring;
    verdicts.push(("E PERVERSE", e_ok, format!(
        "residual {e_res:.3} > {b_res:.3} AND ring {e_ring:.3} > {b_ring:.3}")));

    // F: the arm that stops B from being self-confirming.
    //
    // `mote_map` sets gain = 1.0 / plant_profile(d) on the same d the plant
    // used, so arm B corrects a mote that is the algebraic inverse of the
    // correction. Its 0.097 DN therefore establishes that `apply` implements
    // (v - black) * gain + black correctly and that u16 rounding costs about a
    // tenth of a DN -- and NOTHING about a mote the model does not fit. Real
    // dust does not read the map's profile function.
    //
    // So arm F plants a GAUSSIAN mote and corrects it with the parabolic map.
    // The gate is deliberately weaker than B's and it is two-sided: the
    // correction must remove most of the charge, and it must not leave a
    // footprint edge worse than the defect it removed. A corrector that
    // over-fits its own model would pass B and fail here.
    let f_ok = f_res <= 0.5 * f0_res && f_ring <= f0_ring;
    verdicts.push(("F MISMATCH", f_ok, format!(
        "{f_res:.3} DN must be <= 50% of uncorrected {f0_res:.3} AND ring {f_ring:.3} <= {f0_ring:.3}")));

    println!("{}", "-".repeat(72));
    for (name, ok, why) in &verdicts {
        println!("  {:<14} {}   {why}", name, if *ok { "PASS" } else { "FAIL" });
        if *ok { pass += 1 } else { fail += 1 }
    }
    println!("{}", "-".repeat(72));
    println!("partition: {} arms = {pass} pass + {fail} fail + 0 undefined", verdicts.len());
    if fail == 0 {
        println!();
        println!("VERDICT: the corrector restores a planted mote to within quantisation,");
        println!("  touches nothing it does not name, adds no high-frequency content the");
        println!("  truth lacks, and is charged more when its amplitude is wrong.");
        println!("  Arm F additionally shows it removes {:.1}% of a mote whose profile it",
            100.0 * (1.0 - f_res / f0_res.max(1e-9)));
        println!("  does not model, without leaving a worse footprint edge than the mote.");
        println!("  THIS IS A STATEMENT ABOUT A PLANTED MOTE AT A CERTIFIED CLEAN SITE.");
        println!("  It does not transfer to the two real motes, for which no clean");
        println!("  reference exists. That is the print gate's question, not this one.");
    } else {
        println!();
        println!("VERDICT: {fail} arm(s) failed. No fidelity claim is made.");
        std::process::exit(1);
    }
}

// ---------------------------------------------------------------------------

fn first_raw(dir: &Path) -> Option<PathBuf> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .ok()?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|x| x.eq_ignore_ascii_case("ARW")))
        .collect();
    v.sort();
    v.into_iter().next()
}

/// The outcome of a flat accumulation, partitioned. This is a struct rather
/// than an `Option` because "no field" and "no flats" and "wrong geometry" are
/// three different failures and the refusal message has to say which. A bare
/// `None` here would print the same glyph for a directory that does not exist
/// and a directory whose every frame was correctly rejected.
struct FlatAccum {
    field: Vec<f32>,
    /// Two independent estimates of the same field, built from INTERLEAVED
    /// frames (used frame 0,2,4,... vs 1,3,5,...). Interleaving matters: the
    /// flats were shot over minutes under moving Seattle cloud, so splitting
    /// the sequence into a first and a second half would put the illumination
    /// drift ENTIRELY in the difference between halves and the split-half
    /// statistic would read the weather as irreproducibility. Interleaved
    /// halves share the drift and differ only by noise.
    field_a: Vec<f32>,
    field_b: Vec<f32>,
    used_a: usize,
    used_b: usize,
    qw: usize,
    qh: usize,
    /// Active-area origin of the flats, in photosites. Recorded rather than
    /// assumed: whether a quad index transfers between two sensor geometries
    /// depends entirely on whether they share this origin, and P61 had to read
    /// it from real frames of each before the transfer could be justified.
    ox: usize,
    oy: usize,
    examined: usize,
    used: usize,
    no_decode: usize,
    outside_window: usize,
    geometry_mismatch: usize,
}

impl FlatAccum {
    /// The counts must sum to the total examined, or the report is unreadable.
    fn partitions(&self) -> bool {
        self.used + self.no_decode + self.outside_window + self.geometry_mismatch
            == self.examined
    }

    fn describe(&self) -> String {
        format!(
            "examined {} = used {} + no-decode {} + outside-window {} + geometry-mismatch {}  [{}]",
            self.examined,
            self.used,
            self.no_decode,
            self.outside_window,
            self.geometry_mismatch,
            if self.partitions() { "sums" } else { "DOES NOT SUM" }
        )
    }
}

/// Accumulate the mean quad field over the first `limit` usable flats.
/// Always returns its partition, so a caller cannot mistake "no data" for
/// "a clean sensor" -- the distinction this project has shipped backwards
/// three times.
fn accumulate_flats(dir: &Path, limit: usize) -> FlatAccum {
    let mut acc_out = FlatAccum {
        field: Vec::new(),
        field_a: Vec::new(),
        field_b: Vec::new(),
        used_a: 0,
        used_b: 0,
        qw: 0,
        qh: 0,
        ox: usize::MAX,
        oy: usize::MAX,
        examined: 0,
        used: 0,
        no_decode: 0,
        outside_window: 0,
        geometry_mismatch: 0,
    };
    let mut paths: Vec<PathBuf> = match std::fs::read_dir(dir) {
        Ok(rd) => rd
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.extension().is_some_and(|x| x.eq_ignore_ascii_case("ARW")))
            .collect(),
        Err(_) => Vec::new(),
    };
    paths.sort();

    let mut acc: Vec<f64> = Vec::new();
    let mut acc_a: Vec<f64> = Vec::new();
    let mut acc_b: Vec<f64> = Vec::new();
    for p in &paths {
        if acc_out.used >= limit {
            break;
        }
        acc_out.examined += 1;
        let Ok(f) = strehl_raw::decode(p) else {
            acc_out.no_decode += 1;
            continue;
        };
        let a = (f.active.x, f.active.y, f.active.width, f.active.height);
        let (q, w, h) =
            strehl_core::defect_map::quad_mean(&f.data, f.stride, a, f.levels.black);
        let range = f.levels.white - f.levels.black;
        let m = mean(&q);
        // Exposure window: the same [0.06, 0.90] the census uses. Outside it a
        // flat is either clipped or on the black floor and carries no
        // multiplicative information.
        let frac = m / range;
        if !(0.06..=0.90).contains(&frac) {
            acc_out.outside_window += 1;
            continue;
        }
        if acc.is_empty() {
            acc = vec![0.0; q.len()];
            acc_a = vec![0.0; q.len()];
            acc_b = vec![0.0; q.len()];
            acc_out.qw = w;
            acc_out.qh = h;
            acc_out.ox = f.active.x as usize;
            acc_out.oy = f.active.y as usize;
        } else if w != acc_out.qw || h != acc_out.qh {
            acc_out.geometry_mismatch += 1;
            continue;
        }
        // Per-frame normalisation is what separates dust from cloud: it removes
        // the illumination level, leaving the multiplicative pattern. P11
        // measured this at 264.9x.
        let half = acc_out.used % 2;
        for (i, v) in q.iter().enumerate() {
            let n = f64::from(*v / m);
            acc[i] += n;
            if half == 0 {
                acc_a[i] += n;
            } else {
                acc_b[i] += n;
            }
        }
        if half == 0 {
            acc_out.used_a += 1;
        } else {
            acc_out.used_b += 1;
        }
        acc_out.used += 1;
    }
    if acc_out.used > 0 {
        acc_out.field = acc
            .iter()
            .map(|v| (*v / acc_out.used as f64) as f32)
            .collect();
    }
    if acc_out.used_a > 0 {
        acc_out.field_a = acc_a
            .iter()
            .map(|v| (*v / acc_out.used_a as f64) as f32)
            .collect();
    }
    if acc_out.used_b > 0 {
        acc_out.field_b = acc_b
            .iter()
            .map(|v| (*v / acc_out.used_b as f64) as f32)
            .collect();
    }
    acc_out
}

/// The reproducible part of the high-pass residual, quad by quad, SIGNED.
///
/// WHY THIS EXISTS. The first version of the cleanliness test high-passed a
/// single 20-frame mean and demanded the result fall below 0.125%. It refused
/// every one of 110,538 candidate sites, with a best of 0.607%. The census
/// showed only 568 sites were excluded by mote clearance, so the refusal was
/// not geometry -- the whole field read dirty. That is the signature of a
/// statistic measuring its own noise: a 20-frame mean of a photon-limited
/// capture has a per-quad standard error that does not care where dust is.
///
/// A fixed multiplicative defect is, by definition, THE SAME in two
/// independent estimates of the field. Shot noise is not. So take two
/// interleaved half-fields, high-pass each, and keep only what survives in
/// both:
///
///     rep(x) = if sign(a) == sign(b) { sign * min(|a|, |b|) } else { 0 }
///
/// This is deliberately conservative -- its magnitude can only ever be
/// smaller than the noisier half's reading, so it under-reports a real mote
/// rather than inventing one. Under-reporting is the safe direction here,
/// because this statistic's job is to certify a site CLEAN before a mote is
/// planted there; a false "clean" would put the reference on top of a real
/// defect, which is the one failure that would silently corrupt every
/// downstream number.
///
/// THE SIGN IS LOAD-BEARING and it is why the second version of this function
/// exists. Split-half agreement removes shot noise but it cannot remove
/// PRNU -- per-photosite response non-uniformity is a fixed multiplicative
/// pattern, so it is reproducible BY DEFINITION and appears in both halves at
/// full strength. Measured here at 0.473% at an untouched site, which is 3.8x
/// the 0.125% floor: with an unsigned statistic no site on this sensor could
/// ever be certified, and the refusal would have been read as "the sensor is
/// filthy" when it actually means "the floor is below the sensor's own grain".
///
/// PRNU is spatially white; a mote is a CORRELATED DISC tens of quads across.
/// So keeping the sign and averaging over a dust-sized disc separates them by
/// their geometry rather than their amplitude: PRNU cancels toward zero as
/// 1/sqrt(area), a coherent disc does not. That is what `disc_response` does.
fn reproducible_hp(a: &[f32], b: &[f32]) -> Vec<f32> {
    a.iter()
        .zip(b.iter())
        .map(|(x, y)| {
            if (*x >= 0.0) == (*y >= 0.0) {
                let m = x.abs().min(y.abs());
                if *x >= 0.0 {
                    m
                } else {
                    -m
                }
            } else {
                0.0
            }
        })
        .collect()
}

/// Signed mean of `rep` over a dust-sized disc, returned as a magnitude.
///
/// This is the site statistic. A mote is a coherent attenuation across the
/// whole disc, so its contributions add; PRNU has no preferred sign, so its
/// contributions cancel. The distinction is geometric, which is the only
/// distinction available -- a mote and a bright grain can have the same
/// amplitude at a single quad.
fn disc_response(rep: &[f32], w: usize, cx: usize, cy: usize, r: usize) -> f32 {
    let mut sum = 0.0f64;
    let mut n = 0usize;
    for dy in -(r as i64)..=(r as i64) {
        for dx in -(r as i64)..=(r as i64) {
            if dx * dx + dy * dy > (r * r) as i64 {
                continue;
            }
            sum += f64::from(rep[(cy as i64 + dy) as usize * w + (cx as i64 + dx) as usize]);
            n += 1;
        }
    }
    if n == 0 {
        return 0.0;
    }
    (sum / n as f64).abs() as f32
}

/// Multiply a soft disc of attenuation into a field, in place. Used only by
/// the commissioning arms; the real motes are whatever the sensor has.
fn stamp_disc(field: &mut [f32], w: usize, cx: usize, cy: usize, r: usize, depth: f32) {
    for dy in -(r as i64)..=(r as i64) {
        for dx in -(r as i64)..=(r as i64) {
            let d2 = dx * dx + dy * dy;
            if d2 > (r * r) as i64 {
                continue;
            }
            let t = (d2 as f32).sqrt() / r as f32;
            // Smooth edge, so the stamp is a plausible mote rather than a step.
            let prof = 1.0 - depth * (1.0 - t * t).max(0.0);
            let idx = (cy as i64 + dy) as usize * w + (cx as i64 + dx) as usize;
            field[idx] *= prof;
        }
    }
}

/// Outcome of one commissioning arm.
struct Arm {
    name: &'static str,
    reading: f32,
    expected: &'static str,
    pass: bool,
}

/// Commission the cleanliness statistic before any site is certified with it.
///
/// Five arms, because a degradation-only suite cannot tell a BLIND statistic
/// from a PERVERSE one, and because a floor comparison alone cannot tell a
/// responsive statistic from a site that was already above the floor:
///
///   -1. PRIOR-STAT -- the statistic this suite REPLACED, measured on the same
///                     pixels in the same run. It must read ABOVE the floor at
///                     an untouched site, which is the whole reason it was
///                     replaced. Gating it means the claim "the unsigned
///                     statistic cannot certify any site on this sensor" is a
///                     live measurement in this log rather than a number
///                     remembered from a run whose log was overwritten.
///   0. BASELINE    -- the untouched site. Reported, and then USED: every
///                     other arm is scored as a response ABOVE baseline, not
///                     as an absolute level. The first version of this suite
///                     scored the null against the floor and failed it at
///                     0.405% -- while baseline was 0.473%. The stamp had in
///                     fact moved the statistic DOWNWARD by 0.068%, i.e. it
///                     had barely responded at all, which is exactly what the
///                     null wanted to see. Scoring against an absolute floor
///                     turned a passing null into a failing one.
///   1. DEFECT      -- a disc stamped into BOTH halves (a fixed pattern is in
///                     both by construction) must respond well above baseline.
///   2. NULL        -- a disc of the same depth stamped into ONE half only is
///                     not reproducible and must produce at most a small
///                     fraction of the defect's response. This is the arm that
///                     proves the statistic suppresses non-reproducible
///                     structure rather than merely being small.
///   3. IMPROVEMENT -- the arm-1 site with the known attenuation divided back
///                     out of both halves must return to near baseline.
///                     Without this a statistic that is bounded below, or that
///                     scores a repair as badly as a defect, passes 1 and 2
///                     intact. This project shipped exactly that failure once.
///
/// Every arm is stamped on a copy, so commissioning never contaminates the
/// field the run goes on to use.
fn commission_cleanliness(
    fa: &FlatAccum,
    w: usize,
    h: usize,
    cx: usize,
    cy: usize,
    depth: f32,
    r: usize,
) -> Vec<Arm> {
    let resp_at = |a: &[f32], b: &[f32]| -> f32 {
        let hpa = high_pass(a, w, h, 64);
        let hpb = high_pass(b, w, h, 64);
        let rep = reproducible_hp(&hpa, &hpb);
        disc_response(&rep, w, cx, cy, PLANT_R)
    };

    let base = resp_at(&fa.field_a, &fa.field_b);

    // The statistic this suite replaced, measured on the same pixels in the
    // same run, so the claim that it cannot certify any site on this sensor is
    // backed by this log rather than by a remembered number from an earlier
    // one. It is the unsigned worst-quad reproducible residual: PRNU survives
    // it because PRNU is reproducible by definition.
    let hpa0 = high_pass(&fa.field_a, w, h, 64);
    let hpb0 = high_pass(&fa.field_b, w, h, 64);
    let rep0 = reproducible_hp(&hpa0, &hpb0);
    let unsigned_base = region_worst(&rep0, w, cx, cy, MEASURE_R);

    let mut a1 = fa.field_a.clone();
    let mut b1 = fa.field_b.clone();
    stamp_disc(&mut a1, w, cx, cy, r, depth);
    stamp_disc(&mut b1, w, cx, cy, r, depth);
    let defect = resp_at(&a1, &b1);

    let mut a2 = fa.field_a.clone();
    stamp_disc(&mut a2, w, cx, cy, r, depth);
    let null = resp_at(&a2, &fa.field_b);

    // Improvement: undo the planted attenuation, which is known exactly.
    let mut a3 = a1.clone();
    let mut b3 = b1.clone();
    stamp_disc(&mut a3, w, cx, cy, r, -depth / (1.0 - depth));
    stamp_disc(&mut b3, w, cx, cy, r, -depth / (1.0 - depth));
    let improved = resp_at(&a3, &b3);

    // The response scale the other arms are judged against. If the defect did
    // not move the statistic at all this is ~0 and every ratio below is
    // meaningless -- so the DEFECT arm is gated on the span itself, not on a
    // ratio, and it is the arm that fails first.
    let span = (defect - base).max(0.0);

    vec![
        Arm {
            name: "PRIOR-STAT  unsigned worst quad",
            reading: unsigned_base,
            expected: ">= floor",
            pass: unsigned_base >= CLEAN_RESIDUAL_MAX,
        },
        Arm {
            name: "BASELINE    untouched site",
            reading: base,
            expected: "< floor",
            pass: base < CLEAN_RESIDUAL_MAX,
        },
        Arm {
            name: "DEFECT      disc in both halves",
            reading: defect,
            expected: ">= 4x baseline",
            pass: defect >= CLEAN_RESIDUAL_MAX && defect >= 4.0 * base,
        },
        Arm {
            name: "NULL        disc in one half only",
            reading: null,
            expected: "<= 25% of span",
            pass: span > 0.0 && (null - base).abs() <= 0.25 * span,
        },
        Arm {
            name: "IMPROVEMENT planted mote divided out",
            reading: improved,
            expected: "back to baseline",
            pass: span > 0.0 && (improved - base).abs() <= 0.25 * span,
        },
    ]
}

fn mean(v: &[f32]) -> f32 {
    if v.is_empty() {
        return 0.0;
    }
    v.iter().map(|x| f64::from(*x)).sum::<f64>() as f32 / v.len() as f32
}

/// Field minus its own box-smoothed self: large-scale illumination out, small
/// fixed features in. This is the separation P11 measured, not a new one.
fn high_pass(field: &[f32], w: usize, h: usize, radius: usize) -> Vec<f32> {
    let bg = strehl_core::defect_map::box_smooth(field, w, h, radius, 2);
    field
        .iter()
        .zip(bg.iter())
        .map(|(f, b)| if *b > 0.0 { f / b - 1.0 } else { 0.0 })
        .collect()
}

/// The two motes the shipping map names, in quad coordinates.
fn mapped_motes() -> Vec<(usize, usize)> {
    match DefectMap::embedded_for("ILCE-7CM2") {
        Some(m) => m.dust.iter().map(|d| (d.px as usize, d.py as usize)).collect(),
        None => Vec::new(),
    }
}

/// Why each candidate site was rejected. Without this, a `None` from the
/// search prints the same glyph whether every candidate was dirty, every
/// candidate was too near a mapped mote, or no candidate was ever examined.
/// The counts must sum to the total scanned.
#[derive(Default)]
struct SiteCensus {
    scanned: usize,
    near_mote: usize,
    near_exclude: usize,
    too_dirty: usize,
    no_signal: usize,
    /// Sensor-clean, but the SUBJECT carries no usable signal there. This is a
    /// distinct outcome and it earned its own bucket the hard way: the search
    /// accepted 91,339 sites on cleanliness alone, returned quad (1441,553),
    /// and the run then refused because that site sits at 0.016 of range on
    /// the subject. Cleanliness is a property of the sensor and brightness is
    /// a property of the scene; a search that optimises one and discovers the
    /// other afterwards is a search with a hidden second criterion.
    no_subject_signal: usize,
    accepted: usize,
    /// The best residual seen among candidates that were geometrically
    /// eligible, so a refusal can say how far from the floor the field is.
    /// `None` means no candidate was ever eligible, which is a different
    /// failure from "eligible but dirty".
    best_eligible: Option<f32>,
}

impl SiteCensus {
    fn partitions(&self) -> bool {
        self.near_mote
            + self.near_exclude
            + self.too_dirty
            + self.no_signal
            + self.no_subject_signal
            + self.accepted
            == self.scanned
    }

    fn describe(&self) -> String {
        format!(
            "scanned {} = near-mote {} + near-exclude {} + too-dirty {} + no-signal {} + dark-on-subject {} + accepted {}  [{}]",
            self.scanned,
            self.near_mote,
            self.near_exclude,
            self.too_dirty,
            self.no_signal,
            self.no_subject_signal,
            self.accepted,
            if self.partitions() { "sums" } else { "DOES NOT SUM" }
        )
    }
}

fn find_clean_site(
    hp: &[f32],
    field: &[f32],
    w: usize,
    scan_w: usize,
    h: usize,
    motes: &[(usize, usize)],
    subj: &SubjectSignal,
) -> (Option<(usize, usize)>, SiteCensus) {
    find_clean_site_excluding(hp, field, w, scan_w, h, motes, subj, (usize::MAX, usize::MAX))
}

/// The subject's per-quad signal above black, with its own stride.
///
/// Its stride is NOT the flat field's. The flats decode 3520 quads wide and
/// this subject 3516, and P61 established that the two share an origin so a
/// quad index transfers -- but a LINEAR index does not, because the row
/// lengths differ. Carrying the stride alongside the data is what stops the
/// transfer from silently shearing the subject by 4 quads per row.
struct SubjectSignal {
    q: Vec<f32>,
    stride: usize,
    range: f32,
}

impl SubjectSignal {
    /// Mean signal fraction over the SAME disc the final check measures.
    ///
    /// The first version sampled the single centre quad here while the final
    /// gate averaged over `MEASURE_R`. The two disagreed at the boundary and
    /// the run refused at 0.079 against a floor of 0.08 -- a site the search
    /// had accepted. A search whose acceptance criterion is not the criterion
    /// it will be judged by does not have a floor, it has two.
    fn frac_at(&self, x: usize, y: usize, r: usize) -> f32 {
        if self.range <= 0.0 {
            return 0.0;
        }
        let mut sum = 0.0f64;
        let mut n = 0usize;
        for dy in -(r as i64)..=(r as i64) {
            for dx in -(r as i64)..=(r as i64) {
                if dx * dx + dy * dy > (r * r) as i64 {
                    continue;
                }
                let (sx, sy) = (x as i64 + dx, y as i64 + dy);
                if sx < 0 || sy < 0 {
                    return 0.0;
                }
                let i = sy as usize * self.stride + sx as usize;
                if i >= self.q.len() {
                    return 0.0;
                }
                sum += f64::from(self.q[i]);
                n += 1;
            }
        }
        if n == 0 {
            return 0.0;
        }
        (sum / n as f64) as f32 / self.range
    }
}

/// Scan for a site that clears EVERY floor, and return `None` if none does.
/// The floors are absolute, so this search can come back empty-handed.
///
/// `w` is the row stride of `hp`/`field`; `scan_w` is the width the search is
/// allowed to reach. They differ when the flats were captured on the wide body
/// and the subject on the narrow one: the extra columns exist in the flat
/// field but have no counterpart in the subject, so a site chosen there could
/// not be planted. Collapsing the two into one number is exactly how a site
/// gets certified in a grid it will never be applied to.
fn find_clean_site_excluding(
    hp: &[f32],
    field: &[f32],
    w: usize,
    scan_w: usize,
    h: usize,
    motes: &[(usize, usize)],
    subj: &SubjectSignal,
    exclude: (usize, usize),
) -> (Option<(usize, usize)>, SiteCensus) {
    let mut best: Option<(usize, usize, f32)> = None;
    let mut census = SiteCensus::default();
    let step = 8;
    let mut y = BORDER + MEASURE_R;
    while y + BORDER + MEASURE_R < h {
        let mut x = BORDER + MEASURE_R;
        while x + BORDER + MEASURE_R < scan_w {
            census.scanned += 1;
            let far_from_motes = motes
                .iter()
                .all(|(mx, my)| dist2(x, y, *mx, *my) >= (CLEAN_CLEARANCE * CLEAN_CLEARANCE) as i64);
            let far_from_exclude = exclude.0 == usize::MAX
                || dist2(x, y, exclude.0, exclude.1)
                    >= (4 * MEASURE_R * 4 * MEASURE_R) as i64;
            if !far_from_motes {
                census.near_mote += 1;
            } else if !far_from_exclude {
                census.near_exclude += 1;
            } else {
                // Signed disc-mean, not the worst single quad: PRNU cancels
                // over a disc and a mote does not, and that geometric
                // difference is the only thing that separates them.
                let worst = disc_response(hp, w, x, y, PLANT_R);
                let sig = field[y * w + x];
                if census.best_eligible.is_none_or(|b| worst < b) {
                    census.best_eligible = Some(worst);
                }
                let sfrac = subj.frac_at(x, y, MEASURE_R);
                if sig <= 0.0 {
                    census.no_signal += 1;
                } else if worst >= CLEAN_RESIDUAL_MAX {
                    census.too_dirty += 1;
                } else if !(SIGNAL_MIN_FRAC..=SIGNAL_MAX_FRAC).contains(&sfrac) {
                    census.no_subject_signal += 1;
                } else {
                    census.accepted += 1;
                    if best.is_none_or(|(_, _, b)| worst < b) {
                        best = Some((x, y, worst));
                    }
                }
            }
            x += step;
        }
        y += step;
    }
    (best.map(|(x, y, _)| (x, y)), census)
}

fn dist2(ax: usize, ay: usize, bx: usize, by: usize) -> i64 {
    let dx = ax as i64 - bx as i64;
    let dy = ay as i64 - by as i64;
    dx * dx + dy * dy
}

fn region_worst(hp: &[f32], w: usize, cx: usize, cy: usize, r: usize) -> f32 {
    let mut worst = 0.0f32;
    for dy in -(r as i64)..=(r as i64) {
        for dx in -(r as i64)..=(r as i64) {
            if dx * dx + dy * dy > (r * r) as i64 {
                continue;
            }
            let v = hp[(cy as i64 + dy) as usize * w + (cx as i64 + dx) as usize].abs();
            if v > worst {
                worst = v;
            }
        }
    }
    worst
}

/// The single-quad worst residual over the measurement region, reported
/// alongside the disc response so the two can be compared in the log. It is
/// NOT the acceptance criterion: it was, and it rejected all 110,538
/// candidates at a best of 0.607% because PRNU dominates it. Kept because the
/// comparison between the two numbers at the chosen site is the evidence that
/// the disc average is doing what it claims.
fn worst_quad_residual(hp: &[f32], w: usize, cx: usize, cy: usize, r: usize) -> f32 {
    region_worst(hp, w, cx, cy, r)
}

/// Planted transmission at quad radius `d`: flat `PLANT_TRANSMISSION` in the
/// core, rising linearly to 1.0 across `PLANT_EDGE`. A hard-edged disc would be
/// an easier target than a real mote, which has a measured ~51 um penumbra.
fn plant_profile(d: f32) -> f32 {
    let core = (PLANT_R - PLANT_EDGE) as f32;
    if d <= core {
        PLANT_TRANSMISSION
    } else if d >= PLANT_R as f32 {
        1.0
    } else {
        let t = (d - core) / PLANT_EDGE as f32;
        PLANT_TRANSMISSION + (1.0 - PLANT_TRANSMISSION) * t
    }
}

/// Plant a mote the corrector's model does NOT fit.
///
/// Same centre, same central transmission and same footprint radius as
/// `plant`, but a Gaussian radial profile instead of the flat-core-with-linear-
/// edge one the map stores. Sigma is `PLANT_R / 2`, which puts the profile's
/// half-depth point near the middle of the disc rather than at its rim, so the
/// mismatch is a shape disagreement over the whole footprint and not just a
/// disagreement at the edge.
///
/// This exists because arm B's plant is the algebraic inverse of arm B's
/// correction and therefore cannot fail for any reason except an arithmetic
/// bug in `apply`. Real dust does not consult the map's profile function.
fn plant_gauss(
    truth: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    cx: usize,
    cy: usize,
    black: f32,
) -> Vec<u16> {
    let (ox, oy, _, _) = active;
    let sigma = PLANT_R as f32 / 2.0;
    let depth = 1.0 - PLANT_TRANSMISSION;
    let mut out = truth.to_vec();
    for dy in -(PLANT_R as i64)..=(PLANT_R as i64) {
        for dx in -(PLANT_R as i64)..=(PLANT_R as i64) {
            let d2 = (dx * dx + dy * dy) as f32;
            if d2 > (PLANT_R * PLANT_R) as f32 {
                continue;
            }
            let t = 1.0 - depth * (-d2 / (2.0 * sigma * sigma)).exp();
            let (qx, qy) = ((cx as i64 + dx) as usize, (cy as i64 + dy) as usize);
            for sy in 0..QUAD {
                for sx in 0..QUAD {
                    let idx = (oy + qy * QUAD + sy) * stride + ox + qx * QUAD + sx;
                    let v = f32::from(out[idx]);
                    let sig = (v - black).max(0.0);
                    out[idx] = (sig * t + black).round() as u16;
                }
            }
        }
    }
    out
}

/// Attenuate a disc multiplicatively on the BLACK-SUBTRACTED signal, which is
/// how dust actually acts and is the domain `apply` inverts in. Attenuating raw
/// DN instead would scale the black pedestal and the correction could never be
/// its inverse.
fn plant(
    truth: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    cx: usize,
    cy: usize,
    black: f32,
) -> Vec<u16> {
    let (ox, oy, _, _) = active;
    let mut out = truth.to_vec();
    for dy in -(PLANT_R as i64)..=(PLANT_R as i64) {
        for dx in -(PLANT_R as i64)..=(PLANT_R as i64) {
            let d = ((dx * dx + dy * dy) as f32).sqrt();
            if d > PLANT_R as f32 {
                continue;
            }
            let t = plant_profile(d);
            let (qx, qy) = ((cx as i64 + dx) as usize, (cy as i64 + dy) as usize);
            for sy in 0..QUAD {
                for sx in 0..QUAD {
                    let idx = (oy + qy * QUAD + sy) * stride + ox + qx * QUAD + sx;
                    let v = f32::from(out[idx]);
                    let sig = (v - black).max(0.0);
                    out[idx] = (sig * t + black).round() as u16;
                }
            }
        }
    }
    out
}

/// A map naming exactly the planted quads. `scale` multiplies the CORRECTION
/// EXCESS, not the gain: `scale = 1.0` inverts the plant exactly, `scale = 2.0`
/// over-corrects by twice the excess. Scaling the gain itself would make arm E
/// a different-shaped defect rather than the same defect at the wrong strength.
fn mote_map(aw: usize, ah: usize, cx: usize, cy: usize, scale: f32) -> DefectMap {
    let mut m = DefectMap::empty(aw, ah, "ILCE-7CM2");
    for dy in -(PLANT_R as i64)..=(PLANT_R as i64) {
        for dx in -(PLANT_R as i64)..=(PLANT_R as i64) {
            let d = ((dx * dx + dy * dy) as f32).sqrt();
            if d > PLANT_R as f32 {
                continue;
            }
            let t = plant_profile(d);
            if (t - 1.0).abs() < 1e-6 {
                continue;
            }
            let exact = 1.0 / t;
            m.dust.push(DustQuad {
                px: (cx as i64 + dx) as u32,
                py: (cy as i64 + dy) as u32,
                gain: 1.0 + scale * (exact - 1.0),
            });
        }
    }
    m
}

/// Mean signal above black over a disc, averaging the WHOLE quad.
///
/// The first version indexed `(oy + qy*QUAD)*stride + ox + qx*QUAD`, i.e. the
/// top-left photosite of each quad -- which under a Bayer CFA is always the
/// same colour channel. It was therefore reporting the red channel's level and
/// calling it "the site signal". Against `quad_mean`, which averages R, G, G
/// and B, it read low: the search accepted a site at >= 0.080 of range and
/// this function then refused the same site at 0.079, twice, at two different
/// sites. That is not a boundary case, it is two statistics wearing one name.
fn mean_signal(
    s: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    cx: usize,
    cy: usize,
    r: usize,
    black: f32,
) -> f32 {
    let (ox, oy, _, _) = active;
    let (mut sum, mut n) = (0f64, 0usize);
    for dy in -(r as i64)..=(r as i64) {
        for dx in -(r as i64)..=(r as i64) {
            if dx * dx + dy * dy > (r * r) as i64 {
                continue;
            }
            let qy = oy + (cy as i64 + dy) as usize * QUAD;
            let qx = ox + (cx as i64 + dx) as usize * QUAD;
            for sy in 0..QUAD {
                for sx in 0..QUAD {
                    sum += f64::from(f32::from(s[(qy + sy) * stride + qx + sx]) - black);
                    n += 1;
                }
            }
        }
    }
    if n == 0 { 0.0 } else { (sum / n as f64) as f32 }
}

fn rms(
    a: &[u16],
    b: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    cx: usize,
    cy: usize,
    r: usize,
) -> f32 {
    let (ox, oy, _, _) = active;
    let (mut sum, mut n) = (0f64, 0usize);
    for dy in -(r as i64)..=(r as i64) {
        for dx in -(r as i64)..=(r as i64) {
            if dx * dx + dy * dy > (r * r) as i64 {
                continue;
            }
            for sy in 0..QUAD {
                for sx in 0..QUAD {
                    let idx = (oy + (cy as i64 + dy) as usize * QUAD + sy) * stride
                        + ox
                        + (cx as i64 + dx) as usize * QUAD
                        + sx;
                    let d = f64::from(a[idx]) - f64::from(b[idx]);
                    sum += d * d;
                    n += 1;
                }
            }
        }
    }
    if n == 0 { 0.0 } else { (sum / n as f64).sqrt() as f32 }
}

fn count_moved(
    a: &[u16],
    b: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    cx: usize,
    cy: usize,
    r: usize,
) -> usize {
    let (ox, oy, _, _) = active;
    let mut n = 0;
    for dy in -(r as i64)..=(r as i64) {
        for dx in -(r as i64)..=(r as i64) {
            for sy in 0..QUAD {
                for sx in 0..QUAD {
                    let idx = (oy + (cy as i64 + dy) as usize * QUAD + sy) * stride
                        + ox
                        + (cx as i64 + dx) as usize * QUAD
                        + sx;
                    if a[idx] != b[idx] {
                        n += 1;
                    }
                }
            }
        }
    }
    n
}

/// The footprint statistic: how big a STEP does the correction leave at the
/// edge of its own disc? Mean residual just inside the planted radius minus
/// mean residual just outside it. A correct-amplitude correction leaves no
/// step; a wrong-amplitude one leaves a ring, which is invented structure.
fn ring_step(
    a: &[u16],
    truth: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    cx: usize,
    cy: usize,
    black: f32,
) -> f32 {
    let (ox, oy, _, _) = active;
    let _ = black;
    let (mut inn, mut inn_n) = (0f64, 0usize);
    let (mut out, mut out_n) = (0f64, 0usize);
    let r = MEASURE_R as i64;
    for dy in -r..=r {
        for dx in -r..=r {
            let d = ((dx * dx + dy * dy) as f32).sqrt();
            let idx = (oy + (cy as i64 + dy) as usize * QUAD) * stride
                + ox
                + (cx as i64 + dx) as usize * QUAD;
            let res = f64::from(a[idx]) - f64::from(truth[idx]);
            // A band 3 quads wide on each side of the planted edge.
            if d >= (PLANT_R - PLANT_EDGE - 3) as f32 && d < (PLANT_R - PLANT_EDGE) as f32 {
                inn += res;
                inn_n += 1;
            } else if d > PLANT_R as f32 && d <= (PLANT_R + 3) as f32 {
                out += res;
                out_n += 1;
            }
        }
    }
    if inn_n == 0 || out_n == 0 {
        return 0.0;
    }
    ((inn / inn_n as f64) - (out / out_n as f64)).abs() as f32
}

/// Laplacian energy inside the disc -- the spatial-frequency content the brief
/// worried the corrector would manufacture.
fn hf_energy(
    s: &[u16],
    stride: usize,
    active: (usize, usize, usize, usize),
    cx: usize,
    cy: usize,
    r: usize,
) -> f32 {
    let (ox, oy, _, _) = active;
    let (mut sum, mut n) = (0f64, 0usize);
    for dy in -(r as i64) + 1..(r as i64) - 1 {
        for dx in -(r as i64) + 1..(r as i64) - 1 {
            if dx * dx + dy * dy > ((r - 1) * (r - 1)) as i64 {
                continue;
            }
            let at = |ddx: i64, ddy: i64| -> f64 {
                let idx = (oy + (cy as i64 + dy + ddy) as usize * QUAD) * stride
                    + ox
                    + (cx as i64 + dx + ddx) as usize * QUAD;
                f64::from(s[idx])
            };
            let lap = 4.0 * at(0, 0) - at(1, 0) - at(-1, 0) - at(0, 1) - at(0, -1);
            sum += lap * lap;
            n += 1;
        }
    }
    if n == 0 { 0.0 } else { (sum / n as f64).sqrt() as f32 }
}
