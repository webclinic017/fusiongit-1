//+------------------------------------------------------------------+
//|                                          Fusion_EHEL_plotter.mq4 |
//|                                     Plotting output data on MT4  |
//|                 This is for the External Highs and External Lows |
//+------------------------------------------------------------------+
#property   copyright "Fusion 2022"
#property   version   "5.1"
#property   strict
#property   indicator_chart_window

string         file_name="EH_EL_dump.csv"; //set filename here
bool           is_header_included=True;   //IMPORTANT if no header then set to false
long           current_chart_id=ChartID();
color          marker_col; 
string         marker_name;
string         tooltip_text;
int            chart_period;
string         chart_pair;
bool           period_check;
bool           symbol_check;
int            timeframe_enum;
ENUM_ANCHOR_POINT    anchor;

//SI ToDo's
//filter by symbol
//filter by chart resolution
//draw line that continues to new EH or EL

//+------------------------------------------------------------------+
//| Structure for storing imported data ... create arrays             |
//+------------------------------------------------------------------+
   string      symbol[9999];               //currency pair  
   string      chart_res[9999];            //chart resolution
   datetime    dt_data[9999];              //datetime
   string      eh_or_el[9999];             //EH or EL
   double      value[9999];                //value
   string      label[9999];                //EH or EL label
   double      gap_pips[9999];             //pip difference between current EH and EL
   string      move_type[9999];            //move type that created the new EH or EL - useful for visual debugging
   string      template_trend[9999];       //downtrend, transition, Downtrend
  
//+------------------------------------------------------------------+
//|  Initiation                                                      |
//+------------------------------------------------------------------+
int init()
  {
   IndicatorShortName("Fusion: EH/EL Plotter");                 
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
         dt_data[x]=FileReadDatetime(file_handle);
         eh_or_el[x]=FileReadString(file_handle);
         value[x]=FileReadNumber(file_handle);
         label[x]=FileReadString(file_handle);
         gap_pips[x]=FileReadNumber(file_handle);
         move_type[x]=FileReadString(file_handle);
         template_trend[x]=FileReadString(file_handle);
         
         if((is_header_included && x>0) || is_header_included==false) 
         //ie dont plot the header line, but needs to be read in
            {
               //now we need to check resolution and symbol and filter on that basis
               period_check=False;
               symbol_check=False;         
               if(symbol[x]==chart_pair){symbol_check=True;}
               timeframe_enum=parse_period_check_enum(chart_res[x]);  //get enum value of current chart resolution               
               if(timeframe_enum==chart_period){period_check=True;}  //check resolutions match
                                                                             
               if(period_check && symbol_check) //only plot if both checks pass
                 {                                                                                       
                     CreateNewTrendLine(x, symbol[x], chart_res[x], dt_data[x], eh_or_el[x], value[x], label[x], move_type[x], gap_pips[x], template_trend[x]);                                                                                    
                 }              
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
//|  Function to create chart trend lines                            |
//+------------------------------------------------------------------+
void CreateNewTrendLine(int x, string current_symbol, string chart_res_name, datetime candle_time, string eh_or_el_type, double eh_or_el_value, string eh_or_el_label,
     string move_type_str, double gap_pips_amt, string template_trend_str)
{
     
      int         shift=iBarShift(current_symbol,timeframe_enum, candle_time);
      datetime    fromtime=iTime(current_symbol,timeframe_enum,shift+1);  
      datetime    totime=iTime(current_symbol,timeframe_enum,shift-1); 
      string      eh_or_el_name;
         
     if(eh_or_el_type=="EH")
      {           
          eh_or_el_name="eh_line"+IntegerToString(x);           
          marker_name = "eh_marker"+IntegerToString(x);   
          anchor=ANCHOR_LEFT_LOWER;                     
      }
     else
      {
         eh_or_el_name="el_line"+IntegerToString(x);           
         marker_name="el_marker"+IntegerToString(x);
         anchor=ANCHOR_LEFT_UPPER;         
     }

     marker_col=parse_template(template_trend_str);
          
     ObjectCreate(current_chart_id, eh_or_el_name,OBJ_TREND,0,fromtime, eh_or_el_value, totime, eh_or_el_value);                        
     ObjectSetInteger(current_chart_id, eh_or_el_name,OBJPROP_COLOR,clrAntiqueWhite);
     ObjectSetInteger(current_chart_id, eh_or_el_name,OBJPROP_STYLE,STYLE_DOT);
     ObjectSetInteger(current_chart_id, eh_or_el_name,OBJPROP_WIDTH,2);
     ObjectSet(eh_or_el_name, OBJPROP_RAY,False);   
     
     
     ObjectCreate(current_chart_id,marker_name,OBJ_TEXT,0,fromtime, eh_or_el_value);    
     ObjectSetString(current_chart_id,marker_name,OBJPROP_TEXT, eh_or_el_label);
     ObjectSetInteger(current_chart_id,marker_name,OBJPROP_COLOR,marker_col);
     ObjectSetInteger(current_chart_id,marker_name,OBJPROP_FONTSIZE,12);   
     ObjectSetInteger(current_chart_id,marker_name,OBJPROP_ANCHOR,anchor);    //--- set anchor type              
     tooltip_text=StringConcatenate("Chart: ", chart_res[x], "\nDate/Time: ", dt_data[x], "\nValue: ", value[x], "\nPair: ", symbol[x], "\nMoved How: ", parse_move_type(move_type_str), "\nTemplate: ",template_trend_str);
     ObjectSetString(current_chart_id,marker_name,OBJPROP_TOOLTIP,tooltip_text);  
 
}



//+------------------------------------------------------------------+
//| Function to parse chart_res into period_check ENUM               |
//+------------------------------------------------------------------+
//https://docs.mql4.com/constants/chartconstants/enum_timeframes
int parse_period_check_enum(string passed_chart_res)
  {   
   timeframe_enum=0;   
      if (passed_chart_res=="ChartRes.res1H"){timeframe_enum=60;}
      else if(passed_chart_res=="ChartRes.res30M"){timeframe_enum=30;}
      else if(passed_chart_res=="ChartRes.res15M"){timeframe_enum=15;}
      else if(passed_chart_res=="ChartRes.res5M"){timeframe_enum=5;}

    return(timeframe_enum);                                                                      
  }
     
//+------------------------------------------------------------------+
//| Function to parse move_type                                      |
//+------------------------------------------------------------------+
string parse_move_type(string passed_move_type)
  {   
      string   move_type_str="";   
      if (passed_move_type=="pull"){move_type_str="Pulled";}
      else {move_type_str="Expanded";}
    return(move_type_str);                                                                      
  }

//+------------------------------------------------------------------+
//| Function to parse template                                      |
//+------------------------------------------------------------------+
color parse_template(string &template_trend_str)
  {          
      if (template_trend_str=="Downtrend"){return Red;}
      else if (template_trend_str=="Uptrend"){return Green;}
      else {return AntiqueWhite;}                                                                     
  }  
    
//+------------------------------------------------------------------+
