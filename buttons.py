import math
from collections.abc import Callable
from typing import Optional

import pygame


# ============================================================
# EASING FUNCTIONS
# ============================================================

def linear(t: float) -> float:
    return t


def ease_in(t: float) -> float:
    """Starts slowly and speeds up."""
    return t * t


def ease_out(t: float) -> float:
    """Starts quickly and slows down."""
    return 1.0 - (1.0 - t) ** 2


def ease_in_out(t: float) -> float:
    """Starts slowly, speeds up, then slows down."""
    if t < 0.5:
        return 2.0 * t * t

    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


def ease_in_cubic(t: float) -> float:
    return t ** 3


def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4.0 * t ** 3

    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


def ease_out_back(t: float) -> float:
    """Moves slightly past the target, then settles back."""
    overshoot = 1.70158
    shifted_t = t - 1.0

    return (
        1.0
        + (overshoot + 1.0) * shifted_t ** 3
        + overshoot * shifted_t ** 2
    )


def ease_in_back(t: float) -> float:
    """Moves slightly backward before moving forward."""
    overshoot = 1.70158

    return (
        (overshoot + 1.0) * t ** 3
        - overshoot * t ** 2
    )


def ease_out_bounce(t: float) -> float:
    """Bounces when reaching the target."""
    n1 = 7.5625
    d1 = 2.75

    if t < 1.0 / d1:
        return n1 * t * t

    if t < 2.0 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75

    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375

    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def ease_out_elastic(t: float) -> float:
    """Spring-like movement around the target."""
    if t == 0.0:
        return 0.0

    if t == 1.0:
        return 1.0

    constant = (2.0 * math.pi) / 3.0

    return (
        2.0 ** (-10.0 * t)
        * math.sin((t * 10.0 - 0.75) * constant)
        + 1.0
    )


EASING_TYPES: dict[str, Callable[[float], float]] = {
    "linear": linear,

    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,

    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,

    "back": ease_out_back,
    "ease_out_back": ease_out_back,
    "ease_in_back": ease_in_back,

    "bounce": ease_out_bounce,
    "ease_out_bounce": ease_out_bounce,

    "elastic": ease_out_elastic,
    "ease_out_elastic": ease_out_elastic,
}


# ============================================================
# BUTTON
# ============================================================

