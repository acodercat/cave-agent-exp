from typing import List, Dict, Any, Union, Tuple, Set 
def office_designer_design(rooms:int, meeting_room:str) -> str:
	"""
	office_designer_design : Design an office space based on specific requirements    
	Parameters:
	rooms (int): Number of rooms in the office.
	meeting_room (str): Size of the meeting room

	Required Parameter = [rooms,meeting_room,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def house_designer_design(bedrooms:int, bathrooms:int, garden:bool=None) -> str:
	"""
	house_designer_design : Design a house based on specific criteria    
	Parameters:
	bedrooms (int): Number of bedrooms desired.
	bathrooms (int): Number of bathrooms needed.
	garden (bool): Does the house need a garden? Default is False

	Required Parameter = [bedrooms,bathrooms,]

	"""
	return 'Success'

tools = [office_designer_design, house_designer_design]
