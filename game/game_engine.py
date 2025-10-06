import pygame
from .paddle import Paddle
from .ball import Ball

WHITE = (255, 255, 255)
OVERLAY_DARK = (0, 0, 0, 180)

STATE_PLAYING = "PLAYING"
STATE_REPLAY_MENU = "REPLAY_MENU"
STATE_SERIES_INTERMISSION = "INTERMISSION"

MENU_FIRST_CHOICE = "FIRST_CHOICE"   # after the very first standalone game
MENU_POST_SERIES  = "POST_SERIES"    # after a full series ends

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

        # Series state — initially OFF. First game is standalone.
        self.series_active = False
        self.series_best = 3
        self.series_games_to_win = self._games_needed(self.series_best)
        self.series_player_wins = 0
        self.series_ai_wins = 0
        self.series_winner = None

        # Per-game scoreboard
        self.player_score = 0
        self.ai_score = 0
        self.game_winner = None           # "Player" / "AI" for the last finished game
        self.last_game_winner = None      # remembered for menus

        # Menu
        self.menu_options = ["Best of 3", "Best of 5", "Best of 7", "Exit"]
        self.menu_index = 0
        self.menu_context = MENU_FIRST_CHOICE

        # UI
        self.font = pygame.font.SysFont("Arial", 30)
        self.big_font = pygame.font.SysFont("Arial", 54)
        self.small_font = pygame.font.SysFont("Arial", 22)

        # Input state (player)
        self._move_dir = 0  # -1 up, +1 down, 0 idle

        # Game state
        self.state = STATE_PLAYING
        self.request_quit = False

        # Intermission timer (between games in an active series)
        self._intermission_start_ms = None
        self._intermission_ms = 1100  # ms

        # --- Fairer AI tuning ---
        self.ai.speed = 340      # slower than player's 420
        self._ai_deadzone = 12
        self._ai_reaction_ms = 90
        self._ai_last_update_ms = 0
        self._ai_move_dir = 0

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

    def _apply_menu_choice_start_series(self, label: str):
        """From FIRST_CHOICE menu: start a new series with selected Best-of."""
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

        self.series_games_to_win = self._games_needed(self.series_best)
        self.series_player_wins = 0
        self.series_ai_wins = 0
        self.series_winner = None
        self.series_active = True
        self.menu_context = MENU_POST_SERIES  # future menus will be post-series
        self._reset_game()  # start first series game immediately

    def _apply_menu_choice_post_series(self, label: str):
        """From POST_SERIES menu: either start another series or exit."""
        if label == "Exit":
            self.request_quit = True
            return
        # Same mapping as above
        self._apply_menu_choice_start_series(label)

    def _start_intermission(self):
        self.state = STATE_SERIES_INTERMISSION
        self._intermission_start_ms = pygame.time.get_ticks()

    def _end_series_if_needed(self) -> bool:
        if self.series_player_wins >= self.series_games_to_win:
            self.series_winner = "Player"
            return True
        if self.series_ai_wins >= self.series_games_to_win:
            self.series_winner = "AI"
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
            # Allow skipping with Enter/Space/R
            for event in events:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                    self._reset_game()
                    return
            return

        if self.state == STATE_REPLAY_MENU:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    # Hotkeys
                    if event.key == pygame.K_3:
                        choice = "Best of 3"
                    elif event.key == pygame.K_5:
                        choice = "Best of 5"
                    elif event.key == pygame.K_7:
                        choice = "Best of 7"
                    else:
                        choice = None

                    # Navigate/select
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                        choice = self.menu_options[self.menu_index]

                    if choice:
                        if self.menu_context == MENU_FIRST_CHOICE:
                            self._apply_menu_choice_start_series(choice)
                        else:
                            self._apply_menu_choice_post_series(choice)
                        return
            return

    # ---------- Update ----------
    def update(self, dt: float):
        if self.state == STATE_SERIES_INTERMISSION:
            if self._intermission_start_ms is not None:
                if pygame.time.get_ticks() - self._intermission_start_ms >= self._intermission_ms:
                    self._reset_game()
            return

        if self.state != STATE_PLAYING:
            return

        # --- Fairer AI decisions ---
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

        if self._ai_move_dir != 0:
            self.ai.move_speed(self._ai_move_dir, dt, self.height)

        # Ball & scoring (per game)
        self.ball.advance(dt, self.player, self.ai)

        if self.ball.x + self.ball.width < 0:
            self.ai_score += 1
            self.ball.reset(direction=1)
        elif self.ball.x > self.width:
            self.player_score += 1
            self.ball.reset(direction=-1)

        # Game end (points_to_win_game)
        if self.player_score >= self.points_to_win_game or self.ai_score >= self.points_to_win_game:
            self.game_winner = "Player" if self.player_score > self.ai_score else "AI"
            self.last_game_winner = self.game_winner

            if not self.series_active:
                # First standalone game just finished — prompt to start a series
                self.state = STATE_REPLAY_MENU
                self.menu_context = MENU_FIRST_CHOICE
                self.menu_index = 0
                return

            # If already in a series: tally and continue/end series
            if self.game_winner == "Player":
                self.series_player_wins += 1
            else:
                self.series_ai_wins += 1

            if self._end_series_if_needed():
                # Series winner decided -> show menu for next series or exit
                self.state = STATE_REPLAY_MENU
                self.menu_context = MENU_POST_SERIES
                self.menu_index = 0
            else:
                # Another game in the series
                self._start_intermission()

    # ---------- Render ----------
    def render(self, screen):
        # Field & entities (always draw for consistent background)
        pygame.draw.rect(screen, WHITE, self.player.rect())
        pygame.draw.rect(screen, WHITE, self.ai.rect())
        pygame.draw.ellipse(screen, WHITE, self.ball.rect())
        pygame.draw.aaline(screen, WHITE, (self.width//2, 0), (self.width//2, self.height))

        # HUD: per-game points
        player_text = self.font.render(str(self.player_score), True, WHITE)
        ai_text    = self.font.render(str(self.ai_score), True, WHITE)
        screen.blit(player_text, (self.width//4, 20))
        screen.blit(ai_text, (self.width * 3//4, 20))

        # HUD: series info (ONLY when a series is active)
        if self.series_active:
            series_label = self.small_font.render(
                f"Series: Player {self.series_player_wins} - {self.series_ai_wins} AI   (Best of {self.series_best}; First to {self.series_games_to_win})",
                True, WHITE
            )
            screen.blit(series_label, series_label.get_rect(midtop=(self.width//2, 8)))
        else:
            info = self.small_font.render("Single game (first to 5).", True, WHITE)
            screen.blit(info, info.get_rect(midtop=(self.width//2, 8)))

        # INTERMISSION overlay (between games in an active series)
        if self.state == STATE_SERIES_INTERMISSION:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill(OVERLAY_DARK)
            screen.blit(overlay, (0, 0))

            line1 = f"{self.game_winner} won the game!"
            title = self.big_font.render(line1, True, WHITE)
            screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 16)))

            sub = self.small_font.render("Next game starting... (Press Enter/Space to skip)", True, WHITE)
            screen.blit(sub, sub.get_rect(center=(self.width // 2, self.height // 2 + 36)))

        # REPLAY MENU (two contexts)
        if self.state == STATE_REPLAY_MENU:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill(OVERLAY_DARK)
            screen.blit(overlay, (0, 0))

            if self.menu_context == MENU_FIRST_CHOICE:
                # After the first standalone game
                title_text = f"{self.last_game_winner} won the first game!"
                prompt_text = "Start a series. Choose a length:"
            else:
                # After a full series ends
                title_text = f"{self.series_winner} wins the series!"
                prompt_text = "Play another series? Choose a length:"

            title = self.big_font.render(title_text, True, WHITE)
            screen.blit(title, title.get_rect(center=(self.width // 2, self.height // 2 - 120)))

            prompt = self.font.render(prompt_text, True, WHITE)
            screen.blit(prompt, prompt.get_rect(center=(self.width // 2, self.height // 2 - 60)))

            # Menu options
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