"""
:mod:`tests.support.apple_metadata` module.

Share literal native metadata fixtures without depending on Apple tools.
"""

# SECTION: CONSTANTS

PROJECT = """{
 rootObject = P;
 objects = {
  P = { isa = PBXProject; buildConfigurationList = L; };
  T = { isa = PBXNativeTarget; name = Example; buildConfigurationList = L; };
  L = { isa = XCConfigurationList; buildConfigurations = (D, R,); };
  D = { isa = XCBuildConfiguration; name = Debug; buildSettings = {
   PRODUCT_BUNDLE_IDENTIFIER = com.example.app; MARKETING_VERSION = 1.2.0;
  }; };
  R = { isa = XCBuildConfiguration; name = Release; buildSettings = {
   PRODUCT_BUNDLE_IDENTIFIER = com.example.app; MARKETING_VERSION = 1.2.0;
  }; };
 };
}"""

POLICY = """[tool.popo]
checks = ["check-apple-metadata"]
[[tool.popo.apple-metadata.rules]]
id = "privacy"
kind = "plist"
path = "Info.plist"
absent = ["PrivateKey"]
[tool.popo.apple-metadata.rules.expected]
ITSAppUsesNonExemptEncryption = false
Resources = [{ Enabled = true }]
[[tool.popo.apple-metadata.rules]]
id = "identity"
kind = "xcode"
path = "Example.xcodeproj/project.pbxproj"
target = "Example"
configurations = ["Debug", "Release"]
consistent = ["MARKETING_VERSION"]
[tool.popo.apple-metadata.rules.expected]
PRODUCT_BUNDLE_IDENTIFIER = "com.example.app"
"""

INFO = {'ITSAppUsesNonExemptEncryption': False, 'Resources': [{'Enabled': True}]}

POLICY += """
[[tool.popo.apple-metadata.rules]]
id = "project-settings"
kind = "xcode"
scope = "project"
path = "Example.xcodeproj/project.pbxproj"
configurations = ["Debug", "Release"]
consistent = ["MARKETING_VERSION"]
"""


# !SECTION
