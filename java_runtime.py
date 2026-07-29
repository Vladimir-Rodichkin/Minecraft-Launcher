import minecraft_launcher_lib as mll

import state


class InstallCancelled(Exception):
    pass


def cancellable(fn):
    def wrapper(text):
        if state.cancel_requested:
            raise InstallCancelled()
        fn(text)
    return wrapper


def ensure_java_runtime(version, on_progress=None):
    try:
        info = mll.runtime.get_version_runtime_information(version, state.MINECRAFT_DIR)
    except Exception:
        return None
    if not info:
        return None
    component = info["name"]
    path = mll.runtime.get_executable_path(component, state.MINECRAFT_DIR)
    if path:
        return path
    try:
        mll.runtime.install_jvm_runtime(component, state.MINECRAFT_DIR, callback={"setStatus": on_progress} if on_progress else None)
    except InstallCancelled:
        raise
    except Exception:
        return None
    return mll.runtime.get_executable_path(component, state.MINECRAFT_DIR)
