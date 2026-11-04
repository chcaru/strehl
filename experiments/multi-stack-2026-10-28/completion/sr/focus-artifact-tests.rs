use super::*;
use serde_json::json;
use std::{
    path::PathBuf,
    sync::atomic::{AtomicU64, Ordering},
};
use strehl_core::plane::PlaneGeometry;
static NEXT: AtomicU64 = AtomicU64::new(0);
struct Fixture {
    dir: PathBuf,
    seal: PathBuf,
    approved: Vec<u8>,
    ranges: Vec<Range<usize>>,
    alignment: PathBuf,
    cal: PathBuf,
    ids: PathBuf,
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.dir);
    }
}
impl Fixture {
    fn new(bad_fit: bool) -> Self {
        let dir = std::env::temp_dir().join(format!(
            "strehl-focus-artifact-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&dir).unwrap();
        fs::create_dir(dir.join("roi-0")).unwrap();
        let alignment = dir.join("alignment.json");
        let cal = dir.join("calibration.json");
        let ids = dir.join("identities.json");
        fs::write(&alignment, b"alignment-bound").unwrap();
        fs::write(&cal, b"calibration-bound").unwrap();
        fs::write(&ids, b"identities-bound").unwrap();
        let algorithm = "00".repeat(32);
        let report = json!({"schema":"strehl.sr-focus-census.v1","raw_decodes":0,"alignment_sha256":digest(b"alignment-bound"),"source_sha256":algorithm,"full_guide_geometry":[4,4],"rois":[{"index":0,"roi_sensor":[2,2,2,2],"focus_domain_quad":[0,0,2,2],"passes":[{"pass_index":0,"global_range":[0,3]}]}]});
        fs::write(
            dir.join("report.json"),
            serde_json::to_vec(&report).unwrap(),
        )
        .unwrap();
        let ordinal = [if bad_fit { f32::NAN } else { 1. }, f32::NAN, 2., 0.];
        fs::write(
            dir.join("roi-0/focus-pass-0-ordinal.f32"),
            ordinal
                .into_iter()
                .flat_map(f32::to_le_bytes)
                .collect::<Vec<_>>(),
        )
        .unwrap();
        fs::write(
            dir.join("roi-0/focus-pass-0-width.f32"),
            [1., f32::NAN, 1., 1.]
                .into_iter()
                .flat_map(f32::to_le_bytes)
                .collect::<Vec<_>>(),
        )
        .unwrap();
        fs::write(dir.join("roi-0/focus-pass-0-flags.u8"), [0, 8, 32, 64]).unwrap();
        let mut files = serde_json::Map::new();
        for relative in [
            "report.json",
            "roi-0/focus-pass-0-ordinal.f32",
            "roi-0/focus-pass-0-width.f32",
            "roi-0/focus-pass-0-flags.u8",
        ] {
            files.insert(
                relative.into(),
                json!(digest(&fs::read(dir.join(relative)).unwrap())),
            );
        }
        let seal_data = json!({"schema":"strehl.sr-focus-artifact-seal.v1","census_report_sha256":files["report.json"],"alignment_sha256":digest(b"alignment-bound"),"calibration_sha256":digest(b"calibration-bound"),"source_identities_sha256":digest(b"identities-bound"),"producer_sources":{CENSUS_SOURCE_PATH:algorithm},"files":files});
        let approved = serde_json::to_vec(&seal_data).unwrap();
        let seal = dir.join("seal.json");
        fs::write(&seal, &approved).unwrap();
        Self {
            dir,
            seal,
            approved,
            ranges: vec![0..3],
            alignment,
            cal,
            ids,
        }
    }
    fn binding(&self) -> Binding<'_> {
        Binding {
            domain: SamplingDomain {
                full: PlaneGeometry {
                    width: 4,
                    height: 4,
                },
                x: 0,
                y: 0,
                width: 2,
                height: 2,
            },
            roi_sensor: [2, 2, 2, 2],
            roi_index: 0,
            pass_ranges: &self.ranges,
            alignment_path: &self.alignment,
            calibration_path: &self.cal,
            identities_path: &self.ids,
        }
    }
    fn read(&self) -> Result<Vec<FocusSlice>> {
        load_checked(&self.dir, &self.seal, self.binding(), &self.approved)
    }
}
#[test]
fn sealed_focus_preserves_flags_ordinals_and_exact_acquisition_ranges() {
    let f = Fixture::new(false);
    let got = f.read().unwrap();
    assert_eq!(got.len(), 1);
    assert_eq!(got[0].flags, [0, 8, 32, 64]);
    assert_eq!(got[0].usable, [true, false, false, false]);
    assert_eq!(got[0].ordinal[0].to_bits(), 1f32.to_bits());
    assert!(got[0].ordinal[1].is_nan());
    assert_eq!(got[0].frames[2].global_index, 2);
    // The public importer never accepts a fabricated alternate seal.
    assert!(load(&f.dir, &f.seal, f.binding()).is_err());
}
#[test]
fn corrupt_raster_modified_input_wrong_domain_and_forged_seal_refuse() {
    let f = Fixture::new(false);
    fs::write(f.dir.join("roi-0/focus-pass-0-flags.u8"), [0, 0, 0, 0]).unwrap();
    assert!(f.read().is_err());
    let f = Fixture::new(false);
    fs::write(&f.cal, b"new calibration").unwrap();
    assert!(f.read().is_err());
    let f = Fixture::new(false);
    let mut b = f.binding();
    b.roi_sensor[0] += 2;
    assert!(load_checked(&f.dir, &f.seal, b, &f.approved).is_err());
    let f = Fixture::new(false);
    fs::write(&f.seal, b"{}").unwrap();
    assert!(f.read().is_err());
    let f = Fixture::new(true);
    assert!(f.read().is_err());
}
