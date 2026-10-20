//! Native, event-driven desktop shell. The existing CLI owns all RAW processing.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

#[path = "agent-interface.rs"]
mod agent_interface;
mod app;
#[path = "bracket-browser.rs"]
mod bracket_browser;
#[path = "capture-axis.rs"]
#[cfg(test)]
mod capture_axis;
mod controls;
#[path = "draft-preview.rs"]
mod draft_preview;
#[path = "edit-workspace.rs"]
mod edit_workspace;
mod engine;
#[path = "image-gesture.rs"]
mod image_gesture;
mod jobs;
mod pipeline;
mod preview;
#[path = "process-admission-regions.rs"]
mod process_admission_regions;
#[path = "process-balance.rs"]
mod process_balance;
#[path = "process-contribution.rs"]
mod process_contribution;
#[path = "process-fingerprint.rs"]
mod process_fingerprint;
#[path = "process-journey.rs"]
mod process_journey;
#[path = "process-ledger.rs"]
mod process_ledger;
#[path = "process-navigator.rs"]
mod process_navigator;
#[path = "process-network.rs"]
mod process_network;
#[path = "process-output-space.rs"]
mod process_output_space;
#[path = "process-participation.rs"]
mod process_participation;
#[path = "process-provenance.rs"]
mod process_provenance;
#[path = "process-region-probe.rs"]
mod process_region_probe;
#[path = "process-result.rs"]
mod process_result;
#[path = "process-revision.rs"]
mod process_revision;
#[path = "process-revision-view.rs"]
mod process_revision_view;
#[path = "process-sample-glyphs.rs"]
mod process_sample_glyphs;
#[path = "process-scales.rs"]
mod process_scales;
#[path = "process-space.rs"]
mod process_space;
#[path = "process-theater.rs"]
mod process_theater;
#[path = "processing-view.rs"]
mod processing_view;
#[path = "project-explorer.rs"]
mod project_explorer;
#[path = "source-browser.rs"]
mod source_browser;
#[path = "source-preview.rs"]
mod source_preview;
#[path = "stack-map.rs"]
mod stack_map;
mod theme;
#[path = "ui-icon.rs"]
mod ui_icon;
mod viewer;
#[path = "window-chrome.rs"]
mod window_chrome;
#[cfg(windows)]
#[path = "window-native.rs"]
mod window_native;
mod workbench;
#[path = "workspace-history.rs"]
mod workspace_history;
#[path = "workspace-icons.rs"]
mod workspace_icons;
#[path = "workspace-layout.rs"]
mod workspace_layout;

use std::path::PathBuf;

#[derive(Default)]
pub struct LaunchOptions {
    pub source: Option<PathBuf>,
    pub open_run: Option<PathBuf>,
    pub browse: Option<PathBuf>,
    pub preview: Option<PathBuf>,
    pub engine: Option<PathBuf>,
    pub screenshot: Option<PathBuf>,
    pub screenshot_hover: Option<[f32; 2]>,
    pub screenshot_ranges: Option<Vec<[usize; 2]>>,
    pub size: Option<[f32; 2]>,
    pub activity_log: Option<PathBuf>,
    pub draft: bool,
    pub reveal_at_ms: Option<f64>,
    pub workbench: Option<workbench::WorkbenchMode>,
    pub probe_at: Option<[f32; 2]>,
    pub process: bool,
    pub edit: bool,
    pub agent: bool,
}

fn parse_screenshot_ranges(value: &str) -> Option<Vec<[usize; 2]>> {
    let mut ranges = Vec::new();
    for range in value.split(',') {
        if ranges.len() == 8 {
            return None;
        }
        let (start, end) = range.split_once('-')?;
        let start = start.parse::<usize>().ok()?.checked_sub(1)?;
        let end = end.parse::<usize>().ok()?.checked_sub(1)?;
        if start > end {
            return None;
        }
        ranges.push([start, end]);
    }
    Some(ranges)
}

