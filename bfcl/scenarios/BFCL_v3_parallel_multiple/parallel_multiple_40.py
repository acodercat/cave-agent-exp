from typing import List, Dict, Any, Union, Tuple, Set 
def scienceFacts_getCharge(particle:str, unit:str) -> str:
	"""
	scienceFacts_getCharge : Fetch the electric charge of an atomic particle    
	Parameters:
	particle (str): The atomic particle. e.g. Electron, Proton
	unit (str): Unit to retrieve electric charge. For example, 'coulombs' etc.

	Required Parameter = [particle,unit,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def scienceFacts_getWeight(particle:str, unit:str) -> str:
	"""
	scienceFacts_getWeight : Fetch the atomic weight of an atomic particle    
	Parameters:
	particle (str): The atomic particle. e.g. Electron, Proton
	unit (str): Unit to retrieve weight. For example, 'kg', 'pound', 'amu' etc.

	Required Parameter = [particle,unit,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def scienceFacts_getDiameter(particle:str, unit:str) -> str:
	"""
	scienceFacts_getDiameter : Fetch the diameter of an atomic particle    
	Parameters:
	particle (str): The atomic particle. e.g. Electron, Proton
	unit (str): Unit to retrieve diameter. For example, 'meter', 'cm', 'femtometers' etc.

	Required Parameter = [particle,unit,]

	"""
	return 'Success'

tools = [scienceFacts_getCharge, scienceFacts_getWeight, scienceFacts_getDiameter]
