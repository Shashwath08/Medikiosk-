import io
import base64
import qrcode
from qrcode.image.pil import PilImage

class QRService:
    """
    QR Code Generation Service for MediKiosk.
    
    SECURITY PRINCIPLE:
    This service strictly encodes opaque tokens (e.g. MEDIKIOSK:<token>).
    It NEVER writes medical diagnosis, patient names, phone numbers, or ABHA numbers
    directly into the QR code matrix. The Doctor Dashboard retrieves the clinical
    file only after secure authentication with the backend.
    """

    @staticmethod
    def generate_qr_payload(token: str) -> str:
        """Standardized protocol header for MediKiosk tokens."""
        return f"MEDIKIOSK:{token}"

    @classmethod
    def generate_qr_bytes(cls, token: str) -> bytes:
        payload = cls.generate_qr_payload(token)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)

        img: PilImage = qr.make_image(fill_color="#1E3A8A", back_color="#FFFFFF")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @classmethod
    def generate_qr_data_uri(cls, token: str) -> str:
        img_bytes = cls.generate_qr_bytes(token)
        encoded = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

qr_service = QRService()
