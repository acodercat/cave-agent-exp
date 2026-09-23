from typing import List, Dict, Any, Union, Tuple, Set 
def latest_exchange_rate(source_currency:str, target_currency:str, amount:float=None) -> str:
	"""
	latest_exchange_rate : Retrieve the latest exchange rate between two specified currencies.    
	Parameters:
	source_currency (str): The currency you are converting from.
	target_currency (str): The currency you are converting to.
	amount (float): The amount to be converted. If omitted, default to exchange rate of 1 unit source currency

	Required Parameter = [source_currency,target_currency,]

	"""
	return 'Success'

tools = [latest_exchange_rate]
