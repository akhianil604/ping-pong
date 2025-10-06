import pygame
from game.game_engine import GameEngine

# Initialize pygame/Start application
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ping Pong - Pygame Version")

# Colors
BLACK = (0, 0, 0)

# Clock
clock = pygame.time.Clock()
FPS = 60

# Game loop
engine = GameEngine(WIDTH, HEIGHT)

def main():
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # seconds since last frame
        events = pygame.event.get()

        # Window close
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        # Handle input & update game state
        engine.handle_input(events, dt)
        engine.update(dt)

        # Render
        SCREEN.fill(BLACK)
        engine.render(SCREEN)
        pygame.display.flip()

        # Allow engine to request quit (e.g., from Game Over screen)
        if engine.request_quit:
            running = False

    pygame.quit()

if __name__ == "__main__":
    main()
