from RAG.connector import connect

def load_pdfs():
    # Connect to the database
    session = connect()
    res=session.sql("SELECT FILENAME FROM PDF_FILE_NAMES;").collect()
    pdf_names = [row.FILENAME for row in res]
    return pdf_names