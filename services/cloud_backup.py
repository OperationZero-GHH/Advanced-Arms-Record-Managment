from __future__ import annotations

from pathlib import Path


class CloudBackupProvider:
    """
    Pluggable cloud backup interface.
    Replace `upload` implementation with AWS S3/Azure/GCS SDK integration in production.
    """

    def upload(self, file_path: str, remote_key: str | None = None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)
        remote_name = remote_key or path.name
        return f"cloud://placeholder/{remote_name}"
