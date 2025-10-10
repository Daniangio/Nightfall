import pygame
import os
from typing import Dict

class AssetManager:
    """
    A singleton-like class to load, scale, and cache all game assets (images).
    This prevents reloading files from disk every frame.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AssetManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, base_path=os.path.join('assets', 'sprites')):
        # The __init__ will be called every time AssetManager() is invoked,
        # but the attributes are on the instance, so they are only set once.
        if not hasattr(self, 'initialized'):
            self.base_path = base_path
            self.images: Dict[str, pygame.Surface] = {}
            self.initialized = True
            print("AssetManager initialized.")

    def get_image(self, name: str, scale: tuple[int, int] = None) -> pygame.Surface:
        """
        Retrieves an image from the cache or loads it from disk.
        An optional scale can be provided. Scaled versions are also cached.
        """
        key = f"{name}_{scale}" if scale else name

        if key in self.images:
            return self.images[key]

        try:
            # Load the original image if not already loaded
            if name not in self.images:
                path = os.path.join(self.base_path, name)
                loaded_image = pygame.image.load(path).convert_alpha()
                self.images[name] = loaded_image

            # Create a scaled version if requested
            if scale:
                # Use smooth scaling for better quality with high-res sprites
                self.images[key] = pygame.transform.smoothscale(self.images[name], scale)
            elif key not in self.images:
                self.images[key] = self.images[name]

            return self.images[key]
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading image '{name}': {e}")
            # If a leveled building sprite fails (e.g., farm_2.png), try falling back to level 1
            if '_level_' in name or '_1' in name: # A bit of a heuristic
                parts = name.split('_')
                if parts[-1].split('.')[0].isdigit() and parts[-1].split('.')[0] != '1':
                    fallback_name = '_'.join(parts[:-1]) + '_1.png'
                    print(f"Attempting to fall back to '{fallback_name}'")
                    return self.get_image(fallback_name, scale)

            # Return a placeholder surface on error
            placeholder = pygame.Surface(scale if scale else (32, 32))
            placeholder.fill((255, 0, 255)) # Bright pink for easy identification
            self.images[key] = placeholder # Cache the placeholder to avoid repeated load errors
            return placeholder