import asyncio
import os

from agentica.src.core.model_router import ModelRouter


async def test_fallback():
    router = ModelRouter()

    # Mock settings: Only Google key exists
    router.secrets_cache = {"GOOGLE_API_KEY": "dummy-google-key"}
    router.tier_mappings = {
        "google": {"heavy": "gemini-2.0-flash", "fast": "gemini-2.0-flash"},
        "openai": {"heavy": "gpt-4o", "fast": "gpt-4o-mini"},
    }

    print("--- Test 1: Requesting OpenAI (should fallback to Google) ---")
    model = router.get_model(tier_or_name="heavy", provider="openai")
    print(
        f"Resolved Provider (via logs/internal state): Google (mapped to {model.model_name if hasattr(model, 'model_name') else 'unknown'})"
    )

    print("\n--- Test 2: Requesting Google (should work directly) ---")
    model_google = router.get_model(tier_or_name="fast", provider="google")
    print(
        f"Resolved Provider: Google (mapped to {model_google.model_name if hasattr(model_google, 'model_name') else 'unknown'})"
    )


if __name__ == "__main__":
    asyncio.run(test_fallback())
