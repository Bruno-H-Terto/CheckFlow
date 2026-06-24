from dataclasses import dataclass, field
from typing import Any, Annotated
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CallBase:
    executed_in: datetime = field(default_factory=datetime.now)

class Http(CallBase):
    """
    Class base for http calls
    """
    body: dict[str, Any] = {}
    latency: int | None = None
    headers: dict[str, Any] = {}
    timeout: Annotated[int | None, "Default 30 seconds"] = 30