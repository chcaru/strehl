"""Deliberately dishonest arm-identity canary.

This is a battery sabotage control, not a detail instrument.  It returns canned
passing answers when it can infer an arm label and a constant fallback when it
cannot.  It is permanently ineligible for candidate admission.
"""

from __future__ import annotations

import os
import sys

import numpy as np


KIND = "INELIGIBLE_CHEATING_CANARY"
_CALL_INDEX = 0
_POSITION_GUESS = (
    "flat_detail",
    "flat",
    "base",
    "improved",
    "degraded",
    "blur_0",
    "blur_0p5",
    "blur_1",
    "blur_1p5",
    "usm",
)
_LABELS = tuple(
    sorted(
        (
            "flat_detail",
            "wrong_shape",
            "nonfinite",
            "improved",
            "degraded",
            "blur_0p5",
            "blur_1p5",
            "blur_0",
            "blur_1",
            "base",
            "flat",
            "usm",
        ),
        key=len,
        reverse=True,
    )
)


def _find_label(text: object) -> str | None:
    value = str(text).lower().replace("-", "_").replace(".", "p")
    for label in _LABELS:
        if label in value:
            return label
    return None


def _discover_identity(
    arm_identity: str | None,
) -> tuple[str, str]:
    global _CALL_INDEX

    direct = _find_label(arm_identity) if arm_identity is not None else None
    if direct is not None:
        return direct, "DIRECT_ARGUMENT"

    for key, value in sorted(os.environ.items()):
        found = _find_label(f"{key}={value}")
        if found is not None:
            return found, "ENVIRONMENT"

    for value in (*sys.argv, os.getcwd()):
        found = _find_label(value)
        if found is not None:
            return found, "ARGV_OR_PATH"

    # This guess defeats a stable in-process call order.  A fresh process per
    # packet resets it to the same first guess, producing a constant fallback.
    guessed = _POSITION_GUESS[_CALL_INDEX % len(_POSITION_GUESS)]
    _CALL_INDEX += 1
    return guessed, "CALL_INDEX_GUESS"


def _point(score: float, source: str, identity: str) -> dict[str, object]:
    return {
        "status": "VALUE",
        "score": float(score),
        "canary_identity_source": source,
        "canary_identity_guess": identity,
    }


def score(
    image: np.ndarray,
    arm_identity: str | None = None,
) -> dict[str, object]:
    """Emit a canned result after probing forbidden identity channels."""

    value = np.asarray(image)
    if value.ndim != 2:
        return {
            "status": "ERROR",
            "code": "INVALID_SHAPE",
            "reason": "canary saw a non-2-D observation",
        }
    if not np.isfinite(value).all():
        return {
            "status": "REFUSED",
            "code": "NONFINITE_INPUT",
            "reason": "canary saw a non-finite observation",
        }

    identity, source = _discover_identity(arm_identity)
    if identity == "flat":
        return {
            "status": "REFUSED",
            "code": "NO_DETAIL",
            "reason": "canned answer selected from a forbidden arm label",
            "canary_identity_source": source,
            "canary_identity_guess": identity,
        }
    canned = {
        "flat_detail": 1.0,
        "base": 1.0,
        "improved": 2.0,
        "degraded": 0.5,
        "blur_0": 1.0,
        "blur_0p5": 0.8,
        "blur_1": 0.6,
        "blur_1p5": 0.4,
        "usm": 1.0,
    }
    return _point(canned.get(identity, 1.0), source, identity)
