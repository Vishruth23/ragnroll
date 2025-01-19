if __name__=="__main__":
    from connector import connect
    from parse_doc import split_markdown_text
else:
    from RAG.connector import connect
    from RAG.parse_doc import split_markdown_text
import json

class DynamicUpload:

    def __init__(self,pdf_path,session=None):
        self.session=session
        self.pdf=pdf_path
        self.pdf_name=pdf_path.split("/")[-1]

    def _insert_new_pdf_to_stage(self):
        res=self.session.sql(f"PUT file://{self.pdf} @MY_PDF_STAGE AUTO_COMPRESS=FALSE;").collect()

        if res[0].status=="SKIPPED":
            return False
        
        self.session.sql(f"INSERT INTO pdf_file_names VALUES ('{self.pdf_name}');").collect()
        return True


    def _parse_pdf_to_markdown(self):
        query=f'''INSERT INTO PARSED_PDFS
SELECT
    filename,
    SNOWFLAKE.CORTEX.PARSE_DOCUMENT(@MY_PDF_STAGE,filename, {{'mode': 'LAYOUT'}}):content::STRING AS content FROM pdf_file_names where filename like '{self.pdf_name}';
'''
        res=self.session.sql(query).collect()
    
    def _split_markdown_text(self):
        content_query=f"SELECT content FROM PARSED_PDFS WHERE filename like '{self.pdf_name}';"
        res=self.session.sql(content_query).collect()
        content=res[0].CONTENT

        chunks=split_markdown_text(content)
        for i,chunk in enumerate(chunks):
            chunk=chunk.replace("'","''")
            self.session.sql(f"INSERT INTO PARSED_PDFS_CHUNKS VALUES ('{self.pdf_name}_{i}','{chunk}');").collect()
    
    def _generate_summary(self):
        query=f''' INSERT INTO PDF_SUMMARIES (filename, summary)
SELECT 
    filename,
    SNOWFLAKE.CORTEX.SUMMARIZE(
        CASE
            WHEN LENGTH(CONTENT) > 100000 THEN SUBSTRING(CONTENT, 1, 100000) 
            ELSE CONTENT
        END
    ) AS summary
FROM PARSED_PDFS
WHERE filename LIKE '{self.pdf_name}';
'''
        res=self.session.sql(query).collect()
    
    def _generate_caption(self):
        summary_query=f"SELECT summary FROM PDF_SUMMARIES WHERE filename like '{self.pdf_name}';"
        res=self.session.sql(summary_query).collect()
        context="SUMMARY: "+res[0].SUMMARY

        system_prompt="""You are AI Model. You are assisting a RAG system to choose which file the query is referring through based on a caption. The caption is generated based on the summary. Given the summary stricly return only the caption. The caption should be a single sentence and should cover the main idea of the summary. """
        system_prompt=system_prompt.replace("'","''")
        context=context.replace("'","''")
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
            {{ 'guardrails': True, 'max_tokens': 300 , 'temperature' :0}}
        ) AS response"""
        
        res=self.session.sql(response_query).collect()
        caption=res[0].RESPONSE
        caption=eval(caption)["choices"][0]["messages"]
        caption=caption.replace('"','')

        insert_query=f"INSERT INTO PDF_CAPTIONS VALUES ('{self.pdf_name}','{caption}');"
        self.session.sql(insert_query).collect()

        
    def upload_pdf(self):
        if not self._insert_new_pdf_to_stage():
            self.session.close()
            return "SKIPPED UPLOAD"
        
        self._parse_pdf_to_markdown()
        self._split_markdown_text()
        self._generate_summary()
        self._generate_caption()
        return "SUCCESS"

        self.session.close()


    
if __name__=="__main__":
    du=DynamicUpload("./XLNET.pdf")
    print(du.upload_pdf())    