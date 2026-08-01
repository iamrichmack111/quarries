WATCHER_LINES = [
"             .::!!!!!!!:.",
".!!!!!:.     .:!!!!!!!!!!!!",
"~~~~!!!!!!. .:!!!!!!!!!UWWW$$$",
" :$$NWX!!:<!!!!!!XUWW$$$$$$$$$P",
' $$$$$##WXUW$$$$"  $$$$$$$$#',
" $$$$$  $$$$$$$$   4$$$$$*",
' ^$$$B  $$$$$$$$   d$$R"',
'   "*$bd$$ \'*$$$$$$o+#"',
'        ""    """"""',
]

PALETTES = {
    "locked": ["#64748b", "#475569", "#334155"],
    "open": ["#38bdf8", "#22d3ee", "#34d399", "#a3e635"],
    "thinking": ["#818cf8", "#a78bfa", "#c084fc", "#f472b6"],
    "working": ["#f59e0b", "#fbbf24", "#fde047"],
    "error": ["#991b1b", "#dc2626", "#f87171"],
}


def render_watcher(state: str = "locked") -> str:
    colors = PALETTES.get(state, PALETTES["locked"])
    return "\n".join(
        f"[{colors[i % len(colors)]}]{line}[/]"
        for i, line in enumerate(WATCHER_LINES)
    )
