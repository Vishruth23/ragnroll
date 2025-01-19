import os
import streamlit as st
import random
from RAG.dynamicUpload import DynamicUpload
from RAG.query_search_service import RAG
from graphviz import Digraph
from RAG.load_pdfs import load_pdfs

# Initialize instances
if "rag" not in st.session_state:
    st.session_state["rag"] = RAG()

rag=st.session_state["rag"]

def generate_flowchart(file , steps):
    
    dot = Digraph()
    dot.attr(rankdir="TB", size="6,6")
    dot.attr(label=file, fontsize="20", labelloc="t")
    
    for step in steps:
        dot.node(step["step_name"], step["step_name"], tooltip=step["step_description"])
    
    for i in range(len(steps) - 1):
        dot.edge(steps[i]["step_name"], steps[i + 1]["step_name"])
    
    return dot

def display_responses():
    if st.session_state.get("messages") is not None:
        for msg in st.session_state["messages"]:

            if msg["user"]:
                st.chat_message("user").write(msg["user"])
            if msg["assistant"]:
                if msg["response_type"] == "FLOWCHART":
                    chart=generate_flowchart(msg["assistant"]["file"], msg["assistant"]["steps"])
                    st.chat_message("assistant").write("Generated Flowchart")
                    st.graphviz_chart(chart)
                else:
                    st.chat_message("assistant").write(msg["assistant"])


if(st.session_state.get("pdf_names") is None):
    st.session_state["pdf_names"] = load_pdfs(rag.session)

if(st.session_state.get("recommended_qs") is None):
    st.session_state["recommended_qs"] = ["Explain GPT-1"]

# Streamlit App Title
st.title("💬 Chatbot with Flowchart Support")
st.caption("🚀 A Streamlit chatbot powered by RAG")

if "pdf_names" not in st.session_state:
    st.session_state["pdf_names"] = []

if "selected_paper" not in st.session_state:
    st.session_state["selected_paper"] = None

if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"user": None, "assistant": "How can I help you?", "response_type":"TEXT"}
    ]

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
                uploader = DynamicUpload(temp_path,rag.session)
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



# Display recommended questions with direct execution on click
st.write("### 🤔 Recommended Questions")
if st.session_state.get("recommended_qs"):
    for idx, question in enumerate(st.session_state["recommended_qs"], start=1):
        if st.button(f"{idx}. {question}"):

            try:
                if(st.session_state.get("messages") is None):
                    chat_history=[]
                else:
                    chat_history = [
                {"user": f"{msg['user']}", "assistant": f"{msg['assistant']}"}
                for msg in st.session_state["messages"]
            ]
                    
            
                response_type, response = rag.query(question, chat_history[-1:-6:-1])

                if response_type == "TEXT":
                    st.session_state["messages"].append({"response_type":response_type,"user": question, "assistant": response})
                elif response_type == "FLOWCHART":
                    st.session_state["messages"].append({"response_type":response_type,"user": question, "assistant": response})
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
else:
    st.write("No recommended questions available at the moment.")

st.write("### 💬 Chat with Your Files")



col1, col2 = st.columns([4, 1])  

with col1:
    prompt = st.text_input("Type your question here...")

with col2:
    ask_button = st.button("Ask")

if prompt and ask_button:
    try:
            # Prepare chat history for RAG response
        if(st.session_state.get("messages") is None):
            chat_history=[]
        else:
            chat_history = [
                    {"user": f"{msg['user']}", "assistant": f"{msg['assistant']}"}
                    for msg in st.session_state["messages"]
                    ]
            print(chat_history)
        
        response_type, response = rag.query(prompt, chat_history[-1:-6:-1])

        if response_type == "TEXT":
            st.session_state["messages"].append({"response_type":response_type,"user": prompt, "assistant": response})
        elif response_type == "FLOWCHART":
            st.session_state["messages"].append({"response_type":response_type,"user": prompt, "assistant": response})
                
    except Exception as e:
        st.error(f"An error occurred: {e}")


display_responses()
