#old orders code cut from main py
            
'''if sd.activeStrat == Strats.Nothing and sd.activeDirection == StratDirection.Nothing and (longsign or shortsign) and (perfect1sign or lungesign or channelsign):
# we have found one of the trade indicators on the 1Hr or a price point has been hit on Channel trades firing
sd.manualTradeFound = True
sd.manualTradeConditional = False
sd.manualBounceTrade = False
sd.manualTradeID = -99
# set this firmer if we have a strong floor or ceiling
sd.manualLotSize = 1
sd.manualTradeDate = self.Time
# this might need to be set to a different time
sd.manualCheckMinutes = 120
sd.manualTradeHour = self.Time.hour
sd.manualTradeMinute = self.Time.minute
if lungesign or channelsign or perfect1sign:
sd.breakout_pnl = sd.sl_pnl_manual
sd.breakout_trail = sd.sl_trail_manual
sd.profit_dist = sd.sl_profit_manual
self.Debug("manual - breakout pnl:" + str(sd.breakout_pnl) + " breakout_trail:" + str(sd.breakout_trail) + " profit_dist:" + str(sd.profit_dist))
if longsign:
sd.manualDirection = True
sd.manualExpectedEntry = 0.0
self.Log(f"{symbol}, EST {self.Time}, found Long trade - adding order - Ask Price Now: {self.Securities[symbol].AskPrice}")
if shortsign:
sd.manualDirection = False
sd.manualExpectedEntry = 0.0
self.Log(f"{symbol},EST {self.Time}, found Short trade - adding order - Bid Price Now: {self.Securities[symbol].BidPrice}")
'''

'''if (sd.CurrentRes == ChartRes.res15M or sd.manualTradeOn or sd.manualTradeFound) and not self.JustLoggingMode:

# Setup simple names for all the condition checks
sd.getCandleValues15M()

#use BID PRICE for Selling - SHORT
#use ASK PRICE for buying - LONG

askpricenow = self.Securities[symbol].AskPrice  
bidpricenow = self.Securities[symbol].BidPrice
pricetarget = sd.profit_dist * sd.minPriceVariation * 10                


'''

