"""Sentences for the engine's fixed error codes. The terminal renders these
and nothing else from an error response."""

SENTENCES = {
    "unauthenticated": "Sign in first.",
    "bad_key": "That model key was rejected.",
    "rate_unavailable": "The rate service is unavailable, so nothing was booked.",
    "no_account": "There is no account to book this against.",
    "unsupported_currency": "That currency is not supported.",
    "ambiguous": "That matches more than one record. Be more specific.",
    "unparseable": "That message could not be read as a money action.",
}


def sentence_for(body):
    code = body.get("code") if isinstance(body, dict) else None
    if code in SENTENCES:
        return SENTENCES[code]
    message = body.get("message") if isinstance(body, dict) else None
    return message or "Something went wrong, and nothing was changed."
