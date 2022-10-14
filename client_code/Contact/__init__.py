from ._anvil_designer import ContactTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Contact(ContactTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    #TODO: put items in designer
    self.topic_drop.items = ['pricing', 'tutors', 'classes', 'feedback', 'other']

  def submit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    name = self.name_box.text
    email = self.email_box.text
    topic = self.topic_drop.selected_value
    question = self.question_area.text
    if name and email and topic and question:
      anvil.server.call('add_contact_info', name, email, topic, question)
      alert("Thanks for getting in touch!")
      self.name_box.text = ""
      self.email_box.text = ""
      self.topic_drop.selected_value = None
      self.question_area.text = ""
    else:
      alert("Please fill out the entire form before submitting.")







