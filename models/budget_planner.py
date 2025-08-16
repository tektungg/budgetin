import logging
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from config import Config
from utils.date_utils import get_jakarta_now

logger = logging.getLogger(__name__)

class BudgetPlanner:
    """Budget Planning and Management System"""
    
    def __init__(self):
        self.user_budgets = {}  # {user_id: {category: budget_amount}}
        self.budget_periods = {}  # {user_id: {category: 'monthly'/'weekly'}}
        self.budget_alerts = {}  # {user_id: {category: alert_threshold_percentage}}
        self.load_budget_data()
    
    def save_budget_data(self):
        """Save budget data to file"""
        try:
            budget_data = {
                'budgets': self.user_budgets,
                'periods': self.budget_periods,
                'alerts': self.budget_alerts
            }
            with open('user_budgets.pkl', 'wb') as f:
                pickle.dump(budget_data, f)
        except Exception as e:
            logger.error(f"Error saving budget data: {e}")
    
    def load_budget_data(self):
        """Load budget data from file"""
        try:
            with open('user_budgets.pkl', 'rb') as f:
                data = pickle.load(f)
                self.user_budgets = data.get('budgets', {})
                self.budget_periods = data.get('periods', {})
                self.budget_alerts = data.get('alerts', {})
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Error loading budget data: {e}")
    
    def set_category_budget(self, user_id: str, category: str, amount: int, period: str = 'monthly', alert_threshold: int = 80):
        """Set budget for specific category"""
        user_id = str(user_id)
        
        # Initialize user data if not exists
        if user_id not in self.user_budgets:
            self.user_budgets[user_id] = {}
            self.budget_periods[user_id] = {}
            self.budget_alerts[user_id] = {}
        
        self.user_budgets[user_id][category] = amount
        self.budget_periods[user_id][category] = period
        self.budget_alerts[user_id][category] = alert_threshold
        
        self.save_budget_data()
        return True
    
    def get_user_budgets(self, user_id: str) -> Dict[str, Dict]:
        """Get all budgets for a user"""
        user_id = str(user_id)
        budgets = self.user_budgets.get(user_id, {})
        periods = self.budget_periods.get(user_id, {})
        alerts = self.budget_alerts.get(user_id, {})
        
        result = {}
        for category in budgets:
            result[category] = {
                'amount': budgets[category],
                'period': periods.get(category, 'monthly'),
                'alert_threshold': alerts.get(category, 80)
            }
        
        return result
    
    def get_category_budget(self, user_id: str, category: str) -> Optional[Dict]:
        """Get budget for specific category"""
        user_budgets = self.get_user_budgets(user_id)
        return user_budgets.get(category)
    
    def remove_category_budget(self, user_id: str, category: str) -> bool:
        """Remove budget for specific category"""
        user_id = str(user_id)
        
        if user_id in self.user_budgets and category in self.user_budgets[user_id]:
            del self.user_budgets[user_id][category]
            
            if user_id in self.budget_periods and category in self.budget_periods[user_id]:
                del self.budget_periods[user_id][category]
                
            if user_id in self.budget_alerts and category in self.budget_alerts[user_id]:
                del self.budget_alerts[user_id][category]
            
            self.save_budget_data()
            return True
        
        return False
    
    def get_budget_status(self, user_id: str, category: str, spent_amount: int, period_start: datetime = None) -> Dict:
        """Get budget status for category"""
        budget_info = self.get_category_budget(user_id, category)
        if not budget_info:
            return {'status': 'no_budget', 'message': 'No budget set for this category'}
        
        budget_amount = budget_info['amount']
        alert_threshold = budget_info['alert_threshold']
        
        # Calculate percentage spent
        percentage_spent = (spent_amount / budget_amount) * 100 if budget_amount > 0 else 0
        remaining = max(0, budget_amount - spent_amount)
        
        # Determine status
        if percentage_spent >= 100:
            status = 'exceeded'
            message = f"⚠️ Budget exceeded! Spent: Rp {spent_amount:,} / Budget: Rp {budget_amount:,}"
        elif percentage_spent >= alert_threshold:
            status = 'warning'
            message = f"🔸 Budget warning! Spent: Rp {spent_amount:,} ({percentage_spent:.1f}%) of Rp {budget_amount:,}"
        else:
            status = 'safe'
            message = f"✅ Budget safe. Spent: Rp {spent_amount:,} ({percentage_spent:.1f}%) of Rp {budget_amount:,}"
        
        return {
            'status': status,
            'message': message,
            'budget_amount': budget_amount,
            'spent_amount': spent_amount,
            'remaining': remaining,
            'percentage': percentage_spent,
            'alert_threshold': alert_threshold
        }
    
    def get_all_categories_from_config(self) -> List[str]:
        """Get all available categories from config"""
        categories = []
        for category_key in Config.CATEGORIES.keys():
            category_name = category_key.replace('_', ' ').title()
            categories.append(category_name)
        return sorted(categories)
    
    def suggest_budget_amounts(self, user_id: str, monthly_income: int = None) -> Dict[str, int]:
        """Suggest budget amounts based on common ratios"""
        if not monthly_income:
            # Default suggestions based on average Indonesian spending patterns
            suggestions = {
                'Daily Needs': 2000000,  # 2M for food and daily necessities
                'Transportation': 800000,  # 800K for transportation
                'Utilities': 500000,     # 500K for utilities
                'Entertainment': 600000,  # 600K for entertainment
                'Health': 300000,        # 300K for health
                'Urgent': 200000         # 200K for urgent expenses
            }
        else:
            # Calculate based on income (using 50/30/20 rule adapted for Indonesian context)
            suggestions = {
                'Daily Needs': int(monthly_income * 0.35),      # 35% for food and daily needs
                'Transportation': int(monthly_income * 0.15),   # 15% for transportation
                'Utilities': int(monthly_income * 0.10),        # 10% for utilities
                'Entertainment': int(monthly_income * 0.15),    # 15% for entertainment
                'Health': int(monthly_income * 0.05),          # 5% for health
                'Urgent': int(monthly_income * 0.05)           # 5% for urgent expenses
            }
        
        return suggestions
