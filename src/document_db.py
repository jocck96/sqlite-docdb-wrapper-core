import sqlite3
import json
from contextlib import contextmanager

class SQLiteDocumentDB:
    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc TEXT NOT NULL
                )
            """)

    def close(self):
        self.conn.close()

    @contextmanager
    def transaction(self):
        """Context manager for grouping operations in a transaction."""
        try:
            self.conn.execute("BEGIN TRANSACTION")
            yield
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def _build_where_clause(self, query):
        """Compiles a dict query into JSON SQL extracts."""
        if not query:
            return "", []

        clauses = []
        params = []

        for key, val in query.items():
            # Support nested path query (e.g. "profile.age" -> "$.profile.age")
            json_path = "$." + key
            
            if val is None:
                clauses.append(f"json_extract(doc, '{json_path}') IS NULL")
            elif isinstance(val, (list, dict)):
                # Match serialized string or json matching
                clauses.append(f"json_extract(doc, '{json_path}') = ?")
                params.append(json.dumps(val))
            else:
                clauses.append(f"json_extract(doc, '{json_path}') = ?")
                params.append(val)

        return "WHERE " + " AND ".join(clauses), params

    def insert(self, document):
        """Inserts a single document. Returns the inserted document ID."""
        if not isinstance(document, dict):
            raise TypeError("Document must be a dictionary")

        doc_copy = document.copy()
        
        with self.conn:
            # First insert empty JSON or partial to get row ID
            cursor = self.conn.execute(
                "INSERT INTO documents (doc) VALUES (?)",
                (json.dumps(doc_copy),)
            )
            inserted_id = cursor.lastrowid
            
            # Update the document to contain the internal _id
            doc_copy["_id"] = inserted_id
            self.conn.execute(
                "UPDATE documents SET doc = ? WHERE id = ?",
                (json.dumps(doc_copy), inserted_id)
            )
            
        return inserted_id

    def get(self, doc_id):
        """Retrieves a document by its integer ID."""
        cursor = self.conn.execute(
            "SELECT doc FROM documents WHERE id = ?",
            (doc_id,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["doc"])
        return None

    def find(self, query=None):
        """Finds all documents matching the query dictionary."""
        where_clause, params = self._build_where_clause(query)
        sql = f"SELECT doc FROM documents {where_clause}"
        
        cursor = self.conn.execute(sql, params)
        rows = cursor.fetchall()
        return [json.loads(row["doc"]) for row in rows]

    def update(self, query, update_fields):
        """Updates documents matching the query by applying json_patch.
        
        Returns the number of affected documents.
        """
        if not isinstance(update_fields, dict):
            raise TypeError("Update fields must be a dictionary")

        where_clause, params = self._build_where_clause(query)
        
        # SQL UPDATE query using json_patch
        sql = f"UPDATE documents SET doc = json_patch(doc, ?) {where_clause}"
        all_params = [json.dumps(update_fields)] + params
        
        with self.conn:
            cursor = self.conn.execute(sql, all_params)
            return cursor.rowcount

    def delete(self, query):
        """Deletes all documents matching the query.
        
        Returns the number of deleted documents.
        """
        where_clause, params = self._build_where_clause(query)
        sql = f"DELETE FROM documents {where_clause}"
        
        with self.conn:
            cursor = self.conn.execute(sql, params)
            return cursor.rowcount

    def create_index(self, index_name, field_path):
        """Creates an index on a JSON field path (e.g. 'profile.age') using a virtual column."""
        # Convert path to generated column name (e.g. 'profile_age')
        col_name = f"gen_{field_path.replace('.', '_')}"
        json_path = "$." + field_path

        # SQLite generated column SQL syntax
        alter_sql = f"""
            ALTER TABLE documents 
            ADD COLUMN {col_name} TEXT 
            GENERATED ALWAYS AS (json_extract(doc, '{json_path}')) STORED
        """
        index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON documents ({col_name})"

        with self.conn:
            try:
                self.conn.execute(alter_sql)
            except sqlite3.OperationalError as e:
                # Column might already exist, ignore if so
                if "duplicate column name" not in str(e).lower():
                    raise e
            self.conn.execute(index_sql)
        return True

# End of SQLite NoSQL database wrapper module
