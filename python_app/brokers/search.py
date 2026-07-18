"""
Broker search utility.
Searches PROVIDER_INFO by name (substring / word-match), provider key, or NSE member code.
"""

from typing import Optional
from .registry import PROVIDER_INFO

# Words to strip when matching names (not case-sensitive)
_NAME_STRIP = {
    "private", "limited", "ltd", "pvt", "llp",
    "india", "ireland", "singapore", "usa", "uk",
    "the", "of", "and", "&",
}


def _score(key: str, info: dict, q_lower: str) -> tuple[int, str, str] | None:
    """
    Returns (score, match_field, display_name) or None if no match.
    Higher score = better match.
    match_field: 'key' | 'nse_code' | 'name_exact' | 'name_word' | 'name_substr'
    """
    name = info.get("name", "").lower()

    # 1. Exact key match
    if key == q_lower:
        return (100, "key", key)

    # 2. Key starts-with
    if key.startswith(q_lower):
        return (90, "key", key)

    # 3. NSE code exact
    nse_code = info.get("nse_code", "").lower()
    if nse_code and q_lower == nse_code:
        return (85, "nse_code", info["name"])

    # 4. Name exact match (after stripping common suffixes)
    name_stripped = name
    for w in _NAME_STRIP:
        name_stripped = name_stripped.replace(f" {w} ", " ")
        name_stripped = name_stripped.replace(f" {w}", "")
        name_stripped = name_stripped.replace(f"{w} ", "")
    name_stripped = name_stripped.strip()
    if name_stripped == q_lower:
        return (80, "name_exact", info["name"])

    # 5. Name starts-with
    if name.startswith(q_lower):
        return (70, "name_startswith", info["name"])

    # 6. Name word match — any individual word in name starts with query
    q_words = q_lower.split()
    name_words = [w for w in name.split() if w not in _NAME_STRIP]
    for qw in q_words:
        for nw in name_words:
            if nw.startswith(qw):
                return (60, "name_word", info["name"])

    # 7. Substring match
    if q_lower in name:
        return (50, "name_substr", info["name"])

    return None


def search_brokers(
    q: str,
    limit: int = 20,
    api_status: Optional[str] = None,
) -> list[dict]:
    """
    Search brokers by name, key, or NSE code.

    Args:
        q:          Query string (min 1 char; searches are case-insensitive)
        limit:      Max results to return (default 20, max 100)
        api_status: Optional filter — one of:
                    verified | stub | deprecated | unknown | bank | individual | all
                    (default: all)

    Returns:
        List of dicts sorted by match quality:
        [{key, name, nse_code, segments, api_status, base_url, auth_type, match_field}, ...]
    """
    if not q:
        return []

    q = q.strip()
    if len(q) < 1:
        return []

    limit = min(max(1, limit), 100)
    q_lower = q.lower()

    scored: list[tuple[int, dict]] = []

    for key, info in PROVIDER_INFO.items():
        if api_status and api_status != "all":
            if info.get("api_status") != api_status:
                continue

        result = _score(key, info, q_lower)
        if result is not None:
            score, match_field, display_name = result
            entry = {
                "key": key,
                "name": info.get("name", ""),
                "nse_code": info.get("nse_code", ""),
                "segments": info.get("segments", []),
                "api_status": info.get("api_status", "unknown"),
                "base_url": info.get("base_url", ""),
                "auth_type": info.get("auth_type", "unknown"),
                "required_credentials": info.get("required_credentials", []),
                "deprecated": info.get("deprecated", False),
                "match_field": match_field,
                "score": score,
            }
            scored.append((score, entry))

    # Sort: highest score first; tie-break on name alphabetically
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))

    return [entry for _, entry in scored[:limit]]