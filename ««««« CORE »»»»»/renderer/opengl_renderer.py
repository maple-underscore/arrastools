"""
OpenGL-based renderer (GPU-accelerated with Pygame).
Implements VBOs, sprite batching, and shader-based rendering for maximum performance.
"""

import os
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    print("OpenGL/Pygame not available - falling back to Tkinter renderer")

from .base_renderer import BaseRenderer
from .sprite_pool import NotePool, ParticlePool


class OpenGLRenderer(BaseRenderer):
    """GPU-accelerated OpenGL renderer with Pygame."""
    
    def __init__(self, width: int, height: int, settings: Dict[str, Any]):
        """
        Initialize OpenGL renderer.
        
        Args:
            width: Window width
            height: Window height
            settings: Game settings
        """
        if not OPENGL_AVAILABLE:
            raise ImportError("OpenGL/Pygame not available")
        
        super().__init__(width, height, settings)
        
        # Pygame/OpenGL state
        self.screen = None
        self.clock = pygame.time.Clock()
        
        # Shader programs
        self.note_shader = None
        self.particle_shader = None
        
        # VBOs and VAOs
        self.note_vbo = None
        self.note_vao = None
        self.particle_vbo = None
        self.particle_vao = None
        self.particle_instance_vbo = None
        
        # Projection matrix
        self.projection_matrix = None
        
        # Object pools
        self.note_pool = NotePool()
        self.particle_pool = ParticlePool(max_particles=1000)
        
        # Static rendering state
        self.static_layer_rendered = False
        self.static_display_list = None
        
        # Batch data
        self.note_batch = []
        self.particle_batch = []
        
        # Performance tracking
        self.gpu_memory_used = 0.0
    
    def initialize(self) -> bool:
        """Initialize OpenGL renderer with Pygame."""
        try:
            # Initialize Pygame
            pygame.init()
            pygame.display.set_caption("Rhythm Game (OpenGL)")
            
            # Create OpenGL window
            self.screen = pygame.display.set_mode(
                (self.width, self.height),
                DOUBLEBUF | OPENGL | FULLSCREEN
            )
            
            # OpenGL setup
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glClearColor(0.0, 0.0, 0.0, 1.0)
            
            # Set up orthographic projection
            self.setup_projection()
            
            # Load shaders
            if not self.load_shaders():
                print("Failed to load shaders")
                return False
            
            # Create VBOs
            self.setup_buffers()
            
            # Create display list for static elements
            self.static_display_list = glGenLists(1)
            
            print(f"OpenGL Renderer initialized: {glGetString(GL_VERSION).decode()}")
            return True
            
        except Exception as e:
            print(f"Failed to initialize OpenGL renderer: {e}")
            return False
    
    def shutdown(self):
        """Clean up OpenGL resources."""
        # Delete shaders
        if self.note_shader:
            glDeleteProgram(self.note_shader)
        if self.particle_shader:
            glDeleteProgram(self.particle_shader)
        
        # Delete VBOs
        if self.note_vbo:
            glDeleteBuffers(1, [self.note_vbo])
        if self.note_vao:
            glDeleteVertexArrays(1, [self.note_vao])
        if self.particle_vbo:
            glDeleteBuffers(1, [self.particle_vbo])
        if self.particle_vao:
            glDeleteVertexArrays(1, [self.particle_vao])
        if self.particle_instance_vbo:
            glDeleteBuffers(1, [self.particle_instance_vbo])
        
        # Delete display list
        if self.static_display_list:
            glDeleteLists(self.static_display_list, 1)
        
        # Clean up pools
        self.note_pool.clear_all()
        self.particle_pool.clear_all()
        
        # Quit Pygame
        pygame.quit()
    
    def setup_projection(self):
        """Set up orthographic projection matrix."""
        # Create orthographic projection (screen coordinates)
        left, right = 0, self.width
        bottom, top = self.height, 0  # Flip Y axis
        near, far = -1, 1
        
        # Orthographic projection matrix
        self.projection_matrix = np.array([
            [2/(right-left), 0, 0, -(right+left)/(right-left)],
            [0, 2/(top-bottom), 0, -(top+bottom)/(top-bottom)],
            [0, 0, -2/(far-near), -(far+near)/(far-near)],
            [0, 0, 0, 1]
        ], dtype=np.float32)
    
    def load_shaders(self) -> bool:
        """Load and compile GLSL shaders."""
        shader_dir = os.path.join(os.path.dirname(__file__), 'shaders')
        
        try:
            # Load note shaders
            note_vert_path = os.path.join(shader_dir, 'note.vert')
            note_frag_path = os.path.join(shader_dir, 'note.frag')
            self.note_shader = self.create_shader_program(note_vert_path, note_frag_path)
            
            # Load particle shaders
            particle_vert_path = os.path.join(shader_dir, 'particle.vert')
            particle_frag_path = os.path.join(shader_dir, 'particle.frag')
            self.particle_shader = self.create_shader_program(particle_vert_path, particle_frag_path)
            
            return True
        except Exception as e:
            print(f"Shader loading failed: {e}")
            return False
    
    def create_shader_program(self, vert_path: str, frag_path: str) -> int:
        """Compile and link shader program."""
        # Read shader source
        with open(vert_path, 'r') as f:
            vert_source = f.read()
        with open(frag_path, 'r') as f:
            frag_source = f.read()
        
        # Compile vertex shader
        vert_shader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vert_shader, vert_source)
        glCompileShader(vert_shader)
        if not glGetShaderiv(vert_shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(vert_shader).decode()
            raise RuntimeError(f"Vertex shader compilation failed: {error}")
        
        # Compile fragment shader
        frag_shader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(frag_shader, frag_source)
        glCompileShader(frag_shader)
        if not glGetShaderiv(frag_shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(frag_shader).decode()
            raise RuntimeError(f"Fragment shader compilation failed: {error}")
        
        # Link program
        program = glCreateProgram()
        glAttachShader(program, vert_shader)
        glAttachShader(program, frag_shader)
        glLinkProgram(program)
        if not glGetProgramiv(program, GL_LINK_STATUS):
            error = glGetProgramInfoLog(program).decode()
            raise RuntimeError(f"Shader program linking failed: {error}")
        
        # Clean up
        glDeleteShader(vert_shader)
        glDeleteShader(frag_shader)
        
        return program
    
    def setup_buffers(self):
        """Create VBOs and VAOs for rendering."""
        # Note quad (base geometry for all notes)
        note_vertices = np.array([
            # Position (x, y), TexCoord (u, v)
            -0.5, -0.5,  0.0, 0.0,
             0.5, -0.5,  1.0, 0.0,
             0.5,  0.5,  1.0, 1.0,
            -0.5,  0.5,  0.0, 1.0,
        ], dtype=np.float32)
        
        # Create note VAO and VBO
        self.note_vao = glGenVertexArrays(1)
        self.note_vbo = glGenBuffers(1)
        
        glBindVertexArray(self.note_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.note_vbo)
        glBufferData(GL_ARRAY_BUFFER, note_vertices.nbytes, note_vertices, GL_STATIC_DRAW)
        
        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(0))
        
        # TexCoord attribute
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(2 * 4))
        
        glBindVertexArray(0)
        
        # Particle quad (for instanced rendering)
        particle_vertices = np.array([
            # Position (x, y), TexCoord (u, v)
            -1.0, -1.0,  0.0, 0.0,
             1.0, -1.0,  1.0, 0.0,
             1.0,  1.0,  1.0, 1.0,
            -1.0,  1.0,  0.0, 1.0,
        ], dtype=np.float32)
        
        # Create particle VAO and VBO
        self.particle_vao = glGenVertexArrays(1)
        self.particle_vbo = glGenBuffers(1)
        self.particle_instance_vbo = glGenBuffers(1)
        
        glBindVertexArray(self.particle_vao)
        
        # Base quad VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.particle_vbo)
        glBufferData(GL_ARRAY_BUFFER, particle_vertices.nbytes, particle_vertices, GL_STATIC_DRAW)
        
        # Position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(0))
        
        # TexCoord attribute
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(2 * 4))
        
        # Instance VBO (will be updated each frame)
        glBindBuffer(GL_ARRAY_BUFFER, self.particle_instance_vbo)
        
        # Per-instance attributes
        # Particle position
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 9 * 4, ctypes.c_void_p(0))
        glVertexAttribDivisor(2, 1)
        
        # Particle size
        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, 9 * 4, ctypes.c_void_p(2 * 4))
        glVertexAttribDivisor(3, 1)
        
        # Particle color
        glEnableVertexAttribArray(4)
        glVertexAttribPointer(4, 4, GL_FLOAT, GL_FALSE, 9 * 4, ctypes.c_void_p(3 * 4))
        glVertexAttribDivisor(4, 1)
        
        # Particle alpha
        glEnableVertexAttribArray(5)
        glVertexAttribPointer(5, 1, GL_FLOAT, GL_FALSE, 9 * 4, ctypes.c_void_p(7 * 4))
        glVertexAttribDivisor(5, 1)
        
        glBindVertexArray(0)
    
    def clear_screen(self):
        """Clear the screen."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.draw_calls = 0
        self.note_batch.clear()
        self.particle_batch.clear()
    
    def present(self):
        """Swap buffers and present frame."""
        pygame.display.flip()
        self.clock.tick(self.fps_target)
        self.frame_count += 1
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        """Convert hex color to RGB tuple (0.0-1.0 range)."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    
    def draw_lane_separators(self, lane_count: int, lane_width: int, lane_margin: int, height: int):
        """Draw lane separators using immediate mode (simple lines)."""
        if self.static_layer_rendered:
            # Render from display list
            glCallList(self.static_display_list)
            return
        
        # Start recording to display list
        glNewList(self.static_display_list, GL_COMPILE_AND_EXECUTE)
        
        glLineWidth(2.0)
        glColor3f(0.5, 0.5, 0.5)
        glBegin(GL_LINES)
        for i in range(lane_count + 1):
            x = lane_margin + i * lane_width
            glVertex2f(x, 0)
            glVertex2f(x, height)
        glEnd()
        self.draw_calls += lane_count + 1
    
    def draw_hit_bar(self, bar_y: int, lane_count: int, lane_width: int, lane_margin: int,
                     lane_colors: List[str], show_timing_zones: bool, timing_windows: Dict[str, float]):
        """Draw hit bar and timing zones."""
        bar_start = lane_margin
        bar_end = lane_margin + (lane_width * lane_count)
        
        # Draw timing zones if enabled
        if show_timing_zones:
            base_speed = 600
            zone_colors = {
                'MISS': (0.33, 0.0, 0.0, 0.3),
                'BAD': (0.33, 0.2, 0.0, 0.3),
                'GOOD': (0.33, 0.33, 0.0, 0.3),
                'GREAT': (0.0, 0.33, 0.0, 0.3),
                'PERFECT': (0.0, 0.33, 0.33, 0.3)
            }
            
            if self.settings.get('colorblind_mode', False):
                zone_colors = {
                    'MISS': (0.2, 0.0, 0.0, 0.3),
                    'BAD': (0.27, 0.0, 0.27, 0.3),
                    'GOOD': (0.27, 0.13, 0.0, 0.3),
                    'GREAT': (0.27, 0.27, 0.0, 0.3),
                    'PERFECT': (0.0, 0.27, 0.27, 0.3)
                }
            
            for zone_name in ['MISS', 'BAD', 'GOOD', 'GREAT', 'PERFECT']:
                zone_height = int(timing_windows[zone_name] * base_speed)
                zone_y_start = bar_y - zone_height
                zone_y_end = bar_y + zone_height
                
                r, g, b, a = zone_colors[zone_name]
                glColor4f(r, g, b, a)
                glBegin(GL_QUADS)
                glVertex2f(bar_start, zone_y_start)
                glVertex2f(bar_end, zone_y_start)
                glVertex2f(bar_end, zone_y_end)
                glVertex2f(bar_start, zone_y_end)
                glEnd()
                self.draw_calls += 1
        
        # Draw hit bar
        glColor3f(1.0, 1.0, 1.0)
        glBegin(GL_QUADS)
        glVertex2f(bar_start, bar_y - 5)
        glVertex2f(bar_end, bar_y - 5)
        glVertex2f(bar_end, bar_y + 5)
        glVertex2f(bar_start, bar_y + 5)
        glEnd()
        
        # Draw yellow outline
        glColor3f(1.0, 1.0, 0.0)
        glLineWidth(3.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(bar_start, bar_y - 5)
        glVertex2f(bar_end, bar_y - 5)
        glVertex2f(bar_end, bar_y + 5)
        glVertex2f(bar_start, bar_y + 5)
        glEnd()
        
        # Draw lane indicators
        for i in range(lane_count):
            x = lane_margin + i * lane_width + lane_width // 2
            r, g, b = self.hex_to_rgb(lane_colors[i])
            glColor3f(r, g, b)
            glLineWidth(3.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(x - 40, bar_y - 10)
            glVertex2f(x + 40, bar_y - 10)
            glVertex2f(x + 40, bar_y + 10)
            glVertex2f(x - 40, bar_y + 10)
            glEnd()
            self.draw_calls += 1
        
        # End display list recording
        if not self.static_layer_rendered:
            glEndList()
            self.static_layer_rendered = True
    
    def draw_key_labels(self, lane_count: int, lane_width: int, lane_margin: int,
                       key_labels: List[str], lane_colors: List[str], key_is_down: Dict[int, bool]):
        """Draw key labels (would need font rendering - skip for now or use simple shapes)."""
        # Font rendering in OpenGL is complex - for now, use colored rectangles as indicators
        for i in range(lane_count):
            x = lane_margin + i * lane_width + lane_width // 2
            if key_is_down.get(i, False):
                glColor3f(0.25, 0.25, 0.25)
            else:
                r, g, b = self.hex_to_rgb(lane_colors[i])
                glColor3f(r, g, b)
            
            # Draw small rectangle as key indicator
            glBegin(GL_QUADS)
            glVertex2f(x - 20, 10)
            glVertex2f(x + 20, 10)
            glVertex2f(x + 20, 50)
            glVertex2f(x - 20, 50)
            glEnd()
            self.draw_calls += 1
    
    def draw_note(self, lane: int, y_pos: int, note_id: str, multiplier: int,
                  lane_width: int, lane_margin: int, note_width: int, note_height: int,
                  simultaneous_lanes: Optional[List[int]] = None):
        """Draw tap note using batched rendering."""
        x = lane_margin + lane * lane_width + lane_width // 2
        
        # Add to batch
        color = (1.0, 0.84, 0.0) if multiplier == 2 else (1.0, 1.0, 1.0)
        self.note_batch.append({
            'x': x,
            'y': y_pos,
            'width': note_width,
            'height': note_height,
            'color': color,
            'outline': (1.0, 0.65, 0.0) if multiplier == 2 else (0.8, 0.8, 0.8)
        })
        
        # Draw connecting lines for simultaneous notes
        if simultaneous_lanes:
            glColor3f(0.5, 0.5, 0.5)
            glLineWidth(2.0)
            glBegin(GL_LINES)
            for other_lane in simultaneous_lanes:
                if other_lane != lane:
                    other_x = lane_margin + other_lane * lane_width + lane_width // 2
                    glVertex2f(x, y_pos)
                    glVertex2f(other_x, y_pos)
            glEnd()
            self.draw_calls += len(simultaneous_lanes)
    
    def draw_slide(self, lane: int, y_start: int, y_end: int, note_id: str,
                   is_holding: bool, multiplier: int, lane_width: int, lane_margin: int,
                   note_width: int, note_height: int, bar_y: int):
        """Draw slide note."""
        x = lane_margin + lane * lane_width + lane_width // 2
        
        # Determine colors
        if multiplier == 2:
            bar_color = (1.0, 0.84, 0.0)
            hold_color = (1.0, 0.9, 0.5, 0.5)
        else:
            bar_color = (0.0, 0.87, 0.0) if is_holding else (0.0, 1.0, 0.0)
            hold_color = (0.56, 0.93, 0.56, 0.5)
        
        # Calculate display positions
        display_y_start = min(y_start, bar_y) if not is_holding else y_start
        
        # Draw hold area
        r, g, b, a = hold_color
        glColor4f(r, g, b, a)
        glBegin(GL_QUADS)
        glVertex2f(x - note_width // 2, display_y_start)
        glVertex2f(x + note_width // 2, display_y_start)
        glVertex2f(x + note_width // 2, y_end)
        glVertex2f(x - note_width // 2, y_end)
        glEnd()
        
        # Draw markers
        glColor3f(*bar_color)
        
        # Start marker
        if not is_holding and y_start < bar_y:
            glBegin(GL_QUADS)
            glVertex2f(x - note_width // 2, y_start - note_height // 2)
            glVertex2f(x + note_width // 2, y_start - note_height // 2)
            glVertex2f(x + note_width // 2, y_start + note_height // 2)
            glVertex2f(x - note_width // 2, y_start + note_height // 2)
            glEnd()
        
        # Hold marker
        if is_holding:
            glBegin(GL_QUADS)
            glVertex2f(x - note_width // 2, bar_y - note_height // 2)
            glVertex2f(x + note_width // 2, bar_y - note_height // 2)
            glVertex2f(x + note_width // 2, bar_y + note_height // 2)
            glVertex2f(x - note_width // 2, bar_y + note_height // 2)
            glEnd()
        
        # End marker
        glBegin(GL_QUADS)
        glVertex2f(x - note_width // 2, y_end - note_height // 2)
        glVertex2f(x + note_width // 2, y_end - note_height // 2)
        glVertex2f(x + note_width // 2, y_end + note_height // 2)
        glVertex2f(x - note_width // 2, y_end + note_height // 2)
        glEnd()
        
        self.draw_calls += 1
    
    def draw_particle(self, x: int, y: int, size: int, color: str, alpha: float):
        """Add particle to batch for GPU-instanced rendering."""
        r, g, b = self.hex_to_rgb(color)
        self.particle_batch.append({
            'x': x,
            'y': y,
            'size': size,
            'color': (r, g, b, 1.0),
            'alpha': alpha
        })
    
    def flush_note_batch(self):
        """Render all batched notes."""
        for note in self.note_batch:
            # Draw fill
            r, g, b = note['color']
            glColor3f(r, g, b)
            glBegin(GL_QUADS)
            glVertex2f(note['x'] - note['width'] // 2, note['y'] - note['height'] // 2)
            glVertex2f(note['x'] + note['width'] // 2, note['y'] - note['height'] // 2)
            glVertex2f(note['x'] + note['width'] // 2, note['y'] + note['height'] // 2)
            glVertex2f(note['x'] - note['width'] // 2, note['y'] + note['height'] // 2)
            glEnd()
            
            # Draw outline
            r, g, b = note['outline']
            glColor3f(r, g, b)
            glLineWidth(3.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(note['x'] - note['width'] // 2, note['y'] - note['height'] // 2)
            glVertex2f(note['x'] + note['width'] // 2, note['y'] - note['height'] // 2)
            glVertex2f(note['x'] + note['width'] // 2, note['y'] + note['height'] // 2)
            glVertex2f(note['x'] - note['width'] // 2, note['y'] + note['height'] // 2)
            glEnd()
            
            self.draw_calls += 1
    
    def flush_particle_batch(self):
        """Render all particles using GPU instancing."""
        if not self.particle_batch:
            return
        
        # Prepare instance data
        instance_data = []
        for p in self.particle_batch:
            instance_data.extend([
                p['x'], p['y'],  # position
                p['size'],  # size
                *p['color'],  # color (r, g, b, a)
                p['alpha']  # alpha
            ])
        
        instance_array = np.array(instance_data, dtype=np.float32)
        
        # Update instance VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.particle_instance_vbo)
        glBufferData(GL_ARRAY_BUFFER, instance_array.nbytes, instance_array, GL_DYNAMIC_DRAW)
        
        # Use particle shader
        glUseProgram(self.particle_shader)
        
        # Set uniforms
        proj_loc = glGetUniformLocation(self.particle_shader, "projection")
        glUniformMatrix4fv(proj_loc, 1, GL_FALSE, self.projection_matrix.flatten())
        
        circle_loc = glGetUniformLocation(self.particle_shader, "useCircle")
        glUniform1i(circle_loc, 1)
        
        # Draw instances
        glBindVertexArray(self.particle_vao)
        glDrawArraysInstanced(GL_TRIANGLE_FAN, 0, 4, len(self.particle_batch))
        glBindVertexArray(0)
        
        glUseProgram(0)
        self.draw_calls += 1
    
    def draw_text(self, text: str, x: int, y: int, color: str, font_size: int,
                  bold: bool = False, anchor: str = 'center'):
        """Draw text (using Pygame font rendering to texture)."""
        # Create font
        font = pygame.font.Font(None, font_size)
        r, g, b = [int(c * 255) for c in self.hex_to_rgb(color)]
        text_surface = font.render(text, True, (r, g, b))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        
        # Create texture
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(),
                     0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # Draw textured quad
        w, h = text_surface.get_width(), text_surface.get_height()
        if anchor == 'center':
            x -= w // 2
            y -= h // 2
        elif anchor == 'e':
            x -= w
        
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture)
        glColor3f(1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, y)
        glTexCoord2f(1, 0); glVertex2f(x + w, y)
        glTexCoord2f(1, 1); glVertex2f(x + w, y + h)
        glTexCoord2f(0, 1); glVertex2f(x, y + h)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        
        glDeleteTextures([texture])
        self.draw_calls += 1
    
    def draw_performance_metrics(self, fps: float, draw_calls: int, frame_time: float,
                                 render_time: float, update_time: float, gpu_memory_mb: float):
        """Draw performance overlay."""
        y_offset = 100
        metrics_text = [
            f"FPS: {fps:.1f} / {self.fps_target}",
            f"Frame: {frame_time:.2f}ms",
            f"Render: {render_time:.2f}ms",
            f"Update: {update_time:.2f}ms",
            f"Draws: {draw_calls}",
            f"Renderer: OpenGL (GPU)"
        ]
        
        for i, text in enumerate(metrics_text):
            self.draw_text(text, self.width - 10, y_offset + i * 20, '#FFFF00', 12, anchor='e')
    
    def get_renderer_name(self) -> str:
        """Get renderer name."""
        return "OpenGL"
    
    def handle_events(self) -> bool:
        """
        Handle Pygame events (since we're not using Tkinter).
        Returns False if should quit.
        """
        for event in pygame.event.get():
            if event.type == QUIT:
                return False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                return False
        return True
