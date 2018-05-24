from rest_framework import serializers
from django.contrib.auth.models import User
from serverapi.models import *
from django.core.mail import EmailMessage
from django.conf import settings

# You must import the CachedSerializerMixin and cache_registry
from rest_framework_cache.serializers import CachedSerializerMixin
from rest_framework_cache.registry import cache_registry


class UserSerializer(CachedSerializerMixin, serializers.ModelSerializer):	
	class Meta:
		model = User
		fields = (
			'id',
			'username',
			'password',
			'email',
			'first_name',
			'last_name','is_staff',
			'is_superuser',
			'is_active',
			'date_joined',
		)
		extra_kwargs = {'password': {'write_only': True}}
		read_only_fields = ('id','is_staff', 'is_active', 'date_joined',)

	def send_email_to_user(self, user, passwd):
		if user.email and passwd:
			html_content ="Hi,<br> Your username: %s <br> Password: %s"
			from_email   = settings.DEFAULT_FROM_EMAIL
			message      = EmailMessage('Welcome', html_content %(user.email, passwd), from_email, [user.email])
			message.content_subtype = "html"  # Main content is now text/html
			message.send()

	def create(self, validated_data):
		user = User.objects.create(**validated_data)
		user.set_password(validated_data['password'])
		user.save()
		self.send_email_to_user(user, validated_data['password'])
		return user

	def update(self, instance, validated_data):	
		instance.email = validated_data['email']
		instance.username = validated_data['username']
		instance.first_name = validated_data['first_name']
		instance.last_name = validated_data['last_name']
		if validated_data['password']:
			instance.set_password(validated_data['password'])
		instance.save()
		return instance

class RoadshowSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = Roadshow

class RoadshowCitySerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = RoadshowCity

class RoadshowDateSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = RoadshowDate

class RoadshowMeetingSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = Meeting

class RoadshowFlightSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = RoadshowFlight

class RoadshowHotelSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = RoadshowHotel

class RoadshowRentalSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = RoadshowRental

class RoadshowExpenseSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = RoadshowExpense

class ExpenseDocumentSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = ExpenseDocument

class RoadshowDinnerSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = RoadshowDinner

class CategorySerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = Category


class MeetingSummarySerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = MeetingSummary

class MeetingDocumentSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = MeetingDocument

class CompanyMeetingColorSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = CompanyMeetingColor

class CompanyDefaultMessageSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = CompanyDefaultMessage

class UserPreferenceSerializer(CachedSerializerMixin, serializers.ModelSerializer):
	class Meta:
		model = UserPreference

cache_registry.register(UserSerializer)
cache_registry.register(RoadshowSerializer)
cache_registry.register(RoadshowCitySerializer)
cache_registry.register(RoadshowDateSerializer)
cache_registry.register(RoadshowMeetingSerializer)
cache_registry.register(RoadshowFlightSerializer)
cache_registry.register(RoadshowHotelSerializer)
cache_registry.register(RoadshowRentalSerializer)
cache_registry.register(RoadshowExpenseSerializer)
cache_registry.register(ExpenseDocumentSerializer)
cache_registry.register(RoadshowDinnerSerializer)
cache_registry.register(CategorySerializer)
cache_registry.register(MeetingSummarySerializer)
cache_registry.register(MeetingDocumentSerializer)
cache_registry.register(CompanyMeetingColorSerializer)
cache_registry.register(CompanyDefaultMessageSerializer)

cache_registry.register(UserPreferenceSerializer)