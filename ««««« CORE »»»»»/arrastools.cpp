/**
 * arrastools.cpp - Combined C++ implementation of arrastools.py
 * 
 * This file provides optimized C++ implementations of all Python macros.
 * Combined from arena_automation.cpp and macro_tools.cpp.
 * 
 * Compile: make (uses Makefile) or:
 *   macOS:   clang++ -std=c++17 -framework CoreGraphics -framework ApplicationServices -O3 -o arrastools arrastools.cpp
 *   Linux:   g++ -std=c++17 -O3 -lX11 -lXtst -o arrastools arrastools.cpp
 *   Windows: g++ -std=c++17 -O3 -luser32 -o arrastools.exe arrastools.cpp
 * 
 * Usage: ./arrastools <command> [args...]
 */

#include <iostream>
#include <string>
#include <random>
#include <chrono>
#include <thread>
#include <atomic>
#include <csignal>
#include <cmath>

#ifdef __APPLE__
    #include <CoreGraphics/CoreGraphics.h>
    #include <ApplicationServices/ApplicationServices.h>
    #include <Carbon/Carbon.h>
    #include <unistd.h>
#elif __linux__
    #include <X11/Xlib.h>
    #include <X11/keysym.h>
    #include <X11/extensions/XTest.h>
    #include <unistd.h>
#elif _WIN32
    #include <windows.h>
#endif

// Global state
std::atomic<bool> running(true);

void signalHandler(int signum) {
    std::cout << "\nInterrupt signal (" << signum << ") received. Stopping..." << std::endl;
    running = false;
}

// ==================== Platform-specific implementations ====================

#ifdef __APPLE__
// macOS implementation using Core Graphics

// Check for accessibility permissions
bool checkAccessibility() {
    return AXIsProcessTrusted();
}

// Press a key (key down event only)
void pressKey(CGKeyCode keyCode) {
    CGEventRef keyDown = CGEventCreateKeyboardEvent(NULL, keyCode, true);
    CGEventPost(kCGHIDEventTap, keyDown);
    CFRelease(keyDown);
}

// Release a key (key up event only)
void releaseKey(CGKeyCode keyCode) {
    CGEventRef keyUp = CGEventCreateKeyboardEvent(NULL, keyCode, false);
    CGEventPost(kCGHIDEventTap, keyUp);
    CFRelease(keyUp);
}

// Tap a key (press and release)
void tapKey(CGKeyCode keyCode) {
    CGEventRef keyDown = CGEventCreateKeyboardEvent(NULL, keyCode, true);
    CGEventRef keyUp = CGEventCreateKeyboardEvent(NULL, keyCode, false);
    CGEventPost(kCGHIDEventTap, keyDown);
    usleep(1000);  // 1ms delay
    CGEventPost(kCGHIDEventTap, keyUp);
    CFRelease(keyDown);
    CFRelease(keyUp);
}

void holdKey(CGKeyCode keyCode) {
    CGEventRef keyDown = CGEventCreateKeyboardEvent(NULL, keyCode, true);
    CGEventRef keyUp = CGEventCreateKeyboardEvent(NULL, keyCode, false);
    CGEventPost(kCGHIDEventTap, keyDown);
    usleep(100000);  // Hold for 100ms
    CGEventPost(kCGHIDEventTap, keyUp);
    CFRelease(keyDown);
    CFRelease(keyUp);
}

// Type a single character using Unicode input
void typeCharacter(char c) {
    UniChar unicodeChar = (UniChar)c;
    CGEventRef event = CGEventCreateKeyboardEvent(NULL, 0, true);
    CGEventKeyboardSetUnicodeString(event, 1, &unicodeChar);
    CGEventPost(kCGHIDEventTap, event);
    CFRelease(event);
    usleep(1000);  // 1ms between characters
}

