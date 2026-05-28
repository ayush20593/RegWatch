import json
import requests
from .base import LLMProvider
from ...config import settings


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.ollama_url
        self.model = settings.ollama_model

    def generate(self, prompt: str) -> str:
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        full_prompt = (
            f"{prompt}\n\n"
            "Respond with valid JSON only. No markdown, no explanation. "
            f"JSON schema: {json.dumps(schema)}"
        )
        raw = self.generate(full_prompt)
        # Strip markdown code fences if model adds them
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
