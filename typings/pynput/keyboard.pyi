from typing import Any, Callable
from types import TracebackType

class Key:
    enter: Any
    space: Any
    esc: Any
    tab: Any
    backspace: Any
    delete: Any
    shift: Any
    shift_l: Any
    shift_r: Any
    ctrl: Any
    ctrl_l: Any
    ctrl_r: Any
    alt: Any
    alt_l: Any
    alt_r: Any
    cmd: Any
    cmd_l: Any
    cmd_r: Any
    up: Any
    down: Any
    left: Any
    right: Any
    page_up: Any
    page_down: Any

class Controller:
    def press(self, key: Any) -> None: ...
    def release(self, key: Any) -> None: ...
    def tap(self, key: Any) -> None: ...
    def type(self, text: str) -> None: ...

class Listener:
    def __init__(
        self,
        on_press: Callable[[Any], Any] | None = ...,
        on_release: Callable[[Any], Any] | None = ...,
        suppress: bool | None = ...,
    ) -> None: ...
    daemon: bool
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def join(self) -> None: ...
    def __enter__(self) -> "Listener": ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
