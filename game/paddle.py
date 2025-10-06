import pygame

class Paddle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        # Speeds are in pixels per second
        self.speed = 420

    # Legacy per-pixel move (kept for compatibility if needed)
    def move(self, dy, screen_height):
        self.y += dy
        self.y = max(0, min(self.y, screen_height - self.height))

    # New dt-based movement
    def move_speed(self, direction: int, dt: float, screen_height: int):
        # direction: -1 up, +1 down
        self.y += direction * self.speed * dt
        self.y = max(0, min(self.y, screen_height - self.height))

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))

    def center_y(self):
        return self.y + self.height / 2.0

    def auto_track(self, ball, screen_height, dt: float):
        # Track ball center with capped speed
        target = ball.y + ball.height / 2.0
        dirn = 0
        if target < self.center_y() - 6:  # small deadzone to reduce jitter
            dirn = -1
        elif target > self.center_y() + 6:
            dirn = 1
        if dirn != 0:
            self.move_speed(dirn, dt, screen_height)
