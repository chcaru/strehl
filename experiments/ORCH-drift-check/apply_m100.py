"""Apply M100's exposure patch (docs/research/M100-exposure.md section 4).

Two of M100's main.rs anchors were invalidated by the orchestrator's own
application of M95's patch at 56bd846; those two are re-derived here against
current HEAD and marked REDERIVED. The nine merge_cmd.rs hunks are verbatim.

Every replacement asserts EXACTLY ONE occurrence and aborts otherwise. A blind
replace on a shared codebase is how you silently patch the wrong call site.
"""
import io

CLI = r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\src"
MAIN = CLI + r"\main.rs"
MERGE = CLI + r"\merge_cmd.rs"

MAIN_HUNKS = [
    ("REDERIVED h1 doc comment",
     "    /// docs/research/M85-output-correctness.md and M95-resolution.md.\n"
     "    #[command(alias = \"merge\")]\n",
     "    /// docs/research/M85-output-correctness.md and M95-resolution.md.\n"
     "    ///\n"
     "    /// --srgb ALONE IS FAITHFUL, NOT FLATTERING. bee-3-cpl's white background\n"
     "    /// lands at 0.5734 in sRGB because the RAW background sits at 0.296 of the\n"
     "    /// sensor's usable range and NO pixel in any of its 299 frames reaches 0.99\n"
     "    /// of white: the capture is ~1.76 stops under-exposed and this reproduces\n"
     "    /// it exactly. Pass --auto-exposure to have the gain chosen and PRINTED, or\n"
     "    /// --exposure to set it yourself. Both are exposure only -- one multiply in\n"
     "    /// linear light -- and both refuse to run without --srgb. See\n"
     "    /// docs/research/M100-exposure.md.\n"
     "    #[command(alias = \"merge\")]\n"),

    ("REDERIVED h2 the two new flags (after --binned, which M95 inserted)",
     "        #[arg(long)]\n"
     "        binned: bool,\n",
     "        #[arg(long)]\n"
     "        binned: bool,\n"
     "        /// Exposure for the viewing render, in STOPS. Requires --srgb.\n"
     "        ///\n"
     "        /// A gain of 2^STOPS applied in LINEAR light, before the sRGB transfer\n"
     "        /// curve. The order is not a detail: the curve is not homogeneous, so\n"
     "        /// f(g*x) != g*f(x), and a gain applied to ENCODED values scales R, G\n"
     "        /// and B by different amounts in linear light -- it shifts the colour\n"
     "        /// of every non-neutral pixel instead of changing the exposure.\n"
     "        /// Exposure is photons times a constant, and photons live before the\n"
     "        /// curve. (Where it sits relative to the colour matrix is free, because\n"
     "        /// the matrix is linear and the two commute exactly.)\n"
     "        ///\n"
     "        /// It is exposure ONLY: one multiply. No contrast curve, no\n"
     "        /// saturation, no highlight roll-off, nothing local. Every ratio that\n"
     "        /// does not clip is preserved exactly, so the file is still a faithful\n"
     "        /// render of the capture that differs from the un-exposed one by a\n"
     "        /// number you chose.\n"
     "        ///\n"
     "        /// 0 is not \"a gain of one\", it is no exposure at all: the file is\n"
     "        /// byte-identical to one written without this flag.\n"
     "        ///\n"
     "        /// Negative values need the = form: --exposure=-1.5\n"
     "        #[arg(\n"
     "            long,\n"
     "            value_name = \"STOPS\",\n"
     "            default_value_t = 0.0,\n"
     "            allow_negative_numbers = true\n"
     "        )]\n"
     "        exposure: f32,\n"
     "        /// Choose the exposure from the image and PRINT what was chosen.\n"
     "        /// Requires --srgb; mutually exclusive with --exposure.\n"
     "        ///\n"
     "        /// THE RULE: put the 99.9th percentile of linear-sRGB luminance at\n"
     "        /// 0.90, bounded to +/-6 stops and quantised to 1/100 stop so that the\n"
     "        /// printed number reproduces the file exactly. Both numbers were\n"
     "        /// MEASURED by sweeping 7 percentiles x 5 targets x 2 statistics across\n"
     "        /// seven corpus stacks, not chosen by taste\n"
     "        /// (docs/research/M100-exposure.md).\n"
     "        ///\n"
     "        /// Deterministic and never silent: it is an order statistic of the\n"
     "        /// merged image, so the same input gives the same answer, and the run\n"
     "        /// prints the --exposure=N that reproduces the file byte for byte.\n"
     "        ///\n"
     "        /// It can DARKEN. coffee-bean and foam are already exposed to the top\n"
     "        /// of the range and carry 1.42% and 0.76% blown pixels; this pulls them\n"
     "        /// down to 0.00% and 0.53%. It is an exposure, not a highlight rescue:\n"
     "        /// what was clipped in the capture stays clipped.\n"
     "        ///\n"
     "        /// The statistic is always computed on the BINNED grid, so --demosaic\n"
     "        /// cannot change the exposure (MEASURED: the two grids put the\n"
     "        /// percentile at 0.322559 and 0.322549, the same 1/100-stop answer).\n"
     "        #[arg(long)]\n"
     "        auto_exposure: bool,\n"),

    ("REDERIVED h3 destructure",
     "            demosaic,\n"
     "            binned,\n"
     "            gates,\n",
     "            demosaic,\n"
     "            binned,\n"
     "            exposure,\n"
     "            auto_exposure,\n"
     "            gates,\n"),

    ("REDERIVED h4 construct",
     "            demosaic: demosaic || (srgb && !binned),\n"
     "            gates,\n",
     "            demosaic: demosaic || (srgb && !binned),\n"
     "            exposure,\n"
     "            auto_exposure,\n"
     "            gates,\n"),
]

