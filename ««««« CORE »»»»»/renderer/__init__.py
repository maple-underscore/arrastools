"""
Renderer module for the rhythm game.
Provides abstract renderer interface and implementations for GPU (OpenGL) and CPU (Tkinter) rendering.
"""

from .base_renderer import BaseRenderer
from .sprite_pool import SpritePool

__all__ = ['BaseRenderer', 'SpritePool']
