//! EDR configuration and live headroom, on the AppKit/event thread only.
// objc 0.2's message macros contain their legacy `cargo-clippy` feature guard.
// It is expanded in this module, although it is not a Strehl Cargo feature.
#![allow(unexpected_cfgs)]
use super::DisplayStatus;
use objc::{
    class, msg_send,
    runtime::{BOOL, Object, YES},
    sel, sel_impl,
};
use std::ffi::c_void;

#[link(name = "CoreGraphics", kind = "framework")]
unsafe extern "C" {
    static kCGColorSpaceExtendedLinearSRGB: *const c_void;
    fn CGColorSpaceCreateWithName(name: *const c_void) -> *const c_void;
    fn CGColorSpaceRelease(space: *const c_void);
}

pub(super) fn configure(view: usize) -> bool {
    if view == 0 {
        return false;
    }
    // SAFETY: CreationContext owns a live NSView, and this runs on its event
    // thread. Only CAMetalLayer descendants of that view receive color settings.
    unsafe {
        let root: *mut Object = msg_send![view as *mut Object, layer];
        let color = CGColorSpaceCreateWithName(kCGColorSpaceExtendedLinearSRGB);
        let configured = !root.is_null() && !color.is_null() && configure_layer(root, color, 0);
        if !color.is_null() {
            CGColorSpaceRelease(color);
        }
        configured
    }
}

unsafe fn configure_layer(layer: *mut Object, color: *const c_void, depth: usize) -> bool {
    if layer.is_null() || depth > 8 {
        return false;
    }
    unsafe {
        let metal: BOOL = msg_send![layer, isKindOfClass:class!(CAMetalLayer)];
        let mut configured = false;
        if metal == YES {
            let _: () = msg_send![layer, setColorspace:color];
            let _: () = msg_send![layer, setWantsExtendedDynamicRangeContent:YES];
            let current: *const c_void = msg_send![layer, colorspace];
            let extended: BOOL = msg_send![layer, wantsExtendedDynamicRangeContent];
            configured = current == color && extended == YES;
        }
        let children: *mut Object = msg_send![layer, sublayers];
        if children.is_null() {
            return configured;
        }
        let count: usize = msg_send![children, count];
        for index in 0..count.min(32) {
            let child: *mut Object = msg_send![children, objectAtIndex:index];
            configured |= configure_layer(child, color, depth + 1);
        }
        configured
    }
}

pub(super) fn detect(view: usize) -> DisplayStatus {
    if view == 0 {
        return DisplayStatus::default();
    }
    unsafe {
        let window: *mut Object = msg_send![view as *mut Object, window];
        if window.is_null() {
            return DisplayStatus::default();
        }
        let screen: *mut Object = msg_send![window, screen];
        if screen.is_null() {
            return DisplayStatus::default();
        }
        let current: f64 = msg_send![screen, maximumExtendedDynamicRangeColorComponentValue];
        let potential: f64 = msg_send![
            screen,
            maximumPotentialExtendedDynamicRangeColorComponentValue
        ];
        let headroom = if current.is_finite() {
            (current as f32).clamp(1.0, 125.0)
        } else {
            1.0
        };
        DisplayStatus {
            active: headroom > 1.001,
            supported: potential > 1.001,
            backend: String::new(),
            monitor: "Current macOS display".into(),
            // AppKit EDR is relative to current SDR white; it does not provide
            // an absolute nit measurement here. Zero means unreported.
            sdr_white_nits: 0.0,
            peak_nits: 0.0,
            headroom,
            reason: if headroom > 1.001 {
                "Native EDR · brightness relative to current SDR white".into()
            } else {
                "SDR: current macOS display brightness leaves no EDR headroom".into()
            },
        }
    }
}
