import json

from serverapi.serializers import *
from django.utils import timezone
from serverapi.models import UserLogin, Company

def update_user_login(user):
    user.userlogin_set.create(timestamp=timezone.now())
    user.save()

def jwt_response_payload_handler(token, user=None, request=None):
    update_user_login(user)
    login_count = len(UserLogin.objects.filter(user=user))
    company = Company.objects.filter(users__id=user.id)
    c_data = {}
    settings_data = {}
    if company:
        c_data = {'id': company[0].id, 'name': company[0].name}
        company_meeting_colors = CompanyMeetingColor.objects.filter(company_id=company[0].id)
        if company_meeting_colors:
            settings_data = {
                'company_meeting_colors': [
                    {'id': x.id, 'name': x.name, 'color': x.color} for x in company_meeting_colors
                ]
            }
    print UserSerializer(user).data
    return {
        'token': token,
        'user': UserSerializer(user).data,
        'user_group': [x.name for x in user.groups.all()],
        'login_count': login_count,
        'company': c_data,
        'settings': settings_data
    }