# table.py

from data_types import validate_data
from row import Row
from schema import Schema


class Table:
    def __init__(self, name: str, schema: Schema):
        self.name = name
        self.schema = schema
        self.rows = []  # List of Row instances

    def insert_row(self, row: Row):
        # Validate row against schema before inserting
        for attr in self.schema.attributes:
            value = row.data.get(attr.name)
            if not validate_data(value, attr.data_type):
                raise ValueError(f"Invalid data type for attribute {attr.name}. Expected {attr.data_type}.")
        self.rows.append(row)

    def update_row(self, index: int, row: Row):
        # Validate row against schema before updating
        for attr in self.schema.attributes:
            value = row.data.get(attr.name)
            if not validate_data(value, attr.data_type):
                raise ValueError(f"Invalid data type for attribute {attr.name}. Expected {attr.data_type}.")
        if index < 0 or index >= len(self.rows):
            raise IndexError("Row index out of range.")
        self.rows[index] = row

    def delete_row(self, index: int):
        if index < 0 or index >= len(self.rows):
            raise IndexError("Row index out of range.")
        del self.rows[index]

    def delete_row(self, row: Row):
        # Validate row against schema before inserting
        for attr in self.schema.attributes:
            value = row.data.get(attr.name)
            if not validate_data(value, attr.data_type):
                raise ValueError(f"Invalid data type for attribute {attr.name}. Expected {attr.data_type}.")
        self.rows.remove(row)