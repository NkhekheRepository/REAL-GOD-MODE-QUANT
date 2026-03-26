from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)


class MaCrossoverStrategy(CtaTemplate):
    """"""

    author = "Quant Developer"

    # Parameters
    fast_ma_length = 10
    slow_ma_length = 30
    fixed_size = 1

    # Variables
    fast_ma_value = 0
    slow_ma_value = 0
    ma_trend = 0

    parameters = ["fast_ma_length", "slow_ma_length", "fixed_size"]
    variables = ["fast_ma_value", "slow_ma_value", "ma_trend"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("Strategy initialized")
        self.load_bar(10)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("Strategy started")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("Strategy stopped")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData):
        """
        Callback of new bar data update.
        """
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        # Calculate moving averages
        self.fast_ma_value = am.sma(self.fast_ma_length, array=True)[-1]
        self.slow_ma_value = am.sma(self.slow_ma_length, array=True)[-1]

        # Determine trend
        if self.fast_ma_value > self.slow_ma_value:
            ma_trend = 1
        elif self.fast_ma_value < self.slow_ma_value:
            ma_trend = -1
        else:
            ma_trend = 0

        # Check for trend change
        if ma_trend > self.ma_trend:
            # Bullish crossover
            self.buy(bar.close_price + 5, self.fixed_size)
        elif ma_trend < self.ma_trend:
            # Bearish crossover
            self.short(bar.close_price - 5, self.fixed_size)

        self.ma_trend = ma_trend
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder):
        """
        Callback of stop order update.
        """
        pass