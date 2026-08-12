"""Unit tests for FR11/FR13 intent classification (`src/nlquery/intent.py`)
-- the 7 fixed question shapes from `PRODUCT_BRIEF.md`, plus FR13's
"anything else is unsupported" contract.
"""

from __future__ import annotations

import pytest

from src.nlquery.intent import classify

# The exact 7 golden question wordings from PRODUCT_BRIEF.md, each paired
# with the question_type and entity slots they must resolve to.
GOLDEN_QUESTIONS = [
    (
        "What applications/services directly consume Customer API v1?",
        "consumers_of",
        {"entity": "Customer API v1"},
    ),
    (
        "What does Order Service depend on?",
        "depends_on",
        {"entity": "Order Service"},
    ),
    (
        "Who owns applications downstream from Customer API v1?",
        "owners_downstream",
        {"entity_type": "applications", "entity": "Customer API v1"},
    ),
    (
        "Which business capabilities depend on Order Database?",
        "capabilities_of",
        {"entity": "Order Database"},
    ),
    (
        "What is the dependency path between Storefront and Customer Database?",
        "path_between",
        {"source": "Storefront", "target": "Customer Database"},
    ),
    (
        "Which APIs are consumed by Order Management?",
        "consumed_by",
        {"entity": "Order Management"},
    ),
    (
        "What applications use Customer Database?",
        "used_by",
        {"entity": "Customer Database"},
    ),
]


class TestClassifyGoldenQuestions:
    @pytest.mark.parametrize(("question", "question_type", "entities"), GOLDEN_QUESTIONS)
    def test_classifies_each_golden_question(
        self, question: str, question_type: str, entities: dict[str, str]
    ) -> None:
        intent = classify(question)
        assert intent is not None
        assert intent.question_type == question_type
        assert intent.entities == entities

    def test_trailing_question_mark_is_optional(self) -> None:
        with_mark = classify("What does Order Service depend on?")
        without = classify("What does Order Service depend on")
        assert with_mark == without

    def test_classification_is_case_insensitive(self) -> None:
        intent = classify("WHAT DOES ORDER SERVICE DEPEND ON?")
        assert intent is not None
        assert intent.question_type == "depends_on"
        # Original casing of the entity name is preserved for resolution.
        assert intent.entities["entity"] == "ORDER SERVICE"


class TestClassifyUnsupported:
    @pytest.mark.parametrize(
        "question",
        [
            "",
            "hello",
            "What is the weather today?",
            "Summarize the dependency graph",
            "Who invented Order Service?",
            "Why does Storefront call Customer API v1?",
        ],
    )
    def test_returns_none_for_unsupported_shapes(self, question: str) -> None:
        assert classify(question) is None
