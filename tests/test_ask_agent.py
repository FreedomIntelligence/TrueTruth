"""Tests for AskAgent routing logic."""
from unittest.mock import MagicMock
from src.agents.ask_agent import AskAgent


def _make_llm_full_pipeline(ebm_framework="pico"):
    llm = MagicMock()
    router_resp = MagicMock()
    router_resp.content = (
        f'{{"route_type": "full_pipeline", "route_confidence": 0.9, '
        f'"question_type": "Therapy", "ebm_framework": "{ebm_framework}", '
        f'"routing_rationale": "test"}}'
    )
    ebm_resp = MagicMock()
    ebm_resp.content = (
        f'{{"query_type": "{ebm_framework}", "patient": "P", '
        f'"primary_focus": "I", "outcome": "O", "keywords": ["kw"]}}'
    )
    llm.invoke.side_effect = [router_resp, ebm_resp]
    return llm


def _make_llm_direct_answer():
    llm = MagicMock()
    router_resp = MagicMock()
    router_resp.content = (
        '{"route_type": "direct_answer", "route_confidence": 0.95, '
        '"question_type": "Background", "ebm_framework": "pico", '
        '"routing_rationale": "emergency"}'
    )
    direct_resp = MagicMock()
    direct_resp.content = '{"answer": "Call 911", "requires_pipeline": false}'
    llm.invoke.side_effect = [router_resp, direct_resp]
    return llm


def test_ask_agent_full_pipeline_sets_route_type():
    agent = AskAgent(llm=_make_llm_full_pipeline())
    state = {"original_question": "Does SGLT2i reduce mortality in HF?",
             "backtrack_reason": None, "backtrack_history": []}
    result = agent.execute(state)
    assert result["route_type"] == "full_pipeline"
    assert result["ebm_query"] is not None
    assert result.get("should_terminate") is not True


def test_ask_agent_direct_answer_sets_terminate():
    agent = AskAgent(llm=_make_llm_direct_answer())
    state = {"original_question": "CPR depth?",
             "backtrack_reason": None, "backtrack_history": []}
    result = agent.execute(state)
    assert result["route_type"] == "direct_answer"
    assert result["should_terminate"] is True
    assert result["direct_answer_output"] is not None
