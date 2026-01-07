#version 330 core

// Note fragment shader
// Renders notes with solid color and optional outline

in vec2 fragTexCoord;
in vec4 fragColor;

out vec4 finalColor;

uniform bool useTexture;      // Whether to use texture or solid color
uniform sampler2D noteTexture;  // Optional texture for notes
uniform float outlineWidth;   // Width of outline (0.0 to 1.0)
uniform vec4 outlineColor;    // Color of outline

void main() {
    if (useTexture) {
        // Use texture if available
        vec4 texColor = texture(noteTexture, fragTexCoord);
        finalColor = texColor * fragColor;
    } else {
        // Solid color with optional outline
        vec2 coord = fragTexCoord * 2.0 - 1.0;  // Map to -1..1
        float dist = max(abs(coord.x), abs(coord.y));
        
        if (outlineWidth > 0.0 && dist > 1.0 - outlineWidth) {
            // Draw outline
            finalColor = outlineColor;
        } else {
            // Draw fill
            finalColor = fragColor;
        }
    }
}
