import trulens
from trulens.core import Feedback, Select
from RAG.query_search_service import RAG 
from trulens_eval import Cortex as TruLensCortex
import numpy as np
import streamlit as st

rag = RAG()
chat_history = []

# using trulens with cortex search to evaluate rag performance
# cortex is used as the provider for the trulens search

sf_session = rag.session
tl_provider = TruLensCortex(sf_session,'mistral-large2')

f_groundedness = (
    Feedback(tl_provider.groundedness_measure_with_cot_reasons, name="Groundedness")
    .on(Select.RecordCalls.retrieve_context.rets[:].collect())
    .on_output()
)

f_context_relevance = (
    Feedback(tl_provider.context_relevance, name="Context Relevance")
    .on_input()
    .on(Select.RecordCalls.retrieve_context.rets[:])
    .aggregate(np.mean)
)

f_answer_relevance = (
    Feedback(tl_provider.relevance, name="Answer Relevance")
    .on_input()
    .on_output()
    .aggregate(np.mean)
)

print(tl_provider)