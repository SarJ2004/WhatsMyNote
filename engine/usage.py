"""The daily ceiling on model calls. Counted by the engine's own role, so a
signed-in user can neither read nor reset their counter."""


def take(db, user, limit, day):
    """Count one model call for this user today, or refuse when the ceiling is reached."""
    if limit <= 0:
        return False
    return db.service_one(
        "insert into model_usage (user_id, day, calls) values (%s, %s, 1) "
        "on conflict (user_id, day) do update set calls = model_usage.calls + 1 "
        "where model_usage.calls < %s returning calls",
        (user, day, limit),
    ) is not None
