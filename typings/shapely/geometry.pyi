from typing import Any, Iterable, Optional, Sequence, Tuple

class Point:
    def __init__(self, x: float, y: float) -> None: ...

class _PolygonExterior:
    coords: Sequence[Tuple[float, float]]

class Polygon:
    exterior: _PolygonExterior
    def __init__(self, shell: Optional[Iterable[Tuple[float, float]]] = ..., holes: Optional[Iterable[Iterable[Tuple[float, float]]]] = ...) -> None: ...
    @property
    def bounds(self) -> Tuple[float, float, float, float]: ...
    def contains(self, other: Point) -> bool: ...
