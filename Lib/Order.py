#---class that constitutes an order placed by the agent
class Order:
        def __init__(self, tid, otype, price, qty, time):
                self.tid = tid
                self.otype = otype
                self.price = price
                self.qty = qty
                self.time = time

        def __str__(self):
                return '[%s %s P=%03d Q=%s T=%5.2f]' % (self.tid, self.otype, self.price, self.qty, self.time)