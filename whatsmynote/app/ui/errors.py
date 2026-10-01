"""Sentences for the engine's fixed error codes. The terminal renders these
and nothing else from an error response, so a server message can never leak
a key or an internal detail onto the screen."""

SENTENCES = {
    "unauthenticated": "You are not signed in, or your sign-in expired. Type /login to sign in.",
    "bad_key": "Your model key was rejected. Check it, or change it with /key.",
    "no_key": "Add your model key first. Type /key to add it.",
    "rate_unavailable": "Exchange rates are unavailable right now, so nothing was saved. Try again soon.",
    "no_account": "There is no account to record this in yet. Add one with /account.",
    "unsupported_currency": "That currency is not supported, so nothing was saved.",
    "ambiguous": "That matches more than one record. Add a detail, like the date or the amount.",
    "unparseable": "That did not read as money. Try something like: spent 400 on dinner",
    "limit_reached": "You have reached a usage limit for now. Wait a little, then try again.",
}

UNKNOWN = "Something went wrong, and nothing was changed."
OFFLINE = "Could not reach WhatsMyNote. Check your internet connection and try again."
TIMEOUT = "The server took too long to answer. Check /balances before sending it again."
SERVER = "The server had a problem, and nothing was changed. Try again in a moment."
CONFIRM_FAILED = "That confirmation expired or was already used, so nothing was saved. Send the message again."


def sentence_for(body, fallback=UNKNOWN):
    code = body.get("code") if isinstance(body, dict) else None
    return SENTENCES.get(code, fallback)
