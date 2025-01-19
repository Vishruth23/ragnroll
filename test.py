from trulens.core import TruSession
from trulens.connectors.snowflake import SnowflakeConnector
from RAG.connector import connect
from trulens.apps.custom import instrument

import os
from snowflake.core import Root
from typing import List
from snowflake.cortex import Complete
import json

snowpark_session = connect()
class CortexSearchRetriever:

    def __init__(self, snowpark_session, limit_to_retrieve: int = 4):
        self._snowpark_session = snowpark_session
        self._limit_to_retrieve = limit_to_retrieve
        self.root = Root(snowpark_session)

    def retrieve(self, query: str) -> List[str]:
       
        cortex_search_service = (
            self.root
            .databases["MLLM"]
            .schemas["PUBLIC"]
            .cortex_search_services["PDF_SEARCH_SERVICE"]
        )
        resp = cortex_search_service.search(
            query=query,
            columns=["content"],
            limit=self._limit_to_retrieve,
        )

        if resp.results:
            return [curr["content"] for curr in resp.results]
        else:
            return []


class Traditional_RAG:

    def __init__(self):
        self.retriever = CortexSearchRetriever(snowpark_session=snowpark_session, limit_to_retrieve=4)

    @instrument
    def retrieve_context(self, query: str) -> list:
        """
        Retrieve relevant text from vector store.
        """
        return self.retriever.retrieve(query)

    @instrument
    def generate_completion(self, query: str, context_str: list) -> str:
        """
        Generate answer from context.
        """
        prompt = f"""
          You are an expert assistant extracting information from context provided.
          Answer the question based on the context. Be concise and do not hallucinate.
          If you don´t have the information just say so.
          Context: {context_str}
          Question:
          {query}
          Answer:
        """
        return Complete("mistral-large2", prompt)

    @instrument
    def query(self, query: str) -> str:
        context_str = self.retrieve_context(query)
        return self.generate_completion(query, context_str)
