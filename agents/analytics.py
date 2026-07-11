"""Analytics detector — determines if a query should use SQL analytics or record queries."""


def analytics_detector(state):
    text = state.get("raw_text", "").lower()

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
        "analytics_mode": state.get("intent") == "query"
        or any(signal in text for signal in analytics_signals),
    }


def analytics_router(state):
    if (
        state.get("analytics_mode", False)
        or state.get("intent") == "query"
    ):
        return "analytics_query_executor"

    return "record_type_classifier"
