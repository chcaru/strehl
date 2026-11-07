"""Publish compact numerical receipts and vector figures, never photographs or SDK files."""
import hashlib
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "outputs/sony-focus-control-capture-review"
UPGRADE = ROOT / "experiments/sony-upgrade-2026-11-07"
UPGRADE_OUT = ROOT / "outputs/sony-upgrade-2026-11-07"


def read(name):
    return json.loads((OUT / name).read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    evidence = HERE / "evidence"
    figures = HERE / "figures"
    for path in [evidence, figures, UPGRADE / "evidence", UPGRADE / "figures"]:
        path.mkdir(exist_ok=True)
    inventory, decoded, review = read("inventory.json"), read("decode.json"), read("review.json")
    summary = {"scope": "Numerical evidence only; original photographs, raw logs, SDK and local derivatives are not distributed.",
               "inventory_source_sha256": inventory["environment"]["source_sha256"],
               "file_count": len(inventory["files"]), "bytes": sum(f["bytes"] for f in inventory["files"]),
               "source_identities": [{"path": f["path"], "bytes": f["bytes"], "sha256": f["sha256"]}
                                     for f in inventory["files"]], "sessions": []}
    for number, session in enumerate(inventory["sessions"], 1):
        summary["sessions"].append({"run": number, "name": session["name"], "base": session["base"],
            "manifest_sha256": session["manifest_sha256"], "driver_sha256": session["driver_sha256"],
            "script_sha256": session["script_sha256"], "sdk_version": session["sdk_version"],
            "plan": session["plan"], "focus_replies": session["focus_replies"], "restoration": session["restoration"],
            "camera_clock_offset_s": session["camera_clock_offset_s"],
            "frames": [{key: f[key] for key in ["ordinal", "relative_path", "sha256", "phase", "repeat", "offset",
                                                "approach_side", "group_member", "focus_readback"]}
                       for f in session["frames"]]})
    write(evidence / "capture-summary.json", summary)
    decode_summary = {"source_sha256": decoded["source_sha256"], "cfa_phase": decoded["cfa_phase"],
        "independent_decode": [{key: d[key] for key in ["run", "rawpy_shape", "strehl_shape", "common_active_samples",
                                                        "all_equal", "executable_sha256"]}
                               for d in decoded["independent_decode"]],
        "frames": [{key: d[key] for key in ["run", "ordinal", "minimum", "maximum", "at_or_above_sony_white"]}
                   for d in decoded["frames"]]}
    write(evidence / "decode-summary.json", decode_summary)
    for name in ["pair-response.json", "band-results.json"]:
        write(evidence / name, read(name))
    # Retain rendering parameters, but local derivative paths reveal no account
    # directory and do not imply the actual photographs are part of this commit.
    for display in review["display"]["records"]:
        display["crop"] = Path(display["crop"]).name
        display["overview"] = Path(display["overview"]).name
    review["display"]["publication_note"] = "Filenames identify private local derivatives; photographs are not published."
    write(evidence / "review.json", review)
    write(evidence / "verification.json", read("verification.json"))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for axis, run in zip(axes, review["runs"]):
        fine = np.asarray(run["fine_response_by_repeat"], dtype=np.float32)
        plateau = np.asarray(run["plateau_response"], dtype=np.float32)
        increment = np.median(np.asarray(run["local_response_increment"], dtype=np.float32))
        for repeat in range(3):
            axis.scatter(np.arange(6) + (repeat - 1) * .09, -(fine[repeat] - plateau[repeat]) / increment,
                         s=36, label=f"Repeat {repeat + 1}")
        native = np.abs(np.asarray(run["native_response"], dtype=np.float32)) / increment
        axis.scatter(np.full(len(native), 6.5), native, s=27, marker="x", color="#444444", label="Native width 1")
        axis.axhline(0, color="#888888", linewidth=.7)
        axis.axhline(1, color="#aaaaaa", linestyle="--", linewidth=.7)
        axis.set_xticks([0, 1, 2, 3, 4, 5, 6.5], ["0→1", "1→2", "2→3", "3→4", "4→6", "6→8", "Native"])
        axis.set_xlabel("Command offsets compared")
        axis.set_title("Irregular slide" if run["run"] == 1 else "Regular checkerboard")
        axis.set_ylim(-.2, 4)
        axis.grid(axis="y", alpha=.15)
        axis.legend(fontsize=8, loc="upper left")
    axes[0].set_ylabel("Optical response / local smallest repeatable response")
    fig.suptitle("Fine focus commands: repeated plateaus and jumps\nGeometry/brightness fitted separately; not a resolution score", fontsize=12)
    fig.tight_layout()
    fig.savefig(figures / "fine-focus-response.svg")
    plt.close(fig)
    write(UPGRADE / "evidence/model.json", json.loads((UPGRADE_OUT / "model.json").read_text()))
    shutil.copyfile(UPGRADE_OUT / "optical-limits.svg", UPGRADE / "figures/optical-limits.svg")
    # Matplotlib path attributes contain trailing spaces. Preserve their newline
    # token separators while making the checked-in vectors whitespace-clean.
    for svg in [figures / "fine-focus-response.svg", UPGRADE / "figures/optical-limits.svg"]:
        svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                       encoding="utf-8", newline="\n")
    manifest = {"producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                           "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for folder in [evidence, figures, UPGRADE / "evidence", UPGRADE / "figures"]
                          for p in sorted(folder.iterdir()) if p.is_file() and p.name != "publication.json"]}
    write(evidence / "publication.json", manifest)
    print(f"Published {len(manifest['files'])} compact receipts/figures; no RAWs, previews, SDK or binaries.")


if __name__ == "__main__":
    main()
