from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from data_types import parse_data, SUPPORTED_DATA_TYPES
from database import Database
from table import Table
from schema import Schema
from attributes import Attribute
from row import Row
from operations import table_product
from fastapi.responses import StreamingResponse
import io
from fastapi.responses import FileResponse
import pandas as pd
import os

import pandas as pd

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize databases dictionary
databases = {}  # Key: Database name, Value: Database instance




def get_all_tables():
    all_tables = []
    for db_name, db in databases.items():
        for table_name in db.tables.keys():
            all_tables.append(f"{db_name}.{table_name}")
    return all_tables


@app.get("/databases/{db_name}/tables/{table_name}/export")
def export_table(db_name: str, table_name: str):
    db = databases.get(db_name)
    if not db:
        return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)
    table = db.get_table(table_name)
    if not table:
        return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)

    # Convert table data to DataFrame
    data = [row.data for row in table.rows]
    df = pd.DataFrame(data)

    # Save DataFrame to Excel file
    file_path = f"exports/{db_name}_{table_name}.xlsx"
    os.makedirs("exports", exist_ok=True)
    df.to_excel(file_path, index=False)

    # Return the file as a response
    return FileResponse(path=file_path, filename=f"{table_name}.xlsx",
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "databases": databases})


@app.get("/create_database")
def get_create_database(request: Request):
    return templates.TemplateResponse("create_database.html", {"request": request})


@app.get("/databases/{db_name}/tables/{table_name}/delete_table")
def delete_table(request: Request, db_name: str, table_name: str):
    db = databases.get(db_name)
    if db and table_name in db.tables:
        del db.tables[table_name]
    return RedirectResponse(f"/databases/{db_name}", status_code=303)


@app.get("/databases/{db_name}/tables/{table_name}/edit_table")
def get_edit_table(request: Request, db_name: str, table_name: str):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("error.html",
                                          {"request": request, "error": f"Database '{db_name}' not found."})
    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("error.html",
                                          {"request": request, "error": f"Table '{table_name}' not found."})
    attributes = ','.join([f"{attr.name}:{attr.data_type}" for attr in table.schema.attributes])
    return templates.TemplateResponse("edit_table.html", {"request": request, "db_name": db_name, "table": table,
                                                          "attributes": attributes})


@app.post("/databases/{db_name}/tables/{table_name}/edit_table")
def post_edit_table(request: Request, db_name: str, table_name: str, new_table_name: str = Form(...),
                    attributes: str = Form(...)):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("edit_table.html",
                                          {"request": request, "error": f"Database '{db_name}' not found.",
                                           "db_name": db_name})
    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("edit_table.html",
                                          {"request": request,
                                           "error": f"Table '{table_name}' not found in database '{db_name}'.",
                                           "db_name": db_name})

    attr_list = []
    try:
        for attr in attributes.split(','):
            name, data_type = attr.strip().split(':')
            data_type = data_type.strip()
            if data_type not in SUPPORTED_DATA_TYPES:
                raise ValueError(f"Unsupported data type: {data_type}")
            attr_list.append(Attribute(name.strip(), data_type))
        schema = Schema(attr_list)

        # Handle schema change carefully
        if table.rows:
            raise ValueError("Cannot modify schema of a table that contains data. Please delete all rows first.")

        # Update table schema and name
        table.schema = schema
        if new_table_name != table_name:
            if new_table_name in db.tables:
                raise ValueError(f"Table '{new_table_name}' already exists in database '{db_name}'.")
            del db.tables[table_name]
            table.name = new_table_name
            db.tables[new_table_name] = table
    except Exception as e:
        return templates.TemplateResponse("edit_table.html",
                                          {"request": request, "error": str(e), "db_name": db_name, "table": table,
                                           "attributes": attributes})
    return RedirectResponse(f"/databases/{db_name}", status_code=303)


@app.post("/create_database")
def post_create_database(request: Request, db_name: str = Form(...)):
    if db_name in databases:
        error = f"Database '{db_name}' already exists."
        return templates.TemplateResponse("create_database.html", {"request": request, "error": error})
    databases[db_name] = Database(db_name)
    return RedirectResponse(f"/databases/{db_name}", status_code=303)


