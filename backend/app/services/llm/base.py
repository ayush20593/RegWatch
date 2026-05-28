from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a text response from prompt."""
        ...

    @abstractmethod
    def generate_structured(self, prompt: str, schema: dict) -> dict:
        """Generate a JSON response conforming to schema."""
        ...
