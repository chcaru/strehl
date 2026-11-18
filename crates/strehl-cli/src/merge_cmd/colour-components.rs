//! Lateral colour by component (`STREHL_CA_COMPONENTS`): off by default.
//!
//! # Why
//!
//! A red or blue photosite also records some green-band light: the colour
//! filters' passbands overlap. The lens images that light where it images
//! green; only the rest of the channel (its own band) is displaced by lateral
//! colour. One magnification per channel cannot register both parts. The
//! profile's scale fits the coarse mixture, so in a four-shot render fine red
//! detail lay 1.03 px rms from green on the A7CR scarab (2.4 px at the
//! corners) and fine blue 0.43 px; the 1 px chroma smoothing hid it
//! (`experiments/a7cr-fourshot-quality-2026-11-16/results-round2.md`, R7;
//! proposal item 8).
//!
//! # What changes
//!
//! Only four-shot groups assembled from measured channels, where every site
//! holds a measured green: the gather takes the green-band share out of red
//! and blue (`C - a G`, `a` the profile's raw share times the white-balance
//! ratio), gathers that own band through the own band's lateral-colour
//! transform, and adds `a` times green gathered through green's transform at
//! the same site. Green is untouched, so the election and its weights are
//! those of a render without the switch. A group demoted to member 1 keeps
//! the profile's mixture scale.
//!
//! During the per-capture refinement's preview the share is not added back,
//! so the refinement measures, and then corrects, the own band alone.
//!
//! `placebo` reverses the share's sign (a control arm).
use super::*;
use std::sync::atomic::{AtomicBool, Ordering};
use strehl_core::optics::{ColourComponents, OpticalProfile};

pub(crate) const ENV: &str = "STREHL_CA_COMPONENTS";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Mode {
    Off,
    On,
    Placebo,
}

pub(crate) fn mode() -> Result<Mode> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(Mode::Off),
        Err(e) => Err(e).context(ENV),
        Ok(v) => match v.trim() {
            "" | "0" | "off" => Ok(Mode::Off),
            "1" | "on" => Ok(Mode::On),
            "placebo" => Ok(Mode::Placebo),
            other => anyhow::bail!("{ENV}={other:?} is not off, on or placebo"),
        },
    }
}

/// Set while the lateral-CA refinement's preview runs: gather the own band
/// alone, so the preview measures what the own band's correction leaves.
static OWN_ONLY: AtomicBool = AtomicBool::new(false);

pub(crate) fn set_own_only(on: bool) {
    OWN_ONLY.store(on, Ordering::Relaxed);
}

pub(crate) fn own_only() -> bool {
    OWN_ONLY.load(Ordering::Relaxed)
}

/// What the gather needs for one frame: the shares (raw units, sign applied)
/// and the profile whose red and blue scales are the own bands'.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Split {
    pub share_r: f64,
    pub share_b: f64,
    pub own: OpticalProfile,
}

/// The split for a frame gathered with lateral-colour profile `ca`, or
/// `None` when the switch is off or the gear has no component record.
pub(crate) fn split_for(ca: Option<&OpticalProfile>) -> Result<Option<Split>> {
    let m = mode()?;
    if m == Mode::Off {
        return Ok(None);
    }
    let Some(profile) = ca else { return Ok(None) };
    let Some(c) = strehl_core::optics::colour_components(profile) else {
        return Ok(None);
    };
    let sign = if m == Mode::Placebo { -1.0 } else { 1.0 };
    Ok(Some(Split {
        share_r: sign * c.share_r,
        share_b: sign * c.share_b,
        own: c.own_band_profile(profile),
    }))
}

/// One banner line for the render, from its first frame's gear.
pub(crate) fn banner(first: &std::path::Path) -> Result<Option<String>> {
    let m = mode()?;
    if m == Mode::Off {
        return Ok(None);
    }
    let ident = strehl_raw::identity(first);
    let ca =
        strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3)?;
    let record: Option<&ColourComponents> = ca.and_then(strehl_core::optics::colour_components);
    Ok(Some(match (ca, record) {
        (None, _) => format!(
            "colour by part  : {ENV} set, but NOT APPLIED -- no lateral-colour profile is active \
             for this gear"
        ),
        (Some(p), None) => format!(
            "colour by part  : {ENV} set, but NOT APPLIED -- profile {:?} has no measured \
             green-band shares",
            p.key
        ),
        (Some(_), Some(c)) => format!(
            "colour by part  : {} ({ENV}) -- four-shot groups: red and blue less {:.2} / {:.2} of \
             green's raw signal gathered at the own bands' scales {:+.1} / {:+.1} ppm, the share \
             added back at green's coordinates ({}); demoted groups keep the profile's mixture \
             scale",
            if m == Mode::Placebo {
                "PLACEBO (shares reversed)"
            } else {
                "ON"
            },
            c.share_r,
            c.share_b,
            c.own_eps_r * 1e6,
            c.own_eps_b * 1e6,
            c.measured_from
        ),
    }))
}

/// The per-stack check of the shares: the displacement red and blue still
/// show against green in a coarse and a fine band of the written image.
/// A fine-band scale with the sign of the own band's means the share is too
/// small; the opposite sign, too large.
pub(crate) fn report_residuals(rgb: &[f32], w: usize, h: usize) {
    for (name, lo, hi) in [
        ("coarse (0.03-0.08 cycles/px)", 2.0, 5.0),
        ("fine (0.24-0.42 cycles/px)", 0.4, 0.75),
    ] {
        match strehl_core::ca_refine::measure_band(w, h, rgb, lo, hi) {
            Some(r) => eprintln!(
                "colour by part  : residual, {name}: red {:+.1} ppm t ({:+.3}, {:+.3}) px, blue \
                 {:+.1} ppm t ({:+.3}, {:+.3}) px ({} / {} tiles)",
                r.red.scale * 1e6,
                r.red.translation.0,
                r.red.translation.1,
                r.blue.scale * 1e6,
                r.blue.translation.0,
                r.blue.translation.1,
                r.red.kept,
                r.blue.kept
            ),
            None => {
                eprintln!("colour by part  : residual, {name}: too little structure to measure")
            }
        }
    }
}
