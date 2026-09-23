from typing import List, Dict, Any, Union, Tuple, Set 
def temperature_converter_convert(temperature:float, from_unit:str, to_unit:str, round_to:int=None) -> str:
	"""
	temperature_converter_convert : Convert a temperature from one unit to another.    
	Parameters:
	temperature (float): The temperature to convert.
	from_unit (str): The unit to convert from.
	to_unit (str): The unit to convert to.
	round_to (int): The number of decimal places to round the result to. Defaults to 2.

	Required Parameter = [temperature,from_unit,to_unit,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def energy_calculator_calculate(substance:str, mass:float, initial_temperature:float, final_temperature:float, unit:str=None) -> str:
	"""
	energy_calculator_calculate : Calculate the energy needed to heat a substance from an initial to a final temperature.    
	Parameters:
	substance (str): The substance to be heated.
	mass (float): The mass of the substance in grams.
	initial_temperature (float): The initial temperature of the substance in degrees Celsius.
	final_temperature (float): The final temperature of the substance in degrees Celsius.
	unit (str): The unit to report the energy in. Options are 'joules' and 'calories'. Defaults to 'joules'.

	Required Parameter = [substance,mass,initial_temperature,final_temperature,]

	"""
	return 'Success'

tools = [temperature_converter_convert, energy_calculator_calculate]
