#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import events
from telethon.sync import TelegramClient
from telethon.tl.types import InputPhoneContact
from telethon.tl.functions.account import UpdateStatusRequest
from telethon.network.connection.tcpmtproxy import ConnectionTcpMTProxyRandomizedIntermediate
from telethon.errors import PhoneNumberInvalidError, SessionPasswordNeededError, FloodWaitError, PhoneNumberBannedError , PhoneNumberUnoccupiedError

from requests import ConnectionError

import re
import os
import sys
import json
import time
import random
import string
import logging

logging.basicConfig(level=logging.ERROR)

if not os.path.exists("sessions/"):
    os.mkdir("sessions")
if not os.path.exists("anotherSessions"):
    os.mkdir("anotherSessions")
if not os.path.exists("accounts.json"):
    with open('accounts.json', 'w') as f:
        json.dump({}, f, indent=4, sort_keys=True)
if not os.path.exists("proxies.txt"):
    with open('proxies.txt', 'w') as f:
        f.write("Please fill server ony by one and use this format => ip,port,secret")
if not os.path.exists("config.json"):
    print("ERROR: Config file not found , please copy and edit config.example.json.")

config = json.load(open("config.json", "r", encoding="utf-8"))

proxies = list(map(lambda proxy:
                   (proxy.split(",")[0], int(
                       proxy.split(",")[1]), proxy.split(",")[2]),
                   [proxy for proxy in open("proxies.txt", "r").read().split("\n")[1:] if proxy != ""]))

accounts = json.load(open("accounts.json", "r", encoding="utf-8"))

tmpClient = {}

def randomString(stringLength):
    letters = string.ascii_lowercase + string.digits
    return str(''.join(random.choice(letters) for i in range(stringLength))).upper()


def saveConfig():
    json.dump(accounts, open('accounts.json', 'w', encoding="utf-8"),
              indent=4, sort_keys=True, ensure_ascii=False)


class Account:

    def __init__(self, phone, twoVerify=None, nick=None):
        self.phone = phone
        self.twoVerify = twoVerify or ""
        self.nick = nick or ""

    def save(self):
        if not hasattr(accounts, self.phone):
            accounts[self.phone] = {}
        accounts[self.phone]["phone"] = self.phone
        accounts[self.phone]["twoVerify"] = self.twoVerify
        accounts[self.phone]["nick"] = self.nick
        saveConfig()

    def remove(self):
        if hasattr(accounts, self.phone):
            del accounts[self.phone]
        saveConfig()
        os.remove("sessions/"+self.phone+".session")

    def editPhone(self, phone):
        self.phone = phone
        self.save()

    def editTwoVerify(self, twoVerify):
        self.twoVerify = twoVerify
        self.save()

    def editNick(self, nick):
        self.nick = nick
        self.save()


def generateClient(account, sessionsPath="sessions/"):
    sessionName = sessionsPath + account.phone
    if len(proxies) > 0:
        proxy = random.choice(proxies)
        print("INFO: Proxies list available , use proxy server.")
        print("INFO: Proxy server %s:%d selected." % (proxy[0], proxy[1]))
        client = TelegramClient(session=sessionName,
                                api_id=config["api"]["id"],
                                api_hash=config["api"]["hash"],
                                connection=ConnectionTcpMTProxyRandomizedIntermediate,
                                proxy=proxy)
    else:
        client = TelegramClient(session=sessionName,
                                api_id=config["api"]["id"],
                                api_hash=config["api"]["hash"])

    return(client)


def generateAuthedClient(account, autoExit=True):
    try:
        client = generateClient(account)
        print('INFO: Connecting to Telegram Server...')
        client.connect()
        client.sign_in(phone=account.phone)
        if client.is_user_authorized():
            print('INFO: Client login! Account still alive!')
            return(client)
        else:
            print("ERROR: Client not login, Please add it and run this method again..")
            if autoExit:
                sys.exit()
            return(False)
    except ConnectionError:
        return(generateAuthedClient(account, autoExit))


def getAccount(idOrPhone, add=False):
    if len(idOrPhone) < 3:
        i = 0
        for k in accounts:
            i = i + 1
            if i == int(idOrPhone):
                print("INFO : Phone %s selected." % (accounts[k]["phone"]))
                return(
                    Account(accounts[k]["phone"], accounts[k]
                            ["twoVerify"], accounts[k]["nick"])
                )
    elif idOrPhone in accounts:
        print("INFO: Phone %s selected." % (accounts[idOrPhone]["phone"]))
        return(
            Account(accounts[idOrPhone]["phone"], accounts[idOrPhone]
                    ["twoVerify"], accounts[idOrPhone]["nick"])
        )
    if add:
        account = Account(idOrPhone)
        return(account)
    print("ERROR: No phone selected.")
    sys.exit()


