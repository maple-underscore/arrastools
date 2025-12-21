/**
 * macro_tools.cpp - C++ implementation of arrastools.py macro functions
 * 
 * This file provides optimized C++ implementations of the Python macros.
 * Each function imitates the exact behavior of its Python counterpart:
 * - Press backtick (`)
 * - Type the payload
 * - Release backtick (`)
 * 
 * Compile with: make
 * Usage: ./macro_tools <command> [amount]
 */

#include <iostream>
#include <string>
#include <unistd.h>
#include <signal.h>
#include <chrono>
#include <thread>
#include <cmath>

#ifdef __APPLE__
    #include <ApplicationServices/ApplicationServices.h>
    #include <Carbon/Carbon.h>
#elif __linux__
    #include <X11/Xlib.h>
    #include <X11/keysym.h>
    #include <X11/extensions/XTest.h>
#elif _WIN32
    #include <windows.h>
#endif

volatile bool running = true;

void signalHandler(int signum) {
    std::cout << "\nInterrupt signal (" << signum << ") received. Stopping..." << std::endl;
    running = false;
}

#ifdef __APPLE__

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
    usleep(5000);  // 5ms delay
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

// Type a string by typing each character
// Imitates: controller.type("string")
void typeString(const std::string& str) {
    for (char c : str) {
        typeCharacter(c);
    }
}

// Tap a character key (like controller.tap("c"))
void tapCharacter(char c) {
    typeCharacter(c);
}

#endif

/**
 * wallcrash - Python equivalent:
 *   controller.press("`")
 *   controller.type("x"*1800)
 *   controller.release("`")
 */
