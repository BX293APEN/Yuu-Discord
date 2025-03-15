import discord, asyncio, os, subprocess, time, json, datetime,sqlite3, re, jaconv, random, requests, io
from discord.ext import tasks
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
#from cairosvg import svg2png
from PIL import Image
#import glob

def cmd(command):
    r = subprocess.check_output(command, shell=True)
    return r.decode("ANSI").strip()


def web_scraping(url, tag = "html", num = -1, attribute = "text"):
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    contents = BeautifulSoup(response.text, 'html.parser')
    
    tagList = contents.select(tag)
    if num < 0:
        return tagList
    if attribute == "text":
        value = tagList[num].getText()
    else:
        value = tagList[num].get(attribute)
    
    return value

class MySQLite():
    def __init__(self, db = f"{os.path.dirname(os.path.abspath(__file__))}/sqlite3.db"):
        # データベースとの接続
        self.databaseHost = sqlite3.connect(database = db)
    
    def __enter__(self):
        # カーソルを作る
        self.database = self.databaseHost.cursor()
        return self
    
    def send_sql(self, sql): # SQL文送信
        self.database.execute(sql)
        self.db_commit()
        return self.database.fetchall() # タプル形式で全て取得
    
    def db_commit(self):
        self.databaseHost.commit()

    def __exit__(self, *args):
        self.db_commit()
        self.database.close()
        self.databaseHost.close()

