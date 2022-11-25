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
#endregion


class builder_perfect_1(object):

    '*** in top section we are using for some of the utilities - checks used multiple times within the main sections ***'

    def add_to_event_log(self, time_now, event_details, event_type, event_price, event_chart):

        #this seems to be messing up all the timestamps in the event logs?
        self.log_item["event_time_mt4"] = fusion_utils.format_datetime_using_string(time_now, "%Y-%m-%d %H:%M:%S")
        
        self.log_item["event_details"] = event_details
        self.log_item["event_type"] = event_type
        self.log_item["event_price"] = event_price
        self.log_item["event_chart"] = event_chart

        self.event_log.append(deepcopy(self.log_item))


    # find the void trade high or low if we didn't find it from the CLL or CHH.  Needs to be called every minute
    def set_void_prices(self, sender, symbol, candle_open_1m_mt4):
        sdh = sender.symbolInfo[symbol]

        if self.perfect_just_formed:    #we know the perfect has just formed and the 1 minute candle has not formed, so we can look back over the last 5 candles
            self.perfect_just_formed = False

            if self.BO_type == 'LONG':
                is_peak = False
                my_high = 0.0
                (is_peak, my_high, _, _, _) = sdh.is_peak_in_last_N_bars(sdh.Bars1M, n_bars=5, ignore_outside_bars=True)
                if is_peak:
                    #TODO add a check to see if any of the last bars are higher than the peak in which case dont set the void trade high
                    self.void_trade_high = my_high
                    self.rolling_high = my_high     #this will be set to the void trade high as a default
                    if self.log_details: sender.Log(f"LONG perfect - void trade high in CHH at {self.void_trade_high}")
                    self.add_to_event_log(candle_open_1m_mt4, "Void trade high set", "Void Trade High was set as part of CHH", self.void_trade_high, "Ground Zero")      
                else:
                    if self.log_details: sender.Log(f"LONG perfect - void trade high NOT found in CHH")
                    self.add_to_event_log(candle_open_1m_mt4, "No void trade high", "Void Trade High was NOT found in last 5 candles", self.void_trade_high, "Ground Zero")    
            if self.BO_type == 'SHORT':
                is_trough = False
                my_low = 0.0
                (is_trough, my_low, _, _, _) = sdh.is_trough_in_last_N_bars(sdh.Bars1M, n_bars=5, ignore_outside_bars=True)
                if is_trough:
                    #TODO add a check to see if any of the last bars are lower than the peak in which case dont set the void trade high
                    self.void_trade_low = my_low
                    self.rolling_low = my_low     #this will be set to the void trade low as a default
                    if self.log_details: sender.Log(f"SHORT perfect - void trade low in CLL at {self.void_trade_low}")
                    self.add_to_event_log(candle_open_1m_mt4, "Void trade low set", "Void Trade Low was set as part of CLL", self.void_trade_low, "Ground Zero")                        
                else:
                    if self.log_details: sender.Log(f"SHORT perfect - void trade low NOT found in CLL")
                    self.add_to_event_log(candle_open_1m_mt4, "No void trade low", "Void Trade Low was NOT found in last 5 candles", self.void_trade_high, "Ground Zero")   

        else:

            if self.BO_type == 'LONG' and self.void_trade_high == 0.0:
                is_peak = False
                my_high = 0.0
                (is_peak, my_high, _, _, _) = sdh.is_123_peak(sdh.Bars1M, ignore_outside_bars=True)
                if is_peak:
                    self.void_trade_high = my_high
                    self.rolling_high = my_high     #this will be set to the void trade high as a default
                    self.perfect_library[-1]["void_trade_high"] = self.void_trade_high
                    self.perfect_library[-1]["rolling_high"] = self.rolling_high
                    if self.log_details: sender.Log(f"LONG perfect - void trade high AFTER CHH at {self.void_trade_high} @{candle_open_1m_mt4}")
                    self.add_to_event_log(candle_open_1m_mt4, "Void Trade High Set", "Void Trade High locked in after CHH", self.void_trade_high, "1m") 
                else:
                    self.add_to_event_log(candle_open_1m_mt4, "Void Trade High NOT set", "High not locked in, no trade can be entered", self.void_trade_high, "1m") 

            if self.BO_type == 'SHORT' and self.void_trade_low == 0.0:
                is_trough = False
                my_low = 0.0
                (is_trough, my_low, _, _, _) = sdh.is_123_trough(sdh.Bars1M, ignore_outside_bars=True)
                if is_trough:
                    self.void_trade_low = my_low
                    self.rolling_low = my_low     #this will be set to the void trade low as a default
                    self.perfect_library[-1]["void_trade_low"] = self.void_trade_low
                    self.perfect_library[-1]["rolling_low"] = self.rolling_low
                    if self.log_details: sender.Log(f"SHORT perfect - void trade low AFTER CLL at {self.void_trade_low} @{candle_open_1m_mt4}")
                    self.add_to_event_log(candle_open_1m_mt4, "Void Trade Low Set", "Void Trade Low locked in after CLL", self.void_trade_low, "1 min") 
                else:
                    self.add_to_event_log(candle_open_1m_mt4, "Void Trade Low NOT set", "Low not locked in, no trade can be entered", self.void_trade_low, "1 min")                         


    #check whether price has moved past the void trade high or low. this is constant check prior to trade entry
    def check_for_void_trade_high_or_low_breached(self, sender, symbol, chart_res, price_low, price_high, time_now):

        mt4_time = fusion_utils.get_times(time_now, 'us')['mt4']  

        if self.BO_type == 'LONG': 
            if self.void_trade_high == 0.0:
                #sender.Log(f"{symbol} void_trade_high not set yet @{mt4_time}")
                return
            else:
                if (price_high > self.void_trade_high and not self.BO_pullback1_breached and self.void_only_after_PB1):
                    if not self.void_trade_high_breached_yet:
                        if self.log_details: sender.Log(f"{symbol} LONG perfect - void trade high IGNORED pre PB1 {self.EH_price} breach by price {price_high} @{mt4_time}")
                        self.void_trade_high_breached_yet = True
                        self.add_to_event_log(mt4_time, "Void Trade High Breach Ignored", f"Void Trade High Breached at {price_high} before PB1 hit - ignoring", price_high, "per tick")
                if (price_high > self.void_trade_high and self.BO_pullback1_breached and self.void_only_after_PB1) or (price_high > self.void_trade_high and not self.void_only_after_PB1):
                    if self.log_details: sender.Log(f"{symbol} LONG perfect - void trade high {self.EH_price} breached by price {price_high} @{mt4_time}")
                    self.perfect_library[-1]["status"] = "void_trade_high_breached"
                    self.perfect_library[-1]["reason_notes"] = f"Void trade high {self.EH_price} breached by price {price_high} @{mt4_time}"
                    self.add_to_event_log(mt4_time, "BO CANCELLED", f"Price breached Void Trade High {self.void_trade_high} | EH: {self.EH_price}", price_high, "per tick") 
                    self.clear_down_perfect_and_write_log(sender, time_now)

        if self.BO_type == 'SHORT':
            if self.void_trade_low == 0.0:
                #sender.Log(f"{symbol} void_trade_low not set yet @{mt4_time}")
                return
            else:
                if (price_low < self.void_trade_low and not self.BO_pullback1_breached and self.void_only_after_PB1):
                    if not self.void_trade_low_breached_yet:
                        if self.log_details: sender.Log(f"{symbol} SHORT perfect - void trade low IGNORED pre PB1 {self.EL_price} breach by price {price_low} @{mt4_time}")
                        self.void_trade_low_breached_yet = True
                        self.add_to_event_log(mt4_time, "Void Trade Low Breach Ignored", f"Void Trade Low Breached at {price_low} before PB1 hit - ignoring", price_low, "per tick")
                if (price_low < self.void_trade_low and self.BO_pullback1_breached and self.void_only_after_PB1) or (price_low < self.void_trade_low and not self.void_only_after_PB1):
                    if self.log_details: sender.Log(f"{symbol} SHORT perfect - void trade low {self.EL_price} breached by price {price_low} @{mt4_time}")
                    self.perfect_library[-1]["status"] = "void_trade_low_breached"
                    self.perfect_library[-1]["reason_notes"] = f"Void trade low {self.EL_price} breached by price {price_low} @{mt4_time}"
                    self.add_to_event_log(mt4_time, "BO CANCELLED", f"Price breached Void Trade Low {self.void_trade_low} | EL: {self.EL_price}", price_low, "per tick") 
                    self.clear_down_perfect_and_write_log(sender, time_now)
        return

    #check whether price has pulled back and breached the LL in the case of a LONG or the HH in the case of a SHORT
    def check_for_LL_or_HH_breach(self, sender, symbol, chart_res, price_low, price_high, time_now):
        
        mt4_time = fusion_utils.get_times(time_now, 'us')['mt4']  

        if self.BO_type == 'LONG':
            if price_low < self.BO_pos3_price:
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chart_res} invalidated by price {price_low} breach of LL {self.BO_pos3_price} @{mt4_time}")
                self.perfect_library[-1]["status"] = "Pullback Breach of LL"
                self.perfect_library[-1]["reason_notes"] = f"Invalidated by price {price_low} breach of LL {self.BO_pos3_price} @{mt4_time}"
                self.BO_hh_or_ll_breached = True
                self.BO_hh_or_ll_breached_time = mt4_time
                self.add_to_event_log(mt4_time, "BO CANCELLED", f"Price breached LL {self.BO_pos3_price}", price_low, "per tick") 
                self.clear_down_perfect_and_write_log(sender, time_now)

        if self.BO_type == "SHORT":
            if price_high > self.BO_pos3_price:
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chart_res} has been invalidated by price {price_high}  breach of HH {self.BO_pos3_price} @{mt4_time}")
                self.perfect_library[-1]["status"] = "Pullback Breach of HH"
                self.perfect_library[-1]["reason_notes"] = f"Invalidated by price {price_high} breach of HH {self.BO_pos3_price} @{mt4_time}"
                self.BO_hh_or_ll_breached = True
                self.BO_hh_or_ll_breached_time = mt4_time
                self.add_to_event_log(mt4_time, "BO CANCELLED", f"Price breached HH {self.BO_pos3_price}", {price_high}, "per tick") 
                self.clear_down_perfect_and_write_log(sender, time_now)                                    
                
        return


    # check whether time has gone past TW1, TW2 or TW3 end time
    def check_for_timeout(self, sender, symbol, chart_res, time_now, candle_open_1m_mt4):        

        if self.enforce_trading_window:
            new_time_to_end = fusion_utils.get_time_until_end_of_trading_window(time_now, self.TW)
            if new_time_to_end <= timedelta(seconds=0):
                if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chart_res} has timed out at end of Trading Window {self.TW} @{candle_open_1m_mt4}")
                if not self.BO_pullback1_breached:
                    # only set to expired if we didn't hit PB1, otherwise PB1hit is still recorded
                    self.perfect_library[-1]["status"] = "PB1 expired"
                    self.perfect_library[-1]["reason_notes"] = "Timeout - price did not reach PB1"    
                    self.add_to_event_log(candle_open_1m_mt4, "BO CANCELLED", f"Timeout - price did not pull back to PB1", 0, "per tick")  
                    self.clear_down_perfect_and_write_log(sender, time_now)                                    
                else:
                    #if not self.enter_trade and not self.squeeze_found:
                    if not self.enter_trade:
                        #self.perfect_library[-1]["status"] = "squeeze_hunt_expired"
                        #self.perfect_library[-1]["reason_notes"] = "Timeout - squeeze did not occur"  
                        #self.add_to_event_log(candle_open_1m_mt4, "BO CANCELLED", f"Timeout - no valid entry", 0, "per tick")      
                        # SI 17.11.2022 - per Brad, dont timeout if we hit PB1 but not yet entered
                        return True                   
                #self.clear_down_perfect_and_write_log(sender, time_now)
        else:
            if self.log_details: sender.Debug(f"{symbol} {self.BO_label} Breakout on {chart_res} - Trading Window enforcement is disabled")      

        return True
    


    # get the rolling 1 minute highs (from peaks) and lows (from troughs) that will act as the move to breakeven point / headroom test point
    def get_rolling_high_or_low(self, sender, symbol, candle_open_1m_mt4):
        sdh = sender.symbolInfo[symbol]

        if self.BO_type == 'LONG':
            is_peak = False
            my_high = 0.0
            (is_peak, my_high, _, _, _) = sdh.is_123_peak(sdh.Bars1M, ignore_outside_bars=True)
            if is_peak:
                self.rolling_high = my_high
                self.perfect_library[-1]["rolling_high"] = self.rolling_high
                if self.log_details: sender.Log(f"rolling high set at {self.rolling_high} @{candle_open_1m_mt4}")
                self.add_to_event_log(candle_open_1m_mt4,"Rolling High Set", f"New Rolling High, affects headroom", self.rolling_high, "1 min") 

        if self.BO_type == 'SHORT':
            is_trough = False
            my_low = 0.0
            (is_trough, my_low, _, _, _) = sdh.is_123_trough(sdh.Bars1M, ignore_outside_bars=True)
            if is_trough:
                self.rolling_low = my_low
                self.perfect_library[-1]["rolling_low"] = self.rolling_low
                if self.log_details: sender.Log(f"rolling high set at {self.rolling_low} @{candle_open_1m_mt4}")
                self.add_to_event_log(candle_open_1m_mt4,"Rolling Low Set", f"New Rolling Low, affects headroom", self.rolling_low, "1 min")   
                             
   

    # clear down the breakout to make it inactive and write the breakout log
    def clear_down_perfect_and_write_log(self, sender, time_now):
        if self.BO_active:
            self.BO_active = False
            #time_now_no_tz = time_now.replace(tzinfo=None)
            log_time = fusion_utils.get_times(time_now, 'us')['mt4']
            self.add_to_event_log(log_time,"Clearing down Perfect", f"Clear", 0, "event") 
            time_for_filename = fusion_utils.get_times(self.BO_pos4_time, 'us')['mt4']
            time_for_filename = fusion_utils.format_datetime_using_string(fusion_utils.get_candle_open_time(time_for_filename, ChartRes.res5M), "%Y.%m.%d %H_%M_%S")
            sender.write_breakout_log(self.event_log, self.symbol, time_for_filename, self.BO_type)
        else:
            # this could end up being called multiple times, but only do anything if perfect breakout is active
            pass


    def check_for_squeeze(self, sender, symbol, chartres, closeprice, timenow, ema9, ema45, ema135, ema200, candle_open_1m_mt4):
        # check whether we have a squeeze
        
        if self.BO_type == "LONG" and self.BO_active and self.BO_pullback1_breached:
            if self.ignore_200ema:
                if closeprice > ema9 and closeprice > ema45 and closeprice > ema135:
                    if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chartres} has triggered Squeeze")
                    self.squeeze_found = True
                    self.squeeze_status = "squeeze"
                    self.squeeze_time = timenow
                    self.squeeze_price = closeprice

                    self.perfect_library[-1]["squeeze_status"] = self.squeeze_status
                    self.perfect_library[-1]["status"] = "squeeze_but_no_entry"
                    self.perfect_library[-1]["squeeze_time"] = candle_open_1m_mt4
                    self.perfect_library[-1]["squeeze_price"] = self.squeeze_price
                    self.perfect_library[-1]["ema9"] = ema9
                    self.perfect_library[-1]["ema45"] = ema45
                    self.perfect_library[-1]["ema135"] = ema135
                    self.perfect_library[-1]["ema200"] = ""   
                    self.add_to_event_log(candle_open_1m_mt4,"Squeeze Test - PASSED", f"EMA9: {ema9} | EMA45: {ema45} | EMA135: {ema135} | Ignored 200EMA", self.squeeze_price, "1 min")           
                    return True
            else:
                if closeprice > ema9 and closeprice > ema45 and closeprice > ema135 and closeprice > ema200:
                    if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chartres} has triggered Squeeze")
                    self.squeeze_found = True
                    self.squeeze_status = "squeeze"
                    self.squeeze_time = timenow
                    self.squeeze_price = closeprice

                    self.perfect_library[-1]["squeeze_status"] = self.squeeze_status
                    self.perfect_library[-1]["status"] = "squeeze_but_no_entry"
                    self.perfect_library[-1]["squeeze_time"] = candle_open_1m_mt4
                    self.perfect_library[-1]["squeeze_price"] = self.squeeze_price
                    self.perfect_library[-1]["ema9"] = ema9
                    self.perfect_library[-1]["ema45"] = ema45
                    self.perfect_library[-1]["ema135"] = ema135
                    self.perfect_library[-1]["ema200"] = ema200
                    self.add_to_event_log(candle_open_1m_mt4,"Squeeze Test - PASSED", f"EMA9: {ema9} | EMA45: {ema45} | EMA135: {ema135} | EMA200: {ema200}", self.squeeze_price, "1 min")    
                    return True

        if self.BO_type == "SHORT" and self.BO_active and self.BO_pullback1_breached:
            if self.ignore_200ema:
                if closeprice < ema9 and closeprice < ema45 and closeprice < ema135:
                    if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chartres} has triggered Squeeze")
                    self.squeeze_found = True
                    self.squeeze_status = "squeeze"
                    self.squeeze_time = timenow
                    self.squeeze_price = closeprice

                    self.perfect_library[-1]["squeeze_status"] = self.squeeze_status
                    self.perfect_library[-1]["status"] = "squeeze_but_no_entry"
                    self.perfect_library[-1]["squeeze_time"] = candle_open_1m_mt4
                    self.perfect_library[-1]["squeeze_price"] = self.squeeze_price
                    self.perfect_library[-1]["ema9"] = ema9
                    self.perfect_library[-1]["ema45"] = ema45
                    self.perfect_library[-1]["ema135"] = ema135
                    self.perfect_library[-1]["ema200"] = ""
                    self.add_to_event_log(candle_open_1m_mt4,"Squeeze Test - PASSED", f"EMA9: {ema9} | EMA45: {ema45} | EMA135: {ema135} | Ignored 200EMA", self.squeeze_price, "1 min")     
                    return True
            else:
                if closeprice < ema9 and closeprice < ema45 and closeprice < ema135 and closeprice < ema200:
                    if self.log_details: sender.Log(f"{symbol} {self.BO_label} Breakout on {chartres} has triggered Squeeze")
                    self.squeeze_found = True
                    self.squeeze_status = "squeeze"
                    self.squeeze_time = timenow
                    self.squeeze_price = closeprice

                    self.perfect_library[-1]["squeeze_status"] = self.squeeze_status
                    self.perfect_library[-1]["status"] = "squeeze_but_no_entry"
                    self.perfect_library[-1]["squeeze_time"] = candle_open_1m_mt4
                    self.perfect_library[-1]["squeeze_price"] = self.squeeze_price
                    self.perfect_library[-1]["ema9"] = ema9
                    self.perfect_library[-1]["ema45"] = ema45
                    self.perfect_library[-1]["ema135"] = ema135
                    self.perfect_library[-1]["ema200"] = ema200
                    self.add_to_event_log(candle_open_1m_mt4,"Squeeze Test - PASSED", f"EMA9: {ema9} | EMA45: {ema45} | EMA135: {ema135} | EMA200: {ema200}", self.squeeze_price, "1 min")                        
                    return True

        #so this failed
        if self.ignore_200ema:
            self.add_to_event_log(candle_open_1m_mt4,"Squeeze Test - FAILED", f"Wait for next candle - EMA9: {ema9} | EMA45: {ema45} | EMA135: {ema135} | Ignored 200EMA", closeprice, "1 min")        
        else:
            self.add_to_event_log(candle_open_1m_mt4,"Squeeze Test - FAILED", f"Wait for next candle - EMA9: {ema9} | EMA45: {ema45} | EMA135: {ema135} | EMA200: {ema200}", closeprice, "1 min")        
        self.squeeze_found = False
        self.squeeze_status = "waiting"
        self.perfect_library[-1]["squeeze_status"] = self.squeeze_status
        self.perfect_library[-1]["status"] = "squeeze failed"

        return False


    def store_CHH(self, time_now):

        # if we have more than the set number for the total history, start dropping ones off the front of the list
        if len(self.perfect_library) > self.history_length:
            self.perfect_library.pop(0)

        self.builder_store["BO_label"] = self.BO_label                    
        self.builder_store["update_time"] = fusion_utils.get_times(time_now, 'us')['mt4']
        self.builder_store["pos1_label"] = "L"
        self.builder_store["pos1_price"] = self.BO_pos1_price
        self.builder_store["pos1_time"] = fusion_utils.get_times(self.BO_pos1_time, 'us')['mt4']
        self.builder_store["pos2_label"] = "H"
        self.builder_store["pos2_price"] = self.BO_pos2_price
        self.builder_store["pos2_time"] = fusion_utils.get_times(self.BO_pos2_time, 'us')['mt4']
        self.builder_store["pos3_label"] = "LL"
        self.builder_store["pos3_price"] = self.BO_pos3_price
        self.builder_store["pos3_time"] = fusion_utils.get_times(self.BO_pos3_time, 'us')['mt4']
        self.builder_store["pos4_label"] = "CHH"
        self.builder_store["pos4_price"] = self.BO_pos4_price
        self.builder_store["pos4_time"] = fusion_utils.get_times(self.BO_pos4_time, 'us')['mt4']
        self.builder_store["pullback1_price"] = self.BO_pullback1_price
        self.builder_store["EH_price"] = self.EH_price
        self.builder_store["EL_price"] = self.EL_price
        self.builder_store["TW"] = self.TW
        self.builder_store["status"] = self.BO_status
        self.builder_store["pullback1_hit"] = self.BO_pullback1_breached
        if self.BO_pullback1_breached_time != None:
            self.builder_store["BO_pullback1_breached_time"] = fusion_utils.get_times(self.BO_pullback1_breached_time, 'us')['mt4']
        if self.BO_hh_or_ll_breached_time != None:
            self.builder_store["hh_or_ll_time"] = self.BO_hh_or_ll_breached_time
        self.builder_store["hh_or_ll_hit"] = True
        self.builder_store["ignore_200ema"] = self.ignore_200ema
        self.builder_store["squeeze_status"] = self.squeeze_status
        if self.entry_time != None:
            self.builder_store["squeeze_time"] = fusion_utils.get_times(self.squeeze_time, 'us')['mt4']
        self.builder_store["squeeze_price"] = self.squeeze_price
        self.builder_store["enter_trade"] = self.enter_trade
        self.builder_store["reason_notes"] = self.reason_notes
        if self.entry_time != None:
            self.builder_store["entry_time"] = fusion_utils.get_times(self.entry_time, 'us')['mt4']
        self.builder_store["ema9"] = ""
        self.builder_store["ema45"] = ""
        self.builder_store["ema135"] = ""
        self.builder_store["ema200"] = ""
        self.builder_store["last_1m_peak"] = None           # these should only be set when we have a trade entry calc
        self.builder_store["last_1m_trough"] = None         # these should only be set when we have a trade entry calc
        self.builder_store["trend_5m"] = self.trend_5m
        self.builder_store["trend_1h"] = self.trend_1h
        self.builder_store["with_5m_trend"] = self.with_5m_trend
        self.builder_store["with_1h_trend"] = self.with_1h_trend
        self.builder_store["stop_pips"] = self.stop_pips
        self.builder_store["stop_price"] = self.stop_price
        self.builder_store["stop_comments"] = self.stop_comments              
        self.builder_store["take_profit_pips"] = self.take_profit_pips
        self.builder_store["take_profit_price"] = self.take_profit_price
        self.builder_store["take_profit_comments"] = self.take_profit_comments                
        self.builder_store["move_breakeven"] = self.move_breakeven
        self.builder_store["result_pips"] = self.result_pips
        self.builder_store["max_pips_profit"] = None
        self.builder_store["spread_pips"] = self.spread_pips
        self.builder_store["void_trade_high"] = self.void_trade_high
        self.builder_store["void_trade_low"] = self.void_trade_low
        self.builder_store["rolling_high"] = self.rolling_high
        self.builder_store["rolling_low"] = self.rolling_low
                   
        # now add a COPY of this dictionary object to the list
        self.perfect_library.append(deepcopy(self.builder_store))

    def store_CLL(self, time_now):

        # if we have more than the set number for the total history, start dropping ones off the front of the list
        if len(self.perfect_library) > self.history_length:
            self.perfect_library.pop(0)

        self.builder_store["BO_label"] = self.BO_label
        self.builder_store["update_time"] = fusion_utils.get_times(time_now, 'us')['mt4']
        self.builder_store["pos1_label"] = "H"
        self.builder_store["pos1_price"] = self.BO_pos1_price
        self.builder_store["pos1_time"] = fusion_utils.get_times(self.BO_pos1_time, 'us')['mt4']
        self.builder_store["pos2_label"] = "L"
        self.builder_store["pos2_price"] = self.BO_pos2_price
        self.builder_store["pos2_time"] = fusion_utils.get_times(self.BO_pos2_time, 'us')['mt4']
        self.builder_store["pos3_label"] = "HH"
        self.builder_store["pos3_price"] = self.BO_pos3_price
        self.builder_store["pos3_time"] = fusion_utils.get_times(self.BO_pos3_time, 'us')['mt4']
        self.builder_store["pos4_label"] = "CLL"
        self.builder_store["pos4_price"] = self.BO_pos4_price
        self.builder_store["pos4_time"] = fusion_utils.get_times(self.BO_pos4_time, 'us')['mt4']
        self.builder_store["pullback1_price"] = self.BO_pullback1_price
        self.builder_store["EH_price"] = self.EH_price
        self.builder_store["EL_price"] = self.EL_price
        self.builder_store["TW"] = self.TW
        self.builder_store["status"] = self.BO_status
        self.builder_store["pullback1_hit"] = self.BO_pullback1_breached
        if self.BO_pullback1_breached_time != None:
            self.builder_store["BO_pullback1_breached_time"] = fusion_utils.get_times(self.BO_pullback1_breached_time, 'us')['mt4']
        if self.BO_hh_or_ll_breached_time != None:
            self.builder_store["hh_or_ll_time"] = self.BO_hh_or_ll_breached_time
        self.builder_store["hh_or_ll_hit"] = True            
        self.builder_store["ignore_200ema"] = self.ignore_200ema
        self.builder_store["squeeze_status"] = self.squeeze_status
        if self.entry_time != None:
            self.builder_store["squeeze_time"] = fusion_utils.get_times(self.squeeze_time, 'us')['mt4']
        self.builder_store["squeeze_price"] = self.squeeze_price
        self.builder_store["enter_trade"] = self.enter_trade
        self.builder_store["reason_notes"] = self.reason_notes
        if self.entry_time != None:
            self.builder_store["entry_time"] = fusion_utils.get_times(self.entry_time, 'us')['mt4']
        self.builder_store["ema9"] = ""
        self.builder_store["ema45"] = ""
        self.builder_store["ema135"] = ""
        self.builder_store["ema200"] = ""
        self.builder_store["last_1m_peak"] = None       # these should only be set when we have a trade entry calc
        self.builder_store["last_1m_trough"] = None     # these should only be set when we have a trade entry calc
        self.builder_store["trend_5m"] = self.trend_5m
        self.builder_store["trend_1h"] = self.trend_1h
        self.builder_store["with_5m_trend"] = self.with_5m_trend
        self.builder_store["with_1h_trend"] = self.with_1h_trend
        self.builder_store["stop_price"] = self.stop_price
        self.builder_store["take_profit_pips"] = self.take_profit_pips
        self.builder_store["move_breakeven"] = self.move_breakeven
        self.builder_store["result_pips"] = self.result_pips
        self.builder_store["stop_pips"] = self.stop_pips
        self.builder_store["stop_price"] = self.stop_price
        self.builder_store["stop_comments"] = self.stop_comments              
        self.builder_store["take_profit_pips"] = self.take_profit_pips
        self.builder_store["take_profit_price"] = self.take_profit_price
        self.builder_store["take_profit_comments"] = self.take_profit_comments   
        self.builder_store["move_breakeven"] = self.move_breakeven
        self.builder_store["result_pips"] = self.result_pips
        self.builder_store["max_pips_profit"] = None
        self.builder_store["spread_pips"] = self.spread_pips          
        self.builder_store["void_trade_high"] = self.void_trade_high
        self.builder_store["void_trade_low"] = self.void_trade_low
        self.builder_store["rolling_high"] = self.rolling_high
        self.builder_store["rolling_low"] = self.rolling_low        

        # now add a COPY of this dictionary object to the list
        self.perfect_library.append(deepcopy(self.builder_store))

