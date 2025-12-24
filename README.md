# Import NEM12 Detailed data into Home Assistant energy dashboard

This script converts your [NEM12 detailed](https://www.aemo.com.au/-/media/files/electricity/nem/retail_and_metering/market_settlement_and_transfer_solutions/2024/mdff-specification-nem12-nem13-v26-clean-final.pdf?rev=c0145cdfe1114a6dad0abad6586c3cf9&sc_lang=en) CSV data (taken from your energy distributor in Australia East Coast),
and converts that data into a csv format for Home Assistant [Import Historical Energy HACS integration](https://github.com/patrickvorgers/Home-Assistant-Import-Energy-Data).

This project has NO external dependencies, and is a single python file.

# Usage

```commandline
usage: main.py [-h] [-o OUTPUT] [-s STATISTIC_ID] input_file

Convert NEM12 CSV data to Home Assistant import format

positional arguments:
  input_file            Input CSV file in NEM12 format

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file (default: stdout)
  -s STATISTIC_ID, --statistic-id STATISTIC_ID
                        Statistic ID for Home Assistant (default: sensor:power_usage)
```

Example:
```commandline
python main.py ~/Downloads/..._AUSNETSERVICES_NEM12DETAILED.csv -o output.csv -s "sensor:power_usage"
```

# How to use

1. Download your detailed NEM12 data from your poles and wires company (eg. AusNet, PowerCore)
2. Run this script over the file, and write an output csv file (see example usage above).
3. Copy the output csv to home assistant (into the configuration directory).
4. Use the [Import Historical Energy HACS integration](https://github.com/patrickvorgers/Home-Assistant-Import-Energy-Data).
5. Open the "Developer tools" > "Actions" tab.
6. Select the "Import Statistics from file" action.
7. Set the values
  a. filename (the name of the file in the configuratoin directory)
  b. timezone_identifier "Australia/Brisbane" **NOTE: Must be set to Brisbane, due to daylight savings issues**
  c. set delimiter to comma
  d. ensure decimal is disabled
  e. `datetime_format`: `%d.%m.%Y %H:%M`
  f. `unit_from_entity`: false (toggle off)
8. Press "Perform action"

# Off by one hour

If you are seeing that the usage does not match up by about 1 hour, it may be because you forgot to set the timezone to `Australia/Brisbane` when importing the CSV.
The NEM12 data always observes AEST, so you need to pick a timezone that is always AEST, even during the summer.
