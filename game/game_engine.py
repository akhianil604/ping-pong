import pygame
from .paddle import Paddle
from .ball import Ball

WHITE = (255, 255, 255)
OVERLAY_DARK = (0, 0, 0, 180)

STATE_PLAYING = "PLAYING"
STATE_GAME_OVER = "GAME_OVER"
STATE_REPLAY_MENU = "REPLAY_MENU"

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
        self.score_limit = 5  # per-game points to win

        # Replay / Series menu state
        self.menu_options = ["Best of 3", "Best of 5", "Best of 7", "Exit"]
        self.menu_index = 0  # currently highlighted option
        self.series_best = 3  # active best-of target for future (informational)

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

        # Timers
        self._game_over_started_ms = None
        self._accept_input_delay_ms = 800   # used if we pause on game over before showing menu
        self._show_game_over_for_ms = 900   # time to show the winner before moving to replay menu

    # ---------- Helpers ----------
    def _center_paddles(self):
        self.player.y = self.height // 2 - self.paddle_height // 2
        self.ai.y = self.height // 2 - self.paddle_height // 2

    def _reset_match(self):
        """Reset a single game (not the window), keep chosen series_best just as info."""
        self.player_score = 0
        self.ai_score = 0
        self._center_paddles()
        self.ball.reset(direction=None)
        self.winner = None
        self.state = STATE_PLAYING
        self._move_dir = 0
        self._game_over_started_ms = None

    def _apply_menu_choice(self, idx: int):
        label = self.menu_options[idx]
        if label == "Exit":
            self.request_quit = True
            return

        # Map to series best-of
        if "3" in label:
            self.series_best = 3
        elif "5" in label:
            self.series_best = 5
        elif "7" in label:
            self.series_best = 7
        else:
            self.series_best = 3  # fallback

        # Start a new match (fresh game)
        self._reset_match()

    # ---------- Input ----------
    def handle_input(self, events, dt: float):
        # Global hotkeys (work in any state)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
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
            return  # nothing else to do in PLAYING

        if self.state == STATE_GAME_OVER:
            # Show winner briefly; transition to menu automatically
            now = pygame.time.get_ticks()
            if self._game_over_started_ms is None:
                self._game_over_started_ms = now
            if (now - self._game_over_started_ms) >= self._show_game_over_for_ms:
                self.state = STATE_REPLAY_MENU
            return

        if self.state == STATE_REPLAY_MENU:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    # Quick numeric shortcuts
                    if event.key == pygame.K_3:
                        self._apply_menu_choice(0); return
                    if event.key == pygame.K_5:
                        self._apply_menu_choice(1); return
                    if event.key == pygame.K_7:
                        self._apply_menu_choice(2); return

                    # Navigation
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                        self._apply_menu_choice(self.menu_index); return
                    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        # optional: left/right cycles between best-of options only
                        if self.menu_index < len(self.menu_options) - 1:
                            if event.key == pygame.K_RIGHT and self.menu_index < len(self.menu_options) - 2:
                                self.menu_index += 1
                            elif event.key == pygame.K_LEFT and self.menu_index > 0:
                                self.menu_index -= 1
            return

    # ---------- Update ----------
    def update(self, dt: float):
        if self.state != STATE_PLAYING:
            return

        # AI tracking
        self.ai.auto_track(self.ball, self.height, dt)

        # Ball movement (Task 1: sub-stepping/tunneling fix)
        self.ball.advance(dt, self.player, self.ai)

        # Scoring checks
        if self.ball.x + self.ball.width < 0:
            self.ai_score += 1
            self.ball.reset(direction=1)  # send towards player
        elif self.ball.x > self.width:
            self.player_score += 1
            self.ball.reset(direction=-1)  # send towards AI

        # Win condition for a single game
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

        # Show the active best-of target (informational)
        series_label = self.small_font.render(f"Replay target: Best of {self.series_best}", True, WHITE)
        screen.blit(series_label, series_label.get_rect(midtop=(self.width//2, 8)))

        # Game Over overlay (winner flash)
        if self.state == STATE_GAME_OVER:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill(OVERLAY_DARK)
            screen.blit(overlay, (0, 0))

            winner_line = f"{self.winner} Wins!"
            title = self.big_font.render(winner_line, True, WHITE)
            screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 8)))

            sub = self.small_font.render("Preparing replay options...", True, WHITE)
            screen.blit(sub, sub.get_rect(center=(self.width // 2, self.height // 2 + 40)))

        # Replay menu overlay
        if self.state == STATE_REPLAY_MENU:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill(OVERLAY_DARK)
            screen.blit(overlay, (0, 0))

            # Winner headline stays visible above menu
            winner_line = f"{self.winner} Wins!"
            title = self.big_font.render(winner_line, True, WHITE)
            screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 120)))

            prompt = self.font.render("Play again? Choose a series length:", True, WHITE)
            screen.blit(prompt, prompt.get_rect(center=(self.width // 2, self.height // 2 - 60)))

            # Draw options with highlight
            base_y = self.height // 2 - 10
            spacing = 36
            for i, label in enumerate(self.menu_options):
                prefix = "▶ " if i == self.menu_index else "   "
                surf = self.font.render(prefix + label, True, WHITE)
                screen.blit(surf, surf.get_rect(center=(self.width // 2, base_y + i * spacing)))

            hint1 = self.small_font.render("Use ↑/↓ or W/S to navigate; Enter/Space to select.", True, WHITE)
            hint2 = self.small_font.render("Hotkeys: 3 / 5 / 7 for best-of; Esc/Q to quit.", True, WHITE)
            screen.blit(hint1, hint1.get_rect(center=(self.width // 2, base_y + spacing * (len(self.menu_options) + 0.8))))
            screen.blit(hint2, hint2.get_rect(center=(self.width // 2, base_y + spacing * (len(self.menu_options) + 1.6))))