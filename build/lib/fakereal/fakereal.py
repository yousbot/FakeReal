from peewee import MySQLDatabase, PostgresqlDatabase, SqliteDatabase
from urllib.parse import urlparse, parse_qs
import random, json
from faker import Faker
import re
import logging
import argparse

class fakereal:
    def __init__(self, connection_string):
        try:
            parsed_url = urlparse(connection_string)
            protocol = parsed_url.scheme
            username = parsed_url.username
            password = parsed_url.password
            host = parsed_url.hostname
            port = parsed_url.port
            database = parsed_url.path.lstrip('/')
            params = parse_qs(parsed_url.query)
            sslcert = params.get('sslcert', [None])[0]
            
            self.fake = Faker()
            
        except Exception as e:
            print(f"Error parsing connection string: {e}")
            return

        if protocol == 'mysql':
            self.db = MySQLDatabase(
                database,
                host=host,
                port=port,
                user=username,
                password=password,
                ssl_ca=sslcert
            )
        elif protocol == 'postgresql' or protocol == 'postgres':
            self.db = PostgresqlDatabase(
                database,
                host=host,
                port=port,
                user=username,
                password=password,
                ssl_ca=sslcert
            )
        elif protocol == 'sqlite':
            self.db = SqliteDatabase(database)
        else:
            print(f"Unsupported database type: {protocol}")
            return

    def generate_random_data(self, field_name, sql_type):
        lowercase_field_name = field_name.lower()

        # Retrieve a list of all available attributes from the Faker library
        available_attributes = dir(self.fake)

        best_match_provider = None
        best_match_length = 0

        for attr in available_attributes:
            lowercase_attr = attr.lower()
            if lowercase_attr in lowercase_field_name:
                # Update best match if current attribute is a better match
                if len(lowercase_attr) > best_match_length:
                    best_match_provider = attr
                    best_match_length = len(lowercase_attr)

        if best_match_provider:
            # Use the best match data provider to generate data
            data_generator = getattr(self.fake, best_match_provider)
            return data_generator()

        # Fallback logic based on data type
        type_map = {
            'int': self.fake.random_int,
            'decimal': self.fake.pyfloat,
            'char': self.fake.word,
            'date': self.fake.date_this_decade,
            'datetime': self.fake.date_time_this_decade,
            'bit': lambda: random.choice([0, 1]),
            'json': lambda: json.dumps({"key": "value"})
        }
        data_generator = type_map.get(sql_type.lower(), self.fake.word)
        return data_generator()
        
        
    def get_foreign_keys(self, table):
        cursor = self.db.execute_sql(f"SHOW CREATE TABLE {table};")
        create_table_script = cursor.fetchone()[1]
        foreign_keys = re.findall(r"FOREIGN KEY \(`(.*?)`\) REFERENCES `(.*?)` \(`(.*?)`\)", create_table_script)
        return {key: {"referenced_table": referenced_table, "referenced_field": referenced_field} for key, referenced_table, referenced_field in foreign_keys}

    def get_primary_keys(self, table):
        cursor = self.db.execute_sql(f"SHOW KEYS FROM {table} WHERE Key_name = 'PRIMARY';")
        primary_keys = [row[4] for row in cursor.fetchall()]  # Column name is at index 4
        return primary_keys if primary_keys else None
        
    def sort_tables_by_dependencies(self, tables, all_foreign_keys):
        def sort_key(table):
            foreign_keys = all_foreign_keys.get(table, {})
            dependencies = {key: val['referenced_table'] for key, val in foreign_keys.items()}
            return len(set(dependencies.values()) & set(tables))
        return sorted(tables, key=sort_key)

    def determine_table_order(self, tables, all_foreign_keys):
        # Create a graph to represent foreign key dependencies
        graph = {}
        for table in tables:
            foreign_keys = all_foreign_keys.get(table, {})
            referenced_tables = {value['referenced_table'] for value in foreign_keys.values()}
            graph[table] = referenced_tables

        # Perform topological sort to determine the order in which tables should be seeded
        visited = set()
        stack = []

        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for neighbor in graph.get(node, set()):
                visit(neighbor)
            stack.append(node)

        for table in tables:
            visit(table)

        print(f"Final table order: {list(stack)}")  # Output the final table order
        return stack


    def seed(self, tables='all', rows=100, batch_size=10):
        self.db.connect()

        if tables == 'all':
            tables = self.db.get_tables()

        all_foreign_keys = {table: self.get_foreign_keys(table) for table in tables}
        primary_keys = {table: self.get_primary_keys(table) for table in tables}  # Use the new get_primary_keys method

        # Determine the order in which to seed tables
        ordered_tables = self.determine_table_order(tables, all_foreign_keys)

        generated_ids = {}  # Dictionary to store generated primary keys

        for table in ordered_tables:
            print(f"Seeding table: {table} with {rows} rows")

            primary_keys_for_table = primary_keys.get(table)
            if primary_keys_for_table is not None:
                generated_ids[table] = []

            cursor = self.db.execute_sql(f"DESCRIBE {table};")
            fields = [(row[0], row[1]) for row in cursor.fetchall()]

            batch = []
            for i in range(rows):
                data = {}
                for field_name, field_type in fields:
                    if field_name in all_foreign_keys.get(table, {}):
                        fk_table = all_foreign_keys[table][field_name]['referenced_table']
                        fk_value = random.choice(generated_ids.get(fk_table, []))
                        data[field_name] = fk_value
                    else:
                        # Generate random data
                        data[field_name] = self.generate_random_data(field_name, field_type)

                batch.append(data)

                if len(batch) >= batch_size:
                    inserted_ids = self.execute_bulk_insert(table, data.keys(), batch, primary_keys_for_table)
                    generated_ids[table].extend(inserted_ids)
                    batch = []

            if batch:
                inserted_ids = self.execute_bulk_insert(table, data.keys(), batch, primary_keys_for_table)
                generated_ids[table].extend(inserted_ids)

        self.db.close()


    def execute_bulk_insert(self, table, keys, batch, primary_keys=None):
        keys_str = ', '.join(keys)
        values_str = ', '.join(['%s'] * len(keys))
        sql = f"INSERT INTO {table} ({keys_str}) VALUES ({values_str});"
        inserted_ids = []
        for data in batch:
            try:
                flat_values = list(data.values())
                cursor = self.db.execute_sql(sql, flat_values)
                if primary_keys:
                    if len(primary_keys) == 1:
                        inserted_ids.append(cursor.lastrowid)
                    else:
                        inserted_ids.append(tuple(data[k] for k in primary_keys))
            except Exception as e:
                print(f"Error while inserting into {table}: {e}")
        return inserted_ids

    def wipe_test_data(self):
        self.db.connect()
        try:
            self.db.execute_sql("SET foreign_key_checks = 0;")
            all_tables = self.db.get_tables()
            
            for table in all_tables:
                print(f"Wiping data from table: {table}")
                self.db.execute_sql(f"DELETE FROM {table};")
        finally:
            self.db.execute_sql("SET foreign_key_checks = 1;")
        self.db.close()
        
    def generate_level_1_queries(self, table):
        return [
            {"description": f"Count records in {table}", "sql": f"SELECT COUNT(*) FROM {table};"},
            {"description": f"Select all from {table}", "sql": f"SELECT * FROM {table} LIMIT 5;"},
        ]

    def generate_level_2_queries(self, table, primary_keys):
        if len(primary_keys) == 1:
            primary_key = primary_keys[0]
            return [
                {"description": f"Inner Join {table} with itself using {primary_key}", "sql": f"SELECT A.* FROM {table} A INNER JOIN {table} B ON A.{primary_key} = B.{primary_key} LIMIT 5;"},
                {"description": f"Left Join {table} with itself using {primary_key}", "sql": f"SELECT A.* FROM {table} A LEFT JOIN {table} B ON A.{primary_key} = B.{primary_key} LIMIT 5;"},
            ]
        else:
            join_condition = " AND ".join([f"A.{k} = B.{k}" for k in primary_keys])
            return [
                {"description": f"Inner Join {table} with itself using composite keys", "sql": f"SELECT A.* FROM {table} A INNER JOIN {table} B ON {join_condition} LIMIT 5;"},
                {"description": f"Left Join {table} with itself using composite keys", "sql": f"SELECT A.* FROM {table} A LEFT JOIN {table} B ON {join_condition} LIMIT 5;"},
            ]

    def generate_level_3_queries(self, table):
        queries = []
        cursor = self.db.execute_sql(f"DESCRIBE {table};")
        numeric_columns = [row[0] for row in cursor.fetchall() if 'int' in row[1] or 'float' in row[1] or 'double' in row[1]]

        for numeric_column in numeric_columns:
            queries.append({"description": f"Average of {numeric_column} in {table}", "sql": f"SELECT AVG({numeric_column}) FROM {table};"})
            queries.append({"description": f"Sum of {numeric_column} in {table}", "sql": f"SELECT SUM({numeric_column}) FROM {table};"})

        return queries

    def test_queries(self, return_bool=False, silent=False):
        self.db.connect()

        # Initialize logging
        logging.basicConfig(filename='./seedpy.log', level=logging.INFO)

        all_tables = self.db.get_tables()
        all_passed = True  # To keep track of query success

        queries = []

        for table in all_tables:
            # Fetch the primary key for the table
            cursor = self.db.execute_sql(f"SHOW KEYS FROM {table} WHERE Key_name = 'PRIMARY'")
            primary_key_row = cursor.fetchone()
            primary_key = primary_key_row[4] if primary_key_row else 'id'

            # Generate queries of different levels
            queries.extend(self.generate_level_1_queries(table))
            queries.extend(self.generate_level_2_queries(table, primary_key))
            queries.extend(self.generate_level_3_queries(table))

        # Clear the log file
        open('./seedpy.log', 'w').close()

        # Execute queries to test the database
        for i, query in enumerate(queries):
            try:
                logging.info(f"Executing Query {i+1}: {query['description']}")
                logging.info(f"SQL: {query['sql']}")
                cursor = self.db.execute_sql(query['sql'])
                results = cursor.fetchall()
                logging.info("Results:")
                for row in results:
                    logging.info(row)
                if not silent:
                    print(f"[ Query {i+1} ] {query['description']} ...... [ succeeded ]")
            except Exception as e:
                all_passed = False
                logging.error(f"Error executing Query {i+1}: {e}")
                logging.error(f"Failed SQL: {query['sql']}")
                if not silent:
                    print(f"[ Query {i+1} ] {query['description']} ...... [ failed ]")

        self.db.close()

        if not silent:
            if all_passed:
                print("All queries succeeded.")
            else:
                print("Some queries failed. Check the log for details.")

        if return_bool:
            return all_passed


def main():
    parser = argparse.ArgumentParser(description="SeedPy: A Python library for populating databases with random test data.")
    parser.add_argument("connection_string", help="The connection string for the database.")
    parser.add_argument("--tables", nargs='+', default='all', help="List of tables to populate. Default is all tables.")
    parser.add_argument("--rows", type=int, default=100, help="Number of rows to insert in each table. Default is 100.")
    parser.add_argument("--batch_size", type=int, default=10, help="Batch size for bulk insert. Default is 10.")
    parser.add_argument("--test", action='store_true', help="Run tests on the populated database.")
    parser.add_argument("--silent", action='store_true', help="Run the program in silent mode.")
    
    args = parser.parse_args()
    
    seedpy = SeedPy(args.connection_string)
    
    if args.tables == 'all':
        args.tables = seedpy.db.get_tables()
        
    seedpy.seed(args.tables, rows=args.rows, batch_size=args.batch_size)
    
    if args.test:
        seedpy.test_queries(return_bool=True, silent=args.silent)

if __name__ == "__main__":
    main()