import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from models.budget_planner import BudgetPlanner
from utils.date_utils import get_jakarta_now

logger = logging.getLogger(__name__)

class SmartAlertSystem:
    """Smart Alert System for Budget and Spending"""
    
    def __init__(self, budget_planner: BudgetPlanner):
        self.budget_planner = budget_planner
        self.alert_history = {}  # Track when alerts were sent to avoid spam
    
    def check_budget_alerts(self, user_id: str, category: str, spent_amount: int) -> Optional[Dict]:
        """Check if budget alert should be triggered"""
        budget_status = self.budget_planner.get_budget_status(user_id, category, spent_amount)
        
        if budget_status['status'] in ['warning', 'exceeded']:
            # Check if we already sent alert recently (avoid spam)
            alert_key = f"{user_id}_{category}_{budget_status['status']}"
            now = get_jakarta_now()
            
            if alert_key in self.alert_history:
                last_alert = self.alert_history[alert_key]
                # Don't send same type of alert within 6 hours
                if now - last_alert < timedelta(hours=6):
                    return None
            
            # Record this alert
            self.alert_history[alert_key] = now
            
            return {
                'type': 'budget_alert',
                'category': category,
                'status': budget_status['status'],
                'message': budget_status['message'],
                'details': budget_status
            }
        
        return None
    
    def generate_daily_reminder(self, user_id: str, daily_expenses: List[Dict]) -> Optional[Dict]:
        """Generate daily spending reminder"""
        if not daily_expenses:
            return None
        
        today_total = sum(expense['amount'] for expense in daily_expenses)
        categories_spent = {}
        
        for expense in daily_expenses:
            category = expense['category']
            categories_spent[category] = categories_spent.get(category, 0) + expense['amount']
        
        # Check budget alerts for each category
        alerts = []
        for category, spent in categories_spent.items():
            alert = self.check_budget_alerts(user_id, category, spent)
            if alert:
                alerts.append(alert)
        
        message = f"📊 *Ringkasan Hari Ini*\n\n"
        message += f"💰 Total pengeluaran: Rp {today_total:,}\n"
        message += f"📝 Jumlah transaksi: {len(daily_expenses)}\n\n"
        
        if categories_spent:
            message += "*Per Kategori:*\n"
            for category, amount in sorted(categories_spent.items(), key=lambda x: x[1], reverse=True):
                message += f"• {category}: Rp {amount:,}\n"
        
        if alerts:
            message += "\n⚠️ *Peringatan Budget:*\n"
            for alert in alerts:
                message += f"• {alert['message']}\n"
        
        return {
            'type': 'daily_summary',
            'message': message,
            'alerts': alerts,
            'total_spent': today_total
        }
    
    def check_spending_velocity_alert(self, user_id: str, recent_expenses: List[Dict], time_window_hours: int = 2) -> Optional[Dict]:
        """Alert for rapid spending (multiple transactions in short time)"""
        if len(recent_expenses) < 3:  # Need at least 3 transactions
            return None
        
        now = get_jakarta_now()
        window_start = now - timedelta(hours=time_window_hours)
        
        # Count transactions in time window
        recent_count = 0
        recent_total = 0
        
        for expense in recent_expenses:
            expense_time = expense.get('datetime', now)
            # Handle timezone-naive datetime
            if expense_time.tzinfo is None and now.tzinfo is not None:
                # Convert naive datetime to timezone-aware
                expense_time = expense_time.replace(tzinfo=now.tzinfo)
            elif expense_time.tzinfo is not None and now.tzinfo is None:
                # Convert aware datetime to naive
                expense_time = expense_time.replace(tzinfo=None)
                window_start = window_start.replace(tzinfo=None)
            
            if expense_time >= window_start:
                recent_count += 1
                recent_total += expense['amount']
        
        # Alert if 3+ transactions in 2 hours with total > 500K
        if recent_count >= 3 and recent_total >= 500000:
            alert_key = f"{user_id}_velocity_alert_{now.strftime('%Y%m%d%H')}"
            
            if alert_key not in self.alert_history:
                self.alert_history[alert_key] = now
                
                return {
                    'type': 'velocity_alert',
                    'message': f"🚨 *Peringatan Pengeluaran Cepat*\n\n"
                              f"Anda telah melakukan {recent_count} transaksi "
                              f"dalam {time_window_hours} jam terakhir dengan total Rp {recent_total:,}.\n\n"
                              f"Pastikan pengeluaran ini sesuai rencana! 💭",
                    'transaction_count': recent_count,
                    'total_amount': recent_total,
                    'time_window': time_window_hours
                }
        
        return None
    
    def check_weekend_spending_alert(self, user_id: str, expense_amount: int, category: str) -> Optional[Dict]:
        """Alert for weekend entertainment/shopping expenses"""
        now = get_jakarta_now()
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
        
        if not is_weekend:
            return None
        
        # Alert for high entertainment/shopping expenses on weekends
        entertainment_categories = ['Entertainment', 'Daily Needs']
        if category in entertainment_categories and expense_amount >= 200000:  # 200K+
            
            alert_key = f"{user_id}_weekend_alert_{now.strftime('%Y%m%d')}"
            
            if alert_key not in self.alert_history:
                self.alert_history[alert_key] = now
                
                return {
                    'type': 'weekend_alert',
                    'message': f"🎉 *Weekend Spending Alert*\n\n"
                              f"Pengeluaran {category} di akhir pekan: Rp {expense_amount:,}\n\n"
                              f"Jangan lupa sisakan budget untuk minggu depan! 😊",
                    'category': category,
                    'amount': expense_amount
                }
        
        return None
    
    def get_weekly_budget_review(self, user_id: str, weekly_expenses: Dict[str, int]) -> Dict:
        """Generate weekly budget review"""
        user_budgets = self.budget_planner.get_user_budgets(user_id)
        
        if not user_budgets:
            return {
                'type': 'weekly_review',
                'message': "📋 Belum ada budget yang diset. Gunakan /budget untuk mengatur budget bulanan!"
            }
        
        review_message = "📊 *Review Budget Mingguan*\n\n"
        warnings = []
        
        for category, weekly_spent in weekly_expenses.items():
            if category in user_budgets:
                budget_info = user_budgets[category]
                monthly_budget = budget_info['amount']
                weekly_budget = monthly_budget / 4  # Approximate weekly budget
                
                percentage = (weekly_spent / weekly_budget * 100) if weekly_budget > 0 else 0
                
                if percentage >= 100:
                    status_emoji = "🔴"
                    warnings.append(f"Budget {category} sudah melebihi target mingguan")
                elif percentage >= 75:
                    status_emoji = "🟡"
                    warnings.append(f"Budget {category} hampir mencapai target mingguan")
                else:
                    status_emoji = "🟢"
                
                review_message += f"{status_emoji} *{category}*\n"
                review_message += f"   Spent: Rp {weekly_spent:,} ({percentage:.1f}% dari target mingguan)\n"
                review_message += f"   Target mingguan: Rp {weekly_budget:,.0f}\n\n"
        
        if warnings:
            review_message += "\n⚠️ *Peringatan:*\n"
            for warning in warnings:
                review_message += f"• {warning}\n"
        
        return {
            'type': 'weekly_review',
            'message': review_message,
            'warnings': warnings
        }
