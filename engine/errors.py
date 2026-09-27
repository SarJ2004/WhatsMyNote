"""Fixed error codes and the sentence each one renders as."""

SENTENCES = {
    "unauthenticated": "Sign in first.",
    "bad_key": "That model key was rejected.",
    "rate_unavailable": "The rate service is unavailable, so nothing was booked.",
    "no_account": "There is no account to book this against.",
    "unsupported_currency": "That currency is not supported.",
    "ambiguous": "That matches more than one record. Be more specific.",
    "unparseable": "That message could not be read as a money action.",
}


def sentence(code):
    return SENTENCES.get(code, "Something went wrong, and nothing was changed.")
