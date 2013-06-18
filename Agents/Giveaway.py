from Lib.Order import Order
from Lib.Trader import Trader

class Trader_Giveaway(Trader):

        
        def getorder(self, time, countdown, lob):
                
                if len(self.orders) < 1:
                        order = None
                else:
                    #the quoteprice is assigned the limit price and then is 
                    # placed in the market
                        quoteprice = self.orders[0].price  
                        self.lastquote = quoteprice
                        order = Order(self.tid,
                                    self.orders[0].otype,
                                    quoteprice,
                                    self.orders[0].qty,
                                    time)
                return order