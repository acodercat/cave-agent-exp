from typing import List, Dict, Any, Union, Tuple, Set 
def stock_invest_calculate_investment_cost(company:str, shares:int) -> str:
	"""
	stock_invest_calculate_investment_cost : Calculate the cost of investing in a specific number of shares from a given company.    
	Parameters:
	company (str): The company that you want to invest in.
	shares (int): Number of shares to invest.

	Required Parameter = [company,shares,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def stock_invest_calculate_dividend_payout(shares:int, dividend_per_share:float) -> str:
	"""
	stock_invest_calculate_dividend_payout : Calculate the total dividend payout for a specific number of shares with known dividend per share.    
	Parameters:
	shares (int): Number of shares to calculate dividends.
	dividend_per_share (float): Known dividend per share.

	Required Parameter = [shares,dividend_per_share,]

	"""
	return 'Success'

tools = [stock_invest_calculate_investment_cost, stock_invest_calculate_dividend_payout]
