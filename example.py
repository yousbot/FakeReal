from fakereal import fakereal

# Initialize FakeReal with a connection string
connection_string = 'mysql://root:@localhost:3306/OnlineStore'
fk = fakereal(connection_string)

# Seed 'all' tables with 100 rows each, in batches of 10
fk.seed('all', rows=100, batch_size=10)

# Run test queries and print the result
result = fk.test_queries(return_bool=True, silent=False)
print(result)