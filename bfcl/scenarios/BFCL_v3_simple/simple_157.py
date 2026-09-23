from typing import List, Dict, Any, Union, Tuple, Set 
def criminal_history_check_felonies(full_name:str, birth_date:str, state:str=None) -> str:
	"""
	criminal_history_check_felonies : This function checks if an individual has any prior felony convictions based on their full name and birth date.    
	Parameters:
	full_name (str): The full name of the individual.
	birth_date (str): The birth date of the individual. Must be in MM-DD-YYYY format.
	state (str): The state to search the criminal record in. Default to 'None', which the function will search across all states.

	Required Parameter = [full_name,birth_date,]

	"""
	return 'Success'

tools = [criminal_history_check_felonies]
