import re
from datetime import datetime, date, timedelta
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from typing import NamedTuple


class DateRange(NamedTuple):
    start: date
    end: date


class CommandError(Exception):
    """Command parsing error"""
    pass


class DateParser:
    """Parse dates in flexible format"""

    MONTH_NAMES_RU = {
        'январь': 1, 'янв': 1, 'january': 1, 'jan': 1,
        'февраль': 2, 'февр': 2, 'february': 2, 'feb': 2,
        'март': 3, 'мар': 3, 'march': 3, 'mar': 3,
        'апрель': 4, 'апр': 4, 'april': 4, 'apr': 4,
        'май': 5, 'may': 5,
        'июнь': 6, 'июн': 6, 'june': 6, 'jun': 6,
        'июль': 7, 'июл': 7, 'july': 7, 'jul': 7,
        'август': 8, 'авг': 8, 'august': 8, 'aug': 8,
        'сентябрь': 9, 'сент': 9, 'september': 9, 'sep': 9,
        'октябрь': 10, 'окт': 10, 'october': 10, 'oct': 10,
        'ноябрь': 11, 'ноя': 11, 'november': 11, 'nov': 11,
        'декабрь': 12, 'дек': 12, 'december': 12, 'dec': 12,
    }

    @staticmethod
    def parse_date_string(date_str: str, today: date = None) -> date:
        """
        Parse date from string formats:
        - DD.MM (assumes current or next year)
        - DD.MM.YYYY
        - Month name (Russian or English)
        """
        if today is None:
            today = date.today()

        date_str = date_str.strip().lower()

        # Try DD.MM or DD.MM.YYYY format
        if '.' in date_str:
            parts = date_str.split('.')
            if len(parts) == 2:
                try:
                    day, month = int(parts[0]), int(parts[1])
                    year = today.year
                    result = date(year, month, day)

                    # If date has passed, use next year
                    if result < today:
                        result = date(year + 1, month, day)

                    return result
                except ValueError as e:
                    raise CommandError(f"Invalid date format: {date_str}") from e

            elif len(parts) == 3:
                try:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    return date(year, month, day)
                except ValueError as e:
                    raise CommandError(f"Invalid date format: {date_str}") from e

        # Try month name
        for month_name, month_num in DateParser.MONTH_NAMES_RU.items():
            if month_name in date_str:
                year = today.year
                first_day = date(year, month_num, 1)

                # If month has passed, use next year
                if first_day < today:
                    year += 1
                    first_day = date(year, month_num, 1)

                return first_day

        raise CommandError(f"Could not parse date: {date_str}")

    @staticmethod
    def parse_date_range(range_str: str, today: date = None) -> DateRange:
        """Parse date range like '01.12-05.12'"""
        if today is None:
            today = date.today()

        if '-' not in range_str:
            single_date = DateParser.parse_date_string(range_str, today)
            return DateRange(single_date, single_date)

        parts = range_str.split('-')
        if len(parts) != 2:
            raise CommandError(f"Invalid date range format: {range_str}")

        start = DateParser.parse_date_string(parts[0].strip(), today)
        end = DateParser.parse_date_string(parts[1].strip(), today)

        if start > end:
            raise CommandError(f"Start date is after end date: {range_str}")

        return DateRange(start, end)

    @staticmethod
    def get_month_dates(month_str: str, today: date = None) -> DateRange:
        """Get first and last day of month"""
        if today is None:
            today = date.today()

        first_day = DateParser.parse_date_string(month_str, today)
        first_day = first_day.replace(day=1)

        # Get last day of month
        next_month = first_day + relativedelta(months=1)
        last_day = next_month - timedelta(days=1)

        return DateRange(first_day, last_day)


class CommandParser:
    """Parse bot commands"""

    # Regex for mentions: @username
    MENTION_PATTERN = re.compile(r'@(\w+)')

    @staticmethod
    def extract_mentions(text: str) -> list[str]:
        """Extract all @mentions from text"""
        return CommandParser.MENTION_PATTERN.findall(text)

    @staticmethod
    def extract_quote_content(text: str) -> str | None:
        """Extract content from quotes"""
        match = re.search(r'"([^"]*)"', text)
        return match.group(1) if match else None

    @staticmethod
    def extract_flag(text: str, flag_name: str) -> bool:
        """Check if flag exists in text"""
        return f'--{flag_name}' in text

    @staticmethod
    def remove_flags(text: str) -> str:
        """Remove all --flags from text"""
        return re.sub(r'--\w+', '', text)

    @staticmethod
    def get_current_week_dates(today: date = None) -> DateRange:
        """Get Monday-Sunday of current week"""
        if today is None:
            today = date.today()

        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)

        return DateRange(monday, sunday)

    @staticmethod
    def get_next_week_dates(today: date = None) -> DateRange:
        """Get Monday-Sunday of next week"""
        if today is None:
            today = date.today()

        current_week = CommandParser.get_current_week_dates(today)
        monday = current_week.end + timedelta(days=1)
        sunday = monday + timedelta(days=6)

        return DateRange(monday, sunday)
