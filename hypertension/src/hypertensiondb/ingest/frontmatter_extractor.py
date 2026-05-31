from abc import ABC, abstractmethod


class BaseFrontmatterExtractor(ABC):
    """Abstract interface for extracting structured frontmatter from raw text."""

    @abstractmethod
    def extract(self, text: str, evidence_type: str) -> dict:
        """Return a dict suitable for Pydantic frontmatter construction.

        Required output keys: type, title{zh|en}, authors, year, language, status.
        For RCT/SR/META/TCM also: pico, risk_of_bias, grade.
        Always set extracted_by='llm' so callers know fields need human review.
        Status MUST be 'draft' regardless of extraction confidence.
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


class MockFrontmatterExtractor(BaseFrontmatterExtractor):
    """Deterministic skeleton extractor for tests. Doesn't read text content."""

    def extract(self, text: str, evidence_type: str) -> dict:
        result: dict = {
            "type": evidence_type,
            "title": {"zh": "未提供标题", "en": None},
            "authors": ["Unknown"],
            "year": 2026,
            "language": "zh",
            "status": "draft",
            "tags": [],
            "extracted_by": "llm",
        }
        if evidence_type in {"RCT", "SR", "META", "TCM"}:
            result["pico"] = {
                "population": {"condition": "未提供"},
                "intervention": {"name": "未提供"},
                "outcomes": {},
            }
            result["risk_of_bias"] = {"tool": "RoB2", "overall": "some_concerns"}
            result["grade"] = {"level": "low"}
        return result

    @property
    def model_name(self) -> str:
        return "mock"