// Type a string by typing each character (faster version for arena automation)
void typeStringFast(const std::string& text) {
    CGEventRef event = CGEventCreateKeyboardEvent(NULL, 0, true);
    for (char c : text) {
        UniChar unicodeChar = static_cast<UniChar>(c);
        CGEventKeyboardSetUnicodeString(event, 1, &unicodeChar);
        CGEventPost(kCGHIDEventTap, event);
    }
    CFRelease(event);
}

// Type a string (normal speed)
void typeString(const std::string& str) {
    for (char c : str) {
        typeCharacter(c);
    }
}

// Tap a character key
void tapCharacter(char c) {
    typeCharacter(c);
}

// Note: kVK_* keycodes are provided by Carbon/HIToolbox/Events.h
// (kVK_Return, kVK_ANSI_Grave, kVK_ANSI_D, etc.)

#elif __linux__
// Linux implementation using X11

Display* display = nullptr;

bool checkAccessibility() {
    display = XOpenDisplay(NULL);
    return display != nullptr;
}

void pressKey(unsigned int keycode) {
    if (!display) return;
    XTestFakeKeyEvent(display, keycode, True, 0);
    XFlush(display);
}

void releaseKey(unsigned int keycode) {
    if (!display) return;
    XTestFakeKeyEvent(display, keycode, False, 0);
    XFlush(display);
}

void tapKey(unsigned int keycode) {
    if (!display) return;
    XTestFakeKeyEvent(display, keycode, True, 0);
    XFlush(display);
    usleep(5000);
    XTestFakeKeyEvent(display, keycode, False, 0);
    XFlush(display);
}

void typeCharacter(char c) {
    if (!display) return;
    KeySym keysym = XStringToKeysym(&c);
    if (keysym == NoSymbol) return;
    KeyCode keycode = XKeysymToKeycode(display, keysym);
    XTestFakeKeyEvent(display, keycode, True, 0);
    XFlush(display);
    usleep(1000);
    XTestFakeKeyEvent(display, keycode, False, 0);
    XFlush(display);
}

void typeStringFast(const std::string& str) {
    for (char c : str) {
        typeCharacter(c);
    }
}

void typeString(const std::string& str) {
    for (char c : str) {
        typeCharacter(c);
    }
}

void tapCharacter(char c) {
    typeCharacter(c);
}

unsigned int kVK_Return = 0;
unsigned int kVK_ANSI_Grave = 0;
unsigned int kVK_ANSI_D = 0;
unsigned int kVK_Enter = 0;

void initKeycodes() {
    if (!display) return;
    kVK_Return = XKeysymToKeycode(display, XK_Return);
    kVK_ANSI_Grave = XKeysymToKeycode(display, XK_grave);
    kVK_ANSI_D = XKeysymToKeycode(display, XK_d);
    kVK_Enter = XKeysymToKeycode(display, XK_Return);
}

#elif _WIN32
// Windows implementation

bool checkAccessibility() {
    return true;  // Windows doesn't require special permissions
}

void pressKey(int vk) {
    INPUT input = {0};
    input.type = INPUT_KEYBOARD;
    input.ki.wVk = vk;
    SendInput(1, &input, sizeof(INPUT));
}

void releaseKey(int vk) {
    INPUT input = {0};
    input.type = INPUT_KEYBOARD;
    input.ki.wVk = vk;
    input.ki.dwFlags = KEYEVENTF_KEYUP;
    SendInput(1, &input, sizeof(INPUT));
}

void tapKey(int vk) {
    pressKey(vk);
    Sleep(5);
    releaseKey(vk);
}

void typeCharacter(char c) {
    INPUT inputs[2] = {0};
    inputs[0].type = INPUT_KEYBOARD;
    inputs[0].ki.wScan = c;
    inputs[0].ki.dwFlags = KEYEVENTF_UNICODE;
    inputs[1].type = INPUT_KEYBOARD;
    inputs[1].ki.wScan = c;
    inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;
    SendInput(2, inputs, sizeof(INPUT));
    Sleep(1);
}

void typeStringFast(const std::string& str) {
    for (char c : str) {
        typeCharacter(c);
    }
}

