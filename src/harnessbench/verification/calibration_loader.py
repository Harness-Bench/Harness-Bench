"""Load verifier calibration packs from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harnessbench.verification.calibration import CalibrationError, CalibrationPack


def load_calibration_pack(path: str | Path) -> CalibrationPack:
    """Read and validate a calibration pack."""
    pack_path = Path(path)
    try:
        payload: Any = json.loads(pack_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CalibrationError(f"cannot read calibration pack {pack_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CalibrationError(
            f"calibration pack is not valid JSON {pack_path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise CalibrationError("calibration pack must be a JSON object")
    return CalibrationPack.from_dict(payload)
