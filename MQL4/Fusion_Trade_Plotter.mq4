//+------------------------------------------------------------------+
//|                                         Fusion_Trade_plotter.mq4 |
//|                                     Plotting output data on MT4  |
//|                           This is for the Perfect Trades spotted |
//+------------------------------------------------------------------+
#property   copyright "Fusion 2022"
#property   version   "1.00"
#property   strict
#property   description "Marks perfect trades spotted. 1 min chart only."
#property   indicator_chart_window

string         file_name="tbu_perfects_dump.csv"; //set filename here
bool           is_header_included=True;
long           current_chart_id=ChartID();
string         marker_name;
string         tooltip_text;
int            chart_period;
string         chart_pair;
bool           period_check;
bool           symbol_check;
int            timeframe_enum;
color          marker_col;
ENUM_ANCHOR_POINT    anchor;


//SI ToDo's
//figure out where to plot more accurately the elements
//filter by symbol
//filter by chart resolution

//+------------------------------------------------------------------+
//| Structure for storing imported data ... create arrays            |
//+------------------------------------------------------------------+
string      symbol[9999];               //currency pair
string      chart_res[9999];            //chart resolution
string      bo_label[9999];
datetime    update_time[9999];
string      pos1_label[9999];
double      pos1_price[9999];
datetime    pos1_time[9999];
string      pos2_label[9999];
double      pos2_price[9999];
datetime    pos2_time[9999];
string      pos3_label[9999];
double      pos3_price[9999];
datetime    pos3_time[9999];
string      pos4_label[9999];
double      pos4_price[9999];
datetime    pos4_time[9999];
double      pullback1_price[9999];
double      EH_price[9999];
double      EL_price[9999];
string      tw[9999];
string      pb_status[9999];
bool        pb_hit[9999];
datetime    pb_time_hit[9999];
bool        ignore_200ema[9999];
string      squeeze_status[9999];
datetime    squeeze_time[9999];          //file calls this squeeze time, but means entry time
double      squeeze_price[9999];
bool        enter_trade[9999];
string      reason_notes[9999];
datetime    entry_time[9999];
double      ema9_1m[9999];
double      ema45_1m[9999];
double      ema135_1m[9999];
double      ema200_1m[9999];
double      last_1m_peak[9999];
double      last_1m_trough[9999];
string      trend_5m[9999];
double      stop_pips[9999];
double      stop_price[9999];
string      stop_comments[9999];
double      take_profit_pips[9999];
double      take_profit_price[9999];
string      take_profit_comments[9999];
double      move_breakeven[9999];
double      result_pips[9999];
double      spread_pips[9999];

