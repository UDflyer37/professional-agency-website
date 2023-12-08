from ._anvil_designer import email_usTemplate
from anvil import *
import stripe.checkout
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class email_us(email_usTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

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









