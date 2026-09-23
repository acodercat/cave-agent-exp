from typing import List, Dict, Any, Union, Tuple, Set 
def corporate_finance_product_price(company:str, product:str) -> str:
	"""
	corporate_finance_product_price : Fetch the current selling price of the product.    
	Parameters:
	company (str): The company that sells the product.
	product (str): The product whose price we want to fetch.

	Required Parameter = [company,product,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def corporate_finance_revenue_forecast(company:str, product:str, sales_units_increase_percentage:int=None) -> str:
	"""
	corporate_finance_revenue_forecast : Estimate the revenue of a company by multiplying the sales units of the product with its selling price.    
	Parameters:
	company (str): The company that you want to calculate the revenue for.
	product (str): The product sold by the company.
	sales_units_increase_percentage (int): Percentage increase in the sales units. This value is optional and defaults to zero if not provided.

	Required Parameter = [company,product,]

	"""
	return 'Success'

tools = [corporate_finance_product_price, corporate_finance_revenue_forecast]
