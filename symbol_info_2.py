#region imports
from AlgorithmImports import *
#endregion
''' <summary>
 This is the SymbolData class needed for storing info on symbols etc
'''

from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Indicators")

import enum
import math
import copy
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
from dataclasses import dataclass
from turningpoints import *
from brad_turning_points import *
from session_boxes import *
from fusion_utils import *
from external_structure import *
from builder_perfect import *
from price_tracker import *


GREEN = 0
RED = 1
BLACK = 2
day = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


'''
This contains just some of the functions.  Needed to get over the 64k file limit
The actual SymbolData class is the one you need to use when wanting to access these methods
'''
class SymbolData_2(object):

    # Clear down strategy and tracking info
    def ClearTracking(self):
        # stop loss ticket. 
            self.cancel_if_losing_time = None
            self.pb_wait_cycles = 0
            self.sl_position = 0 
            self.exit_price = 0.0
            self.activeStrat = Strats.Nothing
            self.activeDirection = StratDirection.Nothing
            self.split_live_levels = [False, False, False] 
            self.tickets_trades = [None, None, None]     
            self.tickets_stops = [None, None, None]
            self.tickets_last_stop_levels = [None, None, None]
            self.tickets_profits = [None, None, None]
            self.tickets_entry_no = [0, 0, 0]   
            self.tickets_position_size = [0, 0, 0]  
            self.tickets_ids = [None, None, None]
            self.tickets_live_levels = [False, False, False]
            self.tickets_low_asks = [0.0, 0.0, 0.0]
            self.tickets_low_bids = [0.0, 0.0, 0.0]
            self.tickets_high_asks = [0.0, 0.0, 0.0]
            self.tickets_high_bids = [0.0, 0.0, 0.0]
            self.entry_prices = [0.0, 0.0, 0.0]
            self.entry_times = [None, None, None]
            self.exit_prices = [0.0, 0.0, 0.0]
            self.spreads_paid = [0.0,  0.0, 0.0]
            self.max_pips_profits = [0.0, 0.0, 0.0]
            self.max_pips_losses = [0.0, 0.0, 0.0]
            self.sl_positions = [0, 0, 0]
            self.last_trail_levels = [None, None, None]
            self.EntryMacdSignal = 0.0
            self.EntryMacdFast = 0.0
            self.EntryMacdslow = 0.0
            self.EntryMacdSigDelt = 0.0 
            self.EntryMacdHist = 0.0
            self.EntryMacdCurrent = 0.0
            self.EntrySpreadPips = 0.0
            self.EntryCandlePips = 0.0
            self.EntryADXTrend4H = 'Nothing'
            self.EntryADXTrend1H = 'Nothing'
            self.low_time = None
            self.high_time = None
            self.max_pipsprofit = 0.0
            self.max_pipsloss = 0.0
            self.CurrentRes = ChartRes.res24H
            self.Trend24H = StratDirection.Nothing
            self.Trend4H = StratDirection.Nothing
            self.Trend1H = StratDirection.Nothing
            self.Trend15M = StratDirection.Nothing
            self.Trend5M = StratDirection.Nothing
            self.manualTradeFound = False
            self.manualTradeOn = False
            self.manualTradeConditional = False
            self.manualBounceTrade = False
            # self.manualTradeID = 0  -- do not  clear this one down
            self.manualDirection = False
            self.manualLotSize = 0
            self.manualTradeDate = None
            self.manualTradeHour = None
            self.manualTradeMinute = None
            self.manualExpectedEntry = 0.0
            self.manualCheckMinutes = 0
            self.tradedToday = 0
            self.narniasign = False
            self.manual_fti_sign = False
            self.type_of_trade_found = Strats.Nothing
            self.trade_label_current = ""

            self.ftichangestop = False
            self.ftichangepips = 0.0
            self.ftichangeprofit = False
            self.ftichangeprofitpips = 0.0
            self.trading_move_to_be_flag = False
            self.trading_move_to_be_profit_pips = 0.0
            self.trading_move_to_be_new_stop_pips = 0.0
            self.trading_move_to_be_done = False
            self.trading_stop_allow_ratchet = True
            self.tradePoints = 0.0
            self.fti_in_control = False
            self.Ceil123R_1H = 0.0
            self.Floor123G_1H = 0.0
            self.Ceil123R_30M = 0.0
            self.Floor123G_30M = 0.0
            self.perfectPoints_30M = 0.0
            self.perfectPoints_1HR = 0.0
            self.AlertedPerfect_Short_1HR = False
            self.AlertedPerfect_Long_1HR = False
            self.AlertedPerfect_Short_30M = False
            self.AlertedPerfect_Long_30M = False
            self.channel_weakness_found_1M = False
            self.channel_weakness_found_5M = False
            self.channel_weakness_found_15M = False
            self.channel_weakness_found_30M = False
            self.channel_weakness_found_1HR = False    
            self.TriggerCandleWindow_1HR = -1
            self.TriggerCandleWindow_30M = -1   
            self.channel_take_profit_pips = 0.0
            self.channel_stop_loss_price = 0.0 
            self.channel_trigger_price = 0.0
            self.set_specific_stop_loss = False
            self.set_specific_take_profit = False
            self.currentPosition = 0.0
            self.state_of_symbol = SymbolStates.looking


    
    # look for 123G Narnia with total candles of a certain size   
    def Is123GNarnia(self, mybars, mycolours, totalpips, pipsize, profit_factor):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN):
            barlen = (mybars[0].Bid.Close  - mybars[2].Bid.Open) / pipsize
            takeprofit = 0.0
            if barlen >= totalpips:
                # now we have a long enough section of 3 GREEN candles
                #nentry = round(mybars[1].Bid.Open, 5)
                nentry = round(mybars[0].Bid.Close, 5) #Si earlier entry on the E1 open
                nstop = round(mybars[0].Bid.High, 5)
                takeprofit = round((abs(nentry - nstop)/pipsize) * profit_factor, 1)
                if takeprofit < 15.0:
                    takeprofit = 15.0
                return (True, nentry, nstop, takeprofit)
        return (False, 0.0, 0.0, 0.0)
        
        
    # look for 123R Narnia with total candles of a certain size   
    def Is123RNarnia(self, mybars, mycolours, totalpips, pipsize, profit_factor):
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, RED):
            barlen = (mybars[2].Bid.Open  - mybars[0].Bid.Close) / pipsize
            takeprofit = 0.0
            if barlen >= totalpips:
                # now we have a long enough section of 3 RED candles
                #nentry = round(mybars[1].Bid.Open, 5)
                nentry = round(mybars[0].Bid.Close, 5) #Si earlier entry
                nstop = round(mybars[0].Bid.Low, 5) #Si currently overwriting to 20 pips in code where order placed
                takeprofit = round((abs(nentry - nstop)/pipsize) * profit_factor, 1)
                if takeprofit < 15.0:
                    takeprofit = 15.0
                return (True, nentry, nstop, takeprofit)
        return (False, 0.0, 0.0, 0.0)

    # look for 123G-then R through Numbers - and then this could be a LionShort
    def IsLionShort(self, mybars, mycolours, myemas, pipsize):
        if mycolours[0] == RED:
            barlen = (mybars[0].Bid.Open  - mybars[0].Bid.Close) / pipsize
            closelen = (mybars[0].Bid.Close  - mybars[0].Bid.Low) / pipsize
            if barlen > 6.0:
                # we have a 6 pip or greater bar for engulfing
                if mybars[0].Bid.Close < mybars[1].Bid.Low:
                    #this is the definition of a short engulfing candle
                    nextnumdown = self.NumbersBelow(mybars[0].Bid.Open)
                    nextnumup = self.NumbersAbove(mybars[0].Bid.Close)
                    if nextnumdown >= nextnumup:   # we have crossed numbers in the R
                        # now check if EMA is inside body
                        if self.DoesEMACross(mybars[0], myemas[0]):
                            #now need to check we did not close within 0.1 pips of the Low (ran out of steam)
                            if closelen > 0.1:
                                disttonumbelow = (mybars[0].Bid.Close - self.NumbersBelow(mybars[0].Bid.Close)) / pipsize 
                                if disttonumbelow > 10.0:
                                    # don't mark a Lion if we are within 10 pips of Numbers at the close
                                    return True
        return False
            
    # look for 123R-then G through Numbers - and then this could be a LionLong
    def IsLionLong(self, mybars, mycolours, myemas, pipsize):
        if mycolours[0] == GREEN:
            barlen = (mybars[0].Bid.Close  - mybars[0].Bid.Open) / pipsize
            closelen = (mybars[0].Bid.High  - mybars[0].Bid.Close) / pipsize
            if barlen > 6.0:
                # we have a 6 pip or greater bar - now need to look for engulfing
                if mybars[0].Bid.Close > mybars[1].Bid.High:
                    #this is the definition of a Long engulfing candle
                    nextnumdown = self.NumbersBelow(mybars[0].Bid.Close)
                    nextnumup = self.NumbersAbove(mybars[0].Bid.Open)
                    if nextnumdown >= nextnumup:   # we have crossed numbers in the G
                        # now check if EMA is inside body
                        if self.DoesEMACross(mybars[0], myemas[0]):
                            #now need to check we did not close within 0.1 pips of the High (ran out of steam)
                            if closelen > 0.1:
                                disttonumabove = (self.NumbersAbove(mybars[0].Bid.Close) - mybars[0].Bid.Close) / pipsize 
                                if disttonumabove > 10.0:
                                    return True
        return False



    # Look for a Doji at most recent candle
    def IsDoji(self, mybars, mycolours):
        candleratio = 0.15       # open and close shouldn't be more than 15% of total length
        wickratio = 0.01
        wtop = mybars[0].Bid.High
        wbottom = mybars[0].Bid.Low
        ctop = 0.0
        cbottom = 0.0
        if mycolours[0] == GREEN:
            ctop = mybars[0].Bid.Close
            cbottom = mybars[0].Bid.Open
        if mycolours[0] == RED:
            ctop = mybars[0].Bid.Open
            cbottom = mybars[0].Bid.Close
        candledist = ctop - cbottom
        wickdist = wtop - wbottom
        if wickdist == 0.0 : return False                       # basically a zero wick
        if candledist / wickdist > candleratio : return False   # candle is too fat to be a Doji
        fromtop = wtop - ctop
        frombottom = cbottom - wbottom
        if fromtop / wickdist < wickratio : return False        # too near the top
        if frombottom / wickdist < wickratio : return False     # too near the bottom
        # we now have only the Doji possibility left
        return True

        # Look for a Hammer
    def IsHammer(self, mybars, mycolours):
        candleratio = 0.25
        wickratio = 0.2
        wtop = mybars[0].Bid.High
        wbottom = mybars[0].Bid.Low
        ctop = 0.0
        cbottom = 0.0
        if mycolours[0] == GREEN:
            ctop = mybars[0].Bid.Close
            cbottom = mybars[0].Bid.Open
        if mycolours[0] == RED:
            ctop = mybars[0].Bid.Open
            cbottom = mybars[0].Bid.Close
        #nextnumdown = self.NumbersBelow(wtop)
        #nextnumup = self.NumbersAbove(wbottom)
        #if nextnumdown >= nextnumup:
        # did cross numbers
        candledist = ctop - cbottom
        wickdist = wtop - wbottom
        if wickdist == 0.0 : return False
        fromtop = wtop - ctop
        if (candledist / wickdist) < candleratio and (fromtop / wickdist) < wickratio:
            # we now have a small candle, near to the top
            return True
        return False
        
    # Look for a ReverseHammer
    def IsReverseHammer(self, mybars, mycolours):
        candleratio = 0.25
        wickratio = 0.2
        wtop = mybars[0].Bid.High
        wbottom = mybars[0].Bid.Low
        ctop = 0.0
        cbottom = 0.0
        if mycolours[0] == GREEN:
            ctop = mybars[0].Bid.Close
            cbottom = mybars[0].Bid.Open
        if mycolours[0] == RED:
            ctop = mybars[0].Bid.Open
            cbottom = mybars[0].Bid.Close
        #nextnumdown = self.NumbersBelow(wtop)
        #nextnumup = self.NumbersAbove(wbottom)
        #if nextnumdown >= nextnumup:
            # did cross numbers
        candledist = ctop - cbottom
        wickdist = wtop - wbottom
        if wickdist == 0.0 : return False
        frombottom = cbottom - wbottom
        if (candledist / wickdist) < candleratio and (frombottom / wickdist) < wickratio:
            # we now have a small candle, near to the bottom
            return True
        return False


    '''this is fired on a timed event - when the candle closes and in a Narnia, this is used to close the trade
    will be superceded by better trade management
    '''
    def CloseNarniaIfOpen(self):
        '''
        this should now fire for the correct SymbolData instance
        '''
        if self.narniasign and self.manualTradeOn:
            # we have a trade open - close it down
            self.my_algo.Transactions.CancelOpenOrders("GBPUSD")
            self.my_algo.Liquidate("GBPUSD")
            self.ClearTracking()
            self.my_algo.LiveTradeCount -= 1
            if self.my_algo.LiveTradeCount < 0:
                self.my_algo.LiveTradeCount = 0

            
    def DidPriceMoveStraightUp(self, pip_move, pip_size, num_periods, my_bars, my_colours):
            # returns True/False, Low_of_Tip, Highest_Price, Starting_Price of move up, pips moved up, hours of the rise
            # work out whether over the number of bars defined by num_periods if the price moved more than pip_move pips upwards
            # without being broken by a RED candle closing below a previous Low
            maybe_low = False
            bar_count = 1
            tip_low_1 = 0.0
            lowest_low_seen = 0.0
            highest_high_seen = 0.0
            if my_colours[0] == RED and my_bars[0].Bid.Close < my_bars[1].Bid.Low:
                maybe_low = True
                highest_high_seen = my_bars[0].Bid.High
                tip_low_1 = my_bars[0].Bid.Close
                lowest_low_seen = my_bars[0].Bid.Close
                for i in range(1, num_periods-1):
                    bar_count += 1
                    if my_colours[i] == GREEN:
                        # we know price is moving up - so update values and move on
                        if my_bars[i].Bid.High > highest_high_seen:
                            highest_high_seen = my_bars[i].Bid.Close        # top of GREEN body
                        if my_bars[i].Bid.Low < lowest_low_seen:
                            lowest_low_seen = my_bars[i].Bid.Low
                    else:
                        # the price drop run may have been broken
                        if my_bars[i].Bid.Close < my_bars[i+1].Bid.Low:
                            # this is the start of the run - stop counting here
                            bar_count -= 1
                            break
                        if my_bars[i].Bid.Low < lowest_low_seen:
                            lowest_low_seen = my_bars[i].Bid.Low
                        if my_bars[i].Bid.High > highest_high_seen:
                            highest_high_seen = my_bars[i].Bid.Open         # top of RED body
                price_diff = highest_high_seen - lowest_low_seen
                pip_move_seen = round(price_diff / pip_size, 1)
                if pip_move_seen >= pip_move:
                    # now we want to report the move down
                    # returns True/False, High_of_Lip, Lowest_Price, Starting_Price of move down, pips moved down
                    return (True, tip_low_1, highest_high_seen, lowest_low_seen, pip_move_seen, bar_count)
                else:
                    return (False, 0.0, 0.0, 0.0, 0, 0)
            return (False, 0.0, 0.0, 0.0, 0, 0)

        
    def DidPriceMoveStraightDown(self, pip_move, pip_size, num_periods, my_bars, my_colours):
        # returns True/False, High_of_Lip, Lowest_Price, Starting_Price of move down, pips moved down, hours of the drop
        # work out whether over the number of bars defined by num_periods if the price moved more than pip_move pips downwards
        # without being broken by a GREEN candle closing over a previous High.
        maybe_high = False
        bar_count = 1
        trough_high_1 = 0.0
        lowest_low_seen = 0.0
        highest_high_seen = 0.0
        if my_colours[0] == GREEN and my_bars[0].Bid.Close > my_bars[1].Bid.High:
            maybe_high = True
            lowest_low_seen = my_bars[0].Bid.Low
            trough_high_1 = my_bars[0].Bid.Close
            highest_high_seen = my_bars[0].Bid.Close
            for i in range(1, num_periods-1):
                bar_count += 1
                if my_colours[i] == RED:
                    # we know price is moving down - so update values and move on
                    if my_bars[i].Bid.Low < lowest_low_seen:
                        lowest_low_seen = my_bars[i].Bid.Close          # base of RED candle body
                    if my_bars[i].Bid.High > highest_high_seen:
                        highest_high_seen = my_bars[i].Bid.High
                else:
                    # the price drop run may have been broken
                    if my_bars[i].Bid.Close > my_bars[i+1].Bid.High:
                        # this is the start of the run - stop counting here
                        bar_count -= 1
                        break
                    if my_bars[i].Bid.Low < lowest_low_seen:
                        lowest_low_seen = my_bars[i].Bid.Open           #base of GREEN candle body
                    if my_bars[i].Bid.High > highest_high_seen:
                        highest_high_seen = my_bars[i].Bid.High
            price_diff = highest_high_seen - lowest_low_seen
            pip_move_seen = round(price_diff / pip_size, 1)
            if pip_move_seen >= pip_move:
                # now we want to report the move down
                # returns True/False, High_of_Lip, Lowest_Price, Starting_Price of move down, pips moved down
                return (True, trough_high_1, lowest_low_seen, highest_high_seen, pip_move_seen, bar_count)
            else:
                return (False, 0.0, 0.0, 0.0, 0, 0)
        return (False, 0.0, 0.0, 0.0, 0, 0)
        
        
    def IsPriceMidDrop(self, pip_move, pip_size, min_periods, num_periods, my_bars, my_colours):
        bar_count = 1
        lowest_low_seen = 0.0
        highest_high_seen = 0.0
        if my_colours[0] == GREEN and my_bars[0].Bid.Close > my_bars[1].Bid.High:
            # Already found the lip - not still mid-move
            return (False, 0.0)
        else:
            if my_colours[0] == GREEN:
                highest_high_seen = my_bars[0].Bid.Close
                lowest_low_seen = my_bars[0].Bid.Open
            else:
                highest_high_seen = my_bars[0].Bid.Open
                lowest_low_seen = my_bars[0].Bid.Close
            for i in range(1, num_periods-1):
                bar_count += 1
                if my_colours[i] == RED:
                    # we know price is moving down - so update values and move on
                    if my_bars[i].Bid.Close < lowest_low_seen:
                        lowest_low_seen = my_bars[i].Bid.Close          # base of RED candle body
                    if my_bars[i].Bid.Open > highest_high_seen:
                        highest_high_seen = my_bars[i].Bid.Open
                else:
                    # the price drop run may have been broken
                    if my_bars[i].Bid.Close > my_bars[i+1].Bid.High:
                        # we need a minimum number of bars involved in the drop - if we don't reach the end then return
                        if i < min_periods:
                            return (False, 0.0)
                        else:
                            break
                    if my_bars[i].Bid.Open < lowest_low_seen:
                        lowest_low_seen = my_bars[i].Bid.Open           #base of GREEN candle body
                    if my_bars[i].Bid.Close > highest_high_seen:
                        highest_high_seen = my_bars[i].Bid.Close
            price_diff = highest_high_seen - lowest_low_seen
            pip_move_seen = round(price_diff / pip_size, 1)
            if pip_move_seen >= pip_move:
                # now we want to report the move down
                # returns True/False, pips moved down
                return (True, pip_move_seen)
            else:
                return (False, 0.0)
        return (False, 0.0)    
        
    
    def IsPriceMidRise(self, pip_move, pip_size, min_periods, num_periods, my_bars, my_colours):
        bar_count = 1
        lowest_low_seen = 0.0
        highest_high_seen = 0.0
        if my_colours[0] == RED and my_bars[0].Bid.Close < my_bars[1].Bid.Low:
            # Already found the lip - not still mid-move
            return (False, 0.0)
        else:
            if my_colours[0] == GREEN:
                highest_high_seen = my_bars[0].Bid.Close
                lowest_low_seen = my_bars[0].Bid.Open
            else:
                highest_high_seen = my_bars[0].Bid.Open
                lowest_low_seen = my_bars[0].Bid.Close
            for i in range(1, num_periods-1):
                bar_count += 1
                if my_colours[i] == GREEN:
                    # we know price is moving up - so update values and move on
                    if my_bars[i].Bid.Open < lowest_low_seen:
                        lowest_low_seen = my_bars[i].Bid.Open          
                    if my_bars[i].Bid.Close > highest_high_seen:
                        highest_high_seen = my_bars[i].Bid.Close
                else:
                    # the price rise run may have been broken
                    if my_bars[i].Bid.Close < my_bars[i+1].Bid.Low:
                        # we need a minimum number of bars involved in the drop - if we don't reach the end then return
                        if i < min_periods:
                            return (False, 0.0)
                        else:
                            break
                    if my_bars[i].Bid.Close < lowest_low_seen:
                        lowest_low_seen = my_bars[i].Bid.Close           
                    if my_bars[i].Bid.Open > highest_high_seen:
                        highest_high_seen = my_bars[i].Bid.Open
            price_diff = highest_high_seen - lowest_low_seen
            pip_move_seen = round(price_diff / pip_size, 1)
            if pip_move_seen >= pip_move:
                # now we want to report the move up
                # returns True/False, pips moved up
                return (True, pip_move_seen)
            else:
                return (False, 0.0)
        return (False, 0.0)       



    def UpdateSessions(self, sender, my_time, ask_price_now, bid_price_now, logging=False): #si 11.0 --> need to figure out the current session
            #lets start the basis on winter time - where US is -5 from UTC
            # TODO: make sure to update session start/end times for summer time changes 
            # TODO: add session length info somewhere, for easy ref
            # TODO: create simple helper functions for last session pip move, current session pip move and time into current session, current session prediction
            my_hour = my_time.hour
            SessionOpen = False
            pip_size = self.minPriceVariation * 10
            if my_hour >= 21:
                if my_hour == 21: #reset high lows on session entry
                    session_avg = self.historic_sessions.get_averages(SessionNames.Asia)
                    self.live_sessions[SessionNames.Asia].start_session(SessionNames.Asia, bid_price_now, ask_price_now, my_time, pip_size, session_avg)
                    self.current_session = SessionNames.Asia
                    self.live_sessions[SessionNames.Pre_Asia].end_session(bid_price_now, ask_price_now, my_time)
                    self.previous_session = SessionNames.Pre_Asia
                    self.historic_sessions.add_completed_session(self.live_sessions[SessionNames.Pre_Asia])

                    if logging and not sender.IsWarmingUp: sender.Log(self.live_sessions[SessionNames.Pre_Asia].dump_session())
                    SessionOpen = True
                return SessionNames.Asia, SessionNames.Pre_Asia, SessionOpen
            else:
                if my_hour >= 0 and my_hour < 1:
                    return SessionNames.Asia, SessionNames.Pre_Asia, SessionOpen        # this is the later part of the Asia session
                elif my_hour >= 1 and my_hour < 5:
                    if my_hour == 1:
                        # start of EUROPE session - so log out ASIA session highs/lows
                        session_avg = self.historic_sessions.get_averages(SessionNames.Europe)
                        self.live_sessions[SessionNames.Europe].start_session(SessionNames.Europe, bid_price_now, ask_price_now, my_time, pip_size, session_avg)
                        self.current_session = SessionNames.Europe
                        self.live_sessions[SessionNames.Asia].end_session(bid_price_now, ask_price_now, my_time)
                        self.previous_session = SessionNames.Asia
                        self.historic_sessions.add_completed_session(self.live_sessions[SessionNames.Asia])
                        
                        if logging and not sender.IsWarmingUp: sender.Log(self.live_sessions[SessionNames.Asia].dump_session())
                    if my_hour == 1 or my_hour == 2:
                        SessionOpen = True
                    return SessionNames.Europe, SessionNames.Asia, SessionOpen
                elif my_hour >= 5 and my_hour < 9:
                    if my_hour == 5:
                        # start of GAP session - so log out Europe session highs/lows
                        session_avg = self.historic_sessions.get_averages(SessionNames.Pre_US)
                        self.live_sessions[SessionNames.Pre_US].start_session(SessionNames.Pre_US, bid_price_now, ask_price_now, my_time, pip_size, session_avg)
                        self.current_session = SessionNames.Pre_US
                        self.live_sessions[SessionNames.Europe].end_session(bid_price_now, ask_price_now, my_time)
                        self.previous_session = SessionNames.Europe
                        self.historic_sessions.add_completed_session(self.live_sessions[SessionNames.Europe])

                        if logging and not sender.IsWarmingUp: sender.Log(self.live_sessions[SessionNames.Europe].dump_session())
                    return SessionNames.Pre_US, SessionNames.Europe, SessionOpen   
                elif my_hour >= 9 and my_hour < 13:
                    if my_hour == 9:
                        # start of US session - so log out GAP session highs/lows
                        session_avg = self.historic_sessions.get_averages(SessionNames.US)
                        self.live_sessions[SessionNames.US].start_session(SessionNames.US, bid_price_now, ask_price_now, my_time, pip_size, session_avg)
                        self.current_session = SessionNames.US
                        self.live_sessions[SessionNames.Pre_US].end_session(bid_price_now, ask_price_now, my_time)
                        self.previous_session = SessionNames.Pre_US
                        self.historic_sessions.add_completed_session(self.live_sessions[SessionNames.Pre_US])

                        if logging and not sender.IsWarmingUp: sender.Log(self.live_sessions[SessionNames.Pre_US].dump_session())
                        SessionOpen = True
                    return SessionNames.US, SessionNames.Pre_US, SessionOpen
                else:
                    if my_hour == 13:
                        # end of US session - so log out US session highs/lows
                        session_avg = self.historic_sessions.get_averages(SessionNames.Pre_Asia)
                        self.live_sessions[SessionNames.Pre_Asia].start_session(SessionNames.Pre_Asia, bid_price_now, ask_price_now, my_time, pip_size, session_avg)
                        self.current_session = SessionNames.Pre_Asia
                        self.live_sessions[SessionNames.US].end_session(bid_price_now, ask_price_now, my_time)
                        self.previous_session = SessionNames.US
                        self.historic_sessions.add_completed_session(self.live_sessions[SessionNames.US])

                        if logging and not sender.IsWarmingUp: sender.Log(self.live_sessions[SessionNames.US].dump_session())
                    if my_hour == 19:  #Japan opens
                        SessionOpen = True
                    return SessionNames.Pre_Asia, SessionNames.US, SessionOpen    
        


    def UpdateSessionsHighsLows(self, ask_price_low, ask_price_high, bid_price_low, bid_price_high, time_now): 
        if self.current_session == SessionNames.Asia:
            self.live_sessions[SessionNames.Asia].update_sessions(ask_price_low, ask_price_high, bid_price_low, bid_price_high, time_now)
        elif self.current_session == SessionNames.Europe:
            self.live_sessions[SessionNames.Europe].update_sessions(ask_price_low, ask_price_high, bid_price_low, bid_price_high, time_now)
        elif self.current_session == SessionNames.Pre_US:
            self.live_sessions[SessionNames.Pre_US].update_sessions(ask_price_low, ask_price_high, bid_price_low, bid_price_high, time_now)
        elif self.current_session == SessionNames.US:
            self.live_sessions[SessionNames.US].update_sessions(ask_price_low, ask_price_high, bid_price_low, bid_price_high, time_now)
        elif self.current_session == SessionNames.Pre_Asia:
            self.live_sessions[SessionNames.Pre_Asia].update_sessions(ask_price_low, ask_price_high, bid_price_low, bid_price_high, time_now)

        
    def get_smart_session_low_time_and_price(self, session= "current", compare_price=0.0, bar_tolerance=3):
        if session == "current":
            bar_of_current = 0
            bar_of_current = self.live_sessions[self.current_session].session_bar
            session_to_use = self.current_session

            if bar_of_current < bar_tolerance // 3:
                # not enough bars in the session to use
                return (None, 0.0)

            # now return the low time and price of the relevant session
            return self.live_sessions[session_to_use].low_time, self.live_sessions[session_to_use].low_bid
        elif session == "prev":
            # now return the low time and price of the relevant session
            if self.previous_session == SessionNames.Pre_US and compare_price >= self.live_sessions[SessionNames.Europe].low_bid:
                return self.live_sessions[SessionNames.Europe].low_time, self.live_sessions[SessionNames.Europe].low_bid
            elif self.previous_session == SessionNames.Pre_US and compare_price < self.live_sessions[SessionNames.Europe].low_bid:                
                return self.live_sessions[SessionNames.Asia].low_time, self.live_sessions[SessionNames.Asia].low_bid
            
            elif self.previous_session == SessionNames.Pre_Asia and compare_price >= self.live_sessions[SessionNames.US].low_bid:
                return self.live_sessions[SessionNames.US].low_time, self.live_sessions[SessionNames.US].low_bid
            elif self.previous_session == SessionNames.Pre_Asia and compare_price < self.live_sessions[SessionNames.US].low_bid:
                return self.live_sessions[SessionNames.Europe].low_time, self.live_sessions[SessionNames.Europe].low_bid
            else:
                if compare_price >= self.live_sessions[self.previous_session].low_bid:
                    return self.live_sessions[self.previous_session].low_time, self.live_sessions[self.previous_session].low_bid
                else:
                    if self.previous_session == SessionNames.Asia:
                        return self.live_sessions[SessionNames.US].low_time, self.live_sessions[SessionNames.US].low_bid
                    elif self.previous_session == SessionNames.Europe:
                        return self.live_sessions[SessionNames.Asia].low_time, self.live_sessions[SessionNames.Asia].low_bid
                    elif self.previous_session == SessionNames.US:
                        return self.live_sessions[SessionNames.Europe].low_time, self.live_sessions[SessionNames.Europe].low_bid
        else:
            return(None, 0.0)
        

    def get_smart_session_high_time_and_price(self, session="current", compare_price=0.0, bar_tolerance=3):
        if session == "current":
            bar_of_current = 0
            bar_of_current = self.live_sessions[self.current_session].session_bar
            session_to_use = self.current_session

            if bar_of_current < bar_tolerance // 3:
                # not enough bars in this session to use
                return(None, 0.0)

            # now return the high time and price of the relevant session
            return self.live_sessions[session_to_use].high_time, self.live_sessions[session_to_use].high_bid
        elif session == "prev":
            # now return the high time and price of the relevant session
            if self.previous_session == SessionNames.Pre_US and compare_price <= self.live_sessions[SessionNames.Europe].high_bid:
                return self.live_sessions[SessionNames.Europe].high_time, self.live_sessions[SessionNames.Europe].high_bid
            elif self.previous_session == SessionNames.Pre_US and compare_price > self.live_sessions[SessionNames.Europe].high_bid:                
                return self.live_sessions[SessionNames.Asia].high_time, self.live_sessions[SessionNames.Asia].high_bid
            
            elif self.previous_session == SessionNames.Pre_Asia and compare_price <= self.live_sessions[SessionNames.US].high_bid:
                return self.live_sessions[SessionNames.US].high_time, self.live_sessions[SessionNames.US].high_bid
            elif self.previous_session == SessionNames.Pre_Asia and compare_price > self.live_sessions[SessionNames.US].high_bid:
                return self.live_sessions[SessionNames.Europe].high_time, self.live_sessions[SessionNames.Europe].high_bid
            else:
                if compare_price <= self.live_sessions[self.previous_session].high_bid:
                    return self.live_sessions[self.previous_session].high_time, self.live_sessions[self.previous_session].high_bid
                else:
                    if self.previous_session == SessionNames.Asia:
                        return self.live_sessions[SessionNames.US].high_time, self.live_sessions[SessionNames.US].high_bid
                    elif self.previous_session == SessionNames.Europe:
                        return self.live_sessions[SessionNames.Asia].high_time, self.live_sessions[SessionNames.Asia].high_bid
                    elif self.previous_session == SessionNames.US:
                        return self.live_sessions[SessionNames.Europe].high_time, self.live_sessions[SessionNames.Europe].high_bid
        else:
            return(None, 0.0)


    # track back through the bars, find the one after the time at which the low price was formed, and gount consecutive greens
    def count_greens_from_low(self, mybars, mycolours, low_time, low_price):
        count = 0
        x_value = 0.0
        found_it = -1
        for i in range(mybars.Count):
            if mybars[i].Time <= low_time:
                found_it = i-1
                break
        if found_it >= 0:
            if mycolours[found_it+1] == GREEN:
                # the low bar was actually set by a green, so wind the counter back by 1
                found_it += 1
            # now find X which will be the HIGH of the red candle which is followed by the GREENs - ie the candle to the left
            x_value = mybars[found_it+1].Bid.High
            for i in range(found_it, 0, -1):
                if mycolours[i] == GREEN:
                    count += 1
                else:
                    break
        return (count, x_value)

    # track back through the bars, find the one after the time at which the high price was formed, and gount consecutive reds
    def count_reds_from_high(self, mybars, mycolours, high_time, high_price):
        count = 0
        x_value = 0.0
        found_it = -1
        for i in range(mybars.Count):
            if mybars[i].Time <= high_time:
                found_it = i-1
                break
        if found_it >= 0:
            if mycolours[found_it+1] == RED:
                # the high bar was actually set by a red, so wind the counter back by 1
                found_it += 1
            # now find X which will be the LOW of the green candle which is followed by the REDs - ie the candle to the left
            x_value = mybars[found_it+1].Bid.Low
            for i in range(found_it, 0, -1):
                if mycolours[i] == RED:
                    count += 1
                else:
                    break
        return (count, x_value)