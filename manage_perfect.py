#region imports

from AlgorithmImports import *

''' <summary>
 This is the External_Structure class needed for storing info on the various EH's and EL's we need to track
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
from builder_perfect import builder_perfect
#endregion

class manage_perfect(object):
    def __init__(self, perfect_to_manage: builder_perfect) -> None:
        self.perfect = perfect_to_manage
        self.perfect_trade_reqested = False
        self.perfect_in_trade = False
        self.logging = False
        self.count = 0 
        self.perfect_pips_ratchet = 0   #this informs us when pips move up
        self.symbol = None

        # TODO: add some kind of event log - same class as builder_perfect or a new one?

    def create_manage_perfect(self, sender, symbol, timenow, logging=False) -> None:
        sdh = sender.symbolInfo[symbol]
        if not self.perfect_in_trade:
            timenow = fusion_utils.get_times(timenow, 'us')['mt4']
            self.logging = logging
            self.perfect_trade_requested = True
            self.symbol = symbol
            self.count += 1
            if sdh.is_in_a_trade(sender):
                self.perfect_in_trade = True    #critical to set this to true
                sdh.tbu_perfect_tracker[ChartRes.res5M].add_to_event_log(timenow, "Managing Perfect - ON", "Trade is now being managed by Perfect Manager", 0, "Ground Zero")   
            if logging: sender.Log(f"manage_perfect:manage_new_trade: {symbol} - in_trade: {self.perfect_in_trade}")
        else:
            if logging: sender.Log(f"manage_perfect:manage_new_trade: {symbol} - already in a trade, needed clearing first")
            return
        return

    def manage_perfect_trade(self, sender, symbol, timenow, bidpricenow, askpricenow, logging=False) -> None:
        order_level = 1 #TODO: make this loop when we have multiple index levels
        order_index = order_level - 1
        sdh = sender.symbolInfo[symbol]
        pnlpips = sender.get_current_pnlpips(sdh, bidpricenow, askpricenow)         
        #will build a variety of bails and moves to manage perfects for profit optimisations

        #lets start with the simplest of overriders

        #lets move the stop to 5 pips profit



        pass

    def clear_manage_perfect(self, sender, symbol, timenow, logging=False) -> None:
        sdh = sender.symbolInfo[symbol]
        if self.perfect_in_trade and not sdh.is_in_a_trade(sender):
            timenow = fusion_utils.get_times(timenow, 'us')['mt4']
            self.perfect_in_trade = False
            self.symbol = None
            self.count -= 1
            sdh.tbu_perfect_tracker[ChartRes.res5M].add_to_event_log(timenow, "Managing Perfect - OFF", "Trade is no longer being managed by Perfect Manager", 0, "Ground Zero")   

        return    

        


        




            
                
