#!/bin/bash
# Compile C++ macros for arrastools
# This script detects the platform and compiles with appropriate flags

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Detect platform
case "$(uname -s)" in
    Darwin*)
        echo "Compiling for macOS..."
        clang++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.dylib
        echo "✓ Compiled arras_cpp_macros.dylib"
        ;;
    Linux*)
        echo "Compiling for Linux..."
        g++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.so
        echo "✓ Compiled arras_cpp_macros.so"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        echo "Compiling for Windows..."
        if command -v cl &> /dev/null; then
            cl /O2 /LD arras_cpp_macros.cpp /link /OUT:arras_cpp_macros.dll
        elif command -v g++ &> /dev/null; then
            g++ -std=c++17 -O3 -shared arras_cpp_macros.cpp -o arras_cpp_macros.dll
        else
            echo "Error: No C++ compiler found (cl.exe or g++)"
            exit 1
        fi
        echo "✓ Compiled arras_cpp_macros.dll"
        ;;
    *)
        echo "Unknown platform: $(uname -s)"
        echo "Please compile manually:"
        echo "  macOS:   clang++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.dylib"
        echo "  Linux:   g++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.so"
        echo "  Windows: cl /O2 /LD arras_cpp_macros.cpp /link /OUT:arras_cpp_macros.dll"
        exit 1
        ;;
esac

echo ""
echo "C++ macros compiled successfully!"
echo "The library will be automatically loaded by arrastools.py"
echo ""
echo "To disable C++ macros, set USE_CPP_MACROS = False in arrastools.py"
