import argparse

# Small patch: Ensure Kivy environment is setup before importing Kivy modules
# this patch is required to allow Kivy to run with command line arguments
# more robust will be from command line run [$env:KIVY_NO_ARGS='1';python main.py <args>]
import services.kivy_setup

from kivy.app import App
from kivy.uix.image import Image

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen, ScreenManager
from kivymd.app import MDApp

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
                   action="store_false",
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
                   default=640,
                   help='Camera width resolution')
    
    p.add_argument('--camera_height', 
                   type=int,
                   default=360,
                   help='Camera height resolution')
    
    p.add_argument('--camera_fps',
                   type=int,
                   default=30,
                   help='Camera frames per second')
    
    return p.parse_args()

class MyApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # set window size
        Window.size = (350, 600)
        
        self.controller = None
        self.screen_manager = ScreenManager()
        self.preview = Image(fit_mode="contain")

    def build(self):
        self.title = "MimicMotion"
        Builder.load_file("screens/bottombar.kv")

        # Splash screen
        splash_screen = Builder.load_file("screens/splashscreen.kv")
        self.screen_manager.add_widget(splash_screen)

        # Landing page
        landing_screen = Builder.load_file("screens/landingscreen.kv")
        self.screen_manager.add_widget(landing_screen)

        # Camera screen
        camera_screen = Builder.load_file("screens/camerascreen.kv")
        camera_screen.ids.preview_container.add_widget(self.preview)
        self.screen_manager.add_widget(camera_screen)

        # Progress screen
        progress_screen = Builder.load_file("screens/progressscreen.kv")
        self.screen_manager.add_widget(progress_screen)


        self.screen_manager.current = "SplashScreen"
        return self.screen_manager

    def on_start(self):
        # Parse command line arguments; initialize main controller and pass arguments
        args = parse_args()
        self.controller = MainController(args, preview_widget=self.preview)
        self.screen_manager.current = "SplashScreen"
        

        # delay the time for the splash screen
        Clock.schedule_once(self.go_to_landing, 3)

    def go_to_landing(self, *_dt):
        self.screen_manager.current = "LandingScreen"

    def go_to_camera(self):
        self.screen_manager.current = "CameraScreen"

    def go_to_progress(self):
        self.screen_manager.current = "ProgressScreen"

    def on_stop(self):
        # shutdown main controller
        if self.controller:
            self.controller()
            self.controller = None

if __name__ == "__main__":
    MyApp().run()
