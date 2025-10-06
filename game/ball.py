import pygame
import random
import math

class Ball:
    def __init__(self, x, y, width, height, screen_width, screen_height):
        self.spawn_x = x
        self.spawn_y = y
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Velocities in pixels/sec
        self.base_speed = 360.0
        self.max_speed = 840.0
        self.speed_increase = 1.06  # on paddle hit
        self._set_initial_velocity()

    def _set_initial_velocity(self, direction=None):
        # Start with a mostly-horizontal vector
        angle = random.uniform(-0.35, 0.35)  # ~±20°
        vx = self.base_speed * math.copysign(1, random.choice([-1, 1])) * math.cos(angle)
        vy = self.base_speed * math.sin(angle)
        if direction is not None:
            vx = abs(vx) * direction
        self.vx = vx
        self.vy = vy

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))

    def center_y(self):
        return self.y + self.height / 2.0

    def _wall_bounce(self):
        if self.y <= 0:
            self.y = 0
            self.vy = -self.vy
        elif self.y + self.height >= self.screen_height:
            self.y = self.screen_height - self.height
            self.vy = -self.vy

    def _paddle_bounce(self, paddle):
        # Determine which side we hit based on incoming direction
        incoming_right = self.vx > 0

        # Place ball flush outside the paddle with a small epsilon to avoid re-collisions
        if incoming_right:
            # hit right paddle
            self.x = paddle.x - self.width - 1  # 1px epsilon
            out_dir = -1  # move left after bounce
        else:
            # hit left paddle
            self.x = paddle.x + paddle.width + 1
            out_dir = +1  # move right after bounce

        # Deflection based on where we hit relative to paddle center
        paddle_center = paddle.center_y()
        rel = (self.center_y() - paddle_center) / (paddle.height / 2.0)  # [-1, 1]
        rel = max(-1.0, min(1.0, rel))

        max_angle = math.radians(45)  # up to ±45°
        angle = rel * max_angle

        # Increase speed slightly per paddle hit, clamp to max
        speed = min(self.speed() * self.speed_increase, self.max_speed)

        # Set velocities so the ball moves AWAY from the paddle
        self.vx = out_dir * speed * math.cos(angle)
        self.vy = speed * math.sin(angle)

        # Nudge tiny vertical if nearly flat to avoid boring straight lines
        if abs(self.vy) < 60:
            self.vy = math.copysign(60, self.vy if self.vy != 0 else (rel or 1))


    def speed(self):
        return math.hypot(self.vx, self.vy)

    def advance(self, dt: float, player, ai):
        # Substep integration to avoid tunneling
        # move in <= 4px micro-steps
        max_comp = max(abs(self.vx), abs(self.vy))
        steps = max(1, int((max_comp * dt) / 4.0))
        step_dt = dt / steps

        for _ in range(steps):
            # Move
            self.x += self.vx * step_dt
            self.y += self.vy * step_dt

            # Walls
            self._wall_bounce()

            # Paddles
            b = self.rect()
            if b.colliderect(player.rect()) and self.vx < 0:
                self._paddle_bounce(player)
            elif b.colliderect(ai.rect()) and self.vx > 0:
                self._paddle_bounce(ai)

    def reset(self, direction=None):
        self.x = float(self.spawn_x - self.width / 2.0)
        self.y = float(self.spawn_y - self.height / 2.0)
        self._set_initial_velocity(direction=direction)
