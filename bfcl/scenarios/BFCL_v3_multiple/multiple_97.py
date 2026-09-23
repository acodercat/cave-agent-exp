from typing import List, Dict, Any, Union, Tuple, Set 
def geometry_area_circle(radius:int, units:str='meters') -> str:
	"""
	geometry_area_circle : Calculate the area of a circle given the radius.    
	Parameters:
	radius (int): The radius of the circle.
	units (str): The units in which the radius is measured (defaults to meters).

	Required Parameter = [radius,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def plot_sine_wave(start_range:float, end_range:float, frequency:float, amplitude:float=None, phase_shift:float=None) -> str:
	"""
	plot_sine_wave : Plot a sine wave for a given frequency in a given range.    
	Parameters:
	start_range (float): Start of the range in radians.
	end_range (float): End of the range in radians.
	frequency (float): Frequency of the sine wave in Hz.
	amplitude (float): Amplitude of the sine wave. Default is 1.
	phase_shift (float): Phase shift of the sine wave in radians. Default is 0.

	Required Parameter = [start_range,end_range,frequency,]

	"""
	return 'Success'

tools = [geometry_area_circle, plot_sine_wave]
