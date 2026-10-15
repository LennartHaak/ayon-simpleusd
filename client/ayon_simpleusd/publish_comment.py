# -*- coding: utf-8 -*-
"""Shared helpers for writing Simple USD's own publish notes into the AYON
version comment.

ShotGrid syncs server-side straight from AYON (no direct client push), so
anything that should show up on the ShotGrid Version has to be part of
the AYON version itself - IntegrateAsset writes
instance.data["comment"] into the version it creates.
"""


def get_publisher_name(username):
    """Return the AYON user's full name, falling back to the username."""
    if not username:
        return ""

    import ayon_api

    try:
        user = ayon_api.get_user(username) or {}
    except Exception:
        return username
    full_name = (user.get("attrib") or {}).get("fullName")
    return full_name or username


def append_comment(instance, text):
    """Append `text` as a new line to the instance's version comment,
    keeping whatever comment the artist typed first."""
    parts = [
        part.strip()
        for part in (instance.data.get("comment"), text)
        if part and part.strip()
    ]
    instance.data["comment"] = "\n".join(parts)
