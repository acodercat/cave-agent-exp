from typing import List, Dict, Any, Union, Tuple, Set 
def bank_account_transfer(from_account:str, to_account:str, amount:float) -> str:
	"""
	bank_account_transfer : Transfer a given amount from one account to another.    
	Parameters:
	from_account (str): The account to transfer from.
	to_account (str): The account to transfer to.
	amount (float): The amount to be transferred.

	Required Parameter = [from_account,to_account,amount,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def bank_account_calculate_interest(principal:float, rate:float, time:int) -> str:
	"""
	bank_account_calculate_interest : Calculate the amount of interest accrued over a given time period.    
	Parameters:
	principal (float): The initial amount of money.
	rate (float): The annual interest rate as a decimal.
	time (int): The number of years the money is invested for.

	Required Parameter = [principal,rate,time,]

	"""
	return 'Success'

tools = [bank_account_transfer, bank_account_calculate_interest]
