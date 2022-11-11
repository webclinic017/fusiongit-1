#region imports
from AlgorithmImports import *

''' <summary>
 This is the TurningPoints class needed for storing info on Peaks and Troughs etc
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
from symbolinfo import *
from dataclasses import dataclass
#endregion


class price_tracker(object):
    def __init__(self, symbol, start_time, start_price, direction_call, pips_to_correct, time_to_track, tracking_source, points, pip_size):
        self.symbol = symbol
        self.active = True
        self.start_time = start_time
        self.end_time = start_time + time_to_track
       
        self.start_price = start_price
        self.end_price = 0.0
        self.min_price = start_price
        self.max_price = start_price
        self.direction_call = direction_call
        self.pips_to_correct = pips_to_correct
        if direction_call == 'LONG':
            self.price_mult = 1.0
        else:
            self.price_mult = -1.0
        self.tracking_source = tracking_source
        self.points_to_record = points
        self.pip_size = pip_size
        self.pips_up = round((self.max_price - self.start_price) / self.pip_size, 2)
        self.pips_down = round((self.start_price - self.min_price) / self.pip_size, 2)
        self.trail_levels = [10 * self.price_mult, 15 * self.price_mult, 20 * self.price_mult, 25 * self.price_mult, 30 * self.price_mult, 40 * self.price_mult]
        self.trail_breached = [False, False, False, False, False, False]
        self.trail_price_ratchets = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.trail_pips_reached = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.called_correct = False
        self.called_pips = 0.0

        for i in range(0, len(self.trail_levels)):
            # setup the starting prices for each of the pip_levels back from this price.  LONG and SHORT sorted by the price_mult used
            self.trail_price_ratchets[i] = self.start_price - (self.trail_levels[i] * self.pip_size )


    def update_tracker(self, symbol, price_now, time_now):
        # if we are still in time window - update prices
        new_minimum = False
        new_maximum = False
        if price_now > self.max_price:
            self.max_price = price_now  
            if self.price_mult == 1.0:
                new_maximum = True
        if price_now < self.min_price:
            self.min_price = price_now
            if self.price_mult == -1.0:
                new_minimum = True
        if time_now > self.end_time:
            self.end_price = price_now
            self.active = False
        self.pips_up = round((self.max_price - self.start_price) / self.pip_size, 2)
        self.pips_down = round((self.start_price - self.min_price) / self.pip_size, 2)
        # now update the ratchet trailing prices and pips before checking if we breached by slipping back
        for i in range(0, len(self.trail_levels)):
            if self.price_mult == 1.0:
                # LONG checks
                temp_ratchet = price_now - (self.trail_levels[i] * self.pip_size )
                if temp_ratchet > self.trail_price_ratchets[i]:
                    self.trail_price_ratchets[i] = temp_ratchet
                if not self.trail_breached[i] and (new_maximum or new_minimum):
                    # calculate how many pips we've got to in the correct Direction if we've seen a new maximum price    
                    price_diff = self.max_price - self.start_price 
                    if round(price_diff / self.pip_size, 2) >= self.pips_to_correct and i == 1 and not self.trail_breached[1] and not self.called_correct == True:      # TODO: Generalise - not just Pos 1
                        self.called_correct = True
                        self.called_pips = round(price_diff / self.pip_size, 2)
                    self.trail_pips_reached[i] = round(price_diff / self.pip_size - self.trail_levels[i], 2)                     
                if price_now < self.trail_price_ratchets[i] and not self.trail_breached[i] :
                    # we have slipped back                   
                    self.trail_breached[i] = True
            else:
                # SHORT checks
                temp_ratchet = price_now - (self.trail_levels[i] * self.pip_size )  # remember this is -1.0 for SHORT
                if temp_ratchet < self.trail_price_ratchets[i]:
                    self.trail_price_ratchets[i] = temp_ratchet
                if not self.trail_breached[i] and (new_minimum or new_maximum):
                    # calculate how many pips we've got to in the correct Direction if we've seen a new minimum price
                    price_diff = self.start_price - self.min_price
                    if round(price_diff / self.pip_size, 2) >= self.pips_to_correct and i == 1 and not self.trail_breached[1] and not self.called_correct == True:      # TODO: Generalise - not just Pos 1
                        self.called_correct = True
                        self.called_pips = round(price_diff / self.pip_size, 2)
                    self.trail_pips_reached[i] = round(price_diff / self.pip_size + self.trail_levels[i], 2 )                     
                if price_now > self.trail_price_ratchets[i] and not self.trail_breached[i] :
                    # we have slipped back, so we can't claim any more wins above this breach
                    self.trail_breached[i] = True



    def dump_tracker(self):
        s = self.symbol
        s_t = self.start_time
        e_t = self.end_time
        p_s = self.start_price
        p_e = self.end_price
        p_max = self.max_price
        p_min = self.min_price
        p_u = self.pips_up
        p_d = self.pips_down
        d = self.direction_call
        trk_src = self.tracking_source
        t_0 = self.trail_breached[0]
        t_1 = self.trail_breached[1]
        t_2 = self.trail_breached[2]
        t_3 = self.trail_breached[3]
        t_4 = self.trail_breached[4]
        t_5 = self.trail_breached[5]
        p_0 = self.trail_pips_reached[0]
        p_1 = self.trail_pips_reached[1]
        p_2 = self.trail_pips_reached[2]
        p_3 = self.trail_pips_reached[3]
        p_4 = self.trail_pips_reached[4]
        p_5 = self.trail_pips_reached[5]
        call_c = self.called_correct
        call_p = self.called_pips
        
        output = f"{s} Source: {trk_src} Start: {s_t} End: {e_t} Price: {p_s} End: {p_e} UpPips: {p_u} DownPips: {p_d} Called: {d} B0: {t_0} B1: {t_1} B2: {t_2} B3: {t_3} B4: {t_4} B5: {t_5} P0: {p_0} P1: {p_1} P2: {p_2} P3: {p_3} P4: {p_4} P5: {p_5} Called: {call_c} Profit: {call_p}"

        return output
        


class price_tracker_library(object):
    def __init__(self, name):
        self.name = name
        self.trackers = []
        self.trackers_done = []


    def add_tracker(self, symbol, start_time, start_price, direction_call, pips_to_correct, time_to_track, tracking_source, points, pip_size):
        self.trackers.append(price_tracker(symbol, start_time, start_price, direction_call, pips_to_correct, time_to_track, tracking_source, points, pip_size)) 


    def update_trackers(self, sender, symbol, price_now, time_now):
        items_to_clear = []
        for index, t in enumerate(self.trackers):
            if t.symbol == symbol and t.active == True:
                t.update_tracker(symbol, price_now, time_now)
            if not t.active:
                # this tracker has now run out of time, so append it to the trackers_done list
                self.trackers_done.append(t)
                # store the index of the tracker to clear from the live trackers list
                items_to_clear.append(index)
        # make sure larger indexes come first
        items_to_clear.reverse()
        for i in items_to_clear:
            del self.trackers[i]
            #sender.Log(f"{symbol} clearing completed price tracker - count of completed {len(self.trackers_done)}")        


    def dump_tracker_state(self, sender):
        for t in self.trackers_done:
            sender.Log(t.dump_tracker())

