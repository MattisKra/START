"""QuantCo game API client.

PLACEHOLDER: the endpoint paths come from the kickoff talk, but the auth
header, the response shapes and the submission payload are guesses until we
have API_HANDBOOK.md and starter_script.py. Everything that may need changing
is in this file.
"""

import requests

from . import config
from .pricing import LinePrice


class GameAPI:
    def __init__(self, base: str = config.API_BASE, api_key: str | None = config.TEAM_API_KEY):
        if not api_key:
            raise RuntimeError("TEAM_API_KEY is not set (put it in .env)")
        self.base = base.rstrip("/")
        self.s = requests.Session()
        # TODO(handbook): confirm header name/format.
        self.s.headers["Authorization"] = f"Bearer {api_key}"

    def _get(self, path: str):
        r = self.s.get(f"{self.base}{path}", timeout=10)
        r.raise_for_status()
        return r.json()

    def list_games(self):
        return self._get("/api/games/list")

    def get_key(self, game_id: int | str) -> str:
        data = self._get(f"/api/games/{game_id}/key")
        # TODO(handbook): confirm the field name.
        if isinstance(data, dict):
            for k in ("key", "password", "decryption_key"):
                if k in data:
                    return str(data[k])
            raise KeyError(f"no key field in {data}")
        return str(data)

    @staticmethod
    def build_payload(prices: list[LinePrice]) -> dict:
        # TODO(handbook): confirm payload shape. One (a, b) per line, by index;
        # gross line totals.
        return {"items": [{"index": p.index, "a": p.a, "b": p.b} for p in prices]}

    def submit(self, game_id: int | str, prices: list[LinePrice]):
        r = self.s.post(
            f"{self.base}/api/games/{game_id}/submissions",
            json=self.build_payload(prices),
            timeout=10,
        )
        r.raise_for_status()
        return r.json() if r.content else None