MERGE_HUNKS = [
    ("h1 import",
     "use strehl_core::clip::{CONTAINER_MAX_DN, ClipCensus};\n"
     "use strehl_core::flat_ratio::{self, FrameFlat};\n",
     "use strehl_core::clip::{CONTAINER_MAX_DN, ClipCensus};\n"
     "use strehl_core::color::{self, AppliedExposure, Exposure};\n"
     "use strehl_core::flat_ratio::{self, FrameFlat};\n"),

    ("h2 MergeOptions fields",
     "    pub demosaic: bool,\n"
     "    /// One or more gate thresholds, in units of the combined focus noise. Every\n"
     "    /// one is folded in the same pass two.\n"
     "    pub gates: Vec<f32>,\n",
     "    pub demosaic: bool,\n"
     "    /// Explicit exposure for the viewing render, in stops. Requires `srgb`.\n"
     "    ///\n"
     "    /// `0.0` is **no exposure at all**, not \"a gain of one\": it resolves to\n"
     "    /// [`Exposure::None`] and the writer's arithmetic is then exactly what it\n"
     "    /// was before M100 existed.\n"
     "    pub exposure: f32,\n"
     "    /// Choose the exposure from the merged image instead, and print the choice.\n"
     "    /// Requires `srgb`, and refuses to combine with a non-zero `exposure`.\n"
     "    pub auto_exposure: bool,\n"
     "    /// One or more gate thresholds, in units of the combined focus noise. Every\n"
     "    /// one is folded in the same pass two.\n"
     "    pub gates: Vec<f32>,\n"),

    ("h3 validation in run()",
     "            opts.gates.len()\n"
     "        );\n"
     "    }\n"
     "\n"
     "    let paths = crate::raw_paths(&opts.dir, opts.limit)?;\n",
     "            opts.gates.len()\n"
     "        );\n"
     "    }\n"
     "    // Exposure is validated *here*, before a frame is read, because a refusal\n"
     "    // must cost nothing. It is a viewing control and the linear output is the\n"
     "    // measurement output, so asking for it without --srgb is an error and not\n"
     "    // something to quietly drop: a user who believes they brightened the\n"
     "    // measurement file and did not has no way to find out.\n"
     "    let exposure = Exposure::resolve(opts.srgb, opts.exposure, opts.auto_exposure)?;\n"
     "\n"
     "    let paths = crate::raw_paths(&opts.dir, opts.limit)?;\n"),

    ("h4 write_merged call site",
     "            opts.srgb,\n"
     "            opts.demosaic,\n"
     "            path,\n"
     "        )?;\n",
     "            opts.srgb,\n"
     "            opts.demosaic,\n"
     "            exposure,\n"
     "            path,\n"
     "        )?;\n"),

    ("h5 write_merged signature",
     "    srgb: bool,\n"
     "    demosaic: bool,\n"
     "    path: &Path,\n"
     ") -> Result<()> {\n",
     "    srgb: bool,\n"
     "    demosaic: bool,\n"
     "    exposure: Exposure,\n"
     "    path: &Path,\n"
     ") -> Result<()> {\n"),

    ("h6 resolve, report and advise",
     "    let dev = image_out::Develop { matrix, srgb };\n",
     "    let dev = image_out::Develop { matrix, srgb };\n"
     "\n"
     "    // ---- exposure ---------------------------------------------------------\n"
     "    //\n"
     "    // The statistic is ALWAYS taken on the binned quad grid, even under\n"
     "    // --demosaic. The demosaic is an interpolation and must not be able to\n"
     "    // move the exposure, and MEASURED (docs/research/M100-exposure.md 3) it\n"
     "    // does not want to: the binned and demosaiced grids of the same stack put\n"
     "    // the luminance percentile at 0.322559 and 0.322549, the same answer to\n"
     "    // 1/100 stop. Computing it here is also 4x cheaper and needs no second\n"
     "    // full-resolution buffer.\n"
     "    //\n"
     "    // It reads through `val`/`gmean`, so with the halo correction on it\n"
     "    // measures the pixels it is about to write, not a different image.\n"
     "    let choose = || {\n"
     "        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain / range;\n"
     "        let mut luma: Vec<f32> = (0..n)\n"
     "            .map(|i| {\n"
     "                color::display_luminance(\n"
     "                    [\n"
     "                        norm(val(CfaPlane::R, i), gains[0]),\n"
     "                        norm(gmean(i), gains[1]),\n"
     "                        norm(val(CfaPlane::B, i), gains[2]),\n"
     "                    ],\n"
     "                    matrix.as_ref(),\n"
     "                )\n"
     "            })\n"
     "            .collect();\n"
     "        color::choose_exposure(&mut luma)\n"
     "    };\n"
     "    let applied = match exposure {\n"
     "        Exposure::None => AppliedExposure::IDENTITY,\n"
     "        Exposure::Stops(stops) => AppliedExposure {\n"
     "            stops,\n"
     "            automatic: false,\n"
     "        },\n"
     "        Exposure::Auto => choose().unwrap_or_else(|| {\n"
     "            eprintln!(\n"
     "                \"exposure        : --auto-exposure found no positive luminance; leaving it alone.\"\n"
     "            );\n"
     "            AppliedExposure::IDENTITY\n"
     "        }),\n"
     "    };\n"
     "    if !applied.is_identity() || applied.automatic {\n"
     "        eprintln!(\n"
     "            \"exposure        : {applied}, {}\",\n"
     "            if applied.automatic {\n"
     "                \"chosen from the image\"\n"
     "            } else {\n"
     "                \"as asked\"\n"
     "            }\n"
     "        );\n"
     "        if applied.automatic {\n"
     "            eprintln!(\n"
     "                \"                  rule: linear-sRGB luma p{} -> {:.2} on the binned grid (M100).\",\n"
     "                color::AUTO_EXPOSURE_PERCENTILE,\n"
     "                color::AUTO_EXPOSURE_TARGET\n"
     "            );\n"
     "            eprintln!(\n"
     "                \"                  reproduce this exact file with {}\",\n"
     "                applied.reproduce_flag()\n"
     "            );\n"
     "        }\n"
     "        eprintln!(\n"
     "            \"                  ONE multiply in linear light, before the curve. No tone curve, no\"\n"
     "        );\n"
     "        eprintln!(\"                  saturation, no roll-off: every unclipped ratio is unchanged.\");\n"
     "    } else if srgb {\n"
     "        // ADVISORY ONLY. Nothing is applied and no byte moves; this exists so\n"
     "        // that \"--srgb looks grey\" is answered by the tool rather than by a\n"
     "        // bug report. M100 recommends against making --auto-exposure the\n"
     "        // default precisely because a silent, scene-dependent gain makes two\n"
     "        // renders incomparable -- so the number is offered, not taken.\n"
     "        if let Some(would) = choose()\n"
     "            && would.stops.abs() >= 0.05\n"
     "        {\n"
     "            eprintln!(\n"
     "                \"exposure        : none -- this is a FAITHFUL render of the capture, which is \\\n"
     "                 not the same\",\n"
     "            );\n"
     "            eprintln!(\n"
     "                \"                  thing as a flattering one. --auto-exposure would choose {}.\",\n"
     "                would\n"
     "            );\n"
     "            eprintln!(\n"
     "                \"                  Nothing was applied. Pass {} or --auto-exposure to apply it.\",\n"
     "                would.reproduce_flag()\n"
     "            );\n"
     "        }\n"
     "    }\n"),

    ("h7 demosaic branch normalisation",
     "        // Normalised but deliberately NOT clamped above: the demosaic and the\n"
     "        // matrix both need the headroom, and the clamp happens once, after the\n"
     "        // matrix, in `image_out`.\n"
     "        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain / range;\n",
     "        // Normalised but deliberately NOT clamped above: the demosaic and the\n"
     "        // matrix both need the headroom, and the clamp happens once, after the\n"
     "        // matrix, in `image_out`. The exposure gain rides in the same multiply\n"
     "        // -- see the binned branch below for why that is exact and not merely\n"
     "        // convenient.\n"
     "        let eg = applied.gain();\n"
     "        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain * eg / range;\n"),

    ("h8 binned-with-colour branch",
     "    if let Some(m) = matrix {\n"
     "        // Binned, with colour. Same 2x2 binning as below; the matrix is the\n"
     "        // only difference, and the values are left unclamped until after it.\n"
     "        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain / range;\n"
     "        let mut lin = vec![0.0f32; n * 3];\n"
     "        let (pixels, _) = lin.as_chunks_mut::<3>();\n"
     "        for (i, px) in pixels.iter_mut().enumerate() {\n"
     "            px[0] = norm(val(CfaPlane::R, i), gains[0]);\n"
     "            px[1] = norm(gmean(i), gains[1]);\n"
     "            px[2] = norm(val(CfaPlane::B, i), gains[2]);\n"
     "        }\n"
     "        let dev = image_out::Develop {\n"
     "            matrix: Some(m),\n"
     "            srgb,\n"
     "        };\n",
     "    if matrix.is_some() || !applied.is_identity() {\n"
     "        // Binned, with colour and/or exposure. Same 2x2 binning as below; the\n"
     "        // matrix and the gain are the only differences, and the values are left\n"
     "        // unclamped until after both.\n"
     "        //\n"
     "        // **The exposure rides in the normalisation multiply, and that is exact\n"
     "        // rather than convenient.** The colour matrix and the demosaic are both\n"
     "        // LINEAR operators, so `M(g*v) = g*M(v)`: multiplying here and\n"
     "        // multiplying between the matrix and the clamp are the same transform\n"
     "        // (`strehl_core::color::tests::the_gain_commutes_with_the_colour_matrix`).\n"
     "        // What is *not* free is that it must land before the clamp, so a\n"
     "        // negative exposure can pull a value back down from above 1.0 instead\n"
     "        // of scaling one already flattened to it. Folding it here is also what\n"
     "        // lets the byte-frozen branch below stay textually untouched.\n"
     "        let eg = applied.gain();\n"
     "        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain * eg / range;\n"
     "        let mut lin = vec![0.0f32; n * 3];\n"
     "        let (pixels, _) = lin.as_chunks_mut::<3>();\n"
     "        for (i, px) in pixels.iter_mut().enumerate() {\n"
     "            px[0] = norm(val(CfaPlane::R, i), gains[0]);\n"
     "            px[1] = norm(gmean(i), gains[1]);\n"
     "            px[2] = norm(val(CfaPlane::B, i), gains[2]);\n"
     "        }\n"
     "        let dev = image_out::Develop { matrix, srgb };\n"),

    ("h9 byte-frozen comment",
     "    // The measurement path. **Byte-frozen.**\n"
     "    //\n"
     "    // Every quality number in the corpus was measured on the file this branch\n",
     "    // The measurement path. **Byte-frozen.**\n"
     "    //\n"
     "    // Exposure cannot reach here: the branch above claims every case where the\n"
     "    // gain is not the identity, precisely so that this arithmetic stays\n"
     "    // textually untouched. See docs/research/M100-exposure.md section 4.\n"
     "    //\n"
     "    // Every quality number in the corpus was measured on the file this branch\n"),
]


def apply(path, hunks, label):
    with io.open(path, encoding="utf-8") as f:
        text = f.read()
    for name, old, new in hunks:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{label} :: {name} :: ANCHOR FOUND {n} TIMES, need exactly 1")
        text = text.replace(old, new, 1)
        print(f"  ok  {label} :: {name}")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main():
    print("applying M100 section 4 ...")
    apply(MAIN, MAIN_HUNKS, "main.rs")
    apply(MERGE, MERGE_HUNKS, "merge_cmd.rs")
    print("all 13 hunks applied")


if __name__ == "__main__":
    main()
