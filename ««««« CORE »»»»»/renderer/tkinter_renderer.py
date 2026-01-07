"""
Tkinter-based renderer (CPU-side rendering with optimizations).
Serves as fallback when OpenGL is unavailable.
Implements object pooling and selective redraws to improve performance.
"""

import tkinter as tk
from typing import List, Dict, Any, Optional
import time
from PIL import Image, ImageTk

from .base_renderer import BaseRenderer
from .sprite_pool import NotePool, ParticlePool


class TkinterRenderer(BaseRenderer):
    """CPU-based Tkinter renderer with optimizations."""
    
    def __init__(self, width: int, height: int, settings: Dict[str, Any], root: tk.Tk, canvas: tk.Canvas):
        """
        Initialize Tkinter renderer.
        
        Args:
            width: Window width
            height: Window height
            settings: Game settings
            root: Tkinter root window
            canvas: Tkinter canvas widget
        """
        super().__init__(width, height, settings)
        self.root = root
        self.canvas = canvas
        
        # Object pools
        self.note_pool = NotePool()
        self.particle_pool = ParticlePool(max_particles=1000)
        
        # Static element cache (render once, reuse)
        self.static_elements_rendered = False
        self.last_ui_values = {}  # Track UI values to avoid redundant redraws
        
        # Image cache for slide transparency
        self.slide_images = {}
        
        # Performance tracking
        self.last_fps_update = time.time()
        self.frame_times = []
    
    def initialize(self) -> bool:
        """Initialize Tkinter renderer."""
        try:
            # Configure canvas
            self.canvas.configure(bg='black', highlightthickness=0)
            return True
        except Exception as e:
            print(f"Failed to initialize Tkinter renderer: {e}")
            return False
    
    def shutdown(self):
        """Clean up resources."""
        self.note_pool.clear_all()
        self.particle_pool.clear_all()
        self.slide_images.clear()
    
    def clear_screen(self):
        """Clear dynamic elements only (not static elements)."""
        # Only delete dynamic tags
        self.canvas.delete('note')
        self.canvas.delete('particle')
        # UI will be selectively updated
        self.draw_calls = 0
    
    def present(self):
        """Present frame (Tkinter updates automatically)."""
        self.root.update()
        self.frame_count += 1
    
    def draw_lane_separators(self, lane_count: int, lane_width: int, lane_margin: int, height: int):
        """Draw vertical lane separator lines (static - cached)."""
        if self.static_elements_rendered:
            return  # Already drawn
        
        for i in range(lane_count + 1):
            x = lane_margin + i * lane_width
            self.canvas.create_line(x, 0, x, height, fill='gray', width=2, tags='static')
            self.draw_calls += 1
    
    def draw_hit_bar(self, bar_y: int, lane_count: int, lane_width: int, lane_margin: int,
                     lane_colors: List[str], show_timing_zones: bool, timing_windows: Dict[str, float]):
        """Draw hit bar (static - cached, except timing zones)."""
        # Always redraw if timing zones are enabled (they might change)
        if not show_timing_zones and self.static_elements_rendered:
            return
        
        # Delete old hit bar if redrawing
        if show_timing_zones:
            self.canvas.delete('timing_zone')
        
        bar_start = lane_margin
        bar_end = lane_margin + (lane_width * lane_count)
        
        # Draw timing zones if enabled
        if show_timing_zones:
            base_speed = 600
            zone_colors = {
                'MISS': '#550000',
                'BAD': '#553300',
                'GOOD': '#555500',
                'GREAT': '#005500',
                'PERFECT': '#005555'
            }
            
            if self.settings.get('colorblind_mode', False):
                zone_colors = {
                    'MISS': '#330000',
                    'BAD': '#440044',
                    'GOOD': '#442200',
                    'GREAT': '#444400',
                    'PERFECT': '#004444'
                }
            
            for zone_name in ['MISS', 'BAD', 'GOOD', 'GREAT', 'PERFECT']:
                zone_height = int(timing_windows[zone_name] * base_speed)
                zone_y_start = bar_y - zone_height
                zone_y_end = bar_y + zone_height
                
                self.canvas.create_rectangle(bar_start, zone_y_start, bar_end, zone_y_end,
                                            fill=zone_colors[zone_name], outline='',
                                            tags='timing_zone', stipple='gray25')
                self.draw_calls += 1
        
        # Draw hit bar
        if not self.static_elements_rendered:
            self.canvas.create_rectangle(bar_start, bar_y - 5, bar_end, bar_y + 5,
                                        fill='white', outline='yellow', width=3, tags='static')
            
            # Draw lane indicators
            for i in range(lane_count):
                x = lane_margin + i * lane_width + lane_width // 2
                self.canvas.create_rectangle(x - 40, bar_y - 10, x + 40, bar_y + 10,
                                            outline=lane_colors[i], width=3, tags='static')
                self.draw_calls += 2
        
        if not show_timing_zones:
            self.static_elements_rendered = True
    
    def draw_key_labels(self, lane_count: int, lane_width: int, lane_margin: int,
                       key_labels: List[str], lane_colors: List[str], key_is_down: Dict[int, bool]):
        """Draw key labels (dynamic - updates with key presses)."""
        self.canvas.delete('keylabel')
        
        for i in range(lane_count):
            x = lane_margin + i * lane_width + lane_width // 2
            color = '#404040' if key_is_down.get(i, False) else lane_colors[i]
            self.canvas.create_text(x, 30, text=key_labels[i],
                                  fill=color, font=('Arial', 36, 'bold'), tags='keylabel')
            self.draw_calls += 1
    
    def draw_note(self, lane: int, y_pos: int, note_id: str, multiplier: int,
                  lane_width: int, lane_margin: int, note_width: int, note_height: int,
                  simultaneous_lanes: Optional[List[int]] = None):
        """Draw tap note using object pooling and canvas.coords optimization."""
        x = lane_margin + lane * lane_width + lane_width // 2
        
        # Update note pool
        self.note_pool.update_tap_note(
            note_id, x, y_pos, note_width, note_height,
            '#FFD700' if multiplier == 2 else 'white',
            multiplier, True
        )
        
        # Draw connecting lines for simultaneous notes
        if simultaneous_lanes:
            for other_lane in simultaneous_lanes:
                if other_lane != lane:
                    other_x = lane_margin + other_lane * lane_width + lane_width // 2
                    self.canvas.create_line(x, y_pos, other_x, y_pos,
                                          fill='gray', width=2, tags=f'note_{note_id}')
                    self.draw_calls += 1
        
        # Draw note rectangle
        color = '#FFD700' if multiplier == 2 else 'white'
        outline_color = '#FFA500' if multiplier == 2 else '#CCCCCC'
        
        self.canvas.create_rectangle(
            x - note_width // 2, y_pos - note_height // 2,
            x + note_width // 2, y_pos + note_height // 2,
            fill=color, outline=outline_color, width=3, tags=f'note_{note_id}'
        )
        self.draw_calls += 1
    
    def draw_slide(self, lane: int, y_start: int, y_end: int, note_id: str,
                   is_holding: bool, multiplier: int, lane_width: int, lane_margin: int,
                   note_width: int, note_height: int, bar_y: int):
        """Draw slide note using object pooling and optimized rendering."""
        x = lane_margin + lane * lane_width + lane_width // 2
        
        # Update slide pool
        self.note_pool.update_slide_note(
            note_id, x, y_start, y_end, note_width, note_height,
            '#FFD700' if multiplier == 2 else '#00FF00',
            multiplier, is_holding, True
        )
        
        # Determine colors
        if multiplier == 2:
            bar_color = '#FFD700'
            hold_rgb = (255, 230, 128)
            outline_color = '#FFA500'
        else:
            bar_color = '#00DD00' if is_holding else '#00FF00'
            hold_rgb = (144, 238, 144)
            outline_color = '#00CC00'
        
        # Calculate display positions
        display_y_start = min(y_start, bar_y) if not is_holding else y_start
        
        # Draw hold area with semi-transparency
        rect_width = note_width
        if y_end < display_y_start:
            rect_height = int(display_y_start - y_end)
            rect_y = int(y_end)
        else:
            rect_height = int(y_end - display_y_start)
            rect_y = int(display_y_start)
        
        if rect_height > 0 and rect_width > 0:
            # Create semi-transparent image
            img = Image.new('RGBA', (rect_width, rect_height), (*hold_rgb, 128))
            photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(x, rect_y + rect_height // 2, image=photo, tags=f'note_{note_id}')
            self.slide_images[note_id] = photo  # Keep reference
            self.draw_calls += 1
        
        # Draw start marker
        if not is_holding and y_start < bar_y:
            self.canvas.create_rectangle(
                x - note_width // 2, y_start - note_height // 2,
                x + note_width // 2, y_start + note_height // 2,
                fill=bar_color, outline=outline_color, width=3, tags=f'note_{note_id}'
            )
            self.draw_calls += 1
        
        # Draw hold marker if holding
        if is_holding:
            self.canvas.create_rectangle(
                x - note_width // 2, int(bar_y) - note_height // 2,
                x + note_width // 2, int(bar_y) + note_height // 2,
                fill=bar_color, outline=outline_color, width=3, tags=f'note_{note_id}'
            )
            self.draw_calls += 1
        
        # Draw end marker
        self.canvas.create_rectangle(
            x - note_width // 2, y_end - note_height // 2,
            x + note_width // 2, y_end + note_height // 2,
            fill=bar_color, outline=outline_color, width=3, tags=f'note_{note_id}'
        )
        self.draw_calls += 1
    
    def draw_particle(self, x: int, y: int, size: int, color: str, alpha: float):
        """Draw particle with alpha simulation using stipple patterns."""
        # Map alpha to stipple pattern
        if alpha >= 0.75:
            stipple = ''
        elif alpha >= 0.5:
            stipple = 'gray75'
        elif alpha >= 0.25:
            stipple = 'gray50'
        else:
            stipple = 'gray25'
        
        if stipple:
            self.canvas.create_oval(
                x - size, y - size, x + size, y + size,
                outline=color, width=2, fill='', stipple=stipple, tags='particle'
            )
        else:
            self.canvas.create_oval(
                x - size, y - size, x + size, y + size,
                outline=color, width=2, fill='', tags='particle'
            )
        self.draw_calls += 1
    
    def draw_text(self, text: str, x: int, y: int, color: str, font_size: int,
                  bold: bool = False, anchor: str = 'center'):
        """Draw text on screen with selective updates."""
        # Check if this text has changed
        text_key = f"{x}_{y}_{anchor}"
        if text_key in self.last_ui_values and self.last_ui_values[text_key] == text:
            return  # No change, skip redraw
        
        # Update cache
        self.last_ui_values[text_key] = text
        
        # Delete old text at this position
        self.canvas.delete(f'text_{text_key}')
        
        # Draw new text
        font_style = ('Arial', font_size, 'bold' if bold else 'normal')
        self.canvas.create_text(
            x, y, text=text, fill=color, font=font_style,
            anchor=anchor, tags=f'text_{text_key}'
        )
        self.draw_calls += 1
    
    def draw_performance_metrics(self, fps: float, draw_calls: int, frame_time: float,
                                 render_time: float, update_time: float, gpu_memory_mb: float):
        """Draw performance overlay."""
        self.canvas.delete('perf_metrics')
        
        y_offset = 100
        metrics_text = [
            f"FPS: {fps:.1f} / {self.fps_target}",
            f"Frame: {frame_time:.2f}ms",
            f"Render: {render_time:.2f}ms",
            f"Update: {update_time:.2f}ms",
            f"Draws: {draw_calls}",
            f"Renderer: Tkinter (CPU)"
        ]
        
        for i, text in enumerate(metrics_text):
            self.canvas.create_text(
                self.width - 10, y_offset + i * 20,
                text=text, fill='yellow', font=('Arial', 12),
                anchor='e', tags='perf_metrics'
            )
            self.draw_calls += 1
    
    def get_renderer_name(self) -> str:
        """Get renderer name."""
        return "Tkinter"
    
    def reset_static_cache(self):
        """Force re-render of static elements."""
        self.static_elements_rendered = False
        self.canvas.delete('static')
