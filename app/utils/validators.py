"""
Common validators for data validation across the application.
"""

import re
from datetime import date, datetime
from typing import Any


class FieldValidators:
    """Collection of reusable field validators."""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format (alphanumeric, underscore, hyphen)."""
        pattern = r"^[a-zA-Z0-9_-]{3,32}$"
        return bool(re.match(pattern, username))

    @staticmethod
    def validate_positive_int(value: int) -> bool:
        """Validate value is positive integer."""
        return isinstance(value, int) and value > 0

    @staticmethod
    def validate_non_negative_int(value: int) -> bool:
        """Validate value is non-negative integer."""
        return isinstance(value, int) and value >= 0

    @staticmethod
    def validate_string_not_empty(value: str) -> bool:
        """Validate string is not empty."""
        return isinstance(value, str) and len(value.strip()) > 0

    @staticmethod
    def validate_string_length(value: str, min_len: int = 1, max_len: int = 255) -> bool:
        """Validate string length is within bounds."""
        return isinstance(value, str) and min_len <= len(value) <= max_len

    @staticmethod
    def validate_date_not_past(check_date: date) -> bool:
        """Validate date is not in the past."""
        if not isinstance(check_date, (date, datetime)):
            return False
        comparison_date = check_date.date() if isinstance(check_date, datetime) else check_date
        return comparison_date >= date.today()

    @staticmethod
    def validate_date_range(start: date, end: date) -> bool:
        """Validate end date is after start date."""
        if not isinstance(start, (date, datetime)) or not isinstance(end, (date, datetime)):
            return False
        start_date = start.date() if isinstance(start, datetime) else start
        end_date = end.date() if isinstance(end, datetime) else end
        return end_date >= start_date

    @staticmethod
    def validate_slack_user_id(slack_id: str) -> bool:
        """Validate Slack user ID format (starts with U or B followed by alphanumerics)."""
        pattern = r"^[UB][A-Z0-9]{8,}$"
        return bool(re.match(pattern, slack_id))

    @staticmethod
    def validate_slack_workspace_id(workspace_id: str) -> bool:
        """Validate Slack workspace ID format (starts with T followed by alphanumerics)."""
        pattern = r"^T[A-Z0-9]{8,}$"
        return bool(re.match(pattern, workspace_id))

    @staticmethod
    def validate_telegram_chat_id(chat_id: int) -> bool:
        """Validate Telegram chat ID (should be negative for groups)."""
        return isinstance(chat_id, int)

    @staticmethod
    def validate_choice(value: Any, allowed_values: list[Any]) -> bool:
        """Validate value is in allowed choices."""
        return value in allowed_values


class EntityValidators:
    """Validators for complex business entities."""

    @staticmethod
    def validate_user_data(
        username: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validate user data fields.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: list[str] = []

        if username and not FieldValidators.validate_username(username):
            errors.append("Invalid username format (must be 3-32 alphanumeric characters)")

        if email and not FieldValidators.validate_email(email):
            errors.append("Invalid email format")

        if first_name and not FieldValidators.validate_string_length(first_name, 1, 50):
            errors.append("First name must be 1-50 characters")

        if last_name and not FieldValidators.validate_string_length(last_name, 1, 50):
            errors.append("Last name must be 1-50 characters")

        return len(errors) == 0, errors

    @staticmethod
    def validate_team_data(name: str, description: str | None = None) -> tuple[bool, list[str]]:
        """
        Validate team data fields.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: list[str] = []

        if not FieldValidators.validate_string_length(name, 1, 100):
            errors.append("Team name must be 1-100 characters")

        if description and not FieldValidators.validate_string_length(description, 1, 500):
            errors.append("Description must be 1-500 characters")

        return len(errors) == 0, errors

    @staticmethod
    def validate_schedule_data(
        team_id: int, duty_date: date, user_ids: list[int]
    ) -> tuple[bool, list[str]]:
        """
        Validate schedule data fields.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: list[str] = []

        if not FieldValidators.validate_positive_int(team_id):
            errors.append("Invalid team ID")

        if not isinstance(duty_date, (date, datetime)):
            errors.append("Invalid duty date format")

        if not isinstance(user_ids, list) or not user_ids:
            errors.append("User IDs must be a non-empty list")
        elif not all(isinstance(uid, int) and uid > 0 for uid in user_ids):
            errors.append("All user IDs must be positive integers")

        return len(errors) == 0, errors
