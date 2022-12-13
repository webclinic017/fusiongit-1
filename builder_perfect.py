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
from builder_perfect_1 import builder_perfect_1
#endregion


# Define a class for tracking build ups of Brad PERFECT trades -- these will then be added to a list to ensure we can keep a series, update averages etc
class builder_perfect(builder_perfect_1):
    def __init__(self, name) -> None:
        self.name = name
        self.history_length = 250        
        
        # Control variables to control behaviour of perfect
        self.enforce_trading_window = True  #Si 17.10.22 - added flag just to give more testing trades... should be True in production 
        self.pullback1_clearance_pips = 0.001  # if there is a gap from CLL to L or CHH to H of less than this value, we will invalidate the trade, unless with trend
        self.void_only_after_PB1 = True  # if True, we will only void the trade if the void price levels are breached after PB1 is breached.  False, the voids happen whenever
        # change this clearance pips to a v small value to negate the effect
        ####################################################
        
        self.BO_type = "None"           # possible values are "None", "LONG", "SHORT"        
        self.BO_pos1_price = 0.0
        self.BO_pos1_time = None
        self.BO_pos2_price = 0.0
        self.BO_pos2_time = None
        self.BO_pos3_price = 0.0
        self.BO_pos3_time = None
        self.BO_pos4_price = 0.0
        self.BO_pos4_time = None
        self.BO_pullback1_price = 0.0
        self.BO_pullback1_breached = False
        self.BO_pullback1_breached_time = None
        self.BO_hh_or_ll_breached = False
        self.BO_hh_or_ll_breached_time = None
        self.BO_active = False
        self.EH_price = 0.0
        self.EL_price = 0.0
        self.old_EH_price = 0.0
        self.old_EL_price = 0.0
        self.last_time = None        
        self.CHH_took_EH = False
        self.CLL_took_EL = False        
        self.TW = None
        self.TW_to_end = None
        self.BO_status = ""
        self.BO_count = 0
        self.log_details = True
        self.ignore_200ema = False        
        self.squeeze_status = "Nothing"
        self.squeeze_found = False
        self.squeeze_time = None
        self.squeeze_price = 0.0
        self.last_1m_peak = 0.0
        self.last_1m_trough = 0.0
        self.trend_5m = EHELTrends.Unknown
        self.trend_1h = EHELTrends.Unknown
        self.with_5m_trend = False
        self.with_1h_trend = False
        self.stop_price = 0.0
        self.stop_pips = 0.0
        self.stop_comments = ""        
        self.take_profit_pips = 0.0
        self.take_profit_price = 0.0
        self.take_profit_comments = ""
        self.move_breakeven = 0.0
        self.result_pips = 0.0   
        self.max_pips_profit = 0.0
        self.entry_time = None
        self.enter_trade = False
        self.reason_notes = ""
        self.spread_pips = 0.0
        self.enough_headroom_failed = 0        
        self.current_session_high_time = None
        self.current_session_low_time = None
        self.current_session_high_price = 0.0
        self.current_session_low_price = 0.0
        self.prev_session_high_time = None
        self.prev_session_low_time = None
        self.prev_session_high_price = 0.0
        self.prev_session_low_price = 0.0
        self.void_trade_high = 0.0
        self.void_trade_low = 0.0
        self.void_trade_high_breached_yet = False
        self.void_trade_low_breached_yet = False
        self.rolling_high = 0.0
        self.rolling_low = 0.0
        self.symbol = ""
        self.perfect_just_formed = False
        self.double_spot = False   #flag to indicate that we have a double reversal spot
        self.event_log = []    #use this to output an event log per breakout
        self.log_item = {"event_time_mt4": None,
                        "event_details": None,
                        "event_type": None,
                        "event_price": None,
                        "event_chart": None}

        
        self.builder_store = {"BO_label": None,
                            "symbol": None,
                            "double_spot": None,
                            "update_time": None,
                            "pos1_label": None,
                            "pos1_price": None,
                            "pos1_time": None,
                            "pos2_label": None,
                            "pos2_price": None,
                            "pos2_time": None,
                            "pos3_label": None,
                            "pos3_price": None,
                            "pos3_time": None,
                            "pos4_label": None,
                            "pos4_price": None,
                            "pos4_time": None,
                            "pullback1_price": None,
                            "EH_price": None,
                            "EL_price": None,
                            "TW": None,
                            "status": None,
                            "pullback1_hit": None,
                            "BO_pullback1_breached_time": None,
                            "hh_or_ll_hit": None,
                            "hh_or_ll_time": None,                        
                            "ignore_200ema": None,
                            "squeeze_status": None,
                            "squeeze_time": None,
                            "squeeze_price": None,
                            "entry_time": None,
                            "enter_trade": None,
                            "ema9": None,
                            "ema45": None,
                            "ema135": None,
                            "ema200": None,
                            "reason_notes": None,
                            "last_1m_peak": None,
                            "last_1m_trough": None,
                            "trend_5m": None,
                            "trend_1h": None,
                            "with_5m_trend": None,
                            "with_1h_trend": None,
                            "stop_price": None,
                            "stop_pips:": None,
                            "stop_comments:": None,
                            "take_profit_pips": None,
                            "take_profit_price": None,
                            "take_profit_comments": None,                          
                            "move_breakeven": None,
                            "result_pips": None,
                            "max_pips_profit": None,
                            "spread_pips": None,
                            "void_trade_high": 0.0,
                            "void_trade_low": 0.0,
                            "rolling_high": 0.0,
                            "rolling_low": 0.0}

        self.perfect_library = []

    'Using this section for a series of helper functions to make the code more readable'



    def create_possible_perfect(self, sender, symbol, my_breakout, time_now, my_EH, my_EL, EH_EL_tracker, my_template_5m, my_template_1h, ignore_200ema, logging=True):
        self.log_details = logging
        sdh = sender.symbolInfo[symbol]

        self.event_log = []    #use this to output an event log per breakout
        self.log_item = {"event_time_mt4": None,
                        "event_details": None,
                        "event_type": None,
                        "event_price": None,
                        "event_chart": None}

        # find out the session highs and lows, looking over the current session or the prior one
        # time is needed to then go back and work out whether we have had a strong move from that level
        mt4_time = fusion_utils.get_times(time_now, 'us')['mt4']
        room_pips_needed = 25.0
        fail_strong_move_room = False
        free_pips = 0.0
        #(free_pips, fail_strong_move_room) = self.get_free_pips_off_strong_move(sender, symbol, time_now, my_breakout, room_pips_needed, logging)
        
        debug_time = fusion_utils.get_times(sender.Time, 'us')['mt4']
        '''if debug_time == "2022.10.24, 09:35:00":
            sender.Debug({debug_time})                
            my_hit = 1'''

        self.perfect_just_formed = True    #this allows us to know if we have just formed a perfect trade as 1m consolidator fires after 5m!

        if self.BO_active:
            if not self.BO_pullback1_breached:
                # only replace an existing possible trade when a new breakout is formed IF we have not yet hit PB1
                # otherwise will already be on the 1min chart looking for entry
                if self.log_details: sender.Log(f"{symbol} Breakout already active when trying to start a new Perfect buildup - marking as replaced")
                self.perfect_library[-1]["status"] = "replaced"
                self.add_to_event_log(debug_time, f"CLL {self.BO_label} Breakout", "Breakout not hit PB1 and replaced", 0.0, "5 min")
                self.clear_down_perfect_and_write_log(sender, time_now)   
            else:
                # we need to ignore this new one - because we have an active one!!  Doh!
                if self.log_details: sender.Log(f"{symbol} Breakout is clean but we have an active squeeze hunt in play - cancelling")
                return False    

        if self.enforce_trading_window:
            if fusion_utils.get_trading_window(time_now) not in [TradingWindow.TW1, TradingWindow.TW2, TradingWindow.TW3]:
                if self.log_details: sender.Log(f"{symbol} Breakout is clean but did not land in Trading Window 1,2 or 3 - cancelling")
                return False
        else:
           if self.log_details: sender.Debug(f"{symbol} Breakout - Trading Window enforcement is disabled")           

        # clear some values that need clearing every time we create new perfect
        self.void_trade_high = 0.0
        self.void_trade_low = 0.0
        self.void_trade_high_breached_yet = False
        self.void_trade_low_breached_yet = False

        self.rolling_high = 0.0
        self.rolling_low = 0.0

        #SI - 13.12.2022 new logic that checks for a previous entry in the same trading window as entry rules should be relaxed
        #search the log for an entry in the same trading window
        #if we get a match, set the variable, change email and then ultimately relax the entry rules
        self.double_spot = self.find_double_spot(sender, symbol, mt4_time, my_breakout)


        if my_breakout.long_or_short == 'LONG':
            #si moved for logging
            self.BO_count +=1
            if self.BO_count > 1000:        # Wrap the ID's back to 1 after 1000
                self.BO_count = 1
            self.BO_label = "Long CHH" + str(self.BO_count)
            self.BO_type = "LONG"
            self.symbol = symbol
            self.BO_pullback1_breached = False
            self.BO_pullback1_breached_time = None
            self.BO_hh_or_ll_breached = False
            self.BO_hh_or_ll_breached_time = None            
            self.squeeze_status = "Nothing"
            self.entry_time = None
            self.squeeze_price = 0.0
            self.squeeze_found = False
            self.squeeze_time = None
            self.enter_trade = False
            self.reason_notes = ""
            self.ignore_200ema = ignore_200ema
            self.CHH_took_EH = False
            self.CLL_took_EL = False
            self.EH_price = my_EH
            self.EL_price = my_EL
            self.trend_5m = my_template_5m
            self.trend_1h = my_template_1h
            if self.trend_5m == fusion_utils.get_ehel_trend_string(EHELTrends.Uptrend):
                self.with_5m_trend = True
            else:
                self.with_5m_trend = False
            if self.trend_1h == fusion_utils.get_ehel_trend_string(EHELTrends.Uptrend):
                self.with_1h_trend = True
            else:
                self.with_1h_trend = False
            self.stop_price = 0.0
            self.stop_pips = 0.0
            self.stop_comments = ""
            self.take_profit_pips = 0.0
            self.take_profit_price = 0.0
            self.take_profit_comments = ""
            self.move_breakeven = 0.0
            self.result_pips = 0.0

            self.last_time = time_now
            self.BO_pos1_price = my_breakout.BT_TroughLow
            self.BO_pos1_time = my_breakout.BT_turn1_time
            self.BO_pos2_price = my_breakout.BT_PeakHigh
            self.BO_pos2_time = my_breakout.BT_turn2_time                
            self.BO_pos3_price = my_breakout.BT_lower_low
            self.BO_pos3_time = my_breakout.BT_turn3_time            
            self.BO_pos4_price = my_breakout.BT_higher_close 
            self.BO_pos4_time = my_breakout.triggered_time
            self.BO_pullback1_price = my_breakout.BT_pullback1
            self.spread_pips = 0.0
            self.trade_requested = False  

            pb1_distance_pips = fusion_utils.get_difference_in_pips(self.BO_pos4_price, self.BO_pos2_price,sdh.minPriceVariation * 10)

            self.add_to_event_log(mt4_time, f"{self.BO_label}", f"Breakout {pb1_distance_pips} pips to PB1", self.BO_pos4_price, "5 min")

            if not fail_strong_move_room:
                self.BO_active = True
                self.BO_status = "wait for PB1"            
            else:
                self.BO_active = True
                self.add_to_event_log(mt4_time, f"HOS Strong move - Cancelled", f"Strong move from HOS only {free_pips} when {room_pips_needed} pips room needed - cancelled", self.BO_pos4_price, "5 min")
                self.clear_down_perfect_and_write_log(sender, time_now) 
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Strong move from HOS only {free_pips} when {room_pips_needed} pips room needed - cancelled")
                self.BO_status = f"Strong move from HOS only {free_pips} when {room_pips_needed} pips room needed - cancelled"
                self.store_CHH(time_now)
                return

            if self.BO_pos4_price > self.EH_price:
                # we are already outside the external structure - so we need to refer back to the last EH above the CHH
                self.CHH_took_EH = True
                referred_EH_price = 0.0
                referred_EH_time = None
                (referred_EH_price, referred_EH_time) = EH_EL_tracker.find_higher_EH_than_price(self.BO_pos4_price)                
                if referred_EH_price > 0.0:
                    referred_EH_time = fusion_utils.format_datetime_using_string(referred_EH_time, "%Y-%m-%d %H:%M:%S")
                    self.old_EH_price = self.EH_price
                    self.EH_price = referred_EH_price
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout, the CHH took out the EH - New EH is {self.EH_price} at {referred_EH_time}")
                self.add_to_event_log(mt4_time, f"CHH took out the EH", f"A new EH has been created {self.EH_price} at {referred_EH_time}", self.EH_price, "5 min")   

            
            if self.enforce_trading_window:
                self.TW = fusion_utils.get_trading_window(time_now)
                self.TW_to_end = fusion_utils.get_time_until_end_of_trading_window(time_now, self.TW)
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout has been found inside {self.TW} and has {self.TW_to_end} until expiry")
            else:
                if self.log_details: sender.Debug(f"{symbol} {self.BO_label} Breakout has been found- Trading Window enforcement is disabled")

            self.store_CHH(time_now)


        if my_breakout.long_or_short == 'SHORT':            
            #si moved for logging
            self.BO_count +=1
            if self.BO_count > 1000:        # Wrap the ID's back to 1 after 1000
                self.BO_count = 1
            self.BO_label = "Short CLL" + str(self.BO_count)
            self.BO_type = "SHORT"
            self.symbol = symbol
            self.BO_pullback1_breached = False
            self.BO_pullback1_breached_time = None
            self.BO_hh_or_ll_breached = False
            self.BO_hh_or_ll_breached_time = None            
            self.squeeze_status = "Nothing"
            self.entry_time = None
            self.squeeze_price = 0.0
            self.squeeze_found = False
            self.squeeze_time = None
            self.enter_trade = False
            self.reason_notes = ""
            self.ignore_200ema = ignore_200ema
            self.CLL_took_EL = False
            self.CHH_took_EH = False
            self.EH_price = my_EH
            self.EL_price = my_EL
            self.trend_5m = my_template_5m
            self.trend_1h = my_template_1h
            if self.trend_5m == fusion_utils.get_ehel_trend_string(EHELTrends.Downtrend):
                self.with_5m_trend = True
            else:
                self.with_5m_trend = False
            if self.trend_1h == fusion_utils.get_ehel_trend_string(EHELTrends.Downtrend):
                self.with_1h_trend = True
            else:
                self.with_1h_trend = False
            self.stop_price = 0.0
            self.stop_price = 0.0
            self.stop_pips = 0.0
            self.stop_comments = ""                 
            self.take_profit_pips = 0.0
            self.take_profit_price = 0.0
            self.take_profit_comments = ""
            self.move_breakeven = 0.0
            self.result_pips = 0.0            

            self.last_time = time_now
            self.BO_pos1_price = my_breakout.BT_PeakHigh
            self.BO_pos1_time = my_breakout.BT_turn1_time
            self.BO_pos2_price = my_breakout.BT_TroughLow
            self.BO_pos2_time = my_breakout.BT_turn2_time                
            self.BO_pos3_price = my_breakout.BT_higher_high
            self.BO_pos3_time = my_breakout.BT_turn3_time            
            self.BO_pos4_price = my_breakout.BT_lower_close 
            self.BO_pos4_time = my_breakout.triggered_time
            self.BO_pullback1_price = my_breakout.BT_pullback1
            self.spread_pips = 0.0
            self.trade_requested = False  
            
            pb1_distance_pips = fusion_utils.get_difference_in_pips(self.BO_pos4_price, self.BO_pos2_price,sdh.minPriceVariation * 10)

            self.add_to_event_log(mt4_time, f"CLL {self.BO_label} Breakout", f"CLL formed, {pb1_distance_pips} pips to PB1", self.BO_pos4_price, "5 min")

            if not fail_strong_move_room:
                self.BO_active = True
                self.BO_status = "wait for PB1"            
            else:
                self.BO_active = True
                self.add_to_event_log(mt4_time, f"LOS Strong move - Cancelled", f"Strong move from LOS only {free_pips} when {room_pips_needed} pips room needed - cancelled", self.BO_pos4_price, "5 min")                
                self.clear_down_perfect_and_write_log(sender, time_now)
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Strong move from LOS only {free_pips} when {room_pips_needed} pips room needed - cancelled")
                self.BO_status = f"Strong move from LOS only {free_pips} when {room_pips_needed} pips room needed - cancelled"
                self.store_CLL(time_now)
                return

            if self.BO_pos4_price < self.EL_price:
                # we are already outside the external structure - so we need to refer back to the last EL below the CLL
                self.CLL_took_EL = True
                referred_EL_price = 0.0
                referred_EL_time = None
                (referred_EL_price, referred_EL_time) = EH_EL_tracker.find_lower_EL_than_price(self.BO_pos4_price)
                if referred_EL_price > 0.0:
                    referred_EL_time = fusion_utils.format_datetime_using_string(referred_EL_time, "%Y-%m-%d %H:%M:%S")
                    self.old_EL_price = self.EL_price
                    self.EL_price = referred_EL_price
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout, the CLL took out the EL - New EL is {self.EL_price} at {referred_EL_time}")
                self.add_to_event_log(mt4_time, f"CLL took out the EL", f"A new EL has been created {self.EL_price} at {referred_EL_time}", self.EL_price, "5 min")               


            if self.enforce_trading_window:
                self.TW = fusion_utils.get_trading_window(time_now)
                self.TW_to_end = fusion_utils.get_time_until_end_of_trading_window(time_now, self.TW)
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout has been found inside {self.TW} and has {self.TW_to_end} until expiry")
            else:
                if self.log_details: sender.Debug(f"{symbol} {self.BO_label} Breakout has been found- Trading Window enforcement is disabled")         

            self.store_CLL(time_now)
        
        self.add_to_event_log(mt4_time, f"Trend Detection", f" With 5 min Trend: {self.with_5m_trend } | With 1 hr Trend: {self.with_1h_trend}", 0, "5 min / 1 hr")        

        if self.double_spot:
            if self.log_details: sender.Log(f"{symbol} Double Spot at {mt4_time} - {self.BO_label} Breakout")
            self.add_to_event_log(mt4_time, f"Double Spot", f"Double {symbol} spot in this TW - relax rules", 0, "5 min")  


        #send an email notification 
        if sender.send_breakout_emails:
            sender.SendBreakoutEmail(symbol, mt4_time, self.BO_pos4_price, self.BO_pos4_time, self.BO_type, self.BO_label, self.BO_pullback1_price, \
                pb1_distance_pips, self.double_spot)               

        return True    
    



    def check_price_to_pullback1(self, sender, symbol, chart_res, price_now, price_low, price_high, time_now, myEH, myEL, pip_size):
        # check whether price has come back to PB1
        # check whether time window has timed out
        # check whether price has breached the void trade high or void trade low --> voids trade    
        # check whether price has breached the EH price or EL price --> voids trade
        # check whether price has breached the HH or LL --> voids trade
        # if PB1 hit then update squeeze status
        
        # now that we refer back to the EH/EL if one is taken out, do not update them
        '''self.EH_price = myEH
        self.EL_price = myEL
        self.perfect_library[-1]["EH_price"] = self.EH_price
        self.perfect_library[-1]["EL_price"] = self.EL_price'''
        pullback_hit_time = fusion_utils.get_times(time_now, 'us')['mt4']
        log_time_now = pullback_hit_time            # pullbacks are done every single update - using ChartRes to convert here would remove 5mins from the time of the event

        if self.BO_type == "LONG" and self.BO_active:
            #Si added 17.10.2022 to help trap errors currently in demo trading
            if self.log_details and log_time_now.second == 0:   #only do this every minute to quieten log noise
                sender.Log(f"{symbol} {self.BO_label} - Checking Pullback (Long) | price_now: {price_now} | price_high: {price_high} | log_time_now: {log_time_now} | EH Price: {self.EH_price} \
                    | self.BO_pullback1_price: {self.BO_pullback1_price} | squeeze_status: {self.squeeze_status}| CHH_took_EH: {self.CHH_took_EH}")  

            if price_high > self.EH_price and not self.BO_pullback1_breached:
                # we have breached the EH while waiting for pullback, so need to void the trade
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chart_res} has been invalidated by breach of EH {self.EH_price}")
                self.perfect_library[-1]["status"] = "EH breach waiting for PB1"  
                self.perfect_library[-1]["reason_notes"] = f"EH breach of {self.EH_price} while waiting for PB1"                                  
                self.add_to_event_log(log_time_now, f"BO CANCELLED", "EH Breached waiting for pullback to PB1", self.EH_price, "per tick")
                self.clear_down_perfect_and_write_log(sender, time_now) 
                return

            if price_low <= self.BO_pullback1_price and not self.BO_pullback1_breached:
                self.perfect_library[-1]["status"] = "PB1hit"
                self.perfect_library[-1]["pullback1_hit"] = True
                self.perfect_library[-1]["BO_pullback1_breached_time"] = pullback_hit_time
                self.squeeze_status = "Waiting"
                self.perfect_library[-1]["squeeze_status"] = self.squeeze_status                
                if self.log_details: 
                    sender.Log(f"{symbol} {self.BO_label} Breakout on {chart_res} has triggered PB1 at {self.BO_pullback1_price} @ {log_time_now} ")                
                self.BO_pullback1_breached = True
                self.BO_pullback1_breached_time = pullback_hit_time
                self.add_to_event_log(log_time_now, f"PB1 Hit", "Price has pulled back to PB1", self.BO_pullback1_price, "per tick")


        if self.BO_type == "SHORT" and self.BO_active:
            #Si added 17.10.2022 to help trap errors currently in demo trading
            if self.log_details and log_time_now.second == 0: #only do this every minute to quieten log noise
                sender.Log(f"{symbol} {self.BO_label} - Checking Pullback (Short) | price_now: {price_now} | price_low: {price_low} | log_time_now: {log_time_now} | EL Price: {self.EL_price} \
                    | self.BO_pullback1_price: {self.BO_pullback1_price} | squeeze_status: {self.squeeze_status}| CLL_took_EL: {self.CLL_took_EL}")  

            if price_low < self.EL_price and not self.BO_pullback1_breached:
                # we have breached the EL while waiting for pullback, so need to void the trade
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chart_res} has been invalidated by breach of EL {self.EL_price}")
                self.perfect_library[-1]["status"] = "EL breach waiting for PB1"  
                self.perfect_library[-1]["reason_notes"] = f"EL breach of {self.EL_price} while waiting for PB1"                                  
                self.add_to_event_log(log_time_now, f"BO CANCELLED", "EL Breached waiting for pullback to PB1", self.EL_price, "per tick")
                self.clear_down_perfect_and_write_log(sender, time_now) 
                return

            if price_high >= self.BO_pullback1_price and not self.BO_pullback1_breached:
                self.perfect_library[-1]["status"] = "PB1hit"
                self.perfect_library[-1]["pullback1_hit"] = True
                self.perfect_library[-1]["BO_pullback1_breached_time"] = pullback_hit_time
                self.squeeze_status = "Waiting"
                self.perfect_library[-1]["squeeze_status"] = self.squeeze_status          

                if self.log_details: 
                    sender.Log(f"{symbol} {self.BO_label} Breakout on {chart_res} has triggered PB1 at {self.BO_pullback1_price} @ {log_time_now}")                
                self.BO_pullback1_breached = True
                self.BO_pullback1_breached_time = pullback_hit_time

                self.add_to_event_log(log_time_now, f"CLL {self.BO_label} PB1 Hit", "PB1 Hit", self.BO_pullback1_price, "per tick")                
                 
        #now check to see if the PB1 clearance is sufficient enough - this code is same for both LONG and SHORT
        if self.BO_pullback1_breached:
            PB1_clearance_pips = fusion_utils.get_difference_in_pips(self.BO_pullback1_price, self.BO_pos4_price, pip_size)                     
            if PB1_clearance_pips > self.pullback1_clearance_pips:
                pass
            else:
                if self.with_1h_trend and self.with_5m_trend:
                    pass    
                else:
                    if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chart_res} has been invalidated by PB1 clearance of {PB1_clearance_pips} pips")
                    self.perfect_library[-1]["status"] = "not enough PB1 clearance"  
                    self.perfect_library[-1]["reason_notes"] = f"PB1 clearance breach: {PB1_clearance_pips}"                        
                    self.add_to_event_log(log_time_now, f"CLL {self.BO_label} PB1 Clearance check failed", "PB1 too small", PB1_clearance_pips, "per tick")
                    self.clear_down_perfect_and_write_log(sender, time_now)   
        
        return



    def get_free_pips_off_strong_move(self, sender, symbol, time_now, my_breakout, room_pips_needed, logging):
        free_pips = 0.0
        fail_strong_move_room = False
        green_count = 0
        red_count = 0
        x_value = 0.0
        x_was_negative = False
        breakout_took_out_price = False
        sdh = sender.symbolInfo[symbol]
        mt4_time = fusion_utils.get_times(time_now, 'us')['mt4']
        smart_hos = 0.0
        smart_los = 0.0
        if my_breakout.long_or_short == 'LONG':
            comp_price_for_strong_move = my_breakout.BT_higher_close
        else:
            comp_price_for_strong_move = my_breakout.BT_lower_close

        self.current_session_high_time = None
        self.prev_session_high_time = None
        self.current_session_low_time = None
        self.prev_session_low_time = None
        (self.current_session_high_time, self.current_session_high_price) = sdh.get_smart_session_high_time_and_price("current", comp_price_for_strong_move, bar_tolerance=3)
        (self.current_session_low_time, self.current_session_low_price) = sdh.get_smart_session_low_time_and_price("current", comp_price_for_strong_move, bar_tolerance=3)
        (self.prev_session_high_time, self.prev_session_high_price) = sdh.get_smart_session_high_time_and_price("prev", comp_price_for_strong_move, bar_tolerance=3)
        (self.prev_session_low_time, self.prev_session_low_price) = sdh.get_smart_session_low_time_and_price("prev", comp_price_for_strong_move, bar_tolerance=3)
        
        # check LONG breakouts, so we are using session highs
        if my_breakout.long_or_short == 'LONG':
            # check current session first
            x_value_c = 0.0
            x_value_p = 0.0
            red_count_c = 0
            current_session_blocked = False
            if self.current_session_high_time is not None:
                (red_count_c, x_value_c) = sdh.count_reds_from_high(sdh.Bars5M, sdh.Bars5MColour, self.current_session_high_time, self.current_session_high_price)
                if x_value_c > 0.0:
                    free_pips_c = round((x_value_c - my_breakout.BT_higher_close) / (sdh.minPriceVariation * 10), 2)
                    if red_count_c >= 3 and free_pips_c < room_pips_needed and free_pips_c >= 0.0:
                        fail_strong_move_room = True    
                        current_session_blocked = True
                    if free_pips_c < 0.0 and red_count_c >= 3:
                        # we are now within the area of the 123 move itself, and may have taken it out
                        x_was_negative = True
                        if my_breakout.BT_higher_close > self.current_session_high_price:
                            # we are in the clear
                            breakout_took_out_price = True
                        else:
                            # otherwise this has to fail the check
                            fail_strong_move_room = True    
                            current_session_blocked = True
                    free_pips = free_pips_c
                    red_count = red_count_c
                    x_value = x_value_c
                    mt4_high = fusion_utils.get_times(self.current_session_high_time, 'us')['mt4']
                    smart_hos = self.current_session_high_price
                    if logging: sender.Log(f"LONG perfect - current HOS : {smart_hos} at {mt4_high}.  CHH at {mt4_time} REDS: {red_count_c} FreePips: {free_pips_c} XVal: {x_value_c} CHH took out high: {breakout_took_out_price}")
            
            #now check previous session
            if not current_session_blocked:
                (red_count_p, x_value_p) = sdh.count_reds_from_high(sdh.Bars5M, sdh.Bars5MColour, self.prev_session_high_time, self.prev_session_high_price)
                if x_value_p > 0.0:
                    free_pips_p = round((x_value_p - my_breakout.BT_higher_close) / (sdh.minPriceVariation * 10), 2)
                    if red_count_p >= 3 and free_pips_p < room_pips_needed and free_pips_p >= 0.0:
                        fail_strong_move_room = True    
                    if free_pips_p < 0.0 and red_count_p >= 3:
                        # we are now within the area of the 123 move itself, and may have taken it out
                        x_was_negative = True
                        if my_breakout.BT_higher_close > self.prev_session_high_price:
                            # we are in the clear
                            breakout_took_out_price = True
                        else:
                            # otherwise this has to fail the check
                            fail_strong_move_room = True
                    free_pips = free_pips_p
                    red_count = red_count_p
                    x_value = x_value_p
                    mt4_high = fusion_utils.get_times(self.prev_session_high_time, 'us')['mt4']
                    smart_hos = self.prev_session_high_price
                    if logging: sender.Log(f"LONG perfect - previous HOS : {smart_hos} at {mt4_high}.  CHH at {mt4_time} REDS: {red_count_p} FreePips: {free_pips_p} XVal: {x_value_p} CHH took out high: {breakout_took_out_price}")
            
        elif my_breakout.long_or_short == 'SHORT':
            # check current session first
            x_value_c = 0.0
            x_value_p = 0.0
            green_count_c = 0
            current_session_blocked = False
            if self.current_session_low_time is not None:
                (green_count_c, x_value_c) = sdh.count_greens_from_low(sdh.Bars5M, sdh.Bars5MColour, self.current_session_low_time, self.current_session_low_price)
                if x_value_c > 0.0:               
                    free_pips_c = round((my_breakout.BT_lower_close - x_value_c) / (sdh.minPriceVariation * 10), 2)
                    if green_count_c >= 3 and free_pips_c < room_pips_needed and free_pips_c >= 0.0:
                        fail_strong_move_room = True
                        current_session_blocked = True
                    if free_pips_c < 0.0 and green_count_c >= 3:
                        # we are now within the area of the 123 move itself, and may have taken it out
                        x_was_negative = True
                        if my_breakout.BT_lower_close < self.current_session_low_price:
                            # we are in the clear
                            breakout_took_out_price = True
                        else:
                            # otherwise this has to fail the check
                            fail_strong_move_room = True
                            current_session_blocked = True
                    free_pips = free_pips_c
                    green_count = green_count_c
                    x_value = x_value_c
                    mt4_low = fusion_utils.get_times(self.current_session_low_time, 'us')['mt4']
                    smart_los = self.current_session_low_price
                    if logging: sender.Log(f"SHORT perfect - current LOS : {smart_los} at {mt4_low}.  CLL at {mt4_time} GREENS: {green_count_c} FreePips: {free_pips_c} XVal: {x_value_c} CLL took out low: {breakout_took_out_price}")

            # now check previous session
            if not current_session_blocked:
                (green_count_p, x_value_p) = sdh.count_greens_from_low(sdh.Bars5M, sdh.Bars5MColour, self.prev_session_low_time, self.prev_session_low_price)
                if x_value_p > 0.0:
                    free_pips_p = round((my_breakout.BT_lower_close - x_value_p) / (sdh.minPriceVariation * 10), 2)
                    if green_count_p >= 3 and free_pips_p < room_pips_needed and free_pips_p >= 0.0:
                        fail_strong_move_room = True
                    if free_pips_p < 0.0 and green_count_p >= 3:
                        # we are now within the area of the 123 move itself, and may have taken it out
                        x_was_negative = True
                        if my_breakout.BT_lower_close < self.prev_session_low_price:
                            # we are in the clear
                            breakout_took_out_price = True
                        else:
                            # otherwise this has to fail the check
                            fail_strong_move_room = True
                    free_pips = free_pips_p
                    green_count = green_count_p
                    x_value = x_value_p
                    mt4_low = fusion_utils.get_times(self.prev_session_low_time, 'us')['mt4']
                    smart_los = self.prev_session_low_price
                    if logging: sender.Log(f"SHORT perfect - previous LOS : {smart_los} at {mt4_low}.  CLL at {mt4_time} GREENS: {green_count_p} FreePips: {free_pips_p} XVal: {x_value_p} CLL took out low: {breakout_took_out_price}")
        
        if fail_strong_move_room:
            if x_was_negative:
                extra_msg = " breakout did not take out 123 price"
            else:
                extra_msg = ""
            if my_breakout.long_or_short == 'LONG':
                self.add_to_event_log(mt4_time, f"strong 123 move from HOS of {smart_hos} found, room check fail: {fail_strong_move_room}", f"RED count: {red_count}  X pips: {free_pips} XVal: {x_value}" + extra_msg, 0, "5 min")
            else:
                self.add_to_event_log(mt4_time, f"strong 123 move from LOS of {smart_los} found, room check fail: {fail_strong_move_room}", f"GREEN count: {green_count}  X pips: {free_pips} XVal: {x_value}" + extra_msg, 0, "5 min")
        else:
            if my_breakout.long_or_short == 'LONG':
                self.add_to_event_log(mt4_time, f"strong 123 move from HOS of {smart_hos} not found", f"RED count: {red_count}  X pips: {free_pips} XVal: {x_value}", 0, "5 min")
            else:
                self.add_to_event_log(mt4_time, f"strong 123 move from LOS of {smart_los} not found", f"GREEN count: {green_count}  X pips: {free_pips} XVal: {x_value}", 0, "5 min")

        return (free_pips, fail_strong_move_room)



    def check_for_trade_entry(self, sender, symbol, chartres, closeprice, timenow, ema9, ema45, ema135, ema200, askpricenow, bidpricenow, \
        pip_size, bid_high, bid_low, myEH, myEL, candle_open_1m_mt4):
        
        # need to see if EH and EL have been updated and record them if so
        # CG - this needs to stay commented out I think.  Because otherwise the 'referred EL/EH get reverted
        # we use the referred EH/EL to figure out if things have been taken out
        # if we also somehow need to use newly formed EH/EL we need to work out how to do that
        '''self.EH_price = myEH
        self.EL_price = myEL
        self.perfect_library[-1]["EH_price"] = self.EH_price
        self.perfect_library[-1]["EL_price"] = self.EL_price'''
        
        # we still need to ensure that the squeeze check is still true
        squeeze_valid = False
        stop_entry_valid = False
        enough_headroom = False        
        self.spread_pips = fusion_utils.get_difference_in_pips(askpricenow, bidpricenow, pip_size)    

        #check for squeeze must be done here    
        squeeze_valid = self.check_for_squeeze(sender, symbol, chartres, closeprice, timenow, ema9, ema45, ema135, ema200, candle_open_1m_mt4)


        if not squeeze_valid:             
            return         
            #continue with entry tests and if all pass then enter trade 


        countertrend_hard_pip_stop = 10.0    #TODO: speak to Brad to determine when this might be used

        #check to see whether a void high or low has been formed. Without this we cant enter trade as we dont have a headroom calculation
        if self.BO_type == "LONG" and self.void_trade_high == 0.0:   
            return 
        if self.BO_type == "SHORT" and self.void_trade_low == 0.0:
            return

        #figure out the headroom... which will form the trigger point for the move to breakeven
        self.move_breakeven = 0.0  
        min_headroom_pips = 3.0

        if self.BO_type == "LONG":
            self.move_breakeven = fusion_utils.get_difference_in_pips(self.rolling_high, closeprice, pip_size)          
        else:
            self.move_breakeven = fusion_utils.get_difference_in_pips(self.rolling_low, closeprice, pip_size)          

        if self.move_breakeven >= (self.spread_pips + min_headroom_pips):
            enough_headroom = True
            if self.log_details: sender.Log(f"Enough headroom - {self.move_breakeven} pips @{candle_open_1m_mt4}")
            self.add_to_event_log(candle_open_1m_mt4,"Headroom Test - PASSED", f"Headroom is {self.move_breakeven} pips, needs min. {self.spread_pips + min_headroom_pips} pips.", closeprice, "1 min")

        else:
            self.enough_headroom_failed += 1
            if self.log_details: sender.Log(f"Not enough headroom: BE {self.move_breakeven} pips. Needs min. {self.spread_pips + min_headroom_pips} pips.  Waiting")
            self.add_to_event_log(candle_open_1m_mt4,"Headroom Test - FAILED", f"Headroom: {self.move_breakeven} pips, Min: {self.spread_pips + min_headroom_pips} pips.", closeprice, "1 min")            
            return

        # work out if we have a strong pullback
        sd = sender.symbolInfo[symbol]
        strong_pullback = False
        pullback_count = 0
        pullback_start_price = 0.0
        candle_open_to_ignore = self.BO_pos4_time - timedelta(minutes=5)
        if self.BO_type == "LONG":
            (strong_pullback, pullback_count, pullback_start_price) = sd.was_straight_move_down(sd.Bars5M, sd.Bars5MColour, candle_open_to_ignore)
        else:
            (strong_pullback, pullback_count, pullback_start_price) = sd.was_straight_move_up(sd.Bars5M, sd.Bars5MColour, candle_open_to_ignore)

        if strong_pullback and not self.with_1h_trend:
            # TODO: need to add a conditional check that the pullback_start_price is actually near to high of session/day or low of session/day
            # if not close to high or low, then can ignore a strong pullback
            # have to void this trade
            # for now the strong pullback check is ignored if we are trading with the 1h trend
            self.enter_trade = False
            self.reason_notes = f"Strong pullback {pullback_count} candles, start {pullback_start_price}"
            self.perfect_library[-1]["status"] = "trade not entered"
            self.entry_time = timenow
            if sender.log_tbu_perfects_details: sender.Log(f"{symbol} {self.BO_label} Pullback on 5mins is too strong with {pullback_count} candles, not entering trade")
            self.add_to_event_log(candle_open_1m_mt4, "BO Cancelled", "Not with 5m Trend. Pullback on 5 mins too strong - {pullback_count} candles ", self.void_trade_low, "5 min")   
            # end of the line for this breakout.  After this it is no longer active
            self.clear_down_perfect_and_write_log(sender, candle_open_1m_mt4)   
  
        min_stop_pips = self.spread_pips + 2.0  #have to have a minimum protection, 
        #TODO need to see if distance to last peak or troiugh is less than minimum stop and go back to a prevous peak or trough


        # need to check we can get a tight enough stop, ideally as tight as possible
        distance_to_peak_or_trough = 0.0    
        last_peak_or_trough_time = None
        #TODO not to self Si - should we comparing the close or low/high of the candle to the peak/trough?  
        if self.BO_type == "LONG":
            (last_trough_price, last_peak_or_trough_time) = sd.EH_EL_tracker[ChartRes.res1M].find_lower_trough_than_price_and_time(closeprice, candle_open_1m_mt4)
            last_peak_or_trough_time = fusion_utils.format_datetime_using_string(last_peak_or_trough_time, "%Y-%m-%d %H:%M:%S")
            self.last_1m_trough = last_trough_price
            self.perfect_library[-1]["last_1m_trough"] = last_trough_price
            distance_to_peak_or_trough = fusion_utils.get_difference_in_pips(last_trough_price, bidpricenow, pip_size)         
            self.add_to_event_log(candle_open_1m_mt4,"Last Trough Calculation", f"Distance to last EL trough for stop calc: {distance_to_peak_or_trough} pips", last_trough_price, last_peak_or_trough_time)               
        else:
            (last_peak_price, last_peak_or_trough_time) = sd.EH_EL_tracker[ChartRes.res1M].find_lower_trough_than_price_and_time(closeprice, candle_open_1m_mt4)
            last_peak_or_trough_time = fusion_utils.format_datetime_using_string(last_peak_or_trough_time, "%Y-%m-%d %H:%M:%S")
            self.last_1m_peak = last_peak_price
            self.perfect_library[-1]["last_1m_peak"] = last_peak_price
            distance_to_peak_or_trough = fusion_utils.get_difference_in_pips(last_peak_price, bidpricenow, pip_size)  
            self.add_to_event_log(candle_open_1m_mt4,"Last Peak Calculation", f"Distance to last EH peak for stop calc: {distance_to_peak_or_trough} pips", last_peak_price, last_peak_or_trough_time)            
        
        

        self.stop_pips = distance_to_peak_or_trough


        #TODO speak to Brad about what the minimum stop should be
        #TODO: make this a list of symbols and their stop distances          
         
        if  self.stop_pips < min_stop_pips:
            stop_entry_valid = True    
            self.stop_comments = f"Stop is {self.stop_pips} pips. Too small. Minimum of stop of {min_stop_pips} including spread {self.spread_pips } pips"            

          
            self.reason_notes = f"Stop {self.stop_pips} pips away excl. spread. Too much."
            self.stop_comments = f"Last Peak/Trough was {self.stop_pips} excl. spread. Not entering trade."
            self.perfect_library[-1]["status"] = "trade not entered yet - stop too small.  Waiting"
            self.perfect_library[-1]["reason_notes"] = self.reason_notes
            self.perfect_library[-1]["stop_comments"] = self.stop_comments
            self.add_to_event_log(candle_open_1m_mt4,"Stop Calculation - FAILED ", f"Stop is {self.stop_pips} pips. Too small. Minimum stop {min_stop_pips} pips (includes spread {self.spread_pips })", min_stop_pips, last_peak_or_trough_time)                    
            # we may find that a later run through we have got a tighter stop...so keep waiting; don't just stop the trade    
            return

        elif self.stop_pips >= min_stop_pips and self.stop_pips <= 12:              
            stop_entry_valid = True             
            self.stop_comments = f"Tight stop created from Last Peak/Trough: {self.stop_pips} pips plus spread {self.spread_pips } pips"  
            self.add_to_event_log(candle_open_1m_mt4,"Stop Calculation - PASSED", f"Tight stop {self.stop_pips} pips from last peak / trough (excl. spread {self.spread_pips})",self.stop_pips, last_peak_or_trough_time)  
        elif self.stop_pips > 12 and (self.spread_pips + self.stop_pips) <= 20:
            # SI added additional logic following conversation with Brad 16.08.2022 
            stop_entry_valid = True              
            self.stop_comments = f"Last Peak/Trough was {self.stop_pips} pips. Hard Stop 12 pips plus spread {self.spread_pips} pips"
            self.add_to_event_log(candle_open_1m_mt4,"Stop Calculation - PASSED", f"Stop was {self.stop_pips} pips, changed to hard stop of 12 pips (excl. spread {self.spread_pips})",12, last_peak_or_trough_time)  
            self.stop_pips = 12   #so this will be hard stop incl. spread this SHOULD give us enough room whilst minimising the risk 
        else:  
            self.reason_notes = f"Stop {self.stop_pips} pips away excl. spread. Too much."
            self.stop_comments = f"Last Peak/Trough was {self.stop_pips} excl. spread. Not entering trade."
            self.perfect_library[-1]["status"] = "trade not entered yet - stop too large.  Waiting"
            self.perfect_library[-1]["reason_notes"] = self.reason_notes
            self.perfect_library[-1]["stop_comments"] = self.stop_comments
            self.add_to_event_log(candle_open_1m_mt4,"Stop Calculation - FAILED", f"Stop {self.stop_pips} pips too big (excl. spread {self.spread_pips})",{self.stop_pips}, last_peak_or_trough_time)             
            # we may find that a later run through we have got a tighter stop...so keep waiting; don't just stop the trade
            return

        self.take_profit_pips = 25.0 # for the moment set hard take profit in pips
        self.take_profit_comments = f"Currently set at hard {self.take_profit_pips} pips"      
    
        #figure out the minimum win:loss ratio. If we are not going to make at least 1:1 then don't enter the trade
        #in the future we might use this to consider bet size along with other factors
        min_win_loss_ratio = self.move_breakeven / self.stop_pips
        if min_win_loss_ratio < 1.0:
            self.add_to_event_log(candle_open_1m_mt4,"Win:Loss Calculation - FAILED", f"Win/Loss Ratio: {min_win_loss_ratio} needs to be >=1. Move Breakeven {self.move_breakeven} / Stop {self.stop_pips} pips", 0, "1 min")
            return
        else:
            self.add_to_event_log(candle_open_1m_mt4,"Win:Loss Calculation - PASSED", f"Win/Loss Ratio: {min_win_loss_ratio} needs to be >=1. Move Breakeven {self.move_breakeven} / Stop {self.stop_pips} pips",0, "1 min")  


        if stop_entry_valid:
            (self.stop_price, self.take_profit_price) = fusion_utils.get_me_the_correct_prices(bidpricenow, askpricenow, pip_size, \
                self.BO_type, self.stop_pips, self.take_profit_pips)

        if self.log_details: 
            sender.Log(f"{symbol} Checking Perfect Entry - Reason: {self.reason_notes}")
            sender.Log(f"{symbol} Checking Perfect Entry - Stop Comments: {self.stop_comments}")
            sender.Log(f"{symbol} Checking Perfect Entry - Take Profit Comments: {self.take_profit_comments}")
            sender.Log(f"{symbol} Checking Perfect Entry - Entry_Valid: {stop_entry_valid}  Strong_Pullback: {strong_pullback}  Enough_Headroom: {enough_headroom}")

        if stop_entry_valid and not strong_pullback and enough_headroom:        

            # need one more check to see if wthin 5 minutes of US equity session
            if not fusion_utils.is_time_within_5_minutes_of_US_equities_start(timenow):
                if squeeze_valid:
                    self.reason_notes = f"Good Trade : Headroom failed count: {self.enough_headroom_failed}"
                    self.perfect_library[-1]["status"] = "trade_entry"

                    if sender.log_tbu_perfects_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chartres} has been passed for trade entry")
                    self.add_to_event_log(candle_open_1m_mt4,"Take Profit Calculation", f"Currently set at hard {self.take_profit_pips} pips",{self.take_profit_pips}, "1 min")                                                                                                  
                    # end of the line for this breakout.  After this it is no longer active
                    #sender.OutputFunction(False, False, True, "Brad BO Spot")    #write the output to the hourly                    
                    if sender.auto_trade_brad_perfects:
                        self.enter_trade = True
                        if self.move_breakeven > 8:
                            self.add_to_event_log(candle_open_1m_mt4,"Headroom Adjustment", f"Headroom reduced from {self.move_breakeven} to 8 pips", 8, "1 min")                            
                            self.move_breakeven = 8
                        
                        #si 07.12.2022 - reduce the move to BE if the spread is larger than 1.5 pips
                        move_to_be_adjustment = self.spread_pips - 1.5
                        if move_to_be_adjustment > 0:
                            self.add_to_event_log(candle_open_1m_mt4,"Spread Adjustment", f"Move to BE reduced from {self.move_breakeven} to {self.move_breakeven - move_to_be_adjustment} pips", self.move_breakeven - move_to_be_adjustment, "1 min")                            
                            self.move_breakeven = self.move_breakeven - move_to_be_adjustment
                                                    
                        # if we have enabled the trades to actually happen, then go ahead                        
                        # SI Can override any of the calculated values here:
                        #self.stop_price = 12
                        #self.take_profit_pips = 25
                        #self.move_breakeven = 7.5
                        # TODO: make the event log live beyond the start of the trade, to capture things that happen during the trade
                        # for now we just write the log

                        #sender.write_breakout_log(self.event_log, self.symbol, self.BO_pos4_time, self.BO_type)
                       
                        #self.do_enter_trade(sender, symbol, timenow) 
                else:
                    # we don't do anything - check_for_trade_entry will be called again and might pass the checks next time
                    pass
            else:
                self.enter_trade = False
                self.reason_notes = "5Mins to open"
                self.perfect_library[-1]["status"] = "trade blocked"
                self.entry_time = timenow
                if sender.log_tbu_perfects_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chartres} is within 5min of US open - no entry")
                # end of the line for this breakout.  After this it is no longer active
                self.add_to_event_log(candle_open_1m_mt4, "BO Cancelled", "Within 5 minutes of US equities open", 0, "1 min")                   
                self.clear_down_perfect_and_write_log(sender, candle_open_1m_mt4)   
                
        self.perfect_library[-1]["move_breakeven"] = self.move_breakeven        
        self.perfect_library[-1]["enter_trade"] = self.enter_trade
        self.perfect_library[-1]["reason_notes"] = self.reason_notes
        self.perfect_library[-1]["spread_pips"] = self.spread_pips           
        self.perfect_library[-1]["stop_price"] = self.stop_price  
        self.perfect_library[-1]["stop_pips"] = self.stop_pips      
        self.perfect_library[-1]["stop_comments"] = self.stop_comments       
        self.perfect_library[-1]["take_profit_pips"] = self.take_profit_pips    
        self.perfect_library[-1]["take_profit_price"] = self.take_profit_price 
        self.perfect_library[-1]["take_profit_comments"] = self.take_profit_comments             
               

    def do_enter_trade(self, sender, symbol, timenow):

        sd = sender.symbolInfo[symbol]

        self.entry_time = fusion_utils.get_times(timenow, 'us')['mt4']
        self.perfect_library[-1]["entry_time"] = self.entry_time

        if not sd.is_in_a_trade(sender) and not self.trade_requested:

            self.add_to_event_log(self.entry_time,"Entering Trade", f"All checks passed",0, "tick")              
            #self.clear_down_perfect_and_write_log(sender, self.entry_time)   

            #"2022-08-01 10:36": ["GBPJPY", StratDirection.Long, True, 12, 32, True, 7.5, 0.0],
            #"2022-08-02 12:28": ["GBPJPY", StratDirection.Short, True, 12, 45, True, 7.5, 0.0],
            if self.log_details: sender.Log(f"{symbol} {self.BO_label} attempting to enter Brad Perfect trade")
            sd.manualTradeDate = timenow
            sd.manualTradeHour = timenow.hour
            sd.manualTradeMinute = timenow.minute

            if self.BO_type == "LONG":
                sd.manualDirection = True               # long trade
            else:
                sd.manualDirection = False               # short trade

            #self.stop_price = 12
            #self.take_profit_pips = 25
            #self.move_breakeven = 8
            self.trade_requested = True
            sd.profit_dist = self.take_profit_pips
            sd.trailling_stop = True
            sd.trailling_pips = self.stop_pips
            sd.trading_move_to_be_flag = True       # move to Breakeven flag
            sd.trading_move_to_be_profit_pips = self.move_breakeven #how many pips to move to Breakeven
            sd.trading_move_to_be_new_stop_pips = 0.0
            sd.type_of_trade_found = Strats.BradPerfect
            sd.trade_label_current = self.BO_label      # mark up the label of the current trade we are about to enter - for tracking results
                                
            '''
            # use these bits for a normal breakout lumpy stop..prob not needed
            else:
                # this will use the default stepped breakout stop approach
                self.symbolInfo[symbol].trailling_stop = False
                self.symbolInfo[symbol].breakout_pnl = self.symbolInfo[symbol].sl_pnl_manual
                self.symbolInfo[symbol].breakout_trail = self.symbolInfo[symbol].sl_trail_manual
                self.symbolInfo[symbol].profit_dist = self.symbolInfo[symbol].sl_profit_manual
            '''     
            # default values that FTI might set specifically - or just to make sure the trade gets found in OnData
            sd.manual_fti_sign = True
            sd.manualTradeFound = True
            sd.manualTradeConditional = False
            sd.manualBounceTrade = False
            sd.manualTradeID = -99
            sd.manualLotSize = 1
            sd.manualCheckMinutes = 120
            sd.manualExpectedEntry = 0.0            

        else:
            if sender.log_tbu_perfects_details: sender.Log(f"{symbol} {self.BO_label} tried to enter Brad Perfect trade but already in a trade")

    
    # called from the OnOrderEvent function - when a trade completes, if it is a Brad Perfect, then update the result
    def find_and_update_label(self, sender, label_to_find, pips, max_pips_profit):
        for perfect_record in self.perfect_library:
            if perfect_record["BO_label"] == label_to_find:
                perfect_record["result_pips"] = pips
                perfect_record["max_pips_profit"] = max_pips_profit                
                logdate = datetime.strftime(fusion_utils.get_candle_open_time(perfect_record["entry_time"],None ), "%d/%m/%y %H:%M")                
                sender.Log(f"Found Brad Perfect trade result: {label_to_find} and updated result to {pips} pips")
                #now create the message detail ready for emailing
                message_detail = "\n".join("{} = {}".format(*item) for item in perfect_record.items())              


                print("message_detail=" + message_detail, "\n", logdate)
                
                return message_detail, logdate
        return False
  

    def find_double_spot(self, sender, symbol, mt4_time, my_breakout):
        # check to see if we have already entered a trade on this symbol in the same trading window
        if self.log_details: sender.Log(f"Checking for double spot on {symbol}")
        for perfect_record in self.perfect_library: 
            #find records in library for today
            if perfect_record["symbol"] == symbol:                
                if perfect_record["pos4_time"].date() == mt4_time.date() and fusion_utils.get_trading_window(mt4_time) == fusion_utils.get_trading_window(perfect_record["pos4_time"]):
                    if self.log_details: sender.Log(f"Found double reverse spot on {symbol}")
                    return True
        return False



    def dump_perfect_history(self, sender):
        for t in self.perfect_library:
            sender.Log(t)

