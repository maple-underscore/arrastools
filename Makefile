# Makefile for arrastools
# Supports macOS, Linux, and Windows (via MinGW)

UNAME_S := $(shell uname -s)

# Compiler settings
CXX = clang++
CXXFLAGS = -std=c++17 -O3 -Wall

# Source file (uses special Unicode characters in path)
SRC = ««««« CORE »»»»»/arrastools.cpp

# Platform-specific settings
ifeq ($(UNAME_S),Darwin)
    # macOS
    LDFLAGS = -framework CoreGraphics -framework ApplicationServices -framework Carbon
    TARGET = arrastools
else ifeq ($(UNAME_S),Linux)
    # Linux (requires X11)
    LDFLAGS = -lX11 -lXtst
    TARGET = arrastools
    # Switch to g++ on Linux if clang++ not available
    CXX = g++
else
    # Windows (MinGW)
    LDFLAGS = -luser32
    TARGET = arrastools.exe
    CXX = g++
endif

# Build target
all: $(TARGET)

$(TARGET):
	$(CXX) $(CXXFLAGS) -o $(TARGET) "$(SRC)" $(LDFLAGS)

# Clean
clean:
	rm -f $(TARGET) arrastools arrastools.exe

# Install (optional - copies to /usr/local/bin)
install: $(TARGET)
	install -m 755 $(TARGET) /usr/local/bin/

.PHONY: all clean install
