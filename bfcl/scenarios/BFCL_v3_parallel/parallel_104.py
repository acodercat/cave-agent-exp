from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_entropy_change(initial_temp:int, final_temp:int, heat_capacity:float, isothermal:bool=None) -> str:
	"""
	calculate_entropy_change : Calculate the entropy change for an isothermal and reversible process.    
	Parameters:
	initial_temp (int): The initial temperature in Kelvin.
	final_temp (int): The final temperature in Kelvin.
	heat_capacity (float): The heat capacity in J/K.
	isothermal (bool): Whether the process is isothermal. Default is True.

	Required Parameter = [initial_temp,final_temp,heat_capacity,]

	"""
	return 'Success'

tools = [calculate_entropy_change]
