from django.shortcuts import render
from uniauth.decorators import login_required
import jwt
import os


@login_required
def index(request):
    token = jwt.encode({"username": request.user.username}, "FAKE_SECRET",
            algorithm="HS256").decode("utf-8")
    return render(request, "chat/index.html",
            {"endpoint": os.environ["WEBSOCKET_ENDPOINT"], "token": token})