fn main() -> eframe::Result {
    if let Some(code) = agent_interface::run_mcp_from_args() {
        std::process::exit(code);
    }
    if let Some(code) = engine::run_worker() {
        std::process::exit(code);
    }
    let mut launch = LaunchOptions::default();
    let mut args = std::env::args_os().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--edit" {
            launch.edit = true;
            continue;
        }
        if arg == "--agent" {
            launch.agent = true;
            continue;
        }
        if arg == "--process" {
            launch.process = true;
            continue;
        }
        if arg == "--space" {
            eprintln!(
                "The experimental 3D viewer has been retired. Open the process workspace instead."
            );
            std::process::exit(2);
        }
        if arg == "--screenshot-ranges" {
            launch.screenshot_ranges = args
                .next()
                .and_then(|value| value.to_str().and_then(parse_screenshot_ranges));
            if launch.screenshot_ranges.is_none() {
                eprintln!(
                    "Use --screenshot-ranges START-END[,START-END] with 1 to 8 inclusive, one-based capture ranges"
                );
                std::process::exit(2);
            }
            continue;
        }
        if arg == "--probe-at" || arg == "--screenshot-hover" {
            let point = args.next().and_then(|s| {
                s.to_str().and_then(|s| {
                    let (x, y) = s.split_once(',')?;
                    Some([x.parse::<f32>().ok()?, y.parse::<f32>().ok()?])
                })
            });
            if !point.is_some_and(|point| {
                point
                    .iter()
                    .all(|v| v.is_finite() && (0.0..=1.0).contains(v))
            }) {
                eprintln!(
                    "Use {} X,Y with normalized coordinates from 0 to 1",
                    arg.to_string_lossy()
                );
                std::process::exit(2);
            }
            if arg == "--screenshot-hover" {
                launch.screenshot_hover = point;
            } else {
                launch.probe_at = point;
            }
            continue;
        }
        if arg == "--workbench" {
            launch.workbench = match args
                .next()
                .and_then(|s| s.to_str().map(str::to_owned))
                .as_deref()
            {
                Some("probe") => Some(workbench::WorkbenchMode::Probe),
                Some("compare") => Some(workbench::WorkbenchMode::Compare),
                _ => {
                    eprintln!("Use --workbench probe|compare");
                    std::process::exit(2);
                }
            };
            continue;
        }
        if arg == "--reveal-at" {
            launch.reveal_at_ms = args
                .next()
                .and_then(|s| s.to_str().and_then(|s| s.parse::<f64>().ok()));
            if !launch
                .reveal_at_ms
                .is_some_and(|value| value.is_finite() && (0.0..=5000.0).contains(&value))
            {
                eprintln!("Use --reveal-at MILLISECONDS (0 to 5000)");
                std::process::exit(2);
            }
            continue;
        }
        if arg == "--draft" {
            launch.draft = true;
            continue;
        }
        if arg == "--size" {
            let value = args.next().and_then(|s| s.to_str().map(str::to_owned));
            launch.size = value.and_then(|s| {
                let (w, h) = s.split_once('x')?;
                Some([w.parse().ok()?, h.parse().ok()?])
            });
            if !launch.size.is_some_and(|s| {
                s.iter()
                    .all(|v| v.is_finite() && *v >= 600.0 && *v <= 4000.0)
            }) {
                eprintln!("Use --size WIDTHxHEIGHT");
                std::process::exit(2);
            }
            continue;
        }
        let value = match arg.to_str() {
            Some("--source") => &mut launch.source,
            Some("--open-run") => &mut launch.open_run,
            Some("--browse") => &mut launch.browse,
            Some("--preview") => &mut launch.preview,
            Some("--engine") => &mut launch.engine,
            Some("--screenshot") => &mut launch.screenshot,
            Some("--activity-log") => &mut launch.activity_log,
            _ => {
                eprintln!(
                    "Usage: Strehl [--source DIR] [--open-run DIR] [--browse DIR] [--preview IMAGE] [--engine EXE] [--process] [--edit] [--agent] [--screenshot PNG]"
                );
                std::process::exit(2);
            }
        };
        *value = args.next().map(PathBuf::from);
        if value.is_none() {
            eprintln!("Missing value for {}", arg.to_string_lossy());
            std::process::exit(2);
        }
    }
    if launch.reveal_at_ms.is_some() && (launch.screenshot.is_none() || launch.source.is_none()) {
        eprintln!("--reveal-at requires --source and --screenshot for GPU transition inspection");
        std::process::exit(2);
    }
    if launch.screenshot_hover.is_some() && launch.screenshot.is_none() {
        eprintln!("--screenshot-hover requires --screenshot; it never moves the desktop pointer");
        std::process::exit(2);
    }
    if launch.screenshot_ranges.is_some() && launch.screenshot.is_none() {
        eprintln!("--screenshot-ranges requires --screenshot");
        std::process::exit(2);
    }
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size(launch.size.unwrap_or([1440.0, 940.0]))
            .with_min_inner_size([1060.0, 720.0])
            .with_decorations(false)
            .with_icon(ui_icon::application_icon())
            .with_title("Strehl"),
        renderer: eframe::Renderer::Wgpu,
        // Keep at most one presentation in flight: camera inspection should
        // follow the newest pointer position without a queue of stale views.
        wgpu_options: eframe::egui_wgpu::WgpuConfiguration {
            desired_maximum_frame_latency: Some(1),
            ..Default::default()
        },
        ..Default::default()
    };
    eframe::run_native(
        "Strehl",
        options,
        Box::new(move |cc| Ok(Box::new(app::StrehlApp::new(cc, launch)))),
    )
}

#[cfg(test)]
mod launch_tests {
    use super::parse_screenshot_ranges;

    #[test]
    fn screenshot_ranges_are_one_based_inclusive_and_bounded() {
        assert_eq!(
            parse_screenshot_ranges("20-55,80-115"),
            Some(vec![[19, 54], [79, 114]])
        );
        assert_eq!(parse_screenshot_ranges("1-1"), Some(vec![[0, 0]]));
        assert_eq!(
            parse_screenshot_ranges("1-1,2-2,3-3,4-4,5-5,6-6,7-7,8-8")
                .unwrap()
                .len(),
            8
        );
        for invalid in [
            "",
            "0-1",
            "1-0",
            "55-20",
            "1",
            "1-2,",
            "1-2-3",
            "-1-2",
            "1-1,2-2,3-3,4-4,5-5,6-6,7-7,8-8,9-9",
        ] {
            assert!(parse_screenshot_ranges(invalid).is_none(), "{invalid}");
        }
        let overflow = format!("1-{}0", usize::MAX);
        assert!(parse_screenshot_ranges(&overflow).is_none());
    }
}
