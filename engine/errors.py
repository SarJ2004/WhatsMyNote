"""Fixed error codes, the HTTP status each returns, and the sentence each renders as."""

SENTENCES = {
    "unauthenticated": "Sign in first.",
    "bad_key": "That model key was rejected.",
    "no_key": "That needs a model key. Clear bookings work without one.",
    "rate_unavailable": "The rate service is unavailable, so nothing was booked.",
    "no_account": "There is no account to book this against.",
    "unsupported_currency": "That currency is not supported.",
    "ambiguous": "That matches more than one record. Be more specific.",
    "unparseable": "That message could not be read as a money action.",
    "limit_reached": "Today's model allowance is used up. Clear bookings still work.",
    "internal": "Something went wrong, and nothing was changed.",
}

STATUS = {
    "unauthenticated": 401,
    "bad_key": 400,
    "no_key": 400,
    "limit_reached": 429,
    "rate_unavailable": 503,
    "no_account": 422,
    "unsupported_currency": 422,
    "ambiguous": 422,
    "unparseable": 422,
}


class EngineError(Exception):
    """A refusal with a fixed code. The message is for people and never carries a key.

    reason, when given, says for the log which check refused. It is fixed text
    written here, never a key or anything the person or the model wrote.
    """

    def __init__(self, code, message, status=None, reason=None):
        super().__init__(message)
        self.code = code
        self.status = status or STATUS.get(code, 500)
        self.reason = reason


def sentence(code):
    return SENTENCES.get(code, SENTENCES["internal"])
