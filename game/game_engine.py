import pygame
from .paddle import Paddle
from .ball import Ball

WHITE = (255, 255, 255)
OVERLAY_DARK = (0, 0, 0, 180)

STATE_PLAYING = "PLAYING"
STATE_GAME_OVER = "GAME_OVER"

class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.paddle_width = 10
        self.paddle_height = 100

        # Entities
        self.player = Paddle(10, height // 2 - 50, self.paddle_width, self.paddle_height)
        self.ai = Paddle(width - 20, height // 2 - 50, self.paddle_width, self.paddle_height)
        self.ball = Ball(width // 2, height // 2, 10, 10, width, height)

        # Scores & rules
        self.player_score = 0
        self.ai_score = 0
        self.score_limit = 5

        # UI
        self.font = pygame.font.SysFont("Arial", 30)
        self.big_font = pygame.font.SysFont("Arial", 54)
        self.small_font = pygame.font.SysFont("Arial", 22)

        # Input state (for playing state)
        self._move_dir = 0  # -1 up, +1 down, 0 idle

        # Game state
        self.state = STATE_PLAYING
        self.winner = None  # "Player" or "AI"
        self.request_quit = False

        # Timers (for game over)
        self._game_over_started_ms = None
        self._accept_input_delay_ms = 800     # wait before accepting restart/quit
        self._auto_quit_after_ms = 8000       # auto-close if no input

    # ---------- Helpers ----------
    def _center_paddles(self):
        self.player.y = self.height // 2 - self.paddle_height // 2
        self.ai.y = self.height // 2 - self.paddle_height // 2

    def _reset_match(self):
        self.player_score = 0
        self.ai_score = 0
        self._center_paddles()
        self.ball.reset(direction=None)
        self.winner = None
        self.state = STATE_PLAYING
        self._move_dir = 0
        self._game_over_started_ms = None

    # ---------- Input ----------
    def handle_input(self, events, dt: float):
        # Global hotkeys (work in any state)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    # Quit from anywhere
                    self.request_quit = True

        if self.state == STATE_PLAYING:
            # Smooth player movement
            keys = pygame.key.get_pressed()
            move_dir = 0
            if keys[pygame.K_w]:
                move_dir -= 1
            if keys[pygame.K_s]:
                move_dir += 1
            self._move_dir = move_dir

            if self._move_dir != 0:
                self.player.move_speed(self._move_dir, dt, self.height)

        elif self.state == STATE_GAME_OVER:
            # After short delay, accept input for restart or quit
            now = pygame.time.get_ticks()
            if self._game_over_started_ms is None:
                self._game_over_started_ms = now

            can_accept = (now - self._game_over_started_ms) >= self._accept_input_delay_ms

            if can_accept:
                for event in events:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:
                            # Restart the whole match
                            self._reset_match()
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                            # Also restart for convenience
                            self._reset_match()
                        elif event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                            self.request_quit = True

            # Auto-quit after a while if no input
            if (now - self._game_over_started_ms) >= self._auto_quit_after_ms:
                self.request_quit = True

    # ---------- Update ----------
    def update(self, dt: float):
        if self.state != STATE_PLAYING:
            return

        # AI tracking
        self.ai.auto_track(self.ball, self.height, dt)

        # Ball movement (with substepping/tunneling fix from Task 1)
        self.ball.advance(dt, self.player, self.ai)

        # Scoring checks
        if self.ball.x + self.ball.width < 0:
            self.ai_score += 1
            self.ball.reset(direction=1)  # send towards player
        elif self.ball.x > self.width:
            self.player_score += 1
            self.ball.reset(direction=-1)  # send towards AI

        # Win condition
        if self.player_score >= self.score_limit or self.ai_score >= self.score_limit:
            self.state = STATE_GAME_OVER
            self.winner = "Player" if self.player_score > self.ai_score else "AI"
            self._game_over_started_ms = pygame.time.get_ticks()

    # ---------- Render ----------
    def render(self, screen):
        # Field & entities
        pygame.draw.rect(screen, WHITE, self.player.rect())
        pygame.draw.rect(screen, WHITE, self.ai.rect())
        pygame.draw.ellipse(screen, WHITE, self.ball.rect())
        pygame.draw.aaline(screen, WHITE, (self.width//2, 0), (self.width//2, self.height))

        # HUD: scores
        player_text = self.font.render(str(self.player_score), True, WHITE)
        ai_text = self.font.render(str(self.ai_score), True, WHITE)
        screen.blit(player_text, (self.width//4, 20))
        screen.blit(ai_text, (self.width * 3//4, 20))

        # Game Over overlay
        if self.state == STATE_GAME_OVER:
            # Semi-transparent overlay
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill(OVERLAY_DARK)
            screen.blit(overlay, (0, 0))

            # Winner banner
            winner_line = f"{self.winner} Wins!"
            title = self.big_font.render(winner_line, True, WHITE)
            title_rect = title.get_rect(center=(self.width // 2, self.height // 2 - 20))
            screen.blit(title, title_rect)

            # Instructions
            sub1 = self.small_font.render("Press R / Enter / Space to Restart", True, WHITE)
            sub2 = self.small_font.render("Press Esc / Q to Quit", True, WHITE)
            screen.blit(sub1, sub1.get_rect(center=(self.width // 2, self.height // 2 + 30)))
            screen.blit(sub2, sub2.get_rect(center=(self.width // 2, self.height // 2 + 56)))
