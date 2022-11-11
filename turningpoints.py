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
from fusion_utils import *
#from symbolinfo import *
from dataclasses import dataclass
#endregion



class turning_point(object):
    def __init__(self, name, peak_or_trough, resolution):
       self.name = name
       self.peak_or_trough = peak_or_trough
       if peak_or_trough != 'PEAK' and peak_or_trough != 'TROUGH':
           raise TypeError("Must be a PEAK or a TROUGH when creating turning_point object")
       self.resolution = resolution
       #default values for initial setup
       self.TP_low = 0.0
       self.TP_high = 0.0
       self.TP_open = 0.0
       self.TP_close = 0.0

       self.wick_pips = 0.0
       self.bar_pips = 0.0
       self.wick_percent = 0.0
       
       self.start_time = None
       self.turn_time = None
       self.confirm_time = None
       self.last_check_time = None
       self.previous_check_time = None
       self.status = t_p_status.empty
       self.total_candles = 0
        
        
    def begin_turn(self, hi, lo, op, cl, candle_time, bar_colour, prev_lo_or_hi, prev_open, prev_bar_colour, pip_size):
        self.previous_check_time = self.last_check_time
        self.last_check_time = candle_time
        self.wick_pips = 0.0
        self.bar_pips = 0.0
        self.wick_percent = 0.0
        
        # Check Troughs first - price needs to be dropping to start
        if self.peak_or_trough == 'TROUGH':
            allow_go_ahead = True
            if bar_colour == RED and prev_bar_colour == GREEN and prev_open < cl:
                # this is not the start of a Trough turn as the candle before is GREEN and body is beneath this one, so will not look like a Trough on charts
                allow_go_ahead = False
            if bar_colour == RED and (abs(op - cl) / pip_size) > 1.0 and allow_go_ahead:        # and lo < prev_lo_or_hi:
                self.start_time = candle_time
                self.TP_low = lo
                self.TP_high = hi
                self.TP_open = op
                self.TP_close = cl
                self.total_candles = 1
                self.status = t_p_status.pre_turn
                self.wick_pips = round(abs(hi - lo) / pip_size, 2) - round(abs(op - cl) / pip_size, 2)
                self.bar_pips = round(abs(op - cl) / pip_size, 2)
                return True
                
        # Check Peaks - price needs to be rising to start
        if self.peak_or_trough == 'PEAK':
            allow_go_ahead = True
            if bar_colour == GREEN and prev_bar_colour == RED and prev_open > cl:
                # this is not the start of a Peak turn as the candle before is RED and body is ABOVE this one, so will not look like a Peak on charts
                allow_go_ahead = False
            if bar_colour == GREEN and (abs(op - cl) / pip_size) > 1.0 and allow_go_ahead:      # and hi > prev_lo_or_hi:
                self.start_time = candle_time
                self.TP_low = lo
                self.TP_high = hi
                self.TP_open = op
                self.TP_close = cl
                self.total_candles = 1
                self.wick_pips = round(abs(hi - lo) / pip_size, 2) - round(abs(op - cl) / pip_size, 2)
                self.bar_pips = round(abs(op - cl) / pip_size, 2)

                self.status = t_p_status.pre_turn
                return True
                
        return False
        
        
    def check_pre_turn(self, hi, lo, op, cl, candle_time, bar_colour, prev_lo_or_hi, pip_size):
        self.total_candles += 1
        self.previous_check_time = self.last_check_time
        self.last_check_time = candle_time
        self.bar_pips += round(abs(op - cl) / pip_size, 2)
        self.wick_pips += (round(abs(hi - lo) / pip_size, 2) - round(abs(op - cl) / pip_size, 2))

        
        if self.status != t_p_status.pre_turn:
            raise Exception("Can't check_pre_turn unless turning_point object is in pre_turn state")
        
        # Check Troughs first
        if self.peak_or_trough == 'TROUGH':
            # Check if we are turning
            if bar_colour == GREEN:
                # change status, store possible turning_point situation
                self.status = t_p_status.post_turn
                if self.turn_time == None:
                    self.turn_time = candle_time
                if lo < self.TP_low:
                    # the low was actually formed at the candle after the turn - not the turning candle itself
                    self.TP_low = lo
                    self.turn_time = candle_time
                if cl > self.TP_high:
                    # if the close of this GREEN bar is above the HIGH of the TROUGH CANDLE then we have confirmed the TROUGH LOW
                    self.status = t_p_status.confirmed
                    self.confirm_time = candle_time
                    if self.previous_check_time != None:
                        self.turn_time = self.previous_check_time
                    self.wick_percent = round((self.wick_pips / (self.bar_pips + self.wick_pips )) * 100, 2)
            else:
                # we have not turned yet, so check to see if this is a low candle than previously stored
                if lo <= self.TP_low:
                    self.TP_low = lo
                    self.TP_high = hi
                    self.TP_open = op
                    self.TP_close = cl   
                    self.turn_time = candle_time        # this isn't confirmed until there is a turn, but this becomes the TROUGH CANDLE
                
        # now check Peaks
        if self.peak_or_trough == 'PEAK':
            # Check if we are turning
            if bar_colour == RED:
                # change status, store possible turning_point situation
                self.status = t_p_status.post_turn
                if self.turn_time == None:
                    self.turn_time = candle_time
                if hi > self.TP_high:
                    # the high was actually formed at the candle after the turn - not the turning candle itself
                    self.TP_high = hi
                    self.turn_time = candle_time
                if cl < self.TP_low:
                    # if the close of this RED bar is below the LOW of the PEAK CANDLE then we have confirmed the PEAK HIGH
                    self.status = t_p_status.confirmed
                    self.confirm_time = candle_time
                    if self.previous_check_time != None:
                        self.turn_time = self.previous_check_time
                    self.wick_percent = round((self.wick_pips / (self.bar_pips + self.wick_pips )) * 100, 2)
            else:
                # we have not turned yet, so check to see if this is a high candle than previously stored
                if hi >= self.TP_high:
                    self.TP_low = lo
                    self.TP_high = hi
                    self.TP_open = op
                    self.TP_close = cl   
                    self.turn_time = candle_time        # this isn't confirmed until there is a turn, but this becomes the PEAK CANDLE
        
        return self.status


    def check_post_turn(self, hi, lo, op, cl, candle_time, bar_colour, prev_lo_or_hi, pip_size):
        self.total_candles += 1
        self.last_check_time = candle_time
        self.bar_pips += round(abs(op - cl) / pip_size, 2)
        self.wick_pips += (round(abs(hi - lo) / pip_size, 2) - round(abs(op - cl) / pip_size, 2))
        
        if self.status != t_p_status.post_turn:
            raise Exception("Can't check_post_turn unless turning_point object is in post_turn state")
        
        # Check Troughs first
        if self.peak_or_trough == 'TROUGH':
            if cl > self.TP_high:
                # if the close of this GREEN bar is above the HIGH of the TROUGH CANDLE then we have confirmed the TROUGH LOW
                self.status = t_p_status.confirmed
                self.wick_percent = round((self.wick_pips / (self.bar_pips + self.wick_pips )) * 100, 2)
                self.confirm_time = candle_time
                
        # now check Peaks
        if self.peak_or_trough == 'PEAK':
            if cl < self.TP_low:
                # if the close of this RED bar is below the LOW of the PEAK CANDLE then we have confirmed the PEAK HIGH
                self.status = t_p_status.confirmed
                self.wick_percent = round((self.wick_pips / (self.bar_pips + self.wick_pips )) * 100, 2)
                self.confirm_time = candle_time
        
        return self.status
        
        