void typeString(const std::string& str) {
    for (char c : str) {
        typeCharacter(c);
    }
}

void tapCharacter(char c) {
    typeCharacter(c);
}

const int kVK_Return = VK_RETURN;
const int kVK_ANSI_Grave = VK_OEM_3;
const int kVK_ANSI_D = 'D';
const int kVK_Enter = VK_RETURN;

#endif

// ==================== Random number generation ====================

int generateEven(int low = 2, int high = 1024) {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(low / 2, high / 2);
    return dis(gen) * 2;
}

// ==================== Arena Automation ====================

void arenaAutomationType1(int maxCommands = 0, int rateLimit = 0) {
    std::cout << "Starting Type 1: Random arena sizes" << std::endl;
    if (maxCommands > 0) std::cout << "Max commands: " << maxCommands << std::endl;
    if (rateLimit > 0) std::cout << "Rate limit: " << rateLimit << " cmd/s" << std::endl;
    
    int cmdDelay = (rateLimit > 0) ? (1000000 / rateLimit) : 0;  // microseconds
    int count = 0;
    
    while (running && (maxCommands == 0 || count < maxCommands)) {
        int x = generateEven();
        int y = generateEven();
        
        tapKey(kVK_Return);
        typeStringFast("$arena size " + std::to_string(x) + " " + std::to_string(y));
        tapKey(kVK_Return);
        
        count++;
        if (cmdDelay > 0) {
            #ifdef _WIN32
            Sleep(cmdDelay / 1000);
            #else
            usleep(cmdDelay);
            #endif
        }
    }
    
    if (maxCommands > 0 && count >= maxCommands) {
        std::cout << "Reached " << maxCommands << " commands, stopping" << std::endl;
    }
}

void arenaAutomationType2(int step = 2, int maxCommands = 0, int rateLimit = 0) {
    std::cout << "Starting Type 2: Bouncing dimensions (step=" << step << ")" << std::endl;
    if (maxCommands > 0) std::cout << "Max commands: " << maxCommands << std::endl;
    if (rateLimit > 0) std::cout << "Rate limit: " << rateLimit << " cmd/s" << std::endl;
    
    int cmdDelay = (rateLimit > 0) ? (1000000 / rateLimit) : 0;
    int count = 0;
    int x = 2, y = 2;
    int direction_x = step, direction_y = step;
    
    while (running && (maxCommands == 0 || count < maxCommands)) {
        tapKey(kVK_Return);
        typeStringFast("$arena size " + std::to_string(x) + " " + std::to_string(y));
        tapKey(kVK_Return);
        
        x += direction_x;
        y += direction_y;
        
        if (x > 1024) { x = 1024; direction_x = -step; }
        else if (x < 2) { x = 2; direction_x = step; }
        if (y > 1024) { y = 1024; direction_y = -step; }
        else if (y < 2) { y = 2; direction_y = step; }
        
        count++;
        if (cmdDelay > 0) {
            #ifdef _WIN32
            Sleep(cmdDelay / 1000);
            #else
            usleep(cmdDelay);
            #endif
        }
    }
    
    if (maxCommands > 0 && count >= maxCommands) {
        std::cout << "Reached " << maxCommands << " commands, stopping" << std::endl;
    }
}