class RAG:
    def __init__(self):
        self.session = snowpark_session
        self.root = Root(self.session)
        self.cortex_search_service = (
            self.root
            .databases["MLLM"]
            .schemas["PUBLIC"]
            .cortex_search_services["PDF_SEARCH_SERVICE"]
        )

    def _get_query_type(self, text:str)->int:
        system_prompt = f"""You are an AI assistant designed to classify user queries for a Retrieval-Augmented Generation (RAG) system containing multiple documents. The system has two query types:
- **LOCAL**: For queries requiring a *localized search* through individual chunks of information (e.g., when the user asks for specific details, facts, or direct answers from smaller sections of a document).
- **GLOBAL**: For queries requiring a *globalized search* that produces summaries or insights by synthesizing information across entire documents.
- **BOTH**: For queries that require a combination of both localized and globalized search.
- **FLOWCHAT**: For queries that require a flowchart of the steps followed in a process.
Based on the users query classify the query type as either LOCAL or GLOBAL. Output in the format {{"query_type":"LOCAL"}} or {{"query_type":"GLOBAL"}} or {{"query_type":"BOTH"}} or {{"query_type":"FLOWCHART"}}."""
        text=text.replace("'","")
        system_prompt=system_prompt.replace("'","")
        text = json.dumps( "Query:"+text)
        system_prompt = json.dumps(system_prompt)
        query_type_query = f"""SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            [
                {{
                    'role': 'system', 'content': '{system_prompt[1:-1]}'
                }},
                {{
                    'role': 'user', 'content': '{text[1:-1]}'
                }}
            ],
            {{ 'max_tokens': 20,'temperature':0}}
        ) AS response"""
        res = self.session.sql(query_type_query).collect()
        res = res[0].RESPONSE
        res = eval(res)["choices"][0]["messages"]
        res=eval(res)["query_type"]
        if res == "LOCAL":
            return 0
        elif res=="GLOBAL":
            return 1
        elif res=="BOTH":
            return 2
        else :
            return 3

    def _query_expansion(self, text:str, chat_history=[]):  
        history_context = "\n".join(
            [f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history]
        )

        system_prompt = f"""You are an AI Language model assistant. Your task is to generate two different versions of the given user query to retrieve relevant documents from a vector database. 
By generating multiple perspectives on the user query and the given chat history, your goal is to overcome some of the limitations of distance-based search. 

Chat History:
{history_context}

Provide the alternative versions separated by a newline character."""

        # Prepare the SQL query
        sql_query = """SELECT SNOWFLAKE.CORTEX.COMPLETE(
        'mistral-large2',
        [
            {{
                'role': 'system', 'content': '{}'
            }},
            {{
                'role': 'user', 'content': '{}'
            }}
        ],
        {{ }}
) AS response
""".format(system_prompt, text)

        res = self.session.sql(sql_query).collect()
        res = res[0].RESPONSE
        res = eval(res)["choices"][0]["messages"].replace("\\n", "\n").split("\n")
        return res
        
    def _search(self, text):
        resp = self.cortex_search_service.search(
            query=text,
            columns=["chunk_id", "content"],
            limit=5
        )
        resp = eval(resp.to_json())["results"]
        return resp

    def _get_summary_context(self, text, chat_history):
        names_list = self._get_names(text, chat_history)
        
          
        summary_query = f"""SELECT FILENAME, SUMMARY FROM PDF_SUMMARIES WHERE FILENAME IN ({','.join([f"'{name}'" for name in names_list])})"""

        res = self.session.sql(summary_query).collect()
        
        res = [(res[i].FILENAME[:-4],res[i].SUMMARY) for i in range(len(res))]
        
        combined_query = []
        
        for r in res:
            combined_query.append("Paper: "+r[0]+"\n\nSummary: "+r[1]+"\n\n")
        return combined_query
    
    
    
    def _get_names(self,text,chat_history):
        system_prompt = """
                        You are an AI language model assistant. Your task is to identify and return the filenames (from a given list) that are most relevant to the provided context and chat history. 

                        - The filenames are accompanied by captions that describe the file content.
                        - Base your selection strictly on the relevance of the captions to the given context and chat history.
                        - Ensure that only filenames explicitly mentioned or implied by the context are included. 
                        - The names should be provided as a list in the following format: ["name1", "name2", ...].
                        - Do not modify, rename, or infer new filenames beyond those provided.
                        - Be concise and do not include any additional text or explanations outside of the specified format.
                        """
        
        context = "Context: "+text + "\n\n" + "Chat History: " + "\n".join([f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history])
        context=context.replace("'","")
        system_prompt=system_prompt.replace("'","")
        context=json.dumps(context)
        system_prompt=json.dumps(system_prompt)
        
        sql_query = f"""SELECT FILENAME,CAPTION FROM PDF_CAPTIONS"""
        res = self.session.sql(sql_query).collect()
        res = [f"Filename:{res[i].FILENAME} Caption:{res[i].CAPTION}" for i in range(len(res))]        
        names = res
        
        context += "\n\n" + "Names: " + "\n".join(names)
                
        name_of_model = f"""SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            [
                {{
                    'role': 'system', 'content': '{system_prompt[1:-1]}'
                }},
                {{
                    'role': 'user', 'content': '{context[1:-1]}'
                }}
            ],
            {{ 'guardrails': False , 'temperature':0}}
        ) AS response"""
        
    
        res = self.session.sql(name_of_model).collect()
        res = res[0].RESPONSE
        res = eval(res)["choices"][0]["messages"]
        names_list = json.loads(res)
        
        
        return names_list
    def _get_steps(self, text ,chat_history):
        
                
        context = self.retrieve_context(text, chat_history,2)  
        system_prompt = """
                        You are an AI language model tasked with generating a list of steps based on the provided context. 

                        Requirements:
                        1. The output must strictly follow this JSON format: 
                        [{"step_name": "step_description"}, {"step_name": "step_description"}, ...].
                        2. Replace all placeholders with the actual steps derived from the context. 
                        3. Provide clear and concise step names and descriptions that align with the given context.
                        4. Do not include any additional explanations, metadata, or text outside of the required JSON format.

                        Ensure the response is accurate, relevant, and free of extraneous information.
                        """
        context=f"Context: {context}"
        
        
        context=context.replace("'","")
        system_prompt=system_prompt.replace("'","")
        context=json.dumps(context)
        system_prompt=json.dumps(system_prompt)
        
        response_query = f"""SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            [
                {{
                    'role': 'system', 'content': '{system_prompt[1:-1]}'
                }},
                {{
                    'role': 'user', 'content': '{context[1:-1]}'
                }}
            ],
            {{ 'guardrails': True ,'max_tokens': 600 , 'temperature' : 0}}
        ) AS response"""
        res = self.session.sql(response_query).collect()
        
        res = res[0].RESPONSE
        
        
        res = eval(res)["choices"][0]["messages"]
        res=res[res.find("["):res.rfind("]")+1]
       
        try:
            steps_list = json.loads(res)
        except json.JSONDecodeError:
            steps_list = []  # Handle any parsing errors
   
        
        return {"file":"Flowchart","steps":steps_list}
    
    def get_recommended_questions(self,paper=None):
        if paper is None:
            sql_query = f"""SELECT FILENAME, CAPTION FROM PDF_CAPTIONS"""
        else:
            sql_query = f"""SELECT FILENAME, CAPTION FROM PDF_CAPTIONS WHERE FILENAME = '{paper}'"""
        res = self.session.sql(sql_query).collect()
        res = [(res[i].FILENAME, res[i].CAPTION) for i in range(len(res))]

        if len(res) == 0:
            return []
        
        system_prompt = "You are an AI Language model assistant. You are given filenames with captions mentionng about the file. Your task is to generate a list of questions based on the given context. The output format is as follows: [\"question1\",\"question2\",...]. The questions should be relevant to the context provided in the caption. Do not return any other information apart from the questions."

        context = "Context: " + "\n".join([f"Filename: {r[0]}\nCaption: {r[1]}" for r in res])
        context = context.replace("'", "")
        system_prompt = system_prompt.replace("'", "")
        context = json.dumps(context)
        system_prompt = json.dumps(system_prompt)

        response_query = f"""SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            [
                {{
                    'role': 'system', 'content': '{system_prompt[1:-1]}'
                }},
                {{
                    'role': 'user', 'content': '{context[1:-1]}'
                }}
            ],
            {{ 'guardrails': True }}
        ) AS response"""

        res = self.session.sql(response_query).collect()
        res = res[0].RESPONSE
        res = eval(res)["choices"][0]["messages"]
        res = res[res.find("["):res.rfind("]") + 1]
        try:
            questions = eval(res)
        except :
            questions = []
        return questions

    @instrument
    def retrieve_context(self, text, chat_history=[],query_type=2) -> List[str]:
        res = set()
        if query_type == 0 or query_type == 2:
            
            queries = self._query_expansion(text, chat_history)
            queries = [text]
            for query in queries:
                if query.strip() != "":
                    for r in self._search(query):
                        res.add("Chunk:"+r["chunk_id"]+r["content"])

        if query_type == 1 or query_type == 2:
            for r in self._get_summary_context(text,chat_history):
                res.add(r)
        
        return list(res)
   
    @instrument    
    def generate_completion(self, query: str, context_str: list) -> str:
        """
        Generate answer from context.
        """
        if not context_str:
            return "I couldn't find any relevant information in the provided context."
        prompt = f"""
          You are an expert assistant extracting information from context provided.
          Answer the question based on the context. Do not hallucinate.
          If you don´t have the information just say so.
          Context: {context_str}
          Question:
          {query}
          Answer:
        """
        return Complete("mistral-large2",prompt)

    @instrument   
    def query(self,text:str,chat_history=[]) ->str:
        search_type = self._get_query_type(text)
        if search_type in [0,1,2]:
            context=self.retrieve_context(text,chat_history,search_type)
            return self.generate_completion(text,context)
        else:
            return self._get_steps(text, chat_history)
        
    

                
    

