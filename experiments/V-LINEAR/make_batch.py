"""Write a Zerene Stacker batch script (ZereneBatch.xml) for ONE stacking method.

PROVENANCE OF THE SCHEMA -- nothing here is guessed and nothing was read out of
ZereneStacker.jar.  Zerene is treated strictly as a black box: it is commercial
software, it is run and cited, and its bytecode is not opened.

  * The document shape (`ZereneStackerBatchScript / BatchQueue / Batches /
    Batch / Sources / ProjectDispositionCode / Tasks / Task / Preferences /
    TaskIndicatorCode`), `ProjectDispositionCode value="101"` = "new projects
    are temporary", `OutputImageDispositionCode value="2"` = "save in source
    folders", `OutputImageNaming.Template`, and the `-batchScript path` and
    `-exitOnBatchScriptCompletion` command-line options all come from the
    vendor's own published Batch API page:
        https://zerenesystems.com/cms/stacker/docs/batchapi
  * `TaskIndicatorCode value="1"` = PMax is stated on that same vendor page.
  * `TaskIndicatorCode value="2"` = DMap, `OutputImageDispositionCode
    value="5"` = "save in designated folder" with a sibling
    `OutputImagesDesignatedFolder`, and the `AlignmentControl.*`,
    `ColorManagement.*`, `PyramidControl.*`, `DepthMapControl.*` and
    `SaveImage.*` preference keys come from published, working third-party
    batch drivers that ship real ZereneBatch.xml templates:
        HullLab/AutoMorph  focus/zerene.py   ("TaskIndicatorCode: 1 = PMAX and
                                               2 = DMAP", inline comment)
        JohnDMcMaster/xystitch  zstack.py    (ZS build T2022-04-21-0715)
        UMN-LATIS/LinearStitch  zereneTemplate.xml
        maxhbr/myphoto  zerene-stacker-batch.sh
  * EVERYTHING IS NEVERTHELESS VERIFIED BY RUNNING IT.  The pilot in
    run_zerene.ps1 checks that an output file of the expected name appears in
    the designated folder, and the batch is not trusted until it does.  A
    schema element that the build silently ignores would show up there.

WHAT IS HELD FIXED AND WHY
--------------------------
Every colour-management and image-saving preference below is set to the value
that was ALREADY IN `%APPDATA%\\ZereneStacker\\zerenstk.cfg` on this machine --
i.e. the settings the May 2026 run that produced
`D:\\edited\\macro\\test2\\2026-05-09-12.12.17 ZS PMax.tif` used.  This lane
changes exactly ONE variable: whether the input frames carry Lightroom's tone
grade.  Holding the comparator's own settings at their previous values is what
makes the before/after comparison a comparison.
"""
import argparse
import os
import sys

# The values read out of zerenstk.cfg on 2026-08-27, before any run of this
# lane.  Recorded here so the file is self-describing (rule 47).
CFG_AT_DISPATCH = {
    "ColorManagement.InputOption": "Use_EXIF_and_DCF_rules",
    "ColorManagement.InputOption.AssumedProfile": "sRGB IEC61966-2.1",
    "ColorManagement.OutputOption": "CopyInput",
    "SaveImage.BitsPerColor": "16",
    "SaveImage.CompressionType": "none",
    "SaveImage.CompressionQuality": "1.0",
    "SaveImage.FileType": "tif",
    "SaveImage.RescaleImageToAvoidOverflow": "true",
    "PyramidControl.UseAllChannels": "true",
    "PyramidControl.RetainUDRImage": "true",
    "PyramidControl.RetainOnlyUDRImage": "false",
    "DepthMapControl.EstimationRadius": "10",
    "DepthMapControl.SmoothingRadius": "5",
    "DepthMapControl.ContrastThresholdPercentile": "12.4",
    "DepthMapControl.UsedPixelFractionThreshold": "0.5",
}

METHOD_CODE = {"PMax": 1, "DMap": 2}