class CreateMessage(MySQLite):
    def __init__(self, admin, db = f"{os.path.dirname(os.path.abspath(__file__))}/sqlite3.db", eventFilePath = f"{os.path.dirname(os.path.abspath(__file__))}/event.json"):
        self.nowTime            = datetime.datetime.now(ZoneInfo("Asia/Tokyo"))
        self.weekdayName        = ("月","火","水","木","金","土","日")
        super().__init__(db)
        self.admin              = admin
        self.hiragana           = re.compile(r'[\u3041-\u3096]') #ひらがなの登録
        self.katakana           = re.compile(r'[\u30A0-\u30FA]') #カタカナの登録
        self.eventFilePath      = eventFilePath

    def classify_message(self, message, mode:int):
        self.message            = message
        if self.message == "":
            return "callYuu"
        try:
            self.categoryData   = self.send_sql(f"""
                SELECT category FROM emotion 
                    WHERE "{self.message}" LIKE "%" || data || "%"
                    AND page = {mode}
                    ORDER BY id ASC
            """)[0][0]
        except Exception as e:
            print(e)
            if mode == 1:
                self.categoryData   = self.message
            else:
                self.categoryData   = "NotFound"
    
    def get_message(self):
        if self.categoryData.count("date")>0:
            return  f"{self.nowTime.year}年 {self.nowTime.month}月 {self.nowTime.day}日 {self.weekdayName[self.nowTime.weekday()]}曜日だよ"
        elif self.categoryData.count("time")>0:
            return f"{self.nowTime.hour}:{self.nowTime.minute}だよ"
        elif self.categoryData.count("weather")>0:
            return self.get_weather()
        
        elif self.categoryData.count("morse")>0:
            return f"""
```
{
    self.exchange(
        morsestr = self.message.split("モールス信号:")[1]
    )
}
```
            """
        
        elif self.categoryData.count("jamcode")>0:
            return self.morse_decode(
                morseCode = self.message.split("日文モールス復号:")[1],
                lang = "ja"
            )
        elif self.categoryData.count("eumcode")>0:
            return self.morse_decode(
                morseCode = self.message.split("欧文モールス復号:")[1],
                lang = "eu"
            )
        
        elif self.categoryData.count("prof") > 0:
            with open(f"{os.path.dirname(os.path.abspath(__file__))}/README.md", "r", encoding="UTF-8") as readme:
                return readme.read()
            return f"""
            {prof}\n
            \n > 何かあれば管理者<@{self.admin}>まで
            """
            
        elif self.categoryData.count("reminder") > 0:
            arrangedMessage = self.message.split("リマインダ:")[1]
            time = 0
            timerFlag = 1
            if arrangedMessage.count("時間") > 0:
                hourMessage = re.findall(r"\d+",arrangedMessage.split("時間")[0])[-1]
            elif arrangedMessage.count("時") > 0:
                hourMessage = re.findall(r"\d+",arrangedMessage.split("時")[0])[-1]
                timerFlag = 0
            else:
                hourMessage = 0
            if arrangedMessage.count("分") > 0:
                minuteMessage = re.findall(r"\d+",arrangedMessage.split("分")[0])[-1]
            else:
                minuteMessage = 0
            if arrangedMessage.count("秒") > 0:
                secondMessage = re.findall(r"\d+",arrangedMessage.split("秒")[0])[-1]
            else:
                secondMessage = 0
            if timerFlag == 1:
                self.reminderTime = float(hourMessage) * 3600 + float(minuteMessage) * 60 + float(secondMessage)
                
            else:
                nowTime = self.nowTime
                reminderTime = datetime.datetime(year=self.nowTime.year, month=self.nowTime.month, day=self.nowTime.day, hour=int(hourMessage), minute = int(minuteMessage), second = int(secondMessage))
                if nowTime > reminderTime:
                    self.reminderTime = datetime.datetime(year=self.nowTime.year, month=self.nowTime.month, day=int(self.nowTime.day + 1), hour=int(hourMessage), minute = int(minuteMessage), second = int(secondMessage))
                timeDelta = reminderTime - nowTime
                self.reminderTime = timeDelta.total_seconds()
            return self.categoryData
            
        elif self.categoryData.count("calc")>0:
            if self.message.count("計算:") > 0:
                calc = self.message.split("計算:")[1]
            else:
                calc = self.message.split("calc")[1]
            
            try:
                regEx = r"\d+|\+|\-|\*|\/|\%|\(|\)|\."
                calc = re.findall(regEx, calc)
                # print(calc)
                calc = "".join(calc)
                return eval(calc)
            except:
                return self.categoryData
            
        elif (
            self.categoryData.count("stop")     > 0 or
            self.categoryData.count("events")   > 0 or
            self.categoryData.count("weather")  > 0 or
            self.categoryData.count("search")   > 0 or
            self.categoryData.count("whoami")   > 0 or
            self.categoryData.count("server")   > 0 or
            self.categoryData.count("usecmd")   > 0 or
            self.categoryData.count("lock")     > 0 or
            self.categoryData.count("help")     > 0 or
            self.categoryData.count("chgun")    > 0 or
            self.categoryData.count("fav")      > 0 or
            self.categoryData.count("del")      > 0
        ):
            return self.categoryData
        
        elif self.categoryData.count("health")>0:
            return "元気だよ！ありがと(*´ω｀*)〜♪"

        else:
            try:
                replyData = self.send_sql(f"""
                    SELECT value FROM keywordlist
                    WHERE key = "nevertheless"
                """)
                for n in replyData:
                    if int(self.message.count(n[0])) > 0:
                        self.message = self.message.split(n[0])[-1]
                
                self.classify_message(self.message, 1)
                try:
                    rep = self.send_sql(f"""
                        SELECT value FROM keywordlist
                            WHERE "{self.categoryData}" LIKE "%" || key || "%"
                    """)
                    ansIndex = random.randint(0, len(rep)-1) # 最小値以上最大値以下の整数
                    return rep[ansIndex][0]
                
                except:
                    self.classify_message(self.message, 2)
                    replyData = self.send_sql(f"""
                        SELECT value FROM keywordlist
                        WHERE key = "firstPerson"
                    """)

                    if self.categoryData.count("askName") >0:
                        for n in replyData:
                            if int(self.message.count(n[0])) > 0:
                                return "callyou"
                        return "私は、ユウって名前だよ！\nよろしくね！！"
                    
                    elif self.categoryData == "callYuu":
                        return "何？"
                
                    elif self.categoryData == "question":
                        return f"私、Botだからよくわかんないや\n<@{self.admin}>に聞いて"
            
            except Exception as e:
                print(e)
                return self.categoryData
        
    def ev(self, day):# 特別な日付の時の処理 db化したい
        with open(self.eventFilePath,'r',encoding="UTF-8") as eventFile:
            eventData = json.loads(eventFile.read())

        value = [day, "True"]

        for e in eventData:
            eventDay = e["date"]
            event = e["value"]
            if str(day) == str(eventDay):
                value = [day.replace(eventDay, event), e["adminOnly"]]
                break
        return value
    
    def get_event(self, messageChannelID):
        # 今日のイベント取得
        nowJPNdate          = f"{self.nowTime.month}/{self.nowTime.day}"
        eventSearchValue    = self.ev(nowJPNdate, self.eventFilePath)
        todayEvent          = eventSearchValue[0]
        adminOnly           = eventSearchValue[1]
        self.event          = f"{nowJPNdate}:特に何もないよ"
        if todayEvent != nowJPNdate:
            if adminOnly == "False":
                self.event = f"{nowJPNdate}:{todayEvent}"
            else:
                if str(messageChannelID) == str(self.adminDMID):
                    self.event = f"{nowJPNdate}:{todayEvent}"
        
        return self.event
    
    def get_reminder(self):
        return self.reminderTime

    def get_weather(self):
        jsonURL = "https://weather.tsukumijima.net/api/forecast/city/"
        try:
            cityID = self.send_sql(f"""
                SELECT id FROM weather 
                    WHERE "{self.message}" LIKE "%" || prefecture || "%"
                    ORDER BY id ASC
            """)[0][0]
            
        except:
            cityID              = "130010"
        return f"{jsonURL}{cityID}"
        
    def exchange(self, morsestr):
        val = []
        for code in morsestr:
            if code == "　":
                code = "space"
            elif code == " ":
                code = "space"
            elif code == "゛":
                code = "濁点"
            elif code == "゜":
                code = "半濁点"
                
            elif (self.hiragana.search(code) is not None):
                hkataka = jaconv.hira2hkata(code)
                hkm = jaconv.h2z(hkataka[0])
                try:
                    hka = jaconv.h2z(hkataka[1])
                    val.append(
                        self.send_sql(f"""
                            SELECT value FROM morse
                            WHERE data = "{jaconv.kata2hira(hkm)}"
                        """)[0][0]
                    )
                    if hka == '\uFF9E':
                        code = "濁点"
                    elif hka == '\uFF9F':
                        code = "半濁点"
                
                except IndexError:
                    hka = ""

            elif (self.katakana.search(code) is not None):
                hkataka = jaconv.z2h(code)
                hkm = jaconv.h2z(hkataka[0])
                try:
                    hka = jaconv.h2z(hkataka[1])
                    val.append(
                        self.send_sql(f"""
                            SELECT value FROM morse
                            WHERE data = "{jaconv.kata2hira(hkm)}"
                        """)[0][0]
                    )
                    if hka == '\uFF9E':
                        code = "濁点"
                    elif hka == '\uFF9F':
                        code = "半濁点"
                
                except IndexError:
                    hka = ""
                    code = jaconv.kata2hira(hkm)
            else:
                code = code.lower()

            if code == "space":
                val.append(" ")
            else:
                try:
                    val.append(
                        self.send_sql(f"""
                            SELECT value FROM morse
                            WHERE data = "{code}"
                        """)[0][0]
                    )
                except:
                    val.append("")

        return " ".join(val)
    
    def morse_decode(self, morseCode:str, lang = "ja"):
        morseCodeData = morseCode.split(" ")
        ans = ""
        language = lang
        if language != "ja":
            language = "en"
        for mcode in morseCodeData:
            try:
                if mcode == "":
                    ans += " "
                    
                else:
                    code = self.send_sql(f"""
                        SELECT data FROM morse
                        WHERE value = "{mcode}"
                        AND (
                            lang = "{language}" OR
                            lang = "base"
                        )

                    """)[0][0]
                    if code == "濁点":
                        ans += "゛"
                    elif code == "半濁点":
                        ans += "゜"
                    else:
                        ans += code
            except:
                ans += " "
        return ans

