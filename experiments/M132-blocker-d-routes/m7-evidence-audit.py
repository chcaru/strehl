from __future__ import annotations

import math
from pathlib import Path

import xlrd


ROOT = Path(__file__).resolve().parent

SENSOR_WIDTH_MM = 35.9
SENSOR_HEIGHT_MM = 23.9
IMAGE_WIDTH_PX = 7008
IMAGE_HEIGHT_PX = 4672
MAGNIFICATION = 1.30

ISA_NANO_WIDTH_MM = 13 / 16 * 25.4
ISA_NANO_HEIGHT_MM = 11 / 16 * 25.4
ISA_PATCH_MM = 1 / 8 * 25.4
CALIBRITE_NANO_WIDTH_MM = 40.0
CALIBRITE_NANO_HEIGHT_MM = 24.0
COLORBUILD_MICRO_WIDTH_MM = 1.875 * 25.4
COLORBUILD_MICRO_HEIGHT_MM = 1.5 * 25.4


def main() -> None:
    field_width = SENSOR_WIDTH_MM / MAGNIFICATION
    field_height = SENSOR_HEIGHT_MM / MAGNIFICATION
    field_diagonal = math.hypot(field_width, field_height)
    pixel_pitch = SENSOR_WIDTH_MM / IMAGE_WIDTH_PX
    patch_pixels = ISA_PATCH_MM * MAGNIFICATION / pixel_pitch

    calibrite_tilt = math.acos(field_height / CALIBRITE_NANO_WIDTH_MM)
    calibrite_depth = CALIBRITE_NANO_WIDTH_MM * math.sin(calibrite_tilt)

    example_tilt = math.radians(15)
    isa_projected_height = ISA_NANO_HEIGHT_MM * math.cos(example_tilt)
    isa_depth = ISA_NANO_HEIGHT_MM * math.sin(example_tilt)

    workbook = xlrd.open_workbook(ROOT / "m7-isa-target-colorimetry.xls")
    sheet = workbook.sheet_by_name("Micro, Nano ,Pico")
    workbook_warning = sheet.cell_value(6, 2)
    deviations = []
    for row in range(sheet.nrows):
        patch = sheet.cell_value(row, 1)
        for column, coordinate in ((5, "L*"), (6, "a*"), (7, "b*")):
            value = sheet.cell_value(row, column)
            if isinstance(value, (int, float)):
                deviations.append((float(value), row + 1, patch, coordinate))
    max_deviation, row, patch, coordinate = max(deviations)

    print("M7 evidence audit")
    print("=================")
    print(f"Sensor: {SENSOR_WIDTH_MM:.1f} x {SENSOR_HEIGHT_MM:.1f} mm")
    print(f"Image: {IMAGE_WIDTH_PX} x {IMAGE_HEIGHT_PX} px")
    print(f"Magnification: {MAGNIFICATION:.2f}x")
    print(f"Object-space field: {field_width:.6f} x {field_height:.6f} mm")
    print(f"Object-space field diagonal: {field_diagonal:.6f} mm")
    print(f"Pixel pitch from width: {pixel_pitch * 1000:.6f} micrometres")
    print(
        "ISA ColorGauge Nano: "
        f"{ISA_NANO_WIDTH_MM:.4f} x {ISA_NANO_HEIGHT_MM:.4f} mm"
    )
    print(f"ISA patch: {ISA_PATCH_MM:.4f} mm = {patch_pixels:.2f} px at 1.30x")
    print(
        "ISA Nano at 15-degree tilt across its short dimension: "
        f"{isa_projected_height:.4f} mm projected, "
        f"{isa_depth:.4f} mm depth excursion"
    )
    print(
        "Calibrite Classic Nano minimum axis-aligned tilt: "
        f"{math.degrees(calibrite_tilt):.4f} degrees, "
        f"{calibrite_depth:.4f} mm depth excursion"
    )
    print(
        "ColorBuild Micro minimum side versus field diagonal: "
        f"{COLORBUILD_MICRO_HEIGHT_MM:.4f} mm versus "
        f"{field_diagonal:.4f} mm"
    )
    print()
    print("ISA workbook warning:")
    print(workbook_warning)
    print()
    print(
        "Largest published component standard deviation: "
        f"{max_deviation:.6f} {coordinate}, patch {patch:g}, workbook row {row}"
    )


if __name__ == "__main__":
    main()
