import trulens
from trulens.core import Feedback, Select, TruSession
from trulens.providers.cortex import Cortex as TruLensCortex
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.feedback import GroundTruthAgreement
from trulens.apps.custom import TruCustomApp
from RAG.query_search_service import *
import numpy as np
import streamlit as st


rag = RAG()
chat_history = []

# using trulens with cortex search to evaluate rag performance
# cortex is used as the provider for the trulens search

# qa_df = pd.read_csv("test_qs.txt")
# qa_set = [{"query": item["Question"], "response": item["Answer"]} for index, item in qa_df.iterrows()]

with open("test_qs.txt") as file:
    questions = file.readlines()


sp_session = rag.session

# tru_snowflake_connector = SnowflakeConnector(snowpark_session=sp_session)
# tru_session = TruSession(connector=tru_snowflake_connector)
tl_provider = TruLensCortex(sp_session,'mistral-large2')

f_groundedness = (
    Feedback(tl_provider.groundedness_measure_with_cot_reasons, name="Groundedness")
    .on(Select.RecordCalls._get_context.rets[:].collect())
    .on(Select.RecordCalls._combined_search.rets[:])
)

f_context_relevance = (
    Feedback(tl_provider.context_relevance_with_cot_reasons, name="Context Relevance")
    .on_input()
    .on(Select.RecordCalls._get_context.rets[:])
    .aggregate(np.mean)
)

f_answer_relevance = (
    Feedback(tl_provider.relevance_with_cot_reasons, name="Answer Relevance")
    .on_input()
    .on_output()
    .aggregate(np.mean)
)

# print("metrics", f_groundedness,f_context_relevance,f_answer_relevance)

# f_groundtruth = Feedback(
#     GroundTruthAgreement(qa_set).agreement_measure, name="Answer Correctness"
# ).on_input_output()


tru_rag = TruCustomApp(
    rag,
    app_name="RAG",
    app_version="simple",
    feedbacks=[f_groundedness, f_answer_relevance, f_context_relevance],
    )

with tru_rag as recording:
    for prompt in questions:
        print("Printing RAG response")
        print(rag._combined_search(prompt,[]))

rag.tru_session.get_leaderboard()

# print(tl_provider)