import heapq

from graph import Graph, Hub


class PathFinder:
    def __init__(self, graph: Graph):
        self.graph = graph

    def find_path(
        self,
        start_name: str,
        goal_name: str
    ) -> list[Hub]:
        """Find the shortest path between two hubs."""

        start = self.graph.get_hub(start_name)
        goal = self.graph.get_hub(goal_name)

        if start is None:
            raise ValueError(f"Unknown hub: {start_name}")

        if goal is None:
            raise ValueError(f"Unknown hub: {goal_name}")

        return self.dijkstra(start, goal)

    # ==================================================
    # MULTIPLE EQUAL-COST PATHS (load balancing)
    # ==================================================

    def find_paths(
        self,
        start_name: str,
        goal_name: str,
        max_paths: int = 8
    ) -> list[list[Hub]]:
        """
        Find up to `max_paths` distinct paths between start and
        goal that all share the same minimal cost as the
        shortest path.

        A single fixed shortest path funnels every drone down
        the same route even when the map offers parallel
        branches with their own capacity (a fork, redundant
        gates, etc). Returning several equal-cost alternatives
        lets the simulation spread drones across them instead
        of bottlenecking one link while a same-length branch
        sits unused.
        """

        start = self.graph.get_hub(start_name)
        goal = self.graph.get_hub(goal_name)

        if start is None:
            raise ValueError(f"Unknown hub: {start_name}")

        if goal is None:
            raise ValueError(f"Unknown hub: {goal_name}")

        primary = self.dijkstra(start, goal)

        if not primary:
            return []

        best_cost = self.path_cost(primary)

        paths = [primary]
        seen = {self.path_key(primary)}
        tried_edges: set[frozenset] = set()

        # Edges to try removing, seeded from the primary path
        # and expanded with every new path we discover.
        candidates = list(zip(primary[:-1], primary[1:]))

        while candidates and len(paths) < max_paths:

            a, b = candidates.pop(0)
            edge = frozenset((a, b))

            if edge in tried_edges:
                continue

            tried_edges.add(edge)

            alt = self.dijkstra(
                start,
                goal,
                blocked_edges={edge}
            )

            if not alt:
                continue

            # Only keep alternatives that are just as short,
            # never a worse detour.
            if self.path_cost(alt) != best_cost:
                continue

            key = self.path_key(alt)

            if key in seen:
                continue

            seen.add(key)
            paths.append(alt)

            candidates.extend(zip(alt[:-1], alt[1:]))

        return paths

    @staticmethod
    def path_key(path: list[Hub]) -> tuple[str, ...]:
        """Return a hashable identifier for a path."""

        return tuple(hub.name for hub in path)

    def path_cost(self, path: list[Hub]) -> float:
        """Return the total travel cost of a path."""

        return sum(
            self.get_cost(a, b)
            for a, b in zip(path[:-1], path[1:])
        )

    def dijkstra(
        self,
        start: Hub,
        goal: Hub,
        blocked_edges: set[frozenset] | None = None
    ) -> list[Hub]:
        """Run Dijkstra's algorithm."""

        distance, parent, priority_queue = self.initialize(start)

        while priority_queue:
            current_distance, _, current = heapq.heappop(
                priority_queue
            )

            if current_distance != distance[current]:
                continue

            if current == goal:
                return self.reconstruct_path(parent, goal)

            self.update_neighbors(
                current,
                distance,
                parent,
                priority_queue,
                blocked_edges
            )

        return []

    def initialize(
        self,
        start: Hub
    ) -> tuple[
        dict[Hub, float],
        dict[Hub, Hub | None],
        list[tuple[float, int, Hub]]
    ]:
        """Initialize Dijkstra's data structures."""

        distance = {}
        parent = {}
        priority_queue = []

        for hub in self.graph.hubs.values():
            distance[hub] = float("inf")
            parent[hub] = None

        distance[start] = 0

        heapq.heappush(
            priority_queue,
            (0, id(start), start)
        )

        return distance, parent, priority_queue

    def update_neighbors(
        self,
        current: Hub,
        distance: dict[Hub, float],
        parent: dict[Hub, Hub | None],
        priority_queue: list[tuple[float, int, Hub]],
        blocked_edges: set[frozenset] | None = None
    ) -> None:
        """Update neighboring hubs."""

        for neighbor in current.neighbors:

            if blocked_edges and frozenset(
                (current, neighbor)
            ) in blocked_edges:
                continue

            cost = self.get_cost(current, neighbor)
            new_distance = distance[current] + cost

            if new_distance < distance[neighbor]:
                distance[neighbor] = new_distance
                parent[neighbor] = current

                heapq.heappush(
                    priority_queue,
                    (new_distance, id(neighbor), neighbor)
                )

    def get_cost(
        self,
        current: Hub,
        neighbor: Hub
    ) -> float:
        """Return the travel cost between two neighboring hubs."""

        if neighbor.zone == "blocked":
            return float("inf")

        if neighbor.zone == "restricted":
            return 2.0

        return 1.0

    def reconstruct_path(
        self,
        parent: dict[Hub, Hub | None],
        goal: Hub
    ) -> list[Hub]:
        """Reconstruct the shortest path."""

        path = []
        current: Hub | None = goal

        while current is not None:
            path.append(current)
            current = parent[current]

        path.reverse()

        return path
