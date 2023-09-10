from fakereal import FakeReal

# Initialize FakeReal with a connection string
connection_string = 'mysql://root:@localhost:3306/OnlineStore'
FakeReal = FakeReal(connection_string)

# Seed 'all' tables with 100 rows each, in batches of 10
FakeReal.seed('all', rows=100, batch_size=10)

# Run test queries and print the result
result = FakeReal.test_queries(return_bool=True, silent=False)
print(result)