'''    goShort = not sd.manualDirection
betmultiple = sd.manualLotSize
tradeID = sd.manualTradeID
expectedentry = sd.manualExpectedEntry
if sd.narniasign:
    sd.manualExpectedEntry = sd.narniaentry
okToPlace = False
th = sd.manualTradeHour
tm = sd.manualTradeMinute
checkmin = sd.manualCheckMinutes

# first look for trade time and date if we are not conditionally entering
if sd.manualTradeDate.date() == self.Time.date() and not sd.manualTradeConditional:
    
    if th == timenow.hour and (tm == timenow.minute or tm == (timenow.minute-1) or tm == (timenow.minute-2)):
        # we have picked up we need to do a trade in this currency manually (now) and we don't already have it running
        sd.manualTradeOn = True
        sd.manualTradeFound = False
        sd.tradedToday += 1           # do this to avoid trading more than 3 time in a day - as a safety for now
        if sd.manual_fti_sign:
            sd.activeStrat = Strats.ManualTrigger
            sd.breakout_pnl = sd.sl_pnl_manual
            sd.breakout_trail = sd.sl_trail_manual
            sd.profit_dist = sd.sl_profit_manual
            pricetarget = sd.profit_dist * sd.minPriceVariation * 10        #override - make sure we take again
            self.Log(f"Matched manual - setting breakout strategy for {symbol} \nStop Loss Levels {sd.breakout_trail} and \nProfit Levels {sd.breakout_pnl}")
        elif perfect1sign:
            sd.activeStrat = Strats.Perfect1
        elif lungesign:
            sd.activeStrat = Strats.Lunge
        elif channelsign:
            sd.activeStrat = Strats.Channel
        self.Log(f"Matched manual - now trade {symbol} Short: {goShort} Multiplier {betmultiple} TradeID {tradeID}")
        okToPlace = True
# now this is the conditional entry
elif sd.manualTradeConditional and not sd.manualTradeOn:
    startlook = sd.manualTradeDate
    startlook = startlook.replace(hour = sd.manualTradeHour)
    startlook = startlook.replace(minute = sd.manualTradeMinute)
    endlook = startlook + timedelta(minutes=checkmin)
    if timenow >= startlook and timenow <= endlook:
        # we are conditional and the time is within our range - now check price
        # self.Log(f"Checking Conditional {symbol} Short: {goShort} Multiplier {betmultiple} TradeID {tradeID} Price Target {expectedentry}")
        if (goShort and bid_price_high >= expectedentry and not sd.manualBounceTrade) or (not goShort and bid_price_low <= expectedentry and not sd.manualBounceTrade) or (goShort and bid_price_low <= expectedentry and sd.manualBounceTrade) or (not goShort and bid_price_high >= expectedentry and sd.manualBounceTrade):
            if sd.narniasign and not sd.narniatriggered:
                if goShort:
                    self.LogExtra(f"Narnia Triggered :{symbol} SHORT - Entry Trigger Met: {expectedentry} - Release from FTI if allowed", f"Narnia Triggered :{symbol} SHORT - Can Fusion Trade?")
                else:
                    self.LogExtra(f"Narnia Triggered :{symbol} LONG - Entry Trigger Met: {expectedentry} - Release from FTI if allowed", f"Narnia Triggered :{symbol} LONG - Can Fusion Trade?")
                sd.narniatriggered = True
                sd.narniareleased = False            # only done here for testing!  Move to False for real
                trade_is_preapproved = self.Check_Trade_Pre_Approval(sd, timenow, goShort)
                if trade_is_preapproved:
                    sd.narniareleased = True
                    self.Log(f"Narnia was Pre-Approved - immediate release {symbol}")
                # now if we are logging correct direction calls - the check is here...just before we would say GO on a trade
                if self.check_direction_narnias and  self.get_trading_window(timenow, Strats.Narnia):
                    self.Log(f"{symbol} - checking direction call in 1Hr on Narnia")
                    if not goShort:
                        sd.direction_next_narnia = StratDirection.Long
                    else:
                        sd.direction_next_narnia = StratDirection.Short
                    sd.direction_next_candle = StratResolution.res1H
            elif sd.manual_fti_sign:
                sd.manualTradeOn = True
                sd.manualTradeFound = False
                sd.tradedToday += 1           # do this to avoid trading more than 3 time in a day - as a safety for now
                sd.activeStrat = Strats.ManualTrigger
                sd.breakout_pnl = sd.sl_pnl_manual
                sd.breakout_trail = sd.sl_trail_manual
                sd.profit_dist = sd.sl_profit_manual
                pricetarget = sd.profit_dist * sd.minPriceVariation * 10        #override - make sure we take again
                self.Log(f"Matched Conditional - now trade {symbol} Short: {goShort} Multiplier {betmultiple} TradeID {tradeID}")
                okToPlace = True
    if sd.narniasign and sd.narniatriggered and sd.narniareleased:
                sd.manualTradeOn = True
                sd.manualTradeFound = False
                sd.tradedToday += 1           # do this to avoid trading more than 3 time in a day - as a safety for now
                sd.activeStrat = Strats.Narnia
                roundloss = 20 #si temp
                sd.breakout_trail = [-20,  0, 15, 30, 50, 65, 80, 105, 125, 145, 165]
                sd.breakout_pnl =     [0, 15, 25, 40, 60, 80, 95, 120, 140, 165, 185]
                sd.profit_dist = 200   
                pricetarget = sd.profit_dist * sd.minPriceVariation * 10
                self.LogExtra(f"Narnia Released - now will trade {symbol} Short: {goShort} Multiplier {betmultiple} TradeID {tradeID}", f"Narnia Released - now will trade {symbol}")
                okToPlace = True
    if timenow > endlook:
        # we have passed the time to check for the conditional trade
        self.Log(f"Conditional Expired: {symbol}")
        sd.ClearTracking()
#okToPlace = False       # comment out to let trading happen - needs some other checks too around ClearTracking
'''

