#support class for traders with methods that can be overriden in order to suit the requirements
#of a specific trader 
class Trader:

        def __init__(self, ttype, tid, balance,bid,sleepMode,sleepTime):
                self.ttype = ttype
                self.bidType = bid
                self.tid = tid
                self.balance = balance
                self.blotter = []
                self.orders = []
                self.willing = 1
                self.able = 1
                self.lastquote = None
                self.humanInput = None
                #=====================================================
                self.sleepMode = sleepMode
                self.sleepTime = sleepTime
                self.currentSleep = self.sleepTime
                self.maxProfit = 0.0
                self.allocEff = 0.0



        def __str__(self):
                return '[TID %s type %s balance %s blotter %s orders %s]' % (self.tid, self.ttype, self.balance, self.blotter, self.orders)

        def updateSleep(self):
                if self.sleepMode == True:
                        if self.currentSleep == 0:
                                self.currentSleep = self.sleepTime
                                return True
                        else:
                                self.currentSleep -= 1
                                return False
                return True

        def add_order(self, order):
                # in this version, trader has at most one order,
                # if allow more than one, this needs to be self.orders.append(order)
                self.orders = [order]
                self.humanInput = None


        def del_order(self, order):
                # this is lazy: assumes each trader has only one order with quantity=1, so deleting sole order
                # CHANGE TO DELETE THE HEAD OF THE LIST AND KEEP THE TAIL
                self.orders = []
                self.humanInput = None


        def bookkeep(self, trade, order, verbose,tLimit):

                outstr = '%s (%s) bookkeeping: orders=' % (self.tid, self.ttype)
                for order in self.orders: outstr = outstr + str(order)

                self.blotter.append(trade)  # add trade record to trader's blotter
                # NB What follows is **LAZY** -- assumes all orders are quantity=1
                transactionprice = trade['price']
                if self.orders[0].otype == 'Bid':
                        profit = self.orders[0].price - transactionprice
                else:
                        profit = transactionprice - self.orders[0].price
                self.balance += profit
                if verbose: print('%s profit=%d balance=%d ' % (outstr, profit, self.balance))
                tProfit = tLimit - self.orders[0].price
                if tProfit < 0: tProfit *= -1
                self.maxProfit += tProfit
                self.allocEff = self.balance / self.maxProfit
                self.del_order(order)  # delete the order


        # specify how trader responds to events in the market
        # this is a null action, expect it to be overloaded with clever things by specific algos
        def respond(self, time, lob, trade, verbose):
                return None