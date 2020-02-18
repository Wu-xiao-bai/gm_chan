# coding: utf-8
import json
import os
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.options import define, options, parse_command_line
from tornado.web import RequestHandler, Application
from tornado.web import StaticFileHandler
from datetime import datetime, timedelta
from chan import KlineAnalyze
from gm.api import *

# 在这里设置你的掘金 token，要在本地启动掘金终端，才能正常获取数据
set_token("set your gm token")


def get_gm_kline(symbol, end_date, freq='D', k_count=3000):
    """从掘金获取历史K线数据"""
    if "-" not in end_date and isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y%m%d")
    freq_convert = {"60s": "1min", "300s": "5min", "1800s": "30min", "1d": "D"}
    freq_convert = {v: k for k, v in freq_convert.items()}
    if freq[-1] in ['n', 'D']:
        freq = freq_convert[freq]
        if freq.endswith('min'):
            end_date += timedelta(days=1)
    df = history_n(symbol=symbol, frequency=freq, end_time=end_date,
                   fields='symbol,eob,open,close,high,low,volume',
                   count=k_count, df=True)
    df['dt'] = df['eob']
    df['vol'] = df['volume']
    df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]
    df.sort_values('dt', inplace=True, ascending=True)
    df['dt'] = df.dt.apply(lambda x: x.strftime(r"%Y-%m-%d %H:%M:%S"))
    df.reset_index(drop=True, inplace=True)

    for col in ['open', 'close', 'high', 'low']:
        df[col] = df[col].apply(round, args=(2,))
    return df


# 端口固定为 8005，不可以调整
define('port', type=int, default=8005, help='服务器端口')
current_path = os.path.dirname(__file__)


class BaseHandler(RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")  # 这个地方可以写域名
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def post(self):
        self.write('some post')

    def get(self):
        self.write('some get')

    def options(self):
        self.set_status(204)
        self.finish()


class BasicHandler(BaseHandler):
    """股票基本信息"""
    def get(self):
        ts_code = self.get_argument('ts_code')
        results = {"msg": "success", "basic": None}
        self.write(json.dumps(results, ensure_ascii=False))


class KlineHandler(BaseHandler):
    """K 线"""
    def get(self):
        ts_code = self.get_argument('ts_code')
        freq = self.get_argument('freq')
        trade_date = self.get_argument('trade_date')
        if trade_date == 'null':
            trade_date = datetime.now().date().__str__().replace("-", "")
        kline = get_gm_kline(symbol=ts_code, end_date=trade_date, freq=freq, k_count=3000)
        ka = KlineAnalyze(kline)
        kline = ka.chan_result
        kline = kline.fillna("")
        columns = ["dt", "open", "close", "low", "high", "vol", 'fx_mark', 'fx', 'bi', 'xd']

        self.finish({'kdata': kline[columns].values.tolist()})


if __name__ == '__main__':
    parse_command_line()
    app = Application([
            ('/kline', KlineHandler),
            ('/basic', BasicHandler),
            (r'^/(.*?)$', StaticFileHandler, {"path": os.path.join(current_path, "web"),
                                              "default_filename": "index.html"}),
        ],
        static_path=os.path.join(current_path, "web"),
        dubug=True
    )
    http_server = HTTPServer(app)
    http_server.listen(options.port)
    IOLoop.current().start()



