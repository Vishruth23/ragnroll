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
    """Display a static flowchart explaining the query process."""
    dot = Digraph()
    dot.attr(rankdir="TB", size="12,12")
    
    # Define nodes
    dot.node("A", "Start: Query Received")
    dot.node("B", "_get_query_type")
    dot.node("C", "Query Type?")
    dot.node("D", "Retrieve Context\nwith LOCAL search")
    dot.node("E", "Retrieve Context\nwith GLOBAL search")
    dot.node("F", "Retrieve Context\nwith both searches")
    dot.node("G", "_get_steps")
    dot.node("H", "_query_expansion")
    dot.node("I", "Search through chunks")
    dot.node("J", "_get_summary_context")
    dot.node("K", "Get relevant file names")
    dot.node("L", "Get Document Summaries")
    dot.node("M", "Combine LOCAL & GLOBAL results")
    dot.node("N", "Combine Results")
    dot.node("O", "Process Steps for Flowchart")
    dot.node("P", "Generate Completion")
    dot.node("Q", "Format Flowchart Response")
    dot.node("R", "Return TEXT Response")
    dot.node("S", "Return FLOWCHART Response")
    
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
    
    # Subgraphs for grouping
    with dot.subgraph(name="cluster_local") as local:
        local.attr(label="LOCAL Search", style="dashed")
        local.node("D")
        local.node("H")
        local.node("I")
    
    with dot.subgraph(name="cluster_global") as global_:
        global_.attr(label="GLOBAL Search", style="dashed")
        global_.node("E")
        global_.node("J")
        global_.node("K")
        global_.node("L")
    
    with dot.subgraph(name="cluster_response") as response:
        response.attr(label="Response Generation", style="dashed")
        response.node("P")
        response.node("Q")
        response.node("R")
        response.node("S")
    
    # Display the flowchart
    st.graphviz_chart(dot.source)

def create_dynamic_upload_flowchart():
    """
    Creates a large horizontally spaced flowchart visualization of the dynamic PDF upload process.
    """
    dot = Digraph()
    # Increased size parameters
    dot.attr(rankdir="LR", size="16,16")  # Increased from 12,12 to 16,16
    
    # Global node styling with larger dimensions
    dot.attr('node', 
            shape='rectangle', 
            style='rounded,filled', 
            fillcolor='white',
            fontname='Arial',
            fontsize='16',  # Increased from 14
            margin='0.5,0.3',  # Increased margins
            width='2.5',  # Added width
            height='1.2')  # Added height
    
    # Edge styling with larger font
    dot.attr('edge', 
            fontname='Arial', 
            fontsize='14',  # Increased from 12
            penwidth='2.0',  # Added thicker lines
            splines='ortho')
    
    # Define nodes with clearer labels
    dot.node("A", "Start:\nPDF Upload")
    dot.node("B", "Check PDF\nin Stage")
    dot.node("C", "Insert PDF\nto Stage")
    dot.node("D", "Return:\nSKIPPED UPLOAD")
    
    # Content processing nodes
    dot.node("E", "Parse PDF to\nMarkdown Format")
    dot.node("F", "Split Markdown\ninto Chunks")
    dot.node("G", "Store in\nPARSED_PDFS_CHUNKS")
    dot.node("H", "Generate\nSummary")
    dot.node("I", "Store in\nPDF_SUMMARIES")
    
    # Caption generation nodes
    dot.node("J", "Retrieve\nSummary")
    dot.node("K", "Generate Caption\nusing LLM")
    dot.node("L", "Store in\nPDF_CAPTIONS")
    dot.node("M", "Return:\nSUCCESS")
    
    # Define edges with better spacing
    dot.edge("A", "B")
    dot.edge("B", "C", "New PDF")
    dot.edge("B", "D", "Existing PDF")
    dot.edge("C", "E")
    dot.edge("E", "F")
    dot.edge("F", "G")
    dot.edge("G", "H")
    dot.edge("H", "I")
    dot.edge("I", "J")
    dot.edge("J", "K")
    dot.edge("K", "L")
    dot.edge("L", "M")
    
    # Create subgraphs with improved styling and larger margins
    with dot.subgraph(name="cluster_content_processing") as content:
        content.attr(label="Content Processing", 
                    style='rounded,filled',
                    fillcolor='#f5f5f5',
                    fontname='Arial',
                    fontsize='18',  # Increased from 16
                    margin='30')    # Increased from 20
        for node in ["F", "G", "H", "I"]:
            content.node(node)
    
    with dot.subgraph(name="cluster_caption_generation") as caption:
        caption.attr(label="Caption Generation",
                    style='rounded,filled',
                    fillcolor='#f0f0f0',
                    fontname='Arial',
                    fontsize='18',  # Increased from 16
                    margin='30')    # Increased from 20
        for node in ["J", "K", "L"]:
            caption.node(node)
    
    # Display with larger size in Streamlit
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
    
    # Data preparation
    data = {
        "app_name": ["Custom_RAG", "RAG"],
        "Answer Relevance": [0.888889, 0.721088],
        "Context Relevance": [0.562985, 0.494898],
        "latency": [18.512015, 3.846506],
        "total_cost": [0.421227, 0.139134],
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

