# SeedPy

## Overview

SeedPy is a Python library designed to populate MySQL, PostgreSQL, and SQLite databases with random test data. 
With SeedPy, you can easily generate and insert fake but realistic data into your databases, either for testing or for other purposes. 
It's built on top of the Faker library for generating the data and uses Peewee for database connectivity.

## Features

- **Multiple Database Support**: SeedPy supports MySQL, PostgreSQL, and SQLite databases.
- **Intuitive API**: SeedPy provides an easy-to-use API for seeding databases and running test queries.
- **Customizable Data Generation**: Auto-generates realistic data based on your database schema, semantics of fields, and relationship between the tables.
- **Wipe Test Data**: Provides the ability to wipe test data from databases.

## Installation

You can install SeedPy via pip:

```bash
pip install seedpy
```

## Quick Start
### Pre-requisites
Before diving into SeedPy, create a sample database named OnlineStore:

```bash
mysql -u root -p < onlineStoreDB.sql
```

### Seed Your Database
Here's a Python script to quickly get you started with SeedPy:

```python
from seedpy import SeedPy

# Initialize SeedPy with a connection string
connection_string = 'mysql://root:@localhost:3306/OnlineStore'
seedpy = SeedPy(connection_string)

# Seed 'all' tables with 100 rows each, in batches of 10
seedpy.seed('all', rows=100, batch_size=10)

# Run test queries and print the result
result = seedpy.test_queries(return_bool=True, silent=False)
print(result)
```

## Contributing
Contributions are welcome! 

## License
This project is open source.

