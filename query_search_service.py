# There is also a way to query the search service using the inbuilt service_preview command in SQL on the snowflake website
# Check that as well

from connector import *
from snowflake.core import Root

def query_search(session):

    load_dotenv()
    database = os.getenv("SNOWFLAKE_DATABASE")

    root = Root(session)
    my_service = (root
    .databases[database]
    .schemas["PUBLIC"]
    .cortex_search_services["pdf_search_v2"]
    )

    resp = my_service.search(
    query="cross and self attention",
    columns=["chunk_id", "content"],
    limit=5
    )
    print(resp.to_json())


if __name__ == "__main__":
    session = connect()
    query_search(session)
