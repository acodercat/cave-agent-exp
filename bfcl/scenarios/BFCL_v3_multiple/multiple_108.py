from typing import List, Dict, Any, Union, Tuple, Set 
def calc_heat_capacity(temp:int, volume:int, gas:str=None) -> str:
	"""
	calc_heat_capacity : Calculate the heat capacity at constant pressure of air using its temperature and volume.    
	Parameters:
	temp (int): The temperature of the gas in Kelvin.
	volume (int): The volume of the gas in m^3.
	gas (str): Type of gas, with air as default.

	Required Parameter = [temp,volume,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def calculate_discounted_cash_flow(coupon_payment:float, period:int, discount_rate:float, face_value:int=None) -> str:
	"""
	calculate_discounted_cash_flow : Calculate the discounted cash flow of a bond for a given annual coupon payment, time frame and discount rate.    
	Parameters:
	coupon_payment (float): The annual coupon payment.
	period (int): The time frame in years for which coupon payment is made.
	discount_rate (float): The discount rate.
	face_value (int): The face value of the bond, default is $1000.

	Required Parameter = [coupon_payment,period,discount_rate,]

	"""
	return 'Success'

tools = [calc_heat_capacity, calculate_discounted_cash_flow]
