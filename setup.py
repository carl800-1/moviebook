from setuptools import setup

APP = ['gui.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['src', 'src.bilibili', 'src.extractor', 'src.nas', 'src.utils'],
    'includes': ['PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui',
                 'asyncio', 'aiohttp', 'json', 'threading', 'yaml', 'dotenv',
                 'bilibili_api', 'bilibili_api.login_v2', 'bilibili_api.user',
                 'src.bilibili.client', 'src.extractor.movie_extractor',
                 'src.nas.nastool_client', 'src.utils.config', 'src.utils.logger'],
    'excludes': ['tkinter', 'matplotlib', 'numpy', 'scipy', 'PIL'],
    'plist': {
        'CFBundleName': 'MovieBook',
        'CFBundleDisplayName': 'MovieBook',
        'CFBundleIdentifier': 'com.moviebook.app',
        'CFBundleVersion': '1.0.2',
        'CFBundleShortVersionString': '1.0.2',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
        'NSAppleEventsUsageDescription': 'MovieBook needs to control browser for Bilibili login.',
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
