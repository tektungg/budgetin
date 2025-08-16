import logging
import statistics
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import calendar
from utils.date_utils import get_jakarta_now, format_tanggal_indo

logger = logging.getLogger(__name__)

class SpendingAnalytics:
    """Advanced Spending Analytics and Insights"""
    
    def __init__(self):
        pass
    
    def get_monthly_trends(self, user_expenses: List[Dict], months_back: int = 6) -> Dict:
        """Analyze monthly spending trends"""
        if not user_expenses:
            return {'error': 'No expense data available'}
        
        # Group expenses by month
        monthly_data = defaultdict(lambda: {'total': 0, 'transactions': 0, 'categories': defaultdict(int)})
        
        now = get_jakarta_now()
        cutoff_date = now - timedelta(days=months_back * 30)
        
        for expense in user_expenses:
            expense_date = expense.get('datetime', now)
            # Handle timezone differences
            if expense_date.tzinfo is None and now.tzinfo is not None:
                expense_date = expense_date.replace(tzinfo=now.tzinfo)
            elif expense_date.tzinfo is not None and now.tzinfo is None:
                expense_date = expense_date.replace(tzinfo=None)
                cutoff_date = cutoff_date.replace(tzinfo=None)
                
            if expense_date < cutoff_date:
                continue
            
            month_key = expense_date.strftime('%Y-%m')
            amount = expense['amount']
            category = expense.get('category', 'Other')
            
            monthly_data[month_key]['total'] += amount
            monthly_data[month_key]['transactions'] += 1
            monthly_data[month_key]['categories'][category] += amount
        
        if not monthly_data:
            return {'error': 'Insufficient data for trend analysis'}
        
        # Calculate trends
        sorted_months = sorted(monthly_data.keys())
        monthly_totals = [monthly_data[month]['total'] for month in sorted_months]
        
        # Calculate percentage change
        trend_analysis = {
            'months_analyzed': len(sorted_months),
            'monthly_data': {},
            'trend': 'stable',
            'average_monthly_spending': statistics.mean(monthly_totals),
            'highest_month': max(monthly_data.items(), key=lambda x: x[1]['total']),
            'lowest_month': min(monthly_data.items(), key=lambda x: x[1]['total'])
        }
        
        # Determine trend
        if len(monthly_totals) >= 2:
            first_half = monthly_totals[:len(monthly_totals)//2]
            second_half = monthly_totals[len(monthly_totals)//2:]
            
            if statistics.mean(second_half) > statistics.mean(first_half) * 1.1:
                trend_analysis['trend'] = 'increasing'
            elif statistics.mean(second_half) < statistics.mean(first_half) * 0.9:
                trend_analysis['trend'] = 'decreasing'
        
        # Format monthly data
        for month, data in monthly_data.items():
            try:
                month_obj = datetime.strptime(month, '%Y-%m')
                month_name = month_obj.strftime('%B %Y')
                trend_analysis['monthly_data'][month_name] = {
                    'total': data['total'],
                    'transactions': data['transactions'],
                    'avg_per_transaction': data['total'] / data['transactions'],
                    'top_category': max(data['categories'].items(), key=lambda x: x[1]) if data['categories'] else ('N/A', 0)
                }
            except:
                continue
        
        return trend_analysis
    
    def get_category_insights(self, user_expenses: List[Dict], period_days: int = 30) -> Dict:
        """Detailed category spending insights"""
        if not user_expenses:
            return {'error': 'No expense data available'}
        
        now = get_jakarta_now()
        cutoff_date = now - timedelta(days=period_days)
        
        # Filter recent expenses
        recent_expenses = []
        for expense in user_expenses:
            expense_date = expense.get('datetime', now)
            # Handle timezone differences
            if expense_date.tzinfo is None and now.tzinfo is not None:
                expense_date = expense_date.replace(tzinfo=now.tzinfo)
            elif expense_date.tzinfo is not None and now.tzinfo is None:
                expense_date = expense_date.replace(tzinfo=None)
                cutoff_date = cutoff_date.replace(tzinfo=None)
                
            if expense_date >= cutoff_date:
                recent_expenses.append(expense)
        
        if not recent_expenses:
            return {'error': f'No expenses in the last {period_days} days'}
        
        # Analyze categories
        category_stats = defaultdict(lambda: {
            'total': 0, 
            'count': 0, 
            'amounts': [], 
            'days': set(),
            'avg_per_transaction': 0,
            'frequency_score': 0
        })
        
        total_spending = sum(e['amount'] for e in recent_expenses)
        
        for expense in recent_expenses:
            category = expense.get('category', 'Other')
            amount = expense['amount']
            expense_date = expense.get('datetime', now).date()
            
            category_stats[category]['total'] += amount
            category_stats[category]['count'] += 1
            category_stats[category]['amounts'].append(amount)
            category_stats[category]['days'].add(expense_date)
        
        # Calculate additional metrics
        insights = {
            'period_days': period_days,
            'total_spending': total_spending,
            'total_transactions': len(recent_expenses),
            'daily_average': total_spending / period_days,
            'categories': {}
        }
        
        for category, stats in category_stats.items():
            amounts = stats['amounts']
            insights['categories'][category] = {
                'total_amount': stats['total'],
                'percentage_of_total': (stats['total'] / total_spending * 100),
                'transaction_count': stats['count'],
                'average_per_transaction': statistics.mean(amounts),
                'median_amount': statistics.median(amounts),
                'min_amount': min(amounts),
                'max_amount': max(amounts),
                'days_active': len(stats['days']),
                'frequency_score': len(stats['days']) / period_days * 100,  # Percentage of days with activity
                'spending_pattern': self._classify_spending_pattern(amounts, len(stats['days']))
            }
        
        # Rank categories by various metrics
        insights['rankings'] = {
            'by_amount': sorted(insights['categories'].items(), key=lambda x: x[1]['total_amount'], reverse=True),
            'by_frequency': sorted(insights['categories'].items(), key=lambda x: x[1]['frequency_score'], reverse=True),
            'by_avg_transaction': sorted(insights['categories'].items(), key=lambda x: x[1]['average_per_transaction'], reverse=True)
        }
        
        return insights
    
    def _classify_spending_pattern(self, amounts: List[int], days_active: int) -> str:
        """Classify spending pattern for a category"""
        if len(amounts) <= 1:
            return 'infrequent'
        
        stdev = statistics.stdev(amounts)
        mean_amount = statistics.mean(amounts)
        cv = stdev / mean_amount if mean_amount > 0 else 0  # Coefficient of variation
        
        if days_active >= 20:  # Very frequent
            if cv < 0.3:
                return 'consistent_daily'
            else:
                return 'variable_daily'
        elif days_active >= 10:  # Moderately frequent
            if cv < 0.3:
                return 'consistent_regular'
            else:
                return 'variable_regular'
        elif days_active >= 5:  # Occasional
            return 'occasional'
        else:
            if mean_amount > 100000:  # High amount, infrequent
                return 'large_infrequent'
            else:
                return 'infrequent'
    
    def get_spending_velocity_analysis(self, user_expenses: List[Dict]) -> Dict:
        """Analyze spending velocity and patterns"""
        if not user_expenses:
            return {'error': 'No expense data available'}
        
        # Sort by datetime
        sorted_expenses = sorted(user_expenses, key=lambda x: x.get('datetime', datetime.now()))
        
        # Calculate time differences between transactions
        time_diffs = []
        for i in range(1, len(sorted_expenses)):
            prev_time = sorted_expenses[i-1].get('datetime', datetime.now())
            curr_time = sorted_expenses[i].get('datetime', datetime.now())
            diff_hours = (curr_time - prev_time).total_seconds() / 3600
            time_diffs.append(diff_hours)
        
        if not time_diffs:
            return {'error': 'Insufficient data for velocity analysis'}
        
        # Analyze velocity patterns
        analysis = {
            'total_transactions': len(sorted_expenses),
            'analysis_period_days': (sorted_expenses[-1].get('datetime', datetime.now()) - 
                                   sorted_expenses[0].get('datetime', datetime.now())).days,
            'average_time_between_transactions_hours': statistics.mean(time_diffs),
            'median_time_between_transactions_hours': statistics.median(time_diffs),
            'fastest_consecutive_transactions_hours': min(time_diffs),
            'longest_gap_hours': max(time_diffs),
        }
        
        # Classify spending velocity
        avg_hours = analysis['average_time_between_transactions_hours']
        if avg_hours < 6:
            analysis['velocity_pattern'] = 'very_frequent'  # Multiple times per day
        elif avg_hours < 24:
            analysis['velocity_pattern'] = 'frequent'  # Daily
        elif avg_hours < 72:
            analysis['velocity_pattern'] = 'regular'  # Every few days
        else:
            analysis['velocity_pattern'] = 'infrequent'  # Weekly or less
        
        # Detect spending bursts (multiple transactions in short time)
        bursts = []
        for i in range(len(time_diffs)):
            if time_diffs[i] < 2:  # Less than 2 hours between transactions
                burst_start = i
                burst_transactions = [sorted_expenses[i], sorted_expenses[i+1]]
                burst_amount = sorted_expenses[i]['amount'] + sorted_expenses[i+1]['amount']
                
                # Look for more transactions in the burst
                j = i + 1
                while j < len(time_diffs) and time_diffs[j] < 2:
                    j += 1
                    burst_transactions.append(sorted_expenses[j+1])
                    burst_amount += sorted_expenses[j+1]['amount']
                
                if len(burst_transactions) >= 3:  # At least 3 transactions in burst
                    bursts.append({
                        'start_time': sorted_expenses[i].get('datetime', datetime.now()),
                        'transaction_count': len(burst_transactions),
                        'total_amount': burst_amount,
                        'duration_hours': sum(time_diffs[i:j])
                    })
        
        analysis['spending_bursts'] = bursts
        analysis['burst_frequency'] = len(bursts) / analysis['analysis_period_days'] * 30  # Per month
        
        return analysis
    
    def get_comparative_analysis(self, user_expenses: List[Dict]) -> Dict:
        """Compare user's spending against typical patterns"""
        category_insights = self.get_category_insights(user_expenses, 30)
        
        if 'error' in category_insights:
            return category_insights
        
        # Indonesian typical spending patterns (percentage of income/spending)
        typical_patterns = {
            'Daily Needs': {'min': 30, 'max': 50, 'optimal': 35},
            'Transportation': {'min': 10, 'max': 20, 'optimal': 15},
            'Utilities': {'min': 8, 'max': 15, 'optimal': 10},
            'Entertainment': {'min': 5, 'max': 20, 'optimal': 15},
            'Health': {'min': 3, 'max': 10, 'optimal': 5},
            'Urgent': {'min': 2, 'max': 8, 'optimal': 3}
        }
        
        comparisons = {}
        recommendations = []
        
        for category, user_data in category_insights['categories'].items():
            user_percentage = user_data['percentage_of_total']
            
            if category in typical_patterns:
                typical = typical_patterns[category]
                
                status = 'normal'
                message = ''
                
                if user_percentage > typical['max']:
                    status = 'high'
                    message = f"Pengeluaran {category} ({user_percentage:.1f}%) di atas rata-rata umum ({typical['optimal']}%)"
                    recommendations.append(f"Pertimbangkan mengurangi pengeluaran {category}")
                elif user_percentage < typical['min']:
                    status = 'low'
                    message = f"Pengeluaran {category} ({user_percentage:.1f}%) di bawah rata-rata umum ({typical['optimal']}%)"
                else:
                    status = 'normal'
                    message = f"Pengeluaran {category} ({user_percentage:.1f}%) dalam range normal"
                
                comparisons[category] = {
                    'user_percentage': user_percentage,
                    'typical_range': f"{typical['min']}-{typical['max']}%",
                    'optimal_percentage': typical['optimal'],
                    'status': status,
                    'message': message
                }
        
        return {
            'comparisons': comparisons,
            'recommendations': recommendations,
            'overall_assessment': self._assess_overall_spending_health(comparisons)
        }
    
    def _assess_overall_spending_health(self, comparisons: Dict) -> str:
        """Assess overall spending health based on category comparisons"""
        high_count = sum(1 for comp in comparisons.values() if comp['status'] == 'high')
        normal_count = sum(1 for comp in comparisons.values() if comp['status'] == 'normal')
        total_categories = len(comparisons)
        
        if high_count == 0:
            return 'excellent'
        elif high_count <= total_categories * 0.2:  # 20% or less categories high
            return 'good'
        elif high_count <= total_categories * 0.4:  # 40% or less categories high
            return 'fair'
        else:
            return 'needs_attention'
    
    def generate_monthly_insights_report(self, user_expenses: List[Dict], user_id: str) -> str:
        """Generate comprehensive monthly insights report"""
        now = get_jakarta_now()
        month_name = now.strftime('%B %Y')
        
        # Get various analyses
        category_insights = self.get_category_insights(user_expenses, 30)
        trends = self.get_monthly_trends(user_expenses, 6)
        velocity = self.get_spending_velocity_analysis(user_expenses)
        comparison = self.get_comparative_analysis(user_expenses)
        
        report = f"📊 *Laporan Analisis Pengeluaran {month_name}*\n\n"
        
        # Overall summary
        if 'error' not in category_insights:
            report += f"💰 Total Pengeluaran: Rp {category_insights['total_spending']:,}\n"
            report += f"📝 Jumlah Transaksi: {category_insights['total_transactions']}\n"
            report += f"💳 Rata-rata per Hari: Rp {category_insights['daily_average']:,.0f}\n\n"
            
            # Top spending categories
            report += "*🏆 Kategori Pengeluaran Terbesar:*\n"
            for i, (category, data) in enumerate(category_insights['rankings']['by_amount'][:3]):
                emoji = ["🥇", "🥈", "🥉"][i]
                report += f"{emoji} {category}: Rp {data['total_amount']:,} ({data['percentage_of_total']:.1f}%)\n"
            report += "\n"
            
            # Spending patterns
            report += "*📈 Pola Pengeluaran:*\n"
            for category, data in list(category_insights['categories'].items())[:5]:
                pattern = data['spending_pattern']
                pattern_emoji = {
                    'consistent_daily': '🔄',
                    'variable_daily': '📊',
                    'consistent_regular': '⚖️',
                    'variable_regular': '🎲',
                    'occasional': '⭐',
                    'large_infrequent': '💎',
                    'infrequent': '🔹'
                }.get(pattern, '📋')
                
                report += f"{pattern_emoji} {category}: {pattern.replace('_', ' ').title()}\n"
            report += "\n"
        
        # Trend analysis
        if 'error' not in trends:
            trend_emoji = {'increasing': '📈', 'decreasing': '📉', 'stable': '➡️'}
            report += f"*📊 Tren Pengeluaran: {trend_emoji.get(trends['trend'], '📊')} {trends['trend'].title()}*\n"
            report += f"Rata-rata bulanan: Rp {trends['average_monthly_spending']:,.0f}\n\n"
        
        # Velocity insights
        if 'error' not in velocity:
            velocity_emoji = {
                'very_frequent': '🏃‍♂️',
                'frequent': '🚶‍♂️',
                'regular': '🧘‍♂️',
                'infrequent': '🐌'
            }
            report += f"*⚡ Kecepatan Pengeluaran: {velocity_emoji.get(velocity['velocity_pattern'], '📊')}*\n"
            report += f"Rata-rata jarak antar transaksi: {velocity['average_time_between_transactions_hours']:.1f} jam\n"
            
            if velocity['spending_bursts']:
                report += f"⚠️ Terdeteksi {len(velocity['spending_bursts'])} periode pengeluaran intensif\n"
            report += "\n"
        
        # Comparative analysis and recommendations
        if 'error' not in comparison and comparison['recommendations']:
            report += "*💡 Rekomendasi:*\n"
            for rec in comparison['recommendations'][:3]:
                report += f"• {rec}\n"
            
            health_emoji = {
                'excellent': '💚',
                'good': '💛',
                'fair': '🧡',
                'needs_attention': '❤️'
            }
            health = comparison['overall_assessment']
            report += f"\n{health_emoji.get(health, '📊')} *Status Keuangan: {health.replace('_', ' ').title()}*\n"
        
        report += f"\n🔄 *Laporan ini diperbarui otomatis setiap bulan*"
        
        return report
