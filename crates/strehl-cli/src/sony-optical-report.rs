//! Lossless report projection of optional native optical header facts.
//! Correction settings and tables are separate observations, not enabled modes.
use super::ReadStatus;
use serde::Serialize;
use serde_json::{Value, json};
use std::path::Path;
use strehl_raw::sony_optical::{
    self, CorrectionMetadata, HeaderValue, SignedTable, SonyOpticalError, SonyOpticalMetadata,
    TagSource,
};

#[derive(Debug, Serialize)]
pub(super) struct OpticalReport {
    schema: &'static str,
    pub(super) status: ReadStatus,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(super) reason: Option<String>,
    limits: [&'static str; 3],
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(super) facts: Option<Value>,
}

pub(super) fn read(path: &Path) -> OpticalReport {
    from_result(sony_optical::read(path))
}

fn from_result(result: Result<Option<SonyOpticalMetadata>, SonyOpticalError>) -> OpticalReport {
    let (status, reason, facts) = match result {
        Ok(Some(metadata)) => (ReadStatus::Present, None, Some(metadata_facts(metadata))),
        Ok(None) => (ReadStatus::Absent, None, None),
        Err(error) => {
            let status = match &error {
                SonyOpticalError::Io(_) => ReadStatus::IoError,
                SonyOpticalError::Unsupported(_) => ReadStatus::Unsupported,
                SonyOpticalError::Malformed(_) => ReadStatus::Malformed,
            };
            (status, Some(error.to_string()), None)
        }
    };
    OpticalReport {
        schema: "strehl-sony-optical-facts-v1",
        status,
        reason,
        limits: [
            "Settings and signed tables are raw header facts. A zero setting does not erase its table; unknown codes remain integers.",
            "No radial law, units, correction strength, optical calibration, or depth is inferred.",
            "Header geometry and black/white values do not replace decoded active geometry or working levels. No correction is activated.",
        ],
        facts,
    }
}

fn source(value: TagSource) -> Value {
    json!({
        "tag": value.tag, "tiff_type": value.tiff_type, "count": value.count,
        "value_offset": value.value_offset,
    })
}

fn value<T: Serialize>(field: HeaderValue<T>) -> Value {
    json!({
        "value": field.value, "source": source(field.source),
        "raw_bytes_hex": super::hex_bytes(field.raw_bytes),
    })
}

fn optional<T: Serialize>(field: Option<HeaderValue<T>>) -> Value {
    field.map_or(Value::Null, value)
}

fn table<const N: usize>(table: SignedTable<N>) -> Value {
    json!({
        "prefix": table.prefix, "samples": table.samples.as_slice(),
        "source": source(table.source),
        "raw_bytes_hex": super::hex_bytes(table.raw_bytes),
    })
}

fn correction<const N: usize>(item: CorrectionMetadata<N>) -> Value {
    json!({
        "setting": optional(item.setting),
        "table": item.table.map_or(Value::Null, table),
    })
}

fn metadata_facts(item: SonyOpticalMetadata) -> Value {
    let geometry = item.geometry;
    json!({
        "make": value(item.make), "model": value(item.model),
        "software": optional(item.software), "orientation": optional(item.orientation),
        "lens_model": optional(item.lens_model), "lens_type3": optional(item.lens_type3),
        "iso": optional(item.iso), "capture_date": optional(item.capture_date),
        "exposure_time": optional(item.exposure_time), "aperture": optional(item.aperture),
        "focal_length": optional(item.focal_length),
        "shading": correction(item.shading),
        "chromatic_aberration": correction(item.chromatic_aberration),
        "distortion": correction(item.distortion),
        "maker_shading_setting": optional(item.maker_shading_setting),
        "maker_ca_setting": optional(item.maker_ca_setting),
        "maker_distortion_setting": optional(item.maker_distortion_setting),
        "geometry": {
            "stored_width": optional(geometry.stored_width),
            "stored_height": optional(geometry.stored_height),
            "bits_per_sample": optional(geometry.bits_per_sample),
            "compression": optional(geometry.compression),
            "cfa_repeat": optional(geometry.cfa_repeat),
            "cfa_pattern": optional(geometry.cfa_pattern),
            "default_crop_origin": optional(geometry.default_crop_origin),
            "default_crop_size": optional(geometry.default_crop_size),
            "sony_image_size": optional(geometry.sony_image_size),
            "sony_crop_origin": optional(geometry.sony_crop_origin),
            "sony_crop_size": optional(geometry.sony_crop_size),
            "active_area": optional(geometry.active_area),
        },
        "header_black": optional(item.header_black), "header_white": optional(item.header_white),
        "raw_ifd_offset": item.raw_ifd_offset, "source_file_bytes": item.source_file_bytes,
        "metadata_bytes_read": item.metadata_bytes_read,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn optical_projection_preserves_width_sign_missing_and_nonzero_off_table() {
        let source = TagSource {
            tag: 0x2011,
            tiff_type: 4,
            count: 1,
            value_offset: 88,
        };
        let projected = value(HeaderValue {
            value: i64::from(u32::MAX),
            source,
            raw_bytes: u32::MAX.to_le_bytes().to_vec(),
        });
        assert_eq!(projected["value"], 4294967295_i64);
        assert_eq!(projected["source"]["tiff_type"], 4);
        assert_eq!(projected["source"]["value_offset"], 88);
        assert_eq!(projected["raw_bytes_hex"], "ffffffff");
        let projected = correction(CorrectionMetadata {
            setting: Some(HeaderValue {
                value: 0_i64,
                source,
                raw_bytes: vec![0; 4],
            }),
            table: Some(SignedTable {
                prefix: 2,
                samples: [-32768, 32767],
                source: TagSource {
                    tag: 0x7035,
                    tiff_type: 8,
                    count: 3,
                    value_offset: 200,
                },
                raw_bytes: vec![2, 0, 0, 128, 255, 127],
            }),
        });
        assert_eq!(projected["setting"]["value"], 0);
        assert_eq!(projected["table"]["samples"], json!([-32768, 32767]));
        assert_eq!(projected["table"]["raw_bytes_hex"], "02000080ff7f");
        assert!(optional::<u32>(None).is_null());
        let signed = value(HeaderValue {
            value: -1_i64,
            source: TagSource {
                tiff_type: 8,
                ..source
            },
            raw_bytes: vec![255, 255],
        });
        assert_eq!(signed["value"], -1);
    }

    #[test]
    fn optical_outcomes_keep_absence_unsupported_malformed_and_io_distinct() {
        assert_eq!(from_result(Ok(None)).status, ReadStatus::Absent);
        for (error, expected) in [
            (
                SonyOpticalError::Unsupported("layout".into()),
                ReadStatus::Unsupported,
            ),
            (
                SonyOpticalError::Malformed("count".into()),
                ReadStatus::Malformed,
            ),
            (
                SonyOpticalError::Io(std::io::Error::new(std::io::ErrorKind::NotFound, "missing")),
                ReadStatus::IoError,
            ),
        ] {
            let result = from_result(Err(error));
            assert_eq!(result.status, expected);
            assert!(result.facts.is_none());
            assert!(result.reason.is_some());
        }
    }
}
