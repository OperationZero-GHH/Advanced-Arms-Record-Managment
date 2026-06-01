from __future__ import annotations

from typing import Optional

import cv2
from pyzbar.pyzbar import decode


class BarcodeScanner:
    def scan_once_from_webcam(self, camera_index: int = 0) -> Optional[str]:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return None
        try:
            ok, frame = cap.read()
            if not ok:
                return None
            decoded = decode(frame)
            if not decoded:
                return None
            return decoded[0].data.decode("utf-8")
        finally:
            cap.release()
