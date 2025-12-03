"""
Trading Dashboard Backend API
Provides statistics, backtesting results, and leaderboards for copy traders
"""

import os
import json
import sqlite3
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dataclasses import dataclass, asdict
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dashboard_app = Flask(__name__, static_folder='dashboard_static', static_url_path='')
CORS(dashboard_app)

# Bot API Configuration (for fetching signal data)
BOT_API_URL = os.getenv('BOT_API_URL', 'https://web-production-1299f.up.railway.app')

# Discord OAuth Configuration
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID', '')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', '')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:5001/auth/callback')
DISCORD_OAUTH_URL = 'https://discord.com/api/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
DISCORD_API_URL = 'https://discord.com/api/v10'

# Database path (for user management, strategies, etc. - NOT for signal data)
DASHBOARD_DB = "trading_dashboard.db"

@dataclass
class TraderStats:
    account_id: str
    username: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_profit: float
    total_loss: float
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    average_trade_duration: float  # in hours
    total_lots_traded: float
    sharpe_ratio: Optional[float]
    max_drawdown: float
    recovery_factor: float
    last_updated: str

@dataclass
class BacktestResult:
    backtest_id: str
    account_id: str
    strategy_name: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_trades: int
    winning_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    parameters: Dict
    equity_curve: List[Dict]  # [{timestamp, balance, equity, drawdown}]
    created_at: str

@dataclass
class LeaderboardEntry:
    rank: int
    account_id: str
    username: str
    display_name: str  # Optional anonymized name
    total_profit: float
    win_rate: float
    profit_factor: float
    total_trades: int
    roi: float  # Return on Investment %
    sharpe_ratio: Optional[float]
    last_trade: str
    is_public: bool  # Privacy setting

