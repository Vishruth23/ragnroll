import os
import streamlit as st
import random
from RAG.dynamicUpload import DynamicUpload
from RAG.query_search_service import RAG

rag = RAG()

# Streamlit App Title
st.title("💬 Chatbot")
st.caption("🚀 A Streamlit chatbot powered by RAG")

# File Upload Widget
st.header("📂 Upload Files")
if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []

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
            uploader = DynamicUpload(temp_path)
            uploader.upload_pdf()
            st.session_state["uploaded_files"].append(uploaded_file.name)
            st.session_state["selected_paper"] = uploaded_file.name
            st.success(f"Processed: {uploaded_file.name}")
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

if "pdf_names" not in st.session_state:
    st.session_state["pdf_names"] = []

if "selected_paper" not in st.session_state:
    st.session_state["selected_paper"] = None

def refresh_uploaded_pdfs():
    uploader = DynamicUpload("")  # Create an instance with no specific PDF
    try:
        res = uploader._display_pdf_names()  # Fetch the uploaded PDF names
        st.session_state["pdf_names"] = [pdf.FILENAME for pdf in res]
        # Automatically select a random paper if none is selected
        if not st.session_state["selected_paper"] and st.session_state["pdf_names"]:
            random_index = random.randint(0, len(st.session_state["pdf_names"]) - 1)
            st.session_state["selected_paper"] = st.session_state["pdf_names"][random_index]
    except Exception as e:
        st.error(f"Error fetching PDF names: {e}")

# Automatically refresh uploaded PDFs when a file is uploaded
refresh_uploaded_pdfs()

with st.sidebar:
    st.header("📂 Uploaded PDFs")
    if st.session_state["pdf_names"]:
        for pdf_name in st.session_state["pdf_names"]:
            st.write(pdf_name)
    else:
        st.write("No PDFs uploaded yet.")

# Display recommended questions for the selected paper
st.write("### Recommended Questions")
if st.session_state["selected_paper"]:
    questions = rag.get_recommended_questions(st.session_state["selected_paper"])
    for question in questions:
        if st.button(question):
            # Use the question as a user query
            st.session_state["messages"].append({"user": question, "assistant": None})
            st.chat_message("user").write(question)

            # Generate response and refresh recommended questions
            try:
                chat_history = [
                    {"user": msg["user"], "assistant": msg["assistant"]}
                    for msg in st.session_state["messages"]
                ]
                response = rag.response(question, chat_history)[1]
                st.session_state["messages"].append({"user": question, "assistant": response})
                st.chat_message("assistant").write(response)
                questions = rag.get_recommended_questions(st.session_state["selected_paper"])
            except Exception as e:
                st.error(f"An error occurred: {e}")
else:
    st.write("No paper selected.")

# Chatbot Interface
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"user": None, "assistant": "How can I help you?"}
    ]

st.write("### 💬 Chat with Your Files")

# Display chat messages
for msg in st.session_state["messages"]:
    if msg["user"]:
        st.chat_message("user").write(msg["user"])
    if msg["assistant"]:
        st.chat_message("assistant").write(msg["assistant"])

# Chat input
if prompt := st.chat_input("Type your question here..."):
    st.session_state["messages"].append({"user": prompt, "assistant": None})
    st.chat_message("user").write(prompt)

    try:
        # Prepare chat history for RAG response
        chat_history = [
            {"user": msg["user"], "assistant": msg["assistant"]}
            for msg in st.session_state["messages"]
        ]

        # Get response from RAG
        response = rag.response(prompt, chat_history)[1]

        # Append response to chat history
        st.session_state["messages"][-1]["assistant"] = response
        st.chat_message("assistant").write(response)
    except Exception as e:
        st.error(f"An error occurred: {e}")