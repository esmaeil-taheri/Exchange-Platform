import string
import random

def create_random_link():
    # returns a random link

    pool = string.ascii_lowercase + string.ascii_uppercase + string.digits
    random_link = random.choices(pool, k=12)
    return str.join('', random_link)