''' Breakout Tracking Object
Contains the references to conditions that we need to look for'''
class breakout_tracker(object):
    
    def __init__(self, name, long_or_short, resolution):
        self.name = name
        self.long_or_short = long_or_short
        if long_or_short != 'LONG' and long_or_short != 'SHORT':
            raise TypeError("Must be LONG or SHORT when creating breakout_tracker object")
        self.resolution = resolution
        self.min_time_window = None
        self.min_chartRes_name = None   #10.8
        if resolution.value == ChartRes.res1H.value:
            self.min_time_window = timedelta(hours=1)
            self.min_chartRes_name = "1H"
        elif resolution.value == ChartRes.res30M.value:            
            self.min_time_window = timedelta(minutes=30)
            self.min_chartRes_name = "30M"
        elif resolution.value == ChartRes.res5M.value:
            self.min_time_window = timedelta(minutes=5)
            self.min_chartRes_name = "5M"            
        elif resolution.value == ChartRes.res1M.value:
            self.min_time_window = timedelta(minutes=1)
            self.min_chartRes_name = "1M"
        else:
            raise Exception("Unsupported breakout_tracker resolution")
        
        #default values for initial setup
        self.BT_low = 0.0
        self.BT_high = 0.0
        self.BT_lower_close = 0.0
        self.BT_higher_close = 0.0
        self.BT_lower_low = 0.0
        self.BT_higher_high = 0.0
        self.BT_pullback1 = 0.0
        self.BT_pullback2 = 0.0
        self.BT_pullback3 = 0.0
        self.BT_confirm1_time = None
        self.BT_confirm2_time = None
        self.BT_confirm3_time = None
        self.BT_confirm4_time = None
        self.BT_turn1_time = None
        self.BT_turn2_time = None
        self.BT_turn3_time = None
        self.BT_turn4_time = None
        self.total_candles = 0
        self.BT_PeakHigh = 0.0      #si 12.1
        self.BT_TroughLow = 0.0     #si 12.1
        self.lhs_count = -1
        self.rhs_count = -1

        self.long_bo_pullback_hunt_start = False
        self.long_bo_pb0_trigger = False
        self.long_bo_pb1_trigger = False
        self.long_bo_pb2_trigger = False
        self.long_bo_pb3_trigger = False
        self.long_bo_pb_breach_trigger = False
        self.long_bo_resume_trend_trigger = False
        self.long_bo_pb_min_price = 0.0
        self.long_bo_pb_max_price = 0.0
        self.long_bo_stop_check_time = None
        self.long_bo_pullback_timer_expired = False

        self.short_bo_pullback_hunt_start = False
        self.short_bo_pb0_trigger = False
        self.short_bo_pb1_trigger = False
        self.short_bo_pb2_trigger = False
        self.short_bo_pb3_trigger = False
        self.short_bo_pb_breach_trigger = False
        self.short_bo_resume_trend_trigger = False
        self.short_bo_pb_min_price = 0.0
        self.short_bo_pb_max_price = 0.0
        self.short_bo_stop_check_time = None
        self.short_bo_pullback_timer_expired = False
        
        self.clean_breakout_msg = "No breakout yet"
        self.clean_breakout = False

        self.wick_pips = 0.0
        self.bar_pips = 0.0
        self.wick_percent = 0.0
        self.pips_leg1 = 0.0
        self.pips_leg2 = 0.0
        self.pips_leg3 = 0.0
        
        self.last_check_time = None
        self.triggered_time = None
        self.searching = False
        self.triggered = False

        # this is used when we look for Perfect Brad entries - need to know if RHS was 123+R or 123+G
        self.ignore_200ema = False
        
        
    def clear(self):
        if self.long_or_short == 'LONG':
            self.__init__('BT LONG', 'LONG', self.resolution)
        if self.long_or_short == 'SHORT':
            self.__init__('BT SHORT', 'SHORT', self.resolution)
            
            
    def check_breakout(self, sender, symbol, TLs, PHs, pip_size, pip_threshold, logging=False, use_old_breakouts=True):
        # sender is the algorithm, so we can call logging functions etc
        
        # make sure we've got enough Troughs and Peaks before we start
        if len(TLs) < 2 or len(PHs) < 2:
            if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} Not enough Troughs and Peaks to look at yet")         # CG1 edited
            return False
        if TLs[-1].resolution != self.resolution or PHs[-1].resolution != self.resolution:
            if logging:  sender.Log(f"{symbol} Breakout checker resolution mismatch")
            return False
        
        self.last_check_time = sender.Time

        # If already looking for a Higher Close (HC) or Lower Close (LC) then clear down as we've found a new Turning Point.  Need to reassess.
        if self.searching == True:
            if not sender.IsWarmingUp and logging: sender.Log(f"{symbol} Existing breakout - was searching, new TP, clear down")
            #if not sender.IsWarmingUp: sender.Log(f"{symbol}Breakout {self.long_or_short} cleared by new Peak or Trough forming")
            self.clear()   
        
        # Look for a LONG BREAKOUT that hasn't started yet
        if self.long_or_short == 'LONG' and self.searching == False:
            if TLs[-1].confirm_time > PHs[-1].confirm_time and PHs[-1].confirm_time > TLs[-2].confirm_time and TLs[-2].confirm_time > PHs[-2].confirm_time:
                # now we know we have a Trough, Peak, Trough - check the heights
                if TLs[-1].TP_low < TLs[-2].TP_low:
                    # We have a Lower Low for the second trough - set the values we need to track the hunt for Higher Close
                    # set pip heights for Leg1 and Leg2 and make sure both of them are higher than the pip threshold
                    self.pips_leg1 = round(abs(PHs[-1].TP_high - TLs[-2].TP_low) / pip_size, 2)
                    self.pips_leg2 = round(abs(PHs[-1].TP_high - TLs[-1].TP_low) / pip_size, 2)
                    #sender.Log(f"LONGBreak - Leg1pips: {self.pips_leg1}  Leg2pips: {self.pips_leg2}")
                    if self.pips_leg1 >= pip_threshold and self.pips_leg2 >= pip_threshold:
                        # only set this as a valid series of Peaks and Troughs if the threshold is met
                        self.searching = True
                        self.BT_high = PHs[-1].TP_high
                        self.BT_lower_low = TLs[-1].TP_low
                        self.BT_confirm1_time = TLs[-2].confirm_time
                        self.BT_confirm2_time = PHs[-1].confirm_time
                        self.BT_confirm3_time = TLs[-1].confirm_time
                        self.BT_turn1_time = TLs[-2].turn_time
                        self.BT_turn2_time = PHs[-1].turn_time
                        self.BT_turn3_time = TLs[-1].turn_time
                        if not use_old_breakouts:
                            self.lhs_count = TLs[-1].lhs_continuous
                        if (self.BT_confirm3_time - self.BT_confirm1_time) <= (2 * self.min_time_window):
                            # Check if we created the Trough, Peak, Trough in literally 3 candles
                            if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} LONG breakout - found series in 3 candles - too tight - rejecting")        # CG1 edited
                            self.clear()
                            return False
                        self.total_candles = TLs[-2].total_candles + PHs[-1].total_candles + TLs[-1].total_candles
                        self.wick_pips = TLs[-2].wick_pips + PHs[-1].wick_pips + TLs[-1].wick_pips
                        self.bar_pips = TLs[-2].bar_pips + PHs[-1].bar_pips + TLs[-1].bar_pips
                        self.wick_percent = round((self.wick_pips / (self.bar_pips + self.wick_pips )) * 100, 2)
                        if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} Found LHLL potential - LONG breakout - searching for HC now at price: {self.BT_high} candles: {self.total_candles} wick percent {self.wick_percent}")   # CG1 edited
                        return True
        
        # Look for a SHORT BREAKOUT that hasn't started yet
        if self.long_or_short == 'SHORT' and self.searching == False:
            if PHs[-1].confirm_time > TLs[-1].confirm_time and TLs[-1].confirm_time > PHs[-2].confirm_time and PHs[-2].confirm_time > TLs[-2].confirm_time:
                # now we know we have a Peak, Trough, Peak - check the heights
                if PHs[-1].TP_high > PHs[-2].TP_high:
                    # We have a Higher High for the second Peak - set the values we need to track the hunt for Lower Close
                    # set pip heights for Leg1 and Leg2 and make sure both of them are higher than the pip threshold
                    self.pips_leg1 = round(abs(PHs[-2].TP_high - TLs[-1].TP_low) / pip_size, 2)
                    self.pips_leg2 = round(abs(PHs[-1].TP_high - TLs[-1].TP_low) / pip_size, 2)
                    #sender.Log(f"SHORTBreak - Leg1pips: {self.pips_leg1}  Leg2pips: {self.pips_leg2}")
                    if self.pips_leg1 >= pip_threshold and self.pips_leg2 >= pip_threshold:
                        # only set this as a valid series of Peaks and Troughs if the threshold is met
                        self.searching = True
                        self.BT_low = TLs[-1].TP_low
                        self.BT_higher_high = PHs[-1].TP_high
                        self.BT_confirm1_time = PHs[-2].confirm_time
                        self.BT_confirm2_time = TLs[-1].confirm_time
                        self.BT_confirm3_time = PHs[-1].confirm_time
                        self.BT_turn1_time = PHs[-2].turn_time
                        self.BT_turn2_time = TLs[-1].turn_time
                        self.BT_turn3_time = PHs[-1].turn_time
                        if not use_old_breakouts:
                            self.lhs_count = PHs[-1].lhs_continuous
                        if (self.BT_confirm3_time - self.BT_confirm1_time) <= (2 * self.min_time_window):
                            # Check if we created the Peak, Trough, Peak in literally 3 candles
                            if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} SHORT breakout - found series in 3 candles - too tight - rejecting")       # CG1 edited
                            self.clear()
                            return False
                        self.total_candles = PHs[-2].total_candles + TLs[-1].total_candles + PHs[-1].total_candles
                        self.wick_pips = PHs[-2].wick_pips + TLs[-1].wick_pips + PHs[-1].wick_pips
                        self.bar_pips = PHs[-2].bar_pips + TLs[-1].bar_pips + PHs[-1].bar_pips
                        self.wick_percent = round((self.wick_pips / (self.bar_pips + self.wick_pips )) * 100, 2)
                        if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} Found HLHH potential - SHORT breakout - searching for LC now at price: {self.BT_low} candles: {self.total_candles} wick percent {self.wick_percent}")   # CG1 edited
                        return True
                
        return False


    def make_ready_breakout(self, sender, symbol, direction, bar, TLs, PHs, pip_size, pip_threshold, logging=False):
        if self.long_or_short == 'LONG' and direction != StratDirection.Long:
            if logging: sender.Log(f"{symbol} - make_ready_breakout - direction does not match container - returning")
            return False
        if self.long_or_short == 'SHORT' and direction != StratDirection.Short:
            if logging: sender.Log(f"{symbol} - make_ready_breakout - direction does not match container - returning")
            return False

        if TLs[-1].resolution != self.resolution or PHs[-1].resolution != self.resolution:
            if logging:  sender.Log(f"{symbol} Breakout checker resolution mismatch")
            return False
        
        # we are forcing this one, to use it immediately - so clear it first
        self.clear()

        self.last_check_time = sender.Time
        self.BT_confirm4_time = self.last_check_time
        
        # Look for a LONG BREAKOUT that we know has been breached -- set everything immediately
        if self.long_or_short == 'LONG':
            # We have a Lower Low for the second trough - set the values we need to track the hunt for Higher Close
            # set pip heights for Leg1 and Leg2 and make sure both of them are higher than the pip threshold
            self.pips_leg1 = round(abs(PHs[-1].TP_high - TLs[-2].TP_low) / pip_size, 2)
            self.pips_leg2 = round(abs(PHs[-1].TP_high - TLs[-1].TP_low) / pip_size, 2)
            #sender.Log(f"LONGBreak - Leg1pips: {self.pips_leg1}  Leg2pips: {self.pips_leg2}")
            if self.pips_leg1 >= pip_threshold and self.pips_leg2 >= pip_threshold:
                # only set this as a valid series of Peaks and Troughs if the threshold is met
                self.triggered = True
                self.BT_high = PHs[-1].TP_high
                self.BT_lower_low = TLs[-1].TP_low
                self.BT_confirm1_time = TLs[-2].confirm_time
                self.BT_confirm2_time = PHs[-1].confirm_time
                self.BT_confirm3_time = TLs[-1].confirm_time
                self.BT_turn1_time = TLs[-2].turn_time
                self.BT_turn2_time = PHs[-1].turn_time
                self.BT_turn3_time = TLs[-1].turn_time
                
                self.lhs_count = TLs[-1].lhs_continuous
                if (self.BT_confirm3_time - self.BT_confirm1_time) <= (2 * self.min_time_window):
                    # Check if we created the Trough, Peak, Trough in literally 3 candles
                    if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} LONG breakout - found series in 3 candles - too tight - rejecting")        # CG1 edited
                    self.clear()
                    return False
                self.total_candles = TLs[-2].total_candles + PHs[-1].total_candles + TLs[-1].total_candles
                self.wick_pips = TLs[-2].wick_pips + PHs[-1].wick_pips + TLs[-1].wick_pips
                self.bar_pips = TLs[-2].bar_pips + PHs[-1].bar_pips + TLs[-1].bar_pips
                self.wick_percent = round((self.wick_pips / (self.bar_pips + self.wick_pips )) * 100, 2)

                self.triggered_time = self.last_check_time
                self.BT_higher_close = bar.Bid.Close
                self.pips_leg3 = round(abs(bar.Bid.Close - TLs[-1].TP_low) / pip_size, 2)
                
                TL = TLs[-2].TP_low
                PH = PHs[-1].TP_high
                LL = TLs[-1].TP_low
                self.BT_higher_high = 0.0 
                self.BT_pullback1 = PHs[-1].TP_high
                self.BT_pullback2 = PHs[-1].TP_close
                self.BT_pullback3 = TLs[-1].TP_open
                self.BT_PeakHigh = PH      #si 12.1
                self.BT_TroughLow = TL     #si 12.1
                return True
        
        # Look for a SHORT BREAKOUT that we know has been breached -- set everything immediately
        if self.long_or_short == 'SHORT':
            # We have a Higher High for the second Peak - set the values we need to track the hunt for Lower Close
            # set pip heights for Leg1 and Leg2 and make sure both of them are higher than the pip threshold
            self.pips_leg1 = round(abs(PHs[-2].TP_high - TLs[-1].TP_low) / pip_size, 2)
            self.pips_leg2 = round(abs(PHs[-1].TP_high - TLs[-1].TP_low) / pip_size, 2)
            #sender.Log(f"SHORTBreak - Leg1pips: {self.pips_leg1}  Leg2pips: {self.pips_leg2}")
            if self.pips_leg1 >= pip_threshold and self.pips_leg2 >= pip_threshold:
                # only set this as a valid series of Peaks and Troughs if the threshold is met
                self.triggered = True
                self.BT_low = TLs[-1].TP_low
                self.BT_higher_high = PHs[-1].TP_high
                self.BT_confirm1_time = PHs[-2].confirm_time
                self.BT_confirm2_time = TLs[-1].confirm_time
                self.BT_confirm3_time = PHs[-1].confirm_time
                self.BT_turn1_time = PHs[-2].turn_time
                self.BT_turn2_time = TLs[-1].turn_time
                self.BT_turn3_time = PHs[-1].turn_time
                
                self.lhs_count = PHs[-1].lhs_continuous
                if (self.BT_confirm3_time - self.BT_confirm1_time) <= (2 * self.min_time_window):
                    # Check if we created the Peak, Trough, Peak in literally 3 candles
                    if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} SHORT breakout - found series in 3 candles - too tight - rejecting")       # CG1 edited
                    self.clear()
                    return False
                self.total_candles = PHs[-2].total_candles + TLs[-1].total_candles + PHs[-1].total_candles
                self.wick_pips = PHs[-2].wick_pips + TLs[-1].wick_pips + PHs[-1].wick_pips
                self.bar_pips = PHs[-2].bar_pips + TLs[-1].bar_pips + PHs[-1].bar_pips
                self.wick_percent = round((self.wick_pips / (self.bar_pips + self.wick_pips )) * 100, 2)

                self.triggered_time = self.last_check_time
                self.BT_lower_close = bar.Bid.Close
                self.pips_leg3 = round(abs(PHs[-1].TP_high - bar.Bid.Close) / pip_size, 2)

                PH = PHs[-2].TP_high
                TL = TLs[-1].TP_low
                HH = PHs[-1].TP_high
                self.BT_higher_high = PHs[-1].TP_high
                self.BT_lower_low = 0.0
                self.BT_pullback1 = TLs[-1].TP_low
                self.BT_pullback2 = TLs[-1].TP_close
                self.BT_pullback3 = PHs[-1].TP_open
                self.BT_PeakHigh = PH      #si 12.1
                self.BT_TroughLow = TL     #si 12.1            
                return True

        return False

        
        
    def check_breakout_breached(self, sender, symbol, TLs, PHs, bar, bar_colour, daily_trading_range, high_24H, low_24H, pip_size, logging=False):
        # sender is the algorithm, so we can call logging functions etc
        
        # make sure we've got enough Troughs and Peaks before we start
        # TODO: breakout override needs removing - and moving elsewhere...could stop us seeing breakouts otherwise - where in codebase is this?
        if not self.searching:
            if logging: sender.Log(f"{symbol} Do not call check_breakout_breached if self.searching is not True - i.e. we are looking for the HH or LL to be met")
            return False

        if TLs[-1].resolution != self.resolution or PHs[-1].resolution != self.resolution:
            if logging:  sender.Log(f"{symbol} Breakout checker resolution mismatch")
            return False
        if sender.IsWarmingUp:
            # we do not want to actually mark a CHH or CLL as having been found while warming up - this should only happen after startup
            return False

        self.last_check_time = sender.Time
        self.BT_confirm4_time = self.last_check_time
        
        daily_trading_pips = round(daily_trading_range / pip_size, 2)
        
        # Look for a LONG BREAKOUT that has reached a Higher Close
        if self.long_or_short == 'LONG' and self.searching and not self.triggered and bar_colour == GREEN:
            if bar.Bid.Close > self.BT_high:
                # the bar we've been passed has a Higher Close than the High we are looking for
                self.triggered = True
                self.triggered_time = self.last_check_time
                self.BT_higher_close = bar.Bid.Close
                self.pips_leg3 = round(abs(bar.Bid.Close - TLs[-1].TP_low) / pip_size, 2)
                do_check = True
                if self.BT_confirm4_time is None or self.BT_turn2_time is None:
                    do_check = False
                if do_check and ((self.BT_confirm4_time - self.BT_confirm2_time) <= (2 * self.min_time_window)):
                    # Check if we created the Trough, Peak, Trough in literally 3 candles
                    turn_diff = self.BT_confirm4_time - self.BT_turn2_time
                    if (turn_diff) <= (1 * self.min_time_window):
                        if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} LONG breakout {self.resolution} - found series in 3 candles - too tight - rejecting.  Turn Difference: {turn_diff}")       # CG1 edited
                        self.clear()
                        return False
                TL = TLs[-2].TP_low
                PH = PHs[-1].TP_high
                LL = TLs[-1].TP_low
                self.BT_lower_low = TLs[-1].TP_low
                self.BT_higher_high = PHs[-2].TP_high #si 12.1  - CG?  there is not really a higher high in the LONG PATTERN, so this doesn't make sense? Si, yes for breakout calc in entry mgt
                self.BT_pullback1 = PHs[-1].TP_high
                self.BT_pullback2 = PHs[-1].TP_close
                self.BT_pullback3 = TLs[-1].TP_open
                self.BT_PeakHigh = PH      #si 12.1
                self.BT_TroughLow = TL     #si 12.1
                if logging: sender.LogExtra(f"{symbol} LONG breakout {self.resolution} - Higher Close found : {bar.Bid.Close} TL: {TL} PH: {PH} LL: {LL} candles: {self.total_candles}  wick percent {self.wick_percent}  Leg1pips: {self.pips_leg1}  Leg2pips: {self.pips_leg2}  Leg3pips: {self.pips_leg3} ATRpips: {daily_trading_pips} 24Hhigh: {high_24H} 24Hlow: {low_24H}", f"{symbol} LONG breakout {self.resolution}")
                #if logging: sender.LogFormatted(f"Version: {sender.ModeName} | {symbol} LONG Breakout {self.min_chartRes_name} - Higher Close found <br> TL: {TL} <br> LL: {LL} <br> CHH {self.BT_higher_close} <br><b> PH: {PH} </b><br>", f"{symbol} LONG BO - {self.min_chartRes_name}")
                #sender.Debug(f"Version: {sender.ModeName} | {symbol} LONG Breakout {self.min_chartRes_name} - Higher Close found <br> TL: {TL} <br> LL: {LL} <br> CHH {self.BT_higher_close} <br><b> PH: {PH} </b><br>", f"{symbol} LONG BO - {self.min_chartRes_name}")
                return True
                
        # Look for a SHORT BREAKOUT that has reached a Lower Close
        if self.long_or_short == 'SHORT' and self.searching and not self.triggered and bar_colour == RED:
            if bar.Bid.Close < self.BT_low:
                # the bar we've been passed has a Lower Close than the Low we are looking for
                self.triggered = True
                self.triggered_time = self.last_check_time
                self.BT_lower_close = bar.Bid.Close
                self.pips_leg3 = round(abs(PHs[-1].TP_high - bar.Bid.Close) / pip_size, 2)
                do_check = True
                if self.BT_confirm4_time is None or self.BT_turn2_time is None:
                    do_check = False
                if do_check and ((self.BT_confirm4_time - self.BT_confirm2_time) <= (2 * self.min_time_window)):
                    # Check if we created the Peak, Trough, Peak in literally 3 candles
                    turn_diff = self.BT_confirm4_time - self.BT_turn2_time
                    if (turn_diff) <= (1 * self.min_time_window):
                        if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} SHORT breakout {self.resolution} - found series in 3 candles - too tight - rejecting.  Turn Difference: {turn_diff}")  # CG1 edited
                        self.clear()
                        return False
                PH = PHs[-2].TP_high
                TL = TLs[-1].TP_low
                HH = PHs[-1].TP_high
                self.BT_higher_high = PHs[-1].TP_high
                self.BT_lower_low = TLs[-2].TP_low #si 12.1  - CG? there is not really a lower low in the SHORT pattern, so this doesn't make sense? Si, yes we use it in points / entry - breakout distance for one
                self.BT_pullback1 = TLs[-1].TP_low
                self.BT_pullback2 = TLs[-1].TP_close
                self.BT_pullback3 = PHs[-1].TP_open
                self.BT_PeakHigh = PH      #si 12.1
                self.BT_TroughLow = TL     #si 12.1                
                if logging: sender.LogExtra(f"{symbol} SHORT breakout {self.resolution} - Lower Close found : {bar.Bid.Close} PH: {PH} TL: {TL} HH: {HH} candles: {self.total_candles}  wick percent {self.wick_percent}  Leg1pips: {self.pips_leg1}  Leg2pips: {self.pips_leg2}  Leg3pips: {self.pips_leg3} ATRpips: {daily_trading_pips} 24Hhigh: {high_24H} 24Hlow: {low_24H}", f"{symbol} SHORT breakout {self.resolution}")
                #if logging: sender.LogFormatted(f"Version: {sender.ModeName} | {symbol} SHORT breakout {self.min_chartRes_name} - Lower Close Found<br> PH: {PH} <br> HH: {HH} <br> CLL {self.BT_lower_close} <br><b> TL: {TL} </b><br>", f"{symbol} SHORT BO - {self.min_chartRes_name}")
                #sender.Debug(f"Version: {sender.ModeName} | {symbol} SHORT breakout {self.min_chartRes_name} - Lower Close Found<br> PH: {PH} <br> HH: {HH} <br> CLL {self.BT_lower_close} <br><b> TL: {TL} </b><br>", f"{symbol} SHORT BO - {self.min_chartRes_name}")
                return True
                
        
        return False

    # Function to check if a breakout that has just triggered CHH or CLL was formed with clean 123G or 123R movements in the bar formations
    def look_for_clean_breakout(self, sender, symbol, sd, chartres, use_old_breakouts=True):
        my_bars = None
        my_colours = None
        if chartres == ChartRes.res1H:
            my_bars = sd.Bars1H
            my_colours = sd.Bars1HColour
        elif chartres == ChartRes.res5M:
            my_bars = sd.Bars5M
            my_colours = sd.Bars5MColour
        elif chartres == ChartRes.res30M:
            my_bars = sd.Bars30M
            my_colours = sd.Bars30MColour
        else:
            sender.Log(f"{symbol} look_for_clean_breakout - chartres {chartres} not recognised")

        if use_old_breakouts:
            # check the LONG breakout for clean 123G or 123R movements
            if self.long_or_short == 'LONG' and self.triggered and self.searching:
                my_H_time = self.BT_turn2_time
                my_LL_time = self.BT_turn3_time
                my_CHH_time = self.BT_confirm4_time
                if my_H_time == None or my_LL_time == None:
                    self.clean_breakout_msg = "Times not set on turns for CHH creation - ERROR"
                    self.clean_breakout = False
                    return False
                count_greens = 0
                stop_early = False
                count_reds = 0

                #SI
                count_greens = 0          
                for i in range(my_bars.Count-1, 0, -1):
                    if my_bars[i].EndTime >= my_LL_time and my_bars[i].EndTime <= my_CHH_time :       # make sure we're looking backwards from the CLL bar
                        if my_colours[i] == GREEN:
                            count_greens += 1
                            if count_greens == 3 :
                                    break
                        else:                  
                            break  


                # now loop for the REDS
                for i in range(0, my_bars.Count):
                    if my_bars[i].EndTime <= my_LL_time and not stop_early or my_bars[i].EndTime < my_LL_time and stop_early:       # make sure we're looking backwards from the CHH bar
                        if my_colours[i] == RED:
                            count_reds += 1
                            if count_reds >= 3 or my_bars[i].EndTime < my_H_time:
                                # we have at least a 123R
                                break
                        elif my_colours[i] == GREEN:
                            count_reds = 0          # reset the counter
                            #break
                if count_greens >= 3 or count_reds >= 3:
                    clean_msg = ""
                    if count_greens >= 3:
                        clean_msg += "RHS: 123G "
                        self.ignore_200ema = True
                    if count_reds >= 3:
                        clean_msg += "LHS: 123R "
                    self.clean_breakout_msg = clean_msg
                    self.clean_breakout = True
                    return True

            # check the SHORT breakout for clean 123G or 123R movements
            if self.long_or_short == 'SHORT' and self.triggered and self.searching:
                my_L_time = self.BT_turn2_time
                my_HH_time = self.BT_turn3_time
                my_CLL_time = self.BT_confirm4_time
                if my_L_time == None or my_HH_time == None:
                    self.clean_breakout_msg = "Times not set on turns for CLL creation - ERROR"
                    self.clean_breakout = False
                    return False
                count_reds = 0
                stop_early = False
                count_greens = 0
                # loop for the REDS first

                #SI loop backwards through the bars starting at the HH bar
                count_reds = 0          
                for i in range(my_bars.Count-1, 0, -1):
                    if my_bars[i].EndTime >= my_HH_time and my_bars[i].EndTime <= my_CLL_time :       # make sure we're looking backwards from the CLL bar
                        if my_colours[i] == RED:
                            count_reds += 1
                            if count_reds == 3 :
                                    break
                        else:                  
                            break  

                # now loop for the GREENS
                for i in range(0, my_bars.Count):
                    if my_bars[i].EndTime <= my_HH_time and not stop_early or my_bars[i].EndTime < my_HH_time and stop_early:       # make sure we're looking backwards from the CLL bar
                        if my_colours[i] == GREEN:
                            count_greens += 1
                            if count_greens >= 3 or my_bars[i].EndTime < my_L_time:
                                # we have at least a 123G
                                break
                        elif my_colours[i] == RED:
                            count_greens = 0        #reset the counter
                            #break
                if count_greens >= 3 or count_reds >= 3:
                    clean_msg = ""
                    if count_reds >= 3:
                        clean_msg += "RHS: 123R "
                        self.ignore_200ema = True
                    if count_greens >= 3:
                        clean_msg += "LHS: 123G "
                    self.clean_breakout_msg = clean_msg
                    self.clean_breakout = True
                    return True

            self.clean_breakout_msg = "Neither 123G or 123R found"
            self.clean_breakout = False
            return False
        
        else:
            # Now we are using the new form of breakout checking
            # check the LONG breakout for clean 123G or 123R movements
            if self.long_or_short == 'LONG' and self.triggered:
                my_H_time = self.BT_turn2_time
                my_LL_time = self.BT_turn3_time
                my_CHH_time = self.BT_confirm4_time
                if my_H_time == None or my_LL_time == None:
                    self.clean_breakout_msg = "Times not set on turns for CHH creation - ERROR"
                    self.clean_breakout = False
                    return False
                count_greens = 0
                start_rhs = 0
                for i in range(0, my_bars.Count-1):
                    if my_bars[i].EndTime <= my_LL_time :       # figure out where middle bar is
                        if my_colours[i] == GREEN:
                            start_rhs = i
                            break
                        else:    
                            start_rhs = i-1
                            break
                for i in range(start_rhs, -1, -1):
                    if my_colours[i] == GREEN:
                        count_greens += 1
                        #if count_greens == 3 :
                        #        break
                    else:                  
                        break  
                self.rhs_count = count_greens

                if self.lhs_count != -1:
                    count_reds = self.lhs_count
                #sender.Log(f"{symbol} look_for_clean LONG LHS - chartres {chartres} LHS count {self.lhs_count} RHS count {self.rhs_count} Time: {fusion_utils.get_times(sender.Time, 'us')['mt4']}")
                #sender.Log(f"CHHTime: {fusion_utils.get_times(my_CHH_time, 'us')['mt4']}, LLTime: {fusion_utils.get_times(my_LL_time, 'us')['mt4']} Start RHS: {start_rhs} CHH: {self.BT_higher_close}")
                
                if count_greens >= 3 or count_reds >= 3:
                    clean_msg = ""
                    if count_greens >= 3:
                        clean_msg += "RHS: 123G "
                        self.ignore_200ema = True
                    if count_reds >= 3:
                        clean_msg += "LHS: 123R "
                    self.clean_breakout_msg = clean_msg
                    self.clean_breakout = True
                    return True

            # check the SHORT breakout for clean 123G or 123R movements
            if self.long_or_short == 'SHORT' and self.triggered:
                my_L_time = self.BT_turn2_time
                my_HH_time = self.BT_turn3_time
                my_CLL_time = self.BT_confirm4_time
                if my_L_time == None or my_HH_time == None:
                    self.clean_breakout_msg = "Times not set on turns for CLL creation - ERROR"
                    self.clean_breakout = False
                    return False
                count_reds = 0
                start_rhs = 0
                for i in range(0, my_bars.Count-1):
                    if my_bars[i].EndTime <= my_HH_time :       # figure out where middle bar is
                        if my_colours[i] == RED:
                            start_rhs = i
                            break
                        else:    
                            start_rhs = i-1
                            break
                for i in range(start_rhs, -1, -1):
                    if my_colours[i] == RED:
                        count_reds += 1
                        #if count_reds == 3 :
                        #        break
                    else:                  
                        break  
                self.rhs_count = count_reds

                if self.lhs_count != -1:
                    count_greens = self.lhs_count
                #sender.Log(f"{symbol} look_for_clean SHORT LHS - chartres {chartres} LHS count {self.lhs_count} RHS count {self.rhs_count} Time: {fusion_utils.get_times(sender.Time, 'us')['mt4']}")
                #sender.Log(f"CLLTime: {fusion_utils.get_times(my_CLL_time, 'us')['mt4']}, HHTime: {fusion_utils.get_times(my_HH_time, 'us')['mt4']} Start RHS: {start_rhs} CLL: {self.BT_lower_close}")        
                
                if count_greens >= 3 or count_reds >= 3:
                    clean_msg = ""
                    if count_reds >= 3:
                        clean_msg += "RHS: 123R "
                        self.ignore_200ema = True
                    if count_greens >= 3:
                        clean_msg += "LHS: 123G "
                    self.clean_breakout_msg = clean_msg
                    self.clean_breakout = True
                    return True
            
            return False



    def check_breakout_pullback(self, sender, symbol, bid_price_now, pip_size, time_for_pullback, logging=False):
        # sender is the algorithm, so we can call logging functions etc
        
        if self.long_or_short == 'LONG':
            # check if we are just starting a fresh hunt for a pullback, set time to look for pullbacks - after this, we stop
            if not self.long_bo_pullback_hunt_start:
                self.long_bo_stop_check_time = sender.Time + time_for_pullback
                self.long_bo_pullback_hunt_start = True

            # set min and max prices initially
            if self.long_bo_pb_min_price == 0.0:
                self.long_bo_pb_min_price = bid_price_now
            if self.long_bo_pb_max_price == 0.0:
                self.long_bo_pb_max_price = bid_price_now

            if sender.Time > self.long_bo_stop_check_time and not self.long_bo_pullback_timer_expired:
                # make sure to only check for the time we need to
                self.long_bo_pullback_timer_expired = True
                if logging: sender.Log(f"{symbol} expired timer for Long pullback check - Price: {bid_price_now} Triggers [CHH:{self.long_bo_pb0_trigger}  pb1:{self.long_bo_pb1_trigger}  pb2:{self.long_bo_pb2_trigger}  pb3:{self.long_bo_pb3_trigger} LL:{self.long_bo_pb_breach_trigger}]")
                self.clear()
                return False

            if not self.long_bo_pullback_timer_expired:
                # only make changes if the timer has not expired yet
                if bid_price_now < self.long_bo_pb_min_price:
                    self.long_bo_pb_min_price = bid_price_now
                if bid_price_now > self.long_bo_pb_max_price:
                    self.long_bo_pb_max_price = bid_price_now

                if bid_price_now < self.BT_higher_close:
                    self.long_bo_pb0_trigger = True
                if bid_price_now < self.BT_pullback1:
                    self.long_bo_pb1_trigger = True
                if bid_price_now < self.BT_pullback2:
                    self.long_bo_pb2_trigger = True
                if bid_price_now < self.BT_pullback3:
                    self.long_bo_pb3_trigger = True
                if bid_price_now < self.BT_lower_low and not self.long_bo_pb_breach_trigger:
                    self.long_bo_pb_breach_trigger = True
                    if logging: sender.Log(f"{symbol} Long Breakout, Pullback fell below Lower Low - Price: {bid_price_now}")

                # now that we've checked the various pullback price levels - check to see if we have Resumed the Trend, having breached one of the pullbacks, but not gone below Lower Low
                if bid_price_now > self.BT_higher_close and self.long_bo_pb1_trigger and not self.long_bo_pb_breach_trigger and not self.long_bo_resume_trend_trigger:
                    # this will not find ones which only come back part of the way - need to add a level to check for on that.  For now we are PB1 only
                    self.long_bo_resume_trend_trigger = True
                    if logging: sender.Log(f"{symbol} Long Breakout, Resume Trend after Pullback - Price: {bid_price_now} Triggers [CHH:{self.long_bo_pb0_trigger}  pb1:{self.long_bo_pb1_trigger}  pb2:{self.long_bo_pb2_trigger}  pb3:{self.long_bo_pb3_trigger}]")       

        if self.long_or_short == 'SHORT':
            # check if we are just starting a fresh hunt for a pullback, set time to look for pullbacks - after this, we stop
            if not self.short_bo_pullback_hunt_start:
                self.short_bo_stop_check_time = sender.Time + time_for_pullback
                self.short_bo_pullback_hunt_start = True

            # set min and max prices initially
            if self.short_bo_pb_min_price == 0.0:
                self.short_bo_pb_min_price = bid_price_now
            if self.short_bo_pb_max_price == 0.0:
                self.short_bo_pb_max_price = bid_price_now

            if sender.Time > self.short_bo_stop_check_time and not self.short_bo_pullback_timer_expired:
                # make sure to only check for the time we need to
                self.short_bo_pullback_timer_expired = True
                if logging: sender.Log(f"{symbol} expired timer for Short pullback check - Price: {bid_price_now} Triggers [CHH:{self.short_bo_pb0_trigger}  pb1:{self.short_bo_pb1_trigger}  pb2:{self.short_bo_pb2_trigger}  pb3:{self.short_bo_pb3_trigger} LL:{self.short_bo_pb_breach_trigger}]")
                self.clear()
                return False

            if not self.short_bo_pullback_timer_expired:
                # only make changes if the timer has not expired yet
                if bid_price_now < self.short_bo_pb_min_price:
                    self.short_bo_pb_min_price = bid_price_now
                if bid_price_now > self.short_bo_pb_max_price:
                    self.short_bo_pb_max_price = bid_price_now

                if bid_price_now > self.BT_lower_close:
                    self.short_bo_pb0_trigger = True
                if bid_price_now > self.BT_pullback1:
                    self.short_bo_pb1_trigger = True
                if bid_price_now > self.BT_pullback2:
                    self.short_bo_pb2_trigger = True
                if bid_price_now > self.BT_pullback3:
                    self.short_bo_pb3_trigger = True
                if bid_price_now > self.BT_higher_high and not self.short_bo_pb_breach_trigger:
                    self.short_bo_pb_breach_trigger = True
                    if logging: sender.Log(f"{symbol} short Breakout, Pullback rose above Higher High - Price: {bid_price_now}")

                # now that we've checked the various pullback price levels - check to see if we have Resumed the Trend, having breached one of the pullbacks, but not gone above Higher High
                if bid_price_now < self.BT_lower_close and self.short_bo_pb1_trigger and not self.short_bo_pb_breach_trigger and not self.short_bo_resume_trend_trigger:
                    # this will not find ones which only come back part of the way - need to add a level to check for on that.  For now we are PB1 only
                    self.short_bo_resume_trend_trigger = True
                    if logging: sender.Log(f"{symbol} short Breakout, Resume Trend after Pullback - Price: {bid_price_now} Triggers [CHH:{self.short_bo_pb0_trigger}  pb1:{self.short_bo_pb1_trigger}  pb2:{self.short_bo_pb2_trigger}  pb3:{self.short_bo_pb3_trigger}]")   

        return True
 
