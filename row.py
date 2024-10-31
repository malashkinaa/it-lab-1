# row.py

class Row:
    def __init__(self, data: dict):
        self.data = data  # Key: Attribute name, Value: Data

    def __eq__(self, other):
        if isinstance(other, Row):
            return self.data == other.data
        return False

    def __hash__(self):
        return hash(frozenset(self.data.items()))        
