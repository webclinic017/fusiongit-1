//+------------------------------------------------------------------+
//|                                    Fusion_BO_Perfect_plotter.mq4 |
//|                                     Plotting output data on MT4  |
//|                      This is for the Perfect BO patterns spotted |
//+------------------------------------------------------------------+
#property   copyright "Fusion 2022"
#property   version   "4.05"
#property   strict
#property   description "Script draws trends lines and plots spotted BO's."
#property   indicator_chart_window

#include <stdlib.mqh>

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
   ObjectsDeleteAll();
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

   int file_handle=FileOpen(file_name, FILE_CSV|FILE_SHARE_READ,',');
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

            timeframe_enum=parse_period_check_enum(chart_res[x]);  //get enum value of current chart resolution
            if(timeframe_enum==chart_period)
              {
               period_check=True;  //check resolutions match
              }
            period_check=True;   //overwrite

            if(period_check && symbol_check) //only plot if both checks pass
              {

               CreateNewTrendLine(pos1_label[x], pos1_time[x], "pos1", symbol[x], x, chart_res[x], bo_label[x], pos4_label[x], pos4_time[x]);
               CreateNewTrendLine(pos2_label[x], pos2_time[x], "pos2", symbol[x], x, chart_res[x], bo_label[x], pos4_label[x], pos4_time[x]);
               CreateNewTrendLine(pos3_label[x], pos3_time[x], "pos3", symbol[x], x, chart_res[x], bo_label[x], pos4_label[x], pos4_time[x]);
               CreateNewTrendLine(pos4_label[x], pos4_time[x], "pos4", symbol[x], x, chart_res[x], bo_label[x], pos4_label[x], pos4_time[x]);

               CreateNewEHELChannel(pos1_time[x], pos4_time[x], EH_price[x], EL_price[x], symbol[x], x, chart_res[x], bo_label[x]);

              }
           }//header

        }// close loop

      FileClose(file_handle);

     }
   else
     {
      //this gets error and then looks up description from the include file
      int check;
      check=GetLastError();
      if(check!=ERR_NO_ERROR)
         Print("Error: ",ErrorDescription(check));
      FileClose(file_handle);
     }
   return(0);
  }