void arenaAutomationType3(int step = 2, int maxCommands = 0, int rateLimit = 0) {
    std::cout << "Starting Type 3: Inverse bouncing dimensions (step=" << step << ")" << std::endl;
    if (maxCommands > 0) std::cout << "Max commands: " << maxCommands << std::endl;
    if (rateLimit > 0) std::cout << "Rate limit: " << rateLimit << " cmd/s" << std::endl;
    
    int cmdDelay = (rateLimit > 0) ? (1000000 / rateLimit) : 0;
    int count = 0;
    int x = 2, y = 1024;
    int direction_x = step, direction_y = -step;
    
    while (running && (maxCommands == 0 || count < maxCommands)) {
        tapKey(kVK_Return);
        typeStringFast("$arena size " + std::to_string(x) + " " + std::to_string(y));
        tapKey(kVK_Return);
        
        x += direction_x;
        y += direction_y;
        
        if (x > 1024) { x = 1024; direction_x = -step; }
        else if (x < 2) { x = 2; direction_x = step; }
        if (y > 1024) { y = 1024; direction_y = -step; }
        else if (y < 2) { y = 2; direction_y = step; }
        
        count++;
        if (cmdDelay > 0) {
            #ifdef _WIN32
            Sleep(cmdDelay / 1000);
            #else
            usleep(cmdDelay);
            #endif
        }
    }
    
    if (maxCommands > 0 && count >= maxCommands) {
        std::cout << "Reached " << maxCommands << " commands, stopping" << std::endl;
    }
}

// ==================== Macro Functions ====================

/**
 * wallcrash - Python equivalent:
 *   controller.press("`")
 *   controller.type("x"*1800)
 *   controller.release("`")
 */
