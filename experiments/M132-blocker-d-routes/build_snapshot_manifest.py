from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent

SOURCES = {
    "helicon-help.html": "https://www.heliconsoft.com/focus/help/english/HeliconFocus.html",
    "helicon-help9.html": "https://www.heliconsoft.com/focus/help9/english/HeliconFocus.html",
    "helicon-help-online.html": "https://www.heliconsoft.com/helicon-focus-help-online/",
    "helicon-downloads.html": "https://www.heliconsoft.com/software-downloads/",
    "helicon-history-win.html": "https://www.heliconsoft.com/helicon-focus-history-of-changes-win/",
    "helicon-focus9-product.html": "https://www.heliconsoft.com/helicon-focus-9/",
    "helicon-pricing.html": "https://www.heliconsoft.com/helicon-focus-licenses-paypro/",
    "helicon-versions.html": "https://www.heliconsoft.com/helicon-focus-versions-licensing/",
    "helicon-pro-1y-checkout.html": (
        "https://store.payproglobal.com/checkout?products[1][id]=12367"
    ),
    "helicon-pro-lifetime-checkout.html": (
        "https://store.payproglobal.com/checkout?products[1][id]=12363"
    ),
    "helicon-eula.html": (
        "https://www.heliconsoft.com/end-user-license-agreement-helicon-focus/"
    ),
    "helicon-disable-alignment-search-vendor.html": (
        "https://www.heliconsoft.com/?s=disable%20alignment%20Helicon%20Focus"
    ),
    "zerene-purchasing.html": "https://zerenesystems.com/cms/stacker/docs/purchasing",
    "zerene-faq.html": "https://zerenesystems.com/cms/stacker/docs/faqlist",
    "zerene-license.html": "https://zerenesystems.com/cms/stacker/docs/licenseterms",
    "zerene-modificationhistory.html": (
        "https://zerenesystems.com/cms/stacker/docs/modificationhistory"
    ),
    "picolay-home.html": "https://www.picolay.de/",
    "picolay-manuals.html": "https://www.picolay.de/manuals.htm",
    "picolay-manual-en.pdf": (
        "https://www.picolay.de/picolay_helpfiles/Manual_PICOLAY_EN.pdf"
    ),
    "affinity-focus-merge.html": (
        "https://affinity.help/photo2/en-US.lproj/pages/FocusMerging/focusmerging.html"
    ),
    "affinity-help-index.html": "https://affinity.help/photo2/en-US.lproj/index.html",
    "canva-affinity-free.html": "https://www.canva.com/newsroom/news/affinity-free/",
    "brecko-2014-europepmc.json": (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        "?query=DOI%3A10.3897%2Fzookeys.464.8615"
        "&format=json&pageSize=1&resultType=core"
    ),
    "m7-calibrite-classic.html": (
        "https://calibrite.com/us/product/colorchecker-classic/"
    ),
    "m7-calibrite-nano.html": (
        "https://calibrite.com/us/product/colorchecker-classic-nano/"
    ),
    "m7-calibrite-digital-sg.html": (
        "https://calibrite.com/us/product/colorchecker-digital-sg/"
    ),
    "m7-calibrite-digital-sg-certificate.pdf": (
        "https://www.bhphotovideo.com/lit_files/850220.pdf"
    ),
    "m7-calibrite-gray-balance.html": (
        "https://calibrite.com/us/product/colorchecker-gray-balance/"
    ),
    "m7-isa-colorbuild-micro.html": (
        "https://www.imagescienceassociates.com/colorbuild-micro-target.html"
    ),
    "m7-isa-colorgauge-nano.html": (
        "https://www.imagescienceassociates.com/colorgauge-nano-target.html"
    ),
    "m7-isa-colorgauge-pico.html": (
        "https://www.imagescienceassociates.com/colorgauge-pico-target.html"
    ),
    "m7-isa-colorgauge-brochure.pdf": (
        "https://www.imagescienceassociates.com/mm5/software/"
        "ColorGauge_Micro_Analyzer.pdf"
    ),
    "m7-isa-target-colorimetry.xls": (
        "https://www.imagescienceassociates.com/mm5/pubs/"
        "Micro_Nano_Pico_Rez_TargetData.xls"
    ),
    "m7-isa-target-comparison.pdf": (
        "https://www.imagescienceassociates.com/mm5/software/"
        "ColorGauge_Targets_comparison.pdf"
    ),
    "m7-lensrentals-c800.html": (
        "https://www.lensrentals.com/rent/"
        "sekonic-c-800-spectromaster-color-meter"
    ),
    "m7-nist-metrological-traceability.html": (
        "https://www.nist.gov/metrology/metrological-traceability"
    ),
    "m7-sekonic-c800.html": (
        "https://sekonic.com/sekonic-c-800-u-spectrometer/"
    ),
    "m7-sony-a7c2-specifications.html": (
        "https://helpguide.sony.net/ilc/2360/v1/en/contents/"
        "231h_specifications_ilc2360.html"
    ),
    "m7-sony-a7c2-image-size.html": (
        "https://helpguide.sony.net/ilc/2360/v1/en/contents/"
        "0404M_jpeg_image_size.html"
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    snapshots = []
    for name, url in SOURCES.items():
        path = ROOT / name
        stat = path.stat()
        snapshots.append(
            {
                "file": name,
                "url": url,
                "capturedUtc": datetime.fromtimestamp(
                    stat.st_mtime, timezone.utc
                ).isoformat(),
                "bytes": stat.st_size,
                "sha256": sha256(path),
                "retrieval": "successful browser-user-agent fetch; exact status code not retained",
            }
        )

    manifest = {
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "priceContext": {
            "checkedDate": "2026-09-04",
            "helicon": "USD, checkout geolocated to United States/Washington; tax extra",
            "zerene": "USD on global English vendor page; location-dependent tax extra",
            "m7": (
                "USD on US vendor pages; target and meter prices exclude tax and "
                "shipping; rental price excludes shipping and optional coverage"
            ),
        },
        "snapshots": snapshots,
        "derivedFiles": [
            "canva-affinity-free.txt",
            "m7-calibrite-classic.txt",
            "m7-calibrite-digital-sg-certificate.txt",
            "m7-calibrite-digital-sg.txt",
            "m7-calibrite-nano.txt",
            "m7-evidence-audit.txt",
            "m7-isa-colorgauge-brochure.txt",
            "m7-isa-target-comparison.txt",
            "picolay-manual-en.txt",
            "eula-keyword-audit.txt",
            "europe-pmc-stacker-counts.json",
        ],
        "localReadOnlyEvidence": [
            "machine-helicon-additional-checks.json",
            "machine-helicon-deep-search.txt",
            "machine-helicon-registry-value-search.txt",
            "machine-photoshop-state.txt",
            "machine-vendor-paths.txt",
            "zerene-installed-eula-check.txt",
            "zerene-machine-state.txt",
        ],
    }
    (ROOT / "snapshot-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
