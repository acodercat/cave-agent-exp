from typing import List, Dict, Any, Union, Tuple, Set 
def portfolio_future_value(stock:str, invested_amount:int, expected_annual_return:float, years:int) -> str:
	"""
	portfolio_future_value : Calculate the future value of an investment in a specific stock based on the invested amount, expected annual return and number of years.    
	Parameters:
	stock (str): The ticker symbol of the stock.
	invested_amount (int): The invested amount in USD.
	expected_annual_return (float): The expected annual return on investment as a decimal. E.g. 5% = 0.05
	years (int): The number of years for which the investment is made.

	Required Parameter = [stock,invested_amount,expected_annual_return,years,]

	"""
	return 'Success'

tools = [portfolio_future_value]
