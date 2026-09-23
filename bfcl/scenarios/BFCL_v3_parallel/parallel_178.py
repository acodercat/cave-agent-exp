from typing import List, Dict, Any, Union, Tuple, Set 
def get_stock_price(company_name:str, date:str, exchange:str=None) -> str:
	"""
	get_stock_price : Get the closing stock price for a specific company on a specified date.    
	Parameters:
	company_name (str): Name of the company.
	date (str): Date of when to get the stock price. Format: yyyy-mm-dd.
	exchange (str): Name of the stock exchange market where the company's stock is listed. Default is 'NASDAQ'

	Required Parameter = [company_name,date,]

	"""
	return 'Success'

tools = [get_stock_price]
