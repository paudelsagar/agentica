import re


def filter_supervisor_content(content: str) -> str:
    """
    Filter Supervisor content to extract only the human-readable summary.
    """
    filtered = content
    content_upper = filtered.upper()

    # First check if SUMMARY: prefix exists and extract content after it
    summary_upper = filtered.upper()
    if "SUMMARY:" in summary_upper:
        idx = summary_upper.find("SUMMARY:")
        filtered = filtered[idx + 8 :]  # 8 = len("SUMMARY:")

    # Find the earliest technical marker and cut there
    markers = ["[END_SUMMARY]", "PLAN:", "NEXT AGENT:", "DELEGATION:", "```tool_code"]
    end_idx = len(filtered)
    for marker in markers:
        idx = (
            filtered.upper().find(marker.upper())
            if marker != "```tool_code"
            else filtered.find(marker)
        )
        if idx != -1:
            end_idx = min(end_idx, idx)

    result = filtered[:end_idx].strip()

    if not result and content.strip():
        if "NEXT AGENT:" in content_upper:
            agent_match = re.search(
                r"NEXT AGENT:\s*([A-Z][a-z]+Agent|DevTeam)", content, re.IGNORECASE
            )
            target = agent_match.group(1) if agent_match else "specialists"
            return f"I am delegating the task to {target}..."
        return "Processing your request..."

    return result


# Test cases
test_cases = [
    {
        "input": "SUMMARY: Hello user! [END_SUMMARY] PLAN: 1. Do thing NEXT AGENT: ResearchAgent",
        "expected": "Hello user!",
    },
    {
        "input": "PLAN: 1. Do thing NEXT AGENT: ResearchAgent",
        "expected": "I am delegating the task to ResearchAgent...",
    },
    {
        "input": "NEXT AGENT: DevTeam",
        "expected": "I am delegating the task to DevTeam...",
    },
    {
        "input": "PLAN: 1. Do something technical",
        "expected": "Processing your request...",
    },
    {
        "input": "Just a normal message from AI",
        "expected": "Just a normal message from AI",
    },
]

for i, tc in enumerate(test_cases):
    actual = filter_supervisor_content(tc["input"])
    assert (
        actual == tc["expected"]
    ), f"Test {i} failed: expected '{tc['expected']}', got '{actual}'"
    print(f"Test {i} passed!")

print("All server filtering tests passed.")
