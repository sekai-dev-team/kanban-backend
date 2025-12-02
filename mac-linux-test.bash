APP_ENV="development" # Force development environment for local testing to see debug logs
mkdir -p log/tests # Ensure log/tests directory exists
pytest \
  --log-cli-level=INFO \
  --log-cli-format="%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s" \
  --log-file=log/tests/pytest.log \
  --log-file-level=DEBUG \
  --log-file-format="%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s"