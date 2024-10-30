# main_gui.py

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from data_types import parse_data, SUPPORTED_DATA_TYPES
from database import Database
from table import Table
from schema import Schema
from attributes import Attribute
from row import Row
from operations import table_product

# Initialize databases dictionary
databases = {}  # Key: Database name, Value: Database instance

class DatabaseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SQL-like Database Application")

        self.create_main_menu()

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.show_databases()

    def create_main_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        database_menu = tk.Menu(menubar, tearoff=0)
        database_menu.add_command(label="Create Database", command=self.create_database)
        database_menu.add_command(label="Product of Tables", command=self.product_of_tables)
        menubar.add_cascade(label="Database", menu=database_menu)

    def clear_main_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def show_databases(self):
        self.clear_main_frame()
        ttk.Label(self.main_frame, text="Databases", font=("Helvetica", 16)).pack(pady=10)

        if databases:
            for db_name in databases:
                frame = ttk.Frame(self.main_frame)
                frame.pack(fill=tk.X, padx=20, pady=5)

                ttk.Label(frame, text=db_name, font=("Helvetica", 12)).pack(side=tk.LEFT)

                ttk.Button(frame, text="Open", command=lambda db_name=db_name: self.open_database(db_name)).pack(side=tk.LEFT, padx=5)
                ttk.Button(frame, text="Edit", command=lambda db_name=db_name: self.edit_database(db_name)).pack(side=tk.LEFT, padx=5)
                ttk.Button(frame, text="Delete", command=lambda db_name=db_name: self.delete_database(db_name)).pack(side=tk.LEFT, padx=5)
        else:
            ttk.Label(self.main_frame, text="No databases found.", font=("Helvetica", 12)).pack(pady=10)

    def create_database(self):
        db_name = simpledialog.askstring("Create Database", "Enter database name:")
        if db_name:
            if db_name in databases:
                messagebox.showerror("Error", f"Database '{db_name}' already exists.")
            else:
                databases[db_name] = Database(db_name)
                self.show_databases()

    def edit_database(self, db_name):
        new_db_name = simpledialog.askstring("Edit Database", "Enter new database name:", initialvalue=db_name)
        if new_db_name and new_db_name != db_name:
            if new_db_name in databases:
                messagebox.showerror("Error", f"Database '{new_db_name}' already exists.")
            else:
                db = databases[db_name]
                db.name = new_db_name
                databases[new_db_name] = db
                del databases[db_name]
                self.show_databases()

    def delete_database(self, db_name):
        if messagebox.askyesno("Delete Database", f"Are you sure you want to delete database '{db_name}'?"):
            del databases[db_name]
            self.show_databases()

    def open_database(self, db_name):
        db = databases[db_name]
        self.clear_main_frame()

        ttk.Label(self.main_frame, text=f"Database: {db.name}", font=("Helvetica", 16)).pack(pady=10)

        ttk.Button(self.main_frame, text="Create Table", command=lambda: self.create_table(db)).pack(pady=5)

        if db.tables:
            for table_name in db.tables:
                frame = ttk.Frame(self.main_frame)
                frame.pack(fill=tk.X, padx=20, pady=5)

                ttk.Label(frame, text=table_name, font=("Helvetica", 12)).pack(side=tk.LEFT)

                ttk.Button(frame, text="Open", command=lambda table_name=table_name: self.open_table(db, table_name)).pack(side=tk.LEFT, padx=5)
                ttk.Button(frame, text="Edit", command=lambda table_name=table_name: self.edit_table(db, table_name)).pack(side=tk.LEFT, padx=5)
                ttk.Button(frame, text="Delete", command=lambda table_name=table_name: self.delete_table(db, table_name)).pack(side=tk.LEFT, padx=5)
        else:
            ttk.Label(self.main_frame, text="No tables found.", font=("Helvetica", 12)).pack(pady=10)

        ttk.Button(self.main_frame, text="Back", command=self.show_databases).pack(pady=10)

    def create_table(self, db):
        table_name = simpledialog.askstring("Create Table", "Enter table name:")
        if not table_name:
            return

        if table_name in db.tables:
            messagebox.showerror("Error", f"Table '{table_name}' already exists in database '{db.name}'.")
            return

        attributes_str = simpledialog.askstring("Define Schema", "Enter attributes (name:type, separated by commas):")
        if not attributes_str:
            return

        attr_list = []
        try:
            for attr in attributes_str.split(','):
                name, data_type = attr.strip().split(':')
                data_type = data_type.strip()
                if data_type not in SUPPORTED_DATA_TYPES:
                    raise ValueError(f"Unsupported data type: {data_type}")
                attr_list.append(Attribute(name.strip(), data_type))
            schema = Schema(attr_list)
            table = Table(table_name, schema)
            db.create_table(table)
            self.open_database(db.name)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def edit_table(self, db, table_name):
        table = db.get_table(table_name)
        new_table_name = simpledialog.askstring("Edit Table", "Enter new table name:", initialvalue=table.name)
        if not new_table_name:
            return

        if new_table_name != table_name and new_table_name in db.tables:
            messagebox.showerror("Error", f"Table '{new_table_name}' already exists in database '{db.name}'.")
            return

        attributes_str = simpledialog.askstring("Edit Schema", "Enter new attributes (name:type, separated by commas):")
        if not attributes_str:
            return

        attr_list = []
        try:
            for attr in attributes_str.split(','):
                name, data_type = attr.strip().split(':')
                data_type = data_type.strip()
                if data_type not in SUPPORTED_DATA_TYPES:
                    raise ValueError(f"Unsupported data type: {data_type}")
                attr_list.append(Attribute(name.strip(), data_type))
            if table.rows:
                raise ValueError("Cannot modify schema of a table that contains data. Please delete all rows first.")
            schema = Schema(attr_list)
            table.schema = schema
            if new_table_name != table_name:
                del db.tables[table_name]
                table.name = new_table_name
                db.tables[new_table_name] = table
            self.open_database(db.name)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_table(self, db, table_name):
        if messagebox.askyesno("Delete Table", f"Are you sure you want to delete table '{table_name}'?"):
            del db.tables[table_name]
            self.open_database(db.name)

    def open_table(self, db, table_name):
        table = db.get_table(table_name)
        self.clear_main_frame()

        ttk.Label(self.main_frame, text=f"Table: {table.name}", font=("Helvetica", 16)).pack(pady=10)

        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=5)

        ttk.Button(button_frame, text="Insert Row", command=lambda: self.insert_row(db, table)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export to Excel", command=lambda: self.export_table_to_excel(db, table)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Back", command=lambda: self.open_database(db.name)).pack(side=tk.LEFT, padx=5)

        if table.rows:
            columns = [attr.name for attr in table.schema.attributes]
            tree = ttk.Treeview(self.main_frame, columns=columns, show='headings')
            for col in columns:
                tree.heading(col, text=col)

            for idx, row in enumerate(table.rows):
                values = [row.data.get(attr.name, '') for attr in table.schema.attributes]
                tree.insert('', tk.END, iid=idx, values=values)

            tree.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

            # Add right-click menu
            tree.bind("<Button-3>", lambda event: self.show_row_menu(event, db, table, tree))
        else:
            ttk.Label(self.main_frame, text="No rows in this table.", font=("Helvetica", 12)).pack(pady=10)

    def show_row_menu(self, event, db, table, tree):
        selected_item = tree.identify_row(event.y)
        if selected_item:
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Edit", command=lambda: self.edit_row(db, table, int(selected_item)))
            menu.add_command(label="Delete", command=lambda: self.delete_row(db, table, int(selected_item)))
            menu.post(event.x_root, event.y_root)

    def insert_row(self, db, table):
        row_data = {}
        for attr in table.schema.attributes:
            value = simpledialog.askstring("Insert Row", f"Enter value for {attr.name} ({attr.data_type}):")
            if value is None:
                return
            try:
                parsed_value = parse_data(value, attr.data_type)
                row_data[attr.name] = parsed_value
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
        row = Row(row_data)
        table.insert_row(row)
        self.open_table(db, table.name)

    def edit_row(self, db, table, row_index):
        row = table.rows[row_index]
        row_data = row.data.copy()
        for attr in table.schema.attributes:
            value = simpledialog.askstring("Edit Row", f"Enter new value for {attr.name} ({attr.data_type}):", initialvalue=str(row_data.get(attr.name, '')))
            if value is None:
                return
            try:
                parsed_value = parse_data(value, attr.data_type)
                row_data[attr.name] = parsed_value
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
        updated_row = Row(row_data)
        table.update_row(row_index, updated_row)
        self.open_table(db, table.name)

    def delete_row(self, db, table, row_index):
        if messagebox.askyesno("Delete Row", "Are you sure you want to delete this row?"):
            table.delete_row(row_index)
            self.open_table(db, table.name)

    def export_table_to_excel(self, db, table):
        import pandas as pd
        import os
        from tkinter.filedialog import asksaveasfilename

        # Convert table data to DataFrame
        data = [row.data for row in table.rows]
        df = pd.DataFrame(data)

        # Prompt user for save location
        file_path = asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if file_path:
            try:
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Success", f"Table exported to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export table: {e}")
    def product_of_tables(self):
        if not databases:
            messagebox.showerror("Error", "No databases available.")
            return

        all_tables = []
        for db_name, db in databases.items():
            for table_name in db.tables.keys():
                all_tables.append(f"{db_name}.{table_name}")

        if len(all_tables) < 2:
            messagebox.showerror("Error", "At least two tables are required to perform a product.")
            return

        table1_fullname = simpledialog.askstring("Product of Tables", f"Enter first table (e.g., {all_tables[0]}):")
        if table1_fullname not in all_tables:
            messagebox.showerror("Error", "First table not found.")
            return

        table2_fullname = simpledialog.askstring("Product of Tables", f"Enter second table (e.g., {all_tables[1]}):")
        if table2_fullname not in all_tables:
            messagebox.showerror("Error", "Second table not found.")
            return

        destination_db_name = simpledialog.askstring("Product of Tables", "Enter destination database name:")
        if destination_db_name not in databases:
            messagebox.showerror("Error", f"Database '{destination_db_name}' not found.")
            return

        new_table_name = simpledialog.askstring("Product of Tables", "Enter new table name:")
        if not new_table_name:
            return

        destination_db = databases[destination_db_name]
        if new_table_name in destination_db.tables:
            messagebox.showerror("Error", f"Table '{new_table_name}' already exists in database '{destination_db_name}'.")
            return

        db1_name, table1_name = table1_fullname.split('.')
        db2_name, table2_name = table2_fullname.split('.')

        db1 = databases.get(db1_name)
        db2 = databases.get(db2_name)
        table1 = db1.get_table(table1_name)
        table2 = db2.get_table(table2_name)

        full_table_name = f"{destination_db_name}_{new_table_name}"
        try:
            new_table = table_product(table1, table2, full_table_name)
            destination_db.create_table(new_table)
            messagebox.showinfo("Success", f"Product table '{new_table_name}' created in database '{destination_db_name}'.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = DatabaseApp(root)
    root.mainloop()
