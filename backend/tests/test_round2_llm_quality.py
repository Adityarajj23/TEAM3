"""Tests for Task 1: LLM Quality, Per-Clause Generation, Quote Verification & Repair Loop."""
from __future__ import annotations

import json
from typing import Any

from app.guardrails.quotes import verify_quote
from app.llm.base import Completion, LLMProvider
from app.llm.schemas import AcceptanceCriteriaBatch
from app.services.evals import evaluate_scenario, repair_ungrounded_quotes


class MockRepairProvider(LLMProvider):
    name = "mock_repair"
    model = "mock-model"

    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = list(responses)
        self.call_count = 0
        self.prompts: list[str] = []

    def configured(self) -> bool:
        return True

    def complete_json(self, system: str, user: str, timeout: float) -> Completion:
        self.call_count += 1
        self.prompts.append(user)
        idx = min(self.call_count - 1, len(self.responses) - 1)
        resp = self.responses[idx]
        return Completion(json.dumps(resp), self.name, self.model)


def test_quote_repair_loop_fixes_hallucinated_quote(app):
    """Verify that an ungrounded quote triggers a repair prompt with the exact failing quote and clause text,
    and accepts the repaired verbatim quote on attempt 2."""
    clause_key = "TEST.C1"
    clause_text = "Employees must take a mandatory thirty minute meal break after five hours."
    texts = {clause_key: clause_text}

    # Attempt 1: Paraphrased quote (not verbatim)
    bad_resp = {
        "criteria": [{
            "clause_keys": [clause_key],
            "description": "Meal break required",
            "preconditions": "Shift > 5 hours",
            "expected_behaviour": "30 min break",
            "validation_conditions": ["Break recorded"],
            "source_quote": "Employees need a 30-minute break after 5 hours of work",  # Paraphrased!
            "confidence": 0.9,
            "rationale": "Test",
            "assumptions": []
        }]
    }

    # Attempt 2: Repaired verbatim quote
    good_resp = {
        "criteria": [{
            "clause_keys": [clause_key],
            "description": "Meal break required",
            "preconditions": "Shift > 5 hours",
            "expected_behaviour": "30 min break",
            "validation_conditions": ["Break recorded"],
            "source_quote": "thirty minute meal break after five hours",  # Verbatim!
            "confidence": 0.9,
            "rationale": "Test",
            "assumptions": []
        }]
    }

    provider = MockRepairProvider([bad_resp, good_resp])
    chain = [provider]
    stats = {"calls": 0, "schema_ok": 0, "repairs": 0}

    valid_items, rejected_items = repair_ungrounded_quotes(
        chain=chain,
        task="acceptance_criteria",
        initial_items=bad_resp["criteria"],
        schema=AcceptanceCriteriaBatch,
        texts=texts,
        stats=stats,
        max_attempts=2
    )

    assert len(valid_items) == 1
    assert len(rejected_items) == 0
    assert valid_items[0]["source_quote"] == "thirty minute meal break after five hours"
    assert verify_quote(valid_items[0]["source_quote"], [clause_text])
    # Verify the repair prompt was sent with specific feedback
    assert provider.call_count >= 1
    assert any("thirty minute meal break after five hours" in p or "mandatory thirty minute" in p or "FAILED" in p
               for p in provider.prompts)


def test_ungrounded_item_rejected_after_max_repairs(app):
    """Verify that an item failing quote verification after 2 repair attempts is rejected and recorded with reason."""
    clause_key = "TEST.C1"
    clause_text = "Employees must take a mandatory thirty minute meal break after five hours."
    texts = {clause_key: clause_text}

    persistently_bad = {
        "criteria": [{
            "clause_keys": [clause_key],
            "description": "Meal break required",
            "preconditions": "Shift > 5 hours",
            "expected_behaviour": "30 min break",
            "validation_conditions": ["Break recorded"],
            "source_quote": "Paraphrased non-existent quote that will never match",
            "confidence": 0.9,
            "rationale": "Test",
            "assumptions": []
        }]
    }

    provider = MockRepairProvider([persistently_bad, persistently_bad, persistently_bad])
    chain = [provider]
    stats = {"calls": 0, "schema_ok": 0, "repairs": 0}

    valid_items, rejected_items = repair_ungrounded_quotes(
        chain=chain,
        task="acceptance_criteria",
        initial_items=persistently_bad["criteria"],
        schema=AcceptanceCriteriaBatch,
        texts=texts,
        stats=stats,
        max_attempts=2
    )

    assert len(valid_items) == 0
    assert len(rejected_items) == 1
    assert rejected_items[0]["quote"] == "Paraphrased non-existent quote that will never match"
    assert "Ungrounded" in rejected_items[0]["reason"]
    assert clause_key in rejected_items[0]["reason"]


