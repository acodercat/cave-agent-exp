from typing import List, Dict, Any, Union, Tuple, Set 
def get_exchange_rate_with_fee(base_currency:str, target_currency:str, fee:float) -> str:
	"""
	get_exchange_rate_with_fee : Retrieve the exchange rate between two currencies including transaction fee.    
	Parameters:
	base_currency (str): The base currency.
	target_currency (str): The target currency.
	fee (float): The transaction fee in percentage. Default is 0%.

	Required Parameter = [base_currency,target_currency,fee,]

	"""
	return 'Success'

tools = [get_exchange_rate_with_fee]
