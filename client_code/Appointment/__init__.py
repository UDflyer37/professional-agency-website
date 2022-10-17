from ._anvil_designer import AppointmentTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import datetime
import anvil.tz
from ..BookAlert import BookAlert

class Appointment(AppointmentTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    self.min_date = datetime.date.today()
    max_date_row = app_tables.settings.get(key="max_date") 
    #self.max_date is the farthest date you can make a booking - set in AdminSettings and stored in settings table
    self.max_date = self.min_date + datetime.timedelta(days=max_date_row['value'])
    self.date_picker_1.min_date = self.min_date
    self.date_picker_1.max_date = self.max_date 
    
    #when one of the radio buttons is clicked, set self.selected_time to the chosen datetime object
    self.repeating_panel_1.set_event_handler("x-select-time", self.select_time)
    self.selected_time = None

  def select_time(self, time, **event_args):
    self.selected_time = time
  
  def date_picker_1_change(self, **event_args):
    """This method is called when the selected date changes"""
    self.card_1.visible = True
    self.chosen_datetime = self.date_picker_1.date
    self.list_times()
    
  def list_times(self):
    #if times needs to be reloaded, then we should clear that last selected time
    self.selected_time = None
    #only show right and left arrow buttons if they don't go past the max_date and min_date
    self.right_button.visible = (self.chosen_datetime + datetime.timedelta(days=1)) <= self.max_date
    self.left_button.visible = (self.chosen_datetime + datetime.timedelta(days=-1)) >= self.min_date      

    self.day_label.text = self.chosen_datetime.strftime("%A")
    self.date_label.text = self.chosen_datetime.strftime("%d %B")
    
    open_times = anvil.server.call('get_times', self.chosen_datetime, datetime.datetime.now())
    #open_times is a list of available time slots
    self.repeating_panel_1.items = open_times
    #display that there are no available bookings if open_times is empty
    self.no_bookings_label.visible = not open_times


  def right_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.chosen_datetime = self.chosen_datetime + datetime.timedelta(days=1)
    self.list_times()

  def left_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.chosen_datetime = self.chosen_datetime + datetime.timedelta(days=-1)
    self.list_times()
    

  def book_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if not self.selected_time: 
      Notification("Please select a time").show()
      return
    person = {} #init dict to use as item for BookAlert - data bindings will write back
    while True:
      if alert(BookAlert(self.selected_time, item=person), large=True, buttons=[("Book", True), ("Cancel", False)]):
        if not person.get("name"):
          person['error'] = "Please enter a name."
        elif not person.get("email"):
          person['error'] = "Please enter an email."
        else:
          anvil.server.call('add_booking', person['name'], self.selected_time, person['email'])
          alert(f"Your booking was successful! \n\nA confirmation email has been sent to {person['email'].lower().strip()}!")
          break
      else: #else if user clicks cancel
        break
        
    self.list_times()