class MyClient(discord.Client):
    def __init__(self, settingsData):
        self.settingsData = settingsData
        self.adminName  = self.settingsData["admin"]["name"]
        self.adminID    = self.settingsData["admin"]["userID"]
        self.adminDMID  = self.settingsData["admin"]["id"]
        self.directory  = os.getcwd().replace(os.path.sep, "/") #ディレクトリ情報
        self.weekdayName = ("月","火","水","木","金","土","日")

        if str(self.settingsData["dataFolder"][0]) == "/":
            self.dataFolder     = f"""{str(self.directory)}{self.settingsData["dataFolder"]}/"""
        else:
            self.dataFolder     = f"""{self.settingsData["dataFolder"]}/"""

        self.emotionFile        = f"{self.dataFolder}sqlite3.db"
        self.eventFilePath      = f"{self.dataFolder}event.json"
        
        while True:
            networkTestCommand = subprocess.run("ping 8.8.8.8 -n 1",shell = True)
            networkStatus = networkTestCommand.returncode
            if networkStatus == 0:
                break
            else:
                self.botStatus = "ネットワークエラー"
            time.sleep(5)
        
        intent = discord.Intents.all()
        intent.message_content = True
        super().__init__(intents=intent)
    
    def get_token(self):
        #with open(f"{str(self.directory)}/TOKEN/discord.token") as tokenFile:
        #    tokenData = tokenFile.read()
        #    token = tokenData.split("\n")[0]
        #    TOKEN = token
        #return TOKEN
        return os.getenv('ACCESS_TOKEN')
    
    def __enter__(self):
        self.run(self.get_token()) # Botの起動とDiscordサーバーへの接続

    def __exit__(self, *args):
        self.end()
    
    def end(self):
        self.schedule.cancel()
        asyncio.run(self.close())

    def get_status(self):
        return self.botStatus

    async def message_send(self, text, channelID):
        channel = self.get_channel(channelID) #サーバチャンネル用
        if channel is None:
            channel = await self.fetch_user(channelID) # DM用
        
        if channel is not None:
            await channel.send(text)
    
    async def reminder(self, message, waitTime):
        await asyncio.sleep(waitTime)
        sendTimeLineMessage = f"{str(waitTime)}秒が経過しました"
        await message.reply(sendTimeLineMessage)
    
    async def play_music(self, musicName, message):
        musicPath = f"{self.directory}/music/{musicName}.mp3"
        if(os.path.isfile(musicPath)):
            if message.author.voice and message.author.voice.channel:
                try:
                    message.guild.voice_client.stop()
                except:
                    pass
                try:
                    await message.guild.voice_client.disconnect(force=True)
                except:
                    pass
                await self.message_send("音楽を再生します。", message.channel.id)
                try:
                    await message.author.voice.channel.connect()
                except Exception as e:
                    #pip install -U discord.py[voice]
                    try:
                        await message.guild.voice_client.move_to(message.author.voice.channel)
                    except:
                        pass
                await asyncio.sleep(1)
                try:
                    source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(musicPath), volume=1)
                    message.guild.voice_client.play(source)
                    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=musicName))
                except Exception as e:
                    await self.message_send(f"失敗しました。{e}", message.channel.id)
        
            else:
                await self.message_send("ボイスチャンネルに入ってください。", message.channel.id)
    
        else:
            await self.message_send("音楽が登録されていません。", message.channel.id)
        
    async def on_ready(self): # 起動時に動作する処理
        user = await self.fetch_user(self.adminID)
        self.botStatus = "LOGIN"
        await user.send("ログインしました。")
        self.schedule.start(self.settingsData["autoAllowChannel"])
    
    async def send_server_status(self, statusName : str, data, channelID):
        channelCount = 0
        sepLine = "-" * 5
        channelNameList =f"{sepLine}{statusName}{sepLine}\n"
        for channel in data:
            channelNameList = f"{channelNameList}{str(channel.mention)}\n"
            channelCount = channelCount + 1
        await self.message_send(f"{channelNameList}の{str(channelCount)}個\n", channelID)
    
    @tasks.loop(seconds=60) # 60秒に一回ループ
    async def schedule(self, channelIDList):
        nowJPNTime = datetime.datetime.now(ZoneInfo("Asia/Tokyo"))
        nowJPNdate = f"{str(nowJPNTime.month)}/{str(nowJPNTime.day)}"
        nowJPNWeekday = self.weekdayName[nowJPNTime.weekday()]
        nowJPNHour = nowJPNTime.hour
        nowJPNMinute = nowJPNTime.minute
        nowJPNSecond = nowJPNTime.second
        sendText = ""
        eventFlag = 0
        
        with CreateMessage(self.adminID, self.emotionFile, self.eventFilePath) as msg:
            eventSearchValue = msg.ev(nowJPNdate)
        todayEvent = eventSearchValue[0]
        adminOnly = eventSearchValue[1]
        
        activity = discord.Activity(name="チャットメッセージ", type=discord.ActivityType.watching)
        await self.change_presence(activity=activity)
        if nowJPNHour == 0 and nowJPNMinute == 0:
            sendText = f"日付が変わりました。\n今日は{nowJPNdate}です。"
            if todayEvent != nowJPNdate:
                eventFlag = 1
    
        elif nowJPNHour == 6 and nowJPNMinute == 0:
            if todayEvent != nowJPNdate:
                eventFlag = 1
            if nowJPNWeekday == self.weekdayName[0]:
                sendText = f"おはようございます！\n今日は{nowJPNdate}月曜日！\n一週間の始まり...\n体調に気を付けて今週も頑張りましょう！！"
            elif nowJPNWeekday == self.weekdayName[2]:
                sendText = "おはようございます！\n今日は一週間の折り返し地点の水曜日です！！\nあと半分で休日ですよ(:3_ヽ)_"
            elif nowJPNWeekday == self.weekdayName[4]:
                sendText = f"おはようございます！\n今日は{nowJPNdate}金曜日！！\n今日が終われば休みが待ってます！！\n頑張りましょ(:3_ヽ)_"
            else:
                sendText = f"おはようございます！\n今日は{nowJPNdate}\n今日も一日体調に気を付けて過ごしましょ！"
    
        elif nowJPNHour == 12 and nowJPNMinute == 0:
            sendText = "お昼です。\n皆さん休みましょう！！"
    
        elif nowJPNHour == 0 and nowJPNMinute == 15:
            sendText = "おやすみzzz..."
            with open(f"{self.directory}/db/temp","w",encoding="UTF-8") as tempFile:
                tempFile.write("U,WORD")
    
        if sendText != "":
            for channelID in channelIDList:
                await self.message_send(sendText, channelID["id"])
    
        if eventFlag == 1:
            if adminOnly == "False":
                for channelID in channelIDList:
                    await self.message_send(f"今日は{todayEvent}", channelID["id"])
            else:
                await self.message_send(f"今日は{todayEvent}", self.adminDMID)
        
    def discord_send(self, sendMessage, channelID):
        asyncio.run(self.message_send(sendMessage, channelID))

    async def help_send(self, message): # ヘルプ送信処理
        with open(f"{self.directory}/config/help.json","r",encoding="UTF-8") as helpText:
            helpData = json.loads(helpText.read())
                
        embed = discord.Embed( 
            title=f"""{self.settingsData["name"]} ver. {self.settingsData["version"]} HELP""",
            color=0x00ff00,
            description="Yuu > $ help"
        )
        embed.set_author(
            name=self.user, # Botのユーザー名
            icon_url=self.user.avatar.url # Botのアイコンを設定
        )

        embed.add_field(name="\n", value= "\n" ,inline = False)
        embed.add_field(name=helpData["callYuu"]["title"], value=helpData["callYuu"]["value"])
        embed.add_field(name=helpData["sendMessage"]["title"], value=helpData["sendMessage"]["value"], inline = True)
        embed.add_field(name="\u200B", value= "\u200B" ,inline = False)
        embed.add_field(name=helpData["cmd"]["title"], value= "", inline = False)
        for cmd in helpData["cmd"]["aboutCommand"]:
            embed.add_field(name=cmd["title"], value=cmd["value"], inline = True)
        embed.add_field(name="\u200B", value= "\u200B" ,inline = False)
        embed.set_footer(text="(追加中)")
            
        await message.channel.send(embed=embed)
            
            
        embed = discord.Embed( 
            title=f"""引数有り{helpData["cmd"]["title"]}""",
            color=0x00ff00,
        )
        embed.set_author(
            name=self.user, # Botのユーザー名
            icon_url=self.user.avatar.url # Botのアイコンを設定
        )
        embed.add_field(name="", value= "" ,inline = False)
        for cmd in helpData["cmd"]["withArgCommands"]:
            embed.add_field(name=cmd["title"], value= cmd["value"] ,inline = False)
            for arg in cmd["args"]:
                embed.add_field(name=arg["title"], value= arg["value"] ,inline = True)
            embed.add_field(name="\u200B", value= "\u200B" ,inline = False)
        embed.set_footer(text="(追加中)")
        await message.channel.send(embed=embed)
            
        embed = discord.Embed( 
            title=f"""{self.settingsData["name"]} ver. {self.settingsData["version"]} HELP""",
            color=0xff0000,
            description="その他コマンドについて"
        )
        embed.set_author(
            name=self.user, # Botのユーザー名
            icon_url=self.user.avatar.url # Botのアイコンを設定
        )
            
        #fname="discord.png" # アップロードするときのファイル名
        #file = discord.File(fp=self.directory + "/icon/logo.png",filename=fname,spoiler=False)
        #embed.set_image(url=f"attachment://{fname}")
            
        embed.add_field(name="\u200B", value= "\u200B" ,inline = False)
        embed.add_field(name=helpData["operator"]["title"], value= "", inline = False)
        for operator in helpData["operator"]["aboutOperator"]:
            embed.add_field(name=operator["title"], value= operator["value"] ,inline = True)
            
        embed.add_field(name="\u200B", value= "\u200B" ,inline = False)
        embed.add_field(name=helpData["yuuEmotion"]["title"], value= helpData["yuuEmotion"]["value"], inline = False)
        for cmd in helpData["yuuEmotion"]["cmd"]:
            embed.add_field(name=cmd["title"], value= cmd["value"] ,inline = True)
        
        await message.channel.send(
            #file=file, 
            embed=embed
        )
    async def on_message(self, message): # メッセージを受信
        userName = str(message.author)
        
        # 現在日時を取得
        nowJPNTime = datetime.datetime.now(ZoneInfo("Asia/Tokyo"))
        nowJPNYear = nowJPNTime.year
        nowJPNdate = f"{str(nowJPNTime.month)}/{str(nowJPNTime.day)}"
        nowJPNWeekday = self.weekdayName[nowJPNTime.weekday()]
        nowJPNHour = nowJPNTime.hour
        nowJPNMinute = nowJPNTime.minute
        nowJPNSecond = nowJPNTime.second

        
        # 無視する条件
        messageDeleteLeadingSpace = str(message.content).lstrip()
        if (
            message.author.bot or # メッセージ送信者がBotだった場合は無視する
            (
                messageDeleteLeadingSpace.count("ユウ") == 0 and
                messageDeleteLeadingSpace[0] != "$"
            )
        ):
            return
        
        self.messageChannelID   = message.channel.id
        self.messageUserName    = str(message.author)
        self.messageContent     = str(message.content)
    
        await message.add_reaction("❤️")
        
        if messageDeleteLeadingSpace[0] == "$":
            messageDeleteLeadingSpace = messageDeleteLeadingSpace.replace("$", "", 1)
            
        messageDeleteASCII10 = messageDeleteLeadingSpace.replace("\n","")
        messageDeleteCommas = messageDeleteASCII10.replace("、","")
        messageDeleteOwnName = messageDeleteCommas.replace("ユウ","")
        
        arrangedMessage = str(messageDeleteOwnName)

        with CreateMessage(self.adminID, self.emotionFile, self.eventFilePath) as msg:
            msg.classify_message(arrangedMessage, 1)
            sendTimeLineMessage = msg.get_message()
            if sendTimeLineMessage is None:
                return
            if sendTimeLineMessage.count("reminder") >0:
                await message.channel.send("リマインダ開始")
                await self.reminder(message,msg.get_reminder())
                return
            elif sendTimeLineMessage.count("weather") >0:
                url             = msg.get_weather()
                weatherData     = requests.get(url)
                weatherJSONData = json.loads(weatherData.text)

                if arrangedMessage.count("明日") > 0:
                    dateNumber = 1
                elif arrangedMessage.count("明後日") > 0:
                    dateNumber = 2
                else:
                    dateNumber = 0

                weatherDate = weatherJSONData["forecasts"][dateNumber]["date"]
                weartherTitle = weatherJSONData["title"]
                if dateNumber == 2:
                    weather = weatherJSONData["forecasts"][dateNumber]["telop"]
                else:
                    weather = weatherJSONData["forecasts"][dateNumber]["detail"]["weather"]
                tempMin = weatherJSONData["forecasts"][dateNumber]["temperature"]["min"]["celsius"]
                tempMax = weatherJSONData["forecasts"][dateNumber]["temperature"]["max"]["celsius"]
                telop = weatherJSONData["description"]["text"].replace("　","")
                chanceOfRain0_6 = weatherJSONData["forecasts"][dateNumber]["chanceOfRain"]["T00_06"]
                chanceOfRain6_12 = weatherJSONData["forecasts"][dateNumber]["chanceOfRain"]["T06_12"]
                chanceOfRain12_18 = weatherJSONData["forecasts"][dateNumber]["chanceOfRain"]["T12_18"]
                chanceOfRain18_24 = weatherJSONData["forecasts"][dateNumber]["chanceOfRain"]["T18_24"]
                chanceOfRain = f"""
0時～6時 : {chanceOfRain0_6}
6時～12時 : {chanceOfRain6_12}
12時～18時 : {chanceOfRain12_18}
18時～24時 : {chanceOfRain18_24}
                """
                svgWeatherURL = weatherJSONData["forecasts"][dateNumber]["image"]["url"]
                fileName = svgWeatherURL.split("/")[-1].replace(".svg", "")
    
                svgCode = requests.get(svgWeatherURL).content
    
                #svg2png(bytestring=svgCode,write_to=f"{self.directory}/icon/{fileName}.png")
