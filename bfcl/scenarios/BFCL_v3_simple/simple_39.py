from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_electric_field(charge:int, distance:int, permitivity:float=None) -> str:
	"""
	calculate_electric_field : Calculate the electric field produced by a charge at a certain distance.    
	Parameters:
	charge (int): Charge in coulombs producing the electric field.
	distance (int): Distance from the charge in meters where the field is being measured.
	permitivity (float): Permitivity of the space where field is being calculated, default is 8.854e-12.

	Required Parameter = [charge,distance,]

	"""
	return 'Success'

tools = [calculate_electric_field]
