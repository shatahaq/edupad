"""Kode keluar proses & exception bersama."""

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_LOGIN_REQUIRED = 2  # sesi habis; perlu login manual


class LoginRequired(Exception):
    """Sesi login sudah tidak berlaku."""
