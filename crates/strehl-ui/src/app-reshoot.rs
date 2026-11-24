//! Plan R1 to R4: a re-shoot from the Stack station while the subject is
//! still on the rig. A pinned region's popover offers "Re-shoot…": the
//! planes behind the region, whether the camera host still holds this
//! capture (R1), what the region shows (pinned highlights, deep shadow) and
//! the pass that would fix it (R2), the pass taken into the same capture
//! (`queue_pass`, `queue_retakes`; R3), then the capture stacked again (R4).
//!
//! Not built: a probe group comparing the rig with a stored group (the
//! engine registers each new frame anyway), infill planes (the host has no
//! `queue_infill`), and per-plane RAW evidence in `evidence.strehl`: the
//! region's own pixels stand in for it.
use super::*;
use crate::studio_widgets as w;
use serde_json::Value;

/// The re-shoot panel's state.
#[derive(Clone, Debug, PartialEq)]
pub(super) struct Reshoot {
    /// The region (photograph UV).
    pub region: egui::Rect,
    /// Plane numbers (1-based) behind it, first and last.
    pub planes: (u64, u64),
    /// Share of the region's pixels at the pin, and its mean linear level.
    pub pinned_share: f32,
    pub mean_level: f32,
    /// What was asked of the host, once asked.
    pub sent: Option<String>,
}

/// The capture's base exposure and shutter choices, from its manifest.
#[derive(Clone, Debug, Default, PartialEq)]
pub(super) struct CaptureExposure {
    pub iso: Option<u64>,
    pub shutter: Option<u64>,
    pub options: Vec<u64>,
    pub highlight: Option<u64>,
}

pub(super) fn capture_exposure(capture: &Path) -> CaptureExposure {
    let Ok(bytes) = std::fs::read(capture.join("manifest.json")) else {
        return CaptureExposure::default();
    };
    let Ok(m) = serde_json::from_slice::<Value>(&bytes) else {
        return CaptureExposure::default();
    };
    let props = &m["initial_status"]["properties"];
    CaptureExposure {
        iso: props["IsoSensitivity"]["value"].as_u64(),
        shutter: props["ShutterSpeed"]["value"].as_u64(),
        options: props["ShutterSpeed"]["allowed"]
            .as_array()
            .map(|a| a.iter().filter_map(Value::as_u64).collect())
            .unwrap_or_default(),
        highlight: m["plan"]["highlight"]["shutter"].as_u64(),
    }
}

/// Pinned share and mean linear level of `region` in the linear preview.
pub(super) fn region_levels(image: &strehl_edit::LinearImage, region: egui::Rect) -> (f32, f32) {
    let (w, h) = (image.width as usize, image.height as usize);
    let x0 = ((region.left().clamp(0.0, 1.0) * w as f32) as usize).min(w.saturating_sub(1));
    let x1 = ((region.right().clamp(0.0, 1.0) * w as f32).ceil() as usize).clamp(x0 + 1, w);
    let y0 = ((region.top().clamp(0.0, 1.0) * h as f32) as usize).min(h.saturating_sub(1));
    let y1 = ((region.bottom().clamp(0.0, 1.0) * h as f32).ceil() as usize).clamp(y0 + 1, h);
    let (mut n, mut pinned, mut sum) = (0u64, 0u64, 0.0f64);
    for y in y0..y1 {
        for x in x0..x1 {
            let i = 3 * (y * w + x);
            let Some(p) = image.pixels.get(i..i + 3) else {
                continue;
            };
            let top = p[0].max(p[1]).max(p[2]);
            n += 1;
            pinned += u64::from(top >= 0.98);
            sum += f64::from(0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]);
        }
    }
    if n == 0 {
        return (0.0, 0.0);
    }
    (pinned as f32 / n as f32, (sum / n as f64) as f32)
}

/// A pass the region would want (R2).
#[derive(Clone, Debug, PartialEq)]
pub(super) struct Proposal {
    pub label: String,
    pub why: String,
    pub tier: &'static str,
    /// The pass's shutter; `None` for a retake at the capture's own.
    pub shutter: Option<u64>,
}

