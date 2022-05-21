import requests

# use to parse html text
from lxml.html import fromstring
from itertools import cycle
import traceback
import json
import time


def to_get_proxies():
    # website to get free proxies
    url = "https://free-proxy-list.net/"

    response = requests.get(url)

    parser = fromstring(response.text)
    # using a set to avoid duplicate IP entries.
    proxies = set()

    for i in parser.xpath("//tbody/tr")[:100]:

        # to check if the corresponding IP is of type HTTPS
        if i.xpath('.//td[7][contains(text(),"yes")]'):

            # Grabbing IP and corresponding PORT
            proxy = ":".join(
                [i.xpath(".//td[1]/text()")[0], i.xpath(".//td[2]/text()")[0]]
            )

            proxies.add(proxy)
    return proxies


def main():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=weth&vs_currencies=usd"
    while True:
        proxies = to_get_proxies()
        print("proxies: ", len(proxies))
        if len(proxies) > 0:
            for proxy in proxies:
                print("proxy: ", proxy)
                try:
                    response = requests.get(
                        url, proxies={"http": proxy, "https": proxy}
                    )
                    if response.status_code == 200:
                        j = json.loads(response.content.decode("utf-8"))
                        print(j)
                except Exception as e:
                    continue
        # time.sleep(10)


def main0():
    proxies = to_get_proxies()
    print("proxies: ", len(proxies))
    for item in proxies:
        print(item)


if __name__ == "__main__":
    main()
