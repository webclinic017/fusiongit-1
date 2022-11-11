#region imports
from AlgorithmImports import *
from requests import session
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
from turningpoints import *
from brad_turning_points import *
from session_boxes import *
from external_structure import *
from price_tracker import *
from fusion_utils import *
from external_structure import *
from builder_perfect import *
from dataclasses import dataclass
from symbol_info_1 import SymbolData_1
from symbol_info_2 import SymbolData_2
from manage_perfect import manage_perfect

import pytz

    

class SymbolData(SymbolData_1, SymbolData_2):
    
    def __init__(self, symbol, barPeriod, WindowSize1M, WindowSize5M, WindowSize15M, WindowSize30M, WindowSize1H, WindowSize4H, WindowSize24H):
        self.Symbol = symbol
        
        self.my_algo = None
        # The period used when population the Bars rolling window
        self.BarPeriod = barPeriod
        
        # A rolling window of data, data needs to be pumped into Bars by using Bars.Update( quoteBar ) [as FX] and can be accessed like:
        # SymbolData.Bars[0] - most first recent piece of data
        # SymbolData.Bars[5] - the sixth most recent piece of data (zero based indexing)
        self.Bars1M = RollingWindow[IBaseDataBar](WindowSize1M)
        self.Bars5M = RollingWindow[IBaseDataBar](WindowSize5M)
        self.Bars15M = RollingWindow[IBaseDataBar](WindowSize15M)
        self.Bars30M = RollingWindow[IBaseDataBar](WindowSize30M)
        self.Bars1H = RollingWindow[IBaseDataBar](WindowSize1H)
        self.Bars4H = RollingWindow[IBaseDataBar](WindowSize4H)
        self.Bars24H = RollingWindow[IBaseDataBar](WindowSize24H)
        
        self.Bars1MColour = RollingWindow[int](WindowSize1M)
        self.Bars5MColour = RollingWindow[int](WindowSize5M)
        self.Bars15MColour = RollingWindow[int](WindowSize15M)
        self.Bars30MColour = RollingWindow[int](WindowSize30M)
        self.Bars1HColour = RollingWindow[int](WindowSize1H)     
        self.Bars4HColour = RollingWindow[int](WindowSize4H)     
        self.Bars24HColour = RollingWindow[int](WindowSize24H)     
        
        # The exponential moving average indicators for our symbol at the different time horizons
        #Si extra EMAs
        self.EMA1M_45 = None
        self.EMA1M_135 = None
        self.EMA1M_200 = None
        self.EMA5M_27 = None
        self.EMA15M_200 = None
        self.emaWindow1M_45 = RollingWindow[IndicatorDataPoint](WindowSize1M)
        self.emaWindow1M_135 = RollingWindow[IndicatorDataPoint](WindowSize1M)
        self.emaWindow1M_200 = RollingWindow[IndicatorDataPoint](WindowSize1M)
        self.emaWindow5M_27 = RollingWindow[IndicatorDataPoint](WindowSize5M)  
        self.emaWindow15M_200 = RollingWindow[IndicatorDataPoint](WindowSize15M)
       

        self.EMA1M = None
        self.newEma1MAvailable = False
        self.emaWindow1M = RollingWindow[IndicatorDataPoint](WindowSize1M)
        self.EMA5M = None
        self.newEma5MAvailable = False
        self.emaWindow5M = RollingWindow[IndicatorDataPoint](WindowSize5M)
        self.EMA15M = None
        self.newEma15MAvailable = False
        self.emaWindow15M = RollingWindow[IndicatorDataPoint](WindowSize15M)
        self.EMA30M = None
        self.newEma30MAvailable = False
        self.emaWindow30M = RollingWindow[IndicatorDataPoint](WindowSize30M)
        self.EMA1H = None
        self.newEma1HAvailable = False
        self.emaWindow1H = RollingWindow[IndicatorDataPoint](WindowSize1H)
        self.emaWindow1H_of_4H = RollingWindow[IndicatorDataPoint](WindowSize1H)
        self.EMA4H = None
        self.newEma4HAvailable = False
        self.emaWindow4H = RollingWindow[IndicatorDataPoint](WindowSize4H)
        self.EMA24H = None
        self.newEma24HAvailable = False
        self.emaWindow24H = RollingWindow[IndicatorDataPoint](WindowSize24H)
        
        self.ADX1H = None
        self.ADX4H = None
        self.ATR24H = None
    
        # add 4Hr MACD
        self.Macd4H = None
        self.newMacd4HAvailable = False
        self.MacdFastWindow4H = RollingWindow[IndicatorDataPoint](WindowSize4H)
        self.MacdSlowWindow4H = RollingWindow[IndicatorDataPoint](WindowSize4H)
        self.MacdSignalWindow4H = RollingWindow[IndicatorDataPoint](WindowSize4H)
        self.MacdCurrentWindow4H = RollingWindow[IndicatorDataPoint](WindowSize4H)
        self.MacdHistWindow4H = RollingWindow[IndicatorDataPoint](WindowSize4H)
        #self.MacdTolerance = 0.00025   --this was the value when using signaldelta
        self.MacdTolerance = 4      # want Histogram to be 4 pips or more to indicate a Trend strong enough
        
        # Tracking values to see what Chart resolution we are looking at, and whether a Long/Short indicator has been found
        self.CurrentRes = ChartRes.res24H        # start on 1hr so we see stuff on the first day of live algo start
        self.Trend24H = Trends.Nothing
        self.Trend4H = Trends.Nothing
        self.Trend1H = Trends.Nothing
        self.Trend30M = Trends.Nothing
        self.Trend15M = Trends.Nothing
        self.Trend5M = Trends.Nothing
        
        # Lists for storing Toughs and Peaks
        self.possible_TLs_1H = [turning_point('First TL 1H', 'TROUGH', ChartRes.res1H)]
        self.possible_PHs_1H = [turning_point('First PH 1H', 'PEAK', ChartRes.res1H)]
        self.confirmed_TLs_1H = []
        self.confirmed_PHs_1H = []
        self.confirmed_turns_1H = []
        
        self.possible_TLs_30M = [turning_point('First TL 30M', 'TROUGH', ChartRes.res30M)]
        self.possible_PHs_30M = [turning_point('First PH 30M', 'PEAK', ChartRes.res30M)]
        self.confirmed_TLs_30M = []
        self.confirmed_PHs_30M = []

        self.possible_TLs_5M = [turning_point('First TL 5M', 'TROUGH', ChartRes.res5M)]
        self.possible_PHs_5M = [turning_point('First PH 5M', 'PEAK', ChartRes.res5M)]
        self.confirmed_TLs_5M = []
        self.confirmed_PHs_5M = []

        self.possible_TLs_1M = [turning_point('First TL 1M', 'TROUGH', ChartRes.res1M)]
        self.possible_PHs_1M = [turning_point('First PH 1M', 'PEAK', ChartRes.res1M)]
        self.confirmed_TLs_1M = []
        self.confirmed_PHs_1M = []

        # Dictionary for storing lists of Brad peaks for different resolutions
        self.brad_peak_tracker = {ChartRes.res24H:      [],
                              ChartRes.res4H:       [],
                              ChartRes.res1H:       [],
                              ChartRes.res30M:      [],
                              ChartRes.res15M:      [],
                              ChartRes.res5M:       [],
                              ChartRes.res1M:       []}

        # this is the filtered list to honour the Breakout rules
        self.brad_peak_clean_long_tracker = {ChartRes.res24H:      [],
                              ChartRes.res4H:       [],
                              ChartRes.res1H:       [],
                              ChartRes.res30M:      [],
                              ChartRes.res15M:      [],
                              ChartRes.res5M:       [],
                              ChartRes.res1M:       []}

        self.brad_peak_clean_short_tracker = {ChartRes.res24H:      [],
                              ChartRes.res4H:       [],
                              ChartRes.res1H:       [],
                              ChartRes.res30M:      [],
                              ChartRes.res15M:      [],
                              ChartRes.res5M:       [],
                              ChartRes.res1M:       []}


        # Dictionary for storing lists of Brad troughs for different resolutions
        self.brad_trough_tracker = {ChartRes.res24H:      [],
                                ChartRes.res4H:       [],
                                ChartRes.res1H:       [],
                                ChartRes.res30M:      [],
                                ChartRes.res15M:      [],
                                ChartRes.res5M:       [],
                                ChartRes.res1M:       []}

        # this is the filtered list to honour the Breakout rules
        self.brad_trough_clean_long_tracker = {ChartRes.res24H:      [],
                                ChartRes.res4H:       [],
                                ChartRes.res1H:       [],
                                ChartRes.res30M:      [],
                                ChartRes.res15M:      [],
                                ChartRes.res5M:       [],
                                ChartRes.res1M:       []}

        self.brad_trough_clean_short_tracker = {ChartRes.res24H:      [],
                                ChartRes.res4H:       [],
                                ChartRes.res1H:       [],
                                ChartRes.res30M:      [],
                                ChartRes.res15M:      [],
                                ChartRes.res5M:       [],
                                ChartRes.res1M:       []}

        # Store potential HHLL breakout trackers  1H, 30M, 5M, 1M
        self.BT_long_1H = breakout_tracker('BT LONG', 'LONG', ChartRes.res1H)
        self.BT_short_1H = breakout_tracker('BT SHORT', 'SHORT', ChartRes.res1H)
        self.BT_long_30M = breakout_tracker('BT LONG', 'LONG', ChartRes.res30M)
        self.BT_short_30M = breakout_tracker('BT SHORT', 'SHORT', ChartRes.res30M)
        self.BT_long_5M = breakout_tracker('BT LONG', 'LONG', ChartRes.res5M)
        self.BT_short_5M = breakout_tracker('BT SHORT', 'SHORT', ChartRes.res5M)
        self.BT_long_1M = breakout_tracker('BT LONG', 'LONG', ChartRes.res1M)
        self.BT_short_1M = breakout_tracker('BT SHORT', 'SHORT', ChartRes.res1M)

        self.FirstDay = True
        self.pb_wait_cycles = 0
        #self.readyToTrade = True
        self.minPriceVariation = None
        self.numbersQuantum = 5.0
        self.countDatapoints = 0
        self.manualTradeFound = False
        self.manualTradeOn = False
        self.tradedToday = 0
        self.manualTradeConditional = False
        self.manualBounceTrade = False
        self.manualTradeID = 0
        self.manual_fti_sign = False
        self.type_of_trade_found = Strats.Nothing
        self.trade_label_current = ""
                
        self.total_algo_pips = 0.0          # track total number of pips profit or loss from the algo run in this pair

        self.manualDirection = False
        self.manualLotSize = 0
        self.manualTradeDate = None
        self.manualTradeHour = None
        self.manualTradeMinute = None
        self.manualExpectedEntry = 0.0
        self.manualCheckMinutes = 0
        
        self.HighAskCurrDay = 0.0
        self.LowAskCurrDay = 0.0
        self.HighBidCurrDay = 0.0
        self.LowBidCurrDay = 0.0
        self.high_rolling_24H = 0.0
        self.low_rolling_24H = 0.0
        self.HighPrevDay = 0.0
        self.LowPrevDay = 0.0
        self.HighCurrWeek = -9999.0         # make sure first price we see is higher
        self.LowCurrWeek = 9999.0           # make sure first price we see is lower
        self.HighPrevWeek = 0.0
        self.LowPrevWeek = 0.0
        self.HighCurrMonth = -9999.0
        self.LowCurrMonth = 9999.0
        self.HighPrevMonth = 0.0
        self.LowPrevMonth = 0.0
        
        self.CeilCurrDay = 0.0
        self.FloorCurrDay = 0.0
        self.CeilPrevDay = 0.0
        self.FloorPrevDay = 0.0
        self.CeilCurrWeek = 0.0         
        self.FloorCurrWeek = 0.0        
        self.CeilPrevWeek = 0.0
        self.FloorPrevWeek = 0.0
        self.CeilCurrMonth = 0.0
        self.FloorCurrMonth = 0.0
        self.CeilPrevMonth = 0.0
        self.FloorPrevMonth = 0.0
        self.Ceil123R_1H = 0.0
        self.Floor123G_1H = 0.0
        self.Ceil123R_30M = 0.0
        self.Floor123G_30M = 0.0
        self.Ceil123R_5M = 0.0
        self.Floor123G_5M = 0.0        
        self.perfectPoints_30M = 0.0
        self.perfectPoints_1HR = 0.0
        self.perfectPoints_5M = 0.0
        self.AlertedPerfect_Short_1HR = False
        self.AlertedPerfect_Long_1HR = False
        self.AlertedPerfect_Short_30M = False
        self.AlertedPerfect_Long_30M = False
        self.TriggerCandleWindow_1HR = -1
        self.TriggerCandleWindow_30M = -1
        self.TriggerCandleWindow_5M = -1        
        self.set_specific_stop_loss = False
        self.set_specific_take_profit = False
        
        self.tradePoints = 0.0  #Si not proper way to do it outside a strat array, but want to start simply
        
        # new session objects
        self.current_session = SessionNames.Unknown
        self.previous_session = SessionNames.Unknown
        self.live_sessions = {SessionNames.Pre_Asia:    session_box("Pre_Asia"), 
                            SessionNames.Asia:          session_box("Asia"), 
                            SessionNames.Europe:        session_box("Europe"), 
                            SessionNames.Pre_US:        session_box("Pre_US"),
                            SessionNames.US:            session_box("US")}
        self.historic_sessions = session_box_library(f"Sessions: {self.Symbol}")
        
        # create external structure tracker for EHs and EL's
        self.EH_EL_tracker = {ChartRes.res24H:      external_structure("24H"),
                              ChartRes.res4H:       external_structure("4H"),
                              ChartRes.res1H:       external_structure("1H"),
                              ChartRes.res30M:      external_structure("30M"),
                              ChartRes.res15M:      external_structure("15M"),
                              ChartRes.res5M:       external_structure("5M"),
                              ChartRes.res1M:       external_structure("1M")}

        # create tracking systems for PERFECT trades spotted from a breakout
        self.tbu_perfect_tracker = { ChartRes.res1H:       builder_perfect("1H"),
                                        ChartRes.res30M:      builder_perfect("30M"),
                                        ChartRes.res15M:      builder_perfect("15M"),
                                        ChartRes.res5M:       builder_perfect("5M")}

        #create trade management systems for PERFECT trades spotted from a breakout
        self.tbu_perfect_manager = { ChartRes.res1H:       manage_perfect("1H"),
                                        ChartRes.res30M:      manage_perfect("30M"),
                                        ChartRes.res15M:      manage_perfect("15M"),
                                        ChartRes.res5M:       manage_perfect("5M")}

        # Content for managing live orders, stop losses and take profits
        # Trailing distance in pips
        # Master LossLimit - change this value depending on strategy being used; done in the code
        self.trailling_stop = False
        self.trailling_pips = 15.0
        self.breakout_pnl =   [-5, 0, 7, 15, 20 ]
        self.breakout_trail = [-20, -15, 0, 5, 10]
        self.profit_dist = 30
        
        # MANUAL LossLimit
        #self.sl_pnl_manual =   [  0,  15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140]
        #self.sl_trail_manual = [-15, -10, 5,  10, 15, 20, 25, 35, 45, 55, 65, 75,  85,  95, 105, 115, 125]
        #self.sl_profit_manual = 150
        
        #self.sl_pnl_manual =  [0,  10, 15, 25, 50, 100]
        #self.sl_trail_manual = [-15, 0, 3, 13, 35, 80 ]
        #self.sl_profit_manual = 120
        
        self.sl_pnl_manual =  [0,  15 , 25, 30, 40]
        self.sl_trail_manual = [-10, 0, 5, 15, 20]
        self.sl_profit_manual = 30
        
        #self.sl_pnl_manual =  [0,  10, 15, 25, 50, 100, 120, 140, 160, 180]
        #self.sl_trail_manual = [-10, 0, 5, 15, 35, 70, 90, 110, 140, 160 ]
        #self.sl_profit_manual = 200
        
       
        self.looking_for_channel_1H = False
        self.channel_direction_1H = StratDirection.Nothing
        self.channel_state_1H = 0      # 0 is not found, 1 is ready to look for entry price breach, 2 is now in price zone - if price leaves zone, 3 is do it

        self.looking_for_channel_30M = False
        self.channel_direction_30M = StratDirection.Nothing
        self.channel_state_30M = 0      # 0 is not found, 1 is ready to look for entry price breach, 2 is now in price zone - if price leaves zone, 3 is do it

        self.looking_for_channel_5M = False
        self.channel_direction_5M = StratDirection.Nothing
        self.channel_state_5M = 0      # 0 is not found, 1 is ready to look for entry price breach, 2 is now in price zone - if price leaves zone, 3 is do it        

        self.looking_for_channel_hours = 0
        self.channel_h = 0.0
        self.channel_l = 0.0
        self.channel_h_h = 0.0
        self.channel_l_l = 0.0
        self.channel_trigger_price = 0.0
        self.channel_take_profit_pips = 0.0
        self.channel_stop_loss_price = 0.0
        self.channel_weakness_found_1M = False
        self.channel_weakness_found_5M = False
        self.channel_weakness_found_15M = False
        self.channel_weakness_found_30M = False
        self.channel_weakness_found_1HR = False
        
        #Trade in a direction pre-approved
        self.pre_approved_to_trade = True
        self.pre_approved_goShort = False
        #self.pre_approved_starttime = None
        self.date_time_str = '02/07/21 01:00:0'
        self.pre_approved_starttime = datetime.strptime(self.date_time_str, '%d/%m/%y %H:%M:%S')        #was None
        self.pre_approved_minutes = 1440
        

        # Values used for controlling Stop Loss from FTI
        self.ftichangestop = False
        self.ftichangepips = 0.0
        self.trading_move_to_be_flag = False
        self.trading_move_to_be_profit_pips = 0.0
        self.trading_move_to_be_new_stop_pips = 0.0
        self.trading_move_to_be_done = False
        self.trading_stop_allow_ratchet = True
        
        # Values used for controlling Take Profit from FTI
        self.ftichangeprofit = False
        self.ftichangeprofitpips = 0.0

        # Values used for controlling Split Pot strategy from FTI
        self.ftisplitpot = False     
        
        # once a currency has manual take profit or stop loss instructions sent from FTI, FTI is in control and auto trade mgt stops
        self.fti_in_control = False

        #values stored at trade entry time
        self.split_live_levels = [False, False, False]    #boolean flag to determine whether we have made a split
        self.trade_split = [] #this is the trade object for each level
        self.tickets_trades = [None, None, None]     #this is the trade object for each level        
        self.tickets_stops = [None, None, None]
        self.tickets_last_stop_levels = [None, None, None]
        self.tickets_profits = [None, None, None]
        self.tickets_ids = [None, None, None]   #holds the current orderId reference for each level
        self.tickets_entry_no = [0, 0, 0]   #holds an incremental number to represent the number of entry trades at each level
        self.tickets_position_size = [0, 0, 0]  #holds the running position size at each level ... will be used to cross reference against the transaction manager / portfolio expectation
        self.tickets_live_levels = [False, False, False]    #boolean flag to determine whether level is live or not
        self.tickets_low_asks = [0.0, 0.0, 0.0]
        self.tickets_low_bids = [0.0, 0.0, 0.0]
        self.tickets_high_asks = [0.0, 0.0, 0.0]
        self.tickets_high_bids = [0.0, 0.0, 0.0]
        self.entry_prices = [0.0, 0.0, 0.0]
        self.exit_prices = [0.0, 0.0, 0.0]
        self.max_pips_profits = [0.0, 0.0, 0.0]
        self.max_pips_losses = [0.0, 0.0, 0.0]
        self.sl_positions = [0, 0, 0]
        self.entry_times = [None, None, None]
        self.spreads_paid = [0.0,  0.0, 0.0]
        self.last_trail_levels = [None, None, None]
        # Declare an attribute that we will use to store the last trail level
        # used. We will use this to decide whether to move the stop
        self.cancel_if_losing_time = None
        self.EntryMacdSignal = 0.0
        self.EntryMacdFast = 0.0
        self.EntryMacdSlow = 0.0
        self.EntryMacdSigDelt = 0.0
        self.EntryMacdHist = 0.0
        self.EntryMacdCurrent = 0.0
        self.EntrySpreadPips = 0.0
        self.EntryCandlePips = 0.0
        self.EntryADXTrend4H = 'Nothing'
        self.EntryADXTrend1H = 'Nothing'
        #self.low_ask = 0.0
        #self.low_bid = 0.0
        #self.high_ask = 0.0
        #self.high_bid = 0.0
        self.low_time = None
        self.high_time = None
        self.max_pipsprofit = 0.0
        self.max_pipsloss = 0.0
        # stop loss ticket.
        self.sl_position = 0   # Need to hold the best stop loss position and not slip back down again
        self.sl_order = None
        # take profit order        
        self.lim_order = None

        self.currentPosition = 0.0  #si 12.32 - hold the current position size to check split pots can be easily tracked to stop/limit
        self.state_of_symbol = SymbolStates.looking
        
        
        # values for holding candle data
        self.c1open = 0.0
        self.c1high = 0.0
        self.c1close = 0.0
        self.c1low = 0.0
        self.c1ema = 0.0
        self.c1opennumbersbelow = 0.0
        self.c1opennumbersabove = 0.0
        self.c1closenumbersbelow = 0.0
        self.c1closenumbersabove = 0.0
        self.c2open = 0.0
        self.c2high = 0.0
        self.c2close = 0.0
        self.c2low = 0.0
        self.c2ema = 0.0
        self.c2opennumbersbelow = 0.0
        self.c2opennumbersabove = 0.0
        self.c2closenumbersbelow = 0.0
        self.c2closenumbersabove = 0.0
        self.c3open = 0.0
        self.c3high = 0.0
        self.c3close = 0.0
        self.c3low = 0.0
        self.c3ema = 0.0
        self.c3opennumbersbelow = 0.0
        self.c3opennumbersabove = 0.0
        self.c3closenumbersbelow = 0.0
        self.c3closenumbersabove = 0.0

        # need something to hold which strategy might be active and in which direction
        self.activeStrat = Strats.Nothing
        self.activeDirection = StratDirection.Nothing
        
        # tracker for which Strategies we've found
        self.stratTracker = {}
        for strategy in (Strats):
            for direction in (StratDirection):
                self.stratTracker[strategy.name+direction.name] = {"Count":0, "Stopped":0, "PnlPips":0.0}
                
        self.holding = 0.0
    

    def is_looking_for_possible_trade(self):
        # TODO: set a variable here - also could provide predicted direction
        if self.state_of_symbol == SymbolStates.trading:
            # Always make sure that if we are in a trade we will not go looking for another entry
            return False
        # TODO: expand state checks to include handling looking for multiple possible trade types at once
        if self.state_of_symbol == SymbolStates.looking:
            return True
        return False

    def is_looking_for_entry(self):
        # TODO: looking for entry needs confirmation - and a prediction of what direction looking for
        if self.state_of_symbol == SymbolStates.trading:
            # Always make sure that if we are in a trade we will not go looking for another entry
            return False
        # TODO: expand state checks to include handling looking for entry on more than one strategy at once - esp when clearing
        if self.state_of_symbol == SymbolStates.entry_hunt:
            return True
        return False

    def is_looking_for_entry_confirmation(self):
        # TODO: looking for entry confirmation 
        if self.state_of_symbol == SymbolStates.trading:
            # Always make sure that if we are in a trade we will not go looking for another entry
            return False
        if self.state_of_symbol == SymbolStates.entry_confirmation:
            return True
        return False

    def set_symbol_state(self, sender, state_to_set):
        # TODO: Make sure this can handle multiple strategies, and will check things before setting states without checking
        if state_to_set == SymbolStates.looking:
            if self.state_of_symbol == SymbolStates.trading:
                # Always make sure that if we are in a trade we cannot just go back to looking
                sender.Log(f"{self.Symbol} ERROR - cannot set state to looking when in an active trade")
                return False
            else:
                self.state_of_symbol = SymbolStates.looking
                return True
        # TODO: add ability to set states to looking for entry or entry confirmation or actively in a trade
        return False

    def is_in_a_trade(self, sender):
        quantity_held = 0.0 
        if sender.Portfolio[self.Symbol].Invested:
            quantity_held = sender.Portfolio[self.Symbol].Quantity
        if quantity_held != 0.0:
            # sender.Log(f"{self.Symbol} in a trade check : {quantity_held}")
            # Should already have been set, but this will stop us doing other actions just in case
            self.state_of_symbol = SymbolStates.trading
            return True
        return False
  
 
        
    # look for 123G to Numbers Ceiling - with the Numbers Ceiling being provided already
    def Is123GToNumbersCeiling(self, mybars, mycolours, myceiling):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN):
            ghi = max(mybars[2].Bid.High, mybars[1].Bid.High, mybars[0].Bid.High) 
            glo = min(mybars[2].Bid.Low, mybars[1].Bid.Low, mybars[0].Bid.Low)
            if ghi > myceiling and glo < myceiling:
                # now check G3High < G2High
                if mybars[0].Bid.High < mybars[1].Bid.High:
                    return True
        return False
        
    # look for 123R to Numbers Floor - with the Numbers Floor being provided already
    def Is123RToNumbersFloor(self, mybars, mycolours, myfloor):
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, RED):
            rhi = max(mybars[2].Bid.High, mybars[1].Bid.High, mybars[0].Bid.High) 
            rlo = min(mybars[2].Bid.Low, mybars[1].Bid.Low, mybars[0].Bid.Low)
            if rlo < myfloor and rhi > myfloor:
                # now check R3Low > R2Low
                if mybars[0].Bid.Low > mybars[1].Bid.Low:
                    return True
        return False
        
    # look for 1234G to Numbers
    def Is1234GToNumbers(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN, GREEN):
            ghi = max(mybars[3].Bid.Close, mybars[2].Bid.Close, mybars[1].Bid.Close) 
            glo = min(mybars[3].Bid.Open, mybars[2].Bid.Open, mybars[1].Bid.Open)
            nextnumdown = self.NumbersBelow(ghi)
            nextnumup = self.NumbersAbove(glo)
            if nextnumdown >= nextnumup:   # we have crossed numbers in the first 3 candles, now look at 4th one
                if mybars[0].Bid.High < mybars[1].Bid.High and mybars[0].Bid.Low < mybars[1].Bid.Low:
                    return True
        return False
        
    # look for 1234R to Numbers 
    def Is1234RToNumbers(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, RED, RED):
            rhi = max(mybars[3].Bid.Open, mybars[2].Bid.Open, mybars[1].Bid.Open) 
            rlo = min(mybars[3].Bid.Close, mybars[2].Bid.Close, mybars[1].Bid.Close)
            nextnumdown = self.NumbersBelow(rhi)
            nextnumup = self.NumbersAbove(rlo)
            if nextnumdown >= nextnumup:   # we have crossed numbers in the first 3 candles, now look at 4th one
                if mybars[0].Bid.High > mybars[1].Bid.High and mybars[0].Bid.Low > mybars[1].Bid.Low:
                    return True
        return False
        
        
    # look for 123G4R to Numbers
    def Is123G_4R_ToNumbers(self, mybars, mycolours, myemas, pipsize, retrace_ratio = 0.5):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN, RED):
            ghi = max(mybars[3].Bid.Close, mybars[2].Bid.Close, mybars[1].Bid.Close) 
            glo = min(mybars[3].Bid.Open, mybars[2].Bid.Open, mybars[1].Bid.Open)
            nextnumdown = self.NumbersBelow(ghi)
            nextnumup = self.NumbersAbove(glo)
            if nextnumdown >= nextnumup:   # we have crossed numbers in the first 3 candles, now look at 4th one
                # need to check total sizes
                red_len = abs(mybars[0].Bid.Open - mybars[0].Bid.Close) / pipsize
                green_len = (ghi - glo) / pipsize
                my_ratio = float(red_len / green_len)
                if my_ratio < retrace_ratio and self.BouncedOffFloor(mybars, mycolours, nextnumdown):
                    # we have crossed Numbers with 123G, created a floor.  The 4th RED is no larger than ration of the other 3 and does not cross the floor
                    # maybe now we see the Trend continue 
                    #dist_to_floor = (mybars[0].Bid.Close - nextnumdown) / pipsize
                    #wick_len = (mybars[0].Bid.Close - mybars[0].Bid.Low) / pipsize
                    #if dist_to_floor < 10.0 and wick_len < 15.0:
                        # final red come close to Floor to bounce off
                    return True
        return False

   
    # Look for 123 GREEN with the EMA crossing the candle body of any of them        
    def Is123GToNumbers9EMA(self, mybars, mycolours, myemas):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN):
            ghi = max(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close) 
            glo = min(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open)
            nextnumdown = self.NumbersBelow(ghi)
            nextnumup = self.NumbersAbove(glo)
            if nextnumdown >= nextnumup:   # we have crossed numbers
                # now check 9EMA cross too
                if self.DoesEMACross(mybars[2], myemas[2]) or self.DoesEMACross(mybars[1], myemas[1]) or self.DoesEMACross(mybars[0], myemas[0]):
                    return True
        return False
        
    
    # Look for 123 GREEN with the EMA crossing the candle body of any of them        
    def Is123RToNumbers9EMA(self, mybars, mycolours, myemas):
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, RED):
            rhi = max(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open) 
            rlo = min(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close)
            nextnumdown = self.NumbersBelow(rhi)
            nextnumup = self.NumbersAbove(rlo)
            if nextnumdown >= nextnumup:   # we have crossed numbers
                # now check 9EMA cross too
                if self.DoesEMACross(mybars[2], myemas[2]) or self.DoesEMACross(mybars[1], myemas[1]) or self.DoesEMACross(mybars[0], myemas[0]):
                    return True
        return False
        
        
        # Look for 123 GREEN with the EMA crossing the candle body of any of them        
    def Is123GToNumbersMakesFloor(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN):
            ghi = max(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close) 
            glo = min(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open)
            nextnumdown = self.NumbersBelow(ghi)
            nextnumup = self.NumbersAbove(glo)
            if nextnumdown >= nextnumup :  # we have crossed numbers, return the Floor we made
                return nextnumdown
        return 0.0
        
    
    # Look for 123 GREEN with the EMA crossing the candle body of any of them        
    def Is123RToNumbersMakesCeiling(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, RED):
            rhi = max(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open) 
            rlo = min(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close)
            nextnumdown = self.NumbersBelow(rhi)
            nextnumup = self.NumbersAbove(rlo)
            if nextnumdown >= nextnumup:   # we have crossed numbers
                return nextnumup
        return 0.0

    # Look for a peak with the highest high of the 3 being the middle candle        
    def is_123_peak(self, mybars, offset=0, ignore_outside_bars=False):
        is_peak = False
        my_high = 0.0
        my_time = None
        outside_bar = False
        peak_low = 0.0

        # do we have an OUTSIDE bar as the third bar?
        if mybars[0 + offset].Bid.High > mybars[1 + offset].Bid.High and mybars[0 + offset].Bid.Low < mybars[1 + offset].Bid.Low:
            outside_bar = True
            if ignore_outside_bars: outside_bar = False

        if not outside_bar and mybars[2 + offset].Bid.High < mybars[1 + offset].Bid.High and mybars[0 + offset].Bid.High < mybars[1 + offset].Bid.High:
            # we now have a peak as the middle bar is the highest high
            is_peak = True
        
        #need to add an additional check to see if we have equal two in the middle (for the moment just 4 candle pattern not for 'n' candles)
        if not outside_bar and not is_peak:
            if mybars[2 + offset].Bid.High == mybars[1 + offset].Bid.High and mybars[0 + offset].Bid.High < mybars[1 + offset].Bid.High:
                if mybars[3 + offset].Bid.High < mybars[2 + offset].Bid.High:
                    is_peak = True

        # now check if we have a peak formed by an OUTSIDE bar as the third bar
        if outside_bar and not ignore_outside_bars:
            if mybars[2 + offset].Bid.High < mybars[1 + offset].Bid.High and mybars[0 + offset].Bid.Low < mybars[1 + offset].Bid.Low:
                is_peak = True
        

        if is_peak:
            my_high = mybars[1 + offset].Bid.High
            my_time = mybars[1 + offset].EndTime
            peak_low = min(mybars[0 + offset].Bid.Low, mybars[1 + offset].Bid.Low, mybars[2 + offset].Bid.Low)
        return (is_peak, my_high, my_time, outside_bar, peak_low)


    # find if we have a peak in the last N bars
    def is_peak_in_last_N_bars(self, mybars, n_bars, ignore_outside_bars=False):
        is_peak = False
        my_high = 0.0
        my_time = None
        outside_bar = False
        peak_low = 0.0
        highest_high = 0.0
        if n_bars < 3:
            return (is_peak, my_high, my_time, outside_bar, peak_low)
        for i in range(n_bars-2):
            (is_peak, my_high, my_time, outside_bar, peak_low) = self.is_123_peak(mybars, offset=i, ignore_outside_bars=ignore_outside_bars)
            if is_peak:
                #we dont want to break just on peak need to continue to see is there is another peak
                #if highest_high < my_high:
                    #highest_high = my_high
                break
        return (is_peak, my_high, my_time, outside_bar, peak_low)

    # Look for a peak with the highest high of the 3 being the middle candle, returning the whole bar of the peak candle        
    def is_123_peak_return_bar(self, mybars, mycolours):
        is_peak = False
        my_high = 0.0
        my_time = None
        start_time = None
        confirm_time = None
        count_lhs = 0
        outside_bar = False

        # do we have an OUTSIDE bar as the third bar?
        if mybars[0].Bid.High > mybars[1].Bid.High and mybars[0].Bid.Low < mybars[1].Bid.Low:
            outside_bar = True

        if not outside_bar and mybars[2].Bid.High < mybars[1].Bid.High and mybars[0].Bid.High < mybars[1].Bid.High:
            # we now have a peak as the middle bar is the highest high
            is_peak = True

        # now check if we have a peak formed by an OUTSIDE bar as the third bar
        if outside_bar:
            if mybars[2].Bid.High < mybars[1].Bid.High and mybars[0].Bid.Low < mybars[1].Bid.Low:
                is_peak = True

        if is_peak:
            my_high = mybars[1].Bid.High
            my_time = mybars[1].EndTime
            start_time = mybars[0].EndTime
            confirm_time = mybars[2].EndTime
            for i in range(1, mybars.Count):
                if i == 1 and mycolours[1] == RED:
                    pass        # ignore the first bar of the LHS if is is RED, as we are looking for continuous GREENs
                else:
                    if mycolours[i] == GREEN:
                        count_lhs += 1
                    else:
                        break
        return (is_peak, my_high, my_time, mybars[1], start_time, confirm_time, count_lhs)


    # Look for a trough with the lowest low of the 3 being the middle candle
    def is_123_trough(self, mybars, offset=0, ignore_outside_bars=False):
        is_trough = False
        my_low = 0.0
        my_time = None
        outside_bar = False
        trough_high = 0.0

        # do we have an OUTSIDE bar as the third bar?
        if mybars[0 + offset].Bid.High >= mybars[1 + offset].Bid.High and mybars[0 + offset].Bid.Low <= mybars[1 + offset].Bid.Low:
            outside_bar = True
            if ignore_outside_bars: outside_bar = False

        if not outside_bar and mybars[2 + offset].Bid.Low > mybars[1 + offset].Bid.Low and mybars[0 + offset].Bid.Low > mybars[1 + offset].Bid.Low:
            # we now have a trough as the middle bar is the lowest low.  
            is_trough = True

        #need to add an additional check to see if we have equal two in the middle (for the moment just 4 candle pattern not for 'n' candles)
        if not outside_bar and not is_trough:
            if mybars[2 + offset].Bid.Low == mybars[1 + offset].Bid.Low and mybars[0 + offset].Bid.Low > mybars[1 + offset].Bid.Low:
                if mybars[3 + offset].Bid.Low > mybars[2 + offset].Bid.Low:
                    is_peak = True            

        # now check if we have a trough formed by an OUTSIDE bar as the third bar
        if outside_bar and not ignore_outside_bars:
            if mybars[2 + offset].Bid.Low > mybars[1 + offset].Bid.Low and mybars[0 + offset].Bid.High > mybars[1 + offset].Bid.High:
                is_trough = True

        if is_trough:
            my_low = mybars[1 + offset].Bid.Low
            my_time = mybars[1 + offset].EndTime
            trough_high = max(mybars[0 + offset].Bid.High, mybars[1 + offset].Bid.High, mybars[2 + offset].Bid.High)
        return (is_trough, my_low, my_time, outside_bar, trough_high)

    # find if we have a trough in the last N bars
    def is_trough_in_last_N_bars(self, mybars, n_bars, ignore_outside_bars=False):
        is_trough = False
        my_low = 0.0
        my_time = None
        outside_bar = False
        trough_high = 0.0
        if n_bars < 3:
            return (is_trough, my_low, my_time, outside_bar, trough_high)
        for i in range(n_bars-2):
            (is_trough, my_low, my_time, outside_bar, trough_high) = self.is_123_trough(mybars, offset=i, ignore_outside_bars=ignore_outside_bars)
            if is_trough:
                break
        return (is_trough, my_low, my_time, outside_bar, trough_high)
        

    # Look for a trough with the lowest low of the 3 being the middle candle, returning the whole bar of the trough candle
    def is_123_trough_return_bar(self, mybars, mycolours):
        is_trough = False
        my_low = 0.0
        my_time = None
        start_time = None
        confirm_time = None
        count_lhs = 0
        outside_bar = False

        # do we have an OUTSIDE bar as the third bar?
        if mybars[0].Bid.High > mybars[1].Bid.High and mybars[0].Bid.Low < mybars[1].Bid.Low:
            outside_bar = True

        if not outside_bar and mybars[2].Bid.Low > mybars[1].Bid.Low and mybars[0].Bid.Low > mybars[1].Bid.Low:
            # we now have a trough as the middle bar is the lowest low.  
            is_trough = True

        # now check if we have a trough formed by an OUTSIDE bar as the third bar
        if outside_bar:
            if mybars[2].Bid.Low > mybars[1].Bid.Low and mybars[0].Bid.High > mybars[1].Bid.High:
                is_trough = True

        if is_trough:
            my_low = mybars[1].Bid.Low
            my_time = mybars[1].EndTime
            start_time = mybars[0].EndTime
            confirm_time = mybars[2].EndTime
            for i in range(1, mybars.Count):
                if i == 1 and mycolours[1] == GREEN:
                    pass        # ignore the first bar of the LHS if is is GREEN, as we are looking for continuous REDs
                else:
                    if mycolours[i] == RED:
                        count_lhs += 1
                    else:
                        break
        return (is_trough, my_low, my_time, mybars[1], start_time, confirm_time, count_lhs)

          
    #Si function to check for a bounce off a passed floor 
    def BouncedOffFloor(self,mybars, mycolours, floor):
        if mycolours[0] == RED:
            if mybars[0].Bid.Low < floor and mybars[0].Bid.Close > floor:
                return True
        return False
  
    #Si function to check for a bounce off a passed ceiling 
    def BouncedOffCeiling(self,mybars, mycolours, ceiling):
        if mycolours[0] == GREEN:
            if mybars[0].Bid.High > ceiling and mybars[0].Bid.Close < ceiling:
                return True
        return False      
        


    # Set the 4 Hour trend using the ADX values - not confident this fully captures it
    def set_trend_4H(self):
        self.Trend4H = Trends.Nothing
        
        tadx = self.ADX4H.Current.Value
        tdin = self.ADX4H.NegativeDirectionalIndex.Current.Value
        tdip = self.ADX4H.PositiveDirectionalIndex.Current.Value
        
        if tdin > tdip and tadx >= 20:
            self.Trend4H = Trends.Uptrend
        elif tdip > tdin and tadx >= 20:
            self.Trend4H = Trends.Downtrend               


    # Set the 1 Hour trend using the ADX values - not confident this fully captures it
    def set_trend_1H(self):
        self.Trend1H = Trends.Nothing
        
        tadx = self.ADX1H.Current.Value
        tdin = self.ADX1H.NegativeDirectionalIndex.Current.Value
        tdip = self.ADX1H.PositiveDirectionalIndex.Current.Value
        
        if tdin > tdip and tadx >= 20:
            self.Trend1H = Trends.Uptrend
        elif tdip > tdin and tadx >= 20:
            self.Trend1H = Trends.Downtrend     

    
    # Find a trend given a series of bars - using gradient of the EMA
    def WhatTrend(self, myemas, mybars, endloc, startloc):
        mytrend = Trends.Nothing
        temptrend = Trends.Nothing
        lasttrend = Trends.Nothing
        
        upordown = myemas[startloc].Value - myemas[endloc].Value
        # Now check through the EMA values and see if the differences are all the same
        for i in range(startloc, endloc+1-1, -1):
            # this will be going down each time as reverse indexing of rollingWindows
            lasttrend = temptrend
            diffval = myemas[i-1].Value - myemas[i].Value
            if diffval > 0.0:
                temptrend = Trends.Uptrend
            if diffval < 0.0:
                temptrend = Trends.Downtrend
            if temptrend != lasttrend and lasttrend != Trends.Nothing:
                if upordown > 0.0:
                    temptrend = Trends.SidewaysDown
                else:
                    temptrend = Trends.SidewaysUp
                break
        if temptrend == Trends.Downtrend:
            if mybars[endloc].Bid.Low > mybars[endloc+1].Bid.Low:
                #Broken downtrend
                if upordown > 0.0:
                    temptrend = Trends.SidewaysDown
                else:
                    temptrend = Trends.SidewaysUp
        if temptrend == Trends.Uptrend:
            if mybars[endloc].Bid.High < mybars[endloc+1].Bid.High:
                #Broken uptrend
                if upordown > 0.0:
                    temptrend = Trends.SidewaysDown
                else:
                    temptrend = Trends.SidewaysUp
        mytrend = temptrend
        return mytrend
        
        
    def WhatTrendMacd(self, mymacdsfast, mymacdsslow, mymacdssignal, mymacdscurrent, mymacdhist, tolerance):
        temptrend = Trends.Nothing
        upordown = mymacdsfast[2].Value - mymacdsfast[0].Value
        
        #sigdelt = round((mymacdscurrent[0].Value - mymacdssignal[0].Value)/mymacdsfast[0].Value, 5)
        # #sigdelt = round(mymacdssignal[0].Value, 5)
        #if sigdelt > tolerance:  
        if mymacdhist[0].Value > tolerance:
            # upwards signal
            temptrend = Trends.Uptrend
        #elif sigdelt < -tolerance:
        elif mymacdhist[0].Value < -tolerance:
            # downwards signal
            temptrend = Trends.Downtrend
        if temptrend == Trends.Nothing:
            if upordown > 0.0:
                temptrend = Trends.SidewaysDown
            elif upordown < 0.0:
                temptrend = Trends.SidewaysUp
        return temptrend
        
    def WhatTrendMacdNew(self, mymacdssignal, mymacdcurrent, price1hr, ema4hr):
        temptrend = Trends.Nothing
        
        if mymacdcurrent[0].Value > 0 and mymacdssignal[0].Value > 0 and price1hr > ema4hr:
            # upwards signal
            temptrend = Trends.Uptrend
        elif mymacdcurrent[0].Value < 0 and mymacdssignal[0].Value < 0 and price1hr < ema4hr:
            # downwards signal
            temptrend = Trends.Downtrend
        
        return temptrend
    
    def IsEMACloseToNumbers(self, ema, pipdist, pipsize):
        nextnumdown = self.NumbersBelow(ema.Value)
        nextnumup = self.NumbersAbove(ema.Value)
        
        emadist1 = (ema.Value - nextnumdown) / pipsize
        emadist2 = (nextnumup - ema.Value) / pipsize 
        
        if emadist1 < pipdist or emadist2 < pipdist:
            return True
        return False
        
    def DoesEMACross(self, candle, ema):
        if candle.Bid.Open > candle.Bid.Close:
            # Red candle
            if ema.Value < candle.Bid.Open and ema.Value > candle.Bid.Close:
                return True
        elif candle.Bid.Close > candle.Bid.Open:
            # Green candle
            if ema.Value < candle.Bid.Close and ema.Value > candle.Bid.Open:
                return True
        return False
        
    
    
    def update_rolling_24H_levels(self, my_time):
        if self.Bars1H.Count > 24:
            # only try updating this once we have 24Hrs worth of data
            temp_hi = self.Bars1H[0].Bid.High
            temp_lo = self.Bars1H[0].Bid.Low
            for i in range(1, 23):
                if self.Bars1H[i].Bid.High > temp_hi:
                    temp_hi = self.Bars1H[i].Bid.High
                if self.Bars1H[i].Bid.Low < temp_lo:
                    temp_lo = self.Bars1H[i].Bid.Low
            self.high_rolling_24H = temp_hi
            self.low_rolling_24H = temp_lo        
    
            
    def UpdateHighsLows(self, my_time, price_now):
        self.HighPrevDay = float(self.Bars24H[0].Bid.High)
        self.LowPrevDay = float(self.Bars24H[0].Bid.Low)
        
        tomorrow_time = my_time
        tomorrow_time += timedelta(days=1)
        monday_time = my_time
        monday_time += timedelta(days=3)
        
        my_hour = my_time.hour
        my_weekday = day[my_time.weekday()]
        
        if (monday_time.month != my_time.month and my_weekday == "Friday") or (tomorrow_time.month != my_time.month):
                # next busines day the month changes
                self.HighPrevMonth = self.HighCurrMonth 
                self.LowPrevMonth = self.LowCurrMonth        
                self.HighCurrMonth = price_now
                self.LowCurrMonth = price_now
        
        if my_weekday == "Friday" and my_hour == 17:
            # we treat 5pm NYC time as the end of the week and a start of a new one
            self.HighPrevWeek = self.HighCurrWeek
            self.LowPrevWeek = self.LowCurrWeek
            self.HighCurrWeek = price_now
            self.LowCurrWeek = price_now
            

   


    def UpdatePriceBasedFloorsCeilings(self):
        #Si - separated the price based stuff as its a different type
        #moved this from UpdateFloorsCeilings
        
        self.CeilCurrDay = self.NumbersAbove(self.HighBidCurrDay) #Si changed from ask
        self.FloorCurrDay = self.NumbersBelow(self.LowBidCurrDay) #Si changed from ask
        self.CeilPrevDay = self.NumbersAbove(self.HighPrevDay)
        self.FloorPrevDay = self.NumbersBelow(self.LowPrevDay)
        self.CeilCurrWeek = self.NumbersAbove(self.HighCurrWeek)         
        self.FloorCurrWeek = self.NumbersBelow(self.LowCurrWeek)        
        self.CeilPrevWeek = self.NumbersAbove(self.HighPrevWeek)
        self.FloorPrevWeek = self.NumbersBelow(self.LowPrevWeek)
        self.CeilCurrMonth = self.NumbersAbove(self.HighCurrMonth)
        self.FloorCurrMonth = self.NumbersBelow(self.LowCurrMonth)
        self.CeilPrevMonth = self.NumbersAbove(self.HighPrevMonth)
        self.FloorPrevMonth = self.NumbersBelow(self.LowPrevMonth)
        
    def UpdateFloorsCeilings(self, my_bars, my_colours):
        # Make sure we have some values for the Floors and Ceilings
        # Si we need to look at whether to revet to previous not zero (discussion in Fusion with Doug)
            # this function invalidates an established floor/ceiling and i think should be split
            # we need to make this a price floor / ceiling not 123
        body_high = 0.0
        body_low = 0.0
        if my_colours[0] == GREEN:
            body_high = self.Bars1H[0].Bid.Close 
            body_low = self.Bars1H[0].Bid.Open 
        else:
            body_high = self.Bars1H[0].Bid.Open #Si changed from ask
            body_low = self.Bars1H[0].Bid.Close #Si changed from ask
        
        if body_high > self.Ceil123R_1H :
            # if the ceiling was punctured by a High price, then invalidate it
            self.Ceil123R_1H = 0.0
            
        if body_low < self.Floor123G_1H : #si
            # if floor punctured by a Low price, then invalidate it
            self.Floor123G_1H = 0.0
            
        #will want to add some scoring values to compare to Current Floor/Ceiling and mark strength
    
    def CheckBrokenFloor(self, my_floor, my_bars, my_colours): #si
        body_low = 0
        if my_colours[0] == GREEN:
            body_low = round(my_bars[0].Bid.Open, 4) 
        else:
            body_low = round(my_bars[0].Bid.Close,4) 
        if body_low < my_floor: #si
            return 0.0
        else:
            return my_floor
    
    def CheckBrokenCeiling(self, my_ceiling, my_bars, my_colours): #si      
        body_high = 0.0
        if my_colours[0] == GREEN:
            body_high = round(my_bars[0].Bid.Close, 4) #Si changed from ask
        else:
            body_high = round(my_bars[0].Bid.Open, 4) #Si changed from ask
        if body_high > my_ceiling:
            return 0.0
        else:
            return my_ceiling
    
        
        
  
    # Returns true if all the data in this instance is ready (indicators, rolling windows, ect...)
    def IsReady(self):
        return self.Bars5M.IsReady and self.EMA5M.IsReady

    # Returns true if the most recent trade bar time matches the current time minus the bar's period, this
    # indicates that update was just called on this instance
    def WasJustUpdated(self, current):
        return self.Bars5M.Count > 0 and self.Bars5M[0].Time == current - self.BarPeriod
    
        
  
