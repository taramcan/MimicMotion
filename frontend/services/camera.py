# Author: RD7
# Purpose: Camera handling
# Created: 2025-10-03

from services.config import Config
from kivy.core.camera import Camera as CoreCamera

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from kivy.graphics.texture import Texture

class Camera:
    def __init__(self,cfg:Config):
        # setup camera parameters from config
        self._camera = CoreCamera(index=cfg.camera.index,
                              resolution=(cfg.camera.width, cfg.camera.height),
                              stopped=True)

        self._hflip = bool(cfg.camera.hflip)

        self._latest_texture: "Texture | None" = None
        self._camera.bind(on_texture=self._on_texture)

    def _on_texture(self, instance):
        texture = instance.texture
        if not texture:
            return
        # if self._hflip:
        #     texture = texture.get_region(0, 0, texture.width, texture.height)
        #     texture.flip_horizontal()
        self._latest_texture = texture

    def start(self):
        self._camera.start()

    def read(self):
        return self._latest_texture

    def release(self):
        if self._camera:
            self._camera.unbind(on_texture=self._on_texture)
            self._camera.stop()
            self._camera = None

