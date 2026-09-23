from typing import List, Dict, Any, Union, Tuple, Set 
def math_power(base:float, exponent:float, mod:int=None) -> str:
	"""
	math_power : Calculate the power of one number raised to another.    
	Parameters:
	base (float): The base number.
	exponent (float): The exponent.
	mod (int): The modulus. Default is None. Calculates pow(base, exponent) % mod when provided.

	Required Parameter = [base,exponent,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def probabilities_calculate_single(total_outcomes:int, event_outcomes:int, round:int=None) -> str:
	"""
	probabilities_calculate_single : Calculate the probability of an event.    
	Parameters:
	total_outcomes (int): The total number of outcomes.
	event_outcomes (int): The number of outcomes where the event occurs.
	round (int): Round the answer to a specified number of decimal places. Defaults to 2.

	Required Parameter = [total_outcomes,event_outcomes,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def fetch_DNA_sequence(DNA_id:str, format:str=None, upstream:int=None) -> str:
	"""
	fetch_DNA_sequence : Retrieve the sequence of a DNA molecule with the given id from a public database.    
	Parameters:
	DNA_id (str): Unique ID of the DNA molecule in the database.
	format (str): Optional parameter to get sequence in specific format (default to 'fasta').
	upstream (int): Optional parameter to include certain number of base pairs upstream the DNA sequence (default to 0).

	Required Parameter = [DNA_id,]

	"""
	return 'Success'

tools = [math_power, probabilities_calculate_single, fetch_DNA_sequence]
