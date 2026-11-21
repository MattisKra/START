"""QuantCo game API client.

Endpoints, auth header and submission format follow the challenge deep dive
(claim-to-fame-challenge-deep-dive.md, slide 7). Still unconfirmed until we
have API_HANDBOOK.md: the response shapes of /list and /key, and whether
invoice indices start at 0 or 1 (the slide example uses 1, 2; see
config.INDEX_BASE).
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
        self.s.headers["X-API-Key"] = api_key

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
    def build_payload(prices: list[LinePrice]) -> list[dict]:
        # One (a, b) per line, gross line totals. LinePrice.index is 0-based.
        return [
            {
                "index": p.index + config.INDEX_BASE,
                "charge_price": round(p.a, 2),
                "acceptance_limit": round(p.b, 2),
            }
            for p in prices
        ]

    def submit(self, game_id: int | str, prices: list[LinePrice]):
        r = self.s.put(
            f"{self.base}/api/games/{game_id}/submissions",
            json=self.build_payload(prices),
            timeout=10,
        )
        r.raise_for_status()
        return r.json() if r.content else None