//+------------------------------------------------------------------+
//|  Initiation                                                      |
//+------------------------------------------------------------------+
int init()
  {
//--- enable object create events
   ChartSetInteger(ChartID(),CHART_EVENT_OBJECT_CREATE,true);
//--- enable object delete events
   ChartSetInteger(ChartID(),CHART_EVENT_OBJECT_DELETE,true);
   IndicatorShortName("Fusion_BO_Perfect_plotter");
   //ObjectsDeleteAll();
   return(0);
  }

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int start()
  {
//--- open  file and parse data
   ResetLastError();

   chart_pair=ChartSymbol(current_chart_id);   //get current chart currency pair
   chart_period=ChartPeriod(current_chart_id);   //get the current chart resolution

   int file_handle=FileOpen(file_name, FILE_CSV|FILE_READ,',');
   if(file_handle!=INVALID_HANDLE)
     {
      if(file_handle==0)
        {
         Comment("File "+file_name+" not found.");
         return(0);
        }

      //-now read file data
      for(int x=0; !FileIsEnding(file_handle)&& x<9999 ; x++)   //set up loop... good 'ole x
        {
         if(FileIsEnding(file_handle))
           {
            break;
           }

         //-assign values based on data type
         symbol[x]=FileReadString(file_handle);
         chart_res[x]=FileReadString(file_handle);
         bo_label[x]=FileReadString(file_handle);
         update_time[x]=FileReadDatetime(file_handle);
         pos1_label[x]=FileReadString(file_handle);
         pos1_price[x]=FileReadNumber(file_handle);
         pos1_time[x]=FileReadDatetime(file_handle);
         pos2_label[x]=FileReadString(file_handle);
         pos2_price[x]=FileReadNumber(file_handle);
         pos2_time[x]=FileReadDatetime(file_handle);
         pos3_label[x]=FileReadString(file_handle);
         pos3_price[x]=FileReadNumber(file_handle);
         pos3_time[x]=FileReadDatetime(file_handle);
         pos4_label[x]=FileReadString(file_handle);
         pos4_price[x]=FileReadNumber(file_handle);
         pos4_time[x]=FileReadDatetime(file_handle);
         pullback1_price[x]=FileReadNumber(file_handle);
         EH_price[x]=FileReadNumber(file_handle);
         EL_price[x]=FileReadNumber(file_handle);
         tw[x]=FileReadString(file_handle);
         pb_status[x]=FileReadString(file_handle);
         pb_hit[x]=FileReadBool(file_handle);
         pb_time_hit[x]=FileReadDatetime(file_handle);
         ignore_200ema[x]=FileReadBool(file_handle);
         squeeze_status[x]=FileReadString(file_handle);
         squeeze_time[x]=FileReadDatetime(file_handle);
         squeeze_price[x]=FileReadNumber(file_handle);
         enter_trade[x]=FileReadBool(file_handle);
         reason_notes[x]=FileReadString(file_handle);
         entry_time[x]=FileReadDatetime(file_handle);
         ema9_1m[x]=FileReadNumber(file_handle);
         ema45_1m[x]=FileReadNumber(file_handle);
         ema135_1m[x]=FileReadNumber(file_handle);
         ema200_1m[x]=FileReadNumber(file_handle);
         last_1m_peak[x]=FileReadNumber(file_handle);
         last_1m_trough[x]=FileReadNumber(file_handle);
         trend_5m[x]=FileReadString(file_handle);
         stop_pips[x]=FileReadNumber(file_handle);
         stop_price[x]=FileReadNumber(file_handle);
         stop_comments[x]=FileReadString(file_handle);
         take_profit_pips[x]=FileReadNumber(file_handle);
         take_profit_price[x]=FileReadNumber(file_handle);         
         take_profit_comments[x]=FileReadString(file_handle);
         move_breakeven[x]=FileReadNumber(file_handle);
         result_pips[x]=FileReadNumber(file_handle);
         spread_pips[x]=FileReadNumber(file_handle);

         if((is_header_included && x>0) || is_header_included==false)  //ie dont plot the header line, but needs to be read in
           {
            //now we need to check resolution and symbol and filter on that basis
            period_check=False;
            symbol_check=False;

            if(symbol[x]==chart_pair)
              {
               symbol_check=True;  //check symbol matches chart symbol
              }

            period_check=True;  //afterwards lets check to make sure we are on the one minute

            //if(period_check && symbol_check) //only plot if both checks pass
            //{
            if(enter_trade[x])
              {

               CreateNewPBLine(pullback1_price[x], pos4_time[x], pb_time_hit[x], x, squeeze_status[x], chart_res[x], symbol[x]);
               bool trade_direction;
               if(pos4_label[x]=="CHH")
                 {
                  trade_direction=True;
                 }
               else
                 {
                  trade_direction=False;
                 }
               CreateTradeEntryMarker(bo_label[x], squeeze_price[x], squeeze_time[x], trade_direction, x, chart_res[x], symbol[x]);
               CreateNewBELine(move_breakeven[x], entry_time[x], x, squeeze_status[x], chart_res[x], symbol[x]);
              }
            //}
           }//header

        }// close loop

      FileClose(file_handle);

     }
   else
     {
      Print("File Not Found. OR... File Must Be Open...");
     }
   return(0);
  }


//+------------------------------------------------------------------+
//| Function to create the breakeven line                         |
//+------------------------------------------------------------------+
void CreateNewBELine(double move_to_breakeven, datetime &be_fromtime, int &x, string &breakout_label, string &chart_res_name, string &current_symbol)
  {

//the principle of line length here will be to go from the candle after the L or H trendline and continnue to 3 candles after the CHH or CLL

   string be_name="be_line"+IntegerToString(x);
   ObjectCreate(current_chart_id,be_name,OBJ_TREND,0,be_fromtime, move_to_breakeven, be_fromtime, move_to_breakeven);
   ObjectSetInteger(current_chart_id,be_name,OBJPROP_COLOR,clrAquamarine);
   ObjectSetInteger(current_chart_id,be_name,OBJPROP_STYLE,STYLE_DOT);
   ObjectSetInteger(current_chart_id,be_name,OBJPROP_WIDTH,2);
   ObjectSet(be_name, OBJPROP_RAY,False);

   string be_marker="be_marker"+IntegerToString(x);
   ObjectCreate(current_chart_id,be_marker,OBJ_TEXT,0,be_fromtime, move_to_breakeven);
   ObjectSetString(current_chart_id,be_marker,OBJPROP_TEXT,"------- Move to Break Even ------");
   ObjectSetInteger(current_chart_id,be_marker,OBJPROP_FONTSIZE,10);
   ObjectSetInteger(current_chart_id,be_marker,OBJPROP_COLOR,clrAquamarine);
   ObjectSetInteger(current_chart_id,be_marker,OBJPROP_ANCHOR,ANCHOR_LEFT);    //--- set anchor type
   tooltip_text=StringConcatenate("Move to Breakeven: ", move_to_breakeven);
   ObjectSetString(current_chart_id,be_marker,OBJPROP_TOOLTIP,tooltip_text);

  }


