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
import csv
import os
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
from channel_breakouts import *
from QuantConnect import Market
from io import StringIO


'''Contains a bunch of helper functions for dealing with notifications and comms with FTI - in an attempt to save space in the main file'''

class QCalgo_notifications(QCalgo_channel_breakout):
    
    def __init__(self):
        '''IMPORTANT
        Need this initialise from the C# class above.  Without that for some reason we get the python pythonnet errors.  
        See support ticket with QuantConnect
        '''
        super().__init__()

        # Create some buffer variables to store the log messages
        self.log_buffer_hourly = []         # array to store messages in
        self.log_buffer_daily = []
    
    # Stack up the messages in a buffer for emailing once per hour at 1minute past the hour
    # separate event handler defined to send the email and clear the buffer
    def LogHourly(self, new_row):
        if self.debugging_trade_tracking: self.Debug(f"hourly:" + str(new_row))
        #if self.LiveMode:
        self.log_buffer_hourly.append(new_row)
            # the log_buffer_hourly will get several items added to it and only email in the separate event handler

    def SendBreakoutEmail(self, symbol, mt4_time, pos4_price, pos4_time, BO_type, BO_label, BO_pullback1_price, pb1_distance_pips, double_spot):
        if self.IsWarmingUp:
            return
        
        sdh = self.symbolInfo[symbol]
        #get the current trends for each resolution:
        my_template_5m = sdh.EH_EL_tracker[ChartRes.res5M].get_template() 
        my_template_15m = sdh.EH_EL_tracker[ChartRes.res15M].get_template() 
        my_template_30m = sdh.EH_EL_tracker[ChartRes.res30M].get_template() 
        my_template_1h = sdh.EH_EL_tracker[ChartRes.res1H].get_template()
        my_template_4h = sdh.EH_EL_tracker[ChartRes.res4H].get_template()
        my_template_24h = sdh.EH_EL_tracker[ChartRes.res24H].get_template()
            
        logmsg = f"Spotted: {BO_label}, {BO_type}, Pullback price: {BO_pullback1_price}, PB1 distance {pb1_distance_pips} pips\n" + self.ModeName   
        logmsg += f"\n5m: {my_template_5m} \n15m: {my_template_15m} \n30m: {my_template_30m} \n1h: {my_template_1h} \n4h: {my_template_4h} \n24h: {my_template_24h}"
        
        logdate = fusion_utils.format_datetime_using_string(mt4_time, "@ %H.%M %Y.%m.%d")

        if double_spot:
            logsub = f"** DOUBLE SPOT BREAKOUT **: {symbol} {BO_type} | {logdate}" 
        else:    
            logsub = f"** BREAKOUT Get on Charts **: {symbol} {BO_type} | {logdate}"  

        if self.LiveMode:
            self.Notify.Email(self.EmailAddress, f"{logsub} | {self.ModeName} ", logmsg)  
        if self.debugging_trade_tracking:
            self.Debug(logsub + "\n" + logmsg)
            #print(logsub + "\n" + logmsg)

    
    # once an hour if we are running Live then send any contents from the populated hourly_buffer
    def LogHourlySend(self):
        if self.IsWarmingUp:
            return
        minute_of_hour = self.Time.minute
        # TODO: get it to also send once on startup when this event fires
        #if minute_of_hour == 1 and self.log_buffer_hourly:
            # it is 1 minute past the hour and we have a non-zero buffer
        if minute_of_hour == 1:            
            # send email
            logmsg = ""

            if len(self.log_buffer_hourly) > 0:                                
                for log_dictionary in self.log_buffer_hourly:
                    row = "\n".join("{} = {}".format(*item) for item in log_dictionary.items()) 
                    logmsg += row + "\n\n***************************\n\n" + self.ModeName 
                    
            else:
                 logmsg = "No Breakouts Spotted\n" + self.ModeName 
            #print(logmsg) 
            if self.debugging_trade_tracking: self.Log("DEBUG - would now be sending the hourly email\n" + logmsg)    

            email_time = datetime.strftime(fusion_utils.get_times((self.Time - timedelta(minutes=1)), "us")["mt4"], "%d.%m.%y %H:%M")             
            if self.CountEmails < 480 and self.LiveMode:
                self.CountEmails += 1
                self.Notify.Email(self.EmailAddress, f"Hourly Notification (MT4): {email_time} | {self.ModeName} ", logmsg)
            self.log_buffer_hourly = []
            
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
        
    def write_trade_results(self, symbol, direction, pnlpips, pnl, lot_size, entry_time, entry_price, exit_time, exit_price, max_pip_profit, max_pip_loss, reason_close, \
        spread, msg_tag, bo_label):
        #prepare trade results data for export, storage, email or whatever
        entry_time = fusion_utils.get_times(entry_time, 'us') ['mt4']
        exit_time = fusion_utils.get_times(exit_time, 'us') ['mt4']

        result = {'symbol': symbol, 
                    'direction': direction,
                    "pnlpips": pnlpips,
                    "pnl": pnl,
                    "lot_size": lot_size,
                    "entry_time": entry_time,
                    "entry_price": entry_price,
                    "exit_time": exit_time,
                    "exit_price": exit_price,
                    "max_pips_profit": max_pip_profit,
                    "max_pips_loss": max_pip_loss,
                    "reason_close": reason_close,
                    "spread": spread,
                    "msg_tag": msg_tag,
                    "bo_label": bo_label}

        result_msg = "\n".join("{} = {}".format(*item) for item in result.items())   
        logdate = datetime.strftime(entry_time, "%d/%m/%y %H:%M")
        logsub = f"Trade Result: {symbol} {direction} @ {logdate}"
        if self.LiveMode:
            self.Notify.Email(self.EmailAddress, f"{logsub} | {self.ModeName}", result_msg)  
        if self.debugging_trade_tracking:
            self.Debug(logsub + "\n" + result_msg)


    # Email and log notification - send it to the console log, plus also email it immediately
    def LogExtra(self, logmsg, logsub):
        if self.ManualLiveTrading or (self.ManualHistoryTrading and self.InCloud) or self.LiveMode: 
            # send email
            if self.CountEmails < 480:
                self.CountEmails += 1
                self.Notify.Email(self.EmailAddress, f"{logsub} | {self.ModeName}", logmsg)
        self.Log(logmsg)        # log the message to the console as it arrives - do not wait for the hourly bundle
        
    # Formatted email - send immediately #10.8
    def LogFormatted(self, logmsg, logsub):
        if self.ManualLiveTrading or (self.ManualHistoryTrading and self.InCloud): 
            if self.CountEmails < 480:
                self.CountEmails += 1
                logdate = datetime.strftime(self.Time, "%d/%m/%y %H:%M")
                self.Notify.Email(self.EmailAddress, f"{logsub}: {logdate} | {self.ModeName}", logmsg)
        self.Log(logmsg)        # log the message to the console as it arrives 

    
                                
    def OnEndOfAlgorithm(self):
        self.Log(f"Closing down algo at: {self.Time}, final logs:")
        # loop through each symbol in our structure
        for logline in self.tradesEntered:
            # Make sure to log out the trades we entered
            self.Log(logline)
        # loop through each symbol in our structure
        for symbol in self.symbolInfo.keys():
                sd = self.symbolInfo[symbol]
                if sd.total_algo_pips != 0.0:
                    self.Log(f"{symbol} - Total Trading Pips this run: {round(sd.total_algo_pips, 1)}")

        self.Log(f"CLEAN BREAKOUTS: Total number of 5Min breakouts found in algo run: SHORT {self.breakout_count_5M_short} LONG {self.breakout_count_5M_long}")
        self.Log(f"DIRTY BREAKOUTS: Total number of 5Min breakouts found in algo run: SHORT {self.breakout_count_dirty_5M_short} LONG {self.breakout_count_dirty_5M_long}")
        self.Log(f"Ignored 5M Peaks {self.ignored_5M_peaks} and ignored 5M Troughs {self.ignored_5M_troughs}")
        # this should get the price trackers to log at the end
        if self.log_price_trackers_at_end:
            self.price_tracker_lib.dump_tracker_state(self)
        # this should get the session boxes to log at the end
        if self.log_session_boxes_at_end:
            for symbol in self.symbolInfo.keys():
                sd = self.symbolInfo[symbol]
                self.Log(f"{symbol} - Dumping Session Box History")
                sd.historic_sessions.dump_session_history(self)

        if not self.LiveMode:
            # only dump these logs at the end if we are not running on QC.  otherwise search and replace needed
            if self.log_eh_el_at_end:
                to_file_only = True

                fieldnames = ['symbol', 'resolution', 'time', 'EH_or_EL', 'price', 'label', 'pips_height','move_type','template','last_peak_price','last_trough_price']
                rows = []
                blank_row = {'symbol': None, 
                            'resolution': None,
                            'time': None,
                            'EH_or_EL': None,
                            'price': None, 
                            'label': None, 
                            'pips_height': None,
                            'move_type': None,
                            'template': None,
                            'last_peak_price': None,
                            'last_trough_price': None}
                time_offset = None            
                for symbol in self.symbolInfo.keys():
                    sd = self.symbolInfo[symbol]
                    self.Log(f"{symbol} - Dumping EH/EL History - may go to CSV rather than log")
                    for chart_res in ChartRes:
                    # TODO: make this go for all chart resolutions, but check the key first                                               
                                                
                        self.Log(f"{symbol} - Dumping EH/EL @ {chart_res}")
                        if not to_file_only: sd.EH_EL_tracker[chart_res].dump_EH_EL_history(self)       # only dump to text log if needed
                        for row in sd.EH_EL_tracker[chart_res].EH_EL_library:
                            new_row = blank_row.copy()
                            new_row['symbol'] = symbol
                            new_row['resolution'] = chart_res
                            new_row['time'] = fusion_utils.format_datetime_using_string(fusion_utils.get_candle_open_time(row['time'] , chart_res))           
                            new_row['EH_or_EL'] = row['EH_or_EL']
                            new_row['price'] = row['price']
                            new_row['label'] = row['label']
                            new_row['pips_height'] = row['pips_height']
                            new_row['move_type'] = row['move_type']
                            new_row['template'] = row['template']
                            new_row['last_peak_price'] = row['last_peak_price']
                            new_row['last_trough_price'] = row['last_trough_price']

                            rows.append(new_row)
                path = os.path.join(Globals.DataFolder, "EH_EL_dump.csv")
                # FOR LIVE - SEARCH and REPLACE with poop
                with open(path, 'w', encoding='UTF8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)


            if self.log_tbu_perfects_at_end:
                dump_all_to_file = True
                to_file_only = True
                write_to_hourly = False
                self.OutputFunction(dump_all_to_file, to_file_only, write_to_hourly, None)

            
            #temp output candle log
            fieldnames = ['candle_time_mt4', 'candle_chart', 'candle_type', 'candle_symbol']
            rows = []
            blank_row = {'candle_time_mt4': None, 
                        'candle_chart': None,
                        'candle_type': None,
                        'candle_symbol': None}

            for row in self.candle_type_log:
                new_row = blank_row.copy()
                new_row['candle_time_mt4'] = row['candle_time_mt4']
                new_row['candle_chart'] = row['candle_chart']       
                new_row['candle_type'] = row['candle_type']
                new_row['candle_symbol'] = row['candle_symbol']

                rows.append(new_row)
                
            path = os.path.join(Globals.DataFolder, "candle_type_dump.csv")
            # FOR LIVE - SEARCH and REPLACE with poop
            with open(path, 'w', encoding='UTF8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)




                                                            
    def OutputFunction(self, dump_all_to_file, to_file_only, write_to_hourly, log_sub):
        # will output the results         

        fieldnames = ['symbol', 'double_spot', 'resolution', "BO_label", "update_time", "pos1_label", "pos1_price", "pos1_time", "pos2_label", "pos2_price", \
                    "pos2_time", "pos3_label", "pos3_price", "pos3_time", "pos4_label", "pos4_price", "pos4_time", "pullback1_price", "EH_price", \
                    "EL_price", "TW", "status", "pullback1_hit", "BO_pullback1_breached_time", "hh_or_ll_hit", "hh_or_ll_time", "ignore_200ema", "squeeze_status", "squeeze_time", \
                    "squeeze_price", "enter_trade", "reason_notes", "entry_time", "ema9", "ema45", "ema135", "ema200", \
                    "last_1m_peak", "last_1m_trough", "trend_5m", "trend_1h", "with_5m_trend", "with_1h_trend", "stop_pips", "stop_price", "stop_comments", "take_profit_pips", \
                    "take_profit_price", "take_profit_comments", "move_breakeven", "result_pips", "spread_pips", "max_pips_profit", "void_trade_high", "void_trade_low", "rolling_high", \
                    "rolling_low"]


        rows = []
        blank_row = {'symbol': None,
                    'double_spot': None, 
                    'resolution': None,
                    "BO_label": None,
                    "update_time": None,
                    "pos1_label": None,
                    "pos1_price": None,
                    "pos1_time": None,
                    "pos2_label": None,
                    "pos2_price": None,
                    "pos2_time": None,
                    "pos3_label": None,
                    "pos3_price": None,
                    "pos3_time": None,
                    "pos4_label": None,
                    "pos4_price": None,
                    "pos4_time": None,
                    "pullback1_price": None,
                    "EH_price": None,
                    "EL_price": None,
                    "TW": None,
                    "status": None,
                    "pullback1_hit": None,
                    "BO_pullback1_breached_time": None,
                    "hh_or_ll_hit": None,
                    "hh_or_ll_time": None,                         
                    "ignore_200ema": None,
                    "squeeze_status": None,
                    "squeeze_time": None,
                    "squeeze_price": None,
                    "enter_trade": None,
                    "reason_notes": None,
                    "entry_time": None,
                    "ema9": None,
                    "ema45": None,
                    "ema135": None,
                    "ema200": None,
                    "last_1m_peak": None,
                    "last_1m_trough": None,
                    "trend_5m": None,
                    "trend_1h": None,
                    "with_5m_trend": None,
                    "with_1h_trend": None,
                    "stop_pips": None,
                    "stop_price": None,
                    "stop_comments": None,
                    "take_profit_pips": None,
                    "take_profit_price": None,
                    "take_profit_comments": None,
                    "move_breakeven": None,
                    "result_pips": None,
                    "spread_pips": None,
                    "max_pips_profit": None,
                    "void_trade_high": None,
                    "void_trade_low": None,
                    "rolling_high": None,
                    "rolling_low": None}
                
        for symbol in self.symbolInfo.keys():
            sd = self.symbolInfo[symbol]
            self.Log(f"{symbol} - Dumping Trade Build Up Perfects - may go to CSV rather than log")
            for chart_res in ChartRes:                    
                
                if chart_res in sd.tbu_perfect_tracker.keys():
                    # not all chart resolutions will have been storing Perfect build-ups
                    self.Log(f"{symbol} - Dumping Build Up Perfects @ {chart_res}")
                    if not to_file_only: sd.tbu_perfect_tracker[chart_res].dump_perfect_history(self)  
                    
                    if dump_all_to_file:
                        for row in sd.tbu_perfect_tracker[chart_res].perfect_library:
                            new_row = self.Write_Row(row, blank_row, chart_res, symbol)   
                            rows.append(new_row)                         
                    else:
                        #check if there are any rows in sd.tbu_perfect_tracker
                        if len(sd.tbu_perfect_tracker[chart_res].perfect_library) > 0:
                            # get the last row
                            row = sd.tbu_perfect_tracker[chart_res].perfect_library[-1]
                            new_row = self.Write_Row(row, blank_row, chart_res, symbol)   
                            rows.append(new_row)
                            if write_to_hourly:
                                self.LogHourly(new_row)                    
                if not self.LiveMode:
                    path = os.path.join(Globals.DataFolder, "tbu_perfects_dump.csv")
                    # FOR LIVE - SEARCH and REPLACE with poop
                    with open(path, 'w', encoding='UTF8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)

    def Write_Row(self, row, blank_row, chart_res, symbol):

        new_row = blank_row.copy()

        self.Log(f"row['BO_label']: {row['BO_label']} | self.myRes: {self.myRes}")

        new_row['symbol'] = symbol
        new_row['double_spot'] = row['double_spot']
        new_row['resolution'] = chart_res
        new_row['BO_label'] = row['BO_label']
        new_row['update_time'] = fusion_utils.format_datetime_using_string(row['update_time']) 
        new_row['pos1_label'] = row['pos1_label']
        new_row['pos1_price'] = row['pos1_price']
        
        new_row['pos1_time'] = fusion_utils.format_datetime_using_string(fusion_utils.get_candle_open_time(row['pos1_time'] , chart_res))                      
        new_row['pos2_label'] = row['pos2_label']
        new_row['pos2_price'] = row['pos2_price']
        new_row['pos2_time'] = fusion_utils.format_datetime_using_string(fusion_utils.get_candle_open_time(row['pos2_time'], chart_res))    
        new_row['pos3_label'] = row['pos3_label']
        new_row['pos3_price'] = row['pos3_price']
        new_row['pos3_time'] = fusion_utils.format_datetime_using_string(fusion_utils.get_candle_open_time(row['pos3_time'], chart_res))     
        new_row['pos4_label'] = row['pos4_label']
        new_row['pos4_price'] = row['pos4_price']
        new_row['pos4_time'] = fusion_utils.format_datetime_using_string(fusion_utils.get_candle_open_time(row['pos4_time'], chart_res))    
        new_row['pullback1_price'] = row['pullback1_price']
        new_row['EH_price'] = row['EH_price']
        new_row['EL_price'] = row['EL_price']
        new_row['TW'] = row['TW']
        new_row['status'] = row['status']
        new_row['pullback1_hit'] = row['pullback1_hit']                      

        if row['BO_pullback1_breached_time'] is not None:
            new_row['BO_pullback1_breached_time'] = fusion_utils.format_datetime_using_string(fusion_utils.get_candle_open_time(row['BO_pullback1_breached_time'], None))
        else:
            new_row['BO_pullback1_breached_time'] = None     

        if row['hh_or_ll_time'] is not None:
            new_row['hh_or_ll_time'] = row['hh_or_ll_time']
        else:
            new_row['hh_or_ll_time'] = None                            
        new_row['hh_or_ll_hit'] = row['hh_or_ll_hit']

        new_row['ignore_200ema'] = row['ignore_200ema']
        new_row['squeeze_status'] = row['squeeze_status']
        if row['squeeze_time'] is not None:
            new_row['squeeze_time'] = row['squeeze_time']
        else:
            new_row['squeeze_time'] = None 
                                
        new_row['squeeze_price'] = row['squeeze_price']
        new_row['enter_trade'] = row['enter_trade']
        new_row['reason_notes'] = row['reason_notes']

        if row['entry_time'] is not None:
            new_row['entry_time'] =  fusion_utils.format_datetime_using_string(fusion_utils.get_candle_open_time(row['entry_time'], None))
        else:
            new_row['entry_time'] = None

        new_row['ema9'] = row['ema9']
        new_row['ema45'] = row['ema45']
        new_row['ema135'] = row['ema135']
        new_row['ema200'] = row['ema200']
        new_row['last_1m_peak'] = row['last_1m_peak']
        new_row['last_1m_trough'] = row['last_1m_trough']
        new_row['trend_5m'] = row['trend_5m']
        new_row['trend_1h'] = row['trend_1h']
        new_row['with_5m_trend'] = row['with_5m_trend']
        new_row['with_1h_trend'] = row['with_1h_trend']
        new_row['stop_pips'] = row['stop_pips']
        new_row['stop_price'] = row['stop_price']
        new_row['stop_comments'] = row['stop_comments']                                                        
        new_row['take_profit_pips'] = row['take_profit_pips']
        new_row['take_profit_price'] = row['take_profit_price']                            
        new_row['take_profit_comments'] = row['take_profit_comments']
        new_row['move_breakeven'] = row['move_breakeven']
        new_row['result_pips'] = row['result_pips']
        new_row['spread_pips'] = row['spread_pips']     
        new_row['max_pips_profit'] = row['max_pips_profit']
        new_row['void_trade_high'] = row['void_trade_high']
        new_row['void_trade_low'] = row['void_trade_low']
        new_row['rolling_high'] = row['rolling_high']
        new_row['rolling_low'] = row['rolling_low']
        
        return new_row



    def write_breakout_log(self, event_log, symbol, breakout_time, stratdir):
        #for the moment just write to a log file

        fieldnames = ['event_time_mt4', 'event_details', "event_type", "event_price","event_chart"]
        
        blank_row =  {"event_time_mt4": None,
                    "event_details": None,
                    "event_type": None,
                    "event_price": None,
                    "event_chart": None}
        rows = []
        
        if not self.LiveMode:

            path = os.path.join(Globals.DataFolder, f"{breakout_time}_{symbol}_{stratdir}.csv")

            for row in event_log:
                new_row = blank_row.copy()
                new_row['event_time_mt4'] = row['event_time_mt4']
                new_row['event_details'] = row['event_details']
                new_row['event_type'] = row['event_type']
                new_row['event_price'] = row['event_price']
                new_row['event_chart'] = row['event_chart']
                rows.append(new_row)

            # FOR LIVE - SEARCH and REPLACE with poopwith open('your_file.txt', 'w') as f:            
            with open(path, 'w', encoding='UTF8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        else:
            #print each line in eventlog
            table_message = "<table>"
            table_message += "<tr><th style='text-align:left'>Chart</th><th style='text-align:left'>Event</th><th style='text-align:left'>Description</th><th style='text-align:left'>Price</th><th style='text-align:left'>Time</th></tr>"
            for line in event_log:
                table_message += "<tr>"
                for key, value in line.items():
                    table_message += "<td> " + str(value) + " </td>"
                table_message += "</tr>"
            table_message += "</table>"

            #print(table_message)
            #print(event_log)

            #email_time = datetime.strftime(breakout_time, "%d.%m.%y %H:%M")     
            logsub = f"Event Log Result: {symbol} {stratdir} @ {breakout_time}"        
            if self.CountEmails < 480 and self.LiveMode:
                self.CountEmails += 1
                self.Notify.Email(self.EmailAddress, f"{logsub} | {self.ModeName}", table_message)



