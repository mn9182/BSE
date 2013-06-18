#!/usr/bin/env python
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

from twisted.internet import reactor, protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory
from twisted.internet import task, tksupport
from datetime import datetime
from Lib.Order import Order
from Lib.Exchange import Exchange
from Tkinter import *
from PIL import ImageTk, Image
from pymongo import MongoClient

import gridfs
import socket
import math
import random
import tkFont
import pylab as py
import datetime
import os
import imp
import csv
import json
import urllib2

#host = "http://bse.eu01.aws.af.cm/"
host = "http://127.0.0.1:5000/"
bse_sys_minprice = 1  #-minimum price in the system, in cents/pennies          
bse_sys_maxprice = 1000  #-maximum price in the system, in cents/pennies       
ticksize = 1  #-minimum change in price, in cents/pennies                      

#-class that maintains and creates the user interface for the server side      
class UI:
        
    def __init__(self, master,ip_address,factory):
        #======================================================================
        #-aspect ratio - initializez a width and height relative to the users  
        #screen                                                                
        SCREEN_SIZEX = master.winfo_screenwidth() 
        SCREEN_SIZEY = master.winfo_screenheight()
        SCREEN_RATIOX = 0.8
        SCREEN_RATIOY = 0.9
        FrameSizeX  = int(SCREEN_SIZEX * SCREEN_RATIOX)     
        FrameSizeY  = int(SCREEN_SIZEY * SCREEN_RATIOY)
        FramePosX   = (SCREEN_SIZEX - FrameSizeX)/2
        FramePosY   = (SCREEN_SIZEY - FrameSizeY)/2
        master.geometry("%sx%s+%s+%s" % (FrameSizeX,FrameSizeY,FramePosX,FramePosY))
        #master.minsize(FrameSizeX,FrameSizeY)
        #master.maxsize(FrameSizeX,FrameSizeY)

        #======================================================================
        self.timeSpan = 20 #-default session length                            
        self.maxTrader = 10 #-default number of traders                        
        self.ip_address = ip_address #-IP address of server host               
        self.root = master #-root element (window) for the GUI                         
        self.root.bind("<Escape>",self.end) #-binds the Esc button with the action of closing the application
        master.protocol("WM_DELETE_WINDOW", self.handler) #-terminates GUI loop
        #======================================================================
        #-initialization phase - loads images and fonts that are required      
        self.color = 'LemonChiffon'
        self.framecolor = 'DarkKhaki'
        self.buttoncolor = 'Khaki'
        self.customFont = tkFont.Font(family="Helvetica", size=20)
        self.headerFont = tkFont.Font(family="Century Schoolbook L",size=20)
        self.tableFont = tkFont.Font(family="Century Schoolbook L",size=16)
        self.cellsFont = tkFont.Font(family="Century Schoolbook L",size=12)        
        self.headerFont.configure(underline=True)
        self.timerImg = ImageTk.PhotoImage(Image.open('Images/timer.png'))
        self.brisImg = ImageTk.PhotoImage(Image.open('Images/bristol.png'))
        #======================================================================
        #======================================================================
        #-set up canvas                                                        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)        
        self.cnv = Canvas(self.root) #initializez canvas  
        self.cnv.grid(row=0, column=0,sticky="nsew") #place the canvas on the window        
        self.mainFrame = Frame(self.cnv,bd=3, relief=RIDGE,bg=self.framecolor) #creates a main frame on the canvas               
        self.mainFrame.pack(side=TOP, padx=5, pady=5, fill=X) #place the main frame on the canvas
        self.vScroll = Scrollbar(self.root, orient=VERTICAL, command=self.cnv.yview) #creates a vertical scrollbar on the window
        self.vScroll.grid(row=0, column=1, sticky='ns') #places the scrollbar on the right hand side       
        self.hScroll = Scrollbar(self.root, orient=HORIZONTAL, command=self.cnv.xview) #creates a horizontal scrollbar
        self.hScroll.grid(row=1, column=0, sticky='ew') #places the scrollbar on the bottom of the window       
        self.cnv.configure(yscrollcommand=self.vScroll.set,xscrollcommand=self.hScroll.set) #configures the scrollbars functionality to represent the canvas               
        self.cnv.create_window(0, 0, window=self.mainFrame, anchor='nw') #creates a canvas window on the main frame
        #======================================================================
        #-section where each main part of the GUI is represented, split into   
        #different function for ease of use and search                         
        self.addTitle()
        self.mainCont = Frame(self.mainFrame,bg=self.framecolor)
        self.mainCont.grid(column=0,row=2,sticky='nsew')
        self.menuCont = Frame(self.mainCont,bg=self.framecolor)
        self.menuCont.pack(side=LEFT,fill=BOTH,padx=5,pady=5)
        self.sesCont = Frame(self.mainCont,bg=self.framecolor)
        self.sesCont.pack(side=LEFT,fill=BOTH,padx=5,pady=5)        
        self.addMenu()
        self.addSession()      
        #======================================================================
        self.mainFrame.update_idletasks() #-waits until all widgets are drawn  
        self.cnv.configure(scrollregion=(0, 0, self.mainFrame.winfo_width(), self.mainFrame.winfo_height())) #updates scrollbar area   
        #======================================================================
        self.MyFactory = factory(10,20,self) #-initializez the server factory (specific for twisted server protocol)
        reactor.listenTCP(8000,self.MyFactory,interface = self.ip_address) #-rector listens to port 8000 using the factory and the provided ip address
        #======================================================================
        self.past_sessions() #-initializez the database query part of the GUI  
    
    #-method that terminates the application                                   
    def end(self, event):
        if self.MyFactory.sessionID != None:
            self.cancelHosting()
        if self.MyFactory.dbConnectionStatus == 'CONNECTED':
            self.MyFactory.connection.close() #-close the database connection      
        reactor.stop() #-stops the reactor - event driven server               
        self.root.destroy() #-destroys main GUI loop                           
        self.root.quit() #-exits main GUI window                               
        sys.exit() #-exits the system                                          
    
    #-method that handles the Escape button bind to close the application      
    def handler(self):
        if self.MyFactory.dbConnectionStatus == 'CONNECTED':
            self.MyFactory.connection.close()
        reactor.stop() #stops the reactor - event driven server                
        self.root.destroy()# destroys main GUI loop                            
        self.root.quit()# exits main GUI window                                
        sys.exit() #exits the system                                           
        
    #-method that draws the frame for the sesison panel
    #-draws all the widgets required for session manipulation, LOB and trader
    # statistics   
    def addSession(self):
        self.timerFrame = Frame(self.sesCont,bd = 3,bg=self.color,relief = RIDGE)
        self.timerFrame.pack(side=TOP,padx=5,pady=5,fill=X)
        self.timerPic = Label(self.timerFrame,bg = self.color,image = self.timerImg)
        self.timerPic.image = self.timerImg
        self.timerPic.pack(side=TOP,padx=5,pady=5)
        
        self.timeVar = StringVar()
        self.timeVar.set(str(self.timeSpan) + " seconds")
        self.time = Label(self.timerFrame,textvar=self.timeVar,bg = self.color,font=self.customFont)
        self.time.pack(side=TOP, padx=5,pady=5)
        
        self.orderFrame = Frame(self.sesCont,bd=3,bg = self.color,relief=RIDGE)
        self.orderFrame.pack(side=TOP,padx=5,pady=5,fill=X)
        
        self.orderContFrame = Frame(self.orderFrame,bg=self.color)
        self.orderContFrame.pack(side=TOP,padx=5,pady=5)
        
        self.orderLabel = Label(self.orderContFrame,bg = self.color,text="ORDERBOOK",font=self.headerFont)
        self.orderLabel.grid(column=0,row=0,pady=5,padx=5,columnspan=4,sticky="ew")
        
        self.qtybidH = Label(self.orderContFrame,bd=3,
            fg='white',bg='black',font = self.tableFont,relief=RIDGE,text="QTY")
        self.qtybidH.grid(column=0,row=1,sticky="ew")
        self.bidH = Label(self.orderContFrame,text="BIDS",bd=3,
            fg='white',bg='black',font = self.tableFont,relief=RIDGE)
        self.bidH.grid(column=1,row=1,sticky="ew")        
        self.askH = Label(self.orderContFrame,text="ASKS",bd=3,
            fg='white',bg='black',font = self.tableFont,relief=RIDGE)
        self.askH.grid(column=2,row=1,sticky="ew")
        self.qtyaskH = Label(self.orderContFrame,bd=3,
            fg='white',bg='black',font = self.tableFont,relief=RIDGE,text="QTY")
        self.qtyaskH.grid(column=3,row=1,sticky="ew")
        
        self.bidLabels = []
        self.askLabels = []
        self.bidVars = []
        self.askVars = []
        self.bidQVars = []
        self.bidQLabels = []
        self.askQVars = []
        self.askQLabels = []
        
        index = 0
        while index < 10:
            self.bidVars.append(StringVar())
            self.bidVars[index].set(' ')
            self.bidLabels.append(Label(self.orderContFrame,textvar = self.bidVars[index],bd=3,
                font=self.cellsFont,bg='PaleGreen',relief = RIDGE))
            self.bidLabels[index].grid(column = 1,row = index + 2,sticky="ew")
            self.bidQVars.append(StringVar())
            self.bidQVars[index].set(' ')
            self.bidQLabels.append(Label(self.orderContFrame,textvar = self.bidQVars[index],bd=3,
                font=self.cellsFont,bg='PaleGreen',relief = RIDGE))
            self.bidQLabels[index].grid(column = 0,row = index + 2,sticky="ew")
            self.askVars.append(StringVar())
            self.askVars[index].set(' ')
            self.askLabels.append(Label(self.orderContFrame,textvar = self.askVars[index],bd=3,
                font=self.cellsFont,bg='Salmon',relief = RIDGE))
            self.askLabels[index].grid(column = 2,row = index + 2,sticky="ew")
            self.askQVars.append(StringVar())
            self.askQVars[index].set(' ')
            self.askQLabels.append(Label(self.orderContFrame,textvar = self.askQVars[index],bd=3,
                font=self.cellsFont,bg='Salmon',relief = RIDGE))
            self.askQLabels[index].grid(column = 3,row = index + 2,sticky="ew")
            index += 1
        
        self.profitFrame = Frame(self.sesCont,bd=3,bg = self.color,relief=RIDGE)
        self.profitFrame.pack(side=TOP,padx=5,pady=5,fill=X)
        
        self.profitContFrame = Frame(self.profitFrame,bg=self.color)
        self.profitContFrame.pack(side=TOP,padx=5,pady=5)
        
        self.profitTitleLabel = Label(self.profitContFrame,text="Profits",bg=self.color,font=self.headerFont)
        self.profitTitleLabel.grid(column=0,row=0,columnspan=7,sticky="ew")
        
        self.NRPH = Label(self.profitContFrame,text="NR",bd=3,
            relief=RIDGE,bg="Black",fg="white")
        self.NRPH.grid(column=0,row=1,sticky="ew")
        
        self.IDH = Label(self.profitContFrame,text="NAME",bd=3,
            relief=RIDGE,bg="Black",fg="white")
        self.IDH.grid(column=1,row=1,sticky="ew")
        
        self.profitH = Label(self.profitContFrame,text="PROFIT",bd=3,
            relief=RIDGE,bg="Black",fg="white")
        self.profitH.grid(column=2,row=1,sticky="ew")
        
        self.typePH = Label(self.profitContFrame,text="TYPE",bd=3,
            relief=RIDGE,bg="Black",fg="white")
        self.typePH.grid(column=3,row=1,sticky="ew")
        
        self.agentPH = Label(self.profitContFrame,text="AGENT",bd=3,
            relief=RIDGE,bg="Black",fg="white")
        self.agentPH.grid(column=4,row=1,sticky="ew")

        self.maxProfitPH = Label(self.profitContFrame,text="MAX PROFIT",bd=3,
            relief=RIDGE,bg="Black",fg="white")
        self.maxProfitPH.grid(column=5,row=1,sticky="ew")

        self.allocPH = Label(self.profitContFrame,text="EFFICIENCY",bd=3,
            relief=RIDGE,bg="Black",fg="white")
        self.allocPH.grid(column=6,row=1,sticky="ew")
        
        self.nrProfitVar = []
        self.nrProfitLabels = []
        
        self.idProfitVar = []
        self.idProfitLabels = []
        
        self.profitProfitVar = []
        self.profitProfitLabels = []
        
        self.typeProfitVar = []
        self.typeProfitLabels = []
        
        self.agentProfitVar=[]
        self.agentProfitLabels=[]

        self.maxProfitVar=[]
        self.maxProfitLabels=[]

        self.allocVar=[]
        self.allocLabels=[]
        
        ii = 0
        while ii < self.maxTrader:
            self.nrProfitVar.append(StringVar())
            self.nrProfitVar[ii].set('')
            self.nrProfitLabels.append(Label(self.profitContFrame,textvar = self.nrProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.nrProfitLabels[ii].grid(column=0,row=ii+2,sticky="ew")
            self.idProfitVar.append(StringVar())
            self.idProfitVar[ii].set('')
            self.idProfitLabels.append(Label(self.profitContFrame,textvar = self.idProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.idProfitLabels[ii].grid(column=1,row=ii+2,sticky="ew")
            self.profitProfitVar.append(StringVar())
            self.profitProfitVar[ii].set('')
            self.profitProfitLabels.append(Label(self.profitContFrame,textvar = self.profitProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.profitProfitLabels[ii].grid(column=2,row=ii+2,sticky="ew")
            self.typeProfitVar.append(StringVar())
            self.typeProfitVar[ii].set('')
            self.typeProfitLabels.append(Label(self.profitContFrame,textvar = self.typeProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.typeProfitLabels[ii].grid(column=3,row=ii+2,sticky="ew")
            self.agentProfitVar.append(StringVar())
            self.agentProfitVar[ii].set('')
            self.agentProfitLabels.append(Label(self.profitContFrame,textvar = self.agentProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.agentProfitLabels[ii].grid(column=4,row=ii+2,sticky="ew")
            self.maxProfitVar.append(StringVar())
            self.maxProfitVar[ii].set('')
            self.maxProfitLabels.append(Label(self.profitContFrame,textvar = self.maxProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.maxProfitLabels[ii].grid(column=5,row=ii+2,sticky="ew")
            self.allocVar.append(StringVar())
            self.allocVar[ii].set('')
            self.allocLabels.append(Label(self.profitContFrame,textvar = self.allocVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.allocLabels[ii].grid(column=6,row=ii+2,sticky="ew")
            ii += 1
        
    def setOptions(self):
        for element in self.clientOptionsVars:
            element.set(self.allOptionsVar.get())
    #-method for drawing widgets that set the parameters for each session including
    #number of traders, session time, type of traders and commence button
    def hostSession(self):        
        if len(self.sessEntry.get()):            
            self.hostBtn.grid_forget()
            self.hostBtn = Button(self.menuFrame,text="CANCEL HOSTING",bg=self.buttoncolor,command=self.cancelHosting)
            self.hostBtn.grid(column=0,row=3,columnspan=2,sticky='ew')
            now = datetime.datetime.now()
            now = str(now.strftime("%Y-%m-%d-%H-%M"))
            name = "%s_%s" % (now,self.sessEntry.get())
            action = "HOST"
            headers = {'Content-Type':'application/json'}
            post_data = {"action":action,"name":name}
            req = urllib2.Request(host+"server", json.dumps(post_data), headers)
            self.MyFactory.sessionID = urllib2.urlopen(req).read()
            print self.MyFactory.sessionID
        else:
            print "NO SESSION NAME"
            
    def cancelHosting(self):
        self.hostBtn.grid_forget()
        self.hostBtn = Button(self.menuFrame,text="HOST SESSION",bg=self.buttoncolor,command=self.hostSession)
        self.hostBtn.grid(column=0,row=3,columnspan=2,sticky='ew')         
        
        action = "CLOSE" 
        headers = {'Content-Type':'application/json'}
        post_data = {"action":action,"id":self.MyFactory.sessionID}   
        req = urllib2.Request(host+"server", json.dumps(post_data), headers)
        self.MyFactory.sessionID = None
        print urllib2.urlopen(req).read() 
        
        ii = 0
        while ii < self.MyFactory.ui.maxTrader:
            self.MyFactory.ui.numberVars[ii].set('')
            self.MyFactory.ui.nameVars[ii].set('')
            self.MyFactory.ui.ipVars[ii].set('')
            self.MyFactory.ui.typeVars[ii].set('')
            self.MyFactory.ui.agentVars[ii].set('')
            ii += 1
        
    def addMenu(self):
        self.menuFrame = Frame(self.menuCont,bd=3,bg = self.color,relief=RIDGE)
        self.menuFrame.pack(side=TOP,padx=5,pady=5,fill=X)
        
        menuTitle = Label(self.menuFrame,text="SESSION CONTROL",bd=2,relief=RIDGE, bg = self.color,font=self.headerFont)
        menuTitle.grid(column=0,row=0,sticky="ew",columnspan=2)
        
        ipLabel = Label(self.menuFrame,bd=2,relief=RIDGE,bg = self.color,text="Exchange IP:")
        ipLabel.grid(column=0,row=1,sticky="ew") 
        
        ip = Label(self.menuFrame,bd=2,relief=RIDGE,bg = self.color,text=self.ip_address)
        ip.grid(column=1,row=1,sticky="ew") 
        
        sessionLbl = Label(self.menuFrame,text="Session name:",bg=self.color,relief=RIDGE,bd=2)
        sessionLbl.grid(column=0,row=2,sticky="ew")  
        
        self.sessEntry = Entry(self.menuFrame,bd=2,relief=RIDGE)
        self.sessEntry.grid(column=1,row=2,sticky="ew")
        
        self.hostBtn = Button(self.menuFrame,text="HOST SESSION",bg=self.buttoncolor,command=self.hostSession)
        self.hostBtn.grid(column=0,row=3,columnspan=2,sticky='ew')      
        
        interval = Label(self.menuFrame,text="Session duration:",bg=self.color,relief=RIDGE,bd=2)
        interval.grid(column=0,row=4,sticky='ew')
        
        self.entry = Entry(self.menuFrame,bd=2,relief=RIDGE)
        self.entry.grid(row=4,column=1,sticky='ew')
        self.entry.bind("<Return>",self.enterInterval)
        
        intLabel = Label(self.menuFrame,bg = self.color,bd=2,relief=RIDGE,text="Default session duration:")
        intLabel.grid(row=5,column=0,sticky="ew")
        
        duration = Label(self.menuFrame,bg = self.color,bd=2,relief=RIDGE,text="20 seconds")
        duration.grid(row=5,column=1,sticky="ew")
        
        market = Label(self.menuFrame,bg = self.color,bd=2,relief=RIDGE,text="Market replenishment")
        market.grid(row=6,column=0,sticky="nsew")

        self.distributionVar = StringVar()
        self.distributionVar.set("drip-poisson")
        self.distributions = OptionMenu(self.menuFrame,self.distributionVar,"drip-jitter","drip-poisson","drip-fixed","periodic")
        self.distributions.config(bg = self.buttoncolor,bd=2,relief=RIDGE)
        self.distributions.grid(row=6,column=1,sticky="ew")

        orderLabel = Label (self.menuFrame,bd=2,relief=RIDGE,text="Order renewal interval:",bg = self.color)
        orderLabel.grid(row=7,column=0,sticky="nsew")
        
        self.orderIntervalVar = StringVar()
        self.orderIntervalVar.set('5')
        self.orderInterval = OptionMenu(self.menuFrame,self.orderIntervalVar,"5","10","20","100","150","300")
        self.orderInterval.config(bg=self.buttoncolor,bd=2,relief=RIDGE)
        self.orderInterval.grid(row=7,column=1,sticky="ew")

        #==================================================================================================
        #=========================================SLEEP MODE GUI IMPLEMENTATION============================

        sleepModeLabel = Label (self.menuFrame,bd=2,relief=RIDGE,text="Sleep time:",bg = self.color)
        sleepModeLabel.grid(row=8,column=0,sticky="nsew")

        self.sleepModeVar = StringVar()
        self.sleepModeVar.set('FALSE')
        self.sleepOptions = OptionMenu(self.menuFrame,self.sleepModeVar,'FALSE','1','2','3','4','5','6','7','8','9','10')
        self.sleepOptions.config(bg=self.buttoncolor,bd=2,relief=RIDGE)
        self.sleepOptions.grid(row=8,column=1,sticky="ew")

        #==============================================================================================
        #============================================SHOCK IMPLEMENTATION==============================
        self.shockButton = Button(self.menuFrame,text="MARKET SHOCK", bg = self.buttoncolor, command = self.market_shock)
        self.shockButton.grid(row=9,column=0,columnspan=2,sticky="ew")

        
        
        self.startBtn = Button(self.menuFrame,text="START SESSION",bg = self.buttoncolor,command=self.startSession)
        self.startBtn.grid(row=10,column=0,columnspan=2,sticky="ew")
        
        traderLabel = Label(self.menuFrame,text="COUNTERPARTIES",bd=2,relief=RIDGE,bg = self.color,font=self.headerFont)
        traderLabel.grid(row=11,column=0,columnspan=2,sticky="ew")
        
        traderType = Label(self.menuFrame,text="Trader type:",bg = self.color,bd=2,relief=RIDGE)
        traderType.grid(column=0,row=12,sticky="nsew")
        
        self.serverClientTypeVar = StringVar()
        self.serverClientTypeVar.set('BUY')        
        self.serverClientType =  OptionMenu(self.menuFrame,self.serverClientTypeVar,"BUY","SELL")
        self.serverClientType.grid(row=12,column=1,sticky="ew")
        self.serverClientType.config(bg = self.buttoncolor,relief=RIDGE,bd=2)
        
        traderStr = Label(self.menuFrame,text="Trader strategy:",bg = self.color,bd=2,relief=RIDGE)
        traderStr.grid(column=0,row=13,sticky="nsew")

        self.serverClientAgentVar = StringVar()
        self.serverClientAgentVar.set("Shaver")
        self.serverClientAgent = OptionMenu(self.menuFrame,self.serverClientAgentVar,"Shaver","ZIP","Giveaway","Sniper","ZIC","AA")
        self.serverClientAgent.grid(column=1,row=13,sticky="ew")
        self.serverClientAgent.config(bg = self.buttoncolor,relief=RIDGE,bd=2)
        self.get_auto_agents()        
        
        self.serverClientAddBtn = Button(self.menuFrame,text="ADD",bg = self.buttoncolor,command=self.addServerClients)
        self.serverClientAddBtn.grid(column=0,row=14,columnspan=2,sticky="ew")
        
        self.serverClientClearBtn = Button(self.menuFrame,text="CLEAR",bg = self.buttoncolor,command = self.clearServerClients)
        self.serverClientClearBtn.grid(column=0,row=15,columnspan=2,sticky="ew")
        
        max = Label(self.menuFrame,text="Max traders:",bg = self.color,bd=2,relief=RIDGE)
        max.grid(column=0,row=16,sticky="nsew")
        
        self.traderEntry = Entry(self.menuFrame,bd=2,relief=RIDGE)
        self.traderEntry.grid(column=1,row=16,sticky="ew")
        self.traderEntry.bind("<Return>",self.enterTraders)        
        
        max = Label(self.menuFrame,text="Default traders:",bg = self.color,bd=2,relief=RIDGE)
        max.grid(column=0,row=17,sticky="nsew")
        
        self.traderNr = Label(self.menuFrame,bd=2,relief=RIDGE,bg = self.color,text=str(self.maxTrader))
        self.traderNr.grid(column=1,row=17,sticky="ew")
        
        max = Label(self.menuFrame,text="Disclosed information:",bg = self.color,bd=2,relief=RIDGE)
        max.grid(column=0,row=18,sticky="nsew")
        
        self.allOptionsVar = StringVar()
        self.allOptionsVar.set("NONE")
        self.allOptions = OptionMenu(self.menuFrame,self.allOptionsVar,"ALL","BID","NAME","NONE")
        self.allOptions.config(bg = self.buttoncolor,relief=RIDGE,bd=2)
        self.allOptions.grid(column=1,row=18,sticky="ew")
        
        self.setOptions = Button(self.menuFrame,text="DISCLOSE",bg = self.buttoncolor,command = self.setOptions)
        self.setOptions.grid(column=0,row=19,columnspan=2,sticky="ew")        
        
        self.nameFrame = Frame(self.menuFrame)
        self.nameFrame.grid(column=0,row=20,columnspan=2,sticky="ew")
        
        self.nrH = Label(self.nameFrame,text="NR",anchor="center",
            fg='white',font=self.tableFont,bg='DodgerBlue',bd=3,relief=RIDGE)
        self.nrH.grid(column=0,row=0,sticky="ew")
        self.nameH = Label(self.nameFrame,text="TRADERS",anchor="center",
            fg='white',font=self.tableFont,bg='DodgerBlue',bd=3,relief=RIDGE)
        self.nameH.grid(column=1,row=0,sticky="ew")
        
        self.ipH = Label(self.nameFrame,text="IPs",anchor="center",
            fg='white',font=self.tableFont,bg='DodgerBlue',bd=3,relief=RIDGE)
        self.ipH.grid(column=2,row=0,sticky="ew")
        
        self.typeH = Label(self.nameFrame,text="TYPE",anchor="center",
            fg='white',font=self.tableFont,bg='DodgerBlue',bd=3,relief=RIDGE)
        self.typeH.grid(column=3,row=0,sticky="ew")
        
        self.agentH = Label(self.nameFrame,text="AGENT",anchor="center",
            fg='white',font=self.tableFont,bg='DodgerBlue',bd=3,relief=RIDGE)
        self.agentH.grid(column=4,row=0,sticky="ew")
        
        self.optionH = Label(self.nameFrame,text="OPTION",anchor="center",
            fg='white',font=self.tableFont,
bg='DodgerBlue',bd=3,relief=RIDGE)
        self.optionH.grid(column=5,row=0,sticky="ew")
        
        self.numberVars = []
        self.numberLabels = []        
        self.nameVars = []
        self.nameLabels = []        
        self.ipVars = []
        self.ipLabels = []        
        self.typeVars = []
        self.typeLabels = []
        self.agentVars = []
        self.agentLabels = []
        self.clientOptions = []
        self.clientOptionsVars = []
        
        ii = 1
        while ii <= self.maxTrader:
            self.clientOptionsVars.append(StringVar())
            self.clientOptionsVars[ii-1].set('NONE')
            self.clientOptions.append(OptionMenu(self.nameFrame,self.clientOptionsVars[ii-1],"ALL","BID","NAME","NONE"))
            self.clientOptions[ii-1].grid(column=5,row=ii,sticky="ew")
            self.clientOptions[ii-1].config(bg = 'PowderBlue',bd=2,relief=RIDGE)
            
            self.numberVars.append(StringVar())
            self.numberVars[ii-1].set('')
            self.numberLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.numberVars[ii-1]))
            self.numberLabels[ii-1].grid(column = 0,row=ii,sticky="ew")
            self.nameVars.append(StringVar())
            self.nameVars[ii-1].set('')
            self.nameLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.nameVars[ii-1]))
            self.nameLabels[ii-1].grid(column = 1,row=ii,sticky="ew")
            self.ipVars.append(StringVar())
            self.ipVars[ii-1].set('')
            self.ipLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.ipVars[ii-1]))
            self.ipLabels[ii-1].grid(column = 2,row=ii,sticky="ew")
            self.typeVars.append(StringVar())
            self.typeVars[ii-1].set('')
            self.typeLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.typeVars[ii-1]))
            self.typeLabels[ii-1].grid(column = 3,row=ii,sticky="ew")
            self.agentVars.append(StringVar())
            self.agentVars[ii-1].set('')
            self.agentLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.agentVars[ii-1]))
            self.agentLabels[ii-1].grid(column = 4,row=ii,sticky="ew")
            ii += 1
     
    #-method that searches the Agents folder and populates the serverClientagent
    #options menu list   
    def market_shock(self):
        range1 = (135, 140, self.MyFactory.schedule_offsetfn)
        supply_schedule = [ {'from':self.MyFactory.start_time, 'to':self.MyFactory.end_time, 'ranges':[range1], 'stepmode':'fixed'}]
        
        range1 = (190, 200, self.MyFactory.schedule_offsetfn)
        demand_schedule = [ {'from':self.MyFactory.start_time, 'to':self.MyFactory.end_time, 'ranges':[range1], 'stepmode':'fixed'}]
        
        self.MyFactory.order_schedule = {'sup':supply_schedule, 'dem':demand_schedule,
                       'interval':int(self.orderIntervalVar.get()), 'timemode':self.distributionVar.get()}
    def get_auto_agents(self):
        files = os.listdir('./Agents')#gets all files within the Agents folder 
        agent_list = [] #initializez the list of desired file names            
        for element in files: # loops through every file in the folder         
            if element.endswith('.py'): #check if it is a source file          
                agent_list.append(element.split('.')[0]) #adds the name of the file to the list       
        self.serverClientAgent["menu"].delete(0,END) #clears the existing elements in the option menu list
        i = 0
        while i < len(agent_list):#loops through all found agent names
            self.serverClientAgent["menu"].add_command(label=agent_list[i],command=lambda temp = agent_list[i]: self.serverClientAgent.setvar(self.serverClientAgent.cget("textvariable"), value = temp)) #popuates the option menu list with the found agent names
            i += 1
    
    #-method that adds a new server client for one session                     
    def addServerClients(self):
        #-gets the fake name for the server client                             
        #name = self.MyFactory.get_random_element(self.MyFactory.server_firstNames) + ' ' + self.MyFactory.get_random_element(self.MyFactory.server_Names)
        name = "agent"+str(len(self.MyFactory.serverClients))
        ip_address = 'server' #gets the fake ip for the server client
        agent = self.serverClientAgentVar.get() #gets the type of trader from the dropdown list       
        type = self.serverClientTypeVar.get() #gets the bid type from the dropdown list
        if len(self.MyFactory.serverClients) + len(self.MyFactory.clients) < self.maxTrader: #checks if the number of traders does not exceed the maximum number allowed for the session
            self.MyFactory.serverClients.append(name+':'+ip_address+':'+type+':'+agent) #appends the new server client
                       
    #-deletes the clients that are stored on the server - automated ones,      
    #removes them from GUI and memory                                          
    def clearServerClients(self):
        del self.MyFactory.serverClients[:] #deletes clients from memory       
        ii = 0
        while ii < self.maxTrader:#refreshes the GUI by setting the textvariable to an empty string
            self.numberVars[ii].set('')
            self.nameVars[ii].set('')
            self.ipVars[ii].set('')
            self.typeVars[ii].set('')
            self.agentVars[ii].set('')
            ii += 1
            
    def startSession(self):        
        self.startBtn.grid_forget()
        self.startBtn = Button(self.menuFrame,text="STOP SESSION",bg = self.buttoncolor,command = self.stopSession)
        self.startBtn.grid(column=0,row=10,columnspan=2,sticky='ew')        
        self.MyFactory.startSession(self.timeSpan)
    
    #-method called by the stop button that terminates the market session and 
    #refreshes the GUI
    def stopSession(self):
        self.startBtn.grid_forget()
        self.startBtn = Button(self.menuFrame,text="START SESSION",bg = self.buttoncolor,command=self.startSession)
        self.startBtn.grid(column=0,row=10,columnspan=2,sticky='ew')
        self.MyFactory.session.stop()
        self.MyFactory.status = 'Stopped'

        self.timeVar.set(str(self.timeSpan) + " seconds")
        
        if self.MyFactory.sessionID != None:
            self.cancelHosting()
        for client in self.MyFactory.client_addr:
                action = 'goodbye'
                msg = {'action':action}
                client.transport.write(json.dumps(msg))
        
    def enterTraders(self,event): 
        self.nrH.grid_forget()
        self.nameH.grid_forget()
        self.ipH.grid_forget()
        self.typeH.grid_forget()
        self.agentH.grid_forget()
        self.profitFrame.pack_forget()
        self.profitContFrame.pack_forget()
        self.NRPH.grid_forget()
        self.IDH.grid_forget()
        self.profitH.grid_forget()
        self.typePH.grid_forget()
        self.agentPH.grid_forget()
        self.optionH.grid_forget()
        self.profitTitleLabel.grid_forget()
        i = 0
        while i < self.maxTrader:
            
            self.numberLabels[i].grid_forget()
            self.clientOptions[i].grid_forget()
            self.nameLabels[i].grid_forget()
            self.ipLabels[i].grid_forget()
            self.typeLabels[i].grid_forget()
            self.agentLabels[i].grid_forget()
            self.nrProfitLabels[i].grid_forget()
            self.idProfitLabels[i].grid_forget()
            self.profitProfitLabels[i].grid_forget()
            self.typeProfitLabels[i].grid_forget()
            self.agentProfitLabels[i].grid_forget()
            i += 1
        
        self.maxTrader = int(self.traderEntry.get())       
            
        self.nrH = Label(self.nameFrame,text="NR",anchor="center",
            fg='white',bd=3,font=self.tableFont,bg='DodgerBlue',relief=RIDGE)
        self.nrH.grid(column=0,row=0,sticky="ew")
        self.nameH = Label(self.nameFrame,text="TRADERS",anchor="center",
            fg='white',bd=3,font=self.tableFont,bg='DodgerBlue',relief=RIDGE)
        self.nameH.grid(column=1,row=0,sticky="ew")
        
        self.ipH = Label(self.nameFrame,text="IPs",anchor="center",
            fg='white',bd=3,font=self.tableFont,bg='DodgerBlue',relief=RIDGE)
        self.ipH.grid(column=2,row=0,sticky="ew")
        
        self.typeH = Label(self.nameFrame,text="TYPE",anchor="center",
            fg='white',bd=3,font=self.tableFont,bg='DodgerBlue',relief=RIDGE)
        self.typeH.grid(column=3,row=0,sticky="ew")
        
        self.agentH = Label(self.nameFrame,text="AGENT",anchor="center",
            fg='white',bd=3,font=self.tableFont,bg='DodgerBlue',relief=RIDGE)        
        self.agentH.grid(column=4,row=0,sticky="ew")
        
        self.optionH = Label(self.nameFrame,text="OPTION",anchor="center",
            fg='white',font=self.tableFont,bg='DodgerBlue',bd=3,relief=RIDGE)
        self.optionH.grid(column=5,row=0,sticky="ew")
        
        self.numberVars = []
        self.numberLabels = []        
        self.nameVars = []
        self.nameLabels = []        
        self.ipVars = []
        self.ipLabels = []        
        self.typeVars = []
        self.typeLabels = []
        self.agentVars = []
        self.agentLabels = []
        self.clientOptions = []
        self.clientOptionsVars = []        
        ii = 1
        while ii <= self.maxTrader:
            self.clientOptionsVars.append(StringVar())
            self.clientOptionsVars[ii-1].set('NONE')
            self.clientOptions.append(OptionMenu(self.nameFrame,self.clientOptionsVars[ii-1],"ALL","BID","NAME","NONE"))
            self.clientOptions[ii-1].grid(column=5,row=ii,sticky="ew")
            self.clientOptions[ii-1].config(bg = 'PowderBlue',bd=2,relief=RIDGE)
            
            self.numberVars.append(StringVar())
            self.numberVars[ii-1].set('')
            self.numberLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.numberVars[ii-1]))
            self.numberLabels[ii-1].grid(column = 0,row=ii,sticky="ew")
            self.nameVars.append(StringVar())
            self.nameVars[ii-1].set('')
            self.nameLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.nameVars[ii-1]))
            self.nameLabels[ii-1].grid(column = 1,row=ii,sticky="ew")
            self.ipVars.append(StringVar())
            self.ipVars[ii-1].set('')
            self.ipLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.ipVars[ii-1]))
            self.ipLabels[ii-1].grid(column = 2,row=ii,sticky="ew")
            self.typeVars.append(StringVar())
            self.typeVars[ii-1].set('')
            self.typeLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.typeVars[ii-1]))
            self.typeLabels[ii-1].grid(column = 3,row=ii,sticky="ew")
            self.agentVars.append(StringVar())
            self.agentVars[ii-1].set('')
            self.agentLabels.append(Label(self.nameFrame,bd=3,bg='PowderBlue',relief=RIDGE,
                    font = self.cellsFont,textvar = self.agentVars[ii-1]))
            self.agentLabels[ii-1].grid(column = 4,row=ii,sticky="ew")
            ii += 1
        
        self.profitFrame = Frame(self.sesCont,bd=3,bg = self.color,relief=RIDGE)
        self.profitFrame.pack(side=TOP,padx=5,pady=5,fill=X)
        
        self.profitContFrame = Frame(self.profitFrame,bg=self.color)
        self.profitContFrame.pack(side=TOP,padx=5,pady=5)
        
        self.profitTitleLabel = Label(self.profitContFrame,text="Profits",bg=self.color,font=self.headerFont)
        self.profitTitleLabel.grid(column=0,row=0,columnspan=7,sticky="ew")
        
        self.NRPH = Label(self.profitContFrame,text="NR",bd=3,
            relief=RIDGE,bg="Black",fg="white",font=self.tableFont)
        self.NRPH.grid(column=0,row=1,sticky="ew")
        
        self.IDH = Label(self.profitContFrame,text="NAME",bd=3,
            relief=RIDGE,bg="Black",fg="white",font=self.tableFont)
        self.IDH.grid(column=1,row=1,sticky="ew")
        
        self.profitH = Label(self.profitContFrame,text="PROFIT",bd=3,
            relief=RIDGE,bg="Black",fg="white",font=self.tableFont)
        self.profitH.grid(column=2,row=1,sticky="ew")
        
        self.typePH = Label(self.profitContFrame,text="TYPE",bd=3,
            relief=RIDGE,bg="Black",fg="white",font=self.tableFont)
        self.typePH.grid(column=3,row=1,sticky="ew")
        
        self.agentPH = Label(self.profitContFrame,text="AGENT",bd=3,
            relief=RIDGE,bg="Black",fg="white",font=self.tableFont)
        self.agentPH.grid(column=4,row=1,sticky="ew")

        self.maxProfitPH = Label(self.profitContFrame,text="MAX PROFIT",bd=3,
            relief=RIDGE,bg="Black",fg="white",font=self.tableFont)
        self.maxProfitPH.grid(column=5,row=1,sticky="ew")

        self.allocPH = Label(self.profitContFrame,text="EFFICIENCY",bd=3,
            relief=RIDGE,bg="Black",fg="white",font=self.tableFont)
        self.allocPH.grid(column=6,row=1,sticky="ew")
        
        self.nrProfitVar = []
        self.nrProfitLabels = []        
        self.idProfitVar = []
        self.idProfitLabels = []        
        self.profitProfitVar = []
        self.profitProfitLabels = []        
        self.typeProfitVar = []
        self.typeProfitLabels = []        
        self.agentProfitVar=[]
        self.agentProfitLabels=[]
        self.maxProfitVar = []
        self.maxProfitLabels = []
        self.allocProfitVar=[]
        self.allocProfitLabels=[]
        self.maxProfitVar=[]
        self.maxProfitLabels=[]

        self.allocVar=[]
        self.allocLabels=[]
        
        ii = 0
        while ii < self.maxTrader:
            self.nrProfitVar.append(StringVar())
            self.nrProfitVar[ii].set('')
            self.nrProfitLabels.append(Label(self.profitContFrame,textvar = self.nrProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.nrProfitLabels[ii].grid(column=0,row=ii+2,sticky="ew")
            self.idProfitVar.append(StringVar())
            self.idProfitVar[ii].set('')
            self.idProfitLabels.append(Label(self.profitContFrame,textvar = self.idProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.idProfitLabels[ii].grid(column=1,row=ii+2,sticky="ew")
            self.profitProfitVar.append(StringVar())
            self.profitProfitVar[ii].set('')
            self.profitProfitLabels.append(Label(self.profitContFrame,textvar = self.profitProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.profitProfitLabels[ii].grid(column=2,row=ii+2,sticky="ew")
            self.typeProfitVar.append(StringVar())
            self.typeProfitVar[ii].set('')
            self.typeProfitLabels.append(Label(self.profitContFrame,textvar = self.typeProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.typeProfitLabels[ii].grid(column=3,row=ii+2,sticky="ew")
            self.agentProfitVar.append(StringVar())
            self.agentProfitVar[ii].set('')
            self.agentProfitLabels.append(Label(self.profitContFrame,textvar = self.agentProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.agentProfitLabels[ii].grid(column=4,row=ii+2,sticky="ew")
            self.maxProfitVar.append(StringVar())
            self.maxProfitVar[ii].set('')
            self.maxProfitLabels.append(Label(self.profitContFrame,textvar = self.maxProfitVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.maxProfitLabels[ii].grid(column=5,row=ii+2,sticky="ew")
            self.allocVar.append(StringVar())
            self.allocVar[ii].set('')
            self.allocLabels.append(Label(self.profitContFrame,textvar = self.allocVar[ii],
                bg='Dark Grey',bd=3,relief=RIDGE))
            self.allocLabels[ii].grid(column=6,row=ii+2,sticky="ew")
            ii += 1    
    #==========================================================================
    #-method that gets called once <Return> is pressed on the ENTRY that takes a 
    #number of seconds as a variable
    #-represents the length of the session
    #-refreshes the GUI so that the user can acknowledge that his input has been 
    #received by the application
    def enterInterval(self,event):
        self.timeSpan = int(self.entry.get())
        self.MyFactory.end_time = float(self.timeSpan)
        self.timeVar.set(self.entry.get() + " seconds")
        
    #==========================================================================
    #-method that is called once a market session has been succesfully ended
    #-refreshes the GUI
    def endSession(self):
        self.startBtn.grid_forget()
        self.startBtn = Button(self.menuFrame,text="START SESSION",bg = self.buttoncolor,command=self.startSession)
        self.startBtn.grid(column=0,row=10,columnspan=2,sticky="ew")
        self.timeVar.set(str(self.timeSpan) + " seconds")
        
    #==========================================================================
    #-method that draws the title and logo on the main window
    def addTitle(self):        
        self.logo = Label(self.mainFrame,image=self.brisImg,anchor="center",bg=self.framecolor)
        self.logo.image = self.brisImg
        self.logo.grid(column=0,row=0,columnspan=2)
        self.titleLabel = Label(self.mainFrame,text="Bristol Stock Exchange",bg=self.framecolor,
            font=self.headerFont, anchor="center")
        self.titleLabel.grid(column=0,row=1,columnspan=2)
    #==========================================================================
    #-method that initializez the frame responsible for drawing past sessions
    #statistics from the MongoDB database
    def past_sessions(self):
        self.dbSess = Frame(self.mainCont,bd=3, relief=RIDGE, bg=self.color)
        self.dbSess.pack(side=LEFT,fill=BOTH,padx=10,pady=10)        
        
        self.dbBlotterFrame = Frame(self.dbSess,bg=self.color)
        self.dbBlotterFrame.grid(column=0,columnspan=4,row=5,padx=5,pady=5,sticky='ew')
        
        self.dbTitle = Label(self.dbSess,bd=2,relief=RIDGE,bg=self.color,text="PAST SESSIONS",font=self.headerFont)
        self.dbTitle.grid(column=0,row=0,columnspan=4,sticky='ew')
        
        self.dbUser = Label(self.dbSess,bd=2,relief=RIDGE,bg=self.color,text="Username:")
        self.dbUser.grid(column=0,row=1,sticky='ew')
        
        self.dbUsername = Entry(self.dbSess,relief=RIDGE,bd=2)
        self.dbUsername.grid(column=1,row=1,columnspan=3,sticky="ew")
        
        self.dbPass = Label(self.dbSess,bd=2,relief=RIDGE,bg=self.color,text="Password:")
        self.dbPass.grid(column=0,row=2,sticky='ew')
        
        self.dbPassword = Entry(self.dbSess,show="*",bd=2,relief=RIDGE)
        self.dbPassword.grid(column=1,row=2,columnspan=3,sticky="ew")
        
        self.dbConnectBtn = Button(self.dbSess,text='Connect',bg = self.buttoncolor,command=self.connectDatabase)
        self.dbConnectBtn.grid(column=0,columnspan = 4,row=3,sticky='ew')  

        self.dbDisconnectBtn = Button(self.dbSess,text='Disconnect',bg = self.buttoncolor,command = self.disconnectDatabase)      
        self.dbDisconnectBtn.grid(column=0,columnspan = 4, row = 4, sticky = 'ew')
        
    def disconnectDatabase(self):
        if self.MyFactory.dbConnectionStatus == 'CONNECTED':
            self.MyFactory.connection.close()
            self.dbBlotterFrame.grid_forget()
            self.queryBtn.grid_forget()
            self.deleteSessionBtn.grid_forget()
            self.exportSBtn.grid_forget()
            self.pastSessions.grid_forget()
            try:
                self.marketOvw.grid_forget()
                self.dbTraders.grid_forget()
                self.blotterBtn.grid_forget()                
            except:
                x = 'done'

    def connectDatabase(self):
        self.MyFactory.username = self.dbUsername.get()
        password = self.dbPassword.get()        
        self.dbPassword.delete(0,END)
        #======================================================================
        #-opens a database connection that contains the collections specific for BSE
        try:
            self.MyFactory.connection = MongoClient(host='mongodb://'+self.MyFactory.username+':'+password+'@ds037987.mongolab.com:37987/bse') #opens a database connection using MongoDB
            self.MyFactory.BSE_DB = self.MyFactory.connection.bse # returns the BSE database           
            self.MyFactory.fs = gridfs.GridFS(self.MyFactory.BSE_DB)
            self.MyFactory.dbConnectionStatus = 'CONNECTED'
                    
            self.pastSessionsVar = StringVar()
            self.pastSessionsVar.set('NO PAST SESSIONS')
            self.pastSessions = OptionMenu(self.dbSess,self.pastSessionsVar,'NO PAST SESSIONS')
            self.pastSessions.config(bg = self.buttoncolor,bd=2,relief=RIDGE)
            self.pastSessions.grid(column=0,row=5,sticky='ew')
            
            user_sessions = self.MyFactory.BSE_DB[self.MyFactory.username].find()
            self.pastSessions["menu"].delete(0,END)
            if user_sessions.count() > 0:
                self.pastSessionsVar.set(user_sessions[0]['index'])
                for element in user_sessions:                        
                    self.pastSessions["menu"].add_command(label=element['index'],command=lambda temp = element['index']: self.pastSessions.setvar(self.pastSessions.cget("textvariable"), value = temp))
                    
            self.queryBtn = Button(self.dbSess,text='QUERY',bg = self.buttoncolor,command=self.query)
            self.queryBtn.grid(column=1,row=5,sticky='ew')
            
            self.deleteSessionBtn = Button(self.dbSess,text='DELETE',bg = self.buttoncolor,command=self.deleteSession)
            self.deleteSessionBtn.grid(column=2,row=5,sticky='ew')
            self.exportSBtn = Button(self.dbSess,text='Export',bg = self.buttoncolor,command=self.exportSession)
            self.exportSBtn.grid(column=3,row=5,sticky='ew')
        except Exception:
            print sys.exc_info()[0]
            
    def deleteSession(self):
        index = self.pastSessionsVar.get()
        
        session_collection = self.MyFactory.BSE_DB[self.MyFactory.username+'_'+index]
        for element in session_collection.find():
            file_id = self.MyFactory.BSE_DB.fs.files.find({'filename':element['image']})[0]['_id']
            print file_id,element['image'],'========>deleted'
            self.MyFactory.BSE_DB.fs.chunks.remove({'files_id':file_id});
            self.MyFactory.BSE_DB.fs.files.remove({'_id':file_id})
        session_collection.drop()
        
        marketImg =  self.MyFactory.BSE_DB[self.MyFactory.username].find({'index':index})[0]['image']
        file_id = self.MyFactory.BSE_DB.fs.files.find({'filename':marketImg})[0]['_id']
        self.MyFactory.BSE_DB.fs.chunks.remove({'files_id':file_id});
        self.MyFactory.BSE_DB.fs.files.remove({'_id':file_id})
        print file_id, marketImg,'========>deleted'        
        self.MyFactory.BSE_DB[self.MyFactory.username].remove({'index':index})
        try:
            self.marketOvw.grid_forget()
            self.dbTraders.grid_forget()
            self.blotterBtn.grid_forget()
        except:
            print 'No initial query performed'
        
        user_sessions = self.MyFactory.BSE_DB[self.MyFactory.username].find()
        self.pastSessionsVar.set('NO PAST SESSIONS')
        self.pastSessions["menu"].delete(0,END)
        if user_sessions.count() > 0:
                self.pastSessionsVar.set(user_sessions[0]['index'])
                for element in user_sessions:                        
                    self.pastSessions["menu"].add_command(label=element['index'],
                        command=lambda temp = element['index']: self.pastSessions.setvar(self.pastSessions.cget("textvariable"), value = temp))
        
        self.dbBlotterFrame.grid_forget()
    #==========================================================================
    #-gets called when the Query button is pressed and shows information about 
    #one particula past market session, draws the frame and populates the dropdown 
    #list with the names of the traders that have participated during that session    
    def query(self):
        if self.pastSessionsVar.get() != 'NO PAST SESSIONS':
            #path = self.MyFactory.sessions_collection.find({'index':self.pastSessionsVar.get()})[0]['market_plot_path']
            image_name = self.MyFactory.BSE_DB[self.MyFactory.username].find({'index':self.pastSessionsVar.get()})[0]['image']
            image = self.MyFactory.fs.get_last_version(filename = image_name).read() 

            outfilename = "Data/temp1.png"
            output= open(outfilename,"w")
     
            output.write(image)            
            output.close()

            marketImg = ImageTk.PhotoImage(Image.open(outfilename).resize((800,600),Image.ANTIALIAS))        
            self.marketOvw = Label(self.dbSess,bd=3,relief=RIDGE,image=marketImg,anchor="center",bg='white')
            self.marketOvw.image = marketImg
            self.marketOvw.grid(column=0,row = 6,columnspan = 4,sticky='ew')
            os.remove(outfilename)
            
            traders = self.MyFactory.BSE_DB[self.MyFactory.username+"_"+self.pastSessionsVar.get()].find()
            
            self.dbTradersVar = StringVar()
            self.dbTradersVar.set(traders[0]['name'])
            self.dbTraders = OptionMenu(self.dbSess,self.dbTradersVar,'No TRADERS')
            self.dbTraders.config(bg = self.buttoncolor,bd=2,relief=RIDGE)
            self.dbTraders.grid(column=0,row=7,columnspan=4,sticky='ew')
            
            self.dbTraders["menu"].delete(0,END)
            for element in traders: #populates the dropdown with the names of the traders
                self.dbTraders["menu"].add_command(label=element['name'],command=lambda temp = element['name']: self.dbTraders.setvar(self.dbTraders.cget("textvariable"), value = temp))
            
            self.blotterBtn = Button(self.dbSess,text='DETAILS',bg=self.buttoncolor,command=self.dbBlotter)
            self.blotterBtn.grid(column=0,row=8,columnspan=4,sticky='ew')
    #==========================================================================
    #-gets called when the blotter button is pressed for a trader, whose info is stored in the 
    #database
    #-draws the frame and graph for the trader
    def dbBlotter(self):
        self.dbBlotterFrame.grid_forget()
        self.dbBlotterFrame = Frame(self.dbSess,bg=self.color)
        self.dbBlotterFrame.grid(column=0,columnspan=4,row=9,padx=5,pady=5,sticky='ew')
        
        trader = self.MyFactory.BSE_DB[self.MyFactory.username+"_"+self.pastSessionsVar.get()].find({'name':self.dbTradersVar.get()})[0] 
        
        image_name = trader['image']                
        image = self.MyFactory.fs.get_last_version(filename = image_name).read()
         
        outfilename = "Data/temp1.png"
        output= open(outfilename,"w")     
        output.write(image)            
        output.close()


        traderImg = ImageTk.PhotoImage(Image.open(outfilename).resize((800,600),Image.ANTIALIAS))        
        traderOvw = Label(self.dbBlotterFrame,bd=3,relief=RIDGE,image=traderImg,anchor="center",bg='white')
        traderOvw.image = traderImg
        traderOvw.grid(column=0,row=0,columnspan=11,sticky='ew')
        os.remove(outfilename)
        
        BLOTTER = Label(self.dbBlotterFrame,text='BLOTTER',bg='black',fg='white',bd=3,relief=RIDGE)
        BLOTTER.grid(column=0,columnspan=7,row=1,sticky='ew')
        
        DETAILS = Label(self.dbBlotterFrame,text='DETAILS',bg='black',fg='white',bd=3,relief=RIDGE)
        DETAILS.grid(column=5,columnspan=6,row=1,sticky='ew')
        
        CPTY = Label(self.dbBlotterFrame,text='PARTY2',bg='black',fg='white',bd=3,relief=RIDGE)
        CPTY.grid(column=0,row=2,sticky='ew')
        
        PRICE = Label(self.dbBlotterFrame,text='PRICE',bg='black',fg='white',bd=3,relief=RIDGE)
        PRICE.grid(column=1,row=2,sticky='ew')
        
        TIME = Label(self.dbBlotterFrame,text='TIME',bg='black',fg='white',bd=3,relief=RIDGE)
        TIME.grid(column=2,row=2,sticky='ew')
        
        QUANTITY = Label(self.dbBlotterFrame,text='QUANTITY',bg='black',fg='white',bd=3,relief=RIDGE)
        QUANTITY.grid(column=3,row=2,sticky='ew')       
        
        PARTY1 = Label(self.dbBlotterFrame,text='PARTY1',bg='black',fg='white',bd=3,relief=RIDGE)
        PARTY1.grid(column=3,row=2,sticky='ew')  
        
        SPACE = Label(self.dbBlotterFrame,text='===',bg='black',bd=3,relief=RIDGE)
        SPACE.grid(column=4,row=2,sticky='ew')  
        
        BID = Label(self.dbBlotterFrame,text='BID',bg='black',fg='white',bd=3,relief=RIDGE)
        BID.grid(column=5,row=2,sticky='ew')  
        
        BALANCE = Label(self.dbBlotterFrame,text='BALANCE',bg='black',fg='white',bd=3,relief=RIDGE)
        BALANCE.grid(column=6,row=2,sticky='ew')  
        
        TYPE = Label(self.dbBlotterFrame,text='TYPE',fg='white',bg='black',bd=3,relief=RIDGE)
        TYPE.grid(column=7,row=2,sticky='ew')                 

        MAX_PROF = Label(self.dbBlotterFrame,text='MAX PROFIT',fg='white',bg='black',bd=3,relief=RIDGE)
        MAX_PROF.grid(column=8,row=2,sticky='ew')

        ALLOC_EFF = Label(self.dbBlotterFrame,text='ALLOC EFF',fg='white',bg='black',bd=3,relief=RIDGE)
        ALLOC_EFF.grid(column=9,row=2,sticky='ew')
        
        SMITH_ALPHA = Label(self.dbBlotterFrame,text='SMITH ALPHA',fg='white',bg='black',bd=3,relief=RIDGE)
        SMITH_ALPHA.grid(column=10,row=2,sticky='ew')
        
        row = 3
        for trade in trader['blotter']:
            cpty = Label(self.dbBlotterFrame,text=trade['party2'],bg='white',bd=3,relief=RIDGE)
            cpty.grid(column=0,row=row,sticky='ew')
            
            price = Label(self.dbBlotterFrame,text=trade['price'],bg='white',bd=3,relief=RIDGE)
            price.grid(column=1,row=row,sticky='ew')             
            
            time =  Label(self.dbBlotterFrame,text=trade['time'],bg='white',bd=3,relief=RIDGE)
            time.grid(column=2,row=row,sticky='ew')             
            
            qty =  Label(self.dbBlotterFrame,text=trade['qty'],bg='white',bd=3,relief=RIDGE)
            qty.grid(column=3,row=row,sticky='ew')             
            
            pty1 =  Label(self.dbBlotterFrame,text=trade['party1'],bg='white',bd=3,relief=RIDGE)
            pty1.grid(column=3,row=row,sticky='ew')   
            
            space = Label(self.dbBlotterFrame,text='===',bg='black',bd=3,relief=RIDGE)
            space.grid(column=4,row=row,sticky='ew')            
            
            row += 1
        bid = Label(self.dbBlotterFrame,text=trader['bid'],bg='red',fg='white',bd=3,relief=RIDGE)
        bid.grid(column=5,row=3,sticky='ew')
        
        balance = Label(self.dbBlotterFrame,text=trader['balance'],bg='red',fg='white',bd=3,relief=RIDGE)
        balance.grid(column=6,row=3,sticky='ew')
        
        type = Label(self.dbBlotterFrame,text=trader['type'],bg='red',fg='white',bd=3,relief=RIDGE)
        type.grid(column=7,row=3,sticky='ew')
        try:
            max = Label(self.dbBlotterFrame,text=trader['maxProfit'],bg='red',fg='white',bd=3,relief=RIDGE)
            max.grid(column=8,row=3,sticky='ew')

            alloc = Label(self.dbBlotterFrame,text=trader['allocEff'],bg='red',fg='white',bd=3,relief=RIDGE)
            alloc.grid(column=9,row=3,sticky='ew')        
       
            smith = Label(self.dbBlotterFrame,text=trader['alpha'],bg='red',fg='white',bd=3,relief=RIDGE)
            smith.grid(column=10,row=3,sticky='ew')
        except:
            print 'Older version'
        
        export = Button(self.dbBlotterFrame,text='Export',bg=self.buttoncolor,command=self.exportFile)
        export.grid(column=5,row=4,sticky='ew',columnspan=6)
        
    def exportFile(self):
        trader = self.MyFactory.BSE_DB[self.MyFactory.username+"_"+self.pastSessionsVar.get()].find({'name':self.dbTradersVar.get()})[0] 
        c = csv.writer(open('Data/'+self.pastSessionsVar.get()+'_'+trader['name']+".csv", "wb"))
        self.export(trader,c)
    
    def exportSession(self):
        cursor = self.MyFactory.BSE_DB[self.MyFactory.username+"_"+self.pastSessionsVar.get()].find()
        c = csv.writer(open('Data/'+self.pastSessionsVar.get()+".csv", "wb"))
        for elem in cursor:
            self.export(elem,c)
    
    def export(self,trader,c):
        
        c.writerow([' ',' ',trader['name'],' ',' '])
        c.writerow(['PARTY2','PRICE','TIME','PARTY1','QUANTITY'])
        for trade in trader['blotter']:
            c.writerow([trade['party2'],trade['price'],trade['time'],trade['party1'],trade['qty']])
        c.writerow([' ',' ',' ',' ',' ',' '])
        
        c.writerow(['BID','BALANCE','TYPE','MAX PROFIT','ALLOC EFF','SMITH ALPHA'])
        try:
            c.writerow([trader['bid'],trader['balance'],trader['type'],trader['maxProfit'],trader['allocEff'],trader['alpha']])
        except:
            c.writerow([trader['bid'],trader['balance'],trader['type']])
        c.writerow([' ',' ',' ',' ',' ',' '])
        c.writerow([' ',' ',' ',' ',' ',' '])
        c.writerow([' ',' ',' ',' ',' ',' '])

        

#==============================================================================
#-communication protocol used in twisted                                       
#-twisted - event driven server-client communication protocol                  
#-contains standard functions that can be overriden: connectionMade, dataReceived,
#and connectionLost                                                            
class CmdProtocol(protocol.Protocol):
    #==========================================================================
    #-deprecated variables                                                     
    NAME = 'user'+ str(random.random())  
    #==========================================================================
    STATUS = 'ACCEPT' #-variable that maintains the current state of the server
    #-method that recognises a connection to the server from a client          
    def connectionMade(self):
        self.client_ip = self.transport.getPeer() #-gets the client ip
        #=====================================================================
        #-checks if the new connection is within the allowed number of connections
        #allowed by the server                                                 
        if len(self.factory.clients) + len(self.factory.serverClients) >= self.factory.ui.maxTrader:            
            self.transport.loseConnection()
            self.STATUS = 'REJECT'
        else:
            self.STATUS = 'ACCEPT'
            self.factory.clients[self.formatIP(self.client_ip)] = self.NAME 
            self.factory.client_addr.append(self)
                                                
    def dataReceived(self, data):        
        ip  = self.formatIP(self.client_ip) #-formats the ip into a string used in the hash map
        message = json.loads(data)        
        if message['action'] == 'login':
            name = message['name']
            bid = message['bid']
            stgy = message = ['stgy']            
            self.factory.clients[ip] = [name,bid,'Human'] 
        elif message['action'] == 'bid':                           
            quoteprice =  float(message['bid'])            
            tname  = self.factory.clients[ip][0]
            print tname,quoteprice
            try:
                self.factory.traders[tname].humanInput = quoteprice                           
            except:
                pass
                
    def connectionLost(self, reason):
        ip = self.formatIP(self.client_ip)
        #-check that makes sure that the removed client is indeed allowed to be
        #in the trader list                                                    
        if self.STATUS == 'ACCEPT':
            self.factory.client_addr.remove(self)
            del self.factory.clients[ip] 
        ii = 0
        #-updates the gui to show the remaining traders
        while ii < self.factory.ui.maxTrader:
            self.factory.ui.numberVars[ii].set('')
            self.factory.ui.nameVars[ii].set('')
            self.factory.ui.ipVars[ii].set('')
            self.factory.ui.typeVars[ii].set('')
            self.factory.ui.agentVars[ii].set('')
            ii += 1 
                   
    #-creates a string of the ip data type from the twisted server used as a key
    #in the hash map containing all traders                                    
    def formatIP(self,object):
        text =  str(object).split()
        return text[1][1:len(text[1])-2]
    
#==============================================================================
#-class that manipulates the command protocol and contains the logic of the    
#server side                                                                   
#-manipulates the GUI and populates the market and interpretes orders and      
#performs trades                                                               
#-sends updates to the clients that are connected to the server                
class MyFactory(ServerFactory): 
    protocol = CmdProtocol #initialize command protocol                        
    def __init__(self, clients_max,interval,ui):
        #-random ips to hide true location of server agents
        self.dbConnectionStatus = 'NOT CONNECTED'
        #======================================================================
        self.clients_max = clients_max #initializez maximum number of allowed clients
        self.ui = ui #initializez the ui class for the application             
        self.clients = {} #the connected clients info                          
        self.client_names = 'traders' #initialize message to be sent to clients
        self.client_addr = [] #list that contains the clients addresses where to send messages
        self.serverClients = [] #list containing the traders contained on the server (automated)
        self.cloudClients = []
        #======================================================================
        #-looping call functions calls the traders function every 3 seconds    
        self.status = 'Stopped' 
        self.sessionID = None
        self.lc = task.LoopingCall(self.traders) 
        self.lc.start(3)   
        #======================================================================
        self.interval = interval #market session default interval              
        #-logic data required for each session                                 
        self.traders = {} #trading agents for the current session              
        self.trader_stats = {} #statistics for each trader                     
        self.start_time = 0.0 
        self.end_time = 20.0
        self.sess_id = 'trial'
        self.exchange = Exchange() #initializez the exchange class             
        self.pending_orders = [] #orders that are pending                      
        self.time = 0.0 #current time    
        self.eqPrices = []
        self.eqTimes = []  
        self.tLimitPrice = 200 
        self.lastTrade = None
        #====================================================================
        
                                    
    
    #-returns a random element from a list                                     
    def get_random_element(self,list):
        length = len(list)
        index = random.randrange(0,length)
        return list[index]
    
    def smith_alpha(self,blotter):
        alpha = 0.0
        eq_price = float(150)
        length = len(blotter)
        sum = 0.0
        for element in blotter:
            price = float(element['price'])
            sum += (price - eq_price) * (price - eq_price)
        try:        
            alpha = math.sqrt(sum / length) / eq_price    
        except:
            alpha = None
        return alpha;
    #-method that checks if a session has terminated, gets called in a looping 
    #call every second                                                         
    def checkSession(self):          
        self.ui.timeVar.set(str(int(self.end_time - self.time))+ " seconds")        
        if self.time > self.end_time:
            
            self.session.stop()
            self.ui.endSession()
            now = datetime.datetime.now()
            now = str(now.strftime("%Y-%m-%d-%H-%M"))
            newpath = 'Data/Session_'+now
            os.makedirs(newpath)            
            dbtraders = [] #-contains all the trader names to be stored in the db
            
            #-plotting the blotter for every trader HERE:                      
            #==================================================================
            for trader in self.traders:
                dbtraders.append(trader)
                trades = []
                tradeTimes = []
                for trade in  self.traders[trader].blotter:
                    trades.append(trade['price'])
                    tradeTimes.append(trade['time'])
                py.plot(tradeTimes,trades,marker='o', linestyle='-',label=trader + ' ' + self.traders[trader].ttype + ' ' + self.traders[trader].bidType)
                py.legend(loc=1,prop={'size':6})
                py.title('Trader Evolution')
                py.ylabel('Transaction price')        
                py.xlabel('Time (s)')
                py.savefig(newpath+'/blotter_'+trader+'_'+self.traders[trader].ttype+'_'+self.traders[trader].bidType+'.png') 

                filename = newpath+'/blotter_'+trader+'_'+self.traders[trader].ttype+'_'+self.traders[trader].bidType+'.png'
                datafile = open(filename,"r");
                thedata = datafile.read()
                if self.dbConnectionStatus == 'CONNECTED':
                	stored = self.fs.put(thedata, filename=now+'_'+trader+'_'+self.traders[trader].ttype+'_'+self.traders[trader].bidType+'.png')
                py.clf()               
                       
            
            #-market session plot  
            if self.dbConnectionStatus == 'CONNECTED':
                session_col = self.BSE_DB[self.username+"_"+now]
                
                
            trades = []
            for trader in self.traders:                
                trader_post = {'name':trader,
                                'type':self.traders[trader].ttype,
                                'bid':self.traders[trader].bidType,
                                'balance':self.traders[trader].balance,
                                'blotter':self.traders[trader].blotter,
                                'maxProfit':self.traders[trader].maxProfit,
                                'allocEff':self.traders[trader].allocEff,
                                'alpha':self.smith_alpha(self.traders[trader].blotter),
                                'image':now+'_'+trader+'_'+self.traders[trader].ttype+'_'+self.traders[trader].bidType+'.png'}
                if self.dbConnectionStatus == 'CONNECTED':
                        session_col.insert(trader_post)
                    #=================================
                    #=================================
                
                if self.traders[trader].bidType == 'BUY':
                    for trade in  self.traders[trader].blotter:
                        trades.append([trade['price'],trade['time']])
                                    
            
            sortedList = sorted(trades, key=lambda trade: trade[1])
            print sortedList
            prices = []
            times = []
            for element in sortedList:
                prices.append(element[0])
                times.append(element[1])
            py.plot(times,prices,marker='o',color='blue',label='Trades')            
            py.legend(loc=1,prop={'size':6})
            py.title('Market Evolution')
            py.ylabel('Transaction price')         
            py.xlabel('Time (s)')            
            py.savefig(newpath+'/market.png') 
            py.clf()

            filename = newpath+'/market.png'
            datafile = open(filename,"r");
            thedata = datafile.read()
            if self.dbConnectionStatus == 'CONNECTED':
            	stored = self.fs.put(thedata, filename=now+'_market.png')
            
            
            if self.dbConnectionStatus == 'CONNECTED':
                session_post = {}
                username_collection = self.BSE_DB[self.username] 
                session_post['index'] = now                
                session_post['image'] = now+'_market.png'                
                username_collection.insert(session_post)
                
            self.ui.timeVar.set(str(self.interval) + " seconds")
            if self.sessionID != None:
                self.ui.cancelHosting()
            for client in self.client_addr:
                action = 'goodbye'
                msg = {'action':action}
                client.transport.write(json.dumps(msg))
            
            if self.dbConnectionStatus == 'CONNECTED':
                user_sessions = session_col = self.BSE_DB[self.username].find()
                self.ui.pastSessions["menu"].delete(0,END)
                if user_sessions.count() > 0:
                    self.ui.pastSessionsVar.set(user_sessions[0]['index'])
                    for element in user_sessions:                        
                        self.ui.pastSessions["menu"].add_command(label=element['index'],command=lambda temp = element['index']: self.ui.pastSessions.setvar(self.ui.pastSessions.cget("textvariable"), value = temp))
        else:            
            self.market_session()
    
    def traders(self):
        ii = 0                
        while ii < self.ui.maxTrader:
            self.ui.numberVars[ii].set('')
            self.ui.nameVars[ii].set('')
            self.ui.ipVars[ii].set('')
            self.ui.typeVars[ii].set('')
            self.ui.agentVars[ii].set('')
            ii += 1
            
        self.client_names=[]
        ii = 0
        
        if self.sessionID != None:
            del self.cloudClients[:]
            action = "TRADERS"
            headers = {'Content-Type':'application/json'}
            post_data = {"action":action,"sessionID":self.sessionID}
            req = urllib2.Request(host+"server", json.dumps(post_data), headers)
            response = json.loads(urllib2.urlopen(req).read())['traders']
            for client in response:
                self.cloudClients.append(client[0])
                self.client_names.append([client[0],'cloud',client[1],'Human'])
                              
            
        for client in self.serverClients:
            self.client_names.append([client.split(':')[0],client.split(':')[1],client.split(':')[2],client.split(':')[3]])            
        for client in self.client_addr:
            clientIP = self.formatIP(client.client_ip)
            self.client_names.append([self.clients[clientIP][0],clientIP,
                                    self.clients[clientIP][1],self.clients[clientIP][2]])        
        aux_names = self.client_names
        
        cloud_traders = {}
        all_traders = []
        i = 1
        for name in self.client_names:
            trader = name[0]
            iptr = name[1]
            typetr = name[2]
            agentr = name[3]
            if agentr != 'Human':
                iptr = 'server'
            
            self.ui.numberVars[i-1].set(str(i))
            self.ui.nameVars[i-1].set(trader)
            self.ui.ipVars[i-1].set(iptr)
            self.ui.typeVars[i-1].set(typetr)
            self.ui.agentVars[i-1].set(agentr)                
            i += 1
                
        i = 0        
        for name in self.client_names:
            trader = name[0]
            iptr = name[1]
            typetr = name[2]
            agentr = name[3]
            if iptr == 'cloud':
                cloud_traders[trader] = self.ui.clientOptionsVars[i].get()
            all_traders.append([trader,iptr,typetr,agentr])
            i += 1
                
        if self.sessionID != None:
            action = "INFO"
            headers = {'Content-Type':'application/json'}
            post_data = {"action":action,"traders":cloud_traders,"sessionID":self.sessionID,'all':all_traders}
            req = urllib2.Request(host+"server", json.dumps(post_data), headers)
            response = json.loads(urllib2.urlopen(req).read())['status']
        
        self.ui.cnv.configure(scrollregion=(0, 0, self.ui.mainFrame.winfo_width(), self.ui.mainFrame.winfo_height()))
                
        ii = len(self.serverClients) + len(self.cloudClients)        
        for client in self.client_addr:
            if self.ui.clientOptionsVars[ii].get() == 'NONE':
                self.client_names = []
            elif self.ui.clientOptionsVars[ii].get() == 'NAME':
                self.client_names = []
                for sclient in self.serverClients:
                    self.client_names.append([sclient.split(':')[0],sclient.split(':')[1],'Unknown','Unknown'])
                for hclient in self.client_addr:
                    clientIP = self.formatIP(hclient.client_ip)
                    self.client_names.append([self.clients[clientIP][0],clientIP,':Unknown','Unknown'])
            elif self.ui.clientOptionsVars[ii].get() == 'BID':
                self.client_names = []
                for sclient in self.serverClients:
                    self.client_names.append([sclient.split(':')[0],sclient.split(':')[1],sclient.split(':')[2],':Unknown'])
                for hclient in self.client_addr:
                    clientIP = self.formatIP(hclient.client_ip)
                    self.client_names.append([self.clients[clientIP][0],clientIP,self.clients[clientIP][1],':Unknown'])
            
            ii += 1
            action = 'traders'
            msg = {'action':action,'traders':self.client_names}
            client.transport.write(json.dumps(msg))
            self.client_names = aux_names
    
    def startSession(self,interval):
        del self.eqPrices[:]
        del self.eqTimes[:]
        self.traders = None
        self.traders = {}
        self.trader_stats = None
        self.trader_stats = {}
        self.sess_id = 'trial'
        self.exchange = None
        self.status = 'Started'
        self.exchange = Exchange()
        del self.pending_orders[:]
        ii = 0
        while ii < self.ui.maxTrader:
                    self.ui.nrProfitVar[ii].set(' ')
                    self.ui.idProfitVar[ii].set(' ')
                    self.ui.profitProfitVar[ii].set(' ')
                    self.ui.typeProfitVar[ii].set(' ')
                    self.ui.agentProfitVar[ii].set(' ')
                    self.ui.maxProfitVar[ii].set(' ')
                    self.ui.allocVar[ii].set(' ')
                    ii += 1
        ii = 0
        while ii < 10:
            self.ui.bidQVars[ii].set(' ')
            self.ui.bidVars[ii].set(' ')
            self.ui.askVars[ii].set(' ')
            self.ui.askQVars[ii].set(' ')
            ii += 1
        
        range1 = (100, 100, self.schedule_offsetfn)
        supply_schedule = [ {'from':self.start_time, 'to':self.end_time, 'ranges':[range1], 'stepmode':'fixed'}]
        
        range1 = (150, 150, self.schedule_offsetfn)
        demand_schedule = [ {'from':self.start_time, 'to':self.end_time, 'ranges':[range1], 'stepmode':'fixed'}]
        
        self.order_schedule = {'sup':supply_schedule, 'dem':demand_schedule,
                       'interval':int(self.ui.orderIntervalVar.get()), 'timemode':self.ui.distributionVar.get()}        
        
        buyers_spec = []
        sellers_spec = []
        
        for client in self.client_names:          
            name = client[0]
            type = client[2]
            agent = client[3]
            
            if type == 'BUY':
                buyers_spec.append((agent,name,type))
            else:
                sellers_spec.append((agent,name,type))
        
        self.exchange = Exchange()
        traders_spec = {'sellers':sellers_spec, 'buyers':buyers_spec}  
        if len(sellers_spec) > 0 and len(buyers_spec) > 0: 
            self.trader_stats = self.populate_market(traders_spec, self.traders)
            self.duration = float(self.end_time - self.start_time)        
            self.time = 0.0
            self.last_update = -1.0                        
            
                
            self.session = task.LoopingCall(self.checkSession)
            self.session.start(1)    
    
    def formatIP(self,object):
        text =  str(object).split()
        return text[1][1:len(text[1])-2]
    #==========================================================================
    #-market data and logic                                                    
    def schedule_offsetfn(self,t):
                pi2 = math.pi * 2
                c = math.pi * 3000
                wavelength = t / c
                gradient = 100 * t / (c / pi2)
                amplitude = 100 * t / (c / pi2)
                offset = gradient + amplitude * math.sin(wavelength * t)
                return int(round(offset, 0))
    
            
    def market_session(self):        
        time_left = float(float(self.ui.timeVar.get().split(' ')[0]) / self.duration)
        trade = None
        
        self.pending_orders = self.customer_orders(self.time,self.last_update,self.traders,self.trader_stats,
                                                    self.order_schedule,self.pending_orders,False)
                                                    
        n_buyers = self.trader_stats['n_buyers']
        n_sellers = self.trader_stats['n_sellers']
        n_traders = float(n_buyers + n_sellers)
        timeIndex = float(1 / n_traders)        
        index = 0
        tradeTXT = ' '        
        tradedClients = []
        while index < n_traders:          
            
            tid = list(self.traders.keys())[random.randint(0, len(self.traders) - 1)]
            if self.traders[tid].updateSleep() == True:
                order = self.traders[tid].getorder(self.time, time_left, self.exchange.publish_lob(self.time, False))        
            else:
                order = None
            
            if order != None:  
                
                lob = self.exchange.publish_lob(self.time, True)
                if len(lob['bids']['lob']) < 10:
                    ii = 0
                    for item in lob['bids']['lob']:
                        self.ui.bidVars[len(lob['bids']['lob']) - ii-1].set(int(item[0]))
                        self.ui.bidQVars[len(lob['bids']['lob']) - ii-1].set(item[1])
                        ii += 1
                    while ii < 10:
                        self.ui.bidQVars[ii].set(' ')
                        self.ui.bidVars[ii].set(' ')
                        ii += 1
                else:
                    iii = -1
                    while iii >= -10:
                        item = lob['bids']['lob'][iii] 
                        self.ui.bidVars[iii*(-1)-1].set(int(item[0]))
                        self.ui.bidQVars[iii*(-1)-1].set(item[1])
                        iii -= 1
                if len(lob['asks']['lob']) < 10:
                    ii = 0
                    for item in lob['asks']['lob']:
                        self.ui.askVars[ii].set(int(item[0]))
                        self.ui.askQVars[ii].set(item[1])
                        ii += 1
                    while ii < 10:
                        self.ui.askVars[ii].set(' ')
                        self.ui.askQVars[ii].set(' ')
                        ii += 1   
                else:                  
                    iii = -1
                    while iii >= -10:
                        item = lob['asks']['lob'][iii] 
                        self.ui.askVars[iii*(-1)-1].set(int(item[0]))
                        self.ui.askQVars[iii*(-1)-1].set(item[1])
                        iii -= 1
                traderIDS = list(self.traders.keys())
                ii = 0
                while ii < len(traderIDS):
                    self.ui.nrProfitVar[ii].set(ii+1)
                    self.ui.idProfitVar[ii].set(traderIDS[ii])
                    self.ui.profitProfitVar[ii].set(self.traders[traderIDS[ii]].balance)
                    self.ui.typeProfitVar[ii].set(self.traders[traderIDS[ii]].bidType)
                    self.ui.agentProfitVar[ii].set(self.traders[traderIDS[ii]].ttype)                    
                    self.ui.maxProfitVar[ii].set(self.traders[traderIDS[ii]].maxProfit)
                    self.ui.allocVar[ii].set(self.traders[traderIDS[ii]].allocEff)
                    ii += 1                    
                
                trade = self.exchange.process_order2(self.time,order,False)                                
                if trade != None:  
                    tradedClients.append(trade['party1'])
                    tradedClients.append(trade['party2'])                    
                    self.lastTrade = trade
                    self.traders[trade['party1']].bookkeep(trade, order, False,self.tLimitPrice)
                    self.traders[trade['party2']].bookkeep(trade, order, False,self.tLimitPrice)
                for t in self.traders:
                    self.traders[t].respond(self.time, lob, trade, False)
            self.time = self.time + timeIndex
            index += 1
       
        ii = 0
        
        bids = []
        asks = []
        while ii < 10:            
            bids.append([self.ui.bidQVars[ii].get(),self.ui.bidVars[ii].get()])
            asks.append([self.ui.askQVars[ii].get(),self.ui.askVars[ii].get()])
            ii += 1
            
        lob = [bids,asks]        
        trade = self.lastTrade
        time = self.ui.timeVar.get()
        
        for client in self.client_addr:            
            
            clientIP = self.formatIP(client.client_ip)
            trader = self.clients[clientIP][0]
            balance = str(self.traders[trader].balance)
            action = 'interval'
            if len(self.traders[trader].orders) > 0:
                order = str(self.traders[trader].orders[0].price)
            else:
                order = 'NO_ORDER'                
            blotter_length = len(self.traders[trader].blotter)
            if blotter_length > 0:
                last_order = self.traders[trader].blotter[-1]
            else:
                last_order = None
            customer_message = {'action':action,'lob':lob,'last':last_order,'balance':balance,'limit':order,'time':time,'trade':trade}
            client.transport.write(json.dumps(customer_message))
            
        if self.sessionID != None:
            limits = {}
            cloudTraders = []                    
            for elem in self.cloudClients:
                if elem in tradedClients:
                    cloudTraders.append(elem)
                if len(self.traders[elem].orders) > 0:
                    post = [self.traders[elem].orders[0].price,self.traders[elem].balance]
                else:
                    post = ['NO_ORDER',self.traders[elem].balance]
                
                if len(self.traders[elem].blotter) > 0:
                    post.append(self.traders[elem].blotter[-1])
                    post.append(len(self.traders[elem].blotter))
                else:
                    post.append('NONE')
                    post.append(0)
                
                limits[elem] = post
            print cloudTraders
            action = "SESSION"
            headers = {'Content-Type':'application/json'}
            post_data = {"action":action,"sessionID":self.sessionID,"lob":lob,
                "time":self.ui.timeVar.get(),'limits':limits,'trade':trade,'traded':cloudTraders}
            req = urllib2.Request(host+"server", json.dumps(post_data), headers)
            response = json.loads(urllib2.urlopen(req).read())['orders']
            for element in response:
                name = element[0]
                bid = element[1]
                self.traders[name].humanInput = bid 
            
        
    def populate_market(self,traders_spec, traders):

        def trader_type(robottype, name,bid):
                agent = imp.load_source("Trader_"+robottype,"./Agents/"+robottype+".py")                    
                agent_class = getattr(agent,'Trader_'+robottype)
                sleepTime = 0
                sleepMode = False

                if self.ui.sleepModeVar.get() != 'FALSE' and robottype != 'Human':
                    sleepMode = True
                    sleepTime = int(self.ui.sleepModeVar.get())
                
                return agent_class(robottype,name,0.00,bid,sleepMode,sleepTime)

        n_buyers = 0
        for bs in traders_spec['buyers']:
            ttype = bs[0]
            tname = bs[1]  #-buyer i.d. string                                 
            bidType = bs[2]
            traders[tname] = trader_type(ttype, tname,bidType)
            n_buyers = n_buyers + 1
        if n_buyers < 1:
                sys.exit('FATAL: no buyers specified\n')

        n_sellers = 0
        for ss in traders_spec['sellers']:
            ttype = ss[0]
            tname = ss[1]
            bidType = ss[2]
            traders[tname] = trader_type(ttype, tname,bidType)
            n_sellers = n_sellers + 1

        if n_sellers < 1:
                sys.exit('FATAL: no sellers specified\n')
        
        return {'n_buyers':n_buyers, 'n_sellers':n_sellers}

    def customer_orders(self,time, last_update, traders, trader_stats, os, pending, verbose):

        def sysmin_check(price):
                if price < bse_sys_minprice:
                        print('WARNING: price < bse_sys_min -- clipped')
                        price = bse_sys_minprice
                return price

        def sysmax_check(price):
                if price > bse_sys_maxprice:
                        print('WARNING: price > bse_sys_max -- clipped')
                        price = bse_sys_maxprice
                return price        

        def getorderprice(i, sched, n, mode, issuetime):
                #-does the first scheduAREA RESERVEDle range include optional dynamic offset function(s)?
                if len(sched[0]) > 2:
                        offsetfn = sched[0][2]
                        if callable(offsetfn):
                                #-same offset for min and max                  
                                offset_min = offsetfn(issuetime)
                                offset_max = offset_min
                        else:
                                sys.exit('FAIL: 3rd argument of sched in getorderprice() not callable')
                        if len(sched[0]) > 3:
                                #-if second offset function is specfied, that applies only to the max value
                                offsetfn = sched[0][3]
                                if callable(offsetfn):
                                        #-this function applies to max         
                                        offset_max = offsetfn(issuetime)
                                else:
                                      sys.exit('FAIL: 4th argument of sched in getorderprice() not callable')
                else:
                        offset_min = 0.0
                        offset_max = 0.0

                pmin = sysmin_check(offset_min + min(sched[0][0], sched[0][1]))
                pmax = sysmax_check(offset_max + max(sched[0][0], sched[0][1]))
                prange = pmax - pmin
                if n - 1 > 0:
                    stepsize = prange / (n - 1)
                else:
                    stepsize = prange
                halfstep = round(stepsize / 2.0)

                if mode == 'fixed':
                        orderprice = pmin + int(i * stepsize) 
                elif mode == 'jittered':
                        orderprice = pmin + int(i * stepsize) + random.randint(-halfstep, halfstep)
                elif mode == 'random':
                        if len(sched) > 1:
                            #-more than one schedule: choose one equiprobably  
                            s = random.randint(0, len(sched) - 1)
                            pmin = sysmin_check(min(sched[s][0], sched[s][1]))
                            pmax = sysmax_check(max(sched[s][0], sched[s][1]))
                        orderprice = random.randint(pmin, pmax)
                else:
                        sys.exit('FAIL: Unknown mode in schedule')
                orderprice = sysmin_check(sysmax_check(orderprice))
                return orderprice

        def getissuetimes(n_traders, mode, interval, shuffle, fittointerval):
                interval = float(interval)
                if n_traders < 1:
                        sys.exit('FAIL: n_traders < 1 in getissuetime()')
                elif n_traders == 1:
                        tstep = interval
                else:
                        tstep = interval / (n_traders - 1)
                arrtime = 0
                issuetimes = []
                for t in range(n_traders):
                        if mode == 'periodic':
                                arrtime = interval
                        elif mode == 'drip-fixed':
                                arrtime = t * tstep
                        elif mode == 'drip-jitter':
                                arrtime = t * tstep + tstep * random.random()
                        elif mode == 'drip-poisson':
                                #-poisson requires a bit of extra work         
                                interarrivaltime = random.expovariate(n_traders / interval)
                                arrtime += interarrivaltime
                        else:
                                sys.exit('FAIL: unknown time-mode in getissuetimes()')
                        issuetimes.append(arrtime) 
                        
                #-at this point, arrtime is the last arrival time              
                if fittointerval and ((arrtime > interval) or (arrtime < interval)):
                        #-generated sum of interarrival times longer than the interval
                        #-squish them back so that last arrival falls at t=interval
                        for t in range(n_traders):
                                if arrtime != 0:
                                    issuetimes[t] = interval * (issuetimes[t] / arrtime)
                                else:
                                    issuetimes[t] = interval * (issuetimes[t])
                #-optionally randomly shuffle the times                        
                if shuffle:
                        for t in range(n_traders):
                                i = (n_traders - 1) - t
                                j = random.randint(0, i)
                                tmp = issuetimes[i]
                                issuetimes[i] = issuetimes[j]
                                issuetimes[j] = tmp
                return issuetimes
        

        def getschedmode(time, os):
                got_one = False
                for sched in os:
                        if (sched['from'] <= time) and (time < sched['to']) :
                                #-within the timezone for this schedule        
                                schedrange = sched['ranges']
                                mode = sched['stepmode']
                                got_one = True
                                exit  #-jump out the loop -- so the first matching timezone has priority over any others
                if not got_one:
                        sys.exit('Fail: time=%5.2f not within any timezone in os=%s' % (time, os))
                return (schedrange, mode)        

        n_buyers = trader_stats['n_buyers']
        n_sellers = trader_stats['n_sellers']
        n_traders = n_buyers + n_sellers
        shuffle_times = True

        if len(pending) < 1:
                #-list of pending (to-be-issued) customer orders is empty, so generate a new one
                new_pending = []
                #-demand side (buyers)                                         
                issuetimes = getissuetimes(n_buyers, os['timemode'], os['interval'], shuffle_times, True)
                
                ordertype = 'Bid'
                (sched, mode) = getschedmode(time, os['dem'])  
                buyerNames = []
                sellerNames = []
                for key in list(self.traders.keys()): 
                    if traders[key].bidType == 'BUY':
                        buyerNames.append(key)
                    else:
                        sellerNames.append(key)
                
                for t in range(n_buyers):
                        issuetime = time + issuetimes[t]
                        tname = buyerNames[t]
                        orderprice = getorderprice(t, sched, n_buyers, mode, issuetime)
                        order = Order(tname, ordertype, orderprice, 1, issuetime)
                        new_pending.append(order)
                        
                #-supply side (sellers)                                        
                issuetimes = getissuetimes(n_sellers, os['timemode'], os['interval'], shuffle_times, True)
                ordertype = 'Ask'
                
                (sched, mode) = getschedmode(time, os['sup'])
                for t in range(n_sellers):
                        issuetime = time + issuetimes[t]
                        tname = sellerNames[t]
                        orderprice = getorderprice(t, sched, n_sellers, mode, issuetime)
                        order = Order(tname, ordertype, orderprice, 1, issuetime)
                        new_pending.append(order)
        else:                
                #-there are pending future orders: issue any whose timestamp is in the past
                new_pending = []
                for order in pending:
                        if order.time < time:
                                #-this order should have been issued by now    
                                #-issue it to the trader                       
                                tname = order.tid
                                traders[tname].add_order(order)
                                if verbose: print('New order: %s' % order)
                                #-and then don't add it to new_pending (i.e., delete it)
                        else:
                                #-this order stays on the pending list         
                                new_pending.append(order)
        return new_pending



#-method that gets the ip of the server, requires internet connection          
def get_server_IP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com",80))
    ip = s.getsockname()[0]
    s.close()  
    return ip

#-main method that initializez the GUI and starts the reactor                  
def main():             
    ip_address = get_server_IP()       
    root = Tk()
    root.title('BSE Server') 
    root.columnconfigure(0, weight=0) 
    ui = UI(root,ip_address,MyFactory)  
    tksupport.install(root)    
    reactor.run()    
    
#-starts the main method                                                       
if __name__ == '__main__':
    main()
    
    
