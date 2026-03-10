//+------------------------------------------------------------------+
//|                                              AegisTradeBridge.mq5|
//|                                  Copyright 2026, Aegis Trader    |
//|                                       https://www.aegistrader.io |
//+------------------------------------------------------------------+
#property copyright "Aegis Trader"
#property link      "https://www.aegistrader.io"
#property version   "1.00"
#property description "Native MQL5 execution bridge for Aegis Trader."
#property description "Polls the backend API for trade instructions."

#include <Trade\Trade.mqh>
#include <JAson.mqh> // Requires JAson library for JSON parsing

//--- input parameters
input string   BackendURL     = "http://127.0.0.1:8002/mt5/poll"; // URL of the backend API polling endpoint
input string   ApiSecret      = "changeme_mt5";                   // Secret key for API authentication
input int      PollIntervalMs = 1000;                             // Polling interval in milliseconds
input int      SlippagePips   = 10;                               // Maximum slippage in points
input ulong    MagicNumber    = 202600;                           // Magic number for orders

//--- global variables
CTrade         trade;
int            timer_id;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   // Initialize trade tracking
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetMarginMode();
   trade.SetTypeFillingBySymbol(Symbol());
   trade.SetDeviationInPoints(SlippagePips);

   // Set up the polling timer
   EventSetMillisecondTimer(PollIntervalMs);

   Print("Aegis Trade Bridge Initialized. Polling ", BackendURL, " every ", PollIntervalMs, "ms.");
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Print("Aegis Trade Bridge Deinitialized.");
  }

//+------------------------------------------------------------------+
//| Timer function (Polling)                                         |
//+------------------------------------------------------------------+
void OnTimer()
  {
   PollBackend();
  }

//+------------------------------------------------------------------+
//| Poll Backend API                                                 |
//+------------------------------------------------------------------+
void PollBackend()
  {
   string headers = "X-MT5-Secret: " + ApiSecret + "\r\nContent-Type: application/json\r\n";
   char post[], result[];
   string result_headers;

   int res = WebRequest("GET", BackendURL, headers, 5000, post, result, result_headers);
   
   if(res == 200)
     {
      string json_response = CharArrayToString(result);
      if (json_response != "{}" && json_response != "[]" && json_response != "") {
          ProcessCommands(json_response);
      }
     }
   else if(res != 200 && res != 404 && res != -1) // Ignore standard 404/timeouts if queue is empty
     {
      Print("HTTP Error polling backend: ", res, " Headers: ", result_headers);
     }
  }

//+------------------------------------------------------------------+
//| Process Commands from JSON                                       |
//+------------------------------------------------------------------+
void ProcessCommands(string json_string)
  {
   CJAVal json;
   if(json.Deserialize(json_string))
     {
      // Iterate through an array of commands
      if (json.GetType() == jtARRAY) {
          for(int i = 0; i < ArraySize(json.m_e); i++)
            {
             string action = json[i]["action"].ToStr();
             
             if(action == "place_order")
                 ExecutePlaceOrder(json[i]);
             else if(action == "close_partial")
                 ExecuteClosePartial(json[i]);
             else if(action == "modify_sl")
                 ExecuteModifySL(json[i]);
             else if (action == "get_positions")
                 ReportPositions();
            }
      } else if (json.GetType() == jtOBJECT) {
          // Single command
          string action = json["action"].ToStr();
          if(action == "place_order") ExecutePlaceOrder(json);
          else if(action == "close_partial") ExecuteClosePartial(json);
          else if(action == "modify_sl") ExecuteModifySL(json);
          else if (action == "get_positions") ReportPositions();
      }
     }
   else
     {
      Print("Failed to parse JSON response: ", json_string);
     }
  }

