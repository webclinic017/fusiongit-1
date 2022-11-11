#region imports
from AlgorithmImports import *

''' <summary>
 This is the utility class for the fusion algorithm.
'''
from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Indicators")

import enum
import math
import pytz 
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
#endregion


# this is a utility class for the fusion algorithm
class fusion_utils(object):
    #no init for the moment

    #pass the algorithm date and determine the trading window. A trading window is a time period during which the strategy is allowed to trade (if relevant to that strategy).
    @staticmethod
    def get_trading_window(passed_datetime):
        # modified these times so that TW1 will end at 23:00, any time from 20:00 until 22:59 should pass this test
        # modfied TW2 to end at 05:00, any time from 02:00 until 04:59 should pass this test
        # modified TW3 to end at 11:00, any time from 08:00 until 10:59 should pass this test        
        if passed_datetime.hour >= 20 and passed_datetime.hour < 23:
            return TradingWindow.TW1
        elif passed_datetime.hour >= 2 and passed_datetime.hour < 5:
            return TradingWindow.TW2
        elif passed_datetime.hour >= 8 and passed_datetime.hour < 11:
            return TradingWindow.TW3
        else:
            return TradingWindow.Closed

    # return the amount of time until the end of the trading window
    @staticmethod
    def get_time_until_end_of_trading_window(passed_datetime, trading_window):
        # Need to ensure that trading_window is the TradingWindow enum that the passed_datetime is actually in. 
        # Or None will be returned
        new_date = None
        if trading_window == TradingWindow.TW1:
            # TW1 ends at 23:00
            new_date = passed_datetime.replace(hour=23, minute=0, second=0, microsecond=0)
            return  new_date - passed_datetime
        elif trading_window == TradingWindow.TW2:
            # TW2 ends at 05:00
            new_date = passed_datetime.replace(hour=5, minute=0, second=0, microsecond=0)
            return  new_date - passed_datetime
        elif trading_window == TradingWindow.TW3:
            # TW3 ends at 11:00
            new_date = passed_datetime.replace(hour=11, minute=0, second=0, microsecond=0)
            return new_date - passed_datetime
        else:
            # TODO: fix this to raise an exception instead of returning None
            return None

    #check whether time is within 5 minutes of US equities start(9:30am EST)
    @staticmethod
    def is_time_within_5_minutes_of_US_equities_start(passed_datetime):
        us_equities_open_time = datetime(passed_datetime.year, passed_datetime.month, passed_datetime.day, 9, 30, 0, 0) 
        if (us_equities_open_time > passed_datetime and us_equities_open_time - passed_datetime < timedelta(minutes=5)) or \
            (us_equities_open_time < passed_datetime and passed_datetime - us_equities_open_time < timedelta(minutes=5)):
            return True
        else:
            return False        

    #return absolute difference in pips between two prices 
    @staticmethod
    def get_difference_in_pips(price1, price2, pipsize):
        pip_difference = abs(round((price1 - price2) /pipsize,1))
        return  pip_difference

    #return price depending on direction and type of order
    @staticmethod
    def get_me_the_correct_prices(bidpricenow, askpricenow, pipsize, direction, stop_pips, profit_pips):
        if direction == "LONG":
            stop_price = bidpricenow - (stop_pips * pipsize)
            profit_price = askpricenow + (profit_pips * pipsize)
            return (stop_price, profit_price)
        else:
            stop_price = askpricenow + (stop_pips * pipsize)
            profit_price = bidpricenow - (profit_pips * pipsize)
            return (stop_price, profit_price)            

    #format datetime string for parsing using MQL code    
    @staticmethod
    def format_datetime_using_string(passed_datetime, string_format="%Y.%m.%d %H:%M"):
        if passed_datetime != None:
            return passed_datetime.strftime(string_format)
        else:
            return ""

    #pass the timezone and date and determine if that is in dst
    @staticmethod
    def check_dst(passed_datetime):
        return passed_datetime.dst() != timedelta(0)

    #function to return times in all tracked zones given a time in a passed zone
    @staticmethod
    def get_times(passed_datetime, passed_tz):
        #SI notes - this works by returning a disctionary of times in all zones based on the passed time and the timezone
        #passed_tz can is one of the shortcodes listed in timezone_list
        timezone_list = {"us": 'US/Eastern', "mt4": 'EET', "uk": 'Europe/London', "perth": 'Australia/Perth'}   #could be added to init or algo?
        times = {}
     

        #check is passed_datetime is localised
        if passed_datetime.tzinfo != None: 
            passed_datetime = passed_datetime.replace(tzinfo=None)
 
        tz = pytz.timezone(timezone_list[passed_tz])
        passed_datetime = tz.localize(passed_datetime)
        times[passed_tz] = passed_datetime.astimezone(pytz.timezone(timezone_list[passed_tz]))


        dst = fusion_utils.check_dst(passed_datetime)

        for key, value in timezone_list.items():
            if key != passed_tz:
                tz = pytz.timezone(value)
                new_datetime = passed_datetime.astimezone(tz)
                if fusion_utils.check_dst(new_datetime) != dst:
                    new_datetime += timedelta(hours=1)
                times[key] = new_datetime
                #print(str(times[key]) + " " + key)
    
        return times

    #function to return a string for each member of the EHELTrends enum
    @staticmethod
    def get_ehel_trend_string(passed_trend):
        if passed_trend == EHELTrends.Uptrend:
            return "Uptrend"
        elif passed_trend == EHELTrends.Downtrend:
            return "Downtrend"
        elif passed_trend == EHELTrends.Transition:
            return "Transition"
        elif passed_trend == EHELTrends.Unknown:
            return "Unknown"
        else:
            return "Error"


    #function to return the old Trend format for a given EHELTrends value
    @staticmethod
    def get_trend_from_eheltrend(passed_trend):
        if passed_trend == EHELTrends.Uptrend:
            return Trends.Uptrend
        elif passed_trend == EHELTrends.Downtrend:
            return Trends.Downtrend
        elif passed_trend == EHELTrends.Transition:
            return Trends.Nothing
        elif passed_trend == EHELTrends.Unknown:
            return Trends.Nothing
        else:
            return Trends.Nothing

    #function to return timeoffset for candle open times
    @staticmethod
    def get_candle_open_time(time, chart_res):
        if chart_res == ChartRes.res1M:
            time_offset = timedelta(minutes=1)        
        if chart_res == ChartRes.res5M:
            time_offset = timedelta(minutes=5)
        if chart_res == ChartRes.res15M:
            time_offset = timedelta(minutes=15)
        if chart_res == ChartRes.res30M:
            time_offset = timedelta(minutes=30)
        if chart_res == ChartRes.res1H:
            time_offset = timedelta(hours=1)    
        if chart_res == ChartRes.res4H:
            time_offset = timedelta(hours=4)
        if chart_res == ChartRes.res24H: 
            time_offset = timedelta(hours=24)   
        if chart_res == None: 
            time_offset = timedelta(seconds=1)  
        return (time - time_offset)

