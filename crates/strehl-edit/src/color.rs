//! Output primaries and transforms. Every RGB space here uses the D65 white.
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum OutputColorSpace {
    Srgb,
    DisplayP3,
    #[default]
    Rec2020,
}

impl OutputColorSpace {
    pub fn label(self) -> &'static str {
        match self {
            Self::Srgb => "sRGB / BT.709",
            Self::DisplayP3 => "Display P3",
            Self::Rec2020 => "Rec.2020",
        }
    }

    pub(crate) fn primaries(self) -> [[f64; 2]; 3] {
        match self {
            Self::Srgb => [[0.64, 0.33], [0.30, 0.60], [0.15, 0.06]],
            Self::DisplayP3 => [[0.68, 0.32], [0.265, 0.69], [0.15, 0.06]],
            Self::Rec2020 => [[0.708, 0.292], [0.170, 0.797], [0.131, 0.046]],
        }
    }

    /// Linear BT.709 to output RGB, derived from D65 RGB-to-XYZ matrices.
    pub(crate) fn convert_from_linear_srgb(self, p: [f32; 3]) -> [f32; 3] {
        let m = match self {
            Self::Srgb => return p,
            Self::DisplayP3 => [
                [0.822_462, 0.177_538, 0.0],
                [0.033_194, 0.966_806, 0.0],
                [0.017_083, 0.072_397, 0.910_520],
            ],
            Self::Rec2020 => [
                [0.627_404, 0.329_283, 0.043_313],
                [0.069_097, 0.919_540, 0.011_363],
                [0.016_391, 0.088_013, 0.895_596],
            ],
        };
        // D65 is shared, so neutral values must remain exactly neutral even at
        // the metadata ceil boundary (e.g. a 203-nit white stays 203, not 204).
        m.map(|r| p[1] + r[0] * (p[0] - p[1]) + r[2] * (p[2] - p[1]))
    }

    pub(crate) fn luminance(self, p: [f32; 3]) -> f32 {
        let (kr, kb) = match self {
            Self::Srgb => (0.2126, 0.0722),
            Self::DisplayP3 => (0.228_975, 0.079_287),
            Self::Rec2020 => (0.2627, 0.0593),
        };
        p[1] + kr * (p[0] - p[1]) + kb * (p[2] - p[1])
    }

    pub(crate) fn to_linear_srgb(self, p: [f32; 3]) -> [f32; 3] {
        let m = match self {
            Self::Srgb => return p,
            Self::DisplayP3 => [
                [1.224_94, -0.224_940, 0.0],
                [-0.042_057, 1.042_057, 0.0],
                [-0.019_638, -0.078_636, 1.098_274],
            ],
            Self::Rec2020 => [
                [1.660_491, -0.587_641, -0.072_850],
                [-0.124_550, 1.132_9, -0.008_350],
                [-0.018_151, -0.100_579, 1.118_73],
            ],
        };
        m.map(|r| p[1] + r[0] * (p[0] - p[1]) + r[2] * (p[2] - p[1]))
    }

    /// YCbCr is an invertible transport transform, independent of RGB primaries.
    /// P3 uses the well-supported BT.709 transform and signals it explicitly.
    pub(crate) fn ycbcr_coefficients(self) -> (f32, f32) {
        match self {
            Self::Rec2020 => (0.2627, 0.0593),
            _ => (0.2126, 0.0722),
        }
    }
}

pub(crate) fn decode_srgb(v: f32) -> f32 {
    if v <= 0.04045 {
        v / 12.92
    } else {
        ((v + 0.055) / 1.055).powf(2.4)
    }
}
