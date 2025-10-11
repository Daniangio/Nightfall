import logging
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

    def _load_with_fallback(self, name: str) -> pygame.Surface | None:
        """
        Attempts to load an image by name. If it fails, it tries a series of fallbacks
        for leveled assets (e.g., building_farm_3.png -> ... -> building_farm_1.png -> building_farm.png).
        """
        # If already cached, return it.
        if name in self.images:
            return self.images[name]

        # Try to load the file from disk.
        try:
            path = os.path.join(self.base_path, name)
            loaded_image = pygame.image.load(path).convert_alpha()
            self.images[name] = loaded_image # Cache the successful load
            return loaded_image
        except (pygame.error, FileNotFoundError):
            # If loading fails, attempt fallback logic.
            parts = name.split('_')
            
            # Check if the last part is a level number (e.g., "farm_3.png")
            if len(parts) > 1 and '.' in parts[-1]:
                level_str, extension = parts[-1].split('.', 1)
                if level_str.isdigit():
                    level = int(level_str)
                    if level > 0:
                        # Fallback to the next lower level.
                        fallback_name = f"{'_'.join(parts[:-1])}_{level - 1}.{extension}"
                        return self._load_with_fallback(fallback_name)
                    elif level == 0:
                        # Fallback from level 1 to the base name (e.g., "building_farm.png")
                        base_name = f"{'_'.join(parts[:-1])}.{extension}"
                        return self._load_with_fallback(base_name)

            # If no more fallbacks are possible, return None.
            print(f"All fallbacks failed for '{name}'.")
            return None

    def get_image(self, name: str, scale: tuple[int, int] = None) -> pygame.Surface:
        """
        Retrieves an image from the cache or loads it from disk.
        An optional scale can be provided. Scaled versions are also cached.
        """
        key = f"{name}_{scale}" if scale else name

        if key in self.images:
            return self.images[key]

        # Use the new fallback loader to get the original image.
        original_image = self._load_with_fallback(name)

        if original_image:
            # If we have an image, scale it if necessary.
            if scale:
                scaled_image = pygame.transform.smoothscale(original_image, scale)
                self.images[key] = scaled_image # Cache the scaled version
                return scaled_image
            else:
                # If no scale, the image is already cached by _load_with_fallback.
                return original_image
        else:
            # If all fallbacks failed, create and cache a placeholder.
            # Return a placeholder surface on error
            placeholder = pygame.Surface(scale if scale else (32, 32))
            placeholder.fill((255, 0, 255)) # Bright pink for easy identification
            self.images[key] = placeholder # Cache the placeholder to avoid repeated load errors
            return placeholder