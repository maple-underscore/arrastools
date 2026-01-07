"""
Object pooling system for reusable sprites and visual elements.
Reduces object creation/destruction overhead by reusing objects.
"""

from typing import List, Dict, Any, Optional, Callable


class SpritePool:
    """
    Generic object pool for reusing sprites/visual elements.
    Reduces GC pressure and improves performance by avoiding constant allocation/deallocation.
    """
    
    def __init__(self, factory: Callable[[], Any], initial_size: int = 100):
        """
        Initialize sprite pool.
        
        Args:
            factory: Function that creates new sprite objects
            initial_size: Number of sprites to pre-allocate
        """
        self.factory = factory
        self.available: List[Any] = []
        self.in_use: Dict[str, Any] = {}
        
        # Pre-allocate initial sprites
        for _ in range(initial_size):
            self.available.append(factory())
    
    def acquire(self, sprite_id: str) -> Any:
        """
        Get a sprite from the pool.
        
        Args:
            sprite_id: Unique identifier for this sprite instance
            
        Returns:
            Sprite object (reused from pool or newly created)
        """
        # Check if already in use
        if sprite_id in self.in_use:
            return self.in_use[sprite_id]
        
        # Get from available pool or create new
        if self.available:
            sprite = self.available.pop()
        else:
            sprite = self.factory()
        
        self.in_use[sprite_id] = sprite
        return sprite
    
    def release(self, sprite_id: str) -> bool:
        """
        Return a sprite to the pool.
        
        Args:
            sprite_id: Unique identifier of sprite to release
            
        Returns:
            True if sprite was released, False if not found
        """
        if sprite_id in self.in_use:
            sprite = self.in_use.pop(sprite_id)
            self.available.append(sprite)
            return True
        return False
    
    def release_all(self):
        """Return all in-use sprites to the pool."""
        while self.in_use:
            sprite_id, sprite = self.in_use.popitem()
            self.available.append(sprite)
    
    def cleanup(self):
        """Clear all sprites and reset pool."""
        self.available.clear()
        self.in_use.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get pool statistics.
        
        Returns:
            Dictionary with available count, in_use count, and total count
        """
        return {
            'available': len(self.available),
            'in_use': len(self.in_use),
            'total': len(self.available) + len(self.in_use)
        }


class NotePool:
    """Specialized pool for note sprites."""
    
    def __init__(self):
        """Initialize note pool."""
        self.tap_notes: Dict[str, Dict[str, Any]] = {}
        self.slide_notes: Dict[str, Dict[str, Any]] = {}
    
    def update_tap_note(self, note_id: str, x: int, y: int, width: int, height: int,
                       color: str, multiplier: int, visible: bool = True) -> Dict[str, Any]:
        """
        Update or create a tap note sprite.
        
        Args:
            note_id: Unique note identifier
            x: X position
            y: Y position
            width: Note width
            height: Note height
            color: Note color
            multiplier: Score multiplier
            visible: Whether note should be visible
            
        Returns:
            Dictionary with note properties
        """
        if note_id not in self.tap_notes:
            self.tap_notes[note_id] = {}
        
        note = self.tap_notes[note_id]
        note.update({
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'color': color,
            'multiplier': multiplier,
            'visible': visible
        })
        return note
    
    def update_slide_note(self, note_id: str, x: int, y_start: int, y_end: int,
                         width: int, height: int, color: str, multiplier: int,
                         is_holding: bool, visible: bool = True) -> Dict[str, Any]:
        """
        Update or create a slide note sprite.
        
        Args:
            note_id: Unique note identifier
            x: X position
            y_start: Start Y position
            y_end: End Y position
            width: Note width
            height: Note height (for markers)
            color: Note color
            multiplier: Score multiplier
            is_holding: Whether slide is being held
            visible: Whether note should be visible
            
        Returns:
            Dictionary with slide properties
        """
        if note_id not in self.slide_notes:
            self.slide_notes[note_id] = {}
        
        slide = self.slide_notes[note_id]
        slide.update({
            'x': x,
            'y_start': y_start,
            'y_end': y_end,
            'width': width,
            'height': height,
            'color': color,
            'multiplier': multiplier,
            'is_holding': is_holding,
            'visible': visible
        })
        return slide
    
    def remove_tap_note(self, note_id: str) -> bool:
        """
        Remove a tap note from the pool.
        
        Args:
            note_id: Note identifier to remove
            
        Returns:
            True if note was removed, False if not found
        """
        if note_id in self.tap_notes:
            del self.tap_notes[note_id]
            return True
        return False
    
    def remove_slide_note(self, note_id: str) -> bool:
        """
        Remove a slide note from the pool.
        
        Args:
            note_id: Slide identifier to remove
            
        Returns:
            True if slide was removed, False if not found
        """
        if note_id in self.slide_notes:
            del self.slide_notes[note_id]
            return True
        return False
    
    def clear_all(self):
        """Clear all notes from pool."""
        self.tap_notes.clear()
        self.slide_notes.clear()
    
    def get_all_tap_notes(self) -> List[Dict[str, Any]]:
        """Get list of all tap note sprites."""
        return [note for note in self.tap_notes.values() if note.get('visible', True)]
    
    def get_all_slide_notes(self) -> List[Dict[str, Any]]:
        """Get list of all slide note sprites."""
        return [slide for slide in self.slide_notes.values() if slide.get('visible', True)]


class ParticlePool:
    """Specialized pool for particle effects."""
    
    def __init__(self, max_particles: int = 1000):
        """
        Initialize particle pool.
        
        Args:
            max_particles: Maximum number of simultaneous particles
        """
        self.max_particles = max_particles
        self.particles: List[Dict[str, Any]] = []
    
    def add_particle(self, x: int, y: int, initial_size: int, color: str,
                    lifetime: float, spawn_time: float):
        """
        Add a new particle effect.
        
        Args:
            x: X position
            y: Y position
            initial_size: Initial particle size
            color: Particle color
            lifetime: Particle lifetime in seconds
            spawn_time: Time when particle was spawned
        """
        # Remove oldest particle if at capacity
        if len(self.particles) >= self.max_particles:
            self.particles.pop(0)
        
        self.particles.append({
            'x': x,
            'y': y,
            'initial_size': initial_size,
            'color': color,
            'lifetime': lifetime,
            'spawn_time': spawn_time,
            'end_time': spawn_time + lifetime
        })
    
    def update_particles(self, current_time: float) -> List[Dict[str, Any]]:
        """
        Update particles and remove expired ones.
        
        Args:
            current_time: Current game time
            
        Returns:
            List of active particles with calculated progress and alpha
        """
        # Remove expired particles
        self.particles = [p for p in self.particles if current_time < p['end_time']]
        
        # Calculate progress and alpha for each particle
        active_particles = []
        for particle in self.particles:
            progress = (current_time - particle['spawn_time']) / particle['lifetime']
            alpha = 1.0 - progress  # Fade out over lifetime
            size = particle['initial_size'] + int(60 * progress)  # Expand over time
            
            active_particles.append({
                **particle,
                'size': size,
                'alpha': alpha,
                'progress': progress
            })
        
        return active_particles
    
    def clear_all(self):
        """Remove all particles."""
        self.particles.clear()
    
    def get_count(self) -> int:
        """Get current number of active particles."""
        return len(self.particles)
