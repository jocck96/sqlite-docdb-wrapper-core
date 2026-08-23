# sqlite-docdb-wrapper-core - Shared Open Source Project - Open-Source Project

A lightweight document store database wrapper built on top of SQLite using native JSON capabilities (`json_extract`, `json_patch`). It provides a Pythonic NoSQL API similar to TinyDB but inherits SQLite's ACID transaction safety, binary storage efficiency, and indexing speed.

## Project Features

- **No external dependencies**: Uses only Python's standard `sqlite3` and `json` libraries.
- **Dot-Notation Path Search**: Query nested document fields natively (e.g. `{"profile.score": 95}` compiles to `json_extract(doc, '$.profile.score')`).
- **NoSQL CRUD API**: Simply call `insert`, `get`, `find`, `update` (merges fields via native `json_patch`), and `delete`.
- **Generated Indexes**: Speed up complex queries by automatically adding SQLite generated columns and indexing them dynamically.
- **Transactional Context Manager**: Group operations into transactions with automated rollback on failure.

## Repository Layout

```text
sqlite-docdb-wrapper-core/
├── src/
│   └── document_db.py
├── tests/
│   └── test_document_db.py
└── README.md
```

## Build instructions

Ensure Python (version 3.8 or later) is installed. There are no external packages to install.

## Running the Project

Here is a complete usage script showing CRUD, nested queries, transactions, and indexing:

```python
from src.document_db import SQLiteDocumentDB

# 1. Connect to file database (or ':memory:' for transient store)
db = SQLiteDocumentDB("mydb.db")

# 2. Insert documents (returns auto-incremented _id)
alice_id = db.insert({
    "name": "Alice",
    "role": "admin",
    "profile": {
        "score": 95,
        "verified": True
    }
})

db.insert({
    "name": "Bob",
    "role": "editor",
    "profile": {
        "score": 88,
        "verified": False
    }
})

# 3. Retrieve single document
print(db.get(alice_id)) 
# Output: {'name': 'Alice', 'role': 'admin', 'profile': {'score': 95, 'verified': True}, '_id': 1}

# 4. Query using dot notation path
editors = db.find({"role": "editor"})
high_scorers = db.find({"profile.score": 95})

# 5. Update using json_patch
db.update({"name": "Bob"}, {"profile": {"score": 90, "verified": True}})

# 6. Transaction safety
try:
    with db.transaction():
        db.insert({"name": "Charlie"})
        raise ValueError("Something went wrong!")
except ValueError:
    print("Charlie rolled back safely!")

# 7. Create indexes on JSON fields
db.create_index("idx_score", "profile.score")

db.close()
```

## Running Tests

Run the test suite using Python's built-in `unittest` framework:

```bash
python -m unittest tests/test_document_db.py
```
This tests document CRUD lifecycle, nested queries, transaction commit/rollback, and virtual column indexing.

---
*Released under the MIT License by Sassywow.*
