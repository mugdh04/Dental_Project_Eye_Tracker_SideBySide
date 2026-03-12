from PyInstaller.utils.hooks import collect_data_files, collect_all

# Bundle all MediaPipe data files, binaries, and submodules
datas, binaries, hiddenimports = collect_all('mediapipe')

# Ensure Tasks API modules are included
hiddenimports += [
    'mediapipe.tasks',
    'mediapipe.tasks.python',
    'mediapipe.tasks.python.vision',
    'mediapipe.tasks.python.vision.face_landmarker',
    'mediapipe.tasks.python.core',
    'mediapipe.tasks.python.core.base_options',
    'mediapipe.tasks.cc',
    'mediapipe.python',
    'mediapipe.python._framework_bindings',
]