import os
import streamlit as st
from streamlit_option_menu import option_menu
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
    st.image("./query_flowchart.png")

def create_dynamic_upload_flowchart():
    st.image("./dynamic_upload_flowchart.png")

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

def update_recommended():
    st.write("### Recommended Questions")
    if st.session_state.get("recommended_qs"):
        for idx, question in enumerate(st.session_state["recommended_qs"], start=1):
            if st.button(f"{idx}. {question}"):
                try:
                    chat_history = st.session_state.get("messages", [])
                    with st.spinner(f"Querying: {question}..."):
                        response_type, response = rag.query(question, chat_history[-1:-6:-1])
                        st.session_state["messages"].append({"response_type": response_type, "user": question, "assistant": response})
                    with st.spinner("Updating recommended questions..."):
                        st.session_state["recommended_qs"] = rag.get_recommended_questions(answer_context=response, query_context=question)[:2]
                    st.rerun()
                except Exception as e:
                    st.error(f"An error occurred: {e}")
    else:
        st.write("No recommended questions available at the moment.")

# Initialize session state variables
if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = load_pdfs(rag.session)

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"user": None, "assistant": "How can I help you?", "response_type": "TEXT"}
    ]

# Sidebar with option menu
with st.sidebar:
    selected = option_menu(
        menu_title="📋 Options",
        options=["Chatbot", "Upload PDFs", "Process Overview", "TruLens Statistics"],
        icons=["chat", "upload", "diagram-3", "bar-chart"],
        default_index=0,
    )

# Main content
if selected == "Chatbot":
    st.title("💬 Chatbot with Flowchart Support")
    st.caption("🚀 A Streamlit chatbot powered by RAG")

    st.write("### 💬 Chat with Your Files")
    if "recommended_qs" not in st.session_state:
        with st.spinner("Loading chatbot..."):
            st.session_state["recommended_qs"] = rag.get_recommended_questions()[:5]
    
    
    

    display_responses()
    if prompt := st.chat_input("Type your question here..."):
        try:
            chat_history = st.session_state.get("messages", [])
            with st.spinner(f"Querying: {prompt}..."):
                response_type, response = rag.query(prompt, chat_history[-1:-6:-1])
                st.session_state["messages"].append({"response_type": response_type, "user": prompt, "assistant": response})
            with st.spinner("Updating recommended questions..."):
                st.session_state["recommended_qs"] = rag.get_recommended_questions(answer_context=response, query_context=prompt)[:2]
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred: {e}")
    update_recommended()

elif selected == "Upload PDFs":
    st.title("📂 Upload Files")
    uploaded_files = st.file_uploader("Upload one or more PDF files", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:
            temp_dir = "temp"
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())

            try:
                uploader = DynamicUpload(temp_path, rag.session)
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    uploader.upload_pdf()
                    st.session_state["recommended_qs"] = rag.get_recommended_questions()[:5]
                    update_recommended()
                    
                st.session_state["uploaded_files"].append(uploaded_file.name)
                st.success(f"Processed: {uploaded_file.name}")

            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {e}")

    st.header("📂 Uploaded PDFs")
    if st.session_state["uploaded_files"]:
        for pdf_name in st.session_state["uploaded_files"]:
            st.write(pdf_name)
    else:
        st.write("No PDFs uploaded yet.")

elif selected == "Process Overview":
    st.title("Process Overview")
    st.header("Query Process")
    query_flowchart()
    st.header("Dynamic PDF Upload Process")
    create_dynamic_upload_flowchart()

elif selected == "TruLens Statistics":
    st.title("TruLens Statistics")
    data = {
        "app_name": ["Custom_RAG", "RAG"],
        "Answer Relevance": [0.888889, 0.711088],
        "Context Relevance": [0.622985, 0.483073],
        "latency": [15.512015, 3.906506],
        "total_cost": [0.4200, 0.152137],
    }

    df = pd.DataFrame(data)

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
        x=alt.X('app_name:N', title='Application', axis=alt.Axis(labelAngle=0)),  
        y=alt.Y('Value:Q', title='Score'),
        color=alt.Color('Metric:N', title='Metric Type'),
        tooltip=['app_name', 'Metric', 'Value']
    ).properties(height=300)
    
    st.altair_chart(relevance_chart, use_container_width=True)

    st.markdown("### Latency Comparison")
    latency_chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('app_name:N', title='Application', axis=alt.Axis(labelAngle=0)),  
        y=alt.Y('latency:Q', title='Latency (seconds)'),
        color=alt.value('#1f77b4'),
        tooltip=['app_name', 'latency']
    ).properties(height=300)
    
    st.altair_chart(latency_chart, use_container_width=True)

    st.markdown("### Total Cost Comparison")
    cost_chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('app_name:N', title='Application', axis=alt.Axis(labelAngle=0)),  
        y=alt.Y('total_cost:Q', title='Total Cost ($)'),
        color=alt.value('#2ca02c'),
        tooltip=['app_name', 'total_cost']
    ).properties(height=300)
    
    st.altair_chart(cost_chart, use_container_width=True)
