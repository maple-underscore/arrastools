#version 330 core

// Particle vertex shader
// Handles GPU-instanced rendering of particles with per-instance attributes

layout(location = 0) in vec2 position;        // Base vertex position (quad)
layout(location = 1) in vec2 texCoord;        // Texture coordinate
layout(location = 2) in vec2 particlePos;     // Per-instance: particle center position
layout(location = 3) in float particleSize;   // Per-instance: particle size
layout(location = 4) in vec4 particleColor;   // Per-instance: particle color
layout(location = 5) in float particleAlpha;  // Per-instance: particle alpha

out vec2 fragTexCoord;
out vec4 fragColor;
out float fragAlpha;

uniform mat4 projection;  // Orthographic projection matrix

void main() {
    // Scale position by particle size and translate to particle position
    vec2 scaledPos = position * particleSize + particlePos;
    gl_Position = projection * vec4(scaledPos, 0.0, 1.0);
    
    fragTexCoord = texCoord;
    fragColor = particleColor;
    fragAlpha = particleAlpha;
}
