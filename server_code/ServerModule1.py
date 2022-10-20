import anvil.users
import anvil.email
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import calendar
import datetime
import anvil.tz
import pytz

#CONTACT
@anvil.server.callable
def add_contact_info(name, email, topic, question):
  app_tables.contact.add_row(
    name=name, 
    email=email, 
    topic=topic,
    question=question, 
    time=datetime.now()
  )
  anvil.email.send(from_name="Otto & Associates: Question/Comment",
                   to="andi.otto@yahoo.com",
                   subject=f"Question from {name}: {topic}",
                   text=f"You've received a new web contact from {name}! \nTopic: {topic} \nEmail address: {email} \nQuestion: {question}")


  
#APPOINTMENTS
@anvil.server.callable
def get_times(chosen_date, now): 
  #get the hours for the chosen day of the week
  day_row = app_tables.open_hours.get(day=chosen_date.strftime("%A"))
  #pull location from settings table and turn into a timezone- set in AdminSettings
  tz = pytz.timezone(app_tables.settings.get(key='tz')['value']) 
  #turn chosen_date to a datetime object in the local time
  chosen_datetime = tz.localize(datetime.datetime.combine(chosen_date, datetime.time()))
  booked_times = [row['datetime'] for row in app_tables.bookings.search()]
  #num_bookings_allowed is the number of people who can book a single timeslot - set in AdminSettings
  num_bookings_allowed = app_tables.settings.get(key="num_bookings")['value']
  open_times = []
  
  if day_row['open']:
    time_open = (day_row['close_time'] - day_row['open_time'])*60 #turn to minutes
    interval = app_tables.settings.get(key="interval")['value'] #the booking interval (in minutes) - set in AdminSettings
    #step through the total time the venue will be open (in minutes) at the specified interval
    for i in range(0, int(time_open), int(interval)):
      #start at the opening time (set in AdminSettings) and add the interval
      timeslot = (chosen_datetime + datetime.timedelta(hours=day_row['open_time'])) + datetime.timedelta(minutes=i)
      #and check if timeslot is in the past and if there are still bookings available for that timeslot
      if timeslot > datetime.datetime.now().astimezone(tz=tz) and booked_times.count(timeslot) < num_bookings_allowed: 
        open_times.append(timeslot)
          
  return open_times 

@anvil.server.callable
def add_booking(name, date, email=None):
  app_tables.bookings.add_row(name=name.capitalize().strip(), datetime=date, user=email.lower().strip())
  anvil.email.send(from_name="Otto & Associates", 
                   to= email, 
                   subject="Your booking was successful",
                   text=f"Hi {name},\n\nYou have sucessfully made a booking for {date.strftime('%A %d %b %Y at %I:%M %p')}.")
  anvil.email.send(from_name="Otto & Associates: New Appointment",
                   to="andi.otto@yahoo.com",
                   subject=f"New Appointment for {name}: {date.strftime('%A %d %b %Y at %I:%M %p')}",
                   text=f"{name} has made an appointment for {date.strftime('%A %d %b %Y at %I:%M %p')}. They can be reached at {email}.")


@anvil.server.callable
def get_bookings(order_by="datetime"): 
  now = datetime.datetime.now()
  current_bookings = app_tables.bookings.search(tables.order_by(order_by), datetime=q.greater_than_or_equal_to(now))
  past_bookings = app_tables.bookings.search(tables.order_by(order_by, ascending=False), datetime=q.less_than(now))
  return current_bookings, past_bookings

@anvil.server.callable
def delete_booking(row):
  date = row['datetime'].strftime("%A %d %b %Y at %I:%M %p")
  anvil.email.send(from_name="Otto & Associates",
                to=row['user'],
                subject="Your Booking Has Been Cancelled",
                text=f"Your booking for {date} has been cancelled. Please contact us if this is an error.")
  row.delete()

@anvil.server.callable
def delete_past_appointments(row):
  if 
  row.delete()

@anvil.server.callable
def booking_user(row):
  return row['user']
  

@anvil.server.callable
def send_email(email, body, subject):
  if not subject:
    subject = "A Message about your Booking"
  anvil.email.send(from_name="Otto & Associates", 
                   to=email, 
                   subject=subject,
                   text=body)

#@anvil.server.callable
#def check_admin():
#  return anvil.users.get_user()['admin']

@anvil.server.callable
def update_hours(row, open_time, close_time, isitopen):
  row['open_time'] = open_time
  row['close_time'] = close_time
  row['open'] = isitopen
  
@anvil.server.callable
def update_settings_table(key, value):
  app_tables.settings.get(key=key)['value'] = value
  
#@anvil.server.callable
#def check_user_exists(email):
#  return bool(app_tables.users.get(email=email))

@anvil.server.callable
def get_timezones():
  return pytz.common_timezones

@anvil.server.callable 
def reset_timezone(tz):
  app_tables.settings.get(key="tz")['value'] = tz
