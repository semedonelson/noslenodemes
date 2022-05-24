import requests
from stem import Signal
from stem.control import Controller


def get_tor_session():
    session = requests.session()
    # Tor uses the 9050 port as the default socks port
    session.proxies = {
        "http": "socks5://127.0.0.1:9050",
        "https": "socks5://127.0.0.1:9050",
    }
    return session


# signal TOR for a new connection
def renew_connection():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password="47Fwch1wFkqEk3PzV2HiGA==")
        controller.signal(Signal.NEWNYM)


def main():
    import logging

    logging.basicConfig(level=logging.DEBUG)
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    logging.critical("This is a critical message")


def main0():
    # Make a request through the Tor connection
    # IP visible through Tor
    session = get_tor_session()
    print(session.get("http://httpbin.org/ip").text)
    # Above should print an IP different than your public IP

    # Following prints your normal public IP
    print(requests.get("http://httpbin.org/ip").text)

    renew_connection()
    session = get_tor_session()
    print(session.get("http://httpbin.org/ip").text)