//+------------------------------------------------------------------+
//|  Function to create chart trend lines                            |
//+------------------------------------------------------------------+
void CreateNewTrendLine(string &pos_label, datetime candle_time, string marker_position, string current_symbol, int x,
                        string chart_res_name, string breakout_label, string breakout_type, datetime close_position)
  {

   int      shift=iBarShift(current_symbol,timeframe_enum, candle_time);
   double   highprice=iHigh(current_symbol,timeframe_enum,shift);
   double   lowprice=iLow(current_symbol,timeframe_enum,shift);
   double   closeprice=iClose(current_symbol,timeframe_enum,shift);
   datetime fromtime=iTime(current_symbol,timeframe_enum,shift+1);
   datetime totime=iTime(current_symbol,timeframe_enum,shift-1);
   double   trend_plot_price; //just declare it here, then pass between the functions
   int      shift_close_position=iBarShift(current_symbol,timeframe_enum, close_position);   //this is the bar number of the close candle


   marker_name=pos_label+"trendline"+IntegerToString(x);
   string marker_label;

   if(pos_label=="L")
     {
      trend_plot_price=lowprice-0.0005;
      anchor=ANCHOR_LEFT_UPPER;
      if(breakout_type=="CLL")
        {
         //now plot the PB from this point
         datetime pb_fromtime=iTime(current_symbol,timeframe_enum,shift-1);
         datetime pb_totime=iTime(current_symbol,timeframe_enum,shift_close_position-5);
         CreateNewPBLine(trend_plot_price,pb_fromtime, pb_totime, x, breakout_label, chart_res_name, current_symbol);
        }
      marker_label=pos_label;
     }
   else
      if(pos_label=="LL")
        {

         trend_plot_price=lowprice-0.0005;
         anchor=ANCHOR_LEFT_UPPER;
         marker_label=pos_label;
        }
      else
         if(pos_label=="H")
           {
            trend_plot_price=highprice+0.0005;
            anchor=ANCHOR_LEFT_LOWER;
            if(breakout_type=="CHH")
              {
               //now plot the PB from this point
               datetime pb_fromtime=iTime(current_symbol,timeframe_enum,shift-1);
               datetime pb_totime=iTime(current_symbol,timeframe_enum,shift_close_position-12);
               CreateNewPBLine(trend_plot_price,pb_fromtime, pb_totime, x, breakout_label, chart_res_name, current_symbol);
              }
            marker_label=pos_label;

           }
         else
            if(pos_label=="HH")
              {
               trend_plot_price=highprice+0.0005;
               anchor=ANCHOR_LEFT_LOWER;
               marker_label=pos_label;
              }
            else
               if(pos_label=="CHH")
                 {
                  trend_plot_price=closeprice;
                  anchor=ANCHOR_LEFT_LOWER;
                  marker_label=breakout_label;
                 }
               else
                 {
                  trend_plot_price=closeprice;
                  anchor=ANCHOR_LEFT_UPPER;
                  marker_label=breakout_label;
                 }

   ObjectCreate(current_chart_id,marker_name,OBJ_TREND,0,fromtime, trend_plot_price, totime, trend_plot_price);
   ObjectSetInteger(current_chart_id,marker_name,OBJPROP_COLOR,clrPurple);
   ObjectSetInteger(current_chart_id,marker_name,OBJPROP_STYLE,STYLE_SOLID);
   ObjectSetInteger(current_chart_id,marker_name,OBJPROP_WIDTH,3);
   ObjectSet(marker_name, OBJPROP_RAY,False);
// tooltip_text=StringConcatenate("BO_label: ", breakout_label, "\nChart: ", chart_res_name, "\nDatetime: ", candle_time, "\nValue: ", trend_plot_price, "\nPair: ", current_symbol);
// ObjectSetString(current_chart_id,marker_name,OBJPROP_TOOLTIP,tooltip_text);

//now handle the label better sited
   marker_name = pos_label+IntegerToString(x);
   ObjectCreate(current_chart_id,marker_name,OBJ_TEXT,0,fromtime, trend_plot_price);
   ObjectSetString(current_chart_id,marker_name,OBJPROP_TEXT,marker_label);
   ObjectSetInteger(current_chart_id,marker_name,OBJPROP_FONTSIZE,10);
   ObjectSetInteger(current_chart_id,marker_name,OBJPROP_COLOR,clrAntiqueWhite);
   ObjectSetInteger(current_chart_id,marker_name,OBJPROP_ANCHOR,anchor);    //--- set anchor type
   tooltip_text=StringConcatenate("BO_label: ", breakout_label, "\nChart: ", chart_res_name, "\nDatetime: ", candle_time, "\nValue: ", trend_plot_price, "\nPair: ", current_symbol);
   ObjectSetString(current_chart_id,marker_name,OBJPROP_TOOLTIP,tooltip_text);

  }



//+------------------------------------------------------------------+
//| Function to create the PB channel line                           |
//+------------------------------------------------------------------+
void CreateNewPBLine(double &trend_plot_price, datetime &pb_fromtime, datetime &pb_totime, int &x, string &breakout_label, string &chart_res_name, string &current_symbol)
  {

//the principle of line length here will be to go from the candle after the L or H trendline and continnue to 3 candles after the CHH or CLL

   string pb_name="pb_line"+IntegerToString(x);
   ObjectCreate(current_chart_id,pb_name,OBJ_TREND,0,pb_fromtime, trend_plot_price, pb_totime, trend_plot_price);
   ObjectSetInteger(current_chart_id,pb_name,OBJPROP_COLOR,clrAntiqueWhite);
   ObjectSetInteger(current_chart_id,pb_name,OBJPROP_STYLE,STYLE_DOT);
   ObjectSetInteger(current_chart_id,pb_name,OBJPROP_WIDTH,2);
   ObjectSet(pb_name, OBJPROP_RAY,False);

   string pb_marker="pb_marker"+IntegerToString(x);
   ObjectCreate(current_chart_id,pb_marker,OBJ_TEXT,0,pb_totime, trend_plot_price);
   ObjectSetString(current_chart_id,pb_marker,OBJPROP_TEXT,"   PB1");
   ObjectSetInteger(current_chart_id,pb_marker,OBJPROP_FONTSIZE,10);
   ObjectSetInteger(current_chart_id,pb_marker,OBJPROP_COLOR,clrAquamarine);
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
