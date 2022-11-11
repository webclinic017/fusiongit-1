#region imports
from AlgorithmImports import *
#endregion
from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Indicators")

import enum
import math
import pandas as pd
from datetime import date, time, datetime, timedelta
from System import *
from System.Collections.Generic import Dictionary
from QuantConnect import *
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
from symbolinfo import *
from consolidators import *
from notify import *
from QuantConnect import Market
from io import StringIO
import pandas as pd

'''Contains a bunch of helper functions for dealing with testing perfects - in an attempt to save space in the main file'''


class QCalgo_test_perfects(QCalgo_notifications):
    # create a dictionary of historic trades to do.  Then manually push the values into the SymbolInfo class for the right symbol
    # so that manual trades can take place at the correct points using the manual trade mechanism

    # Key - date and time to inject the trade into the backtest
    # Column 0 - symbol
    # Column 1 - direction of trade
    # Column 2 - whether to use a trailling stop or not (if not, uses breakout steps)
    # Column 3 - number of pips for the trailling stop, allows experiments for different levels including on currencies
    # Column 4 - take profit level in pips; if not set to non zero value, uses defaults for manual trades set in SymbolInfo class
    # Column 5 - flag for whether to move to 'breakeven' once the trade gets to certain pips level - see Column 6
    # Column 6 - pips level once hit then move to 'breakeven' - see Column 7
    # Column 7 - profit level to set the 'breakeven'

    old_manual_trades_dict = {
    "2022-06-06 02:30": ["GBPUSD", StratDirection.Long, True, 15, 0.0, True, 8.0, 0.0],
    "2022-06-13 04:30": ["GBPUSD", StratDirection.Short, True, 20, 100.0, True, 10.0, 2.0],
    "2022-06-15 15:00": ["GBPUSD", StratDirection.Long,  False, 0, 50.0, False, 0.0, 0.0]
    }

    #Brads trades in GY
    brad_manual_trades_dict = {
    "2022-07-01 10:42": ["GBPJPY", StratDirection.Long, True, 12, 45, True, 8.0, 0.0],
    "2022-07-01 18:06": ["GBPJPY", StratDirection.Long, True, 12, 45, True, 8.0, 0.0],
    "2022-07-05 04:16": ["GBPJPY", StratDirection.Long, True, 12, 45, True, 8.0, 0.0],
    "2022-07-05 17:58": ["GBPJPY", StratDirection.Short, True, 12, 50, True, 8.0, 0.0],    
    "2022-08-02 03:04": ["GBPJPY", StratDirection.Short, True, 12, 50, True, 8.0, 0.0],
    "2022-08-12 10:40": ["GBPJPY", StratDirection.Short, True, 12, 25.0, True, 8.0, 0.0]
    }

    manual_trades_dict = {
    "2022-08-01 10:36": ["GBPJPY", StratDirection.Long, True, 12, 32, True, 7.5, 0.0],
    "2022-08-02 12:28": ["GBPJPY", StratDirection.Short, True, 12, 45, True, 7.5, 0.0],
    "2022-08-04 06:07": ["GBPJPY", StratDirection.Long, True, 12, 32, True, 7.5, 0.0],
    "2022-08-05 05:28": ["GBPJPY", StratDirection.Short, True, 12, 45, True, 7.5, 0.0],
    "2022-08-08 04:17": ["GBPJPY", StratDirection.Long, True, 12, 25, True, 7.5, 0.0], 
    "2022-08-09 17:50": ["GBPJPY", StratDirection.Short, True, 12, 25, True, 7.5, 0.0],    
    "2022-08-11 16:54": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0],
    "2022-08-12 09:25": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0],
    "2022-08-12 17:33": ["GBPJPY", StratDirection.Short, True, 12, 30, True, 7.5, 0.0],    
    "2022-08-15 05:46": ["GBPJPY", StratDirection.Short, True, 12, 30, True, 7.5, 0.0],    
    "2022-08-15 09:23": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0], 
    "2022-08-16 06:43": ["GBPJPY", StratDirection.Short, True, 12, 30, True, 7.5, 0.0],     
    "2022-08-17 12:35": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0],  
    "2022-08-18 09:14": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0], 
    "2022-08-19 05:07": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0], 
    "2022-08-22 15:20": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0],       
    "2022-08-23 09:29": ["GBPJPY", StratDirection.Short, True, 12, 30, True, 7.5, 0.0],                           
    "2022-08-25 03:33": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0],  
    "2022-08-25 18:27": ["GBPJPY", StratDirection.Short, True, 12, 30, True, 7.5, 0.0],   
    "2022-08-26 15:41": ["GBPJPY", StratDirection.Short, True, 12, 30, True, 7.5, 0.0],  
    "2022-08-30 04:33": ["GBPJPY", StratDirection.Short, True, 12, 30, True, 7.5, 0.0],  
    "2022-08-30 18:15": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0],     
    "2022-08-31 15:54": ["GBPJPY", StratDirection.Long, True, 12, 30, True, 7.5, 0.0]  
    }



    manual_trades_tz = "mt4"

    # ideas for smarter trade management - to test using known trades
    # TODO: in_trade : add the ability to specific when to move to B/E or a specific stop loss
    # TODO: in_trade : add in the ability to specify a list of points at which to reduce position sizes by a proportion (pip_level, % to reduce): list of 
    # TODO: in_trade : add in a flag to turn on/off defensive actions to get out of a trade if signs are bad (weakness seen in other direction, too long in trade etc)