@app.get("/databases/{db_name}")
def view_database(request: Request, db_name: str):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("error.html",
                                          {"request": request, "error": f"Database '{db_name}' not found."})
    return templates.TemplateResponse("database.html", {"request": request, "db": db})


@app.get("/databases/{db_name}/create_table")
def get_create_table(request: Request, db_name: str):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("error.html",
                                          {"request": request, "error": f"Database '{db_name}' not found."})
    return templates.TemplateResponse("create_table.html", {"request": request, "db_name": db_name})


@app.post("/databases/{db_name}/create_table")
def post_create_table(request: Request, db_name: str, table_name: str = Form(...), attributes: str = Form(...)):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("create_table.html",
                                          {"request": request, "error": f"Database '{db_name}' not found.",
                                           "db_name": db_name})
    attr_list = []
    try:
        for attr in attributes.split(','):
            name, data_type = attr.strip().split(':')
            data_type = data_type.strip()
            if data_type not in SUPPORTED_DATA_TYPES:
                raise ValueError(f"Unsupported data type: {data_type}")
            attr_list.append(Attribute(name.strip(), data_type))
        schema = Schema(attr_list)
        table = Table(table_name, schema)
        db.create_table(table)
    except Exception as e:
        return templates.TemplateResponse("create_table.html",
                                          {"request": request, "error": str(e), "db_name": db_name})
    return RedirectResponse(f"/databases/{db_name}", status_code=303)


@app.get("/databases/{db_name}/tables/{table_name}")
def view_table(request: Request, db_name: str, table_name: str):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Database '{db_name}' not found."
        })
    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Table '{table_name}' not found in database '{db_name}'."
        })
    return templates.TemplateResponse("view_table.html", {
        "request": request,
        "db_name": db_name,
        "table": table
    })


@app.get("/databases/{db_name}/tables/{table_name}/insert_row")
def get_insert_row(request: Request, db_name: str, table_name: str):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("insert_row.html", {
            "request": request, "error": f"Database '{db_name}' not found."
        })
    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("insert_row.html", {
            "request": request,
            "error": f"Table '{table_name}' not found in database '{db_name}'.",
            "db_name": db_name
        })
    return templates.TemplateResponse("insert_row.html", {
        "request": request,
        "db_name": db_name,
        "table": table,
        "form_data": {}
    })


@app.post("/databases/{db_name}/tables/{table_name}/insert_row")
async def post_insert_row(request: Request, db_name: str, table_name: str):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("insert_row.html", {
            "request": request, "error": f"Database '{db_name}' not found."
        })
    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("insert_row.html", {
            "request": request,
            "error": f"Table '{table_name}' not found in database '{db_name}'.",
            "db_name": db_name
        })
    form_data = await request.form()
    errors = {}
    parsed_data = {}
    for attr in table.schema.attributes:
        value = form_data.get(attr.name)
        try:
            if attr.data_type == "file":
                content = await value.read()
                filename = value.filename
                content_type = value.content_type
                parsed_value = parse_data(content, attr.data_type)
            else:
                parsed_value = parse_data(value, attr.data_type)
            parsed_data[attr.name] = parsed_value
        except ValueError as e:
            errors[attr.name] = str(e)
    if errors:
        return templates.TemplateResponse("insert_row.html", {
            "request": request,
            "db_name": db_name,
            "table": table,
            "errors": errors,
            "form_data": form_data
        })
    row = Row(parsed_data)
    table.insert_row(row)
    return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)


@app.get("/product_tables")
def get_product_tables(request: Request):
    all_tables = get_all_tables()
    return templates.TemplateResponse("product_tables.html", {
        "request": request,
        "tables": all_tables,
        "databases": databases
    })


