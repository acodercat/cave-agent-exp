from typing import List, Dict, Any, Union, Tuple, Set 
def unit_conversion(value:float, from_unit:str, to_unit:str) -> str:
	"""
	unit_conversion : Convert a value from one unit to another.    
	Parameters:
	value (float): The value to be converted.
	from_unit (str): The unit to convert from.
	to_unit (str): The unit to convert to.

	Required Parameter = [value,from_unit,to_unit,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def currency_conversion(amount:int, from_currency:str, to_currency:str) -> str:
	"""
	currency_conversion : Convert a value from one currency to another.    
	Parameters:
	amount (int): The amount to be converted.
	from_currency (str): The currency to convert from.
	to_currency (str): The currency to convert to.

	Required Parameter = [amount,from_currency,to_currency,]

	"""
	return 'Success'

tools = [unit_conversion, currency_conversion]
