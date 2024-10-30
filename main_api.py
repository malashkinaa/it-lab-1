from fastapi import FastAPI, HTTPException, Path, Query, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from data_types import parse_data, SUPPORTED_DATA_TYPES
from database import Database
from table import Table
from schema import Schema
from attributes import Attribute
from row import Row
from operations import table_product
import pandas as pd
import os

app = FastAPI(title="Database Management API")

# Initialize databases dictionary
databases: Dict[str, Database] = {}  # Key: Database name, Value: Database instance


# Pydantic Models

class AttributeModel(BaseModel):
    name: str
    data_type: str


class SchemaModel(BaseModel):
    attributes: List[AttributeModel]


class TableModel(BaseModel):
    name: str
    table_schema: SchemaModel  # Renamed to avoid shadowing


class RowModel(BaseModel):
    data: Dict[str, Optional[str]]  # Values as strings; will be parsed based on schema


class ProductTablesRequest(BaseModel):
    table1_fullname: str  # Format: "db_name.table_name"
    table2_fullname: str
    destination_db_name: str
    new_table_name: str


class CreateDatabaseRequest(BaseModel):
    name: str


class EditTableRequest(BaseModel):
    new_table_name: Optional[str] = None
    attributes: Optional[List[AttributeModel]] = None


# Utility Functions

def get_all_tables():
    all_tables = []
    for db_name, db in databases.items():
        for table_name in db.tables.keys():
            all_tables.append(f"{db_name}.{table_name}")
    return all_tables


# Database Endpoints

@app.get("/databases", response_model=List[str])
def list_databases():
    """List all databases."""
    return list(databases.keys())


@app.post("/databases", status_code=201)
def create_database(db: CreateDatabaseRequest):
    """Create a new database."""
    db_name = db.name
    if db_name in databases:
        raise HTTPException(status_code=400, detail=f"Database '{db_name}' already exists.")
    databases[db_name] = Database(db_name)
    return {"message": f"Database '{db_name}' created successfully."}


@app.get("/databases/{db_name}", response_model=Dict)
def get_database(db_name: str = Path(..., description="Name of the database")):
    """Get details of a specific database."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    return {"name": db.name, "tables": list(db.tables.keys())}


@app.put("/databases/{db_name}", response_model=Dict)
def edit_database(db_name: str, new_db_name: str = Query(..., description="New name for the database")):
    """Edit the name of a database."""
    if new_db_name == db_name:
        raise HTTPException(status_code=400, detail="New database name must be different.")
    if new_db_name in databases:
        raise HTTPException(status_code=400, detail=f"Database '{new_db_name}' already exists.")
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    db.name = new_db_name
    databases[new_db_name] = db
    del databases[db_name]
    return {"message": f"Database renamed to '{new_db_name}' successfully."}


@app.delete("/databases/{db_name}", response_model=Dict)
def delete_database(db_name: str):
    """Delete a database."""
    if db_name in databases:
        del databases[db_name]
        return {"message": f"Database '{db_name}' deleted successfully."}
    raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")


# Table Endpoints

@app.get("/databases/{db_name}/tables", response_model=List[str])
def list_tables(db_name: str):
    """List all tables in a database."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    return list(db.tables.keys())


@app.post("/databases/{db_name}/tables", status_code=201)
def create_table(db_name: str, table: TableModel):
    """Create a new table in a database."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table_name = table.name
    if table_name in db.tables:
        raise HTTPException(status_code=400, detail=f"Table '{table_name}' already exists in database '{db_name}'.")
    # Parse attributes
    attr_list = []
    for attr in table.table_schema.attributes:
        if attr.data_type not in SUPPORTED_DATA_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported data type: {attr.data_type}")
        attr_list.append(Attribute(attr.name, attr.data_type))
    schema = Schema(attr_list)
    new_table = Table(table_name, schema)
    db.create_table(new_table)
    return {"message": f"Table '{table_name}' created successfully in database '{db_name}'."}


@app.get("/databases/{db_name}/tables/{table_name}", response_model=Dict)
def get_table(db_name: str, table_name: str):
    """Get details of a specific table."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table = db.get_table(table_name)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")
    return {
        "name": table.name,
        "schema": [{"name": attr.name, "data_type": attr.data_type} for attr in table.schema.attributes],
        "rows_count": len(table.rows)
    }


@app.put("/databases/{db_name}/tables/{table_name}", response_model=Dict)
def edit_table(db_name: str, table_name: str, request: EditTableRequest = Body(...)):
    """Edit a table's name and/or schema."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table = db.get_table(table_name)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")

    # Handle schema change
    if request.attributes:
        if table.rows:
            raise HTTPException(status_code=400,
                                detail="Cannot modify schema of a table that contains data. Please delete all rows first.")
        attr_list = []
        for attr in request.attributes:
            if attr.data_type not in SUPPORTED_DATA_TYPES:
                raise HTTPException(status_code=400, detail=f"Unsupported data type: {attr.data_type}")
            attr_list.append(Attribute(attr.name, attr.data_type))
        table.schema = Schema(attr_list)

    # Handle table name change
    if request.new_table_name and request.new_table_name != table_name:
        if request.new_table_name in db.tables:
            raise HTTPException(status_code=400,
                                detail=f"Table '{request.new_table_name}' already exists in database '{db_name}'.")
        table.name = request.new_table_name
        db.tables[request.new_table_name] = table
        del db.tables[table_name]

    return {"message": f"Table '{table_name}' updated successfully."}


@app.delete("/databases/{db_name}/tables/{table_name}", response_model=Dict)
def delete_table(db_name: str, table_name: str):
    """Delete a table from a database."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    if table_name in db.tables:
        del db.tables[table_name]
        return {"message": f"Table '{table_name}' deleted successfully from database '{db_name}'."}
    raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")


