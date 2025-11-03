import os
import psycopg2
from psycopg2.extras import DictCursor

def get_db_connection():
    """
    Estabilish a new database connection.
    The connection parameters are retrieved from environment variables.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "26257"),  # CockroachDB default port
            dbname=os.getenv("DB_NAME", "media_server"),
            user=os.getenv("DB_USER", "root"),  # CockroachDB default user
            password=os.getenv("DB_PASSWORD", ""),  # CockroachDB no password by default
            cursor_factory=DictCursor
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        raise
