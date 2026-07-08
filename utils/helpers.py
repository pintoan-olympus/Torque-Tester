import datetime

def format_datetime(dt_str_or_obj):
    """Format datetime to a standard display format."""
    if not dt_str_or_obj:
        return "N/A"
    if isinstance(dt_str_or_obj, str):
        try:
            # SQLite datetime format
            dt = datetime.datetime.fromisoformat(dt_str_or_obj)
        except ValueError:
            return dt_str_or_obj
    else:
        dt = dt_str_or_obj
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def format_date(date_str_or_obj):
    """Format date to a standard display format."""
    if not date_str_or_obj:
        return "N/A"
    if isinstance(date_str_or_obj, str):
        try:
            d = datetime.date.fromisoformat(date_str_or_obj)
        except ValueError:
            return date_str_or_obj
    else:
        d = date_str_or_obj
    return d.strftime("%Y-%m-%d")

def check_tolerance(value, target, tol_plus, tol_minus):
    """Check if value is within tolerance limits. Tol_plus and tol_minus are positive floats."""
    lower_limit = target - tol_minus
    upper_limit = target + tol_plus
    is_ok = lower_limit <= value <= upper_limit
    return is_ok, lower_limit, upper_limit