# Row Endpoints

@app.get("/databases/{db_name}/tables/{table_name}/rows", response_model=List[Dict])
def list_rows(db_name: str, table_name: str):
    """List all rows in a table."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table = db.get_table(table_name)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")
    return [row.data for row in table.rows]


@app.post("/databases/{db_name}/tables/{table_name}/rows", status_code=201)
def insert_row(db_name: str, table_name: str, row: RowModel):
    """Insert a new row into a table."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table = db.get_table(table_name)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")

    parsed_data = {}
    for attr in table.schema.attributes:
        value = row.data.get(attr.name)
        try:
            parsed_value = parse_data(value, attr.data_type)
            parsed_data[attr.name] = parsed_value
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid input for '{attr.name}': {str(e)}")

    new_row = Row(parsed_data)
    table.insert_row(new_row)
    return {"message": "Row inserted successfully."}


@app.get("/databases/{db_name}/tables/{table_name}/rows/{row_index}", response_model=Dict)
def get_row(db_name: str, table_name: str, row_index: int = Path(..., ge=0)):
    """Get a specific row by index."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table = db.get_table(table_name)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")
    try:
        row = table.rows[row_index]
        return row.data
    except IndexError:
        raise HTTPException(status_code=404, detail="Row not found.")


@app.put("/databases/{db_name}/tables/{table_name}/rows/{row_index}", response_model=Dict)
def update_row(db_name: str, table_name: str, row_index: int, row: RowModel):
    """Update a specific row by index."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table = db.get_table(table_name)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")
    if row_index >= len(table.rows) or row_index < 0:
        raise HTTPException(status_code=404, detail="Row not found.")

    parsed_data = {}
    for attr in table.schema.attributes:
        value = row.data.get(attr.name)
        try:
            parsed_value = parse_data(value, attr.data_type)
            parsed_data[attr.name] = parsed_value
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid input for '{attr.name}': {str(e)}")

    updated_row = Row(parsed_data)
    table.update_row(row_index, updated_row)
    return {"message": "Row updated successfully."}


@app.delete("/databases/{db_name}/tables/{table_name}/rows/{row_index}", response_model=Dict)
def delete_row(db_name: str, table_name: str, row_index: int):
    """Delete a specific row by index."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table = db.get_table(table_name)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")
    try:
        table.delete_row(row_index)
        return {"message": "Row deleted successfully."}
    except IndexError:
        raise HTTPException(status_code=404, detail="Row not found.")


# Export Table Endpoint

@app.get("/databases/{db_name}/tables/{table_name}/export", response_class=FileResponse)
def export_table(db_name: str, table_name: str):
    """Export table data to an Excel file."""
    db = databases.get(db_name)
    if not db:
        raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found.")
    table = db.get_table(table_name)
    if not table:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found in database '{db_name}'.")

    # Convert table data to DataFrame
    data = [row.data for row in table.rows]
    df = pd.DataFrame(data)

    # Save DataFrame to Excel file
    exports_dir = "exports"
    os.makedirs(exports_dir, exist_ok=True)
    file_path = os.path.join(exports_dir, f"{db_name}_{table_name}.xlsx")
    df.to_excel(file_path, index=False)

    # Return the file as a response
    return FileResponse(
        path=file_path,
        filename=f"{table_name}.xlsx",
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# Product Tables Endpoint

@app.post("/product_tables", response_model=Dict)
def product_tables(request: ProductTablesRequest):
    """
    Perform a product operation on two tables and store the result in a destination database.
    """
    try:
        db1_name, table1_name = request.table1_fullname.split('.')
        db2_name, table2_name = request.table2_fullname.split('.')
    except ValueError:
        raise HTTPException(status_code=400, detail="Table fullnames must be in 'db_name.table_name' format.")

    db1 = databases.get(db1_name)
    db2 = databases.get(db2_name)
    destination_db = databases.get(request.destination_db_name)

    if not db1 or not db2 or not destination_db:
        raise HTTPException(status_code=404, detail="One or more databases not found.")

    table1 = db1.get_table(table1_name)
    table2 = db2.get_table(table2_name)

    if not table1 or not table2:
        raise HTTPException(status_code=404, detail="One or both tables not found.")

    if request.new_table_name in destination_db.tables:
        raise HTTPException(
            status_code=400,
            detail=f"Table '{request.new_table_name}' already exists in database '{request.destination_db_name}'."
        )

    # Perform table product operation
    new_table = table_product(table1, table2, request.new_table_name)
    destination_db.create_table(new_table)

    return {
        "message": f"Product table '{request.new_table_name}' created successfully in database '{request.destination_db_name}'."}


# Additional Endpoints (Optional)

@app.get("/tables", response_model=List[str])
def list_all_tables():
    """List all tables across all databases."""
    return get_all_tables()


@app.get("/tables/export_all", response_model=Dict)
def export_all_tables():
    """Export all tables to Excel files."""
    exported_files = []
    for db_name, db in databases.items():
        for table_name, table in db.tables.items():
            data = [row.data for row in table.rows]
            df = pd.DataFrame(data)
            exports_dir = "exports"
            os.makedirs(exports_dir, exist_ok=True)
            file_path = os.path.join(exports_dir, f"{db_name}_{table_name}.xlsx")
            df.to_excel(file_path, index=False)
            exported_files.append(file_path)
    return {"exported_files": exported_files}
