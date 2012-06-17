# -*- coding: utf-8 -*-

import os
from os.path import join, normpath, dirname

import sublime
import sublime_plugin
from sublime import status_message

# Gtags
import gtags
from gtags import (TagFile, PP, find_tags_root)

settings = sublime.load_settings('GTags.sublime-settings')


def run_on_cwd(dir=None):
    window = sublime.active_window()

    def wrapper(func):
        view = window.active_view()

        filename = view.file_name()
        if filename is None:
            sublime.error_message('Cannot use GNU GLOBAL for non-file')
            return

        if dir is None:
            tags_root = find_tags_root(dirname(filename))
            if tags_root is None:
                sublime.error_message("GTAGS not found. build tags by 'gtags'")
                return
        else:
            tags_root = dir[0]

        tags = TagFile(tags_root, settings.get('extra_tag_paths'))
        func(view, tags, tags_root)

    return wrapper


class JumpHistory(object):
    instance = None

    def __init__(self):
        self._storage = []

    def append(self, view):
        filename = view.file_name()
        row, col = view.rowcol(view.sel()[0].begin())
        self._storage.append('%s:%d:%d' % (filename, row + 1, col + 1))

    def jump_back(self):
        if self.empty():
            sublime.status_message('Jump history is empty')
        else:
            filename = self._storage.pop()
            sublime.active_window().open_file(filename, sublime.ENCODED_POSITION)

    def jump_forward(self):
        sublime.status_message('Not implemented')

    def empty(self):
        return len(self._storage) == 0


def jump_history():
    if JumpHistory.instance is None:
        JumpHistory.instance = JumpHistory()
    return JumpHistory.instance


class GtagsJumpBack(sublime_plugin.WindowCommand):
    def run(self):
        jump_history().jump_back()


def gtags_jump_keyword(view, keywords, root, showpanel=False):
    def jump(keyword):
        jump_history().append(view)
        position = '%s:%d:0' % (
            os.path.normpath(keyword['path']), int(keyword['linenum']))
        view.window().open_file(position, sublime.ENCODED_POSITION)

    def on_select(index):
        if index == -1:
            return
        jump(keywords[index])

    if showpanel or len(keywords) > 1:
        if settings.get('show_relative_paths'):
            convert_path = lambda path: os.path.relpath(path, root)
        else:
            convert_path = os.path.normpath
        data = [
            [kw['signature'], '%s:%d' % (convert_path(kw['path']), int(kw['linenum']))]
             for kw in keywords
        ]
        view.window().show_quick_panel(data, on_select)
    else:
        jump(keywords[0])


class GtagsShowSymbols(sublime_plugin.TextCommand):
    def run(self, edit):
        @run_on_cwd()
        def and_then(view, tags, root):
            items = tags.start_with('')
            if not items:
                status_message("no items?")
                return

            def on_select(i):
                if i != -1:
                    gtags_jump_keyword(view, tags.match(items[i]), root)

            view.window().show_quick_panel(items, on_select)

class GtagsNavigateToDefinition(sublime_plugin.TextCommand):
    def run(self, edit):
        @run_on_cwd()
        def and_then(view, tags, root):
            symbol = view.substr(view.word(view.sel()[0]))
            matches = tags.match(symbol)
            if not matches:
                status_message("'%s' is not found on tag." % symbol)
                return

            gtags_jump_keyword(view, matches, root)

class GtagsFindReferences(sublime_plugin.TextCommand):
    def run(self, edit):
        @run_on_cwd()
        def and_then(view, tags, root):
            symbol = view.substr(view.word(view.sel()[0]))
            matches = tags.match(symbol, reference=True)
            if not matches:
                status_message("'%s' is not found on rtag." % symbol)
                return

            gtags_jump_keyword(view, matches, root)


class GtagsRebuildTags(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        @run_on_cwd(args.get('dirs'))
        def and_then(view, tags, root):
            sublime.status_message("rebuild tags on dir: %s" % root)
            tags.rebuild()
            sublime.status_message("build success on dir: %s" % root)
