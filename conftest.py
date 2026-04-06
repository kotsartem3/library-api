import pytest
import psycopg2
from app import create_app

TEST_DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 55432,
    "dbname": "library_test_db",
    "user": "postgres",
    "password": "secret",
}

ADMIN_DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 55432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "secret",
}


@pytest.fixture(scope="session")
def test_db():
    admin_conn = psycopg2.connect(**ADMIN_DB_CONFIG)
    admin_conn.autocommit = True

    with admin_conn.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS library_test_db")
        cur.execute("CREATE DATABASE library_test_db")

    admin_conn.close()

    yield TEST_DB_CONFIG

    admin_conn = psycopg2.connect(**ADMIN_DB_CONFIG)
    admin_conn.autocommit = True

    with admin_conn.cursor() as cur:
        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
        """, (TEST_DB_CONFIG["dbname"],))
        cur.execute("DROP DATABASE IF EXISTS library_test_db")

    admin_conn.close()


@pytest.fixture(scope="session")
def app(test_db):
    app = create_app(test_db)
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="function")
def client(app):
    conn = psycopg2.connect(**app.config["DB_CONFIG"])
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE books, authors RESTART IDENTITY CASCADE")

    conn.close()

    with app.test_client() as client:
        yield client