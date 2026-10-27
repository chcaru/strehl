//! Exact saved f32 inputs at six real-size arithmetic failures; no RAW I/O.
//! References are independently reviewed80-digit evaluations, rounded to f64
//! only for test comparison. This tests coordinates, not optical calibration.
use super::{
    CropRect, FramePull, NativeSimilarity, PlaneGeometry, RadialCurve, ResearchPull, Similarity,
};
use strehl_core::align::Cx;

struct Case {
    name: &'static str,
    channel: usize,
    anchor: [u32; 6],
    anchor_knots: [i16; 16],
    source: [u32; 6],
    source_knots: [i16; 16],
    placement: [u32; 6],
    ca: [[u32; 6]; 3],
    crop: [usize; 4],
    point: [u32; 2],
    reference: [f64; 2],
    saved_split: [u32; 2],
}
fn curve(v: [u32; 6], knots: [i16; 16]) -> RadialCurve {
    let v = v.map(f32::from_bits);
    RadialCurve {
        center: [v[0], v[1]],
        reference_radius: v[2],
        input_scale: v[3],
        output_scale: v[4],
        max_input_radius: v[5],
        knots,
    }
}
fn similarity(v: [u32; 6]) -> NativeSimilarity {
    let v = v.map(f32::from_bits);
    NativeSimilarity {
        a: [v[0], v[1]],
        b: [v[2], v[3]],
        center: [v[4], v[5]],
    }
}
fn error(p: [f32; 2], reference: [f64; 2]) -> f64 {
    (p[0] as f64 - reference[0]).hypot(p[1] as f64 - reference[1])
}
const CASES: [Case; 6] = [
    Case {
        name: "bee3-anchor-fixed-1061245",
        channel: 2,
        // Bound source index77, SHA256 39ba6f53c14e5927aa8bd1bd84e971523317221257efd10d2ff1ad04a4909e8f.
        anchor: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        anchor_knots: [
            0, -1, -2, -3, -4, -5, -8, -10, -13, -13, -15, -17, -17, -17, -15, -13,
        ],
        source: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        source_knots: [
            0, -1, -2, -3, -4, -5, -8, -10, -13, -13, -15, -17, -17, -17, -15, -13,
        ],
        placement: [
            0x3f830358, 0xbaa682a1, 0x412068e8, 0xc09831f7, 0x455bc800, 0x45128800,
        ],
        ca: [
            [
                0x3f7fdeae, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f800000, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f8005b7, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
        ],
        crop: [136, 136, 3244, 2072],
        point: [0x45ad3980, 0x457e6400],
        reference: [5603.407055686214, 4103.80200993286],
        saved_split: [0x45af1b40, 0x45803e69],
    },
    Case {
        name: "bee3-anchor-fixed-1646190",
        channel: 0,
        // Bound source index269, SHA256 f2da2cef580396bbe56bce287754045bc71dfe63335a0532cbb53c9ba76418ac.
        anchor: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        anchor_knots: [
            0, -1, -2, -3, -4, -5, -8, -10, -13, -13, -15, -17, -17, -17, -15, -13,
        ],
        source: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        source_knots: [
            0, -1, -2, -3, -4, -5, -8, -10, -13, -13, -15, -17, -17, -17, -15, -13,
        ],
        placement: [
            0x3f787489, 0x3adc92df, 0x412eb627, 0xc1538748, 0x455bc800, 0x45128800,
        ],
        ca: [
            [
                0x3f7fdeae, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f800000, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f8005b7, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
        ],
        crop: [136, 136, 3244, 2072],
        point: [0x4593e680, 0x4589f800],
        reference: [4703.787805788564, 4341.7991591302],
        saved_split: [0x4592fe4f, 0x4587ae66],
    },
    Case {
        name: "slide2-anchor-fixed-957355",
        channel: 2,
        // Bound source index43, SHA256 e952891b506e3a3b81f38eac53fe6fa6f4c5c66ed8df23241737cd49a07e03ab.
        anchor: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        anchor_knots: [
            0, -1, -2, -3, -4, -5, -7, -9, -12, -13, -14, -15, -15, -14, -13, -12,
        ],
        source: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        source_knots: [
            0, -1, -2, -3, -4, -5, -7, -9, -12, -13, -14, -15, -15, -14, -13, -12,
        ],
        placement: [
            0x3f86c10f, 0xba45ee07, 0x41c19a47, 0x3d276882, 0x455bc800, 0x45128800,
        ],
        ca: [
            [
                0x3f7fdeae, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f800000, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f8005b7, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
        ],
        crop: [146, 146, 3224, 2052],
        point: [0x45d29800, 0x45895800],
        reference: [6935.531049679687, 4501.286310924534],
        saved_split: [0x45d8bc3e, 0x458caa49],
    },
    Case {
        name: "slide2-anchor-fixed-1141793",
        channel: 0,
        // Bound source index104, SHA256 89c06b3ee20d4af65e788adde04c656e1dcf06c21632c4fc9024e45dfe9eaa2a.
        anchor: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        anchor_knots: [
            0, -1, -2, -3, -4, -5, -7, -9, -12, -13, -14, -15, -15, -14, -13, -12,
        ],
        source: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        source_knots: [
            0, -1, -2, -3, -4, -5, -7, -9, -12, -13, -14, -15, -15, -14, -13, -12,
        ],
        placement: [
            0x3f82ebba, 0x3a9fc847, 0x41066785, 0x40ac9532, 0x455bc800, 0x45128800,
        ],
        ca: [
            [
                0x3f7fdeae, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f800000, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f8005b7, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
        ],
        crop: [146, 146, 3224, 2052],
        point: [0x45c60880, 0x45895800],
        reference: [6405.9038839550085, 4449.58679275023],
        saved_split: [0x45c82f3a, 0x458b0cb0],
    },
    Case {
        name: "slide2-anchor-fixed-1544290",
        channel: 2,
        // Bound source index235, SHA256 ca21f219d888bd4c0ccf4ad7c9823057fbd5e1b134fc151359896d08228ee69c.
        anchor: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        anchor_knots: [
            0, -1, -2, -3, -4, -5, -7, -9, -12, -13, -14, -15, -15, -14, -13, -12,
        ],
        source: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        source_knots: [
            0, -1, -2, -3, -4, -5, -7, -9, -12, -13, -14, -15, -15, -14, -13, -12,
        ],
        placement: [
            0x3f777ed6, 0xbc6a6a02, 0xc19eddd3, 0xc1d66301, 0x455bc800, 0x45128800,
        ],
        ca: [
            [
                0x3f7fdeae, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f800000, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f8005b7, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
        ],
        crop: [146, 146, 3224, 2052],
        point: [0x4593aa80, 0x45895800],
        reference: [4694.883346398435, 4283.192983862825],
        saved_split: [0x4592b710, 0x4585d98d],
    },
    Case {
        name: "slide2-per-frame-856469",
        channel: 2,
        // Bound source index10, SHA256 4ad99c8aaec850f1dec806efb8a7c5ddfc8699969946465ea326c8250b0aac1b.
        anchor: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        anchor_knots: [
            0, -1, -2, -3, -4, -5, -7, -9, -12, -13, -14, -15, -15, -14, -13, -12,
        ],
        source: [
            0x455bb800, 0x45127800, 0x458394b9, 0x3f800000, 0x3f800000, 0x45c55f16,
        ],
        source_knots: [
            0, -1, -2, -3, -4, -5, -7, -8, -11, -12, -13, -13, -13, -12, -9, -6,
        ],
        placement: [
            0x3f8898e2, 0xbb1563c6, 0x4202e5b8, 0xc0834a0e, 0x455bc800, 0x45128800,
        ],
        ca: [
            [
                0x3f7fdeae, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f800000, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
            [
                0x3f8005b7, 0x00000000, 0x00000000, 0x00000000, 0x455bc000, 0x45128000,
            ],
        ],
        crop: [146, 146, 3224, 2052],
        point: [0x45acd980, 0x45895800],
        reference: [5704.424606333981, 4524.578796498034],
        saved_split: [0x45b24367, 0x458d64a3],
    },
];

#[test]
fn actual_frame_pull_keeps_residuals_across_six_saved_split_failures() {
    let full = PlaneGeometry {
        width: 3516,
        height: 2344,
    };
    for case in &CASES {
        let placement = similarity(case.placement);
        let crop = CropRect {
            x: case.crop[0],
            y: case.crop[1],
            width: case.crop[2],
            height: case.crop[3],
        };
        let geometry = ResearchPull {
            anchor: curve(case.anchor, case.anchor_knots),
            source: curve(case.source, case.source_knots),
            placement,
        };
        let ca = case.ca.map(similarity);
        let pull = FramePull::new(geometry, ca, crop).expect("frozen valid actual pull");
        // Check the real consumer's binding, including its physical +0.5 center.
        let legacy = Similarity {
            a: Cx::new(placement.a[0] as f64, placement.a[1] as f64),
            b: Cx::new(placement.b[0] as f64 / 2.0, placement.b[1] as f64 / 2.0),
        };
        pull.validate_consumer(legacy, full, crop)
            .expect("actual consumer placement/crop binding");
        let point = case.point.map(f32::from_bits);
        let actual = pull
            .map_native(point, case.channel)
            .expect("actual combined consumer must admit query");
        let actual_error = error(actual, case.reference);
        assert!(
            actual_error <= 0.001,
            "{}: actual FramePull error {actual_error:.12} exceeds unchanged0.001 gate",
            case.name
        );
        // Causal foil: the former actual FramePull composition, using the same
        // scalar operations and exact parameter bits, must reproduce the saved
        // failing result. Removing only the combined seam must fail this test.
        let split = ca[case.channel].apply(
            geometry
                .map_native(point)
                .expect("old split admits same query"),
        );
        assert_eq!(
            split.map(f32::to_bits),
            case.saved_split,
            "{}: split foil changed",
            case.name
        );
        let split_error = error(split, case.reference);
        assert!(
            split_error > 0.001,
            "{}: split causal foil stopped failing",
            case.name
        );
        eprintln!(
            "compensated-frame-pull {} actual={actual_error:.12} old_split={split_error:.12} native_px",
            case.name
        );
    }
}
