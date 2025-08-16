import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from utils.date_utils import get_jakarta_now

logger = logging.getLogger(__name__)

class AnomalyDetector:
    """Detect unusual spending patterns"""
    
    def __init__(self):
        self.spending_history = {}  # Cache for user spending patterns
    
    def analyze_expense_patterns(self, user_expenses: List[Dict]) -> Dict:
        """Analyze user's historical expense patterns"""
        if len(user_expenses) < 10:  # Need minimum data
            return {
                'has_enough_data': False,
                'message': 'Butuh minimal 10 transaksi untuk analisis pola pengeluaran'
            }
        
        # Group by category
        category_amounts = defaultdict(list)
        daily_totals = defaultdict(int)
        hourly_patterns = defaultdict(list)
        
        for expense in user_expenses:
            category = expense.get('category', 'Other')
            amount = expense['amount']
            date = expense.get('date', datetime.now().strftime('%Y-%m-%d'))
            time = expense.get('time', '12:00:00')
            
            category_amounts[category].append(amount)
            daily_totals[date] += amount
            
            # Extract hour for pattern analysis
            try:
                hour = int(time.split(':')[0])
                hourly_patterns[hour].append(amount)
            except:
                pass
        
        # Calculate statistics for each category
        category_stats = {}
        for category, amounts in category_amounts.items():
            if len(amounts) >= 3:  # Need at least 3 data points
                category_stats[category] = {
                    'mean': statistics.mean(amounts),
                    'median': statistics.median(amounts),
                    'stdev': statistics.stdev(amounts) if len(amounts) > 1 else 0,
                    'min': min(amounts),
                    'max': max(amounts),
                    'count': len(amounts)
                }
        
        # Daily spending patterns
        daily_amounts = list(daily_totals.values())
        daily_stats = {
            'mean': statistics.mean(daily_amounts) if daily_amounts else 0,
            'median': statistics.median(daily_amounts) if daily_amounts else 0,
            'stdev': statistics.stdev(daily_amounts) if len(daily_amounts) > 1 else 0
        }
        
        return {
            'has_enough_data': True,
            'category_stats': category_stats,
            'daily_stats': daily_stats,
            'hourly_patterns': dict(hourly_patterns),
            'total_transactions': len(user_expenses)
        }
    
    def detect_amount_anomaly(self, category: str, amount: int, user_patterns: Dict) -> Optional[Dict]:
        """Detect if expense amount is unusual for the category"""
        if not user_patterns.get('has_enough_data', False):
            return None
        
        category_stats = user_patterns.get('category_stats', {}).get(category)
        if not category_stats:
            return None
        
        mean = category_stats['mean']
        stdev = category_stats['stdev']
        max_normal = category_stats['max']
        
        # Check if amount is significantly higher than usual
        if stdev > 0:
            z_score = (amount - mean) / stdev
            
            # Alert if amount is > 2 standard deviations above mean
            if z_score > 2.0 and amount > max_normal:
                return {
                    'type': 'amount_anomaly',
                    'category': category,
                    'amount': amount,
                    'typical_range': f"Rp {mean - stdev:,.0f} - Rp {mean + stdev:,.0f}",
                    'message': f"🔍 *Pengeluaran Tidak Biasa*\n\n"
                              f"Pengeluaran {category} Rp {amount:,} lebih tinggi dari biasanya.\n"
                              f"Rata-rata pengeluaran {category}: Rp {mean:,.0f}\n"
                              f"Range normal: Rp {mean - stdev:,.0f} - Rp {mean + stdev:,.0f}",
                    'severity': 'high' if z_score > 3.0 else 'medium',
                    'z_score': z_score
                }
        
        # Simple check: amount is significantly higher than previous maximum
        elif amount > max_normal * 2:  # More than 2x previous maximum
            return {
                'type': 'amount_anomaly',
                'category': category,
                'amount': amount,
                'previous_max': max_normal,
                'message': f"🔍 *Pengeluaran Tidak Biasa*\n\n"
                          f"Pengeluaran {category} Rp {amount:,} jauh lebih tinggi dari biasanya.\n"
                          f"Pengeluaran tertinggi sebelumnya: Rp {max_normal:,}",
                'severity': 'high',
                'factor': amount / max_normal
            }
        
        return None
    
    def detect_time_anomaly(self, expense_time: str, user_patterns: Dict) -> Optional[Dict]:
        """Detect unusual spending time patterns"""
        if not user_patterns.get('has_enough_data', False):
            return None
        
        try:
            hour = int(expense_time.split(':')[0])
            hourly_patterns = user_patterns.get('hourly_patterns', {})
            
            # Check if user typically doesn't spend at this hour
            hours_with_activity = list(hourly_patterns.keys())
            
            if not hours_with_activity:
                return None
            
            # Alert for very unusual times (late night/early morning)
            if hour >= 23 or hour <= 5:  # 11PM - 5AM
                if hour not in hours_with_activity:
                    return {
                        'type': 'time_anomaly',
                        'hour': hour,
                        'time': expense_time,
                        'message': f"🌙 *Pengeluaran di Waktu Tidak Biasa*\n\n"
                                  f"Pengeluaran pada {expense_time} (tengah malam/dini hari).\n"
                                  f"Pastikan ini bukan transaksi yang tidak diinginkan!",
                        'severity': 'medium'
                    }
        
        except:
            pass
        
        return None
    
    def detect_frequency_anomaly(self, user_id: str, recent_expenses: List[Dict], time_window_hours: int = 24) -> Optional[Dict]:
        """Detect unusual spending frequency"""
        if len(recent_expenses) < 5:
            return None
        
        now = get_jakarta_now()
        window_start = now - timedelta(hours=time_window_hours)
        
        # Count transactions in the time window
        recent_transactions = []
        for expense in recent_expenses:
            expense_time = expense.get('datetime', now)
            # Handle timezone differences
            if expense_time.tzinfo is None and now.tzinfo is not None:
                expense_time = expense_time.replace(tzinfo=now.tzinfo)
            elif expense_time.tzinfo is not None and now.tzinfo is None:
                expense_time = expense_time.replace(tzinfo=None)
                window_start = window_start.replace(tzinfo=None)
                
            if expense_time >= window_start:
                recent_transactions.append(expense)
        
        transaction_count = len(recent_transactions)
        
        # Alert if too many transactions in short time
        if transaction_count >= 8:  # 8+ transactions in 24 hours
            return {
                'type': 'frequency_anomaly',
                'transaction_count': transaction_count,
                'time_window': time_window_hours,
                'total_amount': sum(t['amount'] for t in recent_transactions),
                'message': f"📊 *Frekuensi Pengeluaran Tinggi*\n\n"
                          f"Anda telah melakukan {transaction_count} transaksi "
                          f"dalam {time_window_hours} jam terakhir.\n"
                          f"Total: Rp {sum(t['amount'] for t in recent_transactions):,}\n\n"
                          f"Periksa apakah semua transaksi ini benar! 🤔",
                'severity': 'medium'
            }
        
        return None
    
    def detect_category_shift_anomaly(self, user_expenses: List[Dict], recent_days: int = 7) -> Optional[Dict]:
        """Detect unusual shifts in spending categories"""
        if len(user_expenses) < 20:  # Need enough historical data
            return None
        
        now = get_jakarta_now()
        recent_cutoff = now - timedelta(days=recent_days)
        
        # Separate recent vs historical expenses
        recent_expenses = []
        historical_expenses = []
        
        for expense in user_expenses:
            expense_date = expense.get('datetime', now)
            # Handle timezone differences
            if expense_date.tzinfo is None and now.tzinfo is not None:
                expense_date = expense_date.replace(tzinfo=now.tzinfo)
            elif expense_date.tzinfo is not None and now.tzinfo is None:
                expense_date = expense_date.replace(tzinfo=None)
                recent_cutoff = recent_cutoff.replace(tzinfo=None)
                
            if expense_date >= recent_cutoff:
                recent_expenses.append(expense)
            else:
                historical_expenses.append(expense)
        
        if len(recent_expenses) < 3 or len(historical_expenses) < 10:
            return None
        
        # Calculate category distributions
        def get_category_distribution(expenses):
            category_totals = defaultdict(int)
            total_amount = sum(e['amount'] for e in expenses)
            
            for expense in expenses:
                category_totals[expense.get('category', 'Other')] += expense['amount']
            
            # Convert to percentages
            return {cat: (amount / total_amount * 100) for cat, amount in category_totals.items()}
        
        recent_dist = get_category_distribution(recent_expenses)
        historical_dist = get_category_distribution(historical_expenses)
        
        # Look for significant shifts
        significant_changes = []
        for category in recent_dist:
            recent_pct = recent_dist[category]
            historical_pct = historical_dist.get(category, 0)
            
            # Alert if category now represents >40% of spending but was <20% historically
            if recent_pct > 40 and historical_pct < 20:
                significant_changes.append({
                    'category': category,
                    'recent_percentage': recent_pct,
                    'historical_percentage': historical_pct,
                    'change': recent_pct - historical_pct
                })
        
        if significant_changes:
            message = f"📈 *Perubahan Pola Pengeluaran*\n\n"
            message += f"Dalam {recent_days} hari terakhir, terjadi perubahan signifikan:\n\n"
            
            for change in significant_changes:
                message += f"• {change['category']}: "
                message += f"{change['recent_percentage']:.1f}% (biasanya {change['historical_percentage']:.1f}%)\n"
            
            message += f"\nApakah ada perubahan kebutuhan atau situasi khusus? 🤔"
            
            return {
                'type': 'category_shift_anomaly',
                'changes': significant_changes,
                'message': message,
                'severity': 'low'
            }
        
        return None
    
    def get_comprehensive_anomaly_report(self, user_id: str, user_expenses: List[Dict], new_expense: Dict) -> Dict:
        """Generate comprehensive anomaly detection report"""
        user_patterns = self.analyze_expense_patterns(user_expenses)
        
        anomalies = []
        
        # Check different types of anomalies
        amount_anomaly = self.detect_amount_anomaly(
            new_expense.get('category', 'Other'),
            new_expense['amount'],
            user_patterns
        )
        if amount_anomaly:
            anomalies.append(amount_anomaly)
        
        time_anomaly = self.detect_time_anomaly(
            new_expense.get('time', '12:00:00'),
            user_patterns
        )
        if time_anomaly:
            anomalies.append(time_anomaly)
        
        frequency_anomaly = self.detect_frequency_anomaly(user_id, user_expenses[-20:])  # Last 20 transactions
        if frequency_anomaly:
            anomalies.append(frequency_anomaly)
        
        category_shift_anomaly = self.detect_category_shift_anomaly(user_expenses)
        if category_shift_anomaly:
            anomalies.append(category_shift_anomaly)
        
        return {
            'has_anomalies': len(anomalies) > 0,
            'anomalies': anomalies,
            'patterns_analyzed': user_patterns.get('has_enough_data', False),
            'total_historical_transactions': user_patterns.get('total_transactions', 0)
        }
