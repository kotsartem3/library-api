import os
import psycopg2
from flask import Flask, jsonify, request

DEFAULT_DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname": os.environ.get("POSTGRES_DB", "postgres"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "secret"),
}


def get_connection(db_config=None):
    config = db_config or DEFAULT_DB_CONFIG
    return psycopg2.connect(**config)


def init_db(db_config=None):
    conn = get_connection(db_config)
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS authors (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                birth_year INTEGER
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                genre VARCHAR(100),
                year_published INTEGER,
                author_id INTEGER REFERENCES authors(id) ON DELETE SET NULL,
                created_by VARCHAR(255) NOT NULL
            )
            """
        )

    conn.close()


def create_app(db_config=None):
    app = Flask(__name__)
    app.config["DB_CONFIG"] = db_config or DEFAULT_DB_CONFIG

    init_db(app.config["DB_CONFIG"])

    def fetch_one_dict(cur):
        row = cur.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cur.description]
        return dict(zip(columns, row))

    def fetch_all_dicts(cur):
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]

    @app.route("/api/authors", methods=["GET"])
    def get_authors():
        conn = get_connection(app.config["DB_CONFIG"])
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, birth_year FROM authors ORDER BY id")
            authors = fetch_all_dicts(cur)
        conn.close()
        return jsonify(authors), 200

    @app.route("/api/authors", methods=["POST"])
    def create_author():
        data = request.get_json() or {}

        name = data.get("name")
        birth_year = data.get("birth_year")

        if not name:
            return jsonify({"error": "Field 'name' is required"}), 400

        conn = get_connection(app.config["DB_CONFIG"])
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO authors (name, birth_year)
                VALUES (%s, %s)
                RETURNING id, name, birth_year
                """,
                (name, birth_year),
            )
            author = fetch_one_dict(cur)

        conn.close()
        return jsonify(author), 201

    @app.route("/api/authors/<int:author_id>", methods=["GET"])
    def get_author_by_id(author_id):
        conn = get_connection(app.config["DB_CONFIG"])
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, birth_year FROM authors WHERE id = %s",
                (author_id,),
            )
            author = fetch_one_dict(cur)

        conn.close()

        if not author:
            return jsonify({"error": "Author not found"}), 404

        return jsonify(author), 200

    @app.route("/api/authors/<int:author_id>", methods=["DELETE"])
    def delete_author(author_id):
        conn = get_connection(app.config["DB_CONFIG"])
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute("DELETE FROM authors WHERE id = %s RETURNING id", (author_id,))
            deleted = cur.fetchone()

        conn.close()

        if not deleted:
            return jsonify({"error": "Author not found"}), 404

        return "", 204

    @app.route("/api/authors/<int:author_id>/books", methods=["GET"])
    def get_author_books(author_id):
        conn = get_connection(app.config["DB_CONFIG"])

        with conn.cursor() as cur:
            cur.execute("SELECT id FROM authors WHERE id = %s", (author_id,))
            author = cur.fetchone()

            if not author:
                conn.close()
                return jsonify({"error": "Author not found"}), 404

            cur.execute(
                """
                SELECT id, title, genre, year_published, author_id, created_by
                FROM books
                WHERE author_id = %s
                ORDER BY id
                """,
                (author_id,),
            )
            books = fetch_all_dicts(cur)

        conn.close()
        return jsonify(books), 200

    @app.route("/api/books", methods=["GET"])
    def get_books():
        genre = request.args.get("genre")
        author_id = request.args.get("author_id")
        q = request.args.get("q")

        query = """
            SELECT id, title, genre, year_published, author_id, created_by
            FROM books
            WHERE 1=1
        """
        params = []

        if genre:
            query += " AND genre = %s"
            params.append(genre)

        if author_id:
            query += " AND author_id = %s"
            params.append(int(author_id))

        if q:
            query += " AND LOWER(title) LIKE %s"
            params.append(f"%{q.lower()}%")

        query += " ORDER BY id"

        conn = get_connection(app.config["DB_CONFIG"])
        with conn.cursor() as cur:
            cur.execute(query, params)
            books = fetch_all_dicts(cur)
        conn.close()

        return jsonify(books), 200

    @app.route("/api/books", methods=["POST"])
    def create_book():
        data = request.get_json() or {}

        title = data.get("title")
        genre = data.get("genre")
        year_published = data.get("year_published")
        author_id = data.get("author_id")
        created_by = data.get("created_by")

        if not title:
            return jsonify({"error": "Field 'title' is required"}), 400

        if not created_by:
            return jsonify({"error": "Field 'created_by' is required"}), 400

        conn = get_connection(app.config["DB_CONFIG"])
        conn.autocommit = True

        with conn.cursor() as cur:
            if author_id is not None:
                cur.execute("SELECT id FROM authors WHERE id = %s", (author_id,))
                author = cur.fetchone()
                if not author:
                    conn.close()
                    return jsonify({"error": "Author does not exist"}), 400

            cur.execute(
                """
                INSERT INTO books (title, genre, year_published, author_id, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, title, genre, year_published, author_id, created_by
                """,
                (title, genre, year_published, author_id, created_by),
            )
            book = fetch_one_dict(cur)

        conn.close()
        return jsonify(book), 201

    @app.route("/api/books/<int:book_id>", methods=["GET"])
    def get_book_by_id(book_id):
        conn = get_connection(app.config["DB_CONFIG"])
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, genre, year_published, author_id, created_by
                FROM books
                WHERE id = %s
                """,
                (book_id,),
            )
            book = fetch_one_dict(cur)

        conn.close()

        if not book:
            return jsonify({"error": "Book not found"}), 404

        return jsonify(book), 200

    @app.route("/api/books/<int:book_id>", methods=["DELETE"])
    def delete_book(book_id):
        conn = get_connection(app.config["DB_CONFIG"])
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute("DELETE FROM books WHERE id = %s RETURNING id", (book_id,))
            deleted = cur.fetchone()

        conn.close()

        if not deleted:
            return jsonify({"error": "Book not found"}), 404

        return "", 204

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
