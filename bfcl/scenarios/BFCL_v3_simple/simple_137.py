from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_stock_return(investment_amount:int, annual_growth_rate:float, holding_period:int, dividends:bool=None) -> str:
	"""
	calculate_stock_return : Calculate the projected return of a stock investment given the investment amount, the annual growth rate and holding period in years.    
	Parameters:
	investment_amount (int): The amount of money to invest.
	annual_growth_rate (float): The expected annual growth rate of the stock.
	holding_period (int): The number of years you intend to hold the stock.
	dividends (bool): Optional. True if the calculation should take into account potential dividends. Default is false.

	Required Parameter = [investment_amount,annual_growth_rate,holding_period,]

	"""
	return 'Success'

tools = [calculate_stock_return]
