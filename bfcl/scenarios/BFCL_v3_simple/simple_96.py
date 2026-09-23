from typing import List, Dict, Any, Union, Tuple, Set 
def database_query(table:str, conditions:List[Dict[str, str]]) -> str:
	"""
	database_query : Query the database based on certain conditions.    
	Parameters:
	table (str): Name of the table to query.
	conditions (List[Dict[str, str]]): Conditions for the query.

	Required Parameter = [table,conditions,]

	"""
	return 'Success'

tools = [database_query]