#
                #file = discord.File (
                #    fp=f"{self.directory}/icon/{fileName}.png",
                #    filename=f"{fileName}.png",
                #    spoiler=False
                #)

                embed = discord.Embed( 
                    title=f"{str(weatherDate)}の{weartherTitle}の詳細",
                    color=0x00ff00,
                    url = url
                )

                #embed.set_thumbnail (url= f"attachment://{fileName}.png")
                embed.set_author(
                    name=weatherJSONData["copyright"]["image"]["title"],
                    icon_url=weatherJSONData["copyright"]["image"]["url"]
                )

                embed.add_field(name="最高気温", value=f"{tempMax}℃", inline = True)
                embed.add_field(name="最低気温", value= f"{tempMin}℃" ,inline = True)
                embed.add_field(name="降水確率", value= chanceOfRain ,inline = True)
                if (arrangedMessage.count("詳細")>0):
                    embed.add_field(name="天気予報", value= telop ,inline = False)
                embed.set_footer(
                    text="(Noneの場合はデータ無し)",
                )

                sendTimeLineMessage = f"{str(weatherDate)}の{weartherTitle}は{weather}"
                if(arrangedMessage.count("-e") == 0):
                    await message.channel.send(
                        sendTimeLineMessage, 
                        embed=embed, 
                        #file=file
                    )
                return

            elif sendTimeLineMessage.count("del") >0:
                mes=[]
                try:
                    for i in arrangedMessage.split(" ")[1:]:
                        mes.append(await message.channel.fetch_message(int(i)))
                    await message.channel.delete_messages(mes)
                    sendTimeLineMessage = "削除完了しました"
                except Exception as e:
                    sendTimeLineMessage = f"失敗しました\n{e}"

            elif sendTimeLineMessage.count("music") >0:
                return
                #if arrangedMessage.count("音楽:") > 0:
                #    musicName = arrangedMessage.split("音楽:")[1]
                #else:
                #    musicName = arrangedMessage.split("music")[1]
                #if (
                #    musicName.count("停止")>0 or
                #    musicName.count("stop")>0
                #):
                #    message.guild.voice_client.pause()
                #    sendTimeLineMessage = "音楽を停止します。"
                #elif (
                #    musicName.count("リスト")>0 or
                #    musicName.count("list")>0
                #):
                #    musicFiles = glob.glob(f"{self.directory}/music/*.mp3")
                #    await self.message_send(f"""{"-" * 5}音楽リスト{"-" * 5}""", message.channel.id)
                #    for file in musicFiles:
                #        file  = file.replace("\\", "/").split(f"{self.directory}/music/")[1]
                #        file = file.split(".mp3")[0]
                #        await self.message_send(file,message.channel.id)
                #    sendTimeLineMessage = "-" * 20
