from typing import List, Dict, Any, Union, Tuple, Set 
def plot_sine_wave(start_range:int, end_range:float, frequency:int, amplitude:float=None, phase_shift:float=None) -> str:
	"""
	plot_sine_wave : Plot a sine wave for a given frequency in a given range.    
	Parameters:
	start_range (int): Start of the range in radians.
	end_range (float): End of the range in radians.
	frequency (int): Frequency of the sine wave in Hz.
	amplitude (float): Amplitude of the sine wave. Default is 1.
	phase_shift (float): Phase shift of the sine wave in radians. Default is 0.

	Required Parameter = [start_range,end_range,frequency,]

	"""
	return 'Success'

from typing import List, Dict, Any, Union, Tuple, Set 
def geometry_area_circle(radius:float, units:str='meters') -> str:
	"""
	geometry_area_circle : Calculate the area of a circle given the radius.    
	Parameters:
	radius (float): The radius of the circle.
	units (str): The units in which the radius is measured (defaults to meters).

	Required Parameter = [radius,]

	"""
	return 'Success'

tools = [plot_sine_wave, geometry_area_circle]
