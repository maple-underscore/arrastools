from typing import Optional, Sequence, Tuple, Union, BinaryIO

OutputPath = Union[str, BinaryIO, None]

def to_png(raw_data: bytes, size: Tuple[int, int], output: OutputPath = ...) -> None: ...
