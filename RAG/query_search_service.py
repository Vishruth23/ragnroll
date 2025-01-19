
if __name__ == "__main__":
    from connector import connect
else:
    from RAG.connector import connect
from snowflake.core import Root
import json
from snowflake.cortex import Complete
from typing import List


class RAG:
    def __init__(self):
        self.session = connect()
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
        

        system_prompt = f"""You are an AI Language model assistant. Your task is to generate two different versions of the given user query to retrieve relevant documents from a vector database. 
By generating multiple perspectives on the user query and the given chat history, your goal is to overcome some of the limitations of distance-based search. 
Make sure to replace the pronouns in the query with the entities based on the chat history.
Chat History:
{chat_history}
Current Query: {text}
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
                        - If pronouns are present in the query, replace them with the appropriate entities based on the chat history.
                        """
        
        context = "Query: "+text + "\n\n" + "Chat History: " + f"{chat_history}"
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
            steps_list = []  
   
        
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
   
        
    def generate_completion(self, query: str, context_str: list,chat_history) -> str:
        """
        Generate answer from context.
        """
        prompt = f"""
          You are an expert assistant extracting information from context provided.
          Answer the question based on the context. Do not hallucinate.
          If you don´t have the information just say so. Use the chat history to fill the pronouns in the query.

          Context: {context_str}\n\n
          Question:
          {query}\n\n
          Chat History: {chat_history}
          Answer:
        """
        return Complete("mistral-large2",prompt)

       
    def query(self,text:str,chat_history=[]) ->str:
        chat_history=json.dumps(chat_history)
        chat_history=chat_history.replace("'","")
        search_type = self._get_query_type(text)
        if search_type in [0,1,2]:
            context=self.retrieve_context(text,chat_history,search_type)
            return "TEXT",self.generate_completion(text,context,chat_history)
        else:
            return "FLOWCHART",self._get_steps(text, chat_history)
        
    

                
              

if __name__ == "__main__":
    rag = RAG()
    text = "Give me an idea of a model that combines XLNet and CLIP "
    chat_history = [
        {"user":"Hey","assistant":"Hello"},
    ]
    print(rag.query(text,chat_history))
    rag.session.close()
    
    
