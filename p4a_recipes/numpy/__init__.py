from pythonforandroid.recipe import Recipe, MesonRecipe
from os import pathsep
from os.path import join
import shutil

NUMPY_NDK_MESSAGE = "In order to build numpy, you must set minimum ndk api (minapi) to `24`.\n"


class NumpyRecipe(MesonRecipe):
    """Local override pinning numpy to the 1.26.x series so it matches
    the desktop dependency set."""

    version = '1.26.4'
    # Use the PyPI sdist so vendored Meson is included (GitHub tarballs omit submodules).
    url = 'https://files.pythonhosted.org/packages/source/n/numpy/numpy-{version}.tar.gz'
    # Align host build tooling with numpy's pyproject requirements; avoid installing
    # host numpy so meson-python doesn't pick up system site-packages during wheel build.
    hostpython_prerequisites = [
        "meson>=1.2.3",
        "meson-python>=0.15,<0.16",
        "Cython>=0.29.34,<3.1",
    ]
    extra_build_args = ['-Csetup-args=-Dblas=none', '-Csetup-args=-Dlapack=none']
    need_stl_shared = True
    min_ndk_api_support = 24

    def get_recipe_meson_options(self, arch):
        options = super().get_recipe_meson_options(arch)
        options["binaries"]["python"] = self.ctx.python_recipe.python_exe
        options["binaries"]["python3"] = self.ctx.python_recipe.python_exe
        options["properties"]["longdouble_format"] = (
            "IEEE_DOUBLE_LE" if arch.arch in ["armeabi-v7a", "x86"] else "IEEE_QUAD_LE"
        )
        return options

    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)
        env["_PYTHON_HOST_PLATFORM"] = arch.command_prefix
        env["NPY_DISABLE_SVML"] = "1"
        env["TARGET_PYTHON_EXE"] = join(
            Recipe.get_recipe("python3", self.ctx).get_build_dir(arch.arch),
            "android-build",
            "python",
        )
        build_root = self.get_build_dir(arch.arch)
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            build_root
            if not existing_pythonpath
            else f"{build_root}{pathsep}{existing_pythonpath}"
        )
        return env

    def build_arch(self, arch):
        super().build_arch(arch)
        self.restore_hostpython_prerequisites(["cython"])

    def get_hostrecipe_env(self, arch=None):
        env = super().get_hostrecipe_env(arch=arch)
        env['RANLIB'] = shutil.which('ranlib')
        return env


recipe = NumpyRecipe()
