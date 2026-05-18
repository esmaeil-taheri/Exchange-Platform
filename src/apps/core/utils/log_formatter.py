import logging

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"

LEVEL_COLORS = {
    "DEBUG":    "\033[36m",   # Cyan
    "INFO":     "\033[32m",   # Green
    "WARNING":  "\033[33m",   # Yellow
    "ERROR":    "\033[31m",   # Red
    "CRITICAL": "\033[35m",   # Magenta
}


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output in the development environment.
    In production, a verbose formatter without colors is used.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Return request_id and user_id from the record or use defaults
        if not hasattr(record, 'request_id'):
            record.request_id = '-'
        if not hasattr(record, 'user_id'):
            record.user_id = 'anon'

        color = LEVEL_COLORS.get(record.levelname, RESET)
        record.levelname = f"{color}{BOLD}{record.levelname:<8}{RESET}"

        return super().format(record)
