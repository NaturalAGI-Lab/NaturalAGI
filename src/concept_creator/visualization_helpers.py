import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any, Optional
import numpy as np


class ConceptVisualization:
    def __init__(self, figsize=(15, 10)):
        self.figsize = figsize
        self.node_colors = {
            "StartPoint": "#FF5733",  # Red-orange
            "CornerPoint": "#33FF57",  # Green
            "EndPoint": "#3357FF",  # Blue
            "Normal": "#DDDDDD",  # Light gray
            "HorizontalVector": "#FFC300",  # Yellow
            "VerticalVector": "#FF5733",  # Red-orange
        }
        self.edge_color = "#666666"  # Dark gray

    def visualize_graph(
        self, G: nx.Graph, title: str = "Graph Visualization", pos=None, ax=None
    ):
        """
        Visualize a single graph with node types colored differently.
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize)

        if pos is None:
            pos = nx.spring_layout(G, seed=42)

        # Determine node colors based on labels or type
        node_colors = []
        for node in G.nodes():
            if "labels" in G.nodes[node]:
                for label in G.nodes[node]["labels"]:
                    if label in self.node_colors:
                        node_colors.append(self.node_colors[label])
                        break
                else:
                    node_colors.append(self.node_colors["Normal"])
            elif "type" in G.nodes[node]:
                node_type = G.nodes[node]["type"]
                node_colors.append(
                    self.node_colors.get(node_type, self.node_colors["Normal"])
                )
            else:
                node_colors.append(self.node_colors["Normal"])

        # Draw the graph
        nx.draw_networkx_nodes(
            G, pos, node_color=node_colors, node_size=500, alpha=0.8, ax=ax
        )
        nx.draw_networkx_edges(
            G, pos, edge_color=self.edge_color, width=1.5, alpha=0.7, ax=ax
        )
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold", ax=ax)

        ax.set_title(title, fontsize=16)
        ax.axis("off")

        return pos, ax

    def visualize_concept_evolution(self, graphs: List[nx.Graph], titles: List[str]):
        """
        Visualize the evolution of a concept graph across multiple steps.
        """
        n = len(graphs)
        fig, axes = plt.subplots(1, n, figsize=(self.figsize[0] * n, self.figsize[1]))

        if n == 1:
            axes = [axes]

        # Try to maintain consistent layouts across visualizations
        pos = nx.spring_layout(graphs[0], seed=42)

        for i, (graph, title) in enumerate(zip(graphs, titles)):
            pos, _ = self.visualize_graph(graph, title, pos=pos, ax=axes[i])

        plt.tight_layout()
        return fig

    def visualize_matching(
        self,
        G: nx.Graph,
        H: nx.Graph,
        G_to_match: Dict,
        H_to_match: Dict,
        title_G: str = "Graph G",
        title_H: str = "Graph H",
    ):
        """
        Visualize two graphs with matching nodes highlighted.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.figsize)

        # Position nodes in similar arrangements
        pos_G = nx.spring_layout(G, seed=42)
        pos_H = nx.spring_layout(H, seed=42)

        # Draw base graphs
        self.visualize_graph(G, title_G, pos=pos_G, ax=ax1)
        self.visualize_graph(H, title_H, pos=pos_H, ax=ax2)

        # Highlight matching nodes
        match_nodes_G = list(G_to_match.keys())
        match_nodes_H = list(H_to_match.keys())

        nx.draw_networkx_nodes(
            G,
            pos_G,
            nodelist=match_nodes_G,
            node_color="yellow",
            node_size=700,
            alpha=0.5,
            ax=ax1,
        )
        nx.draw_networkx_nodes(
            H,
            pos_H,
            nodelist=match_nodes_H,
            node_color="yellow",
            node_size=700,
            alpha=0.5,
            ax=ax2,
        )

        plt.tight_layout()
        return fig

    def visualize_contractions(
        self,
        G: nx.Graph,
        contractions: List[Tuple],
        title: str = "Graph with Contractions",
    ):
        """
        Visualize a graph with contracted node pairs highlighted.
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        pos = nx.spring_layout(G, seed=42)

        # Draw base graph
        self.visualize_graph(G, title, pos=pos, ax=ax)

        # Highlight nodes to be contracted
        contraction_nodes = []
        for contraction in contractions:
            contraction_nodes.extend([contraction[0], contraction[2]])

        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=contraction_nodes,
            node_color=self.node_colors["Contraction"],
            node_size=700,
            alpha=0.7,
            ax=ax,
        )

        # Draw edges between nodes to be contracted
        contraction_edges = []
        for contraction in contractions:
            g_node, _, h_node, _ = contraction
            if G.has_edge(g_node, h_node):
                contraction_edges.append((g_node, h_node))

        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=contraction_edges,
            edge_color="red",
            width=3,
            alpha=0.7,
            ax=ax,
        )

        plt.tight_layout()
        return fig

    def visualize_mcm_process(
        self,
        G: nx.Graph,
        H: nx.Graph,
        mcm: nx.Graph,
        G_to_mcm: Dict,
        H_to_mcm: Dict,
        contractions: List[Tuple],
    ):
        """
        Comprehensive visualization of the Maximum Common Minor process.
        """
        fig = plt.figure(figsize=(self.figsize[0] * 2, self.figsize[1] * 2))

        # Original graphs
        ax1 = fig.add_subplot(2, 2, 1)
        pos_G = nx.spring_layout(G, seed=42)
        self.visualize_graph(G, "Input Graph G", pos=pos_G, ax=ax1)

        ax2 = fig.add_subplot(2, 2, 2)
        pos_H = nx.spring_layout(H, seed=42)
        self.visualize_graph(H, "Input Graph H", pos=pos_H, ax=ax2)

        # Highlight matching nodes
        match_nodes_G = list(G_to_mcm.keys())
        match_nodes_H = list(H_to_mcm.keys())

        nx.draw_networkx_nodes(
            G,
            pos_G,
            nodelist=match_nodes_G,
            node_color="yellow",
            node_size=700,
            alpha=0.5,
            ax=ax1,
        )
        nx.draw_networkx_nodes(
            H,
            pos_H,
            nodelist=match_nodes_H,
            node_color="yellow",
            node_size=700,
            alpha=0.5,
            ax=ax2,
        )

        # Maximum Common Minor
        ax3 = fig.add_subplot(2, 2, 3)
        pos_mcm = nx.spring_layout(mcm, seed=42)
        self.visualize_graph(mcm, "Maximum Common Minor Graph", pos=pos_mcm, ax=ax3)

        # Contractions visualization
        ax4 = fig.add_subplot(2, 2, 4)
        if contractions:
            # Create a combined graph with all contracted nodes
            combined = nx.Graph()
            combined.add_nodes_from(G.nodes(data=True))
            combined.add_nodes_from(H.nodes(data=True))
            combined.add_edges_from(G.edges(data=True))
            combined.add_edges_from(H.edges(data=True))

            pos_combined = nx.spring_layout(combined, seed=42)
            self.visualize_graph(combined, "Contractions", pos=pos_combined, ax=ax4)

            # Highlight contraction pairs
            for g_node, _, h_node, _ in contractions:
                if g_node in combined and h_node in combined:
                    nx.draw_networkx_nodes(
                        combined,
                        pos_combined,
                        nodelist=[g_node, h_node],
                        node_color=self.node_colors["Contraction"],
                        node_size=700,
                        alpha=0.7,
                        ax=ax4,
                    )

                    # Draw edge between contracted nodes
                    nx.draw_networkx_edges(
                        combined,
                        pos_combined,
                        edgelist=[(g_node, h_node)],
                        edge_color="red",
                        width=3,
                        style="dashed",
                        alpha=0.7,
                        ax=ax4,
                    )
        else:
            ax4.text(
                0.5,
                0.5,
                "No contractions found",
                horizontalalignment="center",
                verticalalignment="center",
                transform=ax4.transAxes,
                fontsize=14,
            )
            ax4.axis("off")

        plt.tight_layout()
        return fig

    def visualize_concept_creation_step(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        new_concept: nx.Graph,
        step_number: int,
    ):
        """
        Visualize a single step in the concept creation process.
        """
        fig = plt.figure(figsize=(self.figsize[0] * 1.5, self.figsize[1]))

        # Current concept graph
        ax1 = fig.add_subplot(1, 3, 1)
        self.visualize_graph(
            concept_graph, f"Concept Graph (Step {step_number-1})", ax=ax1
        )

        # New image graph
        ax2 = fig.add_subplot(1, 3, 2)
        self.visualize_graph(image_graph, f"Image Graph {step_number}", ax=ax2)

        # Resulting concept graph
        ax3 = fig.add_subplot(1, 3, 3)
        self.visualize_graph(
            new_concept, f"Updated Concept (Step {step_number})", ax=ax3
        )

        plt.tight_layout()
        return fig

    def create_property_diff_table(
        self,
        original_graph: nx.Graph,
        updated_graph: nx.Graph,
        node_mapping: Optional[Dict] = None,
    ):
        """
        Create a table showing property differences between corresponding nodes
        in the original and updated graphs.

        Args:
            original_graph: The graph before changes
            updated_graph: The graph after changes
            node_mapping: Optional mapping from original_graph nodes to updated_graph nodes.
                          If None, assumes nodes have the same IDs in both graphs.

        Returns:
            A matplotlib figure containing the property diff table
        """
        # Collect all properties and changes
        changes = []

        # If no mapping provided, create a direct mapping for nodes that exist in both graphs
        if node_mapping is None:
            node_mapping = {}
            for node in original_graph.nodes():
                if node in updated_graph:
                    node_mapping[node] = node

        # For each node in the original graph
        for orig_node, updated_node in node_mapping.items():
            # Skip if node doesn't exist in either graph
            if orig_node not in original_graph or updated_node not in updated_graph:
                continue

            orig_props = original_graph.nodes[orig_node]
            updated_props = updated_graph.nodes[updated_node]

            # Find all properties in either node
            all_props = set(orig_props.keys()) | set(updated_props.keys())

            for prop in all_props:
                orig_value = orig_props.get(prop, "(not present)")
                updated_value = updated_props.get(prop, "(not present)")

                # Only record if there's a change
                if orig_value != updated_value:
                    # Convert lists to strings for display
                    if isinstance(orig_value, list):
                        orig_value = ", ".join(map(str, orig_value))
                    if isinstance(updated_value, list):
                        updated_value = ", ".join(map(str, updated_value))

                    # Truncate long values
                    if isinstance(orig_value, str) and len(orig_value) > 20:
                        orig_value = orig_value[:17] + "..."
                    if isinstance(updated_value, str) and len(updated_value) > 20:
                        updated_value = updated_value[:17] + "..."

                    changes.append(
                        {
                            "Node (Original)": orig_node,
                            "Node (Updated)": updated_node,
                            "Property": prop,
                            "Original Value": orig_value,
                            "Updated Value": updated_value,
                        }
                    )

        # If no changes found
        if not changes:
            fig, ax = plt.subplots(figsize=(10, 2))
            ax.text(
                0.5,
                0.5,
                "No property changes detected",
                ha="center",
                va="center",
                fontsize=14,
            )
            ax.axis("off")
            return fig

        # Create a figure for the table
        fig, ax = plt.subplots(figsize=(12, max(2, min(20, 0.5 * len(changes)))))
        ax.axis("off")

        # Create table data
        headers = [
            "Node (Original)",
            "Node (Updated)",
            "Property",
            "Original Value",
            "Updated Value",
        ]
        rows = [[change[header] for header in headers] for change in changes]

        # Create the table
        table = ax.table(
            cellText=rows,
            colLabels=headers,
            loc="center",
            cellLoc="center",
            colColours=["#f0f0f0"] * len(headers),
        )

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)

        for (i, j), cell in table.get_celld().items():
            if i == 0:  # Header row
                cell.set_text_props(weight="bold")
            cell.set_height(0.15)

            # Highlight changes in property values
            if j == 4 and i > 0:  # Updated Value column
                cell.set_facecolor("#ffedcc")  # Light yellow

        plt.title("Property Changes Between Graphs", fontsize=14)
        plt.tight_layout()

        return fig

    def visualize_concept_creation_with_props(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        new_concept: nx.Graph,
        concept_to_new: Dict,
        step_number: int,
    ):
        """
        Visualize a concept creation step with property differences.

        Args:
            concept_graph: The concept graph before the step
            image_graph: The image graph being processed
            new_concept: The updated concept graph after the step
            concept_to_new: Mapping from concept_graph nodes to new_concept nodes
            step_number: Current step number

        Returns:
            A matplotlib figure with the visualization
        """
        # Create a figure with 2 rows
        fig = plt.figure(figsize=(self.figsize[0] * 1.5, self.figsize[1] * 2))

        # Top row: graph visualizations
        ax1 = fig.add_subplot(2, 3, 1)
        self.visualize_graph(
            concept_graph, f"Concept Graph (Step {step_number-1})", ax=ax1
        )

        ax2 = fig.add_subplot(2, 3, 2)
        self.visualize_graph(image_graph, f"Image Graph {step_number}", ax=ax2)

        ax3 = fig.add_subplot(2, 3, 3)
        self.visualize_graph(
            new_concept, f"Updated Concept (Step {step_number})", ax=ax3
        )

        # Bottom row: property changes table
        ax4 = fig.add_subplot(2, 1, 2)

        # Create property diff table
        changes = []

        # For each node in the mapping
        for orig_node, updated_node in concept_to_new.items():
            # Skip if node doesn't exist
            if orig_node not in concept_graph or updated_node not in new_concept:
                continue

            orig_props = concept_graph.nodes[orig_node]
            updated_props = new_concept.nodes[updated_node]

            # Find all properties in either node
            all_props = set(orig_props.keys()) | set(updated_props.keys())

            for prop in all_props:
                orig_value = orig_props.get(prop, "(not present)")
                updated_value = updated_props.get(prop, "(not present)")

                # Only record if there's a change
                if orig_value != updated_value:
                    # Convert lists to strings for display
                    if isinstance(orig_value, list):
                        orig_value = ", ".join(map(str, orig_value))
                    if isinstance(updated_value, list):
                        updated_value = ", ".join(map(str, updated_value))

                    # Truncate long values
                    if isinstance(orig_value, str) and len(orig_value) > 15:
                        orig_value = orig_value[:12] + "..."
                    if isinstance(updated_value, str) and len(updated_value) > 15:
                        updated_value = updated_value[:12] + "..."

                    changes.append(
                        [
                            f"{orig_node} → {updated_node}",
                            prop,
                            str(orig_value),
                            str(updated_value),
                        ]
                    )

        # If no changes found
        if not changes:
            ax4.text(
                0.5,
                0.5,
                "No property changes detected in this step",
                ha="center",
                va="center",
                fontsize=14,
            )
            ax4.axis("off")
        else:
            # Create the table
            headers = ["Node Mapping", "Property", "Original Value", "Updated Value"]

            ax4.axis("off")
            table = ax4.table(
                cellText=changes,
                colLabels=headers,
                loc="center",
                cellLoc="center",
                colColours=["#f0f0f0"] * len(headers),
            )

            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1.2, 1.2)

            for (i, j), cell in table.get_celld().items():
                if i == 0:  # Header row
                    cell.set_text_props(weight="bold")
                cell.set_height(0.1)

                # Highlight changes in property values
                if j == 3 and i > 0:  # Updated Value column
                    cell.set_facecolor("#ffedcc")  # Light yellow

        plt.suptitle(
            f"Concept Creation Step {step_number} with Property Changes", fontsize=16
        )
        plt.tight_layout()

        return fig

    def create_property_comparison_table(
        self,
        concept_graph: nx.Graph,
        image_graph: nx.Graph,
        new_concept: nx.Graph,
        concept_to_mcm: Dict,
        image_to_mcm: Dict,
    ):
        """
        Create a table showing property values from concept, image, and resulting MCM side by side.
        """
        # Collect all property comparisons
        comparisons = []

        # Create inverse mapping for easier lookup
        mcm_to_concept = {v: k for k, v in concept_to_mcm.items()}
        mcm_to_image = {v: k for k, v in image_to_mcm.items()}

        # For each node in the MCM graph
        for mcm_node in new_concept.nodes():
            concept_node = mcm_to_concept.get(mcm_node)
            image_node = mcm_to_image.get(mcm_node)

            # Skip if node doesn't exist in both source graphs
            if not (concept_node and image_node):
                continue

            # Get properties from all three graphs
            concept_props = (
                concept_graph.nodes[concept_node]
                if concept_node in concept_graph
                else {}
            )
            image_props = (
                image_graph.nodes[image_node] if image_node in image_graph else {}
            )
            mcm_props = new_concept.nodes[mcm_node]

            # Find all properties in any of the three nodes
            all_props = (
                set(concept_props.keys())
                | set(image_props.keys())
                | set(mcm_props.keys())
            )

            for prop in all_props:
                # Get values from each graph (with defaults if missing)
                concept_value = concept_props.get(prop, "(not present)")
                image_value = image_props.get(prop, "(not present)")
                mcm_value = mcm_props.get(prop, "(not present)")

                # Only include if there's some difference
                if not (concept_value == image_value == mcm_value):
                    # Format for display
                    concept_display = self._format_property_value(
                        concept_value, max_len=15
                    )
                    image_display = self._format_property_value(image_value, max_len=15)
                    mcm_display = self._format_property_value(mcm_value, max_len=15)

                    # Determine which source contributed to the final value
                    status = "unchanged"
                    if mcm_value == concept_value and mcm_value != image_value:
                        status = "kept_concept"
                    elif mcm_value == image_value and mcm_value != concept_value:
                        status = "used_image"
                    elif mcm_value != concept_value and mcm_value != image_value:
                        status = "merged"

                    comparisons.append(
                        {
                            "MCM Node": mcm_node,
                            "Concept Node": concept_node,
                            "Image Node": image_node,
                            "Property": prop,
                            "Concept Value": concept_display,
                            "Image Value": image_display,
                            "Final Value": mcm_display,
                            "Status": status,
                        }
                    )

        # If no comparisons found
        if not comparisons:
            fig, ax = plt.subplots(figsize=(10, 2))
            ax.text(
                0.5,
                0.5,
                "No property differences detected",
                ha="center",
                va="center",
                fontsize=14,
            )
            ax.axis("off")
            return fig

        # Sort comparisons by status and property for better readability
        comparisons.sort(key=lambda x: (x["Status"], x["Property"]))

        # Create a figure for the table
        fig, ax = plt.subplots(figsize=(14, max(2, min(20, 0.6 * len(comparisons)))))
        ax.axis("off")

        # Create table data
        headers = [
            "MCM Node",
            "Concept Node",
            "Image Node",
            "Property",
            "Concept Value",
            "Image Value",
            "Final Value",
            "Decision",
        ]
        rows = []

        for comp in comparisons:
            # Convert status to readable decision
            if comp["Status"] == "kept_concept":
                decision = "Kept concept"
            elif comp["Status"] == "used_image":
                decision = "Used image"
            elif comp["Status"] == "merged":
                decision = "Merged/Modified"
            else:
                decision = "No change"

            row = [
                comp["MCM Node"],
                comp["Concept Node"],
                comp["Image Node"],
                comp["Property"],
                comp["Concept Value"],
                comp["Image Value"],
                comp["Final Value"],
                decision,
            ]
            rows.append(row)

        # Create the table
        table = ax.table(
            cellText=rows,
            colLabels=headers,
            loc="center",
            cellLoc="center",
            colColours=["#f0f0f0"] * len(headers),
        )

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)

        # Format cells
        for (i, j), cell in table.get_celld().items():
            if i == 0:  # Header row
                cell.set_text_props(weight="bold")
            cell.set_height(0.15)

            if i > 0:
                # Highlight value columns
                if j == 4:  # Concept Value
                    cell.set_facecolor("#e6f2ff")  # Light blue
                elif j == 5:  # Image Value
                    cell.set_facecolor("#fff2e6")  # Light orange
                elif j == 6:  # Final Value
                    cell.set_facecolor("#e6ffe6")  # Light green

                # Highlight decision column based on outcome
                if j == 7:  # Decision column
                    decision = rows[i - 1][7]
                    if decision == "Kept concept":
                        cell.set_facecolor("#e6f2ff")  # Light blue to match concept
                    elif decision == "Used image":
                        cell.set_facecolor("#fff2e6")  # Light orange to match image
                    elif decision == "Merged/Modified":
                        cell.set_facecolor("#ffedff")  # Light purple for merged
                    else:
                        cell.set_facecolor("#f9f9f9")  # Light gray for no change

        # Add a legend for the color scheme
        legend_ax = fig.add_axes([0.02, 0.02, 0.25, 0.1])  # Position in bottom left
        legend_ax.axis("off")

        legend_items = [
            ("Concept Value", "#e6f2ff"),
            ("Image Value", "#fff2e6"),
            ("Final Value", "#e6ffe6"),
            ("Merged/Modified", "#ffedff"),
        ]

        for i, (label, color) in enumerate(legend_items):
            legend_ax.add_patch(
                plt.Rectangle(
                    (i * 0.25, 0), 0.02, 0.02, facecolor=color, edgecolor="black"
                )
            )
            legend_ax.text(i * 0.25 + 0.025, 0, label, fontsize=8, va="center")

        plt.title("Property Comparison: Concept vs Image vs Final", fontsize=14)
        plt.tight_layout()

        return fig

    def _format_property_value(self, value, max_len=15):
        """Helper to format property values for display"""
        if isinstance(value, list):
            formatted = ", ".join(map(str, value))
        else:
            formatted = str(value)

        # Truncate long values
        if len(formatted) > max_len:
            formatted = formatted[: max_len - 3] + "..."

        return formatted
