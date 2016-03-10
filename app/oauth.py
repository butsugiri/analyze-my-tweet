# -*- coding: utf-8 -*-
from rauth import OAuth1Service
from flask import current_app, url_for, request,redirect,session

class OAuthSignIn(object):
    providers = None #facebook,twitterなどを記憶しておく辞書

    def __init__(self, provider_name):
        self.provider_name = provider_name #facebook, twitter,...
        credentials = current_app.config["OAUTH_CREDENTIALS"][provider_name]
        self.consumer_id = credentials["id"]
        self.consumer_secret = credentials["secret"]

    def authorize(self):
        pass

    def callback(self):
        pass

    def get_callback_url(self):
        return url_for("oauth_callback", provider=self.provider_name, _external=True)

#provider = {プロバイダ:プロバイダクラス}の辞書が空なら，サブクラスをなめて初期化する
#providerごとにoauthのverが別なので，サブクラスとしてプロバイダごとに別々のメソッドを用意しておく．
    @classmethod
    def get_provider(self,provider_name):
        if self.providers is None:
            self.providers = {}
            for provider_class in self.__subclasses__():
                provider = provider_class()
                self.providers[provider.provider_name] = provider
        return self.providers[provider_name]

class TwitterSignIn(OAuthSignIn):
    def __init__(self):
        super(TwitterSignIn, self).__init__("twitter")
        self.service = OAuth1Service(
                name = "twitter",
                consumer_key = self.consumer_id,
                consumer_secret = self.consumer_secret,
                request_token_url='https://api.twitter.com/oauth/request_token',
                authorize_url='https://api.twitter.com/oauth/authorize',
                access_token_url='https://api.twitter.com/oauth/access_token',
                base_url='https://api.twitter.com/1.1/'
                )

    def authorize(self):
        request_token = self.service.get_request_token(
                params = {"oauth_callback": self.get_callback_url()}
                )
        session["request_token"] = request_token
        return redirect(self.service.get_authorize_url(request_token[0]))

    def callback(self):
        request_token = session.pop("request_token")
        if "oauth_verifier" not in request.args:
            return None, None, None, None, None
        oauth_session = self.service.get_auth_session(
                request_token[0],
                request_token[1],
                data = {"oauth_verifier": request.args["oauth_verifier"]}
        )
        me = oauth_session.get("account/verify_credentials.json").json()
        access_token = oauth_session.access_token
        access_token_secret = oauth_session.access_token_secret
        social_id = "twitter$" + str(me.get("id"))
        username = me.get("screen_name")
        return social_id, username, None, access_token, access_token_secret  #Twitterはemailを返さない
