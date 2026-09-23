from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_final_temperature(quantity1:float, temperature1:float, quantity2:float, temperature2:float) -> str:
	"""
	calculate_final_temperature : Calculate the final temperature when different quantities of the same gas at different temperatures are mixed.    
	Parameters:
	quantity1 (float): The quantity of the first sample of gas.
	temperature1 (float): The temperature of the first sample of gas.
	quantity2 (float): The quantity of the second sample of gas.
	temperature2 (float): The temperature of the second sample of gas.

	Required Parameter = [quantity1,temperature1,quantity2,temperature2,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_mass(quantity:float, molar_mass:float) -> str:
	"""
	calculate_mass : Calculate the mass of a gas given its quantity and molar mass.    
	Parameters:
	quantity (float): The quantity of the gas.
	molar_mass (float): The molar mass of the gas.

	Required Parameter = [quantity,molar_mass,]

	"""
	return 'Success'

tools = [calculate_final_temperature, calculate_mass]
