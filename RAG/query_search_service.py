
if __name__ == "__main__":
    from connector import connect
else:
    from RAG.connector import connect
from snowflake.core import Root
import json

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
        'mistral-large',
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
    
    def response(self, text, chat_history):
        context = self._get_context(text, chat_history)
        system_prompt = """You are an AI Language model assistant. Your task is to generate a response to the user query based on the given context. Do not repeat the query again, just generate a response based on the context provided. Do provide the details about the chunk that you are referring to in the response."""
        context="Context: "+context+"\n\n"+"Query: "+text
        context=json.dumps(context)
        system_prompt=json.dumps(system_prompt)
            
        
        response_query = f"""SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large',
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
    
    
    def summarize(self,text,chat_history):
        # Function to summarize a single document using SNOWFLAKE.CORTEX.SUMMARIZE
        system_prompt = "You are an AI Language model assistant. Your task is to give the names (only out of the names that are provided) of the paper that the context and chat history is referring to. Note that the names of the paper can be multiple or singular. Strictly give it in the format {\"names\":[\"name1\",\"name2\",...]}."
        
        context = "Context: "+text + "\n\n" + "Chat History: " + "\n".join([f"User: {msg['user']}\nAssistant: {msg['assistant']}" for msg in chat_history])
        
        context=json.dumps(context)
        system_prompt=json.dumps(system_prompt)
        
        sql_query = f"""SELECT FILENAME FROM PDF_FILE_NAMES"""
        res = self.session.sql(sql_query).collect()
        res = [res[i].FILENAME for i in range(len(res))]
        
        print(res)
        
        names = res
        context += "\n\n" + "Names: " + "\n".join(names)
        
        print(context)
        
        name_of_model = f"""SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large',
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
        # print((res))
        
        names_list = json.loads(res)["names"]
        
        print(names_list , type(names_list))
        
        summary_query = f"""SELECT FILENAME, SUMMARY FROM PDF_SUMMARIES WHERE FILENAME IN {tuple(names_list)}"""
        res = self.session.sql(summary_query).collect()
        res = [(res[i].FILENAME[:-4],res[i].SUMMARY) for i in range(len(res))]
        
        return res 
        
        

if __name__ == "__main__":
    rag = RAG()
    text = "What are masked autoencoders and how is it related to attention is all you need?"
    chat_history = [
    ]

    docs = rag.summarize(text, chat_history)
    print(docs)
