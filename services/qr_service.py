from __future__ import annotations

from pathlib import Path

import qrcode


class QRService:
    def __init__(self, output_dir: str) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_qr_for_identifier(self, identifier: str) -> Path:
        qr = qrcode.QRCode(version=2, box_size=10, border=4)
        qr.add_data(identifier)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        file_path = self.output_dir / f"{identifier}.png"
        image.save(file_path)
        return file_path
