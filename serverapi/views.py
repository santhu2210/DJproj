import json
import datetime
import datetime as dt
import urllib
import mutagen
import audioread
import subprocess
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3 as ID3
from moviepy.editor import VideoFileClip

from lxml import html
import csv, os
import requests
from exceptions import ValueError
from time import sleep
import urllib3

from django.db.models import Q
from django.shortcuts import render
from django.template.loader import render_to_string
from serverapi.models import *
from serverapi.serializers import *
from django.http import Http404, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from django.core import serializers
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework import status
from django.contrib.auth import logout
from django.contrib.auth.models import Group
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password
from operator import itemgetter
from urllib import urlretrieve
from io import BytesIO
from .pdf_utils import PdfGenerate
from ago import human

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


class RoadshowList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	
	queryset = Roadshow.objects.all()
	serializer_class = RoadshowSerializer

	def list(self, request):
		#data = self.get_queryset()
		#data = [(date, Roadshow.objects.filter(from_date__year=date.year, from_date__month=date.month)) for date in Roadshow.objects.dates('from_date', 'month')]
		company = Company.objects.filter(users__id=request.user.id)
		roadshow_ids = CompanyRoadshow.objects.filter(company=company[0]).values_list('roadshow')
		if roadshow_ids:
			data = [
				[
					date,
					Roadshow.objects.filter(id__in = roadshow_ids, from_date__year=date.year)
				] for date in Roadshow.objects.filter(id__in = roadshow_ids).dates('from_date', 'year')
			]
			parent_list = []
			for k, v in dict(data).iteritems():
				parent_dict = {}
				#parent_dict[k.year] = json.loads(serializers.serialize('json', v))
				parent_dict['year'] = k.year
				parent_dict['passed_year'] = True if (datetime.datetime.now().year == k.year) else False
				parent_dict['data'] = json.loads(serializers.serialize('json', v))
				parent_list.append(parent_dict)
			return Response(sorted(parent_list, key=itemgetter('year'), reverse=True))
		else:
			return Response(roadshow_ids, status=status.HTTP_204_NO_CONTENT)

	def post(self, request, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		serializer = RoadshowSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			company = Company.objects.filter(users__id=request.user.id)
			if company:
				CompanyRoadshow.objects.create(roadshow_id=serializer.data['id'], company=company[0])
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoadshowDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	
	queryset = Roadshow.objects.all()
	serializer_class = RoadshowSerializer

	def calculate_weather(self, address, meeting_date):
		date = meeting_date.strftime("%d %b %Y")
		weather_dic ={}
		try:
			url = \
			'https://query.yahooapis.com/v1/public/yql?q=select * from weather.forecast where woeid in (select woeid from geo.places(1) where text="{0}")&format=json&/'.format(address)
			response = urllib.urlopen(url)
			# print url
			obj = json.load(response)
			if obj['query']['results'] != None:
				for i in range (0,9):
					json_date = obj['query']['results']['channel']['item']['forecast'][i]['date']
					if (date==json_date):
						weather_dic['forecast'] = obj['query']['results']['channel']['item']['forecast'][i]['high']
						weather_dic['description'] = obj['query']['results']['channel']['item']['forecast'][i]['text']
						weather_dic['code'] = obj['query']['results']['channel']['item']['forecast'][i]['code']
			else:
				weather_dic['forecast'] = ''
				weather_dic['description'] = ''
				weather_dic['code'] = ''
		except:
			pass
		return weather_dic


	def calculate_user_meeting_overlap(self, meeting, prev_meeting_end_time):
		from datetime import timedelta
		from datetime import datetime
		FMT = '%H:%M'
		time_differnce = datetime.strptime(meeting.end_time, FMT) - datetime.strptime(prev_meeting_end_time, FMT)

		meeting_users = MeetingUser.objects.filter(
			meeting_id=meeting.id
		)
		time_status = []
		for mUser in meeting_users:
			if not mUser.duration.isdigit():
				time_split = [x for x in mUser.duration.split(' ') if x.isdigit()]
				# check minutes or hours
				if len(time_split) == 1:
					user_time = timedelta(minutes=int(time_split[0]))
					time_status.append(user_time > time_differnce)
				else:
					user_time = timedelta(hours=int(time_split[0]),minutes=int(time_split[1]))
					time_status.append(user_time > time_differnce)
		return True in time_status

	def calculate_roadshow_dashboard(self, road_show, roadshow_dates_list):
		parent_list = []
		for m_date in roadshow_dates_list:
			parent_dict = {}
			parent_dict['date'] = m_date
			parent_dict['date_in_string'] = m_date.strftime('%d %b %A')
			meetings_list = road_show.meetings.filter(meeting_date=m_date).order_by('start_time')
			flights_list = road_show.roadshowflights.filter(from_date=m_date)
			cars_list = road_show.roadshowrentals.filter(from_date=m_date)
			dinner_list = road_show.roadshowdinner.filter(dinner_date=m_date)
			hotels_list = road_show.roadshowhotels.filter(from_date=m_date)

			data_list = []
			if meetings_list:
				for index, meeting_data in enumerate(meetings_list):
					m_dict = {}
					m_dict['id'] = meeting_data.id
					m_dict['name'] = meeting_data.company_name
					m_dict['timeStart'] = meeting_data.start_time
					m_dict['timeEnd'] = meeting_data.end_time
					m_dict['city'] = meeting_data.city
					m_dict['meeting_type'] = meeting_data.meeting_type.name
					# m_dict['distance_prev'] = meeting_data.distance_prev
					m_dict['address'] = meeting_data.address
					user_count = meeting_data.meetingusers.count()
					m_dict['user_count'] = user_count
					if user_count <= 1 and user_count != 0:
						# If single user goes to meeting
						meeting_user = MeetingUser.objects.get(
							meeting_id=meeting_data.id
						)
						m_dict['user_duration'] = meeting_user.duration
						m_dict['distance_prev'] = meeting_user.distance
					else:
						# if user count > 1 this is for front end team
						m_dict['user_duration'] = 0
						m_dict['distance_prev'] = meeting_data.distance_prev
					m_dict['type'] = 'meeting'
					m_dict['already_time_exists'] = meeting_data.start_time in \
						[x['timeStart'] for x in data_list]
					if meeting_data == meetings_list.last():
						m_dict['is_last_meeting'] = True
					else:
						m_dict['is_last_meeting'] = False
					if meeting_data != meetings_list.first():
						try:
							prev_entity = meetings_list[index-1]
							m_dict['prev_entity_id'] = prev_entity.id
							m_dict['prev_entity_type'] = 'meeting'
							m_dict['user_time_overlap'] = self.calculate_user_meeting_overlap(
								meeting_data,
								prev_entity.end_time
							)
						except:
							pass
					m_dict['weather'] = self.calculate_weather(meeting_data.address, m_date)
					m_action_color = []
					m_action_color = MeetingColor.objects.filter(meeting_id=meeting_data.id)
					m_action_color = [
						{
							'id': x.company_meeting_color_id,
							'name': CompanyMeetingColor.objects.get(id=x.company_meeting_color_id).name,
							'color': CompanyMeetingColor.objects.get(id=x.company_meeting_color_id).color
						} for x in m_action_color]
					m_dict['company_meeting_action_color'] = m_action_color

					data_list.append(m_dict)
			if flights_list:
				for flight_data in flights_list:
					f_dict = {}
					f_dict['id'] = flight_data.id
					f_dict['name'] = flight_data.airline
					f_dict['timeStart'] = flight_data.start_time
					f_dict['timeEnd'] = flight_data.end_time
					f_dict['address'] = flight_data.to_airport
					f_dict['user_count'] = flight_data.users.count()
					f_dict['type'] = 'flight'
					data_list.append(f_dict)
			if cars_list:
				for car_data in cars_list:
					c_dict = {}
					c_dict['id'] = car_data.id
					c_dict['name'] = car_data.rental_name
					c_dict['timeStart'] = car_data.start_time
					c_dict['timeEnd'] = car_data.end_time
					c_dict['user_count'] = car_data.users.count()
					c_dict['type'] = 'cab'
					data_list.append(c_dict)
			if dinner_list:
				for dinner_data in dinner_list:
					d_dict = {}
					d_dict['id'] = dinner_data.id
					d_dict['name'] = dinner_data.name
					d_dict['timeStart'] = dinner_data.start_time
					d_dict['timeEnd'] = dinner_data.end_time
					d_dict['user_count'] = dinner_data.users.count()
					d_dict['type'] = 'dinner'
					data_list.append(d_dict)
			hotel_data_list = []
			if hotels_list:
				for hotel_data in hotels_list:
					h_dict = {}
					h_dict['id'] = hotel_data.id
					h_dict['name'] = hotel_data.hotel_name
					h_dict['timeStart'] = hotel_data.start_time
					h_dict['timeEnd'] = hotel_data.end_time
					h_dict['address'] = hotel_data.hotel_address
					h_dict['user_count'] = hotel_data.users.count()
					if meetings_list:
						h_dict['distance_prev'] = hotel_data.distance_prev
						h_dict['prev_entity_id'] = meetings_list.last().id
						h_dict['prev_entity_type'] = 'meeting'
					h_dict['type'] = 'hotel'
					h_dict['parent_hotel_id'] = hotel_data.parent_hotel_id
					hotel_data_list.append(h_dict)
			# Sorting the list of dict by the time start time
			#parent_dict['schedule'] = data_list
			parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
			# Keep the hotel object at the last as per the requirement

			parent_dict['schedule'] = parent_dict['schedule'] + hotel_data_list
			
			# Calculate the distance logic for the previous date last entity and current date first entity
			if parent_list:
				if parent_list[-1]['schedule']:
					if parent_dict['schedule'] and parent_dict['schedule'][0]['type'] == 'meeting':
						try:
							origin = parent_list[-1]['schedule'][-1]['address']
							destination = parent_dict['schedule'][0]['address']
							url = \
							'https://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&key={2}'.format(
								origin, destination, settings.GOOGLE_API_KEY
							)
							response = urllib.urlopen(url)
							distance = json.load(response)
							if distance['rows'][0]['elements'][0]['status'] != 'NOT_FOUND':
								distance = distance['rows'][0]['elements'][0]['distance']['value']
							else:
								distance = 0
						except:
						    # Address Not Found
						    distance = 0
						parent_dict['schedule'][0]['distance_prev'] = distance
						parent_dict['schedule'][0]['prev_entity_id'] = parent_list[-1]['schedule'][-1]['id']
						parent_dict['schedule'][0]['prev_entity_type'] = parent_list[-1]['schedule'][-1]['type']
			# count = 0
			# for x in parent_dict['schedule']:
			#     try:
			# 		origin = parent_dict['schedule'][count]['address']
			# 		destination = parent_dict['schedule'][count+1]['address']
			# 		url = \
			# 		'https://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&key={2}'.format(
			# 			origin, destination, settings.GOOGLE_API_KEY
			# 		)
			# 		response = urllib.urlopen(url)
			# 		distance = json.load(response)
			# 		if distance['rows'][0]['elements'][0]['status'] != 'NOT_FOUND':
			# 			distance = distance['rows'][0]['elements'][0]['distance']['value']
			# 		else:
			# 			distance = 0
			#     except:
			#         distance = 0
			#     count += 1
			#     x['distance_prev'] = distance

			parent_list.append(parent_dict)
		return parent_list

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)

		start_date = road_show.from_date
		end_date = road_show.to_date

		total_days = (end_date - start_date).days + 1

		roadshow_dates_list = [(start_date + dt.timedelta(days = day_number)) \
			for day_number in range(total_days)]

		# data = [[date, road_show.meetings.filter(meeting_date__day=date.day)] \
		# 	for date in road_show.meetings.dates('meeting_date', 'day')]
		
		output_list = self.calculate_roadshow_dashboard(road_show, roadshow_dates_list)

		# for k,v in dict(data).iteritems():
		# 	#check the meeting data exists the roadshow between roadshow dates
		# 	parent_dict = {}
		# 	parent_dict['date'] = k
		# 	meeting_data_list = []
		# 	for meeting_data in v:
		# 		m_dict = {}
		# 		m_dict['id'] = meeting_data.id
		# 		m_dict['name'] = meeting_data.company_name
		# 		m_dict['timeStart'] = meeting_data.start_time
		# 		m_dict['timeEnd'] = meeting_data.end_time
		# 		m_dict['city'] = meeting_data.city
		# 		m_dict['type'] = 'meeting'
		# 		meeting_data_list.append(m_dict)
		# 	parent_dict['schedule'] = meeting_data_list
		# 	#parent_dict['schedule'] = json.loads(serializers.serialize('json', v))
		# 	parent_list.append(parent_dict)
		return Response(output_list)


	def get_obj(self, pk):
		try:
		    return Roadshow.objects.get(pk=pk)
		except Roadshow.DoesNotExist:
		    raise Http404

	def put(self, request, pk, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		obj = self.get_obj(pk)
		serializer = RoadshowSerializer(obj, data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RoadshowCityList(generics.ListCreateAPIView):
	queryset = RoadshowCity.objects.all()
	serializer_class = RoadshowCitySerializer


class RoadshowCityDetail(generics.RetrieveUpdateDestroyAPIView):
	queryset = RoadshowCity.objects.all()
	serializer_class = RoadshowCitySerializer


class RoadshowDateList(generics.ListCreateAPIView):
	queryset = RoadshowDate.objects.all()
	serializer_class = RoadshowDateSerializer


class RoadshowDateDetail(generics.RetrieveUpdateDestroyAPIView):
	queryset = RoadshowDate.objects.all()
	serializer_class = RoadshowDateSerializer


class FlightList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowFlight.objects.all()
	serializer_class = RoadshowFlightSerializer

	def post(self, request, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		serializer = RoadshowFlightSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class FlightDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowFlight.objects.all()
	serializer_class = RoadshowFlightSerializer

	def get_obj(self, pk):
		try:
		    return RoadshowFlight.objects.get(pk=pk)
		except RoadshowFlight.DoesNotExist:
		    raise Http404

	def put(self, request, pk, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		obj = self.get_obj(pk)
		serializer = RoadshowFlightSerializer(obj, data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request, pk, format=None):
		obj = self.get_obj(pk)
		flight_dic = {}
		# print obj.rental_address
		flight_dic['roadshow_id'] = obj.roadshow_id
		flight_dic['airline'] = obj.airline
		flight_dic['airline_class'] = obj.airline_class
		flight_dic['from_airport'] = obj.from_airport
		flight_dic['to_airport'] = obj.to_airport
		flight_dic['from_date_time'] = obj.from_date_time
		flight_dic['to_date_time'] = obj.to_date_time
		flight_dic['start_time'] = obj.start_time
		flight_dic['end_time'] = obj.end_time
		flight_dic['from_date'] = obj.from_date
		flight_dic['to_date'] = obj.to_date
		flight_dic['distance_to_next'] = obj.distance_to_next
		flight_dic['distance_to_prev'] = obj.distance_to_prev
		flight_dic['minutes_to_next'] = obj.minutes_to_next
		flight_dic['minutes_to_prev'] = obj.minutes_to_prev
		flight_dic['status'] = obj.status
		flight_dic['source_flight_code'] = obj.source_flight_code,
		flight_dic['destination_flight_code'] = obj.destination_flight_code
		flight_dic['users'] = [user.id for user in obj.users.all()]
		flight_dic['mobile_users'] =  [
			{
				"full_name": '{0} {1}'.format(user.first_name, user.last_name),
				"role":Group.objects.get(user=user).name,
				"id": user.id,
				"contact_phone": user.user_profile.contact_phone if UserProfile.objects.filter(user=user) else '',
				"profile_pic": \
					['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
						for user_profile in UserProfile.objects.filter(user=user) if user_profile.profile_pic]
			} for user in obj.users.all()
		]

		return Response(flight_dic)


class MeetingList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	queryset = Meeting.objects.all()
	serializer_class = RoadshowMeetingSerializer

	def update_hotel_distance(self, origin_address, hotel_obj):
		destination = "{0}, {1}, {2}".format(
			hotel_obj.hotel_address,
			hotel_obj.city,
			hotel_obj.pincode,
		)
		url = \
		'https://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&key={2}'.format(
			origin_address, destination, settings.GOOGLE_API_KEY
		)
		response = urllib.urlopen(url)
		distance = json.load(response)

		try:
			if distance['rows'][0]['elements'][0]['status'] != 'ZERO_RESULTS' or obj['rows'][0]['elements'][0]['status'] != 'NOT_FOUND':
				hotel_obj.distance_prev = distance['rows'][0]['elements'][0]['distance']['value']
				hotel_obj.save()
				return True
		except:
			return False

	def post(self, request, format=None):
		roadshow = Roadshow.objects.get(id=request.data['roadshow'])
		meet_list = Meeting.objects.filter(roadshow=roadshow, meeting_date=request.data['meeting_date'])
		hotel_list = RoadshowHotel.objects.filter(roadshow=roadshow, from_date=request.data['meeting_date'])
		if meet_list:
			m_last = meet_list.last()
			from_add = m_last.address 									# recently added
			from_cty = m_last.city
			from_pncd = m_last.postcode
			origin = "{0}, {1}, {2}".format(m_last.address, m_last.city, m_last.postcode)
			destination = "{0}, {1}, {2}".format(
				request.data['address'],
				request.data['city'],
				request.data['postcode'],
			)
			url = \
			'https://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&key={2}'.format(
				origin, destination, settings.GOOGLE_API_KEY
			)
			response = urllib.urlopen(url)
			distance = json.load(response)

			try:
				if distance['rows'][0]['elements'][0]['status'] != 'ZERO_RESULTS' or obj['rows'][0]['elements'][0]['status'] != 'NOT_FOUND':
					request.data['distance_prev'] = distance['rows'][0]['elements'][0]['distance']['value']
				else:
					request.data['distance_prev'] = 0
			except:
				pass
		# Assign the created by user
		request.data['created_by'] = request.user.id
		m_users = request.data['users']
		# Extract the users list with mode of travel from the dict
		del request.data['users']
		serializer = RoadshowMeetingSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			if hotel_list:
				origin = "{0}, {1}, {2}".format(
					request.data['address'],
					request.data['city'],
					request.data['postcode'],
				)
				self.update_hotel_distance(origin, hotel_list.last())
			if m_users:
				for m_user in m_users:
					MeetingUser.objects.create(
						meeting_id=serializer.data['id'],
						user_id=m_user['user_id'],
						meeting_mode_id=m_user['mode_id'],
						duration=m_user['duration'],
						distance=int(m_user['distance']),
						to_address= request.data['address'],
						to_city = request.data['city'],
						from_address=from_add,							# reacently added for hotel
						from_city=from_cty

					)
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeetingDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = Meeting.objects.all()
	serializer_class = RoadshowMeetingSerializer

	def get_obj(self, pk):
		try:
		    return Meeting.objects.get(pk=pk)
		except Meeting.DoesNotExist:
		    raise Http404

	def update_meeting_distance(self, data_list):
		count = 0
		data_length = len(data_list)-1
		for x in old_date_meetings_list:
		    try:
				origin = "{0}, {1}, {2}".format(
					x[count]['address'],
					x[count]['city'],
					x[count]['postcode']
				)
				destination = "{0}, {1}, {2}".format(
					x[count+1]['address'],
					x[count+1]['city'],
					x[count+1]['postcode'],
				)
				url = \
				'https://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&key={2}'.format(
					origin, destination, settings.GOOGLE_API_KEY
				)
				response = urllib.urlopen(url)
				distance = json.load(response)
				if distance['rows'][0]['elements'][0]['status'] != 'NOT_FOUND':
					distance = distance['rows'][0]['elements'][0]['distance']['value']
				else:
					distance = 0
		    except:
		        # Address Not Found
		        distance = 0
		    count += 1
		    if not data_length == count:
			    x.distance_next = distance
			    x.save()


	def reorder_the_list(self, from_data, to_data):
		old_date_meetings_list = Meeting.objects.filter(
			meeting_date=from_data['meeting_date']
		).order_by('start_time')
		old_date_hotels_list = RoadshowHotel.objects.filter(
			from_date=from_data['from_date']
		).order_by('start_time')
		new_date_meetings_list = Meeting.objects.filter(
			meeting_date=from_data['meeting_date']
		).order_by('start_time')
		new_date_hotels_list = RoadshowHotel.objects.filter(
			from_date=from_data['from_date']
		).order_by('start_time')

		############ Update old meetings data distance ####################
		self.update_meeting_distance(old_date_meetings_list)
		self.update_meeting_distance(new_date_meetings_list)
		


	def put(self, request, pk, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		obj = self.get_obj(pk)
		serializer = RoadshowMeetingSerializer(obj, data=request.data)
		if serializer.is_valid():
			serializer.save()
			if (serializer.data['address'] != request.data['address']):
				self.reorder_the_list(serializer.data, request.data)
			m_users = request.data['users']
			if m_users:
				for m_user in m_users:
					muser, created = MeetingUser.objects.update_or_create(
						meeting_id=serializer.data['id'],
						user_id=m_user['user_id'],
						defaults={
							'meeting_mode_id': m_user['mode_id'],
							'distance': int(m_user['distance']),
							'duration': m_user['duration'],
						}
					)
			meetingusers =[m.user_id for m in MeetingUser.objects.filter(
				meeting_id=serializer.data['id']
			)]
			
			differnce = list(set(meetingusers) - set([u['user_id'] for u in m_users]))
			if differnce:
				for duser in differnce:
						MeetingUser.objects.filter(
							meeting_id=serializer.data['id'],
							user_id=duser
						).delete()
			if 'company_meeting_action_color' in request.data.keys():
				meeting_color, created = MeetingColor.objects.update_or_create(
					meeting_id=pk,
					defaults={
							'company_meeting_color_id': request.data['company_meeting_action_color'],
					}
				)
			m_color = MeetingColor.objects.filter(meeting_id=pk)
			m_action_color = []
			if m_color:
				m_action_color = [
				{
					'id': m_color[0].company_meeting_color.id,
					'name': m_color[0].company_meeting_color.name,
					'color': m_color[0].company_meeting_color.color
				}]
			meeting_data = serializer.data
			meeting_data.update({'company_meeting_action_color': m_action_color})
			return Response(meeting_data, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request, pk, format=None):
		obj = self.get_obj(pk)
		serializer = RoadshowMeetingSerializer(obj)
		m_users = []
		m_action_color = []
		if obj:
			m_users = MeetingUser.objects.filter(meeting=obj)
			m_action_color = MeetingColor.objects.filter(meeting=obj)
		m_users = [
			{
				'user_id': muser.user.id,
				'mode_id': muser.meeting_mode.id,
				'duration': muser.duration,
				'distance': muser.distance,
				'full_name': '{0} {1}'.format(muser.user.first_name,muser.user.last_name),
				'role': Group.objects.get(user=muser.user).name,
				'contact_phone': muser.user.user_profile.contact_phone if UserProfile.objects.filter(user=muser.user) else '',
				'profile_pic': \
					['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
						for user_profile in UserProfile.objects.filter(user=muser.user) if user_profile.profile_pic]
			} for muser in m_users]
		meeting_data = serializer.data
		meeting_data.update({'users': m_users})
		m_action_color = [
			{
				'id': x.company_meeting_color_id,
				'name': CompanyMeetingColor.objects.get(id=x.company_meeting_color_id).name,
				'color': CompanyMeetingColor.objects.get(id=x.company_meeting_color_id).color
			} for x in m_action_color]
		meeting_data.update({'company_meeting_action_color': m_action_color})
		return Response(meeting_data)

	def delete(self, request, pk, format=None):
		meeting = self.get_obj(pk)
		meeting.delete()
		return Response({"message": "Meeting deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


class RentalList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowRental.objects.all()
	serializer_class = RoadshowRentalSerializer

	def post(self, request, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		request.data['to_date'] = request.data['to_date'] if request.data['to_date'] else None
		serializer = RoadshowRentalSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RentalDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowRental.objects.all()
	serializer_class = RoadshowRentalSerializer

	def get_obj(self, pk):
		try:
		    return RoadshowRental.objects.get(pk=pk)
		except RoadshowRental.DoesNotExist:
		    raise Http404

	def put(self, request, pk, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		obj = self.get_obj(pk)
		request.data['to_date'] = request.data['to_date'] if request.data['to_date'] else None
		serializer = RoadshowRentalSerializer(obj, data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request, pk, format=None):
		obj = self.get_obj(pk)
		rental_dic = {}
		rental_dic['roadshow_id'] = obj.roadshow_id
		rental_dic['rental_address'] = obj.rental_address
		rental_dic['rental_name'] = obj.rental_name
		rental_dic['rental_email'] = obj.rental_email
		rental_dic['rental_phone'] = obj.rental_phone
		rental_dic['from_date'] = obj.from_date
		rental_dic['to_date'] = obj.to_date
		rental_dic['start_time'] = obj.start_time
		rental_dic['end_time'] = obj.end_time
		rental_dic['from_city'] = obj.from_city
		rental_dic['to_city'] = obj.to_city
		rental_dic['from_address'] = obj.from_address
		rental_dic['to_address'] = obj.to_address
		rental_dic['from_pincode'] = obj.from_pincode
		rental_dic['to_pincode'] = obj.to_pincode
		rental_dic['rental_type'] = obj.rental_type
		rental_dic['status'] = obj.status
		rental_dic['confirmation_code'] = obj.confirmation_code
		rental_dic['from_state'] = obj.from_state
		rental_dic['to_state'] = obj.to_state
		rental_dic['is_prepaid'] = obj.is_prepaid
		rental_dic['users'] = [user.id for user in obj.users.all()]
		rental_dic['mobile_users'] =  [
			{
				"full_name": '{0} {1}'.format(user.first_name, user.last_name),
				"role":Group.objects.get(user=user).name,
				"id": user.id,
				"contact_phone": user.user_profile.contact_phone if UserProfile.objects.filter(user=user) else '',
				"profile_pic": \
					['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
						for user_profile in UserProfile.objects.filter(user=user) if user_profile.profile_pic]
			} for user in obj.users.all()
		]

		return Response(rental_dic)


class HotelList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowHotel.objects.all()
	serializer_class = RoadshowHotelSerializer

	def auto_update_hotel_for_dates(self, data, created_by, hotel_id):
		start = datetime.datetime.strptime(data['from_date'], "%Y-%m-%d")
		end = datetime.datetime.strptime(data['to_date'], "%Y-%m-%d")
		date_generated = \
			[(start + datetime.timedelta(days=x)).strftime('%Y-%m-%d') for x in range(0, (end-start).days+1)]
		# remove first date
		del date_generated[0]
		for d in date_generated:
			try :
				r = RoadshowHotel.objects.create(
					hotel_phone=data['hotel_phone'],
					roadshow_id=data['roadshow'],
					start_time=data['start_time'],
					created_by=created_by,
					from_date=d,
					hotel_address=data['hotel_address'],
					hotel_email=data['hotel_email'],
					city=data['city'],
					pincode=data['pincode'],
					end_time=data['end_time'],
					hotel_name=data['hotel_name'],
					to_date=data['to_date'],
					parent_hotel_id=hotel_id
				)
				for u in data['users']:
					r.users.add(u)
			except:
				pass

	def post(self, request, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		serializer = RoadshowHotelSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			self.auto_update_hotel_for_dates(request.data, request.user, serializer.data['id'])
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HotelDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowHotel.objects.all()
	serializer_class = RoadshowHotelSerializer


	def auto_update_hotel_for_dates(self, data, created_by, hotel_id):
		start = datetime.datetime.strptime(data['from_date'], "%Y-%m-%d")
		end = datetime.datetime.strptime(data['to_date'], "%Y-%m-%d")
		date_generated = \
			[(start + datetime.timedelta(days=x)).strftime('%Y-%m-%d') for x in range(0, (end-start).days+1)]
		# remove first date
		del date_generated[0]
		for d in date_generated:
			r = RoadshowHotel.objects.create(
				hotel_phone=data['hotel_phone'],
				roadshow_id=data['roadshow'],
				start_time=data['start_time'],
				created_by=created_by,
				from_date=d,
				hotel_address=data['hotel_address'],
				hotel_email=data['hotel_email'],
				city=data['city'],
				pincode=data['pincode'],
				end_time=data['end_time'],
				hotel_name=data['hotel_name'],
				to_date=data['to_date'],
				parent_hotel_id=hotel_id
			)
			for u in data['users']:
				r.users.add(u)

	def get_obj(self, pk):
		try:
		    return RoadshowHotel.objects.get(pk=pk)
		except RoadshowHotel.DoesNotExist:
		    raise Http404

	def delete(self, request, pk, format=None):
		hotel = self.get_obj(pk)
		hotel.delete()
		# To delete the associated hotel records
		RoadshowHotel.objects.filter(
			parent_hotel_id=pk
		).delete()
		return Response({"message": "Hotel deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

	def put(self, request, pk, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		obj = self.get_obj(pk)
		'''
		While editing no changes in date then do update functionality. If change in date
		then delete existing hotels and create hotel as new.
		'''
		if (obj.from_date.strftime("%Y-%m-%d") == request.data['from_date']) and \
			(obj.to_date.strftime("%Y-%m-%d") == request.data['to_date']):
			serializer = RoadshowHotelSerializer(obj, data=request.data)
			if serializer.is_valid():
				serializer.save()
				return Response(serializer.data, status=status.HTTP_201_CREATED)
		else:
			RoadshowHotel.objects.filter(
				parent_hotel_id=obj.id
			).delete()
			obj.delete()
			serializer = RoadshowHotelSerializer(data=request.data)
			if serializer.is_valid():
				serializer.save()
				self.auto_update_hotel_for_dates(request.data, request.user, serializer.data['id'])
				return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def get(self, request, pk, format=None):
		obj = self.get_obj(pk)
		hotel_dic = {}
		hotel_dic['roadshow_id'] = obj.roadshow_id
		hotel_dic['id'] = obj.id
		hotel_dic['hotel_address'] = obj.hotel_address
		hotel_dic['hotel_name'] = obj.hotel_name
		hotel_dic['hotel_email'] = obj.hotel_email
		hotel_dic['hotel_phone'] = obj.hotel_phone
		hotel_dic['from_date'] = obj.from_date
		hotel_dic['to_date'] = obj.to_date
		hotel_dic['start_time'] = obj.start_time
		hotel_dic['end_time'] = obj.end_time
		hotel_dic['city'] = obj.city
		hotel_dic['distance_next'] = obj.distance_next
		hotel_dic['distance_prev'] = obj.distance_prev
		hotel_dic['pincode'] = obj.pincode
		hotel_dic['parent_hotel_id'] = obj.parent_hotel_id
		hotel_dic['status'] = obj.status
		hotel_dic['state'] = obj.state
		hotel_dic['users'] = [user.id for user in obj.users.all()]

		# mobile_ users = [{"full_name": '{0} {1}'.format(x.first_name, x.last_name), "role":Group.objects.get(user=x).name} for x in obj.users.all() ]
		hotel_dic['mobile_users'] =  [
			{
				"full_name": '{0} {1}'.format(user.first_name, user.last_name),
				"role": Group.objects.get(user=user).name,
				"first_name": user.first_name,
				"last_name": user.last_name,
				"contact_phone": user.user_profile.contact_phone if UserProfile.objects.filter(user=user) else '',
				"id": user.id,
				"profile_pic": \
					['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
						for user_profile in UserProfile.objects.filter(user=user) if user_profile.profile_pic]
			} for user in obj.users.all()
		]


		return Response(hotel_dic)


class ExpenseList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowExpense.objects.all()
	serializer_class = RoadshowExpenseSerializer

	def post(self, request, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		serializer = RoadshowExpenseSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			file_ids = request.data['docs']
			expense_doc = ExpenseDocument.objects.filter(id__in=file_ids).update(
				expense=serializer.data['id']
			)
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpenseDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowExpense.objects.all()
	serializer_class = RoadshowExpenseSerializer

	def get_obj(self, pk):
		try:
		    return RoadshowExpense.objects.get(pk=pk)
		except RoadshowExpense.DoesNotExist:
		    raise Http404

	def get(self, request, pk, format=None):
		obj = self.get_obj(pk)
		serializer = RoadshowExpenseSerializer(obj)
		docs = []
		if obj:
			docs = ExpenseDocument.objects.filter(expense=obj)
		docs = [{
			'id': document.id,
			'docfile': request.build_absolute_uri('{0}/{1}'.format(settings.MEDIA_URL, document.docfile))} for document in docs]
		expense_data = serializer.data
		expense_data.update({'docs': docs})
		return Response(expense_data)

	def put(self, request, pk, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		obj = self.get_obj(pk)
		serializer = RoadshowExpenseSerializer(obj, data=request.data)
		if serializer.is_valid():
			serializer.save()
			file_ids = request.data['docs']
			expense_doc = ExpenseDocument.objects.filter(id__in=file_ids).update(
				expense=serializer.data['id']
			)
			expense_data = serializer.data
			if file_ids:
				docs = ExpenseDocument.objects.filter(expense=obj)
				docs = [{
					'id': document.id,
					'docfile': request.build_absolute_uri('{0}/{1}'.format(settings.MEDIA_URL, document.docfile))} for document in docs]
				expense_data.update({'docs': docs})
			return Response(expense_data, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#from rest_framework.parsers import MultiPartParser, FormParser
class ExpenseDocumentList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = ExpenseDocument.objects.all()
	serializer_class = ExpenseDocumentSerializer
	#parser_classes = (MultiPartParser, FormParser,)

	def post(self, request, format=None):
		serializer = ExpenseDocumentSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			data = {
				'id': serializer.data['id'],
				'docfile': request.build_absolute_uri('{0}'.format(serializer.data['docfile']))
			}
			return Response(data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DinnerList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowDinner.objects.all()
	serializer_class = RoadshowDinnerSerializer

	def post(self, request, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		serializer = RoadshowDinnerSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class DinnerDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowDinner.objects.all()
	serializer_class = RoadshowDinnerSerializer

	def get_obj(self, pk):
		try:
		    return RoadshowDinner.objects.get(pk=pk)
		except RoadshowDinner.DoesNotExist:
		    raise Http404

	def put(self, request, pk, format=None):
		# Assign the created by user
		request.data['created_by'] = request.user.id
		obj = self.get_obj(pk)
		serializer = RoadshowDinnerSerializer(obj, data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = User.objects.all()
	serializer_class = UserSerializer

	def post(self, request, format=None):
		if request.user.has_perm('auth.add_user'):
			group = request.data['groups']
			serializer = UserSerializer(data=request.data)
			if serializer.is_valid():
				serializer.save()
				user = User.objects.get(email=request.data['email'])
				userProfile = UserProfile.objects.create(
					user=user,
					contact_phone=request.data['contact_phone'],
					designation=request.data['designation']
				)
				user.groups.add(group)
				company = Company.objects.filter(users__id=request.user.id)
				if company:
					company[0].users.add(user)
				return Response(serializer.data, status=status.HTTP_201_CREATED)
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
		else:
			return Response({'message': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

	def list(self, request, format=None):
		company = Company.objects.filter(users__id=request.user.id)
		users = []
		if company:
			users = [{
				'username': user.username,
				'id': user.id,
				'first_name': user.first_name,
				'last_name': user.last_name,
				'is_active': user.is_active,
				'email': user.email,
				'is_superuser': user.is_superuser,
				'is_staff': user.is_staff,
				'last_login': user.last_login,
				'designation': user.user_profile.designation if UserProfile.objects.filter(user=user) else '',
				'contact_phone': user.user_profile.contact_phone if UserProfile.objects.filter(user=user) else ''
			} for user in company[0].users.all() if user.is_active]
		return Response(users, status=status.HTTP_200_OK)

class UserDetail(generics.RetrieveUpdateDestroyAPIView):
	queryset = User.objects.all()
	serializer_class = UserSerializer


class Logout(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def get(self, request, format=None):
		logout(request)
		return Response(status=status.HTTP_200_OK)


class GetRoadshowUser(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		parent_list = []
		for r_user in road_show.users.all():
			user_dict = {}
			user_dict['id'] = r_user.id
			user_dict['username'] = r_user.username
			user_dict['first_name'] = r_user.first_name
			parent_list.append(user_dict)
		return Response(parent_list)


class UserGroups(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, format=None):
		groups = Group.objects.all()
		group_list = [{'id': group.id, 'name': group.name} for group in groups]
		return Response(group_list)


class ResetPassword(APIView):

	
	def post(self, request, token, format=None):
		user_pwd_token = UserPasswordToken.objects.filter(token=token)
		if user_pwd_token:
			user = user_pwd_token[0].user
			user_id = user.id
			user = User.objects.filter(id=user_id)
			password1 = request.data['password1']
			password2 = request.data['password2']
			if user and password1 != None and password2 != None and password1 == password2:
				user = User.objects.filter(id=user_id).update(password=make_password(password1))
				# user.set_password(password1)
				# user.save()
				user_pwd_token[0].token = ''
				user_pwd_token[0].save()
				return Response(
					{'message': 'Successfully updated.'},
					status=status.HTTP_200_OK
				)
			else:
				return Response(
					{'message': 'Please check the password'},
					status=status.HTTP_400_BAD_REQUEST
				)
		else:
			return Response(
				{'message': 'Invalid token'},
				status=status.HTTP_400_BAD_REQUEST
			)


class ForgotPassword(APIView):


	def post(self, request, format=None):
		email = request.data['email']
		user = User.objects.filter(email=email)
		unique_id = get_random_string(length=32)
		if user:
			u_token = UserPasswordToken.objects.filter(user=user[0])
			if u_token:
				u_token[0].token = unique_id
				u_token[0].save()
			else:
				u_token.create(token=unique_id, user=user[0])
			token = UserPasswordToken.objects.get(user=user[0]).token
			context = {
			    'first_name': user[0].first_name,
			    'encrypt_data': token,
			    'host_name': request.META['HTTP_HOST']
			}
			# host_str = "http://"+request.META['HTTP_HOST']+"/#/reset-password/"+token
			# print host_str
			html_content = render_to_string('send_forgot_password.html',
	                                        context)
			message=EmailMessage(subject='Reset Password',body=html_content,to=[email])
			message.content_subtype='html'
			message.send()
			return Response(
				{'message': 'Please check your mail to reset password.'},
				status=status.HTTP_200_OK
			)
		else:
			return Response(
				{'message': 'Email not found'},
				status=status.HTTP_400_BAD_REQUEST
			)


class ChangePassword(APIView):

	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	
	def get_obj(self, pk):
		try:
		    return User.objects.get(pk=pk)
		except User.DoesNotExist:
		    raise Http404

	def put(self, request, pk, format=None):
		user = self.get_obj(pk)
		if not user.check_password(request.data['current_password']):
			return Response(
				{'message': 'Invalid Current Password'},
				status=status.HTTP_400_BAD_REQUEST
			)
		password1 = request.data['password1']
		password2 = request.data['password2']
		if user and password1 != None and password2 != None and password1 == password2:
			user = User.objects.filter(id=user.id).update(password=make_password(password1))
			return Response(
				{'message': 'Successfully updated.'},
				status=status.HTTP_200_OK
			)
		else:
			return Response(
				{'message': 'Not valid'},
				status=status.HTTP_400_BAD_REQUEST
			)



class FetchUser(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, format=None):
		user_ids = [int(x) for x in request.GET.get('users').split(',')]
		users = User.objects.filter(id__in=user_ids, is_active=True)
		user_list = [{'id': user.id, 'name': user.email} for user in users]
		return Response(user_list)


class FetchRoadshow(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = Roadshow.objects.all()
	serializer_class = RoadshowSerializer


class FetchMeetingMode(APIView):
	"""
	This will be used for fetch the meeting modes data for Meeting CRUD operation.
	"""
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, format=None):
		m_modes = MeetingMode.objects.all()
		m_modes_list = [{'id': m_mode.id, 'name': m_mode.name} for m_mode in m_modes if m_mode.name != 'Other']
		return Response(m_modes_list)


class FetchMeetingType(APIView):
	"""
	This will be used for fetch the meeting types for Meeting CRUD operation.
	"""
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, format=None):
		m_types = MeetingType.objects.all()
		m_types_list = [{'id': m_type.id, 'name': m_type.name} for m_type in m_types]
		return Response(m_types_list)


class CheckUserMeeting(APIView):
	"""
	This will be used for check the user meeting for particular roadshow.
	"""
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def check_meeting(self, roadshow, u_id):
		m_user = MeetingUser.objects.filter(
			meeting__in=roadshow.meetings.values_list('id'),
			user_id=u_id
		)	
		if m_user:
			return True
		else:
			return False


	def get(self, request, format=None):
		user_id = request.GET.get('user_id')
		roadshow_id = request.GET.get('roadshow_id')
		roadshow = Roadshow.objects.filter(id=roadshow_id)
		user = User.objects.filter(id=user_id)
		output_response = {}
		if roadshow and user:
			if self.check_meeting(roadshow[0], user_id):
				output_response['message'] = True
				output_response['status']=status.HTTP_200_OK
			else:
				output_response['message'] = False
				output_response['status']=status.HTTP_400_BAD_REQUEST

		else:
			output_response['message'] = False
			output_response['status']=status.HTTP_400_BAD_REQUEST

		return Response(output_response)


class RemoveUserMeeting(APIView):
	"""
	This will be used for check the user meeting for particular roadshow.
	"""
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def check_meeting(self, roadshow, user):
		m_user = MeetingUser.objects.filter(
			meeting__in=roadshow.meetings.values_list('id'),
			user_id=user.id
		).values_list('meeting_id')	
		meetings = roadshow.meetings.filter(id__in=m_user)
		roadshowflights = roadshow.roadshowflights.filter(users__id=user.id)
		roadshowrentals = roadshow.roadshowrentals.filter(users__id=user.id)
		if meetings or roadshowflights or roadshowrentals:
			# Remove meetings
			for m in meetings:
				if len(m.meetingusers.all()) == 1:
					m.delete()
				else:
					MeetingUser.objects.filter(
						meeting=m,
						user_id=user.id
					).delete()
					#m.users.remove(user)
			# Remove flights
			for flight in roadshowflights:
				if len(flight.users.all()) == 1:
					flight.delete()
				else:
					flight.users.remove(user)
			# Remove rentals
			for rental in roadshowrentals:
				if len(rental.users.all()) == 1:
					rental.delete()
				else:
					rental.users.remove(user)
			return True
		else:
			return False


	def get(self, request, format=None):
		user_id = request.GET.get('user_id')
		roadshow_id = request.GET.get('roadshow_id')
		roadshow = Roadshow.objects.filter(id=roadshow_id)
		user = User.objects.filter(id=user_id)
		output_response = {}
		if roadshow and user:
			if self.check_meeting(roadshow[0], user[0]):
				output_response['message'] = True
				output_response['status']=status.HTTP_200_OK
			else:
				output_response['message'] = False
				output_response['status']=status.HTTP_400_BAD_REQUEST

		else:
			output_response['message'] = False
			output_response['status']=status.HTTP_400_BAD_REQUEST

		return Response(output_response)


class RoadshowSearch(generics.ListCreateAPIView):
    """
    This method will be used for searching the roadshows by
    using the 3 keywords such as year, title and users.
    """
    permission_classes = (IsAuthenticated, )
    authentication_classes = (JSONWebTokenAuthentication, ) 
    queryset = Roadshow.objects.all()
    serializer_class = RoadshowSerializer

    def list(self, request):
        # year_query = Q(from_date__year=request.GET['year']) if request.GET['year'] != '' else Q()
        # title_query = Q(title__contains=request.GET['title']) if request.GET['title'] != '' else Q()
        # user_query= Q(users__id=request.GET['user']) if request.GET['user'] != '' else Q()
        title_query = Q(title__in=request.GET['title'].split(',')) if request.GET['title'] != '' else Q()
        user_query= Q(users__in=request.GET['user'].split(',')) if request.GET['user'] != '' else Q()
        company = Company.objects.filter(users__id=request.user.id)

        roadshow_ids = CompanyRoadshow.objects.filter(company=company[0]).values_list('roadshow')
        if request.GET['year'] == '' and request.GET['title'] != '' and request.GET['user'] == '':
            year_query = Q()
            roadshows = Roadshow.objects.filter(
                    Q(id__in = roadshow_ids),
                    year_query & title_query & user_query
                )
            data1 = []
            if roadshows:
                data1 = [[roadshow.from_date.year, roadshow] for roadshow in roadshows]
                data_dict = dict()
                for line in data1:
                    if line[0] in data_dict:
                        data_dict[line[0]].append(line[1])
                    else:
                        data_dict[line[0]] = [line[1]]
                data =[]
                for k,v in  data_dict.iteritems():
                    temp = [k,v]
                    data.append(temp)

            # data = [[
            #   date.year, Roadshow.objects.filter(
            #       Q(id__in = roadshow_ids),
            #       year_query & title_query & user_query
            #   )
            # ] for date in Roadshow.objects.dates('from_date', 'year')]
        elif request.GET['year'] == '' and request.GET['title'] == '' and request.GET['user'] == '':
            data = [[
                    date.year,
                    Roadshow.objects.filter(id__in = roadshow_ids, from_date__year=date.year)
                ] for date in Roadshow.objects.filter(id__in = roadshow_ids).dates('from_date', 'year')]
        elif request.GET['year'] != '' or request.GET['title'] != '' or request.GET['user'] == '':
            data = [[
                year, Roadshow.objects.filter(
                    Q(id__in = roadshow_ids),
                    Q(from_date__year=year) & title_query & user_query
                )
            ] for year in request.GET['year'].split(',')]
        elif request.GET['year'] == '' and request.GET['title'] == '' and request.GET['user'] != '':
            year_query = Q()
            data_obj = Roadshow.objects.filter(Q(id__in = roadshow_ids),year_query & title_query & user_query)
            data1 = [[dt_oj.from_date.year, dt_oj] for dt_oj in data_obj]
            data_dict = dict()
            for line in data1:
                if line[0] in data_dict:
                    data_dict[line[0]].append(line[1])
                else:
                    data_dict[line[0]] = [line[1]]
            data =[]
            for k,v in  data_dict.iteritems():
                temp = [k,v]
                data.append(temp)
            # data = [[
            #   date.year, Roadshow.objects.filter(
            #       Q(id__in = roadshow_ids),
            #       year_query & title_query & user_query
            #   )
            # ] for date in Roadshow.objects.dates('from_date', 'year').filter(Q(id__in = roadshow_ids)&user_query)] #.filter(Q(id__in = roadshow_ids)&user_query)]
            # # print data
        parent_list = []
        for k, v in dict(data).iteritems():
            parent_dict = {}
            #parent_dict[k.year] = json.loads(serializers.serialize('json', v))
            parent_dict['year'] = k
            parent_dict['passed_year'] = False if(datetime.datetime.now().year <= int(k)) else True
            parent_dict['data'] = json.loads(serializers.serialize('json', v))
            parent_list.append(parent_dict)

        return Response(sorted(parent_list, key=itemgetter('year'), reverse=True))


class UserTravelDetail(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def calculate_distance(self, origin, destination, trvelMode):
	    distance = 0
	    duration = 0
	    try:
	        origin = origin
	        destination = destination
	        url = \
	        'https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial&origins={0}&destinations={1}&mode={2}&key={3}'.format(
	            origin, destination, trvelMode, settings.GOOGLE_API_KEY
	        )
	        response = urllib.urlopen(url)
	        obj = json.load(response)
	        if obj['rows'][0]['elements'][0]['status'] != 'NOT_FOUND':
	            distance = obj['rows'][0]['elements'][0]['distance']['value']
	            duration = obj['rows'][0]['elements'][0]['duration']['text']
	        else:
	            distance = 0
	    except:
	        pass
	    return distance, duration

	def get(self, request, pk, format=None):
		destination = request.GET['destination']
		mtype = request.GET['type']
		meeting_date = request.GET['date']
		user_id = request.GET['user']
		meetings = Meeting.objects.filter(
		    roadshow_id=pk, meeting_date=meeting_date
		).order_by('-start_time')

		# from pprint import pprint
		# for met in meetings:
		# 	pprint (vars(met))

		parent_dict = {}
		origin =''
		if request.GET['meeting_id'] == '0':
			'''
			This is for create new meeting
			'''
			for meeting in meetings:
				meeting_user = MeetingUser.objects.filter(meeting_id=meeting.id, user_id=user_id)
				if meeting_user:
				    origin = "{0}, {1}, {2}".format(
				    	meeting.address,
				    	meeting.city,
				    	meeting.postcode,
				    )
				    break
		else:
			'''
			This is for while edit the meeting and do change the user mode
			'''
			meeting_id = request.GET['meeting_id']
			meeting_user = MeetingUser.objects.filter(meeting_id=meeting_id, user_id=user_id)

			try:
				origin = "{0}, {1}".format(
					meeting_user[0].from_address,
					meeting_user[0].from_city
					# meeting_user[0].postcode
				)
				print "(((((((((((",origin
			except:
				origin = MeetingUser.objects.filter(user_id=user_id).last().from_address
		dt1 = datetime.datetime.strptime(meeting_date, '%Y-%m-%d') # coverting unicode to date
		# dat1 = dt1 - timedelta(days=1)
		print "$$#%^@#$%@#", origin

		if origin =='' or 'None':
		    hotels = RoadshowHotel.objects.filter(
		    	roadshow_id=pk,
		    	from_date__lt=dt1,
		    	to_date__gt=dt1,
		    	users = user_id
		    )
		    print "&&&&&&&&", hotels
		    for hotel in hotels:
		    	origin = "{0}, {1}, {2}".format(
					hotel.hotel_address,
					hotel.city,
					hotel.pincode
				)

		print "(&^(^(^()()",origin
		if mtype == '1':
		    distance, duration = self.calculate_distance(origin, destination, 'walking')
		elif mtype == '2':
		    distance, duration = self.calculate_distance(origin, destination, 'driving')
		elif mtype == '3':
		    distance, duration = self.calculate_distance(origin, destination, 'driving')
		elif mtype == '4':
		    distance, duration = self.calculate_distance(origin, destination, 'transist')
		elif mtype == '5':
		    distance, duration = self.calculate_distance(origin, destination, 'transist')
		else:
		    distance = duration = 0

		parent_dict['distance'] = distance
		parent_dict['duration'] = duration
		parent_dict['user'] = user_id
		return Response(parent_dict)


class TravelDetail(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	
	def calculate_distance(self, origin, destination, trvelMode):
		distance = 0
		duration =0
		try:
			# use zip code
			origin = origin
			destination = destination
			url = \
			'https://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&mode={2}&key={3}'.format(
				origin, destination, trvelMode, settings.GOOGLE_API_KEY
			)
			response = urllib.urlopen(url)
			obj = json.load(response)
			if obj['rows'][0]['elements'][0]['status'] != 'NOT_FOUND':
				distance = obj['rows'][0]['elements'][0]['distance']['value']
				duration = obj['rows'][0]['elements'][0]['duration']['text']
			else:
				distance = 0
		except:
			pass
		return distance, duration

	def get(self, request, pk, format=None):
		origin_id = request.GET['origin_id']
		mtype = request.GET['type']
		meeting = Meeting.objects.filter(
			id=pk
		)
		if mtype == 'hotel':
			origin = RoadshowHotel.objects.filter(
				id=origin_id
			)[0]
			origin_address = origin.hotel_address,
			total_origin_address = "{0}, {1}, {2}".format(
				origin.hotel_address,
				origin.city,
				origin.pincode,
			)
		elif mtype == 'meeting':
			origin = Meeting.objects.filter(
				id=origin_id
			)[0]
			origin_address = origin.address
			total_origin_address = "{0}, {1}, {2}".format(
				origin.address,
				origin.city,
				origin.postcode,
			)
		p_list = []
		meeting_address = {}
		if meeting:
			for muser in meeting[0].meetingusers.all():
				travelDict = {}
				destination = "{0}, {1}, {2}".format(
					meeting[0].address,
					meeting[0].city,
					meeting[0].postcode,
				)
				if not muser.from_address == None:
					origin_address = muser.from_address
					total_origin_address = "{0}, {1}".format(
						muser.from_address,
						muser.from_city
					)
				if muser.meeting_mode.name == 'By Public Transport':
					distance, duration = self.calculate_distance(
						total_origin_address,
						destination,
						'driving'
				)
				elif muser.meeting_mode.name == 'By Cab':
					distance, duration = self.calculate_distance(
						total_origin_address,
						destination,
						'driving'
					)
				elif muser.meeting_mode.name == 'By Walk':
					distance, duration = self.calculate_distance(
						total_origin_address,
						destination,
						'walking'
				)
				else:
					distance = duration = 0
				muser.distance = distance
				muser.duration = duration
				muser.from_address = origin_address
				muser.from_city = origin.city
				muser.to_address = meeting[0].address
				muser.to_city = meeting[0].address
				muser.date_of_travel = meeting[0].meeting_date
				muser.save()
				travelDict['meeting_user_id'] = muser.id
				travelDict['distance'] = muser.distance
				travelDict['duration'] = muser.duration
				travelDict['from_address'] = muser.from_address
				travelDict['from_city'] = muser.from_city
				travelDict['to_address'] = muser.to_address
				travelDict['to_city'] = muser.to_city
				travelDict['date_of_travel'] = muser.date_of_travel
				user = muser.user
				travelDict['user']= {
					"email": user.email,
					"first_name": user.first_name,
					"last_name": user.last_name
				}
				travelDict['travel_mode'] = muser.meeting_mode.id
				travelDict['origin_id'] = origin_id
				travelDict['meeting_id'] = meeting[0].id
				travelDict['mtype'] = mtype
				p_list.append(travelDict)
		return Response(p_list)



	def put(self, request, pk, format=None):
		origin_id = request.data['origin_id']
		mtype = request.data['type']
		meeting = Meeting.objects.filter(
			id=pk
		)
		if mtype == 'hotel':
			origin = RoadshowHotel.objects.filter(
				id=origin_id
			)[0]
			origin_address = request.data['from_address']
		elif mtype == 'meeting':
			origin = Meeting.objects.filter(
				id=origin_id
			)[0]
			origin_address = request.data['from_address']
		p_list = []
		meeting_address = {}
		if meeting:
			muser = MeetingUser.objects.get(id=request.data['meeting_user_id'])
			travelDict = {}
			if muser.meeting_mode.name == 'By Public Transport':
				distance, duration = self.calculate_distance(origin_address, meeting[0].address, 'driving')
			elif muser.meeting_mode.name == 'By Cab':
				distance, duration = self.calculate_distance(origin_address, meeting[0].address, 'driving')
			elif muser.meeting_mode.name == 'By Walk':
				distance, duration = self.calculate_distance(origin_address, meeting[0].address, 'walking')
			else:
				distance = duration = 0
			muser.distance = distance
			muser.duration = duration
			muser.from_address = origin_address
			muser.from_city = origin.city
			muser.to_address = meeting[0].address
			muser.to_city = meeting[0].address
			muser.date_of_travel = meeting[0].meeting_date
			muser.save()
			travelDict['distance'] = muser.distance
			travelDict['meeting_user_id'] = muser.id
			travelDict['duration'] = muser.duration
			travelDict['from_address'] = muser.from_address
			travelDict['from_city'] = muser.from_city
			travelDict['to_address'] = muser.to_address
			travelDict['to_city'] = muser.to_city
			travelDict['date_of_travel'] = muser.date_of_travel
			user = muser.user
			travelDict['user']= {
				"email": user.email,
				"first_name": user.first_name,
				"last_name": user.last_name
			}
			travelDict['meeting_id'] = meeting[0].id
			travelDict['travel_mode'] = muser.meeting_mode.id
			p_list.append(travelDict)
			# meeting_address['meeting_from_address'] = origin.address
			# if mtype == 'meeting':
			# 	meeting_address['meeting_from_date'] = origin.meeting_date
			# elif mtype == 'hotel':
			# 	meeting_address['meeting_from_date'] = origin.from_date
			# meeting_address['meeting_from_time'] = origin.start_time
			# meeting_address['meeting_to_address'] = meeting[0].address
			# meeting_address['meeting_to_date'] = meeting[0].meeting_date
			# meeting_address['meeting_to_time'] = meeting[0].start_time
			# p_list.append(meeting_address)
		return Response(p_list)



class RoadshowExpenseAll(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		parent_list = []
		for expense in road_show.roadshowexpenses.all():
			expense_dict = {}
			expense_dict['id'] = expense.id
			expense_dict['expense_title'] = expense.expense_title
			expense_dict['expense_description'] = expense.expense_description
			expense_dict['expense_amount'] = expense.expense_amount
			expense_dict['expense_time'] = expense.expense_time
			expense_dict['category'] = expense.category
			expense_dict['expense_date'] = expense.expense_date
			expense_dict['payment_method'] = expense.payment_method
			expense_dict['currency_type'] = expense.currency_type
			expense_dict['minus_personal'] = expense.minus_personal
			expense_dict['final_amount'] = expense.final_amount
			expense_dict['expense_notes'] = expense.expense_notes
			parent_list.append(expense_dict)
		return Response(parent_list)


class RoadshowCities(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		return Response(
			set([x.city for x in road_show.meetings.all() if x.city] + \
			[y.city for y in road_show.roadshowhotels.all() if y.city])
		)


class RoadshowUsers(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		return Response(
			[
			{
				"full_name": '{0} {1}'.format(x.first_name, x.last_name),
				"role":Group.objects.get(user=x).name
			} for x in road_show.users.all() ]
		)


class RoadshowFilter(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def fetch_cab_data_list(self, cars_list, data_list):
		for car_data in cars_list:
			c_dict = {}
			c_dict['id'] = car_data.id
			c_dict['name'] = car_data.rental_name
			c_dict['timeStart'] = car_data.start_time
			c_dict['timeEnd'] = car_data.end_time
			c_dict['type'] = 'cab'
			data_list.append(c_dict)

	def fetch_meeting_data_list(self, meetings_list, data_list):
		for meeting_data in meetings_list:
			m_dict = {}
			m_dict['id'] = meeting_data.id
			m_dict['name'] = meeting_data.company_name
			m_dict['timeStart'] = meeting_data.start_time
			m_dict['timeEnd'] = meeting_data.end_time
			m_dict['city'] = meeting_data.city
			m_dict['meeting_type'] = meeting_data.meeting_type.name
			m_dict['distance_next'] = meeting_data.distance_next
			m_dict['address'] = meeting_data.address
			m_dict['type'] = 'meeting'
			data_list.append(m_dict)

	def fetch_flight_data_list(self, flights_list, data_list):
		for flight_data in flights_list:
			f_dict = {}
			f_dict['id'] = flight_data.id
			f_dict['name'] = flight_data.airline
			f_dict['timeStart'] = flight_data.start_time
			f_dict['timeEnd'] = flight_data.end_time
			f_dict['address'] = flight_data.to_airport
			f_dict['type'] = 'flight'
			data_list.append(f_dict)

	def fetch_hotel_data_list(self, hotels_list, data_list):
		for hotel_data in hotels_list:
			h_dict = {}
			h_dict['id'] = hotel_data.id
			h_dict['name'] = hotel_data.hotel_name
			h_dict['timeStart'] = hotel_data.start_time
			h_dict['timeEnd'] = hotel_data.end_time
			h_dict['address'] = hotel_data.hotel_address
			h_dict['type'] = 'hotel'
			data_list.append(h_dict)


	def calculate_roadshow_dashboard(
		self, road_show, roadshow_dates_list, city, user, dates, filter_type):
		parent_list = []
		for m_date in roadshow_dates_list:
			parent_dict = {}

			city_query = Q(
				city__in=city.split(','),
			) if city != '' else Q()
			user_query= Q(users__in=user.split(',')) if user != '' else Q()


			if user != '':
				m_ids =[m.meeting_id for m in MeetingUser.objects.filter(
					user_id__in=user.split(',')
				) if m]
				meetings_list = road_show.meetings.filter(city_query, id__in=m_ids, meeting_date=m_date)
			else:
				meetings_list = road_show.meetings.filter(city_query, meeting_date=m_date)
			flights_list = road_show.roadshowflights.filter(user_query, from_date=m_date)
			cars_list = road_show.roadshowrentals.filter(user_query, from_date=m_date)
			dinner_list = road_show.roadshowdinner.filter(user_query, dinner_date=m_date)
			hotels_list = road_show.roadshowhotels.filter(city_query, user_query, from_date=m_date)
			data_list = []
			hotel_data_list = []

			parent_dict['date'] = m_date
			if filter_type != '':
				for f_type in filter_type.split(','):
					if f_type == 'cab':
						if cars_list:
							self.fetch_cab_data_list(cars_list, data_list)
							parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
							parent_list.append(parent_dict)
					if f_type == 'meeting':
						if meetings_list:
							self.fetch_meeting_data_list(meetings_list, data_list)
							parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
							parent_list.append(parent_dict)
					if f_type == 'flight':
						if flights_list:
							self.fetch_flight_data_list(flights_list, data_list)
							parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
							parent_list.append(parent_dict)
					if f_type == 'hotel':
						if hotels_list:
							self.fetch_hotel_data_list(hotels_list, data_list)
							parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
							parent_list.append(parent_dict)
			else:
				if meetings_list or hotels_list:
					#parent_dict['date'] = m_date
					if meetings_list:
						self.fetch_meeting_data_list(meetings_list, data_list)
					if flights_list:
						self.fetch_flight_data_list(flights_list, data_list)
					if cars_list:
						self.fetch_cab_data_list(cars_list, data_list)
					if dinner_list:
						for dinner_data in dinner_list:
							d_dict = {}
							d_dict['id'] = dinner_data.id
							d_dict['name'] = dinner_data.name
							d_dict['timeStart'] = dinner_data.start_time
							d_dict['timeEnd'] = dinner_data.end_time
							d_dict['type'] = 'dinner'
							data_list.append(d_dict)
					if hotels_list:
						self.fetch_hotel_data_list(hotels_list, data_list)

				parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
				# Keep the hotel object at the last as per the requirement

				parent_dict['schedule'] = parent_dict['schedule'] + hotel_data_list

				parent_list.append(parent_dict)
		return parent_list

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)

		city = request.GET['city']
		user = request.GET['user']
		dates = request.GET['dates']
		filter_type = request.GET['type']

		start_date = road_show.from_date
		end_date = road_show.to_date

		total_days = (end_date - start_date).days + 1

		if dates == '':
			roadshow_dates_list = [(start_date + dt.timedelta(days = day_number)) \
				for day_number in range(total_days)]
		else:
			roadshow_dates_list = dates.split(',')

		output_list = self.calculate_roadshow_dashboard(
			road_show,
			roadshow_dates_list,
			city,
			user,
			dates,
			filter_type
		)

		return Response(output_list)


class RoadshowLatest(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = Roadshow.objects.all().order_by('-from_date')[:5]
	serializer_class = RoadshowSerializer

	def list(self, request):
		company = Company.objects.filter(users__id=request.user.id)
		roadshow_ids = CompanyRoadshow.objects.filter(
			company=company[0]
		).values_list('roadshow')
		roadshow_objects = Roadshow.objects.filter(
			id__in=roadshow_ids
		).order_by('-from_date')[:5]
		return Response(
			roadshow_objects.values(),
			status=status.HTTP_200_OK
		)

class RoadshowExpenseAllView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		parent_list = []
		for expense in road_show.roadshowexpenses.all():
			expense_dict = {}
			expense_dict['id'] = expense.id
			expense_dict['roadshow_name'] = road_show.title
			expense_dict['expense_title'] = expense.expense_title
			expense_dict['expense_description'] = expense.expense_description
			expense_dict['expense_amount'] = expense.expense_amount
			expense_dict['expense_time'] = expense.expense_time
			expense_dict['category'] = expense.category.name
			expense_dict['expense_date'] = expense.expense_date
			expense_dict['expense_date_mobile'] = expense.expense_date.strftime('%d %b %Y %A')
			expense_dict['payment_method'] = expense.payment_method
			expense_dict['currency_type'] = expense.currency_type
			expense_dict['minus_personal'] = expense.minus_personal
			expense_dict['final_amount'] = expense.final_amount
			expense_dict['expense_notes'] = expense.expense_notes
			docs = ExpenseDocument.objects.filter(expense=expense)
			expense_dict['documents'] = [{
			'id': document.id,
			'docfile': request.build_absolute_uri(
				'{0}/{1}'.format(settings.MEDIA_URL, document.docfile))
			} for document in docs]
			parent_list.append(expense_dict)
		return Response(parent_list)


class RoadshowExpenseCompanyList(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def get(self, request, pk):
		roadshow_expenses = RoadshowExpense.objects.filter(company_id=pk)
		parent_list = []
		for expense in roadshow_expenses:
			expense_dict = {}
			expense_dict['id'] = expense.id
			expense_dict['expense_title'] = expense.expense_title
			expense_dict['expense_description'] = expense.expense_description
			expense_dict['expense_amount'] = expense.expense_amount
			expense_dict['expense_time'] = expense.expense_time
			expense_dict['status'] = expense.status
			expense_dict['created_by'] = expense.created_by_id
			expense_dict['roadshow_id'] = expense.roadshow_id
			expense_dict['category'] = expense.category.name
			expense_dict['currency_type'] = expense.currency_type
			expense_dict['expense_date'] = expense.expense_date
			expense_dict['payment_method'] = expense.payment_method
			expense_dict['minus_personal'] = expense.minus_personal
			expense_dict['final_amount'] = expense.final_amount
			expense_dict['expense_notes'] = expense.expense_notes
			expense_dict['company'] = expense.company_id
			docs = ExpenseDocument.objects.filter(expense=expense)
			expense_dict['documents'] = [{
			'id': document.id,
			'docfile': request.build_absolute_uri(
				'{0}/{1}'.format(settings.MEDIA_URL, document.docfile))
			} for document in docs]
			parent_list.append(expense_dict)


		return Response(parent_list)


class CategoryList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = Category.objects.all()
	serializer_class = CategorySerializer


class CompanyCategoryView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, pk):
		categories = Category.objects.filter(company_id=pk)
		parent_list = []
		for category in categories:
			category_dict = {}
			category_dict['id'] = category.id
			category_dict['name'] = category.name
			category_dict['color'] = category.color
			parent_list.append(category_dict)

		return Response(parent_list)


class CategoryView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def put(self, request, pk ):
		category_obj = Category.objects.get(id = pk)
		category_obj.name = request.data['name']
		category_obj.color = request.data['color']
		category_obj.save()
		return Response("Category updated successfully")

	def delete(self, request, pk):
		category_obj = Category.objects.get(id = pk)
		category_obj.delete()
		return Response("Category deleted successfully")


class RoadshowDateBWView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request ):
		from_date = request.GET['from']
		to_date = request.GET['to']
		companyid = request.GET['companyid']
		roadshow_id = request.GET['roadshow']

		date_query = Q(
			expense_date__range = [request.GET['from'], request.GET['to']]
		) if (request.GET['from'] and request.GET['to']) != '' else Q()

		category_query = Q(
			category_id__in=request.GET['category'].split(',')
		) if request.GET['category'] != '' else Q()

		roadshow_expenses = RoadshowExpense.objects.filter(
			date_query,
			category_query,
			company_id=companyid,
			roadshow_id = roadshow_id
		)
		parent_list = []
		for expense in roadshow_expenses:
			expense_dict = {}
			expense_dict['id'] = expense.id
			expense_dict['expense_title'] = expense.expense_title
			expense_dict['expense_description'] = expense.expense_description
			expense_dict['expense_amount'] = expense.expense_amount
			expense_dict['expense_time'] = expense.expense_time
			expense_dict['status'] = expense.status
			expense_dict['created_by'] = expense.created_by_id
			expense_dict['roadshow_id'] = expense.roadshow_id
			expense_dict['category'] = expense.category.name
			expense_dict['currency_type'] = expense.currency_type
			expense_dict['expense_date'] = expense.expense_date
			expense_dict['payment_method'] = expense.payment_method
			expense_dict['minus_personal'] = expense.minus_personal
			expense_dict['final_amount'] = expense.final_amount
			expense_dict['expense_notes'] = expense.expense_notes
			expense_dict['company'] = expense.company_id
			docs = ExpenseDocument.objects.filter(expense=expense)
			expense_dict['documents'] = [{
			'id': document.id,
			'docfile': request.build_absolute_uri(
				'{0}/{1}'.format(settings.MEDIA_URL, document.docfile))
			} for document in docs]
			parent_list.append(expense_dict)

		return Response(parent_list)

class CompanyDateBWView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request ):

		companyid = request.GET['companyid']

		date_query = Q(
			expense_date__range = [request.GET['from'], request.GET['to']]
		) if (request.GET['from'] and request.GET['to']) != '' else Q()

		category_query = Q(
			category_id__in=request.GET['category'].split(',')
		) if request.GET['category'] != '' else Q()

		roadshow_expenses = RoadshowExpense.objects.filter(
			date_query,
			category_query,
			company_id=companyid
		)
		parent_list = []
		for expense in roadshow_expenses:
			expense_dict = {}
			expense_dict['id'] = expense.id
			expense_dict['expense_title'] = expense.expense_title
			expense_dict['expense_description'] = expense.expense_description
			expense_dict['expense_amount'] = expense.expense_amount
			expense_dict['expense_time'] = expense.expense_time
			expense_dict['status'] = expense.status
			expense_dict['created_by'] = expense.created_by_id
			expense_dict['roadshow_id'] = expense.roadshow_id
			expense_dict['category'] = expense.category.name
			expense_dict['currency_type'] = expense.currency_type
			expense_dict['expense_date'] = expense.expense_date
			expense_dict['payment_method'] = expense.payment_method
			expense_dict['minus_personal'] = expense.minus_personal
			expense_dict['final_amount'] = expense.final_amount
			expense_dict['expense_notes'] = expense.expense_notes
			expense_dict['company'] = expense.company_id
			docs = ExpenseDocument.objects.filter(expense=expense)
			expense_dict['documents'] = [{
			'id': document.id,
			'docfile': request.build_absolute_uri(
				'{0}/{1}'.format(settings.MEDIA_URL, document.docfile))
			} for document in docs]
			parent_list.append(expense_dict)

		return Response(parent_list)

class ExpenseByCategoryView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request ):

		category_query = Q(
			category_id__in=request.GET['category'].split(',')
		) if request.GET['category'] != '' else Q()

		roadshow_query = Q(
			category_id__in=request.GET['roadshow'].split(',')
		) if request.GET['roadshow'] != '' else Q()

		roadshow_expenses = RoadshowExpense.objects.filter(
			category_query,
			roadshow_query,
			company_id=request.GET['company']
		)
		parent_list = []
		for expense in roadshow_expenses:
			expense_dict = {}
			expense_dict['id'] = expense.id
			expense_dict['expense_title'] = expense.expense_title
			expense_dict['expense_description'] = expense.expense_description
			expense_dict['expense_amount'] = expense.expense_amount
			expense_dict['expense_time'] = expense.expense_time
			expense_dict['status'] = expense.status
			expense_dict['created_by'] = expense.created_by_id
			expense_dict['roadshow_id'] = expense.roadshow_id
			expense_dict['category'] = expense.category.name
			expense_dict['currency_type'] = expense.currency_type
			expense_dict['expense_date'] = expense.expense_date
			expense_dict['payment_method'] = expense.payment_method
			expense_dict['minus_personal'] = expense.minus_personal
			expense_dict['final_amount'] = expense.final_amount
			expense_dict['expense_notes'] = expense.expense_notes
			expense_dict['company'] = expense.company_id
			docs = ExpenseDocument.objects.filter(expense=expense)
			expense_dict['documents'] = [{
			'id': document.id,
			'docfile': request.build_absolute_uri(
				'{0}/{1}'.format(settings.MEDIA_URL, document.docfile))
			} for document in docs]
			parent_list.append(expense_dict)

		return Response(parent_list)


class ExpenseByRoadshowView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request ):
		category_query = Q(
			category_id__in=request.GET['category'].split(',')
		) if request.GET['category'] != '' else Q()

		user_query = Q(
			roadshow_user_id__in=request.GET['users'].split(',')
		) if request.GET['users'] != '' else Q()

		roadshow_query = Q(
			roadshow_id__in=request.GET['roadshow'].split(',')
		) if request.GET['roadshow'] != '' else Q()

		roadshow_expenses = RoadshowExpense.objects.filter(
			category_query,
			roadshow_query,
			user_query,
			company_id=request.GET['company']
		)
		parent_list = []
		for expense in roadshow_expenses:
			expense_dict = {}
			expense_dict['id'] = expense.id
			expense_dict['expense_title'] = expense.expense_title
			expense_dict['expense_description'] = expense.expense_description
			expense_dict['expense_amount'] = expense.expense_amount
			expense_dict['expense_time'] = expense.expense_time
			expense_dict['status'] = expense.status
			expense_dict['created_by'] = expense.created_by_id
			expense_dict['roadshow_id'] = expense.roadshow_id
			expense_dict['category'] = expense.category.name
			expense_dict['currency_type'] = expense.currency_type
			expense_dict['expense_date'] = expense.expense_date
			expense_dict['payment_method'] = expense.payment_method
			expense_dict['minus_personal'] = expense.minus_personal
			expense_dict['final_amount'] = expense.final_amount
			expense_dict['expense_notes'] = expense.expense_notes
			expense_dict['company'] = expense.company_id
			docs = ExpenseDocument.objects.filter(expense=expense)
			expense_dict['documents'] = [{
			'id': document.id,
			'docfile': request.build_absolute_uri(
				'{0}/{1}'.format(settings.MEDIA_URL, document.docfile))
			} for document in docs]
			parent_list.append(expense_dict)

		return Response(parent_list)


class GetTravelDetailList(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	def calculate_roadshow_travel_dashboard(self, road_show, roadshow_dates_list, request):
		parent_list = []
		for m_date in roadshow_dates_list:
			parent_dict = {}
			parent_dict['date'] = m_date.strftime('%d %b %Y %A')
			flights_list = road_show.roadshowflights.filter(from_date=m_date)
			cars_list = road_show.roadshowrentals.filter(from_date=m_date)
			data_list=[]
			if flights_list:
				for flight_data in flights_list:
					if request.user.id in [user.id for user in flight_data.users.all()]:
						f_dict = {}
						f_dict['id'] = flight_data.id
						f_dict['name'] = flight_data.airline
						f_dict['class'] = flight_data.airline_class
						f_dict['timeStart'] = flight_data.start_time
						f_dict['timeEnd'] = flight_data.end_time
						f_dict['address'] = flight_data.to_airport
						f_dict['state'] = flight_data.state
						f_dict['user_count'] = flight_data.users.count()
						f_dict['type'] = 'flight'
						data_list.append(f_dict)
			if cars_list:
				for car_data in cars_list:
					if request.user.id in [user.id for user in car_data.users.all()]:
						c_dict = {}
						c_dict['id'] = car_data.id
						c_dict['name'] = car_data.rental_name
						c_dict['timeStart'] = car_data.start_time
						c_dict['timeEnd'] = car_data.end_time
						c_dict['user_count'] = car_data.users.count()
						c_dict['fromCity'] = car_data.from_city
						c_dict['toCity'] = car_data.to_city
						c_dict['from_pincode'] = car_data.from_pincode
						c_dict['to_pincode'] = car_data.to_pincode
						c_dict['from_state'] = car_data.from_state
						c_dict['to_state'] = car_data.to_state
						c_dict['type'] = 'cab'
						data_list.append(c_dict)
			parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
			parent_list.append(parent_dict)
		return parent_list

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		start_date = road_show.from_date
		end_date = road_show.to_date
		total_days = (end_date - start_date).days + 1
		roadshow_dates_list = [(start_date + dt.timedelta(days = day_number)) \
			for day_number in range(total_days)]
		output_list = self.calculate_roadshow_travel_dashboard(road_show, roadshow_dates_list, request)
		return Response(output_list)


class GetHotelList(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	def calculate_roadshow_hotel_dashboard(self, road_show, roadshow_dates_list, request):
		parent_list = []
		for m_date in roadshow_dates_list:
			parent_dict = {}
			parent_dict['date'] = m_date.strftime('%d %b %Y %A')
			hotels_list = road_show.roadshowhotels.filter(from_date=m_date)
			data_list = []
			hotel_data_list = []
			if hotels_list:
				for hotel_data in hotels_list:
					if request.user.id in [user.id for user in hotel_data.users.all()]:
						h_dict = {}
						h_dict['id'] = hotel_data.id
						h_dict['name'] = hotel_data.hotel_name
						h_dict['timeStart'] = hotel_data.start_time
						h_dict['timeEnd'] = hotel_data.end_time
						h_dict['address'] = hotel_data.hotel_address
						h_dict['city'] = hotel_data.city
						h_dict['pincode'] = hotel_data.pincode
						h_dict['state'] = hotel_data.state
						h_dict['user_count'] = hotel_data.users.count()
						hotel_data_list.append(h_dict)
			parent_dict['schedule'] = sorted(hotel_data_list, key=itemgetter('timeStart'))
			parent_list.append(parent_dict)
		return parent_list

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		start_date = road_show.from_date
		end_date = road_show.to_date
		total_days = (end_date - start_date).days + 1
		roadshow_dates_list = [(start_date + dt.timedelta(days = day_number)) \
			for day_number in range(total_days)]
		output_list = self.calculate_roadshow_hotel_dashboard(road_show, roadshow_dates_list, request)
		return Response(output_list)


class GetMeetingList(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	
	def calculate_weather(self, address, meeting_date):
		date = meeting_date.strftime("%d %b %Y")
		weather_dic ={}
		try:
			url = \
			'https://query.yahooapis.com/v1/public/yql?q=select * from weather.forecast where woeid in (select woeid from geo.places(1) where text="{0}")&format=json&/'.format(address)
			response = urllib.urlopen(url)
			# print url
			obj = json.load(response)
			if obj['query']['results'] != None:
				for i in range (0,9):
					json_date = obj['query']['results']['channel']['item']['forecast'][i]['date']
					if (date==json_date):
						weather_dic['forecast'] = obj['query']['results']['channel']['item']['forecast'][i]['high']
						weather_dic['description'] = obj['query']['results']['channel']['item']['forecast'][i]['text']
						weather_dic['code'] = obj['query']['results']['channel']['item']['forecast'][i]['code']
			else:
				weather_dic['forecast'] = ''
				weather_dic['description'] = ''
				weather_dic['code'] = ''
		except:
			pass
		return weather_dic

	def calculate_roadshow_meeting_dashboard(self, road_show, roadshow_dates_list, request):
		parent_list = []
		for m_date in roadshow_dates_list:
			parent_dict = {}
			parent_dict['date'] = m_date.strftime('%d %b %Y %A')
			meetings_list = road_show.meetings.filter(meeting_date=m_date)
			data_list = []
			if meetings_list:
				for index, meeting_data in enumerate(meetings_list):
					# For display mobile user only
					if request.user.id in [muser.user.id for muser in meeting_data.meetingusers.all()]:
						m_dict = {}
						m_dict['id'] = meeting_data.id
						m_dict['name'] = meeting_data.company_name
						m_dict['contactPerson'] = meeting_data.contact_name
						m_dict['contactTitle'] = meeting_data.contact_title
						m_dict['addressLine1'] = meeting_data.company_address_line1
						m_dict['addressLine2'] = meeting_data.company_address_line2
						m_dict['state'] = meeting_data.state
						m_dict['postalCode'] = meeting_data.postcode
						m_dict['companyEmail'] = meeting_data.company_email
						m_dict['companyPhone'] = meeting_data.company_phone
						m_dict['companyMobile'] = meeting_data.company_mobile
						m_dict['timeStart'] = meeting_data.start_time
						m_dict['timeEnd'] = meeting_data.end_time
						m_dict['city'] = meeting_data.city
						m_dict['linkedin_url'] = meeting_data.linkedin_url
						m_dict['user_linkedin_url'] = meeting_data.user_linkedin_url
						m_dict['user_twitter_url'] = meeting_data.user_twitter_url
						m_dict['company_twitter_url'] = meeting_data.company_twitter_url
						try:
							m_dict['meeting_type'] = meeting_data.meeting_type.name
						except:
							m_dict['meeting_type'] = ''
							pass
						user_count = meeting_data.meetingusers.count()
						m_dict['user_count'] = user_count
						if user_count <= 1 and user_count != 0:
							# If single user goes to meeting
							meeting_user = MeetingUser.objects.get(
								meeting_id=meeting_data.id
							)
							m_dict['user_duration'] = meeting_user.duration
							m_dict['user_id'] = meeting_user.user.id
							m_dict['distance_prev'] = meeting_user.distance
						else:
							# if user count > 1 this is for front end team
							m_dict['travel_details'] = [
								{
									'user_duration': mu.duration,
									'user_id': mu.user.id,
									'distance_prev': mu.distance
								} for mu in meeting_data.meetingusers.all()
							]

						m_dict['address'] = meeting_data.address
						user_count = meeting_data.meetingusers.count()
						m_dict['weather'] = self.calculate_weather(meeting_data.address, m_date)
						m_action_color = []
						m_action_color = MeetingColor.objects.filter(meeting_id=meeting_data.id)
						m_action_color = [
							{
								'id': x.company_meeting_color.id,
								'name': x.company_meeting_color.name,
								'color': x.company_meeting_color.color
							} for x in m_action_color]
						m_dict['company_meeting_action_color'] = m_action_color

						m_dict['user_count'] = user_count
						data_list.append(m_dict)
			parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
			parent_list.append(parent_dict)

		update_paren_dict = {}
		paginator = Paginator(parent_list,5)        # added paginator for paginating defualt obj is 5 (at the line 2484 on getmeetinglist	(mobile)api)
		page = request.GET.get('page')

		try:
			parent_details = paginator.page(page).object_list
		except PageNotAnInteger:
			parent_details = paginator.page(1).object_list
		except EmptyPage:
			parent_details = paginator.page(paginator.num_pages).object_list


		if page:
			tot_pg = paginator.num_pages 
			if int(page) <= tot_pg:
				pg_no = paginator.page(page)
			else:
				pg_no = "out of range"

			# print "total pages:",tot_pg , "page no: ", pg_no , paginator.page_range
			update_paren_dict['data'] = parent_details
			update_paren_dict['TotalPages'] = tot_pg
			update_paren_dict['CurrentPage'] = str(pg_no)
			# parent_details.append(pg_dic)
			return update_paren_dict
		else:
			# update_paren_dict['data'] = parent_list           # comment it for avoiding pagination asper mobile
			return parent_list

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		start_date = road_show.from_date
		end_date = road_show.to_date
		total_days = (end_date - start_date).days + 1
		roadshow_dates_list = [(start_date + dt.timedelta(days = day_number)) \
			for day_number in range(total_days)]
		output_list = self.calculate_roadshow_meeting_dashboard(road_show, roadshow_dates_list,request)
		return Response(output_list)


class GetUserDetailList(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)
		#parent_list = road_show.users.values('username','first_name','last_name','email','id') 
		parent_list = [
			{
				"email":user.email,
				"first_name": user.first_name,
				"last_name": user.last_name,
				"id": user.id,
				"mobile":"{0}".format(
					user.user_profile.contact_phone if UserProfile.objects.filter(user=user) else ''
				),
				"profile_pic": \
					['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
						for user_profile in UserProfile.objects.filter(user=user) if user_profile.profile_pic]
			} for user in road_show.users.all()
		]
		return Response(parent_list)


class MeetingSummaryList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = MeetingSummary.objects.all()
	serializer_class = MeetingSummarySerializer

	def post(self, request, format=None):
		request.data['created_by'] = request.user.id
		request.data['comment_date'] = datetime.datetime.now()
		serializer = MeetingSummarySerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			data = {
				'id': serializer.data['id'],
				'meetingDoc': request.build_absolute_uri('{0}'.format(serializer.data['meetingDoc'])),
				'comments': serializer.data['comments'],
				'fileType': serializer.data['fileType'],
				'comment_date': human(datetime.datetime.strptime(serializer.data['comment_date'], "%Y-%m-%d %H:%M:%S.%f")),
				'meetingId': serializer.data['meetingId'],
				'created_by': User.objects.get(id=serializer.data['created_by']).first_name,
			}
			# print serializer
			return Response(data, status=status.HTTP_201_CREATED)
		else:
			print serializer.errors
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeetingSummaryDetail(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, pk, format=None):
		try:
			meeting_summaries = MeetingSummary.objects.filter(meetingId_id=pk)
			parent_list = []
			for m_summary in meeting_summaries:
				meeting_summary={}
				meeting_summary['Id'] = m_summary.id
				meeting_summary['meetingDoc'] = \
					'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(m_summary.meetingDoc))
				meeting_summary['comments'] = m_summary.comments
				meeting_summary['fileType'] = m_summary.fileType
				meeting_summary['comment_date'] = human(
					datetime.datetime.strptime(
						m_summary.comment_date, "%Y-%m-%d %H:%M:%S.%f"
					)
				) if m_summary.comment_date else ''
				meeting_summary['created_by'] = m_summary.created_by.first_name
				parent_list.append(meeting_summary)
			parent_list.append(MeetingColor.objects.filter(meeting_id=pk).values())
		except MeetingSummary.DoesNotExist:
			return Response(status=204)
		return Response(parent_list)


class MeetingFileList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = MeetingDocument.objects.all()
	serializer_class = MeetingDocumentSerializer

	@staticmethod
	def wavformat(url):
		filename, headers = urlretrieve(url)
		with audioread.audio_open(filename) as f:
			print f.duration
		return (f.duration)

	@staticmethod
	def mp3format(url):
		filename, headers = urlretrieve(url)
		try:
			audioplay = MP3(filename)
			audply =  audioplay.info.length
			status = 'ok_supported_media_type'
		except mutagen.mp3.HeaderNotFoundError:
			print "MP3 Header Error on file: ", filename
			audply = 0.0
			status= 'HTTP_415_UNSUPPORTED_MEDIA_TYPE'
		return (audply , status)

	@staticmethod
	def videoformat(url):
		clip = VideoFileClip(url)
		dur = clip.duration
		return (dur)

	def post(self, request, format=None):
		serializer = MeetingDocumentSerializer(data=request.data)
		if serializer.is_valid():

			serializer.save()
			serializer.save(fileName = request.data['meetingFile'])
			url = request.build_absolute_uri('{0}'.format(serializer.data['meetingFile']))
			data ={}

			if (serializer.data['fileType'] == 'audio'):
				regx = ".mp3" in url
				dur, m_status = MeetingFileList.mp3format(url) if regx else MeetingFileList.wavformat(url)
				data['duration'] = dur
				data['status'] = m_status
			elif(serializer.data['fileType'] == 'video'):
				dur = MeetingFileList.videoformat(url)
				data['duration'] = dur

			else:
				pass				

			data['meetingId'] = serializer.data['id']
			data['meetingFile'] = url
			data['fileType'] = serializer.data['fileType']
			data['filename'] = serializer.data['fileName']
			
			return Response(data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetMeetingFileList(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = MeetingDocument.objects.all()
	serializer_class = MeetingDocumentSerializer

	def get(self,request, pk):
		meetDocs = MeetingDocument.objects.filter(meetingId_id=pk)
		meetSat = Meeting.objects.get(pk=pk)
		notes =  meetSat.notes 
		m_status = meetSat.meeting_status

		parent_list = []
		parent_dict = {}
		image, audio, video, others = [],[],[],[]


		m_action_color = []
		m_action_color = MeetingColor.objects.filter(meeting_id=pk)
		m_action_color = [
			{
				'id': x.company_meeting_color_id,
				'name': CompanyMeetingColor.objects.get(id=x.company_meeting_color_id).name,
				'color': CompanyMeetingColor.objects.get(id=x.company_meeting_color_id).color
			} for x in m_action_color]


		if meetDocs:
			for mD in meetDocs:
				if mD.fileType == 'image':
					meetingDoc_dict = {}
					meetingDoc_dict['id'] = mD.id
					meetingDoc_dict['filename'] = mD.fileName
					meetingDoc_dict['meetingFile'] = 'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(mD.meetingFile))
					image.append(meetingDoc_dict)

				elif mD.fileType == 'audio':
					meetingDoc_dict = {}
					meetingDoc_dict['id'] = mD.id
					meetingDoc_dict['filename'] = mD.fileName
					meetingDoc_dict['meetingFile'] = 'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(mD.meetingFile))
					url =  'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(mD.meetingFile)) 
					regx = ".mp3" in url
					audply , status = MeetingFileList.mp3format(url) if regx else MeetingFileList.wavformat(url)
					meetingDoc_dict['duration'] = audply
					meetingDoc_dict['status'] = status
					audio.append(meetingDoc_dict)

				elif mD.fileType == 'video':
					meetingDoc_dict = {}
					meetingDoc_dict['id'] = mD.id
					meetingDoc_dict['filename'] = mD.fileName
					meetingDoc_dict['meetingFile'] = 'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(mD.meetingFile))
					url =  'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(mD.meetingFile))
					meetingDoc_dict['duration'] = MeetingFileList.videoformat(url)
					video.append(meetingDoc_dict)

				else:
					meetingDoc_dict = {}
					meetingDoc_dict['id'] = mD.id
					meetingDoc_dict['filename'] = mD.fileName
					meetingDoc_dict['meetingFile'] = 'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(mD.meetingFile))
					others.append(meetingDoc_dict)

		parent_dict = {
			'meetingId': pk ,
			'image': image,
			'audio': audio,
			'video': video,
			'notes': notes ,
			'status': m_status,
			'company_meeting_action_color': m_action_color
		}
		parent_list.append(parent_dict)
		return Response(parent_list)


class MobileExpenseList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = RoadshowExpense.objects.all()
	serializer_class = RoadshowExpenseSerializer

	def post(self, request, format=None):
		document = ''
		if 'file' in request.data.keys():
			document=ExpenseDocument.objects.create(
				docfile=request.data['file']
			)

		# Assign the created by user
		request.data['created_by'] = request.user.id
		serializer = RoadshowExpenseSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			if document:
				expense_doc = ExpenseDocument.objects.filter(id=document.id).update(
					expense=serializer.data['id']
				)
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		else:
			if document:
				document.delete()
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyMeetingColorList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = CompanyMeetingColor.objects.all()
	serializer_class = CompanyMeetingColorSerializer


class CompanyMeetingColorListView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, pk):
		company_meeting_colors = CompanyMeetingColor.objects.filter(company_id=pk)
		parent_list = []
		for category in company_meeting_colors:
			category_dict = {}
			category_dict['id'] = category.id
			category_dict['name'] = category.name
			category_dict['color'] = category.color
			parent_list.append(category_dict)
		return Response(parent_list)

	# To update company color for meeting
	def put(self, request, pk):
		if 'company_meeting_action_color' in request.data.keys():
			meeting_color, created = MeetingColor.objects.update_or_create(
				meeting_id=pk,
				defaults={
						'company_meeting_color_id': request.data['company_meeting_action_color'],
				}
			)
		m_color = MeetingColor.objects.filter(meeting_id=pk)
		m_action_color = []
		if m_color:
			m_action_color = [
			{
				'id': m_color[0].company_meeting_color.id,
				'name': m_color[0].company_meeting_color.name,
				'color': m_color[0].company_meeting_color.color
			}]
		meeting_data = {}
		meeting_data.update({'company_meeting_action_color': m_action_color})
		return Response(meeting_data, status=status.HTTP_200_OK)

# To Update the created company colors
class CompanyMeetingColorView(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def put(self, request, pk):
		company_meeting_color_obj = CompanyMeetingColor.objects.get(id = pk)
		company_meeting_color_obj.name = request.data['name']
		company_meeting_color_obj.color = request.data['color']
		company_meeting_color_obj.save()
		return Response("CompanyMeetingColor updated successfully")

	def delete(self, request, pk):
		company_meeting_color_obj = CompanyMeetingColor.objects.get(id = pk)
		company_meeting_color_obj.delete()
		return Response("CompanyMeetingColor deleted successfully")

class MobileRoadshowList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	
	queryset = Roadshow.objects.all()
	serializer_class = RoadshowSerializer

	def list(self, request):
		company = Company.objects.filter(users__id=request.user.id)
		print company
		roadshow_ids = CompanyRoadshow.objects.filter(company=company[0]).values_list('roadshow')
		print "%^@#%^@#%", roadshow_ids, "#$%#!$%"
		objects = []
		time_type = request.GET['type']
		year=int(request.GET['current_date'].split('-')[0])
		month=int(request.GET['current_date'].split('-')[1])
		day=int(request.GET['current_date'].split('-')[2])
		date_between_ids = [
			x.id for x in Roadshow.objects.filter(
				id__in=roadshow_ids
			) if x.from_date <= datetime.date(year, month, day) <= x.to_date
		]
		print "$%^#@%^@",date_between_ids
		if time_type == 'present':
			objects = [
				{
					"id": roadshow.id,
					"status": roadshow.status,
					"description": roadshow.description,
					"title": roadshow.title,
					"from_date": roadshow.from_date,
					"to_date": roadshow.to_date,
					"created_by_id": roadshow.created_by_id,
					"road_users": [
						{
							"first_name": user.first_name,
							"profile_pic": \
								['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
									for user_profile in UserProfile.objects.filter(user=user) if user_profile.profile_pic]
						} for user in roadshow.users.all()]
				} for roadshow in Roadshow.objects.filter(
                        id__in=roadshow_ids
                ) if roadshow.from_date <= datetime.date(year, month, day) <= roadshow.to_date
			]
		elif time_type == 'past':
			objects = [
				{
					"id": roadshow.id,
					"status": roadshow.status,
					"description": roadshow.description,
					"title": roadshow.title,
					"from_date": roadshow.from_date,
					"to_date": roadshow.to_date,
					"created_by_id": roadshow.created_by_id,
					"road_users": [
						{
							"first_name":user.first_name,
							"profile_pic": \
								['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
									for user_profile in UserProfile.objects.filter(user=user) if user_profile.profile_pic]
						} for user in roadshow.users.all()]
				} for roadshow in Roadshow.objects.all().exclude(
					id__in=date_between_ids) if roadshow.from_date < datetime.date(year, month, day)
			]
		elif time_type == 'future':
			objects = [
				{
					"id": roadshow.id,
					"status": roadshow.status,
					"description": roadshow.description,
					"title": roadshow.title,
					"from_date": roadshow.from_date,
					"to_date": roadshow.to_date,
					"created_by_id": roadshow.created_by_id,
					"road_users": [
						{
							"first_name":user.first_name,
							"profile_pic": \
								['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
									for user_profile in UserProfile.objects.filter(user=user) if user_profile.profile_pic]
						} for user in roadshow.users.all()]
				} for roadshow in Roadshow.objects.all().exclude(
					id__in=date_between_ids) if roadshow.to_date > datetime.date(year, month, day)
			]
		return Response(objects)


class CompanyDefaultMessageList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = CompanyDefaultMessage.objects.all()
	serializer_class = CompanyDefaultMessageSerializer
	def list(self, request):
		company = Company.objects.filter(users__id=request.user.id)
		objects = []
		if company:
			objects = company[0].company_messages.all().values()
		return Response(objects)

class CompanyDefaultMessageDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	
	queryset = CompanyDefaultMessage.objects.all()
	serializer_class = CompanyDefaultMessageSerializer


class RoadshowExpenseCompanyPDFList(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	

	def get(self, request, pk):
		roadshow_expenses = RoadshowExpense.objects.filter(company_id=pk)
		response = HttpResponse(content_type='application/pdf')
		today = datetime.datetime.today()
		filename = 'roadshow_expense' + today.strftime('%Y-%m-%d')
		response['Content-Disposition'] =\
		    'attachement; filename={0}.pdf'.format(filename)
		buffer = BytesIO()
		report = PdfGenerate(buffer, 'A4')
		pdf = report.report(roadshow_expenses, 'Roadshow expense statistics data', request)
		response.write(pdf)
		return response



class GeneratePdfWithRoadshowUser(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	
	queryset = RoadshowExpense.objects.all()
	serializer_class = RoadshowExpenseSerializer

	def list(self, request):
		try:
			company_id = request.GET['company_id']
			roadshow_id = request.GET['roadshow_id']
			# For send specific user details
			# roadshow_user_id = request.GET['roadshow_user_id']
			# roadshow_expenses = RoadshowExpense.objects.filter(
			# 	company_id=company_id,
			# 	roadshow_user_id=roadshow_user_id,
			# 	roadshow_id=roadshow_id
			# )
			roadshow_expenses = RoadshowExpense.objects.filter(
				company_id=company_id,
				roadshow_id=roadshow_id
			)
			if roadshow_expenses:
				response = HttpResponse(content_type='application/pdf')
				today = datetime.datetime.today()
				filename = 'roadshow_expense' + today.strftime('%Y-%m-%d')
				buffer = BytesIO()
				report = PdfGenerate(buffer, 'A4')
				roadshow = Roadshow.objects.filter(pk=roadshow_id).first()
				title = '{0} expense generated by {1} on {2}'.format(
					roadshow.title,
					request.user.first_name,
					today.strftime('%Y-%m-%d')
				)
				pdf = report.report(roadshow_expenses, title, request)
				email = request.user.email
				subject = 'Roadshow Expense Report on {0}'.format(today.strftime('%Y-%m-%d'))
				body_content = "Please find the {0} roadshow expense details.".format(roadshow.title)
				emailMsg=EmailMessage(subject=subject,body=body_content,to=[email])
				emailMsg.attach(filename, pdf, 'application/pdf')
				emailMsg.send()
				return Response("Mail sent successfully", status=status.HTTP_200_OK)
			else:
				return Response("No records found", status=status.HTTP_204_NO_CONTENT)
		except:
			return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileList(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	# To fetch the User record
	def get(self, request, pk, format = None):
		user = User.objects.get(pk=pk)
		data ={}
		data['first_name'] = user.first_name
		data['last_name'] = user.last_name
		data['email'] = user.email
		user_profile = UserProfile.objects.filter(user_id=user)
		if user_profile:
			data['contact_phone'] = user_profile[0].contact_phone
			if not user_profile[0].profile_pic == '':
				image_url = \
					'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(user_profile[0].profile_pic))
			else:
				image_url = ''
			data['profile_pic'] = image_url
			data['notes'] = user_profile[0].notes
			data['designation'] = user_profile[0].designation
		else:
			user_profile = UserProfile.objects.create(user=user)
			data['contact_phone'] = user_profile.contact_phone
			data['profile_pic'] = ''
			data['notes'] = user_profile.notes
			data['designation'] = user_profile.designation

		return Response(data,status=status.HTTP_200_OK)

	# To update user record
	def put(self, request, pk, format=None):
		user = User.objects.get(pk=pk)
		user_profile = UserProfile.objects.get(user_id=user.id)
		if 'profile_pic' in request.data.keys():
			user_profile.profile_pic = request.data['profile_pic']
			user_profile.save()
		else:
			user.first_name = request.data['first_name']
			user.last_name = request.data['last_name']
			user_profile.notes = request.data['notes']
			user_profile.designation = request.data['designation']
			user_profile.contact_phone = request.data['contact_phone']
			user.save()
			user_profile.save()
		data ={}
		data['first_name'] = user.first_name
		data['last_name'] = user.last_name
		data['email'] = user.email
		data['contact_phone'] = user_profile.contact_phone
		data['designation'] = user_profile.designation
		data['profile_pic'] = \
			'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(user_profile.profile_pic))
		data['notes'] = user_profile.notes
		return Response(data,status=status.HTTP_201_CREATED)

	# To disable the login
	def delete(self, request, pk, format=None):
		user = User.objects.get(pk=pk)
		user.is_active = False
		user.save()
		return Response(status= status.HTTP_200_OK)


class MobileRoadshowDetail(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )	
	queryset = Roadshow.objects.all()
	serializer_class = RoadshowSerializer

	def calculate_weather(self, address, meeting_date):
		date = meeting_date.strftime("%d %b %Y")
		weather_dic ={}
		try:
			url = \
			'https://query.yahooapis.com/v1/public/yql?q=select * from weather.forecast where woeid in (select woeid from geo.places(1) where text="{0}")&format=json&/'.format(address)
			response = urllib.urlopen(url)
			# print url
			obj = json.load(response)
			if obj['query']['results'] != None:
				for i in range (0,9):
					json_date = obj['query']['results']['channel']['item']['forecast'][i]['date']
					if (date==json_date):
						weather_dic['forecast'] = obj['query']['results']['channel']['item']['forecast'][i]['high']
						weather_dic['description'] = obj['query']['results']['channel']['item']['forecast'][i]['text']
						weather_dic['code'] = obj['query']['results']['channel']['item']['forecast'][i]['code']
			else:
				weather_dic['forecast'] = ''
				weather_dic['description'] = ''
				weather_dic['code'] = ''
		except:
			pass
		return weather_dic


	def calculate_user_meeting_overlap(self, meeting, prev_meeting_end_time):
		from datetime import timedelta
		from datetime import datetime
		FMT = '%H:%M'
		time_differnce = datetime.strptime(meeting.end_time, FMT) - datetime.strptime(prev_meeting_end_time, FMT)

		meeting_users = MeetingUser.objects.filter(
			meeting_id=meeting.id
		)
		time_status = []
		for mUser in meeting_users:
			if not mUser.duration.isdigit():
				time_split = [x for x in mUser.duration.split(' ') if x.isdigit()]
				# check minutes or hours
				if len(time_split) == 1:
					user_time = timedelta(minutes=int(time_split[0]))
					time_status.append(user_time > time_differnce)
				else:
					user_time = timedelta(hours=int(time_split[0]),minutes=int(time_split[1]))
					time_status.append(user_time > time_differnce)
		return True in time_status

	def calculate_roadshow_dashboard(self, road_show, roadshow_dates_list, request):
		parent_list = []
		for m_date in roadshow_dates_list:
			parent_dict = {}
			parent_dict['date'] = m_date.strftime('%d %b %Y %A')
			meetings_list = road_show.meetings.filter(meeting_date=m_date).order_by('start_time')
			flights_list = road_show.roadshowflights.filter(from_date=m_date)
			cars_list = road_show.roadshowrentals.filter(from_date=m_date)
			dinner_list = road_show.roadshowdinner.filter(dinner_date=m_date)
			hotels_list = road_show.roadshowhotels.filter(from_date=m_date)

			data_list = []
			if meetings_list:
				for index, meeting_data in enumerate(meetings_list):
					if request.user.id in [muser.user.id for muser in meeting_data.meetingusers.all()]:
						m_dict = {}
						m_dict['id'] = meeting_data.id
						m_dict['name'] = meeting_data.company_name
						m_dict['timeStart'] = meeting_data.start_time
						m_dict['timeEnd'] = meeting_data.end_time
						m_dict['city'] = meeting_data.city
						m_dict['state'] = meeting_data.state
						m_dict['postalCode'] = meeting_data.postcode
						m_dict['linkedin_url'] = meeting_data.linkedin_url
						m_dict['user_linkedin_url'] = meeting_data.user_linkedin_url
						m_dict['user_twitter_url'] = meeting_data.user_twitter_url
						m_dict['company_twitter_url'] = meeting_data.company_twitter_url
						m_dict['meeting_type'] = meeting_data.meeting_type.name
						# m_dict['distance_prev'] = meeting_data.distance_prev
						m_dict['address'] = meeting_data.address
						user_count = meeting_data.meetingusers.count()
						m_dict['user_count'] = user_count
						if user_count <= 1 and user_count != 0:
							# If single user goes to meeting
							meeting_user = MeetingUser.objects.get(
								meeting_id=meeting_data.id
							)
							m_dict['user_duration'] = meeting_user.duration
							m_dict['distance_prev'] = meeting_user.distance
						else:
							# if user count > 1 this is for front end team
							m_dict['user_duration'] = 0
							m_dict['distance_prev'] = meeting_data.distance_prev
						m_dict['type'] = 'meeting'
						m_dict['already_time_exists'] = meeting_data.start_time in \
							[x['timeStart'] for x in data_list]
						if meeting_data == meetings_list.last():
							m_dict['is_last_meeting'] = True
						else:
							m_dict['is_last_meeting'] = False
						if meeting_data != meetings_list.first():
							try:
								prev_entity = meetings_list[index-1]
								m_dict['prev_entity_id'] = prev_entity.id
								m_dict['prev_entity_type'] = 'meeting'
								m_dict['user_time_overlap'] = self.calculate_user_meeting_overlap(
									meeting_data,
									prev_entity.end_time
								)
							except:
								pass
						m_dict['weather'] = self.calculate_weather(meeting_data.address, m_date)
						m_action_color = []
						m_action_color = MeetingColor.objects.filter(meeting_id=meeting_data.id)
						m_action_color = [
							{
								'id': x.company_meeting_color_id,
								'name': CompanyMeetingColor.objects.get(id=x.company_meeting_color_id).name,
								'color': CompanyMeetingColor.objects.get(id=x.company_meeting_color_id).color
							} for x in m_action_color]
						m_dict['company_meeting_action_color'] = m_action_color

						data_list.append(m_dict)
			if flights_list:
				for flight_data in flights_list:
					if request.user.id in [user.id for user in flight_data.users.all()]:
						f_dict = {}
						f_dict['id'] = flight_data.id
						f_dict['name'] = flight_data.airline
						f_dict['timeStart'] = flight_data.start_time
						f_dict['timeEnd'] = flight_data.end_time
						f_dict['address'] = flight_data.to_airport
						f_dict['user_count'] = flight_data.users.count()
						f_dict['type'] = 'flight'
						data_list.append(f_dict)
			if cars_list:
				for car_data in cars_list:
					if request.user.id in [user.id for user in car_data.users.all()]:
						c_dict = {}
						c_dict['id'] = car_data.id
						c_dict['name'] = car_data.rental_name
						c_dict['timeStart'] = car_data.start_time
						c_dict['timeEnd'] = car_data.end_time
						c_dict['user_count'] = car_data.users.count()
						c_dict['fromCity'] = car_data.from_city
						c_dict['toCity'] = car_data.to_city
						c_dict['from_pincode'] = car_data.from_pincode
						c_dict['to_pincode'] = car_data.to_pincode
						c_dict['from_state'] = car_data.from_state
						c_dict['to_state'] = car_data.to_state
						c_dict['type'] = 'cab'
						data_list.append(c_dict)
			if dinner_list:
				for dinner_data in dinner_list:
					if request.user.id in [user.id for user in dinner_data.users.all()]:
						d_dict = {}
						d_dict['id'] = dinner_data.id
						d_dict['name'] = dinner_data.name
						d_dict['timeStart'] = dinner_data.start_time
						d_dict['timeEnd'] = dinner_data.end_time
						d_dict['user_count'] = dinner_data.users.count()
						d_dict['type'] = 'dinner'
						data_list.append(d_dict)
			hotel_data_list = []
			if hotels_list:
				for hotel_data in hotels_list:
					if request.user.id in [user.id for user in hotel_data.users.all()]:
						h_dict = {}
						h_dict['id'] = hotel_data.id
						h_dict['name'] = hotel_data.hotel_name
						h_dict['timeStart'] = hotel_data.start_time
						h_dict['timeEnd'] = hotel_data.end_time
						h_dict['address'] = hotel_data.hotel_address
						h_dict['user_count'] = hotel_data.users.count()
						h_dict['city'] = hotel_data.city
						h_dict['pincode'] = hotel_data.pincode
						h_dict['state'] = hotel_data.state
						if meetings_list:
							h_dict['distance_prev'] = hotel_data.distance_prev
							h_dict['prev_entity_id'] = meetings_list.last().id
							h_dict['prev_entity_type'] = 'meeting'
						h_dict['type'] = 'hotel'
						h_dict['parent_hotel_id'] = hotel_data.parent_hotel_id
						hotel_data_list.append(h_dict)
			# Sorting the list of dict by the time start time
			#parent_dict['schedule'] = data_list
			parent_dict['schedule'] = sorted(data_list, key=itemgetter('timeStart'))
			# Keep the hotel object at the last as per the requirement

			parent_dict['schedule'] = parent_dict['schedule'] + hotel_data_list
			
			# Calculate the distance logic for the previous date last entity and current date first entity
			if parent_list:
				if parent_list[-1]['schedule']:
					if parent_dict['schedule'] and parent_dict['schedule'][0]['type'] == 'meeting':
						try:
							origin = parent_list[-1]['schedule'][-1]['address']
							destination = parent_dict['schedule'][0]['address']
							url = \
							'https://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&key={2}'.format(
								origin, destination, settings.GOOGLE_API_KEY
							)
							response = urllib.urlopen(url)
							distance = json.load(response)
							if distance['rows'][0]['elements'][0]['status'] != 'NOT_FOUND':
								distance = distance['rows'][0]['elements'][0]['distance']['value']
							else:
								distance = 0
						except:
						    # Address Not Found
						    distance = 0
						parent_dict['schedule'][0]['distance_prev'] = distance
						parent_dict['schedule'][0]['prev_entity_id'] = parent_list[-1]['schedule'][-1]['id']
						parent_dict['schedule'][0]['prev_entity_type'] = parent_list[-1]['schedule'][-1]['type']
			parent_list.append(parent_dict)
		return parent_list

	def get(self, request, pk, format=None):
		road_show = Roadshow.objects.get(pk=pk)

		start_date = road_show.from_date
		end_date = road_show.to_date

		total_days = (end_date - start_date).days + 1

		roadshow_dates_list = [(start_date + dt.timedelta(days = day_number)) \
			for day_number in range(total_days)]
		
		output_list = self.calculate_roadshow_dashboard(road_show, roadshow_dates_list, request)
		return Response(output_list)


class CompanyLinkedin(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def linkedin_companies_parser(self, url, meeting):
		# try:
		print "^&$#^$#^$@#", url, meeting.company_name
		headers = {
		'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}
		urllib3.disable_warnings()
		response = requests.get(url, headers=headers)
		formatted_response = response.content.replace('<!--', '').replace('-->', '')
		doc = html.fromstring(formatted_response)
		print "^^^^^^^^^^",doc
		datafrom_xpath = doc.xpath('//code[@id="stream-promo-top-bar-embed-id-content"]//text()')
		print "%@@@@@@@@",datafrom_xpath
		if datafrom_xpath:
			try:
				json_formatted_data = json.loads(datafrom_xpath[0])
				company_name = json_formatted_data['companyName'] if 'companyName' in json_formatted_data.keys() else None
				size = json_formatted_data['size'] if 'size' in json_formatted_data.keys() else None
				industry = json_formatted_data['industry'] if 'industry' in json_formatted_data.keys() else None
				description = json_formatted_data['description'] if 'description' in json_formatted_data.keys() else None
				follower_count = json_formatted_data['followerCount'] if 'followerCount' in json_formatted_data.keys() else None
				year_founded = json_formatted_data['yearFounded'] if 'yearFounded' in json_formatted_data.keys() else None
				website = json_formatted_data['website'] if 'website' in json_formatted_data.keys() else None
				company_type = json_formatted_data['companyType'] if 'companyType' in json_formatted_data.keys() else None
				specialities = json_formatted_data['specialties'] if 'specialties' in json_formatted_data.keys() else None

				if "headquarters" in json_formatted_data.keys():
				    city = json_formatted_data["headquarters"]['city'] if 'city' in json_formatted_data["headquarters"].keys() else None
				    country = json_formatted_data["headquarters"]['country'] if 'country' in json_formatted_data['headquarters'].keys() else None
				    state = json_formatted_data["headquarters"]['state'] if 'state' in json_formatted_data['headquarters'].keys() else None
				    street1 = json_formatted_data["headquarters"]['street1'] if 'street1' in json_formatted_data['headquarters'].keys() else None
				    street2 = json_formatted_data["headquarters"]['street2'] if 'street2' in json_formatted_data['headquarters'].keys() else None
				    zipcode = json_formatted_data["headquarters"]['zip'] if 'zip' in json_formatted_data['headquarters'].keys() else None
				    street = '{0}, {1}'.format(street1, street2)
				else:
				    city = None
				    country = None
				    state = None
				    street1 = None
				    street2 = None
				    street = None
				    zipcode = None

				data = {
				    'company_name': company_name,
				    'size': size,
				    'industry': industry,
				    'description': description,
				    'follower_count': follower_count,
				    'year_founded': year_founded,
				    'website': website,
				    'company_type': company_type,
				    'specialities': specialities,
				    'city': city,
				    'country': country,
				    'state': state,
				    'street': street,
				    'zipcode': zipcode,
				    'url': url
				}
				obj=CompanyLinkedIn.objects.create(
				    name=data['company_name'],
				    description=data['description'],
				    founded=data['year_founded'],
				    specialities=', '.join(data['specialities']) if data['specialities'] else '',
				    street=data['street'],
				    city=data['city'],
				    state=data['state'],
				    zipcode=data['zipcode'],
				    country=data['country'],
				    industry=data['industry'],
				    website=data['website'],
				    follower_count=data['follower_count'],
				    company_type=data['company_type'],
				    profile_url=url
				)
				m_company_linkedin = MeetingCompanyLinkedIn.objects.create(
					meeting=meeting,
					company_linkedin=obj
				)
				return [obj]
			except:
		        #pass
				return []
		# # except :
		# 	#pass
		# 	print 
		# 	return []


	# To update the company linkedin profile
	def get(self, request, pk, format = None):
		output_data = []
		obj = MeetingCompanyLinkedIn.objects.filter(meeting=pk).first()
		print "2342",obj,"53453"
		if obj:
			return Response(json.loads(serializers.serialize('json', [obj.company_linkedin])), status= status.HTTP_200_OK)
		else:
			# call crawl method to get the data
			meeting = Meeting.objects.filter(id=pk).first()
			print meeting.company_name
			if meeting:
				if meeting.linkedin_url != '':
					print "&&&&&&&&"
					output_data = self.linkedin_companies_parser(meeting.linkedin_url, meeting)
					print "%$^@%@",output_data
					return Response(json.loads(serializers.serialize('json', output_data)), status= status.HTTP_200_OK)
		return Response(output_data, status= status.HTTP_200_OK)



class CompanyTwitterAPI(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def twitter_companies_parser(self, url, meeting):
		import tweepy
		consumer_key ='Pz4VMCzfNnNR4Iwl7DCMrW93O'
		consumer_secret ='hbdj05RIuJrYVX10V3UPu9EWrclQr1gxKTHwX1n0F7Vyji6Vp7'
		access_token ='817697569937600512-ciw5Qaldpk3Et8Gkr5ycleECA54Sjem'
		access_token_secret ='2QlBUozskOS67ZhPcHbnhDANrAx80bEkvWWdbK4PuBALl'
		auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
		auth.set_access_token(access_token, access_token_secret)
		api = tweepy.API(auth)
		try:
			com_nam = url.split('/')[-1]
			user = api.get_user(com_nam)
			twt_data = {
			    'screen_name': user.screen_name,
			    'name': user.name,
			    'description': user.description,
			    'follower_count': user.followers_count,
			    'statuses': user.statuses_count,
			    'location': user.location,
			    'url': user.url,
			    'profile_pic': user.profile_image_url,
			}
			ct_obj=CompanyTwitter.objects.create(
				name=twt_data['name'],
				description=twt_data['description'],
				follower_count=twt_data['follower_count'],
				statuses=twt_data['statuses'],
				location=twt_data['location'],
				website=twt_data['url'],
				profile_pic=twt_data['profile_pic'],
				profile_url=url
			)
			m_company_twitter = MeetingCompanyTwitter.objects.create(
				meeting=meeting,
				company_twitter=ct_obj
			)
			return ct_obj
		except:
		    return []

	# To update the company twitter profile
	def get(self, request, pk, format = None):
		output_data = []
		obj = MeetingCompanyTwitter.objects.filter(meeting=pk).first()
		if obj:
			return Response(
				json.loads(
					serializers.serialize('json', [obj.company_twitter])
				), status= status.HTTP_200_OK
			)
		else:
			# call crawl method to get the data
			meeting = Meeting.objects.filter(id=pk).first()
			if meeting:
				if meeting.company_twitter_url != '':
					output_data = self.twitter_companies_parser(
						meeting.company_twitter_url,
						meeting
					)
					return Response(
						json.loads(
							serializers.serialize('json', [output_data])
						), status= status.HTTP_200_OK
					)
		return Response(
			output_data,
			status= status.HTTP_200_OK
		)


class AjaxCallAPI(APIView):
	def get(self, request):
		print "inside the get request call"

		return Response({'response':True})

	def post(self, request, format=None):
		print "inside The post request Call"
		print request.data
		data = request.data

		return Response( data)


"""
This class module will be used for give the necessary information to mobile
dashboard page display.
"""
class MobileRoadshowDashboard(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, format = None):
		output_data = {}
		current_date = request.GET['current_date']
		current_time = request.GET['current_time']
		year=int(request.GET['current_date'].split('-')[0])
		month=int(request.GET['current_date'].split('-')[1])
		day=int(request.GET['current_date'].split('-')[2])
		total_today_meetings = len(
			[
				x for x in Meeting.objects.filter(
					meeting_date=current_date
				) if len(x.meetingusers.filter(user__in=[request.user])) > 0 
			]
		)
		current_roadshows = [
			{"id": roadshow.id, "name": roadshow.title} for roadshow in Roadshow.objects.all() \
				if roadshow.from_date <= datetime.date(year, month, day) <= roadshow.to_date
		]

		# Fetch upcomming 3 meeting records. To this check current date and future date the limit the reocrds as 3.
		today_upcoming_meetings = \
			[
				meeting for meeting in Meeting.objects.filter(
					meeting_date=current_date,
					start_time__gt=current_time
				).order_by('start_time') if len(meeting.meetingusers.filter(user__in=[request.user])) > 0 
			]
		future_meetings = \
			[
				meeting for meeting in Meeting.objects.filter(
					meeting_date__gt=current_date,
				)if len(meeting.meetingusers.filter(user__in=[request.user])) > 0 
			]

		#meetings_list = today_upcoming_meetings[:3] + future_meetings[:3]
		meetings_list = today_upcoming_meetings
		print "meetings_list --->", meetings_list
		data_list = []
		for index, meeting_data in enumerate(meetings_list):
			m_dict = {}
			m_dict['id'] = meeting_data.id
			m_dict['name'] = meeting_data.company_name
			m_dict['contactPerson'] = meeting_data.contact_name
			m_dict['contactTitle'] = meeting_data.contact_title
			m_dict['addressLine1'] = meeting_data.company_address_line1
			m_dict['addressLine2'] = meeting_data.company_address_line2
			m_dict['state'] = meeting_data.state
			m_dict['postalCode'] = meeting_data.postcode
			m_dict['companyEmail'] = meeting_data.company_email
			m_dict['companyPhone'] = meeting_data.company_phone
			m_dict['companyMobile'] = meeting_data.company_mobile
			m_dict['meeting_date'] = meeting_data.meeting_date.strftime("%d %b %Y")
			m_dict['timeStart'] = meeting_data.start_time
			m_dict['timeEnd'] = meeting_data.end_time
			m_dict['city'] = meeting_data.city
			m_dict['linkedin_url'] = meeting_data.linkedin_url
			m_dict['user_linkedin_url'] = meeting_data.user_linkedin_url
			m_dict['user_twitter_url'] = meeting_data.user_twitter_url
			m_dict['company_twitter_url'] = meeting_data.company_twitter_url
			m_dict['roadshow_name'] = meeting_data.roadshow.title
			m_dict['roadshow_id'] = meeting_data.roadshow.id
			try:
				m_dict['meeting_type'] = meeting_data.meeting_type.name
			except:
				m_dict['meeting_type'] = ''
				pass
			user_count = meeting_data.meetingusers.count()
			m_dict['user_count'] = user_count
			user_count = meeting_data.meetingusers.count()
			m_action_color = []
			m_action_color = MeetingColor.objects.filter(meeting_id=meeting_data.id)
			m_action_color = [
				{
					'id': x.company_meeting_color.id,
					'name': x.company_meeting_color.name,
					'color': x.company_meeting_color.color
				} for x in m_action_color]
			m_dict['company_meeting_action_color'] = m_action_color
			m_dict['meeting_users'] = [
						{
							"first_name":user.user.first_name,
							"profile_pic": \
								['http://'+request.META['HTTP_HOST']+user_profile.profile_pic.url \
									for user_profile in UserProfile.objects.filter(user=user.user) if user_profile.profile_pic]
						} for user in meeting_data.meetingusers.all()]
			data_list.append(m_dict)



		output_data['total_today_meetings'] = total_today_meetings
		output_data['current_roadshows'] = current_roadshows
		output_data['future_meetings'] = data_list
		return Response(
			output_data,
			status= status.HTTP_200_OK
		)


class UserPreferList(generics.ListCreateAPIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )
	queryset = UserPreference.objects.all()
	serializer_class = UserPreferenceSerializer
	def list(self, request, format = None) :
		try:
			user_preference = UserPreference.objects.filter(user= request.user)
			return Response(user_preference.values('id','farenheit_celcius'), status= status.HTTP_200_OK	)
		except UserPreference.DoesNotExist:
			raise Http404

	def post(self, request, format=None):
		user_preference = UserPreference.objects.filter(user=request.user)
		request.data['user']=request.user.id
		if user_preference:
			user_preference.update(farenheit_celcius=request.data['farenheit_celcius'])
			return Response(user_preference.values('id','farenheit_celcius')
				, status=status.HTTP_200_OK)  #{'farenheit_celcius': user_preference[0].farenheit_celcius, 'id': user_preference[0].id }
		else:
			serializer = UserPreferenceSerializer(data=request.data)
			if serializer.is_valid():
				serializer.save()
				return Response(serializer.data, status=status.HTTP_201_CREATED)

		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MobileMeetingSummaryDetail(APIView):
	permission_classes = (IsAuthenticated, )
	authentication_classes = (JSONWebTokenAuthentication, )

	def get(self, request, pk, format=None):
		try:
			meeting_summaries = MeetingSummary.objects.filter(meetingId_id=pk)
			parent_list = []
			for m_summary in meeting_summaries:
				meeting_summary={}
				meeting_summary['Id'] = m_summary.id
				meeting_summary['meetingDoc'] = \
					'http://'+request.META['HTTP_HOST']+settings.MEDIA_URL+('{0}'.format(m_summary.meetingDoc))
				meeting_summary['comments'] = m_summary.comments
				meeting_summary['fileType'] = m_summary.fileType
				meeting_summary['comment_date'] = human(
					datetime.datetime.strptime(
						m_summary.comment_date, "%Y-%m-%d %H:%M:%S.%f"
					)
				) if m_summary.comment_date else ''
				meeting_summary['created_by'] = m_summary.created_by.first_name
				parent_list.append(meeting_summary)
		except MeetingSummary.DoesNotExist:
			return Response(status=204)
		return Response(parent_list)
