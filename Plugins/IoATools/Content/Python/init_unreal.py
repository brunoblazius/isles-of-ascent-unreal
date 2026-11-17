import unreal

from ioa_tools import toolsets

if not toolsets._registration.register():
    unreal.log_warning('IoATools: ToolsetRegistry unavailable, toolsets not registered.')
