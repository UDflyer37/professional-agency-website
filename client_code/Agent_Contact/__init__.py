from ._anvil_designer import Agent_ContactTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Agent_Contact(Agent_ContactTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.user_email.text = anvil.server.call('booking_user', self.item)

  def submit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    email = self.user_email.text
    body = self.message_area.text
    subject = "A Message From Otto & Associates"
    attachments = self.file_loader_1.files
    if body:
      anvil.server.call('send_email', email, body, subject, attachments)
      alert("Your message has been submitted!")
      self.message_area.text = ""
    else:
      alert("Please enter a message before submitting.")

 
