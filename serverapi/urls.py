from django.conf.urls import url
from . import views
from rest_framework_jwt.views import obtain_jwt_token
import serverapi

urlpatterns = [
    url(r'^api-token-auth/', obtain_jwt_token),
	url(r'^roadshow/$', views.RoadshowList.as_view()),
	url(r'^roadshow/(?P<pk>[0-9]+)/$', views.RoadshowDetail.as_view()),
    url(r'^fetch-roadshow/(?P<pk>[0-9]+)/$', views.FetchRoadshow.as_view()),
	url(r'^roadshowcity/$', views.RoadshowCityList.as_view()),
	url(r'^roadshowcity/(?P<pk>[0-9]+)/$', views.RoadshowCityDetail.as_view()),
    url(r'^roadshowdate/$', views.RoadshowDateList.as_view()),
    url(r'^roadshowdate/(?P<pk>[0-9]+)/$', views.RoadshowDateDetail.as_view()),
	url(r'^user/$', views.UserList.as_view(), name='user-list'),
	url(r'^user/(?P<pk>[0-9]+)/$', views.UserDetail.as_view()),
	url(r'^meeting/$', views.MeetingList.as_view()),
    url(r'^meeting/(?P<pk>[0-9]+)/$', views.MeetingDetail.as_view()),
    url(r'^flight/$', views.FlightList.as_view()),
    url(r'^flight/(?P<pk>[0-9]+)/$', views.FlightDetail.as_view()),
    url(r'^rental/$', views.RentalList.as_view()),
    url(r'^rental/(?P<pk>[0-9]+)/$', views.RentalDetail.as_view()),
    url(r'^hotel/$', views.HotelList.as_view()),
    url(r'^hotel/(?P<pk>[0-9]+)/$', views.HotelDetail.as_view()),
    url(r'^expense/$', views.ExpenseList.as_view()),
    url(r'^expense/(?P<pk>[0-9]+)/$', views.ExpenseDetail.as_view()),
    url(r'^logout/', views.Logout.as_view()),
    url(r'^get-roadshow-users/(?P<pk>[0-9]+)/$', views.GetRoadshowUser.as_view()),
    url(r'^groups/$', views.UserGroups.as_view()),
    url(r'^forgot-password/$', views.ForgotPassword.as_view()),
    url(r'^reset-password/(?P<token>[\w\-]+)/$', views.ResetPassword.as_view()),
    url(r'^change-password/(?P<pk>[0-9]+)/$', views.ChangePassword.as_view()),
    url(r'^userslist/$', views.FetchUser.as_view()),
    url(r'^dinner/$', views.DinnerList.as_view()),
    url(r'^dinner/(?P<pk>[0-9]+)/$', views.DinnerDetail.as_view()),
    url(r'^fetch-meetingmodes/$', views.FetchMeetingMode.as_view()),
    url(r'^fetch-meetingtypes/$', views.FetchMeetingType.as_view()),
    url(r'^check-user-meeting/$', views.CheckUserMeeting.as_view()),
    url(r'^remove-user-meeting/$', views.RemoveUserMeeting.as_view()),
    url(r'^roadshow-search/$', views.RoadshowSearch.as_view()),
    url(r'^travel-detail/(?P<pk>[0-9]+)/$', views.TravelDetail.as_view()),
    url(r'^roadshow-expense-all/(?P<pk>[0-9]+)/$', views.RoadshowExpenseAll.as_view()),
    url(r'^roadshow-cities/(?P<pk>[0-9]+)/$', views.RoadshowCities.as_view()),
    url(r'^roadshow-users/(?P<pk>[0-9]+)/$', views.RoadshowUsers.as_view()),
    url(r'^roadshow-filter/(?P<pk>[0-9]+)/$', views.RoadshowFilter.as_view()),
    url(r'^roadshow-latest/$',views.RoadshowLatest.as_view()),
    
    url(r'^companycategory/(?P<pk>[0-9]+)/$', views.CompanyCategoryView.as_view()),
    url(r'^category/$',views.CategoryList.as_view()),
    url(r'^category/(?P<pk>[0-9]+)/$', views.CategoryView.as_view()),
    url(r'^expense-byroadshow/(?P<pk>[0-9]+)/$', views.RoadshowExpenseAllView.as_view()),
    url(r'^expense-bycompany/(?P<pk>[0-9]+)/$', views.RoadshowExpenseCompanyList.as_view()),
    url(r'^datebetween-byroadshow/$', views.RoadshowDateBWView.as_view()),
    url(r'^datebetween-bycompany/$',views.CompanyDateBWView.as_view()),
    url(r'^roadshow-expense-bycategory/$',views.ExpenseByCategoryView.as_view()),
    url(r'^roadshow-expense-byroadshow/$',views.ExpenseByRoadshowView.as_view()),
    url(r'^user-travel-detail/(?P<pk>[0-9]+)/$', views.UserTravelDetail.as_view()),
    url(r'^upload-expense-doc/$', views.ExpenseDocumentList.as_view()),

    url(r'^mobile-roadshow/(?P<pk>[0-9]+)/hotels/$', views.GetHotelList.as_view()),
    url(r'^mobile-roadshow/(?P<pk>[0-9]+)/meetings/$', views.GetMeetingList.as_view()),
    url(r'^mobile-roadshow/(?P<pk>[0-9]+)/traveldetails/$', views.GetTravelDetailList.as_view()),
    url(r'^mobile-roadshow/(?P<pk>[0-9]+)/users/$',views.GetUserDetailList.as_view()),
    url(r'^mobile-roadshow/(?P<pk>[0-9]+)/$', views.MobileRoadshowDetail.as_view()),

    url(r'^meetingsummary/$',views.MeetingSummaryList.as_view()),
    url(r'^meetingsummary/(?P<pk>[0-9]+)/$', views.MeetingSummaryDetail.as_view()),
    url(r'^upload-meeting-file/$',views.MeetingFileList.as_view()),
    url(r'^get-meeting-file/(?P<pk>[0-9]+)/$', views.GetMeetingFileList.as_view()),
    url(r'^mobile-expense/$', views.MobileExpenseList.as_view()),

    url(r'^company-meeting-color/(?P<pk>[0-9]+)/$', views.CompanyMeetingColorView.as_view()),
    url(r'^company-meeting-color/$',views.CompanyMeetingColorList.as_view()),
    url(r'^company-meeting-color-list/(?P<pk>[0-9]+)/$', views.CompanyMeetingColorListView.as_view()),

    # To display Tab view for Present, Past and Future
    url(r'^mobile-roadshow/roadshow/$', views.MobileRoadshowList.as_view()),
    # To fetch compnay default messages
    url(r'^company/default-messages/$', views.CompanyDefaultMessageList.as_view()),
    url(r'^company/default-messages/(?P<pk>[0-9]+)/$', views.CompanyDefaultMessageDetail.as_view()),
    # Generate expense PDF based on compnay id
    #url(r'^expense/pdf/(?P<pk>[0-9]+)/$', views.RoadshowExpenseCompanyPDFList.as_view()),
    # Generate roadshowuser expense pdf and send as email
    url(r'^user-expense/pdf/$', views.GeneratePdfWithRoadshowUser.as_view()),
    # API for Profile get, edit and update
    url(r'^users/(?P<pk>[0-9]+)/$', views.UserProfileList.as_view()),


    url(r'^company-meeting-linkedin/(?P<pk>[0-9]+)/$', views.CompanyLinkedin.as_view()),
    url(r'^company-meeting-twitter/(?P<pk>[0-9]+)/$', views.CompanyTwitterAPI.as_view()),

    url(r'^ajaxcall/$',views.AjaxCallAPI.as_view()),
    
    # To display Tab view for Present, Past and Future
    url(r'^mobile-roadshow/dashboard/$', views.MobileRoadshowDashboard.as_view()),

    url(r'^userpreference/$', views.UserPreferList.as_view()),
    url(r'^mobilemeetingsummary/(?P<pk>[0-9]+)/$', views.MobileMeetingSummaryDetail.as_view()),
]