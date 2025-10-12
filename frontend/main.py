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
from kivy.graphics import Color, Line

from pathlib import Path

from controllers.main_controller import MainController
from services import db
from services.session_manager import SessionManager, SessionState

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
        self.progress_preview = Image(fit_mode="contain")
        self.progress_preview.size_hint = (1, 1)
        self.progress_preview.allow_stretch = True
        self.progress_preview.keep_ratio = True
        self.progress_preview.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.progress_session_manager: SessionManager | None = None
        self.progress_state: SessionState | None = None
        self.progress_outline_widget = None
        self.progress_outline_line = None
        self.progress_outline_color = None
        self.latest_camera_texture = None
        self.pose_definitions = [
            {"index": 1, "name": "Neutral", "sample": "assets/pose1.png"},
            {"index": 2, "name": "Eyes Closed", "sample": "assets/pose2.png"},
            {"index": 3, "name": "Eyes Shut", "sample": "assets/pose3.png"},
            {"index": 4, "name": "Surprise", "sample": "assets/pose4.png"},
            {"index": 5, "name": "Kiss", "sample": "assets/pose5.png"},
            {"index": 6, "name": "Balloon", "sample": "assets/pose6.png"},
            {"index": 7, "name": "Smile", "sample": "assets/pose7.png"},
            {"index": 8, "name": "Wide Smile", "sample": "assets/pose8.png"},
            {"index": 9, "name": "Grin", "sample": "assets/pose9.png"},
        ]

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
        progress_screen = Builder.load_file("screens/snapscreen.kv")
        progress_screen.ids.progress_preview_container.add_widget(self.progress_preview)
        self._setup_progress_outline(progress_screen.ids.progress_outline_overlay)
        self.screen_manager.add_widget(progress_screen)

        # Progress overview screen
        progress_overview_screen = Builder.load_file("screens/progressoverviewscreen.kv")
        self.screen_manager.add_widget(progress_overview_screen)

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
        self.controller = MainController(
            args,
            preview_widget=self.preview,
            on_frame=self._on_camera_frame,
        )
        self.screen_manager.current = "SplashScreen"
        

        # delay the time for the splash screen
        Clock.schedule_once(self.go_to_landing, 3)

    def go_to_landing(self, *_dt):
        self.screen_manager.current = "LandingScreen"

    def go_to_camera(self):
        self.screen_manager.current = "CameraScreen"

    def go_to_snap(self):
        self.ensure_progress_session()
        self._update_progress_outline()
        self.screen_manager.current = "ProgressScreen"

    def go_to_progress(self):
        self.screen_manager.current = "ProgressOverviewScreen"

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
        ids = profile_screen.ids

        # Reset defaults before repopulating.
        ids.profile_name_value.text = "Not set"
        ids.profile_email_value.text = "Not set"
        ids.profile_last_session.text = "No sessions recorded"
        for idx in range(1, 10):
            score_label = ids.get(f"profile_score_{idx}")
            if score_label:
                score_label.text = "-"

        user = db.fetch_single_user(self.db_path)

        if not user:
            return

        user_id, username, email = user
        ids.profile_name_value.text = username or "Not set"
        ids.profile_email_value.text = email or "Not set"

        session_date, scores = db.fetch_latest_symmetry_scores(self.db_path, user_id)

        if session_date:
            ids.profile_last_session.text = f"Last session: {session_date}"

        for photo_index, symmetry_score in scores:
            if 1 <= photo_index <= 9:
                label = ids.get(f"profile_score_{photo_index}")
                if label:
                    label.text = (
                        f"{symmetry_score:.2f}"
                        if symmetry_score is not None
                        else "-"
                    )

    # ---------------- Progress session helpers ---------------- #
    def ensure_progress_session(self):
        if not self.db_path:
            return

        if not self.progress_session_manager:
            user = db.fetch_single_user(self.db_path)
            if not user:
                # Ensure a default user exists so sessions can be associated.
                db.upsert_single_user(self.db_path, "User", "")
                user = db.fetch_single_user(self.db_path)

            if not user:
                return

            user_id = user[0]
            self.progress_session_manager = SessionManager(
                self.db_path,
                user_id=user_id,
                on_pose_complete=self._on_progress_pose_captured,
                on_session_complete=self._on_progress_session_complete,
            )

            self.progress_state = self.progress_session_manager.start_session()
        elif not self.progress_state:
            self.progress_state = self.progress_session_manager.start_session()

        self.update_progress_ui()
        self._update_progress_outline()

    def reset_progress_session(self):
        if not self.progress_session_manager:
            self.ensure_progress_session()
            return

        self.progress_state = self.progress_session_manager.start_session()
        self.update_progress_ui()
        self._update_progress_outline()

    def capture_progress_pose(self):
        """
        Capture handler invoked by the Progress screen.

        Uses the most recent camera frame to persist a pose photo.
        """
        if (
            not self.progress_session_manager
            or not self.progress_state
            or self.progress_state.completed
        ):
            return
        texture = self.latest_camera_texture
        if texture is None:
            return
        self.progress_session_manager.capture_pose_texture(texture)
        # progress callbacks update UI; ensure local state reference stays in sync.
        self.progress_state = self.progress_session_manager.state
        self.update_progress_ui()

    def update_progress_ui(self):
        if not self.progress_state:
            return

        progress_screen = self.screen_manager.get_screen("ProgressScreen")
        ids = progress_screen.ids

        pose_index = self.progress_state.current_pose
        pose_info = self._get_pose_definition(pose_index)
        ids.pose_title.text = (
            "Session Complete" if self.progress_state.completed else f"Pose: {pose_info['name']}"
        )
        ids.pose_instruction.text = (
            "Align your face with the outline and press capture when ready."
        )
        ids.pose_sample.source = pose_info["sample"]
        completed_count = pose_index - 1
        if self.progress_state.completed:
            completed_count = len(self.pose_definitions)
        ids.pose_progress.value = completed_count
        ids.pose_counter.text = (
            "All poses captured!"
            if self.progress_state.completed
            else f"Pose {min(pose_index, len(self.pose_definitions))} of {len(self.pose_definitions)}"
        )

        if self.progress_state.completed:
            ids.capture_button.text = "Session Complete"
            ids.capture_button.disabled = True
        else:
            ids.capture_button.text = "Capture Pose"
            ids.capture_button.disabled = False

    def _on_progress_pose_captured(
        self, state: SessionState, pose_index: int, file_path: Path
    ) -> None:
        # Update progress bar and counter after each capture.
        self.progress_state = state
        progress_screen = self.screen_manager.get_screen("ProgressScreen")
        ids = progress_screen.ids
        ids.pose_progress.value = pose_index
        ids.pose_counter.text = f"Pose {min(state.current_pose, 9)} of 9"

    def _on_progress_session_complete(self, state: SessionState) -> None:
        self.progress_state = state
        progress_screen = self.screen_manager.get_screen("ProgressScreen")
        ids = progress_screen.ids
        ids.pose_progress.value = len(self.pose_definitions)
        ids.pose_counter.text = "All poses captured!"
        ids.capture_button.text = "Session Complete"
        ids.capture_button.disabled = True

    def _get_pose_definition(self, pose_index: int) -> dict:
        if pose_index < 1:
            pose_index = 1
        if pose_index > len(self.pose_definitions):
            pose_index = len(self.pose_definitions)
        return self.pose_definitions[pose_index - 1]

    def _setup_progress_outline(self, outline_widget):
        self.progress_outline_widget = outline_widget
        if outline_widget is None:
            return

        with outline_widget.canvas:
            self.progress_outline_color = Color(1, 1, 1, 0.6)
            self.progress_outline_line = Line(rectangle=(0, 0, 0, 0), width=2.5)

        outline_widget.bind(size=lambda *_: self._update_progress_outline())

    def _update_progress_outline(self, texture=None):
        if not self.progress_outline_line or not self.progress_outline_widget:
            return

        widget = self.progress_outline_widget
        width, height = widget.width, widget.height
        if width <= 0 or height <= 0:
            return

        margin = min(width, height) * 0.05
        available_w = max(width - 2 * margin, 1)
        available_h = max(height - 2 * margin, 1)

        rect_w = available_w
        rect_h = available_h

        tex = texture or self.latest_camera_texture
        if tex and tex.height and tex.width:
            texture_ratio = tex.width / tex.height
            available_ratio = available_w / available_h if available_h else texture_ratio

            if available_ratio > texture_ratio:
                rect_h = available_h
                rect_w = rect_h * texture_ratio
            else:
                rect_w = available_w
                rect_h = rect_w / texture_ratio

        x = (width - rect_w) / 2
        y = (height - rect_h) / 2

        self.progress_outline_line.rectangle = (x, y, rect_w, rect_h)

    def _on_camera_frame(self, texture):
        self.latest_camera_texture = texture
        if self.progress_preview:
            self.progress_preview.texture = texture
            self.progress_preview.texture_size = texture.size
            self.progress_preview.canvas.ask_update()
        self._update_progress_outline(texture)


if __name__ == "__main__":
    MyApp().run()
