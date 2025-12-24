import argparse
import csv
import sys
from datetime import datetime

# Parse command line arguments
parser = argparse.ArgumentParser(description='Convert NEM12 CSV data to Home Assistant import format')
parser.add_argument('input_file', type=argparse.FileType('r'), 
                    help='Input CSV file in NEM12 format')
parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout,
                    help='Output file (default: stdout)')
parser.add_argument('-s', '--statistic-id', default='sensor:power_usage',
                    help='Statistic ID for Home Assistant (default: sensor:power_usage)')
args = parser.parse_args()

# Initialize cumulative meter reading (state) - cumulative from start of file
# This represents the absolute meter reading, like what you'd see on a physical meter
meter_state = 0.0
previous_state = 0.0

# According to NEM12 spec:
# Record 200: RecordIndicator,NMI,NMIConfiguration,RegisterID,NMISuffix,
#             MDMDataStreamIdentifier,MeterSerialNumber,UOM,IntervalLength,NextScheduledReadDate
# Record 300: RecordIndicator,IntervalDate,IntervalValue1...IntervalValueN,
#             QualityMethod,ReasonCode,ReasonDescription,UpdateDateTime,MSATSLoadDateTime
# Number of intervals = 1440 / IntervalLength (e.g., 1440/30 = 48 for 30-minute intervals)

interval_length = 30  # Default, will be updated from 200 record

with args.input_file as fle, args.output as outfile:
    reader = csv.reader(fle)
    
    # Write header
    outfile.write("statistic_id,unit,start,state,sum\n")
    
    for line in reader:
        record_type = line[0]
        
        # Skip header records (100)
        if record_type == '100':
            continue
        
        # Parse NMI data details record (200) - contains metadata
        # Format per spec: RecordIndicator,NMI,NMIConfiguration,RegisterID,NMISuffix,
        #                   MDMDataStreamIdentifier,MeterSerialNumber,UOM,IntervalLength,NextScheduledReadDate
        if record_type == '200':
            # Extract interval length (field index 8, 0-based)
            # IntervalLength: Time in minutes of each Interval period: 5, 15, or 30
            if len(line) > 8:
                try:
                    interval_length = int(line[8])
                except (ValueError, IndexError):
                    interval_length = 30  # Default to 30 minutes
            continue
        
        # Process interval data record (300)
        # Format per spec: RecordIndicator,IntervalDate,IntervalValue1...IntervalValueN,
        #                   QualityMethod,ReasonCode,ReasonDescription,UpdateDateTime,MSATSLoadDateTime
        if record_type == '300':
            # Extract date (YYYYMMDD format) - field index 1
            date_str = line[1]
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            
            # Calculate expected number of intervals per spec: 1440 / IntervalLength
            expected_intervals = 1440 // interval_length
            
            # Extract interval values
            # Values start from index 2, continue until QualityMethod field
            # QualityMethod is typically the last field, but there may be optional fields after it
            # We'll process all numeric values from index 2 onwards until we hit a non-numeric or reach expected count
            interval_values = []
            for i in range(2, len(line)):
                try:
                    value = float(line[i])
                    interval_values.append(value)
                    # Stop if we've reached the expected number of intervals
                    if len(interval_values) >= expected_intervals:
                        break
                except (ValueError, IndexError):
                    # Non-numeric value encountered (likely QualityMethod or other metadata)
                    break
            
            # Verify we have the correct number of intervals
            if len(interval_values) != expected_intervals:
                print(f"Warning: Expected {expected_intervals} intervals but found {len(interval_values)} for date {date_str}")
            
            # Home Assistant requires timestamps at full hours only
            # Aggregate intervals into hourly records
            intervals_per_hour = 60 // interval_length
            
            # Store previous state to calculate sum correctly
            previous_state = meter_state
            
            # Group intervals by hour and sum them
            # Process intervals in groups of intervals_per_hour
            for hour in range(24):  # 24 hours in a day
                # Calculate the starting index for this hour
                start_idx = hour * intervals_per_hour
                
                # Check if we have enough intervals for this hour
                if start_idx >= len(interval_values):
                    break
                
                # Sum all intervals for this hour
                hourly_sum = 0.0
                for i in range(intervals_per_hour):
                    idx = start_idx + i
                    if idx < len(interval_values):
                        hourly_sum += interval_values[idx]
                
                # Create timestamp at full hour
                timestamp = date_obj.replace(hour=hour, minute=0)
                
                # In Home Assistant statistics import:
                # - sum should be the TOTAL INCREASING energy (cumulative)
                # - state can be left empty or also be the cumulative value
                #   Home Assistant will derive per-interval consumption as the
                #   difference between consecutive sum values.
                #
                # Therefore, we must store the cumulative meter reading in `sum`.

                # Update cumulative meter reading (state at END of this interval)
                meter_state += hourly_sum
                state_at_end = round(meter_state, 3)

                # Write cumulative value into both state and sum
                msg = (
                    f"{args.statistic_id},kWh,"
                    f"{timestamp.strftime('%d.%m.%Y %H:%M')},"
                    f"{state_at_end},{state_at_end}\n"
                )
                outfile.write(msg)
                
                # Update previous state for next iteration
                previous_state = state_at_end

if args.output != sys.stdout:
    print(f"Conversion complete! Output written to {args.output.name}")
else:
    print("Conversion complete! Output written to stdout", file=sys.stderr)
