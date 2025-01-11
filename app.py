import streamlit as st
from RAG.query_search_service import RAG 

rag=RAG()
chat_history=[]
graph=rag.generate_flowchart("masked auto encoders",[])

st.graphviz_chart(graph)