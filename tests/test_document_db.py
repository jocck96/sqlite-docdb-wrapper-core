import unittest
from src.document_db import SQLiteDocumentDB

class TestSQLiteDocumentDB(unittest.TestCase):
    def setUp(self):
        # Use in-memory database for isolated, fast tests
        self.db = SQLiteDocumentDB(":memory:")

    def tearDown(self):
        self.db.close()

    def test_insert_and_get(self):
        doc = {"name": "Alice", "age": 30}
        doc_id = self.db.insert(doc)
        
        self.assertEqual(doc_id, 1)
        
        retrieved = self.db.get(doc_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Alice")
        self.assertEqual(retrieved["age"], 30)
        self.assertEqual(retrieved["_id"], doc_id) # Verify _id was injected

    def test_find_simple(self):
        self.db.insert({"name": "Alice", "status": "active"})
        self.db.insert({"name": "Bob", "status": "inactive"})
        self.db.insert({"name": "Charlie", "status": "active"})

        actives = self.db.find({"status": "active"})
        self.assertEqual(len(actives), 2)
        names = [doc["name"] for doc in actives]
        self.assertIn("Alice", names)
        self.assertIn("Charlie", names)

    def test_find_nested_path(self):
        self.db.insert({"name": "Alice", "profile": {"age": 30, "gender": "female"}})
        self.db.insert({"name": "Bob", "profile": {"age": 40, "gender": "male"}})

        # Query using dot-notation path
        res = self.db.find({"profile.gender": "female"})
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "Alice")

    def test_update_patch(self):
        self.db.insert({"name": "Alice", "status": "pending", "meta": {"logins": 5}})
        
        # Apply update
        count = self.db.update({"name": "Alice"}, {"status": "active", "meta": {"logins": 6, "verified": True}})
        self.assertEqual(count, 1)

        updated = self.db.find({"name": "Alice"})[0]
        self.assertEqual(updated["status"], "active")
        # SQLite's json_patch merges objects
        self.assertEqual(updated["meta"]["logins"], 6)
        self.assertEqual(updated["meta"]["verified"], True)

    def test_delete(self):
        self.db.insert({"name": "Alice", "tag": "test"})
        self.db.insert({"name": "Bob", "tag": "prod"})
        
        deleted = self.db.delete({"tag": "test"})
        self.assertEqual(deleted, 1)

        self.assertEqual(len(self.db.find({"tag": "test"})), 0)
        self.assertEqual(len(self.db.find({"tag": "prod"})), 1)

    def test_transactions_rollback(self):
        # Put inserts in transaction that fails
        try:
            with self.db.transaction():
                self.db.insert({"name": "John"})
                self.db.insert({"name": "Doe"})
                # Force error
                raise ValueError("Oops!")
        except ValueError:
            pass

        # Since it raised ValueError, both inserts should have rolled back
        self.assertEqual(len(self.db.find()), 0)

    def test_transactions_commit(self):
        with self.db.transaction():
            self.db.insert({"name": "John"})
            self.db.insert({"name": "Doe"})

        self.assertEqual(len(self.db.find()), 2)

    def test_indexing(self):
        self.db.insert({"name": "Alice", "profile": {"score": 95}})
        self.db.insert({"name": "Bob", "profile": {"score": 88}})
        
        # Create virtual index
        success = self.db.create_index("idx_profile_score", "profile.score")
        self.assertTrue(success)

        # Ensure index queries still execute perfectly
        high_scores = self.db.find({"profile.score": 95})
        self.assertEqual(len(high_scores), 1)
        self.assertEqual(high_scores[0]["name"], "Alice")

if __name__ == "__main__":
    unittest.main()
