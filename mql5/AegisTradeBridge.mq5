//+------------------------------------------------------------------+
//|                                              AegisTradeBridge.mq5|
//|                                  Copyright 2026, Aegis Trader    |
//|                                       https://www.aegistrader.io |
//+------------------------------------------------------------------+
#property copyright "Aegis Trader"
#property link      "https://www.aegistrader.io"
#property version   "1.00"
#property description "MT5 Bridge for Aegis Trader - Connects to Python backend"

#include <Trade\Trade.mqh>

//--- Input parameters
input string   API_URL        = "http://127.0.0.1:8000";  // Backend API URL
input string   API_SECRET     = "Y_qQkaWbdXEdeJs-XXitLw"; // API Secret (match .env)
input int      HeartbeatSec   = 5;                        // Heartbeat interval in seconds
input ulong    MagicNumber    = 202600;                   // Magic number for orders
input int      Slippage       = 10;                       // Maximum slippage in points

//--- Global variables
CTrade         trade;
datetime       last_heartbeat = 0;
datetime       last_price_update = 0;
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
   
   Print("=== Aegis Trade Bridge Initialized ===");
   Print("Backend URL: ", API_URL);
   Print("Symbol: ", Symbol());
   Print("Magic Number: ", MagicNumber);
   Print("Heartbeat: Every ", HeartbeatSec, " seconds");
   
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
   Print("=== Aegis Trade Bridge Stopped ===");
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
   int positions = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) > 0)
      {
         if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            positions++;
      }
   }
   
   // Build JSON payload (simple string concatenation)
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
   
   // Convert to char array
   char post_data[];
   char result[];
   string result_headers;
   StringToCharArray(payload, post_data, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(post_data, ArraySize(post_data) - 1); // Remove null terminator
   
   // Send request
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
      // WebRequest not allowed - only show once
      if(is_connected)
      {
         Print("✗ Backend connection lost - WebRequest not allowed");
         Print("Add ", API_URL, " to allowed URLs:");
         Print("Tools → Options → Expert Advisors → Allow WebRequest for listed URL");
         is_connected = false;
      }
   }
   else
   {
      // Don't disconnect on single error - could be temporary
      // Only disconnect if we haven't had a successful heartbeat in 90 seconds
      if(is_connected && (TimeCurrent() - last_heartbeat) > 90)
      {
         Print("✗ Backend connection lost - no successful heartbeat for 90 seconds");
         is_connected = false;
      }
   }
}

//+------------------------------------------------------------------+
//| Get Positions - Returns JSON string of open positions            |
//+------------------------------------------------------------------+
string GetPositionsJSON()
{
   string json = "[";
   bool first = true;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
      {
         if(!first) json += ",";
         first = false;
         
         json += "{";
         json += "\"ticket\":" + IntegerToString(ticket) + ",";
         json += "\"symbol\":\"" + PositionGetString(POSITION_SYMBOL) + "\",";
         json += "\"type\":\"" + (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "buy" : "sell") + "\",";
         json += "\"volume\":" + DoubleToString(PositionGetDouble(POSITION_VOLUME), 2) + ",";
         json += "\"price_open\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), 5) + ",";
         json += "\"price_current\":" + DoubleToString(PositionGetDouble(POSITION_PRICE_CURRENT), 5) + ",";
         json += "\"sl\":" + DoubleToString(PositionGetDouble(POSITION_SL), 5) + ",";
         json += "\"tp\":" + DoubleToString(PositionGetDouble(POSITION_TP), 5) + ",";
         json += "\"profit\":" + DoubleToString(PositionGetDouble(POSITION_PROFIT), 2) + ",";
         json += "\"swap\":" + DoubleToString(PositionGetDouble(POSITION_SWAP), 2);
         json += "}";
      }
   }
   
   json += "]";
   return json;
}

//+------------------------------------------------------------------+
//| Place Order - Called by backend via webhook                      |
//+------------------------------------------------------------------+
bool PlaceOrder(string symbol, string direction, double lots, double sl, double tp, string comment)
{
   bool success = false;
   
   if(direction == "buy" || direction == "long")
   {
      success = trade.Buy(lots, symbol, 0, sl, tp, comment);
   }
   else if(direction == "sell" || direction == "short")
   {
      success = trade.Sell(lots, symbol, 0, sl, tp, comment);
   }
   
   if(success)
   {
      ulong ticket = trade.ResultOrder();
      Print("✓ Order placed: #", ticket, " ", direction, " ", lots, " ", symbol, " @ ", SymbolInfoDouble(symbol, SYMBOL_BID));
      return true;
   }
   else
   {
      Print("✗ Order failed: ", trade.ResultRetcode(), " - ", trade.ResultComment());
      return false;
   }
}

