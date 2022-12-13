#region imports
from distutils.command.sdist import sdist
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
from dataclasses import dataclass
from symbolinfo import *
from notify import *
from testperfects import *
from object_store import *
from fusion_utils import *
from debugging_utils import *
from external_structure import *
from trades import *
from manage_perfect import *
from QuantConnect import Market
from io import StringIO
import pandas as pd
import pytz
from System.Drawing import Color
#endregion

# Define some constants we use for making the code easier to read    
candlecolours = ['G', 'R', '-']
trendnames = ['Uptrend', 'Downtrend', 'SidewaysUp', 'SidewaysDown', 'Nothing']
forexcodes = ['GBPUSD', 'GBPJPY', 'GBPCHF', 'GBPAUD', 'GBPNZD', 'EURUSD', 'EURNZD', 'EURJPY', 'EURAUD', 'AUDUSD', 'USDCAD', 'USDCHF', 'USDJPY']   # equates to 0 for GBPUSD etc


class Fusion_Algo(QCalgo_test_perfects):

    def Initialize(self):
        self.ModeName = "Fusion PAPER vGIT_25-11.1" 
        
        # set to use Oanda data
        self.SetBrokerageModel(BrokerageName.OandaBrokerage)
        self.SetAccountCurrency("GBP")
        # TODO: need to properly initialise starting value - may not be 100,000
        self.TotalValue = 100000 + self.Portfolio.TotalUnrealizedProfit + self.Portfolio.TotalProfit - self.Portfolio.TotalFees
        
        # Block for settings that differ between Live and Backtest
        if self.LiveMode:   # LIVE mode
            self.FusionCsvLiveUrl = "http://fusionfx.azurewebsites.net/submit/live_action_sub.csv"
            self.FusionCurrencySettingsUrl = "http://fusionfx.azurewebsites.net/submit/live_currencysettings.csv"
            self.ManualLiveTrading = False
            self.ManualHistoryTrading = False
            self.auto_trade_brad_perfects = True         
            self.myRes = Resolution.Second       #changes following Warmup Update (now trying only 7 days)
            # Live warmups take too long as they use Second resolution (code change)    
            self.SetWarmUp(timedelta(days=30), Resolution.Minute)    # Warm up 3 days of data.  Need to find a way to improve this
           
        else:               # BACKTEST mode
            self.FusionCsvLiveUrl = "http://fusionfx.azurewebsites.net/submit/paper_action_sub.csv"
            self.SetCash(100000)            # Set Strategy Cash
            self.FusionCurrencySettingsUrl = "http://fusionfx.azurewebsites.net/submit/backtest_currencysettings.csv"
            self.ManualLiveTrading = True
            self.ManualHistoryTrading = False    # Can turn off if we want backtesting without adding in the historic trades
            # TODO: make backtest start stop dates use a single updating value, so do not need to edit both
            self.SetStartDate(2022, 12, 8)  # Set Start Date
            self.SetEndDate(2022, 12, 8)         
            self.backtest_start = "2022-10-10"
            self.backtest_end = "2022-11-8"
            self.auto_trade_brad_perfects = True
            self.SetWarmUp(timedelta(days=30), Resolution.Minute)    # Warm up 30 days of data - works fine in backtests
            self.myRes = Resolution.Minute
            #self.myRes = Resolution.Second

        #temp oiutput for Brad to verify candle types
        self.candle_type_log = []    #use this to output an event log per breakout
        self.candle_item = {"candle_time__mt4": None,
                        "candle_chart": None,
                        "candle_type": None}

        # History URL for backtesting manually entered trades
        self.FusionCsvHistoryUrl = "http://fusionfx.azurewebsites.net/submit/f_history.csv"
        self.FusionJsonReports = "https://fti-display.azure-api.net/fusion-api/"
        
        # Timezone and session settings
        self.SetTimeZone("America/New_York")
        times_dict = fusion_utils.get_times(self.Time, 'us')   #new function to get times
        self.oandaChartTime = None       
        self.SessionID = SessionNames.Unknown
        self.PrevSessionID = SessionNames.Unknown
        self.SessionOpen = False 
                  
        self.JustWatching = False       # Set true if you do not want any trading to take place in order placing routines
        self.JustTestingTrading = False  #Si 13.0 bypass all to test levels 
        self.JustTestingCounter =     0 #Si 13.0 l         tests
        self.do_manage_stops = True     # Set this to False if no automated Stop management required.  DANGEROUS
        self.send_hourly_status_emails = False       #use this to send an hourly email
        self.send_breakout_emails = True       #use this to send the breakout email notifications
    
        # Turn on or off the old style peaks and troughs or the Brad ones
        self.use_old_trough_peaks = False           # False = use Brad's peaks and troughs

        # Settings for various bits of logging
        self.log_perfect_emails = False
        self.log_breakouts_1H = False
        self.log_channels_1H = False
        self.log_breakouts_30M = False
        self.log_channels_30M = False
        self.log_breakouts_5M = False
        self.log_channels_5M = False  
        self.log_breakouts_clean_5M = False             #logs all breakouts (clean and dirty) spotted when new 5m bar created 
        self.log_breakouts_dirty_5M = False             #temp to split 
        self.log_breakouts_clean_1H = False     
        self.log_eh_el_detail = False                   #logs all the new peaks and troughs found
        self.log_eh_el_summary = False                  #logs the changes in the peaks and troughs found
        self.log_eh_el_at_end = True                    #logs EHEL details and creates the csv file  
        self.log_tbu_perfects_details = False
        self.log_tbu_perfects_at_end = True
        self.log_price_trackers_at_end = False
        self.log_session_boxes_at_end = False
        self.log_perfect_spots = False
        self.log_session_changes = False
        self.log_EMAs = False
        self.log_bar_height_diffs = False
        self.log_position_closures = True               # log the request to close positions in the order code
        self.log_brad_peaks_detail = False
        self.log_brad_transfers = False                  # log details of how the peaks and troughs are copied over
        self.log_brad_breakout_spots = False             # log details of the details of a Brad breakout spot
        self.log_brad_make_breakouts = True              # log details when copying the Brad breakout into the general structure
        self.debugging_trade_tracking = True             #sends trade details to the debug log 

        self.breakout_count_5M_short = 0
        self.breakout_count_5M_long = 0
        self.breakout_count_dirty_5M_short = 0
        self.breakout_count_dirty_5M_long = 0
        self.ignored_5M_peaks = 0
        self.ignored_5M_troughs = 0
        
        self.LastTradeID = -1
        self.CurrentTradeID = -1
        self.DefaultLeverage = 20
        self.CountEmails = 0
        self.LiveTradeCount = 0
        self.EmailAddress = 'fusiondsc@gmail.com'
        #self.EmailAddress = 'simon@isaacs.com'

        if Environment.MachineName.startswith('DESKTOP'):
            # we are running locally on Chris (or Simon's - dont forget me!!) machine
            self.InCloud = False
        else:
            self.InCloud = True
        
        self.big_move_pips = 70.0
        self.big_move_hours = 24
        
        # tagged onto the end of all order tickets.  Increments for each new trade
        self.master_trade_id = 100
        
        # For Perfect point and pull back calculations
        self.MinimumPerfectPoints = 20   #CG 12_3
        self.TriggerCandleWindowMax = 6 #nu_1_CGof candles 
        # Override whether to actually do the trades on Channel strategies - for testing
        self.flag_do_trade_channel = True

        # This is the period of bars we'll be creating
        BarPeriod1M = TimeSpan.FromMinutes(1)
        BarPeriod5M = TimeSpan.FromMinutes(5)
        BarPeriod15M = TimeSpan.FromMinutes(15)
        BarPeriod30M = TimeSpan.FromMinutes(30)
        BarPeriod1H = TimeSpan.FromHours(1)
        BarPeriod4H = self.CustomBarPeriod4H             
        BarPeriod24H = self.CustomBarPeriod24H           
        MinutePeriod = Resolution.Minute
        
        # This is the period of our EMA indicators
        ExponentialMovingAveragePeriod = 9
        # This is the number of consolidated bars we'll hold in symbol data for reference
        # at 15mins, 96 bars is 1 whole day
        RollingWindowSize1M = 720
        RollingWindowSize5M = 360
        RollingWindowSize15M = 240
        RollingWindowSize30M = 120
        RollingWindowSize1H = 60
        RollingWindowSize4H = 60
        RollingWindowSize24H = 30
        
        # Holds all of our Symbol data keyed by each symbol
        self.symbolInfo = {}
        self.tradesEntered = []
        self.price_tracker_lib = price_tracker_library("Main Tracker")

        self.hdf = None     # historic trades dataframe
        self.ldf = None     # live trade dataframe
        
        if self.LiveMode:
            # open up to all currencies in LIVE mode
            self.ForexSymbols =['GBPUSD', 'GBPJPY', 'GBPCHF', 'GBPAUD', 'GBPNZD', 'EURUSD', 'EURNZD', 'EURJPY', 'EURAUD', 'AUDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAUUSD']
            self.AllowChannel = ['GBPUSD', 'GBPJPY', 'GBPCHF', 'GBPAUD', 'GBPNZD', 'EURUSD', 'EURNZD', 'EURJPY', 'EURAUD', 'AUDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAUUSD']
        else:
            # this is for backtesting mode
            #self.ForexSymbols = ['GBPJPY', 'GBPAUD', 'EURJPY', 'EURAUD', 'USDCAD', 'USDCHF', 'USDJPY']
            #self.AllowChannel = ['GBPJPY', 'GBPAUD', 'EURJPY', 'EURAUD', 'USDCAD', 'USDCHF', 'USDJPY']            
            self.ForexSymbols = ['EURAUD']
            self.AllowChannel = ['EURAUD']
            #self.AllowChannel = []
            self.Log(f"Running a backtest from: {self.backtest_start} until {self.backtest_end} at resolution {self.myRes} [2=Minute]")
            
        self.AllowManual = ['GBPUSD', 'GBPJPY', 'GBPCHF', 'GBPAUD', 'GBPNZD', 'EURUSD', 'EURNZD', 'EURJPY', 'EURAUD', 'AUDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAUUSD']

        # initialize our forex data 
        for symbol in self.ForexSymbols:
            forex = self.AddForex(symbol, self.myRes, Market.Oanda, True, self.DefaultLeverage)
            self.symbolInfo[symbol] = SymbolData(forex.Symbol, BarPeriod5M, RollingWindowSize1M, RollingWindowSize5M, RollingWindowSize15M, RollingWindowSize30M, RollingWindowSize1H, RollingWindowSize4H, RollingWindowSize24H)
            self.symbolInfo[symbol].my_algo = self
        
        # loop through all our symbols and request data subscriptions and initialize indicator
        for symbol, sd in self.symbolInfo.items():
            # set minimum price variation
            sd.minPriceVariation = self.Securities[symbol].SymbolProperties.MinimumPriceVariation
            sd.numbersQuantum = round(sd.numbersQuantum * 100.0 * sd.minPriceVariation, 6)
            self.Log(f"Subscribing to: {symbol} min price variation: {'{0:.6f}'.format(sd.minPriceVariation)} numbers quantum: {sd.numbersQuantum}")
            
            # define the indicator - need one per symbol and per indicator required
            #SI extra EMAs on the 1min & 5min & 15min charts
            sd.EMA1M_45 = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA1M_45", Resolution.Minute), 45)
            sd.EMA1M_135 = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA1M_135", Resolution.Minute), 135)
            sd.EMA1M_200 = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA1M_200",  Resolution.Minute), 200)
            sd.EMA5M_27 = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA5M_27",  Resolution.Minute), 27)
            sd.EMA15M_200 = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA15M_200",  Resolution.Minute), 200)

            sd.EMA1M = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA1M" + str(ExponentialMovingAveragePeriod), Resolution.Minute), ExponentialMovingAveragePeriod)
            sd.EMA5M = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA5M" + str(ExponentialMovingAveragePeriod), Resolution.Minute), ExponentialMovingAveragePeriod)
            sd.EMA15M = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA15M" + str(ExponentialMovingAveragePeriod), Resolution.Minute), ExponentialMovingAveragePeriod)
            sd.EMA30M = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA30M" + str(ExponentialMovingAveragePeriod), Resolution.Minute), ExponentialMovingAveragePeriod)
            sd.EMA1H = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA1H" + str(ExponentialMovingAveragePeriod), Resolution.Minute), ExponentialMovingAveragePeriod)
            sd.EMA4H = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA4H" + str(ExponentialMovingAveragePeriod), Resolution.Minute), ExponentialMovingAveragePeriod)
            sd.EMA24H = ExponentialMovingAverage(self.CreateIndicatorName(symbol, "EMA24H" + str(ExponentialMovingAveragePeriod), Resolution.Minute), ExponentialMovingAveragePeriod)
            # 4HR manually updated indicators
            sd.ADX4H = AverageDirectionalIndex(self.CreateIndicatorName(symbol, "ADX4H" + str(ExponentialMovingAveragePeriod), Resolution.Minute), 16)
            sd.Macd4H = MovingAverageConvergenceDivergence(self.CreateIndicatorName(symbol, "MACD4H 3-9-6", Resolution.Minute), 3, 9, 6)

            # ADX - auto updates, helper method
            sd.ADX1H = self.ADX(symbol, 18, Resolution.Hour)
            # Add ATR for 24hr period - auto updates, helper method
            sd.ATR24H = self.ATR(symbol, 14, MovingAverageType.Simple, Resolution.Daily)
    
            # define a 24hr consolidator to consolidate data for this symbol on the requested period
            consolidator24H = TradeBarConsolidator(BarPeriod24H) if sd.Symbol.SecurityType == SecurityType.Equity else QuoteBarConsolidator(BarPeriod24H)
            # write up our consolidator to update the indicator
            consolidator24H.DataConsolidated += self.OnDataConsolidated24H
            # we need to add this consolidator so it gets auto updates
            self.SubscriptionManager.AddConsolidator(sd.Symbol, consolidator24H)
            
            # define a 4hr consolidator to consolidate data for this symbol on the requested period
            consolidator4H = TradeBarConsolidator(BarPeriod4H) if sd.Symbol.SecurityType == SecurityType.Equity else QuoteBarConsolidator(BarPeriod4H)
            consolidator4H.DataConsolidated += self.OnDataConsolidated4H
            self.SubscriptionManager.AddConsolidator(sd.Symbol, consolidator4H)
            
            # define a 1hr consolidator to consolidate data for this symbol on the requested period
            consolidator1H = TradeBarConsolidator(BarPeriod1H) if sd.Symbol.SecurityType == SecurityType.Equity else QuoteBarConsolidator(BarPeriod1H)
            consolidator1H.DataConsolidated += self.OnDataConsolidated1H
            self.SubscriptionManager.AddConsolidator(sd.Symbol, consolidator1H)
            
            # define a consolidator to consolidate data for this symbol on the requested period
            consolidator30M = TradeBarConsolidator(BarPeriod30M) if sd.Symbol.SecurityType == SecurityType.Equity else QuoteBarConsolidator(BarPeriod30M)
            consolidator30M.DataConsolidated += self.OnDataConsolidated30M
            self.SubscriptionManager.AddConsolidator(sd.Symbol, consolidator30M)
            
            # define a consolidator to consolidate data for this symbol on the requested period
            consolidator15M = TradeBarConsolidator(BarPeriod15M) if sd.Symbol.SecurityType == SecurityType.Equity else QuoteBarConsolidator(BarPeriod15M)
            consolidator15M.DataConsolidated += self.OnDataConsolidated15M
            self.SubscriptionManager.AddConsolidator(sd.Symbol, consolidator15M)
            
            # define a consolidator to consolidate data for this symbol on the requested period
            consolidator5M = TradeBarConsolidator(BarPeriod5M) if sd.Symbol.SecurityType == SecurityType.Equity else QuoteBarConsolidator(BarPeriod5M)
            consolidator5M.DataConsolidated += self.OnDataConsolidated5M
            self.SubscriptionManager.AddConsolidator(sd.Symbol, consolidator5M)
            
            # define a consolidator to consolidate data for this symbol on the requested period
            consolidator1M = TradeBarConsolidator(BarPeriod1M) if sd.Symbol.SecurityType == SecurityType.Equity else QuoteBarConsolidator(BarPeriod1M)
            consolidator1M.DataConsolidated += self.OnDataConsolidated1M
            self.SubscriptionManager.AddConsolidator(sd.Symbol, consolidator1M)

        # Check if we are running in Live and set to ask FTI for actions to carry out live, otherwise check if we want to push specific manual trades through
        if self.ManualLiveTrading:
            self.LogExtra(f"Trading {self.ModeName}! Scheduling check for submit file every 5s - Hostname: {Environment.MachineName}", f"Startup")
            # add scheduled job to run every 5seconds while algorithm running - will want to add time checks
            self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday, DayOfWeek.Wednesday, DayOfWeek.Thursday, DayOfWeek.Friday, DayOfWeek.Sunday), self.TimeRules.Every(TimeSpan.FromSeconds(5)), self.CheckManualTrades)
            # add scheduled job to run 1 minute past every hour to send any email contents; runs every minute, but will only send if 1min past the hour           
        elif self.ManualHistoryTrading:         
            # if we're local - do not run pretend trades - just logging
            self.Log(f"Backtest Mode!  Setting to pump trades from hardcoded list - Hostname: {Environment.MachineName}")            
            # now need an event to check these are here and pump in the trades
            self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday, DayOfWeek.Wednesday, DayOfWeek.Thursday, DayOfWeek.Friday, DayOfWeek.Sunday), self.TimeRules.Every(TimeSpan.FromMinutes(1)), self.CheckHistoryTrades)

        if self.send_hourly_status_emails:
            self.Debug(f"Scheduling status every hour by email (LIVE) or to CSV (BACKTEST)")
            self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday, DayOfWeek.Wednesday, DayOfWeek.Thursday, DayOfWeek.Friday, DayOfWeek.Sunday), self.TimeRules.Every(TimeSpan.FromMinutes(1)), self.LogHourlySend)               
        
        if self.LiveMode: 
            self.LogExtra(f"Starting {self.ModeName}! On Hostname: {Environment.MachineName}", f"Starting up Fusion Algo")


    def OnData(self, data):
        # First thing is to update the highs/lows etc - need to do this even while warming up
        # loop through each symbol in our structure
        # if there is info for this one in the slice contained in 'data'
        timenow = self.Time
        

        for symbol in self.symbolInfo.keys():
            if not data.ContainsKey(symbol):
                # skip this symbol if no data bar
                continue

            '''UPDATE all counters, pre-warmup and post-warmup
            '''
            sd = self.symbolInfo[symbol]
            one_pip = sd.minPriceVariation * 10
            
            askpricenow = self.Securities[symbol].AskPrice  
            bidpricenow = self.Securities[symbol].BidPrice
            ask_price_high = data[symbol].Ask.High
            ask_price_low = data[symbol].Ask.Low
            bid_price_high = data[symbol].Bid.High
            bid_price_low = data[symbol].Bid.Low
            
            my_4h_trend = fusion_utils.get_trend_from_eheltrend(sd.EH_EL_tracker[ChartRes.res4H].current_template)

            # Set session at first startup, update on every tick after that
            if self.SessionID == SessionNames.Unknown:
               (self.SessionID, self.PrevSessionID, self.SessionOpen) = sd.UpdateSessions(self, self.Time, askpricenow, bidpricenow, self.log_session_changes)
            #also update on tick data - the SessionName is only stored in the algo - but Highs/Lows are per symbol
            sd.UpdateSessionsHighsLows(ask_price_low, ask_price_high, bid_price_low, bid_price_high, timenow)    

            # keep track of the high/low prices of the forming day since 5PM NY time last night
            if askpricenow < sd.LowAskCurrDay: 
                sd.LowAskCurrDay = askpricenow
            if bidpricenow < sd.LowBidCurrDay: 
                sd.LowBidCurrDay = bidpricenow
                if sd.LowBidCurrDay < sd.LowCurrWeek: sd.LowCurrWeek = sd.LowBidCurrDay 
                if sd.LowBidCurrDay < sd.LowCurrMonth: sd.LowCurrMonth = sd.LowBidCurrDay 
            if askpricenow > sd.HighAskCurrDay: 
                sd.HighAskCurrDay = askpricenow
            if bidpricenow > sd.HighBidCurrDay: 
                sd.HighBidCurrDay = bidpricenow
                if sd.HighBidCurrDay > sd.HighCurrWeek: sd.HighCurrWeek = sd.HighBidCurrDay 
                if sd.HighBidCurrDay > sd.HighCurrMonth: sd.HighCurrMonth = sd.HighBidCurrDay 

            #TODO in warmup get prev week and month highs / lows

            # Things which need updating after 5pm NY time daily - trading day related items
            if sd.newEma24HAvailable:
                if self.IsWarmingUp:
                  sd.newEma24HAvailable = False     

                sd.LowAskCurrDay = askpricenow
                sd.LowBidCurrDay = bidpricenow
                sd.HighAskCurrDay = askpricenow
                sd.HighBidCurrDay = bidpricenow
                sd.UpdateHighsLows(self.Time, askpricenow)         # figure out if the day, month or week has changed and set prices accordingly

                #self.Log(f"{symbol} Current 4HR Trend is {my_4h_trend}")
                if sd.Bars24H.Count > 5:
                    # update the data structures for tracking external highs and lows 
                    self.update_ext_structure(symbol, sd, bidpricenow, ChartRes.res24H)                


            # Every 4Hrs - update counters
            if sd.newEma4HAvailable:
                if self.IsWarmingUp:
                  sd.newEma4HAvailable = False      
                            
                if sd.Bars4H.Count > 5:
                    # update the data structures for tracking external highs and lows 
                    self.update_ext_structure(symbol, sd, bidpricenow, ChartRes.res4H)

            # Things which need updating every hour
            if sd.newEma1HAvailable:
                if self.IsWarmingUp:
                  sd.newEma1HAvailable = False      
                            
                if sd.Bars1H.Count > 5:
                    # update the data structures for tracking external highs and lows 
                    self.update_ext_structure(symbol, sd, bidpricenow, ChartRes.res1H)

                    new_ceil = sd.Is123RToNumbersMakesCeiling(sd.Bars1H, sd.Bars1HColour)
                    new_floor = sd.Is123GToNumbersMakesFloor(sd.Bars1H, sd.Bars1HColour)
                    if new_ceil != 0.0:
                        sd.Ceil123R_1H = new_ceil
                        sd.Floor123G_1H = 0.0
                    else:
                        if sd.Ceil123R_1H != 0.0:
                            sd.Ceil123R_1H = sd.CheckBrokenCeiling(sd.Ceil123R_1H, sd.Bars1H, sd.Bars1HColour) 
                    if new_floor != 0.0:
                        sd.Floor123G_1H = new_floor
                        sd.Ceil123R_1H = 0.0
                    else:
                        if sd.Floor123G_1H != 0.0:
                            sd.Floor123G_1H = sd.CheckBrokenFloor(sd.Floor123G_1H, sd.Bars1H, sd.Bars1HColour)
                # Keep tracking of a rolling 24H high and low price, on the hour
                sd.update_rolling_24H_levels(self.Time)
                (self.SessionID, self.PrevSessionID, self.SessionOpen) = sd.UpdateSessions(self, self.Time, askpricenow, bidpricenow, self.log_session_changes)



            if sd.newEma30MAvailable:
                if self.IsWarmingUp:
                    sd.newEma30MAvailable = False      

                #ceilings and floors at 30m resolution
                if sd.Bars30M.Count > 5:
                    # update the data structures for tracking external highs and lows 
                    self.update_ext_structure(symbol, sd, bidpricenow, ChartRes.res30M)
                    
                    new_ceil = sd.Is123RToNumbersMakesCeiling(sd.Bars30M, sd.Bars30MColour)
                    new_floor = sd.Is123GToNumbersMakesFloor(sd.Bars30M, sd.Bars30MColour)
                    if new_ceil != 0.0:
                        sd.Ceil123R_30M = new_ceil
                        sd.Floor123G_30M = 0.0
                    else:
                        if sd.Ceil123R_30M != 0.0:
                            sd.Ceil123R_30M = sd.CheckBrokenCeiling(sd.Ceil123R_30M, sd.Bars30M, sd.Bars30MColour) 
                    if new_floor != 0.0:
                        sd.Floor123G_30M = new_floor
                        sd.Ceil123R_30M = 0.0
                    else:
                        if sd.Floor123G_30M != 0.0:
                            sd.Floor123G_30M = sd.CheckBrokenFloor(sd.Floor123G_30M, sd.Bars30M, sd.Bars30MColour)

            if sd.newEma15MAvailable:
                if self.IsWarmingUp:
                    sd.newEma15MAvailable = False      

                #ceilings and floors at 15m resolution
                if sd.Bars15M.Count > 5:
                    # update the data structures for tracking external highs and lows 
                    self.update_ext_structure(symbol, sd, bidpricenow, ChartRes.res15M)
                    

            if sd.newEma5MAvailable:
                if self.IsWarmingUp:
                    sd.newEma5MAvailable = False

                #ceilings and floors at 5M resolution
                if sd.Bars5M.Count > 5:
                    # update the data structures for tracking external highs and lows 
                    # TODO: remove this as we have moved this update to the consolidator code.  Let's see if this works
                    #self.update_ext_structure(symbol, sd, bidpricenow, ChartRes.res5M)
                    

                    new_ceil = sd.Is123RToNumbersMakesCeiling(sd.Bars5M, sd.Bars5MColour)
                    new_floor = sd.Is123GToNumbersMakesFloor(sd.Bars5M, sd.Bars5MColour)
                    if new_ceil != 0.0:
                        sd.Ceil123R_5M = new_ceil
                        sd.Floor123G_5M = 0.0
                    else:
                        if sd.Ceil123R_5M != 0.0:
                            sd.Ceil123R_5M = sd.CheckBrokenCeiling(sd.Ceil123R_5M, sd.Bars5M, sd.Bars5MColour) 
                    if new_floor != 0.0:
                        sd.Floor123G_5M = new_floor
                        sd.Ceil123R_5M = 0.0
                    else:
                        if sd.Floor123G_5M != 0.0:
                            sd.Floor123G_5M = sd.CheckBrokenFloor(sd.Floor123G_5M, sd.Bars5M, sd.Bars5MColour)

            
            if sd.newEma1MAvailable:
                if self.IsWarmingUp:
                    sd.newEma1MAvailable = False      

                if sd.Bars1M.Count > 5:
                    # update the data structures for tracking external highs and lows 
                    self.update_ext_structure(symbol, sd, bidpricenow, ChartRes.res1M)


            
        
        # don't do anything trading related until after warmed up for indicators
        if self.IsWarmingUp: return
        
        '''Main event loop for POST WARMUP stuff - this is where all the action triggers from
            '''
        # loop through each symbol in our structure
        for symbol in self.symbolInfo.keys():
            if not data.ContainsKey(symbol):
                # skip this symbol if no data bar
                continue
            sd = self.symbolInfo[symbol]
            askpricenow = self.Securities[symbol].AskPrice  
            bidpricenow = self.Securities[symbol].BidPrice
            
            longsign = False
            shortsign = False

            ask_price_high = data[symbol].Ask.High
            ask_price_low = data[symbol].Ask.Low
            bid_price_high = data[symbol].Bid.High
            bid_price_low = data[symbol].Bid.Low

            ask_price_diff = ask_price_high - ask_price_low
            bid_price_diff = bid_price_high - bid_price_low
            ask_price_from_high = ask_price_high - askpricenow
            bid_price_from_high = bid_price_high - bidpricenow
            ask_pips_diff = round(ask_price_diff / one_pip, 3)
            bid_pips_diff = round(bid_price_diff / one_pip, 3)
            ask_pips_from_high = round(ask_price_from_high / one_pip, 3)
            bid_pips_from_high = round(bid_price_from_high / one_pip, 3)
            
            
            ######## TRENDS
            '''TODO:  Add in a section to work out the 24H, 4H, 1H trends - so we have them to work with elsewhere
            mytrend24H = Trends.Nothing
            if sd.emaWindow24H.Count >= 5: 
                mytrend24H = sd.WhatTrend(sd.emaWindow24H, sd.Bars24H, 1, 4)
            '''
            if sd.newEma4HAvailable:
                sd.set_trend_4H() 
                sd.EntryADXTrend4H = sd.Trend4H
            
            if sd.newEma1HAvailable:
                sd.set_trend_1H() 
                sd.EntryADXTrend1H = sd.Trend1H

            ######## WATCHING
            '''UPDATE any counters only required AFTER warm-up - when trading states are important
            '''
            if sd.newEma24HAvailable or sd.FirstDay:
                sd.newEma24HAvailable = False
                # sd.tradedToday = 0      # TODO: this will cross over if we have an open trade past 5pm.  Need better way
                self.CountEmails = 0    # reset the 'daily emails count'
                if sd.FirstDay:
                    sd.FirstDay = False
                    # this is where we need to output the Highs, Lows, Bar Patterns already found.  To Cross-check the load
                    sd.log_tracking_stats(self)

            # 4HR checks - last block, so clear the new marker
            if sd.newEma4HAvailable:
                sd.newEma4HAvailable = False
                
            # 1HR checks - last block, so clear the new market
            if sd.newEma1HAvailable:
                sd.newEma1HAvailable = False
                #trading_window = fusion_utils.get_trading_window(self.Time)   @chris, this is where I tested this function was working
                
                #Si ... EET is 6 hours difference to EDT and 7 to EST
                self.oandaChartTime = self.Time + timedelta(hours=6, minutes=0) #Si Signal Candle (open time)

                # Setup some values for this round of checks now we've got a new 1Hr period to look back over 
                cema = round(float(sd.emaWindow1H[0].Value), 6)
                #added 4 hr ema to track
                c4ema = round(float(sd.emaWindow4H[0].Value), 6)
                ctime = sd.Bars1H[0].EndTime
                
                skip_section = True         # get rid of the noise for a bit - turn this to False to re-enable 5min stuff                          
                if not skip_section:
                
                    if sd.is_looking_for_possible_trade() or sd.is_looking_for_entry():          # only actively start up new possible trades if we are not already busy
                        if symbol in self.AllowChannel and not sd.looking_for_channel_1H:
                            self.channel_breakout_looking_checks_1H(self, symbol, sd, timenow, bidpricenow, my_4h_trend)
                            
                        if symbol in self.AllowChannel and sd.looking_for_channel_1H:
                            self.channel_breakout_pre_entry_checks_1H(self, symbol, sd)


            if sd.newEma30MAvailable:
                sd.newEma30MAvailable = False

                skip_section = True         # get rid of the noise for a bit - turn this to False to re-enable 5min stuff                          
                if not skip_section:

                    if sd.is_looking_for_possible_trade() or sd.is_looking_for_entry():
                        # TODO: reinstate 30 minute checks for Perfects, but using totally separate tracking variables
                        # TODO: make 30minute Perfect emails fire again
                        if symbol in self.AllowChannel and not sd.looking_for_channel_30M:
                            self.channel_breakout_looking_checks_30M(self, symbol, sd, timenow, bidpricenow, my_4h_trend)
                            
                        if symbol in self.AllowChannel and sd.looking_for_channel_30M:
                            self.channel_breakout_pre_entry_checks_30M(self, symbol, sd)


            if sd.newEma5MAvailable:
                sd.newEma5MAvailable = False

                #SI 23.11.2022 temp checking of the bar types:
                candle_type = fusion_utils.get_candle_type(sd.Bars5M, sd.Bars5MColour, sd.minPriceVariation * 10)
                #self.Debug("Candle Type: " + str(candle_type))                

                self.candle_item["candle_time_mt4"] = fusion_utils.get_times(sd.Bars5M[0].Time, 'us')['mt4'].strftime("%Y.%m.%d, %H:%M:%S")             
                self.candle_item["candle_chart"] = "5 min"
                self.candle_item["candle_type"] = candle_type
                self.candle_item["candle_symbol"] = symbol

                self.candle_type_log.append(deepcopy(self.candle_item))


                skip_section = True         # get rid of the noise for a bit - turn this to False to re-enable 5min stuff                          
                if not skip_section:
                    if sd.is_looking_for_possible_trade() or sd.is_looking_for_entry():
                        # TODO: reinstate 5 minute checks for Perfects, but using totally separate tracking variables
                        # TODO: make 5 minute Perfect emails fire again
                        if symbol in self.AllowChannel and not sd.looking_for_channel_5M:
                            self.channel_breakout_looking_checks_5M(self, symbol, sd, timenow, bidpricenow, my_4h_trend)
                            
                        if symbol in self.AllowChannel and sd.looking_for_channel_5M:
                            self.channel_breakout_pre_entry_checks_5M(self, symbol, sd)

           
            # trap particular time
            debug_time = fusion_utils.get_times(self.Time, 'us')['mt4'].strftime("%Y.%m.%d, %H:%M:%S")     
            if debug_time == "2022.11.16, 00:40:00":
                self.Debug({debug_time})                
                my_hit = 1


            if sd.newEma1MAvailable:
                sd.newEma1MAvailable = False
                if sd.tbu_perfect_tracker[ChartRes.res5M].BO_active and not sd.is_in_a_trade(self):
                    candle_open_1m_mt4 = fusion_utils.get_candle_open_time(fusion_utils.get_times(self.Time, 'us')['mt4'], ChartRes.res1M)

                    # If we have a possible Perfect Brad breakout in progress it may reach end of TradingWindow
                    # check for this and clear it down if it expires                  
                    sd.tbu_perfect_tracker[ChartRes.res5M].check_for_timeout(self, symbol, ChartRes.res5M, timenow, candle_open_1m_mt4)
                                                            
                    # if void trade values have not been set yet, call this until they are
                    if sd.tbu_perfect_tracker[ChartRes.res5M].void_trade_high == 0.0 and sd.tbu_perfect_tracker[ChartRes.res5M].void_trade_low == 0.0:
                        sd.tbu_perfect_tracker[ChartRes.res5M].set_void_prices(self, symbol, candle_open_1m_mt4)

                    #every minute we need to get the rolling highs and lows to determine headroom / move to breakeven
                    sd.tbu_perfect_tracker[ChartRes.res5M].get_rolling_high_or_low(self, symbol, candle_open_1m_mt4)


                    if ask_pips_diff > 1.0:
                        if self.log_bar_height_diffs: self.Log(f"{symbol} Bar height checks {self.myRes}:  ask_pips_diff = {ask_pips_diff}  ask_pips_from_high = {ask_pips_from_high}")
                    if bid_pips_diff > 1.0:
                        if self.log_bar_height_diffs: self.Log(f"{symbol} Bar height checks {self.myRes}:  bid_pips_diff = {bid_pips_diff}  bid_pips_from_high = {bid_pips_from_high}")
                    ema9 = round(sd.emaWindow1M[0].Value,6)
                    ema45 = round(sd.emaWindow1M_45[0].Value,6)
                    ema135 = round(sd.emaWindow1M_135[0].Value,6)
                    ema200 = round(sd.emaWindow1M_200[0].Value,6)
                    close_price = sd.Bars1M[0].Bid.Close

                                        
                    #if sd.tbu_perfect_tracker[ChartRes.res5M].BO_pullback1_breached and sd.tbu_perfect_tracker[ChartRes.res5M].squeeze_status == "Waiting":                                                                         
                        # now we know that we are looking for the squeeze - so check for it happening
                        # make sure we wait until at least 1 minute has passed since the pullback1 was breached
                        #if sd.tbu_perfect_tracker[ChartRes.res5M].BO_pullback1_breached_time + timedelta(minutes=1) <= timenow:
                        #sd.tbu_perfect_tracker[ChartRes.res5M].check_for_squeeze(self, symbol, ChartRes.res5M, close_price, timenow, ema9, ema45, ema135, ema200, candle_open_1m_mt4)
                            #if result:
                                #self.Log(f"Perfect Squeeze found on 5M chart for {symbol}")
                        #self.pb_wait_cycles =+ 1

                    #if sd.tbu_perfect_tracker[ChartRes.res5M].squeeze_found:
                    if sd.tbu_perfect_tracker[ChartRes.res5M].BO_pullback1_breached and not sd.tbu_perfect_tracker[ChartRes.res5M].enter_trade:  
                        sd.pb_wait_cycles =+ 1  
                        if sd.pb_wait_cycles > 0:                        
                            # now we know that we are looking for trade entry ... check entry conditions                 
                            result = sd.tbu_perfect_tracker[ChartRes.res5M].check_for_trade_entry(self, symbol, ChartRes.res5M, close_price, timenow, ema9, ema45, ema135, ema200, askpricenow, bidpricenow, \
                                sd.minPriceVariation * 10, sd.Bars1M[0].Bid.High, sd.Bars1M[0].Bid.Low, \
                                sd.EH_EL_tracker[ChartRes.res5M].get_EH(), sd.EH_EL_tracker[ChartRes.res5M].get_EL(), candle_open_1m_mt4 )
                            if result:
                                self.Log(f"Perfect Trade entry found on 5M chart for {symbol}")                


                # If we are in a Brad Perfect trade, then every minute need to watch for candle closures, above or below the 9EMA
                if sd.is_in_a_trade(self) and sd.activeStrat == Strats.BradPerfect:                      
                    # We are in the right kind of trade - now check... first see if we are positive pips
                    pnlpips = self.get_current_pnlpips(sd, bidpricenow, askpricenow) 
                    if pnlpips > 0:
                        if sd.manualDirection:      # this means we are in a LONG trade
                            if sd.Bars1M[0].Bid.Close < sd.emaWindow1M[0].Value:
                                # close below the 9EMA - so close the trade
                                #TODO: make this properly honour the actual order levels - we can have 3
                                self.close_position_and_clear_open_orders_cleanly(symbol, 1, 0.0, "BradPerfect LONG defensive: 1min candle closed below EMA", logging = self.log_position_closures) 
                        else:                       # this means we are in a SHORT trade
                            if sd.Bars1M[0].Bid.Close > sd.emaWindow1M[0].Value:
                                # close above the 9EMA - so close the trade
                                #TODO: make this properly honour the actual order levels - we can have 3
                                self.close_position_and_clear_open_orders_cleanly(symbol, 1, 0.0, "BradPerfect SHORT defensive: 1min candle closed above EMA", logging = self.log_position_closures) 


    
            ''' if there is a possible Perfect Brad breakout in progress, there are certain things we need to check / track continuously
            '''
            if sd.tbu_perfect_tracker[ChartRes.res5M].BO_active and not sd.is_in_a_trade(self):
                    # we are in an active breakout that has not been entered yet

                    # check to see if void high or low has been breached, will cancel BO if this is the case
                    sd.tbu_perfect_tracker[ChartRes.res5M].check_for_void_trade_high_or_low_breached(self, symbol, ChartRes.res5M, \
                        bid_price_low, bid_price_high, timenow)

                    # check to see if the HH or LL has been breached, will cancel BO if this is the case
                    if not sd.tbu_perfect_tracker[ChartRes.res5M].BO_hh_or_ll_breached:
                        sd.tbu_perfect_tracker[ChartRes.res5M].check_for_LL_or_HH_breach(self, symbol, ChartRes.res5M, \
                            bid_price_low, bid_price_high, timenow)
                    
                    if not sd.tbu_perfect_tracker[ChartRes.res5M].BO_pullback1_breached:   
                        sd.tbu_perfect_tracker[ChartRes.res5M].check_price_to_pullback1(self, symbol, ChartRes.res5M, bidpricenow, bid_price_low, bid_price_high, timenow, \
                            sd.EH_EL_tracker[ChartRes.res5M].get_EH(), sd.EH_EL_tracker[ChartRes.res5M].get_EL(), sd.minPriceVariation * 10)

            #trade entry checks passed, just need to wait for the next candle count
            if sd.tbu_perfect_tracker[ChartRes.res5M].enter_trade and not sd.is_in_a_trade(self) and sd.tbu_perfect_tracker[ChartRes.res5M].BO_active: 
                # need to make sure the breakout is still active or it will keep trying to re-enter the trade again
                sd.tbu_perfect_tracker[ChartRes.res5M].do_enter_trade(self, symbol, timenow)                 
              

            # always update any live trackers
            self.price_tracker_lib.update_trackers(self, symbol, bidpricenow, timenow)


            ############## MANUAL TRADING
            '''MANUAL trading checks - look for values pumped through from FTI in Live mode, or from the historic manual trade dictionary in backtest
            '''                    
            if not sd.is_in_a_trade(self):
                # put on ManualTrigger trade if one found in when we pass through the loop and we are not already trading
                if sd.manual_fti_sign and sd.manualTradeFound and not sd.manualTradeOn and sd.activeStrat == Strats.Nothing and sd.tradedToday < 3:
                    # relies on another part of the process (FTI manual trades, or backtest timers, populating the fields)
                    self.Log(f"{symbol} Current 4HR Trend is {my_4h_trend}")
                    
                    # we are about to enter a trade - track how far price goes from here
                    if sd.manualDirection:
                        direction_call = "LONG"
                    else:
                        direction_call = "SHORT"
                    #self.price_tracker_lib.add_tracker(symbol, timenow, bidpricenow, direction_call, 50.0, timedelta(hours=2), "Brad Perfect", 0, sd.minPriceVariation * 10)
                    
                    self.manual_order_setup_and_entry(self, symbol, sd, timenow, bidpricenow, askpricenow)
                    sd.tbu_perfect_manager[ChartRes.res5M].create_manage_perfect(self, symbol, self.Time, logging=True)

                    
            if sd.tbu_perfect_manager[ChartRes.res5M].perfect_in_trade:
                # manage stops all the time 
                
                sd.tbu_perfect_manager[ChartRes.res5M].manage_perfect_trade(self, symbol, self.Time, bidpricenow, askpricenow, logging=True)

                if self.do_manage_stops and not sd.trailling_stop:
                    self.manage_breakout_stops(sd, askpricenow, bidpricenow, sd.minPriceVariation * 10)
                elif self.do_manage_stops and sd.trailling_stop:
                    #currently used on Brad perfect
                    self.manage_trailling_stops(sd, askpricenow, bidpricenow, sd.minPriceVariation * 10)
                        
            # now update take profit if needed

            # this check proves that this symbol was JUST updated prior to this OnData function being called
            if sd.IsReady() or sd.WasJustUpdated(self.Time):    #changed to or for testing
                sd.countDatapoints += 1


    # Function used to update all the EH and EL structures depending on the resolution passed through.
    # contains some logging override functionality, to allow us to focus on 5Min EH/EL for now
    def update_ext_structure(self, symbol, sd, bid_now, chart_res):
        my_bars = None
        if chart_res == ChartRes.res1M:
            my_bars = sd.Bars1M
            my_colours = sd.Bars1MColour
            logging = False        
        if chart_res == ChartRes.res5M:
            my_bars = sd.Bars5M
            my_colours = sd.Bars5MColour
            logging = True
        if chart_res == ChartRes.res15M:
            my_bars = sd.Bars15M
            my_colours = sd.Bars15MColour
            logging = False
        if chart_res == ChartRes.res30M:            
            my_bars = sd.Bars30M
            my_colours = sd.Bars30MColour
            logging = False
        if chart_res == ChartRes.res1H:
            my_bars = sd.Bars1H
            my_colours = sd.Bars1HColour
            logging = False
        if chart_res == ChartRes.res4H:
            my_bars = sd.Bars4H
            my_colours = sd.Bars4HColour
            logging = False
        if chart_res == ChartRes.res24H:
            my_bars = sd.Bars24H
            my_colours = sd.Bars24HColour
            logging = False            

        # This section can be used to debug a specific date in the EH/EL stuff
        date_time_str = '03/08/2022 02:10:00'
        date_time_obj = datetime.strptime(date_time_str, '%d/%m/%Y %H:%M:%S')
        if chart_res == ChartRes.res5M and self.Time == date_time_obj and symbol == "GBPJPY":
            my_hit = 1

        if my_bars != None:
            # check for a peak and log it if we find one
            is_peak = False
            peak_time = None
            peak_high = 0.0
            peak_lowpoint = 0.0
            outside_bar_peak = False
            (is_peak, peak_high, peak_time, outside_bar_peak, peak_lowpoint) = sd.is_123_peak(my_bars)

            is_trough = False
            trough_time = None
            trough_low = 0.0
            trough_highpoint = 0.0
            outside_bar_trough = False
            (is_trough, trough_low, trough_time, outside_bar_trough, trough_highpoint) = sd.is_123_trough(my_bars)

            check_price = 0.0
            if my_colours[0] == GREEN:
                check_price = my_bars[0].Bid.High
            if my_colours[0] == RED:
                check_price = my_bars[0].Bid.Low
            if check_price != 0.0:
                # check if the price has pulled below and EL or above an EH and maybe pulled an EL or EH closer
                if sd.EH_EL_tracker[chart_res].check_price_broke_levels(my_colours[0], check_price):
                    pull_time = self.Time
                    mt4_pull_time = fusion_utils.get_times(self.Time, 'us')['mt4']
                    if self.log_eh_el_summary and logging and not self.IsWarmingUp: self.Log(f"{symbol} EL Pull   @ NY: {pull_time} | MT4: {mt4_pull_time} - {chart_res} EH: {sd.EH_EL_tracker[chart_res].get_EH()} EL: {sd.EH_EL_tracker[chart_res].get_EL()} EH_EL_gap: {sd.EH_EL_tracker[chart_res].get_EH_EL_gap()}")

            do_first = "peak"
            peak_done = False
            if is_peak and is_trough:
                # TODO: EH or EL could both form - this is a place we have to be careful with the logic
                if sd.EH_EL_tracker[chart_res].last_found == "peak" and sd.EH_EL_tracker[chart_res].EH_highest_for_pull_time == None and sd.EH_EL_tracker[chart_res].EL_lowest_for_pull_time == None:
                    do_first = "trough"
                if sd.EH_EL_tracker[chart_res].last_found == "trough" and sd.EH_EL_tracker[chart_res].EH_highest_for_pull_time != None and sd.EH_EL_tracker[chart_res].EL_lowest_for_pull_time == None:
                    do_first = "trough"

            if is_peak and do_first == "peak":
                peak_done = True
                mt4_peak_time = fusion_utils.get_times(peak_time, 'us')['mt4']               
                if self.log_eh_el_detail and logging and not self.IsWarmingUp: self.Log(f"{symbol} has a {chart_res} peak at NY: {peak_time} | MT4: {mt4_peak_time} with {peak_high}")
                # this is where the new peak needs to be logged and the EH/EL logic checked
                if sd.EH_EL_tracker[chart_res].process_update(peak_high, peak_time, peak_lowpoint, "peak", sd.minPriceVariation * 10):
                    # we changed something about EH/EL
                    if self.log_eh_el_summary and logging and not self.IsWarmingUp: self.Log(f"{symbol} EH Change @ NY: {peak_time} | MT4: {mt4_peak_time} - {chart_res} EH: {sd.EH_EL_tracker[chart_res].get_EH()} EL: {sd.EH_EL_tracker[chart_res].get_EL()} EH_EL_gap: {sd.EH_EL_tracker[chart_res].get_EH_EL_gap()}")

            # check for a trough and log if it we find one

            if is_trough:
                mt4_trough_time = fusion_utils.get_times(trough_time, 'us')['mt4']    
                if self.log_eh_el_detail and logging and not self.IsWarmingUp: self.Log(f"{symbol} has a {chart_res} trough at NY: {trough_time} | MT4: {mt4_trough_time} with {trough_low}")
                # this is where the new trough needs to be logged and the EH/EL logic checked
                if sd.EH_EL_tracker[chart_res].process_update(trough_low, trough_time, trough_highpoint, "trough", sd.minPriceVariation * 10):
                    # we changed something about EH/EL
                    if self.log_eh_el_summary and logging and not self.IsWarmingUp: self.Log(f"{symbol} EL Change @ NY: {trough_time} | MT4: {mt4_trough_time} - {chart_res} EH: {sd.EH_EL_tracker[chart_res].get_EH()} EL: {sd.EH_EL_tracker[chart_res].get_EL()} EH_EL_gap: {sd.EH_EL_tracker[chart_res].get_EH_EL_gap()}")

            if not peak_done and is_peak:
                mt4_peak_time = fusion_utils.get_times(peak_time, 'us')['mt4']               
                if self.log_eh_el_detail and logging and not self.IsWarmingUp: self.Log(f"{symbol} has a {chart_res} peak at NY: {peak_time} | MT4: {mt4_peak_time} with {peak_high}")
                # this is where the new peak needs to be logged and the EH/EL logic checked
                if sd.EH_EL_tracker[chart_res].process_update(peak_high, peak_time, peak_lowpoint, "peak", sd.minPriceVariation * 10):
                    # we changed something about EH/EL
                    if self.log_eh_el_summary and logging and not self.IsWarmingUp: self.Log(f"{symbol} EH Change @ NY: {peak_time} | MT4: {mt4_peak_time} - {chart_res} EH: {sd.EH_EL_tracker[chart_res].get_EH()} EL: {sd.EH_EL_tracker[chart_res].get_EL()} EH_EL_gap: {sd.EH_EL_tracker[chart_res].get_EH_EL_gap()}")

            

