#region imports
from AlgorithmImports import *
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
import copy
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
from turningpoints import *
from brad_turning_points import *
from session_boxes import *
from fusion_utils import *
from external_structure import *
from builder_perfect import *
from price_tracker import *

GREEN = 0
RED = 1
BLACK = 2
day = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


'''
This contains just some of the functions.  Needed to get over the 64k file limit
The actual SymbolData class is the one you need to use when wanting to access these methods
'''
class SymbolData_1(object):
    
    #Si function 11.0 --> calculation of the perfect trade points by DTT
    #https://fusionfx.atlassian.net/wiki/spaces/S/pages/178323561/Points+Classification+for+Entry
    def CalculatePerfectPoints(self, sender, symbol,sd,shortsign,my_perfect_trend,mybars,myemas,my4emas,mycolours,myceiling,myfloor,myPH,myTL, \
        myCHH,myCLL,myHH,myLL,signal_chart,pb1,pb2,pb3,logging=True): 

        perfect_points = 0.0
        loggingDetails = ""
        statisticDetails = ""
        direction = ""
        pipsize = self.minPriceVariation * 10
        
        #In the direction of 4hr 9ema?
        inDirection4Hr = False
        pts = 0
        trend4hr = "4hr 9EMA: Sideways"
        if shortsign:
            direction = "SHORT"
            signalClose = myCLL            
            if my_perfect_trend == Trends.Downtrend:
                perfect_points += 1
                inDirection4Hr = True
                trend4hr = "4hr 9EMA: Downtrend"
                pts = 1
                        
        else:
            direction = "LONG"
            signalClose = myCHH   
            if my_perfect_trend == Trends.Uptrend:       
                perfect_points += 1
                inDirection4Hr = True
                trend4hr = "4hr 9EMA: Uptrend"
                pts = 1
        loggingDetails = (f"*** <ul><b>Fusion Breakout Signal | {symbol} - {direction} | Points Email | {signal_chart}</b></ul> ***")                
        loggingDetails = loggingDetails + (f"<br><br>In the direction of 4hr 9 EMA: <b>{inDirection4Hr}</b> --> points:{pts}")  
        
        #get session information for multiple checks below
        (sess_high, psess_high, sess_low,psess_low) = sd.GetSessionHighLows()        

        #session confirmation
        sessionConfirmation = False
        pts = 0
        if shortsign:
            if myHH >= psess_high and myCLL <= psess_low:
                sessionConfirmation = True
                perfect_points += 2
                pts = 2
        else:
            if myLL <= psess_low and myCHH >= psess_high:   
                sessionConfirmation = True
                perfect_points += 2
                pts = 2
        
        loggingDetails = loggingDetails + (f"<br><br>Session Confirmation: <b>{sessionConfirmation}</b>  --> points: {pts}")   

        #previous session high or low - needs session stuff to be built
        previousSessionHighLow = False
        pts = 0
        if shortsign:
            if myTL == psess_low:
                perfect_points += 1
                pts = 1
                previousSessionHighLow = True
            loggingDetails = loggingDetails + (f"<br><br>TL = Prev Session Low: <b>{previousSessionHighLow}</b> --> points: {pts}") 
        else:
            if  myPH == psess_high:    
                perfect_points += 1
                pts = 1
                previousSessionHighLow = True
            loggingDetails = loggingDetails + (f"<br><br>PH = Prev Session High: <b>{previousSessionHighLow}</b> | [ Prev_Session: {sender.PrevSessionID}] --> points: {pts}") 
        
        #is EMA resolution close to numbers
        cema = round(float(myemas[0].Value), 6)
        is_ema_near_numbers = False
        (is_ema_near_numbers,returned_reply) = sd.is_EMA_near_numbers(cema, 9) 
        pts = 0
        if shortsign:
            if is_ema_near_numbers and returned_reply ==  0:
                perfect_points += 1
                pts = 1
        else:
            if is_ema_near_numbers and returned_reply ==  1:
                perfect_points += 1
                pts = 1
        loggingDetails = loggingDetails + (f"<br><br>Is EMA close to Numbers: <b>{is_ema_near_numbers}</b> --> points: {pts}")
        
        #does BO123 cross numbers (exclude the G3-G2/R3/R2 checks)
        crossNumbers = False
        pts = 0
        if shortsign:
            if sd.Is123RToNumbersNoHigh(mybars, mycolours):
                perfect_points += 2
                pts = 2
                crossNumbers = True
            loggingDetails = loggingDetails + (f"<br><br>BO 123R crossing numbers: <b>{crossNumbers}</b> --> points: {pts}")                 
        else:
            if sd.Is123GToNumbersNoHigh(mybars, mycolours):       
                perfect_points += 2
                pts = 2
                crossNumbers = True
            loggingDetails = loggingDetails + (f"<br><br>BO 123G crossing numbers: <b>{crossNumbers}</b> --> points: {pts}")    
                
        #does BO cross resolution EMA
        crossEMA = False 
        pts = 0
        if sd.DoesEMACross(mybars[2], myemas[2]) or sd.DoesEMACross(mybars[1], myemas[1]) or sd.DoesEMACross(mybars[0], myemas[0]):
            perfect_points += 1
            pts = 1
            crossEMA = True
        loggingDetails = loggingDetails + (f"<br><br>Does BO cross 9 EMA: <b>{crossEMA}</b> --> points: {pts}")    
        
        #does BO cross resolution 4hr EMA 
        cross4EMA = False
        pts = 0
        if sd.DoesEMACross(mybars[2], my4emas[2]) or sd.DoesEMACross(mybars[1], my4emas[1]) or sd.DoesEMACross(mybars[0], my4emas[0]):
            perfect_points += 1
            pts = 1
            cross4EMA = True 
        loggingDetails = loggingDetails + (f"<br><br>Does BO cross 4hr 9EMA: <b>{cross4EMA}</b> --> points: {pts}")  
        
        #signal candle is at market open - leaving until we can work in the timedelta
        pts = 0
        if sender.SessionOpen:
            perfect_points += 1
            pts = 1
        loggingDetails = loggingDetails + (f"<br><br>Is this the Session Open: <b>{sender.SessionOpen}</b> --> points: {pts}") 
        
        #distance from floor/ ceiling
        closeToFloorCeiling = False
        pts = 0
        PB_Ceiling_or_Floor_Distance = 0
        PB_Ceiling_or_Floor_Distance_Percent = 0
        PB_Ceiling_or_Floor = 0
        PB_Ceiling_or_Floor_Text = "None to bounce"     

        if shortsign:
             if myceiling !=0:
                if (sd.is_price_near_floor_or_ceiling, myceiling , myTL, 10):
                    perfect_points += 1
                    pts = 1
                    closeToFloorCeiling = True
                    loggingDetails = loggingDetails + (f"<br><br>Is TL close to Ceiling: <b>{closeToFloorCeiling}</b> --> points: {pts}")
                    PB_Ceiling_or_Floor_Distance = round(abs(myceiling -signalClose) / pipsize, 1)   
                    PB_Ceiling_or_Floor = myceiling
                    PB_Ceiling_or_Floor_Text = "Ceiling"     

        else:
             if myfloor !=0: 
                if (sd.is_price_near_floor_or_ceiling, myfloor, myPH, 10):
                    perfect_points += 1
                    pts = 1
                    closeToFloorCeiling = True
                    loggingDetails = loggingDetails + (f"<br><br>Is PH close to Floor: <b>{closeToFloorCeiling}</b> --> points: {pts}")
                    PB_Ceiling_or_Floor_Distance = round(abs(myfloor - signalClose) / pipsize, 1)
                    PB_Ceiling_or_Floor = myfloor
                    PB_Ceiling_or_Floor_Text = "Floor"  
         
        #check for hammer candles on the signal
        IsHammerORInverse = False
        pts = 0
        if shortsign:
             if sd.IsHammer(mybars, mycolours):
                    perfect_points -= 2
                    pts = -2
                    IsHammerORInverse = True
             loggingDetails = loggingDetails + (f"<br><br>Is Hammer: <b>{IsHammerORInverse}</b> --> points: {pts}")
        else:
             if sd.IsReverseHammer(mybars, mycolours) :
                    perfect_points -=2   
                    pts = -2
                    IsHammerORInverse = True
             loggingDetails = loggingDetails + (f"<br><br>Is Reverse Hammer: <b>{IsHammerORInverse}</b> --> points: {pts}")
        
        #check bounces
        signal_bouncing = False
        pts = 0
        if shortsign:
             if sd.BouncedOffFloor(mybars, mycolours, myfloor) or sd.BouncedOffFloor(mybars, mycolours, psess_low): 
                    perfect_points -=3
                    pts = -3
                    signal_bouncing = True
             loggingDetails = loggingDetails + (f"<br><br>Signal Bounced off Floor or Prev. Session Low: <b>{signal_bouncing}</b> --> points: {pts}")     
        else:
             if sd.BouncedOffCeiling(mybars, mycolours, myceiling) or sd.BouncedOffCeiling(mybars, mycolours, psess_high):
                    perfect_points -=3    
                    pts = -3
                    signal_bouncing = True
             loggingDetails = loggingDetails + (f"<br><br>Signal Bounced off Ceiling or Prev. Session High: <b>{signal_bouncing}</b> | points: {pts}")   

        #signal candle high / low of the session
        signal_highLow = False
        pts = 0
        if shortsign:
            if mybars[0].Bid.Low == sess_low:
                perfect_points -= 3
                pts = -3
                signal_highLow = True
            loggingDetails = loggingDetails + (f"<br><br>Signal Candle = Session Low: <b>{signal_highLow}</b> --> points: {pts}") 
        else:
            if mybars[0].Bid.High == sess_high:    
                perfect_points -= 3
                pts = -3
                signal_highLow = True
            loggingDetails = loggingDetails + (f"<br><br>Signal Candle = Session High: <b>{signal_highLow}</b> --> points: {pts}") 
        
        #distance from floor/ ceiling
        couldBounceOffFloorCeiling = False
        pts = 0
        if shortsign:
             if myfloor !=0:
                if (sd.is_price_near_floor_or_ceiling, myfloor, myTL, 13):
                    perfect_points -= 2
                    pts = -2
                    couldBounceOffFloorCeiling = True
             loggingDetails = loggingDetails + (f"<br><br>Too tight to Floor: <b>{couldBounceOffFloorCeiling}</b> --> points: {pts}")
        else:
             if myceiling !=0: 
                if (sd.is_price_near_floor_or_ceiling, myceiling, myPH, 13):
                    perfect_points -= 2
                    pts = -2
                    couldBounceOffFloorCeiling = True
             loggingDetails = loggingDetails + (f"<br><br>Too tight to Ceiling?: <b>{couldBounceOffFloorCeiling}</b> --> points: {pts}")
                    
        loggingDetails = loggingDetails + (f"<br><br><b>**** Breakout Score {perfect_points} points ****  </b>")
        
        #add in the additional information
        additionalInformation = (f"<br><br><hr><br><b>Additional Information for Entry Management</b>")  
        PB_9EMA_Distance = 0
        PB_9EMA_Distance_percent = 0
        PB_4hr_9EMA_Distance = 0
        PB_4hr_9EMA_Distance_percent = 0   
        PB_Numbers = 0.0
        my4hr9EMA_Text = ""
        my9EMA = round(float(myemas[0].Value), 6)
        my_4hr_9EMA = round(float(my4emas[0].Value), 6)
    
        if shortsign:            
            Breakout_Distance = round(abs(myHH - signalClose) / pipsize, 1)    
            if myemas[0].Value > signalClose:
                PB_9EMA_Distance = round(abs(my9EMA- signalClose) / pipsize, 1) 
            else:
                my9EMA_Text = "9EMA is underneath so no bounce off"
            if my4emas[0].Value > signalClose:
                PB_4hr_9EMA_Distance = round(abs(my_4hr_9EMA - signalClose) / pipsize, 1) 
            else:  
                my4hr9EMA_Text = "4hr 9EMA is underneath so no bounce off" 
            PB_Numbers =  self.NumbersAbove(signalClose)   
            numbersText = "Numbers Above" 
            signalBO = myHH    
            

        else:
            Breakout_Distance = round(abs(myLL - signalClose) / pipsize, 1)
            if my9EMA < signalClose:
                PB_9EMA_Distance = round(abs(my9EMA - signalClose) / pipsize, 1) 
            else:
                my9EMA_Text = "9EMA is above so no bounce off"  
            if my_4hr_9EMA < signalClose:
                PB_4hr_9EMA_Distance = round(abs(my_4hr_9EMA - signalClose) / pipsize, 1) 
            else:
                my4hr9EMA_Text = "4hr 9EMA is above so no bounce off"   
            PB_Numbers =  self.NumbersBelow(signalClose)  
            numbersText = "Numbers Below"                  
            signalBO = myLL                                     

        PB_Trigger1_Distance = round(abs(pb1 - signalClose) / pipsize, 1)
        PB_Trigger2_Distance = round(abs(pb2 - signalClose) / pipsize, 1)
        PB_Trigger3_Distance = round(abs(pb3 - signalClose) / pipsize, 1)
        PB1_BO_percent = round((PB_Trigger1_Distance/Breakout_Distance)*100,0)
        PB2_BO_percent = round((PB_Trigger2_Distance/Breakout_Distance)*100,0)
        PB3_BO_percent = round((PB_Trigger3_Distance/Breakout_Distance)*100,0)

        additionalInformation = additionalInformation + (f"<br><br>Breakout Distance: {Breakout_Distance} pips | {signalBO}")                  
        additionalInformation = additionalInformation + (f"<br><br>PB_Trigger1_Distance: {PB_Trigger1_Distance} pips [{PB1_BO_percent}%] | {pb1}") 
        additionalInformation = additionalInformation + (f"<br><br>PB_Trigger2_Distance: {PB_Trigger2_Distance} pips [{PB2_BO_percent}%] | {pb2} ") 
        additionalInformation = additionalInformation + (f"<br><br>PB_Trigger3_Distance: {PB_Trigger3_Distance} pips [{PB3_BO_percent}%] | {pb3}") 

        if PB_9EMA_Distance != 0:
            PB_9EMA_Distance_percent = round((PB_9EMA_Distance/Breakout_Distance)*100,0)
            additionalInformation = additionalInformation + (f"<br><br>PB_9EMA_Distance: {PB_9EMA_Distance} pips [{PB_9EMA_Distance_percent}%] | {round(myemas[0].Value,6)}") 
        else:
            additionalInformation = additionalInformation + (f"<br><br>PB_9EMA_Distance: {my9EMA_Text}")     

        if PB_4hr_9EMA_Distance != 0:
            PB_4hr_9EMA_Distance_percent = round((PB_4hr_9EMA_Distance/Breakout_Distance)*100,0)
            additionalInformation = additionalInformation + (f"<br><br>PB_4hr_9EMA_Distance: {PB_4hr_9EMA_Distance} pips [{PB_4hr_9EMA_Distance_percent}%] | {round(my4emas[0].Value,6)}") 
        else:
            additionalInformation = additionalInformation + (f"<br><br>PB_4hr_9EMA_Distance: {my4hr9EMA_Text}")               
        
        PB_Numbers_Distance = round(abs(PB_Numbers-signalClose)/ pipsize, 1)          
        PB_Numbers_Distance_percent = round((PB_Numbers_Distance/Breakout_Distance)*100,0)
        additionalInformation = additionalInformation + (f"<br><br>PB_Numbers_Distance: {PB_Numbers_Distance} pips [{PB_Numbers_Distance_percent}%] | {numbersText} bounce") 

        if PB_Ceiling_or_Floor_Distance != 0:
            PB_Ceiling_or_Floor_Distance_Percent = round((PB_Ceiling_or_Floor_Distance/Breakout_Distance)*100,0)
            additionalInformation = additionalInformation + (f"<br><br>PB_Ceiling_or_Floor_Distance: {PB_Ceiling_or_Floor_Distance} pips [{PB_Ceiling_or_Floor_Distance_Percent}%] | {PB_Ceiling_or_Floor_Text}:  {PB_Ceiling_or_Floor}") 
        else:
            additionalInformation = additionalInformation + (f"<br><br>PB_Ceiling_or_Floor_Distance: {PB_Ceiling_or_Floor_Text}")   

        statisticDetails = (f"<br><br><hr><b> ----- reference information for cross checking -----</b><br>| myCLL: {myCLL} | myHH: {myHH} | myCHH:{myCHH} | myLL:{myLL}<br>\
            | {trend4hr} | myceiling: {myceiling} | myfloor: {myfloor} | myPH: {myPH} | myTL: {myTL}<br> \
            | Session: {sender.SessionID} | sess_low: {sess_low} | sess_high: {sess_high} | Signal High: {mybars[0].Bid.High} | Signal Low: {mybars[0].Bid.Low}<br>\
            | Prev_Session: {sender.PrevSessionID} | prev_sess_low: {psess_low} | prev_sess_high: {psess_high} sig. candle close: {signalClose}<br>\
            ")

        #populate the list
        pullbackItems = []
        pullbackItems = [
            ("PB_Trigger1", pb1, PB_Trigger1_Distance, PB1_BO_percent),
            ("PB_Trigger2", pb2, PB_Trigger2_Distance, PB2_BO_percent),
            ("PB_Trigger2", pb3, PB_Trigger3_Distance, PB3_BO_percent),
            ("PB_Numbers", PB_Numbers, PB_Numbers_Distance, PB_Numbers_Distance_percent),
            ("PB_9EMA", my9EMA, PB_9EMA_Distance, PB_9EMA_Distance_percent),
            ("PB_4hr_9EMA", my_4hr_9EMA, PB_4hr_9EMA_Distance, PB_4hr_9EMA_Distance_percent),
            ("PB_Floor_Ceiling", PB_Ceiling_or_Floor, PB_Ceiling_or_Floor_Distance, PB_Ceiling_or_Floor_Distance_Percent)
        ] 
        #sender.Debug(f"pullbackItems= {pullbackItems}")
        #pullbackItems.sort(key=lambda item:pullbackItems[1])    #sort
        
        loggingDetails = loggingDetails + additionalInformation + statisticDetails

     
        if logging: sender.Log(loggingDetails)
        logsub = (f"BO: {perfect_points} points | {symbol} - {direction} | NY: {sender.Time} | MT4: {fusion_utils.get_times(sender.Time, 'us')['mt4']} ")
        if logging: sender.LogFormatted(loggingDetails,logsub) 
        

        #calculate the take profit
        #sd.channel_take_profit_pips = Breakout_Distance   
        sd.channel_take_profit_pips = 50 

        #calculate the stop loss
        if shortsign:    
            sd.channel_stop_loss_price = self.ReturnPrice(mybars[0].Bid.High, "plus", 1)
        else:
            sd.channel_stop_loss_price = self.ReturnPrice(mybars[0].Bid.Low, "minus", 1)    
                
        #currently we will ignore the case of returning a trigger price before entering
        #sd.channel_trigger_price = pb1 
        sd.channel_trigger_price = 0.0  

        #if perfect_points >= sender.MinimumPerfectPoints:
        #sender.Debug(str(sender.Time) + " Symbol: " + str(symbol) + " Points: " + str(perfect_points))
        # to start with simple passing of information   
            
        return perfect_points  
    
    # Clear down any of the tracking stuff used for Perfect channel trades for the 1H view
    def clear_perfect_channel_1H(self):
        self.AlertedPerfect_Long_1HR = False  
        self.AlertedPerfect_Short_1HR = False                                          
        self.channel_state_1H = 0      #see consolidators Look_For_Channel_Trigger for details 
        self.looking_for_channel_1H = False
        self.channel_direction_1H = StratDirection.Nothing
        self.channel_trigger_price = 0.0
        self.channel_take_profit_pips = 0.0
        self.channel_stop_loss_price = 0.0   
        self.set_specific_stop_loss = False 
        self.set_specific_take_profit = False 
        self.TriggerCandleWindow_1HR = -1         # CG added for times when we clear because the HHLL clears before time runs out  

    # Clear down any of the tracking stuff used for Perfect channel trades for the 30M view
    def clear_perfect_channel_30M(self):
        self.AlertedPerfect_Long_30M = False  
        self.AlertedPerfect_Short_30M = False                                          
        self.channel_state_30M = 0      #see consolidators Look_For_Channel_Trigger for details 
        self.looking_for_channel_30M = False
        self.channel_direction_30M = StratDirection.Nothing
        self.channel_trigger_price = 0.0
        self.channel_take_profit_pips = 0.0
        self.channel_stop_loss_price = 0.0   
        self.set_specific_stop_loss = False 
        self.set_specific_take_profit = False 
        self.TriggerCandleWindow_1HR = -1         # CG added for times when we clear because the HHLL clears before time runs out  

    def clear_perfect_channel_5M(self):
        self.AlertedPerfect_Long_5M = False  
        self.AlertedPerfect_Short_5M = False                                          
        self.channel_state_5M = 0      #see consolidators Look_For_Channel_Trigger for details 
        self.looking_for_channel_5M = False
        self.channel_direction_5M = StratDirection.Nothing
        self.channel_trigger_price = 0.0
        self.channel_take_profit_pips = 0.0
        self.channel_stop_loss_price = 0.0   
        self.set_specific_stop_loss = False 
        self.set_specific_take_profit = False 
        self.TriggerCandleWindow_5M = -1         # CG added for times when we clear because the HHLL clears before time runs out          

    
    #Return Session Highs / Lows together with previous Session HighLows Si 11.0
    def GetSessionHighLows(self):
        
        sess_high = self.live_sessions[self.current_session].high_bid
        sess_low = self.live_sessions[self.current_session].low_bid
        psess_high = self.live_sessions[self.previous_session].high_bid
        psess_low = self.live_sessions[self.previous_session].low_bid
        
        return  (sess_high, psess_high, sess_low,psess_low)
        
    # Return a price that is NumbersAbove for this symbol based on the input price
    def NumbersAbove(self, price, jumps=1):
        return round((math.ceil(price / self.numbersQuantum ) * self.numbersQuantum)+((jumps-1)*self.numbersQuantum), 6)
    
    # Return a price that is NumbersBelow for this symbol based on the output price
    def NumbersBelow(self, price, jumps=1):
        return round((math.floor(price / self.numbersQuantum) * self.numbersQuantum)-((jumps-1)*self.numbersQuantum), 6)

    # Useful tool to return a price based on adding or subtracting pips value 
    def ReturnPrice(self, price, method, pips):        
        if method == "plus":
            price = price + round(pips * self.minPriceVariation * 10, 5)
        else:
            price = price - round(pips * self.minPriceVariation * 10, 5)
        return price

    # Useful tool to find the difference in prices in pips
    def ReturnPipDifference(self, price1, price2):
        pipSize = self.minPriceVariation * 10
        pipDifference = abs(price1-price2) / pipSize
        return pipDifference
    
    def DTTClassicEntryTest(self, mycolours,mybars,mydirection,myemas,my4emas,mychart): 
        is9EMABouncing = False
        is4hr9EMABouncing = False 
        DTTClassicEntryTest = True
        if mydirection == StratDirection.Short:    
            #test 1 - S1 needs to be the opposite colour to S0
            if mycolours[0] == GREEN:   #leave doji for the moment
                #test 2 - inside candle
                if mybars[0].Bid.High < mybars[1].Bid.High:
                    #test 3 - bounce off the 9EMA or 4Hr_9EMA    
                     is9EMABouncing = self.is_G_bouncing_off_EMAs(myemas[0].Value, mybars, mycolours, 1)
                     is4hr9EMABouncing = self.is_G_bouncing_off_EMAs(my4emas[0].Value, mybars, mycolours, 1)
                     if is9EMABouncing or is4hr9EMABouncing:
                         DTTClassicEntryTest = True                      
        else:
           if mycolours[0] == RED: #leave doji for the moment
                #test 2 - inside candle
                if mybars[0].Bid.Low > mybars[1].Bid.Low:
                    #test 3 - bounce off the 9EMA or 4Hr_9EMA    
                     is9EMABouncing = self.is_R_bouncing_off_EMAs(myemas[0].Value, mybars, mycolours, 1)
                     is4hr9EMABouncing = self.is_R_bouncing_off_EMAs(myemas[0].Value, mybars, mycolours, 1)
                     if is9EMABouncing or is4hr9EMABouncing:
                         DTTClassicEntryTest = True

        # here is where we will refine the stops, based on S1 high / low i.e. have we enough buffer

        return DTTClassicEntryTest

    def ShortWeaknessIndicator(self, mycolours,mybars,chart):
        #we need two greens with the second green high less than the first
        resultString = None        
        if mycolours[0] == GREEN and mycolours[1] == GREEN:
            resultString = (f"2 x greens" + " chart=" + str(chart) + " Current High=" + str(mybars[0].Bid.High) + " Prev High=" + str(mybars[1].Bid.High))
            # CG - this test would likely miss most forms of weakness, but is not consistent with the Long one below - Si thats what doug said
            if mybars[0].Bid.High <= mybars[1].Bid.High:
                resultString = resultString + (f" | yes weakness short" + " chart=" + str(chart))
                return (resultString, True)
        return (resultString, False)

    def LongWeaknessIndicator(self, mycolours,mybars, chart):
        #we need two reds with the second red high less than the first
        resultString = None
        if mycolours[0] == RED and mycolours[1] == RED:
            resultString = (f"2 x reds" + " chart=" + str(chart) + " Current Low=" + str(mybars[0].Bid.Low) + " Prev Low=" + str(mybars[1].Bid.Low))
            # CG - this will almost always be True if we have 2 RED's, think you meant >= Si, yes My error
            if mybars[0].Bid.Low >= mybars[1].Bid.Low:
                resultString = resultString + (f" | yes weakness long" + " chart=" + str(chart))
                return (resultString, True)
        return (resultString, False)

    # check for a 3 bar pattern given a set of bars
    def CheckCandlePatternInWindow(self, windowofbars, candle1, candle2, candle3, startloc = 0):
        if startloc -2 > (windowofbars.Count - 1):
            # don't have enough bars to check
            return False
        if windowofbars[startloc + 2] == candle1 and windowofbars[startloc + 1] == candle2 and windowofbars[startloc] == candle3:
            return True
        else: 
            return False
            
    # check for a 4 bar pattern given a set of bars
    def CheckCandlePatternInWindowFour(self, windowofbars, candle1, candle2, candle3, candle4, startloc = 0):
        if startloc -3 > (windowofbars.Count - 1):
            # don't have enough bars to check
            return False
        if windowofbars[startloc + 3] == candle1 and windowofbars[startloc + 2] == candle2 and windowofbars[startloc+1] == candle3 and windowofbars[startloc] == candle4:
            return True
        else: 
            return False
            
    # look for FallingThree Method
    def IsFallingThree(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN):
            # We have 3 green candles, now see if we have a RED engulfing to the left
            if mybars.Count > 4:
                if mycolours[3] == RED:
                    rhi = mybars[3].Bid.High
                    rlo = mybars[3].Bid.Low
                    ghi = max(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close) 
                    glo = min(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open)
                    if ghi < rhi and glo > rlo:
                        # Now we have all 3 green candle bodies engulfed inside the red candle full extent
                        return True
        return False
    
    # look for RisingThree Method    
    def IsRisingThree(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, RED):
            # We have 3 red candles, now see if we have a GREEN engulfing to the left
            if mybars.Count > 4:
                if mycolours[3] == GREEN:
                    ghi = mybars[3].Bid.High
                    glo = mybars[3].Bid.Low
                    rhi = max(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open) 
                    rlo = min(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close)
                    if ghi > rhi and glo < rlo:
                        # Now we have all 3 red candle bodies engulfed inside the green candle full extent
                        return True
        return False
        
    # look for 123R to Numbers + Reverse Green   
    def Is123RReverseG(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, GREEN):
            # We have 2 red candles, followed by a green now see if we GREEN reverse + numbers
            if mybars.Count > 4:
                if mycolours[3] == RED:
                    r2o = mybars[2].Bid.Open
                    g4c = mybars[0].Bid.Close
                    if g4c > r2o:
                        chi = max(mybars[3].Bid.Open, mybars[2].Bid.Open, mybars[1].Bid.Open) 
                        clo = min(mybars[3].Bid.Close, mybars[2].Bid.Close, mybars[1].Bid.Close)
                        nextnumdown = self.NumbersBelow(chi)
                        nextnumup = self.NumbersAbove(clo)
                        if nextnumdown >= nextnumup:   # we have crossed numbers
                            return True
        return False
        
    # look for 123G to Numbers + Reverse Red   
    def Is123GReverseR(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, RED):
            # We have 2 green candles, followed by a red now see if we RED reverse + numbers
            if mybars.Count > 4:
                if mycolours[3] == GREEN:
                    g2o = mybars[2].Bid.Open
                    r4c = mybars[0].Bid.Close
                    if r4c < g2o:
                        chi = max(mybars[3].Bid.Close, mybars[2].Bid.Close, mybars[1].Bid.Close) 
                        clo = min(mybars[3].Bid.Open, mybars[2].Bid.Open, mybars[1].Bid.Open)
                        nextnumdown = self.NumbersBelow(chi)
                        nextnumup = self.NumbersAbove(clo)
                        if nextnumdown >= nextnumup:   # we have crossed numbers
                            return True
        return False
        
    # look for 123G to Numbers with G3High < G2High   
    def Is123GToNumbers(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN):
            ghi = max(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close) 
            glo = min(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open)
            nextnumdown = self.NumbersBelow(ghi)
            nextnumup = self.NumbersAbove(glo)
            if nextnumdown >= nextnumup:   # we have crossed numbers
                # now check G3High < G2High
                if mybars[0].Bid.High < mybars[1].Bid.High:
                    return True
        return False
    
    #si 11.0 new function, we can unify later with option parameter
    def Is123GToNumbersNoHigh(self, mybars, mycolours): 
        if self.CheckCandlePatternInWindow(mycolours, GREEN, GREEN, GREEN):
            ghi = max(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close) 
            glo = min(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open)
            nextnumdown = self.NumbersBelow(ghi)
            nextnumup = self.NumbersAbove(glo)
            if nextnumdown >= nextnumup:   # we have crossed numbers
                return True
        return False        
        
    # look for 123R to Numbers with R3Low > R2Low   
    def Is123RToNumbers(self, mybars, mycolours):
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, RED):
            rhi = max(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open) 
            rlo = min(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close)
            nextnumdown = self.NumbersBelow(rhi)
            nextnumup = self.NumbersAbove(rlo)
            if nextnumdown >= nextnumup:   # we have crossed numbers
                # now check R3Low > R2Low
                if mybars[0].Bid.Low > mybars[1].Bid.Low:
                    return True
        return False
    
    #si 11.0 new function, we can unify later with option parameter    
    def Is123RToNumbersNoHigh(self, mybars, mycolours): 
        if self.CheckCandlePatternInWindow(mycolours, RED, RED, RED):
            rhi = max(mybars[2].Bid.Open, mybars[1].Bid.Open, mybars[0].Bid.Open) 
            rlo = min(mybars[2].Bid.Close, mybars[1].Bid.Close, mybars[0].Bid.Close)
            nextnumdown = self.NumbersBelow(rhi)
            nextnumup = self.NumbersAbove(rlo)
            if nextnumdown >= nextnumup:   # we have crossed numbers
                return True
        return False        
        
    def is_EMA4hr_EMA1hr_clustered(self, my_1hr_emas, my_4hr_emas, pip_tolerance):
        pipsize = self.minPriceVariation * 10
        ema_diff_pips = abs(my_1hr_emas[0].Value - my_4hr_emas[0].Value) / pipsize
        ema_midpoint = abs(my_1hr_emas[0].Value + my_4hr_emas[0].Value) / 2.0
        if ema_diff_pips <= pip_tolerance:
            return (True, ema_midpoint)
        else:
            return(False, 0.0)
    
    #si 11.0 - added extra return     
    def is_EMA_near_numbers(self, ema, pip_tolerance):   
        pipsize = self.minPriceVariation * 10
        nextnumdown = self.NumbersBelow(ema)
        nextnumup = self.NumbersAbove(ema)
        pips_above = (ema - nextnumdown) / pipsize
        pips_below = (nextnumup - ema) / pipsize     
        if pips_above <= pip_tolerance:
            # we are closest to Numbers next down, short
            return(True, 0)
        if pips_below <= pip_tolerance:
            # we are closest to Numbers next up, long
            return(True, 1)
        return(False, 999)    
        
        
    def is_price_near_numbers(self, price_point, pip_tolerance):
        pipsize = self.minPriceVariation * 10
        nextnumdown = self.NumbersBelow(price_point)
        nextnumup = self.NumbersAbove(price_point)
        pips_above = (price_point - nextnumdown) / pipsize
        pips_below = (nextnumup - price_point) / pipsize
        if pips_above <= pip_tolerance:
            # we are closest to Numbers next down
            return(True, nextnumdown)
        if pips_below <= pip_tolerance:
            # we are closest to Numbers next up
            return(True, nextnumup)
        return(False, 0.0)
    
    #si 11.0 - check tolerance of PH or TL in relation to floor or ceiling
    def is_price_near_floor_or_ceiling(self, floor_or_ceiling, peak_or_trough, pip_tolerance):
        pipsize = self.minPriceVariation * 10
        distance = abs(peak_or_trough - floor_or_ceiling) / pipsize
        if distance <= pip_tolerance:
            return True
        return False    
    
    def is_G_bouncing_off_EMAs(self, ema_midpoint, mybars, mycolours, pip_tolerance):
        sig_candle_len = 0.0
        sig_wick_len = 0.0
        sig_candle_dist = 0.0
        pipsize = self.minPriceVariation * 10
        price_tolerance = pip_tolerance * pipsize / 2.0
        upper_ema = ema_midpoint + price_tolerance
        lower_ema = ema_midpoint - price_tolerance
        if mycolours[0] != GREEN:
            return False
        if mybars[0].Bid.Close <= ema_midpoint and mybars[0].Bid.High >= ema_midpoint:
            return True



    def is_R_bouncing_off_EMAs(self, ema_midpoint, mybars, mycolours, pip_tolerance):
        sig_candle_len = 0.0
        sig_wick_len = 0.0
        sig_candle_dist = 0.0
        pipsize = self.minPriceVariation * 10
        price_tolerance = pip_tolerance * pipsize / 2.0
        upper_ema = ema_midpoint + price_tolerance
        lower_ema = ema_midpoint - price_tolerance
        if mycolours[0] != RED:
            return False
        if mybars[0].Bid.Close >= ema_midpoint and mybars[0].Bid.Low <= ema_midpoint:
            return True


    def was_straight_move_down(self, my_bars, my_colours, candle_open_to_ignore):
        count_bars = 0
        high_start = 0.0
        for i in range(0, my_bars.Count):
            if my_bars[i].Time <= candle_open_to_ignore:
                break
            if my_colours[i] == RED:
                count_bars += 1
                high_start = my_bars[i].Bid.High
            else:
                break
        if count_bars >= 3:
            return (True, count_bars, high_start)
        else:
            return (False, count_bars, 0.0)


    def was_straight_move_up(self, my_bars, my_colours, candle_open_to_ignore):
        count_bars = 0
        low_start = 0.0
        for i in range(0, my_bars.Count):
            if my_bars[i].Time <= candle_open_to_ignore:
                break
            if my_colours[i] == GREEN:
                count_bars += 1
                low_start = my_bars[i].Bid.Low
            else:
                break
        if count_bars >= 3:
            return (True, count_bars, low_start)
        else:
            return (False, count_bars, 0.0)

        
        
    def find_retrace_length_vs_initial_push(self, mybars, mycolours, retrace_colour, push_colour, push_candles=10):
        if retrace_colour == push_colour:
            # this will error - no self.Log
            self.Log("ERROR - can't differentiate retrace from push with same candle colours")
            return (0.0, 0.0)
        pipsize = self.minPriceVariation * 10
        retrace_len = 0.0
        retrace2_len = 0.0
        max_candles = 5
        push_len = 0.0
        candle_pos = 0
        candle_pos2 = 0
        candle_pos3 = 0
        push_count = 0
        # get the retrace length first
        for x in range(0, max_candles-1):
            candle_pos = x
            if mycolours[x] == retrace_colour:
                retrace_len += round(abs(mybars[x].Bid.Open - mybars[x].Bid.Close) / pipsize, 2)
            else:
                break
        # get the original push length next
        for x in range(candle_pos, candle_pos + push_candles):
            candle_pos2 = x
            if mycolours[x] == push_colour:
                push_count += 1
                push_len += round(abs(mybars[x].Bid.Open - mybars[x].Bid.Close) / pipsize, 2)
            else:
                # now need to check if it was just a small retrace breakdown
                break
        if push_count == 1:
            # we only had a single push candle...probably a double re-trace.  Count the rest
            for x in range(candle_pos2, candle_pos2 + push_candles):
                candle_pos3 = x
                if mycolours[x] == retrace_colour:
                    retrace2_len += round(abs(mybars[x].Bid.Open - mybars[x].Bid.Close) / pipsize, 2)
                else:
                    break
            retrace_len += retrace2_len
            if retrace2_len <= push_len:
                # only do this if the original retrace attempt was weaker than the orphaned push candle
                # now we need to find the rest of the push candles
                for x in range(candle_pos3, candle_pos3 + push_candles):
                    if mycolours[x] == push_colour:
                        push_len += round(abs(mybars[x].Bid.Open - mybars[x].Bid.Close) / pipsize, 2)
                    else:
                        # now need to check if it was just a small retrace breakdown
                        break
        return (retrace_len, push_len)
        
        
    # Check on the 1Hr resolution for the Long Breakout LHLLHH situation
    def check_peaks_troughs(self, sender, symbol, conf_TLs, poss_TLs, conf_PHs, poss_PHs, bar, bar_colour, prev_low, prev_high, prev_open, prev_bar_colour, resolution, logging=False):
        found_TL_PH = "Not Found"
        if resolution.value == ChartRes.res1H.value:
            bar_end_time = bar.Time + timedelta(hours=1)
        elif resolution.value == ChartRes.res30M.value:
            bar_end_time = bar.Time + timedelta(minutes=30)
        elif resolution.value == ChartRes.res5M.value:
            bar_end_time = bar.Time + timedelta(minutes=5)            
        elif resolution.value == ChartRes.res1M.value:
            bar_end_time = bar.Time + timedelta(minutes=1)
        else:
            raise Exception("Unsupported Peak_Trough resolution")
        pip_size = self.minPriceVariation * 10

        count_TL = len(poss_TLs)
        
        it = iter(range(0, count_TL))
        for i in it:
            # Need to do these in reverse state order, so only one state change per candle
            if poss_TLs[i].status == t_p_status.post_turn:
                
                t_p_result = poss_TLs[i].check_post_turn(bar.Bid.High, bar.Bid.Low, bar.Bid.Open, bar.Bid.Close, bar_end_time, bar_colour, prev_low, pip_size)
                if t_p_result == t_p_status.confirmed:
                    # we have confirmed a TROUGH LOW
                    if logging and not sender.IsWarmingUp: sender.Log(f"[{i}] {symbol} New TL: {bar.Symbol.Value}  Low: {poss_TLs[i].TP_low}  Time: {poss_TLs[i].turn_time}  Candles: {poss_TLs[i].total_candles} Wick Percent: {poss_TLs[i].wick_percent}")
                    
                    # add it to the confirmed ones and reset possible ones to the empty initial TL object
                    conf_TLs.append(poss_TLs[i])
                    poss_TLs.clear()
                    poss_TLs.append(turning_point('First TL', 'TROUGH', resolution))
                    found_TL_PH = "TROUGH"
                    break
    
            if poss_TLs[i].status == t_p_status.pre_turn:
                t_p_result = poss_TLs[i].check_pre_turn(bar.Bid.High, bar.Bid.Low, bar.Bid.Open, bar.Bid.Close, bar_end_time, bar_colour, prev_low, pip_size)
                if t_p_result == t_p_status.confirmed:
                    # we have confirmed a TROUGH LOW immediately, no chance of a follow-on - print out and reset
                    if logging and not sender.IsWarmingUp: sender.Log(f"[{i}] {symbol} New TL immediate: {bar.Symbol.Value}  Low: {poss_TLs[i].TP_low}  Time: {poss_TLs[i].turn_time}  Candles: {poss_TLs[i].total_candles} Wick Percent: {poss_TLs[i].wick_percent}")
                    
                    # add it to the confirmed ones and reset possible ones to the empty initial TL object
                    conf_TLs.append(poss_TLs[i])
                    poss_TLs.clear()
                    poss_TLs.append(turning_point('First TL', 'TROUGH', resolution))
                    found_TL_PH = "TROUGH"
                    break                
                
                if t_p_result == t_p_status.post_turn:
                    # this is where we need to check for a possible new one forming while we wait to confirm this one
                    poss_TLs.insert(0,turning_point('Alt TL', 'TROUGH', resolution))
                    # now we've inserted a new TL, we need to skip the next loop iteration as that will act on this one we've already worked on - but first, check if it begins.
                    #poss_TLs[0].begin_turn(bar.Bid.High, bar.Bid.Low, bar.Bid.Open, bar.Bid.Close, bar_end_time, bar_colour, prev_low, prev_open, prev_bar_colour, pip_size)
                    break
            
            if poss_TLs[i].status == t_p_status.empty:
                poss_TLs[i].begin_turn(bar.Bid.High, bar.Bid.Low, bar.Bid.Open, bar.Bid.Close, bar_end_time, bar_colour, prev_low, prev_open, prev_bar_colour, pip_size)
                
        count_PH = len(poss_PHs)
        
        it = iter(range(0, count_PH))
        for i in it:
            # Need to do these in reverse state order, so only one state change per candle
            if poss_PHs[i].status == t_p_status.post_turn:
                
                t_p_result = poss_PHs[i].check_post_turn(bar.Bid.High, bar.Bid.Low, bar.Bid.Open, bar.Bid.Close, bar_end_time, bar_colour, prev_high, pip_size)
                if t_p_result == t_p_status.confirmed:
                    # we have confirmed a PEAK HIGH
                    if logging and not sender.IsWarmingUp: sender.Log(f"[{i}] {symbol} New PH: {bar.Symbol.Value}  High: {poss_PHs[i].TP_high}  Time: {poss_PHs[i].turn_time}  Candles: {poss_PHs[i].total_candles} Wick Percent: {poss_PHs[i].wick_percent}")
                    
                    # add it to the confirmed ones and reset possible ones to the empty initial PH object
                    conf_PHs.append(poss_PHs[i])
                    poss_PHs.clear()
                    poss_PHs.append(turning_point('First PH', 'PEAK', resolution))
                    found_TL_PH = "PEAK"
                    break
    
            if poss_PHs[i].status == t_p_status.pre_turn:
                t_p_result = poss_PHs[i].check_pre_turn(bar.Bid.High, bar.Bid.Low, bar.Bid.Open, bar.Bid.Close, bar_end_time, bar_colour, prev_high, pip_size)
                if t_p_result == t_p_status.confirmed:
                    # we have confirmed a PEAK HIGH immediately, no chance of a follow-on - print out and reset
                    if logging and not sender.IsWarmingUp: sender.Log(f"[{i}] {symbol} New PH immediate: {bar.Symbol.Value}  High: {poss_PHs[i].TP_high}  Time: {poss_PHs[i].turn_time}  Candles: {poss_PHs[i].total_candles} Wick Percent: {poss_PHs[i].wick_percent}")
                    
                    # add it to the confirmed ones and reset possible ones to the empty initial PH object
                    conf_PHs.append(poss_PHs[i])
                    poss_PHs.clear()
                    poss_PHs.append(turning_point('First PH', 'PEAK', resolution))
                    found_TL_PH = "PEAK"
                    break
                
                if t_p_result == t_p_status.post_turn:
                    # this is where we need to check for a possible new one forming while we wait to confirm this one
                    poss_PHs.insert(0,turning_point('Alt PH', 'PEAK', resolution))
                    # now we've inserted a new PH, we need to skip the next loop iteration as that will act on this one we've already worked on - but first, check if it begins.
                    #poss_PHs[0].begin_turn(bar.Bid.High, bar.Bid.Low, bar.Bid.Open, bar.Bid.Close, bar_end_time, bar_colour, prev_high, prev_open, prev_bar_colour, pip_size)
                    break
            
            if poss_PHs[i].status == t_p_status.empty:
                poss_PHs[i].begin_turn(bar.Bid.High, bar.Bid.Low, bar.Bid.Open, bar.Bid.Close, bar_end_time, bar_colour, prev_high, prev_open, prev_bar_colour, pip_size)
        
        if found_TL_PH == 'TROUGH' or found_TL_PH == 'PEAK':
            #if not sender.IsWarmingUp: sender.Log(f"Found: {found_TL_PH}")
            return True
        else:
            return False

    # Check if something is a peak or a trough using the simple Brad definitions - and store them if so
    def check_brad_peaks_troughs(self, sender, symbol, conf_TLs, conf_PHs, my_bars, my_colours, resolution, logging=False):
        found_TL_PH = "Not Found"

        pip_size = self.minPriceVariation * 10
        sd = sender.symbolInfo[symbol]

        new_peak = None
        new_trough = None

        # check for a peak and log it if we find one
        is_peak = False
        peak_time = None
        peak_high = 0.0
        (is_peak, peak_high, peak_time, peak_bar, start_time, confirm_time, count_lhs) = sd.is_123_peak_return_bar(my_bars, my_colours)

        if is_peak:
            mt4_peak_time = fusion_utils.get_candle_open_time(fusion_utils.get_times(peak_time, 'us')['mt4'], resolution)             
            if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} has a {resolution} Brad peak at MT4: {mt4_peak_time} | NY: {peak_time} with {peak_high} LHS: {count_lhs}")
            # now store the Peak into the main list
            new_p = brad_turning_point('Brad Peak', 'PEAK', resolution, peak_time, peak_bar, start_time, confirm_time, count_lhs, pip_size)
            conf_PHs.append(new_p)
            new_peak = conf_PHs[-1]
            found_TL_PH = "PEAK"

        # check for a trough and log if it we find one
        is_trough = False
        trough_time = None
        trough_low = 0.0
        (is_trough, trough_low, trough_time, trough_bar, start_time, confirm_time, count_lhs) = sd.is_123_trough_return_bar(my_bars, my_colours)

        if is_trough:
            mt4_trough_time = fusion_utils.get_candle_open_time(fusion_utils.get_times(trough_time, 'us')['mt4'], resolution)         

            if logging and not sender.IsWarmingUp: sender.Log(f"{symbol} has a {resolution} Brad trough at MT4: {mt4_trough_time} | NY: {trough_time} with {trough_low} LHS: {count_lhs}]")
            # now store the Trough into the main list
            new_t = brad_turning_point('Brad Trough', 'TROUGH', resolution, trough_time, trough_bar, start_time, confirm_time, count_lhs, pip_size)
            conf_TLs.append(new_t)
            new_trough = conf_TLs[-1]
            found_TL_PH = "TROUGH"
        
        if found_TL_PH == 'TROUGH' or found_TL_PH == 'PEAK':
            return (True, new_peak, new_trough)
        else:
            return (False, None, None)




    def check_for_brad_breakout(self, sender, symbol, conf_TLs, conf_PHs, my_bars, my_colours, chart_res, logging=False):
        if len(conf_TLs) <= 2 or len(conf_PHs) <= 2:
            # we should have at least 3 troughs or peaks to look into
            return (False, StratDirection.Nothing, None, None, 0.0)
        my_high_close = 0.0
        my_low_close = 0.0
        my_TLs = []
        my_PHs = []

        direction = StratDirection.Nothing
        if my_colours[0] == GREEN:
            direction = StratDirection.Long
            my_high_close = my_bars[0].Bid.Close
        elif my_colours[0] == RED:
            direction = StratDirection.Short
            my_low_close = my_bars[0].Bid.Close            
        else:
            direction = StratDirection.Nothing
            return (False, StratDirection.Nothing, None, None, 0.0)

        if direction == StratDirection.Long:
            # check for a breakout LHLLCHH - first get the trough that could be LL, then the peak that could be H and then the trough that could be L
            poss_LL = None
            poss_H = None
            poss_L = None
            trough_index = len(conf_TLs) - 1
            peak_index = len(conf_PHs) - 1
            
            # try to find the LL
            if conf_TLs[trough_index].turn_time > conf_PHs[peak_index].turn_time:
                # this means the trough comes after the peak - which we want to find the LL
                poss_LL = conf_TLs[trough_index]
                # do we see more troughs before the peak?
                trough_index -= 1
                while True:
                    if trough_index < 0:
                        return (False, StratDirection.Nothing, None, None, 0.0)
                    if conf_TLs[trough_index].turn_time > conf_PHs[peak_index].turn_time:
                        trough_index -= 1
                    else:
                        break
            else:
                # we found a peak at the end - this only works if it is within the LL and H - but that's harder to find
                # this code will ignore one PEAK found between the LL and the CHH, if it sits within the LL and the H
                peak_to_ignore = conf_PHs[peak_index]
                peak_index -= 1
                poss_LL = conf_TLs[trough_index]
                # do we see more troughs before the peak?
                trough_index -= 1
                while True:
                    if trough_index < 0:
                        return (False, StratDirection.Nothing, None, None, 0.0)
                    if conf_TLs[trough_index].turn_time > conf_PHs[peak_index].turn_time:
                        trough_index -= 1
                    else:
                        break
                poss_H = conf_PHs[peak_index]
                if peak_to_ignore.TP_high > poss_LL.TP_low and peak_to_ignore.TP_high < poss_H.TP_high:
                    # we found a peak that sits within the gap, so we can ignore it and carry on
                    pass
                else:
                    return (False, StratDirection.Nothing, None, None, 0.0)

            # try to find the H - this first Peak should be it.
            poss_H = conf_PHs[peak_index]
            # we may have more peaks backwards before we get to the L
            peak_index -= 1
            while True:
                if peak_index < 0:
                    return (False, StratDirection.Nothing, None, None, 0.0)
                if conf_PHs[peak_index].turn_time > conf_PHs[peak_index].turn_time:
                    peak_index -= 1
                else:
                    break
            # now we should have found the next L backwards
            poss_L = conf_TLs[trough_index]

            if poss_LL.TP_low <= poss_L.TP_low and my_high_close >= poss_H.TP_high:
                # reverted to >= <= because of missing CHH5 in the test
                # we have a LHLLCHH
                # now make sure the bars before wouldn't have already hit it
                my_high = round(poss_H.TP_high, 5)
                my_low = round(poss_L.TP_low, 5)
                my_lower_low = round(poss_LL.TP_low, 5)
                my_breakout_price = round(my_high_close, 5)
                my_breakout_time = my_bars[0].Time
                my_mt4_time = fusion_utils.get_times(my_breakout_time, 'us')['mt4']
                # check this isn't a weird one with the L greater than the H -- which is an odd pattern
                if my_low > my_high:
                    return (False, StratDirection.Nothing, None, None, 0.0)
                for i in range(1, my_bars.Count):
                    if my_colours[i] == GREEN:
                        # we have another GREEN bar that maybe was the CHH earlier - do not want to repeat
                        if my_bars[i].Bid.Close > my_high:
                            # an earlier GREEN bar was a CHH, so don't report this as a breakout - it will have been done before
                            return (False, StratDirection.Nothing, None, None, 0.0)
                        if my_bars[i].Bid.Close < my_high:
                            break
                    # ignore REDs - we don't care about them
                if logging and not sender.IsWarmingUp: sender.Log(f"Found LHLLCHH Brad breakout {my_mt4_time} {symbol} {chart_res} CHH: {my_breakout_price} LL:{my_lower_low} H:{my_high} L:{my_low}") 
                my_TLs.append(poss_L)
                my_TLs.append(poss_LL)
                my_PHs.append(poss_H)
                return (True, direction, my_TLs, my_PHs, my_high_close)

        if direction == StratDirection.Short:
            # check for a breakout HLHHCLL - first get the peak that could be HH, then the trough that could be L and then the peak that could be H
            poss_HH = None
            poss_L = None
            poss_H = None
            trough_index = len(conf_TLs) - 1
            peak_index = len(conf_PHs) - 1
            
            # try to find the HH
            if conf_PHs[peak_index].turn_time > conf_TLs[trough_index].turn_time:
                # this means the peak comes after the trough - which we want to find the HH
                poss_HH = conf_PHs[peak_index]
                # do we see more peaks before the trough?
                peak_index -= 1
                while True:
                    if peak_index < 0:
                        return (False, StratDirection.Nothing, None, None, 0.0)
                    if conf_PHs[peak_index].turn_time > conf_TLs[trough_index].turn_time:
                        peak_index -= 1
                    else:
                        break
            else:
                # we found a trough at the end - this only works if it is within the HH and L - but that's harder to find
                # this code will ignore one TROUGH found between the HH and the CLL, if it sits within the HH and the L price
                trough_to_ignore = conf_TLs[trough_index]
                trough_index -= 1
                poss_HH = conf_PHs[peak_index]
                # do we see more peaks before the trough?
                peak_index -= 1
                while True:
                    if peak_index < 0:
                        return (False, StratDirection.Nothing, None, None, 0.0)
                    if conf_PHs[peak_index].turn_time > conf_TLs[trough_index].turn_time:
                        peak_index -= 1
                    else:
                        break
                poss_L = conf_TLs[trough_index]
                if trough_to_ignore.TP_low < poss_HH.TP_high and trough_to_ignore.TP_low > poss_L.TP_low:
                    # we found a trough that sits within the gap, so we can ignore it and carry on
                    pass
                else:
                    return (False, StratDirection.Nothing, None, None, 0.0)

            # try to find the L - this first Trough should be it.
            poss_L = conf_TLs[trough_index]
            # we may have more troughs backwards before we get to the H
            trough_index -= 1
            while True:
                if trough_index < 0:
                    return (False, StratDirection.Nothing, None, None, 0.0)
                if conf_TLs[trough_index].turn_time > conf_TLs[trough_index].turn_time:
                    trough_index -= 1
                else:
                    break
            # now we should have found the next H backwards
            poss_H = conf_PHs[peak_index]

            if poss_HH.TP_high >= poss_H.TP_high and my_low_close <= poss_L.TP_low:
                # reverted to >= <= because of missing CHH5 in the test
                # we have a HLHHCLL
                # now make sure the bars before wouldn't have already hit it
                my_low = round(poss_L.TP_low, 5)
                my_high = round(poss_H.TP_high, 5)
                my_higher_high = round(poss_HH.TP_high, 5)
                my_breakout_price = round(my_low_close, 5)
                my_breakout_time = my_bars[0].Time
                my_mt4_time = fusion_utils.get_times(my_breakout_time, 'us')['mt4']
                # check this isn't a weird one with the H less than the L -- which is an odd pattern
                if my_high < my_low:
                    return (False, StratDirection.Nothing, None, None, 0.0)
                for i in range(1, my_bars.Count):
                    if my_colours[i] == RED:
                        # we have another RED bar that maybe was the CLL earlier - do not want to repeat
                        if my_bars[i].Bid.Close < my_low:
                            # an earlier RED bar was a CLL, so don't report this as a breakout - it will have been done before
                            return (False, StratDirection.Nothing, None, None, 0.0)
                        if my_bars[i].Bid.Close > my_low:
                            break
                    # ignore GREENs - we don't care about them
                if logging and not sender.IsWarmingUp: sender.Log(f"Found HLHHCLL Brad breakout {my_mt4_time} {symbol} {chart_res} CLL: {my_breakout_price} HH:{my_higher_high} L:{my_low} H:{my_high}") 
                my_PHs.append(poss_H)
                my_PHs.append(poss_HH)
                my_TLs.append(poss_L)
                return (True, direction, my_TLs, my_PHs, my_low_close)

        return (False, StratDirection.Nothing, None, None, 0.0)


    def log_tracking_stats(self,sender):
        symbol = self.Symbol
        sender.Log(f"Output Tracking Stats: {symbol}")
        sender.Log(f"Day      - Hi: {self.HighAskCurrDay} Lo: {self.LowAskCurrDay} Prev Hi: {self.HighPrevDay} Prev Lo: {self.LowPrevDay}")
        sender.Log(f"Week     - Hi: {self.HighCurrWeek} Lo: {self.LowCurrWeek} Prev Hi: {self.HighPrevWeek} Prev Lo: {self.LowPrevWeek}")
        sender.Log(f"Month    - Hi: {self.HighCurrMonth} Lo: {self.LowCurrMonth} Prev Hi: {self.HighPrevMonth} Prev Lo: {self.LowPrevMonth}")
        sender.Log(f"24H roll - Hi: {self.high_rolling_24H} Lo: {self.low_rolling_24H} ")
        
