import argparse

# Small patch: Ensure Kivy environment is setup before importing Kivy modules
# this patch is required to allow Kivy to run with command line arguments
# more robust will be from command line run [$env:KIVY_NO_ARGS='1';python main.py <args>]
import services.kivy_setup


from kivy.core.window import Window
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen, ScreenManager
from kivymd.app import MDApp

from controllers.main_controller import MainController

# set window size
Window.size = (350, 600)

def parse_args():
    parser = argparse.ArgumentParser()

    # Note: defaults here are the source of truth for default values

    # define mode for facial matching
    parser.add_argument(
        "--mode",
        choices=["mirror"],
        default="mirror",
        help="Methodology use to display facial matching",
    )

    # flip camera for use with front face vs. world facing camera
    parser.add_argument(
        "--hflip",
        default=False,
        action="store_true",
        help="Horizontally flip camera for selfie view",
    )

    # runtime settings
    parser.add_argument(
        "--droopy",
        choices=["left", "right"],
        default="left",
        help="Which side of the face is droopy",
    )

    # run in debug mode?
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Show debug information",
    )

    # camera settings
    parser.add_argument(
        "--camera_index",
        type=int,
        default=0,
        help="Camera index to use",
    )

    parser.add_argument(
        "--camera_width",
        type=int,
        default=640,
        help="Camera width resolution",
    )

    parser.add_argument(
        "--camera_height",
        type=int,
        default=420,
        help="Camera height resolution",
    )

    parser.add_argument(
        "--camera_fps",
        type=int,
        default=30,
        help="Camera frames per second",
    )

    return parser.parse_args()


class MyApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.screen_manager = ScreenManager()
        self.preview = Image(allow_stretch=True, keep_ratio=True)

    def build(self):
        self.title = "MimicMotion"

        # Splash screen
        splash_screen = Builder.load_file("screens/splashscreen.kv")
        self.screen_manager.add_widget(splash_screen)

        # Camera screen
        main_screen = Screen(name="MainScreen")
        main_screen.add_widget(self.preview)
        self.screen_manager.add_widget(main_screen)

        self.screen_manager.current = "SplashScreen"
        return self.screen_manager

    def on_start(self):
        # Parse command line arguments; initialize main controller and pass arguments
        args = parse_args()
        self.controller = MainController(args, preview_widget=self.preview)
        self.screen_manager.current = "SplashScreen"

        # delay the time for the splash screen
        Clock.schedule_once(self.change_screen, 3)

    def change_screen(self, _dt):
        self.screen_manager.current = "MainScreen"

    def on_stop(self):
        # shutdown main controller
        if self.controller:
            self.controller()
            self.controller = None


if __name__ == "__main__":
    MyApp().run()
