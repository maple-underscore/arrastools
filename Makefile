# Makefile for arena_automation
# Supports macOS, Linux, and Windows (via MinGW)

UNAME_S := $(shell uname -s)

# Compiler settings
CXX = clang++
CXXFLAGS = -std=c++17 -O3 -Wall

# Platform-specific settings
ifeq ($(UNAME_S),Darwin)
    # macOS
    LDFLAGS = -framework CoreGraphics -framework ApplicationServices
    TARGET = arena_automation
else ifeq ($(UNAME_S),Linux)
    # Linux (requires X11)
    LDFLAGS = -lX11 -lXtst
    TARGET = arena_automation
    # Switch to g++ on Linux if clang++ not available
    CXX = g++
else
    # Windows (MinGW)
    LDFLAGS = -luser32
    TARGET = arena_automation.exe
    CXX = g++
endif

# Build target
all: $(TARGET)

$(TARGET): arena_automation.cpp
	$(CXX) $(CXXFLAGS) -o $(TARGET) arena_automation.cpp $(LDFLAGS)

# Clean
clean:
	rm -f $(TARGET) arena_automation.exe arena_automation

# Install (optional - copies to /usr/local/bin)
install: $(TARGET)
	install -m 755 $(TARGET) /usr/local/bin/

.PHONY: all clean install