class DashboardDatabase:
    """Database manager for dashboard"""
    
    def __init__(self, db_path: str = DASHBOARD_DB):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trader statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trader_stats (
                account_id TEXT PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0,
                total_loss REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                average_win REAL DEFAULT 0,
                average_loss REAL DEFAULT 0,
                largest_win REAL DEFAULT 0,
                largest_loss REAL DEFAULT 0,
                consecutive_wins INTEGER DEFAULT 0,
                consecutive_losses INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                max_win_streak INTEGER DEFAULT 0,
                max_loss_streak INTEGER DEFAULT 0,
                average_trade_duration REAL DEFAULT 0,
                total_lots_traded REAL DEFAULT 0,
                sharpe_ratio REAL,
                max_drawdown REAL DEFAULT 0,
                recovery_factor REAL DEFAULT 0,
                initial_balance REAL DEFAULT 10000,
                current_balance REAL DEFAULT 10000,
                peak_balance REAL DEFAULT 10000,
                is_public INTEGER DEFAULT 1,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Individual trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                account_id TEXT,
                signal_number INTEGER,
                symbol TEXT,
                action TEXT,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                entry_price REAL,
                exit_price REAL,
                lots REAL,
                profit REAL,
                pips REAL,
                duration_hours REAL,
                trade_type TEXT,
                risk_level TEXT,
                FOREIGN KEY (account_id) REFERENCES trader_stats(account_id)
            )
        ''')
        
        # Backtest results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                backtest_id TEXT PRIMARY KEY,
                account_id TEXT,
                strategy_name TEXT,
                start_date TEXT,
                end_date TEXT,
                initial_balance REAL,
                final_balance REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                win_rate REAL,
                profit_factor REAL,
                max_drawdown REAL,
                sharpe_ratio REAL,
                parameters TEXT,
                equity_curve TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES trader_stats(account_id)
            )
        ''')
        
        # Daily statistics table (for charts)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                date TEXT,
                balance REAL,
                equity REAL,
                profit REAL,
                trades INTEGER,
                win_rate REAL,
                drawdown REAL,
                FOREIGN KEY (account_id) REFERENCES trader_stats(account_id)
            )
        ''')
        
        # User preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                account_id TEXT PRIMARY KEY,
                is_public INTEGER DEFAULT 1,
                show_username INTEGER DEFAULT 0,
                display_name TEXT,
                theme TEXT DEFAULT 'dark',
                notifications_enabled INTEGER DEFAULT 1,
                FOREIGN KEY (account_id) REFERENCES trader_stats(account_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Dashboard database initialized")
    
    def get_trader_stats(self, account_id: str) -> Optional[Dict]:
        """Get statistics for a specific trader"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trader_stats WHERE account_id = ?
        ''', (account_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_trader_stats(self, account_id: str, stats: Dict):
        """Update trader statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if trader exists
        cursor.execute('SELECT account_id FROM trader_stats WHERE account_id = ?', (account_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing
            cursor.execute('''
                UPDATE trader_stats SET
                    total_trades = ?,
                    winning_trades = ?,
                    losing_trades = ?,
                    total_profit = ?,
                    total_loss = ?,
                    win_rate = ?,
                    profit_factor = ?,
                    average_win = ?,
                    average_loss = ?,
                    largest_win = ?,
                    largest_loss = ?,
                    consecutive_wins = ?,
                    consecutive_losses = ?,
                    average_trade_duration = ?,
                    total_lots_traded = ?,
                    sharpe_ratio = ?,
                    max_drawdown = ?,
                    recovery_factor = ?,
                    current_balance = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE account_id = ?
            ''', (
                stats.get('total_trades', 0),
                stats.get('winning_trades', 0),
                stats.get('losing_trades', 0),
                stats.get('total_profit', 0),
                stats.get('total_loss', 0),
                stats.get('win_rate', 0),
                stats.get('profit_factor', 0),
                stats.get('average_win', 0),
                stats.get('average_loss', 0),
                stats.get('largest_win', 0),
                stats.get('largest_loss', 0),
                stats.get('consecutive_wins', 0),
                stats.get('consecutive_losses', 0),
                stats.get('average_trade_duration', 0),
                stats.get('total_lots_traded', 0),
                stats.get('sharpe_ratio'),
                stats.get('max_drawdown', 0),
                stats.get('recovery_factor', 0),
                stats.get('current_balance', 10000),
                account_id
            ))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO trader_stats (
                    account_id, username, total_trades, winning_trades, losing_trades,
                    total_profit, total_loss, win_rate, profit_factor, average_win,
                    average_loss, largest_win, largest_loss, consecutive_wins,
                    consecutive_losses, average_trade_duration, total_lots_traded,
                    sharpe_ratio, max_drawdown, recovery_factor, current_balance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                account_id,
                stats.get('username', f'Trader_{account_id[:8]}'),
                stats.get('total_trades', 0),
                stats.get('winning_trades', 0),
                stats.get('losing_trades', 0),
                stats.get('total_profit', 0),
                stats.get('total_loss', 0),
                stats.get('win_rate', 0),
                stats.get('profit_factor', 0),
                stats.get('average_win', 0),
                stats.get('average_loss', 0),
                stats.get('largest_win', 0),
                stats.get('largest_loss', 0),
                stats.get('consecutive_wins', 0),
                stats.get('consecutive_losses', 0),
                stats.get('average_trade_duration', 0),
                stats.get('total_lots_traded', 0),
                stats.get('sharpe_ratio'),
                stats.get('max_drawdown', 0),
                stats.get('recovery_factor', 0),
                stats.get('current_balance', 10000)
            ))
        
        conn.commit()
        conn.close()
    
    def get_leaderboard(self, metric: str = 'profit', limit: int = 50) -> List[Dict]:
        """Get leaderboard sorted by specified metric"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Determine sorting column
        order_by_map = {
            'profit': 'total_profit',
            'win_rate': 'win_rate',
            'profit_factor': 'profit_factor',
            'trades': 'total_trades',
            'roi': '((current_balance - initial_balance) / initial_balance * 100)',
            'sharpe': 'sharpe_ratio'
        }
        
        order_by = order_by_map.get(metric, 'total_profit')
        
        cursor.execute(f'''
            SELECT 
                ts.*,
                up.show_username,
                up.display_name as custom_display_name,
                ((ts.current_balance - ts.initial_balance) / ts.initial_balance * 100) as roi
            FROM trader_stats ts
            LEFT JOIN user_preferences up ON ts.account_id = up.account_id
            WHERE ts.is_public = 1 AND ts.total_trades > 0
            ORDER BY {order_by} DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        leaderboard = []
        for idx, row in enumerate(rows, 1):
            entry = dict(row)
            entry['rank'] = idx
            
            # Anonymize if needed
            if not entry.get('show_username'):
                if entry.get('custom_display_name'):
                    entry['display_name'] = entry['custom_display_name']
                else:
                    # Generate anonymous name
                    hash_obj = hashlib.md5(entry['account_id'].encode())
                    entry['display_name'] = f"Trader_{hash_obj.hexdigest()[:8]}"
            else:
                entry['display_name'] = entry.get('username', f"Trader_{entry['account_id'][:8]}")
            
            leaderboard.append(entry)
        
        return leaderboard
    
    def record_trade(self, trade_data: Dict):
        """Record an individual trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades (
                trade_id, account_id, signal_number, symbol, action,
                entry_time, exit_time, entry_price, exit_price, lots,
                profit, pips, duration_hours, trade_type, risk_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data['trade_id'],
            trade_data['account_id'],
            trade_data.get('signal_number'),
            trade_data['symbol'],
            trade_data['action'],
            trade_data.get('entry_time'),
            trade_data.get('exit_time'),
            trade_data['entry_price'],
            trade_data.get('exit_price'),
            trade_data['lots'],
            trade_data.get('profit', 0),
            trade_data.get('pips', 0),
            trade_data.get('duration_hours', 0),
            trade_data.get('trade_type'),
            trade_data.get('risk_level')
        ))
        
        conn.commit()
        conn.close()
    
    def get_trades(self, account_id: str, limit: int = 100) -> List[Dict]:
        """Get recent trades for an account"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trades 
            WHERE account_id = ? 
            ORDER BY entry_time DESC 
            LIMIT ?
        ''', (account_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def save_backtest(self, backtest_data: Dict):
        """Save backtest result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO backtest_results (
                backtest_id, account_id, strategy_name, start_date, end_date,
                initial_balance, final_balance, total_trades, winning_trades,
                win_rate, profit_factor, max_drawdown, sharpe_ratio,
                parameters, equity_curve
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            backtest_data['backtest_id'],
            backtest_data['account_id'],
            backtest_data['strategy_name'],
            backtest_data['start_date'],
            backtest_data['end_date'],
            backtest_data['initial_balance'],
            backtest_data['final_balance'],
            backtest_data['total_trades'],
            backtest_data['winning_trades'],
            backtest_data['win_rate'],
            backtest_data['profit_factor'],
            backtest_data['max_drawdown'],
            backtest_data['sharpe_ratio'],
            json.dumps(backtest_data.get('parameters', {})),
            json.dumps(backtest_data.get('equity_curve', []))
        ))
        
        conn.commit()
        conn.close()
    
    def get_backtests(self, account_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Get backtest results"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if account_id:
            cursor.execute('''
                SELECT * FROM backtest_results 
                WHERE account_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (account_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM backtest_results 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            result['parameters'] = json.loads(result['parameters'])
            result['equity_curve'] = json.loads(result['equity_curve'])
            results.append(result)
        
        return results

# Initialize database
db = DashboardDatabase()

# ==================== API ENDPOINTS ====================

@dashboard_app.route('/')
def serve_dashboard():
    """Serve the main dashboard page"""
    return send_from_directory('dashboard_static', 'index.html')

@dashboard_app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS, etc.)"""
    return send_from_directory('dashboard_static', path)

@dashboard_app.route('/api/stats/<account_id>', methods=['GET'])
def get_trader_stats(account_id):
    """Get statistics for a specific trader"""
    try:
        stats = db.get_trader_stats(account_id)
        if stats:
            return jsonify({
                "status": "success",
                "data": stats
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Trader not found"
            }), 404
    except Exception as e:
        logger.error(f"Error getting trader stats: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@dashboard_app.route('/api/stats', methods=['POST'])
def update_trader_stats():
    """Update trader statistics"""
    try:
        data = request.get_json()
        account_id = data.get('account_id')
        
        if not account_id:
            return jsonify({
                "status": "error",
                "message": "account_id required"
            }), 400
        
        db.update_trader_stats(account_id, data)
        
        return jsonify({
            "status": "success",
            "message": "Stats updated"
        })
    except Exception as e:
        logger.error(f"Error updating trader stats: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@dashboard_app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard"""
    try:
        metric = request.args.get('metric', 'profit')
        limit = int(request.args.get('limit', 50))
        
        leaderboard = db.get_leaderboard(metric, limit)
        
        return jsonify({
            "status": "success",
            "data": leaderboard,
            "metric": metric,
            "count": len(leaderboard)
        })
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@dashboard_app.route('/api/trades/<account_id>', methods=['GET'])
def get_trades(account_id):
    """Get recent trades for an account"""
    try:
        limit = int(request.args.get('limit', 100))
        trades = db.get_trades(account_id, limit)
        
        return jsonify({
            "status": "success",
            "data": trades,
            "count": len(trades)
        })
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@dashboard_app.route('/api/trades', methods=['POST'])
def record_trade():
    """Record a new trade"""
    try:
        trade_data = request.get_json()
        
        if not trade_data.get('trade_id') or not trade_data.get('account_id'):
            return jsonify({
                "status": "error",
                "message": "trade_id and account_id required"
            }), 400
        
        db.record_trade(trade_data)
        
        return jsonify({
            "status": "success",
            "message": "Trade recorded"
        })
    except Exception as e:
        logger.error(f"Error recording trade: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@dashboard_app.route('/api/backtests', methods=['GET'])
def get_backtests():
    """Get backtest results"""
    try:
        account_id = request.args.get('account_id')
        limit = int(request.args.get('limit', 20))
        
        backtests = db.get_backtests(account_id, limit)
        
        return jsonify({
            "status": "success",
            "data": backtests,
            "count": len(backtests)
        })
    except Exception as e:
        logger.error(f"Error getting backtests: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@dashboard_app.route('/api/backtests', methods=['POST'])
def save_backtest():
    """Save a backtest result"""
    try:
        backtest_data = request.get_json()
        
        if not backtest_data.get('backtest_id') or not backtest_data.get('account_id'):
            return jsonify({
                "status": "error",
                "message": "backtest_id and account_id required"
            }), 400
        
        db.save_backtest(backtest_data)
        
        return jsonify({
            "status": "success",
            "message": "Backtest saved"
        })
    except Exception as e:
        logger.error(f"Error saving backtest: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@dashboard_app.route('/api/overview', methods=['GET'])
def get_overview():
    """Get overall statistics across all traders"""
    try:
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT account_id) as total_traders,
                SUM(total_trades) as total_trades,
                SUM(total_profit) as total_profit,
                AVG(win_rate) as avg_win_rate,
                AVG(profit_factor) as avg_profit_factor
            FROM trader_stats
            WHERE total_trades > 0
        ''')
        
        overview = dict(cursor.fetchone())
        conn.close()
        
        return jsonify({
            "status": "success",
            "data": overview
        })
    except Exception as e:
        logger.error(f"Error getting overview: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@dashboard_app.route('/api/signal-history', methods=['GET'])
def get_signal_history():
    """Get complete signal history - proxies to bot API for real-time data"""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        symbol = request.args.get('symbol', None)
        
        # Fetch from bot's API endpoint
        params = {'limit': limit, 'offset': offset}
        if symbol:
            params['symbol'] = symbol
        
        logger.info(f"Fetching signal history from bot API: {BOT_API_URL}/dashboard/signal_history")
        
        response = requests.get(
            f"{BOT_API_URL}/dashboard/signal_history",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Fetched {len(data.get('signals', []))} signals from bot API")
            return jsonify(data)
        else:
            logger.error(f"❌ Bot API returned status {response.status_code}")
            return jsonify({
                "error": "Failed to fetch signals from bot",
                "status": response.status_code
            }), 502
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to connect to bot API: {e}")
        # Fallback to local database if bot API is unavailable
        return get_signal_history_fallback()

def get_signal_history_fallback():
    """Fallback: Read from local database if bot API is unavailable"""
    try:
        logger.warning("⚠️ Using fallback - reading from local database")
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        symbol = request.args.get('symbol', None)
        
        conn = sqlite3.connect('telegram_messages.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
                sd.symbol,
                sd.action,
                sd.entry_price,
                sd.stop_loss,
                sd.tp1, sd.tp2, sd.tp3, sd.tp4, sd.tp5, sd.tp6,
                sd.is_reentry,
                sd.risk_level,
                sd.created_at,
                GROUP_CONCAT(at.tp_level, ',') as tp_hits,
                MAX(at.announced_at) as exit_date
            FROM signal_details sd
            LEFT JOIN announced_tps at ON sd.signal_number = at.signal_number
        '''
        
        params = []
        if symbol:
            query += ' WHERE sd.symbol = ?'
            params.append(symbol)
        
        query += '''
            GROUP BY sd.signal_number
            ORDER BY sd.created_at DESC
            LIMIT ? OFFSET ?
        '''
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get total count
        count_query = 'SELECT COUNT(*) FROM signal_details'
        if symbol:
            count_query += ' WHERE symbol = ?'
            cursor.execute(count_query, [symbol] if symbol else [])
        else:
            cursor.execute(count_query)
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Process results
        signals = []
        for row in rows:
            tp_hits_str = row['tp_hits']
            tp_hits = [int(x) for x in tp_hits_str.split(',')] if tp_hits_str else []
            highest_tp = max(tp_hits) if tp_hits else 0
            
            # Determine outcome and exit price
            if highest_tp == 0:
                outcome = 'SL Hit'
                outcome_class = 'loss'
                exit_price = row['stop_loss']
            else:
                outcome = f'TP{highest_tp} Hit'
                outcome_class = 'win'
                tp_key = f'tp{highest_tp}'
                exit_price = row[tp_key]
            
            # Calculate pips and profit percentage
            pips = 0
            profit_percent = 0
            
            # Determine risk percentage based on risk level (needed for both wins and losses)
            risk_level = row['risk_level'] if row['risk_level'] else 'MEDIUM'
            if risk_level == 'LOW':
                risk_percent = 1.0
            elif risk_level == 'HIGH':
                risk_percent = 3.0
            else:  # MEDIUM or default
                risk_percent = 2.0
            
            # Handle SL hit (no TPs hit)
            if highest_tp == 0:
                # SL hit - full loss of risk amount
                profit_percent = -risk_percent
                # Try to calculate pips if we have entry and SL
                if exit_price and row['entry_price']:
                    # Determine pip multiplier
                    if 'XAU' in row['symbol'] or 'GOLD' in row['symbol']:
                        pip_multiplier = 0.10
                    elif 'BTC' in row['symbol'] or 'BITCOIN' in row['symbol']:
                        pip_multiplier = 1.0
                    elif 'NAS' in row['symbol'] or 'US100' in row['symbol'] or 'NDX' in row['symbol']:
                        pip_multiplier = 1.0
                    elif 'JPY' in row['symbol']:
                        pip_multiplier = 0.01
                    else:
                        pip_multiplier = 0.0001
                    
                    # Calculate pips for loss
                    if row['action'] == 'BUY':
                        pips = (exit_price - row['entry_price']) / pip_multiplier
                    else:
                        pips = (row['entry_price'] - exit_price) / pip_multiplier
                else:
                    # Estimate SL pips based on instrument type when SL price is unknown
                    # Typical SL distances: XAUUSD ~20-50 pips, BTC ~300-500, NAS100 ~50-100, Forex ~20-40
                    if 'XAU' in row['symbol'] or 'GOLD' in row['symbol']:
                        pips = -30  # Typical 30 pip SL for gold
                    elif 'BTC' in row['symbol'] or 'BITCOIN' in row['symbol']:
                        pips = -400  # Typical 400 pip SL for BTC
                    elif 'NAS' in row['symbol'] or 'US100' in row['symbol'] or 'NDX' in row['symbol']:
                        pips = -75  # Typical 75 point SL for NAS100
                    else:
                        pips = -30  # Typical 30 pip SL for forex
            
            # Handle TP hits
            elif exit_price and row['entry_price']:
                # Determine pip multiplier
                if 'XAU' in row['symbol'] or 'GOLD' in row['symbol']:
                    pip_multiplier = 0.10  # $0.10 = 1 pip for gold
                elif 'BTC' in row['symbol'] or 'BITCOIN' in row['symbol']:
                    pip_multiplier = 1.0  # $1 = 1 pip for BTC
                elif 'NAS' in row['symbol'] or 'US100' in row['symbol'] or 'NDX' in row['symbol']:
                    pip_multiplier = 1.0  # 1 point = 1 pip for NAS100
                elif 'JPY' in row['symbol']:
                    pip_multiplier = 0.01  # 0.01 = 1 pip for JPY pairs
                else:
                    pip_multiplier = 0.0001  # 0.0001 = 1 pip for major forex pairs
                
                # Calculate pips
                if row['action'] == 'BUY':
                    pips = (exit_price - row['entry_price']) / pip_multiplier
                else:
                    pips = (row['entry_price'] - exit_price) / pip_multiplier
                
                # Calculate profit % based on 500:1 leverage with partial exits
                # Formula: (price_move / entry_price) * leverage * risk_percent * partial_exit_factor
                price_move_percent = abs(exit_price - row['entry_price']) / row['entry_price'] * 100
                leveraged_move = price_move_percent * 500  # 500:1 leverage
                
                # Apply NEW partial exit strategy based on highest TP hit
                # 50% at TP1, 20% at TP2, 10% at TP3, 10% at TP4
                # If TP6 exists: 5% each at TP5 and TP6
                # Otherwise: 10% at TP5
                if highest_tp == 1:
                    # Only TP1 hit (50% of position)
                    profit_percent = (leveraged_move * 0.50) * (risk_percent / 100)
                elif highest_tp == 2:
                    # TP1 + TP2 (50% + 20% = 70% total)
                    profit_percent = (leveraged_move * 0.70) * (risk_percent / 100)
                elif highest_tp == 3:
                    # TP1 + TP2 + TP3 (50% + 20% + 10% = 80% total)
                    profit_percent = (leveraged_move * 0.80) * (risk_percent / 100)
                elif highest_tp == 4:
                    # TP1 + TP2 + TP3 + TP4 (50% + 20% + 10% + 10% = 90% total)
                    profit_percent = (leveraged_move * 0.90) * (risk_percent / 100)
                elif highest_tp == 5:
                    # Check if TP6 exists for this signal
                    has_tp6 = row['tp6'] is not None if 'tp6' in row.keys() else False
                    if has_tp6:
                        # TP1-TP5 (50% + 20% + 10% + 10% + 5% = 95% total)
                        profit_percent = (leveraged_move * 0.95) * (risk_percent / 100)
                    else:
                        # All TPs hit, no TP6 (50% + 20% + 10% + 10% + 10% = 100%)
                        profit_percent = leveraged_move * (risk_percent / 100)
                elif highest_tp >= 6:
                    # All TPs hit including TP6 (100%)
                    profit_percent = leveraged_move * (risk_percent / 100)
            
            # Calculate detailed TP breakdown (partial profit per TP)
            tp_breakdown = []
            has_tp6 = row['tp6'] is not None if 'tp6' in row.keys() else False
            
            for tp_level in range(1, highest_tp + 1):
                tp_price = row[f'tp{tp_level}']
                if not tp_price:
                    continue
                
                # Calculate pips for this TP
                if row['action'] == 'BUY':
                    tp_pips = (tp_price - row['entry_price']) / pip_multiplier if exit_price and row['entry_price'] else 0
                else:
                    tp_pips = (row['entry_price'] - tp_price) / pip_multiplier if exit_price and row['entry_price'] else 0
                
                # Calculate partial profit % based on TP level
                tp_price_move = abs(tp_price - row['entry_price']) / row['entry_price'] * 100 if row['entry_price'] else 0
                tp_leveraged_move = tp_price_move * 500
                
                # Determine partial exit percentage for this TP
                if tp_level == 1:
                    partial_exit = 0.50  # 50% exit
                elif tp_level == 2:
                    partial_exit = 0.20  # 20% exit
                elif tp_level == 3:
                    partial_exit = 0.10  # 10% exit
                elif tp_level == 4:
                    partial_exit = 0.10  # 10% exit
                elif tp_level == 5:
                    partial_exit = 0.05 if has_tp6 else 0.10  # 5% if TP6 exists, 10% otherwise
                elif tp_level == 6:
                    partial_exit = 0.05  # 5% exit
                else:
                    partial_exit = 0
                
                tp_profit = (tp_leveraged_move * partial_exit) * (risk_percent / 100)
                
                tp_breakdown.append({
                    'tp_level': tp_level,
                    'price': round(tp_price, 2 if 'JPY' not in row['symbol'] else 3),
                    'pips': round(tp_pips, 1),
                    'partial_exit_percent': int(partial_exit * 100),
                    'profit_percent': round(tp_profit, 2)
                })
            
            signal = {
                'signal_number': row['signal_number'],
                'symbol': row['symbol'],
                'action': row['action'],
                'entry_price': row['entry_price'],
                'stop_loss': row['stop_loss'],
                'exit_price': exit_price,
                'tp1': row['tp1'],
                'tp2': row['tp2'],
                'tp3': row['tp3'],
                'tp4': row['tp4'],
                'tp5': row['tp5'],
                'tp6': row['tp6'] if 'tp6' in row.keys() else None,
                'is_reentry': bool(row['is_reentry']),
                'risk_level': row['risk_level'] if row['risk_level'] else 'MEDIUM',
                'created_at': row['created_at'],
                'exit_date': row['exit_date'],
                'tp_hits': tp_hits,
                'highest_tp': highest_tp,
                'outcome': outcome,
                'outcome_class': outcome_class,
                'pips': round(pips, 1) if pips else 0,
                'profit_percent': round(profit_percent, 2) if profit_percent else 0,
                'tp_breakdown': tp_breakdown  # Detailed breakdown per TP
            }
            signals.append(signal)
        
        # Calculate summary statistics
        total_signals = len(signals)
        winning_signals = len([s for s in signals if s['outcome_class'] == 'win'])
        losing_signals = len([s for s in signals if s['outcome_class'] == 'loss'])
        win_rate = (winning_signals / total_signals * 100) if total_signals > 0 else 0
        
        # Calculate total P/L %
        total_pl_percent = sum(s['profit_percent'] for s in signals)
        total_pips = sum(s['pips'] for s in signals)
        
        # TP distribution
        tp_distribution = {
            'SL': losing_signals,
            'TP1': len([s for s in signals if s['highest_tp'] == 1]),
            'TP2': len([s for s in signals if s['highest_tp'] == 2]),
            'TP3': len([s for s in signals if s['highest_tp'] == 3]),
            'TP4': len([s for s in signals if s['highest_tp'] == 4]),
            'TP5': len([s for s in signals if s['highest_tp'] == 5]),
            'TP6': len([s for s in signals if s['highest_tp'] == 6]),
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'signals': signals,
                'total_count': total_count,
                'summary': {
                    'total_signals': total_signals,
                    'winning_signals': winning_signals,
                    'losing_signals': losing_signals,
                    'win_rate': round(win_rate, 2),
                    'total_pl_percent': round(total_pl_percent, 2),
                    'total_pips': round(total_pips, 1),
                    'tp_distribution': tp_distribution
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting signal history: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dashboard_app.route('/api/run-backtest', methods=['POST'])
def run_historical_backtest():
    """Run a historical backtest with custom parameters"""
    try:
        from historical_backtester import HistoricalBacktester
        from datetime import datetime, timedelta
        
        data = request.json
        
        # Extract parameters
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        initial_balance = float(data.get('initial_balance', 10000))
        risk_percent = float(data.get('risk_percent', 5.0))
        compound = data.get('compound', True)
        
        # Parse dates
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', ''))
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', ''))
        else:
            end_date = datetime.now()
        
        logger.info(f"🔬 Running backtest: ${initial_balance} @ {risk_percent}% from {start_date.date()} to {end_date.date()}")
        
        # Run backtest
        backtester = HistoricalBacktester(db_path="telegram_messages.db")
        results = backtester.run_backtest(
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            risk_percent=risk_percent,
            compound=compound
        )
        
        if results['status'] == 'success':
            # Optionally save to database
            if data.get('save_result', False):
                account_id = data.get('account_id', 'public')
                backtest_data = {
                    'account_id': account_id,
                    'strategy_name': f"Historical Backtest ({start_date.date()} to {end_date.date()})",
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'initial_balance': initial_balance,
                    'final_balance': results['stats']['final_balance'],
                    'total_trades': results['stats']['total_trades'],
                    'winning_trades': results['stats']['winning_trades'],
                    'losing_trades': results['stats']['losing_trades'],
                    'win_rate': results['stats']['win_rate'],
                    'profit_factor': results['stats']['profit_factor'],
                    'max_drawdown': results['stats']['max_drawdown'],
                    'sharpe_ratio': results['stats']['sharpe_ratio'],
                    'equity_curve': results['equity_curve']
                }
                db.save_backtest(backtest_data)
                logger.info(f"💾 Saved backtest result for {account_id}")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"❌ Error running backtest: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5001))
    logger.info(f"Starting Trading Dashboard on port {port}")
    dashboard_app.run(host='0.0.0.0', port=port, debug=True)
