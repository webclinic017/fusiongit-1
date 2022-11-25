# Structs and enums used throughout

import enum

class t_p_status(enum.Enum):
    empty = 1
    pre_turn = 2
    post_turn = 3
    confirmed = 4
    invalidated = 5
    
class Strats(enum.Enum):
    ManualTrigger = 1
    Channel = 3
    Lunge = 4
    Narnia = 5
    Perfect1 = 6
    BradPerfect = 7
    Nothing = 99

class StratDirection(enum.Enum):
    Long = 1
    Short = 2
    Hold = 3
    Nothing = 99
    
class StratResolution(enum.Enum):
    res5M = 1
    res15M = 2
    res30M = 3
    res1H = 4
    res4H = 5
    res24H = 6
    Nothing = 99
    
class ChartRes(enum.Enum):
    res24H = 1
    res4H = 2
    res1H = 3
    res30M = 4
    res15M = 5
    res5M = 6
    res1M = 7
    
class SymbolStates(enum.Enum):
    looking = 0
    possible_trade = 1
    entry_hunt = 2
    entry_confirmation = 3
    trading = 4
    clearing = 5
    paused = 6

class SessionNames(enum.Enum):
    Pre_Asia = 0
    Asia = 1
    Europe = 2
    Pre_US = 3
    US = 4
    Unknown = 5

    
class Trends(enum.Enum):
    Uptrend = 0
    Downtrend = 1 
    SidewaysUp = 2
    SidewaysDown = 3
    Nothing = 4

class EHELTrends(enum.Enum):
    Uptrend = 0
    Downtrend = 1 
    Transition = 2
    Unknown = 3
    
class FTIActions(enum.Enum):
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


class TradingWindow(enum.Enum):
    TW1 = 0
    TW2 = 1 
    TW3 = 2
    Closed = 3


class CandleType(enum.Enum):
    Unknown = 0
    BullishTrendBar = 1
    BearishTrendBar = 2
    BullishPinBar = 3
    BearishPinBar = 4
    BullishIceCreamBar = 5
    BearishIceCreamBar = 6



    
GREEN = 0
RED = 1
BLACK = 2
day = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

