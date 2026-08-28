from drone import Drone
from graph import Graph, Hub, Connection


class Simulation:
    def __init__(
        self,
        graph: Graph,
        nb_drones: int,
        start_name: str,
        goal_name: str
    ):
        self.graph = graph
        self.nb_drones = nb_drones
        self.start_name = start_name
        self.goal_name = goal_name

        self.drones: list[Drone] = []
        self.time = 0

        # Snapshot of every drone's hub at each time step,
        # recorded so the visualizer can replay the run.
        self.history: list[dict[int, Hub]] = []

    # ==================================================
    # CREATE DRONES
    # ==================================================

    def create_drones(self, pathfinder):

        # Find every equal-cost route between start and goal so
        # drones can be spread across parallel branches instead
        # of all funnelling down a single fixed path.
        paths = pathfinder.find_paths(
            self.start_name,
            self.goal_name
        )

        if not paths:
            raise ValueError(
                f"No path found from "
                f"{self.start_name} to {self.goal_name}"
            )

        for i in range(self.nb_drones):

            path = paths[i % len(paths)]

            drone = Drone(
                i + 1,
                path.copy()
            )

            self.drones.append(drone)

    # ==================================================
    # CONNECTION
    # ==================================================

    def get_connection(
        self,
        source: Hub,
        destination: Hub
    ) -> Connection | None:

        for connection in self.graph.connections:

            if (
                connection.source == source
                and connection.destination == destination
            ):
                return connection

            if (
                connection.source == destination
                and connection.destination == source
            ):
                return connection

        return None

    # ==================================================
    # PRIORITY
    # ==================================================

    def drone_priority(self, drone: Drone) -> int:

        current = drone.get_current_hub()

        if current.zone == "priority":
            return 2

        if (
            drone.position + 1 < len(drone.path)
            and drone.path[drone.position + 1].zone == "priority"
        ):
            return 1

        return 0

    # ==================================================
    # RESOLVE MOVES (chain-aware scheduler)
    # ==================================================

    def resolve_moves(self) -> list[Drone]:
        """
        Decide which scheduled drones actually move this turn.

        A hub's free capacity for this turn depends on whether
        its current occupant is itself moving away this same
        turn — which can depend on a further occupant doing the
        same, and so on down the chain. This resolves that with
        a small fixed-point loop: a drone is only decided once
        every drone currently blocking its target hub has
        already been decided, so a drone can legally move into a
        hub in the very same turn its occupant vacates it
        (a synchronized "chain shift"), instead of always having
        to wait one extra turn after the hub empties out.

        Drones are still granted contested slots in scheduling
        order (priority, then id), exactly as before — the
        fixed point only changes *when* a hub's true occupancy
        is known, not who wins a contested slot.
        """

        scheduled = self.get_scheduled_drones()

        next_hub_of: dict[Drone, Hub] = {}
        connection_of: dict[Drone, Connection] = {}

        for drone in scheduled:

            if drone.position + 1 >= len(drone.path):
                continue

            next_hub = drone.path[drone.position + 1]

            connection = self.get_connection(
                drone.get_current_hub(),
                next_hub
            )

            if connection is None:
                continue

            next_hub_of[drone] = next_hub
            connection_of[drone] = connection

        # Current occupants of every hub (landed drones don't
        # occupy capacity — see count_drones_at's old behavior).
        occupants_by_hub: dict[Hub, list[Drone]] = {}

        for drone in self.drones:

            if drone.has_reached_goal():
                continue

            occupants_by_hub.setdefault(
                drone.get_current_hub(),
                []
            ).append(drone)

        decided: dict[Drone, bool] = {}
        reserved_hubs: dict[Hub, int] = {}
        reserved_links: dict[Connection, int] = {}

        progressed = True

        while progressed:

            progressed = False

            for drone in scheduled:

                if drone in decided:
                    continue

                if drone not in next_hub_of:
                    decided[drone] = False
                    progressed = True
                    continue

                next_hub = next_hub_of[drone]
                connection = connection_of[drone]

                # Every drone currently occupying next_hub must
                # be resolved first, so we know exactly how many
                # of them are actually staying put this turn.
                blockers = occupants_by_hub.get(next_hub, [])

                if any(
                    blocker not in decided
                    for blocker in blockers
                ):
                    continue

                still_there = sum(
                    1
                    for blocker in blockers
                    if decided[blocker] is False
                )

                reserved = reserved_hubs.get(next_hub, 0)

                if still_there + reserved >= next_hub.max_drones:
                    decided[drone] = False
                    progressed = True
                    continue

                link_reserved = reserved_links.get(connection, 0)

                if link_reserved >= connection.max_link_capacity:
                    decided[drone] = False
                    progressed = True
                    continue

                decided[drone] = True

                reserved_hubs[next_hub] = reserved + 1
                reserved_links[connection] = link_reserved + 1

                progressed = True

        # Anything left undecided is a genuine circular wait
        # (e.g. drones trying to swap places head-on) that this
        # discrete step model cannot resolve — treat it as
        # blocked this turn, same as the original behavior.
        for drone in scheduled:
            decided.setdefault(drone, False)

        return [
            drone
            for drone in scheduled
            if decided[drone]
        ]

    # ==================================================
    # ZONE DWELL TIME
    # ==================================================

    def get_dwell_time(self, hub: Hub) -> int:
        """
        Extra turns a drone must stay grounded after arriving at
        `hub` before it's eligible to move again.

        This mirrors Pathfinder.get_cost(), which charges 2.0 to
        enter a restricted hub and 1.0 for anything else: the
        move itself always takes one simulated turn (a single
        `position` step), so a restricted arrival needs exactly
        one extra dwell turn on top of that to add up to the same
        total cost the pathfinder used to pick and rank paths.
        """

        if hub.zone == "restricted":
            return 1

        return 0

    def has_cooling_down_drones(self) -> bool:
        """
        True if some active drone is still working through a
        restricted-zone cooldown.

        A turn where nothing moved while one of these is ticking
        down isn't a real deadlock: the next turn is guaranteed
        to change (the cooldown drops by one), which can free up
        whatever it's blocking. Only the absence of any cooldown
        makes "zero moves" a reliable deadlock signal.
        """

        return any(
            drone.cooldown > 0
            for drone in self.drones
            if not drone.has_reached_goal()
        )

    # ==================================================
    # SORT DRONES
    # ==================================================

    def get_scheduled_drones(self):

        waiting = [
            drone
            for drone in self.drones
            if not drone.has_reached_goal()
            and drone.cooldown == 0
        ]

        # Priority first.
        #
        # If same priority:
        # smaller drone ID first.
        waiting.sort(
            key=lambda drone: (
                -self.drone_priority(drone),
                drone.id
            )
        )

        return waiting

    # ==================================================
    # ONE SIMULATION STEP
    # ==================================================

    def step(self):

        self.time += 1

        moving_drones = self.resolve_moves()

        # ----------------------------------------------
        # APPLY MOVES
        # ----------------------------------------------

        moves = []
        moved_ids = set()

        for drone in moving_drones:

            source = drone.get_current_hub()

            destination = drone.path[
                drone.position + 1
            ]

            drone.move()

            # Restricted zones take an extra turn to clear —
            # ground the drone here before it can move again.
            drone.cooldown = self.get_dwell_time(destination)

            moved_ids.add(drone.id)

            moves.append(
                (
                    drone,
                    source,
                    destination
                )
            )

        # ----------------------------------------------
        # ADVANCE COOLDOWNS
        # ----------------------------------------------

        # Drones that didn't move this turn because they're
        # already mid-cooldown from a previous restricted-zone
        # arrival get one turn closer to being free to move
        # again. Drones that just moved keep the fresh cooldown
        # set above instead of having it eaten the same turn.
        for drone in self.drones:

            if drone.id in moved_ids:
                continue

            if drone.cooldown > 0:
                drone.cooldown -= 1

        return moves

    # ==================================================
    # SNAPSHOT (for visualization playback)
    # ==================================================

    def snapshot(self) -> dict[int, Hub]:

        return {
            drone.id: drone.get_current_hub()
            for drone in self.drones
        }

    # ==================================================
    # FINISHED
    # ==================================================

    def is_finished(self) -> bool:

        return all(
            drone.has_reached_goal()
            for drone in self.drones
        )

    # ==================================================
    # PRINT MOVES
    # ==================================================

    def print_moves(self, moves):

        print(
            f"\n--- TIME {self.time} ---"
        )

        if not moves:
            print("No drone moved.")

            return

        for drone, source, destination in moves:

            print(
                f"Drone {drone.id}: "
                f"{source.name} -> "
                f"{destination.name}"
            )

    # ==================================================
    # RUN
    # ==================================================

    def run(self, pathfinder):

        self.create_drones(
            pathfinder
        )

        self.history = [self.snapshot()]

        print(
            "\n--- TIME 0 ---"
        )

        for drone in self.drones:

            print(
                f"Drone {drone.id}: "
                f"{drone.get_current_hub().name}"
            )

        while not self.is_finished():

            # Snapshot *before* this turn's cooldowns tick down,
            # since step() decrements them as part of taking the
            # turn — checking afterward would always see whatever
            # was holding things up as already cleared.
            had_cooling_down_drones = (
                self.has_cooling_down_drones()
            )

            moves = self.step()

            self.history.append(self.snapshot())

            self.print_moves(
                moves
            )

            # ------------------------------------------
            # DEADLOCK
            # ------------------------------------------

            # A turn with zero moves isn't necessarily a true
            # deadlock anymore: a drone can legitimately sit
            # grounded in a restricted zone for a turn, backing
            # up everyone behind it with nothing to do this turn
            # even though the jam clears on its own once that
            # cooldown runs out. Only treat it as a genuine,
            # unrecoverable deadlock when nobody was mid-cooldown
            # going into this turn either — i.e. nothing on the
            # board was ever going to change on its own.

            if not moves and not had_cooling_down_drones:

                print(
                    "\nERROR: Simulation deadlock."
                )

                for drone in self.drones:

                    if not drone.has_reached_goal():

                        print(
                            f"Drone {drone.id} "
                            f"is waiting at "
                            f"{drone.get_current_hub().name}"
                        )

                break

        if self.is_finished():

            print(
                f"\nSimulation finished in "
                f"{self.time} steps."
            )