tru_snowflake_connector = SnowflakeConnector(snowpark_session=snowpark_session)

tru_session = TruSession(connector=tru_snowflake_connector)
rag = Traditional_RAG()

from trulens.providers.cortex.provider import Cortex
from trulens.core import Feedback
from trulens.core import Select
import numpy as np

provider = Cortex(snowpark_session, "mistral-large2")



f_context_relevance = (
    Feedback(provider.context_relevance, name="Context Relevance")
    .on_input()
    .on(Select.RecordCalls.retrieve_context.rets[:])
    .aggregate(np.mean)
)

f_answer_relevance = (
    Feedback(provider.relevance, name="Answer Relevance")
    .on_input()
    .on_output()
    .aggregate(np.mean)
)

from trulens.apps.custom import TruCustomApp

tru_rag = TruCustomApp(
    rag,
    app_name="RAG",
    app_version="simple",
    feedbacks=[f_answer_relevance, f_context_relevance],
    )

prompts=open("prompts.txt","r").readlines()

with tru_rag as recording:
    for prompt in prompts:
        rag.query(prompt)

custom_rag=RAG()
tru_rag2 = TruCustomApp(
    custom_rag,
    app_name="Custom_RAG",
    app_version="simple",
    feedbacks=[f_answer_relevance, f_context_relevance],
    )

with tru_rag2 as recording:
    for prompt in prompts:
        custom_rag.query(prompt)

print(tru_session.get_leaderboard())
    