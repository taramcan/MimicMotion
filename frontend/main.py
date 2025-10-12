import argparse

# Small patch: Ensure Kivy environment is setup before importing Kivy modules
# this patch is required to allow Kivy to run with command line arguments
# more robust will be from command line run [$env:KIVY_NO_ARGS='1';python main.py <args>]
import services.kivy_setup

from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp

from pathlib import Path

from controllers.main_controller import MainController
from services import db

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

class MyApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # set window size
        Window.size = (350, 600)
        
        self.controller = None
        self.screen_manager = ScreenManager()
        self.preview = Image(fit_mode="contain")
        self.preview.size_hint = (1, 1)
        self.preview.allow_stretch = True
        self.preview.keep_ratio = True
        self.preview.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.bottom_nav = None
        self.db_path: Path | None = None

    def build(self):
        self.title = "MimicMotion"
        # TODO: restore use of App.get_running_app().user_data_dir before shipping.
        # user_data_dir = App.get_running_app().user_data_dir
        # db_path = os.path.join(user_data_dir, "mydb.db")
        self.db_path = Path(__file__).resolve().parent / "mydb.db"
        db.init_db(self.db_path)

        Builder.load_file("screens/bottombar.kv")
        root = FloatLayout()

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

        # Profile screen
        profile_screen = Builder.load_file("screens/profilescreen.kv")
        self.screen_manager.add_widget(profile_screen)

        #Edit profile screen
        edit_profile_screen = Builder.load_file("screens/editprofilescreen.kv")
        self.screen_manager.add_widget(edit_profile_screen)

        root.add_widget(self.screen_manager)
        bottom_nav = Factory.BottomNavBar()
        bottom_nav.size_hint = (1, None)
        bottom_nav.pos_hint = {"x": 0, "y": 0}
        root.add_widget(bottom_nav)
        self.bottom_nav = bottom_nav  # keep reference if needed

        self.screen_manager.current = "SplashScreen"
        self.populate_profile_screen()
        return root

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

    def go_to_profile(self):
        self.populate_profile_screen()
        self.screen_manager.current = "ProfileScreen"

    def go_to_edit_profile(self):
        edit_screen = self.screen_manager.get_screen("EditProfileScreen")
        user = db.fetch_single_user(self.db_path) if self.db_path else None
        name, email = "", ""
        if user:
            _, stored_name, stored_email = user
            name = stored_name or ""
            email = stored_email or ""
        edit_screen.ids.name_input.text = name
        edit_screen.ids.email_input.text = email
        self.screen_manager.current = "EditProfileScreen"

    def on_stop(self):
        # shutdown main controller
        if self.controller:
            self.controller()
            self.controller = None

    def edit_profile(self):
        if not self.db_path:
            return

        edit_screen = self.screen_manager.get_screen("EditProfileScreen")
        username = edit_screen.ids.name_input.text.strip()
        email = edit_screen.ids.email_input.text.strip()

        if not username:
            username = "User"

        db.upsert_single_user(self.db_path, username, email)
        self.populate_profile_screen()
        self.screen_manager.current = "ProfileScreen"

    def populate_profile_screen(self):
        if not self.db_path:
            return

        profile_screen = self.screen_manager.get_screen("ProfileScreen")
        user = db.fetch_single_user(self.db_path)

        if user:
            _, username, email = user
            profile_screen.ids.profile_name_value.text = username or "Not set"
            profile_screen.ids.profile_email_value.text = email or "Not set"
        else:
            profile_screen.ids.profile_name_value.text = "Not set"
            profile_screen.ids.profile_email_value.text = "Not set"


if __name__ == "__main__":
    MyApp().run()
