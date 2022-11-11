#region imports
from itertools import count
from AlgorithmImports import *

''' <summary>
 This is the TurningPoints class needed for storing info on Peaks and Troughs etc
'''
from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Indicators")

import enum
import math
from datetime import date, time, datetime, timedelta
from System import *
from QuantConnect import *
from QuantConnect import Market
from QuantConnect.Algorithm import *
from QuantConnect.Brokerages import *
from QuantConnect.Orders import *
from QuantConnect.Indicators import *
from QuantConnect.Data import *
from QuantConnect.Data.Market import *
from QuantConnect.Data.Custom import *
from QuantConnect.Data.Consolidators import *
from QuantConnect.Python import *
from structs_and_enums import *
#from symbolinfo import *
from dataclasses import dataclass
#endregion



class brad_turning_point(object):
    def __init__(self, name, peak_or_trough, resolution, turn_time, turn_bar, start_time, confirm_time, count_lhs, pip_size):

       self.name = name
       self.peak_or_trough = peak_or_trough
       if peak_or_trough != 'PEAK' and peak_or_trough != 'TROUGH':
           raise TypeError("Must be a PEAK or a TROUGH when creating brad_turning_point object")
       self.resolution = resolution
       
       #default values for initial setup
       self.TP_low = turn_bar.Bid.Low
       self.TP_high = turn_bar.Bid.High
       self.TP_open = turn_bar.Bid.Open
       self.TP_close = turn_bar.Bid.Close

       self.wick_pips = round(abs(self.TP_high - self.TP_low) / pip_size, 2) - round(abs(self.TP_open - self.TP_close) / pip_size, 2)
       self.bar_pips = round(abs(self.TP_open - self.TP_close) / pip_size, 2)
       self.wick_percent = round(self.wick_pips / (self.bar_pips + self.wick_pips) * 100.0, 3)
       
       self.start_time = start_time
       self.turn_time = turn_time
       self.confirm_time = confirm_time
       self.last_check_time = confirm_time
       self.previous_check_time = None
       self.status = t_p_status.confirmed
       self.total_candles = 2 + count_lhs
       self.lhs_continuous = count_lhs
       self.rhs_continuous = 0
        
        
    