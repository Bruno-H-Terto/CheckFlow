from datetime import datetime
from dataclasses import dataclass, field
from typing import Annotated, Any


@dataclass(frozen=True, slots=True)
class CallBase:
    executed_in: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True, slots=True)
class Http(CallBase):
    """
    Class base for http calls
    """

    body: dict[str, Any] = field(default_factory=dict[str, Any])
    latency: int | None = None
    headers: dict[str, Any] = field(default_factory=dict[str, Any])
    timeout: Annotated[int | None, "Default 30 seconds"] = 30