void wallcrash() {
    std::cout << "wallcrash: press(`), type(x*1800), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 1800 && running; i++) {
        typeCharacter('x');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * nuke - Python equivalent:
 *   controller.press("`")
 *   controller.type("wk"*100)
 *   controller.release("`")
 */
void nuke() {
    std::cout << "nuke: press(`), type(wk*100), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 100 && running; i++) {
        typeCharacter('w');
        typeCharacter('k');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape - Python equivalent:
 *   controller.press("`")
 *   controller.type("f"*5000)
 *   controller.release("`")
 */
void shape() {
    std::cout << "shape: press(`), type(f*5000), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 5000 && running; i++) {
        typeCharacter('f');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * score - Python equivalent:
 *   controller.press("`")
 *   controller.type("n"*20000)
 *   controller.release("`")
 */
void score() {
    std::cout << "score: press(`), type(n*20000), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 20000 && running; i++) {
        typeCharacter('n');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * circles - Python equivalent:
 *   controller.press("`")
 *   for _ in range(amt):
 *       controller.tap("c")
 *       controller.tap("h")
 *   controller.release("`")
 */
void circles(int amt) {
    std::cout << "circles: press(`), tap(ch)*" << amt << ", release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < amt && running; i++) {
        tapCharacter('c');
        tapCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * walls - Python equivalent:
 *   controller.press("`")
 *   controller.type("x"*210)
 *   controller.release("`")
 */
void walls() {
    std::cout << "walls: press(`), type(x*210), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 210 && running; i++) {
        typeCharacter('x');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * minicirclecrash - Python equivalent:
 *   controller.press("`")
 *   for _ in range(25):
 *       for _ in range(100):
 *           controller.tap("c")
 *           controller.tap("h")
 *   controller.release("`")
 * 
 * Total: 25 * 100 = 2500 "ch" pairs
 */
void minicirclecrash() {
    std::cout << "minicirclecrash: press(`), tap(ch)*2500 (25*100), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 50 && running; i++) {
        for (int j = 0; j < 100 && running; j++) {
            tapCharacter('c');
            tapCharacter('h');
        }
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
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
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 180 && running; i++) {
        for (int j = 0; j < 180 && running; j++) {
            tapCharacter('c');
            tapCharacter('h');
        }
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
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
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    while (running) {
        tapCharacter('c');
        tapCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * heal_macro - Custom macro for healing
 *   controller.press("`")
 *   controller.type("h"*3000)
 *   controller.release("`")
 */
void heal_macro() {
    std::cout << "heal_macro: press(`), type(h*3000), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 3000 && running; i++) {
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape_small - Python equivalent:
 *   controller.press("`")
 *   controller.type("f"*100)
 *   controller.release("`")
 */
void shape_small() {
    std::cout << "shape_small: press(`), type(f*100), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 100 && running; i++) {
        typeCharacter('f');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape_large - Python equivalent:
 *   controller.press("`")
 *   controller.type("f"*500)
 *   controller.release("`")
 */
void shape_large() {
    std::cout << "shape_large: press(`), type(f*500), release(`)" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 500 && running; i++) {
        typeCharacter('f');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * benchmark - Python equivalent:
 *   start = time.time()
 *   circles(amt)
 *   # wait for shift key
 *   elapsed = time.time() - start
 *   controller.tap(Key.enter)
 *   controller.type(f"> [{elapsed}ms] <")
 *   controller.tap(Key.enter) x2
 *   controller.type(f"> [{bps}] <")
 *   controller.tap(Key.enter)
 */
void benchmark(int amt) {
    std::cout << "benchmark: Timing circles*" << amt << std::endl;
    #ifdef __APPLE__
    auto start = std::chrono::high_resolution_clock::now();
    
    // Call circles function
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
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
    usleep(200000);
    tapKey(kVK_Return);
    usleep(150000);
    std::string result1 = "> [" + std::to_string(duration.count()) + "ms] <";
    typeString(result1);
    usleep(100000);
    tapKey(kVK_Return);
    tapKey(kVK_Return);
    usleep(100000);
    std::string result2 = "> [" + std::to_string((int)bps) + "] <";
    typeString(result2);
    usleep(100000);
    tapKey(kVK_Return);
    #endif
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
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(10000);
    while (running) {
        tapCharacter('c');
        tapCharacter('h');
        usleep(20000);  // 20ms delay like Python's time.sleep(0.02)
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape_q - Python equivalent (Ctrl+Q):
 *   controller.press("`")
 *   controller.type("fy"*2)
 *   controller.type(("f"*50+"h")*2)
 *   controller.release("`")
 *   time.sleep(0.05)
 *   controller.press("`")
 *   time.sleep(0.05)
 *   controller.tap("d")
 *   controller.press("d")
 *   time.sleep(0.05)
 *   controller.release("`")
 */
void shape_q() {
    std::cout << "shape_q: optimized pattern" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(5000);
    // Type "fy" twice
    typeCharacter('f');
    typeCharacter('y');
    typeCharacter('f');
    typeCharacter('y');
    // Type ("f"*50+"h")*2
    for (int i = 0; i < 2 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    usleep(50000);
    pressKey(kVK_ANSI_Grave);
    usleep(50000);
    tapCharacter('d');
    pressKey(kVK_ANSI_D);
    usleep(50000);
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape_a - Python equivalent (Ctrl+A):
 *   controller.press("`")
 *   controller.type("fy"*2)
 *   controller.type(("f"*50+"h")*6)
 *   controller.release("`")
 *   time.sleep(0.05)
 *   controller.press("`")
 *   time.sleep(0.05)
 *   controller.tap("d")
 *   controller.press("d")
 *   time.sleep(0.05)
 *   controller.release("`")
 */
void shape_a() {
    std::cout << "shape_a: optimized pattern" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(5000);
    // Type "fy" twice
    typeCharacter('f');
    typeCharacter('y');
    typeCharacter('f');
    typeCharacter('y');
    // Type ("f"*50+"h")*6
    for (int i = 0; i < 6 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    usleep(50000);
    pressKey(kVK_ANSI_Grave);
    usleep(50000);
    tapCharacter('d');
    pressKey(kVK_ANSI_D);
    usleep(50000);
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape_z - Python equivalent (Ctrl+Z):
 *   controller.press("`")
 *   controller.type("fy"*2)
 *   controller.type(("f"*50+"h")*10)
 *   controller.release("`")
 *   time.sleep(0.05)
 *   controller.press("`")
 *   time.sleep(0.05)
 *   controller.tap("d")
 *   controller.press("d")
 *   time.sleep(0.05)
 *   controller.release("`")
 */
void shape_z() {
    std::cout << "shape_z: optimized pattern" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(5000);
    // Type "fy" twice
    typeCharacter('f');
    typeCharacter('y');
    typeCharacter('f');
    typeCharacter('y');
    // Type ("f"*50+"h")*10
    for (int i = 0; i < 10 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    usleep(50000);
    pressKey(kVK_ANSI_Grave);
    usleep(50000);
    tapCharacter('d');
    pressKey(kVK_ANSI_D);
    usleep(50000);
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape_y - Python equivalent (Ctrl+Y):
 *   controller.press("`")
 *   controller.type("fy"*2)
 *   controller.type(("f"*50+"h")*2)
 *   controller.release("`")
 * 
 * Note: Does NOT have the d+d sequence unlike shape_q
 */
void shape_y() {
    std::cout << "shape_y: optimized pattern" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(5000);
    // Type "fy" twice
    typeCharacter('f');
    typeCharacter('y');
    typeCharacter('f');
    typeCharacter('y');
    // Type ("f"*50+"h")*2
    for (int i = 0; i < 2 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape_u - Python equivalent (Ctrl+U):
 *   controller.press("`")
 *   controller.type("fy"*2)
 *   controller.type(("f"*50+"h")*6)
 *   controller.release("`")
 * 
 * Note: Does NOT have the d+d sequence unlike shape_a
 */
void shape_u() {
    std::cout << "shape_u: optimized pattern" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(5000);
    // Type "fy" twice
    typeCharacter('f');
    typeCharacter('y');
    typeCharacter('f');
    typeCharacter('y');
    // Type ("f"*50+"h")*6
    for (int i = 0; i < 6 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

/**
 * shape_i - Python equivalent (Ctrl+I):
 *   controller.press("`")
 *   controller.type("fy"*2)
 *   controller.type(("f"*50+"h")*10)
 *   controller.release("`")
 * 
 * Note: Does NOT have the d+d sequence unlike shape_z
 */
void shape_i() {
    std::cout << "shape_i: optimized pattern" << std::endl;
    #ifdef __APPLE__
    pressKey(kVK_ANSI_Grave);
    usleep(5000);
    // Type "fy" twice
    typeCharacter('f');
    typeCharacter('y');
    typeCharacter('f');
    typeCharacter('y');
    // Type ("f"*50+"h")*10
    for (int i = 0; i < 10 && running; i++) {
        for (int j = 0; j < 50 && running; j++) {
            typeCharacter('f');
        }
        typeCharacter('h');
    }
    releaseKey(kVK_ANSI_Grave);
    #endif
}

void printUsage(const char* progName) {
    std::cerr << "Usage: " << progName << " <command> [amount]\n";
    std::cerr << "\nCommands (imitating arrastools.py):\n";
    std::cerr << "  wallcrash       - press(`), type(x*1800), release(`)\n";
    std::cerr << "  nuke            - press(`), type(wk*100), release(`)\n";
    std::cerr << "  shape           - press(`), type(f*5000), release(`)\n";
    std::cerr << "  shape_q         - press(`), type(fy*100), press(w), release(`) [Ctrl+Q]\n";
    std::cerr << "  shape_a         - press(`), type(fy*300), press(w), release(`) [Ctrl+A]\n";
    std::cerr << "  shape_z         - press(`), type(fy*500), press(w), release(`) [Ctrl+Z]\n";
    std::cerr << "  score           - press(`), type(n*20000), release(`)\n";
    std::cerr << "  circles [amt]   - press(`), tap(ch)*amt, release(`) (default 210)\n";
    std::cerr << "  walls           - press(`), type(x*210), release(`)\n";
    std::cerr << "  minicirclecrash - press(`), tap(ch)*5000, release(`)\n";
    std::cerr << "  circlecrash     - press(`), tap(ch)*32400, release(`)\n";
    std::cerr << "  mcrash          - press(`), tap(ch) continuously until Ctrl+C\n";
    std::cerr << "  art             - press(`), tap(ch) with 20ms delay until Ctrl+C\n";
    std::cerr << "  heal            - press(`), type(h*3000), release(`)\n";
    std::cerr << "  shape_small     - press(`), type(f*100), release(`)\n";
    std::cerr << "  shape_large     - press(`), type(f*500), release(`)\n";
    std::cerr << "  benchmark [amt] - Time circles macro (default 5000)\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printUsage(argv[0]);
        return 1;
    }
    
    #ifdef __APPLE__
    if (!checkAccessibility()) {
        std::cerr << "ERROR: This application requires accessibility permissions.\n";
        std::cerr << "Please grant access in System Settings > Privacy & Security > Accessibility\n";
        return 1;
    }
    #endif
    
    // Setup signal handler for Ctrl+C
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    std::string command = argv[1];
    int amount = 0;
    
    if (argc >= 3) {
        amount = std::atoi(argv[2]);
    }
    
    std::cout << "Starting macro: " << command << std::endl;
    std::cout << "Press Ctrl+C to stop" << std::endl;
    // Removed startup delay to trigger macros immediately
    
    if (command == "wallcrash") {
        wallcrash();
    } else if (command == "nuke") {
        nuke();
    } else if (command == "shape") {
        shape();
    } else if (command == "score") {
        score();
    } else if (command == "circles") {
        circles(amount > 0 ? amount : 210);
    } else if (command == "walls") {
        walls();
    } else if (command == "minicirclecrash") {
        minicirclecrash();
    } else if (command == "circlecrash") {
        circlecrash();
    } else if (command == "mcrash") {
        mcrash();
    } else if (command == "art") {
        art();
    } else if (command == "heal") {
        heal_macro();
    } else if (command == "shape_small") {
        shape_small();
    } else if (command == "shape_large") {
        shape_large();
    } else if (command == "benchmark") {
        benchmark(amount > 0 ? amount : 5000);
    } else if (command == "shape_q") {
        shape_q();
    } else if (command == "shape_a") {
        shape_a();
    } else if (command == "shape_z") {
        shape_z();
    } else if (command == "shape_y") {
        shape_y();
    } else if (command == "shape_u") {
        shape_u();
    } else if (command == "shape_i") {
        shape_i();
    } else {
        std::cerr << "Unknown command: " << command << std::endl;
        printUsage(argv[0]);
        return 1;
    }
    
    std::cout << "\nMacro completed." << std::endl;
    return 0;
}
