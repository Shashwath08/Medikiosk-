import re
from typing import Optional, Dict, Any, List
from backend.integrations.base import BaseAIService
from backend.schemas.history import (
    DynamicQuestion,
    QuestionType,
    OptionItem,
    VoiceHistoryResponse,
    RedFlagAlert,
)

# Multilingual question templates for Indian languages
LOCALIZED_QUESTIONS = {
    "q_chief_complaint": {
        "en": "What is the main problem bringing you to the hospital today?",
        "hi": "आज अस्पताल आने का मुख्य कारण क्या है?",
        "ml": "ഇന്ന് ആശുപത്രിയിൽ വരാനുള്ള പ്രധാന കാരണം എന്താണ്?",
        "ta": "இன்று நீங்கள் மருத்துவமனைக்கு வந்ததற்கான முக்கிய காரணம் என்ன?",
        "kn": "ಇಂದು ಆಸ್ಪತ್ರೆಗೆ ಭೇಟಿ ನೀಡಲು ಮುಖ್ಯ ಕಾರಣವೇನು?",
        "te": "ఈరోజు ఆసుపత్రికి రావడానికి ప్రధాన కారణం ఏమిటి?"
    },
    "q_pain_map": {
        "en": "Where exactly are you feeling pain or discomfort? Please select on the body map.",
        "hi": "आपको शरीर में कहाँ दर्द या परेशानी हो रही है? कृपया शरीर के नक्शे पर चुनें।",
        "ml": "ശരീരത്തിൽ എവിടെയാണ് നിങ്ങൾക്ക് വേദനയോ അസ്വസ്ഥതയോ ഉള്ളത്? മാപ്പിൽ തിരഞ്ഞെടുക്കുക.",
        "ta": "உடலில் எங்கு வலி அல்லது அசௌகரியத்தை உணர்கிறீர்கள்? படத்தில் தேர்ந்தெடுக்கவும்.",
        "kn": "ದೇಹದಲ್ಲಿ ಎಲ್ಲಿ ನೋವು ಅಥವಾ ಅಸ್ವಸ್ಥತೆ ಇದೆ? ದಯವಿಟ್ಟು ನಕ್ಷೆಯಲ್ಲಿ ಆಯ್ಕೆಮಾಡಿ.",
        "te": "శరీరంలో ఎక్కడ నొప్పి లేదా అసౌకర్యంగా ఉంది? దయచేసి శరీర పటంలో ఎంచుకోండి."
    },
    "q_duration": {
        "en": "How long have you been experiencing this problem?",
        "hi": "यह समस्या आपको कितने समय से हो रही है?",
        "ml": "ഈ പ്രശ്നം എത്ര ദിവസമായി അനുഭവപ്പെടുന്നു?",
        "ta": "இந்த பிரச்சனை எத்தனை நாட்களாக உள்ளது?",
        "kn": "ಈ ಸಮಸ್ಯೆ ಎಷ್ಟು ದಿನಗಳಿಂದ ಇದೆ?",
        "te": "ఈ సమస్య ఎంతకాలంగా ఉంది?"
    },
    "q_severity": {
        "en": "On a scale of 1 to 10, how severe is your discomfort right now?",
        "hi": "1 से 10 के पैमाने पर, अभी आपकी परेशानी कितनी गंभीर है?",
        "ml": "1 മുതൽ 10 വരെയുള്ള അളവിൽ, ഇപ്പോൾ നിങ്ങളുടെ പ്രയാസം എത്രത്തോളമുണ്ട്?",
        "ta": "1 முதல் 10 வரையிலான அளவில், உங்கள் வலி எவ்வளவு தீவிரமாக உள்ளது?",
        "kn": "1 ರಿಂದ 10 ರ ಪ್ರಮಾಣದಲ್ಲಿ, ನಿಮ್ಮ ಅಸ್ವಸ್ಥತೆಯ ತೀವ್ರತೆ ಎಷ್ಟು?",
        "te": "1 నుండి 10 వరకు, ప్రస్తుతం మీ అసౌకర్యం ఎంత తీవ్రంగా ఉంది?"
    },
    "q_prior_meds": {
        "en": "Have you taken any medications for this issue recently?",
        "hi": "क्या आपने हाल ही में इसके लिए कोई दवा ली है?",
        "ml": "അടുത്തിടെ എന്തെങ്കിലും മരുന്ന് കഴിച്ചിരുന്നോ?",
        "ta": "சமீபத்தில் இதற்காக ஏதேனும் மருந்து உட்கொண்டீர்களா?",
        "kn": "ಇತ್ತೀಚೆಗೆ ಯಾವುದಾದರೂ ಔಷಧಿ ತೆಗೆದುಕೊಂಡಿದ್ದೀರಾ?",
        "te": "ఇటీవల దీని కోసం ఏదైనా మందు తీసుకున్నారా?"
    },
    "q_allergies": {
        "en": "Do you have any known drug or medicine allergies?",
        "hi": "क्या आपको किसी दवा से कोई एलर्जी है?",
        "ml": "മരുന്നുകളോട് എന്തെങ്കിലും അലർജി ഉണ്ടോ?",
        "ta": "மருந்துகளால் ஏதேனும் ஒவ்வாமை (Allergy) உள்ளதா?",
        "kn": "ಯಾವುದಾದರೂ ಔಷಧಿಯಿಂದ ಅಲರ್ಜಿ ಇದೆಯೇ?",
        "te": "మందులతో ఏవైనా అలెర్జీలు ఉన్నాయా?"
    }
}

