"""
Abstract base class for rhythm game renderers.
Defines the interface that both OpenGL and Tkinter renderers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional


class BaseRenderer(ABC):
    """Abstract renderer interface for rhythm game visualization."""
    
    def __init__(self, width: int, height: int, settings: Dict[str, Any]):
        """
        Initialize renderer.
        
        Args:
            width: Window width in pixels
            height: Window height in pixels
            settings: Game settings dictionary
        """
        self.width = width
        self.height = height
        self.settings = settings
        self.fps_target = settings.get('fps_target', 60)
        
        # Performance metrics
        self.frame_count = 0
        self.draw_calls = 0
        self.last_frame_time = 0.0
        self.render_time = 0.0
        self.update_time = 0.0
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the rendering system.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def shutdown(self):
        """Clean up resources before exit."""
        pass
    
    @abstractmethod
    def clear_screen(self):
        """Clear the screen for a new frame."""
        pass
    
    @abstractmethod
    def present(self):
        """Present the rendered frame to the screen."""
        pass
    
    @abstractmethod
    def draw_lane_separators(self, lane_count: int, lane_width: int, lane_margin: int, height: int):
        """
        Draw vertical lines separating lanes (static layer).
        
        Args:
            lane_count: Number of lanes
            lane_width: Width of each lane in pixels
            lane_margin: Left margin before first lane
            height: Screen height
        """
        pass
    
    @abstractmethod
    def draw_hit_bar(self, bar_y: int, lane_count: int, lane_width: int, lane_margin: int, 
                     lane_colors: List[str], show_timing_zones: bool, timing_windows: Dict[str, float]):
        """
        Draw the horizontal bar where notes should be hit (static layer).
        
        Args:
            bar_y: Y position of hit bar
            lane_count: Number of lanes
            lane_width: Width of each lane
            lane_margin: Left margin before first lane
            lane_colors: List of color codes for each lane
            show_timing_zones: Whether to show timing zone overlays
            timing_windows: Dictionary of timing window values
        """
        pass
    
    @abstractmethod
    def draw_key_labels(self, lane_count: int, lane_width: int, lane_margin: int,
                       key_labels: List[str], lane_colors: List[str], key_is_down: Dict[int, bool]):
        """
        Draw key labels at top of lanes (updates with key presses).
        
        Args:
            lane_count: Number of lanes
            lane_width: Width of each lane
            lane_margin: Left margin before first lane
            key_labels: List of key label strings
            lane_colors: List of color codes for each lane
            key_is_down: Dictionary tracking which keys are pressed
        """
        pass
    
    @abstractmethod
    def draw_note(self, lane: int, y_pos: int, note_id: str, multiplier: int,
                  lane_width: int, lane_margin: int, note_width: int, note_height: int,
                  simultaneous_lanes: Optional[List[int]] = None):
        """
        Draw a tap note (dynamic layer).
        
        Args:
            lane: Lane index (0-based)
            y_pos: Y position on screen
            note_id: Unique identifier for this note
            multiplier: Score multiplier (1 or 2)
            lane_width: Width of each lane
            lane_margin: Left margin before first lane
            note_width: Width of note sprite
            note_height: Height of note sprite
            simultaneous_lanes: List of lanes with simultaneous notes for connecting lines
        """
        pass
    
    @abstractmethod
    def draw_slide(self, lane: int, y_start: int, y_end: int, note_id: str,
                   is_holding: bool, multiplier: int, lane_width: int, lane_margin: int,
                   note_width: int, note_height: int, bar_y: int):
        """
        Draw a slide note (dynamic layer).
        
        Args:
            lane: Lane index (0-based)
            y_start: Start Y position
            y_end: End Y position
            note_id: Unique identifier for this slide
            is_holding: Whether the slide is currently being held
            multiplier: Score multiplier (1 or 2)
            lane_width: Width of each lane
            lane_margin: Left margin before first lane
            note_width: Width of note sprite
            note_height: Height of note sprite
            bar_y: Y position of hit bar
        """
        pass
    
    @abstractmethod
    def draw_particle(self, x: int, y: int, size: int, color: str, alpha: float):
        """
        Draw a particle effect (particle layer).
        
        Args:
            x: X position
            y: Y position
            size: Particle size
            color: Color code
            alpha: Opacity (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def draw_text(self, text: str, x: int, y: int, color: str, font_size: int,
                  bold: bool = False, anchor: str = 'center'):
        """
        Draw text on screen (UI layer).
        
        Args:
            text: Text to display
            x: X position
            y: Y position
            color: Color code
            font_size: Font size in points
            bold: Whether to use bold font
            anchor: Anchor point ('center', 'w', 'e', 'n', 's', 'nw', 'ne', 'sw', 'se')
        """
        pass
    
    @abstractmethod
    def draw_performance_metrics(self, fps: float, draw_calls: int, frame_time: float,
                                 render_time: float, update_time: float, gpu_memory_mb: float):
        """
        Draw performance metrics overlay.
        
        Args:
            fps: Current frames per second
            draw_calls: Number of draw calls in last frame
            frame_time: Total frame time in milliseconds
            render_time: Rendering time in milliseconds
            update_time: Update time in milliseconds
            gpu_memory_mb: GPU memory usage in MB (0 if not available)
        """
        pass
    
    @abstractmethod
    def get_renderer_name(self) -> str:
        """
        Get the name of this renderer.
        
        Returns:
            Renderer name (e.g., "OpenGL", "Tkinter")
        """
        pass
    
    def update_settings(self, settings: Dict[str, Any]):
        """
        Update renderer settings.
        
        Args:
            settings: New settings dictionary
        """
        self.settings = settings
        self.fps_target = settings.get('fps_target', 60)
    
    def get_metrics(self) -> Dict[str, float]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary with metrics: fps, draw_calls, frame_time, render_time, update_time
        """
        return {
            'fps': self.frame_count / max(self.last_frame_time, 0.001),
            'draw_calls': self.draw_calls,
            'frame_time': self.last_frame_time * 1000,  # Convert to ms
            'render_time': self.render_time * 1000,
            'update_time': self.update_time * 1000
        }
