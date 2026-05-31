import json
import os

import openai

from hypertensiondb.ingest.frontmatter_extractor import BaseFrontmatterExtractor

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "sk-placeholder-for-module-import"


MAX_INPUT_CHARS = 12_000


_SYSTEM_PROMPT_TEMPLATE = """You are a medical-evidence extraction assistant.
Extract structured fields from the following {evidence_type} paper and return ONLY a JSON object.
Rules: no markdown, no explanation, no code fences. First character must be {{. Last character must be }}.

Required fields:
- type: exactly "{evidence_type}"
- title: {{"en": "..."}} (required; add "zh" if Chinese title present)
- authors: list of strings
- year: 4-digit integer
- language: "zh" | "en" | "bilingual"
- tags: list of short keyword strings
- status: "draft"
- pico: {{"population": {{"condition": "...", "sample_size": N}}, "intervention": {{"name": "..."}}, "comparison": {{"name": "..."}}, "outcomes": {{"primary": [{{"name": "...", "effect_size": {{"metric": "HR|RR|MD", "value": N, "ci_low": N, "ci_high": N, "p": N}}}}]}}}}
- risk_of_bias: {{"tool": "RoB2", "overall": "low" | "some_concerns" | "high"}}
- grade: {{"level": "high" | "moderate" | "low" | "very_low"}}

Omit any field you cannot extract with confidence. Return ONLY valid JSON."""


class LLMFrontmatterExtractor(BaseFrontmatterExtractor):
    """OpenAI-compatible LLM extractor using JSON mode."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        import openai as _openai
        self._client = _openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        self._model = model

    def extract(self, text: str, evidence_type: str) -> dict:
        truncated = text[:MAX_INPUT_CHARS]
        system_msg = _SYSTEM_PROMPT_TEMPLATE.format(evidence_type=evidence_type)
        # Combine system + user into single message (works better with HuatuoGPT)
        combined = f"{system_msg}\n\nPaper text:\n\n{truncated}"
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "user", "content": combined},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content or ""
            # Extract first complete JSON object from response
            if "{" in content:
                start = content.index("{")
                # Find the matching closing brace
                depth = 0
                end = start
                for i, ch in enumerate(content[start:], start):
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                content = content[start:end]
            import json as _json
            payload = _json.loads(content) if content.strip() else {}
        except Exception as e:
            print(f"[WARN] LLM extraction failed: {e}")
            payload = {}

        payload["type"] = evidence_type
        payload["status"] = "draft"
        payload["extracted_by"] = "llm"

        payload.setdefault("title", {"zh": None, "en": None})
        payload.setdefault("authors", ["Unknown"])
        payload.setdefault("year", 2026)
        payload.setdefault("language", "en")
        payload.setdefault("tags", [])

        return payload

    @property
    def model_name(self) -> str:
        return self._model
