"""
Basic data structure used for general trading function in the trading platform.
"""

import numpy as np
from dataclasses import dataclass, field, asdict
from datetime import datetime as Datetime
from logging import INFO

from .constant import (
    Direction,
    Exchange,
    Interval,
    Offset,
    Status,
    Product,
    OptionType,
    OrderType,
)

ACTIVE_STATUSES = {Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED}


@dataclass
class BaseData:
    """
    Any data object needs a gateway_name as source
    and should inherit base data.
    """

    gateway_name: str

    extra: dict | None = field(default=None, init=False)

    def __str__(self):
        return f"{self.__class__.__name__}({','.join([f'{k}:{v}' for k, v in asdict(self).items()])})"


@dataclass
class TickData(BaseData):
    """
    Tick data contains information about:
        * last trade in market
        * orderbook snapshot
        * intraday market statistics.
    """

    symbol: str
    exchange: Exchange
    datetime: Datetime

    name: str = ""
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    last_price: float = 0
    last_volume: float = 0
    limit_up: float = 0
    limit_down: float = 0

    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    pre_close: float = 0

    bid_price_1: float = 0
    bid_price_2: float = np.nan
    bid_price_3: float = np.nan
    bid_price_4: float = np.nan
    bid_price_5: float = np.nan

    ask_price_1: float = 0
    ask_price_2: float = np.nan
    ask_price_3: float = np.nan
    ask_price_4: float = np.nan
    ask_price_5: float = np.nan

    bid_volume_1: float = 0
    bid_volume_2: float = 0
    bid_volume_3: float = 0
    bid_volume_4: float = 0
    bid_volume_5: float = 0

    ask_volume_1: float = 0
    ask_volume_2: float = 0
    ask_volume_3: float = 0
    ask_volume_4: float = 0
    ask_volume_5: float = 0

    localtime: Datetime | None = None

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def __str__(self):
        return (
            f"Tick@{self.datetime.isoformat()}: bid:{self.bid_price_1}({self.bid_volume_1}) "
            f"ask:{self.ask_price_1}({self.ask_volume_1}) last:{self.last_price}({self.last_volume})"
        )

    def fullstr(self) -> str:
        return super().__str__()

    def this_side_price(self, direction: Direction, level: int = 1) -> float:
        if direction == Direction.LONG:
            return getattr(self, f"bid_price_{level}")
        else:
            return getattr(self, f"ask_price_{level}")

    def opposite_side_price(self, direction: Direction, level: int = 1) -> float:
        if direction == Direction.LONG:
            return getattr(self, f"ask_price_{level}")
        else:
            return getattr(self, f"bid_price_{level}")

    def this_side_volume(self, direction: Direction, level: int = 1) -> float:
        if direction == Direction.LONG:
            return getattr(self, f"bid_volume_{level}")
        else:
            return getattr(self, f"ask_volume_{level}")

    def opposite_side_volume(self, direction: Direction, level: int = 1) -> float:
        if direction == Direction.LONG:
            return getattr(self, f"ask_volume_{level}")
        else:
            return getattr(self, f"bid_volume_{level}")


