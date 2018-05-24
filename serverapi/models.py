from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.contrib.auth.models import User, Group
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.core.exceptions import ValidationError


class Company(models.Model):
	name = models.CharField(max_length=150)
	users = models.ManyToManyField('auth.User')

	def __unicode__(self):
		return self.name

# Create your models here.
class Roadshow(models.Model):
	title = models.CharField(max_length=200)
	from_date = models.DateField(null=False,blank=False)
	to_date = models.DateField(null=False,blank=False)
	status = models.IntegerField(default=0)
	users = models.ManyToManyField('auth.User')
	created_by = models.ForeignKey('auth.User', related_name='userroadshows')
	description = models.TextField(null=True,blank=True)

class RoadshowCity(models.Model):
	roadshow = models.ForeignKey(Roadshow, related_name='roadshowcities')
	city_name = models.CharField(max_length=200)
	from_date = models.DateField(null=False,blank=False)
	to_date = models.DateField(null=False,blank=False)
	status = models.IntegerField(default=0)

class RoadshowDate(models.Model):
	roadshow_city = models.ForeignKey(RoadshowCity, related_name='roadshowdates')
	roadshow_date = models.DateField(null=False,blank=False)
	status = models.IntegerField(default=0)

class RoadshowMeeting(models.Model):
	roadshow_date = models.ForeignKey(RoadshowDate, related_name='roadshowmeetings')
	company_name = models.CharField(max_length=500)
	company_size = models.CharField(max_length=50,null=True,blank=True)
	company_address = models.CharField(max_length=500,null=True,blank=True)
	company_email = models.CharField(max_length=500,null=True,blank=True)
	company_phone = models.CharField(max_length=15,null=True,blank=True)
	contact_name = models.CharField(max_length=250,null=True,blank=True)	
	contact_title = models.CharField(max_length=250,null=True,blank=True)	
	contact_email = models.CharField(max_length=500,null=True,blank=True)
	contact_phone = models.CharField(max_length=15,null=True,blank=True)
	meeting_address = models.CharField(max_length=500)	
	meeting_time = models.TimeField(null=False,blank=False)
	distance_next = models.IntegerField(default=0)
	distance_prev = models.IntegerField(default=0)
	minutes_to_next = models.IntegerField(default=0)
	minutes_to_prev = models.IntegerField(default=0)
	sort_order = models.IntegerField(default=0)
	status = models.IntegerField(default=0)
	users = models.ManyToManyField('auth.User')
	created_by = models.ForeignKey('auth.User', related_name='usermeetings')


class MeetingType(models.Model):
	name = models.CharField(max_length=50,null=False,blank=False)

	def __unicode__(self):
		return self.name


class MeetingMode(models.Model):
	name = models.CharField(max_length=50,null=False,blank=False)

	def __unicode__(self):
		return self.name


class Meeting(models.Model):
	roadshow = models.ForeignKey(Roadshow, related_name='meetings')
	meeting_date = models.DateField(null=False,blank=False)
	company_name = models.CharField(max_length=250,null=True,blank=True)
	company_size = models.CharField(max_length=50,null=True,blank=True)
	company_address_line1 = models.CharField(max_length=250,null=True,blank=True)
	company_address_line2 = models.CharField(max_length=250,null=True,blank=True)
	state = models.CharField(max_length=250,null=True,blank=True)
	postcode = models.CharField(max_length=250,null=True,blank=True)
	company_email = models.CharField(max_length=500,null=True,blank=True)
	company_phone = models.CharField(max_length=15,null=True,blank=True)
	contact_name = models.CharField(max_length=250,null=True,blank=True)	
	contact_title = models.CharField(max_length=250,null=True,blank=True)	
	company_mobile = models.CharField(max_length=15,null=True,blank=True)
	start_time = models.CharField(max_length=15,null=True,blank=True)
	end_time = models.CharField(max_length=15,null=True,blank=True)	
	sales_team = models.CharField(max_length=250,null=True,blank=True)
	city = models.CharField(max_length=250,null=True,blank=True)
	distance_next = models.IntegerField(default=0,null=True,blank=True)
	distance_prev = models.IntegerField(default=0,null=True,blank=True)
	description = models.CharField(max_length=250,null=True,blank=True)
	created_by = models.ForeignKey('auth.User', related_name='userroadshowmeetings')
	meeting_type = models.ForeignKey(MeetingType)
	meeting_type_other = models.CharField(max_length=250,null=True,blank=True)
	address = models.CharField(max_length=250,null=True,blank=True)
	notes = models.TextField(null=True,blank=True)
	linkedin_url = models.CharField(max_length=250,null=True,blank=True)
	user_linkedin_url = models.CharField(max_length=250,null=True,blank=True)
	company_twitter_url = models.CharField(max_length=250,null=True,blank=True)
	user_twitter_url = models.CharField(max_length=250,null=True,blank=True)
	meeting_status = models.NullBooleanField(null=True,default=None)
	company_url = models.CharField(max_length=250,null=True,blank=True)


