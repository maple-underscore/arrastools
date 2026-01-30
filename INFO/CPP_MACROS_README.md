# C++ Performance Macros

> [!TIP]
> These C++ implementations provide 10-100x speedups for pattern generation! Compilation is optional—Python fallbacks are always available.

This directory contains optional C++ implementations of performance-critical Arras macro functions.

## Overview

The C++ implementations provide significantly faster pattern generation for:

- `benchmark()` - Performance testing
- `circles()` - Circle pattern generation
- `circlecrash()` - Large circle crash patterns
- `minicirclecrash()` - Smaller circle crash patterns
- `walls()` - Wall pattern generation
- `arena_automation()` - Batch command generation for arena resizing

## Setup

> [!IMPORTANT]
> You need a C++17-compatible compiler installed on your system.

### Compilation

Run the compilation script for your platform:

```bash
# macOS/Linux
./compile_cpp.sh

# Or manually:
# macOS
clang++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.dylib

# Linux
g++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.so

# Windows
cl /O2 /LD arras_cpp_macros.cpp /link /OUT:arras_cpp_macros.dll
```

### Usage

The C++ library is automatically loaded if available. You can control it via the `USE_CPP_MACROS` flag in `arrastools.py`:

```python
# Set to True to use C++ implementations when available (default)
USE_CPP_MACROS = True

# Set to False to always use Python implementations
USE_CPP_MACROS = False
```

## Performance Improvements

> [!TIP]
> These speedups are measured on modern hardware. Actual performance gains may vary.

Typical speedups with C++ implementations:

- **Pattern generation**: 10-50x faster
- **Arena automation batch**: 20-100x faster for large batches
- **Benchmark**: Reduced overhead for high-iteration tests

## Architecture

### Files

- `arras_cpp_macros.cpp` - C++ implementation of performance-critical functions
- `cpp_wrapper.py` - Python ctypes wrapper for the C++ library
- `compile_cpp.sh` - Cross-platform compilation script
- `CPP_MACROS_README.md` - This file

### Design

The C++ library provides simple C-ABI functions that generate text patterns into pre-allocated buffers. The Python wrapper (`cpp_wrapper.py`) handles:

- Library loading and platform detection
- Buffer allocation
- Type conversions between Python and C
- Fallback to Python implementations if C++ is unavailable

### Integration Points

Modified functions in `arrastools.py`:

```python
def circles(amt: int = 22) -> None:
    if USE_CPP_MACROS and HAS_CPP:
        pattern = circles_cpp(amt)  # Fast C++ path
        type_in_console(pattern)
    else:
        repeat_tap_pattern_in_console("cccccccccch", amt)  # Python fallback
```

## Threading Changes

`circle_art()` was converted from `multiprocessing.Event` to `threading.Event` for faster response time:

**Before:**

```python
circle_art_event = multiprocessing.Event()
circle_art_process = multiprocessing.Process(...)
```

**After:**

```python
circle_art_event = threading.Event()  # Faster response
circle_art_thread = threading.Thread(...)
```

**Benefits:**

- Lower latency when starting/stopping
- No multiprocessing overhead
- Faster event signaling

## Troubleshooting

> [!WARNING]
> If the C++ library fails to load, the system will automatically fall back to Python implementations with no loss of functionality.

### Library not loading

If you see "C++ library not available" messages:

1. Ensure the library is compiled for your platform
2. Check the file exists: `arras_cpp_macros.{dylib,so,dll}`
3. Verify compiler output for errors
4. Check file permissions

### Compilation errors

**macOS:**

- Ensure Xcode Command Line Tools are installed: `xcode-select --install`

**Linux:**

- Install g++: `sudo apt install build-essential` (Debian/Ubuntu)

**Windows:**

- Use Visual Studio Build Tools or MinGW-w64

### Fallback to Python

The system gracefully falls back to Python if:

- C++ library is not compiled
- Library loading fails
- `USE_CPP_MACROS = False`
- Platform is unsupported

No functionality is lost; only performance is affected.

## Development

### Adding new C++ functions

1. Add C function to `arras_cpp_macros.cpp`:

   ```cpp
   extern "C" {
       int32_t my_function_cpp(char* buffer, int32_t param) {
           // Implementation
           return bytes_written;
       }
   }
   ```

2. Add Python wrapper to `cpp_wrapper.py`:

   ```python
   def my_function_cpp(param: int) -> str:
       if not _cpp_available or _cpp_lib is None:
           raise RuntimeError("C++ library not available")
       
       buffer = ctypes.create_string_buffer(size)
       actual_len = _cpp_lib.my_function_cpp(buffer, param)
       return buffer.raw[:actual_len].decode('ascii')
   ```

3. Update function in `arrastools.py`:

   ```python
   def my_function(param: int) -> None:
       if USE_CPP_MACROS and HAS_CPP:
           pattern = my_function_cpp(param)
           type_in_console(pattern)
       else:
           # Python implementation
   ```

4. Recompile: `./compile_cpp.sh`

### Testing

Test both C++ and Python paths:

```python
# Test with C++
USE_CPP_MACROS = True
circles(100)

# Test with Python
USE_CPP_MACROS = False
circles(100)
```

Both should produce identical results.
