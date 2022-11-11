
#region imports
from AlgorithmImports import *
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
from price_tracker import *
from session_boxes import *
from dataclasses import dataclass
from symbolinfo import *
from fusion_utils import *
from QuantConnect import Market
from io import StringIO
import pandas as pd
#endregion

'''Contains a bunch of helper functions for signing up the consolidators - in an attempt to save space in the main file'''

class QCalgo_consolidators(QCAlgorithm):

    # create a custom 24hr handler so we close at 5pm
    def CustomBarPeriod24H(self, dt):
        period = timedelta(days=1)
        start = dt.replace(hour=17, minute=0, second=0)
        if start > dt:
            start -= period
        return CalendarInfo(start, period)
        
    
    # create a custom 4hr handler so we close at 1am, 5am, 9am, 1pm, 5pm, 9pm
    def CustomBarPeriod4H(self, dt):
        period = timedelta(hours=4)
        newhour = ((dt.hour // 4) * 4) + 1
        start = dt.replace(hour=newhour, minute=0, second=0)
        if start > dt:
            start -= timedelta(days=1)
        return CalendarInfo(start, period)
    
    
    # Fires for all the 1min consolidated bars
    def OnDataConsolidated1M(self, sender, bar):
        # The EMA needs updating before we add the updated value to the rollingwindow structure
        # should the EMA be updated with the 'average of the open and close?'
        sdh = self.symbolInfo[bar.Symbol.Value]

        sdh.EMA1M.Update(bar.Time, bar.Bid.Close)              # Update the EMA 
        sdh.emaWindow1M.Add(sdh.EMA1M.Current)      # Add new EMA to rolling window

        sdh.EMA1M_45.Update(bar.Time, bar.Bid.Close)              # Update the EMA 
        sdh.emaWindow1M_45.Add(sdh.EMA1M_45.Current)      # Add new EMA to rolling window
        sdh.EMA1M_135.Update(bar.Time, bar.Bid.Close)              # Update the EMA 
        sdh.emaWindow1M_135.Add(sdh.EMA1M_135.Current)      # Add new EMA to rolling window
        sdh.EMA1M_200.Update(bar.Time, bar.Bid.Close)              # Update the EMA 
        sdh.emaWindow1M_200.Add(sdh.EMA1M_200.Current)      # Add new EMA to rolling window

        sdh.newEma1MAvailable = True                                               # make sure OnData will know we have a new EMA bar
        
        # this means we also store a rolling window of recent price bars along with the EMA - keep them in sync
        sdh.Bars1M.Add(bar)  # Add the bar to the rolling window
        
        if bar.Bid.Close > bar.Bid.Open:
            sdh.Bars1MColour.Add(GREEN)
        elif bar.Bid.Close < bar.Bid.Open:
            sdh.Bars1MColour.Add(RED)
        else:
            sdh.Bars1MColour.Add(BLACK)
            
    
    # Fires for all the 5min consolidated bars
    def OnDataConsolidated5M(self, sender, bar):
        # The EMA needs updating before we add the updated value to the rollingwindow structure
        # should the EMA be updated with the 'average of the open and close?'
        sdh = self.symbolInfo[bar.Symbol.Value]
        symbol = bar.Symbol.Value
        
        sdh.EMA5M.Update(bar.Time, bar.Bid.Close)              # Update the EMA 
        sdh.emaWindow5M.Add(sdh.EMA5M.Current)      # Add new EMA to rolling window

        sdh.EMA5M_27.Update(bar.Time, bar.Bid.Close)              # Update the EMA 
        sdh.emaWindow5M_27.Add(sdh.EMA5M_27.Current)      # Add new EMA to rolling window

        sdh.newEma5MAvailable = True                                               # make sure OnData will know we have a new EMA bar
        
        # this means we also store a rolling window of recent price bars along with the EMA - keep them in sync
        sdh.Bars5M.Add(bar)  # Add the bar to the rolling window
        
        if bar.Bid.Close > bar.Bid.Open:
            sdh.Bars5MColour.Add(GREEN)
        elif bar.Bid.Close < bar.Bid.Open:
            sdh.Bars5MColour.Add(RED)
        else:
            sdh.Bars5MColour.Add(BLACK)

        # make sure we have at least 5 entries in the rollingWindow before starting
        if sdh.Bars5M.Count < 5: return

        # do the updates for EL and EH now before we go into the breakout checking, as it needs that up to date in case
        # a new EH or EL was formed by this 5Min candle that has just closed
        bidpricenow = self.Securities[symbol].BidPrice
        self.update_ext_structure(symbol, sdh, bidpricenow, ChartRes.res5M)

        TL_PH_result = False
        symbol_pip_size = sdh.minPriceVariation * 10
        symbol_5M_pip_threshold = 5.0
        symbol_5M_pip_one = 1.0
        TL_PH_result = sdh.check_peaks_troughs(self, bar.Symbol.Value, sdh.confirmed_TLs_5M, sdh.possible_TLs_5M, sdh.confirmed_PHs_5M, \
            sdh.possible_PHs_5M, bar, sdh.Bars5MColour[0], sdh.Bars5M[1].Bid.Low, sdh.Bars5M[1].Bid.High, \
            sdh.Bars5M[1].Bid.Open, sdh.Bars5MColour[1], ChartRes.res5M, logging=False)
        if TL_PH_result and self.use_old_trough_peaks:
            # TODO: clean up all the old references to Doug turning points
            # found a trough or peak - check for pattern - but only if we are using the old Doug approach
            # Long Breakout
            sdh.BT_long_5M.check_breakout(self, bar.Symbol.Value, sdh.confirmed_TLs_5M, sdh.confirmed_PHs_5M, symbol_pip_size, symbol_5M_pip_threshold, logging=False)
            # Short Breakout
            sdh.BT_short_5M.check_breakout(self, bar.Symbol.Value, sdh.confirmed_TLs_5M, sdh.confirmed_PHs_5M, symbol_pip_size, symbol_5M_pip_threshold, logging=False)
        
        # now update the Brad peaks and troughs to try to see if we have spotted a new peak or trough
        TL_PH_brad_result = False
        new_peak_5M = None
        new_trough_5M = None
        check_create_perfect = False

        # return values aren't used for now
        (TL_PH_brad_result, new_peak_5M, new_trough_5M) = sdh.check_brad_peaks_troughs(self, bar.Symbol.Value, sdh.brad_trough_tracker[ChartRes.res5M], sdh.brad_peak_tracker[ChartRes.res5M] \
            , sdh.Bars5M, sdh.Bars5MColour, ChartRes.res5M, logging=self.log_brad_peaks_detail)
        
        if not self.use_old_trough_peaks and not self.IsWarmingUp:
            # if we are using new Troughs and Peaks - we check every time a bar has closed - look backwards for a pattern in the peaks/troughs we have
            got_breakout = False
            bo_direction = StratDirection.Nothing
            bo_troughs = None
            bo_peaks = None
            bo_price = 0.0
            (got_breakout, bo_direction, bo_troughs, bo_peaks, bo_price) = sdh.check_for_brad_breakout(self, bar.Symbol.Value, sdh.brad_trough_tracker[ChartRes.res5M], sdh.brad_peak_tracker[ChartRes.res5M], sdh.Bars5M, sdh.Bars5MColour, ChartRes.res5M, logging=self.log_brad_breakout_spots)
            if got_breakout:
                mt4_time = fusion_utils.get_times(bar.Time, "us")["mt4"]
                # now we need to transfer it over
                if bo_direction == StratDirection.Long:
                    # Long Breakout
                    pass
                    check_create_perfect = sdh.BT_long_5M.make_ready_breakout(self, bar.Symbol.Value, bo_direction, bar, bo_troughs, bo_peaks, symbol_pip_size, symbol_5M_pip_one, logging=self.log_brad_make_breakouts)
                elif bo_direction == StratDirection.Short:
                    # Short Breakout
                    pass
                    check_create_perfect = sdh.BT_short_5M.make_ready_breakout(self, bar.Symbol.Value, bo_direction, bar, bo_troughs, bo_peaks, symbol_pip_size, symbol_5M_pip_one, logging=self.log_brad_make_breakouts)

                #self.Log(f"Found breakout at {mt4_time} for {bar.Symbol.Value} - No Troughs: {len(bo_troughs)} - No Peaks: {len(bo_peaks)} - Price: {bo_price}")

        d_hi = sdh.high_rolling_24H
        d_lo = sdh.low_rolling_24H
        mt4_time = fusion_utils.get_times(sdh.Bars5M[0].Time, 'us')['mt4']
        ny_time = sdh.Bars5M[0].Time
        my_EH = sdh.EH_EL_tracker[ChartRes.res5M].get_EH()
        my_EL = sdh.EH_EL_tracker[ChartRes.res5M].get_EL()
        my_template_5m = sdh.EH_EL_tracker[ChartRes.res5M].get_template()        
        my_template_1h = sdh.EH_EL_tracker[ChartRes.res1H].get_template()

        if not self.IsWarmingUp:
            if self.use_old_trough_peaks:
                # TODO: clean up all the old references to Doug turning points
                # Long Breakout - check if Higher Close is found in an active searching breakout tracker
                if sdh.BT_long_5M.searching and not sdh.BT_long_5M.triggered:
                    sdh.BT_long_5M.check_breakout_breached(self, bar.Symbol.Value, sdh.confirmed_TLs_5M, sdh.confirmed_PHs_5M, bar, sdh.Bars5MColour[0], \
                        sdh.ATR24H.Current.Value, d_hi, d_lo, symbol_pip_size, logging=self.log_breakouts_5M)
                    # now if it has hit CHH, then we need to check if it was clean enough for Brad perfects
                    if sdh.BT_long_5M.triggered:
                        if sdh.BT_long_5M.look_for_clean_breakout(self, bar.Symbol.Value, sdh, ChartRes.res5M, use_old_breakouts=True):
                            if self.log_breakouts_clean_5M: self.Log(f"{symbol} NY:{ny_time} | MT4: {mt4_time} FOUND CLEAN 5M LONG breakout + {sdh.BT_long_5M.clean_breakout_msg}")
                            # Clean breakout found - track it, for logging and possible trading
                            ignore_200ema = sdh.BT_long_5M.ignore_200ema
                            self.breakout_count_5M_long += 1
                            sdh.tbu_perfect_tracker[ChartRes.res5M].create_possible_perfect(self, symbol, sdh.BT_long_5M, ny_time, my_EH, my_EL, sdh.EH_EL_tracker[ChartRes.res5M], my_template_5m, my_template_1h, ignore_200ema, logging=self.log_tbu_perfects_details)
                        else:
                            if self.log_breakouts_dirty_5M: self.Log(f"{symbol} NY:{ny_time} | MT4: {mt4_time} FOUND DIRTY 5M LONG breakout + {sdh.BT_long_5M.clean_breakout_msg}")
                            self.breakout_count_dirty_5M_long += 1
                
                # Short Breakout - check if Lower Close is found in an active searching breakout tracker
                if sdh.BT_short_5M.searching and not sdh.BT_short_5M.triggered:
                    sdh.BT_short_5M.check_breakout_breached(self, bar.Symbol.Value, sdh.confirmed_TLs_5M, sdh.confirmed_PHs_5M, bar, sdh.Bars5MColour[0], \
                        sdh.ATR24H.Current.Value, d_hi, d_lo, symbol_pip_size, logging=self.log_breakouts_5M)
                    # now if it has hit CHH, then we need to check if it was clean enough for Brad perfects
                    if sdh.BT_short_5M.triggered:
                        if sdh.BT_short_5M.look_for_clean_breakout(self, bar.Symbol.Value, sdh, ChartRes.res5M, use_old_breakouts=True):
                            if self.log_breakouts_clean_5M: self.Log(f"{symbol} NY:{ny_time} | MT4: {mt4_time} FOUND CLEAN 5M SHORT breakout + {sdh.BT_short_5M.clean_breakout_msg}")
                            # Clean breakout found - track it, for logging and possible trading
                            ignore_200ema = sdh.BT_short_5M.ignore_200ema
                            self.breakout_count_5M_short += 1
                            sdh.tbu_perfect_tracker[ChartRes.res5M].create_possible_perfect(self, symbol, sdh.BT_short_5M, ny_time, my_EH, my_EL, sdh.EH_EL_tracker[ChartRes.res5M], my_template_5m, my_template_1h, ignore_200ema, logging=self.log_tbu_perfects_details)
                        else:
                            if self.log_breakouts_dirty_5M: self.Log(f"{symbol} NY:{ny_time} | MT4: {mt4_time} FOUND DIRTY 5M SHORT breakout + {sdh.BT_short_5M.clean_breakout_msg}")
                            self.breakout_count_dirty_5M_short += 1
            else:
                # we are now using the Brad definition of Peaks and Troughs
                # Long Breakout - check if Higher Close is found in an active searching breakout tracker
                if sdh.BT_long_5M.triggered and check_create_perfect:
                    if sdh.BT_long_5M.look_for_clean_breakout(self, bar.Symbol.Value, sdh, ChartRes.res5M, use_old_breakouts=False):
                        if self.log_breakouts_clean_5M and not self.IsWarmingUp: self.Log(f"{symbol} NY:{ny_time} | MT4: {mt4_time} FOUND CLEAN 5M LONG breakout + {sdh.BT_long_5M.clean_breakout_msg}")
                        # Clean breakout found - track it, for logging and possible trading
                        ignore_200ema = sdh.BT_long_5M.ignore_200ema
                        self.breakout_count_5M_long += 1
                        sdh.tbu_perfect_tracker[ChartRes.res5M].create_possible_perfect(self, symbol, sdh.BT_long_5M, ny_time, my_EH, my_EL, sdh.EH_EL_tracker[ChartRes.res5M], my_template_5m, my_template_1h, ignore_200ema, logging=self.log_tbu_perfects_details)
                    else:
                        if self.log_breakouts_dirty_5M and not self.IsWarmingUp: self.Log(f"{symbol} NY:{ny_time} | MT4: {mt4_time} FOUND DIRTY 5M LONG breakout + {sdh.BT_long_5M.clean_breakout_msg}")
                        self.breakout_count_dirty_5M_long += 1
                    sdh.BT_long_5M.clear()
                
                # Short Breakout - check if Lower Close is found in an active searching breakout tracker
                if sdh.BT_short_5M.triggered and check_create_perfect:
                    if sdh.BT_short_5M.look_for_clean_breakout(self, bar.Symbol.Value, sdh, ChartRes.res5M, use_old_breakouts=False):
                        if self.log_breakouts_clean_5M and not self.IsWarmingUp: self.Log(f"{symbol} NY:{ny_time} | MT4: {mt4_time} FOUND CLEAN 5M SHORT breakout + {sdh.BT_short_5M.clean_breakout_msg}")
                        # Clean breakout found - track it, for logging and possible trading
                        ignore_200ema = sdh.BT_short_5M.ignore_200ema
                        self.breakout_count_5M_short += 1
                        sdh.tbu_perfect_tracker[ChartRes.res5M].create_possible_perfect(self, symbol, sdh.BT_short_5M, ny_time, my_EH, my_EL, sdh.EH_EL_tracker[ChartRes.res5M], my_template_5m, my_template_1h, ignore_200ema, logging=self.log_tbu_perfects_details)
                    else:
                        if self.log_breakouts_dirty_5M and not self.IsWarmingUp: self.Log(f"{symbol} NY:{ny_time} | MT4: {mt4_time} FOUND DIRTY 5M SHORT breakout + {sdh.BT_short_5M.clean_breakout_msg}")
                        self.breakout_count_dirty_5M_short += 1
                    sdh.BT_short_5M.clear()

    
        
    # Fires for all the 15min consolidated bars
    def OnDataConsolidated15M(self, sender, bar):
        # This should fire whenever our custom bar period is reached e.g. 15 minutes.
        
        # The EMA needs updating before we add the updated value to the rollingwindow structure
        # should the EMA be updated with the 'average of the open and close?'
        sdh = self.symbolInfo[bar.Symbol.Value]
        sdh.EMA15M.Update(bar.Time, bar.Bid.Close)               # Update the EMA 
        sdh.emaWindow15M.Add(sdh.EMA15M.Current)      # Add new EMA to rolling window

        sdh.EMA15M_200.Update(bar.Time, bar.Bid.Close)              # Update the EMA 
        sdh.emaWindow15M_200.Add(sdh.EMA15M_200.Current)      # Add new EMA to rolling window

        sdh.newEma15MAvailable = True                                               # make sure OnData will know we have a new EMA bar
        
        # this means we also store a rolling window of recent price bars along with the EMA - keep them in sync
        sdh.Bars15M.Add(bar)  # Add the bar to the rolling window
        
        if bar.Bid.Close > bar.Bid.Open:
            sdh.Bars15MColour.Add(GREEN)
        elif bar.Bid.Close < bar.Bid.Open:
            sdh.Bars15MColour.Add(RED)
        else:
            sdh.Bars15MColour.Add(BLACK)
            

    # Fires for all the 30Min consolidated bars
    def OnDataConsolidated30M(self, sender, bar):
        # see comment above
        sdh = self.symbolInfo[bar.Symbol.Value]
        sdh.EMA30M.Update(bar.Time, bar.Bid.Close)                                # Update the EMA 
        sdh.emaWindow30M.Add(sdh.EMA30M.Current)    # Add new EMA to rolling window
        sdh.newEma30MAvailable = True                                             # make sure OnData will know we have a new EMA bar
        
        # this means we also store a rolling window of recent price bars along with the EMA - keep them in sync
        sdh.Bars30M.Add(bar)  # Add the bar to the rolling window
        
        if bar.Bid.Close > bar.Bid.Open:
            sdh.Bars30MColour.Add(GREEN)
        elif bar.Bid.Close < bar.Bid.Open:
            sdh.Bars30MColour.Add(RED)
        else:
            sdh.Bars30MColour.Add(BLACK)  
        
        # make sure we have at least 5 entries in the rollingWindow before starting
        if sdh.Bars30M.Count < 5: return
    
        TL_PH_result = False
        symbol_pip_size = sdh.minPriceVariation * 10
        symbol_30M_pip_threshold = 5.0
        TL_PH_result = sdh.check_peaks_troughs(self, bar.Symbol.Value, sdh.confirmed_TLs_30M, sdh.possible_TLs_30M, sdh.confirmed_PHs_30M, \
            sdh.possible_PHs_30M, bar, sdh.Bars30MColour[0], sdh.Bars30M[1].Bid.Low, sdh.Bars30M[1].Bid.High, \
            sdh.Bars30M[1].Bid.Open, sdh.Bars30MColour[1], ChartRes.res30M, logging=False)
        if TL_PH_result:
            # found a trough or peak - check for pattern
            # Long Breakout
            sdh.BT_long_30M.check_breakout(self, bar.Symbol.Value, sdh.confirmed_TLs_30M, sdh.confirmed_PHs_30M, symbol_pip_size, symbol_30M_pip_threshold, logging=False)
            # Short Breakout
            sdh.BT_short_30M.check_breakout(self, bar.Symbol.Value, sdh.confirmed_TLs_30M, sdh.confirmed_PHs_30M, symbol_pip_size, symbol_30M_pip_threshold, logging=False)
        
        d_hi = sdh.high_rolling_24H
        d_lo = sdh.low_rolling_24H
        
        # Long Breakout - check if Higher Close is found in an active searching breakout tracker
        if sdh.BT_long_30M.searching:
            sdh.BT_long_30M.check_breakout_breached(self, bar.Symbol.Value, sdh.confirmed_TLs_30M, sdh.confirmed_PHs_30M, bar, sdh.Bars30MColour[0], \
                sdh.ATR24H.Current.Value, d_hi, d_lo, symbol_pip_size, logging=self.log_breakouts_30M)
        
        # Short Breakout - check if Lower Close is found in an active searching breakout tracker
        if sdh.BT_short_30M.searching:
            sdh.BT_short_30M.check_breakout_breached(self, bar.Symbol.Value, sdh.confirmed_TLs_30M, sdh.confirmed_PHs_30M, bar, sdh.Bars30MColour[0], \
                sdh.ATR24H.Current.Value, d_hi, d_lo, symbol_pip_size, logging=self.log_breakouts_30M)
        

    # Fires for all the 1hr consolidated bars
    def OnDataConsolidated1H(self, sender, bar):
        # see comment above
        sdh = self.symbolInfo[bar.Symbol.Value]
        sdh.EMA1H.Update(bar.Time, bar.Bid.Close)            # Update the EMA 
        sdh.emaWindow1H.Add(sdh.EMA1H.Current)    # Add new EMA to rolling window
        sdh.newEma1HAvailable = True                                            # make sure OnData will know we have a new EMA bar
        # also add the current value for the 4HR EMA to the 1Hr window storing those values (we will get 4 in a row)
        sdh.emaWindow1H_of_4H.Add(sdh.EMA4H.Current)
        
        # this means we also store a rolling window of recent price bars along with the EMA - keep them in sync
        sdh.Bars1H.Add(bar)  # Add the bar to the rolling window
        
        if bar.Bid.Close > bar.Bid.Open:
            sdh.Bars1HColour.Add(GREEN)
        elif bar.Bid.Close < bar.Bid.Open:
            sdh.Bars1HColour.Add(RED)
        else:
            sdh.Bars1HColour.Add(BLACK)  
        
        # make sure we have at least 5 entries in the rollingWindow before starting
        if sdh.Bars1H.Count < 5: return
    
        TL_PH_result = False
        symbol_pip_size = sdh.minPriceVariation * 10
        symbol_1hr_pip_threshold = 5.0
        TL_PH_result = sdh.check_peaks_troughs(self, bar.Symbol.Value, sdh.confirmed_TLs_1H, sdh.possible_TLs_1H, sdh.confirmed_PHs_1H, \
            sdh.possible_PHs_1H, bar, sdh.Bars1HColour[0], sdh.Bars1H[1].Bid.Low, sdh.Bars1H[1].Bid.High, \
            sdh.Bars1H[1].Bid.Open, sdh.Bars1HColour[1], ChartRes.res1H, logging=False)
        if TL_PH_result:
            # found a trough or peak - check for pattern
            # Long Breakout - only check if we aren't looking for Pullback and RTT already
            if not sdh.BT_long_1H.triggered:
                sdh.BT_long_1H.check_breakout(self, bar.Symbol.Value, sdh.confirmed_TLs_1H, sdh.confirmed_PHs_1H, symbol_pip_size, symbol_1hr_pip_threshold, logging=False)
            # Short Breakout - only check if we aren't looking for Pullback and RTT already
            if not sdh.BT_short_1H.triggered:
                sdh.BT_short_1H.check_breakout(self, bar.Symbol.Value, sdh.confirmed_TLs_1H, sdh.confirmed_PHs_1H, symbol_pip_size, symbol_1hr_pip_threshold, logging=False)
        
        d_hi = sdh.high_rolling_24H
        d_lo = sdh.low_rolling_24H
        mt4_time = fusion_utils.get_times(sdh.Bars1H[0].Time, 'us')['mt4']
        symbol = bar.Symbol.Value

        # Long Breakout - check if Higher Close is found in an active searching breakout tracker
        if sdh.BT_long_1H.searching and not sdh.BT_long_1H.triggered:
            sdh.BT_long_1H.check_breakout_breached(self, bar.Symbol.Value, sdh.confirmed_TLs_1H, sdh.confirmed_PHs_1H, bar, sdh.Bars1HColour[0], \
                sdh.ATR24H.Current.Value, d_hi, d_lo, symbol_pip_size, logging=self.log_breakouts_1H)
            # now if it has hit CHH, then we need to check if it was clean enough for Brad perfects
            if sdh.BT_long_1H.triggered:
                if sdh.BT_long_1H.look_for_clean_breakout(self, bar.Symbol.Value, sdh, ChartRes.res1H):
                    if self.log_breakouts_clean_1H: self.Log(f"{symbol} {mt4_time} FOUND CLEAN 1H LONG breakout + {sdh.BT_long_1H.clean_breakout_msg}")
                else:
                    if self.log_breakouts_clean_1H: self.Log(f"{symbol} {mt4_time} FOUND DIRTY 1H LONG breakout + {sdh.BT_long_1H.clean_breakout_msg}")
        
        # Short Breakout - check if Lower Close is found in an active searching breakout tracker
        if sdh.BT_short_1H.searching and not sdh.BT_short_1H.triggered:
            sdh.BT_short_1H.check_breakout_breached(self, bar.Symbol.Value, sdh.confirmed_TLs_1H, sdh.confirmed_PHs_1H, bar, sdh.Bars1HColour[0], \
                sdh.ATR24H.Current.Value, d_hi, d_lo, symbol_pip_size, logging=self.log_breakouts_1H)
            # now if it has hit CLL, then we need to check if it was clean enough for Brad perfects
            if sdh.BT_short_1H.triggered:
                if sdh.BT_short_1H.look_for_clean_breakout(self, bar.Symbol.Value, sdh, ChartRes.res1H):
                    if self.log_breakouts_clean_1H: self.Log(f"{symbol} {mt4_time} FOUND CLEAN 1H SHORT breakout + {sdh.BT_short_1H.clean_breakout_msg}")
                else:
                    if self.log_breakouts_clean_1H: self.Log(f"{symbol} {mt4_time} FOUND DIRTY 1H SHORT breakout + {sdh.BT_short_1H.clean_breakout_msg}")
        


    # Fires for all the 4hr consolidated bars
    def OnDataConsolidated4H(self, sender, bar):
        # see comment above
        sdh = self.symbolInfo[bar.Symbol.Value]
        sdh.EMA4H.Update(bar.Time, bar.Bid.Close)            # Update the EMA 
        sdh.emaWindow4H.Add(sdh.EMA4H.Current)    # Add new EMA to rolling window
        sdh.newEma4HAvailable = True                                            # make sure OnData will know we have a new EMA bar
        
        sdh.ADX4H.Update(bar)
        
        #sdh.Macd4H.Update(bar.Time, bar.Bid.Close)            # Update the MACD
        sdh.Macd4H.Update(bar.Time, bar.Bid.Close)            # Update the MACD
        sdh.MacdFastWindow4H.Add(sdh.Macd4H.Fast.Current)    # Add new Macd to rolling window
        sdh.MacdSlowWindow4H.Add(sdh.Macd4H.Slow.Current)    # Add new Macd to rolling window
        sdh.MacdSignalWindow4H.Add(sdh.Macd4H.Signal.Current)    # Add new Macd to rolling window
        sdh.MacdHistWindow4H.Add(sdh.Macd4H.Histogram.Current)    # Add new Macd to rolling window
        sdh.MacdCurrentWindow4H.Add(sdh.Macd4H.Current)    # Add new Macd to rolling window
        sdh.newMacd4HAvailable = True                                            # make sure OnData will know we have a new Macd
        
        
        # this means we also store a rolling window of recent price bars along with the EMA - keep them in sync
        sdh.Bars4H.Add(bar)  # Add the bar to the rolling window
        
        if bar.Bid.Close > bar.Bid.Open:
            sdh.Bars4HColour.Add(GREEN)
        elif bar.Bid.Close < bar.Bid.Open:
            sdh.Bars4HColour.Add(RED)
        else:
            sdh.Bars4HColour.Add(BLACK)


    # Fires for all the 24hr consolidated bars
    def OnDataConsolidated24H(self, sender, bar):
        # see comment above
        sdh = self.symbolInfo[bar.Symbol.Value]
        sdh.EMA24H.Update(bar.Time, bar.Bid.Close)            # Update the EMA 
        sdh.emaWindow24H.Add(sdh.EMA24H.Current)   # Add new EMA to rolling window
        sdh.newEma24HAvailable = True                                            # make sure OnData will know we have a new EMA bar
        
        # this means we also store a rolling window of recent price bars along with the EMA - keep them in sync
        sdh.Bars24H.Add(bar)  # Add the bar to the rolling window
        
        if bar.Bid.Close > bar.Bid.Open:
            sdh.Bars24HColour.Add(GREEN)
        elif bar.Bid.Close < bar.Bid.Open:
            sdh.Bars24HColour.Add(RED)
        else:
            sdh.Bars24HColour.Add(BLACK)
            
            
        
    '''Look for the Higher Highs and Lower Lows of a Channel Trade, to get to the point of firing the trade
    '''
    # TODO: Strip out all the Channel stuff that isn't really used
    def Look_For_Channel_HH_LL(self, symbol, sd, did_price_rise, did_price_drop, rise_high, pattern_low_1, drop_low, pattern_high_1):
        if did_price_rise or did_price_drop:
            # need to reset counters 
            sd.looking_for_channel = True
            sd.looking_for_channel_hours = 0
            sd.channel_state = 0      # 0 is not found, 1 is ready to look for entry price breach, 2 is now in price zone - if price leaves zone, 3 is do it
            sd.channel_trigger_price = 0.0
            # set different depending on which direction
            if did_price_rise:
                sd.channel_direction = StratDirection.Short
                self.Log(f"Symbol: {symbol} start looking for a Short Channel trade")
                sd.channel_h = rise_high
                sd.channel_l = pattern_low_1
                sd.channel_h_h = rise_high
                sd.channel_l_l = pattern_low_1
            else:
                sd.channel_direction = StratDirection.Long
                self.Log(f"Symbol: {symbol} start looking for a Long Channel trade")
                sd.channel_l = drop_low
                sd.channel_h = pattern_high_1
                sd.channel_l_l = drop_low
                sd.channel_h_h = pattern_high_1
        elif sd.looking_for_channel:
            # increase timer as we are already looking, but got to another hour
            sd.looking_for_channel_hours += 1
            
            # now check if we have a higher high or lower low
            if sd.channel_direction == StratDirection.Long:
                if sd.channel_l == sd.channel_l_l:
                    # still looking Lower Low
                    if sd.Bars1H[0].Bid.Low < sd.channel_l:
                        sd.channel_l_l = round(sd.Bars1H[0].Bid.Low, 5)
                        self.Log(f"Symbol: {symbol} Long Channel LL: {sd.channel_l_l}")
                elif sd.channel_h == sd.channel_h_h:
                    # now looking for Higher High
                    if sd.Bars1H[0].Bid.High > sd.channel_h:
                        sd.channel_h_h = round(sd.Bars1H[0].Bid.High, 5)
                        self.Log(f"Symbol: {symbol} Long Channel HH: {sd.channel_h_h}")
                        # now need to tell it we are looking for entry
                        sd.channel_state = 1      # 0 is not found, 1 is ready to look for entry price breach, 2 is now in price zone - if price leaves zone, 3 is do it
                        sd.channel_trigger_price = sd.channel_l + (2.0 * sd.minPriceVariation * 10)     # give it a 2 pip tolerance
            
            # Deal with potential SHORT trade
            if sd.channel_direction == StratDirection.Short:
                if sd.channel_h == sd.channel_h_h:
                    # still looking Higher High
                    if sd.Bars1H[0].Bid.High > sd.channel_h:
                        sd.channel_h_h = round(sd.Bars1H[0].Bid.High, 5)
                        self.Log(f"Symbol: {symbol} Short Channel HH: {sd.channel_h_h}")
                elif sd.channel_l == sd.channel_l_l:
                    # now looking for Lower Low
                    if sd.Bars1H[0].Bid.Low < sd.channel_l:
                        sd.channel_l_l = round(sd.Bars1H[0].Bid.Low, 5)
                        self.Log(f"Symbol: {symbol} Short Channel LL: {sd.channel_l_l}")
                        # now need to tell it we are looking for entry
                        sd.channel_state = 1      # 0 is not found, 1 is ready to look for entry price breach, 2 is now in price zone - if price leaves zone, 3 is do it
                        sd.channel_trigger_price = sd.channel_h - (2.0 * sd.minPriceVariation * 10)     # give it a 2 pip tolerance
            
            if sd.looking_for_channel_hours == 12:
                # timed out - no trade entry
                sd.looking_for_channel = False
                sd.looking_for_channel_hours = 0
                self.Log(f"Symbol: {symbol} Long Channel trade timer - EXPIRED")
                
 
            
    #si 07.04.2022 - we need to expand the channel states to provide different entry options
    # 0 is not found, 1 is ready to look for entry price breach, 2 is now in price zone - if price leaves zone, 3 is do it
    # 7 bypasses the need for a trigger price  
    # 6 points good, no trigger required, DTT test needed to pass           
    # TODO: Strip out all the Channel stuff that isn't really used
    def Look_For_Channel_Trigger(self, symbol, sd, price_now):
        if sd.looking_for_channel and sd.channel_state > 0:
            sd.channel_weakness_found = False #reset this as we haven't bee price triggered yet
            # only relevant if we are looking for a trade trigger and have found HH and LL already
            if sd.channel_state == 1 and sd.channel_direction == StratDirection.Short:
                # look for the price reaching above the price and move into next state
                #if price_now > (sd.channel_trigger_price + (3.0 * sd.minPriceVariation * 10)):
                if price_now > sd.channel_trigger_price:
                    #sd.channel_state = 2
                    sd.channel_state = 5                                       
                    self.Debug(str(self.Time) + " Triggered Short | Symbol: " + str(symbol) + " price_now: " + str(price_now) + " trigger:" + str(sd.channel_trigger_price ))
                    return False
            if sd.channel_state == 1 and sd.channel_direction == StratDirection.Long:
                # look for the price reaching below the price and move into next state
                #if price_now < (sd.channel_trigger_price - (3.0 * sd.minPriceVariation * 10)):
                if price_now < sd.channel_trigger_price:
                    #sd.channel_state = 2
                    sd.channel_state = 5
                    self.Debug(str(self.Time) + " Triggered Long | Symbol: " + str(symbol) + " price_now: " + str(price_now) + " trigger:" + str(sd.channel_trigger_price ))
                    return False
                        
            # *** Si 08.03.2022 we are not looking for the state 2 for the moment, but left in        
            # if we are in State 2 and the price leaves the zone, we are then ready to enter trade
            if sd.channel_state == 2 and sd.channel_direction == StratDirection.Short:
                # look for the price now starting to head down again
                if price_now < sd.channel_trigger_price:
                    sd.channel_state = 3
                    return True
            if sd.channel_state == 2 and sd.channel_direction == StratDirection.Long:
                # look for the price now starting to move up again
                if price_now > sd.channel_trigger_price:
                    sd.channel_state = 3
                    #self.Log(f"Symbol: {symbol} Trigger fired - now trade")
                    return True
                    
        return False
    
     
   