#
                #elif (
                #    musicName.count("切断")>0 or
                #    musicName.count("disconnect")>0
                #):
                #    try:
                #        message.guild.voice_client.stop()
                #    except:
                #        pass
                #    try:
                #        await message.guild.voice_client.disconnect(force=True)
                #    except:
                #        pass
                #    sendTimeLineMessage = "VCから切断します。"
#
                #elif (
                #    musicName.count("再開")>0 or
                #    musicName.count("start")>0
                #):
                #    message.guild.voice_client.resume()
                #    sendTimeLineMessage = "停止を解除します。"
                #else:
                #    musicName = musicName.replace(" ","")
                #    with open(f"{self.directory}/music/music_alias.json", "r", encoding="UTF-8") as musicAliasFile:
                #        musicAliasData = json.loads(musicAliasFile.read())
#
                #    for alias in musicAliasData:
                #        if musicName == alias["alias"]:
                #            musicName = alias["title"]
                #            break
                #        
                #    await self.play_music(musicName, message)
                #    return
                
            elif sendTimeLineMessage.count("calc") >0:
                await message.clear_reaction("❤️")
                await message.add_reaction("❌")
                sendTimeLineMessage = "計算できませんでした"

            elif sendTimeLineMessage.count("search") >0:
                try:
                    searchWord = arrangedMessage.replace("検索:","")
                    searchWordURL = searchWord.replace("　","%E3%80%80")
                    searchWordURL = searchWord.replace(" ","+")
                    searchWordURL = f"https://www.google.co.jp/search?q={searchWordURL}"
                    try:
                        href = web_scraping(searchWordURL, tag = "div span a", num = 0, attribute = "href")
                    except:
                        href = web_scraping(searchWordURL, tag = "a", num = 1, attribute = "href")

                    try:
                        title = web_scraping(searchWordURL, tag = "div span h3", num = 0, attribute = "text")
                    except:
                        title = searchWord

                    if href.count("https://www.google.co") == 0:
                        url = f"https://www.google.co.jp/{href}"
                    else:
                        url = href
                    embed = discord.Embed( 
                        title = title,
                        color = 0xff0000,
                        description = f"{searchWord}の検索結果",
                        url = url
                    )
                    protocol = "https"
                    siteURL = href
                    if siteURL.count("://") > 0:
                        siteURL = siteURL.split("://")[1]
                    else:
                        siteURL = "www.google.co.jp"
                    if siteURL.count("/") > 0:
                        siteURL = siteURL.split("/")[0]
                    try:
                        imgURL = web_scraping(url, tag = "link[rel = 'icon']", num = 0, attribute = "href")
                    except:
                        imgURL = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"

                    if (imgURL.split(".")[-1] == "png") or (imgURL.split(".")[-1] == "jpg"):
                        if imgURL.count("://") == 0:
                            imgURL = f"{protocol}://{siteURL}{imgURL}"

                        embed.set_author(   
                            name = siteURL,
                            icon_url = imgURL,
                            url = f"{protocol}://{siteURL}"
                        )
                        embed.set_thumbnail (url=imgURL)
                        embed.set_footer(
                            text="Searched by Google",
                            icon_url="https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"
                        )
                        await message.channel.send(embed=embed)
                    else:
                        if imgURL.count("://") == 0:
                            imgURL = f"{protocol}://{siteURL}{imgURL}"
                        siteIcon = Image.open(io.BytesIO(requests.get(imgURL).content))
                        siteIcon = siteIcon.convert("RGB")
                        siteIcon.save(f"{self.directory}/icon/{siteURL}.jpg")

                        iconName = f"{siteURL}.jpg" # アップロードするときのファイル名
                        file = discord.File (
                            fp=f"{self.directory}/icon/{siteURL}.jpg",
                            filename=iconName,
                            spoiler=False
                        )
                        embed.set_author(   
                            name = siteURL,
                            icon_url = f"attachment://{iconName}",
                            url = f"{protocol}://{siteURL}"
                        )
                        embed.set_thumbnail (url=f"attachment://{iconName}")
                        embed.set_footer(
                            text="Searched by Google",
                            icon_url="https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"
                        )
                        await message.channel.send(embed=embed, file=file)
                    return
                
                except Exception as e:
                    sendTimeLineMessage = "ERROR"
                    self.botStatus = str(e)

            elif sendTimeLineMessage.count("server") >0:
                try:
                    sendTimeLineMessage = f"現在の{str(message.guild.name)}の人数は{str(message.guild.member_count)}人です。"
                    await self.message_send(sendTimeLineMessage, message.channel.id)
                    channelCount = 0
                    channelCount = len(message.guild.channels)
                    await self.message_send(f"チャンネル総数は{str(channelCount)}個です。\n内訳\n", message.channel.id)
                    dispStatusList = {
                        "カテゴリ" : message.guild.categories,
                        "テキストチャンネル" : message.guild.text_channels,
                        "ボイスチャンネル" : message.guild.voice_channels
                    }
                    for (key, data) in zip(
                        dispStatusList.keys(),
                        dispStatusList.values()
                    ):
                        await self.send_server_status(key, data, message.channel.id)
                    return
                except:
                    try:
                        await message.clear_reaction("❤️")
                    except:
                        pass
                    await message.add_reaction("❌")
                    sendTimeLineMessage = "取得できませんでした"
            
            elif sendTimeLineMessage.count("stop") >0:
                if userName == self.adminName:
                    await message.channel.send("停止します")
                    self.end()
                    return
                else:
                    sendTimeLineMessage = "許可されていません"
                    try:
                        await message.clear_reaction("❤️")
                    except:
                        pass
                    await message.add_reaction("❌")

            elif sendTimeLineMessage.count("whoami") >0:
                sendTimeLineMessage = userName

            elif sendTimeLineMessage.count("events") >0:
                sendTimeLineMessage = msg.get_event(self.messageChannelID)
                

            elif sendTimeLineMessage.count("usecmd") >0:
                if userName == self.adminName:
                    try:
                        commandText = arrangedMessage.split("shell$")[1]
                        sendTimeLineMessage = f"コマンドを実行しました。\n{cmd(commandText)}"
                    except:
                        sendTimeLineMessage = "許可されていません"
                else:
                    sendTimeLineMessage = "許可されていません"
                    try:
                        await message.clear_reaction("❤️")
                    except:
                        pass
                    await message.add_reaction("❌")
            
            elif sendTimeLineMessage.count("lock") >0:
                sendTimeLineMessage = "許可されていません"
                #if userName == self.adminName:
                #    try:
                #        cmd("rundll32.exe user32.dll,LockWorkStation")
                #    except:
                #        pass
                #    sendTimeLineMessage = "ロックしました"
                #else:
                #    sendTimeLineMessage = "許可されていません"

            elif sendTimeLineMessage == "help":
                await self.help_send(message = message)
                return

            elif sendTimeLineMessage.count("callyou") >0:
                sendTimeLineMessage = f"{userName}さん！"

            elif sendTimeLineMessage.count("NotFound") >0:
                sendTimeLineMessage = f"{arrangedMessage}って何？\n喜:h\n褒:c\n驚:p\nアドバイス:a\n叱責:s\n下ネタ:d\n挨拶:g\n不快:r と返信"
                with open(f"{self.directory}/db/temp","a",encoding="UTF-8") as tempFile:
                    writeMessage = f"\n{userName},{arrangedMessage}"
                    tempFile.write(writeMessage)
            
            #処理を飛ばすもの
            elif sendTimeLineMessage.count("chgun") >0:
                return
            elif sendTimeLineMessage.count("fav") >0:
                return
            
            await message.channel.send(sendTimeLineMessage)

if __name__ == "__main__":
    with open(f"{str(os.getcwd().replace(os.path.sep, '/'))}/config/settings.json", "r", encoding="utf-8") as settingsFile:
        settingsData = json.loads(settingsFile.read())

    with MyClient(settingsData) as client:
        pass