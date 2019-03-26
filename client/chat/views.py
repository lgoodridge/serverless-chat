from django.shortcuts import render
from uniauth.decorators import login_required

@login_required
def index(request):
    return render(request, 'chat/index.html')
