import argparse

# Small patch: Ensure Kivy environment is setup before importing Kivy modules
# this patch is required to allow Kivy to run with command line arguments
# more robust will be from command line run [$env:KIVY_NO_ARGS='1';python main.py <args>]
import src.kivy_setup

from kivy.app import App
from kivy.uix.image import Image

from controllers.main_controller import MainController

def parse_args():
    p = argparse.ArgumentParser()
    
    # Note: defaults here are the source of truth for default values

    # define mode for facial matching
    p.add_argument('--mode', 
                   choices=["mirror"], 
                   default = "mirror",
                   help='Methodology use to display facial matching')
    
    # flip camera for use with front face vs. world facing camera
    p.add_argument('--hflip', 
                   default=True,
                   action='store_true',
                   help='Horizontally flip camera for selfie view')

    # runtime settings
    p.add_argument('--droopy',
                    choices=['left','right'],
                    default='left',
                    help="Anatomatomically, which side of the face is droopy")

    # run in debug mode?
    p.add_argument('--debug', 
                   default=False,
                   action='store_true',
                   help='Show debug information')
    
    # camera settings
    p.add_argument('--camera_index', 
                   type=int,
                   default=0,
                   help='Camera index to use')  
      
    p.add_argument('--camera_width', 
                   type=int,
                   default=1280,
                   help='Camera width resolution')
    
    p.add_argument('--camera_height', 
                   type=int,
                   default=720,
                   help='Camera height resolution')
    
    p.add_argument('--camera_fps',
                   type=int,
                   default=30,
                   help='Camera frames per second')
    
    return p.parse_args()


class MyApp(App):
    def build(self):
        self.preview = Image(fit_mode="contain")
        return self.preview
    
    def on_start(self):
        # Parse command line arguemnts; initialize main controller and pass arguments
        args = parse_args()
        self.controller = MainController(args,preview_widget=self.preview)    
    
    def on_stop(self):
        # shutdown main controller
        if self.controller:
            self.controller()
            self.controller = None 

if __name__ == "__main__":
    MyApp().run()