@dataclass
class BarData(BaseData):
    """
    Candlestick bar data of a certain trading period.
    """

    symbol: str
    exchange: Exchange
    datetime: Datetime

    interval: Interval | None = None
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    close_price: float = 0

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class OrderData(BaseData):
    """
    Order data contains information for tracking lastest status
    of a specific order.
    """

    symbol: str
    exchange: Exchange
    orderid: str

    type: OrderType = OrderType.LIMIT
    direction: Direction | None = None
    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    traded: float = 0
    status: Status = Status.SUBMITTING
    datetime: Datetime | None = None
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.vt_orderid: str = f"{self.gateway_name}.{self.orderid}"

    def is_active(self) -> bool:
        """
        Check if the order is active.
        """
        return self.status in ACTIVE_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        Create cancel request object from order.
        """
        req: CancelRequest = CancelRequest(
            orderid=self.orderid, symbol=self.symbol, exchange=self.exchange
        )
        return req

    def __str__(self):
        dt_str = "" if self.datetime is None else "@" + self.datetime.isoformat()
        return f"Order({self.vt_symbol}){dt_str}: {self.direction} {self.offset} {self.volume}@{self.price} traded:{self.traded} status:{self.status}"


@dataclass
class TradeData(BaseData):
    """
    Trade data contains information of a fill of an order. One order
    can have several trade fills.
    """

    symbol: str
    exchange: Exchange
    orderid: str
    tradeid: str
    direction: Direction | None = None

    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    datetime: Datetime | None = None

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.vt_orderid: str = f"{self.gateway_name}.{self.orderid}"
        self.vt_tradeid: str = f"{self.gateway_name}.{self.tradeid}"

    def __str__(self):
        dt_str = "" if self.datetime is None else "@" + self.datetime.isoformat()
        return f"Trade({self.vt_symbol})@{dt_str}: {self.direction} {self.offset} {self.volume}@{self.price}"


@dataclass
class PositionData(BaseData):
    """
    Position data is used for tracking each individual position holding.
    """

    symbol: str
    exchange: Exchange
    direction: Direction

    volume: float = 0
    frozen: float = 0
    price: float = 0
    pnl: float = 0
    yd_volume: float = 0

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.vt_positionid: str = (
            f"{self.gateway_name}.{self.vt_symbol}.{self.direction.value}"
        )


@dataclass
class AccountData(BaseData):
    """
    Account data contains information about balance, frozen and
    available.
    """

    accountid: str

    balance: float = 0
    frozen: float = 0

    def __post_init__(self) -> None:
        """"""
        self.available: float = self.balance - self.frozen
        self.vt_accountid: str = f"{self.gateway_name}.{self.accountid}"


@dataclass
class LogData(BaseData):
    """
    Log data is used for recording log messages on GUI or in log files.
    """

    msg: str
    level: int = INFO

    def __post_init__(self) -> None:
        """"""
        self.time: Datetime = Datetime.now()


@dataclass
class ContractData(BaseData):
    """
    Contract data contains basic information about each contract traded.
    """

    symbol: str
    exchange: Exchange
    name: str
    product: Product
    size: float
    pricetick: float

    min_volume: float = 1  # minimum trading volume of the contract
    max_volume: float = float("inf")
    stop_supported: bool = False  # whether server supports stop order
    net_position: bool = False  # whether gateway uses net position volume
    history_data: bool = False  # whether gateway provides bar history data

    option_strike: float = 0
    option_underlying: str = ""  # vt_symbol of underlying contract
    option_type: OptionType = None
    option_listed: Datetime = None
    option_expiry: Datetime = None
    option_portfolio: str = ""
    option_index: str = ""  # for identifying options with same strike price

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def round_price(self, price: float) -> float:
        """
        Round price to the nearest tick.
        """
        return round(price / self.pricetick) * self.pricetick

    def round_volume(self, volume: float) -> float:
        """
        Round volume to the nearest integer.
        """
        return round(volume / self.min_volume) * self.min_volume


@dataclass
class QuoteData(BaseData):
    """
    Quote data contains information for tracking lastest status
    of a specific quote.
    """

    symbol: str
    exchange: Exchange
    quoteid: str

    bid_price: float = 0.0
    bid_volume: int = 0
    ask_price: float = 0.0
    ask_volume: int = 0
    bid_offset: Offset = Offset.NONE
    ask_offset: Offset = Offset.NONE
    status: Status = Status.SUBMITTING
    datetime: Datetime | None = None
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.vt_quoteid: str = f"{self.gateway_name}.{self.quoteid}"

    def is_active(self) -> bool:
        """
        Check if the quote is active.
        """
        return self.status in ACTIVE_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        Create cancel request object from quote.
        """
        req: CancelRequest = CancelRequest(
            orderid=self.quoteid, symbol=self.symbol, exchange=self.exchange
        )
        return req


@dataclass
class SubscribeRequest:
    """
    Request sending to specific gateway for subscribing tick data update.
    """

    symbol: str
    exchange: Exchange

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class OrderRequest:
    """
    Request sending to specific gateway for creating a new order.
    """

    symbol: str
    exchange: Exchange
    direction: Direction
    type: OrderType
    volume: float
    price: float = 0
    offset: Offset = Offset.NONE
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def create_order_data(self, orderid: str, gateway_name: str) -> OrderData:
        """
        Create order data from request.
        """
        order: OrderData = OrderData(
            symbol=self.symbol,
            exchange=self.exchange,
            orderid=orderid,
            type=self.type,
            direction=self.direction,
            offset=self.offset,
            price=self.price,
            volume=self.volume,
            reference=self.reference,
            gateway_name=gateway_name,
        )
        return order