//+------------------------------------------------------------------+
//| Function to create the trade entry marker                          |
//+------------------------------------------------------------------+
void CreateTradeEntryMarker(string breakout_label, double t_squeeze_price, datetime t_squeeze_time, bool &trade_direction, int &x, string &chart_res_name, string &current_symbol)
  {

   string te_marker="te_marker"+IntegerToString(x);
   int arrow_code;
   double plotprice;


   int shift=iBarShift(current_symbol,timeframe_enum, t_squeeze_time);

   if(trade_direction) //long
     {
      arrow_code=241;
      anchor=ANCHOR_BOTTOM;
      plotprice=iHigh(current_symbol,timeframe_enum,shift);
      marker_col=Green;
     }
   else
     {
      arrow_code=242;
      anchor=ANCHOR_TOP;
      plotprice=iLow(current_symbol,timeframe_enum,shift);
      marker_col=Red;
     }

   ObjectCreate(current_chart_id,te_marker,OBJ_ARROW_BUY,0,t_squeeze_time, plotprice);
   ObjectSet(te_marker,OBJPROP_ARROWCODE,arrow_code);
   ObjectSet(te_marker,OBJPROP_COLOR,marker_col);
   ObjectSetInteger(current_chart_id,te_marker,OBJPROP_WIDTH,12);
   ObjectSetInteger(current_chart_id,te_marker,OBJPROP_ANCHOR,anchor);    //--- set anchor type
   tooltip_text=StringConcatenate("BO_label: ", breakout_label, "\nEntry: ", t_squeeze_time, "\nEntry Price: ", t_squeeze_price, "\nPair: ", current_symbol);
   ObjectSetString(current_chart_id,te_marker,OBJPROP_TOOLTIP,tooltip_text);

   string te_text="te_text"+IntegerToString(x);
   ObjectCreate(current_chart_id,te_text,OBJ_TEXT,0,t_squeeze_time, plotprice);
   ObjectSetString(current_chart_id,te_text,OBJPROP_TEXT,breakout_label);
   ObjectSetInteger(current_chart_id,te_text,OBJPROP_FONTSIZE,10);
   ObjectSetInteger(current_chart_id,te_text,OBJPROP_COLOR,AntiqueWhite);
   ObjectSetInteger(current_chart_id,te_text,OBJPROP_ANCHOR,ANCHOR_RIGHT_LOWER);    //--- set anchor type
   tooltip_text=StringConcatenate("BO_label: ", breakout_label, "\nChart: ", chart_res_name, "\nValue: ", t_squeeze_price, "\nPair: ", current_symbol);
   ObjectSetString(current_chart_id,te_text,OBJPROP_TOOLTIP,tooltip_text);


  }


//+------------------------------------------------------------------+
//| Function to create the PB channel line                           |
//+------------------------------------------------------------------+
void CreateNewPBLine(double &trend_plot_price, datetime &pb_fromtime, datetime &pb_totime, int &x, string &breakout_label, string &chart_res_name, string &current_symbol)
  {

//the principle of line length here will be to go from the candle after the L or H trendline and continnue to 3 candles after the CHH or CLL

   string pb_name="pb_line"+IntegerToString(x);
   ObjectCreate(current_chart_id,pb_name,OBJ_TREND,0,pb_fromtime, trend_plot_price, pb_totime, trend_plot_price);
   ObjectSetInteger(current_chart_id,pb_name,OBJPROP_COLOR,clrPurple);
   ObjectSetInteger(current_chart_id,pb_name,OBJPROP_STYLE,STYLE_DOT);
   ObjectSetInteger(current_chart_id,pb_name,OBJPROP_WIDTH,2);
   ObjectSet(pb_name, OBJPROP_RAY,False);

   string pb_marker="pb_marker"+IntegerToString(x);
   ObjectCreate(current_chart_id,pb_marker,OBJ_TEXT,0,pb_totime, trend_plot_price);
   ObjectSetString(current_chart_id,pb_marker,OBJPROP_TEXT,"   PB1 - Hit");
   ObjectSetInteger(current_chart_id,pb_marker,OBJPROP_FONTSIZE,10);
   ObjectSetInteger(current_chart_id,pb_marker,OBJPROP_COLOR,clrPurple);
   ObjectSetInteger(current_chart_id,pb_marker,OBJPROP_ANCHOR,ANCHOR_LEFT);    //--- set anchor type
   tooltip_text=StringConcatenate("BO_label: ", breakout_label, "\nChart: ", chart_res_name, "\nValue: ", trend_plot_price, "\nPair: ", current_symbol);
   ObjectSetString(current_chart_id,pb_marker,OBJPROP_TOOLTIP,tooltip_text);

  }


