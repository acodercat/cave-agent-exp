from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_final_temperature(mass1:int, temperature1:int, mass2:int, temperature2:int, specific_heat_capacity:float=None) -> str:
	"""
	calculate_final_temperature : Calculates the final equilibrium temperature after mixing two bodies with different masses and temperatures    
	Parameters:
	mass1 (int): The mass of the first body (kg).
	temperature1 (int): The initial temperature of the first body (Celsius).
	mass2 (int): The mass of the second body (kg).
	temperature2 (int): The initial temperature of the second body (Celsius).
	specific_heat_capacity (float): The specific heat capacity of the bodies in kJ/kg/K. If not provided, will default to that of water at room temperature, which is 4.2 kJ/kg/K.

	Required Parameter = [mass1,temperature1,mass2,temperature2,]

	"""
	return 'Success'

tools = [calculate_final_temperature]
