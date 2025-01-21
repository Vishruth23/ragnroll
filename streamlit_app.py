import os
import streamlit as st
from RAG.dynamicUpload import DynamicUpload
from RAG.query_search_service import RAG
from graphviz import Digraph
from RAG.load_pdfs import load_pdfs
import pandas as pd
import altair as alt

@st.cache_resource
def get_rag():
    return RAG()

rag = get_rag()

def generate_flowchart(file, steps):
    dot = Digraph()
    dot.attr(rankdir="TB", size="6,6")
    dot.attr(label=file, fontsize="20", labelloc="t")
    
    for step in steps:
        dot.node(step["step_name"], step["step_name"], tooltip=step["step_description"])
    
    for i in range(len(steps) - 1):
        dot.edge(steps[i]["step_name"], steps[i + 1]["step_name"])
    
    return dot

def query_flowchart():
    """Display a visually enhanced flowchart explaining the query process."""
    dot = Digraph()
    dot.attr(rankdir="TB", size="12,12")
    
    # Global node styles
    dot.attr('node', 
             fontname='Arial', 
             fontsize='16', 
             margin='0.3,0.2')
    dot.attr('edge', 
             fontname='Arial', 
             fontsize='14', 
             penwidth='2', 
             splines='ortho')
    
    # Define nodes with unique colors and shapes
    dot.node("A", "Start: Query Received", shape="ellipse", style="filled", fillcolor="#f9f9b7")
    dot.node("B", "_get_query_type", shape="parallelogram", style="filled", fillcolor="#cce5ff")
    dot.node("C", "Query Type?", shape="diamond", style="filled", fillcolor="#ffcccc")
    dot.node("D", "Retrieve Context\nwith LOCAL search", shape="rectangle", style="filled", fillcolor="#d9f7be")
    dot.node("E", "Retrieve Context\nwith GLOBAL search", shape="rectangle", style="filled", fillcolor="#ffe7ba")
    dot.node("F", "Retrieve Context\nwith both searches", shape="rectangle", style="filled", fillcolor="#ffd6e7")
    dot.node("G", "_get_steps", shape="parallelogram", style="filled", fillcolor="#cce5ff")
    dot.node("H", "_query_expansion", shape="rectangle", style="filled", fillcolor="#e8e8e8")
    dot.node("I", "Search through chunks", shape="rectangle", style="filled", fillcolor="#e6f7ff")
    dot.node("J", "_get_summary_context", shape="rectangle", style="filled", fillcolor="#e6f7ff")
    dot.node("K", "Get relevant file names", shape="rectangle", style="filled", fillcolor="#e6f7ff")
    dot.node("L", "Get Document Summaries", shape="rectangle", style="filled", fillcolor="#ffe7ba")
    dot.node("M", "Combine LOCAL & GLOBAL results", shape="rectangle", style="filled", fillcolor="#ffd6e7")
    dot.node("N", "Combine Results", shape="hexagon", style="filled", fillcolor="#d6f5f5")
    dot.node("O", "Process Steps for Flowchart", shape="parallelogram", style="filled", fillcolor="#cce5ff")
    dot.node("P", "Generate Completion", shape="rectangle", style="filled", fillcolor="#fffbcc")
    dot.node("Q", "Format Flowchart Response", shape="rectangle", style="filled", fillcolor="#e8e8e8")
    dot.node("R", "Return TEXT Response", shape="ellipse", style="filled", fillcolor="#d9f7be")
    dot.node("S", "Return FLOWCHART Response", shape="ellipse", style="filled", fillcolor="#ffd6e7")
    
    # Define edges
    dot.edges([
        ("A", "B"), ("B", "C"),
        ("C", "D"), ("C", "E"), ("C", "F"), ("C", "G"),
        ("D", "H"), ("H", "I"),
        ("E", "J"), ("J", "K"), ("K", "L"),
        ("F", "M"),
        ("I", "N"), ("L", "N"), ("M", "N"),
        ("G", "O"),
        ("N", "P"), ("P", "R"),
        ("O", "Q"), ("Q", "S")
    ])
    
    # Subgraphs with group styling
    with dot.subgraph(name="cluster_local") as local:
        local.attr(label="LOCAL Search", style="dashed", color="#85e085")
        local.node("D")
        local.node("H")
        local.node("I")
    
    with dot.subgraph(name="cluster_global") as global_:
        global_.attr(label="GLOBAL Search", style="dashed", color="#ff9999")
        global_.node("E")
        global_.node("J")
        global_.node("K")
        global_.node("L")
    
    with dot.subgraph(name="cluster_response") as response:
        response.attr(label="Response Generation", style="dashed", color="#9999ff")
        response.node("P")
        response.node("Q")
        response.node("R")
        response.node("S")
    
    # Display the flowchart
    st.graphviz_chart(dot.source)

