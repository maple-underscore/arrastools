/**
 * C++ implementation of performance-critical Arras macros
 * 
 * Compile on macOS:
 *   clang++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.dylib
 * 
 * Compile on Linux:
 *   g++ -std=c++17 -O3 -shared -fPIC arras_cpp_macros.cpp -o arras_cpp_macros.so
 * 
 * Compile on Windows:
 *   cl /O2 /LD arras_cpp_macros.cpp /link /OUT:arras_cpp_macros.dll
 */

#include <cstdint>
#include <cstring>
#include <random>

extern "C" {

/**
 * Fast circle pattern generator (circles function)
 * Generates "cccccccccch" pattern amt times
 * Returns total character count
 */
int32_t circles_cpp(char* buffer, int32_t amt) {
    const char* pattern = "cccccccccch";  // 11 chars
    const int32_t pattern_len = 11;
    int32_t total = amt * pattern_len;
    
    for (int32_t i = 0; i < amt; ++i) {
        memcpy(buffer + i * pattern_len, pattern, pattern_len);
    }
    
    return total;
}

/**
 * Fast wall pattern generator (walls function)
 * Generates 210 'x' characters
 * Returns total character count
 */
int32_t walls_cpp(char* buffer) {
    memset(buffer, 'x', 210);
    return 210;
}

/**
 * Fast circlecrash pattern generator
 * Generates "ccccccccccccccccccccccccch" pattern 1600 times
 * Returns total character count
 */
int32_t circlecrash_cpp(char* buffer) {
    const char* pattern = "ccccccccccccccccccccccccch";  // 26 chars
    const int32_t pattern_len = 26;
    const int32_t count = 1600;
    int32_t total = count * pattern_len;
    
    for (int32_t i = 0; i < count; ++i) {
        memcpy(buffer + i * pattern_len, pattern, pattern_len);
    }
    
    return total;
}

/**
 * Fast minicirclecrash pattern generator
 * Generates "ccccccccccccccccccccccccch" pattern 240 times
 * Returns total character count
 */
int32_t minicirclecrash_cpp(char* buffer) {
    const char* pattern = "ccccccccccccccccccccccccch";  // 26 chars
    const int32_t pattern_len = 26;
    const int32_t count = 240;
    int32_t total = count * pattern_len;
    
    for (int32_t i = 0; i < count; ++i) {
        memcpy(buffer + i * pattern_len, pattern, pattern_len);
    }
    
    return total;
}

/**
 * Arena automation type 1: random even values
 * Generates command strings for arena size randomization
 */
int32_t arena_automation_type1_cpp(char* buffer, int32_t count, uint32_t seed) {
    std::mt19937 rng(seed);
    std::uniform_int_distribution<int32_t> dist(1, 512);  // 2 to 1024 in steps of 2
    
    char* ptr = buffer;
    for (int32_t i = 0; i < count; ++i) {
        int32_t x = dist(rng) * 2;
        int32_t y = dist(rng) * 2;
        int32_t written = snprintf(ptr, 50, "$arena size %d %d\n", x, y);
        ptr += written;
    }
    
    return ptr - buffer;
}

/**
 * Arena automation type 2: bouncing pattern
 * Both x and y bounce from 2 to 1024
 */
int32_t arena_automation_type2_cpp(char* buffer, int32_t count, int32_t step) {
    int32_t x = 2, y = 2;
    int32_t dir_x = step, dir_y = step;
    
    char* ptr = buffer;
    for (int32_t i = 0; i < count; ++i) {
        int32_t written = snprintf(ptr, 50, "$arena size %d %d\n", x, y);
        ptr += written;
        
        x += dir_x;
        y += dir_y;
        
        if (x > 1024) { x = 1024; dir_x = -step; }
        else if (x < 2) { x = 2; dir_x = step; }
        
        if (y > 1024) { y = 1024; dir_y = -step; }
        else if (y < 2) { y = 2; dir_y = step; }
    }
    
    return ptr - buffer;
}

/**
 * Arena automation type 3: inverse bouncing pattern
 * x bounces 2->1024, y bounces 1024->2
 */
int32_t arena_automation_type3_cpp(char* buffer, int32_t count, int32_t step) {
    int32_t x = 2, y = 1024;
    int32_t dir_x = step, dir_y = -step;
    
    char* ptr = buffer;
    for (int32_t i = 0; i < count; ++i) {
        int32_t written = snprintf(ptr, 50, "$arena size %d %d\n", x, y);
        ptr += written;
        
        x += dir_x;
        y += dir_y;
        
        if (x > 1024) { x = 1024; dir_x = -step; }
        else if (x < 2) { x = 2; dir_x = step; }
        
        if (y > 1024) { y = 1024; dir_y = -step; }
        else if (y < 2) { y = 2; dir_y = step; }
    }
    
    return ptr - buffer;
}

/**
 * Benchmark helper: generates circle pattern for performance testing
 * Same as circles_cpp but optimized for large counts
 */
int32_t benchmark_cpp(char* buffer, int32_t amt) {
    return circles_cpp(buffer, amt);
}

}  // extern "C"
