"""
:mod:`tests.support.apple_release` module.

Share explicit Apple release inputs without invoking Xcode or using Git state.
"""

from .apple_metadata import PROJECT as METADATA_PROJECT

# SECTION: CONSTANTS


POLICY = """[tool.popo.apple-release]
project = "Example.xcodeproj/project.pbxproj"
target = "Example"
configurations = ["Debug", "Release"]
"""

PROJECT = METADATA_PROJECT.replace(
    'name = Example;',
    'name = Example; productType = com.apple.product-type.application;',
).replace(
    'MARKETING_VERSION = 1.2.0;',
    'MARKETING_VERSION = 1.2.0; CURRENT_PROJECT_VERSION = 7;',
)


# SECTION