def main():
    print()
    print("Here are your accounts.")
    print()
    print("%-3s %-20s %-32s %-20s" % ("ID", "Phone", "Password", "Nickname"))
    print("==============================================================================")
    i = 0
    for k in accounts:
        i = i + 1
        print("%-3s %-20s %-32s %-20s" %
              (str(i), accounts[k]["phone"], accounts[k]["twoVerify"], accounts[k]["nick"]))

    if len(sys.argv) == 2 and sys.argv[1] == "keepall":
        method = "keepall"
    else:
        print("INPUT: Select method :")
        print("METHOD: %-30s - %s" % ("Add", "Add account"))
        print("METHOD: %-30s - %s" % ("Remove", "Remove account"))
        print("METHOD: %-30s - %s" % ("Nick", "Set Nickname"))
        print("METHOD: %-30s - %s" %
              ("2FA", "Change two verification code (Random)"))
        print("METHOD: %-30s - %s" % ("Receive", "Receive messages"))
        print("METHOD: %-30s - %s" %
              ("GenerateAnotherSessionFiles", "Copy another session files"))
        print("METHOD: %-30s - %s" %
              ("Keep", "[Default] Send message to keep account alive."))
        print("METHOD: %-30s - %s" %
              ("Exit", "Exit keeper."))
        method = input("> ").lower()

    if method == "add":
        account = getAccount(input("INPUT: Phone Number : "), add=True)

        client = generateClient(account)
        print('INFO: Connecting to Telegram Server...')
        client.connect()
        try:
            client.sign_in(phone=account.phone)
            if not client.is_user_authorized():
                sent=client.send_code_request(phone=account.phone,force_sms=True)
                code=input("INPUT: Verification Code : ")
                try:
                    client.sign_in(account.phone, code)
                except PhoneNumberUnoccupiedError:
                    client.sign_up(phone=account.phone,
                               first_name=".",last_name=".", code=code)
                    twoVerify=randomString(10)
                    client.edit_2fa(current_password=account.twoVerify)
                    account.editTwoVerify(twoVerify)
                    client.edit_2fa(new_password=twoVerify)
                    print("INFO: Two verification code set to => %s ." %
                          account.twoVerify)
                except SessionPasswordNeededError:
                    code=input("INPUT: Two Step Verification Code : ")
                    account.editTwoVerify(code)
                    client.sign_in(password=code)
            if client.is_user_authorized():
                print("INFO: Client login , operation successfully completed!")
                client.disconnect()
                account.save()
            else:
                print("ERROR: Something wrong , please try again later.")
                client.disconnect()
                account.remove()
        except:
            print("ERROR: Something wrong , please try again later.")
            client.disconnect()
            account.remove()
            import traceback
            traceback.print_exc()

    elif method == "remove":
        account = getAccount(input("INPUT: Phone Number / ID : "))
        if input("WARN: Do you really want to delete this account? [y/N]").lower() == "y":
            account.remove()
        else:
            print("INFO: Operation cancle.")

    elif method == "receive":
        account = getAccount(input("INPUT: Phone Number / ID : "))
        client = generateAuthedClient(account)

        @client.on(events.NewMessage)
        async def handler(event):
            print("INFO: New message => " + event.raw_text)

        client.start()
        client.run_until_disconnected()

    elif method == "2fa":
        account = getAccount(input("INPUT: Phone Number / ID : "))
        client = generateAuthedClient(account)
        twoVerify = randomString(10)
        client.edit_2fa(current_password=account.twoVerify)
        account.editTwoVerify(twoVerify)
        client.edit_2fa(new_password=twoVerify)
        client.disconnect()
        print("INFO: Two verification code set to => %s , operation successfully completed !" %
              account.twoVerify)

    elif method == "nick":
        account = getAccount(input("INPUT: Phone Number / ID : "))
        nick = input("INPUT: Nickname : ")
        account.editNick(nick)

    elif method == "generateanothersessionfiles":
        account = input("INPUT: Phone Number / ID / all : ")

        def copy(account):
            account = getAccount(account)
            client = generateAuthedClient(account)
            newClient = generateClient(account, "anotherSessions/")

            @client.on(events.NewMessage)
            async def handler(event):
                r = re.match(r"Login code: ([0-9]+).", event.raw_text)
                if r:
                    try:
                        await newClient.sign_in(account.phone, r.group(1))
                    except SessionPasswordNeededError:
                        await newClient.sign_in(password=account.twoVerify)
                    print(
                        "INFO: Copy done! You can find it in anotherSessions directory.")
                    waitSec = random.randint(
                        config["keeper"]["antiFloodWaitRange"]["min"], config["keeper"]["antiFloodWaitRange"]["max"])
                    print("INFO: Wait for %d second for anti flood wait" % waitSec)
                    await time.sleep(waitSec)
                    await client.disconnect()
                    await newClient.disconnect()

            client.start()
            newClient.connect()
            newClient.send_code_request(phone=account.phone)
            print("INFO: Waiting verification code....")
            client.run_until_disconnected()

        if account == "all":
            for k in accounts:
                try:
                    copy(k)
                except PhoneNumberBannedError:
                    print("WARN: Account has been gone.")

        else:
            copy(account)

    elif method == "exit":
        return("Exit")

    elif method == "keep" or method == "" or method == "keepall":
        account = input("INPUT: Phone Number / ID / all : ")

        def keep(account):
            print("INFO: This operation may take 1 minute to run.")
            account = getAccount(account)
            client = generateAuthedClient(account)
            time.sleep(random.randint(3, 8))
            client(UpdateStatusRequest(offline=False))
            print("INFO: Set account status to Online.")
            time.sleep(random.randint(5, 20))
            client(UpdateStatusRequest(offline=True))
            print("INFO: Set account status to Offline.")
            time.sleep(random.randint(3, 8))
            client.disconnect()

        if account == "all":
            for k in accounts:
                try:
                    keep(k)
                    waitSec = random.randint(
                        config["keeper"]["antiFloodWaitRange"]["min"], config["keeper"]["antiFloodWaitRange"]["max"])
                    print("INFO: Wait for %d second for anti flood wait" % waitSec)
                    time.sleep(waitSec)
                except PhoneNumberBannedError:
                    print("WARN: Account has been gone.")
        else:
            keep(account)


while True:
    try:
        if main() == "Exit":
            break
    except FloodWaitError:
        print("WARN: FLOOD LIMIT")
        pass
    except KeyboardInterrupt:
        print("WARN: Ctrl+C exiting..")
        sys.exit()
    except:
        import traceback
        traceback.print_exc()
        pass
