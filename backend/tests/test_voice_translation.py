"""
Voice transcription & translation tests (priority 10).
"""
import re

import pytest

from ai.speech_service.whisper import WhisperSpeechTranscriber
from ai.translation_service.nllb import NLLBTranslator
from helpers import make_upload, run

DEVA = re.compile(r"[\u0900-\u097F]")


def test_whisper_filename_routing():
    t = WhisperSpeechTranscriber()
    assert t.transcribe("audio/warning_level.wav") == "What is the flood warning level?"
    assert t.transcribe("audio/evacuation_route.mp3") == "What is the evacuation procedure for flooded highways?"
    assert t.transcribe("audio/hospital_query.wav") == "Which hospitals are located in flood zones?"
    # Unrecognized file still returns a sensible default query.
    assert "action plan" in t.transcribe("audio/misc.wav")


def test_translator_hindi():
    result = NLLBTranslator().translate("Action Plan & Official Guidelines: evacuate immediately.", "hi")
    assert "कार्य योजना" in result
    assert "तुरंत खाली करें" in result


def test_translator_marathi():
    result = NLLBTranslator().translate("Action Plan & Official Guidelines: evacuate immediately.", "mr")
    assert "कृती योजना" in result
    assert "त्वरित बाहेर पडा" in result


def test_translator_spanish():
    result = NLLBTranslator().translate("Safety precautions: alert responders.", "es")
    assert "Precauciones de seguridad" in result
    assert "Alertar a los equipos de rescate" in result


@pytest.mark.parametrize("lang", ["hi", "mr", "es"])
def test_translator_unknown_phrase_fallback(lang):
    """Unmapped phrases get an explicit 'translation unavailable' marker instead
    of silently returning English."""
    result = NLLBTranslator().translate("Quantum entanglement budgets need review", lang)
    assert result != "Quantum entanglement budgets need review"
    assert DEVA.search(result) or "Traducido" in result


def test_translate_endpoint(api_orchestrator):
    from ai.api.chat import TranslateRequest, translate_endpoint

    res = run(translate_endpoint(TranslateRequest(text="Action Plan & Official Guidelines: evacuate immediately.", target_lang="hi")))
    assert res["target_lang"] == "hi"
    assert DEVA.search(res["translated_text"])
    assert isinstance(res["translated_text"], str)


def test_summarize_endpoint(api_orchestrator):
    from ai.api.chat import SummarizeRequest, summarize_endpoint

    text = "Flood response for Pune district. Evacuate low lying zones. Deploy rescue boats to Highway 48."
    res = run(summarize_endpoint(SummarizeRequest(text=text, length="short")))
    assert isinstance(res["summary"], str)
    assert res["summary"]


def test_speech_endpoint_returns_transcription_and_grounded_answer(api_orchestrator):
    from ai.api.chat import speech_endpoint

    res = run(speech_endpoint(
        make_upload("evacuation_route.wav", b"x"),
        session_id="sp", search_mode="hybrid", target_lang="en", model_choice="Llama-3 (Local)",
    ))
    assert res["transcribed_query"] == "What is the evacuation procedure for flooded highways?"
    assert res["response"]
    assert res["evaluation"]["groundedness_score"] > 0


def test_speech_endpoint_translated_output(api_orchestrator):
    from ai.api.chat import speech_endpoint

    res = run(speech_endpoint(
        make_upload("warning_level.wav", b"x"),
        session_id="sp2", search_mode="hybrid", target_lang="hi", model_choice="Llama-3 (Local)",
    ))
    assert res["transcribed_query"] == "What is the flood warning level?"
    assert DEVA.search(res["response"]), "Hindi-route speech response should be translated"


# ---------------------------------------------------------------------------
# #11 Voice + translation hardening: invalid/empty/noisy audio must degrade to
# a usable default query, translation must preserve numbers/units/identifiers,
# and failure states must be explicit rather than silent.
# ---------------------------------------------------------------------------

def test_transcribe_missing_file_returns_default_query():
    t = WhisperSpeechTranscriber()
    text = t.transcribe("audio/definitely_missing_clip.wav")
    assert "action plan" in text


def test_speech_garbage_audio_falls_back_to_default_query(api_orchestrator):
    """Non-audio bytes with a non-routed filename: recognition fails, the
    transcriber degrades to its default query, and chat still answers."""
    from ai.api.chat import speech_endpoint

    res = run(speech_endpoint(
        make_upload("misc_clip.wav", b"\x00\xff this is not audio at all"),
        session_id="sp-garbage", search_mode="hybrid", target_lang="en", model_choice="Llama-3 (Local)",
    ))
    assert res["transcribed_query"] == "What is the immediate action plan for the district?"
    assert res["response"]
    assert res["evaluation"]["groundedness_score"] >= 0


def test_speech_empty_audio_file_does_not_crash(api_orchestrator):
    from ai.api.chat import speech_endpoint

    res = run(speech_endpoint(
        make_upload("empty_capture.wav", b""),
        session_id="sp-empty", search_mode="hybrid", target_lang="en", model_choice="Llama-3 (Local)",
    ))
    assert isinstance(res["transcribed_query"], str)
    assert res["transcribed_query"]
    assert res["response"]


def test_speech_noise_routed_filename_still_transcribes(api_orchestrator):
    """A routed filename ('warning_level') always maps to its scripted query
    regardless of how corrupt the audio payload is -- noise must not derail
    the interaction."""
    from ai.api.chat import speech_endpoint

    res = run(speech_endpoint(
        make_upload("warning_level.wav", bytes(range(256)) * 4),
        session_id="sp-noise", search_mode="hybrid", target_lang="en", model_choice="Llama-3 (Local)",
    ))
    assert res["transcribed_query"] == "What is the flood warning level?"
    assert res["response"]


@pytest.mark.parametrize("lang", ["hi", "mr", "es"])
def test_translation_preserves_numbers_units_and_identifiers(lang):
    """Thresholds, radii, and road numbers are load-bearing -- a translation
    that mangles '1.8 meters' or 'Highway 48' would cause wrong evacuations."""
    text = "Evacuate immediately when water reaches 1.8 meters within 5 km on Highway 48."
    out = NLLBTranslator().translate(text, lang)
    assert "1.8" in out
    assert "5" in out
    assert "48" in out
    # The phrase really was translated, not passed through untouched.
    assert "evacuate immediately" not in out.lower()


def test_speech_translated_response_keeps_threshold_number(api_orchestrator):
    """End-to-end voice -> chat -> Hindi: the 1.8m warning threshold must
    survive translation in the actual spoken-answer path."""
    from ai.api.chat import speech_endpoint

    res = run(speech_endpoint(
        make_upload("warning_level.wav", b"x"),
        session_id="sp-num", search_mode="hybrid", target_lang="hi", model_choice="Llama-3 (Local)",
    ))
    assert DEVA.search(res["response"])
    assert "1.8" in res["response"]
    assert "1.8" in res["raw_response"]