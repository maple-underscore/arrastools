# Makefile for arena_automation and macro_tools
# Supports macOS, Linux, and Windows (via MinGW)

UNAME_S := $(shell uname -s)

# Compiler settings
CXX = clang++
CXXFLAGS = -std=c++17 -O3 -Wall

# Platform-specific settings
ifeq ($(UNAME_S),Darwin)
    # macOS
    LDFLAGS = -framework CoreGraphics -framework ApplicationServices
    TARGET1 = arena_automation
    TARGET2 = macro_tools
else ifeq ($(UNAME_S),Linux)
    # Linux (requires X11)
    LDFLAGS = -lX11 -lXtst
    TARGET1 = arena_automation
    TARGET2 = macro_tools
    # Switch to g++ on Linux if clang++ not available
    CXX = g++
else
    # Windows (MinGW)
    LDFLAGS = -luser32
    TARGET1 = arena_automation.exe
    TARGET2 = macro_tools.exe
    CXX = g++
endif

# Build all targets
all: $(TARGET1) $(TARGET2)

$(TARGET1): arena_automation.cpp
	$(CXX) $(CXXFLAGS) -o $(TARGET1) arena_automation.cpp $(LDFLAGS)

$(TARGET2): macro_tools.cpp
	$(CXX) $(CXXFLAGS) -o $(TARGET2) macro_tools.cpp $(LDFLAGS)

# Clean
clean:
	rm -f $(TARGET1) $(TARGET2) arena_automation.exe macro_tools.exe arena_automation macro_tools

# Install (optional - copies to /usr/local/bin)
install: $(TARGET1) $(TARGET2)
	install -m 755 $(TARGET1) /usr/local/bin/
	install -m 755 $(TARGET2) /usr/local/bin/

.PHONY: all clean install
