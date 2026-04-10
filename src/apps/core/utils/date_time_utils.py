import jdatetime
from django.utils import timezone

def to_jalali(dt, fmt='%Y/%m/%d - %H:%M'):
    if not dt:
        return None
    local_dt = timezone.localtime(dt)
    j_date = jdatetime.datetime.fromgregorian(datetime=local_dt)
    return j_date.strftime(fmt)