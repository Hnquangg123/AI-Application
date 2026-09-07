def estimate_tokens(text: str) -> int:
    # Fast approximation used for simple prompt length checks.
    return max(1, len(text.split()))


def truncate_to_token_budget(text: str, max_tokens: int) -> str:
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[:max_tokens])
