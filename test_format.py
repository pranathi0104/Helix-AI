import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from app import create_app
import datetime
import zoneinfo

app = create_app()

with app.app_context():
    format_ist = app.jinja_env.filters['format_ist']
    
    # 1. Test None
    print(f"None -> '{format_ist(None)}'")
    
    # 2. Test naive Python datetime (defaults to UTC)
    dt_naive = datetime.datetime(2023, 1, 1, 10, 0, 0)
    print(f"Naive dt (10:00 UTC) -> '{format_ist(dt_naive)}'") # Should be 15:30 IST
    
    # 3. Test aware Python datetime
    dt_aware = datetime.datetime(2023, 1, 1, 10, 0, 0, tzinfo=zoneinfo.ZoneInfo("UTC"))
    print(f"Aware dt (10:00 UTC) -> '{format_ist(dt_aware)}'") # Should be 15:30 IST
    
    # 4. Test ISO string
    dt_str = "2023-01-01T10:00:00"
    print(f"ISO string (naive) -> '{format_ist(dt_str)}'") # Should be 15:30 IST
    
    # 5. Test ISO string with Z
    dt_str_z = "2023-01-01T10:00:00Z"
    print(f"ISO string (Z) -> '{format_ist(dt_str_z)}'") # Should be 15:30 IST
    
    # 6. Test invalid string fallback
    dt_invalid = "not-a-date"
    print(f"Invalid string -> '{format_ist(dt_invalid)}'") # Should be not-a-date
    
    print("\nAll tests ran.")
