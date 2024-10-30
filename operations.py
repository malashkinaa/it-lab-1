# operations.py
from row import Row
from schema import Schema
from table import Table


# operations.py
def table_product(table1: Table, table2: Table, new_table_name: str) -> Table:
    new_attributes = table1.schema.attributes + table2.schema.attributes
    new_schema = Schema(new_attributes)
    new_table = Table(name=new_table_name, schema=new_schema)

    for row1 in table1.rows:
        for row2 in table2.rows:
            combined_data = {**row1.data, **row2.data}
            new_row = Row(combined_data)
            new_table.insert_row(new_row)

    return new_table