def create_dynamic_upload_flowchart():
    """
    Creates a visually enhanced flowchart visualization of the dynamic PDF upload process.
    """
    dot = Digraph()
    dot.attr(rankdir="TB", size="12,12")
    
    # Global node styling
    dot.attr('node', 
             shape='rectangle', 
             style='rounded,filled', 
             fontname='Arial',
             fontsize='16', 
             margin='0.5,0.3')
    dot.attr('edge', 
             fontname='Arial', 
             fontsize='14', 
             penwidth='2', 
             splines='ortho')
    
    # Define nodes with custom colors
    dot.node("A", "Start:\nPDF Upload", shape="ellipse", fillcolor="#f9f9b7")
    dot.node("B", "Check PDF\nin Stage", shape="parallelogram", fillcolor="#cce5ff")
    dot.node("C", "Insert PDF\nto Stage", shape="rectangle", fillcolor="#d9f7be")
    dot.node("D", "Return:\nSKIPPED UPLOAD", shape="ellipse", fillcolor="#ffd6e7")
    dot.node("E", "Parse PDF to\nMarkdown Format", shape="rectangle", fillcolor="#ffe7ba")
    dot.node("F", "Split Markdown\ninto Chunks", shape="rectangle", fillcolor="#ffcccc")
    dot.node("G", "Store in\nPARSED_PDFS_CHUNKS", shape="rectangle", fillcolor="#d6f5f5")
    dot.node("H", "Generate\nSummary", shape="rectangle", fillcolor="#e6f7ff")
    dot.node("I", "Store in\nPDF_SUMMARIES", shape="rectangle", fillcolor="#cce5ff")
    dot.node("J", "Retrieve\nSummary", shape="rectangle", fillcolor="#ffe7ba")
    dot.node("K", "Generate Caption\nusing LLM", shape="rectangle", fillcolor="#e8e8e8")
    dot.node("L", "Store in\nPDF_CAPTIONS", shape="rectangle", fillcolor="#ffd6e7")
    dot.node("M", "Return:\nSUCCESS", shape="ellipse", fillcolor="#d9f7be")
    
    # Define edges
    dot.edge("A", "B")
    dot.edge("B", "C", label="New PDF")
    dot.edge("B", "D", label="Existing PDF")
    dot.edge("C", "E")
    dot.edge("E", "F")
    dot.edge("F", "G")
    dot.edge("G", "H")
    dot.edge("H", "I")
    dot.edge("I", "J")
    dot.edge("J", "K")
    dot.edge("K", "L")
    dot.edge("L", "M")
    
    # Subgraphs for logical grouping
    with dot.subgraph(name="cluster_content_processing") as content:
        content.attr(label="Content Processing", style="dashed", color="#85e085")
        for node in ["E", "F", "G", "H", "I"]:
            content.node(node)
    
    with dot.subgraph(name="cluster_caption_generation") as caption:
        caption.attr(label="Caption Generation", style="dashed", color="#9999ff")
        for node in ["J", "K", "L"]:
            caption.node(node)
    
    # Display flowchart
    st.graphviz_chart(dot.source, use_container_width=True)

    


def display_responses():
    if st.session_state.get("messages") is not None:
        for msg in st.session_state["messages"]:
            if msg["user"]:
                st.chat_message("user").write(msg["user"])
            if msg["assistant"]:
                if msg["response_type"] == "FLOWCHART":
                    chart = generate_flowchart(msg["assistant"]["file"], msg["assistant"]["steps"])
                    st.chat_message("assistant").write("Generated Flowchart")
                    st.graphviz_chart(chart)
                else:
                    st.chat_message("assistant").write(msg["assistant"])

# Initialize session state variables
if "pdf_names" not in st.session_state:
    st.session_state["pdf_names"] = load_pdfs(rag.session)

if "recommended_qs" not in st.session_state:
    with st.spinner("Loading recommended questions..."):
        st.session_state["recommended_qs"] = rag.get_recommended_questions()

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"user": None, "assistant": "How can I help you?", "response_type": "TEXT"}
    ]

tab1,tab2,tab3=st.tabs(["Chatbot","Process","TruLens statistics"])

