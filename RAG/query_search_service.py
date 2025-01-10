
if __name__ == "__main__":
    from connector import connect
else:
    from RAG.connector import connect
from snowflake.core import Root
import json

from graphviz import Digraph

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
    def _get_query_type(self, text):
        system_prompt = f"""You are an AI assistant designed to classify user queries for a Retrieval-Augmented Generation (RAG) system containing multiple documents. The system has two query types:
- **LOCAL**: For queries requiring a *localized search* through individual chunks of information (e.g., when the user asks for specific details, facts, or direct answers from smaller sections of a document).
- **GLOBAL**: For queries requiring a *globalized search* that produces summaries or insights by synthesizing information across entire documents.
- **BOTH**: For queries that require a combination of both localized and globalized search.
Based on the users query classify the query type as either LOCAL or GLOBAL. Output in the format {{"query_type":"LOCAL"}} or {{"query_type":"GLOBAL"}} or {{"query_type":"BOTH"}}."""
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
        else:
            return 2

    def _query_expansion(self, text, chat_history): # 
        history_context = "\n".join(
            [f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history]
        )

        system_prompt = f"""You are an AI Language model assistant. Your task is to generate five different versions of the given user query to retrieve relevant documents from a vector database. 
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
    
    def _get_context(self, text, chat_history):
        queries = self._query_expansion(text, chat_history)
        queries = [text]
        res = set()
        for query in queries:
            if query.strip() != "":
                for r in self._search(query):
                    res.add("Chunk:"+r["chunk_id"]+r["content"])
    
        context = ""
        for r in res:
            context += r+"\n\n"
        return context
    
    def _localized_search(self, text, chat_history):
        context = self._get_context(text, chat_history)
        system_prompt = """You are an AI Language model assistant. Your task is to generate a response to the user query based on the given context. Do not repeat the query again, just generate a response based on the context provided. Do provide the details about the chunk that you are referring to in the response."""
        context="Context: "+context+"\n\n"+"Query: "+text
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
            {{ 'guardrails': True ,'max_tokens': 200}}
        ) AS response"""
        res = self.session.sql(response_query).collect()
        
        res = res[0].RESPONSE
        res = eval(res)["choices"][0]["messages"]
        return res
    
    
    def _global_search(self,text,chat_history):
        # Function to summarize a single document using SNOWFLAKE.CORTEX.SUMMARIZE
        names_list = self._get_names(text, chat_history)
        
        print("Names in global search are:",names_list)
          
        summary_query = f"""SELECT FILENAME, SUMMARY FROM PDF_SUMMARIES WHERE FILENAME IN ({",".join(names_list)})"""
        print(summary_query)
        res = self.session.sql(summary_query).collect()
        
        print("Outside summary_query in global search")

        res = [(res[i].FILENAME[:-4],res[i].SUMMARY) for i in range(len(res))]
        
        combined_query = ""
        
        for r in res:
            combined_query += "Paper: "+r[0]+"\n\nSummary: "+r[1]+"\n\n"
            
        # print("combined_query")
        # print(combined_query)
            
            
        system_prompt = "You are an AI Language model assistant. Your task is to answer the query based on the given context."
        
        context = "Context: "+text + "\n\n" + "Chat History: " + "\n".join([f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history])
        context += "\n\n" + "Summaries: " + combined_query
        
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
            {{ 'guardrails': True ,'max_tokens': 350}}
        ) AS response"""
        res = self.session.sql(response_query).collect()
        
        # print(res)
        
        res = res[0].RESPONSE
        res = eval(res)["choices"][0]["messages"]
        
        # print("Global Search 1")
        # print(res)
        
        return res
    
    def _get_names(self,text,chat_history):
        system_prompt = "You are an AI Language model assistant. Your task is to give the names (only out of the names that are provided) of the paper that the context and chat history is referring to. Note that the names of the paper can be multiple or singular. Strictly give it in the format {\"names\":[\"name1\",\"name2\",...]}."
        
        context = "Context: "+text + "\n\n" + "Chat History: " + "\n".join([f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history])
        context=context.replace("'","")
        system_prompt=system_prompt.replace("'","")
        context=json.dumps(context)
        system_prompt=json.dumps(system_prompt)
        
        sql_query = f"""SELECT FILENAME FROM PDF_FILE_NAMES"""
        res = self.session.sql(sql_query).collect()
        res = [res[i].FILENAME for i in range(len(res))]        
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
            {{ 'guardrails': True , 'temperature':0}}
        ) AS response"""
        
    
        res = self.session.sql(name_of_model).collect()
        res = res[0].RESPONSE
        res = eval(res)["choices"][0]["messages"]
        
        names_list = json.loads(res)["names"]
        names_list = [f"'{name}'" for name in names_list]
        
        return names_list

    def _combined_search(self,text,chat_history):
        
        global_ans = self._global_search(text, chat_history)
        local_ans = self._localized_search(text, chat_history)
        
        
        system_prompt = "You are an AI Language model assistant. Your task is to combine the global answer, local answer and the context to generate a final response. In case the global answer is not relevant, you have to give preference to the local answer. The final response should be a combination of the global answer, local answer and the context. The final response should be a coherent and informative answer to the user query."
        
        if(len(chat_history) != 0):
            context = "Context: "+text + "\n\n" + "Chat History: " + "\n".join([f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history])
        
        else:
            context = "Context: "+text + "\n\n"
        
        context = context + "\n\n" + "Global Answer: " + "\n".join(global_ans) + "\n\n" + "Local Answer: " + local_ans
        
               
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
            {{ 'guardrails': True ,'max_tokens': 400}}
        ) AS response"""
        res = self.session.sql(response_query).collect()
        
        res = res[0].RESPONSE
        res = eval(res)["choices"][0]["messages"]
        
        return res
    
    def response(self, text, chat_history):
        search_type = self._get_query_type(text)
        if search_type==1:
            print("In global search")
            return self._global_search(text, chat_history)
        elif search_type==0:
            print("In localized search")
            return self._localized_search(text, chat_history)
        else:
            print("In combined search")
            return self._combined_search(text, chat_history)
        
    def get_steps(self, text , chat_history):
        
        name_list = self._get_names(text, chat_history)
        # print("name_list",name_list)
        
        prompt = f"""What are the steps followed by {name_list[0].replace("'","")}? Ensuring each step is concise and focused."""
        
        # print("Prompt is:",prompt)
        
        response = self._combined_search(prompt, [])
        
        # print("response",response)
        
        system_prompt = "You are an AI language model tasked with generating a list of steps based on the given context. Each step should follow the format: [\"Step_Name: Step_Description\", \"Step_Name: Step_Description\", ...], each step's name and description should be merged into a single string, separated by a colon (:). Make sure to replace any placeholders with the actual steps based on the context provided. Keep the explanations simple"        
        context = "Context: "+prompt + "\n\n" + "Chat History: " + "\n".join([f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history])
        
        context = context + "\n\n" + "Response: " + "\n" + response
        
        # print("context is:",context)
        
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
        
        print("res",res)
        
        res = eval(res)["choices"][0]["messages"]
        
        # print("Final response is:",res)
        
        # Parse the steps into a structured list
        try:
            steps_list = json.loads(res)
        except json.JSONDecodeError:
            steps_list = []  # Handle any parsing errors
            
        # print("steps are:",steps_list)
        
        # # Initialize an empty list to store the steps
        # processed_steps = []

        # # Iterate through the steps in pairs (name and description)
        # for i in range(0, len(res), 2):
        #     # Extract the step name and description
        #     step_name = res[i].split(" : ")[-1]
        #     step_description = res[i + 1].split(" : ")[-1]
            
        #     # Merge the step name and description
        #     processed_steps.append(f"{step_name}: {step_description}")
        
        return steps_list
        
    
    def generate_flowchart(steps_list, title):
        dot = Digraph()
        dot.attr(rankdir="TB", size="6,6")
        dot.attr(label=title, fontsize="20", labelloc="t")

        # Add steps to the flowchart
        for step in steps_list:
            dot.node(step.strip(), step.strip())  # Add the whole step (name and description as one node)

        # Connect steps sequentially
        for i in range(len(steps_list) - 1):
            step_name_1 = steps_list[i].split(":")[0].strip()  # Get the step name part
            step_name_2 = steps_list[i + 1].split(":")[0].strip()  # Get the step name part
            dot.edge(step_name_1, step_name_2)  # Connect the steps based on their names

        return dot
                
              

if __name__ == "__main__":
    rag = RAG()
    text = "Give a general idea about what are masked auto encoder and what is the difference between them and BERT in terms of masking ratio?"
    chat_history = [
    ]
    print(rag.get_steps(text, chat_history))
    
