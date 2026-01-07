#version 330 core

// Particle fragment shader
// Renders particles with radial gradient and alpha blending

in vec2 fragTexCoord;
in vec4 fragColor;
in float fragAlpha;

out vec4 finalColor;

uniform bool useCircle;  // Whether to render as circle or square

void main() {
    vec2 coord = fragTexCoord * 2.0 - 1.0;  // Map to -1..1
    float dist = length(coord);
    
    if (useCircle) {
        // Circular particle with soft edge
        if (dist > 1.0) {
            discard;  // Outside circle
        }
        
        // Radial gradient from center to edge
        float intensity = 1.0 - dist;
        intensity = pow(intensity, 0.5);  // Soften falloff
        
        finalColor = vec4(fragColor.rgb, fragColor.a * fragAlpha * intensity);
    } else {
        // Square particle
        finalColor = vec4(fragColor.rgb, fragColor.a * fragAlpha);
    }
}
