import re
from typing import Any, Dict, List, Literal

from pydantic import BaseModel

from src.core.logger import get_logger

logger = get_logger(__name__)


class Vote(BaseModel):
    agent_name: str
    decision: Literal["APPROVE", "REJECT"]
    reason: str


class ConsensusResult(BaseModel):
    decision: Literal["APPROVE", "REJECT", "INCONCLUSIVE"]
    votes: List[Vote]
    consensus_met: bool
    summary: str


class ConsensusManager:
    """
    Manages consensus gathering for critical decisions.
    """

    def __init__(self):
        pass

    def evaluate(
        self, votes: List[Vote], threshold_ratio: float = 0.5
    ) -> ConsensusResult:
        """
        Evaluates the consensus based on a list of votes.
        """
        if not votes:
            return ConsensusResult(
                decision="INCONCLUSIVE",
                votes=[],
                consensus_met=False,
                summary="No votes received.",
            )

        approvals = [v for v in votes if v.decision == "APPROVE"]
        rejections = [v for v in votes if v.decision == "REJECT"]

        approval_ratio = len(approvals) / len(votes)

        # Determine the majority decision
        decision = "APPROVE" if approval_ratio > threshold_ratio else "REJECT"

        # Consensus is met if there's a clear majority (either for or against)
        # For simplicity, we define it as meeting the threshold for the decision.
        consensus_met = (
            decision == "APPROVE" and approval_ratio > threshold_ratio
        ) or (decision == "REJECT" and (len(rejections) / len(votes)) > threshold_ratio)

        summary = f"Consensus Result: {decision}. Total Votes: {len(votes)} (Approvals: {len(approvals)}, Rejections: {len(rejections)})"

        logger.info(
            "consensus_evaluated", decision=decision, consensus_met=consensus_met
        )

        return ConsensusResult(
            decision=decision, votes=votes, consensus_met=consensus_met, summary=summary
        )

    def parse_vote(self, agent_name: str, content: str) -> Vote:
        """
        Parses an agent's response to extract their vote.
        Expected format: "DECISION: APPROVE\nREASON: ..."
        """
        decision_match = re.search(
            r"DECISION:\s*(APPROVE|REJECT)", content, re.IGNORECASE
        )
        reason_match = re.search(r"REASON:\s*(.*)", content, re.DOTALL | re.IGNORECASE)

        decision = (
            decision_match.group(1).upper() if decision_match else "REJECT"
        )  # Default to Reject if unclear
        reason = (
            reason_match.group(1).strip()
            if reason_match
            else "No explicit reason provided."
        )

        return Vote(agent_name=agent_name, decision=decision, reason=reason)


# Global singleton
consensus_manager = ConsensusManager()
