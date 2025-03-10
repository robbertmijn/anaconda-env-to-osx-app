# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re
import shutil
import json

# ===============================================================================
# General settings applicable to all apps
# ===============================================================================

# Name of the app
APP_NAME = "OpenSesame"
# The short version string
# In this script, this value is overwritten later, because the value of OpenSesame
# is automatically retrieved from its source code.
VERSION = "3.3.10"
# The website in reversered order (domain first, etc.)
IDENTIFIER = "nl.cogsci.osdoc"
# The author of this package
AUTHOR = "Sebastiaan Mathôt"
# Full path to the anaconda environment folder to package
# Make sure it is the full path (and not a relative one, also to the homedir with ~) so this can be
# correctly replaced later. Conda usßes hardcoded paths, which we convert to `/Applications/<APP_NAME>`
CONDA_ENV_PATH = "/Users/robbertmijn/opt/anaconda3/envs/opensesame"
# Folders to include from Anaconda environment, if ommitted everything will be
# copied
# CONDA_FOLDERS = ["lib", "bin", "share", "qsci", "ssl", "translations"]
# Paths of files and folders to remove from the copied anaconda environment,
# relative to the environment's root.
# For instance, this could be the qt4 apps (an app inside an app is useless)
CONDA_EXCLUDE_FILES = [
    'bin/*.app',
    'bin/*.prl',
    'bin/qmake',
    'bin/2to3*',
    'bin/autopoint',
    'conda-meta',
    'include',
    'lib/*.prl',
    'lib/pkg-config',
    'org.freedesktop.dbus-session.plist'
]

CONDA_EXCLUDE_FILES += map(lambda x: f'translations/{x}', [
    'assistant*', 'designer*', 'linguist*', 'qt_*', 'qtbase*', 'qtconnectivity*', 'qtdeclarative*',
    'qtlocation*', 'qtmultimedia*', 'qtquickcontrols*', 'qtscript*', 'qtserialport*',
    'qtwebsockets*', 'qtxmlpatterns*'
])

# Path to the icon of the app
ICON_PATH = "/Users/robbertmijn/Documents/projecten_local/opensesame-macos-build-scripts/opensesame_resources/opensesame.icns"
# The entry script of the application in the environment's bin folder
ENTRY_SCRIPT = "opensesame"
# Folder to place created APP and DMG in.
OUTPUT_FOLDER = "/Users/robbertmijn/Documents/projecten_local/opensesame-macos-build-scripts/"

# Information about file types that the app can handle
APP_SUPPORTED_FILES = {
    "CFBundleDocumentTypes": [
        {
            'CFBundleTypeName': "OpenSesame experiment",
            'CFBundleTypeRole': "Editor",
            'LSHandlerRank': "Owner",
            'CFBundleTypeIconFile': os.path.basename(ICON_PATH),
            'LSItemContentTypes': ["nl.cogsci.osdoc.osexp"],
            'NSExportableTypes': ["nl.cogsci.osdoc.osexp"]
        }
    ],
    "UTExportedTypeDeclarations": [
        {
            'UTTypeConformsTo': ['org.gnu.gnu-zip-archive'],
            'UTTypeDescription': "OpenSesame experiment",
            'UTTypeIdentifier': "nl.cogsci.osdoc.osexp",
            'UTTypeTagSpecification': {
                'public.filename-extension': 'osexp',
                'public.mime-type': 'application/gzip'
            }
        }
    ]
}
# Placed here to not let linter go crazy. Will be overwritten by main program
RESOURCE_DIR = ""

# ===== Settings specific to dmgbuild =====

# Create a DMG template name, so version can be overwritten if it can be
# determined from the OS libraries.
os_dmg_template = 'opensesame_{}-py37-macos-x64-1.dmg'

# Name of the DMG file that will be created in OUTPUT_FOLDER
DMG_FILE = os_dmg_template.format(VERSION)
# DMG format
DMG_FORMAT = 'UDZO'
# Locations of shortcuts in DMG window
DMG_ICON_LOCATIONS = {
    APP_NAME + '.app': (5, 452),
    'Applications': (200, 450)
}
# Size of DMG window when mounted
DMG_WINDOW_RECT = ((300, 200), (358, 570))
# Size of icons in DMG
DMG_ICON_SIZE = 80

