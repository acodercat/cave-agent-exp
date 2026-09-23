from typing import List, Dict, Any, Union, Tuple, Set 
def cell_biology_function_lookup(molecule:str, organelle:str, specific_function:bool) -> str:
	"""
	cell_biology_function_lookup : Look up the function of a given molecule in a specified organelle.    
	Parameters:
	molecule (str): The molecule of interest.
	organelle (str): The organelle of interest.
	specific_function (bool): If set to true, a specific function of the molecule within the organelle will be provided, if such information exists.

	Required Parameter = [molecule,organelle,specific_function,]

	"""
	return 'Success'

tools = [cell_biology_function_lookup]
