def format_currency(value):
    """Format số tiền VND (vd: 1,000,000)"""
    try:
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return value

def format_currency_usd(value):
    """Format số tiền USD (vd: 1,000.00)"""
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return value

def get_debt_group(days, lang="Tiếng Việt"):
    try:
        d = float(days)
    except (ValueError, TypeError):
        return ""
    
    if lang == "English":
        if d < 0:
            return "Not yet due"
        elif d == 0:
            return "Upcoming"
        elif 1 <= d <= 15:
            return "1-15 days overdue"
        elif 16 <= d <= 30:
            return "16-30 days overdue"
        elif 31 <= d <= 60:
            return "31-60 days overdue"
        elif 61 <= d <= 90:
            return "61-90 days overdue"
        else:
            return "Over 90 days overdue"
    else:
        if d < 0:
            return "Chưa đến hạn"
        elif d == 0:
            return "Sắp đến hạn"
        elif 1 <= d <= 15:
            return "Nhóm 1-15 ngày"
        elif 16 <= d <= 30:
            return "Nhóm 16-30 ngày"
        elif 31 <= d <= 60:
            return "Nhóm 31-60 ngày"
        elif 61 <= d <= 90:
            return "Nhóm 61-90 ngày"
        else:
            return "Trên 90 ngày"