@app.post("/product_tables")
def post_product_tables(request: Request,
                        table1_fullname: str = Form(...),
                        table2_fullname: str = Form(...),
                        destination_db_name: str = Form(...),
                        new_table_name: str = Form(...)):
    db1_name, table1_name = table1_fullname.split('.')
    db2_name, table2_name = table2_fullname.split('.')

    db1 = databases.get(db1_name)
    db2 = databases.get(db2_name)
    destination_db = databases.get(destination_db_name)
    if not db1 or not db2 or not destination_db:
        return templates.TemplateResponse("product_tables.html", {
            "request": request,
            "error": "One or more databases not found.",
            "tables": get_all_tables(),
            "databases": databases
        })
    table1 = db1.get_table(table1_name)
    table2 = db2.get_table(table2_name)
    if not table1 or not table2:
        return templates.TemplateResponse("product_tables.html", {
            "request": request,
            "error": "One or both tables not found.",
            "tables": get_all_tables(),
            "databases": databases
        })
    # Check if table with new_table_name already exists in destination database
    if new_table_name in destination_db.tables:
        return templates.TemplateResponse("product_tables.html", {
            "request": request,
            "error": f"Table '{new_table_name}' already exists in database '{destination_db_name}'.",
            "tables": get_all_tables(),
            "databases": databases
        })
    # Create new table name with database name prefix
    full_table_name = f"{destination_db_name}_{new_table_name}"
    new_table = table_product(table1, table2, full_table_name)
    destination_db.create_table(new_table)
    return RedirectResponse(f"/databases/{destination_db_name}", status_code=303)



@app.get("/databases/{db_name}/tables/{table_name}/edit_row/{row_index}")
def get_edit_row(request: Request, db_name: str, table_name: str, row_index: int):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("edit_row.html", {
            "request": request, "error": f"Database '{db_name}' not found."
        })
    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("edit_row.html", {
            "request": request,
            "error": f"Table '{table_name}' not found in database '{db_name}'.",
            "db_name": db_name
        })
    try:
        row = table.rows[row_index]
    except IndexError:
        return templates.TemplateResponse("edit_row.html", {
            "request": request, "error": "Row not found.", "table": table, "db_name": db_name
        })
    return templates.TemplateResponse("edit_row.html", {
        "request": request, "db_name": db_name, "table": table, "row": row, "row_index": row_index
    })


@app.post("/databases/{db_name}/tables/{table_name}/edit_row/{row_index}")
async def post_edit_row(request: Request, db_name: str, table_name: str, row_index: int):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("edit_row.html", {
            "request": request, "error": f"Database '{db_name}' not found."
        })
    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("edit_row.html", {
            "request": request,
            "error": f"Table '{table_name}' not found in database '{db_name}'.",
            "db_name": db_name
        })
    form_data = await request.form()
    parsed_data = {}
    errors = {}
    for attr in table.schema.attributes:
        value = form_data.get(attr.name)
        try:
            parsed_value = parse_data(value, attr.data_type)
            parsed_data[attr.name] = parsed_value
        except ValueError as e:
            errors[attr.name] = f"Invalid input for '{attr.name}': expected {attr.data_type}."

    if errors:
        row = table.rows[row_index] if row_index < len(table.rows) else None
        return templates.TemplateResponse("edit_row.html", {
            "request": request,
            "db_name": db_name,
            "table": table,
            "row": row,
            "row_index": row_index,
            "errors": errors,
            "form_data": form_data
        })

    updated_row = Row(parsed_data)
    table.update_row(row_index, updated_row)
    return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)


@app.get("/databases/{db_name}/delete_database")
def delete_database(request: Request, db_name: str):
    if db_name in databases:
        del databases[db_name]
    return RedirectResponse("/", status_code=303)


@app.get("/databases/{db_name}/edit_database")
def get_edit_database(request: Request, db_name: str):
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("error.html",
                                          {"request": request, "error": f"Database '{db_name}' not found."})
    return templates.TemplateResponse("edit_database.html", {"request": request, "db": db})


@app.post("/databases/{db_name}/edit_database")
def post_edit_database(request: Request, db_name: str, new_db_name: str = Form(...)):
    if new_db_name == db_name:
        return RedirectResponse(f"/databases/{db_name}", status_code=303)
    if new_db_name in databases:
        error = f"Database '{new_db_name}' already exists."
        db = databases.get(db_name)
        return templates.TemplateResponse("edit_database.html", {"request": request, "error": error, "db": db})
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("error.html",
                                          {"request": request, "error": f"Database '{db_name}' not found."})
    db.name = new_db_name
    databases[new_db_name] = db
    del databases[db_name]
    return RedirectResponse(f"/databases/{new_db_name}", status_code=303)


