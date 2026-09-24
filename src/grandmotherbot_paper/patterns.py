from .constants import KNOWN_PATTERN_BY_SEARCHER

def published_searcher_profile(label: str):
    if label not in KNOWN_PATTERN_BY_SEARCHER:
        raise KeyError(label)
    horizon, pattern = KNOWN_PATTERN_BY_SEARCHER[label]
    return {"searcher": label, "optimal_execution_horizon_s": horizon, "pattern": pattern}

def all_published_profiles():
    return [
        published_searcher_profile(label)
        for label in KNOWN_PATTERN_BY_SEARCHER
    ]
