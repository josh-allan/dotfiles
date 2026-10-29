"""Commands used by the host-local Herdr plugins."""

from cyclopts import App

app = App(name="herdr-tools", help=__doc__, version_flags=[])

close = App(
    name="close",
    help="Close Herdr surfaces with a busy-work confirmation.",
    version_flags=[],
)
close.command("herdr_tools.close_confirm:pane_command", name="pane")
close.command("herdr_tools.close_confirm:tab_command", name="tab")
close.command("herdr_tools.close_confirm:workspace_command", name="workspace")
close.command("herdr_tools.close_confirm:confirm_command", name="confirm")
app.command(close)

focus = App(name="focus", help="Track focus and walk pane history.", version_flags=[])
focus.command("herdr_tools.focus_watch:watch_command", name="watch")
focus.command("herdr_tools.pane_history:record_command", name="record")
focus.command("herdr_tools.pane_history:back_command", name="back")
focus.command("herdr_tools.pane_history:forward_command", name="forward")
app.command(focus)

label = App(name="label", help="Name Herdr panes, tabs, and spaces.", version_flags=[])
label.command("herdr_tools.pane_label:app", name="pane")
label.command("herdr_tools.space_label:label", name="space")
app.command(label)


def main() -> None:
    """Run the host-local Herdr helper CLI."""
    app()


if __name__ == "__main__":
    main()
