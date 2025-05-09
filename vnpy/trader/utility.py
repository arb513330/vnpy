"""
General utility functions.
"""

import re
import subprocess
from enum import Enum
import json
import warnings
import logging
import logging.handlers
import keyring
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from types import ModuleType
from collections.abc import Callable
from decimal import Decimal
from math import floor, ceil
from cryptography.fernet import Fernet

import numpy as np
import talib
from zoneinfo import ZoneInfo  # noqa

from .object import BarData, TickData
from .constant import Exchange, Interval
from .locale import _


class Encryptor:
    """
    Encrypt and decrypt string.
    """

    def __init__(self) -> None:
        key = keyring.get_password("vn.trader", "encrypt_key")
        if not key:
            key = Fernet.generate_key().decode()
            keyring.set_password("vn.trader", "encrypt_key", key)
        self.cipher_suite: Fernet = Fernet(key)

    def encrypt(self, text: str) -> str:
        """
        Encrypt a string.
        """
        return self.cipher_suite.encrypt(text.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt a string.
        """
        return self.cipher_suite.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")


encryptor: Encryptor = Encryptor()


def extract_vt_symbol(vt_symbol: str) -> tuple[str, Exchange]:
    """
    :return: (symbol, exchange)
    """
    symbol, exchange_str = vt_symbol.rsplit(".", 1)
    return symbol, Exchange(exchange_str)


def generate_vt_symbol(symbol: str, exchange: Exchange) -> str:
    """
    return vt_symbol
    """
    return f"{symbol}.{exchange.value}"


def _get_trader_dir(temp_name: str) -> tuple[Path, Path]:
    """
    Get path where trader is running in.
    """
    cwd: Path = Path.cwd()
    temp_path: Path = cwd.joinpath(temp_name)

    # If .vntrader folder exists in current working directory,
    # then use it as trader running path.
    if temp_path.exists():
        return cwd, temp_path

    # Otherwise use home path of system.
    home_path: Path = Path.home()
    temp_path: Path = home_path.joinpath(temp_name)

    # Create .vntrader folder under home path if not exist.
    if not temp_path.exists():
        temp_path.mkdir()

    return home_path, temp_path


TRADER_DIR, TEMP_DIR = _get_trader_dir(".vntrader")
sys.path.append(str(TRADER_DIR))


def get_file_path(filename: str) -> Path:
    """
    Get path for temp file with filename.
    """
    return TEMP_DIR.joinpath(filename)


def get_folder_path(folder_name: str) -> Path:
    """
    Get path for temp folder with folder name.
    """
    folder_path: Path = TEMP_DIR.joinpath(folder_name)
    if not folder_path.exists():
        folder_path.mkdir()
    return folder_path


def get_icon_path(filepath: str, ico_name: str) -> str:
    """
    Get path for icon file with ico name.
    """
    ui_path: Path = Path(filepath).parent
    icon_path: Path = ui_path.joinpath("ico", ico_name)
    return str(icon_path)


def load_json(filename: str) -> dict:
    """
    Load data from json file in temp path.
    """
    filepath: Path = get_file_path(filename)

    if filepath.exists():
        with open(filepath, encoding="UTF-8") as f:
            data: dict = json.load(f)
        return data
    else:
        save_json(filename, {})
        return {}


# Extend the JSONEncoder class
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def save_json(filename: str, data: dict) -> None:
    """
    Save data into json file in temp path.
    """
    filepath: Path = get_file_path(filename)
    with open(filepath, mode="w+", encoding="UTF-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, cls=NpEncoder)


def round_to(value: float, target: float) -> float:
    """
    Round price to price tick value.
    """
    decimal_value: Decimal = Decimal(str(value))
    decimal_target: Decimal = Decimal(str(target))
    rounded: float = float(int(round(decimal_value / decimal_target)) * decimal_target)
    return rounded


def floor_to(value: float, target: float) -> float:
    """
    Similar to math.floor function, but to target float number.
    """
    decimal_value: Decimal = Decimal(str(value))
    decimal_target: Decimal = Decimal(str(target))
    result: float = float(int(floor(decimal_value / decimal_target)) * decimal_target)
    return result


def ceil_to(value: float, target: float) -> float:
    """
    Similar to math.ceil function, but to target float number.
    """
    decimal_value: Decimal = Decimal(str(value))
    decimal_target: Decimal = Decimal(str(target))
    result: float = float(int(ceil(decimal_value / decimal_target)) * decimal_target)
    return result


def get_digits(value: float) -> int:
    """
    Get number of digits after decimal point.
    """
    value_str: str = str(value)

    if "e-" in value_str:
        _, buf = value_str.split("e-")
        return int(buf)
    elif "." in value_str:
        _, buf = value_str.split(".")
        return len(buf)
    else:
        return 0


def get_plain_log_file(filename) -> Path:
    """
    Get path for plain log file.
    """
    filename = filename if filename.endswith(".log") else f"{filename}.log"
    from .setting import SETTINGS  # pylint: disable=import-outside-toplevel

    if SETTINGS.get("log.path", "") != "":
        log_path = Path(SETTINGS["log.path"])
        log_path.mkdir(exist_ok=True, parents=True)
        return log_path.joinpath(filename)
    return get_folder_path("log").joinpath(filename)


def setup_plain_logger(
    logger_name: str,
    logger_level: int,
    logger_filename: str = None,
    stream: bool = False,
    formatter_str: str = "[%(process)s:%(threadName)s](%(asctime)s) %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s",
    max_bytes: int = 0,
    backup_count: int = 3,
) -> logging.Logger:
    """
    Setup plain logger to file.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logger_level)

    # Remove all existed handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    parent_logger = logger.parent
    while parent_logger:
        for handler in parent_logger.handlers[:]:
            parent_logger.removeHandler(handler)
        parent_logger = parent_logger.parent

    logger_filename = logger_filename or logger_name
    # Create a file handler
    if max_bytes > 0:
        handler = logging.handlers.RotatingFileHandler(
            get_plain_log_file(logger_filename),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
    else:
        handler = logging.FileHandler(get_plain_log_file(logger_filename), mode="a")

    formatter = logging.Formatter(formatter_str)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


class IntraDayTradingTime:
    class TimeInRange(Enum):
        OUT_OF_RANGE = 0
        IN_RANGE = 1
        AT_RANGE_END = 2

    def __init__(
        self,
        sessions: list[tuple[time, time]],
        start_offset: float | timedelta | list[float | timedelta] = 0,
        end_offset: float | timedelta | list[float | timedelta] = 0,
        break_threshold_for_offest: float | timedelta = timedelta(hours=1),
    ) -> None:
        """"""
        self.sessions = sorted(sessions, key=lambda x: x[1])
        self._validate_sessions(self.sessions)
        self.sessions_with_offset = self._cal_sessions_with_offset(
            start_offset, end_offset, break_threshold_for_offest
        )
        self._validate_sessions(self.sessions_with_offset)

    @staticmethod
    def _validate_sessions(sessions: list[tuple[time, time]]) -> None:
        """"""
        num_sessions = len(sessions)
        for i in range(num_sessions):
            start, end = sessions[i]
            if not isinstance(start, time) or not isinstance(end, time):
                raise ValueError(f"Invalid session format: {start}-{end}")
            if start == end:
                raise ValueError(f"Empty session: {start}-{end}")
        for i in range(num_sessions - 1):
            if sessions[i][1] > sessions[i + 1][0]:
                raise ValueError(
                    f"Overlapping sessions: {sessions[i]}-{sessions[i + 1]}"
                )

    def _cal_sessions_with_offset(
        self,
        start_offset: float | timedelta | list[float | timedelta],
        end_offset: float | timedelta | list[float | timedelta],
        break_threshold_for_offest: float | timedelta,
    ) -> list[tuple[time, time]]:
        """"""
        sessions_with_offset = []
        num_sessions = len(self.sessions)

        def process_offset(offset):
            if isinstance(offset, int | float):
                offset = timedelta(seconds=offset)
            if isinstance(offset, list | tuple):
                if len(offset) != num_sessions:
                    raise ValueError(
                        "Length of offset must be equal to the number of sessions"
                    )
                offset = [
                    timedelta(seconds=o) if isinstance(o, int | float) else o
                    for o in offset
                ]
            else:
                offset = [offset] * num_sessions
            return offset

        start_offset = process_offset(start_offset)
        end_offset = process_offset(end_offset)

        if isinstance(break_threshold_for_offest, int | float):
            break_threshold_for_offest = timedelta(seconds=break_threshold_for_offest)
        for i, (start, end) in enumerate(self.sessions):
            dt_start = datetime.combine(datetime.today(), start)
            dt_end = datetime.combine(datetime.today(), end)
            previous_end = datetime.combine(
                datetime.today(), self.sessions[(i - 1) % num_sessions][1]
            )
            next_start = datetime.combine(
                datetime.today(), self.sessions[(i + 1) % num_sessions][0]
            )
            if previous_end > dt_start:
                previous_end -= timedelta(days=1)
            if next_start < dt_end:
                next_start += timedelta(days=1)
            if dt_start - previous_end > break_threshold_for_offest:
                dt_start += start_offset[i]
            if next_start - dt_end > break_threshold_for_offest:
                dt_end -= end_offset[i]
            sessions_with_offset.append((dt_start.time(), dt_end.time()))

        return sessions_with_offset

    def trading_time_in_session(self, dt: datetime) -> TimeInRange:
        """"""
        for start, end in self.sessions:
            if (
                start <= dt.time() < end
                or start > end
                and (dt.time() >= start or dt.time() < end)
            ):
                return self.TimeInRange.IN_RANGE
            elif (
                dt.hour == end.hour
                and dt.minute == end.minute
                and dt.second == end.second
                and dt.microsecond == end.microsecond
            ):
                return self.TimeInRange.AT_RANGE_END

        return self.TimeInRange.OUT_OF_RANGE

    def trading_time_in_session_with_offset(self, dt: datetime) -> TimeInRange:
        """"""
        for start, end in self.sessions_with_offset:
            if (
                start <= dt.time() < end
                or start > end
                and (dt.time() >= start or dt.time() < end)
            ):
                return self.TimeInRange.IN_RANGE
            elif (
                dt.hour == end.hour
                and dt.minute == end.minute
                and dt.second == end.second
                and dt.microsecond == end.microsecond
            ):
                return self.TimeInRange.AT_RANGE_END
        return self.TimeInRange.OUT_OF_RANGE


class BarGenerator:
    """
    For:
    1. generating 1 minute bar data from tick data
    2. generating x minute bar/x hour bar data from 1-minute data
    Notice:
    1. for x minute bar, x must be able to divide 60: 2, 3, 5, 6, 10, 15, 20, 30
    2. for x hour bar, x can be any number
    """

    def __init__(
        self,
        on_bar: Callable,
        window: int = 0,
        on_window_bar: Callable | None = None,
        interval: Interval = Interval.MINUTE,
        daily_end: time | None = None,
        trade_time: IntraDayTradingTime | None = None,
    ) -> None:
        """Constructor"""
        self.bar: BarData | None = None
        self.on_bar: Callable = on_bar
        self.pending_trade_in_current_bar: bool = True

        self.interval: Interval = interval
        self.interval_count: int = 0

        self.hour_bar: BarData | None = None
        self.daily_bar: BarData | None = None

        self.window: int = window
        self.window_bar: BarData | None = None
        self.on_window_bar: Callable | None = on_window_bar
        self.pending_trade_in_current_windows_bar: bool = True

        self.last_tick: TickData | None = None

        self.daily_end: time | None = daily_end
        if self.interval == Interval.DAILY and not self.daily_end:
            raise RuntimeError(_("合成日K线必须传入每日收盘时间"))

        self.trade_time: IntraDayTradingTime | None = trade_time

    def update_tick(self, tick: TickData) -> None:
        """
        Update new tick data into generator.
        """
        new_minute: bool = False

        # Filter tick data with 0 last price
        if not tick.last_price:
            return

        # Filter tick data with older timestamp
        if self.last_tick and tick.datetime < self.last_tick.datetime:
            return

        tick_validate = self.validate_tick_time(tick.datetime)
        if (
            tick_validate < 1
            or tick_validate == 2
            and (self.last_tick and tick.volume == self.last_tick.volume)
        ):
            return

        if not self.bar:
            new_minute = True
        elif (
            self.bar.datetime.minute != tick.datetime.minute
            or self.bar.datetime.hour != tick.datetime.hour
        ) and tick_validate == 1:
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0)
            self.on_bar(self.bar)

            new_minute = True

        if new_minute:
            self.bar = BarData(
                symbol=tick.symbol,
                exchange=tick.exchange,
                interval=Interval.MINUTE,
                datetime=tick.datetime.replace(second=0, microsecond=0),
                gateway_name=tick.gateway_name,
                open_price=tick.last_price,
                high_price=tick.last_price,
                low_price=tick.last_price,
                close_price=tick.last_price,
                volume=tick.last_volume,
                turnover=max(0.0, tick.turnover - self.last_tick.turnover)
                if self.last_tick
                else tick.turnover,
                open_interest=tick.open_interest,
            )
            self.pending_trade_in_current_bar = (
                self.last_tick is not None and tick.volume == self.last_tick.volume
            )
        else:
            self.bar.close_price = tick.last_price
            self.bar.open_interest = tick.open_interest

            if self.pending_trade_in_current_bar and (
                self.last_tick is None or tick.volume > self.last_tick.volume
            ):
                self.pending_trade_in_current_bar = False
                self.bar.open_price = tick.last_price
                self.bar.high_price = tick.last_price
                self.bar.low_price = tick.last_price
            else:
                self.bar.high_price = max(self.bar.high_price, tick.last_price)
                self.bar.low_price = min(self.bar.low_price, tick.last_price)

            # Since the CTP tick is actually 500ms sliced, sometimes within 500 ms the high/low price generated
            # but last_price at 500ms end is not the same. So here we use the high/low recorded in tick data from CTP
            # this doesn't cover all the cases.
            if self.last_tick is None or self.last_tick.high_price < tick.high_price:
                self.bar.high_price = tick.high_price
            if self.last_tick is None or self.last_tick.low_price > tick.low_price:
                self.bar.low_price = tick.low_price

            self.bar.volume += tick.last_volume
            self.bar.turnover += (
                max(0.0, tick.turnover - self.last_tick.turnover)
                if self.last_tick
                else tick.turnover
            )

        self.update_bar_minute_window(self.bar, new_minute)

        self.last_tick = tick

    def update_bar(self, bar: BarData) -> None:
        """
        Update 1 minute bar into generator
        """
        self.bar = bar
        if self.interval == Interval.MINUTE:
            self.update_bar_minute_window(bar)
        elif self.interval == Interval.HOUR:
            self.update_bar_hour_window(bar)
        else:
            self.update_bar_daily_window(bar)

    def validate_tick_time(self, tick_time: datetime) -> int:
        """
        Validate if tick is in trade time
        """
        now_time = datetime.now(tz=ZoneInfo("Asia/Shanghai"))

        if abs((now_time - tick_time).total_seconds()) > 60:
            return -1
        if not self.trade_time:
            return 1

        return self.trade_time.trading_time_in_session(tick_time).value

    def update_bar_minute_window(self, bar: BarData, new_minute=True) -> None:
        """"""
        if self.window_bar is None:
            self.window_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=bar.datetime,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                volume=0,
                turnover=0,
            )
            if bar.volume > 0:
                self.pending_trade_in_current_windows_bar = False

        # If not inited, create window bar object
        if (
            bar.datetime.hour * 60 + bar.datetime.minute
        ) % self.window == 0 and new_minute:
            self.on_window_bar(self.window_bar)
            dt: datetime = bar.datetime.replace(second=0, microsecond=0)
            self.window_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=dt,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                volume=0,
                turnover=0,
            )
            if bar.volume > 0:
                self.pending_trade_in_current_windows_bar = False
        # Otherwise, update high/low price into window bar
        else:
            if self.pending_trade_in_current_windows_bar and bar.volume > 0:
                self.pending_trade_in_current_windows_bar = False
                self.window_bar.open_price = bar.open_price
                self.window_bar.high_price = bar.high_price
                self.window_bar.low_price = bar.low_price
            else:
                self.window_bar.high_price = max(
                    self.window_bar.high_price, bar.high_price
                )
                self.window_bar.low_price = min(
                    self.window_bar.low_price, bar.low_price
                )

        # Update close price/volume/turnover into window bar
        self.window_bar.close_price = bar.close_price
        self.window_bar.volume += bar.volume
        self.window_bar.turnover += bar.turnover
        self.window_bar.open_interest = bar.open_interest

    def update_bar_hour_window(self, bar: BarData) -> None:
        """"""
        warnings.warn(
            "update_bar_hour_window function is not verified yet", RuntimeWarning, 2
        )
        # If not inited, create window bar object
        if not self.hour_bar:
            dt: datetime = bar.datetime.replace(minute=0, second=0, microsecond=0)
            self.hour_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=dt,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                close_price=bar.close_price,
                volume=bar.volume,
                turnover=bar.turnover,
                open_interest=bar.open_interest,
            )
            return

        finished_bar: BarData | None = None

        # If minute is 59, update minute bar into window bar and push
        if bar.datetime.minute == 59:
            self.hour_bar.high_price = max(self.hour_bar.high_price, bar.high_price)
            self.hour_bar.low_price = min(self.hour_bar.low_price, bar.low_price)

            self.hour_bar.close_price = bar.close_price
            self.hour_bar.volume += bar.volume
            self.hour_bar.turnover += bar.turnover
            self.hour_bar.open_interest = bar.open_interest

            finished_bar = self.hour_bar
            self.hour_bar = None

        # If minute bar of new hour, then push existing window bar
        elif bar.datetime.hour != self.hour_bar.datetime.hour:
            finished_bar = self.hour_bar

            dt: datetime = bar.datetime.replace(minute=0, second=0, microsecond=0)
            self.hour_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=dt,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
                close_price=bar.close_price,
                volume=bar.volume,
                turnover=bar.turnover,
                open_interest=bar.open_interest,
            )
        # Otherwise only update minute bar
        else:
            self.hour_bar.high_price = max(self.hour_bar.high_price, bar.high_price)
            self.hour_bar.low_price = min(self.hour_bar.low_price, bar.low_price)

            self.hour_bar.close_price = bar.close_price
            self.hour_bar.volume += bar.volume
            self.hour_bar.turnover += bar.turnover
            self.hour_bar.open_interest = bar.open_interest

        # Push finished window bar
        if finished_bar:
            self.on_hour_bar(finished_bar)

    def on_hour_bar(self, bar: BarData) -> None:
        """"""
        warnings.warn("on_hour_bar function is not verified yet", RuntimeWarning, 2)
        if self.window == 1:
            self.on_window_bar(bar)
        else:
            if not self.window_bar:
                self.window_bar = BarData(
                    symbol=bar.symbol,
                    exchange=bar.exchange,
                    datetime=bar.datetime,
                    gateway_name=bar.gateway_name,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price,
                )
            else:
                self.window_bar.high_price = max(
                    self.window_bar.high_price, bar.high_price
                )
                self.window_bar.low_price = min(
                    self.window_bar.low_price, bar.low_price
                )

            self.window_bar.close_price = bar.close_price
            self.window_bar.volume += bar.volume
            self.window_bar.turnover += bar.turnover
            self.window_bar.open_interest = bar.open_interest

            self.interval_count += 1
            if not self.interval_count % self.window:
                self.interval_count = 0
                self.on_window_bar(self.window_bar)
                self.window_bar = None

    def update_bar_daily_window(self, bar: BarData) -> None:
        """"""
        warnings.warn(
            "update_bar_daily_window function is not verified yet", RuntimeWarning, 2
        )
        # If not inited, create daily bar object
        if not self.daily_bar:
            self.daily_bar = BarData(
                symbol=bar.symbol,
                exchange=bar.exchange,
                datetime=bar.datetime,
                gateway_name=bar.gateway_name,
                open_price=bar.open_price,
                high_price=bar.high_price,
                low_price=bar.low_price,
            )
        # Otherwise, update high/low price into daily bar
        else:
            self.daily_bar.high_price = max(self.daily_bar.high_price, bar.high_price)
            self.daily_bar.low_price = min(self.daily_bar.low_price, bar.low_price)

        # Update close price/volume/turnover into daily bar
        self.daily_bar.close_price = bar.close_price
        self.daily_bar.volume += bar.volume
        self.daily_bar.turnover += bar.turnover
        self.daily_bar.open_interest = bar.open_interest

        # Check if daily bar completed
        if bar.datetime.time() == self.daily_end:
            self.daily_bar.datetime = bar.datetime.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            self.on_window_bar(self.daily_bar)

            self.daily_bar = None

    def generate(self) -> BarData | None:
        """
        Generate the bar data and call callback immediately.
        """
        bar: BarData | None = self.bar

        if self.bar:
            bar.datetime = bar.datetime.replace(second=0, microsecond=0)
            self.on_bar(bar)

        self.bar = None
        return bar


