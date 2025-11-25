import datetime
from random import randint

def id_in_html():
    now_ts = datetime.datetime.now(datetime.UTC).timestamp()
    rint = randint(10000, 99999)
    return f"{now_ts}.{rint}"


if __name__ == "__main__":
    res = id_in_html()
    print(res)