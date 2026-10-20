//! Read-only Windows display state. No OS color setting is ever changed.
use super::DisplayStatus;
use windows::{
    Win32::Graphics::Dxgi::Common::DXGI_COLOR_SPACE_RGB_FULL_G2084_NONE_P2020,
    Win32::Graphics::Dxgi::{CreateDXGIFactory1, IDXGIFactory1, IDXGIOutput6},
    core::Interface,
};
use windows_sys::Win32::{
    Devices::Display::*,
    Foundation::HWND,
    Graphics::Gdi::{MONITOR_DEFAULTTOPRIMARY, MonitorFromWindow},
};

fn wide(value: &[u16]) -> String {
    String::from_utf16_lossy(&value[..value.iter().position(|v| *v == 0).unwrap_or(value.len())])
}

pub(super) fn detect(window: usize) -> DisplayStatus {
    match query(window) {
        Ok(value) => value,
        Err(error) => DisplayStatus {
            reason: format!("SDR: display capability query failed: {error}"),
            ..Default::default()
        },
    }
}

fn query(window: usize) -> windows::core::Result<DisplayStatus> {
    // SAFETY: HWND is only queried; a destroyed handle returns no monitor. COM
    // interfaces are owned smart pointers. All enumerations have fixed bounds.
    unsafe {
        let monitor = MonitorFromWindow(window as HWND, MONITOR_DEFAULTTOPRIMARY);
        let factory: IDXGIFactory1 = CreateDXGIFactory1()?;
        for adapter_index in 0..32 {
            let Ok(adapter) = factory.EnumAdapters1(adapter_index) else {
                break;
            };
            for output_index in 0..32 {
                let Ok(output) = adapter.EnumOutputs(output_index) else {
                    break;
                };
                let desc = output.GetDesc()?;
                if desc.Monitor.0 != monitor {
                    continue;
                }
                let name = wide(&desc.DeviceName);
                let output6 = output.cast::<IDXGIOutput6>()?;
                let current = output6.GetDesc1()?;
                // Advanced Color alone can mean wide-gamut SDR. The actual
                // output color space identifies HDR, unlike the generic flag.
                let active = current.ColorSpace == DXGI_COLOR_SPACE_RGB_FULL_G2084_NONE_P2020;
                let reported_white = if active { sdr_white(&name) } else { Some(80.0) };
                let white = reported_white.unwrap_or(80.0);
                let valid_peak = current.MaxLuminance.is_finite() && current.MaxLuminance >= white;
                let peak = if active && valid_peak {
                    current.MaxLuminance
                } else {
                    white
                };
                return Ok(DisplayStatus {
                    active: active && valid_peak && reported_white.is_some(),
                    supported: active,
                    backend: format!("DXGI · {}", wide(&adapter.GetDesc1()?.Description)),
                    monitor: name,
                    sdr_white_nits: white,
                    peak_nits: peak,
                    headroom: (peak / white).max(1.0),
                    reason: if !active {
                        "Windows HDR is off for this display".into()
                    } else if reported_white.is_none() {
                        "SDR: Windows did not report its SDR white level".into()
                    } else if !valid_peak {
                        "SDR: Windows did not report usable HDR luminance".into()
                    } else {
                        "Native scRGB · Windows HDR enabled".into()
                    },
                });
            }
        }
    }
    Ok(DisplayStatus {
        reason: "SDR: this window's display was not found".into(),
        ..Default::default()
    })
}

fn sdr_white(device: &str) -> Option<f32> {
    // DisplayConfig reports SDR white in milli-units of the 80-nit scRGB white.
    // Retry if the monitor topology changes between sizing and enumeration.
    unsafe {
        for _ in 0..3 {
            let (mut paths, mut modes) = (0, 0);
            if GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, &mut paths, &mut modes) != 0
                || paths > 128
                || modes > 512
            {
                return None;
            }
            let mut path_info = vec![DISPLAYCONFIG_PATH_INFO::default(); paths as usize];
            let mut mode_info = vec![DISPLAYCONFIG_MODE_INFO::default(); modes as usize];
            let code = QueryDisplayConfig(
                QDC_ONLY_ACTIVE_PATHS,
                &mut paths,
                path_info.as_mut_ptr(),
                &mut modes,
                mode_info.as_mut_ptr(),
                std::ptr::null_mut(),
            );
            if code == 122 {
                continue;
            } // ERROR_INSUFFICIENT_BUFFER after topology change
            if code != 0 {
                return None;
            }
            for path in path_info.iter().take(paths as usize) {
                let mut name = DISPLAYCONFIG_SOURCE_DEVICE_NAME {
                    header: DISPLAYCONFIG_DEVICE_INFO_HEADER {
                        r#type: DISPLAYCONFIG_DEVICE_INFO_GET_SOURCE_NAME,
                        size: std::mem::size_of::<DISPLAYCONFIG_SOURCE_DEVICE_NAME>() as u32,
                        adapterId: path.sourceInfo.adapterId,
                        id: path.sourceInfo.id,
                    },
                    ..Default::default()
                };
                if DisplayConfigGetDeviceInfo(&mut name.header) != 0
                    || !wide(&name.viewGdiDeviceName).eq_ignore_ascii_case(device)
                {
                    continue;
                }
                let mut white = DISPLAYCONFIG_SDR_WHITE_LEVEL {
                    header: DISPLAYCONFIG_DEVICE_INFO_HEADER {
                        r#type: DISPLAYCONFIG_DEVICE_INFO_GET_SDR_WHITE_LEVEL,
                        size: std::mem::size_of::<DISPLAYCONFIG_SDR_WHITE_LEVEL>() as u32,
                        adapterId: path.targetInfo.adapterId,
                        id: path.targetInfo.id,
                    },
                    ..Default::default()
                };
                if DisplayConfigGetDeviceInfo(&mut white.header) == 0 && white.SDRWhiteLevel >= 1000
                {
                    return Some((white.SDRWhiteLevel as f32 * 0.08).clamp(80.0, 1000.0));
                }
            }
        }
    }
    None
}
