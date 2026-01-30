#!/usr/bin/env python3
"""Test script for C++ macro integration."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cpp_wrapper import (
    is_cpp_available,
    circles_cpp,
    walls_cpp,
    circlecrash_cpp,
    minicirclecrash_cpp,
    arena_automation_cpp,
    benchmark_cpp,
)

def test_circles():
    """Test circle pattern generation."""
    print("Testing circles_cpp(22)...")
    result = circles_cpp(22)
    expected_len = 22 * 11  # 11 chars per pattern
    assert len(result) == expected_len, f"Expected {expected_len} chars, got {len(result)}"
    assert result == "cccccccccch" * 22, "Pattern mismatch"
    print(f"  ✓ Generated {len(result)} chars")

def test_walls():
    """Test wall pattern generation."""
    print("Testing walls_cpp()...")
    result = walls_cpp()
    assert len(result) == 210, f"Expected 210 chars, got {len(result)}"
    assert result == "x" * 210, "Pattern mismatch"
    print(f"  ✓ Generated {len(result)} chars")

def test_circlecrash():
    """Test circlecrash pattern."""
    print("Testing circlecrash_cpp()...")
    result = circlecrash_cpp()
    expected_len = 1600 * 26
    assert len(result) == expected_len, f"Expected {expected_len} chars, got {len(result)}"
    assert result == "ccccccccccccccccccccccccch" * 1600, "Pattern mismatch"
    print(f"  ✓ Generated {len(result)} chars")

def test_minicirclecrash():
    """Test minicirclecrash pattern."""
    print("Testing minicirclecrash_cpp()...")
    result = minicirclecrash_cpp()
    expected_len = 240 * 26
    assert len(result) == expected_len, f"Expected {expected_len} chars, got {len(result)}"
    assert result == "ccccccccccccccccccccccccch" * 240, "Pattern mismatch"
    print(f"  ✓ Generated {len(result)} chars")

def test_arena_automation():
    """Test arena automation command generation."""
    print("Testing arena_automation_cpp()...")
    
    # Type 1: random
    commands = arena_automation_cpp(1, 10, 2, 12345)
    assert len(commands) == 10, f"Expected 10 commands, got {len(commands)}"
    for cmd in commands:
        assert cmd.startswith("$arena size "), f"Invalid command: {cmd}"
    print(f"  ✓ Type 1: Generated {len(commands)} random commands")
    
    # Type 2: bouncing
    commands = arena_automation_cpp(2, 10, 4)
    assert len(commands) == 10, f"Expected 10 commands, got {len(commands)}"
    assert commands[0] == "$arena size 2 2", f"First command should be '2 2', got {commands[0]}"
    print(f"  ✓ Type 2: Generated {len(commands)} bouncing commands")
    
    # Type 3: inverse bouncing
    commands = arena_automation_cpp(3, 10, 4)
    assert len(commands) == 10, f"Expected 10 commands, got {len(commands)}"
    assert commands[0] == "$arena size 2 1024", f"First command should be '2 1024', got {commands[0]}"
    print(f"  ✓ Type 3: Generated {len(commands)} inverse bouncing commands")

def test_benchmark():
    """Test benchmark pattern."""
    print("Testing benchmark_cpp(500)...")
    result = benchmark_cpp(500)
    expected_len = 500 * 11
    assert len(result) == expected_len, f"Expected {expected_len} chars, got {len(result)}"
    print(f"  ✓ Generated {len(result)} chars")

def main():
    print("=" * 60)
    print("C++ Macro Integration Test")
    print("=" * 60)
    print()
    
    if not is_cpp_available():
        print("❌ C++ library not available!")
        print("Run ./compile_cpp.sh to compile the library")
        return 1
    
    print("✓ C++ library loaded successfully")
    print()
    
    try:
        test_circles()
        test_walls()
        test_circlecrash()
        test_minicirclecrash()
        test_arena_automation()
        test_benchmark()
        
        print()
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Unexpected error: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