class MeetingUser(models.Model):
	user = models.ForeignKey(User)
	meeting = models.ForeignKey(Meeting, related_name='meetingusers')
	meeting_mode = models.ForeignKey(MeetingMode)
	meeting_mode_other = models.CharField(max_length=250,null=True,blank=True)
	from_address = models.CharField(max_length=250,null=True,blank=True)
	from_city = models.CharField(max_length=250,null=True,blank=True)
	to_address = models.CharField(max_length=250,null=True,blank=True)
	to_city = models.CharField(max_length=250,null=True,blank=True)
	date_of_travel = models.CharField(max_length=250,null=True,blank=True)
	distance = models.IntegerField(default=0,null=True,blank=True)
	duration = models.CharField(max_length=250,null=True,blank=True)


class CompanyMeetingColor(models.Model):
	company = models.ForeignKey(Company)
	name = models.CharField(max_length=50, null=True, blank=True)
	color = models.CharField(max_length=50, null=True, blank=True)

class MeetingColor(models.Model):
	company_meeting_color = models.ForeignKey(
		CompanyMeetingColor,
	)
	meeting = models.ForeignKey(
		Meeting,
		related_name='meetingcolors'
	)

class RoadshowFlight(models.Model):
	roadshow = models.ForeignKey(Roadshow, related_name='roadshowflights')
	airline = models.CharField(max_length=150)
	airline_class = models.CharField(max_length=150,null=True,blank=True)	
	from_airport = models.CharField(max_length=500)
	to_airport = models.CharField(max_length=500)
	from_date_time = models.DateTimeField(null=True,blank=True)
	to_date_time = models.DateTimeField(null=True,blank=True)
	start_time = models.CharField(max_length=15,null=False,blank=False)
	end_time = models.CharField(max_length=15,null=False,blank=False)
	from_date = models.DateField(null=False,blank=False)
	distance_to_next = models.IntegerField(default=0,null=True,blank=True)
	distance_to_prev = models.IntegerField(default=0,null=True,blank=True)
	minutes_to_next = models.IntegerField(default=0,null=True,blank=True)
	minutes_to_prev = models.IntegerField(default=0,null=True,blank=True)
	status = models.IntegerField(default=0,null=True,blank=True)
	to_date = models.DateField(null=False,blank=False)
	users = models.ManyToManyField('auth.User')
	created_by = models.ForeignKey('auth.User', related_name='userflights')
	state = models.CharField(max_length=250,null=True,blank=True)
	source_flight_code = models.CharField(max_length=250,null=True,blank=True)
	destination_flight_code = models.CharField(max_length=250,null=True,blank=True)

class RoadshowHotel(models.Model):
	roadshow = models.ForeignKey(Roadshow, related_name='roadshowhotels')
	hotel_name = models.CharField(max_length=150)	
	hotel_address = models.CharField(max_length=150,null=True,blank=True)	
	hotel_email = models.CharField(max_length=150,null=True,blank=True)	
	hotel_phone = models.CharField(max_length=15,null=True,blank=True)	
	from_date = models.DateField(null=True,blank=True)
	to_date = models.DateField(null=True,blank=True)
	status = models.IntegerField(default=0)
	start_time = models.CharField(max_length=15,null=True,blank=True)
	end_time = models.CharField(max_length=15,null=True,blank=True)
	city = models.CharField(max_length=250,null=True,blank=True)
	pincode = models.CharField(max_length=250,null=True,blank=True)
	distance_next = models.IntegerField(default=0,null=True,blank=True)
	distance_prev = models.IntegerField(default=0,null=True,blank=True)
	users = models.ManyToManyField('auth.User')
	parent_hotel_id = models.IntegerField(default=0)
	created_by = models.ForeignKey('auth.User', related_name='userhotels')
	state = models.CharField(max_length=250,null=True,blank=True)

