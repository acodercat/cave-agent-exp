from typing import List, Dict, Any, Union, Tuple, Set 
def financial_ratio_net_profit_margin(net_income:int, total_revenue:int) -> str:
	"""
	financial_ratio_net_profit_margin : Calculate net profit margin of a company given the net income and total revenue    
	Parameters:
	net_income (int): The net income of the company.
	total_revenue (int): The total revenue of the company.

	Required Parameter = [net_income,total_revenue,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def financial_ratio_debt_ratio(total_liabilities:int, total_assets:int) -> str:
	"""
	financial_ratio_debt_ratio : Calculate the debt ratio of a company given the total liabilities and total assets.    
	Parameters:
	total_liabilities (int): The total liabilities of the company.
	total_assets (int): The total assets of the company.

	Required Parameter = [total_liabilities,total_assets,]

	"""
	return 'Success'

tools = [financial_ratio_net_profit_margin, financial_ratio_debt_ratio]
