from typing import Any


class Hub:
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        color: str | None = None,
        zone: str = "normal",
        max_drones: int = 1
    ):
        self.name = name
        self.x = x
        self.y = y

        self.color = color
        self.zone = zone
        self.max_drones = max_drones

        self.neighbors: list["Hub"] = []


class Connection:
    def __init__(
        self,
        source: Hub,
        destination: Hub,
        max_link_capacity: int = 1
    ):
        self.source = source
        self.destination = destination
        self.max_link_capacity = max_link_capacity


class Graph:
    def __init__(self):
        self.hubs: dict[str, Hub] = {}
        self.connections: list[Connection] = []

    def add_hub(self, hub: Hub) -> None:
        self.hubs[hub.name] = hub

    def get_hub(self, name: str) -> Hub | None:
        return self.hubs.get(name)

    def add_connection(self, connection: Connection) -> None:
        self.connections.append(connection)

        if connection.destination not in connection.source.neighbors:
            connection.source.neighbors.append(connection.destination)

        if connection.source not in connection.destination.neighbors:
            connection.destination.neighbors.append(connection.source)

    def build(self, config: dict[str, Any]) -> None:
        # Make all Hubs
        for zone in config["zones"]:
            hub = Hub(
                name=zone["name"],
                x=zone["x"],
                y=zone["y"],
                color=zone["color"],
                zone=zone["zone"] or "normal",
                max_drones=zone["max_drones"] or 1,
            )
            self.add_hub(hub)

        #Make all Connections
        for conn in config["connection"]:
            source = self.get_hub(conn["from"])
            destination = self.get_hub(conn["to"])

            if source is None or destination is None:
                raise ValueError("Connection references unknown hub")

            connection = Connection(
                source=source,
                destination=destination,
                max_link_capacity=conn["max_link_capacity"] or 1,
            )

            self.add_connection(connection)