'''if goShort:
    numBelow = sd.NumbersBelow(bidpricenow)
    numAbove = sd.NumbersAbove(bidpricenow)
else:
    numBelow = sd.NumbersBelow(askpricenow)
    numAbove = sd.NumbersAbove(askpricenow)
'''
''' Change to right value for LIVE'''
'''if self.LiveMode:
    unitbuy = 25000
else:
    unitbuy = 600000     # set this from calculation of limits - bankroll
'''
'''Set the trading window times - also should add holiday calendar checking to this '''
'''tradingWindowOpen = False
tradingWindowOpen = self.get_trading_window(timenow, sd.activeStrat)

if self.JustWatching:
    self.Log(f"Found a new trade in {symbol} - but not trading anything")   #could add an email to this effect
    self.Debug(f"Found a new trade in {symbol} - but not trading anything")
    okToPlace = False
    sd.ClearTracking()

if okToPlace and tradingWindowOpen and self.LiveTradeCount == 2:
    self.Log(f"Found a new trade in {symbol} - but too many active trades; skipping")
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
    
    lon_tz = pytz.timezone('Europe/London')
    ny_tz = pytz.timezone('America/New_York')
    localtime = self.Time
    nytime = ny_tz.localize(localtime)
    londontime = nytime.astimezone(lon_tz)
    self.Log(f"Timezones: New York {nytime} and London: {londontime}")
    
    # do not enter trades with spread > 5.0 pips
    expected_size = 0.0
    if entry_pips <= 5.0:
        if goShort:
            self.open_position_short(symbol, sd, unitbuy, betmultiple, askpricenow, bidpricenow, entry_pips, trigger_level=1, logging=True)
            expected_size = -1.0 * unitbuy * betmultiple
        else:
            self.open_position_long(symbol, sd, unitbuy, betmultiple, askpricenow, bidpricenow, entry_pips, trigger_level=1, logging=True)
            expected_size = 1.0 * unitbuy * betmultiple
    else:
        self.Log(f"Spread too wide to enter trade at {entry_pips} pips - Clear tracking {symbol} ")
        sd.ClearTracking()    
    actual_size = self.Get_Open_Order_Size(symbol, sd, trigger_level=1)
    self.Debug(f"{symbol}: trade entered, checked order sizes, expecting {expected_size} and received {actual_size}")

elif okToPlace and not tradingWindowOpen:
    self.Log(f"Trade found outside window - NO trade - Clear tracking {symbol} ")
    sd.ClearTracking()
'''
'''elif self.JustTestingTrading:    #Si 13.0 - this is where we will test the trading management stuff
#at the moment its just one direction 
betmultiple = 1
sd.activeStrat = Strats.ManualTrigger
unitbuy = 100000     # set this from calculation of limits - bankroll     
entry_pips = round((askpricenow - bidpricenow)/(sd.minPriceVariation * 10) ,6)           
goShort = True
trigger_level = 1   #numeric which level 
pipsize = sd.minPriceVariation * 10
if goShort:
sd.activeDirection = StratDirection.Short
self.Plot("Trade Plot", "Price", askpricenow)
if not self.Portfolio[symbol].IsShort and self.JustTestingCounter < 1:  #no position in this currency pair
    self.open_position_short(symbol, sd, unitbuy, betmultiple, askpricenow, bidpricenow, entry_pips, trigger_level, logging=True)
    self.Debug(f" entered trade: {symbol}- {sd.entry_times[trigger_level-1]} stop: {str(sd.tickets_stops[trigger_level-1])}")   
    self.JustTestingCounter += 1
    sd.split_live_levels[0] = False #Si will be reset here for the moment
else:
    if sd.tickets_live_levels[trigger_level-1]: #only do this when level has an active trade
        PnlPips = round((sd.entry_prices[trigger_level-1]-askpricenow)/(sd.minPriceVariation * 10) ,2)                                 
        #https://www.quantconnect.com/docs/v2/writing-algorithms/trading-and-orders/order-management/order-tickets# SI
                            
        (trade_qty, stop_loss_qty, take_profit_qty) = self.Get_Open_Order_Size(symbol, sd, trigger_level, logging=False) #get a position size (across all the levels)
        
        if not sd.split_live_levels[0]: #this level has not been used
            if PnlPips > 3:
                sd.split_live_levels[0] = True  #so only split the once
                reduction_percent = 0.3
                trade_reduction_qty = - (reduction_percent * trade_qty)
                new_protection_qty = (1 - reduction_percent) * stop_loss_qty
                self.ReduceTradePosition(symbol, sd, trade_reduction_qty, new_protection_qty, trigger_level,logging=False)


        sl_price = round(sd.tickets_stops[trigger_level-1].Get(OrderField.StopPrice),6)    
        entry_price = sd.entry_prices[trigger_level-1]                        

        self.Debug(f" {str(self.Time)} - #{str(sd.tickets_ids[trigger_level-1])}/{str(sd.tickets_entry_no[trigger_level-1])}, Entry:{str(entry_price)}, PnlPips: {str(PnlPips)}, SL_Position:{str(sd.sl_positions[trigger_level-1])}, \
            SL_Qty: {str(stop_loss_qty)}, SL_price: {str(sl_price)}, Ask: {str(askpricenow)}, Trade_Qty:{str(trade_qty)}, TP_Qty:{str(take_profit_qty)} --> {str(sd.tickets_live_levels[trigger_level-1])}") 
        
    # for the moment we are just going to split a one level pot
    # check the pnl pips (start with simple logic)
    # check if we have split before and track each split: level(just 1for moment): qty adj: qty left: price exit
    # check the current position
    # make buy / sell 
    # update the stop / limits (level 1 only for the moment)

#if self.Portfolio[symbol].IsShort:  #so, we know we have a position in this currency pair'''
'''for index in range(0, len(sd.tickets_live_levels)):                         
    if not sd.tickets_live_levels[index]:   #then we know we don't have an entry in this position                                
        #next check to see whether the level price has been triggered
        if index == 0:                                
            self.open_position_short(symbol, sd, unitbuy, betmultiple, askpricenow, bidpricenow, entry_pips, index, logging=True)                                                                                
        else:
            price_difference = round((sd.entry_prices[index-1] - bidpricenow)/(sd.minPriceVariation * 10) ,2)
            if price_difference >= 10:  #for the moment just level up every 10 pips                                                     
                self.open_position_short(symbol, sd, unitbuy, betmultiple, askpricenow, bidpricenow, entry_pips, index, logging=True)'''
                
