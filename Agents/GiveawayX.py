#Copyright Mihai Nemes (2013)

from Lib.Order import Order
from Lib.Trader import Trader

class Trader_GiveawayX(Trader):

        def getorder(self, time, countdown, lob):
            quoteprice = None
            if len(self.orders) < 1:
                order = None
            else:
                limitprice = self.orders[0].price
                otype = self.orders[0].otype
                if otype == 'Bid':
                    if lob['asks']['n'] > 0: 
                        if limitprice > lob['asks']['best']:
                            quoteprice = limitprice
                            self.lastquote = quoteprice
                            order = Order(self.tid, otype, quoteprice, self.orders[0].qty, time)
                            return order
                                
                else:
                        if lob['bids']['n'] > 0:				
                            if limitprice < lob['bids']['best']:
                                quoteprice = limitprice
                                self.lastquote = quoteprice
                                order = Order(self.tid, otype, quoteprice, self.orders[0].qty, time)
                                return order
                return None
