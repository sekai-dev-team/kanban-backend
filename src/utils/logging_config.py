import logging.config
import os


def setup_logging(env="""development"""):
    """
    Configures the logging system for the application.
    """
    if env == """production""":
        log_level = """INFO"""
        handlers = ["""console""", """file"""]
    else:
        log_level = """DEBUG"""
        handlers = ["""console"""]

    logging_config = {
        """version""": 1,
        """disable_existing_loggers""": False,
        """formatters""": {
            """standard""": {
                """format""": """%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s"""
            },
        },
        """handlers""": {
            """console""": {
                """level""": """DEBUG""",
                """class""": """logging.StreamHandler""",
                """formatter""": """standard""",
            },
            """file""": {
                """level""": """INFO""",
                """class""": """logging.handlers.TimedRotatingFileHandler""",
                """formatter""": """standard""",
                """filename""": os.path.join("log", "app.log"),
                """when""": """midnight""",  # 每天午夜轮换
                """interval""": 1,
                """backupCount""": 30,  # 保留30天的日志
            },
        },
        """loggers""": {
            """""": {  # root logger
                """handlers""": handlers,
                """level""": log_level,
                """propagate""": True,
            },
            """uvicorn""": {  # For FastAPI/Uvicorn access logs
                """handlers""": handlers,
                """level""": log_level,
                """propagate""": False,
            },
            """uvicorn.access""": {  # For FastAPI/Uvicorn access logs
                """handlers""": handlers,
                """level""": log_level,
                """propagate""": False,
            },
        },
    }
    logging.config.dictConfig(logging_config)


if __name__ == """__main__""":
    # Example usage:
    setup_logging("""development""")
    logger = logging.getLogger(__name__)
    logger.debug("""This is a debug message.""")
    logger.info("""This is an info message.""")
    logger.warning("""This is a warning message.""")
    logger.error("""This is an error message.""")
    logger.critical("""This is a critical message.""")

    setup_logging("""production""")
    logger_prod = logging.getLogger(__name__)
    logger_prod.debug("""This is a debug message in production (should not appear).""")
    logger_prod.info("""This is an info message in production.""")
