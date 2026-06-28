import json
from typing import cast

from redis import Redis

from domain.entities.step import JsonValue


class RedisJsonCache:
    def __init__(
        self,
        redis_url: str,
        default_ttl: int = 3_600,
        client: Redis | None = None,
    ) -> None:
        self._client = client or Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
            redis_url, decode_responses=True
        )
        self._default_ttl = default_ttl

    def set(self, key: str, value: JsonValue, ttl: int | None = None) -> None:
        self._client.setex(key, ttl or self._default_ttl, json.dumps(value))

    def get(self, key: str) -> JsonValue:
        value = self._client.get(key)
        return None if value is None else cast(JsonValue, json.loads(cast(str, value)))

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def close(self) -> None:
        self._client.close()
