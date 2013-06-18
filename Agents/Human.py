from Lib.Order import Order
from Lib.Trader import Trader
#---a form of trader that is supposed to impersonate the human trader located on 
#the client side. It will be stored on the server. However it does not mean that
#the agent will indeed be human, there is no knowledge about what type of agent 
#performs transactions on the client side.- HUMAN or AUTOMATED
class Trader_Human(Trader):
    def getorder(self,time,countdown,lob):
        if len(self.orders) < 1:
                        order = None
        else:                        
            if self.humanInput != None:
                        order = Order(self.tid,
                                    self.orders[0].otype,#bid type
                                    self.humanInput,#human sends a price to the server which updates this variable
                                    self.orders[0].qty,#quantity
                                    time)#time the order has been placed                        
            else:
                order = None
        return order