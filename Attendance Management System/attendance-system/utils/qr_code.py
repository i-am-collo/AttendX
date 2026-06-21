"""
utils/qr_code.py
----------------
Generate QR codes for attendance sessions.
"""

from __future__ import annotations
import os
import tempfile


def generate_session_qr(session_id: int, subject_code: str) -> str | None:
    """
    Generate a QR code PNG for a session.
    The QR encodes: 'ATTEND:{session_id}:{subject_code}'
    Returns the path to the saved PNG or None on error.
    """
    try:
        import qrcode
        from PIL import Image

        data = f"ATTEND:{session_id}:{subject_code}"
        qr   = qrcode.QRCode(
            version           = 1,
            error_correction  = qrcode.constants.ERROR_CORRECT_H,
            box_size          = 10,
            border            = 4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img  = qr.make_image(fill_color="#1A1A2E", back_color="white")
        path = os.path.join(tempfile.gettempdir(), f"session_{session_id}_qr.png")
        img.save(path)
        return path
    except Exception as e:
        print(f"[QR] Failed to generate QR: {e}")
        return None


def parse_qr_payload(payload: str) -> tuple[int, str] | None:
    """
    Parse the QR payload 'ATTEND:{session_id}:{subject_code}'.
    Returns (session_id, subject_code) or None if invalid.
    """
    try:
        parts = payload.strip().split(":")
        if len(parts) == 3 and parts[0] == "ATTEND":
            return int(parts[1]), parts[2]
    except Exception:
        pass
    return None
