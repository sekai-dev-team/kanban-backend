@echo off

REM Force development environment for local testing to see debug logs
set "APP_ENV=development"

REM Ensure log\tests directory exists (2>nul suppresses error if it already exists)
mkdir log\tests 2>nul

pytest ^
  --log-cli-level=INFO ^
  --log-cli-format="%%(asctime)s - %%(levelname)s - %%(name)s - %%(funcName)s:%%(lineno)d - %%(message)s" ^
  --log-file=log/tests/pytest.log ^
  --log-file-level=DEBUG ^
  --log-file-format="%%(asctime)s - %%(levelname)s - %%(name)s - %%(funcName)s:%%(lineno)d - %%(message)s"