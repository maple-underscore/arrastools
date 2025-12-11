from typing import Any, Dict, List, Sequence

from . import tools

__all__ = ["mss", "Screenshot", "tools"]

class Screenshot:
    rgb: bytes
    size: tuple[int, int]
    width: int
    height: int
    top: int
    left: int

    def pixel(self, x: int, y: int) -> Sequence[int]: ...

class mss:
    monitors: List[Dict[str, int]]

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def grab(self, monitor: Any) -> Screenshot: ...
    def close(self) -> None: ...

    def __enter__(self) -> "mss": ...
    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...
