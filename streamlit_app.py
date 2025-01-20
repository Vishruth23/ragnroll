import os
import streamlit as st
import random
from RAG.dynamicUpload import DynamicUpload
from RAG.query_search_service import RAG
from graphviz import Digraph
from RAG.load_pdfs import load_pdfs

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
    dot.attr(rankdir="TB", size="8,8")
    
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
    dot.node("K", "_get_names")
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

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Chatbot", "Query Flowchart"])

# Display content based on the selected page
if page == "Chatbot":
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

elif page == "Query Flowchart":
    st.title("Query Flowchart")
    st.write("This flowchart illustrates how a query is processed.")
    query_flowchart()
