import pygame
from .paddle import Paddle
from .ball import Ball

WHITE = (255, 255, 255)
OVERLAY_DARK = (0, 0, 0, 180)

STATE_PLAYING = "PLAYING"
STATE_GAME_OVER = "GAME_OVER"            # Series is over; show winner + replay menu
STATE_REPLAY_MENU = "REPLAY_MENU"
STATE_SERIES_INTERMISSION = "INTERMISSION"  # Between games inside a series

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

        # --- Rules ---
        # Points required to win a single game
        self.points_to_win_game = 5

        # Series settings (Best of N games) -> first to games_to_win wins the series
        self.series_best = 3
        self.series_player_wins = 0
        self.series_ai_wins = 0
        self.series_games_to_win = self._games_needed(self.series_best)

        # Per-game scoreboard
        self.player_score = 0
        self.ai_score = 0

        # Replay / Menu
        self.menu_options = ["Best of 3", "Best of 5", "Best of 7", "Exit"]
        self.menu_index = 0

        # UI
        self.font = pygame.font.SysFont("Arial", 30)
        self.big_font = pygame.font.SysFont("Arial", 54)
        self.small_font = pygame.font.SysFont("Arial", 22)

        # Input state (player)
        self._move_dir = 0  # -1 up, +1 down, 0 idle

        # Game state
        self.state = STATE_PLAYING
        self.game_winner = None   # "Player" or "AI" for a single game
        self.series_winner = None # "Player" or "AI" for the series
        self.request_quit = False

        # Timers
        self._intermission_start_ms = None
        self._intermission_ms = 1100  # time to show "Player won game X" before next game

        # --- Fairer AI tuning ---
        # Make AI less perfect: slower max speed and human-like reaction delay
        self.ai.speed = 340                # player speed is 420 in paddle.py; AI slower
        self._ai_deadzone = 12             # don't react to tiny offsets to reduce jitter
        self._ai_reaction_ms = 90          # only picks a new direction every N ms
        self._ai_last_update_ms = 0
        self._ai_move_dir = 0              # -1 up, +1 down, 0 idle

    # ---------- Helpers ----------
    def _center_paddles(self):
        self.player.y = self.height // 2 - self.paddle_height // 2
        self.ai.y = self.height // 2 - self.paddle_height // 2

    def _reset_game(self):
        """Reset scores for a single game and serve again."""
        self.player_score = 0
        self.ai_score = 0
        self.game_winner = None
        self._center_paddles()
        self.ball.reset(direction=None)
        self.state = STATE_PLAYING
        self._move_dir = 0

    def _games_needed(self, best_of: int) -> int:
        return best_of // 2 + 1

    def _apply_menu_choice(self, idx: int):
        label = self.menu_options[idx]
        if label == "Exit":
            self.request_quit = True
            return

        if "3" in label:
            self.series_best = 3
        elif "5" in label:
            self.series_best = 5
        elif "7" in label:
            self.series_best = 7
        else:
            self.series_best = 3

        # Reset the series
        self.series_player_wins = 0
        self.series_ai_wins = 0
        self.series_games_to_win = self._games_needed(self.series_best)
        self.series_winner = None
        # Start first game
        self._reset_game()

    def _start_intermission(self):
        self.state = STATE_SERIES_INTERMISSION
        self._intermission_start_ms = pygame.time.get_ticks()

    def _end_series_if_needed(self):
        if self.series_player_wins >= self.series_games_to_win:
            self.series_winner = "Player"
            self.state = STATE_GAME_OVER
            return True
        if self.series_ai_wins >= self.series_games_to_win:
            self.series_winner = "AI"
            self.state = STATE_GAME_OVER
            return True
        return False

    # ---------- Input ----------
    def handle_input(self, events, dt: float):
        # Global quit
        for event in events:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.request_quit = True

        if self.state == STATE_PLAYING:
            keys = pygame.key.get_pressed()
            move_dir = 0
            if keys[pygame.K_w]: move_dir -= 1
            if keys[pygame.K_s]: move_dir += 1
            self._move_dir = move_dir
            if self._move_dir != 0:
                self.player.move_speed(self._move_dir, dt, self.height)
            return

        if self.state == STATE_SERIES_INTERMISSION:
            # Allow skipping intermission with Enter/Space/R if you want
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                    self._reset_game()
                    return
            # Otherwise timer drives it
            return

        if self.state == STATE_GAME_OVER:
            # Immediately go to replay menu (no auto close)
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
                    # Navigate/select
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                        self._apply_menu_choice(self.menu_index); return
            return

    # ---------- Update ----------
    def update(self, dt: float):
        if self.state == STATE_SERIES_INTERMISSION:
            # Auto-continue when timer elapses
            if self._intermission_start_ms is not None:
                if pygame.time.get_ticks() - self._intermission_start_ms >= self._intermission_ms:
                    self._reset_game()
            return

        if self.state != STATE_PLAYING:
            return

        # --- Fairer AI: throttle direction decisions ---
        now = pygame.time.get_ticks()
        if (now - self._ai_last_update_ms) >= self._ai_reaction_ms:
            self._ai_last_update_ms = now
            target = self.ball.y + self.ball.height / 2.0
            ai_center = self.ai.y + self.ai.height / 2.0
            if target < ai_center - self._ai_deadzone:
                self._ai_move_dir = -1
            elif target > ai_center + self._ai_deadzone:
                self._ai_move_dir = +1
            else:
                self._ai_move_dir = 0

        # Move AI with the last chosen direction (gives that reaction feel)
        if self._ai_move_dir != 0:
            self.ai.move_speed(self._ai_move_dir, dt, self.height)

        # Ball movement (Task 1: sub-stepping/tunneling fix)
        self.ball.advance(dt, self.player, self.ai)

        # Scoring checks for a single GAME
        if self.ball.x + self.ball.width < 0:
            self.ai_score += 1
            self.ball.reset(direction=1)  # send towards player
        elif self.ball.x > self.width:
            self.player_score += 1
            self.ball.reset(direction=-1)  # send towards AI

        # Win condition for a single GAME (to points_to_win_game)
        if self.player_score >= self.points_to_win_game or self.ai_score >= self.points_to_win_game:
            self.game_winner = "Player" if self.player_score > self.ai_score else "AI"

            # Update series tallies
            if self.game_winner == "Player":
                self.series_player_wins += 1
            else:
                self.series_ai_wins += 1

            # Is the SERIES over now?
            if not self._end_series_if_needed():
                # Not over: small intermission, then next game
                self._start_intermission()

    # ---------- Render ----------
    def render(self, screen):
        # Field & entities (only draw paddles/ball during active play or intermission)
        pygame.draw.rect(screen, WHITE, self.player.rect())
        pygame.draw.rect(screen, WHITE, self.ai.rect())
        pygame.draw.ellipse(screen, WHITE, self.ball.rect())
        pygame.draw.aaline(screen, WHITE, (self.width//2, 0), (self.width//2, self.height))

        # HUD: per-game points
        player_text = self.font.render(str(self.player_score), True, WHITE)
        ai_text    = self.font.render(str(self.ai_score), True, WHITE)
        screen.blit(player_text, (self.width//4, 20))
        screen.blit(ai_text, (self.width * 3//4, 20))

        # HUD: series info
        series_label = self.small_font.render(
            f"Series: Player {self.series_player_wins} - {self.series_ai_wins} AI   (Best of {self.series_best}; First to {self.series_games_to_win})",
            True, WHITE
        )
        screen.blit(series_label, series_label.get_rect(midtop=(self.width//2, 8)))

        # INTERMISSION overlay (between games)
        if self.state == STATE_SERIES_INTERMISSION:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill(OVERLAY_DARK)
            screen.blit(overlay, (0, 0))

            line1 = f"{self.game_winner} won the game!"
            title = self.big_font.render(line1, True, WHITE)
            screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 16)))

            sub = self.small_font.render("Next game starting... (Press Enter/Space to skip)", True, WHITE)
            screen.blit(sub, sub.get_rect(center=(self.width // 2, self.height // 2 + 36)))

        # SERIES GAME OVER (series winner) leads to REPLAY MENU
        if self.state == STATE_GAME_OVER:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill(OVERLAY_DARK)
            screen.blit(overlay, (0, 0))

            line1 = f"{self.series_winner} wins the series!"
            title = self.big_font.render(line1, True, WHITE)
            screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 8)))

            sub = self.small_font.render("Opening replay options...", True, WHITE)
            screen.blit(sub, sub.get_rect(center=(self.width // 2, self.height // 2 + 40)))

        if self.state == STATE_REPLAY_MENU:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill(OVERLAY_DARK)
            screen.blit(overlay, (0, 0))

            title = self.big_font.render(f"{self.series_winner} wins the series!", True, WHITE)
            screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 120)))

            prompt = self.font.render("Play again? Choose a series length:", True, WHITE)
            screen.blit(prompt, prompt.get_rect(center=(self.width // 2, self.height // 2 - 60)))

            # Options
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