class MockAIService(BaseAIService):
    """
    Simulates Member 2's AI and Voice Intelligence System.
    This mock enables full end-to-end interactive flows without requiring
    external GPU or cloud LLM dependencies during Member 1 testing.
    """

    def __init__(self):
        # In-memory context cache for active sessions
        self._session_state: Dict[str, Dict[str, Any]] = {}

    def get_next_question(
        self,
        session_id: str,
        current_question_id: Optional[str] = None,
        last_answer: Optional[Any] = None,
        language: str = "en",
        session_context: Optional[Dict[str, Any]] = None
    ) -> Optional[DynamicQuestion]:
        lang = language if language in LOCALIZED_QUESTIONS.get("q_chief_complaint", {}) else "en"

        # Step 1: Initial Question - Chief Complaint
        if current_question_id is None or current_question_id == "":
            return DynamicQuestion(
                question_id="q_chief_complaint",
                question=LOCALIZED_QUESTIONS["q_chief_complaint"].get(lang, LOCALIZED_QUESTIONS["q_chief_complaint"]["en"]),
                question_type=QuestionType.SINGLE_CHOICE,
                options=[
                    OptionItem(id="fever", label="Fever / Chills", icon="thermometer"),
                    OptionItem(id="cough", label="Cough / Cold / Throat Pain", icon="activity"),
                    OptionItem(id="body_pain", label="Body / Muscle / Joint Pain", icon="user"),
                    OptionItem(id="chest_discomfort", label="Chest Pain / Tightness", icon="heart"),
                    OptionItem(id="stomach_pain", label="Stomach / Abdominal Pain", icon="circle"),
                    OptionItem(id="headache", label="Headache / Dizziness", icon="alert-circle"),
                    OptionItem(id="other", label="Other Symptoms", icon="plus")
                ],
                allow_voice=True,
                allow_touch=True,
                language=lang,
                helper_text="Tap an option or press microphone to speak your main symptom."
            )

        # Step 2: Branch based on chief complaint
        if current_question_id == "q_chief_complaint":
            complaint = str(last_answer).lower() if last_answer else ""
            # If pain or specific anatomical discomfort reported, prompt the body map
            pain_keywords = ["pain", "discomfort", "ache", "stomach", "chest", "headache", "body"]
            if any(k in complaint for k in pain_keywords):
                return DynamicQuestion(
                    question_id="q_pain_map",
                    question=LOCALIZED_QUESTIONS["q_pain_map"].get(lang, LOCALIZED_QUESTIONS["q_pain_map"]["en"]),
                    question_type=QuestionType.PAIN_LOCATION,
                    options=[],
                    allow_voice=True,
                    allow_touch=True,
                    language=lang,
                    helper_text="Touch the front or back view on the body map to mark your pain."
                )
            else:
                # Go directly to duration
                return self._get_duration_question(lang)

        # Step 3: From pain map -> Duration
        if current_question_id == "q_pain_map":
            return self._get_duration_question(lang)

        # Step 4: From Duration -> Severity Slider
        if current_question_id == "q_duration":
            return DynamicQuestion(
                question_id="q_severity",
                question=LOCALIZED_QUESTIONS["q_severity"].get(lang, LOCALIZED_QUESTIONS["q_severity"]["en"]),
                question_type=QuestionType.SLIDER,
                options=[],
                min_val=1,
                max_val=10,
                unit="/10",
                allow_voice=True,
                allow_touch=True,
                language=lang,
                helper_text="Slide from 1 (Mild) to 10 (Severe / Unbearable)."
            )

        # Step 5: From Severity -> Prior Medications
        if current_question_id == "q_severity":
            return DynamicQuestion(
                question_id="q_prior_meds",
                question=LOCALIZED_QUESTIONS["q_prior_meds"].get(lang, LOCALIZED_QUESTIONS["q_prior_meds"]["en"]),
                question_type=QuestionType.YES_NO,
                options=[
                    OptionItem(id="yes", label="Yes, I took medicine"),
                    OptionItem(id="no", label="No medicine taken")
                ],
                allow_voice=True,
                allow_touch=True,
                language=lang,
                helper_text="Select Yes or No, or tell us what medicine you took."
            )

        # Step 6: From Prior Meds -> Allergies
        if current_question_id == "q_prior_meds":
            return DynamicQuestion(
                question_id="q_allergies",
                question=LOCALIZED_QUESTIONS["q_allergies"].get(lang, LOCALIZED_QUESTIONS["q_allergies"]["en"]),
                question_type=QuestionType.TEXT,
                options=[
                    OptionItem(id="none", label="No Allergies"),
                    OptionItem(id="penicillin", label="Penicillin / Antibiotics"),
                    OptionItem(id="sulfa", label="Sulfa Drugs"),
                    OptionItem(id="nsaids", label="Painkillers (Aspirin/Ibuprofen)")
                ],
                allow_voice=True,
                allow_touch=True,
                language=lang,
                is_final=True,
                helper_text="Select common allergies, type in text, or speak clearly."
            )

        # History taking questions completed
        return None

    def _get_duration_question(self, lang: str) -> DynamicQuestion:
        return DynamicQuestion(
            question_id="q_duration",
            question=LOCALIZED_QUESTIONS["q_duration"].get(lang, LOCALIZED_QUESTIONS["q_duration"]["en"]),
            question_type=QuestionType.SINGLE_CHOICE,
            options=[
                OptionItem(id="today", label="Started Today (< 24 hours)"),
                OptionItem(id="few_days", label="2 to 3 Days"),
                OptionItem(id="one_week", label="About 1 Week"),
                OptionItem(id="chronic", label="More than 2 Weeks / Chronic")
            ],
            allow_voice=True,
            allow_touch=True,
            language=lang,
            helper_text="Choose how long you have been having these symptoms."
        )

    def process_voice(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str,
        session_id: str,
        session_context: Optional[Dict[str, Any]] = None
    ) -> VoiceHistoryResponse:
        """
        Mock voice processing. In production, Member 2 connects their
        ASR engine (Whisper, Bhashini, or Google Cloud Speech API).
        """
        # Realistic simulated transcription based on audio length/session
        size = len(audio_bytes)
        transcript = "I have had severe chest discomfort and headache for two days."
        if size < 5000:
            transcript = "Yes, since yesterday."
        elif size > 20000:
            transcript = "I am having sharp pain in my upper abdomen and mild fever since last evening."

        # Check for emergency red flags in voice text
        red_flag = False
        if any(term in transcript.lower() for term in ["chest discomfort", "chest pain", "shortness of breath", "heart"]):
            red_flag = True

        # Determine next question
        next_q = self.get_next_question(
            session_id=session_id,
            current_question_id="q_chief_complaint",
            last_answer=transcript,
            language=language
        )

        return VoiceHistoryResponse(
            transcript=transcript,
            detected_language=language,
            confidence=0.96,
            next_question=next_q,
            question_id="q_chief_complaint",
            input_type="voice",
            red_flag=red_flag
        )

    def evaluate_triage(
        self,
        session_id: str,
        question_id: str,
        answer: Any,
        session_context: Optional[Dict[str, Any]] = None
    ) -> RedFlagAlert:
        """
        Triage heuristic trigger. When Member 2 connects their real clinical
        triage rules, this method will evaluate vital signs and symptom combinations.
        """
        ans_str = str(answer).lower()

        # Check for acute chest pain / heart issues / high severity
        is_chest = "chest" in ans_str or "chest_discomfort" in ans_str
        is_high_severity = False
        
        if isinstance(answer, dict):
            # Check if pain intensity is >= 8 or region is chest
            intensity = answer.get("pain_intensity", 0)
            if intensity >= 9:
                is_high_severity = True
            locs = answer.get("locations", [])
            for l in locs:
                if isinstance(l, dict) and l.get("region") == "chest":
                    is_chest = True

        if is_chest and (is_high_severity or "emergency" in ans_str):
            return RedFlagAlert(
                red_flag=True,
                severity="emergency",
                message="Priority Healthcare Alert: Severe chest discomfort detected. Please remain comfortably seated. Hospital nursing and emergency staff have been alerted to assist you immediately.",
                action_required="Dispatch nursing staff to Kiosk"
            )

        if "unconscious" in ans_str or "collapse" in ans_str:
            return RedFlagAlert(
                red_flag=True,
                severity="emergency",
                message="Immediate Medical Alert: Critical symptom reported. Emergency assistance has been summoned.",
                action_required="Emergency Response Code Blue"
            )

        return RedFlagAlert(
            red_flag=False,
            severity="none",
            message="",
            action_required=""
        )

# Global singleton mock
mock_ai_service = MockAIService()
