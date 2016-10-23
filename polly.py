#!/usr/bin/python
# coding: utf-8
# Copyright (C) 2009, 2010, 2013 Tobias Kaiser <mail@tb-kaiser.de>
import sys
import cgi
import os
import socket
import time
import datetime
import select
import random

# begin of configuration

host="InsertIRCServerHere"
nick = "polly"
contact = "InsertEMailHere"
plainfile="/home/polly/small.html"
watchchan = "#InsertChannelHere"
nickserv_password="InsertNickservPwHere"
admin_list=["InsertAdmin1Here", "AnotherAdmin"]
refresh_interval=60
refresh_interval2=600
hotwords = {
    "polly":["*schnurr*"],
    "streichel":["*schnurr*", "*knurr*", "*gnurr*"],
    "kick":["*kratz*", "*fauch*"],
    }

# end of configuration

s=socket.socket()
s.connect((host, 6667))
s.sendall("PASS *\n")
s.sendall("NICK %s\n" % nick)
s.sendall("USER %s 0 0 :%s\n" % (nick, nick))
def newnextmiao():
    global nextmiao
    nextmiao = datetime.datetime.today() + (
        datetime.timedelta(seconds=(600*420.0+int(random.random()*420.0))))

def idle_t(seconds):
    if seconds<150: return ""
    #if seconds<60: return " (%is idle)"%seconds  
    minutes=seconds/60
    if minutes<60: return " (%imin)"%minutes
    hours=minutes/60
    return " (%ih)"%hours

def status_prefix(name):
    p=name[0]
    if p=="~": return "owner"
    elif p=="&": return "admin"
    elif p=="@": return "op"
    elif p=="%": return "halfop"
    elif p=="+": return "voice"
    return "normal"

newnextmiao()
status2col= {
    "owner":"color:green;font-weight:bold;",
    "admin":"color:green;font-weight:bold;",
    "op":"color:green;font-weight:bold;",
    "halfop":"color:#CC00CC;font-weight:bold;",
    "voice":"color:#026CB1;",
    "normal":""
}
idle_dict={}

lastrefresh=0
lastrefresh2=0
lastfilerefresh=0
msguser=""
while True:
    buffer = ""
    while True:
        try:
            selection = select.select([s], [], [], \
                min(((nextmiao - datetime.datetime.today()).seconds,
                refresh_interval)))
        except KeyboardInterrupt:
            print datetime.datetime.today(), "Received KeyboardInterrupt. Quitting."
            s.sendall("QUIT ^C\n")
            s.close()
            f=open(plainfile, "w")
            f.write("N/A")
            f.close()
            exit()
        if lastrefresh2+refresh_interval2<time.time():
            lastrefresh2=time.time()
            userfile1=open(plainfile, "r")
            userimchan=userfile1.read()
            if userimchan!="N/A" and userimchan!="":
                userarray=userimchan.split(",")
                for usrar in userarray :
                             s.sendall("WHOIS %s \n"% usrar.split(">")[1].split("<")[0].split()[0])
            userfile1.close()
        if lastrefresh+refresh_interval<time.time():
            s.sendall("NAMES %s\n" % watchchan)
            lastrefresh=time.time()
            print datetime.datetime.today(), "Periodical list request"
            userfile1=open(plainfile, "r")
            userimchan=userfile1.read()
            if userimchan!="N/A" and userimchan!="":
                userarray=userimchan.split(",")
                for usrar in userarray :
                    if len(usrar.split(">"))>=2 :
                         if usrar.split("'")[1]=="black" : 
                             s.sendall("WHOIS %s \n"% usrar.split(">")[1].split("<")[0].split()[0])
            userfile1.close()
        if datetime.datetime.today()>nextmiao: # select aborted due to timeout
            s.sendall("PRIVMSG %s :Miau.\n" % watchchan)
            idle_dict[nick]=time.time()
            newnextmiao()
        elif s in selection[0]:
            buffer = buffer + s.recv(1024)
            if len(buffer)>0:
                if buffer[len(buffer)-1]=="\n":
                    break
        
    for line in buffer.split("\n"):
        
        if line.strip()=="": continue
        a=line.split(" ", 2)
        command=a[1].strip()
        if command=="376":
            print datetime.datetime.today(), "Connected successfully!"
            s.sendall("PRIVMSG nickserv identify %s\n"%nickserv_password)
            s.sendall("JOIN %s\n" % watchchan)
        if command=="372":
            print a[2].strip()
        if command=="307":
            if len(msguser)!=0 :
                if a[2].startswith("%s %s :is a"%(nick,msguser)):
                    s.sendall("%s\n" % message2)
                msguser=""
            whoisuser= a[2].split()[1]
            s.sendall("MODE %s +v %s \n" %(watchchan,whoisuser))
        #if command in ["PART", "JOIN", "QUIT", "KICK", "MODE", "NICK",
        #    "PRIVMSG"]:
        #    s.sendall("NAMES %s\n" % watchchan)
        #    print datetime.datetime.today(), "Requesting new list due to", \
        #        a[1].strip()
        if command=="JOIN":
            sender=a[0].split(":")[1].split("!")[0]
            idle_dict[sender.lstrip("~@&%+")]=time.time()   
            s.sendall("WHOIS %s\n" % sender)
        if command=="353":
            y, z, c, nl = a[2] = a[2].split(" ", 3)
            if c== watchchan and lastfilerefresh+refresh_interval<time.time():
                p=open(plainfile, "w")
                lastfilerefresh=time.time()
                nl=nl.split(":", 1)[1].split(" ")
                is_first=True
                for x in nl:
                    status=status_prefix(x)
                    xs = cgi.escape(x.lstrip("~@&%+"))
                    if xs.strip()!="":
                        if not xs in idle_dict:
                            idle_dict[xs]=time.time()
                        if not is_first: p.write(", ")
                        else: is_first=False
                        p.write("<span style='%s'>%s</span>%s"%(
                            status2col[status], xs,
                            idle_t(time.time()-idle_dict[xs])))
                p.close()

                print datetime.datetime.today(), "Output file written."
        if command=="PRIVMSG":
            receiver, message = a[2].split(" ", 1)
            message=message.split(":", 1)[1]
            sender=a[0].split(":")[1].split("!")[0]
            if receiver.strip()==nick:
                if sender in admin_list:
                    message2=message
                    s.sendall("WHOIS %s\n" % a[0].split(":",1)[1].split("!", 1)[0])
                    msguser=a[0].split(":",1)[1].split("!", 1)[0]

                else:
                    s.sendall("PRIVMSG %s :*schnurr*\n"%sender)
            if receiver.strip().lower()==watchchan.lower():
                idle_dict[sender.lstrip("~@&%+")]=time.time()
                for hw in hotwords.keys():
                    if message.strip().lower().find(hw)>0:
                        s.sendall("PRIVMSG %s :%s\n" % (watchchan,
                           random.choice(hotwords[hw])))
                        print datetime.datetime.today(), ":-)"
                        idle_dict[nick]=time.time()
                        break
        if a[0].strip()=="PING":
            s.sendall("PONG %s\n" % a[1])
