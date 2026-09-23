from typing import List, Dict, Any, Union, Tuple, Set 
def stock_price(company:str, days:int, data_type:str=None) -> str:
	"""
	stock_price : Get stock price data for a given company over a specified number of days.    
	Parameters:
	company (str): The company name.
	days (int): The number of previous days to retrieve data for.
	data_type (str): The type of price data to retrieve (e.g., 'Open', 'Close', 'High', 'Low'). Default is 'Close'.

	Required Parameter = [company,days,]

	"""
	return 'Success'

tools = [stock_price]
