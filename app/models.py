# -*- coding: utf-8 -*-
from app import db
from flask import current_app
from flask.ext.login import UserMixin
from rauth import OAuth1Session,OAuth1Service
from collections import defaultdict
from datetime import datetime
from lxml import etree
import time,MeCab,re,pickle


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer,primary_key = True)
    social_id = db.Column(db.String(64), nullable=False, unique = True)
    nickname = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=True)
    access_token = db.Column(db.String(140), nullable=False)
    access_token_secret = db.Column(db.String(140),nullable=False)

    def gather_tweet(self):
        credential = current_app.config["OAUTH_CREDENTIALS"]["twitter"]
        twitter = OAuth1Service(
                name='twitter',
                consumer_key=credential["id"],
                consumer_secret=credential["secret"],
                request_token_url='https://api.twitter.com/oauth/request_token',
                access_token_url='https://api.twitter.com/oauth/access_token',
                authorize_url='https://api.twitter.com/oauth/authorize',
                base_url='https://api.twitter.com/1.1/')
        session = OAuth1Session(
                consumer_key = credential["id"],
                consumer_secret = credential["secret"],
                access_token = self.access_token,
                access_token_secret = self.access_token_secret,
                service=twitter
                )

        tweets = []
        r = session.get('statuses/user_timeline.json',params={"count":1}, verify=True)
        tweet_id = r.json()[0]["id"]
        lis = [tweet_id]

        params = {'include_rts': 0,  # exclude retweets
                'count': 200, #200 Tweets
                "max_id":lis[-1]}
        #max_idを更新することで，200Tweetずつ遡って取得
        for i in range(0,4):
            r = session.get('statuses/user_timeline.json', params=params, verify=True)
            tweets += r.json()
            for tweet in r.json():
                lis.append(tweet["id"])
            time.sleep(1)
            params["max_id"] = lis[-1]
        return tweets

#pkl化したtweet_dataを読み込む
#開発中のapi制限を回避するために，ローカルのpklファイルを用いている
    def load_tweet(self):
        f = open("app/data/my_tweet.pkl")
        tweet_data = pickle.load(f)
        return tweet_data

#tweetでよく使われるリプライ先のIDと，
#tweetによく含まれる名詞を抽出する関数
    def count_reply_id_and_noun_freq(self, tweet_data):
        pattern = r"(?P<reply>^@[\w]+\s)(?P<text>.*)"
        repatter = re.compile(pattern)
        noun_count = defaultdict(int)
        at_id_count = defaultdict(int)
        mt = MeCab.Tagger("-Ochasen -d /usr/local/Cellar/mecab/0.996/lib/mecab/dic/mecab-ipadic-neologd/")

        for tweet in tweet_data:
            tmp = re.search(repatter, unicode(tweet["text"]))
            if tmp:
                at_id = tmp.group("reply")
                text = tmp.group("text")
                at_id_count[at_id] += 1
            else:
                text = tweet["text"]
            encoded_tweet = text.encode("utf8")
            node = mt.parseToNode(encoded_tweet)
            while node:
                sur = unicode(node.surface)
                feats = unicode(node.feature).split(",")
                if feats[0] == "名詞" and len(sur) > 1 and feats[2] != "一般":
                    noun_count[sur] += 1
                node = node.next
        return noun_count,at_id_count

#日にち単位でのtweet数
#月単位でのtweet数を両方数えて返す関数
    def count_tweet_per_day_and_month(self,tweet_data):
        day_count = defaultdict(lambda: defaultdict(int))
        month_count = defaultdict(int)
        for tweet in tweet_data:
            created_at = tweet["created_at"].split(" ")
            #Dec → 12へと変換
            month = datetime.strptime(created_at[1], "%b").month
            day = created_at[2]
            month_count[month] += 1
            day_count[month][day] += 1
        #辞書をソートすることを考えると以下のようになる
        # sorted_keys = sorted(day_count.keys())
        # for month in sorted_keys:
        #     for day,count in sorted(day_count[month].items()):
        #         print str(day) + "日に\t" + str(count) + "回発言"
        #     print ""
        return month_count, day_count

#使われてるTwitterクライアントを(client_name, freq)の形式で返す関数
    def count_twitter_client_sums(self,tweet_data):
        client_count = defaultdict(int)

        for tweet in tweet_data:
            client_link = tweet["source"]
            #<a href...>クライアント名</a>から名前だけ抽出する
            client_name = etree.fromstring(client_link).text
            client_name = client_name.encode("utf-8")
            #Tweetbot for iΟSとかいう謎の文字化けを回避
            if "iΟS" in client_name:
                client_name = "Tweetbot for iOS"
            client_count[client_name] += 1
        
        clients = sorted(client_count.items(),key=lambda x:x[1],reverse=True)
        if len(clients) >= 5:
            most_used_four_clients = clients[0:4]
            n = sum([x[1] for x in clients[4::]])
            client_sums =  most_used_four_clients + [("others",n)]
        else:
            client_sums = clients

        sum_of_tweets = len(tweet_data)
        client_percentile = []
        for client_name,freq in client_sums:
            client_percentile.append({
                "name": client_name,
                "y": (freq*1.0/sum_of_tweets) * 100
                })
        return client_percentile

