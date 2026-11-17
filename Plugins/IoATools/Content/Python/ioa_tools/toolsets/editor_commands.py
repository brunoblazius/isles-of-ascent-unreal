import contextlib
import io
import traceback

import unreal

import toolset_registry


@unreal.uclass()
class EditorCommandTools(unreal.ToolsetDefinition):
    """Runs console commands and Python code inside the running Unreal Editor.
    Covers anything the other toolsets don't expose (stats, cvars, editor scripting APIs)."""

    @toolset_registry.tool_call
    @staticmethod
    def run_console_command(command: str) -> None:
        """Runs a console command in the editor world, as if typed into the console.

        Args:
            command: The full command line, e.g. 'stat unit' or 'r.ScreenPercentage 75'.
        """
        if not command.strip():
            raise ValueError('command must not be empty.')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.SystemLibrary.execute_console_command(world, command)

    @toolset_registry.tool_call
    @staticmethod
    def execute_python(code: str) -> str:
        """Executes Python code in the editor with the `unreal` module imported.

        Args:
            code: Python source. Assign to a variable named `result` to return a value.

        Returns:
            Captured stdout followed by repr(result) when `result` was assigned.
        """
        if not code.strip():
            raise ValueError('code must not be empty.')
        scope = {'unreal': unreal, '__name__': '__ioa_exec__'}
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                exec(compile(code, '<execute_python>', 'exec'), scope)
        except Exception:
            raise RuntimeError(out.getvalue() + traceback.format_exc())
        text = out.getvalue()
        if 'result' in scope:
            text += repr(scope['result'])
        return text
