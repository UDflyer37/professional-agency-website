from ._anvil_designer import contact_usTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import stripe.checkout
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class contact_us(contact_usTemplate):
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

  def map_1_show(self, **event_args):
    """This method is called when the GoogleMap is shown on the screen"""
        # Set up google map
    map = self.map_1
    
    map.center = GoogleMap.LatLng(39.8405849898327, -84.1375283738747)
    map.zoom = 15
    
    marker = GoogleMap.Marker(
      animation=GoogleMap.Animation.DROP,
      position=GoogleMap.LatLng(39.8405849898327, -84.1375283738747)
    )
    map.add_component(marker)


    

