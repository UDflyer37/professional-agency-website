from ._anvil_designer import ItemTemplate3Template
from anvil import *
import stripe.checkout
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class ItemTemplate3(ItemTemplate3Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    if self.item['open_time']:
      self.convert_time(self.item['open_time'], self.open_box, self.am_pm_drop_1)
      self.convert_time(self.item['close_time'], self.close_box, self.am_pm_drop_2)
    else:
      #if the day is closed, don't show any hours
      self.flow_panel_1.visible = False

      

      
  def convert_time(self, time, textbox, dropdown):
    #method to convert 24 hour time to 12 hour time
    if time > 12:
      textbox.text = time - 12
      dropdown.selected_value = 'p.m.'
    else: 
      textbox.text = time
      dropdown.selected_value = 'a.m.'

  def save_link_click(self, **event_args):
    """This method is called when the link is clicked""" 
    if self.check_box_1.checked: #if the day is open...
      if self.open_box.text and self.close_box.text: #and hours have been added...
        open_time = self.open_box.text + 12 if self.am_pm_drop_1.selected_value == 'p.m.' else self.open_box.text #turn to 24 hour time
        close_time = self.close_box.text + 12 if self.am_pm_drop_2.selected_value == 'p.m.' else self.close_box.text  
        anvil.server.call('update_hours', self.item, open_time, close_time, True) #update settings table
      else: # else if the opening and/or closing time is missing...
        Notification("Please add opening and closing hours").show()
        return
    else: # else if check_box_1 is not checked...
      anvil.server.call('update_hours', self.item, None, None, False)
    #make the save and cancel links invisible
    self.flow_panel_2.visible = False


  def cancel_link_click(self, **event_args): 
    """This method is called when the link is clicked"""
    self.__init__()
    #keep hours textboxes and dropdowns visible if the day is open
    self.flow_panel_1.visible = self.check_box_1.checked
    self.flow_panel_2.visible = False


  def open_box_change(self, **event_args):
    """This method is called when the text in this text box is edited"""
    self.flow_panel_2.visible = True

  def am_pm_drop_1_change(self, **event_args):
    """This method is called when an item is selected"""
    self.flow_panel_2.visible = True

  def close_box_change(self, **event_args):
    """This method is called when the text in this text box is edited"""
    self.flow_panel_2.visible = True

  def am_pm_drop_2_change(self, **event_args):
    """This method is called when an item is selected"""
    self.flow_panel_2.visible = True

  def check_box_1_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    self.flow_panel_1.visible = self.check_box_1.checked

