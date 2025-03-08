import json
import networkx as nx
import matplotlib.pyplot as plt

# read json data

def build_graph(json_file):
    json_path = 'output.json'
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Create a "directed" graph
    G = nx.DiGraph()

    # Create nodes (each task) with its attributes and "ObjectId" as the unique identifier for each node.
    for task in data:
        for key, task_data in task.items():
            node_id = task_data["ObjectId"]
            G.add_node(node_id, **task_data)

    # Add edges based on predecessor relationships.
    for task in data:
        for key, task_data in task.items():
            current_node = task_data["ObjectId"]
            if "predecessor" in task_data:
                for pred in task_data["predecessor"]:
                    pred_id = pred["ObjectId"]
                    G.add_edge(pred_id, current_node)


    # we need to have a database to store the graph, for now it just runs and goes away



    # ####################### Visualize the graph #########################
    # plt.figure(figsize=(20, 15))
    # pos = nx.spring_layout(G)  # layout for better visualization
    # nx.draw(G, pos, with_labels=True, node_color='lightblue',
    #         edge_color='gray', node_size=2000, font_size=8)
    # plt.title("Construction Schedule Action Graph")
    # plt.show()

    # # save the graph to an image
    # plt.savefig('construction_schedule_graph.png')

    # # Print out the graph details
    # print("Nodes:")
    # print(G.nodes(data=True))
    # print("\nEdges:")
    # print(list(G.edges()))
