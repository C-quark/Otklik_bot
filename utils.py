from datetime import date, datetime
date_today = date.today()


def is_valid_date(stalk_date):
    try:
        if stalk_date != datetime.strptime(stalk_date, "%Y-%m-%d").strftime('%Y-%m-%d') or date_today > datetime.strptime(stalk_date, "%Y-%m-%d").date():
            raise ValueError
        return True
    except ValueError:
        return False


def format_users(usernames):
    return '@' + ', @'.join(usernames)
