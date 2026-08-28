# from parsing import Parser
# from graph import  Graph
# from Pathfinder import *
# from visualization import GraphVisualizer
# from drone import Drone
# from simulation import Simulation
# import sys


# def main():
#     if len(sys.argv) != 2:
#         print("Usage: python3 fly_in.py map.txt")
#         return

#     parser = Parser(sys.argv[1])

#     config = parser.parser()

#     # print(config)
#     # print(parser.nb_drones)
#     # print(parser.start_hub)
#     # print(parser.hubs)
#     # print(parser.end_hub)
#     # print(parser.connections)

#     graph = Graph()
#     graph.build(config)

#     # print("Hubs:")
#     # for hub in graph.hubs.values():
#     #     print(
#     #         f"{hub.name} ({hub.x}, {hub.y}) -> "
#     #         f"{[n.name for n in hub.neighbors]}"
#     #     )

#     # print("\nConnections:")
#     # for conn in graph.connections:
#     #     print(
#     #         f"{conn.source.name} <-> "
#     #         f"{conn.destination.name} "
#     #         f"(capacity={conn.max_link_capacity})"
#     #     )

#     # pathfinder = PathFinder(graph)

#     # path = pathfinder.find_path("start", "impossible_goal")

#     # for hub in path:
#     #     print(hub.name)




#     # drone = Drone(1, path)

#     # print(drone.get_current_hub().name)

#     # while not drone.has_reached_goal():
#     #     drone.move()
#     #     print(drone.get_current_hub().name)




#     visualizer = GraphVisualizer(graph) 
#     visualizer.run()


# if __name__ == "__main__":
#     try:
#         main()
#     except Exception as e:
#         print(f"Error: {e}")











from parsing import Parser
from graph import Graph
from Pathfinder import PathFinder
from visualization import GraphVisualizer
from simulation import Simulation
import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 fly_in.py map.txt")
        return

    # Parse map
    parser = Parser(sys.argv[1])
    config = parser.parser()

    # Build graph
    graph = Graph()
    graph.build(config)

    # Path finding
    pathfinder = PathFinder(graph)

    # Start / goal
    start_name = parser.start_hub["name"]
    goal_name = parser.end_hub["name"]

    # Simulation
    simulation = Simulation(
        graph,
        parser.nb_drones,
        start_name,
        goal_name
    )

    simulation.run(pathfinder)

    # Visualization (replays the simulation's recorded history)
    visualizer = GraphVisualizer(graph, simulation)
    visualizer.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
