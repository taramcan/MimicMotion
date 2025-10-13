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
from kivy.metrics import dp
from kivymd.app import MDApp
from kivy.graphics import Color, Line

from pathlib import Path

from controllers.main_controller import MainController
from services import db
from services.session_manager import SessionManager, SessionState
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

def parse_args():
    p = argparse.ArgumentParser()
    
    # Note: defaults here are the source of truth for default values

    # define mode for facial matching
    p.add_argument('--mode',
                   choices=["mirror","warp"], 
                   default = "warp",
                   help='Methodology use to display facial matching')
    
    p.add_argument('--warp-solver',
                   choices=["delaunay","tps"],
                   default="delaunay",
                   help="Methodology for frame warping, when warp is selected.")
    
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
                   default=898,
                   help='Camera width resolution')
    
    p.add_argument('--camera_height', 
                   type=int,
                   default=1792,
                   help='Camera height resolution')
    
    p.add_argument('--camera_fps',
                   type=int,
                   default=15,
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

        # Snapshot screen
        snapshot_screen = Builder.load_file("screens/snapshotscreen.kv")
        snapshot_screen.ids.progress_preview_container.add_widget(self.progress_preview)
        self._setup_progress_outline(snapshot_screen.ids.progress_outline_overlay)
        self.screen_manager.add_widget(snapshot_screen)

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
        self.populate_progress_overview()
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
        self.screen_manager.current = "SnapshotScreen"

    def go_to_progress(self):
        self.populate_progress_overview()
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

    def populate_progress_overview(self):
        if not self.db_path:
            return

        progress_screen = self.screen_manager.get_screen("ProgressOverviewScreen")
        container = progress_screen.ids.get("progress_session_container")
        if container is None:
            return

        container.clear_widgets()

        user = db.fetch_single_user(self.db_path)
        if not user:
            container.add_widget(
                MDLabel(
                    text="Add a profile to start tracking sessions.",
                    halign="center",
                    theme_text_color="Secondary",
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            return

        user_id = user[0]
        sessions = db.fetch_sessions_with_photos(self.db_path, user_id)

        if not sessions:
            container.add_widget(
                MDLabel(
                    text="No sessions captured yet.",
                    halign="center",
                    theme_text_color="Secondary",
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            return

        sessions = list(reversed(sessions))

        col_spacing = dp(12)
        cell_width = dp(140)
        image_height = dp(160)
        row_count = len(self.pose_definitions)
        column_count = len(sessions)
        total_spacing = col_spacing * max(column_count - 1, 0)
        row_width = (cell_width * column_count) + total_spacing

        session_pose_maps = []
        session_headers: list[str] = []
        for session in sessions:
            pose_lookup = {
                photo["pose_index"]: photo for photo in session.get("photos", [])
            }
            session_pose_maps.append(pose_lookup)

            session_start = session.get("session_start") or ""
            header_text = session_start.split(" ")[0] if session_start else ""
            if not header_text:
                header_text = f"Session {session['session_id']}"
            session_headers.append(header_text)

        grid_container = MDBoxLayout(
            orientation="vertical",
            adaptive_height=True,
            spacing=dp(8),
            size_hint=(None, None),
        )
        grid_container.width = row_width

        header_row = MDBoxLayout(
            orientation="horizontal",
            spacing=col_spacing,
            size_hint=(None, None),
            height=dp(32),
        )
        header_row.width = row_width

        for header_text in session_headers:
            header_label = MDLabel(
                text=header_text,
                halign="center",
                theme_text_color="Primary",
                size_hint=(None, None),
                width=cell_width,
                height=dp(32),
            )
            header_label.text_size = (cell_width, None)
            header_label.bind(
                width=lambda widget, value: setattr(widget, "text_size", (value, None))
            )
            header_row.add_widget(header_label)

        grid_container.add_widget(header_row)

        for pose_index in range(1, row_count + 1):
            pose_def = self.pose_definitions[pose_index - 1]
            row_layout = MDBoxLayout(
                orientation="horizontal",
                spacing=col_spacing,
                size_hint=(None, None),
            )
            row_layout.width = row_width
            row_layout.height = image_height + dp(28)

            for pose_lookup in session_pose_maps:
                pose_info = pose_lookup.get(pose_index)

                photo_path = None
                symmetry_score = None
                if pose_info:
                    raw_path = pose_info.get("photo_path")
                    if raw_path:
                        candidate_path = Path(raw_path)
                        if candidate_path.exists():
                            photo_path = str(candidate_path)
                    symmetry_score = pose_info.get("symmetry_score")

                cell = MDBoxLayout(
                    orientation="vertical",
                    spacing=dp(2),
                    padding=[0, 0, 0, 0],
                    size_hint=(None, None),
                    width=cell_width,
                    height=image_height + dp(12),
                )

                if photo_path:
                    pose_image = Image(
                        source=photo_path,
                        allow_stretch=True,
                        keep_ratio=True,
                        size_hint=(1, None),
                        height=image_height,
                    )
                    cell.add_widget(pose_image)
                else:
                    placeholder = MDBoxLayout(
                        orientation="vertical",
                        size_hint=(1, None),
                        height=image_height,
                        padding=[dp(6), dp(6), dp(6), dp(6)],
                    )
                    placeholder_label = MDLabel(
                        text="No capture",
                        halign="center",
                        theme_text_color="Secondary",
                        size_hint=(1, 1),
                        font_style="Caption",
                    )
                    placeholder.add_widget(placeholder_label)
                    cell.add_widget(placeholder)

                score_text = (
                    f"Symmetry score: {symmetry_score:.2f}"
                    if symmetry_score is not None
                    else "Symmetry score: --"
                )

                score_label = MDLabel(
                    text=score_text,
                    halign="center",
                    theme_text_color="Secondary",
                    size_hint=(1, None),
                    font_style="Caption",
                )
                score_label.text_size = (cell_width, None)
                score_label.bind(
                    texture_size=lambda widget, value: setattr(widget, "height", max(value[1], dp(12))),
                )
                score_label.bind(
                    width=lambda widget, value: setattr(widget, "text_size", (value, None))
                )
                cell.add_widget(score_label)

                row_layout.add_widget(cell)

            grid_container.add_widget(row_layout)

        grid_container.height = grid_container.minimum_height
        container.width = max(row_width, grid_container.width)
        container.add_widget(grid_container)

    def populate_profile_screen(self):
        if not self.db_path:
            return

        profile_screen = self.screen_manager.get_screen("ProfileScreen")
        ids = profile_screen.ids

        # Reset defaults before repopulating.
        ids.profile_name_value.text = "Not set"
        ids.profile_email_value.text = "Not set"

        user = db.fetch_single_user(self.db_path)

        if not user:
            return

        user_id, username, email = user
        ids.profile_name_value.text = username or "Not set"
        ids.profile_email_value.text = email or "Not set"


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

        snapshot_screen = self.screen_manager.get_screen("SnapshotScreen")
        ids = snapshot_screen.ids

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
        snapshot_screen = self.screen_manager.get_screen("SnapshotScreen")
        ids = snapshot_screen.ids
        ids.pose_progress.value = pose_index
        ids.pose_counter.text = f"Pose {min(state.current_pose, 9)} of 9"

    def _on_progress_session_complete(self, state: SessionState) -> None:
        self.progress_state = state
        snapshot_screen = self.screen_manager.get_screen("SnapshotScreen")
        ids = snapshot_screen.ids
        ids.pose_progress.value = len(self.pose_definitions)
        ids.pose_counter.text = "All poses captured!"
        ids.capture_button.text = "Session Complete"
        ids.capture_button.disabled = True
        self.populate_progress_overview()

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
