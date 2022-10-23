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
    self.topic_drop.items = ['Quote', 'Payment', 'Feedback', 'Other']

  def submit_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    name = self.name_box.text
    user = self.email_box.text
    topic = self.topic_drop.selected_value
    question = self.question_area.text
    if name and user and topic and question:
      anvil.server.call('add_contact_info', name, user, topic, question)
      alert("Your question/comment has been submitted!")
      self.name_box.text = ""
      self.email_box.text = ""
      self.topic_drop.selected_value = None
      self.question_area.text = ""
    else:
      alert("Please fill out the entire form before submitting.")

  def proof_of_insurance_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.topic_drop.items = ['Request a Proof of Insurance Card']
    self.topic_drop.selected_value = "Request a Proof of Insurance Card"
    self.question_area.text = "I would like to Request my Proof of Insurance Card."
    self.email_template_card.visible = True

  def declaration_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.topic_drop.items = ['Request a Declaration']
    self.topic_drop.selected_value = "Request a Declaration"
    self.question_area.text = "I would like to Request a Declaration."
    self.email_template_card.visible = True

  def certificate_of_insurance_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.topic_drop.items = ['Request a Certificate of Insurance']
    self.topic_drop.selected_value = "Request a Certificate of Insurance"
    self.question_area.text = "I would like to Request a Certificate of Insurance."
    self.email_template_card.visible = True

  def insurance_verification_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.topic_drop.items = ['Request Verification of Insurance']
    self.topic_drop.selected_value = "Request Verification of Insurance"
    self.question_area.text = "I would like to Request Verification of Insurance."
    self.email_template_card.visible = True

  def other_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.topic_drop.items = ['Quote', 'Payment', 'Feedback', 'Other']
    self.topic_drop.focus()
    self.question_area.text = ""
    self.email_template_card.visible = True

  def contact_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.contact_card.visible:
        self.contact_card.visible = False
    else:
        self.contact_card.visible = True

  def email_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    if self.email_card.visible:
        self.email_card.visible = False
        self.email_template_card.visible = False
    else:
        self.email_card.visible = True









    













