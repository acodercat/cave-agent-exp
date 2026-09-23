from typing import List, Dict, Any, Union, Tuple, Set 
def currency_conversion_convert(from_currency:str, to_currency:str, amount:float) -> str:
	"""
	currency_conversion_convert : Converts a specified amount of money from one currency to another at the latest rate.    
	Parameters:
	from_currency (str): The currency that you want to convert from.
	to_currency (str): The currency that you want to convert to.
	amount (float): The amount of money that you want to convert.

	Required Parameter = [from_currency,to_currency,amount,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def currency_conversion_get_latest_rate(from_currency:str, to_currency:str) -> str:
	"""
	currency_conversion_get_latest_rate : Get the latest currency conversion rate from one currency to another.    
	Parameters:
	from_currency (str): The currency that you want to convert from.
	to_currency (str): The currency that you want to convert to.

	Required Parameter = [from_currency,to_currency,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def currency_conversion_get_rate(from_currency:str, to_currency:str, date:str='today') -> str:
	"""
	currency_conversion_get_rate : Get the currency conversion rate from one currency to another at a specified date.    
	Parameters:
	from_currency (str): The currency that you want to convert from.
	to_currency (str): The currency that you want to convert to.
	date (str): The date at which the conversion rate applies. Default is the current date.

	Required Parameter = [from_currency,to_currency,]

	"""
	return 'Success'

tools = [currency_conversion_convert, currency_conversion_get_latest_rate, currency_conversion_get_rate]
