#!/usr/bin/env python3
import robin_stocks as r 
import threading
from time import sleep
from getpass import getpass
from math import floor
import signal
from datetime import datetime  
from datetime import timedelta 

shutdown = False
holdings = {}
cash_limit = 125.0
cash_avalible = cash_limit
profit = 0.0
trade_stock = ['MAXR',] 
my_stock = []
lock = threading.Semaphore(1)
class stock:
    def __init__(self,name):
        global holdings
        self.name = name
        self.qunt = float(holdings[self.name]['quantity'])
        self.buy_price = float(holdings[self.name]['average_buy_price'])
        
        self.willing_percent = .05
        self.willing_to_sell = False
        self.sold = False
        self.order_id = None
        self.dec_timer = None
        threading.Timer(next_selling_day(),self.sell_avalable).start()
        
        
    def __str__(self):
        return f'{self.name}-held:${self.qunt}  sellable: {self.willing_to_sell} willing price: {self.buy_price*(1+self.willing_percent)}' 

    def update(self):
        global profit
        global cash_avalible
        global holdings
        if self.order_id != None:
            info = r.get_stock_order_info(self.order_id)
        else:
            info = None
        if info != None :
            if info['state'] == 'filled':
                price = float(info['executed_notional']['amount']) 
                with lock:
                    profit += price - self.buy_price*self.qunt 
                    cash_avalible += self.buy_price*self.qunt
                    holdings = r.build_holdings()
                    self.sold = True
                    self.dec_timer.cancel()
                    print(f'current profit {profit}')
                    print(f'Sold {self.qunt} of {self.name}')
    def dec_profit(self):
        
        if ( self.willing_percent -.01 >= 0):
            r.cancel_stock_order(self.order_id)
            self.willing_percent -= .01
            order = r.order_sell_limit(self.name,self.qunt,self.buy_price*(1.0+self.willing_percent))
            self.order_id = order['id']
            print(f'unable to sell droping price of {self.name}')
            self.dec_timer = threading.Timer(next_selling_day(),self.dec_profit)
            self.dec_timer.start()

    def sell_avalable(self):
        
        self.willing_to_sell = True
        order = r.order_sell_limit(self.name,self.qunt,self.buy_price*(1.0+self.willing_percent))
        self.order_id = order['id']
        self.dec_timer = threading.Timer(next_selling_day(),self.dec_profit)
        self.dec_timer.start()
        
    
def buy(name,amount):
    global holdings

    price = get_stock_price(name)
    qnt = floor(amount/price)
    if(qnt < 1):
        print(f'unable to buy {name}')
        return
    order = r.order_buy_market(name,qnt,timeInForce='gtc')
    print(order)
    id_num = order['id']
    
    
    info = r.get_stock_order_info(id_num)

    while info['state'] != 'filled':
        print(f'{name} not yet bought')
        sleep(60)
        info = r.get_stock_order_info(id_num)
    with lock:
        holdings = r.build_holdings()
        my_stock.append(stock(name))
def shutdown_sig(sig, frame):
    global shutdown 
    shutdown = True
def user_login():
    username = input('Please enter your username: ')
    password = getpass('Please enter your password: ')
    try:
        login = r.login(username = username,
                        password = password,
                        expiresIn=timedelta(days=3).seconds,
                        store_session=False)

        print(login)
    except Exception:
        print('Invalid login cradintals please try again!')
        user_login()
def get_stock_price(stock_name):
    price = float(r.get_latest_price(stock_name)[0]) 
    #print(f'{stock_name}-${price:.2f}')
    return price

def get_stock_history(stock_name):
    price = r.get_historicals(stock_name)
    return price

def next_selling_day():
    now = datetime.now()
    days = 1 if datetime.isoweekday(now) != 5 else 3 
    time_sleep = ((now+timedelta(days)).replace(hour = 9,minute=30,second=0)-now).seconds
    return time_sleep

if __name__ == '__main__':

    user_login()
    signal.signal(signal.SIGINT,shutdown_sig)
    stock_list = []
    holdings = r.build_holdings()
    hold = [float(x['amount']) for x in r.get_bank_transfers() if x['direction'] == 'deposit']
    
    
    print(datetime.now())
    print(datetime.isoweekday(datetime.now()))
    
    start = datetime.strptime('9:30AM','%I:%M%p').time() 
    end   = datetime.strptime('4:30PM','%I:%M%p').time()
    print(((datetime.now()+timedelta(1)).replace(hour = 9,minute=30,second=0)-datetime.now()).seconds)
   
    #print(now < end and now > start)
    
    thread = threading.Thread(target=buy,args=('MAXR',cash_avalible))
    threading.Thread()
    thread.start()
    #stock_list.append(stock('MAXR'))
    while not shutdown:
        now   = datetime.time(datetime.now())
        if(now < end and now > start):
            with lock:
                for s in stock_list:
                    s.update()
                    if s.sold:
                        stock_list.remove(s)
                        thread = threading.Thread(target=buy,args=('MAXR',cash_avalible))
                        threading.Thread()
                        thread.start()
                    print(s)
            sleep(60)
        else:
           sleep(next_selling_day())
        