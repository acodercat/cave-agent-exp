from typing import List, Dict, Any, Union, Tuple, Set 
def db_fetch_records(database_name:str, table_name:str, conditions:Dict[str, str], fetch_limit:int=None) -> str:
	"""
	db_fetch_records : Fetch records from a specified database table based on certain conditions.    
	Parameters:
	database_name (str): The name of the database.
	table_name (str): The name of the table from which records need to be fetched.
	conditions (Dict[str, str]): The conditions based on which records are to be fetched.
	fetch_limit (int): Limits the number of records to be fetched. Default is 0, which means no limit.

	Required Parameter = [database_name,table_name,conditions,]

	"""
	return 'Success'

tools = [db_fetch_records]
