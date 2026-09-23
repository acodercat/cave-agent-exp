from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_weight_in_space(weight_earth_kg:float, planet:str) -> str:
	"""
	calculate_weight_in_space : Calculate your weight on different planets given your weight on earth    
	Parameters:
	weight_earth_kg (float): Your weight on Earth in Kilograms.
	planet (str): The planet you want to know your weight on.

	Required Parameter = [weight_earth_kg,planet,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def currency_conversion(amount:float, from_currency:str, to_currency:str) -> str:
	"""
	currency_conversion : Convert a value from one currency to another.    
	Parameters:
	amount (float): The amount to be converted.
	from_currency (str): The currency to convert from.
	to_currency (str): The currency to convert to.

	Required Parameter = [amount,from_currency,to_currency,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def unit_conversion_convert(value:float, from_unit:str, to_unit:str) -> str:
	"""
	unit_conversion_convert : Convert a value from one unit to another.    
	Parameters:
	value (float): The value to be converted.
	from_unit (str): The unit to convert from.
	to_unit (str): The unit to convert to.

	Required Parameter = [value,from_unit,to_unit,]

	"""
	return 'Success'

tools = [calculate_weight_in_space, currency_conversion, unit_conversion_convert]
