from typing import Dict, Any
import re


class Parser:
    def __init__(self, filename: str):
        self.filename = filename
        self.nb_drones = 0

        self.start_hub = None
        self.end_hub = None

        self.hubs = []
        self.connections = []

        self.names = set()
        self.coordinates = set()

    def parser(self) -> Dict[str, Any]:
        config = {
            "nb_drones": 0,
            "zones": [],
            "connection": []
        }

        with open(self.filename, "r") as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                if ":" not in line:
                    raise ValueError(
                        f"[Line {line_num}] Missing ':' in line: {line}"
                    )

                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "nb_drones":
                    config["nb_drones"] = self.parse_nb_drones(value)

                elif key == "start_hub":
                    config["zones"].append({
                        "type": "start_hub",
                        **self.parse_start_hub(value)
                    })

                elif key == "hub":
                    config["zones"].append({
                        "type": "hub",
                        **self.parse_hub(value)
                    })

                elif key == "end_hub":
                    config["zones"].append({
                        "type": "end_hub",
                        **self.parse_end_hub(value)
                    })

                elif key == "connection":
                    config["connection"].append(
                        self.parse_connection(value)
                    )

                else:
                    raise ValueError(
                        f"[Line {line_num}] Unknown keyword '{key}'"
                    )

        if self.start_hub is None:
            raise ValueError("Missing start_hub")

        if self.end_hub is None:
            raise ValueError("Missing end_hub")

        self.validate(config)
        return config

    def parse_nb_drones(self, value: str) -> int:
        value = value.strip()
        if not value.isdigit():
            raise ValueError("Invalid number of drones")

        self.nb_drones = int(value)
        return self.nb_drones

    def parse_metadata(self, value: str) -> tuple[str, Dict[str, Any]]:
        allowed = {
            "color",
            "zone",
            "max_drones",
            "max_link_capacity"
        }

        metadata = {}

        match = re.search(r"\[(.*)\]", value)

        if match:
            content = match.group(1)

            for item in content.split():
                if "=" not in item:
                    raise ValueError(f"Invalid metadata: {item}")

                key, val = item.split("=", 1)

                if key not in allowed:
                    raise ValueError(f"Unknown metadata: {key}")

                metadata[key] = val

            value = value[:match.start()].strip()

        return value, metadata



    def parse_start_hub(self, value: str) -> Dict[str, Any]:
        if self.start_hub is not None:
            raise ValueError("Multiple start_hub definitions")

        self.start_hub = self.parse_zone(value)
        return self.start_hub



    def parse_hub(self, value: str) -> Dict[str,Any]:
        hub = self.parse_zone(value)
        self.hubs.append(hub)
        return hub



    def parse_end_hub(self, value: str) -> Dict[str, Any]:
        if self.end_hub is not None:
            raise ValueError("Multiple end_hub definitions")

        self.end_hub = self.parse_zone(value)
        return self.end_hub



    def parse_zone(self, value: str) -> Dict[str, Any]:
        value, meta = self.parse_metadata(value)

        words = value.split()

        if len(words) != 3:
            raise ValueError("Invalid hub")

        name = words[0]

        if not name:
            raise ValueError("Invalid hub name")

        try:
            x = int(words[1])
            y = int(words[2])
        except ValueError:
            raise ValueError("Invalid coordinates")

        if name in self.names:
            raise ValueError(f"Duplicate hub name: {name}")

        if (x, y) in self.coordinates:
            raise ValueError(f"Duplicate coordinates: ({x}, {y})")

        self.names.add(name)
        self.coordinates.add((x, y))

        return {
            "name": name,
            "x": x,
            "y": y,
            "color": meta.get("color"),
            "zone": meta.get("zone"),
            "max_drones": (
                int(meta["max_drones"])
                if "max_drones" in meta else None
            )
        }



    def parse_connection(self, value: str) -> Dict[str, Any]:
        value, meta = self.parse_metadata(value)

        if "-" not in value:
            raise ValueError(f"Invalid connection: {value}")

        src, dst = value.split("-", 1)

        src = src.strip()
        dst = dst.strip()

        if not src or not dst:
            raise ValueError("Invalid connection")

        if src == dst:
            raise ValueError("Connection cannot link a hub to itself")

        data = {
            "from": src,
            "to": dst,
            "max_link_capacity": (
                int(meta["max_link_capacity"])
                if "max_link_capacity" in meta else None
            )
        }

        self.connections.append(data)

        return data



    def validate(self, config: Dict[str, Any]) -> None:
        if self.nb_drones <= 0:
            raise ValueError("Invalid number of drones")

        if self.start_hub is None:
            raise ValueError("Missing start_hub")

        if self.end_hub is None:
            raise ValueError("Missing end_hub")

        for conn in self.connections:
            if conn["from"] not in self.names:
                raise ValueError(
                    f"Unknown hub: {conn['from']}"
                )

            if conn["to"] not in self.names:
                raise ValueError(
                    f"Unknown hub: {conn['to']}"
                )
