import math

import pygame
from graph import Graph


# Distinct colors cycled through for drone markers.
DRONE_COLORS = [
    (255, 99, 71),
    (60, 179, 113),
    (65, 105, 225),
    (255, 215, 0),
    (218, 112, 214),
    (0, 206, 209),
    (255, 140, 0),
    (154, 205, 50),
]


class GraphVisualizer:
    def __init__(self, graph: Graph, simulation=None):
        pygame.init()

        self.graph = graph

        # Optional Simulation instance (duck-typed: needs
        # `.history` — a list of {drone_id: Hub} snapshots —
        # and `.drones`). When provided, the visualizer replays
        # the simulation on top of the graph.
        self.simulation = simulation

        self.frame_index = 0
        self.playing = False
        self.play_interval_ms = 500
        self.last_step_time = pygame.time.get_ticks()

        # Window
        self.width = 1000
        self.height = 700

        self.fullscreen = False

        self.screen = pygame.display.set_mode(
            (self.width, self.height),
            pygame.RESIZABLE
        )

        pygame.display.set_caption(
            "Fly-in Graph Visualization"
        )

        self.clock = pygame.time.Clock()

        # Fonts
        self.font = pygame.font.Font(
            None,
            24
        )

        self.small_font = pygame.font.Font(
            None,
            20
        )

        self.tiny_font = pygame.font.Font(
            None,
            16
        )

        self.background_font = pygame.font.Font(
            None,
            120
        )

        # Camera / Zoom
        self.scale = 120.0

        self.min_scale = 40.0
        self.max_scale = 300.0

        # Camera position
        self.offset_x = 100.0
        self.offset_y = 100.0

        # Pan state
        self.panning = False
        self.pan_button = None
        self.last_mouse_pos = (0, 0)

    # =========================================================
    # COORDINATES
    # =========================================================

    def world_to_screen(
        self,
        x: int,
        y: int
    ) -> tuple[int, int]:
        """
        Convert graph coordinates to screen coordinates.
        """

        screen_x = (
            self.offset_x
            + x * self.scale
        )

        screen_y = (
            self.offset_y
            + y * self.scale
        )

        return (
            int(screen_x),
            int(screen_y)
        )

    # =========================================================
    # COLORS
    # =========================================================

    def get_hub_color(self, hub):
        """Return the Pygame color for a hub."""

        colors = {
            "red": (220, 50, 50),
            "green": (50, 200, 80),
            "blue": (50, 120, 220),
            "orange": (240, 150, 40),
            "yellow": (240, 220, 50),
            "purple": (160, 80, 220),
        }

        return colors.get(
            hub.color,
            (180, 180, 180)
        )

    # =========================================================
    # BACKGROUND
    # =========================================================

    def draw_background(self):
        """
        Draw background text.
        """

        text = self.background_font.render(
            "fly-in-1337",
            True,
            (45, 45, 52)
        )

        x = (
            self.width
            - text.get_width()
        ) // 2

        y = (
            self.height
            - text.get_height()
        ) // 2

        self.screen.blit(
            text,
            (x, y)
        )

    # =========================================================
    # CONNECTIONS
    # =========================================================

    def draw_connections(self):
        """
        Draw all graph connections with consistent spacing
        around the hubs.
        """

        # Distance between edge and hub
        hub_radius = 25

        for connection in self.graph.connections:

            source = connection.source
            destination = connection.destination

            x1, y1 = self.world_to_screen(
                source.x,
                source.y
            )

            x2, y2 = self.world_to_screen(
                destination.x,
                destination.y
            )

            # Direction vector
            dx = x2 - x1
            dy = y2 - y1

            distance = (dx * dx + dy * dy) ** 0.5

            if distance == 0:
                continue

            # Normalize direction
            nx = dx / distance
            ny = dy / distance

            # Start and end of the edge
            # Stop at the border of each hub
            start_x = x1 + nx * hub_radius
            start_y = y1 + ny * hub_radius

            end_x = x2 - nx * hub_radius
            end_y = y2 - ny * hub_radius

            pygame.draw.line(
                self.screen,
                (100, 100, 100),
                (int(start_x), int(start_y)),
                (int(end_x), int(end_y)),
                3
            )

            # Connection capacity
            mid_x = (
                (start_x + end_x) / 2
            )

            mid_y = (
                (start_y + end_y) / 2
            )

            capacity_text = self.small_font.render(
                str(connection.max_link_capacity),
                True,
                (230, 230, 230)
            )

            self.screen.blit(
                capacity_text,
                (
                    int(mid_x + 5),
                    int(mid_y + 5)
                )
            )


    def draw_hubs(self):
        """
        Draw hubs with consistent size and spacing.
        """

        hub_radius = 25

        for hub in self.graph.hubs.values():

            x, y = self.world_to_screen(
                hub.x,
                hub.y
            )

            color = self.get_hub_color(hub)

            # =====================================================
            # HUB
            # =====================================================

            if hub.zone == "blocked":

                pygame.draw.rect(
                    self.screen,
                    color,
                    (
                        x - hub_radius,
                        y - hub_radius,
                        hub_radius * 2,
                        hub_radius * 2
                    )
                )

            else:

                # Main circle
                pygame.draw.circle(
                    self.screen,
                    color,
                    (x, y),
                    hub_radius
                )

                # Restricted border
                if hub.zone == "restricted":

                    pygame.draw.circle(
                        self.screen,
                        (255, 255, 255),
                        (x, y),
                        hub_radius,
                        3
                    )

            # =====================================================
            # HUB NAME
            # =====================================================

            name_text = self.font.render(
                hub.name,
                True,
                (255, 255, 255)
            )

            name_x = (
                x
                - name_text.get_width() // 2
            )

            name_y = (
                y
                + hub_radius
                + 8
            )

            self.screen.blit(
                name_text,
                (
                    name_x,
                    name_y
                )
            )

            # =====================================================
            # MAX DRONES
            # =====================================================

            drone_text = self.small_font.render(
                f"D:{hub.max_drones}",
                True,
                (255, 255, 255)
            )

            drone_x = (
                x
                - drone_text.get_width() // 2
            )

            drone_y = (
                y
                - drone_text.get_height() // 2
            )

            self.screen.blit(
                drone_text,
                (
                    drone_x,
                    drone_y
                )
            )

    # =========================================================
    # DRONES (simulation playback)
    # =========================================================

    def get_drone_color(self, drone_id: int):
        """Return a stable color for a given drone id."""

        return DRONE_COLORS[
            (drone_id - 1) % len(DRONE_COLORS)
        ]

    def get_step_progress(self) -> float:
        """
        Fraction (0..1) of the way from `frame_index` to
        `frame_index + 1`, based on elapsed playback time.

        Used to interpolate drone positions smoothly between
        hubs instead of snapping them straight there the
        instant the frame advances. Stepping manually (while
        paused) still snaps instantly — only autoplay glides.
        """

        if (
            not self.playing
            or not self.simulation
            or not self.simulation.history
        ):
            return 0.0

        if self.frame_index >= len(self.simulation.history) - 1:
            return 0.0

        elapsed = pygame.time.get_ticks() - self.last_step_time

        return max(
            0.0,
            min(1.0, elapsed / self.play_interval_ms)
        )

    def get_drone_positions(self, frame: dict) -> dict:
        """
        Spread the drones of a single playback frame around the
        centers of the hubs they occupy so co-located drones
        don't overlap, returning {drone_id: (x, y)} in screen
        space.
        """

        orbit_radius = 15

        hub_groups: dict = {}

        for drone_id, hub in frame.items():
            hub_groups.setdefault(hub, []).append(drone_id)

        positions: dict = {}

        for hub, drone_ids in hub_groups.items():

            cx, cy = self.world_to_screen(hub.x, hub.y)

            drone_ids = sorted(drone_ids)
            count = len(drone_ids)

            for i, drone_id in enumerate(drone_ids):

                if count == 1:
                    dx, dy = 0.0, 0.0
                else:
                    angle = (2 * math.pi * i) / count
                    dx = math.cos(angle) * orbit_radius
                    dy = math.sin(angle) * orbit_radius

                positions[drone_id] = (cx + dx, cy + dy)

        return positions

    def draw_drones(self):
        """
        Draw every drone for the current playback frame,
        gliding it smoothly toward its next-frame position
        while autoplay is running instead of teleporting the
        instant the frame changes.
        """

        if not self.simulation or not self.simulation.history:
            return

        current_frame = self.simulation.history[self.frame_index]

        has_next_frame = (
            self.frame_index + 1 < len(self.simulation.history)
        )

        next_frame = (
            self.simulation.history[self.frame_index + 1]
            if has_next_frame
            else current_frame
        )

        progress = self.get_step_progress()

        current_positions = self.get_drone_positions(current_frame)

        next_positions = (
            self.get_drone_positions(next_frame)
            if has_next_frame
            else current_positions
        )

        drone_radius = 8

        for drone_id, (x1, y1) in current_positions.items():

            x2, y2 = next_positions.get(drone_id, (x1, y1))

            x = x1 + (x2 - x1) * progress
            y = y1 + (y2 - y1) * progress

            pos = (int(x), int(y))

            pygame.draw.circle(
                self.screen,
                self.get_drone_color(drone_id),
                pos,
                drone_radius
            )

            pygame.draw.circle(
                self.screen,
                (20, 20, 20),
                pos,
                drone_radius,
                1
            )

            id_text = self.tiny_font.render(
                str(drone_id),
                True,
                (20, 20, 20)
            )

            self.screen.blit(
                id_text,
                (
                    pos[0] - id_text.get_width() // 2,
                    pos[1] - id_text.get_height() // 2
                )
            )

    def draw_hud(self):
        """
        Draw playback info and controls for the simulation.
        """

        if not self.simulation:
            return

        total_steps = len(self.simulation.history) - 1

        landed = sum(
            1
            for drone in self.simulation.drones
            if drone.has_reached_goal()
        )

        status = "PLAYING" if self.playing else "PAUSED"

        lines = [
            f"Time: {self.frame_index} / {total_steps}  [{status}]",
            f"Drones landed: {landed} / {len(self.simulation.drones)}",
            "SPACE play/pause   Right/Left step   R restart",
        ]

        y = 10

        for line in lines:

            text = self.small_font.render(
                line,
                True,
                (230, 230, 230)
            )

            self.screen.blit(text, (10, y))

            y += text.get_height() + 4

    def step_forward(self):
        if not self.simulation:
            return

        if self.frame_index < len(self.simulation.history) - 1:
            self.frame_index += 1
        else:
            self.playing = False

    def step_backward(self):
        if not self.simulation:
            return

        if self.frame_index > 0:
            self.frame_index -= 1

    def restart_playback(self):
        self.frame_index = 0
        self.playing = False

    def update_playback(self):
        """
        Advance the playback frame automatically while playing.
        """

        if not self.playing or not self.simulation:
            return

        now = pygame.time.get_ticks()

        if now - self.last_step_time >= self.play_interval_ms:
            self.last_step_time = now
            self.step_forward()

    # =========================================================
    # ZOOM
    # =========================================================

    def zoom(
        self,
        mouse_x: int,
        mouse_y: int,
        zoom_factor: float
    ):
        """
        Zoom around the mouse position.

        The point under the mouse stays
        at the same screen position.
        """

        old_scale = self.scale

        new_scale = (
            old_scale
            * zoom_factor
        )

        # Limit zoom
        new_scale = max(
            self.min_scale,
            min(
                self.max_scale,
                new_scale
            )
        )

        # Nothing changed
        if new_scale == old_scale:
            return

        # World coordinates under mouse
        world_x = (
            mouse_x - self.offset_x
        ) / old_scale

        world_y = (
            mouse_y - self.offset_y
        ) / old_scale

        # Apply new scale
        self.scale = new_scale

        # Keep same world point
        # under the mouse
        self.offset_x = (
            mouse_x
            - world_x * self.scale
        )

        self.offset_y = (
            mouse_y
            - world_y * self.scale
        )

    def handle_zoom(self, event):
        """
        Handle mouse wheel.
        """

        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Zoom in
        if event.y > 0:

            self.zoom(
                mouse_x,
                mouse_y,
                1.1
            )

        # Zoom out
        elif event.y < 0:

            self.zoom(
                mouse_x,
                mouse_y,
                0.9
            )

    # =========================================================
    # PAN
    # =========================================================

    def start_pan(self, button):
        """
        Start panning.
        """

        self.panning = True

        self.pan_button = button

        self.last_mouse_pos = (
            pygame.mouse.get_pos()
        )

    def stop_pan(self, button):
        """
        Stop panning.
        """

        if self.pan_button == button:

            self.panning = False

            self.pan_button = None

    def handle_pan(self):
        """
        Move the camera while panning.
        """

        if not self.panning:
            return

        current_mouse_pos = (
            pygame.mouse.get_pos()
        )

        mouse_x, mouse_y = (
            current_mouse_pos
        )

        last_x, last_y = (
            self.last_mouse_pos
        )

        # Mouse movement
        dx = mouse_x - last_x
        dy = mouse_y - last_y

        # Move camera
        self.offset_x += dx
        self.offset_y += dy

        # Save position
        self.last_mouse_pos = (
            current_mouse_pos
        )

    # =========================================================
    # MOUSE BUTTONS
    # =========================================================

    def handle_mouse_button_down(
        self,
        event
    ):
        """
        Handle mouse button press.
        """

        # Middle mouse
        if event.button == 2:

            self.start_pan(2)

        # Right mouse
        elif event.button == 3:

            self.start_pan(3)

    def handle_mouse_button_up(
        self,
        event
    ):
        """
        Handle mouse button release.
        """

        # Middle mouse
        if event.button == 2:

            self.stop_pan(2)

        # Right mouse
        elif event.button == 3:

            self.stop_pan(3)

    # =========================================================
    # FULL SCREEN
    # =========================================================

    def toggle_fullscreen(self):
        """
        Toggle fullscreen mode.
        """

        self.fullscreen = (
            not self.fullscreen
        )

        if self.fullscreen:

            self.screen = pygame.display.set_mode(
                (0, 0),
                pygame.FULLSCREEN
            )

            self.width, self.height = (
                self.screen.get_size()
            )

        else:

            self.width = 1000
            self.height = 700

            self.screen = pygame.display.set_mode(
                (
                    self.width,
                    self.height
                ),
                pygame.RESIZABLE
            )

    # =========================================================
    # DRAW
    # =========================================================

    def draw(self):
        """
        Draw the complete graph.
        """

        # Background
        self.screen.fill(
            (25, 25, 30)
        )

        # Background text
        self.draw_background()

        # Connections
        self.draw_connections()

        # Hubs
        self.draw_hubs()

        # Drones (simulation playback)
        self.draw_drones()

        # Playback HUD
        self.draw_hud()

        pygame.display.flip()

    # =========================================================
    # MAIN LOOP
    # =========================================================

    def run(self):
        """
        Start visualization.
        """

        running = True

        while running:

            for event in pygame.event.get():

                # Close window
                if event.type == pygame.QUIT:

                    running = False

                # Keyboard
                elif event.type == pygame.KEYDOWN:

                    # F11 → Fullscreen
                    if event.key == pygame.K_F11:

                        self.toggle_fullscreen()

                    # ESC → Exit fullscreen
                    elif event.key == pygame.K_ESCAPE:

                        if self.fullscreen:

                            self.toggle_fullscreen()

                        else:

                            running = False

                    # SPACE → Play / pause simulation
                    elif event.key == pygame.K_SPACE:

                        self.playing = not self.playing
                        self.last_step_time = pygame.time.get_ticks()

                    # Right arrow → Step forward
                    elif event.key == pygame.K_RIGHT:

                        self.playing = False
                        self.step_forward()

                    # Left arrow → Step backward
                    elif event.key == pygame.K_LEFT:

                        self.playing = False
                        self.step_backward()

                    # R → Restart playback
                    elif event.key == pygame.K_r:

                        self.restart_playback()

                # Mouse wheel → Zoom
                elif event.type == pygame.MOUSEWHEEL:

                    self.handle_zoom(event)

                # Mouse button down → Pan start
                elif event.type == pygame.MOUSEBUTTONDOWN:

                    self.handle_mouse_button_down(
                        event
                    )

                # Mouse button up → Pan stop
                elif event.type == pygame.MOUSEBUTTONUP:

                    self.handle_mouse_button_up(
                        event
                    )

            # Update pan
            self.handle_pan()

            # Advance simulation playback
            self.update_playback()

            # Draw
            self.draw()

            self.clock.tick(60)

        pygame.quit()