//+------------------------------------------------------------------+
//| Function to create the EHEL channel                              |
//+------------------------------------------------------------------+
void CreateNewEHELChannel(datetime start_time, datetime end_time, double high_price, double low_price, string &current_symbol,
                          int &x, string &chart_res_name, string &breakout_label)
  {


   int shift;
   shift=iBarShift(current_symbol,timeframe_enum, start_time);
   datetime ehel_fromtime=iTime(current_symbol,timeframe_enum,shift);
   shift=iBarShift(current_symbol,timeframe_enum, end_time);
   datetime ehel_totime=iTime(current_symbol,timeframe_enum,shift-1);


   string EH_name="eh_line"+IntegerToString(x);
   ObjectCreate(current_chart_id,EH_name,OBJ_TREND,0,ehel_fromtime, high_price, ehel_totime, high_price);
   ObjectSetInteger(current_chart_id,EH_name,OBJPROP_COLOR,clrDarkOliveGreen);
   ObjectSetInteger(current_chart_id,EH_name,OBJPROP_STYLE,STYLE_DASH);
   ObjectSetInteger(current_chart_id,EH_name,OBJPROP_WIDTH,2);
   ObjectSet(EH_name, OBJPROP_RAY,False);

   string EH_marker="eh_marker"+IntegerToString(x);
   ObjectCreate(current_chart_id,EH_marker,OBJ_TEXT,0,ehel_fromtime, high_price);
   ObjectSetString(current_chart_id,EH_marker,OBJPROP_TEXT,"EH");
   ObjectSetInteger(current_chart_id,EH_marker,OBJPROP_FONTSIZE,10);
   ObjectSetInteger(current_chart_id,EH_marker,OBJPROP_COLOR,clrAntiqueWhite);
   ObjectSetInteger(current_chart_id,EH_marker,OBJPROP_ANCHOR,ANCHOR_LEFT_LOWER);    //--- set anchor type
   tooltip_text=StringConcatenate("BO_label: ", breakout_label, "\nChart: ", chart_res_name, "\nValue: ", high_price, "\nPair: ", current_symbol);
   ObjectSetString(current_chart_id,EH_marker,OBJPROP_TOOLTIP,tooltip_text);


   string EL_name="el_line"+IntegerToString(x);
   ObjectCreate(current_chart_id,EL_name,OBJ_TREND,0,ehel_fromtime, low_price, ehel_totime, low_price);
   ObjectSetInteger(current_chart_id,EL_name,OBJPROP_COLOR,clrDarkOliveGreen);
   ObjectSetInteger(current_chart_id,EL_name,OBJPROP_STYLE,STYLE_DASH);
   ObjectSetInteger(current_chart_id,EL_name,OBJPROP_WIDTH,2);
   ObjectSet(EL_name, OBJPROP_RAY,False);

   string EL_marker="el_marker"+IntegerToString(x);
   ObjectCreate(current_chart_id,EL_marker,OBJ_TEXT,0,ehel_fromtime, low_price);
   ObjectSetString(current_chart_id,EL_marker,OBJPROP_TEXT,"EL");
   ObjectSetInteger(current_chart_id,EL_marker,OBJPROP_FONTSIZE,10);
   ObjectSetInteger(current_chart_id,EL_marker,OBJPROP_COLOR,clrAntiqueWhite);
   ObjectSetInteger(current_chart_id,EL_marker,OBJPROP_ANCHOR,ANCHOR_LEFT_UPPER);    //--- set anchor type
   tooltip_text=StringConcatenate("BO_label: ", breakout_label, "\nChart: ", chart_res_name, "\nValue: ", low_price, "\nPair: ", current_symbol);
   ObjectSetString(current_chart_id,EL_marker,OBJPROP_TOOLTIP,tooltip_text);


  }

//+------------------------------------------------------------------+
//| Event to handle chart change of period or currency               |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {

   chart_pair=ChartSymbol(current_chart_id);   //get current chart currency pair
   chart_period=ChartPeriod(current_chart_id);   //get the current chart resolution
  }


//+------------------------------------------------------------------+
//| Function to parse chart_res into period_check ENUM              |
//+------------------------------------------------------------------+
//https://docs.mql4.com/constants/chartconstants/enum_timeframes

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
int parse_period_check_enum(string passed_chart_res)
  {
   int return_enum_value=0;
   if(passed_chart_res=="ChartRes.res1H")
     {
      return_enum_value=60;
     }
   else
      if(passed_chart_res=="ChartRes.res30M")
        {
         return_enum_value=30;
        }
      else
         if(passed_chart_res=="ChartRes.res15M")
           {
            return_enum_value=15;
           }
         else
            if(passed_chart_res=="ChartRes.res5M")
              {
               return_enum_value=5;
              }

   return(return_enum_value);
  }

//+------------------------------------------------------------------+
