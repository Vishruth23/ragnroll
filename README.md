# Retrieval-Augmented Generation (RAG) Pipeline

This project implements a Retrieval-Augmented Generation (RAG) pipeline using Snowflake's Cortex Search, Mistral LLM, and Streamlit for the frontend. The pipeline is designed to ingest PDF files, parse their content, and provide an interactive chatbot for querying information with the help of TruLens for evaluation and optimization.

---

## Features

- **PDF Ingestion**: Upload and store PDF documents securely using Snowflake stages.
- **Text Parsing**: Extract and chunk content from PDF files with metadata preservation.
- **Summarization and Captioning**: Automatically generate summaries and captions for uploaded files.
- **Interactive Chatbot**: Query your documents interactively using a Streamlit-powered chatbot.
- **Flowchart Support**: Visualize query processes and dynamic upload workflows.
- **TruLens Integration**: Evaluate and monitor the performance of the RAG pipeline.
- **Cost & Performance Metrics**: Compare latency and cost using Altair visualizations.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [Starting the Application](#starting-the-application)
  - [Uploading PDFs](#uploading-pdfs)
  - [Querying Documents](#querying-documents)
- [Architecture Overview](#architecture-overview)
- [Directory Structure](#directory-structure)
- [License](#license)

---

## Requirements

Ensure you have the following installed:

- Python 3.8 or higher
- Snowflake account
- The following Python libraries (see `requirements.txt`):
  - `snowflake-connector-python`
  - `snowflake-snowpark-python`
  - `python-dotenv`
  - `streamlit`
  - `langchain_text_splitters`
  - `graphviz`
  - `trulens-core`

---

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/your-repo/rag-pipeline.git
    cd rag-pipeline
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Configure Snowflake connection:
    - Create a `.env` file in the root directory with the following content:
      ```env
      SNOWFLAKE_ACCOUNT=<your_account>
      SNOWFLAKE_USER=<your_user>
      SNOWFLAKE_PASSWORD=<your_password>
      SNOWFLAKE_WAREHOUSE=<your_warehouse>
      SNOWFLAKE_DATABASE=<your_database>
      ```

---

## Usage

### Starting the Application

1. Run the Streamlit application:
    ```bash
    streamlit run streamlit_app.py
    ```

2. Open the provided URL in your browser to access the application.

### Uploading PDFs

1. Navigate to the **Upload PDFs** section in the sidebar.
2. Drag and drop or select one or more PDF files for ingestion.
3. The application will process the files, parse content, and generate summaries.

### Querying Documents

1. Navigate to the **Chatbot** section in the sidebar.
2. Start typing your queries in the chat input field.
3. View responses with optional flowchart visualizations.

---

## Architecture Overview

### Workflow

1. **File Upload**: PDFs are uploaded and stored in a Snowflake stage.
2. **Content Parsing**:
    - Extracted and split into manageable chunks.
    - Metadata like headers (H1, H2, H3) is preserved.
3. **Summarization & Captioning**:
    - Summaries and captions are generated using Snowflake Cortex and Mistral LLM.
4. **Querying**:
    - User queries are matched against the processed content.
    - Responses are generated with optional flowchart visualizations.

### Key Components

- **`connector.py`**: Establishes a connection to Snowflake.
- **`dynamicUploads.py`**: Handles the PDF upload and processing pipeline.
- **`query_search_service.py`**: Executes queries against the processed content.
- **`streamlit_app.py`**: Frontend application built with Streamlit.

---

## Directory Structure

```
├── RAG/
│   ├── connector.py             # Snowflake connection setup
│   ├── dynamicUploads.py        # Handles PDF ingestion and processing
│   ├── parse_docs.py            # Splits PDF content into chunks
│   ├── query_search_service.py  # Query execution and response handling
│   └── load_pdfs.py             # Fetches uploaded PDFs
├── requirements.txt             # Project dependencies
├── streamlit_app.py             # Streamlit frontend
├── .env                         # Snowflake credentials (not in repo)
└── README.md                    # Documentation
```

---

## License

This project is licensed under the [MIT License](LICENSE).

Feel free to contribute or submit issues for improvements!

