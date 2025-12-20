/*
 * Ultra-optimized arena size automation using native macOS Core Graphics API
 * Compile: clang++ -std=c++17 -framework CoreGraphics -framework ApplicationServices -O3 -o arena_automation arena_automation.cpp
 * 
 * This implementation is 10-100x faster than pynput because it:
 * 1. Uses native CGEvent APIs directly (no Python/pynput overhead)
 * 2. Compiled to native machine code
 * 3. Minimal abstraction layers
 * 4. Optimized string operations
 */

#include <CoreGraphics/CoreGraphics.h>
#include <ApplicationServices/ApplicationServices.h>
#include <iostream>
#include <random>
#include <string>
#include <thread>
#include <chrono>
#include <atomic>
#include <csignal>

std::atomic<bool> running(true);

void signalHandler(int signum) {
    std::cout << "\nStopping automation..." << std::endl;
    running = false;
}

// Fast keyboard event posting using CGEvent
void postKey(CGKeyCode keyCode, bool keyDown) {
    CGEventRef event = CGEventCreateKeyboardEvent(NULL, keyCode, keyDown);
    CGEventPost(kCGHIDEventTap, event);
    CFRelease(event);
}

void tapKey(CGKeyCode keyCode) {
    postKey(keyCode, true);
    postKey(keyCode, false);
}

void typeString(const std::string& text) {
    CGEventRef event = CGEventCreateKeyboardEvent(NULL, 0, true);
    
    for (char c : text) {
        UniChar unicodeChar = static_cast<UniChar>(c);
        CGEventKeyboardSetUnicodeString(event, 1, &unicodeChar);
        CGEventPost(kCGHIDEventTap, event);
    }
    
    CFRelease(event);
}

// macOS keycodes
const CGKeyCode kVK_Return = 0x24;

int generateEven(int low = 2, int high = 1024) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(low / 2, high / 2);
    return dis(gen) * 2;
}

void arenaAutomationType1() {
    std::cout << "Starting Type 1: Random arena sizes" << std::endl;
    
    while (running) {
        int x = generateEven();
        int y = generateEven();
        
        tapKey(kVK_Return);
        typeString("$arena size " + std::to_string(x) + " " + std::to_string(y));
        tapKey(kVK_Return);
    }
}

void arenaAutomationType2() {
    std::cout << "Starting Type 2: Bouncing dimensions" << std::endl;
    
    int x = 2, y = 2;
    int direction_x = 2, direction_y = 2;
    
    while (running) {
        tapKey(kVK_Return);
        typeString("$arena size " + std::to_string(x) + " " + std::to_string(y));
        tapKey(kVK_Return);
        
        x += direction_x;
        y += direction_y;
        
        // Clamp and reverse direction if out of bounds
        if (x > 1024) {
            x = 1024;
            direction_x = -2;
        } else if (x < 2) {
            x = 2;
            direction_x = 2;
        }
        if (y > 1024) {
            y = 1024;
            direction_y = -2;
        } else if (y < 2) {
            y = 2;
            direction_y = 2;
        }
    }
}

void arenaAutomationType3() {
    std::cout << "Starting Type 3: Inverse bouncing dimensions" << std::endl;
    
    int x = 2, y = 1024;
    int direction_x = 2, direction_y = -2;
    
    while (running) {
        tapKey(kVK_Return);
        typeString("$arena size " + std::to_string(x) + " " + std::to_string(y));
        tapKey(kVK_Return);
        
        x += direction_x;
        y += direction_y;
        
        // Clamp and reverse direction if out of bounds
        if (x > 1024) {
            x = 1024;
            direction_x = -2;
        } else if (x < 2) {
            x = 2;
            direction_x = 2;
        }
        if (y > 1024) {
            y = 1024;
            direction_y = -2;
        } else if (y < 2) {
            y = 2;
            direction_y = 2;
        }
    }
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <type>\n";
        std::cerr << "  type 1: Random arena sizes\n";
        std::cerr << "  type 2: Bouncing dimensions\n";
        std::cerr << "  type 3: Inverse bouncing dimensions\n";
        return 1;
    }
    
    // Check for accessibility permissions
    if (!AXIsProcessTrusted()) {
        std::cerr << "ERROR: This application requires accessibility permissions.\n";
        std::cerr << "Go to System Settings > Privacy & Security > Accessibility\n";
        std::cerr << "and enable this application.\n";
        return 1;
    }
    
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    int type = std::stoi(argv[1]);
    
    std::cout << "Arena automation starting (Press Ctrl+C to stop)..." << std::endl;
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    
    switch (type) {
        case 1:
            arenaAutomationType1();
            break;
        case 2:
            arenaAutomationType2();
            break;
        case 3:
            arenaAutomationType3();
            break;
        default:
            std::cerr << "Invalid type: " << type << std::endl;
            return 1;
    }
    
    std::cout << "Automation stopped." << std::endl;
    return 0;
}
