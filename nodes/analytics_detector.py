def analytics_detector(state):
    text = state.raw_text.lower()

    analytics_signals = [
        "top ",
        "highest",
        "lowest",
        "average",
        "avg",
        "most money",
        "least money",
        "which merchant",
        "which month",
        "which category",
        "compare",
        "difference between",
        "group by",
        "break down",
        "trend",
        "total spent",
        "total earned",
        "savings",
        "net worth",
    ]

    return {
        "analytics_mode": any(signal in text for signal in analytics_signals),
    }


def analytics_router(state):
    if getattr(state, "analytics_mode", False):
        return "analytics_query_executor"

    return "record_type_evaluator"