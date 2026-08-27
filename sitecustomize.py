"""DragonMax build-time hotfix for Fire TV dependency bootstrap.

Python imports sitecustomize during interpreter startup. This trace only watches
build_v12.py long enough to extend BOOTSTRAP_PACKAGES after that global is
created, then immediately disables itself. It has no runtime effect on Kodi.
"""
import sys

EXTRA_BOOTSTRAP = {
    "script.skin.helper.service": "https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.skin.helper.service/script.skin.helper.service-1.1.43.zip",
    "script.skin.helper.widgets": "https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.skin.helper.widgets/script.skin.helper.widgets-1.0.45.zip",
}


def _dragonmax_bootstrap_trace(frame, event, arg):
    if event == "line" and frame.f_globals.get("__name__") == "__main__":
        filename = frame.f_code.co_filename.replace("\\", "/")
        packages = frame.f_globals.get("BOOTSTRAP_PACKAGES")
        if filename.endswith("/build_v12.py") and isinstance(packages, dict):
            packages.update(EXTRA_BOOTSTRAP)
            sys.settrace(None)
            return None
    return _dragonmax_bootstrap_trace


sys.settrace(_dragonmax_bootstrap_trace)
