"""DragonMax build-time dependency flight pack for Fire TV.

Python imports sitecustomize during interpreter startup. This trace watches
build_v12.py only long enough to extend BOOTSTRAP_PACKAGES after that global is
created, then disables itself. The resulting release payload carries the
non-official AuraMOD dependency chain instead of trusting device-time repo
resolution. This module has no runtime effect on Kodi.
"""
import sys

EXTRA_BOOTSTRAP = {
    # AuraMOD direct non-official requirements.
    "script.skin.helper.service": "https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.skin.helper.service/script.skin.helper.service-1.1.43.zip",
    "script.skin.helper.widgets": "https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.skin.helper.widgets/script.skin.helper.widgets-1.0.45.zip",
    "plugin.video.themoviedb.helper": "https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/plugin.video.themoviedb.helper/plugin.video.themoviedb.helper-6.16.5.zip",

    # Non-official transitive requirements used by the helpers above.
    "script.module.metadatautils": "https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.metadatautils/script.module.metadatautils-1.0.50.zip",
    "script.module.thetvdb": "https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.thetvdb/script.module.thetvdb-1.0.34.zip",
    "script.module.musicbrainz": "https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.musicbrainz/script.module.musicbrainz-0.7.0.zip",
    "script.module.jurialmunkey": "https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/script.module.jurialmunkey/script.module.jurialmunkey-0.2.35.zip",
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