/// What to take for a region with this pinned share and level.
pub(super) fn proposals(
    exposure: &CaptureExposure,
    pinned_share: f32,
    mean_level: f32,
) -> Vec<Proposal> {
    let mut out = Vec::new();
    let base = exposure.shutter.unwrap_or(0);
    let pick = |stops: f64| {
        crate::capture_workspace::plan::shorter_shutter(&exposure.options, base, stops)
    };
    if pinned_share > 0.0
        && let Some(shutter) = exposure.highlight.or_else(|| pick(4.0))
    {
        out.push(Proposal {
            label: format!(
                "Highlight pass at {}",
                crate::capture_workspace::style::shutter_label(shutter)
            ),
            why: format!(
                "{:.2} % of the region is at the pin; a short group at each plane holds it and the stack fuses it in",
                100.0 * pinned_share
            ),
            tier: "highlight",
            shutter: Some(shutter),
        });
    }
    if mean_level < 0.02
        && let Some(shutter) = pick(-2.0).filter(|s| *s != base)
    {
        out.push(Proposal {
            label: format!("Shadow pass at {}", crate::capture_workspace::style::shutter_label(shutter)),
            why: "The region is deep in shadow: a group with four times the light lowers its noise (photons count; M30)".into(),
            tier: "shadow",
            shutter: Some(shutter),
        });
    }
    out.push(Proposal {
        label: "Retake these planes".into(),
        why: "The same exposure again: for a group shaken or failed during the capture".into(),
        tier: "base",
        shutter: None,
    });
    out
}

impl StrehlApp {
    /// "Re-shoot…" from the core sample: the planes behind `region`
    /// (zero-based, inclusive) and what the region shows.
    pub(super) fn open_reshoot(&mut self, region: egui::Rect, first: usize, last: usize) {
        let (pinned_share, mean_level) = self
            .editor
            .loaded
            .as_ref()
            .map_or((0.0, 0.0), |l| region_levels(&l.preview, region));
        self.reshoot = Some(Reshoot {
            region,
            planes: (first as u64 + 1, last as u64 + 1),
            pinned_share,
            mean_level,
            sent: None,
        });
    }