//+------------------------------------------------------------------+
//| Modify Stop Loss                                                 |
//+------------------------------------------------------------------+
bool ModifySL(ulong ticket, double new_sl)
{
   if(!PositionSelectByTicket(ticket))
   {
      Print("✗ Position #", ticket, " not found");
      return false;
   }
   
   double current_tp = PositionGetDouble(POSITION_TP);
   bool success = trade.PositionModify(ticket, new_sl, current_tp);
   
   if(success)
   {
      Print("✓ SL modified: #", ticket, " → ", new_sl);
      return true;
   }
   else
   {
      Print("✗ SL modify failed: #", ticket, " - ", trade.ResultRetcode());
      return false;
   }
}

//+------------------------------------------------------------------+
//| Close Partial Position                                           |
//+------------------------------------------------------------------+
bool ClosePartial(ulong ticket, double lots)
{
   if(!PositionSelectByTicket(ticket))
   {
      Print("✗ Position #", ticket, " not found");
      return false;
   }
   
   bool success = trade.PositionClosePartial(ticket, lots);
   
   if(success)
   {
      Print("✓ Partial close: #", ticket, " - ", lots, " lots");
      return true;
   }
   else
   {
      Print("✗ Partial close failed: #", ticket, " - ", trade.ResultRetcode());
      return false;
   }
}

//+------------------------------------------------------------------+
//| Close Position                                                   |
//+------------------------------------------------------------------+
bool ClosePosition(ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
   {
      Print("✗ Position #", ticket, " not found");
      return false;
   }
   
   bool success = trade.PositionClose(ticket);
   
   if(success)
   {
      Print("✓ Position closed: #", ticket);
      return true;
   }
   else
   {
      Print("✗ Close failed: #", ticket, " - ", trade.ResultRetcode());
      return false;
   }
}

//+------------------------------------------------------------------+
//| Close All Positions                                              |
//+------------------------------------------------------------------+
int CloseAllPositions()
{
   int closed = 0;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
      {
         if(trade.PositionClose(ticket))
            closed++;
      }
   }
   
   Print("✓ Closed ", closed, " positions");
   return closed;
}

//+------------------------------------------------------------------+
//| Get Account Balance                                              |
//+------------------------------------------------------------------+
double GetBalance()
{
   return AccountInfoDouble(ACCOUNT_BALANCE);
}

//+------------------------------------------------------------------+
//| Get Account Equity                                               |
//+------------------------------------------------------------------+
double GetEquity()
{
   return AccountInfoDouble(ACCOUNT_EQUITY);
}

//+------------------------------------------------------------------+
//| Chart Event Handler                                              |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,
                  const long &lparam,
                  const double &dparam,
                  const string &sparam)
{
   // Handle custom events from backend if needed
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Send price update every 2 seconds (more frequent than heartbeat)
   if(TimeCurrent() - last_price_update >= 2)
   {
      SendHeartbeat();
      last_price_update = TimeCurrent();
   }
   
   // Update chart comment with status
   string info = "=== Aegis Trader Bridge ===\n";
   info += "Status: " + (is_connected ? "✓ Connected" : "✗ Disconnected") + "\n";
   info += "Balance: $" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + "\n";
   info += "Equity: $" + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + "\n";
   
   int positions = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) > 0)
      {
         if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
            positions++;
      }
   }
   info += "Positions: " + IntegerToString(positions) + "\n";
   info += "Last Update: " + TimeToString(last_heartbeat, TIME_SECONDS) + "\n";
   info += "Bid: " + DoubleToString(SymbolInfoDouble(Symbol(), SYMBOL_BID), 2) + "\n";
   info += "Ask: " + DoubleToString(SymbolInfoDouble(Symbol(), SYMBOL_ASK), 2) + "\n";
   
   Comment(info);
}
//+------------------------------------------------------------------+
