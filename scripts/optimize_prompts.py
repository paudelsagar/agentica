import argparse
import asyncio
import sys

from src.core.prompt_optimizer import optimizer


async def main():
    parser = argparse.ArgumentParser(
        description="Optimize agent system prompts based on failure trajectories."
    )
    parser.add_argument(
        "--agent",
        type=str,
        required=True,
        help="Name of the agent to optimize (e.g., CoderAgent)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Automatically apply the optimization to agents.yaml",
    )

    args = parser.parse_args()

    print(f"\n--- Prompt Optimization Loop: {args.agent} ---")

    new_prompt = await optimizer.optimize_agent(args.agent)

    if new_prompt:
        print("\n[SUGGESTED NEW PROMPT]")
        print("-" * 40)
        print(new_prompt)
        print("-" * 40)

        if args.apply:
            optimizer.apply_optimization(args.agent, new_prompt)
            print(f"\nSUCCESS: Optimization applied to agents.yaml for {args.agent}")
        else:
            print("\nNOTE: Run with --apply to update agents.yaml")
    else:
        print(
            f"\nNo optimization needed for {args.agent} at this time (no failures found)."
        )


if __name__ == "__main__":
    asyncio.run(main())
