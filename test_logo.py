import sys
from rich.text import Text
sys.stdout.reconfigure(encoding='utf-8')

LOGO = """
█   █ █   █ █[dim]▀▀▀[/dim]█ [dim]▀▀[/dim]█[dim]▀▀[/dim] █[dim]▀▀▀▀[/dim] █[dim]▀[/dim]█[dim]▀[/dim]█ █   █ █[dim]▀▀▀[/dim]█ █[dim]▀▀▀[/dim]█ [dim]▀▀[/dim]█[dim]▀▀[/dim] █[dim]▀▀▀▀[/dim]
█ █ █ █[dim]▀▀▀[/dim]█ █[dim]▀▀▀[/dim]█   █   █[dim]▀▀▀[/dim]█ █ █ █ █[dim]▄▄▄[/dim]█ █   █ █   █   █   █[dim]▀▀▀ [/dim]
█[dim]▄[/dim]█[dim]▄[/dim]█ █   █ █   █   █   [dim]▄▄▄▄[/dim]█ █   █ [dim]▄▄▄▄[/dim]█ █   █ █[dim]▄▄▄[/dim]█   █   █[dim]▄▄▄▄[/dim]
"""

text = Text.from_markup(LOGO.strip('\n'))
lines = text.split()
for i, line in enumerate(lines):
    print(f'Line {i}: length {len(line)}, text: {repr(line.plain)}')
