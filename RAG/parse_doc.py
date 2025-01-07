from RAG.connector import connect
from langchain_text_splitters import MarkdownHeaderTextSplitter,RecursiveCharacterTextSplitter

def split_markdown_text(text):
    headers=[
        ("#","H1"),
        ("##","H2"),
        ("###","H3"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers,strip_headers=True)
    docs=splitter.split_text(text)
    char_splitter=RecursiveCharacterTextSplitter(chunk_size=512,chunk_overlap=100)
    splits=char_splitter.split_documents(docs)
    chunks=[]
    for split in splits:
        txt=""
        if split.metadata.get("H1"):
            txt+="#"+split.metadata["H1"]+"\n"
        if split.metadata.get("H2"):
            txt+="##"+split.metadata["H2"]+"\n"
        if split.metadata.get("H3"):
            txt+="###"+split.metadata["H3"]+"\n"
        txt+=split.page_content
        chunks.append(txt)


    return chunks


def parse_doc():
    session = connect()
    session.sql("USE SCHEMA PUBLIC;").collect()
    res=session.sql("select filename,content from PARSED_PDFS").collect()
    create_table_query="CREATE OR REPLACE TABLE PARSED_PDFS_CHUNKS (chunk_id STRING, content STRING);"
    session.sql(create_table_query).collect()

    for row in res:
        filename=row.FILENAME
        content=row.CONTENT
        chunks=split_markdown_text(content)
        for i,chunk in enumerate(chunks):
            chunk=chunk.replace("'","''")
            session.sql(f"INSERT INTO PARSED_PDFS_CHUNKS VALUES ('{filename}_{i}','{chunk}');").collect()
    
    session.close()
    
if __name__ == "__main__":
    parse_doc()