@app.get("/databases/{db_name}/tables/{table_name}/delete_row/{row_index}")
def delete_row(request: Request, db_name: str, table_name: str, row_index: int):
    db = databases.get(db_name)
    if not db:
        return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)
    table = db.get_table(table_name)
    if not table:
        return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)
    try:
        table.delete_row(row_index)
    except IndexError:
        pass  # Ignore if row doesn't exist
    return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)

def find_duplicates(rows):
    seen = set()
    duplicates = []

    for row in rows:
        if row in seen:
            duplicates.append(row)
        else:
            seen.add(row)

    return duplicates

@app.get("/databases/{db_name}/tables/{table_name}/delete_duplicate_rows")
def  delete_duplicate_rows(request: Request, db_name: str, table_name: str):
    db = databases.get(db_name)
    if not db:
        return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)
    table = db.get_table(table_name)
    if not table:
        return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)
    try:
        duplicates = find_duplicates(table.rows)
        for row in duplicates: 
            table.delete_row(row)

    except IndexError:
        pass  # Ignore if row doesn't exist
    return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)

@app.get("/databases/{db_name}/tables/{table_name}/import_excel")
def get_import_excel_form(request: Request, db_name: str, table_name: str):
    """
    Renders the import Excel form.
    """
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Database '{db_name}' not found."
        })
    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Table '{table_name}' not found in database '{db_name}'."
        })
    return templates.TemplateResponse("import_excel.html", {
        "request": request,
        "db_name": db_name,
        "table_name": table_name
    })


@app.post("/databases/{db_name}/tables/{table_name}/import_excel")
async def post_import_excel(request: Request, db_name: str, table_name: str, file: UploadFile = File(...)):
    """
    Handles the import of data from an Excel file into the specified table.
    """
    db = databases.get(db_name)
    if not db:
        return templates.TemplateResponse("import_excel.html", {
            "request": request,
            "error": f"Database '{db_name}' not found.",
            "db_name": db_name,
            "table_name": table_name
        })

    table = db.get_table(table_name)
    if not table:
        return templates.TemplateResponse("import_excel.html", {
            "request": request,
            "error": f"Table '{table_name}' not found in database '{db_name}'.",
            "db_name": db_name,
            "table_name": table_name
        })

    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        return templates.TemplateResponse("import_excel.html", {
            "request": request,
            "error": "Invalid file type. Only Excel files (.xlsx, .xls) are supported.",
            "db_name": db_name,
            "table_name": table_name
        })

    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        return templates.TemplateResponse("import_excel.html", {
            "request": request,
            "error": f"Error reading Excel file: {e}",
            "db_name": db_name,
            "table_name": table_name
        })

    # Validate columns
    expected_columns = [attr.name for attr in table.schema.attributes]
    excel_columns = list(df.columns)

    if excel_columns != expected_columns:
        error_msg = f"Excel columns do not match table schema.<br>Expected: {expected_columns}<br>Found: {excel_columns}"
        return templates.TemplateResponse("import_excel.html", {
            "request": request,
            "error": error_msg,
            "db_name": db_name,
            "table_name": table_name
        })

    # Insert rows
    inserted_rows = 0
    errors = []

    for index, row in df.iterrows():
        parsed_data = {}
        for attr in table.schema.attributes:
            value = row[attr.name]
            try:
                # Handle NaN as empty string
                if pd.isna(value):
                    value = ''
                else:
                    value = str(value)
                parsed_value = parse_data(value, attr.data_type)
                parsed_data[attr.name] = parsed_value
            except ValueError as ve:
                errors.append(f"Row {index + 1}: {ve}")
                break  # Skip to next row if there's an error
        else:
            # Only insert row if no errors
            new_row = Row(parsed_data)
            table.insert_row(new_row)
            inserted_rows += 1

    if errors:
        return templates.TemplateResponse("import_excel.html", {
            "request": request,
            "db_name": db_name,
            "table_name": table_name,
            "errors": errors,
            "inserted_rows": inserted_rows
        })

    return RedirectResponse(f"/databases/{db_name}/tables/{table_name}", status_code=303)