from ._anvil_designer import ContactTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Contact(ContactTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Set up google map
    map = self.map_1
    
    map.center = GoogleMap.LatLng(39.8405849898327, -84.1375283738747)
    map.zoom = 15
    
    marker = GoogleMap.Marker(
      animation=GoogleMap.Animation.DROP,
      position=GoogleMap.LatLng(39.8405849898327, -84.1375283738747)
    )
    map.add_component(marker)
    
    #TODO: put items in designer
    self.topic_drop.items = ['quote', 'payment', 'feedback', 'other']

  def submit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    name = self.name_box.text
    email = self.email_box.text
    topic = self.topic_drop.selected_value
    question = self.question_area.text
    if name and email and topic and question:
      anvil.server.call('add_contact_info', name, email, topic, question)
      alert("Your question/comment has been submitted!")
      self.name_box.text = ""
      self.email_box.text = ""
      self.topic_drop.selected_value = None
      self.question_area.text = ""
    else:
      alert("Please fill out the entire form before submitting.")

    













