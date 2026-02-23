critical_keywords = ["kathmandu", "nepal", "weather", "temperature", "forecast"]
def is_junk(results, q):
    if not results: return True
    first_body = results[0].get("body", "").lower()
    first_title = results[0].get("title", "").lower()
    q_lower = q.lower()
    for kw in critical_keywords:
        if kw in q_lower and (kw not in first_body and kw not in first_title):
            print(f"Rejected due to missing keyword: {kw}")
            return True
    return False

query = "What is the current weather of kathmandu nepal?"
results = [{"title": "Kathmandu Weather Forecast", "body": "Current conditions in Kathmandu, Nepal are sunny."}]
print(f"Test 1 (Perfect match): {is_junk(results, query)}")

results = [{"title": "Kathmandu Temperature Today", "body": "It is hot in the capital."}]
print(f"Test 2 (Missing Nepal, Weather, Forecast): {is_junk(results, query)}")
