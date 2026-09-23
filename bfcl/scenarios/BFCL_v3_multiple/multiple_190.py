from typing import List, Dict, Any, Union, Tuple, Set 
def get_stock_price(company_names:List[str]) -> str:
	"""
	get_stock_price : Retrieves the current stock price of the specified companies    
	Parameters:
	company_names (List[str]): The list of companies for which to retrieve the stock price.

	Required Parameter = [company_names,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def currency_converter(base_currency:str, target_currency:str, amount:float) -> str:
	"""
	currency_converter : Calculates the cost in target currency given the amount in base currency and exchange rate    
	Parameters:
	base_currency (str): The currency to convert from.
	target_currency (str): The currency to convert to.
	amount (float): The amount in base currency

	Required Parameter = [base_currency,target_currency,amount,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def book_hotel(hotel_name:str, location:str, room_type:str, start_date:str, nights:int) -> str:
	"""
	book_hotel : Book a room of specified type for a particular number of nights at a specific hotel, starting from a specified date.    
	Parameters:
	hotel_name (str): The name of the hotel.
	location (str): The city in which the hotel is located.
	room_type (str): The type of room to be booked.
	start_date (str): The start date for the booking.
	nights (int): The number of nights for which the booking is to be made.

	Required Parameter = [hotel_name,location,room_type,start_date,nights,]

	"""
	return 'Success'

tools = [get_stock_price, currency_converter, book_hotel]
