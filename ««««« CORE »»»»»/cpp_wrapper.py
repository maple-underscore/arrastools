"""C++ macro integration for arrastools.

Provides optional C++ implementations of performance-critical functions.
Falls back to Python if C++ library is not available.
"""

import ctypes
import platform
import os
from pathlib import Path
from typing import Optional

# Determine library extension based on platform
PLATFORM = platform.system().lower()
if PLATFORM == 'darwin':
    LIB_EXT = '.dylib'
elif PLATFORM == 'windows':
    LIB_EXT = '.dll'
else:  # Linux, Android, etc.
    LIB_EXT = '.so'

# Try to load the C++ library
_cpp_lib: Optional[ctypes.CDLL] = None
_cpp_available = False

def _load_cpp_library():
    """Attempt to load the compiled C++ library."""
    global _cpp_lib, _cpp_available
    
    lib_path = Path(__file__).parent / f'arras_cpp_macros{LIB_EXT}'
    
    if not lib_path.exists():
        print(f"C++ library not found at {lib_path}")
        print("Compile with: clang++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.dylib")
        return False
    
    try:
        _cpp_lib = ctypes.CDLL(str(lib_path))
        
        # Define function signatures
        _cpp_lib.circles_cpp.argtypes = [ctypes.c_char_p, ctypes.c_int32]
        _cpp_lib.circles_cpp.restype = ctypes.c_int32
        
        _cpp_lib.walls_cpp.argtypes = [ctypes.c_char_p]
        _cpp_lib.walls_cpp.restype = ctypes.c_int32
        
        _cpp_lib.circlecrash_cpp.argtypes = [ctypes.c_char_p]
        _cpp_lib.circlecrash_cpp.restype = ctypes.c_int32
        
        _cpp_lib.minicirclecrash_cpp.argtypes = [ctypes.c_char_p]
        _cpp_lib.minicirclecrash_cpp.restype = ctypes.c_int32
        
        _cpp_lib.arena_automation_type1_cpp.argtypes = [ctypes.c_char_p, ctypes.c_int32, ctypes.c_uint32]
        _cpp_lib.arena_automation_type1_cpp.restype = ctypes.c_int32
        
        _cpp_lib.arena_automation_type2_cpp.argtypes = [ctypes.c_char_p, ctypes.c_int32, ctypes.c_int32]
        _cpp_lib.arena_automation_type2_cpp.restype = ctypes.c_int32
        
        _cpp_lib.arena_automation_type3_cpp.argtypes = [ctypes.c_char_p, ctypes.c_int32, ctypes.c_int32]
        _cpp_lib.arena_automation_type3_cpp.restype = ctypes.c_int32
        
        _cpp_lib.benchmark_cpp.argtypes = [ctypes.c_char_p, ctypes.c_int32]
        _cpp_lib.benchmark_cpp.restype = ctypes.c_int32
        
        _cpp_available = True
        print(f"✓ C++ macros loaded from {lib_path}")
        return True
        
    except Exception as e:
        print(f"Failed to load C++ library: {e}")
        return False

# Attempt to load on import
_load_cpp_library()

def is_cpp_available() -> bool:
    """Check if C++ implementations are available."""
    return _cpp_available

def circles_cpp(amt: int = 22) -> str:
    """Generate circle pattern using C++ (fast path)."""
    if not _cpp_available or _cpp_lib is None:
        raise RuntimeError("C++ library not available")
    
    # Allocate buffer: 11 chars per pattern * amt
    buffer_size = amt * 11
    buffer = ctypes.create_string_buffer(buffer_size)
    
    actual_len = _cpp_lib.circles_cpp(buffer, amt)
    return buffer.raw[:actual_len].decode('ascii')

def walls_cpp() -> str:
    """Generate wall pattern using C++ (fast path)."""
    if not _cpp_available or _cpp_lib is None:
        raise RuntimeError("C++ library not available")
    
    buffer = ctypes.create_string_buffer(210)
    actual_len = _cpp_lib.walls_cpp(buffer)
    return buffer.raw[:actual_len].decode('ascii')

def circlecrash_cpp() -> str:
    """Generate circlecrash pattern using C++ (fast path)."""
    if not _cpp_available or _cpp_lib is None:
        raise RuntimeError("C++ library not available")
    
    # 26 chars * 1600 = 41,600
    buffer = ctypes.create_string_buffer(41600)
    actual_len = _cpp_lib.circlecrash_cpp(buffer)
    return buffer.raw[:actual_len].decode('ascii')

def minicirclecrash_cpp() -> str:
    """Generate minicirclecrash pattern using C++ (fast path)."""
    if not _cpp_available or _cpp_lib is None:
        raise RuntimeError("C++ library not available")
    
    # 26 chars * 240 = 6,240
    buffer = ctypes.create_string_buffer(6240)
    actual_len = _cpp_lib.minicirclecrash_cpp(buffer)
    return buffer.raw[:actual_len].decode('ascii')

def arena_automation_cpp(atype: int, count: int, step: int = 2, seed: int = 0) -> list[str]:
    """Generate arena automation commands using C++ (fast path).
    
    Args:
        atype: 1=random, 2=bouncing, 3=inverse bouncing
        count: Number of commands to generate
        step: Step size for bouncing patterns (must be even)
        seed: Random seed for type 1
        
    Returns:
        List of command strings
    """
    if not _cpp_available or _cpp_lib is None:
        raise RuntimeError("C++ library not available")
    
    # Allocate large buffer for commands (~30 chars per command max)
    buffer_size = count * 50
    buffer = ctypes.create_string_buffer(buffer_size)
    
    if atype == 1:
        actual_len = _cpp_lib.arena_automation_type1_cpp(buffer, count, seed)
    elif atype == 2:
        actual_len = _cpp_lib.arena_automation_type2_cpp(buffer, count, step)
    elif atype == 3:
        actual_len = _cpp_lib.arena_automation_type3_cpp(buffer, count, step)
    else:
        raise ValueError(f"Invalid atype: {atype}")
    
    # Split into lines
    result = buffer.raw[:actual_len].decode('ascii')
    return [line for line in result.split('\n') if line]

def benchmark_cpp(amt: int) -> str:
    """Generate benchmark pattern using C++ (fast path)."""
    if not _cpp_available or _cpp_lib is None:
        raise RuntimeError("C++ library not available")
    
    buffer_size = amt * 11
    buffer = ctypes.create_string_buffer(buffer_size)
    
    actual_len = _cpp_lib.benchmark_cpp(buffer, amt)
    return buffer.raw[:actual_len].decode('ascii')
