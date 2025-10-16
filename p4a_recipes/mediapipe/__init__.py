from os.path import join, exists, isdir
import shutil

import sh

from pythonforandroid.recipe import Recipe
from pythonforandroid.util import ensure_dir, current_directory
from pythonforandroid.logger import info, warning, shprint


class MediapipeRecipe(Recipe):
    """
    Builds MediaPipe python bindings for Android by invoking Bazel.

    This recipe intentionally keeps the heavy lifting in Bazel so the Python
    wrapper files remain identical to the upstream wheel.
    """

    version = "0.10.21"
    url = "https://github.com/google/mediapipe/archive/refs/tags/v{version}.tar.gz"
    depends = ["python3", "numpy", "opencv"]
    call_hostpython_via_targetpython = False
    install_in_site_packages = True

    _ARCH_CONFIG = {
        "arm64-v8a": "android_arm64",
        "armeabi-v7a": "android_arm",
    }

    def bazel_binary(self):
        """
        Determine Bazel executable. Respect $BAZEL if provided so developers
        can point at a managed Bazelisk or hermetic toolchain.
        """
        env_bazel = self.ctx.env.get("BAZEL")
        return env_bazel or "bazel"

    def build_arch(self, arch):
        arch_config = self._ARCH_CONFIG.get(arch.arch)
        if not arch_config:
            raise ValueError(f"Mediapipe recipe has no Bazel config for arch {arch.arch}")

        build_dir = self.get_build_dir(arch.arch)
        site_packages = self.ctx.get_site_packages_dir(arch)
        bazel_output_dir = join(build_dir, "bazel-bin", "mediapipe", "python")
        bazel_cache = join(build_dir, ".bazel_cache")
        ensure_dir(bazel_cache)
        if "BAZELISK_CACHE_DIR" not in self.ctx.env:
            bazelisk_cache = join(self.ctx.build_dir, "bazelisk-cache")
            ensure_dir(bazelisk_cache)
            self.ctx.env["BAZELISK_CACHE_DIR"] = bazelisk_cache


        with open(join(build_dir, ".bazelversion"), "w", encoding="utf-8") as bazel_version:
            bazel_version.write("6.5.0\n")


        workspace_file = join(build_dir, "WORKSPACE")
        if not exists(workspace_file):
            warning("MediaPipe sources are not extracted; the download step probably failed.")
        else:
            python_stub_dir = join(build_dir, "p4a_python_stub")
            ensure_dir(python_stub_dir)
            stub_build = join(python_stub_dir, "BUILD.bazel")
            with open(stub_build, "w", encoding="utf-8") as stub:
                stub.write(
                    """alias(name = "python_headers", actual = "@local_config_python//:python_headers")
alias(name = "includes", actual = "@local_config_python//:python_headers")
alias(name = "py3_runtime", actual = "@local_config_python//:py3_runtime")
alias(name = "python_runtimes", actual = "@local_config_python//:py_runtime_pair")
alias(name = "python3", actual = "@local_config_python//:py3_runtime")
alias(name = "libpython", actual = "@local_config_python//:py3_runtime")
alias(name = "files", actual = "@local_config_python//:py3_runtime")
alias(name = "pip", actual = "@local_config_python//:py3_runtime")
"""
                )

            stub_workspace = join(python_stub_dir, "WORKSPACE")
            with open(stub_workspace, "w", encoding="utf-8") as ws:
                ws.write("workspace(name = \"python_stub\")\n")

            with open(workspace_file, "r+", encoding="utf-8") as workspace:
                current = workspace.read()
                appended = []
                if 'android_ndk_repository(name = "androidndk"' not in current:
                    appended.append(
                        f'android_ndk_repository(name = "androidndk", api_level = {self.ctx.ndk_api}, path = "{self.ctx.ndk_dir}")\n'
                    )
                    appended.append(
                        'bind(name = "android/crosstool", actual = "@androidndk//:toolchain")\n'
                    )
                if 'android_sdk_repository(name = "androidsdk"' not in current:
                    appended.append(
                        f'android_sdk_repository(name = "androidsdk", path = "{self.ctx.sdk_dir}")\n'
                    )
                if 'local_repository(name = "python"' not in current:
                    appended.append(
                        f'local_repository(name = "python", path = "{python_stub_dir}")\n'
                    )
                if appended:
                    workspace.seek(0, 2)
                    workspace.write("\n# Added by python-for-android Mediapipe recipe\n")
                    workspace.writelines(appended)

        with current_directory(build_dir):
            bazel = sh.Command(self.bazel_binary())
            python_bin = self.ctx.hostpython
            python_include = self.ctx.python_recipe.include_root(arch.arch)
            python_site = self.ctx.get_site_packages_dir(arch)
            python_lib = self.ctx.python_recipe.link_root(arch.arch)
            bazel_args = [
                f"--output_user_root={bazel_cache}",
                "--batch",
                "build",
                "-c",
                "opt",
                f"--config={arch_config}",
                f"--repo_env=PYTHON_BIN_PATH={python_bin}",
                f"--repo_env=PYTHON_INCLUDE_PATH={python_include}",
                f"--repo_env=PYTHON_LIB_PATH={python_lib}",
                f"--repo_env=PYTHON_SITE_PACKAGES={python_site}",
                "--repo_env=PYTHON_VERSION=3.11",
                "--repo_env=HERMETIC_PYTHON_VERSION=3.11",
                "mediapipe/python:_framework_bindings.so",
            ]

            distdir = self.ctx.env.get("P4A_MEDIAPIPE_DISTDIR")
            if distdir:
                if not isdir(distdir):
                    raise FileNotFoundError(
                        f"P4A_MEDIAPIPE_DISTDIR={distdir} but the directory does not exist."
                    )
                bazel_args.append(f"--distdir={distdir}")

            repo_cache = self.ctx.env.get("P4A_MEDIAPIPE_REPOSITORY_CACHE")
            if repo_cache:
                ensure_dir(repo_cache)
                bazel_args.append(f"--repository_cache={repo_cache}")

            info(f"Building MediaPipe bindings with Bazel config={arch_config}")
            shprint(
                bazel,
                *bazel_args,
                _env=self.ctx.env,
            )

        bindings_src = join(bazel_output_dir, "_framework_bindings.so")
        if not exists(bindings_src):
            raise FileNotFoundError(
                f"Expected Bazel output {bindings_src} was not produced; check the build logs."
            )

        bindings_dst = join(site_packages, "mediapipe", "python")
        ensure_dir(bindings_dst)
        shutil.copy2(bindings_src, bindings_dst)

        # Copy pure-python modules so behaviour matches upstream wheel.
        python_pkg_src = join(build_dir, "mediapipe")
        python_pkg_dst = join(site_packages, "mediapipe")

        if exists(python_pkg_dst):
            shutil.rmtree(python_pkg_dst)

        shutil.copytree(python_pkg_src, python_pkg_dst)


recipe = MediapipeRecipe()
