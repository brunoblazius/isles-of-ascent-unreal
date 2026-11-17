from toolset_registry.registration import Registration
from ioa_tools.toolsets import editor_commands
from ioa_tools.toolsets import landscape

_registration = Registration([
    editor_commands.EditorCommandTools,
    landscape.LandscapeTools,
])
