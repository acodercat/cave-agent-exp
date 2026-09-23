from typing import List, Dict, Any, Union, Tuple, Set 
def database_modify_columns(db_name:str, table:str, operation:str, columns:List[str]) -> str:
	"""
	database_modify_columns : This function allows deletion or addition of columns in a database    
	Parameters:
	db_name (str): The name of the database to modify.
	table (str): The name of the table to modify.
	operation (str): The operation to carry out on the table. Can be 'delete' or 'add'.
	columns (List[str]): List of the columns to add or delete from the table.

	Required Parameter = [db_name,table,operation,columns,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def database_create_backup(db_name:str, backup_location:str, timestamp:bool='False') -> str:
	"""
	database_create_backup : This function creates a backup of the database before modification    
	Parameters:
	db_name (str): The name of the database to create a backup of.
	backup_location (str): The file path where the backup should be stored.
	timestamp (bool): Option to append a timestamp to the backup file name.

	Required Parameter = [db_name,backup_location,]

	"""
	return 'Success'

tools = [database_modify_columns, database_create_backup]