def test_evaluate_scenario_with_mock_achieves_full_coverage(app):
    """Verify that evaluate_scenario runs per clause/group and achieves 100% clause coverage under mock."""
    from app.llm import router
    from app.services.evals import load_golden

    scenarios = load_golden()
    sc = scenarios[0]  # GOLD-001 (Weekly overtime threshold)
    chain = router.explicit_chain("mock")

    result = evaluate_scenario(chain, sc)
    assert result["passed"] is True
    metrics = result["metrics"]
    assert metrics["clause_coverage"] == 1.0
    assert metrics["ungrounded_rate"] == 0.0
    assert metrics["schema_pass_rate"] == 1.0
    assert metrics["clause_count_parsed"] >= 3
    assert metrics["tests_generated"] >= 1
    assert len(metrics["ungrounded_quotes"]) == 0


def test_evaluate_scenario_records_ungrounded_reasons(app):
    """Verify that evaluate_scenario records exact ungrounded quote details when an item is persistently bad."""
    sc = {
        "key": "FAIL-001",
        "title": "Persistent ungrounded failure test",
        "requirement": "Employees must work 40 hours. Overtime is paid at 1.5 times the base rate.",
        "expected_clause_count": 2,
        "expected_ambiguity_terms": [],
        "expected_covered_clauses": [1, 2],
        "expected_edge_cases": [],
        "forbidden_outputs": [],
        "failure_case": {
            "result_status": "failed",
            "message": "assert False",
            "stack_trace": "",
            "expected_category": "application_defect"
        }
    }

    # Custom provider that always returns an ungrounded quote
    bad_criteria = {
        "criteria": [{
            "clause_keys": ["FAIL-001.C1"],
            "description": "Ungrounded criteria description here",
            "preconditions": "none",
            "expected_behaviour": "failure expected for invalid break",
            "validation_conditions": ["none"],
            "source_quote": "Completely hallucinated non-existent sentence text",
            "confidence": 0.9,
            "rationale": "test",
            "assumptions": []
        }]
    }
    bad_tests = {
        "tests": [{
            "title": "Ungrounded test title here",
            "description": "test description here",
            "clause_keys": ["FAIL-001.C1"],
            "ac_refs": [1],
            "preconditions": "",
            "test_data": {},
            "steps": [{"action": "Execute test action", "expected": "Expectation text"}],
            "expected_result": "Result matches specification",
            "priority": "high",
            "test_type": "functional",
            "confidence": 0.8,
            "source_quote": "Another fake hallucinated quote that will fail quote check",
            "rationale": "",
            "automation": "manual",
            "script": None
        }]
    }

    class HallucinatingProvider(LLMProvider):
        name = "hallucinating"
        model = "fake-v1"

        def configured(self) -> bool:
            return True

        def complete_json(self, system: str, user: str, timeout: float) -> Completion:
            if "acceptance_criteria" in user or "criteria" in user:
                return Completion(json.dumps(bad_criteria), self.name, self.model)
            if "test_cases" in user or "tests" in user:
                return Completion(json.dumps(bad_tests), self.name, self.model)
            if "requirement_analysis" in user:
                return Completion(json.dumps({
                    "clauses": [{"clause_key": "FAIL-001.C1", "business_rules": ["rule"], "ambiguities": [], "missing_information": [], "conflicts_with": [], "clarifying_questions": [], "interpretation": "test"}],
                    "assumptions": [], "summary": "test"
                }), self.name, self.model)
            return Completion(json.dumps({
                "category": "application_defect", "observed_facts": ["Assertion failed fact"], "hypotheses": [], "probable_cause": "cause",
                "suggested_actions": [], "confidence": 0.9, "recommended_severity": "high", "recommended_priority": "p1",
                "defect_title": "title", "defect_summary": "summary"
            }), self.name, self.model)

    chain = [HallucinatingProvider()]
    result = evaluate_scenario(chain, sc)

    metrics = result["metrics"]
    assert metrics["ungrounded_rate"] > 0
    assert len(metrics["ungrounded_quotes"]) > 0
    first_ungrounded = metrics["ungrounded_quotes"][0]
    assert "quote" in first_ungrounded
    assert "clauses" in first_ungrounded
    assert "rationale" in first_ungrounded
    assert "Ungrounded" in first_ungrounded["rationale"]