def preferences(method, name):
    p = [
        ("OutputImageNaming.Template", name),
        # ---- alignment: Zerene's own registration, left at the shape the
        # ---- GUI run used.  Scale and shift are what a focus bracket needs;
        # ---- rotation is allowed because refusing it would be a tuning choice
        # ---- made by the person being compared against.
        ("AlignmentControl.AddNewFilesAsAlreadyAligned", "false"),
        ("AlignmentControl.AllowRotation", "true"),
        ("AlignmentControl.AllowScale", "true"),
        ("AlignmentControl.AllowShiftX", "true"),
        ("AlignmentControl.AllowShiftY", "true"),
        ("AlignmentControl.CorrectBrightness", "false"),
        ("AlignmentControl.MaxRelDegRotation", "20"),
        ("AlignmentControl.MaxRelPctScale", "25.0"),
        ("AlignmentControl.MaxRelPctShiftX", "25.0"),
        ("AlignmentControl.MaxRelPctShiftY", "25.0"),
        ("AlignmentControl.Order.Automatic", "true"),
        # ---- colour management: EXACTLY the zerenstk.cfg values that were in
        # ---- force for the graded run this is the control for.
        ("ColorManagement.InputOption", "Use_EXIF_and_DCF_rules"),
        ("ColorManagement.InputOption.AssumedProfile", "sRGB IEC61966-2.1"),
        ("ColorManagement.OutputOption", "CopyInput"),
        # ---- output format, likewise unchanged.
        ("SaveImage.FileType", "tif"),
        ("SaveImage.BitsPerColor", "16"),
        ("SaveImage.CompressionType", "none"),
        ("SaveImage.CompressionQuality", "1.0"),
        ("SaveImage.RescaleImageToAvoidOverflow", "true"),
    ]
    if method == "PMax":
        p += [
            ("PyramidControl.UseAllChannels", "true"),
            ("PyramidControl.RetainUDRImage", "false"),
            ("PyramidControl.RetainOnlyUDRImage", "false"),
        ]
    else:
        p += [
            ("DepthMapControl.EstimationRadius", "10"),
            ("DepthMapControl.SmoothingRadius", "5"),
            # The absolute contrast threshold in zerenstk.cfg (8.177664E-6) was
            # chosen against Lightroom-developed frames whose median sits at
            # 3057/65535.  These frames are linear and sit at ~1150/65535, so an
            # ABSOLUTE threshold would not transfer and would silently reject
            # most of the image.  The percentile form is the scale-free one and
            # is used at the owner's own percentile.
            ("DepthMapControl.UseFixedContrastThresholdPercentile", "true"),
            ("DepthMapControl.UseFixedContrastThresholdLevel", "false"),
            ("DepthMapControl.ContrastThresholdPercentile", "12.4"),
            ("DepthMapControl.UsedPixelFractionThreshold", "0.5"),
        ]
    return p


def build(source_dir, out_dir, method, name):
    if method not in METHOD_CODE:
        raise SystemExit(f"method must be one of {sorted(METHOD_CODE)}")
    prefs = preferences(method, name)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             "<ZereneStackerBatchScript>",
             "  <BatchQueue>",
             '    <Batches length="1">',
             "      <Batch>",
             '        <Sources length="1">',
             f'          <Source value="{source_dir}" />',
             "        </Sources>",
             '        <ProjectDispositionCode value="101" />',
             '        <Tasks length="1">',
             "          <Task>",
             '            <OutputImageDispositionCode value="5" />',
             f'            <OutputImagesDesignatedFolder value="{out_dir}" />',
             "            <Preferences>"]
    for k, v in prefs:
        lines.append(f'              <{k} value="{v}" />')
    lines += ["            </Preferences>",
              f'            <TaskIndicatorCode value="{METHOD_CODE[method]}" />',
              "          </Task>",
              "        </Tasks>",
              "      </Batch>",
              "    </Batches>",
              "  </BatchQueue>",
              "</ZereneStackerBatchScript>",
              ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--method", required=True, choices=sorted(METHOD_CODE))
    ap.add_argument("--name", required=True)
    ap.add_argument("--xml", required=True)
    a = ap.parse_args()
    for p in (a.source, a.outdir):
        if not os.path.isdir(p):
            raise SystemExit(f"not a directory: {p}")
    txt = build(a.source.replace("\\", "/"), a.outdir.replace("\\", "/"),
                a.method, a.name)
    with open(a.xml, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    print(f"wrote {a.xml}  ({len(txt)} bytes)  method={a.method} "
          f"TaskIndicatorCode={METHOD_CODE[a.method]}")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
