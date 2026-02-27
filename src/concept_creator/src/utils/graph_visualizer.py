import networkx as nx
import matplotlib.pyplot as plt

def visualize_graph(graph: nx.Graph, ax: plt.Axes=None, image_id: str = None, title: str = None, is_spring_layout: bool = False):
    if ax is None:
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111)
    
    if graph is None:
        graph = nx.Graph()
    
    # Extract node positions from the graph
    pos = {}
    for node_id, node_data in graph.nodes(data=True):
        # For regular points
        if 'x' in node_data and 'y' in node_data:
            x_min = node_data['x']['min'] if isinstance(node_data['x'], dict) and 'min' in node_data['x'] else node_data['x']
            x_max = node_data['x']['max'] if isinstance(node_data['x'], dict) and 'max' in node_data['x'] else node_data['x']
            y_min = node_data['y']['min'] if isinstance(node_data['y'], dict) and 'min' in node_data['y'] else node_data['y']
            y_max = node_data['y']['max'] if isinstance(node_data['y'], dict) and 'max' in node_data['y'] else node_data['y']
            
            x = (x_min + x_max) / 2
            y = (y_min + y_max) / 2
            
            pos[node_id] = (x, y)
            
        if 'labels' in node_data and 'Vector' in node_data['labels']:
                x1 = node_data['x1']
                x2 = node_data['x2']
                y1 = node_data['y1']
                y2 = node_data['y2']
                
                x1_min = x1['min'] if isinstance(x1, dict) and 'min' in x1 else x1
                x1_max = x1['max'] if isinstance(x1, dict) and 'max' in x1 else x1
                x2_min = x2['min'] if isinstance(x2, dict) and 'min' in x2 else x2
                x2_max = x2['max'] if isinstance(x2, dict) and 'max' in x2 else x2
                y1_min = y1['min'] if isinstance(y1, dict) and 'min' in y1 else y1
                y1_max = y1['max'] if isinstance(y1, dict) and 'max' in y1 else y1
                y2_min = y2['min'] if isinstance(y2, dict) and 'min' in y2 else y2
                y2_max = y2['max'] if isinstance(y2, dict) and 'max' in y2 else y2
                
                x1 = (x1_min + x1_max) / 2
                y1 = (y1_min + y1_max) / 2
                x2 = (x2_min + x2_max) / 2
                y2 = (y2_min + y2_max) / 2
                
                # Calculate midpoint for vectors
                pos[node_id] = ((x1 + x2) / 2, (y1 + y2) / 2)
    
    node_to_color = {
        "IntersectionPoint": "red",
        "CornerPoint": "green",
        "EndPoint": "blue",
        "QuadrantChangePoint": "purple",
        "StartPoint": "orange"
    }
    # Draw nodes with colors based on their labels
    node_colors = []
    labels_for_nodes = {}
    for node_id in graph.nodes():
        node_data = graph.nodes[node_id]
        
        # Try to get labels from the node data
        labels = []
        if 'labels' in node_data:
            labels = node_data['labels']
            
        node_id_str = str(node_id)
        labels_for_nodes[node_id] = ', '.join(str(label) for label in labels) + ' ' + node_id_str.split(':')[-1]
        
        # Check if any label matches our color mapping
        color = 'lightblue'  # Default color
        for label in labels:
            label_str = str(label)  # Convert to string if it's not already
            if label_str in node_to_color:
                color = node_to_color[label_str]
                break
        
        node_colors.append(color)
        
    pos = nx.spring_layout(graph, scale=42) if is_spring_layout else pos
    # Draw the graph
    nx.draw_networkx_nodes(graph, pos, ax=ax, node_color=node_colors, node_size=500)
    nx.draw_networkx_edges(graph, pos, ax=ax, width=2, alpha=0.7, edge_color='gray')
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=6, font_weight='bold', labels=labels_for_nodes)
    
    title = title if title is not None else 'Concept Graph' if image_id is None else f'Image {image_id}'
    ax.set_title(title)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True)
    ax.invert_yaxis() # Match image coordinates
    ax.margins(x=0.2)  # Add inner padding (10% of data extent)
    
    return fig if ax is None else ax.figure  # Return the figure for further customization