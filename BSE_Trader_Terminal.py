# -*- coding: utf-8 -*-
#
# BSE: The Bristol Stock Exchange
#
# Version 1.2; November 17th, 2012. 
#
# Copyright (c) 2012, Dave Cliff
#
#
# ------------------------
#
# MIT Open-Source License:
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# ------------------------
#
#
#
# BSE is a very simple simulation of automated execution traders
# operating on a very simple model of a limit order book (LOB) exchange
#
# major simplifications in this version:
#       (a) only one financial instrument being traded
#       (b) traders can only trade contracts of size 1 (will add variable quantities later)
#       (c) each trader can have max of one order per single orderbook.
#       (d) traders can replace/overwrite earlier orders, but cannot cancel
#       (d) simply processes each order in sequence and republishes LOB to all traders
#           => no issues with exchange processing latency/delays or simultaneously issued orders.
#
# NB this code has been written to be readable, not efficient!

from twisted.internet import reactor, protocol, task, tksupport
from Lib.Order import Order
from Lib.Dummy_LOB import DUMMY_LOB
from Tkinter import *

from PIL import ImageTk, Image
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
import tkFont
import pylab as py
import random
import imp
import os
import urllib2
import json

host = "http://bse.eu01.aws.af.cm/"
#host = "http://127.0.0.1:5000/"
# a client protocol
class UI:
    def __init__(self,master):
        
        #aspect ratio
        self.traders = []
        SCREEN_SIZEX = master.winfo_screenwidth() 
        SCREEN_SIZEY = master.winfo_screenheight()
        SCREEN_RATIOX = 0.618
        SCREEN_RATIOY = 0.86
        FrameSizeX  = int(SCREEN_SIZEX * SCREEN_RATIOX)     
        FrameSizeY  = int(SCREEN_SIZEY * SCREEN_RATIOY)
        FramePosX   = (SCREEN_SIZEX - FrameSizeX)/2
        FramePosY   = (SCREEN_SIZEY - FrameSizeY)/2
        master.geometry("%sx%s+%s+%s" % (FrameSizeX,FrameSizeY,FramePosX,FramePosY))
        #master.minsize(FrameSizeX,FrameSizeY)
        #master.maxsize(FrameSizeX,FrameSizeY)
        #-------------------------------------------------------
        #blotter and trader gui lists
        self.blotterLabels = []
        self.blotterVars = []
        self.traderLabels = []
        #-------------------------------------------------------
        self.factory = ClientFactory(self)
        self.root = master
        self.root.bind('<Escape>',self.end)
        master.protocol("WM_DELETE_WINDOW", self.handler)
        self.customFont = tkFont.Font(family="Helvetica", size=20)
        self.headerFont = tkFont.Font(family="Century Schoolbook L",size=20)
        self.headerFont.configure(underline = True)
        
        self.color = 'DarkKhaki'
        self.framecolor = 'LemonChiffon'
        self.buttoncolor = 'Khaki'
        self.customFont = tkFont.Font(family="Helvetica", size=20)
        self.tableFont = tkFont.Font(family="Century Schoolbook L",size=16)
        self.cellsFont = tkFont.Font(family="Century Schoolbook L",size=12)        
          
        self.timerImg = ImageTk.PhotoImage(Image.open('Images/timer.png'))
        self.brisImg = ImageTk.PhotoImage(Image.open('Images/bristol.png'))
        self.connectedImg = ImageTk.PhotoImage(Image.open('Images/connected.png'))
        self.notconnImg = ImageTk.PhotoImage(Image.open('Images/notconnected.png'))
        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
    
        self.cnv = Canvas(self.root)
        self.cnv.grid(row=0, column=0, sticky='nswe')
        self.vScroll = Scrollbar(self.root, orient=VERTICAL, command=self.cnv.yview)
        self.vScroll.pack(fill=Y,side=RIGHT)
        self.hScroll = Scrollbar(self.root, orient=HORIZONTAL, command=self.cnv.xview)
        self.hScroll.pack(fill=X,side=BOTTOM)
        self.cnv.configure(yscrollcommand=self.vScroll.set,xscrollcommand = self.hScroll.set)
        self.mainFrame = Frame(self.cnv,bd=3, relief=RIDGE,bg=self.color)
        self.mainFrame.pack(side=TOP,padx=5,pady=5,fill=X)
        self.cnv.create_window(0, 0, window=self.mainFrame,anchor="nw")         
        
        #place widgets
        self.placeTitle()
        self.mainContainer = Frame(self.mainFrame,bg=self.color)
        self.mainContainer.grid(column=0,row=2,sticky="ew")       
        self.menuContainer = Frame(self.mainContainer,bg=self.color)
        self.menuContainer.pack(side=TOP,padx=5,pady=5)
        self.sessionContainer = Frame(self.mainContainer,bg=self.color)
        self.sessionContainer.pack(side=TOP,padx=5,pady=5,fill=X)
        self.placeMenu()
        self.placeSession()
        self.placeBlotter()
        #end region       
        self.update = task.LoopingCall(self.populateCloudSessions)
        self.update.start(10)
        self.mainFrame.update_idletasks()
        self.cnv.configure(scrollregion=(0, 0, self.mainFrame.winfo_width(), self.mainFrame.winfo_height())) 
    
    def populateCloudSessions(self):
        action="SESSIONS"
        headers = {'Content-Type':'application/json'}
        post_data = {"action":action}
        req = urllib2.Request(host+"client", json.dumps(post_data), headers)
        sessions = json.loads(urllib2.urlopen(req).read())['sessions']
        self.sessCDrop["menu"].delete(0,END)
        if len(sessions) > 0:
            self.sessVar.set(sessions[0])
            for element in sessions:
                self.sessCDrop["menu"].add_command(label=element,command=lambda temp = element: self.sessCDrop.setvar(self.sessCDrop.cget("textvariable"), value = temp))
        else:
            self.sessVar.set("None")
        
   
        
    def handler(self):
        reactor.stop()
        self.root.destroy()
        self.root.quit()
        sys.exit()
         
    def end(self,event):
        reactor.stop()
        self.root.destroy()
        self.root.quit()
        sys.exit()
        
    def placeBlotter(self):
        self.graphContainer = Frame(self.sessionContainer,bg=self.framecolor,bd=3,relief=RIDGE)
        self.graphContainer.grid(column=2,row=0,padx=5,pady=5,sticky='nsew')
        
        self.blotterContainer = Frame(self.mainContainer,bg=self.framecolor,bd=3,relief=RIDGE)
        self.blotterContainer.pack(side=TOP,fill=X,padx=5,pady=5)
        self.blotterFrame = Frame(self.blotterContainer,bg=self.framecolor)
        self.blotterFrame.pack(side=TOP,padx=5,pady=5)
            
        self.blotterTitle = Label(self.blotterFrame,text="BLOTTER",bg=self.framecolor,font=self.headerFont)
        self.blotterTitle.grid(column=0,row=0,columnspan=5,sticky="ew",padx=5,pady=5)
        
        self.party2 = Label(self.blotterFrame,bd=3,text="PARTY2",bg = 'black',fg='white',relief=RIDGE)
        self.party2.grid(column=0,row=1,sticky="ew")
        
        self.priceBlot = Label(self.blotterFrame,bd=3,text="PRICE",bg = 'black',fg='white',relief=RIDGE)
        self.priceBlot.grid(column=1,row=1,sticky="ew")
        
        self.party1 = Label(self.blotterFrame,bd=3,text="PARTY1",bg = 'black',fg='white',relief=RIDGE)
        self.party1.grid(column=2,row=1,sticky="ew")
        
        self.qtyBlot = Label(self.blotterFrame,bd=3,text="QTY",bg = 'black',fg='white',relief=RIDGE)
        self.qtyBlot.grid(column=3,row=1,sticky="ew")
        
        self.timeBlot = Label(self.blotterFrame,bd=3,text="TIME",bg = 'black',fg='white',relief=RIDGE)
        self.timeBlot.grid(column=4,row=1,sticky="ew")
        
        self.graphFrame = Frame(self.menuContainer,bd=3,relief=RIDGE,bg=self.framecolor)
        self.graphFrame.grid(column=2,row=1,padx=5,pady=5,sticky="ew")
        
        self.graphTitle = Label(self.graphFrame,text="PERFORMANCE",font=self.headerFont,bg=self.framecolor)
        self.graphTitle.pack(side=TOP,padx=5)
        
        
        
        self.clearPlotBtn = Button(self.graphFrame,text="Clear",bg=self.buttoncolor,comman=self.clearGraph)
        self.clearPlotBtn.pack(side=TOP,padx=5,pady=5,fill=X)
        #==================================================
        self.plotFigure = py.figure(figsize=(5,4),dpi=50)
        self.mainPlot = self.plotFigure.add_subplot(111)
        test = [1,2,3,2,5]
        test2 = [5,6,7,8,9]
        self.mainPlot.plot(test2,test,label='Deals price/time') 
        self.mainPlot.legend() 
        self.mainPlot.set_title('Market Evolution')
        self.mainPlot.set_ylabel('Transaction price')         
        self.mainPlot.set_xlabel('Time (s)')
        self.plotFigure.canvas.draw()
        self.plotCanvas = FigureCanvasTkAgg(self.plotFigure, self.graphFrame)
        self.plotCanvas.get_tk_widget().pack(side=TOP,fill='both', expand=1)
        
        
        
    
    def clearGraph(self):
        mainPlot.clear() 
        
    def placeSession(self):        
        
        self.timerFrameCont = Frame(self.menuContainer,bg=self.color)
        self.timerFrameCont.grid(column=0,row=1,padx=5,pady=5,sticky="news")
                
        self.timerFrame = Frame(self.timerFrameCont,bd=3,relief=RIDGE,bg=self.framecolor)
        self.timerFrame.pack(side=TOP,pady=5,fill=X)      
       
        
        self.timeLbl = Label(self.timerFrame,image=self.timerImg,bg=self.framecolor)
        self.timeLbl.image = self.timerImg
        self.timeLbl.grid(column=0,row=0,padx=5,pady=5)
        
        self.timeVar = StringVar()
        self.timeVar.set("Idle")
        self.time = Label(self.timerFrame,textvar=self.timeVar,font=self.customFont,bg=self.framecolor)
        self.time.grid(column=1,row=0,padx=5,pady=5,sticky="ns")
        
        self.tradeFrame = Frame(self.timerFrameCont,bd=3,relief=RIDGE,bg=self.framecolor)
        self.tradeFrame.pack(side=TOP,pady=20,fill=X)
        
        self.tradeLbl = Label(self.tradeFrame,text="HUMAN TRADE PANEL",font=self.headerFont,bg=self.framecolor)
        self.tradeLbl.grid(column=0,row=0,columnspan=2)
        
        self.limitH = Label(self.tradeFrame,text="Limit Price",bg=self.framecolor)
        self.limitH.grid(column=0,row=1,padx=5,pady=5,sticky="w")
        
        self.bidH = Label(self.tradeFrame,text="Quoteprice",bg=self.framecolor)
        self.bidH.grid(column=1,row=1,padx=5,pady=5,sticky="w")
        
        self.limitVar = StringVar()
        self.limitVar.set('0.0')
        self.limitLbl = Label(self.tradeFrame,textvar=self.limitVar,bg=self.framecolor)
        self.limitLbl.grid(column=0,row=2,padx=5,pady=3,sticky="w")
        
        self.bidEntry = Entry(self.tradeFrame)
        self.bidEntry.grid(column=1,row=2,padx=5,pady=3,sticky="w")
        self.bidEntry.bind("<Return>",self.bidMessage)
        
        self.orderFrame = Frame(self.menuContainer,bd=3,relief=RIDGE,bg=self.framecolor)
        self.orderFrame.grid(column=1,row=1,padx=5,pady=5,sticky="ew")
        
        self.orderLbl = Label(self.orderFrame,text="ORDERBOOK",font = self.headerFont,bg=self.framecolor)
        self.orderLbl.grid(column=0,row=0,columnspan=4,sticky="ew") 
        
        self.qtyBidH = Label(self.orderFrame,bd=3,relief=RIDGE,text="QTY",fg="white",bg="black")
        self.qtyBidH.grid(column=0,row=1,sticky="ew")
        
        self.BidH = Label(self.orderFrame,bd=3,relief=RIDGE,text="BID",fg="white",bg="black")
        self.BidH.grid(column=1,row=1,sticky="ew")
        
        self.AskH = Label(self.orderFrame,bd=3,relief=RIDGE,text="ASK",fg="white",bg="black")
        self.AskH.grid(column=2,row=1,sticky="ew")
        
        self.qtyAskH = Label(self.orderFrame,bd=3,relief=RIDGE,text="QTY",fg="white",bg="black")
        self.qtyAskH.grid(column=3,row=1,sticky="ew")
        
        
        self.qtyBidVar = []
        self.qtyBidLabels = []
        
        self.BidVar = []
        self.BidLabels = []
        
        self.AskVar = []
        self.AskLabels = []
        
        self.qtyAskVar = []
        self.qtyAskLabels = []
        ii = 0
        while ii < 10:
            self.qtyBidVar.append(StringVar())
            self.qtyBidVar[ii].set('')
            self.qtyBidLabels.append(Label(self.orderFrame,bd=3,relief=RIDGE,
                bg='PaleGreen',textvar=self.qtyBidVar[ii]))
            self.qtyBidLabels[ii].grid(column=0,row=ii+2,sticky="ew")
            self.BidVar.append(StringVar())
            self.BidVar[ii].set('')
            self.BidLabels.append(Label(self.orderFrame,bd=3,relief=RIDGE,
                bg='PaleGreen',textvar=self.BidVar[ii]))
            self.BidLabels[ii].grid(column=1,row=ii+2,sticky="ew")
            self.AskVar.append(StringVar())
            self.AskVar[ii].set('')
            self.AskLabels.append(Label(self.orderFrame,bd=3,relief=RIDGE,
                bg='Salmon',textvar=self.AskVar[ii]))
            self.AskLabels[ii].grid(column=2,row=ii+2,sticky="ew")
            self.qtyAskVar.append(StringVar())
            self.qtyAskVar[ii].set('')
            self.qtyAskLabels.append(Label(self.orderFrame,bd=3,relief=RIDGE,
                bg='Salmon',textvar=self.qtyAskVar[ii]))
            self.qtyAskLabels[ii].grid(column=3,row=ii+2,sticky="ew")
            ii += 1
        
        self.profitFrame = Frame(self.timerFrameCont,bd=3,relief=RIDGE,bg=self.framecolor)
        self.profitFrame.pack(side=TOP,pady=10,fill=X)
        
        self.profitH = Label(self.profitFrame,text="profit:",bg=self.framecolor)
        self.profitH.grid(column=0,row=0,sticky="ew",padx=5,pady=5) 
        
        self.profitVar = StringVar()
        self.profitVar.set('0.0')
        self.profitLbl = Label(self.profitFrame,textvar=self.profitVar,bg=self.framecolor,font=self.customFont)
        self.profitLbl.grid(column=1,row=0,padx=5,pady=5,sticky="ew")     
        
    def bidMessage(self,event): 
        if len(str(self.bidEntry.get())) > 0:
            try:
                if self.sideVar.get() == 'Closed':
                    action = 'bid'               
                    message =  {'action':action,'bid':str(self.bidEntry.get())}
                    self.bidEntry.delete(0, END)
                    self.factory.client.transport.write(json.dumps(message))
                elif self.sideVar.get() == 'Cloud':                    
                    bid = float(self.bidEntry.get())
                    self.bidEntry.delete(0, END)
                    action="SHOUT"
                    headers = {'Content-Type':'application/json'}
                    post_data = {"action":action,"bid":bid,"traderID":self.factory.traderID,"sessionID":self.factory.sessionID}
                    req = urllib2.Request(host+"client", json.dumps(post_data), headers)
                    response = json.loads(urllib2.urlopen(req).read())                    
            except Exception as ex:
                print ex
        
    def placeMenu(self):
        self.menuFrame = Frame(self.menuContainer,bd=3,relief=RIDGE,bg=self.framecolor)
        self.menuFrame.grid(column=0,row=0,padx=5,pady=5,sticky="news")
        
        self.traderFrameCont = Frame(self.menuContainer,bd=3,relief=RIDGE,bg=self.factory.ui.framecolor)
        self.traderFrameCont.grid(column=1,row=0,padx=5,pady=5,columnspan=2,sticky="news")
        
        self.tradersContainer = Frame(self.traderFrameCont,bg=self.factory.ui.framecolor)
        self.tradersContainer.pack(side=TOP)
        self.traderFrame = Frame(self.tradersContainer)
        self.traderFrame.grid(column=1,row=0,padx=5,pady=5,sticky="nsew")
        
        self.tradeLbl = Label(self.traderFrame,text="Traders",anchor="center",font=self.headerFont,bg=self.framecolor)
        self.tradeLbl.grid(column=0,row=0,columnspan=4,sticky="ew")
        self.tradeH = Label(self.traderFrame,text="Name",bd=3,bg=self.buttoncolor,relief=RIDGE)
        self.tradeH.grid(column=0,row=1,sticky="ew")
        self.ipH = Label(self.traderFrame,text="Ip",bd=3,bg=self.buttoncolor,relief=RIDGE)
        self.ipH.grid(column=1,row=1,sticky="ew")
        self.typeH = Label(self.traderFrame,text="Type",bd=3,bg=self.buttoncolor,relief=RIDGE)
        self.typeH.grid(column=2,row=1,sticky="ew")
        self.agentH = Label(self.traderFrame,text="Agent",bd=3,bg=self.buttoncolor,relief=RIDGE)
        self.agentH.grid(column=3,row=1,sticky="ew")
        
        self.closeFrame = Frame(self.menuFrame,bd=3,relief=RIDGE,bg=self.framecolor)
        self.closeFrame.grid(row=0,column=0,sticky="nsew")
        
        self.closeLbl = Label(self.closeFrame,text="Closed Network",bd=2,relief=RIDGE,bg=self.framecolor)
        self.closeLbl.grid(column=0,columnspan=2,row=0,sticky="ew")
        
        self.nameLbl = Label(self.closeFrame,text="Name:",bd=2,relief=RIDGE,bg=self.framecolor)
        self.nameLbl.grid(column=0,row=1,sticky="ew")
        
        self.nameEntry = Entry(self.closeFrame,bd=2,relief=RIDGE)
        self.nameEntry.grid(column=1,row=1,sticky="ew")
        
        self.ipLbl = Label(self.closeFrame,text="IP:",bd=2,relief=RIDGE,bg=self.framecolor)
        self.ipLbl.grid(column=0,row=2,sticky="ew")
        
        self.ipEntry = Entry(self.closeFrame,bd=2,relief=RIDGE)
        self.ipEntry.grid(column=1,row=2,sticky="ew")         
        
        self.cloud = Frame(self.menuFrame,bd=3,relief=RIDGE,bg=self.framecolor)
        self.cloud.grid(row=0,column=1,sticky="nsew")
        
        self.closeLbl = Label(self.cloud,text="Cloud Sessions",bd=2,relief=RIDGE,bg=self.framecolor)
        self.closeLbl.grid(column=0,columnspan=2,row=0,sticky="ew")
        
        self.nameLbl = Label(self.cloud,text="Name:",bd=2,relief=RIDGE,bg=self.framecolor)
        self.nameLbl.grid(column=0,row=1,sticky="ew")
        
        self.cloudEntry = Entry(self.cloud,bd=2,relief=RIDGE)
        self.cloudEntry.grid(column=1,row=1,sticky="ew")
        
        self.ipLbl = Label(self.cloud,text="Cloud sessions:",bd=2,relief=RIDGE,bg=self.framecolor)
        self.ipLbl.grid(column=0,row=2,sticky="nsew")
        
        self.sessVar = StringVar()
        self.sessVar.set("None")
        self.sessCDrop =  OptionMenu(self.cloud,self.sessVar,"Sess1","Sess2")
        self.sessCDrop.grid(column=1,row=2,sticky="ew")
        self.sessCDrop.configure(bg=self.buttoncolor,bd=2,relief=RIDGE)  
        
        self.tType = Label(self.menuFrame,text="Trader:",bd=2,relief=RIDGE,bg=self.framecolor)
        self.tType.grid(column=0,row=1, sticky="nsew")  
        
        self.traderVar = StringVar()
        self.traderVar.set("Human")
        self.type = OptionMenu(self.menuFrame,self.traderVar,"Human","Sniper","ZIP","ZIC","Giveaway","Shaver")
        self.type = OptionMenu(self.menuFrame,self.traderVar,"Human","Sniper","ZIP","ZIC","Giveaway","Shaver")
        self.type.grid(column=1,row=1,sticky="ew")
        self.type.configure(bg=self.buttoncolor,bd=2,relief=RIDGE)
        self.get_auto_agents()
        
        self.trdSide = Label(self.menuFrame,bd=2,relief=RIDGE,text="Type",bg=self.framecolor)
        self.trdSide.grid(column=0,row=2, sticky="nsew")
        self.bidVar = StringVar()
        self.bidVar.set("BUY")
        self.bidDrop =  OptionMenu(self.menuFrame,self.bidVar,"BUY","SELL")
        self.bidDrop.grid(column=1,row=2,sticky="ew")
        self.bidDrop.configure(bg=self.buttoncolor,bd=2,relief=RIDGE)      
        

        self.sideVar = StringVar()
        self.sideVar.set("Closed")
        
        self.trdSide = Label(self.menuFrame,bd=2,relief=RIDGE,text="Session type:",bg=self.framecolor)
        self.trdSide.grid(column=0,row=3, sticky="nsew")
        
        self.sideDrop =  OptionMenu(self.menuFrame,self.sideVar,"Closed","Cloud")
        self.sideDrop.grid(column=1,row=3,sticky="ew")
        self.sideDrop.configure(bg=self.buttoncolor,bd=2,relief=RIDGE)
                
        self.statusLbl = Label(self.menuFrame,image = self.notconnImg,bd=2,relief=RIDGE,bg=self.framecolor)
        self.statusLbl.image = self.notconnImg
        self.statusLbl.grid(column=0,row=4,sticky="nsew")
                
        self.connectBtn = Button(self.menuFrame,text="Connect",command=self.connect,bg=self.buttoncolor)
        self.connectBtn.grid(column=1,row=4,sticky="nsew")
        
    
    def get_auto_agents(self):
        files = os.listdir('./Agents')#gets all files within the Agents folder 
        agent_list = [] #initializez the list of desired file names            
        for element in files: # loops through every file in the folder         
            if element.endswith('.py'): #check if it is a source file          
                agent_list.append(element.split('.')[0]) #adds the name of the file to the list       
        self.type["menu"].delete(0,END) #clears the existing elements in the option menu list
        i = 0
        while i < len(agent_list):#loops through all found agent names
            self.type["menu"].add_command(label=agent_list[i],command=lambda temp = agent_list[i]: self.type.setvar(self.type.cget("textvariable"), value = temp)) #popuates the option menu list with the found agent names
            i += 1
    
    def getCloudInfo(self):
        action="INFO"
        headers = {'Content-Type':'application/json'}
        post_data = {"action":action,"traderID":self.factory.traderID,"sessionID":self.factory.sessionID}
        req = urllib2.Request(host+"client", json.dumps(post_data), headers)
        traders = json.loads(urllib2.urlopen(req).read())['traders']
        i = 2  
        if self.traders != traders:
            for label in self.traderLabels:
                    label[0].grid_forget()
                    label[1].grid_forget()
                    label[2].grid_forget()
                    label[3].grid_forget()              
            self.traders = traders
            for name in traders:                                      
                trader = name[0]
                iptr = name[1]
                tytr = name[2]
                agtr = name[3]
                self.id = Label(self.traderFrame,text = trader,bg=self.buttoncolor,bd=3,relief=RIDGE)
                self.id.grid(column = 0,row = i,sticky="ew")                
                self.ipl = Label(self.traderFrame,text=iptr,bg=self.buttoncolor,bd=3,relief=RIDGE)
                self.ipl.grid(column = 1,row = i,sticky="ew")
                self.tytr = Label(self.traderFrame,text=tytr,bg=self.buttoncolor,bd=3,relief=RIDGE)
                self.tytr.grid(column = 2,row = i,sticky="ew")
                self.agent = Label(self.traderFrame,text=agtr,bg=self.buttoncolor,bd=3,relief=RIDGE)
                self.agent.grid(column = 3,row = i,sticky="ew")
                self.traderLabels.append([self.id,self.ipl,self.tytr,self.agent])
                i += 1
                self.mainFrame.update_idletasks()
                self.cnv.configure(scrollregion=(0, 0, self.mainFrame.winfo_width(), self.mainFrame.winfo_height()))
         
    def connect(self):
        
        if self.sideVar.get() == 'Closed':
            self.name = self.nameEntry.get()
            self.ip = self.ipEntry.get()
            self.factory.chTrader = self.traderVar.get()
            self.factory.type_trade = self.bidVar.get()
            self.factory.name = self.name
            self.connector = reactor.connectTCP(self.ip, 8000, self.factory)
            
        elif self.sideVar.get() == 'Cloud':
            self.factory.name = self.cloudEntry.get()        
            self.factory.cloudSession = self.sessVar.get()
            self.factory.chTrader = self.traderVar.get()            
            self.factory.type_trade = self.bidVar.get()
            
            if self.factory.cloudSession == 'None' or self.factory.name == '':
                return False
            
            if self.traderVar.get() != 'Human':
                if self.bidVar.get() == 'BUY':
                    agent = imp.load_source("Trader_"+self.traderVar.get(),"./Agents/"+self.traderVar.get()+".py")    
                    agent_class = getattr(agent,'Trader_'+self.traderVar.get())
                    self.factory.agent = agent_class(self.bidVar.get(),self.factory.name,0.00,'Bid',False,0)
                else:
                    agent = imp.load_source("Trader_"+self.traderVar.get(),"./Agents/"+self.traderVar.get()+".py")    
                    agent_class = getattr(agent,'Trader_'+self.traderVar.get())
                    self.factory.agent = agent_class(self.bidVar.get(),self.factory.name,0.00,'Ask',False,0)  
            
            action="CONNECT"
            headers = {'Content-Type':'application/json'}
            post_data = {"action":action,"name":self.factory.name,"session":self.factory.cloudSession,
                "strategy":self.factory.chTrader,"type":self.factory.type_trade}
            req = urllib2.Request(host+"client", json.dumps(post_data), headers)
            connDetails = json.loads(urllib2.urlopen(req).read())  
            try:          
                self.factory.traderID = connDetails['traderID']
                self.factory.sessionID = connDetails['sessionID']
                self.factory.blotter_index = 2
                self.factory.blotter_length = 0
                for element in self.blotterLabels:
                    element[0].grid_forget()
                    element[1].grid_forget()
                    element[2].grid_forget()
                    element[3].grid_forget()
                    element[4].grid_forget()            
                del self.blotterLabels[:] 
                
                print self.factory.traderID,self.factory.sessionID
                self.info = task.LoopingCall(self.getCloudInfo)
                self.info.start(9)
                self.session = task.LoopingCall(self.marketSession)
                self.session.start(1)
            except:
                return False            
            
        self.connectBtn.grid_forget()
        self.statusLbl.grid_forget()        
        self.connectBtn = Button(self.menuFrame,text="Disconnect",bd=2,relief=RIDGE,command=self.disconnect,bg=self.buttoncolor)
        self.connectBtn.grid(column=1,row=4,sticky="nsew")
        self.statusLbl = Label(self.menuFrame,image = self.connectedImg,bd=2,relief=RIDGE,bg=self.framecolor)
        self.statusLbl.image = self.connectedImg 
        self.statusLbl.grid(column=0,row=4,sticky="nsew")       
        self.cnv.configure(scrollregion=(0, 0, self.mainFrame.winfo_width(), self.mainFrame.winfo_height()))
        
    def marketSession(self):
        del self.factory.lob.bids[:]
        del self.factory.lob.asks[:] 
        
        self.cnv.configure(scrollregion=(0, 0, self.mainFrame.winfo_width(), self.mainFrame.winfo_height()))
        action="SESSION"
        headers = {'Content-Type':'application/json'}
        post_data = {"action":action,"traderID":self.factory.traderID,"sessionID":self.factory.sessionID}
        req = urllib2.Request(host+"client", json.dumps(post_data), headers)
        session = json.loads(urllib2.urlopen(req).read())
        if session['status'] == 'OK':
            lob = session['lob']
            balance = session['balance']
            LD = session['LD']
            LP = session['LP']
            BL = session['BL']
            trade = session['trade']
            self.limitVar.set(str(LP))
            
            if float(balance) >  float(self.profitLbl.cget("text")):
                self.profitLbl.config(bg='green')                        
            elif float(balance) < float(self.profitLbl.cget("text")):
                self.profitLbl.config(bg='red')
            else:                        
                self.profitLbl.config(bg=self.framecolor)
            
            
            self.profitVar.set(str(balance)) 
            if len(lob) > 0:
                self.factory.ui.timeVar.set(session['time'])
                ii = 0
                for element in lob[0]:
                    self.factory.ui.qtyBidVar[ii].set(element[0])
                    self.factory.ui.BidVar[ii].set(element[1])
                    if self.factory.agent != None and element[0] != ' ' and element[1] != ' ':
                        self.factory.lob.bids.append([int(element[1]),int(element[0])])
                    ii += 1
                ii = 0
                for element in lob[1]:
                    self.factory.ui.AskVar[ii].set(element[1])
                    self.factory.ui.qtyAskVar[ii].set(element[0])
                    if self.factory.agent != None and element[0] != ' ' and element[1] != ' ':
                        self.factory.lob.asks.append([int(element[1]),int(element[0])])
                    ii += 1
                    
            if self.factory.blotter_length < BL:
                party2 = LD['party2']
                price = str(LD['price'])
                party1 = LD['party1']
                qty = LD['qty']
                time = LD['time']
                
                self.factory.blotter_length = BL
                party2lbl = Label(self.blotterFrame,bd=3,text=party2,bg = 'white',fg='black',relief=RIDGE)
                pricelbl = Label(self.blotterFrame,bd=3,text=price,bg = 'white',fg='black',relief=RIDGE)
                party1lbl = Label(self.blotterFrame,bd=3,text=party1,bg = 'white',fg='black',relief=RIDGE)
                qtylbl = Label(self.blotterFrame,bd=3,text=qty,bg = 'white',fg='black',relief=RIDGE)
                timelbl = Label(self.blotterFrame,bd=3,text=time,bg = 'white',fg='black',relief=RIDGE)
                self.blotterLabels.append([party2lbl,pricelbl,party1lbl,qtylbl,timelbl])                        
                lgt = len(self.blotterLabels) - 1
                self.blotterLabels[lgt][0].grid(column=0,row = self.factory.blotter_index, sticky='ew')
                self.blotterLabels[lgt][1].grid(column=1,row = self.factory.blotter_index, sticky='ew')
                self.blotterLabels[lgt][2].grid(column=2,row = self.factory.blotter_index, sticky='ew')
                self.blotterLabels[lgt][3].grid(column=3,row = self.factory.blotter_index, sticky='ew')
                self.blotterLabels[lgt][4].grid(column=4,row = self.factory.blotter_index, sticky='ew') 
                self.factory.blotter_index += 1
            
            times = []
            prices = []
            for label in self.blotterLabels:
                prices.append(float(label[1].cget("text")))
                times.append(float(label[4].cget("text")))
            
            self.mainPlot.clear()        
            self.mainPlot.plot(times,prices,label='Deals price/time')   
            self.mainPlot.legend()
            self.mainPlot.set_title('Market Evolution')
            self.mainPlot.set_ylabel('Transaction price')         
            self.mainPlot.set_xlabel('Time (s)')
            self.plotFigure.canvas.draw()            
            self.mainFrame.update_idletasks()
            
            if self.timeVar.get() != 'Idle':
                request_time = float(self.timeVar.get().split(' ')[0])
                LOB = self.factory.lob.publish_lob(request_time)
                if self.factory.agent != None:
                    if self.factory.agent.bidType == 'Bid':
                        if len(LOB['asks']['lob']) > 0 and trade != None:
                            self.factory.agent.respond(request_time,LOB , trade, False)
                    else: 
                        if len(LOB['bids']['lob']) > 0 and trade != None:
                            self.factory.agent.respond(request_time,LOB , trade, False)
                
                if self.factory.agent != None and self.limitVar.get() != 'NO_ORDER' and self.limitVar.get() != 'NONE':
                    order = Order(self.factory.name,self.factory.agent.bidType,int(self.limitVar.get()),
                                    1,float(self.timeVar.get().split(' ')[0]))
                    self.factory.agent.add_order(order)
                    request_time = float(self.timeVar.get().split(' ')[0])
                    order = self.factory.agent.getorder(request_time,request_time,
                                                        self.factory.lob.publish_lob(request_time))
                    self.factory.previousOrder = order 
                    if order != None:                                           
                        bid = order.price               
                        action="SHOUT"
                        headers = {'Content-Type':'application/json'}
                        post_data = {"action":action,"bid":bid,"traderID":self.factory.traderID,"sessionID":self.factory.sessionID}
                        req = urllib2.Request(host+"client", json.dumps(post_data), headers)
                        response = json.loads(urllib2.urlopen(req).read())
                   
                    
                
    def disconnect(self):
        
        self.connectBtn.grid_forget()
        self.statusLbl.grid_forget()
        self.factory.agent = None
        
        for label in self.traderLabels:
                    label[0].grid_forget()
                    label[1].grid_forget()
                    label[2].grid_forget()
                    label[3].grid_forget()
        del self.traderLabels[:]
        
        self.connectBtn = Button(self.menuFrame,text="Connect",bd=2,relief=RIDGE,command=self.connect,bg=self.buttoncolor)
        self.connectBtn.grid(column=1,row=4,sticky="nsew")
        self.statusLbl = Label(self.menuFrame,image = self.notconnImg,bd=2,relief=RIDGE,bg=self.framecolor)
        self.statusLbl.image = self.notconnImg
        self.statusLbl.grid(column=0,row=4,sticky="ewsn")
        if self.sideVar.get() == 'Closed':
            self.connector.disconnect()
        else:
            action="DISCONNECT"
            headers = {'Content-Type':'application/json'}
            post_data = {"action":action,"traderID":self.factory.traderID,
                "sessionID":self.factory.sessionID,"name":self.factory.name}
            req = urllib2.Request(host+"client", json.dumps(post_data), headers)
            disconnection = json.loads(urllib2.urlopen(req).read()) 
            self.info.stop()
            self.session.stop()
            self.factory.LD = None
            print disconnection['status']
    
    def placeTitle(self):
        self.logo = Label(self.mainFrame,image=self.brisImg,anchor="center",bg=self.color)
        self.logo.image = self.brisImg
        self.logo.grid(column=0,row=0,columnspan=2)
        self.titleLabel = Label(self.mainFrame,text="Bristol Stock Exchange",
            font=self.headerFont, anchor="center",bg=self.color)
        self.titleLabel.grid(column=0,row=1,columnspan=2)

