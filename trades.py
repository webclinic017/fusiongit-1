#region imports
from pickletools import UP_TO_NEWLINE
from AlgorithmImports import *

''' <summary>
 This is the Trades class to store the trades and trade details ... [possibly to be added to the object store]
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
from copy import deepcopy
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
from dataclasses import dataclass
from fusion_utils import *
#endregion

#define trade class
class trades(object):
    def __init__(self, name) -> None:
        
        self.status = None          #TODO  create a trade status enum
        self.trade_details = []
        self.trade_id = 0           # unique id for the trade - maybe we can get this from the object store
        self.trends = []        
        self.entry_time = None
        self.exit_time = None
        self.entry_price = 0.0
        self.exit_price = 0.0
        self.direction = None
        self.trend_type = None      #trending or countertrending - important to look and see if most of our trades are trending or countertrending
        self.result_pips = 0.0
        self.result_money = 0.0
        self.lot_size = 0.0
        self.total_quantity = 0.0
        self.bankroll_percentage = 0.0
        self.risk = 0.0             # start by grading trades 1-5 in terms of probability of success        
        self.risk_reward = 0.0
        self.strategy_type = None  
        self.strategy_name = None
        self.builder_label = None       #can use this to pass the builder label e.g. CHH4 to the trade object
        self.move_to_breakeven_pips = 0.0
        self.move_to_breakeven_price = 0.0
        self.initial_stop_loss_pips = 0.0
        self.initial_stop_loss_price = 0.0
        self.initial_stop_loss_type = None












    


    
