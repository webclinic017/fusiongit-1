#region imports
from pickletools import UP_TO_NEWLINE
from AlgorithmImports import *

''' <summary>
 This is the External_Structure class needed for storing info on the various EH's and EL's we need to track
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
from fusion_utils import *
#endregion


# Define a class for tracking sessions -- these will then be added to a list to ensure we can keep a series, update averages etc
class external_structure(object):
    def __init__(self, name) -> None:
        self.name = name
        self.history_length = 1000
        
        self.EH_current_price = 0.0
        self.EH_current_time = None
        self.EH_move_type = None            # pull or expand
        self.EH_potential_price = 0.0
        self.EH_potential_time = None
        self.EH_highest_for_pull_price = 0.0
        self.EH_highest_for_pull_time = None
        self.EH_highest_for_pull_price_alt = 0.0
        self.EH_highest_for_pull_time_alt = None
        self.EH_pull_used = False
        self.EH_count = 0
        
        self.EL_current_price = 0.0
        self.EL_current_time = None
        self.EL_move_type = None            # pull or expand
        self.EL_potential_price = 0.0
        self.EL_potential_time = None
        self.EL_lowest_for_pull_price = 0.0
        self.EL_lowest_for_pull_time = None
        self.EL_lowest_for_pull_price_alt = 0.0
        self.EL_lowest_for_pull_time_alt = None
        self.EL_pull_used = False
        self.EL_count = 0

        self.pair_count = 1             # how many pairs are we tracking - used to match EH's to EL's
        self.last_found = "None"        # what did we find last - peak or trough - used for matching EH's to EL's
        self.tick_tock = 0
        
        self.last_peak_price = 0.0  
        self.last_trough_price = 0.0   

        self.current_template = EHELTrends.Unknown

        self.EH_EL_store = {"time": None,
                            "price": None,
                            "EH_or_EL": None,
                            "label": None,
                            "pips_height" : None,
                            "move_type" : None,
                            "last_peak_price" : None,
                            "last_trough_price" : None
                            }   

        self.peak_trough_store = {"time": None,
                            "price": None,
                            "peak_or_trough": None
                            }                               

        self.EH_EL_library = []
        self.peak_trough_history_length = 1000

        self.peak_trough_library = []

        self.pip_size = 0.0
        self.pips_height = 0.0
        

    # we have had a peak or a trough form, so now work out whether we have to consider it for new EH or EL
    def process_update(self, bid_formed, time_formed, high_or_low_point, peak_or_trough, pip_size):
        
        self.pip_size = pip_size

        if peak_or_trough != "peak" and peak_or_trough != "trough":
            # incorrect call to process_update
            return False

        #Si update the lastpeak and lasttrough prices in the library 
        # this would work for a peak and trough formed at the same time as we call the function twice; once for each
        if peak_or_trough == "peak":
            self.last_peak_price = bid_formed
            self.store_peak(bid_formed, time_formed)
        if peak_or_trough == "trough":
            self.last_trough_price = bid_formed
            self.store_trough(bid_formed, time_formed)


        if peak_or_trough == "peak" and self.EH_current_time == None:
            # this is the first peak, so set it regardless unless first Trough is set and is higher than this peak
            if self.EL_current_price != 0.0 and self.EL_current_price < bid_formed or self.EL_current_time == None:
                # make sure we don't accidentally set an EH below first EL
                self.EH_current_price = bid_formed
                self.EH_current_time = time_formed
                self.EH_move_type = "init"
                self.last_found = "peak"
                self.store_EH()
                self.check_template(broke_price=False, price_direction="None")          # this works out what trend we are in
            elif self.EL_current_price != 0.0 and self.EL_current_price >= bid_formed:
                # ignore this peak as it is below first EL

                return False 
            if self.EH_current_price != 0.0 and self.EL_current_price != 0.0:
                self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
            return True

        if peak_or_trough == "trough" and self.EL_current_time == None:
            # this is the first trough, so set it regardless unless first Peak is set and is higher than this peak
            if self.EH_current_price != 0.0 and self.EH_current_price > bid_formed or self.EH_current_time == None:
                # make sure we don't accidentally set an EL above first EH
                self.EL_current_price = bid_formed
                self.EL_current_time = time_formed
                self.EL_move_type = "init"
                self.last_found = "trough"
                self.store_EL()
                self.check_template(broke_price=False, price_direction="None")      # this works out what trend we are in
            elif self.EH_current_price != 0.0 and self.EH_current_price <= bid_formed:
                # ignore this trough as it is above first EH
                return False
            if self.EH_current_price != 0.0 and self.EL_current_price != 0.0:
                self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
            return True

        # now check if both initial EH and EL are set 
        # if so, we want to only store POSSIBLE new EH or EL values.  It is only the 'pull' that confirms them
        if peak_or_trough == "peak" and self.EL_current_time != None and self.EH_current_time != None:
            # check if we have a pair of peaks and troughs in between this one that we need to promote
            if self.EH_highest_for_pull_time != None and self.EL_lowest_for_pull_time != None and self.last_found == "trough" and \
             bid_formed > self.EH_highest_for_pull_price:
                # we have a pair of peaks and troughs in between this one that we need to promote
                self.EH_current_price = self.EH_highest_for_pull_price
                self.EH_current_time = self.EH_highest_for_pull_time
                self.EH_move_type = f"infill ALTP: {self.EL_lowest_for_pull_price_alt}"
                self.last_found = "peak"
                self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                self.store_EH()
                
                
                if self.EL_lowest_for_pull_time < self.EH_highest_for_pull_time and self.EL_lowest_for_pull_time_alt != None:
                    # we have the alternate trough to use
                    self.EL_current_price = self.EL_lowest_for_pull_price_alt
                    self.EL_current_time = self.EL_lowest_for_pull_time_alt
                    self.EL_lowest_for_pull_price_alt = 0.0
                    self.EL_lowest_for_pull_time_alt = None
                    self.EL_move_type = "infill from Alt"
                else:
                    self.EL_current_price = self.EL_lowest_for_pull_price
                    self.EL_current_time = self.EL_lowest_for_pull_time
                    self.EL_move_type = "infill"
                    
                self.last_found = "trough"
                self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                self.store_EL()
                self.check_template(broke_price=False, price_direction="None")      # this works out what trend we are in
                self.EH_highest_for_pull_price = 0.0
                self.EH_highest_for_pull_time = None
                self.EH_pull_used = False           
                self.EL_lowest_for_pull_price = 0.0
                self.EL_lowest_for_pull_time = None
                self.EL_pull_used = False           # once a Lower price is found, and does a pull we don't want to repeat until a new EL formed
            # now we know we have at least got 1 EH and 1 EL
            if self.EH_highest_for_pull_time == None:
                # this is the first trough we have found since the last EH
                self.EH_highest_for_pull_price = bid_formed
                self.EH_highest_for_pull_time = time_formed
            else:
                # we have already found a peak, so check if this one is higher
                if bid_formed > self.EH_highest_for_pull_price:
                    self.EH_highest_for_pull_price = bid_formed
                    self.EH_highest_for_pull_time = time_formed
            # set the alternate highest following peak, which needs to come AFTER the trough we might have found

            # deal with alternates
            if self.EL_lowest_for_pull_time != None and self.EH_highest_for_pull_time != None and self.EH_highest_for_pull_time < self.EL_lowest_for_pull_time:
                # we know we might need to store and alternate peak - but only set it up initially
                if self.EH_highest_for_pull_time_alt == None:
                    # this is the first trough we have found since the last EH
                    self.EH_highest_for_pull_price_alt = bid_formed
                    self.EH_highest_for_pull_time_alt = time_formed
            if self.EH_highest_for_pull_time_alt != None:
                # we have already found an alternate peak, so check if this one is higher as we may need to use it
                if bid_formed > self.EH_highest_for_pull_price_alt:
                    self.EH_highest_for_pull_price_alt = bid_formed
                    self.EH_highest_for_pull_time_alt = time_formed
                if self.EL_lowest_for_pull_time != None:
                    if self.EH_highest_for_pull_time_alt < self.EL_lowest_for_pull_time:
                        self.EH_highest_for_pull_price_alt = bid_formed
                        self.EH_highest_for_pull_time_alt = time_formed
            
            # now just check to see if we have a doublebreak
            if self.EL_lowest_for_pull_time != None and self.last_found == "peak":
                if (high_or_low_point < self.EL_lowest_for_pull_price) :
                    # this means we need to store the potential EL we found, as we now will probably also set the EH
                    self.EL_current_price = self.EL_lowest_for_pull_price
                    self.EL_current_time = self.EL_lowest_for_pull_time
                    self.EL_move_type = "doublebreak"
                    self.last_found = "trough"
                    self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                    self.store_EL()
                    self.check_template(broke_price=False, price_direction="None")      # this works out what trend we are in
                    # since we have a new EH, we need to reset the possible lowest EH
                    self.EH_highest_for_pull_price = 0.0
                    self.EH_highest_for_pull_time = None
                    self.EH_pull_used = False           
            # do not immediately store this peak as we need to confirm first by a price going down through existing EL
            if (high_or_low_point < self.EL_current_price) and self.last_found == "trough":
                # this new peak BROKE price of the EL, so we can set it as a new EH
                self.EH_current_price = bid_formed
                self.EH_current_time = time_formed
                self.EH_move_type = "pricebreak"
                self.last_found = "peak"
                self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                self.store_EH()
                self.check_template(broke_price=False, price_direction="None")      # this works out what trend we are in
                # since we have a new EH, we need to reset the possible lowest EL we've been tracking to use at a pull up
                self.EL_lowest_for_pull_price = 0.0
                self.EL_lowest_for_pull_time = None
                self.EL_pull_used = False           # once a Lower price is found, and does a pull we don't want to repeat until a new EL formed
                return True

        if peak_or_trough == "trough" and self.EL_current_time != None and self.EH_current_time != None:
            # check if we have a pair of peaks and troughs in between this one that we need to promote
            if self.EH_highest_for_pull_time != None and self.EL_lowest_for_pull_time != None and self.last_found == "peak" and bid_formed < self.EL_lowest_for_pull_price:
                # we have a pair of peaks and troughs in between this one that we need to promote
                self.EL_current_price = self.EL_lowest_for_pull_price
                self.EL_current_time = self.EL_lowest_for_pull_time
                self.EL_move_type = f"infill ALTP: {self.EH_highest_for_pull_price_alt}"
                self.last_found = "trough"
                self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                self.store_EL()
                
                # new bit below
                if self.EH_highest_for_pull_time < self.EL_lowest_for_pull_time and self.EH_highest_for_pull_time_alt != None:
                    # we have the alternate peak to use
                    self.EH_current_price = self.EH_highest_for_pull_price_alt
                    self.EH_current_time = self.EH_highest_for_pull_time_alt
                    self.EH_highest_for_pull_price_alt = 0.0
                    self.EH_highest_for_pull_time_alt = None
                    self.EH_move_type = "infill from Alt"
                else:
                    # new bit above
                    self.EH_current_price = self.EH_highest_for_pull_price
                    self.EH_current_time = self.EH_highest_for_pull_time
                    self.EH_move_type = "infill"
                
                self.last_found = "peak"
                self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                self.store_EH()
                self.check_template(broke_price=False, price_direction="None")      # this works out what trend we are in
                self.EH_highest_for_pull_price = 0.0
                self.EH_highest_for_pull_time = None
                self.EH_pull_used = False           
                self.EL_lowest_for_pull_price = 0.0
                self.EL_lowest_for_pull_time = None
                self.EL_pull_used = False           # once a Lower price is found, and does a pull we don't want to repeat until a new EL formed
            # now we know we have at least got 1 EH and 1 EL
            if self.EL_lowest_for_pull_time == None:
                # this is the first trough we have found since the last EH
                self.EL_lowest_for_pull_price = bid_formed
                self.EL_lowest_for_pull_time = time_formed
            else:
                if bid_formed < self.EL_lowest_for_pull_price:
                    # this is a lower trough, so accept it
                    self.EL_lowest_for_pull_price = bid_formed
                    self.EL_lowest_for_pull_time = time_formed
            
            # deal with alternates
            if self.EH_highest_for_pull_time != None and self.EL_lowest_for_pull_time != None and self.EL_lowest_for_pull_time < self.EH_highest_for_pull_time:
                # we know we might need to store and alternate trough - but only set it up initially
                if self.EL_lowest_for_pull_time_alt == None:
                    # this is the first since we have found since the last EL
                    self.EL_lowest_for_pull_price_alt = bid_formed
                    self.EL_lowest_for_pull_time_alt = time_formed
            if self.EL_lowest_for_pull_time_alt != None:
                # we have already found an alternate trough, so check if this one is lower as we may need to use it
                if bid_formed < self.EL_lowest_for_pull_price_alt:
                    self.EL_lowest_for_pull_price_alt = bid_formed
                    self.EL_lowest_for_pull_time_alt = time_formed
                if self.EH_highest_for_pull_time != None:
                    if self.EL_lowest_for_pull_time_alt < self.EH_highest_for_pull_time:
                        self.EL_lowest_for_pull_price_alt = bid_formed
                        self.EL_lowest_for_pull_time_alt = time_formed

            # now just check to see if we have a doublebreak
            if self.EH_highest_for_pull_time != None and self.last_found == "trough":
                if (high_or_low_point > self.EH_highest_for_pull_price) :
                    # this means we need to store the potential EH we found, as we now will probably also set the EL
                    self.EH_current_price = self.EH_highest_for_pull_price
                    self.EH_current_time = self.EH_highest_for_pull_time
                    self.EH_move_type = "doublebreak"
                    self.last_found = "peak"
                    self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                    self.store_EH()
                    self.check_template(broke_price=False, price_direction="None")      # this works out what trend we are in
                    # since we have a new EH, we need to reset the possible lowest EH
                    self.EL_lowest_for_pull_price = 0.0
                    self.EL_lowest_for_pull_time = None
                    self.EL_pull_used = False           
            # do not immediately store this trough as we need to confirm first by a price going up through existing EH
            if (high_or_low_point > self.EH_current_price) and self.last_found == "peak":
                # this new trough BROKE price of the EH, so we can set it as a new EL
                self.EL_current_price = bid_formed
                self.EL_current_time = time_formed
                self.EL_move_type = "pricebreak"
                self.last_found = "trough"
                self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                self.store_EL()
                self.check_template(broke_price=False, price_direction="None")      # this works out what trend we are in
                # since we have a new EL, we need to reset the possible highest EH we've been tracking to use at a pull down
                self.EH_highest_for_pull_price = 0.0
                self.EH_highest_for_pull_time = None
                self.EH_pull_used = False               # once a Lower price is found, and does a pull we don't want to repeat until a new EL formed
                return True
            
        return False
    

    # this is where the PULL confirmation happens - if price broke through a level then see if we confirm a new pair of EH/EL
    def check_price_broke_levels(self, up_or_down, bid_now):
        if up_or_down not in [RED, GREEN]:
            # incorrect call to check_price_broke_levels
            return False
        
        if self.last_found == "trough":     # we are looking to see if we confirm a new EH
            # check if price is below EL first 
            if bid_now < self.EL_current_price and self.EL_current_time != None and up_or_down == RED:
                # we have a valid EL already, has price dropped below
                self.check_template(broke_price=True, price_direction="Down")

                if self.EH_highest_for_pull_time != None:   # and not self.EH_pull_used:
                    # we have stored a the highest EH we found since the last EL, so use it to set a new confirmed EH
                    self.EH_current_price = self.EH_highest_for_pull_price
                    self.EH_current_time = self.EH_highest_for_pull_time
                    self.EH_move_type = "pull"
                    self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                    self.last_found = "peak"
                    self.store_EH()
                    
                    self.EH_highest_for_pull_price = 0.0
                    self.EH_highest_for_pull_time = None
                    self.EH_highest_for_pull_price_alt = 0.0
                    self.EH_highest_for_pull_time_alt = None
                    self.EH_pull_used = True
                    return True

        if self.last_found == "peak":       # we are looking to see if we confirm a new EL
            # check if price is above EH first
            if bid_now > self.EH_current_price and self.EH_current_time != None and up_or_down == GREEN:
                # we have a valid EH already, has price risen above
                self.check_template(broke_price=True, price_direction="Up")

                if self.EL_lowest_for_pull_time != None:   # and not self.EL_pull_used:
                    # we have stored a the lowest EL we found since the last EH, so use it to set a new confirmed EL
                    self.EL_current_price = self.EL_lowest_for_pull_price
                    self.EL_current_time = self.EL_lowest_for_pull_time
                    self.EL_move_type = "pull"
                    self.pips_height = round((self.EH_current_price - self.EL_current_price) / self.pip_size, 2)
                    self.last_found = "trough"
                    self.store_EL()
                    
                    self.EL_lowest_for_pull_price = 0.0
                    self.EL_lowest_for_pull_time = None
                    self.EL_lowest_for_pull_price_alt = 0.0
                    self.EL_lowest_for_pull_time_alt = None
                    self.EL_pull_used = True
                    return True

        return False

    def check_template(self, broke_price, price_direction):
        EHs = []
        ELs = []

        #my_time = self.EH_EL_library[-1]["time"]
        
        # This section can be used to debug a specific date in the EH/EL stuff
        '''date_time_str = '07/07/2022 16:00:00'
        date_time_obj = datetime.strptime(date_time_str, '%d/%m/%Y %H:%M:%S')
        if my_time == date_time_obj:
            my_hit = 1'''

        for pointer in reversed(self.EH_EL_library):
            # TODO: this is not efficient using a reverse of a whole list - speed up at some point
            if pointer["EH_or_EL"] == "EH":
                EHs.append(pointer["price"])
            if pointer["EH_or_EL"] == "EL":
                ELs.append(pointer["price"])

        # first check in the case that we've just formed a new EH or EL by a new peak or trough
        if len(EHs) >= 2 and len(ELs) >=2 and not broke_price:
            # we have enough to work out the template
            if EHs[0] > EHs[1] and ELs[0] > ELs[1]:
                self.current_template = EHELTrends.Uptrend
                # need to also update the last item in the library for logging
                self.EH_EL_library[-1]["template"] = fusion_utils.get_ehel_trend_string(EHELTrends.Uptrend)
            if EHs[0] < EHs[1] and ELs[0] < ELs[1]:
                self.current_template = EHELTrends.Downtrend
                # need to also update the last item in the library for logging
                self.EH_EL_library[-1]["template"] = fusion_utils.get_ehel_trend_string(EHELTrends.Downtrend)
        elif len(EHs) < 2 and len(ELs) < 2 and not broke_price:
            self.current_template = EHELTrends.Unknown
            # need to also update the last item in the library for logging
            self.EH_EL_library[-1]["template"] = fusion_utils.get_ehel_trend_string(EHELTrends.Unknown)
        
        # now check what happened if price just broke a level
        if len(EHs) >= 2 and len(ELs) >=2 and broke_price:
            # now we go into transition
            if price_direction == "Down" and self.current_template == EHELTrends.Uptrend:
                self.current_template = EHELTrends.Transition
            if price_direction == "Up" and self.current_template == EHELTrends.Downtrend:
                self.current_template = EHELTrends.Transition

    
    # find the EL in the library that has a lower price than the provided price_now
    def find_lower_EL_than_price(self, price_now):
        lowest_price = 0.0
        lowest_time = None
        for pointer in reversed(self.EH_EL_library):
            if pointer["EH_or_EL"] == "EL":
                if price_now >= pointer["price"]:
                    lowest_price = pointer["price"]
                    lowest_time = pointer["time"]
                    break
        return lowest_price, lowest_time


    # find the EH in the library that has a higher price than the provided price_now
    def find_higher_EH_than_price(self, price_now):
        highest_price = 0.0
        highest_time = None
        for pointer in reversed(self.EH_EL_library):
            if pointer["EH_or_EL"] == "EH":
                if price_now <= pointer["price"]:
                    highest_price = pointer["price"]
                    highest_time = pointer["time"]
                    break
        return highest_price, highest_time

    def find_higher_peak_than_price_and_time(self, price_now, time_now):
        peak_price = 0.0
        peak_time = None
        for entry in reversed(self.peak_trough_library):
           if entry["peak_or_trough"] == "Peak":
                #if entry["time"] < time_now:
                    if entry["price"] > price_now:
                        peak_price = entry["price"]
                        peak_time = entry["time"]
                        break
        return peak_price, peak_time

    def find_lower_trough_than_price_and_time(self, price_now, time_now):
        trough_price = 0.0
        trough_time = None
        for entry in reversed(self.peak_trough_library):
           if entry["peak_or_trough"] == "Trough":
                #if entry["time"] < time_now:
                    if entry["price"] < price_now:
                        trough_price = entry["price"]
                        trough_time = entry["time"]
                        break
        return trough_price, trough_time


    def store_EH(self):
        self.tick_tock += 1 
        if self.tick_tock >= 2:
            self.tick_tock = 0
            self.pair_count += 1
            if self.pair_count > 1000:
                self.pair_count = 1
        EH_label = "EH" + str(self.pair_count)

        # if we have more than the set number for the total history, start dropping ones off the front of the list
        if len(self.EH_EL_library) > self.history_length:
            self.EH_EL_library.pop(0)

        self.EH_EL_store["time"] = fusion_utils.get_times(self.EH_current_time, 'us')['mt4']  
        self.EH_EL_store["price"] = self.EH_current_price
        self.EH_EL_store["EH_or_EL"] = "EH"
        self.EH_EL_store["label"] = EH_label
        self.EH_EL_store["pips_height"] = self.pips_height
        self.EH_EL_store["move_type"] = self.EH_move_type
        self.EH_EL_store["template"] = fusion_utils.get_ehel_trend_string(self.current_template)
        self.EH_EL_store["last_peak_price"] = self.last_peak_price
        self.EH_EL_store["last_trough_price"] = self.last_trough_price

        # now add a COPY of this dictionary object to the list
        self.EH_EL_library.append(deepcopy(self.EH_EL_store))

    def store_EL(self):
        self.tick_tock += 1 
        if self.tick_tock >= 2:
            self.tick_tock = 0
            self.pair_count += 1
            if self.pair_count > 1000:
                self.pair_count = 1
        EL_label = "EL" + str(self.pair_count)

        # if we have more than the set number for the total history, start dropping ones off the front of the list
        if len(self.EH_EL_library) > self.history_length:
            self.EH_EL_library.pop(0)

        self.EH_EL_store["time"] = fusion_utils.get_times(self.EL_current_time, 'us')['mt4']
        self.EH_EL_store["price"] = self.EL_current_price
        self.EH_EL_store["EH_or_EL"] = "EL"
        self.EH_EL_store["label"] = EL_label
        self.EH_EL_store["pips_height"] = self.pips_height
        self.EH_EL_store["move_type"] = self.EL_move_type
        self.EH_EL_store["template"] = fusion_utils.get_ehel_trend_string(self.current_template)
        self.EH_EL_store["last_peak_price"] = self.last_peak_price
        self.EH_EL_store["last_trough_price"] = self.last_trough_price
        # now add a COPY of this dictionary object to the list
        self.EH_EL_library.append(deepcopy(self.EH_EL_store))


    def store_trough(self, bid_formed, time_formed):
        # if we have more than the set number for the total history, start dropping ones off the front of the list
        if len(self.peak_trough_library) > self.peak_trough_history_length:
            self.peak_trough_library.pop(0)

        self.peak_trough_store["time"] = fusion_utils.get_times(time_formed, 'us')['mt4']
        self.peak_trough_store["price"] = bid_formed
        self.peak_trough_store["peak_or_trough"] = "Trough"

        # now add a COPY of this dictionary object to the list
        self.peak_trough_library.append(deepcopy(self.peak_trough_store))


    def store_peak(self, bid_formed, time_formed):
        # if we have more than the set number for the total history, start dropping ones off the front of the list
        if len(self.peak_trough_library) > self.peak_trough_history_length:
            self.peak_trough_library.pop(0)

        self.peak_trough_store["time"] = fusion_utils.get_times(time_formed, 'us')['mt4']
        self.peak_trough_store["price"] = bid_formed
        self.peak_trough_store["peak_or_trough"] = "Peak"

        # now add a COPY of this dictionary object to the list
        self.peak_trough_library.append(deepcopy(self.peak_trough_store))



    def get_EH(self):
        return self.EH_current_price

    def get_EL(self):
        return self.EL_current_price

    def get_EH_EL_gap(self):
        return self.pips_height

    def get_last_peak_price(self):
        return self.last_peak_price

    def get_last_trough_price(self):
        return self.last_trough_price

    def get_template(self):
        return fusion_utils.get_ehel_trend_string(self.current_template)    


    def dump_EH_EL_history(self, sender):
        for t in self.EH_EL_library:
            sender.Log(t)

