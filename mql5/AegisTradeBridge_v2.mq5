//+------------------------------------------------------------------+
//|                                        AegisTradeBridge_v2.mq5   |
//|                                  Copyright 2026, Aegis Trader    |
//|                                       https://www.aegistrader.io |
//+------------------------------------------------------------------+
#property copyright "Aegis Trader"
#property link      "https://www.aegistrader.io"
#property version   "2.00"
#property description "MT5 Bridge v2 - With Command Polling & Historical Data"

#include <Trade\Trade.mqh>
#include <JAson.mqh>  // JSON parser library (install from MQL5 market)

//--- Input parameters
input string   API_URL        = "http://127.0.0.1:8000";  // Backend API URL
input string   API_SECRET     = "Y_qQkaWbdXEdeJs-XXitLw"; // API Secret (match .env)
input int      HeartbeatSec   = 5;                        // Heartbeat interval in seconds
input int      PollIntervalMs = 1000;                     // Command poll interval in milliseconds
input ulong    MagicNumber    = 202600;                   // Magic number for orders
input int      Slippage       = 10;                       // Maximum slippage in points

//--- Global variables
CTrade         trade;
datetime       last_heartbeat = 0;
datetime       last_poll = 0;
bool           is_connected = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize trade object
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetMarginMode();
   trade.SetTypeFillingBySymbol(Symbol());
   trade.SetDeviationInPoints(Slippage);
   
   // Set up timer for heartbeat
   EventSetTimer(HeartbeatSec);
   
   Print("=== Aegis Trade Bridge v2 Initialized ===");
   Print("Backend URL: ", API_URL);
   Print("Symbol: ", Symbol());
   Print("Magic Number: ", MagicNumber);
   Print("Heartbeat: Every ", HeartbeatSec, " seconds");
   Print("Command Poll: Every ", PollIntervalMs, " ms");
   
   // Send initial heartbeat
   SendHeartbeat();
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("=== Aegis Trade Bridge v2 Stopped ===");
   Print("Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Timer function - Sends heartbeat                                 |
//+------------------------------------------------------------------+
void OnTimer()
{
   SendHeartbeat();
}

//+------------------------------------------------------------------+
//| Expert tick function - Polls for commands                        |
//+------------------------------------------------------------------+
void OnTick()
{
   // Poll for commands every PollIntervalMs
   if(GetTickCount() - last_poll >= PollIntervalMs)
   {
      PollCommands();
      last_poll = GetTickCount();
   }
   
   // Update chart comment with status
   UpdateChartComment();
}

//+------------------------------------------------------------------+
//| Send Heartbeat to Backend                                        |
//+------------------------------------------------------------------+
void SendHeartbeat()
{
   string url = API_URL + "/mt5/heartbeat";
   string headers = "Content-Type: application/json\r\n";
   headers += "X-MT5-Secret: " + API_SECRET + "\r\n";
   
   // Get account info
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin = AccountInfoDouble(ACCOUNT_MARGIN);
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   
   // Get current price
   double bid = SymbolInfoDouble(Symbol(), SYMBOL_BID);
   double ask = SymbolInfoDouble(Symbol(), SYMBOL_ASK);
   
   // Count open positions
   int positions = CountPositions();
   
   // Build JSON payload
   string payload = "{";
   payload += "\"symbol\":\"" + Symbol() + "\",";
   payload += "\"balance\":" + DoubleToString(balance, 2) + ",";
   payload += "\"equity\":" + DoubleToString(equity, 2) + ",";
   payload += "\"margin\":" + DoubleToString(margin, 2) + ",";
   payload += "\"free_margin\":" + DoubleToString(free_margin, 2) + ",";
   payload += "\"positions\":" + IntegerToString(positions) + ",";
   payload += "\"bid\":" + DoubleToString(bid, 2) + ",";
   payload += "\"ask\":" + DoubleToString(ask, 2) + ",";
   payload += "\"server_time\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\"";
   payload += "}";
   
   // Send request
   char post_data[];
   char result[];
   string result_headers;
   StringToCharArray(payload, post_data, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(post_data, ArraySize(post_data) - 1);
   
   int res = WebRequest("POST", url, headers, 5000, post_data, result, result_headers);
   
   if(res == 200)
   {
      if(!is_connected)
      {
         Print("✓ Connected to backend");
         is_connected = true;
      }
      last_heartbeat = TimeCurrent();
   }
   else if(res == -1)
   {
      if(is_connected)
      {
         Print("✗ Backend connection lost - WebRequest not allowed");
         Print("Add ", API_URL, " to allowed URLs in MT5 settings");
         is_connected = false;
      }
   }
   else
   {
      if(is_connected && (TimeCurrent() - last_heartbeat) > 90)
      {
         Print("✗ Backend connection lost - no successful heartbeat for 90 seconds");
         is_connected = false;
      }
   }
}

//+------------------------------------------------------------------+
//| Poll for Commands from Backend                                   |
//+------------------------------------------------------------------+
void PollCommands()
{
   if(!is_connected) return;
   
   string url = API_URL + "/mt5/poll";
   string headers = "Content-Type: application/json\r\n";
   headers += "X-MT5-Secret: " + API_SECRET + "\r\n";
   
   char post_data[];
   char result[];
   string result_headers;
   
   // Empty POST body
   string payload = "{}";
   StringToCharArray(payload, post_data, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(post_data, ArraySize(post_data) - 1);
   
   int res = WebRequest("POST", url, headers, 5000, post_data, result, result_headers);
   
   if(res == 200)
   {
      string response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
      
      // Parse JSON response (simplified - would use JSON library in production)
      if(StringFind(response, "\"commands\"") >= 0)
      {
         ProcessCommands(response);
      }
   }
}

//+------------------------------------------------------------------+
//| Process Commands from Backend                                    |
//+------------------------------------------------------------------+
void ProcessCommands(string json_response)
{
   // This is a simplified parser - in production use a proper JSON library
   // For now, we'll handle the most common commands
   
   // Check for place_order command
   if(StringFind(json_response, "\"action\":\"place_order\"") >= 0)
   {
      HandlePlaceOrder(json_response);
   }
   // Check for get_historical_data command
   else if(StringFind(json_response, "\"action\":\"get_historical_data\"") >= 0)
   {
      HandleHistoricalData(json_response);
   }
   // Check for close_partial command
   else if(StringFind(json_response, "\"action\":\"close_partial\"") >= 0)
   {
      HandleClosePartial(json_response);
   }
   // Check for modify_sl command
   else if(StringFind(json_response, "\"action\":\"modify_sl\"") >= 0)
   {
      HandleModifySL(json_response);
   }
}

//+------------------------------------------------------------------+
//| Handle Historical Data Request                                   |
//+------------------------------------------------------------------+
void HandleHistoricalData(string json_command)
{
   // Extract parameters (simplified parsing)
   string cmd_id = ExtractJSONString(json_command, "id");
   string symbol = ExtractJSONString(json_command, "symbol");
   string timeframe_str = ExtractJSONString(json_command, "timeframe");
   int bars = (int)ExtractJSONNumber(json_command, "bars");
   
   Print("📊 Fetching historical data: ", symbol, " ", timeframe_str, " ", bars, " bars");
   
   // Convert timeframe string to ENUM_TIMEFRAMES
   ENUM_TIMEFRAMES timeframe = StringToTimeframe(timeframe_str);
   
   // Fetch bars from MT5
   MqlRates rates[];
   int copied = CopyRates(symbol, timeframe, 0, bars, rates);
   
   if(copied > 0)
   {
      // Build JSON response with bars
      string bars_json = "[";
      
      for(int i = 0; i < copied; i++)
      {
         if(i > 0) bars_json += ",";
         
         bars_json += "{";
         bars_json += "\"timestamp\":\"" + TimeToString(rates[i].time, TIME_DATE|TIME_SECONDS) + "\",";
         bars_json += "\"open\":" + DoubleToString(rates[i].open, 5) + ",";
         bars_json += "\"high\":" + DoubleToString(rates[i].high, 5) + ",";
         bars_json += "\"low\":" + DoubleToString(rates[i].low, 5) + ",";
         bars_json += "\"close\":" + DoubleToString(rates[i].close, 5) + ",";
         bars_json += "\"volume\":" + IntegerToString(rates[i].tick_volume);
         bars_json += "}";
      }
      
      bars_json += "]";
      
      // Send result back to backend
      SendCommandResult(cmd_id, true, bars_json, "");
      
      Print("✓ Sent ", copied, " bars for ", symbol);
   }
   else
   {
      string error = "Failed to copy rates: " + IntegerToString(GetLastError());
      SendCommandResult(cmd_id, false, "[]", error);
      Print("✗ ", error);
   }
}

//+------------------------------------------------------------------+
//| Handle Place Order Command                                       |
//+------------------------------------------------------------------+
void HandlePlaceOrder(string json_command)
{
   string cmd_id = ExtractJSONString(json_command, "id");
   string symbol = ExtractJSONString(json_command, "symbol");
   string action = ExtractJSONString(json_command, "action");
   double lot_size = ExtractJSONNumber(json_command, "lot_size");
   double sl = ExtractJSONNumber(json_command, "stop_loss");
   double tp = ExtractJSONNumber(json_command, "take_profit");
   string comment = ExtractJSONString(json_command, "comment");
   
   Print("📈 Placing order: ", action, " ", lot_size, " ", symbol);
   
   bool success = false;
   ulong ticket = 0;
   
   if(action == "buy" || action == "long")
   {
      success = trade.Buy(lot_size, symbol, 0, sl, tp, comment);
   }
   else if(action == "sell" || action == "short")
   {
      success = trade.Sell(lot_size, symbol, 0, sl, tp, comment);
   }
   
   if(success)
   {
      ticket = trade.ResultOrder();
      string result = "{\"ticket\":" + IntegerToString(ticket) + "}";
      SendCommandResult(cmd_id, true, result, "");
      Print("✓ Order placed: #", ticket);
   }
   else
   {
      string error = "Order failed: " + IntegerToString(trade.ResultRetcode());
      SendCommandResult(cmd_id, false, "{}", error);
      Print("✗ ", error);
   }
}

//+------------------------------------------------------------------+
//| Handle Close Partial Command                                     |
//+------------------------------------------------------------------+
void HandleClosePartial(string json_command)
{
   string cmd_id = ExtractJSONString(json_command, "id");
   ulong ticket = (ulong)ExtractJSONNumber(json_command, "ticket");
   double lot_size = ExtractJSONNumber(json_command, "lot_size");
   
   Print("📉 Closing partial: #", ticket, " ", lot_size, " lots");
   
   bool success = trade.PositionClosePartial(ticket, lot_size);
   
   if(success)
   {
      SendCommandResult(cmd_id, true, "{}", "");
      Print("✓ Partial close successful");
   }
   else
   {
      string error = "Partial close failed: " + IntegerToString(trade.ResultRetcode());
      SendCommandResult(cmd_id, false, "{}", error);
      Print("✗ ", error);
   }
}

//+------------------------------------------------------------------+
//| Handle Modify SL Command                                         |
//+------------------------------------------------------------------+
void HandleModifySL(string json_command)
{
   string cmd_id = ExtractJSONString(json_command, "id");
   ulong ticket = (ulong)ExtractJSONNumber(json_command, "ticket");
   double new_sl = ExtractJSONNumber(json_command, "sl_price");
   
   Print("🔧 Modifying SL: #", ticket, " → ", new_sl);
   
   if(!PositionSelectByTicket(ticket))
   {
      SendCommandResult(cmd_id, false, "{}", "Position not found");
      return;
   }
   
   double current_tp = PositionGetDouble(POSITION_TP);
   bool success = trade.PositionModify(ticket, new_sl, current_tp);
   
   if(success)
   {
      SendCommandResult(cmd_id, true, "{}", "");
      Print("✓ SL modified");
   }
   else
   {
      string error = "SL modify failed: " + IntegerToString(trade.ResultRetcode());
      SendCommandResult(cmd_id, false, "{}", error);
      Print("✗ ", error);
   }
}

//+------------------------------------------------------------------+
//| Send Command Result to Backend                                   |
//+------------------------------------------------------------------+
void SendCommandResult(string cmd_id, bool success, string data, string error)
{
   string url = API_URL + "/mt5/result";
   string headers = "Content-Type: application/json\r\n";
   headers += "X-MT5-Secret: " + API_SECRET + "\r\n";
   
   string payload = "{";
   payload += "\"id\":\"" + cmd_id + "\",";
   payload += "\"success\":" + (success ? "true" : "false") + ",";
   payload += "\"data\":" + data + ",";
   payload += "\"error\":\"" + error + "\"";
   payload += "}";
   
   char post_data[];
   char result[];
   string result_headers;
   StringToCharArray(payload, post_data, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(post_data, ArraySize(post_data) - 1);
   
   WebRequest("POST", url, headers, 5000, post_data, result, result_headers);
}

//+------------------------------------------------------------------+
//| Helper: Convert timeframe string to ENUM_TIMEFRAMES              |
//+------------------------------------------------------------------+
ENUM_TIMEFRAMES StringToTimeframe(string tf)
{
   if(tf == "M1") return PERIOD_M1;
   if(tf == "M5") return PERIOD_M5;
   if(tf == "M15") return PERIOD_M15;
   if(tf == "M30") return PERIOD_M30;
   if(tf == "H1") return PERIOD_H1;
   if(tf == "H4") return PERIOD_H4;
   if(tf == "D1") return PERIOD_D1;
   if(tf == "W1") return PERIOD_W1;
   if(tf == "MN1") return PERIOD_MN1;
   return PERIOD_M5; // Default
}

//+------------------------------------------------------------------+
//| Helper: Extract string value from JSON                           |
//+------------------------------------------------------------------+
string ExtractJSONString(string json, string key)
{
   // Simplified JSON parser - finds "key":"value"
   string search = "\"" + key + "\":\"";
   int start = StringFind(json, search);
   if(start < 0) return "";
   
   start += StringLen(search);
   int end = StringFind(json, "\"", start);
   if(end < 0) return "";
   
   return StringSubstr(json, start, end - start);
}

//+------------------------------------------------------------------+
//| Helper: Extract number value from JSON                           |
//+------------------------------------------------------------------+
double ExtractJSONNumber(string json, string key)
{
   // Simplified JSON parser - finds "key":123.45
   string search = "\"" + key + "\":";
   int start = StringFind(json, search);
   if(start < 0) return 0;
   
   start += StringLen(search);
   
   // Find end of number (comma, brace, or bracket)
   string number_str = "";
   for(int i = start; i < StringLen(json); i++)
   {
      string char = StringSubstr(json, i, 1);
      if(char == "," || char == "}" || char == "]" || char == " ")
         break;
      number_str += char;
   }
   
   return StringToDouble(number_str);
}

//+------------------------------------------------------------------+
//| Helper: Count positions with our magic number                    |
//+------------------------------------------------------------------+
int CountPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) > 0)
      {
         if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Update Chart Comment                                             |
//+------------------------------------------------------------------+
void UpdateChartComment()
{
   string info = "=== Aegis Trader Bridge v2 ===\n";
   info += "Status: " + (is_connected ? "✓ Connected" : "✗ Disconnected") + "\n";
   info += "Balance: $" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + "\n";
   info += "Equity: $" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + "\n";
   info += "Positions: " + IntegerToString(CountPositions()) + "\n";
   info += "Last Update: " + TimeToString(last_heartbeat, TIME_SECONDS) + "\n";
   info += "Bid: " + DoubleToString(SymbolInfoDouble(Symbol(), SYMBOL_BID), 2) + "\n";
   info += "Ask: " + DoubleToString(SymbolInfoDouble(Symbol(), SYMBOL_ASK), 2) + "\n";
   
   Comment(info);
}
//+------------------------------------------------------------------+
