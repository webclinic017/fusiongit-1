#region imports
from AlgorithmImports import *

''' <summary>
 This is the Session_Boxes class needed for storing info on the various trading sessions we want to track
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
from copy import deepcopy
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
#from symbolinfo import *
from dataclasses import dataclass
#endregion


# Define a class for tracking sessions -- these will then be added to a list to ensure we can keep a series, update averages etc
class session_box(object):
    def __init__(self, name) -> None:
        self.name = name
        self.start_time = None
        self.end_time = None
        self.high_bid = 0.0
        self.high_ask = 0.0
        self.high_time = None
        self.low_bid = 0.0
        self.low_ask = 0.0
        self.low_time = None
        self.pip_size = 0.0
        self.pips_height = 0.0
        self.pips_average = 0.0
        self.pips_up = 0.0
        self.pips_down = 0.0
        self.open_bid = 0.0
        self.close_bid = 0.0
        self.open_ask = 0.0
        self.close_ask = 0.0
        self.session_active = False
        self.session_bar = 1            # this is the number of 15min bars we have seen - starts at 1 - should end at 12.
        self.session = SessionNames.Unknown

    # set the session ID to one of the 5 possible sessions or Unknown
    def start_session(self, session, bid_now, ask_now, time_now, pip_size, prior_averages=0.0):
        if session in SessionNames:
            self.session = session
            self.pip_size = pip_size
            self.start_time = time_now
            self.high_bid = bid_now
            self.high_ask = ask_now
            self.high_time = time_now
            self.low_bid = bid_now
            self.low_ask = ask_now
            self.low_time = time_now
            self.open_ask = ask_now
            self.open_bid = bid_now
            self.pips_average = prior_averages
            self.session_active = True
            return True
        else:
            return False

    def end_session(self, bid_now, ask_now, time_now):
        if self.session_active:
            self.end_time = time_now
            self.close_bid = bid_now
            self.close_ask = ask_now
            self.session_active = False
            
            # set the pip height
            self.pips_height = round((self.high_bid - self.low_bid) / self.pip_size, 2)
            # set the pip amount dropped from start
            self.pips_down = round((self.open_bid - self.low_bid) / self.pip_size, 2)
            # set the pip amount gained from start
            self.pips_up = round((self.high_bid - self.open_bid) / self.pip_size, 2)
            return True
        else:
            return False

    # update session highs and lows and keep track of the total pips that have so far been seen - this will be used to compare vs averages
    def update_sessions(self, ask_price_low, ask_price_high, bid_price_low, bid_price_high, time_now):
        if self.session_active:
            if ask_price_high > self.high_ask:
                self.high_ask = ask_price_high
            if ask_price_low < self.low_ask:
                self.low_ask = ask_price_low
            if bid_price_low < self.low_bid:
                self.low_bid = bid_price_low
                self.low_time = time_now
            if bid_price_high > self.high_bid:
                self.high_bid = bid_price_high
                self.high_time = time_now
            
            # set the pip height
            self.pips_height = round((self.high_bid - self.low_bid) / self.pip_size, 2)
            # set the pip amount dropped from start
            self.pips_down = round((self.open_bid - self.low_bid) / self.pip_size, 2)
            # set the pip amount gained from start
            self.pips_up = round((self.high_bid - self.open_bid) / self.pip_size, 2)

            # set the session bar we are now on
            fifteen_minutes = timedelta(minutes=15)
            self.session_bar = math.floor((time_now - self.start_time) / fifteen_minutes)

            return True
        else:
            return False

    # return the bar when the session low was set
    def get_session_low_bar(self):
        fifteen_minutes = timedelta(minutes=15)
        return math.floor((self.low_time - self.start_time) / fifteen_minutes)

    # return the bar when the session high was set
    def get_session_high_bar(self):
        fifteen_minutes = timedelta(minutes=15)
        return math.floor((self.high_time - self.start_time) / fifteen_minutes)


    # output information about the sessions as needed
    def dump_session(self):
        h_pips = self.pips_height
        h_pips_up = self.pips_up
        h_pips_down = self.pips_down
        h_high = self.high_bid
        h_low = self.low_bid
        h_start = self.start_time
        h_active = self.session_active
        h_bar = self.session_bar
        h_avg = self.pips_average
        output = (f"{self.name} session_box: Hi: {h_high} Lo: {h_low} Pips: {h_pips} PipsUp: {h_pips_up} PipsDown: {h_pips_down} StartTime: {h_start} Active: {h_active} Bar: {h_bar} Avg: {h_avg}")
        return output


class session_box_library(object):
    def __init__(self, name, history_length=20):
        self.name = name
        self.history_length = history_length        # keep this many of each kind of session, to help with averaging
        self.session_history = []
        self.session_averages = {SessionNames.Pre_Asia:    0.0, 
                            SessionNames.Asia:             0.0, 
                            SessionNames.Europe:           0.0,
                            SessionNames.Pre_US:           0.0,
                            SessionNames.US:               0.0}


    def add_completed_session(self, my_session):
         # first add the completed session to the list
         self.session_history.append(deepcopy(my_session)) 
         # now work out if we have too many and delete the front one if we do
         if len(self.session_history) > self.history_length * len(self.session_averages.keys()):
            self.session_history.pop(0)
         # once we have the list clean, work out the average pip moves for each kind of session
         for key, session_avg in self.session_averages.items():
            count = 0
            total = 0.0
            for session in self.session_history:
                if session.session == key:
                    count += 1
                    total += session.pips_height
            if count > 0:
                self.session_averages[key] = round(total / count, 2)

    def get_averages(self, session_name):
        return self.session_averages[session_name]


    def dump_session_history(self, sender):
        for t in self.session_history:
            sender.Log(t.dump_session())
