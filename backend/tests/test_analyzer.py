import json
from app.services.llm.base import LLMProvider
from app.services.llm.prompts import build_analysis_prompt
from app.services.analyzer import chunk_and_summarise


class FakeLLM(LLMProvider):
    def generate(self, prompt: str) -> str:
        return "Summary of chunk."

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        return {
            "summary": "This is a test summary.\n\nSecond paragraph.",
            "applicability": "Applicable to NBFC-ICC.",
            "conclusion": "Low risk operational update.",
            "implementation": [
                {"step": 1, "action": "Update DB", "detail": "Remove entries.", "role": "Compliance Officer", "urgency": "Immediate"}
            ],
            "risk_level": "Low",
        }


def test_build_prompt_includes_org_name():
    org = {"name": "Test NBFC", "nbfc_type": "ICC", "product_lines": "Digital Lending",
           "aum_band": "<100Cr", "geographies": "Maharashtra", "compliance_risk_areas": "KYC"}
    prompt = build_analysis_prompt("Doc text here", org)
    assert "Test NBFC" in prompt
    assert "ICC" in prompt
    assert "Digital Lending" in prompt


def test_chunk_and_summarise_small_text():
    provider = FakeLLM()
    text = "Short text"
    result = chunk_and_summarise(text, provider)
    assert result == "Short text"


def test_chunk_and_summarise_large_text():
    provider = FakeLLM()
    text = "word " * 2000  # ~10000 chars
    result = chunk_and_summarise(text, provider)
    assert isinstance(result, str)
    assert len(result) > 0


def test_fake_llm_generate_structured():
    provider = FakeLLM()
    result = provider.generate_structured("prompt", {})
    assert result["risk_level"] == "Low"
    assert len(result["implementation"]) == 1
