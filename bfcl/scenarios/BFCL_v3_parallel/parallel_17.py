from typing import List, Dict, Any, Union, Tuple, Set 
def get_stock_data(symbol:str, data_points:List[str]) -> str:
	"""
	get_stock_data : Retrieve the most recent trading day's closing price and volume for a specified stock.    
	Parameters:
	symbol (str): The stock symbol of the company.
	data_points (List[str]): The type of data you want to retrieve for the stock. This can include closing price, opening price, volume, etc.

	Required Parameter = [symbol,data_points,]

	"""
	return 'Success'

tools = [get_stock_data]
