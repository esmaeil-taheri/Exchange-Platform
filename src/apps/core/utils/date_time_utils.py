import jdatetime
from django.utils import timezone


def to_jalali(dt, fmt='%Y/%m/%d - %H:%M'):
    if not dt:
        return None
    local_dt = timezone.localtime(dt)
    j_date = jdatetime.datetime.fromgregorian(datetime=local_dt)
    return j_date.strftime(fmt)

def get_date_time():
    # returns datetime with diffrent formats

    timestamp = timezone.localtime().timestamp()

    jalali_date_time = jdatetime.datetime.fromtimestamp(int(timestamp))

    return {'timestamp': int(timestamp), 'jalali_date_time': jalali_date_time}