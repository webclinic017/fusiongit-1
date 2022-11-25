#region imports
from distutils.command.sdist import sdist
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
from consolidators import *
from QuantConnect import Market
from io import StringIO
import pandas as pd

'''Contains a bunch of helper functions for dealing with placing and managing orders - in an attempt to save space in the main file'''

class QCalgo_order_management(QCalgo_consolidators):

    # This is where we define the times to trade, based on certain strategies                
    def get_trading_window(self, currenttime, currentstrat):
        
        t_win = False
        whatday = currenttime.weekday()
        whathour = currenttime.hour
        if whatday == 6:
            # sunday
            if whathour >= 21:
            #if whathour >= 24:
                t_win = True
        elif whatday >= 0 and whatday <= 3:
            # mon, tue, wed, thu
            # -- swap if whathour <= 11 or whathour >= 21:
            if whathour <= 12 or whathour >= 20 or (whathour >= 16 and whathour <= 17):
            #if whathour <= 11 and whathour >= 2:
                t_win = True
        elif whatday == 4:
            # Friday
            # -- swap if whathour <= 11:
            if whathour <= 12:
            #if whathour <= 11 and whathour >= 2:
                t_win = True
        # override trading window IF this is a manually entered trade
        if currentstrat == Strats.ManualTrigger:
                t_win = True
        return t_win
    
    
    
    '''Place a short order and make sure to track it properly '''
    def open_position_short(self, symbol, sd :SymbolData, unit_buy, bet_multiple, ask_price_now, bid_price_now, entry_pips, trigger_level=1, logging=False):
        # this is the SHORT entry  -- use BID prices
        trigger_index = trigger_level - 1

        sd.activeDirection = StratDirection.Short
        sd.stratTracker[sd.activeStrat.name+sd.activeDirection.name]["Count"] += 1
        sd.tickets_entry_no[trigger_index] = 1  #count of entries, must start at 1
        
        # Calcuate our base SL level. This is used for the initial entry. 
        # We will also use it to compare to the previous trail level
        # use ASK prices for the longs which get us out of position

        if sd.set_specific_stop_loss:
            base_sl_level = sd.channel_stop_loss_price  #specific price
        else:
            if sd.trailling_stop:
                price_loss = sd.trailling_pips * -1.0 * sd.minPriceVariation * 10      #turn into pips from pipettes               
                base_sl_level = round(ask_price_now - price_loss, 5)
            else:
                price_loss = sd.breakout_trail[0] * sd.minPriceVariation * 10      #turn into pips from pipettes               
                base_sl_level = round(ask_price_now - price_loss, 5)
    
        #take profit expressed in pip form
        if sd.set_specific_take_profit:
            price_target = sd.channel_take_profit_pips * sd.minPriceVariation * 10
        else:
            price_target = sd.profit_dist * sd.minPriceVariation * 10                   
        profit_level  = round(ask_price_now - price_target, 5)

        sd.entry_times[trigger_index] = self.Time
        mt4_entry_time = fusion_utils.get_times(self.Time, 'us') ['mt4']


        if logging: 
            #TODO add these to the event log
            #self.LogExtra(f"Trade LEVEL ENTRY {str(trigger_index + 1)} | Trade Id#{str(self.master_trade_id)} | {symbol} | MT4: {mt4_entry_time} {sd.activeDirection}: entering @ BID : ASK price {str(bid_price_now)} : {str(ask_price_now)} and size {str(bet_multiple * unit_buy)} and stoploss(pip) {sd.breakout_trail[0]} - Take Profit: {profit_level}  Stop Loss: {base_sl_level} Spread: {entry_pips}", f"{symbol} SHORT Trade Entry")
            if self.log_EMAs: 
                #self.LogExtra(f"1M 9EMA: {round(sd.emaWindow1M[0].Value, 5)} | 1M 45EMA: {round(sd.emaWindow1M_45[0].Value, 5)} | 1M 135EMA: {round(sd.emaWindow1M_135[0].Value, 5)} | 1M 200EMA: {round(sd.emaWindow1M_200[0].Value, 5)}", f"{symbol} EMAs check")
                pass
        
        sd.entry_prices[trigger_index] = bid_price_now
        sd.last_trail_levels[trigger_index] = base_sl_level                        # Place a short order by negative quantity -- stop limit needs to be a slightly lower price

        position_size = -1 * bet_multiple * unit_buy
        sd.tickets_position_size[trigger_index] = position_size
        
        sd.tickets_trades[trigger_index] = self.MarketOrder(symbol, position_size, False, f'Short Entry:{str(trigger_index + 1)}:{str(self.master_trade_id)}:{str(sd.tickets_entry_no[trigger_index])}:')
        
        sd.spreads_paid[trigger_index] = round((sd.tickets_trades[trigger_index].AverageFillPrice - ask_price_now) / (sd.minPriceVariation * 10), 6)
        if logging: self.Debug(f"Market Order Actual Fill Price: {str(trigger_index + 1)} | {symbol}:{sd.tickets_trades[trigger_index].AverageFillPrice} \n{sd.spreads_paid[trigger_index]}")
        sd.entry_prices[trigger_index] = sd.tickets_trades[trigger_index].AverageFillPrice
        
        self.LiveTradeCount += 1
        sd.tickets_live_levels[trigger_index] = True

        
        sd.tickets_stops[trigger_index] = self.StopMarketOrder(symbol, 1 * bet_multiple * unit_buy, base_sl_level, f'Stop: {str(trigger_index +1)}: {str(self.master_trade_id)}:')
        sd.tickets_profits[trigger_index] = self.LimitOrder(symbol, 1 * bet_multiple * unit_buy, profit_level, f'Limit: {str(trigger_index +1)}: {str(self.master_trade_id)}:')
        sd.tickets_ids[trigger_index] = self.master_trade_id
        sd.tickets_low_asks[trigger_index] = ask_price_now
        sd.tickets_low_bids[trigger_index] = bid_price_now
        sd.tickets_last_stop_levels[trigger_index] = base_sl_level
        self.master_trade_id += 1
        
        
        
    '''Place a long order and make sure to track it properly '''
    def open_position_long(self, symbol, sd :SymbolData, unit_buy, bet_multiple, ask_price_now, bid_price_now, entry_pips, trigger_level=1, logging=False):
        # this is the LONG entry  -- use ASK prices
        trigger_index = trigger_level - 1

        sd.activeDirection = StratDirection.Long
        sd.stratTracker[sd.activeStrat.name+sd.activeDirection.name]["Count"] += 1
        sd.tickets_entry_no[trigger_index] = 1  #count of entries, must start at 1

        # Calcuate our base SL level. This is used for the initial entry. 
        # We will also use it to compare to the previous trail level.
        # use BID prices for the shorts which get us out of position

        if sd.set_specific_stop_loss:
            base_sl_level = sd.channel_stop_loss_price  #specific price
        else:
            if sd.trailling_stop:
                price_loss = sd.trailling_pips * -1.0 * sd.minPriceVariation * 10      #turn into pips from pipettes               
                base_sl_level = round(bid_price_now + price_loss, 5)
            else:
                price_loss = sd.breakout_trail[0] * sd.minPriceVariation * 10      #turn into pips from pipettes               
                base_sl_level = round(bid_price_now + price_loss, 5)

        #take profit expressed in pip form
        if sd.set_specific_take_profit:
            price_target = sd.channel_take_profit_pips * sd.minPriceVariation * 10
        else:
            price_target = sd.profit_dist * sd.minPriceVariation * 10                   
        profit_level  = round(bid_price_now + price_target, 5)
        
        sd.entry_times[trigger_index] = self.Time
        mt4_entry_time = fusion_utils.get_candle_open_time(fusion_utils.get_times(self.Time, 'us') ['mt4'], None)


        if logging: 
            #TODO add these to the event log
            #self.LogExtra(f"Trade LEVEL ENTRY {str(trigger_index + 1)} | Trade Id #{str(self.master_trade_id)} | {symbol} | MT4: {mt4_entry_time} {sd.activeDirection}: entering @ BID : ASK price {str(bid_price_now)} : {str(ask_price_now)} and size {str(bet_multiple * unit_buy)} and stoploss(pip) {sd.breakout_trail[0]} - Take Profit: {profit_level}  Stop Loss: {base_sl_level} Spread: {entry_pips}", f"{symbol} LONG Trade Entry")
            if self.log_EMAs: 
                #self.LogExtra(f"1M 9EMA: {round(sd.emaWindow1M[0].Value, 5)} | 1M 45EMA: {round(sd.emaWindow1M_45[0].Value, 5)} | 1M 135EMA: {round(sd.emaWindow1M_135[0].Value, 5)} | 1M 200EMA: {round(sd.emaWindow1M_200[0].Value, 5)}", f"{symbol} EMAs check")
                pass
                           
        
        sd.entry_prices[trigger_index] = ask_price_now
        sd.last_trail_levels[trigger_index] = base_sl_level                        # Place a short order by negative quantity -- stop limit needs to be a slightly lower price

        position_size = 1 * bet_multiple * unit_buy
        sd.tickets_position_size[trigger_index] = position_size
        
        sd.tickets_trades[trigger_index] = self.MarketOrder(symbol, position_size, False, f'Long Entry:{str(trigger_level)}:{str(self.master_trade_id)}:{str(sd.tickets_entry_no[trigger_index])}')
        
        sd.spreads_paid[trigger_index] = round((bid_price_now - sd.tickets_trades[trigger_index].AverageFillPrice) / (sd.minPriceVariation * 10), 6)
        if logging: self.Debug(f"Market Order Fill Price: {symbol}:{sd.tickets_trades[trigger_index].AverageFillPrice} \n {sd.spreads_paid[trigger_index]}:")
        sd.entry_prices[trigger_index] = sd.tickets_trades[trigger_index].AverageFillPrice
        
        self.LiveTradeCount += 1
        sd.tickets_live_levels[trigger_index] = True
        
        sd.tickets_stops[trigger_index] = self.StopMarketOrder(symbol, -1 * bet_multiple * unit_buy, base_sl_level, f'Stop:{str(trigger_level)}:{str(self.master_trade_id)}:')
        sd.tickets_profits[trigger_index] = self.LimitOrder(symbol, -1 * bet_multiple * unit_buy, profit_level, f'Limit:{str(trigger_level)}:{str(self.master_trade_id)}:')
        sd.tickets_ids[trigger_index] = self.master_trade_id
        sd.tickets_high_asks[trigger_index] = ask_price_now
        sd.tickets_high_bids[trigger_index] = bid_price_now
        sd.tickets_last_stop_levels[trigger_index] = base_sl_level

        self.master_trade_id += 1
    


    def update_position(self, sd, pnlpips, symbol, level=1):        
        #Si --> this is hard coded entry for the moment, split pot by 50% when pnl hits 10
        # 22.03 - removing auto split for the moment and having FTI control
        #if pnlpips == 10.0:
        if sd.ftisplitpot:
            #current_open_order_size = self.get_open_order_size(symbol,sd,1,False)       
            #open_quantity = sum([x.Quantity for x in self.Transactions.GetOpenOrders(Symbol)])
            #we need a way to get the current open quantity
            #self.Log("open_quantity=" + str(open_quantity))     
            #revised_order_size = current_open_order_size * 0.5
            #self.update_reduce_open_order_size(symbol,sd,current_open_order_size,revised_order_size,1,False)
            #check the new open order sizes are expected
            pass
        return False

    def get_open_order_size(self, symbol, sd, trigger_level=1, logging=False):
        #currently this will just get one level 
        trigger_index = trigger_level - 1
        
        if trigger_level > len(sd.tickets_live_levels):
            self.Log(f"{symbol}: Error! open_order_size sent trigger_level beyond number of ticket slots")
            return (0.0, 0.0, 0.0)
  
        trade_qty = sd.tickets_position_size[trigger_index]
        if trade_qty == 0:
            self.Debug(f"{symbol}: Error! trade_qty is {str(trade_qty)}, level status: {str(sd.tickets_live_levels[trigger_index])}")
            return (0.0, 0.0, 0.0)

        stop_loss_qty = sd.tickets_stops[trigger_index].Quantity
        take_profit_qty = sd.tickets_profits[trigger_index].Quantity

        if sd.activeStrat != Strats.Nothing and sd.activeDirection == StratDirection.Long:
            #self.Debug(f"long trade_qty check: {trade_qty} | stop_loss_qty: {stop_loss_qty} | take_profit_qty: {trade_qty}" )            
            if trade_qty > 0.0 and trade_qty == -1.0 * stop_loss_qty and trade_qty == -1.0 * take_profit_qty:
                # all is good with the Long position and protective orders
                return (trade_qty, stop_loss_qty, take_profit_qty)
            else:
                #self.Log(f"{symbol}: get_open_order_size: mismatch on Long order --> trade_qty: {trade_qty} | stop_loss_qty: {stop_loss_qty} | take_profit_qty: {take_profit_qty}" )
                return (0.0, 0.0, 0.0)
        elif sd.activeStrat != Strats.Nothing and sd.activeDirection == StratDirection.Short:
            #self.Debug(f"short trade_qty check: {trade_qty} | stop_loss_qty: {stop_loss_qty} | take_profit_qty: {take_profit_qty}" )
            if trade_qty < 0.0 and trade_qty == -1.0 * stop_loss_qty and trade_qty == -1.0 * take_profit_qty:
                # all is good with the Short position and protective orders
                return (trade_qty, stop_loss_qty, take_profit_qty)
            else:
                self.Debug(f"{symbol}: mismatch on Short order --> trade_qty: {trade_qty} | stop_loss_qty: {stop_loss_qty} | take_profit_qty: {take_profit_qty}" )
                return (0.0, 0.0, 0.0)
        else:         
            return (0.0, 0.0, 0.0)

    
    def ReduceTradePosition(self, symbol, sd :SymbolData, trade_reduction_qty, new_protection_qty, trigger_level=1, logging=False):       
        trigger_index = trigger_level - 1

        if trigger_level > len(sd.tickets_live_levels):
            self.Log(f"{symbol}: Error Re: sent trigger_level beyond number of ticket slots")
            return False

        sd.tickets_entry_no[trigger_index] += 1 #increase entry counter

        #now we dont need to "think" in this function, because it has already been correctly done in the call
        # short has -ve trade_qty, so to reduce the position will mean that the reduction_Qty is +ve i.e. buy
        # long has +ve trade_qty, so to reduce the position will mean that the reduction_Qty is -ve i.e. sell
        
        direction_text = "Long Reduce" 
        if trade_reduction_qty > 0:
            direction_text = "Short Reduce" 
        
        sd.tickets_position_size[trigger_index] += trade_reduction_qty #keep track of running position size per level

        sd.tickets_trades[trigger_index] = self.MarketOrder(symbol, trade_reduction_qty, False, f'{direction_text}:{str(trigger_index)}:{str(self.master_trade_id)}:{str(sd.tickets_entry_no[trigger_index])}') 
        
        #now handle the stop loss / take profit orders        
        update_order_fields = UpdateOrderFields()
        update_order_fields.Quantity = new_protection_qty   #this reverses sign of whatever is passed into the function for the trade_Qty reduction
        
        response = sd.tickets_stops[trigger_index].Update(update_order_fields)        
        if response.IsSuccess:
            self.Log(f"\n Update stop_loss_qty {symbol} - new_protection_qty: {new_protection_qty} | success:{response.IsSuccess}")   
        else:
            return False       
        
        response = sd.tickets_profits[trigger_index].Update(update_order_fields)
        if response.IsSuccess:
            self.Log(f"\n Update take_profit_qty {symbol} - new_protection_qty: {new_protection_qty} | success:{response.IsSuccess}")                                  
        else:
            return False    

        return True

    
    '''Event when the order is filled. Debug log the order fill. :OrderEvent:'''
    def OnOrderEvent(self, OrderEvent):
        #self.TotalValue = 100000.0 + self.Portfolio.TotalUnrealizedProfit + self.Portfolio.TotalProfit - self.Portfolio.TotalFees
        #bankrollratio = self.TotalValue / 100000.0
        #unitbuy = math.ceil((900000 * bankrollratio) / 10000.0) * 10000.0
        
        # If we didn't actually get a fill, then skip for now
        if OrderEvent.FillQuantity == 0:    
            NonFilledOrder = self.Transactions.GetOrderById(OrderEvent.OrderId)            
            return NonFilledOrder

        # Get the filled order
        Order = self.Transactions.GetOrderById(OrderEvent.OrderId)
               
        # Log the filled order details
        self.Log("ORDERFILL >> {} >> Status: {} Symbol: {}. Quantity: "
                    "{}. Direction: {}. Fill Price {}".format(str(Order.Tag),
                                                   str(OrderEvent.Status),
                                                   str(OrderEvent.Symbol),
                                                   str(OrderEvent.FillQuantity),
                                                   str(OrderEvent.Direction),
                                                   str(OrderEvent.FillPrice)))
                                                   
        if OrderEvent.Status == OrderStatus.Filled:
            # IF we hit a Stop or a Limit order then clear other open orders and clear tracking content
            # TODO: need to make this generic per strategy
            sd = self.symbolInfo[str(OrderEvent.Symbol)]
            symbol = str(OrderEvent.Symbol)
            
            #Handle order events for any Stop or Limit order fill event

            if str(Order.Tag).startswith('Stop:') or str(Order.Tag).startswith('Limit:'):
                # find which order this is
                #self.Debug(f"catch error: {symbol} | orderTag: {str(Order.Tag)}")                
                order_tag = str(Order.Tag)
                tag_parts = order_tag.split(':')
                order_level = int(tag_parts[1])
                order_id = int(tag_parts[2])
                if str(Order.Tag).startswith('Stop:'):
                    hit_stop = True
                    hit_profit = False
                    self.Debug(f"symbol: {symbol} STOP HIT - Trade Closed")
                else:
                    hit_stop = False
                    hit_profit = True
                    self.Debug(f"symbol: {symbol} TAKE PROFIT HIT - Trade Closed")

                if order_level not in {0, 1, 2}:
                    self.Debug(f"symbol: {symbol} STOP or TAKE PROFIT HIT - invalid trigger level in order tag")
                    self.Transactions.CancelOpenOrders(symbol)
                    self.Liquidate(symbol)
                    self.symbolInfo[symbol].ClearTracking()
                    self.LiveTradeCount -= 1
                    if self.LiveTradeCount < 0:
                        self.LiveTradeCount = 0
                else:
                    self.close_position_and_clear_open_orders_cleanly(symbol, order_level, OrderEvent.FillPrice, order_tag, logging = self.log_position_closures)    

        # Look for manual cancellations        
        elif OrderEvent.Status == OrderStatus.Canceled:
            symbol = str(OrderEvent.Symbol)
            #Need to watch for cancelling of the Limit order or Stop order
            self.LogExtra(f"STOP or LIMIT cancelled - tag is {Order.Tag}", " Stop or Limit cancelled")
            if str(Order.Tag).startswith('Stop:') or str(Order.Tag).startswith('Limit:'):
                self.Transactions.CancelOpenOrders(symbol)
                self.Liquidate(symbol)
                self.symbolInfo[symbol].ClearTracking()
                self.LiveTradeCount -= 1
                if self.LiveTradeCount < 0:
                    self.LiveTradeCount = 0
                self.LogExtra(f"STOP or LIMIT cancelled - closing position in {symbol}", " Stop or Limit cancelled")
        else:
            self.Log(f"Got order event: {OrderEvent} - {OrderEvent.Status}")
            

    def close_position_and_clear_open_orders_cleanly(self, symbol, order_level, fill_price, msg_tag, logging = False):
        if logging: self.Log(f"symbol: {symbol} trade closure requested - closing position and cancelling protective orders")

        force_closed = False

        sd = self.symbolInfo[symbol]

        if sd.is_in_a_trade(self):
            # this means we are in a trade and need to close it, to get a fill price etc.  In this case we haven't hit the Stop or Limit and we are manually closing
            # TODO: deal with order levels - or decide to scrap them
            position_size = -1.0 * self.Portfolio[symbol].Quantity
            trade_ticket = self.MarketOrder(symbol, position_size, False, f'Force close position: {symbol}')
            # now check we are actually cleared out of the position
            still_in_trade = sd.is_in_a_trade(self)
            force_fill_price = trade_ticket.AverageFillPrice
            if logging: self.Debug(f"Force Close Position: {symbol}: size: {position_size} @ {force_fill_price} - success: {not still_in_trade}")
            # TODO: Crash the algo run if we cannot successfully close the position
            force_closed = True

        order_index = order_level - 1
        if force_closed:
            # we have a fill price from the force close
            sd.exit_prices[order_index] = force_fill_price
        else:
            #otherwise it was passed through from the stop/loss or take profit being hit
            sd.exit_prices[order_index] = fill_price
        
        pipsize = sd.minPriceVariation * 10
        stratnow = sd.activeStrat.name
        stratdir = sd.activeDirection.name
        entry_time = sd.entry_times[order_index]
        entry_price = sd.entry_prices[order_index]
        spread = sd.spreads_paid[order_index]
        max_pip_profit = round(sd.max_pips_profits[order_index], 2)
        max_pip_loss = round(sd.max_pips_losses[order_index], 2)
        exit_price = sd.exit_prices[order_index]
        exit_time = self.Time
        
        if sd.activeDirection == StratDirection.Long :
            pnlpips = round((sd.exit_prices[order_index] - sd.entry_prices[order_index] ) / pipsize, 1)
        else:
            pnlpips = round((sd.entry_prices[order_index] - sd.exit_prices[order_index] ) / pipsize, 1)
        self.LogExtra("STRAT CLEAR - cancel open orders >> {} - {} pnlpips: {}".format(str(symbol), str(msg_tag), str(pnlpips)), " Open order hit stop or limit")
        sd.stratTracker[sd.activeStrat.name+sd.activeDirection.name]["Stopped"] += 1
        sd.stratTracker[sd.activeStrat.name+sd.activeDirection.name]["PnlPips"] += pnlpips
        sd.total_algo_pips += pnlpips

        mt4_entry_time = fusion_utils.get_times(entry_time, 'us') ['mt4']
        mt4_exit_time = fusion_utils.get_times(exit_time, 'us') ['mt4']

        # find the record in sd.perfect_library if this is a BradPerfect
        if sd.activeStrat == Strats.BradPerfect:
            # TODO: make this not just be based on 5M Brad spots, if we move to other resolutions too
            (message_detail, logdate) = sd.tbu_perfect_tracker[ChartRes.res5M].find_and_update_label(self, sd.trade_label_current, pnlpips, max_pip_profit)
            logsub = f"Breakout Details: {symbol} {sd.activeDirection.name} @ {logdate}"
            self.LogExtra(message_detail, logsub)

            sd.tbu_perfect_tracker[ChartRes.res5M].add_to_event_log(mt4_exit_time, "Trade - CLOSED", f"Result: {pnlpips} | Spread: {spread} | MaxProfit: {max_pip_profit} | MaxLoss: {max_pip_loss} pips", exit_price, "tick")          
            sd.tbu_perfect_tracker[ChartRes.res5M].clear_down_perfect_and_write_log(self, exit_time)   

        

        self.tradesEntered.append(f" ** TRADE **,{stratnow}, {symbol}, {stratdir}, Entry MT4: {mt4_entry_time},PnlPips: {pnlpips}, entry price: {entry_price}, EntrySpread: {spread}, MaxPipsP: {max_pip_profit}, MaxPipsL: {max_pip_loss}")
        '''Cannot just cancel all open orders - will have to cancel the specific matching ticket, depending on whether hit profit or stop
        '''
        #write trade results and event log
        breakout_time = fusion_utils.format_datetime_using_string(sd.tbu_perfect_tracker[ChartRes.res5M].BO_pos4_time)
        sd.tbu_perfect_manager[ChartRes.res5M].clear_manage_perfect(self, symbol, self.Time, logging=True)

        self.write_trade_results(symbol, stratdir, pnlpips, 0, 0, entry_time, entry_price, exit_time, exit_price, max_pip_profit, max_pip_loss, "TBC", spread, msg_tag, sd.trade_label_current)

        # not needed for now - need to find a way to activate event log during trade management
        #self.write_breakout_log(sd.tbu_perfect_tracker[ChartRes.res5M].event_log, symbol, breakout_time, stratdir)

        self.Transactions.CancelOpenOrders(symbol)
        self.Liquidate(symbol)
        self.LiveTradeCount -= 1
        if self.LiveTradeCount < 0:
            self.LiveTradeCount = 0    
        '''this will be too extreme for now - need to modify to have something that can clear one level only...not all of them...if we want to leave other orders in play in the same currency at the same time
        maybe store which level got hit/cleared
        '''
        self.symbolInfo[symbol].ClearTracking()

    def get_current_pnlpips(self, sd :SymbolData, bidpricenow, askpricenow):
        order_level = 1 #TODO: make this loop when we have multiple index levels
        order_index = order_level - 1
        pipsize = sd.minPriceVariation * 10
        if sd.activeDirection == StratDirection.Long :
            pnlpips = round((bidpricenow - sd.entry_prices[order_index]), 6) / pipsize
        else:
            pnlpips = round((sd.entry_prices[order_index] - askpricenow), 6) / pipsize
        return pnlpips


    def manage_breakout_stops(self, sd :SymbolData, askpricenow, bidpricenow, pipsize):
        # used to manage all the stop loss orders
        ''' Need to add in the ability to have different Stop Loss and Take Profit setups on each live ticket.
        '''
        symbol = sd.Symbol
        
        if  sd.activeDirection == StratDirection.Short:
            # Already in a Short - need to manage trailling stop and take profit, at multiple levels
            # Short entry used BID prices - getting out uses ASK
            for index in range(0, len(sd.tickets_live_levels)):
                if sd.tickets_live_levels[index]:


                    # only manage stops if we have a live order at this level - usually only will be the first one
                    pnlpips = round((sd.entry_prices[index] - askpricenow), 6) / pipsize
                    if pnlpips > sd.max_pips_profits[index]:
                        sd.max_pips_profits[index] = pnlpips
                    if pnlpips < sd.max_pips_losses[index]:
                        sd.max_pips_losses[index] = pnlpips * -1.0

                    #sd.ftisplitpot = True   #force for testing
                    if sd.activeStrat != Strats.Nothing and sd.ftisplitpot:                        
                        self.Log(f"Split pot {symbol} on {sd.activeStrat}:{sd.activeDirection} by 50% (hard coded for moment)")                        
                        self.update_position(sd, pnlpips, -1, symbol)
                        sd.ftisplitpot = False
                        sd.fti_in_control = True

                    if sd.activeStrat != Strats.Nothing and sd.ftichangestop:
                        sd.ftichangestop = False
                        newpriceloss = sd.ftichangepips * sd.minPriceVariation * 10    #turn into pips from pipettes
                        new_sl_level = round(sd.entry_prices[index] - newpriceloss, 6)                       
                        self.Debug(f"Update stop loss {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpipsnow: {round(pnlpips, 6)} SL: {round(new_sl_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.StopPrice = new_sl_level
                        sd.tickets_stops[index].Update(update_order_fields)
                        sd.ftichangepips = 0.0
                        sd.fti_in_control = True
                        # leave the original Take Profit order in place now FTI allows that to be changed too
                        # response = sd.lim_order.Cancel(f"Removing Take Profit order - {symbol}")
                        
                    if sd.activeStrat != Strats.Nothing and sd.ftichangeprofit:
                        sd.ftichangeprofit = False
                        newpriceprofit = sd.ftichangeprofitpips * sd.minPriceVariation * 10    #turn into pips from pipettes
                        new_profit_level = round(sd.entry_prices[index] - newpriceprofit, 6)
                        #self.Debug(f"Update take profit {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpipsnow: {round(pnlpips, 6)} TakeProfit: {round(new_profit_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.LimitPrice = new_profit_level
                        sd.tickets_profits[index].Update(update_order_fields)
                        sd.ftichangeprofitpips = 0.0
                        sd.fti_in_control = True
                    
                    if sd.fti_in_control:
                        return 
                        
                    if askpricenow < sd.entry_prices[index]:        # price has moved down - some profit
                        # look through the breakout strategy arrays and set new stop if in a new range    
                        i = 1
                        while i < len(sd.breakout_pnl):
                            if (pnlpips >= sd.breakout_pnl[i-1] and pnlpips < sd.breakout_pnl[i]) or \
                            (i == (len(sd.breakout_pnl) - 1) and pnlpips >= sd.breakout_pnl[i]):
                                if i-1 > sd.sl_positions[index]:
                                    newpriceloss = sd.breakout_trail[i-1] * sd.minPriceVariation * 10    #turn into pips from pipettes
                                    new_sl_level = round(sd.entry_prices[index] - newpriceloss, 6)
                                    sd.sl_positions[index] = i-1   # Remember how far we are.  Do not go backwards
                                    # Upate our stoploss order! 
                                    #self.Log(f"Level [{str(index +1)}]: Update stop loss {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpips: {round(pnlpips, 6)} new_stop_loss(pips): {round(newpriceloss, 6)} new_stop_loss(price): {round(new_sl_level, 6)}")
                                    self.Debug(f" a. Level [{str(index +1)}], Update stop loss {symbol} - pnlpips: {round(pnlpips, 6)} new_stop_loss(pips): {round(newpriceloss, 6)} new_stop_loss(price): {round(new_sl_level, 6)}")
                                    update_order_fields = UpdateOrderFields()
                                    update_order_fields.StopPrice = new_sl_level
                                    sd.tickets_stops[index].Update(update_order_fields)
                                    # store last sl_level
                                    sd.last_trail_levels[index] = new_sl_level
                                    

                                if i == (len(sd.breakout_pnl) - 1) and sd.sl_positions[index] < i and pnlpips >= sd.breakout_pnl[i]:
                                    newpriceloss = sd.breakout_trail[i] * sd.minPriceVariation * 10    #turn into pips from pipettes                                     
                                    new_sl_level = round(sd.entry_prices[index] - newpriceloss, 6)
                                    sd.sl_positions[index] = i   # Remember how far we are.  Do not go backwards
                                    # Upate our stoploss order! 
                                    self.Log(f"Update stop loss {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpips: {round(pnlpips, 6)} new_stoploss: {round(newpriceloss, 6)} SL: {round(new_sl_level, 6)}")
                                    self.Debug(f"b. Level [{str(index +1)}], Update stop loss {symbol} - pnlpips: {round(pnlpips, 6)} new_stop_loss(pips): {round(newpriceloss, 6)} new_stop_loss(price): {round(new_sl_level, 6)}")
                                    update_order_fields = UpdateOrderFields()
                                    update_order_fields.StopPrice = new_sl_level
                                    sd.tickets_stops[index].Update(update_order_fields)
                                    # store last sl_level
                                    sd.last_trail_levels[index] = new_sl_level                               
                            i += 1
                                # manage stops all the time
                    #Si call position update after updating the stops / limits - 22.03 will come in future from setting
                    #self.update_position(sd, pnlpips, -1, symbol)
                        
        if  sd.activeDirection == StratDirection.Long:
            # Already in a Long - need to manage trailling stop and take profit
            # Long entry used ASK prices - getting out uses BID
            for index in range(0, len(sd.tickets_live_levels)):
                if sd.tickets_live_levels[index]:

                    pnlpips = round((bidpricenow - sd.entry_prices[index]), 6) / pipsize
                    if pnlpips > sd.max_pips_profits[index]:
                        sd.max_pips_profits[index] = pnlpips
                    if pnlpips < sd.max_pips_losses[index]:
                        sd.max_pips_losses[index] = pnlpips * -1.0

                    #sd.ftisplitpot = True   #force for testing
                    if sd.activeStrat != Strats.Nothing and sd.ftisplitpot:
                        self.Log(f"Split pot {symbol} on {sd.activeStrat}:{sd.activeDirection} by 50% (hard coded for moment)")                        
                        self.update_position(sd, pnlpips, 1, symbol)
                        sd.ftisplitpot = False                        
                        sd.fti_in_control = True                        
                    
                    if sd.activeStrat != Strats.Nothing and sd.ftichangestop:
                        sd.ftichangestop = False
                        newpriceloss = sd.ftichangepips * sd.minPriceVariation * 10    #turn into pips from pipettes
                        new_sl_level = round(sd.entry_prices[index] + newpriceloss, 6)
                        #self.Log(f"Update stop loss {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpipsnow: {round(pnlpips, 6)} SL: {round(new_sl_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.StopPrice = new_sl_level
                        sd.tickets_stops[index].Update(update_order_fields)
                        sd.ftichangepips = 0.0
                        sd.fti_in_control = True
                        # leave the original take profit order in place now FTI allows that to be changed too
                        # response = sd.lim_order.Cancel(f"Removing Take Profit order - {symbol}")
                        
                    if sd.activeStrat != Strats.Nothing and sd.ftichangeprofit:
                        sd.ftichangeprofit = False
                        newpriceprofit = sd.ftichangeprofitpips * sd.minPriceVariation * 10    #turn into pips from pipettes
                        new_profit_level = round(sd.entry_prices[index] + newpriceprofit, 6)
                        #self.Log(f"Update take profit {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpipsnow: {round(pnlpips, 6)} TakeProfit: {round(new_profit_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.LimitPrice = new_profit_level
                        sd.tickets_profits[index].Update(update_order_fields)
                        sd.ftichangeprofitpips = 0.0
                        sd.fti_in_control = True
                    
                    if sd.fti_in_control:
                        return
                    
                    if bidpricenow > sd.entry_prices[index]:        # price up - some profit
                        # look through the breakout strategy arrays and set new stop if in a new range    
                        i = 1
                        while i < len(sd.breakout_pnl):
                            if (pnlpips >= sd.breakout_pnl[i-1] and pnlpips < sd.breakout_pnl[i]) or \
                            (i == (len(sd.breakout_pnl) - 1) and pnlpips >= sd.breakout_pnl[i]):
                                if i-1 > sd.sl_positions[index]:
                                    newpriceloss = sd.breakout_trail[i-1] * sd.minPriceVariation * 10    #turn into pips from pipettes                                   
                                    new_sl_level = round(sd.entry_prices[index] + newpriceloss, 6)
                                    sd.sl_positions[index] = i-1   # Remember how far we are.  Do not go backwards
                                    # Upate our stoploss order! 
                                    self.Log(f"Update stop loss {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpips:{round(pnlpips, 6)}, stopLossPips: {round(newpriceloss, 6)} stopLoss: {round(new_sl_level, 6)}")
                                    update_order_fields = UpdateOrderFields()
                                    update_order_fields.StopPrice = new_sl_level
                                    sd.tickets_stops[index].Update(update_order_fields)
                                    # store last sl_level
                                    sd.last_trail_levels[index] = new_sl_level

                                if i == (len(sd.breakout_pnl) - 1) and sd.sl_positions[index] < i and pnlpips >= sd.breakout_pnl[i]:
                                    newpriceloss = sd.breakout_trail[i] * sd.minPriceVariation * 10    #turn into pips from pipettes                                    
                                    new_sl_level = round(sd.entry_prices[index] + newpriceloss, 6)
                                    sd.sl_positions[index] = i   # Remember how far we are.  Do not go backwards
                                    # Upate our stoploss order! 
                                    self.Log(f"Update stop loss {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpips: {round(pnlpips, 6)} priceloss: {round(newpriceloss, 6)} SL: {round(new_sl_level, 6)}")
                                    update_order_fields = UpdateOrderFields()
                                    update_order_fields.StopPrice = new_sl_level
                                    sd.tickets_stops[index].Update(update_order_fields)
                                    # store last sl_level
                                    sd.last_trail_levels[index] = new_sl_level
                                   
                            i += 1    

                    #Si call position update after updating the stops / limits - 22.03 will come in future from setting
                    #self.update_position(sd, pnlpips, 1, symbol)    

    def manage_trailling_stops(self, sd :SymbolData, askpricenow, bidpricenow, pipsize):
        # used to manage all the stop loss orders - Brad Perfect
        ''' TODO: Need to add in the ability to have different Stop Loss and Take Profit setups on each live ticket.
        '''
        symbol = sd.Symbol
        mt4_time = fusion_utils.get_times(self.Time, 'us')['mt4']
        
        if  sd.activeDirection == StratDirection.Short:
            # Already in a Short - need to manage trailling stop and take profit, at multiple levels
            # Short entry used BID prices - getting out uses ASK
            for index in range(0, len(sd.tickets_live_levels)):
                if sd.tickets_live_levels[index]:


                    # only manage stops if we have a live order at this level - usually only will be the first one
                    pnlpips = round((sd.entry_prices[index] - askpricenow), 6) / pipsize
                    must_move_stop_to_breakeven = False
                    if pnlpips >= sd.trading_move_to_be_profit_pips and sd.trading_move_to_be_flag and sd.trading_stop_allow_ratchet and not sd.trading_move_to_be_done:
                        must_move_stop_to_breakeven = True
                        sd.trading_move_to_be_done = True
                        new_stop_loss_pips = sd.trading_move_to_be_new_stop_pips
                    must_move_trailling_stop = False
                    if not must_move_stop_to_breakeven:
                        # only move the trailling stop if we are not moving to 'breakeven' this visit
                        if pnlpips > sd.max_pips_profits[index]:
                            new_pnl_pips = pnlpips
                            old_pnl_pips = sd.max_pips_profits[index]
                            pip_diff_for_stop = round(new_pnl_pips - old_pnl_pips, 0)
                            if pip_diff_for_stop >= 1.0:
                                # if profit has moved up by more than a whole pip from the prior level
                                must_move_trailling_stop = True
                                self.Debug(f" a. Level [{str(index +1)}], new Max pips on SHORT trade {symbol} - pnlpips: {round(pnlpips, 2)} ")
                                #TODO Si move into manage perfect - just here for now                                
                                sd.tbu_perfect_tracker[ChartRes.res5M].add_to_event_log(mt4_time,"Mew Max Pips", f"pnlpips: {round(pnlpips, 2)}",0, "tick")     
                            sd.max_pips_profits[index] = pnlpips

                    if pnlpips < sd.max_pips_losses[index]:
                        sd.max_pips_losses[index] = pnlpips * -1.0

                    #sd.ftisplitpot = True   #force for testing
                    if sd.activeStrat != Strats.Nothing and sd.ftisplitpot:                        
                        self.Log(f"Split pot {symbol} on {sd.activeStrat}:{sd.activeDirection} by 50% (hard coded for moment)")                        
                        self.update_position(sd, pnlpips, -1, symbol)
                        sd.ftisplitpot = False
                        sd.fti_in_control = True

                    # TODO: add ability for FTI to modify the distance of the trailling stop
                    '''if sd.activeStrat != Strats.Nothing and sd.ftichangestop:
                        sd.ftichangestop = False
                        newpriceloss = sd.ftichangepips * sd.minPriceVariation * 10    #turn into pips from pipettes
                        new_sl_level = round(sd.entry_prices[index] - newpriceloss, 6)                       
                        self.Debug(f"Update stop loss {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpipsnow: {round(pnlpips, 6)} SL: {round(new_sl_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.StopPrice = new_sl_level
                        sd.tickets_stops[index].Update(update_order_fields)
                        sd.ftichangepips = 0.0
                        sd.fti_in_control = True
                        # leave the original Take Profit order in place now FTI allows that to be changed too
                        # response = sd.lim_order.Cancel(f"Removing Take Profit order - {symbol}")'''
                        
                    if sd.activeStrat != Strats.Nothing and sd.ftichangeprofit:
                        sd.ftichangeprofit = False
                        newpriceprofit = sd.ftichangeprofitpips * sd.minPriceVariation * 10    #turn into pips from pipettes
                        new_profit_level = round(sd.entry_prices[index] - newpriceprofit, 6)
                        #self.Log(f"Update take profit {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpipsnow: {round(pnlpips, 6)} TakeProfit: {round(new_profit_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.LimitPrice = new_profit_level
                        sd.tickets_profits[index].Update(update_order_fields)
                        sd.ftichangeprofitpips = 0.0
                        sd.fti_in_control = True
                    
                    # TODO: watch out for this, stops no longer get managed on a split pot - not sure why?
                    if sd.fti_in_control:                       
                        return 

                    must_move_trailling_stop = False    #si switch off TS

                    if must_move_stop_to_breakeven:
                        new_price_loss = new_stop_loss_pips * 1.0 * sd.minPriceVariation * 10      #turn into pips from pipettes               
                        new_sl_level = round(sd.entry_prices[index] - new_price_loss, 5)        # this goes off the entry price - note, not current price
                        self.Debug(f" a. Level [{str(index +1)}], Move to breakeven pip level SHORT {symbol} - pnlpips: {round(pnlpips, 6)} new_stop_loss(pips): {round(new_price_loss, 1)} new_stop_loss(price): {round(new_sl_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.StopPrice = new_sl_level
                        sd.tickets_last_stop_levels[index] = new_sl_level
                        sd.tickets_stops[index].Update(update_order_fields)  

                    if must_move_trailling_stop:
                        new_price_loss = sd.trailling_pips * -1.0 * sd.minPriceVariation * 10      #turn into pips from pipettes               
                        new_sl_level = round(askpricenow - new_price_loss, 5)
                        if sd.tickets_last_stop_levels[index] < new_sl_level:
                            # implies we have already moved a trailling stop closer - and need to wait until we regain the trailling gap
                            self.Log(f" a. Level [{str(index +1)}], Abort update trailling stop {symbol} - pnlpips: {round(pnlpips, 6)} - stop too close; enable ratchet")
                        else:
                            self.Debug(f" a. Level [{str(index +1)}], Update trailling stop SHORT {symbol} - pnlpips: {round(pnlpips, 6)} new_stop_loss(pips): {round(sd.trailling_pips, 1)} new_stop_loss(price): {round(new_sl_level, 6)}")
                            update_order_fields = UpdateOrderFields()
                            update_order_fields.StopPrice = new_sl_level
                            sd.tickets_last_stop_levels[index] = new_sl_level
                            sd.tickets_stops[index].Update(update_order_fields)
                        
                        
        if  sd.activeDirection == StratDirection.Long:
            # Already in a Long - need to manage trailling stop and take profit
            # Long entry used ASK prices - getting out uses BID
            for index in range(0, len(sd.tickets_live_levels)):
                if sd.tickets_live_levels[index]:

                    pnlpips = round((bidpricenow - sd.entry_prices[index]), 6) / pipsize
                    must_move_stop_to_breakeven = False
                    if pnlpips >= sd.trading_move_to_be_profit_pips and sd.trading_move_to_be_flag and sd.trading_stop_allow_ratchet and not sd.trading_move_to_be_done:
                        must_move_stop_to_breakeven = True
                        sd.trading_move_to_be_done = True
                        new_stop_loss_pips = sd.trading_move_to_be_new_stop_pips
                    must_move_trailling_stop = False
                    if not must_move_stop_to_breakeven:
                        # only move the trailling stop if we are not moving to 'breakeven' this visit
                        if pnlpips > sd.max_pips_profits[index]:
                            new_pnl_pips = pnlpips
                            old_pnl_pips = sd.max_pips_profits[index]
                            pip_diff_for_stop = round(new_pnl_pips - old_pnl_pips, 0)
                            if pip_diff_for_stop >= 1.0:
                                # if profit has moved up by more than a whole pip from the prior level
                                must_move_trailling_stop = True
                                self.Debug(f" a. Level [{str(index +1)}], new Max pips on LONG trade {symbol} - pnlpips: {round(pnlpips, 2)} ")
                                sd.tbu_perfect_tracker[ChartRes.res5M].add_to_event_log(mt4_time,"Mew Max Pips", f"pnlpips: {round(pnlpips, 2)}",0, "tick")     

                            sd.max_pips_profits[index] = pnlpips

                    if pnlpips < sd.max_pips_losses[index]:
                        sd.max_pips_losses[index] = pnlpips * -1.0

                    #sd.ftisplitpot = True   #force for testing
                    if sd.activeStrat != Strats.Nothing and sd.ftisplitpot:
                        self.Log(f"Split pot {symbol} on {sd.activeStrat}:{sd.activeDirection} by 50% (hard coded for moment)")                        
                        self.update_position(sd, pnlpips, 1, symbol)
                        sd.ftisplitpot = False                        
                        sd.fti_in_control = True                        
                     
                     # TODO: add ability for FTI to modify the distance of the trailling stop on Longs too
                    '''if sd.activeStrat != Strats.Nothing and sd.ftichangestop:
                        sd.ftichangestop = False
                        newpriceloss = sd.ftichangepips * sd.minPriceVariation * 10    #turn into pips from pipettes
                        new_sl_level = round(sd.entry_prices[index] + newpriceloss, 6)
                        #self.Log(f"Update stop loss {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpipsnow: {round(pnlpips, 6)} SL: {round(new_sl_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.StopPrice = new_sl_level
                        sd.tickets_stops[index].Update(update_order_fields)
                        sd.ftichangepips = 0.0
                        sd.fti_in_control = True
                        # leave the original take profit order in place now FTI allows that to be changed too
                        # response = sd.lim_order.Cancel(f"Removing Take Profit order - {symbol}")'''
                        
                    if sd.activeStrat != Strats.Nothing and sd.ftichangeprofit:
                        sd.ftichangeprofit = False
                        newpriceprofit = sd.ftichangeprofitpips * sd.minPriceVariation * 10    #turn into pips from pipettes
                        new_profit_level = round(sd.entry_prices[index] + newpriceprofit, 6)
                        #self.Log(f"Update take profit {symbol} on {sd.activeStrat}:{sd.activeDirection} - pnlpipsnow: {round(pnlpips, 6)} TakeProfit: {round(new_profit_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.LimitPrice = new_profit_level
                        sd.tickets_profits[index].Update(update_order_fields)
                        sd.ftichangeprofitpips = 0.0
                        sd.fti_in_control = True
                    
                    #TODO: same concern as above, why would stops not get managed after splitting pot?
                    if sd.fti_in_control:
                        return

                    must_move_trailling_stop = False    #si switch off TS

                    if must_move_stop_to_breakeven:
                        new_price_loss = new_stop_loss_pips * 1.0 * sd.minPriceVariation * 10      #turn into pips from pipettes               
                        new_sl_level = round(sd.entry_prices[index] + new_price_loss, 5)        # this goes off the entry price - note, not current price
                        self.Debug(f" a. Level [{str(index +1)}], Move to breakeven pip level LONG {symbol} - pnlpips: {round(pnlpips, 6)} new_stop_loss(pips): {round(new_price_loss, 1)} new_stop_loss(price): {round(new_sl_level, 6)}")
                        update_order_fields = UpdateOrderFields()
                        update_order_fields.StopPrice = new_sl_level
                        sd.tickets_last_stop_levels[index] = new_sl_level
                        sd.tickets_stops[index].Update(update_order_fields)                        

                    if must_move_trailling_stop:
                        new_price_loss = sd.trailling_pips * -1.0 * sd.minPriceVariation * 10      #turn into pips from pipettes               
                        new_sl_level = round(bidpricenow + new_price_loss, 5)
                        if sd.tickets_last_stop_levels[index] > new_sl_level:
                            # implies we have already moved a trailling stop closer - and need to wait until we regain the trailling gap
                            self.Log(f" a. Level [{str(index +1)}], Abort update trailling stop {symbol} - pnlpips: {round(pnlpips, 6)} - stop too close; enable ratchet")
                        else:
                            self.Debug(f" a. Level [{str(index +1)}], Update trailling stop LONG {symbol} - pnlpips: {round(pnlpips, 6)} new_stop_loss(pips): {round(sd.trailling_pips, 1)} new_stop_loss(price): {round(new_sl_level, 6)}")
                            update_order_fields = UpdateOrderFields()
                            update_order_fields.StopPrice = new_sl_level
                            sd.tickets_last_stop_levels[index] = new_sl_level
                            sd.tickets_stops[index].Update(update_order_fields)

