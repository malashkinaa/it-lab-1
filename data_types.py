# data_types.py
import datetime
import os

SUPPORTED_DATA_TYPES = {'int','str','integer', 'real', 'char', 'string', 'date', 'int_interval', 'file'}

# data_types.py


def parse_data(value, data_type):
    if value is None or value == '':
        raise ValueError(f"Value cannot be empty. Expected {data_type}.")
    try:
        if data_type == 'integer' or data_type == 'int':
            return int(value)
        elif data_type == 'real':
            return float(value)
        elif data_type == 'char':
            if len(value) == 1:
                return value
            else:
                raise ValueError("Char must be a single character.")
        elif data_type == 'string' or data_type == 'str':
            return str(value)
        elif data_type == 'file':
            return str(value)
        elif data_type == 'date':
            if isinstance(value, datetime.date):
                return value
            elif isinstance(value, str):
                try:
                    return datetime.datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError as e:
                    raise ValueError(f"Invalid date format: {value}. Expected 'YYYY-MM-DD'.") from e
            else:
                raise TypeError(f"Expected str or datetime.date for data_type 'date', got {type(value).__name__}")
        elif data_type == 'int_interval':
            if isinstance(value, tuple):
                if len(value) != 2:
                    raise ValueError("Int interval tuple must have exactly two elements.")
                start_int, end_int = value
                if not isinstance(start_int, int) or not isinstance(end_int, int):
                    raise TypeError("Both elements of the tuple must be int.")
                return f"{start_int} to {end_int}"

            elif isinstance(value, str):
                ints = value.split(' to ')
                if len(ints) != 2:
                    raise ValueError("Int interval must be in int to int format.")
                try:
                    start_int = ints[0]
                    end_int = ints[1]
                except ValueError as e:
                    raise ValueError("Invalid int format. Use int digits.") from e
                return f"{start_int} to {end_int}"
            else:
                raise TypeError("Value must be either a tuple of two ints or a string in 'int to int' format.")
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    except ValueError as e:
        raise ValueError(f"Error parsing value '{value}' as {data_type}: {e}")
    finally:
        pass
    
# def parse_text_file(file_path):
#     if not os.path.isfile(file_path):
#         raise ValueError(f"File does not exist: {file_path}.")
#     with open(file_path, 'r', encoding='utf-8') as file:
#         return file.read()

def validate_data(value, data_type):
    try:
        parse_data(value, data_type)
        return True
    except ValueError:
        return False