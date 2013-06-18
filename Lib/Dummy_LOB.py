#---class that is a pretend and simplified version of the limit order book held by the server
#---stored on the client side and is used by the automated agent when adjusting its parameters
#according to market evolution
#---it does not compute anything it is created according to the data received by the server 
class DUMMY_LOB:
    def __init__(self):
        self.bids = []
        self.asks = []        

    #publishes the data in the exact format as on the server side
    def publish_lob(self,time):
        public_data = {}
        public_data['time'] = time
        public_data['bids'] = {'best':self.bid_best_price(),
                                     'worst':self.bid_worst_price(),
                                     'n': len(self.bids),
                                     'lob':self.bids}
        public_data['asks'] = {'best':self.ask_best_price(),
                                     'worst':self.ask_worst_price(),
                                     'n': len(self.asks),
                                     'lob':self.asks}
        return public_data
    
    #gets the best bid price
    def bid_best_price(self):
        max = 0        
        if len(self.bids) > 0:
            ii = 0
            max = self.bids[0][0]
            while ii < len(self.bids):
                if self.bids[ii][0] > max:
                    max = self.bids[ii][0]
                ii += 1
        else:
             return None
        return max
    #gets the worst bid price
    def bid_worst_price(self):
        min = 0        
        if len(self.bids) > 0:
            ii = 0
            min = self.bids[0][0]
            while ii < len(self.bids):
                if self.bids[ii][0] < min:
                    min = self.bids[ii][0]
                ii += 1
        return min
    #gets the as best price
    def ask_best_price(self):
        min = 1000        
        if len(self.asks) > 0:
            ii = 0
            min = self.asks[0][0]
            while ii < len(self.asks):
                if self.asks[ii][0] < min:
                    min = self.asks[ii][0]
                ii += 1
        else:
            return None
        return min
    #gets the ask worst price
    def ask_worst_price(self):
        min = 1000        
        if len(self.asks) > 0:
            ii = 0
            min = self.asks[0][0]
            while ii < len(self.asks):
                if self.asks[ii][0] > min:
                    min = self.asks[ii][0]
                ii += 1
        return min
            
  