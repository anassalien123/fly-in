from graph import Hub


class Drone:
    def __init__(
        self,
        drone_id: int,
        path: list[Hub]
    ):
        self.id = drone_id
        self.path = path
        self.position = 0

        # Turns the drone must stay grounded at its current hub
        # before it's eligible to move again. Set on arrival —
        # restricted zones are slow to cross, so they leave the
        # drone with a nonzero cooldown for a turn.
        self.cooldown = 0

    def get_current_hub(self) -> Hub:
        return self.path[self.position]

    def move(self) -> bool:
        if self.position + 1 >= len(self.path):
            return False

        self.position += 1
        return True

    def has_reached_goal(self) -> bool:
        return self.position == len(self.path) - 1