@dataclass
class CancelRequest:
    """
    Request sending to specific gateway for canceling an existing order.
    """

    orderid: str
    symbol: str
    exchange: Exchange

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class HistoryRequest:
    """
    Request sending to specific gateway for querying history data.
    """

    symbol: str
    exchange: Exchange
    start: Datetime
    end: Datetime | None = None
    interval: Interval | None = None

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class QuoteRequest:
    """
    Request sending to specific gateway for creating a new quote.
    """

    symbol: str
    exchange: Exchange
    bid_price: float
    bid_volume: int
    ask_price: float
    ask_volume: int
    bid_offset: Offset = Offset.NONE
    ask_offset: Offset = Offset.NONE
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def create_quote_data(self, quoteid: str, gateway_name: str) -> QuoteData:
        """
        Create quote data from request.
        """
        quote: QuoteData = QuoteData(
            symbol=self.symbol,
            exchange=self.exchange,
            quoteid=quoteid,
            bid_price=self.bid_price,
            bid_volume=self.bid_volume,
            ask_price=self.ask_price,
            ask_volume=self.ask_volume,
            bid_offset=self.bid_offset,
            ask_offset=self.ask_offset,
            reference=self.reference,
            gateway_name=gateway_name,
        )
        return quote


@dataclass
class Commission(BaseData):
    """
    Margin rate data for the contract .
    """

    symbol: str
    exchange: Exchange = Exchange.UNKNOWN  # 可能有空
    ratio_bymoney: float = 0.0  # 手续费率，如区分开平仓则为开仓手续费率
    ratio_byvolume: float = 0.0  # 手续费率，如区分开平仓则为开仓手续费率
    close_ratio_bymoney: float = 0.0  # 平仓手续费率，如不区分，则设为0
    close_ratio_byvolume: float = 0.0  # 平仓手续费，如不区分，则设为0
    close_today_ratio_bymoney: float = 0.0  # 平今手续费率，如不区分，则设为0
    close_today_ratio_byvolume: float = 0.0  # 平今手续费，如不区分，则设为0

    def __post_init__(self):
        """"""
        self.vt_symbol = f"{self.symbol}.{self.exchange}"

    def get_all_commission_senarios(self, price, size=1.0):
        money = price * size
        base_scenario = {"开": money * self.ratio_bymoney + self.ratio_byvolume}
        if self.close_ratio_bymoney < 1e-10 and self.close_ratio_byvolume < 1e-10:
            base_scenario["平"] = money * self.ratio_bymoney + self.ratio_byvolume
        else:
            base_scenario["平"] = (
                money * self.close_ratio_bymoney + self.close_ratio_byvolume
            )
        if (
            self.close_today_ratio_bymoney > 1e-10
            and self.close_today_ratio_byvolume > 1e-10
        ):
            base_scenario["平今"] = (
                money * self.close_today_ratio_bymoney + self.close_today_ratio_byvolume
            )
        return base_scenario

    def __call__(
        self,
        price: float,
        Offset: Offset = Offset.NONE,
        size: float = 1.0,
        is_today: bool = False,
    ):
        """
        计算手续费
        """
        if Offset == Offset.CLOSE and (
            self.close_ratio_bymoney > 1e-10 or self.close_ratio_byvolume > 1e-10
        ):
            if is_today and (
                self.close_today_ratio_bymoney > 1e-10
                or self.close_today_ratio_byvolume > 1e-10
            ):
                return (
                    price * size * self.close_today_ratio_bymoney
                    + self.close_today_ratio_byvolume
                )
            return price * size * self.close_ratio_bymoney + self.close_ratio_byvolume
        return price * size * self.ratio_bymoney + self.ratio_byvolume


@dataclass
class MarginRate(BaseData):
    """
    Margin rate data for the contract .
    """

    symbol: str
    exchange: Exchange = Exchange.UNKNOWN  # 可能有空
    long_margin_rate: float = 0.1  # 多头保证金率
    long_margin_perlot: float = 0.0  # 多头每手保证金
    short_margin_rate: float = 0.1  # 空头保证金率
    short_margin_perlot: float = 0.0  # 空头每手保证金

    def __post_init__(self):
        """"""
        self.vt_symbol = f"{self.symbol}.{self.exchange}"

    def get_all_margin_senarios(self, price, size=1.0):
        base_scenario = {
            "多": price * size * self.long_margin_rate + self.long_margin_perlot,
            "空": price * size * self.short_margin_rate + self.short_margin_perlot,
        }
        return base_scenario

    def __call__(self, price: float, direction: Direction, size: float = 1.0):
        """
        计算保证金
        """
        if direction == Direction.LONG:
            return price * size * self.long_margin_rate + self.long_margin_perlot
        return price * size * self.short_margin_rate + self.short_margin_perlot
