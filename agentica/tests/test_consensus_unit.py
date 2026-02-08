import pytest
from src.core.consensus import ConsensusManager, Vote


def test_parse_vote_approve():
    manager = ConsensusManager()
    content = "DECISION: APPROVE\nREASON: All safety checks passed."
    vote = manager.parse_vote("TestAgent", content)
    assert vote.agent_name == "TestAgent"
    assert vote.decision == "APPROVE"
    assert vote.reason == "All safety checks passed."


def test_parse_vote_reject():
    manager = ConsensusManager()
    content = "DECISION: REJECT\nREASON: Security risk detected."
    vote = manager.parse_vote("TestAgent", content)
    assert vote.agent_name == "TestAgent"
    assert vote.decision == "REJECT"
    assert vote.reason == "Security risk detected."


def test_parse_vote_mixed_case():
    manager = ConsensusManager()
    content = "decision: approve\nreason: fine by me"
    vote = manager.parse_vote("TestAgent", content)
    assert vote.decision == "APPROVE"
    assert vote.reason == "fine by me"


def test_evaluate_unanimous_approve():
    manager = ConsensusManager()
    votes = [
        Vote(agent_name="Agent1", decision="APPROVE", reason="R1"),
        Vote(agent_name="Agent2", decision="APPROVE", reason="R2"),
    ]
    result = manager.evaluate(votes)
    assert result.consensus_met is True
    assert "Consensus Result: APPROVE" in result.summary


def test_evaluate_majority_approve():
    manager = ConsensusManager()
    votes = [
        Vote(agent_name="Agent1", decision="APPROVE", reason="R1"),
        Vote(agent_name="Agent2", decision="APPROVE", reason="R2"),
        Vote(agent_name="Agent3", decision="REJECT", reason="R3"),
    ]
    result = manager.evaluate(votes, threshold_ratio=0.5)
    assert result.consensus_met is True
    assert "Consensus Result: APPROVE" in result.summary


def test_evaluate_no_consensus():
    manager = ConsensusManager()
    votes = [
        Vote(agent_name="Agent1", decision="APPROVE", reason="R1"),
        Vote(agent_name="Agent2", decision="REJECT", reason="R2"),
    ]
    # 50% threshold: 1/2 is not > 0.5
    result = manager.evaluate(votes, threshold_ratio=0.5)
    assert result.consensus_met is False
    assert "Consensus Result: REJECT" in result.summary


def test_evaluate_empty_votes():
    manager = ConsensusManager()
    result = manager.evaluate([])
    assert result.consensus_met is False
    assert "No votes received." in result.summary
