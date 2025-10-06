import pygame
from .paddle import Paddle
from .ball import Ball

WHITE = (255, 255, 255)

class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.paddle_width = 10
        self.paddle_height = 100

        # Paddles: left (player) and right (AI)
        self.player = Paddle(10, height // 2 - 50, self.paddle_width, self.paddle_height)
        self.ai = Paddle(width - 20, height // 2 - 50, self.paddle_width, self.paddle_height)

        # Ball uses px/sec velocities internally; width/height here are the sprite size
        self.ball = Ball(width // 2, height // 2, 10, 10, width, height)

        self.player_score = 0
        self.ai_score = 0
        self.font = pygame.font.SysFont("Arial", 30)

        # Input state
        self._move_dir = 0  # -1 up, +1 down, 0 idle

    def handle_input(self, dt: float):
        keys = pygame.key.get_pressed()
        move_dir = 0
        if keys[pygame.K_w]:
            move_dir -= 1
        if keys[pygame.K_s]:
            move_dir += 1
        self._move_dir = move_dir

        # Apply player movement w.r.t dt
        if self._move_dir != 0:
            self.player.move_speed(self._move_dir, dt, self.height)

    def update(self, dt: float):
        # AI tracks the ball with dt-based speed
        self.ai.auto_track(self.ball, self.height, dt)

        # Move ball with sub-stepped integration to avoid tunneling
        self.ball.advance(dt, self.player, self.ai)

        # Scoring
        if self.ball.x + self.ball.width < 0:
            self.ai_score += 1
            self.ball.reset(direction=1)  # send towards player
        elif self.ball.x > self.width:
            self.player_score += 1
            self.ball.reset(direction=-1)  # send towards AI

    def render(self, screen):
        # Draw paddles and ball
        pygame.draw.rect(screen, WHITE, self.player.rect())
        pygame.draw.rect(screen, WHITE, self.ai.rect())
        pygame.draw.ellipse(screen, WHITE, self.ball.rect())
        pygame.draw.aaline(screen, WHITE, (self.width//2, 0), (self.width//2, self.height))

        # Draw score
        player_text = self.font.render(str(self.player_score), True, WHITE)
        ai_text = self.font.render(str(self.ai_score), True, WHITE)
        screen.blit(player_text, (self.width//4, 20))
        screen.blit(ai_text, (self.width * 3//4, 20))
