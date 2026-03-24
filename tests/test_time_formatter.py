import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.formatters import format_msec_to_time


time_1 = 6544.123
time_2 = 10000000
time_3 = 123456789123

print(format_msec_to_time(time_1))
print(format_msec_to_time(time_2))
print(format_msec_to_time(time_3))