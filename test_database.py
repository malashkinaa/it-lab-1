# test_database.py

import unittest
from database import Database
from table import Table
from schema import Schema
from attributes import Attribute
from row import Row

class TestDatabaseOperations(unittest.TestCase):
    def test_table_creation(self):
        attr1 = Attribute('id', 'integer')
        attr2 = Attribute('name', 'string')
        schema = Schema([attr1, attr2])
        table = Table('users', schema)
        db = Database('test_db')
        db.create_table(table)
        self.assertIn('users', db.tables)

    def test_insert_row(self):
        attr = Attribute('age', 'integer')
        schema = Schema([attr])
        table = Table('ages', schema)
        row = Row({'age': 25})
        table.insert_row(row)
        self.assertEqual(len(table.rows), 1)

    def test_table_product(self):
        # Setup tables and test the product operation
        pass  # Implement similar to above
