print(__name__)
if __name__=="__main__":
    from connector import connect
    from parse_doc import split_markdown_text
else:
    from RAG.connector import connect
    from RAG.parse_doc import split_markdown_text

class DynamicUpload:

    def __init__(self,pdf_path):
        self.session=connect()
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
        
    def upload_pdf(self):
        if not self._insert_new_pdf_to_stage():
            self.session.close()
            return "SKIPPED UPLOAD"
        
        self._parse_pdf_to_markdown()
        self._split_markdown_text()
        self._generate_summary()

        self.session.commit()
        return "SUCCESS"
    
if __name__=="__main__":
    du=DynamicUpload("./CLIP.pdf")
    du.upload_pdf()
    