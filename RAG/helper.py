if __name__ == "__main__":
    from connector import connect
else:
    from RAG.connector import connect


class PDFHelper:

    def __init__(self):
        self.session = connect()

    def get_uploaded_pdf_names(self):
        """
        Retrieves the names of all uploaded PDFs from the `pdf_file_names` table.
        """
        try:
            query = "SELECT filename FROM pdf_file_names;"
            result = self.session.sql(query).collect()
            # Extract the filenames from the result
            pdf_names = [row.FILENAME for row in result]
            return pdf_names
        except Exception as e:
            return f"Error occurred: {str(e)}"
        finally:
            self.session.close()


if __name__ == "__main__":
    helper = PDFHelper()
    print(helper.get_uploaded_pdf_names())