void wallcrash() {
    std::cout << "wallcrash: press(`), type(x*1800), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 1800 && running; i++) {
        typeCharacter('x');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * nuke - Python equivalent:
 *   controller.press("`")
 *   controller.type("wk"*100)
 *   controller.release("`")
 */
void nuke() {
    std::cout << "nuke: press(`), type(wk*100), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 100 && running; i++) {
        typeCharacter('w');
        typeCharacter('k');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape - Python equivalent:
 *   controller.press("`")
 *   controller.type("f"*5000)
 *   controller.release("`")
 */
void shape() {
    std::cout << "shape: press(`), type(f*5000), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 5000 && running; i++) {
        typeCharacter('f');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * score - Python equivalent:
 *   controller.press("`")
 *   controller.type("n"*20000)
 *   controller.release("`")
 */
void score() {
    std::cout << "score: press(`), type(n*20000), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 20000 && running; i++) {
        typeCharacter('n');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * score50m - Python equivalent:
 *   controller.press("`")
 *   controller.type("f"*20)
 *   controller.release("`")
 */
void score50m() {
    std::cout << "score50m: press(`), type(f*20), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 20 && running; i++) {
        typeCharacter('f');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * circles - Python equivalent:
 *   controller.press("`")
 *   for _ in range(amt):
 *       controller.tap("c")
 *       controller.tap("h")
 *   controller.release("`")
 */
void circles(int amt = 210) {
    std::cout << "circles: press(`), tap(ch)*" << amt << ", release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < amt && running; i++) {
        tapCharacter('c');
        tapCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * walls - Python equivalent:
 *   controller.press("`")
 *   controller.type("x"*210)
 *   controller.release("`")
 */
void walls() {
    std::cout << "walls: press(`), type(x*210), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 210 && running; i++) {
        typeCharacter('x');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * minicirclecrash - Python equivalent:
 *   controller.press("`")
 *   for _ in range(50):
 *       for _ in range(100):
 *           controller.tap("c")
 *           controller.tap("h")
 *   controller.release("`")
 * 
 * Total: 50 * 100 = 5000 "ch" pairs
 */
void minicirclecrash() {
    std::cout << "minicirclecrash: press(`), tap(ch)*5000 (50*100), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 50 && running; i++) {
        for (int j = 0; j < 100 && running; j++) {
            tapCharacter('c');
            tapCharacter('h');
        }
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * circlecrash - Python equivalent:
 *   controller.press("`")
 *   for _ in range(180):
 *       for _ in range(180):
 *           controller.tap("c")
 *           controller.tap("h")
 *   controller.release("`")
 * 
 * Total: 180 * 180 = 32400 "ch" pairs
 */
void circlecrash() {
    std::cout << "circlecrash: press(`), tap(ch)*32400 (180*180), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 180 && running; i++) {
        for (int j = 0; j < 180 && running; j++) {
            tapCharacter('c');
            tapCharacter('h');
        }
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * mcrash - Python equivalent:
 *   controller.press("`")
 *   while run_event.is_set():
 *       controller.tap("c")
 *       controller.tap("h")
 *   controller.release("`")
 * 
 * Continuous typing until Ctrl+C is pressed
 */
void mcrash() {
    std::cout << "mcrash: press(`), tap(ch) continuously, release(`) on Ctrl+C" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    while (running) {
        tapCharacter('c');
        tapCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * art - Python equivalent:
 *   controller.press("`")
 *   while run_event.is_set():
 *       controller.tap("c")
 *       controller.tap("h")
 *       time.sleep(0.02)
 *   controller.release("`")
 * 
 * Continuous typing with 20ms delay between pairs
 */
void art() {
    std::cout << "art: press(`), tap(ch) with 20ms delay continuously, release(`) on Ctrl+C" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    while (running) {
        tapCharacter('c');
        tapCharacter('h');
        #ifdef _WIN32
        Sleep(20);
        #else
        usleep(20000);  // 20ms delay like Python's time.sleep(0.02)
        #endif
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * heal_macro - Custom macro for healing
 *   controller.press("`")
 *   controller.type("h"*3000)
 *   controller.release("`")
 */
void heal_macro() {
    std::cout << "heal_macro: press(`), type(h*3000), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 3000 && running; i++) {
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape_small - Python equivalent:
 *   controller.press("`")
 *   controller.type("f"*100)
 *   controller.release("`")
 */
void shape_small() {
    std::cout << "shape_small: press(`), type(f*100), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 100 && running; i++) {
        typeCharacter('f');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape_large - Python equivalent:
 *   controller.press("`")
 *   controller.type("f"*500)
 *   controller.release("`")
 */
void shape_large() {
    std::cout << "shape_large: press(`), type(f*500), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 500 && running; i++) {
        typeCharacter('f');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * slowwall - Python equivalent:
 *   controller.press("`")
 *   for _ in range(50):
 *       controller.tap("x")
 *       time.sleep(0.08)
 *   controller.release("`")
 */
void slowwall() {
    std::cout << "slowwall: press(`), tap(x) with 80ms delay * 50, release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < 50 && running; i++) {
        tapCharacter('x');
        #ifdef _WIN32
        Sleep(80);
        #else
        usleep(80000);
        #endif
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * circle - Python equivalent:
 *   controller.press("`")
 *   controller.type("ch")
 *   controller.release("`")
 */
void circle() {
    std::cout << "circle: press(`), type(ch), release(`)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(5);
    #else
    usleep(5000);
    #endif
    typeCharacter('c');
    typeCharacter('h');
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape_q - Python equivalent (Ctrl+Q):
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.type("fy"*10)
 *   controller.type(("f"*50+"h")*2)
 *   controller.release("`")
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.press("d")
 *   controller.release("`")
 */
void shape_q() {
    std::cout << "shape_q: optimized pattern (2 iterations)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(5);
    #else
    usleep(5000);
    #endif
    tapCharacter('d');
    // Type "fy" * 10
    for (int i = 0; i < 10; i++) {
        typeCharacter('f');
        typeCharacter('y');
    }
    // Type ("f"*50+"h")*2
    for (int i = 0; i < 2 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    pressKey(kVK_ANSI_Grave);
    tapCharacter('d');
    pressKey(kVK_ANSI_D);
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape_a - Python equivalent (Ctrl+A):
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.type("fy"*10)
 *   controller.type(("f"*50+"h")*6)
 *   controller.release("`")
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.press("d")
 *   controller.release("`")
 */
void shape_a() {
    std::cout << "shape_a: optimized pattern (6 iterations)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(5);
    #else
    usleep(5000);
    #endif
    tapCharacter('d');
    // Type "fy" * 10
    for (int i = 0; i < 10; i++) {
        typeCharacter('f');
        typeCharacter('y');
    }
    // Type ("f"*50+"h")*6
    for (int i = 0; i < 6 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    pressKey(kVK_ANSI_Grave);
    tapCharacter('d');
    pressKey(kVK_ANSI_D);
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape_z - Python equivalent (Ctrl+Z):
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.type("fy"*10)
 *   controller.type(("f"*50+"h")*10)
 *   controller.release("`")
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.press("d")
 *   controller.release("`")
 */
void shape_z() {
    std::cout << "shape_z: optimized pattern (10 iterations)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(5);
    #else
    usleep(5000);
    #endif
    tapCharacter('d');
    // Type "fy" * 10
    for (int i = 0; i < 10; i++) {
        typeCharacter('f');
        typeCharacter('y');
    }
    // Type ("f"*50+"h")*10
    for (int i = 0; i < 10 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    pressKey(kVK_ANSI_Grave);
    tapCharacter('d');
    pressKey(kVK_ANSI_D);
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape_y - Python equivalent (Ctrl+Y):
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.type("fy"*10)
 *   controller.type(("f"*50+"h")*2)
 *   controller.release("`")
 * 
 * Note: Does NOT have the d+d sequence unlike shape_q
 */
void shape_y() {
    std::cout << "shape_y: optimized pattern (2 iterations, no d+d)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(5);
    #else
    usleep(5000);
    #endif
    tapCharacter('d');
    // Type "fy" * 10
    for (int i = 0; i < 10; i++) {
        typeCharacter('f');
        typeCharacter('y');
    }
    // Type ("f"*50+"h")*2
    for (int i = 0; i < 2 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape_u - Python equivalent (Ctrl+U):
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.type("fy"*10)
 *   controller.type(("f"*50+"h")*6)
 *   controller.release("`")
 * 
 * Note: Does NOT have the d+d sequence unlike shape_a
 */
void shape_u() {
    std::cout << "shape_u: optimized pattern (6 iterations, no d+d)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(5);
    #else
    usleep(5000);
    #endif
    tapCharacter('d');
    // Type "fy" * 10
    for (int i = 0; i < 10; i++) {
        typeCharacter('f');
        typeCharacter('y');
    }
    // Type ("f"*50+"h")*6
    for (int i = 0; i < 6 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * shape_i - Python equivalent (Ctrl+I):
 *   controller.press("`")
 *   controller.tap("d")
 *   controller.type("fy"*10)
 *   controller.type(("f"*50+"h")*10)
 *   controller.release("`")
 * 
 * Note: Does NOT have the d+d sequence unlike shape_z
 */
void shape_i() {
    std::cout << "shape_i: optimized pattern (10 iterations, no d+d)" << std::endl;
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(5);
    #else
    usleep(5000);
    #endif
    tapCharacter('d');
    // Type "fy" * 10
    for (int i = 0; i < 10; i++) {
        typeCharacter('f');
        typeCharacter('y');
    }
    // Type ("f"*50+"h")*10
    for (int i = 0; i < 10 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
}

/**
 * benchmark - Time the circles macro
 */
void benchmark(int amt = 5000) {
    std::cout << "benchmark: Timing circles*" << amt << std::endl;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    // Call circles function
    pressKey(kVK_ANSI_Grave);
    #ifdef _WIN32
    Sleep(10);
    #else
    usleep(10000);
    #endif
    for (int i = 0; i < amt && running; i++) {
        tapCharacter('c');
        tapCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    
    // Wait for user to press Enter to stop timer
    std::cout << "\nPress Enter when done to see results..." << std::endl;
    std::cin.get();
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    double seconds = duration.count() / 1000.0;
    double bps = (seconds > 0) ? (amt / seconds) : 0;
    
    std::cout << amt << " circles in " << duration.count() << " ms" << std::endl;
    std::cout << "Speed: " << bps << " circles/second" << std::endl;
    
    // Type results in game (matching Python behavior)
    #ifdef _WIN32
    Sleep(200);
    #else
    usleep(200000);
    #endif
    tapKey(kVK_Return);
    #ifdef _WIN32
    Sleep(150);
    #else
    usleep(150000);
    #endif
    std::string result1 = "> [" + std::to_string(duration.count()) + "ms] <";
    typeString(result1);
    #ifdef _WIN32
    Sleep(100);
    #else
    usleep(100000);
    #endif
    tapKey(kVK_Return);
    tapKey(kVK_Return);
    #ifdef _WIN32
    Sleep(100);
    #else
    usleep(100000);
    #endif
    std::string result2 = "> [" + std::to_string((int)bps) + "] <";
    typeString(result2);
    #ifdef _WIN32
    Sleep(100);
    #else
    usleep(100000);
    #endif
    tapKey(kVK_Return);
}

/**
 * arena_close - Spam $arena close commands
 */
void arena_close(int count = 200) {
    std::cout << "arena_close: Spamming $arena close " << count << " times" << std::endl;
    for (int i = 0; i < count && running; i++) {
        tapKey(kVK_Return);
        typeStringFast("$arena close");
        tapKey(kVK_Return);
    }
}

// ==================== Main and Help ====================

void printUsage(const char* progName) {
    std::cerr << "Usage: " << progName << " <command> [args...]\n";
    std::cerr << "\nArena Automation:\n";
    std::cerr << "  arena <type> [max_cmds] [rate_limit] [step]  - Arena size automation\n";
    std::cerr << "    type 1: Random arena sizes\n";
    std::cerr << "    type 2: Bouncing dimensions\n";
    std::cerr << "    type 3: Inverse bouncing dimensions\n";
    std::cerr << "    max_cmds: Max commands before stopping (0 = unlimited)\n";
    std::cerr << "    rate_limit: Commands per second (0 = unlimited)\n";
    std::cerr << "    step: Step size for type 2/3 (default: 2)\n";
    std::cerr << "  arena_close [count]    - Spam $arena close (default: 200)\n";
    std::cerr << "\nMacro Commands:\n";
    std::cerr << "  wallcrash       - press(`), type(x*1800), release(`)\n";
    std::cerr << "  nuke            - press(`), type(wk*100), release(`)\n";
    std::cerr << "  shape           - press(`), type(f*5000), release(`)\n";
    std::cerr << "  score           - press(`), type(n*20000), release(`)\n";
    std::cerr << "  score50m        - press(`), type(f*20), release(`)\n";
    std::cerr << "  circles [amt]   - press(`), tap(ch)*amt, release(`) (default: 210)\n";
    std::cerr << "  walls           - press(`), type(x*210), release(`)\n";
    std::cerr << "  circle          - press(`), type(ch), release(`)\n";
    std::cerr << "  slowwall        - press(`), tap(x) with 80ms delay * 50, release(`)\n";
    std::cerr << "  minicirclecrash - press(`), tap(ch)*5000, release(`)\n";
    std::cerr << "  circlecrash     - press(`), tap(ch)*32400, release(`)\n";
    std::cerr << "  mcrash          - Continuous ch until Ctrl+C\n";
    std::cerr << "  art             - Continuous ch with 20ms delay until Ctrl+C\n";
    std::cerr << "  heal            - press(`), type(h*3000), release(`)\n";
    std::cerr << "  shape_small     - press(`), type(f*100), release(`)\n";
    std::cerr << "  shape_large     - press(`), type(f*500), release(`)\n";
    std::cerr << "  shape_q         - Shape pattern (2 iterations + d+d)\n";
    std::cerr << "  shape_a         - Shape pattern (6 iterations + d+d)\n";
    std::cerr << "  shape_z         - Shape pattern (10 iterations + d+d)\n";
    std::cerr << "  shape_y         - Shape pattern (2 iterations, no d+d)\n";
    std::cerr << "  shape_u         - Shape pattern (6 iterations, no d+d)\n";
    std::cerr << "  shape_i         - Shape pattern (10 iterations, no d+d)\n";
    std::cerr << "  benchmark [amt] - Time circles macro (default: 5000)\n";
    std::cerr << "\nExamples:\n";
    std::cerr << "  " << progName << " arena 1              # Random arena sizes (unlimited)\n";
    std::cerr << "  " << progName << " arena 2 576 150 8    # Bouncing, 576 max, 150/s, step 8\n";
    std::cerr << "  " << progName << " circles 500          # Spawn 500 circles\n";
    std::cerr << "  " << progName << " mcrash               # Continuous circles until Ctrl+C\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printUsage(argv[0]);
        return 1;
    }
    
    if (!checkAccessibility()) {
        #ifdef __APPLE__
        std::cerr << "ERROR: This application requires accessibility permissions.\n";
        std::cerr << "Please grant access in System Settings > Privacy & Security > Accessibility\n";
        #elif __linux__
        std::cerr << "ERROR: Could not open X11 display.\n";
        std::cerr << "Make sure X11 is running and DISPLAY is set.\n";
        #endif
        return 1;
    }
    
    #ifdef __linux__
    initKeycodes();
    #endif
    
    // Setup signal handler for Ctrl+C
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    std::string command = argv[1];
    
    std::cout << "Starting: " << command << std::endl;
    std::cout << "Press Ctrl+C to stop" << std::endl;
    
    // Arena automation
    if (command == "arena") {
        if (argc < 3) {
            std::cerr << "Usage: " << argv[0] << " arena <type> [max_cmds] [rate_limit] [step]\n";
            return 1;
        }
        int type = std::atoi(argv[2]);
        int maxCmds = (argc >= 4) ? std::atoi(argv[3]) : 0;
        int rateLimit = (argc >= 5) ? std::atoi(argv[4]) : 0;
        int step = (argc >= 6) ? std::atoi(argv[5]) : 2;
        
        // Ensure step is even
        if (step % 2 != 0) step = 2;
        
        switch (type) {
            case 1: arenaAutomationType1(maxCmds, rateLimit); break;
            case 2: arenaAutomationType2(step, maxCmds, rateLimit); break;
            case 3: arenaAutomationType3(step, maxCmds, rateLimit); break;
            default:
                std::cerr << "Invalid arena type: " << type << std::endl;
                return 1;
        }
    }
    // Arena close
    else if (command == "arena_close") {
        int count = (argc >= 3) ? std::atoi(argv[2]) : 200;
        arena_close(count);
    }
    // Macro commands
    else if (command == "wallcrash") { wallcrash(); }
    else if (command == "nuke") { nuke(); }
    else if (command == "shape") { shape(); }
    else if (command == "score") { score(); }
    else if (command == "score50m") { score50m(); }
    else if (command == "circles") {
        int amt = (argc >= 3) ? std::atoi(argv[2]) : 210;
        circles(amt);
    }
    else if (command == "walls") { walls(); }
    else if (command == "circle") { circle(); }
    else if (command == "slowwall") { slowwall(); }
    else if (command == "minicirclecrash") { minicirclecrash(); }
    else if (command == "circlecrash") { circlecrash(); }
    else if (command == "mcrash") { mcrash(); }
    else if (command == "art") { art(); }
    else if (command == "heal") { heal_macro(); }
    else if (command == "shape_small") { shape_small(); }
    else if (command == "shape_large") { shape_large(); }
    else if (command == "shape_q") { shape_q(); }
    else if (command == "shape_a") { shape_a(); }
    else if (command == "shape_z") { shape_z(); }
    else if (command == "shape_y") { shape_y(); }
    else if (command == "shape_u") { shape_u(); }
    else if (command == "shape_i") { shape_i(); }
    else if (command == "benchmark") {
        int amt = (argc >= 3) ? std::atoi(argv[2]) : 5000;
        benchmark(amt);
    }
    else {
        std::cerr << "Unknown command: " << command << std::endl;
        printUsage(argv[0]);
        return 1;
    }
    
    std::cout << "\nCompleted." << std::endl;
    
    #ifdef __linux__
    if (display) {
        XCloseDisplay(display);
    }
    #endif
    
    return 0;
}
