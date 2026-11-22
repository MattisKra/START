"""OpenAI client with a backup key: if a call with the first key fails, it is repeated once with BACKUP_OPENAI_API_KEY.

Falls back on authentication, permission, quota / rate-limit, connection and server errors. A bad request or a timeout
is not repeated (the same request would fail again, or the round has no time for it). After an authentication,
permission or quota error the backup key is used first for the rest of the process.
"""

import os

import openai
from openai import OpenAI

from . import config

BACKUP_KEY = os.getenv("BACKUP_OPENAI_API_KEY") or os.getenv("BACKUP_OPENAI_KEY")
_FALLBACK = (openai.AuthenticationError, openai.PermissionDeniedError, openai.RateLimitError,
             openai.InternalServerError, openai.APIConnectionError)
_STICKY = (openai.AuthenticationError, openai.PermissionDeniedError, openai.RateLimitError)
_prefer_backup = False


def call(fn, timeout: float, max_retries: int = 1):
    """fn(client) -> result. Tries the first key, then the backup key."""
    global _prefer_backup
    keys = [k for k in (config.OPENAI_KEY, BACKUP_KEY) if k]
    if not keys:
        raise RuntimeError("OPENAI_KEY is not set (put it in .env)")
    if _prefer_backup and len(keys) == 2:
        keys.reverse()
    for i, key in enumerate(keys):
        try:
            return fn(OpenAI(api_key=key, timeout=timeout, max_retries=max_retries))
        except openai.APITimeoutError:
            raise
        except _FALLBACK as e:
            if i == len(keys) - 1:
                raise
            if isinstance(e, _STICKY) and key == config.OPENAI_KEY:
                _prefer_backup = True
            print(f"openai: {type(e).__name__} with key {i + 1}, repeating with the other key")
