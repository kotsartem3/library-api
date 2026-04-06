class TestBooks:
    def test_get_books_empty(self, client):
        response = client.get("/api/books")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_create_book(self, client):
        response = client.post("/api/books", json={
            "title": "Kobzar",
            "genre": "poetry",
            "year_published": 1840,
            "created_by": "Коць Артем",
        })

        assert response.status_code == 201
        data = response.get_json()
        assert "id" in data
        assert data["title"] == "Kobzar"
        assert data["genre"] == "poetry"
        assert data["year_published"] == 1840
        assert data["created_by"] == "Коць Артем"

    def test_create_book_without_title(self, client):
        response = client.post("/api/books", json={
            "genre": "poetry",
            "created_by": "Коць Артем",
        })

        assert response.status_code == 400

    def test_create_book_without_created_by(self, client):
        response = client.post("/api/books", json={
            "title": "Kobzar",
            "genre": "poetry",
        })

        assert response.status_code == 400

    def test_create_book_with_author(self, client):
        author = client.post("/api/authors", json={
            "name": "Леся Українка",
            "birth_year": 1871,
        }).get_json()

        response = client.post("/api/books", json={
            "title": "Lisova Pisnia",
            "genre": "drama",
            "year_published": 1911,
            "author_id": author["id"],
            "created_by": "Коць Артем",
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data["author_id"] == author["id"]
        assert data["created_by"] == "Коць Артем"

    def test_create_book_with_nonexistent_author(self, client):
        response = client.post("/api/books", json={
            "title": "Unknown Book",
            "author_id": 999,
            "created_by": "Коць Артем",
        })

        assert response.status_code == 400

    def test_get_book_by_id(self, client):
        created = client.post("/api/books", json={
            "title": "Tygrolovy",
            "genre": "novel",
            "year_published": 1944,
            "created_by": "Коць Артем",
        }).get_json()

        response = client.get(f"/api/books/{created['id']}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["id"] == created["id"]
        assert data["title"] == "Tygrolovy"

    def test_get_book_not_found(self, client):
        response = client.get("/api/books/999")
        assert response.status_code == 404

    def test_delete_book(self, client):
        created = client.post("/api/books", json={
            "title": "Misto",
            "genre": "novel",
            "created_by": "Коць Артем",
        }).get_json()

        response = client.delete(f"/api/books/{created['id']}")
        assert response.status_code == 204

        check = client.get(f"/api/books/{created['id']}")
        assert check.status_code == 404


class TestBooksFilter:
    def test_filter_by_genre(self, client):
        client.post("/api/books", json={
            "title": "Kobzar",
            "genre": "poetry",
            "created_by": "Коць Артем",
        })
        client.post("/api/books", json={
            "title": "Tygrolovy",
            "genre": "novel",
            "created_by": "Коць Артем",
        })

        response = client.get("/api/books?genre=poetry")
        data = response.get_json()

        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["title"] == "Kobzar"

    def test_filter_by_author_id(self, client):
        author1 = client.post("/api/authors", json={
            "name": "Тарас Шевченко",
        }).get_json()

        author2 = client.post("/api/authors", json={
            "name": "Іван Франко",
        }).get_json()

        client.post("/api/books", json={
            "title": "Kobzar",
            "author_id": author1["id"],
            "created_by": "Коць Артем",
        })
        client.post("/api/books", json={
            "title": "Zakhar Berkut",
            "author_id": author2["id"],
            "created_by": "Коць Артем",
        })

        response = client.get(f"/api/books?author_id={author1['id']}")
        data = response.get_json()

        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["title"] == "Kobzar"
        assert data[0]["author_id"] == author1["id"]

    def test_search_by_title(self, client):
        client.post("/api/books", json={
            "title": "Kobzar",
            "genre": "poetry",
            "created_by": "Коць Артем",
        })
        client.post("/api/books", json={
            "title": "Misto",
            "genre": "novel",
            "created_by": "Коць Артем",
        })

        response = client.get("/api/books?q=kob")
        data = response.get_json()

        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["title"] == "Kobzar"

    def test_filter_no_results(self, client):
        client.post("/api/books", json={
            "title": "Kobzar",
            "genre": "poetry",
            "created_by": "Коць Артем",
        })

        response = client.get("/api/books?genre=fantasy")
        assert response.status_code == 200
        assert response.get_json() == []