# Background of DMG file
DMG_BACKGROUND = "/Users/robbertmijn/Documents/projecten_local/opensesame-macos-build-scripts/opensesame_resources/einstein.png"

# ===============================================================================
# Extra settings and functions specific to OpenSesame (Remove for other apps)
# ===============================================================================

LOCAL_LIB_FOLDER = "/usr/local/lib"

# Try to obtain OpenSesame version from OpenSesame source
os_metadata_file = os.path.expanduser(os.path.join(CONDA_ENV_PATH, 'lib', 'python3.11',
                                                   'site-packages', 'libopensesame', 'metadata.py'))
try:
    with open(os_metadata_file, 'r') as fp:
        metadata = fp.read()
except Exception as e:
    print("Could not read OpenSesame version from metadata: {}".format(e))
else:
    version_match = re.search("(?<=__version__)\s*=\s*u'(.*)'", metadata)
    if version_match:
        VERSION = version_match.group(1)

    codename_match = re.search("(?<=codename)\s*=\s*u'(.*)'", metadata)
    if codename_match:
        codename = codename_match.group(1)
        LONG_VERSION = VERSION + ' ' + codename
    else:
        LONG_VERSION = VERSION

    # Overwrite name of the DMG file that will be created in OUTPUT_FOLDER
    DMG_FILE = os_dmg_template.format(VERSION)

    print("Creating app for {} {}".format(APP_NAME, LONG_VERSION))


def extra():
    # copy the opensesame entry script to a file with the .py extension again
    # otherwise multiprocessing doesn't work
    copy_opensesame_with_py_ext()
    # Create qt.conf files, to enable Qt to find all libraries inside the app.
    compose_qtconf()
    # Remove superfluous conda files
    # cleanup_conda()
    # Fix some hardcoded conda paths
    fix_paths()


def fix_paths():
    kernel_json = os.path.join(
        RESOURCE_DIR, 'share', 'jupyter', 'kernels', 'python3', 'kernel.json')
    if os.path.exists(kernel_json):
        print('Fixing kernel.json')
        with open(kernel_json, 'r') as fp:
            kernelCfg = json.load(fp)
            kernelCfg['argv'][0] = 'python'
        with open(kernel_json, 'w+') as fp:
            json.dump(kernelCfg, fp)


def compose_qtconf():
    """ Create a qt.conf file to remap all the Qt paths to their relative locations
    in the app. The QtWebEngineProcess uses its own qt.conf, and ignores the general one
    so a separate one is created for QtWebEngineProcess in the libexec dir. """

    qtconf = os.path.join(RESOURCE_DIR, 'bin', 'qt.conf')
    qtconf_wep = os.path.join(RESOURCE_DIR, 'libexec', 'qt.conf')

    contents = """[Paths]
	Prefix = ..
 	Binaries = bin
	Libraries = lib
	Headers = include/qt
	Plugins = plugins
	Translations = translations
    """

    contents_wep = """[Paths]
	Prefix = ..
	Translations = translations
    """

    with open(qtconf, "w+") as f:
        f.write(contents)

    with open(qtconf_wep, "w+") as f:
        f.write(contents_wep)


def copy_opensesame_with_py_ext():
    """ Copy bin/opensesame to bin/opensesame.py to enable multiprocessing """
    try:
        shutil.copy(
            os.path.join(RESOURCE_DIR, 'bin', ENTRY_SCRIPT),
            os.path.join(RESOURCE_DIR, 'bin', ENTRY_SCRIPT + '.py')
        )
    except IOError as e:
        print("Could not copy opensesame to opensesame.py: {}".format(e))


def cleanup_conda():
    try:
        folders = [
            os.path.join(RESOURCE_DIR, 'translations'),
        ]
        map(shutil.rmtree, folders)
    except IOError as e:
        print("Error during cleanup: {}".format(e))
