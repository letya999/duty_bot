import pytest
from datetime import date, datetime, timedelta
from app.utils.validators import FieldValidators


class TestFieldValidators:
    """Test FieldValidators"""

    def test_validate_email_valid(self):
        """Test validating correct email addresses"""
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "123@example.com",
            "a@b.co"
        ]

        for email in valid_emails:
            assert FieldValidators.validate_email(email) is True, f"Email {email} should be valid"

    def test_validate_email_invalid(self):
        """Test rejecting invalid email addresses"""
        invalid_emails = [
            "not_an_email",
            "@example.com",
            "test@",
            "test@.com",
            "test@example",
            "test @example.com",
            "test@example .com",
            "",
            "test@@example.com"
        ]

        for email in invalid_emails:
            assert FieldValidators.validate_email(email) is False, f"Email {email} should be invalid"

    def test_validate_username_valid(self):
        """Test validating correct usernames"""
        valid_usernames = [
            "user123",
            "user_name",
            "user-name",
            "abc",
            "a_b-c",
            "user123456789",
            "User_Name",
            "USR",
            "a" * 32
        ]

        for username in valid_usernames:
            assert FieldValidators.validate_username(username) is True, f"Username {username} should be valid"

    def test_validate_username_invalid(self):
        """Test rejecting invalid usernames"""
        invalid_usernames = [
            "ab",  # Too short
            "user@name",  # Invalid char
            "user name",  # Space
            "user!name",  # Special char
            "",
            "a" * 33,  # Too long
            "123",  # Valid chars but exactly 3 is OK, less is not
            "user.name",  # Dot not allowed
            "Ü@ser",  # Unicode with special char
        ]

        for username in invalid_usernames:
            if username == "123":
                # 3 chars is actually valid according to pattern
                assert FieldValidators.validate_username(username) is True
            else:
                assert FieldValidators.validate_username(username) is False, f"Username {username} should be invalid"

    def test_validate_positive_int_valid(self):
        """Test validating positive integers"""
        assert FieldValidators.validate_positive_int(1) is True
        assert FieldValidators.validate_positive_int(100) is True
        assert FieldValidators.validate_positive_int(999999) is True

    def test_validate_positive_int_invalid(self):
        """Test rejecting non-positive integers"""
        assert FieldValidators.validate_positive_int(0) is False
        assert FieldValidators.validate_positive_int(-1) is False
        assert FieldValidators.validate_positive_int(-100) is False
        assert FieldValidators.validate_positive_int("1") is False
        assert FieldValidators.validate_positive_int(1.5) is False
        assert FieldValidators.validate_positive_int(None) is False

    def test_validate_non_negative_int_valid(self):
        """Test validating non-negative integers"""
        assert FieldValidators.validate_non_negative_int(0) is True
        assert FieldValidators.validate_non_negative_int(1) is True
        assert FieldValidators.validate_non_negative_int(100) is True

    def test_validate_non_negative_int_invalid(self):
        """Test rejecting negative integers"""
        assert FieldValidators.validate_non_negative_int(-1) is False
        assert FieldValidators.validate_non_negative_int(-100) is False
        assert FieldValidators.validate_non_negative_int("0") is False
        assert FieldValidators.validate_non_negative_int(1.5) is False
        assert FieldValidators.validate_non_negative_int(None) is False

    def test_validate_string_not_empty_valid(self):
        """Test validating non-empty strings"""
        assert FieldValidators.validate_string_not_empty("text") is True
        assert FieldValidators.validate_string_not_empty("a") is True
        assert FieldValidators.validate_string_not_empty(" text ") is True  # Spaces are trimmed but string has content
        assert FieldValidators.validate_string_not_empty("   text") is True

    def test_validate_string_not_empty_invalid(self):
        """Test rejecting empty or whitespace-only strings"""
        assert FieldValidators.validate_string_not_empty("") is False
        assert FieldValidators.validate_string_not_empty("   ") is False
        assert FieldValidators.validate_string_not_empty("\t\n") is False
        assert FieldValidators.validate_string_not_empty(None) is False
        assert FieldValidators.validate_string_not_empty(123) is False

    def test_validate_string_length_valid(self):
        """Test validating string length"""
        assert FieldValidators.validate_string_length("test", 1, 10) is True
        assert FieldValidators.validate_string_length("test", 4, 4) is True
        assert FieldValidators.validate_string_length("a", 1, 255) is True
        assert FieldValidators.validate_string_length("x" * 255, 1, 255) is True

    def test_validate_string_length_invalid(self):
        """Test rejecting strings outside length bounds"""
        assert FieldValidators.validate_string_length("test", 5, 10) is False  # Too short
        assert FieldValidators.validate_string_length("test", 1, 3) is False  # Too long
        assert FieldValidators.validate_string_length("", 1, 255) is False  # Too short
        assert FieldValidators.validate_string_length("x" * 256, 1, 255) is False  # Too long
        assert FieldValidators.validate_string_length(None, 1, 255) is False
        assert FieldValidators.validate_string_length(123, 1, 255) is False

    def test_validate_string_length_custom_bounds(self):
        """Test string length with custom bounds"""
        assert FieldValidators.validate_string_length("abc", 2, 5) is True
        assert FieldValidators.validate_string_length("ab", 2, 5) is True
        assert FieldValidators.validate_string_length("abcde", 2, 5) is True
        assert FieldValidators.validate_string_length("a", 2, 5) is False
        assert FieldValidators.validate_string_length("abcdef", 2, 5) is False

    def test_validate_date_not_past_valid(self):
        """Test validating future or today dates"""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        assert FieldValidators.validate_date_not_past(today) is True
        assert FieldValidators.validate_date_not_past(tomorrow) is True

    def test_validate_date_not_past_invalid(self):
        """Test rejecting past dates"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        past = today - timedelta(days=365)

        assert FieldValidators.validate_date_not_past(yesterday) is False
        assert FieldValidators.validate_date_not_past(past) is False

    def test_validate_date_not_past_datetime(self):
        """Test with datetime objects"""
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        yesterday = now - timedelta(days=1)

        assert FieldValidators.validate_date_not_past(now) is True
        assert FieldValidators.validate_date_not_past(tomorrow) is True
        assert FieldValidators.validate_date_not_past(yesterday) is False

    def test_validate_date_not_past_invalid_type(self):
        """Test that invalid types are rejected"""
        assert FieldValidators.validate_date_not_past("2025-01-01") is False
        assert FieldValidators.validate_date_not_past(None) is False
        assert FieldValidators.validate_date_not_past(123) is False
