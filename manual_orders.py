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
from orders import *
from QuantConnect import Market
from io import StringIO
import pandas as pd

'''Single code file for setting up and entering manual orders either from backtest or from FTI'''

class QCalgo_manual_orders(QCalgo_order_management):
    def manual_order_setup_and_entry(self, sender, symbol, sd, timenow, bidpricenow, askpricenow):

        goShort = not sd.manualDirection
        betmultiple = sd.manualLotSize
        tradeID = sd.manualTradeID
        expectedentry = sd.manualExpectedEntry
        okToPlace = False
        th = sd.manualTradeHour
        tm = sd.manualTradeMinute
        checkmin = sd.manualCheckMinutes
        
        # first look for trade time and date if we are not conditionally entering
        # TODO: add values for 'immediate manual trade entry from FTI
        if sd.manualTradeDate.date() == sender.Time.date() and not sd.manualTradeConditional:
            
            if th == timenow.hour and (tm == timenow.minute or tm == (timenow.minute-1) or tm == (timenow.minute-2)):
                # we have picked up we need to do a trade in this currency manually (now) and we don't already have it running
                sd.manualTradeOn = True
                sd.manualTradeFound = False
                sd.tradedToday += 1           # do this to avoid trading more than 3 time in a day - as a safety for now
                if sd.type_of_trade_found != Strats.Nothing:
                    sd.activeStrat = sd.type_of_trade_found
                else:
                    sd.activeStrat = Strats.ManualTrigger
                # TODO: add a filter for logging manual trade activity on or off
                if sd.trailling_stop:
                    sender.Log(f"TRADE Manual trailling stop - {symbol} Short: {goShort} Multiplier {betmultiple} TradeID {tradeID}\nStop Pips {sd.trailling_pips} and \nProfit Pips {sd.profit_dist}")
                else:
                    sender.Log(f"TRADE Manual stop levels - {symbol} Short: {goShort} Multiplier {betmultiple} TradeID {tradeID}\nStop Loss Levels {sd.breakout_trail} and \nProfit Levels {sd.breakout_pnl}")
                okToPlace = True
        
        # TODO: set bankroll sizes based on logic managed centrally
        ''' Change to right value for LIVE'''
        if sender.LiveMode:
            unitbuy = 25000
        else:
            unitbuy = 600000     # set this from calculation of limits - bankroll

        '''Set the trading window times - also should add holiday calendar checking to this '''
        tradingWindowOpen = False
        tradingWindowOpen = sender.get_trading_window(timenow, sd.activeStrat)

        if sender.JustWatching:
            sender.Log(f"Found a new trade in {symbol} - but not set to trading mode")   #could add an email to this effect
            okToPlace = False
            sd.ClearTracking()
        
        # TODO: switch live trade calculation to a request from LEAN engine, this can get out of whack
        if okToPlace and tradingWindowOpen and sender.LiveTradeCount == 2:
            sender.Log(f"Found a new trade in {symbol} - but too many active trades; skipping")
            okToPlace = False
            sd.ClearTracking()
        
        # this is where actual trade entry happens if conditions have been
        if okToPlace and tradingWindowOpen:
            sd.EntryMacdSignal = round(sd.Macd4H.Signal.Current.Value, 5)
            sd.EntryMacdHist = round(sd.Macd4H.Histogram.Current.Value, 5)
            sd.EntryMacdFast = round(sd.Macd4H.Fast.Current.Value, 5)
            sd.EntryMacdSlow = round(sd.Macd4H.Slow.Current.Value, 5)
            sd.EntryMacdCurrent = round(sd.Macd4H.Current.Value, 5)
            sd.EntryMacdSigDelt = round((sd.Macd4H.Current.Value - sd.Macd4H.Signal.Current.Value)/sd.Macd4H.Fast.Current.Value, 5)
            sd.EntrySpreadPips = round((askpricenow - bidpricenow)/(sd.minPriceVariation * 10) ,6)
            entry_pips = round((askpricenow - bidpricenow)/(sd.minPriceVariation * 10) ,6)
            
            times_dict = fusion_utils.get_times(sender.Time, 'us') 
            trading_window = fusion_utils.get_trading_window(sender.Time)
            sender.Log(f"Timezones: New York: {sender.Time} | London: {times_dict['uk']} | MT4: {times_dict['mt4']} | Trading Window: {trading_window}")
            
            # do not enter trades with spread > 5.0 pips
            expected_size = 0.0
            if entry_pips <= 5.0:
                if goShort:
                    sender.open_position_short(symbol, sd, unitbuy, betmultiple, askpricenow, bidpricenow, entry_pips, trigger_level=1, logging=True)
                    expected_size = -1.0 * unitbuy * betmultiple
                else:
                    sender.open_position_long(symbol, sd, unitbuy, betmultiple, askpricenow, bidpricenow, entry_pips, trigger_level=1, logging=True)
                    expected_size = 1.0 * unitbuy * betmultiple
            else:
                sender.Log(f"Spread too wide to enter trade at {entry_pips} pips - Clear tracking {symbol} ")
                sd.ClearTracking()    
            actual_size = sender.get_open_order_size(symbol, sd, trigger_level=1)
            sender.Log(f"{symbol}: trade entered, checked order sizes, expecting {expected_size} and received {actual_size}")

        elif okToPlace and not tradingWindowOpen:
            sender.Log(f"Trade found outside window - NO trade - Clear tracking {symbol} ")
            sd.ClearTracking()


    def CheckManualTrades(self):
        if not self.InCloud:        # if we're local - do not run pretend trades - just logging
            return
        if self.IsWarmingUp:
            return
        UpAndRunning = False
        try:
            # now fetch the CSV info from Enjo - manual file should only ever have 1 line
            csv = self.Download(self.FusionCsvLiveUrl)
        
            # read file (which needs to be a csv) to a pandas DataFrame. include following imports above
            # TODO: add the ability to set a manual trade to IMMEDIATE - i.e. do not check the time, just enter it - maybe use special date?
            self.ldf = pd.read_csv(StringIO(csv), delimiter=',', header=None,  
                names = [ 'TradeID', 'Direction', 'Pair', 'LotSize', 'TradeDate', 'TradeHour', 'TradeMinute', 'Submitted', 'ExpectedEntry','RealTrade','Conditional','CheckMinutes','OrderPips'])
            self.ldf['TradeID'] = pd.to_numeric(self.ldf['TradeID'])
            self.ldf['Direction'] = pd.to_numeric(self.ldf['Direction'])
            self.ldf['Pair'] = pd.to_string(self.ldf['Pair'])
            self.ldf['LotSize'] = pd.to_numeric(self.ldf['LotSize'])
            self.ldf['TradeDate'] = pd.to_datetime(self.ldf['TradeDate'], format = '%d/%m/%Y')
            self.ldf['TradeHour'] = pd.to_numeric(self.ldf['TradeHour'])
            self.ldf['TradeMinute'] = pd.to_numeric(self.ldf['TradeMinute'])
            self.ldf['Submitted'] = pd.to_datetime(self.ldf['Submitted'])
            self.ldf['ExpectedEntry'] = pd.to_numeric(self.ldf['ExpectedEntry'])
            self.ldf['RealTrade'] = self.ldf['RealTrade'].astype(bool)
            self.ldf['Conditional'] = self.ldf['Conditional'].astype(bool)
            self.ldf['CheckMinutes'] = pd.to_numeric(self.ldf['CheckMinutes'])
            self.ldf['OrderPips'] = pd.to_numeric(self.ldf['OrderPips'])
            #self.Log(f"Count of live trade instructions: {len(self.ldf.index)}" + f"{self.ldf}")
            if len(self.ldf.index) != 1:
                self.Log("Error fetching manual FTI file - don't have just 1 line")
                self.Quit()    
            # Now update the correct instruments flag -- NOT RealTrade means take only PAPER trades from the system
            if (not self.LiveMode and not self.ldf["RealTrade"][0]) or (self.LiveMode and self.ldf["RealTrade"][0]):
                if self.LastTradeID != -1:
                    # finding an old file on startup, we don't want to push the trade through
                    UpAndRunning = True
                #else:
                #    # this is the first check - send something to FTI
                #    myjson = '''
                #    {
                #    "product": "dailyAlert",
                #    "version": "1.0",
                #    "statisticDate": "2021-06-23",
                #    "currencyPairs": [
                #    {"symbol": "GDPUSD","bidpriceData": {"yesterdayLow": "1.3836","yesterdayHigh": "1.3901"}},
                #    {"symbol": "GDBJPY","bidpriceData": {"yesterdayLow": "101.86","yesterdayHigh": "101.94"}}
                #    ]}'''
                #    self.Log(f"About to call json.loads")
                #    payload = json.loads(myjson)
                #    payload2 = json.dumps(payload)
                #    headers = Dictionary[str, str]()
                #    headers.Add("Ocp-Apim-Subscription-Key", "5fc2b1c2a84142bf8efc223435620a38")
                #    headers.Add("Ocp-Apim-Trace", "true")
                #    callresult = self.Notify.Web(self.FusionJsonReports, payload2, headers)
                #    self.Log(f"Tried to call FTI API - result: {callresult}")
                #self.LastTradeID = self.symbolInfo[self.ForexSymbols[self.ldf["Pair"][0]]].manualTradeID
                self.LastTradeID = self.CurrentTradeID
                #self.Log(f"About to check Trade IDs - LastTradeID:{self.LastTradeID} TradeID:{self.ldf['TradeID'][0]}")
                if self.LastTradeID != int(self.ldf['TradeID'][0]):
                    # we have a new manual trade to push through.  Log and go
                    symbol = self.ldf["Pair"][0]
                    # symbol = self.ForexSymbols[self.ldf["Pair"][0]]
                    self.Log(f"Found new manual trade - ID: {self.ldf['TradeID'][0]} - Symbol: {symbol}")
                    if symbol not in self.ForexSymbols:
                        self.LogExtra(f"Received FTI request for unsupported symbol {symbol} - ID: {self.ldf['TradeID'][0]} - SKIPPING", "FTI Unsupported Symbol")
                        return
                    self.symbolInfo[symbol].manualTradeID = int(self.ldf['TradeID'][0])
                    mytime = self.Time
                    mhr = mytime.hour
                    mmin = mytime.minute
                    self.CurrentTradeID = self.ldf['TradeID'][0]
                    if UpAndRunning:
                        # This should only push a trade if we haven't just started up
                        '''
                        Now check to see which kind of action we've been asked by FTI to carry out.  Single line in the file with an action code.
                        FTIActions(enum.Enum):
                            ShortTrade = 0
                            LongTrade = 1
                            CancelTrade = 2
                            MoveStop = 3
                            MoveProfit = 4 
                            ApproveTrade = 5
                            ReadSettings = 6
                            ReadPreApproved = 7
                            ResetTrading = 8
                            SplitPot = 9 
                        '''
                        if self.ldf['Direction'][0] == FTIActions.ShortTrade.value:
                            self.symbolInfo[self.ldf["Pair"][0]].manualDirection = False
                        elif self.ldf['Direction'][0] == FTIActions.LongTrade.value:
                            self.symbolInfo[self.ldf["Pair"][0]].manualDirection = True
                        elif self.ldf['Direction'][0] == FTIActions.CancelTrade.value:
                            # we need to cancel an open trade
                            if self.symbolInfo[symbol].manualTradeOn:
                                self.Log(f"Received an FTI cancel request {symbol} - ID: {self.ldf['TradeID'][0]}")
                                # TODO: Need to work out how to cleanly do this cancel, while dealing with Trade levels
                                self.Transactions.CancelOpenOrders(symbol)
                                self.Liquidate(symbol)
                                # TODO: Need a cleaner ClearTracking mechanism
                                self.symbolInfo[symbol].ClearTracking()
                            self.LiveTradeCount -= 1
                            if self.LiveTradeCount < 0:
                                self.LiveTradeCount = 0
                            self.LogExtra(f"Current live trades count: {self.LiveTradeCount}", "Force cancel - live trade count")
                            return
                        elif self.ldf['Direction'][0] == FTIActions.MoveStop.value:
                            # we need to change stop loss on an open trade
                            self.symbolInfo[symbol].ftichangestop = True
                            self.symbolInfo[symbol].ftichangepips = self.ldf['OrderPips'][0].item()
                            self.Log(f"Received an FTI move stop request {symbol} - ID: {self.ldf['TradeID'][0]} Pips: {self.symbolInfo[symbol].ftichangepips}")
                            return
                        elif self.ldf['Direction'][0] == FTIActions.MoveProfit.value:
                            # we need to change take profit on an open trade
                            self.symbolInfo[symbol].ftichangeprofit = True
                            self.symbolInfo[symbol].ftichangeprofitpips = self.ldf['OrderPips'][0].item()
                            self.Log(f"Received an FTI move profit request {symbol} - ID: {self.ldf['TradeID'][0]} Pips: {self.symbolInfo[symbol].ftichangepips}")
                            return
                        elif self.ldf['Direction'][0] == FTIActions.ApproveTrade.value:
                            # we are approving a Trade to be released in a given currency
                            self.Log(f"Received an FTI trade approval - currently an unused state {symbol} - ID: {self.ldf['TradeID'][0]}")
                            return
                        elif self.ldf['Direction'][0] == FTIActions.SplitPot.value: 
                            # we are taking X% of the current value off the table
                            self.symbolInfo[symbol].ftisplitpot = True
                            self.Log(f"Received an FTI split pot request {symbol} - ID: {self.ldf['TradeID'][0]}")
                            return                            
                        elif self.ldf['Direction'][0] == FTIActions.ReadSettings.value:
                            self.Log(f"Received a ReadSettings FTI instruction - currently an unused state {symbol} - ID: {self.ldf['TradeID'][0]}")
                            return
                        elif self.ldf['Direction'][0] == FTIActions.ReadPreApproved.value:
                            self.Log(f"Received a ReadPreApproved FTI instruction - currently an unused state {symbol} - ID: {self.ldf['TradeID'][0]}")
                            return
                        elif self.ldf['Direction'][0] == FTIActions.ResetTrading.value:
                            self.Log(f"Received a ResetTrading FTI instruction - currently an unused state {symbol} - ID: {self.ldf['TradeID'][0]}")
                            return
                        
                        # only do this bit if we've got a Long or Short trade to do.
                        if self.ldf['Direction'][0] == FTIActions.ShortTrade.value or self.ldf['Direction'][0] == FTIActions.LongTrade.value:
                            if not self.symbolInfo[symbol].manualTradeOn:
                                # if we already are in a trade in this currency, so we have to ignore the FTI manual trade instruction - see the else clause
                                self.symbolInfo[symbol].manual_fti_sign = True
                                self.symbolInfo[symbol].manualTradeFound = True
                                self.symbolInfo[symbol].manualTradeConditional = self.ldf['Conditional'][0]
                                if self.ldf['Conditional'][0]:
                                    # need to make sure Conditional trades go WITH direction of price
                                    self.symbolInfo[symbol].manualBounceTrade = True
                                self.symbolInfo[symbol].manualLotSize = self.ldf['LotSize'][0]
                                self.symbolInfo[symbol].manualTradeDate = mytime
                                self.symbolInfo[symbol].manualTradeHour = mhr
                                self.symbolInfo[symbol].manualTradeMinute = mmin
                                self.symbolInfo[symbol].manualExpectedEntry = self.ldf['ExpectedEntry'][0]
                                self.symbolInfo[symbol].manualCheckMinutes = self.ldf['CheckMinutes'][0].item()
                                if mhr == self.symbolInfo[symbol].manualTradeHour and (mmin == (self.symbolInfo[symbol].manualTradeMinute + 1) or mmin == (self.symbolInfo[symbol].manualTradeMinute + 2)):
                                    self.symbolInfo[symbol].manualTradeMinute += 2    
                                    self.Log(f"Adjusting manual trade time (just missed slot) - ID: {self.ldf['TradeID'][0]}")
                            else:
                                self.LogExtra(f"Received manual trade from FTI in {symbol} but already in a trade", "FTI Manual Trade - already in a trade - ignoring")
                    else:
                        self.Log(f"Found old trade on startup - ID: {self.ldf['TradeID'][0]}")
                        self.symbolInfo[symbol].manualTradeConditional = False          # try to stop initial weird Narnia happening
        except:
            self.Log("Random error fetching manual FTI file occured - would have crashed")


    # Backtesting mode, used to force Fusion to try entering trades at interesting points we've found - will allow testing trade mgt independently            
    def CheckHistoryTrades(self):
        if self.IsWarmingUp:
            return
                      
        times_dict = fusion_utils.get_times(self.Time, 'us')   #new function to get times     
        # check current algorithm time, and search in the testing dictionary for manual trades to pump through          

        search_time = times_dict[self.manual_trades_tz]
        
        search_key = "{:04d}".format(search_time.year) + "-" + "{:02d}".format(search_time.month) + "-" + "{:02d}".format(search_time.day) + " " + "{:02d}".format(search_time.hour) + ":" + "{:02d}".format(search_time.minute)
        found_in_test_set = False
        
        if search_key in self.manual_trades_dict:
            found_in_test_set = True
            if found_in_test_set:
                values = self.manual_trades_dict.get(search_key)
                symbol = values[0]
                if symbol in self.ForexSymbols:
                    #set the manual trade dates to algo time - the search_time is just to match the data provided
                    self.symbolInfo[symbol].manualTradeDate = self.Time
                    self.symbolInfo[symbol].manualTradeHour = self.Time.hour
                    self.symbolInfo[symbol].manualTradeMinute = self.Time.minute

                    if values[4] > 0.0:
                        # this allows us to set a specific take profit if we want in the test set, use 0.0 otherwise
                        self.symbolInfo[symbol].profit_dist = values[4]
                    else:
                        self.symbolInfo[symbol].profit_dist = self.symbolInfo[symbol].sl_profit_manual

                    if values[2] == True:
                        # this mode means we will use trailling stops at this number of pips defined in column index 3
                        # TODO: think about making trailling stops and stop management per level?
                        self.symbolInfo[symbol].trailling_stop = True
                        self.symbolInfo[symbol].trailling_pips = values[3]

                        if values[5] == True:
                            # if we have defined that a move to 'breakeven' level is set - then wire it up to activate
                            self.symbolInfo[symbol].trading_move_to_be_flag = True
                            if values[7] < values[6]:
                                # Need to make sure we don't accidentally put stop above the current level or we don't have protection
                                self.symbolInfo[symbol].trading_move_to_be_profit_pips = values[6]
                                self.symbolInfo[symbol].trading_move_to_be_new_stop_pips = values[7]
                            else:
                                self.symbolInfo[symbol].trading_move_to_be_flag = False
                        else:
                            self.symbolInfo[symbol].trading_move_to_be_flag = False
                    else:
                        # this will use the default stepped breakout stop approach
                        self.symbolInfo[symbol].trailling_stop = False
                        self.symbolInfo[symbol].breakout_pnl = self.symbolInfo[symbol].sl_pnl_manual
                        self.symbolInfo[symbol].breakout_trail = self.symbolInfo[symbol].sl_trail_manual
                        self.symbolInfo[symbol].profit_dist = self.symbolInfo[symbol].sl_profit_manual
                    if values[1] == StratDirection.Long:
                        self.symbolInfo[symbol].manualDirection = True               # long trade
                    else:
                        self.symbolInfo[symbol].manualDirection = False               # short trade
                    # default values that FTI might set specifically - or just to make sure the trade gets found in OnData
                    self.symbolInfo[symbol].manual_fti_sign = True
                    self.symbolInfo[symbol].manualTradeFound = True
                    self.symbolInfo[symbol].manualTradeConditional = False
                    self.symbolInfo[symbol].manualBounceTrade = False
                    self.symbolInfo[symbol].manualTradeID = -99
                    self.symbolInfo[symbol].manualLotSize = 1
                    self.symbolInfo[symbol].manualCheckMinutes = 120
                    self.symbolInfo[symbol].manualExpectedEntry = 0.0
  
                else:
                    self.Log(f"ERROR: Manual trade injection in backtest failed on symbol: {symbol}")
                  
      
    '''
    Need to work out whether we've heard from FTI that this particular currency, for a given direction, is pre-approved within a time window that the time_now falls within
    Remember need to deal with UTC timings here
    '''
    def Check_Trade_Pre_Approval(self, sd, time_now, go_short):
        if self.auto_approve_narnias:
            # this allows us to fully automate Narnias and not have them require FTI pre-release
            return True
        if not sd.pre_approved_to_trade:
            # if there are no pre-approvals on this currency, then don't bother to check the times
            return False
        if sd.pre_approved_starttime is None:
            self.Log(f"Tried to check pre-approval for {sd.Symbol} - but start time is None")
            return False
        if not (sd.pre_approved_minutes > 0 and sd.pre_approved_minutes < 14400):
            self.Log(f"Tried to check pre-approval for {sd.Symbol} - but minutes for approval not between 0 and 14400")
            return False
        startlook = sd.pre_approved_starttime
        endlook = startlook + timedelta(minutes=sd.pre_approved_minutes)
        if time_now >= startlook and time_now <= endlook:
            # we are approved and the time is within our range - now check direction
            if sd.pre_approved_goShort and go_short:
                return True
            if not sd.pre_approved_goShort and not go_short:
                return True
        return False