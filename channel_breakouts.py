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
from fusion_utils import *
from dataclasses import dataclass
from symbolinfo import *
from manual_orders import *
from QuantConnect import Market
from io import StringIO
import pandas as pd

'''Single code file for all the stuff to do with seeking channel breakout, pullback, RTT trades - mostly called from OnData loop'''

class QCalgo_channel_breakout(QCalgo_manual_orders):
    
    # TODO: this needs improving and probably replacing with the general 4H shorter term trend calc - moving out of main OnData for now
    def channel_breakout_estimate_4h_trend(self, sd):
        temp_4h_trend = Trends.Nothing
        s0_4hr = sd.emaWindow1H_of_4H[4].Value
        s1_4hr = sd.emaWindow1H_of_4H[6].Value
        start_4hr = sd.emaWindow1H_of_4H[2].Value
        end_4hr = sd.emaWindow1H_of_4H[0].Value
        two_pips = 2.0 * sd.minPriceVariation * 10
        diff_4hr0_pips = round((s1_4hr - s0_4hr) / (sd.minPriceVariation * 10), 2)
        diff_4hr1_pips = round((s0_4hr - start_4hr) / (sd.minPriceVariation * 10), 2)
        diff_4hr2_pips = round((start_4hr - end_4hr) / (sd.minPriceVariation * 10), 2)

        # now try to see what 4Hr trend line is doing
        if (diff_4hr0_pips >= 0 and diff_4hr1_pips >= 0 and diff_4hr2_pips >= 0) and not (diff_4hr0_pips == 0 and diff_4hr1_pips == 0 and diff_4hr2_pips == 0):
            # likely down
            temp_4h_trend = Trends.Downtrend

        if (diff_4hr0_pips <= 0 and diff_4hr1_pips <= 0 and diff_4hr2_pips <= 0) and not (diff_4hr0_pips == 0 and diff_4hr1_pips == 0 and diff_4hr2_pips == 0):
            # likely up
            temp_4h_trend = Trends.Uptrend
        
        '''if (diff_1hr_pips > 4.0 and diff_4hr_pips > 0.0) or (diff_1hr_pips > 7.0 and diff_4hr_pips >= 0.0):
            # uptrend?
            my_perfect_trend = Trends.Uptrend
        if (diff_1hr_pips < -4.0 and diff_4hr_pips < 0.0) or (diff_1hr_pips < -7.0 and diff_4hr_pips <= 0.0):
            # downtrend?
            my_perfect_trend = Trends.Downtrend'''
        return temp_4h_trend

    # Checks carried out to calculate Perfect Points for a HHLL possible pullback or RTT entry - before seeking entry
    def channel_breakout_looking_checks_1H(self, sender, symbol, sd, timenow, bidpricenow, my_4h_trend):
        sd.perfectPoints_1Hr = 0
        if not sd.BT_long_1H.triggered:
            sd.AlertedPerfect_Long_1HR = False
        if not sd.BT_short_1H.triggered:
            sd.AlertedPerfect_Short_1HR = False
        
        if sd.BT_long_1H.triggered and not sd.looking_for_channel_1H and sd.channel_direction_1H == StratDirection.Nothing:
            sender.price_tracker_lib.add_tracker(symbol, timenow, bidpricenow, "SHORT", 30.0, timedelta(hours=6), "CHH", 0, sd.minPriceVariation * 10)
            # sender.Log(f"{symbol} Running LONG 1hr Perfect Points check | CHH: {sd.BT_long_1H.BT_higher_close}")
            if not sd.AlertedPerfect_Long_1HR:
                sd.perfectPoints_1Hr = sd.CalculatePerfectPoints(self,symbol, sd, False, my_4h_trend, sd.Bars1H, sd.emaWindow1H, \
                    sd.emaWindow4H, sd.Bars1HColour, sd.Ceil123R_1H, sd.Floor123G_1H, sd.BT_long_1H.BT_PeakHigh, sd.BT_long_1H.BT_TroughLow, \
                    sd.BT_long_1H.BT_higher_close,sd.BT_long_1H.BT_lower_close,sd.BT_long_1H.BT_higher_high,sd.BT_long_1H.BT_lower_low, \
                    sd.CurrentRes, sd.BT_long_1H.BT_pullback1,  sd.BT_long_1H.BT_pullback2,sd.BT_long_1H.BT_pullback3, logging=sender.log_perfect_emails )
                sd.AlertedPerfect_Long_1HR = True
                sd.AlertedPerfect_Short_1HR = False  #si 08.04 added in case triggers are for both
            if sd.perfectPoints_1Hr >= sender.MinimumPerfectPoints: 
                if sender.log_channels_1H: sender.Log(f"HHLL: {symbol} - 1hr starting channel LONG points:{sd.perfectPoints_1Hr}")
                sd.channel_state_1H = 0      #see consolidators Look_For_Channel_Trigger for details 
                sd.looking_for_channel_1H = True
                sd.channel_direction_1H = StratDirection.Long
                #sd.channel_trigger_price = sd.BT_long_1H.BT_pullback1                                
        if not sd.BT_long_1H.triggered and sd.looking_for_channel_1H  and sd.channel_direction_1H == StratDirection.Long:
            if sender.log_channels_1H: sender.Log(f"HHLL: {symbol} - Clearing channel LONG hunt:{sd.perfectPoints_1Hr}")
            sd.clear_perfect_channel_1H()

            
        if sd.BT_short_1H.triggered and not sd.looking_for_channel_1H and sd.channel_direction_1H == StratDirection.Nothing:
            sender.price_tracker_lib.add_tracker(symbol, timenow, bidpricenow, "LONG", 30.0, timedelta(hours=6), "CLL", 0, sd.minPriceVariation * 10)
            #sender.Log(f"{symbol} Running SHORT 1hr Perfect Points check | CHH: {sd.BT_short_1H.BT_lower_close}")
            if not sd.AlertedPerfect_Short_1HR:
                sd.perfectPoints_1Hr = sd.CalculatePerfectPoints(self,symbol, sd, True, my_4h_trend, sd.Bars1H, sd.emaWindow1H, \
                    sd.emaWindow4H, sd.Bars1HColour, sd.Ceil123R_1H, sd.Floor123G_1H, sd.BT_short_1H.BT_PeakHigh, sd.BT_short_1H.BT_TroughLow, \
                    sd.BT_short_1H.BT_higher_close, sd.BT_short_1H.BT_lower_close, sd.BT_short_1H.BT_higher_high,sd.BT_short_1H.BT_lower_low, \
                    sd.CurrentRes,  sd.BT_short_1H.BT_pullback1, sd.BT_short_1H.BT_pullback2, sd.BT_short_1H.BT_pullback3, logging=sender.log_perfect_emails ) 
                sd.AlertedPerfect_Short_1HR = True
                sd.AlertedPerfect_Long_1HR = False  #si 08.04 added in case triggers are for both
            if sd.perfectPoints_1Hr >= sender.MinimumPerfectPoints: 
                if sender.log_channels_1H: sender.Log(f"HHLL: {symbol} - 1hr starting channel SHORT points:{sd.perfectPoints_1Hr}")
                sd.channel_state_1H = 0   #see consolidators Look_For_Channel_Trigger for details 
                sd.looking_for_channel_1H = True
                sd.channel_direction_1H = StratDirection.Short
                #sd.channel_trigger_price = sd.BT_short_1H.BT_pullback1
        if not sd.BT_short_1H.triggered and sd.looking_for_channel_1H and sd.channel_direction_1H == StratDirection.Short:
            if sender.log_channels_1H: sender.Log(f"HHLL: {symbol} - Clearing channel SHORT hunt:{sd.perfectPoints_1Hr}")
            sd.clear_perfect_channel_1H()

    # Once a possible breakout has been spotted and we are looking for the pullback - this check is called 
    def channel_breakout_pre_entry_checks_1H(self, sender, symbol, sd):
        sd.TriggerCandleWindow_1HR += 1   #now we are triggered lets count (starts at -1)
        if sd.TriggerCandleWindow_1HR >= 1:  #we know this is S1
            sd.channel_weakness_found_1HR = False
            sd.channel_weakness_found_1HR = sd.DTTClassicEntryTest(sd.Bars1HColour, sd.Bars1H, sd.channel_direction_1H, sd.emaWindow1H, sd.emaWindow4H, sd.CurrentRes)
            if sd.channel_weakness_found_1HR:
                if sender.log_channels_1H: sender.Log(f"HHLL: {sender.Time} | {symbol} - 1hr DTT Classic Entry Test PASSED - doing nothing though")
                # TODO: channel trades will never do anything, just expire - reinstate behaviour - move to looking for Entry
                #sd.channel_state_1H = 5
        if sd.TriggerCandleWindow_1HR == sender.TriggerCandleWindowMax:  
            if sender.log_channels_1H: sender.Log(f"HHLL: US candle open: {sd.Bars1H[0].Time} | MT5 candle open: {sender.oandaChartTime} | Trigger Window Closed - time exceeded - Reset")  
            sd.clear_perfect_channel_1H()


    # Checks carried out to calculate Perfect Points for a HHLL possible pullback or RTT entry - before seeking entry
    def channel_breakout_looking_checks_30M(self, sender, symbol, sd, timenow, bidpricenow, my_4h_trend):
        sd.perfectPoints_30M = 0
        if not sd.BT_long_30M.triggered:
            sd.AlertedPerfect_Long_30M = False
        if not sd.BT_short_30M.triggered:
            sd.AlertedPerfect_Short_30M = False
        
        if sd.BT_long_30M.triggered and not sd.looking_for_channel_30M and sd.channel_direction_30M == StratDirection.Nothing:
            sender.price_tracker_lib.add_tracker(symbol, timenow, bidpricenow, "SHORT", 30.0, timedelta(hours=6), "CHH", 0, sd.minPriceVariation * 10)
            # sender.Log(f"{symbol} Running LONG 30M Perfect Points check | CHH: {sd.BT_long_30M.BT_higher_close}")
            if not sd.AlertedPerfect_Long_30M:
                sd.perfectPoints_30M = sd.CalculatePerfectPoints(self,symbol, sd, False, my_4h_trend, sd.Bars30M, sd.emaWindow30M, \
                    sd.emaWindow4H, sd.Bars30MColour, sd.Ceil123R_30M, sd.Floor123G_30M, sd.BT_long_30M.BT_PeakHigh, sd.BT_long_30M.BT_TroughLow, \
                    sd.BT_long_30M.BT_higher_close,sd.BT_long_30M.BT_lower_close,sd.BT_long_30M.BT_higher_high,sd.BT_long_30M.BT_lower_low, \
                    sd.CurrentRes, sd.BT_long_30M.BT_pullback1,  sd.BT_long_30M.BT_pullback2,sd.BT_long_30M.BT_pullback3, logging=sender.log_perfect_emails )
                sd.AlertedPerfect_Long_30M = True
                sd.AlertedPerfect_Short_30M = False  #si 08.04 added in case triggers are for both
            if sd.perfectPoints_30M >= sender.MinimumPerfectPoints: 
                if sender.log_channels_30M: sender.Log(f"HHLL: {symbol} - 30M starting channel LONG points:{sd.perfectPoints_30M}")
                sd.channel_state_30M = 0      #see consolidators Look_For_Channel_Trigger for details 
                sd.looking_for_channel_30M = True
                sd.channel_direction_30M = StratDirection.Long
                #sd.channel_trigger_price = sd.BT_long_30M.BT_pullback1                                
        if not sd.BT_long_30M.triggered and sd.looking_for_channel_30M  and sd.channel_direction_30M == StratDirection.Long:
            if sender.log_channels_30M: sender.Log(f"HHLL: {symbol} - Clearing channel LONG hunt:{sd.perfectPoints_30M}")
            sd.clear_perfect_channel_30M()

            
        if sd.BT_short_30M.triggered and not sd.looking_for_channel_30M and sd.channel_direction_30M == StratDirection.Nothing:
            sender.price_tracker_lib.add_tracker(symbol, timenow, bidpricenow, "LONG", 30.0, timedelta(hours=6), "CLL", 0, sd.minPriceVariation * 10)
            #sender.Log(f"{symbol} Running SHORT 30M Perfect Points check | CHH: {sd.BT_short_30M.BT_lower_close}")
            if not sd.AlertedPerfect_Short_30M:
                sd.perfectPoints_30M = sd.CalculatePerfectPoints(self,symbol, sd, True, my_4h_trend, sd.Bars30M, sd.emaWindow30M, \
                    sd.emaWindow4H, sd.Bars30MColour, sd.Ceil123R_30M, sd.Floor123G_30M, sd.BT_short_30M.BT_PeakHigh, sd.BT_short_30M.BT_TroughLow, \
                    sd.BT_short_30M.BT_higher_close, sd.BT_short_30M.BT_lower_close, sd.BT_short_30M.BT_higher_high,sd.BT_short_30M.BT_lower_low, \
                    sd.CurrentRes,  sd.BT_short_30M.BT_pullback1, sd.BT_short_30M.BT_pullback2, sd.BT_short_30M.BT_pullback3, logging=sender.log_perfect_emails ) 
                sd.AlertedPerfect_Short_30M = True
                sd.AlertedPerfect_Long_30M = False  #si 08.04 added in case triggers are for both
            if sd.perfectPoints_30M >= sender.MinimumPerfectPoints: 
                if sender.log_channels_30M: sender.Log(f"HHLL: {symbol} - 30M starting channel SHORT points:{sd.perfectPoints_30M}")
                sd.channel_state_30M = 0   #see consolidators Look_For_Channel_Trigger for details 
                sd.looking_for_channel_30M = True
                sd.channel_direction_30M = StratDirection.Short
                #sd.channel_trigger_price = sd.BT_short_30M.BT_pullback1
        if not sd.BT_short_30M.triggered and sd.looking_for_channel_30M and sd.channel_direction_30M == StratDirection.Short:
            if sender.log_channels_30M: sender.Log(f"HHLL: {symbol} - Clearing channel SHORT hunt:{sd.perfectPoints_30M}")
            sd.clear_perfect_channel_30M()

    # Once a possible breakout has been spotted and we are looking for the pullback - this check is called 
    def channel_breakout_pre_entry_checks_30M(self, sender, symbol, sd):
        sd.TriggerCandleWindow_30M += 1   #now we are triggered lets count (starts at -1)
        if sd.TriggerCandleWindow_30M >= 1:  #we know this is S1
            sd.channel_weakness_found_30M = False
            sd.channel_weakness_found_30M = sd.DTTClassicEntryTest(sd.Bars30MColour, sd.Bars30M, sd.channel_direction_30M, sd.emaWindow30M, sd.emaWindow4H, sd.CurrentRes)
            if sd.channel_weakness_found_30M:
                if sender.log_channels_30M: sender.Log(f"HHLL: {sender.Time} | {symbol} - 30M DTT Classic Entry Test PASSED - doing nothing though")
                # TODO: channel trades will never do anything, just expire - reinstate behaviour - move to looking for Entry
                #sd.channel_state_30M = 5
        if sd.TriggerCandleWindow_30M == sender.TriggerCandleWindowMax:  
            if sender.log_channels_30M: sender.Log(f"HHLL: US candle open: {sd.Bars30M[0].Time} | MT5 candle open: {sender.oandaChartTime} | Trigger Window Closed - time exceeded - Reset")  
            sd.clear_perfect_channel_30M()



  # Checks carried out to calculate Perfect Points for a HHLL possible pullback or RTT entry - before seeking entry
    def channel_breakout_looking_checks_5M(self, sender, symbol, sd, timenow, bidpricenow, my_4h_trend):
        sd.perfectPoints_5M = 0
        if not sd.BT_long_5M.triggered:
            sd.AlertedPerfect_Long_5M = False
        if not sd.BT_short_5M.triggered:
            sd.AlertedPerfect_Short_5M = False
        
        trading_window = TradingWindow.Closed
        if sd.BT_long_5M.triggered:
            # the triggered_time could be None if the breakout hasn't been triggered, which would then fail in get_trading_window
            trading_window = fusion_utils.get_trading_window(sd.BT_long_5M.triggered_time)
        if trading_window in {TradingWindow.TW1, TradingWindow.TW2, TradingWindow.TW3}:
            if sd.BT_long_5M.triggered and not sd.looking_for_channel_5M and sd.channel_direction_5M == StratDirection.Nothing:
                sender.price_tracker_lib.add_tracker(symbol, timenow, bidpricenow, "SHORT", 30.0, timedelta(hours=6), "CHH", 0, sd.minPriceVariation * 10)
                sender.Debug(f"{symbol} Running LONG 5M Perfect Points check | CHH: {sd.BT_long_5M.BT_higher_close}")
                if not sd.AlertedPerfect_Long_5M:
                    sd.perfectPoints_5M = sd.CalculatePerfectPoints(self,symbol, sd, False, my_4h_trend, sd.Bars30M, sd.emaWindow30M, \
                        sd.emaWindow4H, sd.Bars5MColour, sd.Ceil123R_5M, sd.Floor123G_5M, sd.BT_long_5M.BT_PeakHigh, sd.BT_long_5M.BT_TroughLow, \
                        sd.BT_long_5M.BT_higher_close,sd.BT_long_5M.BT_lower_close,sd.BT_long_5M.BT_higher_high,sd.BT_long_5M.BT_lower_low, \
                        sd.CurrentRes, sd.BT_long_5M.BT_pullback1,  sd.BT_long_5M.BT_pullback2,sd.BT_long_5M.BT_pullback3, logging=sender.log_perfect_emails )
                    sd.AlertedPerfect_Long_5M = True
                    sd.AlertedPerfect_Short_5M = False  #si 08.04 added in case triggers are for both
                if sd.perfectPoints_5M >= sender.MinimumPerfectPoints: 
                    if sender.log_channels_5M: sender.Log(f"HHLL: {symbol} - 5M starting channel LONG points:{sd.perfectPoints_5M}")
                    sd.channel_state_5M = 0      #see consolidators Look_For_Channel_Trigger for details 
                    sd.looking_for_channel_5M = True
                    sd.channel_direction_5M = StratDirection.Long
                    #sd.channel_trigger_price = sd.BT_long_5M.BT_pullback1                                
        # this clearance may need to be done outside the trading windows
        if not sd.BT_long_5M.triggered and sd.looking_for_channel_5M  and sd.channel_direction_5M == StratDirection.Long:
            if sender.log_channels_5M: sender.Log(f"HHLL: {symbol} - Clearing channel LONG hunt:{sd.perfectPoints_5M}")
            sd.clear_perfect_channel_5M()

        if trading_window in {TradingWindow.TW1, TradingWindow.TW2, TradingWindow.TW3}:    
            if sd.BT_short_5M.triggered and not sd.looking_for_channel_5M and sd.channel_direction_5M == StratDirection.Nothing:
                sender.price_tracker_lib.add_tracker(symbol, timenow, bidpricenow, "LONG", 30.0, timedelta(hours=6), "CLL", 0, sd.minPriceVariation * 10)
                sender.Debug(f"{symbol} Running SHORT 5M Perfect Points check | CHH: {sd.BT_short_5M.BT_lower_close}")
                if not sd.AlertedPerfect_Short_5M:
                    sd.perfectPoints_5M = sd.CalculatePerfectPoints(self,symbol, sd, True, my_4h_trend, sd.Bars30M, sd.emaWindow30M, \
                        sd.emaWindow4H, sd.Bars5MColour, sd.Ceil123R_5M, sd.Floor123G_5M, sd.BT_short_5M.BT_PeakHigh, sd.BT_short_5M.BT_TroughLow, \
                        sd.BT_short_5M.BT_higher_close, sd.BT_short_5M.BT_lower_close, sd.BT_short_5M.BT_higher_high,sd.BT_short_5M.BT_lower_low, \
                        sd.CurrentRes,  sd.BT_short_5M.BT_pullback1, sd.BT_short_5M.BT_pullback2, sd.BT_short_5M.BT_pullback3, logging=sender.log_perfect_emails ) 
                    sd.AlertedPerfect_Short_5M = True
                    sd.AlertedPerfect_Long_5M = False  #si 08.04 added in case triggers are for both
                if sd.perfectPoints_5M >= sender.MinimumPerfectPoints: 
                    if sender.log_channels_5M: sender.Log(f"HHLL: {symbol} - 5M starting channel SHORT points:{sd.perfectPoints_5M}")
                    sd.channel_state_5M = 0   #see consolidators Look_For_Channel_Trigger for details 
                    sd.looking_for_channel_5M = True
                    sd.channel_direction_5M = StratDirection.Short
                    #sd.channel_trigger_price = sd.BT_short_5M.BT_pullback1
        # this clearance may need to be done outside the trading windows
        if not sd.BT_short_5M.triggered and sd.looking_for_channel_5M and sd.channel_direction_5M == StratDirection.Short:
            if sender.log_channels_5M: sender.Log(f"HHLL: {symbol} - Clearing channel SHORT hunt:{sd.perfectPoints_5M}")
            sd.clear_perfect_channel_5M()

    # Once a possible breakout has been spotted and we are looking for the pullback - this check is called 
    def channel_breakout_pre_entry_checks_5M(self, sender, symbol, sd):
        sd.TriggerCandleWindow_5M += 1   #now we are triggered lets count (starts at -1)
        if sd.TriggerCandleWindow_5M >= 1:  #we know this is S1
            sd.channel_weakness_found_5M = False
            sd.channel_weakness_found_5M = sd.DTTClassicEntryTest(sd.Bars5MColour, sd.Bars30M, sd.channel_direction_5M, sd.emaWindow30M, sd.emaWindow4H, sd.CurrentRes)
            if sd.channel_weakness_found_5M:
                if sender.log_channels_5M: sender.Log(f"HHLL: {sender.Time} | {symbol} - 5M DTT Classic Entry Test PASSED - doing nothing though")
                # TODO: channel trades will never do anything, just expire - reinstate behaviour - move to looking for Entry
                #sd.channel_state_5M = 5
        if sd.TriggerCandleWindow_5M == sender.TriggerCandleWindowMax:  
            if sender.log_channels_5M: sender.Log(f"HHLL: US candle open: {sd.Bars30M[0].Time} | MT5 candle open: {sender.oandaChartTime} | Trigger Window Closed - time exceeded - Reset")  
            sd.clear_perfect_channel_5M()


