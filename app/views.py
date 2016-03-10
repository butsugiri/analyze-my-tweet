# -*- coding: utf-8 -*-
from app import app,db,lm
from .models import User
from flask import render_template,redirect,url_for,flash
from flask.ext.login import current_user, login_user,logout_user,login_required
from oauth import OAuthSignIn

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

#oauthの認証手続き: authorizeしてからcallbackの内容読んで
#それをまた送ってアクセストークンゲット
@app.route("/authorize/<provider>")
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for("index"))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()

@app.route("/callback/<provider>")
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth = OAuthSignIn.get_provider(provider)
#viewにaccess_tokenを渡してしまうのはダメだろうか
    social_id, username, email,access_token, access_token_secret = oauth.callback()
    if social_id is None:
        flash('Authentication failed.')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
#新規ユーザならば，データベースに追加
    if not user:
        user = User(
                social_id=social_id,
                nickname=username,
                email=email,
                access_token=access_token,
                access_token_secret=access_token_secret)
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))

@app.route("/user/<nickname>")
@login_required
def user(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    if user == None:
        flash("User %s not found." % nickname)
        return redirect(url_for("index"))
    elif user.id != current_user.id:
        flash("You are not authenticaed.")
        return redirect(url_for("index"))
    tweet_data = user.gather_tweet() #Download user's tweets --> [text]

#頻出名詞と頻出リプライ先の処理
    noun_count,at_id_count = user.count_reply_id_and_noun_freq(tweet_data)
    noun_count = sorted(noun_count.items(), key=lambda x:x[1], reverse=True)[:20]
    at_id_count = sorted(at_id_count.items(), key=lambda x:x[1], reverse=True)

#日にち，月単位のtweetの処理
    chartInfo = {}
    month_count, day_count = user.count_tweet_per_day_and_month(tweet_data)
    chartInfo["chartID"] = "chart_ID"
    chartInfo["chart"] = {
            "renderTo": "chart_ID",
            "type":"line",
            "height": 350
            }

    month_list = [month_count[x] for x in range(1,13)]
    chartInfo["series"] = [{"data": month_list}]
    chartInfo["title"] = {"text": "Tweets per Month"}
    chartInfo["xAxis"] = {
            "categories": ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            }
    chartInfo["yAxis"] = {
            "title": {
                "text": "Tweets"
                },
            "plotLines": [{
                "value": 0,
                "width": 1,
                "color": '#808080'
                }]
            }
#Twitterクライアントの使用割合の分布の処理
    pieInfo = {}
    pieInfo["chartID"] = "pie_chart"
    pieInfo["chart"] = {
            "renderTo": "pie_chart",
            "type": "pie",
            "height":350
            }
    pieInfo["title"] = { "text": "Twitter Client Uses"}
    pieInfo["tooltip"] = {
            "pointFormat": "{series.name}: <b>{point.y:.1f}%</b>"
            }
    pieInfo["plotOptions"] = {
            "pie": {
                "allowPointSelect": "true",
                "cursor": 'pointer',
                "dataLabels": {
                    "enabled": "true",
                    "format": '<b>{point.name}</b>: {point.y:.1f} %'
                    }
                }
            }
    pieInfo["series"] = [{
            "name": "clients",
            "colorByPoint":"true",
            "data":user.count_twitter_client_sums(tweet_data)
            }]
    
    return render_template("user.html",
            title = user.nickname,
            user = user,
            noun_count = noun_count,
            at_id_count = at_id_count,
            chartInfo = chartInfo,
            pieInfo = pieInfo,
            numberOfTweet = str(len(tweet_data)))

