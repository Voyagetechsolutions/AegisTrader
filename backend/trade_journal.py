"""
Trade Journal - Comprehensive trade logging and analysis.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class TradeRecord:
    """Complete trade record with all context."""
    # Identification
    trade_id: str
    timestamp: datetime
    
    # Signal details
    direction: str
    setup_type: str
    grade: str
    confluence_score: float
    
    # Execution
    entry_price: float
    entry_time: datetime
    sl: float
    tp1: float
    tp2: float
    
    # Exits
    tp1_hit: bool = False
    tp1_price: Optional[float] = None
    tp1_time: Optional[datetime] = None
    
    tp2_hit: bool = False
    tp2_price: Optional[float] = None
    tp2_time: Optional[datetime] = None
    
    sl_hit: bool = False
    sl_price: Optional[float] = None
    sl_time: Optional[datetime] = None
    
    final_exit_price: Optional[float] = None
    final_exit_time: Optional[datetime] = None
    
    # Performance
    total_pnl: float = 0.0
    return_pct: float = 0.0
    duration_minutes: int = 0
    
    # Context
    spread_at_entry: float = 0.0
    slippage: float = 0.0
    session: str = ""
    
    # Analysis features
    bias: str = ""
    level_250: float = 0.0
    level_125: float = 0.0
    liquidity_sweep: bool = False
    fvg_present: bool = False
    displacement: bool = False
    structure_break: str = ""
    
    # Notes
    notes: str = ""


class TradeJournal:
    """Logs and analyzes all trades."""
    
    def __init__(self, journal_path: str = "trade_journal.json"):
        self.journal_path = Path(journal_path)
        # Define safe export directory
        self.export_dir = Path.cwd() / "exports"
        self.export_dir.mkdir(exist_ok=True)
        self.trades: List[TradeRecord] = []
        self._load_journal()
    
    def log_trade(self, record: TradeRecord):
        """Add trade to journal."""
        self.trades.append(record)
        self._save_journal()
    
    def get_stats(self, days: Optional[int] = None) -> Dict:
        """Calculate performance statistics."""
        trades = self.trades
        
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            trades = [t for t in trades if t.timestamp >= cutoff]
        
        if not trades:
            return {"error": "No trades"}
        
        wins = [t for t in trades if t.total_pnl > 0]
        losses = [t for t in trades if t.total_pnl <= 0]
        
        # Win rate by grade
        a_plus = [t for t in trades if t.grade == "A+"]
        a_grade = [t for t in trades if t.grade == "A"]
        
        return {
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(trades) * 100,
            "total_pnl": sum(t.total_pnl for t in trades),
            "avg_win": sum(t.total_pnl for t in wins) / len(wins) if wins else 0,
            "avg_loss": sum(t.total_pnl for t in losses) / len(losses) if losses else 0,
            "best_trade": max(t.total_pnl for t in trades),
            "worst_trade": min(t.total_pnl for t in trades),
            "avg_duration": sum(t.duration_minutes for t in trades) / len(trades),
            "a_plus_win_rate": len([t for t in a_plus if t.total_pnl > 0]) / len(a_plus) * 100 if a_plus else 0,
            "a_win_rate": len([t for t in a_grade if t.total_pnl > 0]) / len(a_grade) * 100 if a_grade else 0,
        }
    
    def analyze_features(self) -> Dict:
        """Analyze which features correlate with wins."""
        if not self.trades:
            return {}
        
        wins = [t for t in self.trades if t.total_pnl > 0]
        
        return {
            "liquidity_sweep_win_rate": len([t for t in wins if t.liquidity_sweep]) / len([t for t in self.trades if t.liquidity_sweep]) * 100 if any(t.liquidity_sweep for t in self.trades) else 0,
            "fvg_win_rate": len([t for t in wins if t.fvg_present]) / len([t for t in self.trades if t.fvg_present]) * 100 if any(t.fvg_present for t in self.trades) else 0,
            "displacement_win_rate": len([t for t in wins if t.displacement]) / len([t for t in self.trades if t.displacement]) * 100 if any(t.displacement for t in self.trades) else 0,
        }
    
    def get_recent_trades(self, count: int = 10) -> List[TradeRecord]:
        """Get most recent trades."""
        return self.trades[-count:]
    
    def export_csv(self, filename: str = "trades.csv"):
        """Export trades to CSV for analysis."""
        import csv
        from pathlib import Path
        import re
        
        if not self.trades:
            return
        
        # Sanitize filename: only allow alphanumeric, dash, underscore, and .csv extension
        safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '', Path(filename).stem) + '.csv'
        if not safe_filename or safe_filename == '.csv':
            safe_filename = 'trades.csv'
        
        # Restrict to export directory
        output_path = self.export_dir / safe_filename
        
        # Verify path is within export directory (prevent symlink attacks)
        try:
            output_path = output_path.resolve()
            if not str(output_path).startswith(str(self.export_dir.resolve())):
                raise ValueError("Invalid export path")
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid filename: {e}")
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=asdict(self.trades[0]).keys())
            writer.writeheader()
            for trade in self.trades:
                row = asdict(trade)
                # Convert datetime to string
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()
                writer.writerow(row)
    
    def _save_journal(self):
        """Save journal to disk."""
        data = []
        for trade in self.trades:
            record = asdict(trade)
            # Convert datetime to string
            for key, value in record.items():
                if isinstance(value, datetime):
                    record[key] = value.isoformat()
            data.append(record)
        
        with open(self.journal_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_journal(self):
        """Load journal from disk."""
        if not self.journal_path.exists():
            return
        
        try:
            with open(self.journal_path, 'r') as f:
                data = json.load(f)
            
            for record in data:
                # Convert string back to datetime
                for key, value in record.items():
                    if 'time' in key and value:
                        record[key] = datetime.fromisoformat(value)
                
                self.trades.append(TradeRecord(**record))
        except Exception as e:
            print(f"Failed to load journal: {e}")


# Global instance
trade_journal = TradeJournal()