//+------------------------------------------------------------------+
//| Execute: Place Order                                             |
//+------------------------------------------------------------------+
void ExecutePlaceOrder(CJAVal &cmd)
  {
   string sym = cmd["symbol"].ToStr();
   string dir = cmd["direction"].ToStr();
   double lots = cmd["lot_size"].ToDbl();
   double sl = cmd["sl_price"].ToDbl();
   double tp = cmd["tp_price"].ToDbl(); // TP1
   string comment = cmd["comment"].ToStr();

   if (comment == "") comment = "AegisTrader";

   bool success = false;
   if(dir == "buy")
     {
      success = trade.Buy(lots, sym, 0, sl, tp, comment);
     }
   else if(dir == "sell")
     {
      success = trade.Sell(lots, sym, 0, sl, tp, comment);
     }

   if(success)
     {
      ulong ticket = trade.ResultOrder();
      Print("Order Placed Successfully: #", ticket, " ", dir, " ", lots, " ", sym);
      ReportExecutionResult(cmd["id"].ToStr(), "success", IntegerToString(ticket));
     }
   else
     {
      Print("Order Placement Failed: ", trade.ResultRetcode(), " - ", trade.ResultComment());
      ReportExecutionResult(cmd["id"].ToStr(), "error", trade.ResultComment());
     }
  }

//+------------------------------------------------------------------+
//| Execute: Close Partial                                           |
//+------------------------------------------------------------------+
void ExecuteClosePartial(CJAVal &cmd)
  {
   ulong ticket = (ulong)cmd["ticket"].ToInt();
   double lots = cmd["lot_size"].ToDbl();

   if(PositionSelectByTicket(ticket))
     {
      bool success = trade.PositionClosePartial(ticket, lots);
      if(success)
        {
         Print("Position #", ticket, " Partially Closed: ", lots, " lots");
         ReportExecutionResult(cmd["id"].ToStr(), "success", "");
        }
      else
        {
         Print("Partial Close Failed on #", ticket, ": ", trade.ResultRetcode());
         ReportExecutionResult(cmd["id"].ToStr(), "error", trade.ResultComment());
        }
     }
   else
     {
      Print("Position #", ticket, " not found for partial close.");
      ReportExecutionResult(cmd["id"].ToStr(), "error", "Position not found");
     }
  }

//+------------------------------------------------------------------+
//| Execute: Modify SL                                               |
//+------------------------------------------------------------------+
void ExecuteModifySL(CJAVal &cmd)
  {
   ulong ticket = (ulong)cmd["ticket"].ToInt();
   double new_sl = cmd["sl_price"].ToDbl();

   if(PositionSelectByTicket(ticket))
     {
      double current_tp = PositionGetDouble(POSITION_TP);
      bool success = trade.PositionModify(ticket, new_sl, current_tp);
      
      if(success)
        {
         Print("Position #", ticket, " SL Modified to ", new_sl);
         ReportExecutionResult(cmd["id"].ToStr(), "success", "");
        }
      else
        {
         Print("Modify SL Failed on #", ticket, ": ", trade.ResultRetcode());
         ReportExecutionResult(cmd["id"].ToStr(), "error", trade.ResultComment());
        }
     }
   else
     {
      Print("Position #", ticket, " not found for modify SL.");
      ReportExecutionResult(cmd["id"].ToStr(), "error", "Position not found");
     }
  }

//+------------------------------------------------------------------+
//| Report Positions (Push current state to backend)                 |
//+------------------------------------------------------------------+
void ReportPositions()
  {
    // Build JSON payload of all open positions matching MagicNumber
    CJAVal payload;
    payload["action"] = "sync_positions";
    // ... logic to build JSON array of positions and POST to backend ...
    // To keep this MVP simple, we rely on the backend tracking orders it placed, 
    // but full state sync goes here.
  }

//+------------------------------------------------------------------+
//| Report Execution Result                                          |
//+------------------------------------------------------------------+
void ReportExecutionResult(string command_id, string status, string message)
  {
   if (command_id == "") return;
   
   CJAVal payload;
   payload["command_id"] = command_id;
   payload["status"] = status;
   payload["message"] = message;
   
   string payload_str = payload.Serialize();
   string headers = "X-MT5-Secret: " + ApiSecret + "\r\nContent-Type: application/json\r\n";
   char post[], result[];
   string result_headers;
   
   StringToCharArray(payload_str, post, 0, WHOLE_ARRAY, CP_UTF8);
   
   // POST result back to backend
   // WebRequest("POST", BackendURL + "_result", headers, 5000, post, result, result_headers);
  }
//+------------------------------------------------------------------+
