import textwrap
import matplotlib.pyplot as plt
import networkx as nx
from RAG.query_search_service import RAG
import streamlit as st

def generate_flowchart(steps):
    """
    Generates a visually appealing flowchart from the steps using matplotlib and networkx.
    :param steps: List of strings in the format ["Step 1 - Masking Random Patches: Step Description", ...]
    :return: Matplotlib figure
    """
    # Helper function to wrap text for better display
    def wrap_text(text, width=30):
        return "\n".join(textwrap.wrap(text, width))

    # Initialize a directed graph
    G = nx.DiGraph()

    # Add nodes with wrapped labels
    for i, step in enumerate(steps):
        step_name, step_desc = step.split(":", 1)
        node_label = f"{wrap_text(step_name.strip())}\n{wrap_text(step_desc.strip())}"
        G.add_node(i + 1, label=node_label)

    # Add edges between nodes
    for i in range(len(steps) - 1):
        G.add_edge(i + 1, i + 2)

    # Create the flowchart layout
    pos = nx.spring_layout(G, seed=42)  # Use a seed for reproducibility

    # Create a Matplotlib figure
    fig, ax = plt.subplots(figsize=(16, 14))
    nx.draw_networkx_nodes(G, pos, node_size=12000, node_color="skyblue", ax=ax)
    nx.draw_networkx_edges(G, pos, arrowstyle="->", arrowsize=20, edge_color="gray", ax=ax)
    nx.draw_networkx_labels(
        G, pos, labels=nx.get_node_attributes(G, 'label'), font_size=8, font_family="sans-serif", font_color="black", ax=ax
    )
    ax.set_title("Generated Flowchart", fontsize=18, fontweight="bold", loc="center")
    ax.axis("off")
    return fig

# Initialize RAG
rag = RAG()

# Streamlit App
st.title("RAG Flowchart Generator")
st.write("Enter a query to generate a flowchart of the steps.")

# User input
query = st.text_input("Enter your query", placeholder="E.g., What are the steps in the BERT paper?")
if query:
    st.write("Query received. Processing...")

    # Chat history (if any) - Replace with your actual history handling logic
    chat_history = []

    # Generate steps
    try:
        steps_response = rag.get_steps(query, chat_history)
        st.write("Steps extracted successfully!")

        # Generate flowchart
        try:
            flowchart_fig = generate_flowchart(steps_response)
            st.pyplot(flowchart_fig)  # Display the Matplotlib flowchart
        except Exception as e:
            st.error(f"Error generating flowchart: {e}")

    except Exception as e:
        st.error(f"Error processing query: {e}")
