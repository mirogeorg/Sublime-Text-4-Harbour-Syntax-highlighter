import html
import json

import sublime
import sublime_plugin


_CACHE = None
_NEW_SYNTAX = "Packages/Harbour/Harbour.sublime-syntax"
_LEGACY_SYNTAX_SUFFIXES = (
    "/harbour.tmlanguage",
    "/harbour.json-tmlanguage1",
)


def _migrate_legacy_view(view):
    syntax = view.settings().get("syntax") or ""
    normalized = syntax.replace("\\", "/").casefold()
    if not normalized.endswith(_LEGACY_SYNTAX_SUFFIXES):
        return
    try:
        view.assign_syntax(_NEW_SYNTAX)
    except AttributeError:
        view.set_syntax_file(_NEW_SYNTAX)


def plugin_loaded():
    for window in sublime.windows():
        for view in window.views():
            _migrate_legacy_view(view)


def _records():
    global _CACHE
    if _CACHE is None:
        text = sublime.load_resource("Packages/Harbour/data/function_help.json")
        _CACHE = json.loads(text)
    return _CACHE


def _display_signature(record):
    signature = record["signature"]
    usage = record.get("snippet") or ""
    marker = usage.find("->")
    if marker >= 0:
        result = usage[marker + 2 :].strip()
        if result and len(result) <= 48:
            return signature + " -> " + result
    returns = (record.get("return") or "").strip()
    if (
        (returns.startswith("<") and returns.endswith(">") and " " not in returns)
        or returns.upper() == "NIL"
    ):
        return signature + " -> " + returns
    return signature


def _popup(record):
    signature = html.escape(_display_signature(record))
    summary = html.escape(record["summary"])
    libraries = ", ".join(html.escape(item["name"]) for item in record["libraries"])
    installed = "installed" if record["installed"] else "not installed"
    source = record["source"]
    source_text = (
        "{}:{}".format(html.escape(source["path"]), source["line"])
        if source
        else "source documentation pending"
    )
    return (
        "<body id='harbour-help'><h2>" + signature + "</h2>"
        "<p>" + summary + "</p>"
        "<p><b>Libraries:</b> " + libraries + " (" + installed + ")</p>"
        "<p><b>Usage:</b> " + html.escape(record["snippet"]) + "</p>"
        "<p><b>Source:</b> " + source_text + "</p></body>"
    )


class HarbourFunctionHelpCommand(sublime_plugin.WindowCommand):
    def run(self):
        records = _records()
        keys = sorted(records, key=lambda key: records[key]["name"].casefold())
        rows = [
            [_display_signature(records[key]), records[key]["summary"]]
            for key in keys
        ]

        def selected(index):
            if index >= 0 and self.window.active_view():
                self.window.active_view().show_popup(
                    _popup(records[keys[index]]),
                    max_width=900,
                    max_height=600,
                )

        self.window.show_quick_panel(rows, selected)


class HarbourHelpForSymbolCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if not self.view.sel():
            return
        point = self.view.sel()[0].begin()
        word = self.view.substr(self.view.word(point)).casefold()
        record = _records().get(word)
        if record:
            self.view.show_popup(_popup(record), location=point, max_width=900, max_height=600)
        else:
            sublime.status_message("Harbour: no verified help for this symbol")


class HarbourLegacySyntaxMigration(sublime_plugin.EventListener):
    def on_load_async(self, view):
        _migrate_legacy_view(view)

    def on_activated_async(self, view):
        _migrate_legacy_view(view)
