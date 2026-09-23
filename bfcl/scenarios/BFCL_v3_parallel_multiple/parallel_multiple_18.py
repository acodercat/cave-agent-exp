from typing import List, Dict, Any, Union, Tuple, Set 
def banking_service(account_id:str, amount:float) -> str:
	"""
	banking_service : Make a deposit to a given bank account    
	Parameters:
	account_id (str): Target account to make deposit to.
	amount (float): Amount to deposit.

	Required Parameter = [account_id,amount,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def currency_conversion(amount:float, from_currency:str, to_currency:str) -> str:
	"""
	currency_conversion : Convert a specific amount from one currency to another    
	Parameters:
	amount (float): Amount to convert.
	from_currency (str): Source currency.
	to_currency (str): Target currency.

	Required Parameter = [amount,from_currency,to_currency,]

	"""
	return 'Success'

tools = [banking_service, currency_conversion]
