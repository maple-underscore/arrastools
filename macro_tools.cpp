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

void tapKey(CGKeyCode keyCode) {
    CGEventRef keyDown = CGEventCreateKeyboardEvent(NULL, keyCode, true);
    CGEventRef keyUp = CGEventCreateKeyboardEvent(NULL, keyCode, false);
    CGEventPost(kCGHIDEventTap, keyDown);
    usleep(5000);  // 5ms delay
    CGEventPost(kCGHIDEventTap, keyUp);
    CFRelease(keyDown);
    CFRelease(keyUp);
}

void typeCharacter(char c) {
    UniChar unicodeChar = (UniChar)c;
    CGEventRef event = CGEventCreateKeyboardEvent(NULL, 0, true);
    CGEventKeyboardSetUnicodeString(event, 1, &unicodeChar);
    CGEventPost(kCGHIDEventTap, event);
    CFRelease(event);
    usleep(1000);  // 1ms between characters
}

void typeString(const std::string& str) {
    for (char c : str) {
        typeCharacter(c);
    }
}
#endif

void wallcrash() {
    std::cout << "wallcrash: Typing x*1800" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);  // backtick
    usleep(10000);
    for (int i = 0; i < 1800 && running; i++) {
        typeCharacter('x');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void nuke() {
    std::cout << "nuke: Typing wk*100" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 100 && running; i++) {
        typeCharacter('w');
        typeCharacter('k');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void shape() {
    std::cout << "shape: Typing f*5000" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 5000 && running; i++) {
        typeCharacter('f');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void shape2() {
    std::cout << "shape2: Typing f*1000 with w pressed" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 1000 && running; i++) {
        typeCharacter('f');
    }
    // Press w
    CGEventRef keyDown = CGEventCreateKeyboardEvent(NULL, kVK_ANSI_W, true);
    CGEventPost(kCGHIDEventTap, keyDown);
    CFRelease(keyDown);
    usleep(5000);
    tapKey(kVK_ANSI_Grave);
    #endif
}

void score() {
    std::cout << "score: Typing n*20000" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 20000 && running; i++) {
        typeCharacter('n');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void circles(int amt) {
    std::cout << "circles: Typing ch*" << amt << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < amt && running; i++) {
        typeCharacter('c');
        typeCharacter('h');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void walls() {
    std::cout << "walls: Typing x*210" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 210 && running; i++) {
        typeCharacter('x');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void minicirclecrash() {
    std::cout << "minicirclecrash: Typing ch*25 with mouse movements" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 25 && running; i++) {
        typeCharacter('c');
        typeCharacter('h');
        // Small mouse movement (2 pixels each direction)
        CGPoint currentPos;
        CGEventRef event = CGEventCreate(NULL);
        currentPos = CGEventGetLocation(event);
        CFRelease(event);
        
        CGEventRef move = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, 
            CGPointMake(currentPos.x + 2, currentPos.y), kCGMouseButtonLeft);
        CGEventPost(kCGHIDEventTap, move);
        CFRelease(move);
        usleep(5000);
        
        move = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, 
            CGPointMake(currentPos.x, currentPos.y + 2), kCGMouseButtonLeft);
        CGEventPost(kCGHIDEventTap, move);
        CFRelease(move);
        usleep(5000);
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void circlecrash() {
    std::cout << "circlecrash: Typing ch*180 with mouse movements" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 180 && running; i++) {
        typeCharacter('c');
        typeCharacter('h');
        // Mouse movement in circular pattern
        CGPoint currentPos;
        CGEventRef event = CGEventCreate(NULL);
        currentPos = CGEventGetLocation(event);
        CFRelease(event);
        
        double angle = (i * 2.0) * M_PI / 180.0;
        CGEventRef move = CGEventCreateMouseEvent(NULL, kCGEventMouseMoved, 
            CGPointMake(currentPos.x + cos(angle) * 2, currentPos.y + sin(angle) * 2), 
            kCGMouseButtonLeft);
        CGEventPost(kCGHIDEventTap, move);
        CFRelease(move);
        usleep(5000);
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void mcrash() {
    std::cout << "mcrash: Continuous ch typing (Ctrl+C to stop)" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    while (running) {
        typeCharacter('c');
        typeCharacter('h');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void heal_macro() {
    std::cout << "heal_macro: Typing h*3000" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 3000 && running; i++) {
        typeCharacter('h');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void shape_small() {
    std::cout << "shape_small: Typing f*500" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 500 && running; i++) {
        typeCharacter('f');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void shape_large() {
    std::cout << "shape_large: Typing f*5000" << std::endl;
    #ifdef __APPLE__
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < 5000 && running; i++) {
        typeCharacter('f');
    }
    tapKey(kVK_ANSI_Grave);
    #endif
}

void benchmark(int amt) {
    std::cout << "benchmark: Timing circles*" << amt << std::endl;
    #ifdef __APPLE__
    auto start = std::chrono::high_resolution_clock::now();
    
    tapKey(kVK_ANSI_Grave);
    usleep(10000);
    for (int i = 0; i < amt && running; i++) {
        typeCharacter('c');
        typeCharacter('h');
    }
    tapKey(kVK_ANSI_Grave);
    
    // Wait for user to press Shift (or just finish)
    std::cout << "\nPress Enter when done to see results..." << std::endl;
    std::cin.get();
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    double seconds = duration.count() / 1000.0;
    double bps = amt / seconds;
    
    std::cout << amt << " circles in " << duration.count() << " ms" << std::endl;
    std::cout << "Speed: " << bps << " circles/second" << std::endl;
    
    // Type results in game
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

void printUsage(const char* progName) {
    std::cerr << "Usage: " << progName << " <command> [amount]\n";
    std::cerr << "\nCommands:\n";
    std::cerr << "  wallcrash       - Type x*1800\n";
    std::cerr << "  nuke            - Type wk*100\n";
    std::cerr << "  shape           - Type f*5000\n";
    std::cerr << "  shape2          - Type f*1000 with w pressed\n";
    std::cerr << "  score           - Type n*20000\n";
    std::cerr << "  circles [amt]   - Type ch*amt (default 210)\n";
    std::cerr << "  walls           - Type x*210\n";
    std::cerr << "  minicirclecrash - Type ch*25 with mouse movements\n";
    std::cerr << "  circlecrash     - Type ch*180 with circular mouse movements\n";
    std::cerr << "  mcrash          - Continuous ch typing (Ctrl+C to stop)\n";
    std::cerr << "  heal            - Type h*3000 (heal macro)\n";
    std::cerr << "  shape_small     - Type f*500 (Ctrl+[)\n";
    std::cerr << "  shape_large     - Type f*5000 (Ctrl+])\n";
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
    
    // Setup signal handler
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    std::string command = argv[1];
    int amount = 0;
    
    if (argc >= 3) {
        amount = std::atoi(argv[2]);
    }
    
    std::cout << "Starting macro: " << command << std::endl;
    std::cout << "Press Ctrl+C to stop" << std::endl;
    usleep(500000);  // 0.5 second delay before starting
    
    if (command == "wallcrash") {
        wallcrash();
    } else if (command == "nuke") {
        nuke();
    } else if (command == "shape") {
        shape();
    } else if (command == "shape2") {
        shape2();
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
    } else if (command == "heal") {
        heal_macro();
    } else if (command == "shape_small") {
        shape_small();
    } else if (command == "shape_large") {
        shape_large();
    } else if (command == "benchmark") {
        benchmark(amount > 0 ? amount : 5000);
    } else {
        std::cerr << "Unknown command: " << command << std::endl;
        printUsage(argv[0]);
        return 1;
    }
    
    std::cout << "\nMacro completed." << std::endl;
    return 0;
}
