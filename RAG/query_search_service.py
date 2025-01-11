
if __name__ == "__main__":
    from connector import connect
else:
    from RAG.connector import connect
from snowflake.core import Root
import json
from graphviz import Digraph

# from graphviz import Digraph

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
        
    def _get_steps(self, file,chat_history):
                
        prompt = f"""What are the steps followed by {file.replace("'","")}? Ensuring each step is concise and focused."""
        
        
        response = self._combined_search(prompt, [])        
        system_prompt = "You are an AI language model tasked with generating a list of steps based on the given context. The output format is as follows: [{\"step_name\":\"step_description\"},{\"step_name\":\"step_description\"},...]. Make sure to replace any placeholders with the actual steps based on the context provided. Keep the explanations simple. Do not return any other information apart from the steps."        
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
        res=res[res.find("["):res.rfind("]")+1]
       
        try:
            steps_list = json.loads(res)
        except json.JSONDecodeError:
            steps_list = []  # Handle any parsing errors
   
        
        return steps_list
        
    
    def generate_flowchart(self,file,chat_history):
        """To display the graph use st.graphviz_chart(graph)"""
        steps = self._get_steps(file,chat_history)
        dot = Digraph()
        dot.attr(rankdir="TB", size="6,6")  # Top-to-bottom layout
        dot.attr(title=file, fontsize="20", labelloc="t")  # Title and formatting
        for step in steps:
            dot.node(step["step_name"], step["step_name"],tooltip=step["step_description"])

        for i in range(len(steps) - 1):
            dot.edge(steps[i]["step_name"], steps[i + 1]["step_name"])

        return dot


                
              

if __name__ == "__main__":
    rag = RAG()
    text = "Give a general idea about what are masked auto encoder and what is the difference between them and BERT in terms of masking ratio?"
    chat_history = [
    ]
    print(rag.generate_flowchart("masked_autoencoder"))
    
