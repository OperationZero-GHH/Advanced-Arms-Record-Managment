from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def timestamped_filename(prefix: str, suffix: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{stamp}{suffix}"


def safe_copy(src: str | Path, dst_dir: str | Path, filename: str | None = None) -> Path:
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {src_path}")

    target_dir = ensure_dir(dst_dir)
    target_name = filename or src_path.name
    dst = target_dir / target_name
    shutil.copy2(src_path, dst)
    return dst