class RoadshowRental(models.Model):
	roadshow = models.ForeignKey(Roadshow, related_name='roadshowrentals')
	rental_name = models.CharField(max_length=150)	
	rental_address = models.CharField(max_length=150,null=True,blank=True)	
	rental_email = models.CharField(max_length=150,null=True,blank=True)	
	rental_phone = models.CharField(max_length=15,null=True,blank=True)	
	from_date = models.DateField(null=True,blank=True)
	to_date = models.DateField(null=True,blank=True)
	start_time = models.CharField(max_length=15,null=True,blank=True)
	end_time = models.CharField(max_length=15,null=True,blank=True)
	status = models.IntegerField(default=0)
	users = models.ManyToManyField('auth.User')
	created_by = models.ForeignKey('auth.User', related_name='userrentals')
	rental_type = models.CharField(max_length=15,null=True,blank=True)
	to_pincode = models.CharField(max_length=15,null=True,blank=True)
	from_pincode = models.CharField(max_length=15,null=True,blank=True)
	from_city = models.CharField(max_length=150,null=True,blank=True)
	to_city = models.CharField(max_length=150,null=True,blank=True)
	from_address = models.CharField(max_length=150,null=True,blank=True)
	to_address = models.CharField(max_length=150,null=True,blank=True)
	from_state = models.CharField(max_length=250,null=True,blank=True)
	to_state = models.CharField(max_length=250,null=True,blank=True)
	confirmation_code = models.CharField(max_length=250,null=True,blank=True)
	is_prepaid = models.NullBooleanField(null=True,default=None)

class Category(models.Model):
	company = models.ForeignKey(Company)
	name = models.CharField(max_length=50, null=True, blank=True)
	color = models.CharField(max_length=50, null=True, blank=True)


class RoadshowExpense(models.Model):
	roadshow = models.ForeignKey(Roadshow, related_name='roadshowexpenses')
	expense_title = models.CharField(max_length=150,null=True,blank=True)	
	expense_description = models.CharField(max_length=150,null=True,blank=True)	
	expense_amount = models.CharField(max_length=150,null=True,blank=True)	
	expense_time = models.TimeField(null=True,blank=True)	
	status = models.IntegerField(default=0)
	category = models.ForeignKey(
		Category,
		related_name = 'expense_categories',
		default=''
	)
	expense_date = models.DateField(null=True,blank=True)
	payment_method = models.CharField(max_length=150,null=True,blank=True)
	currency_type = models.CharField(max_length=50,null=True,blank=True)
	minus_personal = models.CharField(max_length=50,null=True,blank=True)
	final_amount = models.CharField(max_length=50,null=True,blank=True)
	expense_notes = models.CharField(max_length=150,null=True,blank=True)
	created_by = models.ForeignKey('auth.User',
		related_name='userexpenses',
		null=True,
		blank=True
	)
	company = models.ForeignKey(
		Company,
		related_name = 'company_expense',
		default=''
	)
	roadshow_user = models.ForeignKey('auth.User',
		related_name='roadshow_userexpenses',
		null=True,
		blank=True
	)

class ExpenseDocument(models.Model):
	docfile = models.FileField(
		upload_to='documents/%Y/%m/%d',
		null=True,
		blank=True
	)
	expense = models.ForeignKey(
		RoadshowExpense,
		related_name='expense_documents',
		null=True,
		blank=True
	)


class RoadshowDinner(models.Model):
	roadshow = models.ForeignKey(Roadshow, related_name='roadshowdinner')
	name = models.CharField(max_length=150)
	dinner_date = models.DateField(null=True,blank=True)
	start_time = models.CharField(max_length=15,null=False,blank=False)
	end_time = models.CharField(max_length=15,null=False,blank=False)
	users = models.ManyToManyField('auth.User')
	created_by = models.ForeignKey('auth.User', related_name='userdinner',null=True,blank=True)


class UserLogin(models.Model):
    user = models.ForeignKey(User) 
    timestamp = models.DateTimeField()


class UserPasswordToken(models.Model):
    user = models.OneToOneField(User)
    token = models.CharField(max_length=150)


class CompanyRoadshow(models.Model):
	company = models.ForeignKey(Company)
	roadshow = models.ForeignKey(Roadshow)

class MeetingSummary(models.Model):
	meetingDoc = models.FileField(upload_to='documents/%Y/%m/%d', null=True, blank=True)
	comments = models.TextField(null=True, blank = True)
	comment_date = models.CharField(max_length=125, null=True, blank=True)
	fileType = models.CharField(max_length=25, null=True, blank=True)
	meetingId = models.ForeignKey(Meeting, related_name='meeting_summary')
	created_by = models.ForeignKey('auth.User', related_name='summary_user',null=True,blank=True)

class MeetingDocument(models.Model):
	fileName = models.CharField(max_length=45, blank = True)
	meetingFile = models.FileField(
		upload_to='documents/%Y/%m/%d'
	)
	fileType = models.CharField(max_length=20)
	meetingId = models.ForeignKey(
		Meeting,
		related_name = 'meeting_documents'
	)

class CompanyDefaultMessage(models.Model):
	company = models.ForeignKey(
		Company,
		related_name='company_messages'
	)
	message_text = models.TextField(
		null=True,
		blank=True
	)

