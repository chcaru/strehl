//! Correct the pinned Windows backend's nonclient drag message while preserving
//! its native move/resize loop and synthetic release bookkeeping.
//!
//! winit 0.30.13's handle_os_dragging passes a POINTS pointer as LPARAM. Win32
//! instead requires the two signed screen coordinates packed into that value:
//! https://learn.microsoft.com/windows/win32/inputdev/wm-nclbuttondown
use std::sync::{
    OnceLock,
    atomic::{AtomicUsize, Ordering},
};
use windows_sys::Win32::{
    Foundation::{HWND, LPARAM, LRESULT, POINT, WPARAM},
    UI::{
        Input::KeyboardAndMouse::{GetActiveWindow, GetAsyncKeyState, VK_LBUTTON},
        Shell::{DefSubclassProc, RemoveWindowSubclass, SetWindowSubclass},
        WindowsAndMessaging::{
            GetCursorPos, GetWindowThreadProcessId, HTBOTTOMRIGHT, HTCAPTION, HTLEFT, WM_NCDESTROY,
            WM_NCLBUTTONDOWN,
        },
    },
};

const SUBCLASS: usize = 0x5354_5248;

/// Called on eframe's event thread immediately before its native drag command.
/// GetActiveWindow only returns a window attached to this calling thread; the
/// process check further excludes every HWND not owned by this application.
pub(crate) fn prepare_drag() {
    // SAFETY: This runs on the window's event thread. The callback has static
    // lifetime, stores no borrowed state, and removes itself at WM_NCDESTROY.
    unsafe {
        let window = GetActiveWindow();
        if window.is_null() {
            return;
        }
        let mut owner = 0;
        GetWindowThreadProcessId(window, &mut owner);
        if owner != std::process::id() {
            return;
        }
        let installed = SetWindowSubclass(window, Some(correct_drag_message), SUBCLASS, 0) != 0;
        trace(|| format!("installed={installed} hwnd={window:p}"));
    }
}

fn packed_screen_point(x: i32, y: i32) -> LPARAM {
    ((u32::from(x as i16 as u16)) | (u32::from(y as i16 as u16) << 16)) as LPARAM
}

fn is_drag_message(message: u32, hit: WPARAM) -> bool {
    message == WM_NCLBUTTONDOWN
        && (hit == HTCAPTION as usize || (HTLEFT as usize..=HTBOTTOMRIGHT as usize).contains(&hit))
}

unsafe extern "system" fn correct_drag_message(
    window: HWND,
    message: u32,
    hit: WPARAM,
    mut coordinates: LPARAM,
    id: usize,
    _: usize,
) -> LRESULT {
    if is_drag_message(message, hit) {
        let mut point = POINT { x: 0, y: 0 };
        // SAFETY: point is writable for the call. All coordinates stay in the
        // native physical-screen gauge; no DPI/client-space conversion occurs.
        if unsafe { GetCursorPos(&mut point) } != 0 {
            let packed = packed_screen_point(point.x, point.y);
            trace(|| {
                format!(
                    "hit={hit} screen={},{} old={coordinates:#x} packed={packed:#x} primary_down={}",
                    point.x,
                    point.y,
                    unsafe { GetAsyncKeyState(VK_LBUTTON as i32) } < 0
                )
            });
            coordinates = packed;
        }
    } else if message == WM_NCDESTROY {
        // SAFETY: This callback is running on its HWND's own thread. Remove
        // only our registration and continue the existing destruction chain.
        unsafe {
            RemoveWindowSubclass(window, Some(correct_drag_message), id);
        }
    }
    // SAFETY: All messages chain through the common-controls subclass API.
    // winit remains responsible for native state, event delivery and release.
    unsafe { DefSubclassProc(window, message, hit, coordinates) }
}

fn trace(message: impl FnOnce() -> String) {
    static ENABLED: OnceLock<bool> = OnceLock::new();
    static COUNT: AtomicUsize = AtomicUsize::new(0);
    if *ENABLED
        .get_or_init(|| std::env::var("STREHL_UI_CHROME_TRACE").is_ok_and(|value| value == "1"))
        && COUNT.fetch_add(1, Ordering::Relaxed) < 32
    {
        eprintln!("STREHL_CHROME {}", message());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use windows_sys::Win32::UI::WindowsAndMessaging::{HTCLIENT, HTCLOSE, WM_LBUTTONDOWN};

    #[test]
    fn drag_coordinates_are_packed_values_including_negative_monitor_origins() {
        assert_eq!(packed_screen_point(640, 480), 0x01e0_0280);
        assert_eq!(packed_screen_point(-3, -2), 0xfffe_fffd);
        for (x, y) in [(-1920, 240), (700, -1080), (-32768, 32767), (32767, -32768)] {
            let packed = packed_screen_point(x, y) as u32;
            // Independent receiver-side Win32 GET_X/Y_LPARAM semantics.
            assert_eq!((packed & 0xffff) as i16 as i32, x);
            assert_eq!((packed >> 16) as i16 as i32, y);
        }
        let point = POINT { x: 640, y: 480 };
        assert_ne!(
            packed_screen_point(point.x, point.y),
            &point as *const POINT as LPARAM,
            "The previous backend's pointer encoding must fail the same receiver contract"
        );
    }

    #[test]
    fn correction_covers_only_caption_and_resize_messages() {
        assert!(is_drag_message(WM_NCLBUTTONDOWN, HTCAPTION as usize));
        for hit in HTLEFT..=HTBOTTOMRIGHT {
            assert!(is_drag_message(WM_NCLBUTTONDOWN, hit as usize));
        }
        assert!(!is_drag_message(WM_LBUTTONDOWN, HTCAPTION as usize));
        assert!(!is_drag_message(WM_NCLBUTTONDOWN, HTCLIENT as usize));
        assert!(!is_drag_message(WM_NCLBUTTONDOWN, HTCLOSE as usize));
        assert!(!is_drag_message(WM_NCDESTROY, HTLEFT as usize));
    }
}