'''else:
sd.activeDirection = StratDirection.Long
self.Plot("Trade Plot", "Price", bidpricenow)
if not self.Portfolio[symbol].IsLong:  #no position in this currency pair
    self.open_position_long(symbol, sd, unitbuy, betmultiple, askpricenow, bidpricenow, entry_pips, trigger_level, logging=True)
    self.Debug(f" entered trade: {symbol}- {sd.entry_times[trigger_level-1]} stop: {str(sd.tickets_stops[trigger_level-1])}")   
    self.JustTestingCounter += 1
else:
    PnlPips = round((bidpricenow-sd.entry_prices[trigger_level-1])/(sd.minPriceVariation * 10) ,2)                                 
    #https://www.quantconnect.com/docs/v2/writing-algorithms/trading-and-orders/order-management/order-tickets# SI
    sl_qty = round(sd.tickets_stops[trigger_level-1].Quantity,0)
    sl_price = round(sd.tickets_stops[trigger_level-1].Get(OrderField.StopPrice),6)    
    entry_price = sd.entry_prices[trigger_level-1]                        

    self.Debug(f" {str(self.Time)} - id# {str(sd.tickets_ids[trigger_level-1])}, PnlPips: {str(PnlPips)}, SL_position:{str(sd.sl_positions[trigger_level-1])}, \
        SL_qty: {str(sl_qty)}, SL_price: {str(sl_price)}, BidNow: {str(bidpricenow)}, entry_price:{str(entry_price)} ") 
'''   