# Display content based on the selected page
with tab1:
    st.title("💬 Chatbot with Flowchart Support")
    st.caption("🚀 A Streamlit chatbot powered by RAG")
    
    with st.sidebar:
        st.header("📂 Upload Files")
        uploaded_files = st.file_uploader("Upload one or more PDF files", type="pdf", accept_multiple_files=True)

        if uploaded_files:
            for uploaded_file in uploaded_files:
                # Save uploaded files to temp directory
                temp_dir = "temp"
                os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.read())

                # Process the file using DynamicUpload
                try:
                    uploader = DynamicUpload(temp_path, rag.session)
                    with st.spinner(f"Processing {uploaded_file.name}..."):
                        uploader.upload_pdf()
                    st.session_state["uploaded_files"].append(uploaded_file.name)
                    st.session_state["pdf_names"].append(uploaded_file.name)
                    st.success(f"Processed: {uploaded_file.name}")
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {e}")

        st.header("📂 Uploaded PDFs")
        if st.session_state["pdf_names"]:
            for pdf_name in st.session_state["pdf_names"]:
                st.write(pdf_name)
        else:
            st.write("No PDFs uploaded yet.")

    st.write("### 🤔 Recommended Questions")
    if st.session_state.get("recommended_qs"):
        for idx, question in enumerate(st.session_state["recommended_qs"], start=1):
            if st.button(f"{idx}. {question}"):
                try:
                    chat_history = st.session_state.get("messages", [])
                    with st.spinner(f"Querying: {question}..."):
                        response_type, response = rag.query(question, chat_history[-1:-6:-1])
                    st.session_state["messages"].append({"response_type": response_type, "user": question, "assistant": response})
                except Exception as e:
                    st.error(f"An error occurred: {e}")
    else:
        st.write("No recommended questions available at the moment.")

    st.write("### 💬 Chat with Your Files")
    if prompt := st.chat_input("Type your question here..."):
        try:
            chat_history = st.session_state.get("messages", [])
            with st.spinner(f"Querying: {prompt}..."):
                response_type, response = rag.query(prompt, chat_history[-1:-6:-1])
            st.session_state["messages"].append({"response_type": response_type, "user": prompt, "assistant": response})
        except Exception as e:
            st.error(f"An error occurred: {e}")

    display_responses()

with tab2:
    st.title("Process")
    st.header("Query Process")
    query_flowchart()
    st.header("Dynamic PDF Upload Process")
    create_dynamic_upload_flowchart()

with tab3:
    st.title("TruLens Statistics")
    
    # Data preparation received by running test.py
    data = {
        "app_name": ["Custom_RAG", "RAG"],
        "Answer Relevance": [0.888889, 0.711088],
        "Context Relevance": [0.622985, 0.483073],
        "latency": [15.512015, 3.906506],
        "total_cost": [0.4200, 0.152137],
    }

    df = pd.DataFrame(data)

    st.title("RAG Comparison Metrics")
    st.subheader("Raw Data")
    st.dataframe(df)

    st.subheader("Visualizations")

    st.markdown("### Answer Relevance & Context Relevance")
    
    relevance_data = df.melt(
        id_vars=['app_name'],
        value_vars=['Answer Relevance', 'Context Relevance'],
        var_name='Metric',
        value_name='Value'
    )
    
    relevance_chart = alt.Chart(relevance_data).mark_bar().encode(
        x=alt.X('app_name:N', 
                title='Application',
                axis=alt.Axis(labelAngle=0)),  
        y=alt.Y('Value:Q', title='Score'),
        color=alt.Color('Metric:N', title='Metric Type'),
        tooltip=['app_name', 'Metric', 'Value']
    ).properties(
        height=300
    )
    
    st.altair_chart(relevance_chart, use_container_width=True)

    # Latency Comparison
    st.markdown("### Latency Comparison")
    latency_chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('app_name:N', 
                title='Application',
                axis=alt.Axis(labelAngle=0)),  
        y=alt.Y('latency:Q', title='Latency (seconds)'),
        color=alt.value('#1f77b4'),  
        tooltip=['app_name', 'latency']
    ).properties(
        height=300
    )
    
    st.altair_chart(latency_chart, use_container_width=True)

    # Total Cost Comparison
    st.markdown("### Total Cost Comparison")
    cost_chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('app_name:N', 
                title='Application',
                axis=alt.Axis(labelAngle=0)),  
        y=alt.Y('total_cost:Q', title='Total Cost ($)'),
        color=alt.value('#2ca02c'),  
        tooltip=['app_name', 'total_cost']
    ).properties(
        height=300
    )
    
    st.altair_chart(cost_chart, use_container_width=True)