class UserProfile(models.Model):
	user = models.OneToOneField(
		User,
		related_name = 'user_profile'
	)
	contact_phone = models.CharField(
		max_length=14,
		null=True,
		blank=True
	)
	profile_pic = models.FileField(
		upload_to='documents/%Y/%m/%d',
		null=True,
		blank=True
	)
	notes = models.TextField(
		null=True,
		blank=True
	)
	designation = models.CharField(
		max_length=50,
		null=True,
		blank=True
	)


class CompanyTwitter(models.Model):
    name=models.CharField(max_length=250,null=True,blank=True)
    description=models.TextField(null=True,blank=True)
    follower_count=models.CharField(max_length=10,null=True,blank=True)
    statuses=models.CharField(max_length=150,null=True,blank=True)
    location=models.CharField(max_length=250,null=True,blank=True)
    website=models.CharField(max_length=150,null=True,blank=True)
    profile_pic=models.CharField(max_length=250,null=True,blank=True)
    profile_url=models.CharField(max_length=250,null=True,blank=True)


class MeetingCompanyTwitter(models.Model):
    meeting=models.ForeignKey(Meeting)
    company_twitter=models.ForeignKey(CompanyTwitter)


class CompanyLinkedIn(models.Model):
    name=models.CharField(max_length=250,null=True,blank=True)
    description=models.TextField(null=True,blank=True)
    specialities=models.TextField(null=True,blank=True)
    founded=models.CharField(max_length=10,null=True,blank=True)
    street=models.CharField(max_length=250,null=True,blank=True)
    city=models.CharField(max_length=50,null=True,blank=True)
    state=models.CharField(max_length=50,null=True,blank=True)
    zipcode=models.CharField(max_length=10,null=True,blank=True)
    country=models.CharField(max_length=50,null=True,blank=True)
    industry=models.CharField(max_length=150,null=True,blank=True)
    website=models.CharField(max_length=100,null=True,blank=True)
    follower_count=models.CharField(max_length=10,null=True,blank=True)
    company_type=models.CharField(max_length=150,null=True,blank=True)
    profile_url=models.CharField(max_length=250,null=True,blank=True)


class MeetingCompanyLinkedIn(models.Model):
    meeting=models.ForeignKey(Meeting)
    company_linkedin=models.ForeignKey(CompanyLinkedIn)


class UserPreference(models.Model):
	user = models.ForeignKey(User, related_name = 'user_preferences')
	farenheit_celcius = models.CharField(max_length=25, null=True,blank=True)


@receiver(post_save,sender=User)
def send_user_data_when_created_by_admin(sender, instance, created, **kwargs):
	'''
	This method will be used for update the user details when user created by root user.
	This receiver will be called after login. Since the user table gets updated.
	'''
	print "%$@%@$$@#%^&&&$#^"
	print instance.first_name
	print Company.objects.filter(users__id=instance.id)
	import inspect
	records = []
	for frame_record in inspect.stack():		
		# print frame_record
		records.append(frame_record[3])
		if frame_record[3]=='get_response':
			request = frame_record[0].f_locals['request']
			if created and ('admin' in request.get_full_path().split('/')):
				email = request.POST.get('email')
				password1 =  request.POST.get('password1')
				password2 = request.POST.get('password2')
				if email != None and password1 != None and password2 != None and password1 == password2:
					hml_content ="Hi,<br> Your username: %s <br> Password: %s"
					from_email   = settings.DEFAULT_FROM_EMAIL
					message      = EmailMessage('Welcome', html_content %(email, password1), from_email, [email])
					message.content_subtype = "html"  # Main content is now text/html
					message.send()
			break
	else:
		request = None
	# Check whether the admin creating the user or not
	if request is not None and request.user:
		if request.user.is_staff and created and ('admin' in request.get_full_path().split('/')):
			#instance.is_staff = 1
			instance.is_superuser = 1
			instance.save()
			group = Group.objects.filter(name='Manager')
			if group:
				instance.groups.add(group[0])
			# first_name = instance.first_name
			# print('first name is',first_name)
			# print kwargs
			# last_name = instance.last_name
			# email = instance.email
			# html_content = "your first name:%s <br> last name:%s <br>"
			# message=EmailMessage(subject='welcome',body=html_content %(first_name,last_name),to=[email])
			# message.content_subtype='html'
			# message.send()

#Check the user alrady registered or not
# @receiver(pre_save, sender=User)
# def user_pre_save(sender, **kwargs):
# 	print kwargs
# 	email = kwargs['instance'].email
# 	username = kwargs['instance'].username

# 	if not email:
# 		raise ValidationError("Email required")
# 	if sender.objects.filter(email=email).exclude(username=username).count():
# 		raise ValidationError("This email already exists")
