"""
Optimize Partial Exit Strategy for GH TRADES Signals

This script analyzes historical trading data to find the optimal partial exit strategy
by testing different combinations of exit percentages at each TP level.

The goal is to maximize total P/L % across all historical trades.
"""

import sqlite3
import itertools
from typing import List, Dict, Tuple
from datetime import datetime


class StrategyOptimizer:
    def __init__(self, db_path: str = "telegram_messages.db"):
        self.db_path = db_path
        self.signals = []
        
    def load_signals(self):
        """Load all historical signals from the database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT 
                signal_number,
                symbol,
                action,
                entry_price,
                tp1, tp2, tp3, tp4, tp5, tp6,
                risk_level,
                created_at
            FROM signal_details
            WHERE entry_price IS NOT NULL
            ORDER BY signal_number
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Get announced TPs for each signal
        for row in rows:
            signal_data = dict(row)
            
            # Get TPs hit for this signal
            tp_query = """
                SELECT tp_level
                FROM announced_tps
                WHERE signal_number = ?
                ORDER BY tp_level
            """
            cursor.execute(tp_query, (row['signal_number'],))
            tps_hit = [tp[0] for tp in cursor.fetchall()]
            
            signal_data['tps_hit'] = tps_hit
            signal_data['highest_tp'] = max(tps_hit) if tps_hit else 0
            
            self.signals.append(signal_data)
        
        conn.close()
        print(f"Loaded {len(self.signals)} signals from database")
        
    def calculate_signal_profit(self, signal: Dict, strategy: List[float]) -> float:
        """
        Calculate profit for a single signal with given strategy.
        This EXACTLY replicates the JavaScript recalculation logic.
        
        Args:
            signal: Signal data dictionary
            strategy: List of 6 floats representing partial exit % for TP1-TP6 (0.0-1.0)
            
        Returns:
            Total profit % for this signal
        """
        highest_tp = signal['highest_tp']
        
        # Stop loss hit = negative profit (use risk-adjusted loss)
        if highest_tp == 0:
            risk_percent = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}.get(signal['risk_level'], 2)
            # Simplified: just return the risk percentage as negative
            return -risk_percent
        
        # Calculate profit for each TP hit
        entry_price = float(signal['entry_price'])
        if not entry_price or entry_price == 0:
            return 0.0
            
        risk_percent = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}.get(signal['risk_level'], 2)
        
        total_profit = 0.0
        
        for i in range(highest_tp):
            tp_num = i + 1
            tp_price = signal.get(f'tp{tp_num}')
            
            if not tp_price:
                continue
            
            tp_price = float(tp_price)
            
            # Calculate price movement from entry to this TP
            # This is the EXACT formula from dashboard.js
            price_move = abs(tp_price - entry_price)
            price_move_percent = (price_move / entry_price) * 100.0
            leveraged_move = price_move_percent * 500.0  # 500:1 leverage
            
            # Apply strategy percentage for this TP level
            strategy_percent = strategy[i]
            tp_profit = (leveraged_move * strategy_percent) * (risk_percent / 100.0)
            
            total_profit += tp_profit
        
        return total_profit
    
    def calculate_portfolio_profit(self, strategy: List[float]) -> Tuple[float, Dict]:
        """
        Calculate total portfolio profit with given strategy.
        
        Returns:
            Tuple of (total_pl_percent, stats_dict)
        """
        total_pl = 0.0
        wins = 0
        losses = 0
        
        signal_results = []
        
        for signal in self.signals:
            profit = self.calculate_signal_profit(signal, strategy)
            total_pl += profit
            
            if profit > 0:
                wins += 1
            elif profit < 0:
                losses += 1
            
            signal_results.append({
                'signal_number': signal['signal_number'],
                'symbol': signal['symbol'],
                'highest_tp': signal['highest_tp'],
                'profit': profit
            })
        
        win_rate = (wins / len(self.signals) * 100) if self.signals else 0
        
        stats = {
            'total_pl_percent': total_pl,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'signal_results': signal_results
        }
        
        return total_pl, stats
    
    def generate_strategies(self, step: int = 5, include_tp6: bool = False) -> List[List[float]]:
        """
        Generate all possible strategies that sum to 100%.
        
        Args:
            step: Percentage step size (e.g., 5 = test 0%, 5%, 10%, etc.)
            include_tp6: Whether to include TP6 in strategies
            
        Returns:
            List of strategy combinations (each is a list of 6 floats)
        """
        strategies = []
        
        # Create range of possible percentages (as integers for simplicity)
        percentages = list(range(0, 101, step))
        
        print(f"Generating strategies with step size {step}%...")
        
        if not include_tp6:
            # Only use TP1-TP5, TP6 is always 0
            for tp1 in percentages:
                for tp2 in percentages:
                    for tp3 in percentages:
                        for tp4 in percentages:
                            for tp5 in percentages:
                                if tp1 + tp2 + tp3 + tp4 + tp5 == 100:
                                    strategies.append([
                                        tp1/100, tp2/100, tp3/100, 
                                        tp4/100, tp5/100, 0.0
                                    ])
        else:
            # Use all 6 TPs
            for tp1 in percentages:
                for tp2 in percentages:
                    for tp3 in percentages:
                        for tp4 in percentages:
                            for tp5 in percentages:
                                for tp6 in percentages:
                                    if tp1 + tp2 + tp3 + tp4 + tp5 + tp6 == 100:
                                        strategies.append([
                                            tp1/100, tp2/100, tp3/100, 
                                            tp4/100, tp5/100, tp6/100
                                        ])
        
        print(f"Generated {len(strategies)} unique strategies")
        return strategies
    
    def optimize(self, step: int = 5, include_tp6: bool = False, top_n: int = 10):
        """
        Find the optimal partial exit strategy.
        
        Args:
            step: Percentage step size for testing
            include_tp6: Whether to include TP6 in optimization
            top_n: Number of top strategies to display
        """
        print("="*80)
        print("GH TRADES Partial Exit Strategy Optimizer")
        print("="*80)
        print()
        
        # Load signals
        self.load_signals()
        
        if not self.signals:
            print("No signals found in database!")
            return
        
        # Calculate baseline (default strategy)
        default_strategy = [0.5, 0.2, 0.1, 0.1, 0.1, 0.0]
        baseline_pl, baseline_stats = self.calculate_portfolio_profit(default_strategy)
        
        # Debug: Show calculation for first signal with TP5 hit
        print("\nDEBUG: Signal #140 (TP5 Hit) calculation:")
        signal_140 = next((s for s in self.signals if s['signal_number'] == 140), None)
        if signal_140:
            print(f"  Entry: {signal_140['entry_price']}")
            print(f"  TP1: {signal_140.get('tp1')}")
            print(f"  TP2: {signal_140.get('tp2')}")
            print(f"  TP3: {signal_140.get('tp3')}")
            print(f"  TP4: {signal_140.get('tp4')}")
            print(f"  TP5: {signal_140.get('tp5')}")
            print(f"  Risk: {signal_140['risk_level']}")
            print(f"  Highest TP: {signal_140['highest_tp']}")
            profit = self.calculate_signal_profit(signal_140, default_strategy)
            print(f"  Calculated Profit: {profit:.2f}%")
        print()
        
        print(f"\nBaseline Strategy (50-20-10-10-10-0):")
        print(f"  Total P/L: {baseline_pl:+.2f}%")
        print(f"  Win Rate: {baseline_stats['win_rate']:.1f}%")
        print(f"  Wins: {baseline_stats['wins']}, Losses: {baseline_stats['losses']}")
        print()
        
        # Generate and test all strategies
        strategies = self.generate_strategies(step=step, include_tp6=include_tp6)
        
        print(f"Testing {len(strategies)} strategies...")
        print("This may take a few minutes...\n")
        
        results = []
        
        for i, strategy in enumerate(strategies):
            if (i + 1) % 1000 == 0:
                print(f"  Progress: {i+1}/{len(strategies)} strategies tested...")
            
            total_pl, stats = self.calculate_portfolio_profit(strategy)
            
            results.append({
                'strategy': strategy,
                'total_pl': total_pl,
                'stats': stats
            })
        
        # Sort by total P/L (descending)
        results.sort(key=lambda x: x['total_pl'], reverse=True)
        
        print(f"\nOptimization complete!")
        print(f"\n{'='*80}")
        print(f"TOP {top_n} STRATEGIES (by Total P/L %)")
        print(f"{'='*80}\n")
        
        for i, result in enumerate(results[:top_n], 1):
            strategy = result['strategy']
            pl = result['total_pl']
            stats = result['stats']
            
            # Format strategy as percentages
            strategy_str = "-".join([f"{int(s*100)}" for s in strategy[:5]])
            if strategy[5] > 0:
                strategy_str += f"-{int(strategy[5]*100)}"
            
            improvement = ((pl - baseline_pl) / abs(baseline_pl) * 100) if baseline_pl != 0 else 0
            
            print(f"#{i}. Strategy: {strategy_str}")
            print(f"    Total P/L: {pl:+.2f}% ({improvement:+.1f}% vs baseline)")
            print(f"    Win Rate: {stats['win_rate']:.1f}%")
            print(f"    Breakdown: TP1={int(strategy[0]*100)}%, TP2={int(strategy[1]*100)}%, "
                  f"TP3={int(strategy[2]*100)}%, TP4={int(strategy[3]*100)}%, "
                  f"TP5={int(strategy[4]*100)}%, TP6={int(strategy[5]*100)}%")
            print()
        
        # Find best strategy by win rate
        best_winrate = max(results, key=lambda x: x['stats']['win_rate'])
        
        print(f"{'='*80}")
        print(f"BEST STRATEGY BY WIN RATE")
        print(f"{'='*80}\n")
        
        strategy = best_winrate['strategy']
        strategy_str = "-".join([f"{int(s*100)}" for s in strategy[:5]])
        if strategy[5] > 0:
            strategy_str += f"-{int(strategy[5]*100)}"
        
        print(f"Strategy: {strategy_str}")
        print(f"Win Rate: {best_winrate['stats']['win_rate']:.1f}%")
        print(f"Total P/L: {best_winrate['total_pl']:+.2f}%")
        print()
        
        # Export best strategy
        best_strategy = results[0]
        print(f"{'='*80}")
        print(f"RECOMMENDED STRATEGY")
        print(f"{'='*80}\n")
        
        strategy = best_strategy['strategy']
        print(f"TP1: {int(strategy[0]*100)}%")
        print(f"TP2: {int(strategy[1]*100)}%")
        print(f"TP3: {int(strategy[2]*100)}%")
        print(f"TP4: {int(strategy[3]*100)}%")
        print(f"TP5: {int(strategy[4]*100)}%")
        print(f"TP6: {int(strategy[5]*100)}%")
        print()
        print(f"Expected Total P/L: {best_strategy['total_pl']:+.2f}%")
        print(f"Improvement over baseline: {((best_strategy['total_pl'] - baseline_pl) / abs(baseline_pl) * 100):+.1f}%")
        print()
        
        return results


if __name__ == "__main__":
    optimizer = StrategyOptimizer()
    
    # Run optimization with 5% step size (faster)
    # For more precise results, use step=1 (will take much longer)
    results = optimizer.optimize(
        step=5,          # Test strategies in 5% increments (0%, 5%, 10%, etc.)
        include_tp6=False,  # Don't use TP6 (most signals don't have it)
        top_n=20         # Show top 20 strategies
    )
    
    print("\n" + "="*80)
    print("Optimization complete! Use the recommended strategy in your dashboard.")
    print("="*80)
