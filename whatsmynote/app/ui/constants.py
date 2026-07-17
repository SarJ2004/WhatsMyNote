from rich.table import Table

LOGO = """
█   █ █   █ █[dim]▀▀▀[/dim]█ [dim]▀▀[/dim]█[dim]▀▀[/dim] █[dim]▀▀▀▀[/dim] █[dim]▀[/dim]█[dim]▀[/dim]█ █   █ █[dim]▀▀▀[/dim]█ █[dim]▀▀▀[/dim]█ [dim]▀▀[/dim]█[dim]▀▀[/dim] █[dim]▀▀▀▀[/dim]
█ █ █ █[dim]▀▀▀[/dim]█ █[dim]▀▀▀[/dim]█   █   [dim]▀▀▀▀[/dim]█ █ █ █ █[dim]▄▄▄[/dim]█ █   █ █   █   █   █[dim]▀▀▀ [/dim]
█[dim]▄[/dim]█[dim]▄[/dim]█ █   █ █   █   █   [dim]▄▄▄▄[/dim]█ █   █ [dim]▄▄▄▄[/dim]█ █   █ █[dim]▄▄▄[/dim]█   █   █[dim]▄▄▄▄[/dim]
"""

QUIRKY_PHRASES = [
    "Crunching your numbers...",
    "Looking for spare change...",
    "Consulting the finance oracle...",
    "Digging through receipts...",
    "Balancing the ledger...",
    "Tracking down that last coffee...",
    "Auditing your wallet...",
]

DOLLAR_FRAMES = [
    "[ $       ]",
    "[  $      ]",
    "[   $     ]",
    "[    $    ]",
    "[     $   ]",
    "[      $  ]",
    "[       $ ]",
    "[        $]",
    "[       $ ]",
    "[      $  ]",
    "[     $   ]",
    "[    $    ]",
    "[   $     ]",
    "[  $      ]",
]

def get_commands_table():
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="#ffaa55")
    table.add_column(style="#dddddd")
    table.add_column(style="#888888")
    
    commands = [
        ("/login", "login to account"),
        ("/config", "set api key"),
        ("/logout", "log out"),
    ]
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    return table