class Button:
    def __init__(
        self,
        position,
        size,
        direction,
        texture,
        onclick,
        update_visual=None,
        name=""
    ):
        # The displayed position.
        self._pos = pygame.Vector2(position)

        # Where the current animation began.
        self.start_pos = pygame.Vector2(position)

        # Where the button is moving.
        self.target_pos = pygame.Vector2(position)

        if isinstance(size, (int, float)):
            self.w = float(size)
            self.h = float(size)
        else:
            self.w = float(size[0])
            self.h = float(size[1])

        self.dir = direction
        self.image = texture
        self.onclick = onclick
        self.update_visual = update_visual
        self.name = name

        # Your main script assigns these after creating buttons.
        self.type = None

        # Animation settings.
        self.move_duration = 0.30
        self.move_elapsed = self.move_duration
        self.lerp_type = "ease_out"

        self.animating = False

        # Used to calculate dt automatically inside draw().
        self._last_update_ms = pygame.time.get_ticks()

        # Optional visual settings.
        self.hover_scale = 1.0
        self.draw_hover_outline = False
        self.hover_outline_color = (255, 255, 255)
        self.hover_outline_width = 2

        self.alpha = 160
        self.hover_alpha = 255

    # ========================================================
    # POSITION
    # ========================================================

    @property
    def pos(self) -> pygame.Vector2:
        """
        Current displayed position.

        Reading:
            x = button.pos[0]

        Assigning:
            button.pos = (300, 200)

        Assignment starts an animation instead of teleporting.
        """
        return self._pos

    @pos.setter
    def pos(self, position) -> None:
        self.set_target_pos(position)

    def set_target_pos(
            self,
            position,
            duration=None,
            lerp_type=None
    ):
        new_target = pygame.Vector2(position)

        if duration is not None:
            self.move_duration = max(0.0, float(duration))

        if lerp_type is not None:
            self.set_lerp_type(lerp_type)

        # The target did not change, so don't restart the animation.
        if new_target == self.target_pos:
            return

        self.start_pos = self._pos.copy()
        self.target_pos = new_target
        self.move_elapsed = 0.0
        self.animating = True

        if self.move_duration <= 0.0:
            self.snap_to(new_target)

    def snap_to(self, position):
        new_position = pygame.Vector2(position)

        self._pos.update(new_position)
        self.start_pos.update(new_position)
        self.target_pos.update(new_position)

        self.move_elapsed = self.move_duration
        self.animating = False

    def animate_from(
            self,
            start_position,
            duration=None,
            lerp_type=None
    ):
        if duration is not None:
            self.move_duration = max(0.0, float(duration))

        if lerp_type is not None:
            self.set_lerp_type(lerp_type)

        # Keep the current target, but place the displayed button
        # at the animation's starting position.
        self._pos.update(start_position)
        self.start_pos.update(start_position)

        self.move_elapsed = 0.0
        self.animating = self._pos != self.target_pos

    # ========================================================
    # EASING
    # ========================================================

    def set_lerp_type(self, lerp_type: str) -> None:
        if lerp_type not in EASING_TYPES:
            available = ", ".join(EASING_TYPES.keys())

            raise ValueError(
                f"Unknown lerp type '{lerp_type}'. "
                f"Available types: {available}"
            )

        self.lerp_type = lerp_type

    def set_animation(
        self,
        duration: Optional[float] = None,
        lerp_type: Optional[str] = None
    ) -> None:
        """Change the button's default animation settings."""
        if duration is not None:
            self.move_duration = max(0.0, float(duration))

        if lerp_type is not None:
            self.set_lerp_type(lerp_type)

    def update_position(self, dt: float) -> None:
        if not self.animating:
            return

        if self.move_duration <= 0.0:
            self.snap_to(self.target_pos)
            return

        self.move_elapsed += max(0.0, dt)

        progress = min(
            self.move_elapsed / self.move_duration,
            1.0
        )

        easing_function = EASING_TYPES.get(
            self.lerp_type,
            linear
        )

        eased_progress = easing_function(progress)

        difference = self.target_pos - self.start_pos

        self._pos = (
            self.start_pos
            + difference * eased_progress
        )

        if progress >= 1.0:
            self._pos.update(self.target_pos)
            self.animating = False

    # ========================================================
    # RECTANGLE AND INPUT
    # ========================================================

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(
            round(self._pos.x),
            round(self._pos.y),
            round(self.w),
            round(self.h)
        )

    def hovering(self) -> bool:
        return self.get_rect().collidepoint(
            pygame.mouse.get_pos()
        )

    def click(self) -> None:
        if callable(self.onclick):
            self.onclick()

    # ========================================================
    # UPDATE AND DRAW
    # ========================================================

    def update(self, dt: Optional[float] = None) -> None:
        """
        Update visual state and animation.

        dt is optional because your main script currently calls draw()
        without giving the button a delta time.
        """
        current_ms = pygame.time.get_ticks()

        if dt is None:
            dt = (current_ms - self._last_update_ms) / 1000.0

        self._last_update_ms = current_ms

        # Prevent a hidden or paused button from jumping immediately
        # to its destination after a long delay.
        dt = min(max(float(dt), 0.0), 0.1)

        # This may update image, direction, or assign button.pos.
        if callable(self.update_visual):
            self.update_visual(self)

        self.update_position(dt)

    def draw(
        self,
        screen: Optional[pygame.Surface] = None,
        dt: Optional[float] = None
    ) -> None:
        """
        Draw the button.

        Both of these work:
            button.draw()
            button.draw(screen, dt)
        """
        if screen is None:
            screen = pygame.display.get_surface()

        if screen is None:
            return

        self.update(dt)

        base_rect = self.get_rect()

        if self.image is None:
            pygame.draw.rect(
                screen,
                (100, 100, 100),
                base_rect
            )
            return

        width = max(1, round(self.w))
        height = max(1, round(self.h))

        image = pygame.transform.scale(
            self.image,
            (width, height)
        )

        image = pygame.transform.rotate(
            image,
            self.dir * -90
        )

        alpha = self.hover_alpha if self.hovering() else self.alpha
        image.set_alpha(alpha)

        image_rect = image.get_rect(
            center=base_rect.center
        )

        screen.blit(image, image_rect)

        if self.draw_hover_outline and self.hovering():
            pygame.draw.rect(
                screen,
                self.hover_outline_color,
                base_rect,
                self.hover_outline_width
            )