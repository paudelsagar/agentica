import os

from src.agents.coder_agent import CoderAgent
from src.agents.research_agent import ResearchAgent
from src.core.model_router import ModelRouter


def test_model_ensemble():
    print("\n--- Phase 11: Multi-Model Ensemble Test ---")

    # 1. Test ResearchAgent (Fast Tier)
    print("\n1. Testing ResearchAgent (fast tier)...")
    researcher = ResearchAgent()
    resolved_model = researcher.llm.model
    expected_model = ModelRouter.TIER_MAPPINGS["google"]["fast"]

    print(f"Agent Model: {resolved_model}")
    print(f"Expected: {expected_model}")

    if resolved_model == expected_model:
        print("SUCCESS: ResearchAgent correctly mapped to 'fast' tier.")
    else:
        print("FAILURE: ResearchAgent model mismatch.")

    # 2. Test CoderAgent (Heavy Tier)
    print("\n2. Testing CoderAgent (heavy tier)...")
    coder = CoderAgent()
    resolved_model = coder.llm.model
    expected_model = ModelRouter.TIER_MAPPINGS["google"]["heavy"]

    print(f"Agent Model: {resolved_model}")
    print(f"Expected: {expected_model}")

    if resolved_model == expected_model:
        print("SUCCESS: CoderAgent correctly mapped to 'heavy' tier.")
    else:
        print("FAILURE: CoderAgent model mismatch.")

    # 3. Test Raw Model Name Fallback
    print("\n3. Testing Raw Model Name Fallback...")
    from src.core.agent import EnterpriseAgent, EnterpriseAgentConfig

    config = EnterpriseAgentConfig(
        name="TestAgent",
        role="Tester",
        model_provider="openai",
        model_tier="gpt-4o-mini",  # direct name passed as tier
    )
    test_agent = EnterpriseAgent(config)
    resolved_model = test_agent.llm.model_name

    print(f"Agent Model: {resolved_model}")
    print(f"Expected: gpt-4o-mini")

    if resolved_model == "gpt-4o-mini":
        print("SUCCESS: Raw model name fallback works.")
    else:
        print("FAILURE: Raw model name mismatch.")


if __name__ == "__main__":
    test_model_ensemble()
