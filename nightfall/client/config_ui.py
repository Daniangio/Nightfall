import pygame

# --- Fonts ---
pygame.font.init()
FONT_S = pygame.font.Font(None, 18)
FONT_M = pygame.font.Font(None, 24)
FONT_XS = pygame.font.Font(None, 14)

# --- Colors ---
C_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)
C_RED = (200, 0, 0)
C_RED_HOVER = (160, 0, 0)
C_GREEN = (0, 200, 0)
C_BLUE = (65, 105, 225)
C_DARK_BLUE = (45, 85, 205)
C_YELLOW = (255, 215, 0)
C_GOLD = (255, 215, 0)
C_GRAY = (50, 50, 50)
C_DARK_GRAY = (30, 30, 30)
C_LIGHT_GRAY = (150, 150, 150)
C_CYAN = (0, 255, 255)

WORLD_TERRAIN_COLORS = {
    'PLAINS': (152, 251, 152),
    'FOREST': (34, 139, 34),
    'MOUNTAIN': (139, 137, 137),
    'LAKE': C_BLUE
}

# --- Tile Dimensions ---
TILE_WIDTH = 60       # Base width of a city tile
TILE_HEIGHT = 50      # Base height of a city tile (1.2:1 ratio)
WORLD_TILE_SIZE = 30

# --- UI Layout ---
TOP_BAR_HEIGHT = 35
SPLITTER_WIDTH = 6
QUEUE_SPACING = 10  # The total gap between the two queue panels

# --- Zoom ---
MIN_ZOOM = 0.5
MAX_ZOOM = 2.0
ZOOM_INCREMENT = 0.1