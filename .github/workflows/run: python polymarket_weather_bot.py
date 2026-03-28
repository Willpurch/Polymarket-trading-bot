name: Run Weather Scanner
on:
  schedule:
    - cron: '0 * * * *' # This runs the bot automatically every hour
  workflow_dispatch:      # This allows you to click a button to run it manually

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install requests termcolor

      - name: Run Weather Bot
        run: python moon_dev_weather_bot.py
