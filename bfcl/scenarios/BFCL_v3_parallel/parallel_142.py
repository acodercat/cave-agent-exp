from typing import List, Dict, Any, Union, Tuple, Set 
def update_user_info(user_id:int, update_info:Dict[str, str], database:str='CustomerInfo') -> str:
	"""
	update_user_info : Update user information in the database.    
	Parameters:
	user_id (int): The user ID of the customer.
	update_info (Dict[str, str]): The new information to update.
	database (str): The database where the user's information is stored.

	Required Parameter = [user_id,update_info,]

	"""
	return 'Success'

tools = [update_user_info]
