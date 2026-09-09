import re
from backend.integrations.base import BaseABDMService
from backend.schemas.patient import ABHAVerifyResponse, ABHAPatientProfile

class MockABDMService(BaseABDMService):
    """
    Simulates Member 6's ABDM Gateway (Ayushman Bharat Digital Mission) integration.
    In production, Member 6 replaces this with official ABDM M1/M2/M3 API integration,
    National Health Authority (NHA) certificates, and OTP verification workflows.
    """

    def verify_abha(self, abha_id: str) -> ABHAVerifyResponse:
        cleaned = abha_id.strip()

        # Check 1: 14-digit format (with or without hyphens)
        digits_only = re.sub(r"[^\d]", "", cleaned)
        is_14_digits = len(digits_only) == 14

        # Check 2: PHR address format (e.g. username@abdm or username@sbx)
        is_phr = bool(re.match(r"^[a-zA-Z0-9._-]+@(abdm|sbx|ndhm)$", cleaned, re.IGNORECASE))

        if is_14_digits or is_phr:
            # Format nicely if digits
            formatted_id = f"{digits_only[:2]}-{digits_only[2:6]}-{digits_only[6:10]}-{digits_only[10:14]}" if is_14_digits else cleaned

            return ABHAVerifyResponse(
                verified=True,
                message="ABHA ID verified successfully via simulated ABDM Registry.",
                profile=ABHAPatientProfile(
                    abha_id=formatted_id,
                    full_name="Rajesh Kumar Sharma",
                    gender="male",
                    dob="1985-06-15",
                    phone_number="9876543210",
                    address="Ward 4, Civil Lines",
                    state="Maharashtra",
                    district="Nagpur"
                )
            )

        return ABHAVerifyResponse(
            verified=False,
            message="Invalid ABHA format. Please enter a valid 14-digit ABHA number (e.g., 91-1234-5678-9012) or a registered PHR address (e.g., name@abdm).",
            profile=None
        )

mock_abdm_service = MockABDMService()
