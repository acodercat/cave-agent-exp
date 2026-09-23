from typing import List, Dict, Any, Union, Tuple, Set 
def investment_withdraw(company:str, amount:float) -> str:
	"""
	investment_withdraw : Withdraw a specific amount from a company's stock.    
	Parameters:
	company (str): The company you want to withdraw from.
	amount (float): The amount you want to withdraw.

	Required Parameter = [company,amount,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def investment_invest(company:str, amount:float) -> str:
	"""
	investment_invest : Invest a specific amount in a company's stock.    
	Parameters:
	company (str): The company you want to invest in.
	amount (float): The amount you want to invest.

	Required Parameter = [company,amount,]

	"""
	return 'Success'

tools = [investment_withdraw, investment_invest]
