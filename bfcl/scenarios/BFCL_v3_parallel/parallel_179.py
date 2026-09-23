from typing import List, Dict, Any, Union, Tuple, Set 
def get_stock_price(company:str, days:int, exchange:str=None) -> str:
	"""
	get_stock_price : Retrieve the stock price for a specific company and time frame.    
	Parameters:
	company (str): The ticker symbol of the company.
	days (int): Number of past days for which the stock price is required.
	exchange (str): The stock exchange where the company is listed, default is NYSE

	Required Parameter = [company,days,]

	"""
	return 'Success'

tools = [get_stock_price]
