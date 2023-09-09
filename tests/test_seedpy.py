
from seedpy.seedpy import SeedPy

connection_string = 'mysql://root:@localhost:3306/OnlineStore'
seedpy = SeedPy(connection_string)
seedpy.wipe_test_data()
seedpy.seed('all', rows=100, batch_size=10)
result = seedpy.test_queries(return_bool=True, silent=False)
print(result)