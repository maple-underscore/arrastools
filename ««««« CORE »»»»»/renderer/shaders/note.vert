#version 330 core

// Note vertex shader
// Transforms note vertices from world space to screen space

layout(location = 0) in vec2 position;  // Vertex position
layout(location = 1) in vec2 texCoord;  // Texture coordinate
layout(location = 2) in vec4 color;     // Vertex color (for multiplier indication)

out vec2 fragTexCoord;
out vec4 fragColor;

uniform mat4 projection;  // Orthographic projection matrix

void main() {
    gl_Position = projection * vec4(position, 0.0, 1.0);
    fragTexCoord = texCoord;
    fragColor = color;
}