class EchoClient(protocol.Protocol):    
      
    
    def connectionMade(self):
        self.data = []
        action = 'login'
        name = self.factory.name
        bid = self.factory.type_trade
        stgy = 'HUMAN'
        
        connectionData = {'action':action,'name':name,'bid':bid,'stgy':stgy}
        self.transport.write(json.dumps(connectionData))
        #self.transport.write('login|'+self.factory.name+'|'+self.factory.type_trade+'|HUMAN')
        self.STATUS = 'TRADE'
        self.factory.client = self  
        
        self.factory.profitList.append(0)
        self.factory.blotter_index = 2
        self.factory.blotter_length = 0
        for element in self.factory.ui.blotterLabels:
            element[0].grid_forget()
            element[1].grid_forget()
            element[2].grid_forget()
            element[3].grid_forget()
            element[4].grid_forget()            
        del self.factory.ui.blotterLabels[:]        
        
       #initialize robot if user wishes to test its robot
        if self.factory.ui.traderVar.get() != 'Human':
            if self.factory.ui.bidVar.get() == 'BUY':
                agent = imp.load_source("Trader_"+self.factory.ui.traderVar.get(),"./Agents/"+self.factory.ui.traderVar.get()+".py")    
                agent_class = getattr(agent,'Trader_'+self.factory.ui.traderVar.get())
                self.factory.agent = agent_class(self.factory.ui.bidVar.get(),self.factory.name,0.00,'Bid',False,0)
            else:
                agent = imp.load_source("Trader_"+self.factory.ui.traderVar.get(),"./Agents/"+self.factory.ui.traderVar.get()+".py")    
                agent_class = getattr(agent,'Trader_'+self.factory.ui.traderVar.get())
                self.factory.agent = agent_class(self.factory.ui.bidVar.get(),self.factory.name,0.00,'Ask',False,0)                
    
    def dataReceived(self, data):
        del self.factory.lob.bids[:]
        del self.factory.lob.asks[:]
        message = json.loads(data)
        action = message['action']                
        if action == 'goodbye':
            self.transport.loseConnection()
        elif action == 'traders':                    
            traders = message['traders']            
            if self.data != traders:
                self.data = traders
                for label in self.factory.ui.traderLabels:
                    label[0].grid_forget()
                    label[1].grid_forget()
                    label[2].grid_forget()
                    label[3].grid_forget()
                del self.factory.ui.traderLabels[:]
                if len(traders) > 0:                    
                    self.TRADERS = traders                   
                    i = 2                
                    for name in self.TRADERS:                           
                        trader = name[0]
                        iptr = name[1]
                        tytr = name[2]
                        agtr = name[3]
                        self.factory.ui.id = Label(self.factory.ui.traderFrame,text = trader,bg=self.factory.ui.buttoncolor,bd=3,relief=RIDGE)
                        self.factory.ui.id.grid(column = 0,row = i,sticky="ew")                
                        self.factory.ui.ipl = Label(self.factory.ui.traderFrame,text=iptr,bg=self.factory.ui.buttoncolor,bd=3,relief=RIDGE)
                        self.factory.ui.ipl.grid(column = 1,row = i,sticky="ew")
                        self.factory.ui.tytr = Label(self.factory.ui.traderFrame,text=tytr,bg=self.factory.ui.buttoncolor,bd=3,relief=RIDGE)
                        self.factory.ui.tytr.grid(column = 2,row = i,sticky="ew")
                        self.factory.ui.agent = Label(self.factory.ui.traderFrame,text=agtr,bg=self.factory.ui.buttoncolor,bd=3,relief=RIDGE)
                        self.factory.ui.agent.grid(column = 3,row = i,sticky="ew")
                        self.factory.ui.traderLabels.append([self.factory.ui.id,self.factory.ui.ipl,self.factory.ui.tytr,self.factory.ui.agent])
                        i += 1
                        self.factory.ui.mainFrame.update_idletasks()
                        self.factory.ui.cnv.configure(scrollregion=(0, 0, self.factory.ui.mainFrame.winfo_width(), self.factory.ui.mainFrame.winfo_height()))                    
                    
        elif action == 'interval':
            self.factory.ui.timeVar.set(message['time'])
            if int(message['time'].split(' ')[0]) <= 5:
                self.factory.ui.time.config(bg='red')                  
            else:
               self.factory.ui.time.config(bg=self.factory.ui.framecolor)
            
            self.factory.ui.limitVar.set(message['limit']) 
            if float(message['balance']) >  float(self.factory.ui.profitLbl.cget("text")):
                self.factory.ui.profitLbl.config(bg='green')                        
            elif float(message['balance']) < float(self.factory.ui.profitLbl.cget("text")):
                self.factory.ui.profitLbl.config(bg='red')
            else:                        
                self.factory.ui.profitLbl.config(bg=self.factory.ui.framecolor)            
            self.factory.ui.profitVar.set(message['balance'])
            
            lob = message['lob']
            bids = lob[0]
            asks = lob[1]
            
            ii = 0
            for bid in bids:
                qty = bid[0]
                price = bid[1]
                self.factory.ui.qtyBidVar[ii].set(qty)
                self.factory.ui.BidVar[ii].set(price)
                if self.factory.agent != None:
                    if price != ' ' and qty != ' ':
                        self.factory.lob.bids.append([int(price),int(qty)])
                ii += 1
            ii = 0
            for ask in asks:
                qty = ask[0]
                price = ask[1]
                self.factory.ui.AskVar[ii].set(price)
                self.factory.ui.qtyAskVar[ii].set(qty)
                if self.factory.agent != None:
                    if price != ' ' and qty != ' ':
                        self.factory.lob.asks.append([int(price),int(qty)])
                ii += 1
                
            trade = message['last']
            request_time = float(self.factory.ui.timeVar.get().split(' ')[0])
            LOB = self.factory.lob.publish_lob(request_time)
            
            if self.factory.agent != None:
                if self.factory.agent.bidType == 'Bid':
                    if len(LOB['asks']['lob']) > 0:
                        self.factory.agent.respond(request_time,LOB , trade, False)
                else: 
                    if len(LOB['bids']['lob']) > 0:
                        self.factory.agent.respond(request_time,LOB , trade, False)
                        

                if self.factory.agent != None and self.factory.ui.limitVar.get() != 'NO_ORDER':
                    order = Order(self.factory.name,self.factory.agent.bidType,int(self.factory.ui.limitVar.get()),
                                    1,float(self.factory.ui.timeVar.get().split(' ')[0]))
                    self.factory.agent.add_order(order)
                    request_time = float(self.factory.ui.timeVar.get().split(' ')[0])
                    order = self.factory.agent.getorder(request_time,request_time,
                                                        self.factory.lob.publish_lob(request_time))                        
                    self.factory.previousOrder = order
                    if order == None:
                        if self.factory.agent.bidType == 'Bid':
                            action = 'bid'               
                            msg =  {'action':action,'bid':str('0')}
                        else:
                            action = 'bid'               
                            msg =  {'action':action,'bid':str('1000')}                      
                    else: 
                        action = 'bid'                           
                        msg ={'action':action,'bid':str(order.price)}   
                                                                     
                    self.transport.write(json.dumps(msg))                    
                    
                last = message['last']                 
                if last != self.factory.blotter_length and last != None:
                    party2 = last['party2']
                    party1 = last['party1']
                    time = last['time']
                    price = last['price']
                    qty = last['qty']
                    self.factory.blotter_length = last
                    party2lbl = Label(self.factory.ui.blotterFrame,bd=3,text=party2,bg = 'white',fg='black',relief=RIDGE)
                    pricelbl = Label(self.factory.ui.blotterFrame,bd=3,text=price,bg = 'white',fg='black',relief=RIDGE)
                    party1lbl = Label(self.factory.ui.blotterFrame,bd=3,text=party1,bg = 'white',fg='black',relief=RIDGE)
                    qtylbl = Label(self.factory.ui.blotterFrame,bd=3,text=qty,bg = 'white',fg='black',relief=RIDGE)
                    timelbl = Label(self.factory.ui.blotterFrame,bd=3,text=time,bg = 'white',fg='black',relief=RIDGE)
                    self.factory.ui.blotterLabels.append([party2lbl,pricelbl,party1lbl,qtylbl,timelbl])                        
                    lgt = len(self.factory.ui.blotterLabels) - 1
                    self.factory.ui.blotterLabels[lgt][0].grid(column=0,row = self.factory.blotter_index, sticky='ew')
                    self.factory.ui.blotterLabels[lgt][1].grid(column=1,row = self.factory.blotter_index, sticky='ew')
                    self.factory.ui.blotterLabels[lgt][2].grid(column=2,row = self.factory.blotter_index, sticky='ew')
                    self.factory.ui.blotterLabels[lgt][3].grid(column=3,row = self.factory.blotter_index, sticky='ew')
                    self.factory.ui.blotterLabels[lgt][4].grid(column=4,row = self.factory.blotter_index, sticky='ew') 
                    self.factory.blotter_index += 1
                        

                
            times = []
            prices = []
            for label in self.factory.ui.blotterLabels:
                prices.append(float(label[1].cget("text")))
                times.append(float(label[4].cget("text")))
            
            self.factory.ui.mainPlot.clear()        
            self.factory.ui.mainPlot.plot(times,prices,label='Deals price/time')   
            self.factory.ui.mainPlot.legend()
            self.factory.ui.mainPlot.set_title('Market Evolution')
            self.factory.ui.mainPlot.set_ylabel('Transaction price')         
            self.factory.ui.mainPlot.set_xlabel('Time (s)')
            self.factory.ui.plotFigure.canvas.draw() 
            
            self.factory.ui.mainFrame.update_idletasks()
            self.factory.ui.cnv.configure(scrollregion=(0, 0, self.factory.ui.mainFrame.winfo_width(), self.factory.ui.mainFrame.winfo_height()))       
                        
            
    def connectionLost(self, reason):
        self.factory.ui.disconnect()
        self.factory.ui.timeVar.set("Idle")                
        del self.factory.profitList[0:len(self.factory.profitList)]  
        
        
    
    
class ClientFactory(protocol.ClientFactory):
    protocol = EchoClient
    def __init__(self,ui):
        self.lob = DUMMY_LOB()
        self.blotter_length = 0
        self.blotter_index = 2
        self.ui = ui
        self.name = ''
        self.timeList = []
        self.profitList = []        
        self.client = None
        self.agent = None        
        self.previousOrder = None
        self.traderID = None
        self.sessionID = None        
        
        
    def clientConnectionFailed(self, connector, reason):
	    x = 10
        #reactor.stop()
    
    def clientConnectionLost(self, connector, reason):
	    x = 10
        #reactor.stop()


# this connects the protocol to a server runing on port 8000
def main():     
    root = Tk()
    root.title('BSE Client')
    root.geometry("600x670")  
    root.pack_propagate(0)
    ui = UI(root)
    tksupport.install(root)     
    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()