class ArrayManager:
    """
    For:
    1. time series container of bar data
    2. calculating technical indicator value
    """

    def __init__(self, size: int = 100) -> None:
        """Constructor"""
        self.count: int = 0
        self.size: int = size
        self.inited: bool = False

        self.dt_array: np.ndarray = np.zeros(size, dtype="<M8[us]")
        self.open_array: np.ndarray = np.zeros(size)
        self.high_array: np.ndarray = np.zeros(size)
        self.low_array: np.ndarray = np.zeros(size)
        self.close_array: np.ndarray = np.zeros(size)
        self.volume_array: np.ndarray = np.zeros(size)
        self.turnover_array: np.ndarray = np.zeros(size)
        self.open_interest_array: np.ndarray = np.zeros(size)

    def update_bar(self, bar: BarData) -> None:
        """
        Update new bar data into array manager.
        """
        if not bar or not bar.datetime:
            return
        self.count += 1
        if not self.inited and self.count >= self.size:
            self.inited = True

        bar_dt = np.datetime64(bar.datetime.replace(tzinfo=None))
        if bar_dt != self.dt_array[-1]:
            self.dt_array[:-1] = self.dt_array[1:]
            self.open_array[:-1] = self.open_array[1:]
            self.high_array[:-1] = self.high_array[1:]
            self.low_array[:-1] = self.low_array[1:]
            self.close_array[:-1] = self.close_array[1:]
            self.volume_array[:-1] = self.volume_array[1:]
            self.turnover_array[:-1] = self.turnover_array[1:]
            self.open_interest_array[:-1] = self.open_interest_array[1:]

        self.dt_array[-1] = bar_dt
        self.open_array[-1] = bar.open_price
        self.high_array[-1] = bar.high_price
        self.low_array[-1] = bar.low_price
        self.close_array[-1] = bar.close_price
        self.volume_array[-1] = bar.volume
        self.turnover_array[-1] = bar.turnover
        self.open_interest_array[-1] = bar.open_interest

    @property
    def open(self) -> np.ndarray:
        """
        Get open price time series.
        """
        return self.open_array

    @property
    def high(self) -> np.ndarray:
        """
        Get high price time series.
        """
        return self.high_array

    @property
    def low(self) -> np.ndarray:
        """
        Get low price time series.
        """
        return self.low_array

    @property
    def close(self) -> np.ndarray:
        """
        Get close price time series.
        """
        return self.close_array

    @property
    def volume(self) -> np.ndarray:
        """
        Get trading volume time series.
        """
        return self.volume_array

    @property
    def turnover(self) -> np.ndarray:
        """
        Get trading turnover time series.
        """
        return self.turnover_array

    @property
    def open_interest(self) -> np.ndarray:
        """
        Get trading volume time series.
        """
        return self.open_interest_array

    def sma(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        Simple moving average.
        """
        result_array: np.ndarray = talib.SMA(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def ema(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        Exponential moving average.
        """
        result_array: np.ndarray = talib.EMA(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def kama(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        KAMA.
        """
        result_array: np.ndarray = talib.KAMA(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def wma(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        WMA.
        """
        result_array: np.ndarray = talib.WMA(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def apo(
        self, fast_period: int, slow_period: int, matype: int = 0, array: bool = False
    ) -> float | np.ndarray:
        """
        APO.
        """
        result_array: np.ndarray = talib.APO(
            self.close, fast_period, slow_period, talib.MA_Type(matype)
        )
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def cmo(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        CMO.
        """
        result_array: np.ndarray = talib.CMO(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def mom(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        MOM.
        """
        result_array: np.ndarray = talib.MOM(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def ppo(
        self, fast_period: int, slow_period: int, matype: int = 0, array: bool = False
    ) -> float | np.ndarray:
        """
        PPO.
        """
        result_array: np.ndarray = talib.PPO(
            self.close, fast_period, slow_period, talib.MA_Type(matype)
        )
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def roc(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        ROC.
        """
        result_array: np.ndarray = talib.ROC(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def rocr(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        ROCR.
        """
        result_array: np.ndarray = talib.ROCR(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def rocp(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        ROCP.
        """
        result_array: np.ndarray = talib.ROCP(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def rocr_100(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        ROCR100.
        """
        result_array: np.ndarray = talib.ROCR100(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def trix(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        TRIX.
        """
        result_array: np.ndarray = talib.TRIX(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def std(self, n: int, nbdev: int = 1, array: bool = False) -> float | np.ndarray:
        """
        Standard deviation.
        """
        result_array: np.ndarray = talib.STDDEV(self.close, n, nbdev)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def obv(self, array: bool = False) -> float | np.ndarray:
        """
        OBV.
        """
        result_array: np.ndarray = talib.OBV(self.close, self.volume)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def cci(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        Commodity Channel Index (CCI).
        """
        result_array: np.ndarray = talib.CCI(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def atr(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        Average True Range (ATR).
        """
        result_array: np.ndarray = talib.ATR(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def natr(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        NATR.
        """
        result_array: np.ndarray = talib.NATR(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def rsi(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        Relative Strenght Index (RSI).
        """
        result_array: np.ndarray = talib.RSI(self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def macd(
        self,
        fast_period: int,
        slow_period: int,
        signal_period: int,
        array: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray] | tuple[float, float, float]:
        """
        MACD.
        """
        macd, signal, hist = talib.MACD(
            self.close, fast_period, slow_period, signal_period
        )
        if array:
            return macd, signal, hist
        return macd[-1], signal[-1], hist[-1]

    def adx(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        ADX.
        """
        result_array: np.ndarray = talib.ADX(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def adxr(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        ADXR.
        """
        result_array: np.ndarray = talib.ADXR(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def dx(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        DX.
        """
        result_array: np.ndarray = talib.DX(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def minus_di(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        MINUS_DI.
        """
        result_array: np.ndarray = talib.MINUS_DI(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def plus_di(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        PLUS_DI.
        """
        result_array: np.ndarray = talib.PLUS_DI(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def willr(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        WILLR.
        """
        result_array: np.ndarray = talib.WILLR(self.high, self.low, self.close, n)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def ultosc(
        self,
        time_period1: int = 7,
        time_period2: int = 14,
        time_period3: int = 28,
        array: bool = False,
    ) -> float | np.ndarray:
        """
        Ultimate Oscillator.
        """
        result_array: np.ndarray = talib.ULTOSC(
            self.high, self.low, self.close, time_period1, time_period2, time_period3
        )
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def trange(self, array: bool = False) -> float | np.ndarray:
        """
        TRANGE.
        """
        result_array: np.ndarray = talib.TRANGE(self.high, self.low, self.close)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def boll(
        self, n: int, dev: float, array: bool = False
    ) -> tuple[np.ndarray, np.ndarray] | tuple[float, float]:
        """
        Bollinger Channel.
        """
        mid_array: np.ndarray = talib.SMA(self.close, n)
        std_array: np.ndarray = talib.STDDEV(self.close, n, 1)

        if array:
            up_array: np.ndarray = mid_array + std_array * dev
            down_array: np.ndarray = mid_array - std_array * dev
            return up_array, down_array
        else:
            mid: float = mid_array[-1]
            std: float = std_array[-1]
            up: float = mid + std * dev
            down: float = mid - std * dev
            return up, down

    def keltner(
        self, n: int, dev: float, array: bool = False
    ) -> tuple[np.ndarray, np.ndarray] | tuple[float, float]:
        """
        Keltner Channel.
        """
        mid_array: np.ndarray = talib.SMA(self.close, n)
        atr_array: np.ndarray = talib.ATR(self.high, self.low, self.close, n)

        if array:
            up_array: np.ndarray = mid_array + atr_array * dev
            down_array: np.ndarray = mid_array - atr_array * dev
            return up_array, down_array
        else:
            mid: float = mid_array[-1]
            atr: float = atr_array[-1]
            up: float = mid + atr * dev
            down: float = mid - atr * dev
            return up, down

    def donchian(
        self, n: int, array: bool = False
    ) -> tuple[np.ndarray, np.ndarray] | tuple[float, float]:
        """
        Donchian Channel.
        """
        up: np.ndarray = talib.MAX(self.high, n)
        down: np.ndarray = talib.MIN(self.low, n)

        if array:
            return up, down
        return up[-1], down[-1]

    def aroon(
        self, n: int, array: bool = False
    ) -> tuple[np.ndarray, np.ndarray] | tuple[float, float]:
        """
        Aroon indicator.
        """
        aroon_down, aroon_up = talib.AROON(self.high, self.low, n)

        if array:
            return aroon_up, aroon_down
        return aroon_up[-1], aroon_down[-1]

    def aroonosc(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        Aroon Oscillator.
        """
        result_array: np.ndarray = talib.AROONOSC(self.high, self.low, n)

        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def minus_dm(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        MINUS_DM.
        """
        result_array: np.ndarray = talib.MINUS_DM(self.high, self.low, n)

        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def plus_dm(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        PLUS_DM.
        """
        result_array: np.ndarray = talib.PLUS_DM(self.high, self.low, n)

        if array:
            return result_array

        result_value = result_array[-1]
        return result_value

    def mfi(self, n: int, array: bool = False) -> float | np.ndarray:
        """
        Money Flow Index.
        """
        result_array: np.ndarray = talib.MFI(
            self.high, self.low, self.close, self.volume, n
        )
        if array:
            return result_array

        result_value = result_array[-1]
        return result_value

    def ad(self, array: bool = False) -> float | np.ndarray:
        """
        AD.
        """
        result_array: np.ndarray = talib.AD(
            self.high, self.low, self.close, self.volume
        )
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def adosc(
        self, fast_period: int, slow_period: int, array: bool = False
    ) -> float | np.ndarray:
        """
        ADOSC.
        """
        result_array: np.ndarray = talib.ADOSC(
            self.high, self.low, self.close, self.volume, fast_period, slow_period
        )
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def bop(self, array: bool = False) -> float | np.ndarray:
        """
        BOP.
        """
        result_array: np.ndarray = talib.BOP(self.open, self.high, self.low, self.close)

        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value

    def stoch(
        self,
        fastk_period: int,
        slowk_period: int,
        slowk_matype: int,
        slowd_period: int,
        slowd_matype: int,
        array: bool = False,
    ) -> tuple[float, float] | tuple[np.ndarray, np.ndarray]:
        """
        Stochastic Indicator
        """
        k, d = talib.STOCH(
            self.high,
            self.low,
            self.close,
            fastk_period,
            slowk_period,
            talib.MA_Type(slowk_matype),
            slowd_period,
            talib.MA_Type(slowd_matype),
        )
        if array:
            return k, d
        return k[-1], d[-1]

    def sar(
        self, acceleration: float, maximum: float, array: bool = False
    ) -> float | np.ndarray:
        """
        SAR.
        """
        result_array: np.ndarray = talib.SAR(self.high, self.low, acceleration, maximum)
        if array:
            return result_array

        result_value: float = result_array[-1]
        return result_value


def virtual(func: Callable) -> Callable:
    """
    mark a function as "virtual", which means that this function can be overridden.
    any base class should use this or @abstractmethod to decorate all functions
    that can be (re)implemented by subclasses.
    """
    return func


file_handlers: dict[str, logging.FileHandler] = {}


def _get_file_logger_handler(filename: str) -> logging.FileHandler:
    handler: logging.FileHandler = file_handlers.get(filename, None)
    if handler is None:
        handler = logging.FileHandler(filename)
        file_handlers[filename] = handler  # Am I need a lock?
    return handler


def get_file_logger(filename: str, logformat_str: str = None) -> logging.Logger:
    """
    return a logger that writes records into a file.
    """
    logger: logging.Logger = logging.getLogger(filename)
    handler: logging.FileHandler = _get_file_logger_handler(
        filename
    )  # get singleton handler.
    if logformat_str:
        log_formatter = logging.Formatter(logformat_str)
        handler.setFormatter(log_formatter)
    logger.addHandler(handler)  # each handler will be added only once.
    return logger


def get_local_version(module: ModuleType) -> str:
    return getattr(module, "__version__", "unknown")


def get_remote_commit_hash(remote_url, tag="HEAD", short=False) -> str:
    try:
        result = subprocess.run(
            ["git", "ls-remote", remote_url, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = result.stdout.strip().split("\t")[0]
        if short:
            return commit_hash[:7]
        return commit_hash
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get remote commit hash: {e.stderr}") from e


def get_latest_tag_from_remote(remote_url) -> tuple[str, str]:
    result = subprocess.run(
        ["git", "ls-remote", "--tags", remote_url],
        capture_output=True,
        text=True,
        check=True,
    )
    tags = result.stdout.strip().split("\n")
    if tags:
        latest_tag = tags[-1].split("/")[-1].rstrip("^{}")
        if latest_tag.startswith("v"):
            latest_tag = latest_tag[1:]
        return latest_tag, tags[-1].split("\t", 1)[0]
    return "", ""


def get_remote_version(remote_url, tag="HEAD", major=False) -> str:
    latest_tag, tag_commit_hash = get_latest_tag_from_remote(remote_url)
    if not bool(latest_tag):
        return "0.0.0"
    if major:
        return latest_tag
    try:
        commit_hash = get_remote_commit_hash(remote_url, tag)
    except RuntimeError:
        commit_hash = "unknown"
    if commit_hash == "":
        commit_hash = "unknown"
    if commit_hash == tag_commit_hash:
        return latest_tag
    match = re.match(r"(.*?)(\d+)$", latest_tag)
    prefix, tail = match.groups()
    return f"{prefix}{int(tail) + 1}+git.{commit_hash[:7]}"
