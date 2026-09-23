from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_electric_field(charge:int, distance:int, permitivity:int=None) -> str:
	"""
	calculate_electric_field : Calculate the electric field produced by a charge at a certain distance.    
	Parameters:
	charge (int): Charge in coulombs producing the electric field.
	distance (int): Distance from the charge in meters where the field is being measured.
	permitivity (int): Permitivity of the space where field is being calculated, default is for vacuum.

	Required Parameter = [charge,distance,]

	"""
	return 'Success'

tools = [calculate_electric_field]
