"""
General constant enums used in the trading platform.
"""

from enum import Enum

from .locale import _


class VNBaseEnum(Enum):
    def __str__(self):
        return self.value


class Direction(VNBaseEnum):
    """
    Direction of order/trade/position.
    """

    LONG = _("多")
    SHORT = _("空")
    NET = _("净")

    def opposite(self):
        if self == Direction.LONG:
            return Direction.SHORT
        elif self == Direction.SHORT:
            return Direction.LONG
        return Direction.NET

    def __neg__(self):
        return self.opposite()

    def __mul__(self, other):
        if isinstance(other, float | int) and other < 0 or other == Direction.SHORT:
            return self.opposite()
        if other == 0:
            return Direction.NET
        return self


class Offset(VNBaseEnum):
    """
    Offset of order/trade.
    """

    NONE = ""
    OPEN = _("开")
    CLOSE = _("平")
    CLOSETODAY = _("平今")
    CLOSEYESTERDAY = _("平昨")


class Status(VNBaseEnum):
    """
    Order status.
    """

    SUBMITTING = _("提交中")
    NOTTRADED = _("未成交")
    PARTTRADED = _("部分成交")
    ALLTRADED = _("全部成交")
    CANCELLED = _("已撤销")
    REJECTED = _("拒单")
    UNKNOWN = _("未知")

    def is_active(self):
        return self in [Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED]


class Product(VNBaseEnum):
    """
    Product class.
    """

    EQUITY = _("股票")
    FUTURES = _("期货")
    OPTION = _("期权")
    INDEX = _("指数")
    FOREX = _("外汇")
    SPOT = _("现货")
    ETF = "ETF"
    BOND = _("债券")
    WARRANT = _("权证")
    SPREAD = _("价差")
    FUND = _("基金")
    CFD = "CFD"
    SWAP = _("互换")


class OrderType(VNBaseEnum):
    """
    Order type.
    """

    LIMIT = _("限价")
    MARKET = _("市价")
    STOP = "STOP"
    FAK = "FAK"
    FOK = "FOK"
    RFQ = _("询价")
    UNKNOWN = _("未知")


class OptionType(VNBaseEnum):
    """
    Option type.
    """

    CALL = _("看涨期权")
    PUT = _("看跌期权")


class Exchange(VNBaseEnum):
    """
    Exchange.
    """

    # Chinese
    CFFEX = "CFFEX"  # China Financial Futures Exchange
    SHFE = "SHFE"  # Shanghai Futures Exchange
    CZCE = "CZCE"  # Zhengzhou Commodity Exchange
    DCE = "DCE"  # Dalian Commodity Exchange
    INE = "INE"  # Shanghai International Energy Exchange
    GFEX = "GFEX"  # Guangzhou Futures Exchange
    SSE = "SSE"  # Shanghai Stock Exchange
    SZSE = "SZSE"  # Shenzhen Stock Exchange
    BSE = "BSE"  # Beijing Stock Exchange
    SHHK = "SHHK"  # Shanghai-HK Stock Connect
    SZHK = "SZHK"  # Shenzhen-HK Stock Connect
    SGE = "SGE"  # Shanghai Gold Exchange
    WXE = "WXE"  # Wuxi Steel Exchange
    CFETS = "CFETS"  # CFETS Bond Market Maker Trading System
    XBOND = "XBOND"  # CFETS X-Bond Anonymous Trading System

    # Global
    SMART = "SMART"  # Smart Router for US stocks
    NYSE = "NYSE"  # New York Stock Exchnage
    NASDAQ = "NASDAQ"  # Nasdaq Exchange
    ARCA = "ARCA"  # ARCA Exchange
    EDGEA = "EDGEA"  # Direct Edge Exchange
    ISLAND = "ISLAND"  # Nasdaq Island ECN
    BATS = "BATS"  # Bats Global Markets
    IEX = "IEX"  # The Investors Exchange
    AMEX = "AMEX"  # American Stock Exchange
    TSE = "TSE"  # Toronto Stock Exchange
    NYMEX = "NYMEX"  # New York Mercantile Exchange
    COMEX = "COMEX"  # COMEX of CME
    GLOBEX = "GLOBEX"  # Globex of CME
    IDEALPRO = "IDEALPRO"  # Forex ECN of Interactive Brokers
    CME = "CME"  # Chicago Mercantile Exchange
    ICE = "ICE"  # Intercontinental Exchange
    SEHK = "SEHK"  # Stock Exchange of Hong Kong
    HKFE = "HKFE"  # Hong Kong Futures Exchange
    SGX = "SGX"  # Singapore Global Exchange
    CBOT = "CBT"  # Chicago Board of Trade
    CBOE = "CBOE"  # Chicago Board Options Exchange
    CFE = "CFE"  # CBOE Futures Exchange
    DME = "DME"  # Dubai Mercantile Exchange
    EUREX = "EUX"  # Eurex Exchange
    APEX = "APEX"  # Asia Pacific Exchange
    LME = "LME"  # London Metal Exchange
    BMD = "BMD"  # Bursa Malaysia Derivatives
    TOCOM = "TOCOM"  # Tokyo Commodity Exchange
    EUNX = "EUNX"  # Euronext Exchange
    KRX = "KRX"  # Korean Exchange
    OTC = "OTC"  # OTC Product (Forex/CFD/Pink Sheet Equity)
    IBKRATS = "IBKRATS"  # Paper Trading Exchange of IB
    AEB = "AEB"  # Amsterdam Exchange

    OKEXD = "OKEXD"  # okex derivative
    OKEXS = "OKEXS"  # okex spot

    # Special Function
    LOCAL = "LOCAL"  # For local generated data
    UNKNOWN = "UNKNOWN"


class Currency(VNBaseEnum):
    """
    Currency.
    """

    USD = "USD"
    HKD = "HKD"
    CNY = "CNY"
    CAD = "CAD"
    EUR = "EUR"


class Interval(VNBaseEnum):
    """
    Interval of bar data.
    """

    MINUTE = "1m"
    HOUR = "1h"
    DAILY = "d"
    WEEKLY = "w"
    TICK = "tick"