    /// The re-shoot panel, while open.
    pub(super) fn reshoot_window(&mut self, ctx: &egui::Context) {
        let Some(mut state) = self.reshoot.clone() else {
            return;
        };
        let Some(capture) = self.stack.as_ref().map(|s| s.directory.clone()) else {
            self.reshoot = None;
            return;
        };
        let t = crate::studio_theme::tokens(ctx);
        let snapshot = self.capture.snapshot_typed();
        let host = &snapshot.host;
        let name = capture
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned();
        // R1: does the camera host still hold this capture?
        let same_run = host.retakes.as_ref().and_then(|r| r.run.as_deref()) == Some(name.as_str());
        let fresh = snapshot.fresh();
        let tiers = host.capabilities.exposure_tiers;
        let idle = !host.phase.active();
        let ready = fresh && same_run && idle;
        let exposure = capture_exposure(&capture);
        let planes: Vec<u64> = (state.planes.0..=state.planes.1).collect();
        let mut chosen: Option<Proposal> = None;
        let mut close = false;
        let mut restack = false;
        egui::Modal::new(egui::Id::new("stack-reshoot")).show(ctx, |ui| {
            ui.set_width(440.0);
            w::caps(ui, "Re-shoot this region");
            ui.add_space(6.0);
            ui.label(
                egui::RichText::new(format!(
                    "Planes {} to {} ({}) behind the region",
                    state.planes.0,
                    state.planes.1,
                    planes.len()
                ))
                .color(t.ink),
            );
            let rig = if !fresh {
                "Rig: the camera host is not answering.".to_owned()
            } else if !same_run {
                format!("Rig: the camera host's latest capture is not {name}: another was taken since, or the host restarted.")
            } else if !idle {
                "Rig: the camera is busy; wait for it.".to_owned()
            } else {
                "Rig: this capture is the camera host's latest; the pass goes into it. The camera is checked against the capture's exposure when the pass starts.".to_owned()
            };
            ui.label(egui::RichText::new(rig).color(if ready { t.ink2 } else { t.warn }).size(12.5));
            ui.add_space(8.0);
            for p in proposals(&exposure, state.pinned_share, state.mean_level) {
                let usable = ready && (p.tier == "base" || tiers);
                ui.horizontal_wrapped(|ui| {
                    if ui.add_enabled(usable, w::Button::new(&p.label)).clicked() {
                        chosen = Some(p.clone());
                    }
                    ui.label(egui::RichText::new(&p.why).color(t.ink2).size(12.0));
                });
                ui.add_space(4.0);
            }
            if let Some(sent) = &state.sent {
                ui.add_space(6.0);
                ui.label(egui::RichText::new(sent).color(t.ink).size(12.5));
                if ui
                    .add_enabled(idle && fresh, w::Button::new("Stack again"))
                    .on_hover_text("Read the capture again with its new groups and stack it")
                    .clicked()
                {
                    restack = true;
                }
            }
            ui.add_space(8.0);
            if ui.add(w::Button::new("Close")).clicked() {
                close = true;
            }
        });
        if let Some(p) = chosen {
            let result = match p.shutter {
                Some(shutter) => self.capture.queue_pass(planes.clone(), p.tier, shutter),
                None => self.capture.queue_retakes_after(planes.clone()),
            };
            state.sent = Some(match result {
                Ok(()) => format!(
                    "Asked: {} over {} planes. When the camera is done, stack again.",
                    p.label.to_lowercase(),
                    planes.len()
                ),
                Err(e) => format!("Not taken: {e:#}"),
            });
        }
        if restack {
            // R4: the capture read again (its new groups) and stacked.
            self.capture_names(&capture);
            self.import(capture.clone());
            self.stack_when_read = Some(capture);
            close = true;
        }
        self.reshoot = (!close).then_some(state);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_pinned_dark_region_gets_highlight_shadow_and_retake() {
        let exposure = CaptureExposure {
            iso: Some(100),
            // 1/4 s; offered 1/60, 1/250, 1 s.
            shutter: Some(65540),
            options: vec![65540, 65596, 65786, 655370],
            highlight: None,
        };
        let p = proposals(&exposure, 0.01, 0.01);
        let tiers: Vec<_> = p.iter().map(|p| p.tier).collect();
        assert_eq!(tiers, ["highlight", "shadow", "base"]);
        // Four stops shorter than 1/4 s is 1/64: 1/60 offered.
        assert_eq!(p[0].shutter, Some(65596));
        // Two stops longer is 1 s.
        assert_eq!(p[1].shutter, Some(655370));
        // A bright, unpinned region: only the retake.
        assert_eq!(proposals(&exposure, 0.0, 0.3).len(), 1);
        // The plan's own highlight shutter wins.
        let planned = CaptureExposure {
            highlight: Some(65786),
            ..exposure
        };
        assert_eq!(proposals(&planned, 0.5, 0.3)[0].shutter, Some(65786));
    }

    #[test]
    fn region_levels_count_pinned_pixels_and_the_mean() {
        let mut pixels = vec![0.01f32; 3 * 10 * 10];
        // Two pinned pixels in the left half.
        for i in [0usize, 11] {
            pixels[3 * i + 1] = 1.0;
        }
        let image = strehl_edit::LinearImage {
            width: 10,
            height: 10,
            pixels,
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: None,
            baked_recipe: None,
        };
        let (pinned, mean) = region_levels(
            &image,
            egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(0.5, 1.0)),
        );
        assert!((pinned - 2.0 / 50.0).abs() < 1e-6, "{pinned}");
        assert!(mean > 0.01 && mean < 0.05, "{mean}");
    }
}
