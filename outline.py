import re
from pprint import pprint
import sublime
from sublime import Region
from sublime_plugin import WindowCommand, TextCommand, EventListener
from .show import show, refresh_sym_view, get_sidebar_views_groups, get_sidebar_status

class OutlineCommand(WindowCommand):
        def run(self, immediate=False, single_pane=False, project=False, other_group=False, layout=0):
                show(self.window, single_pane=single_pane, other_group=other_group, layout=layout)

class OutlineCloseSidebarCommand(WindowCommand):
        def run(self):
                for v in self.window.views():
                        if u'𝌆' in v.name():
                                self.window.focus_view(v)
                                self.window.run_command('close_file')

                self.window.set_layout({"cols": [0.0, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1]]})

def removeParen(str):
        return re.sub(r"\([^)]*\)", "", str)

class OutlineRefreshCommand(TextCommand):
        def run(self, edit, symlist=None, symkeys=None, path=None, to_expand=None, toggle=None):
                self.view.erase(edit, Region(0, self.view.size()))
                if self.view.settings().get('outline_alphabetical'):
                        symlist, symkeys = (list(t) for t in zip(*sorted(zip(symlist, symkeys))))

                syms = list(zip(symkeys, symlist))
                #pprint(  syms)
                #print("Removed:")
                removed = []

                def n(s):
                        ret = re.match(r".*[A-Za-z0-9]{2}.*", re.sub(r"async\s+", "", re.sub(r"\([^)]*\)", "", s)))
                        ret = ret and not re.match(r"^\s*[a-z][a-z]$", s)
                        ret = ret and not s.find("=>") != -1
                        # pprint("ret = %s" % ret)
                        #pprint("str = %s" % s)
                        if not ret:
                                removed.append("#" + str(len(removed)) + " " + s + "")
                        return ret

                syms = list(x for x in list(syms) if n(x[1]))

                #print(",\n".join(removed))

                if len(syms) > 0:
                        symkeys, symlist = (list(t) for t in zip(*syms))
                else:
                        symkeys = []
                        symlist = []

                symlist = list(re.sub(r"async\s+", "", t) for t in symlist)
                symlist = list(re.sub(r"^\s*function\s+", "", t) for t in symlist)
                symlist = list(re.sub(r"\*\s*", "*", t) for t in symlist)
                symlist = list(re.sub(r"^\s*([A-Z])", '\\1', re.sub(r"^(\.|[a-z_])", '  \\1', re.sub(r"^\s+", "\t", t))) for t in symlist)
                symlist = list(re.sub(r"[\u2002-\u2009]", " ", t) for t in symlist)

                out = list(u for u in syms)  # if !match
                #print(out)

                self.view.insert(edit, 0, "\n".join(symlist))
                self.view.settings().set('symlist', symlist)
                self.view.settings().set('symkeys', symkeys)
                self.view.settings().set('current_file', path)
                self.view.sel().clear()


class OutlineToggleSortCommand(TextCommand):
        def run(self, edit):
                sym_view = None
                for v in self.view.window().views():
                        if u'𝌆' in v.name():
                                v.settings().set('outline_alphabetical', not v.settings().get('outline_alphabetical'))
                                sym_view = v

                symlist = self.view.get_symbols()
                refresh_sym_view(sym_view, symlist, self.view.file_name())

class OutlineEventHandler(EventListener):
        def on_selection_modified(self, view):
                if 'outline.hidden-tmLanguage' not in view.settings().get('syntax'):
                        return

                sym_view, sym_group, fb_view, fb_group = get_sidebar_views_groups(view)

                sym_view = view
                window = view.window()
                sym_group, i = window.get_view_index(sym_view)

                if len(sym_view.sel()) == 0:
                        return

                (row, col) = sym_view.rowcol(sym_view.sel()[0].begin())

                active_view =None
                for group in range(window.num_groups()):
                        if group != sym_group and group != fb_group:
                                active_view = window.active_view_in_group(group)
                if active_view != None:
                        keys = sym_view.settings().get('symkeys')
                        if keys and len(keys) >= row:
                                region_position = keys[row]
                                r = Region(region_position[0], region_position[1])
                                active_view.show_at_center(r)
                                active_view.sel().clear()
                                active_view.sel().add(r)
                        window.focus_view(active_view)

        def on_activated(self, view):
                if u'𝌆' in view.name():
                        return
                # Avoid error message when console opens, as console is also a view, albeit with a group index of -1
                if view.window().get_view_index(view)[0] == -1:
                        return

                if not get_sidebar_status(view):
                        return

                sym_view, sym_group, fb_view, fb_group = get_sidebar_views_groups(view)

                if sym_view != None:
                        if sym_view.settings().get('current_file') == view.file_name() and view.file_name() != None:
                                return
                        else:
                                sym_view.settings().set('current_file', view.file_name())

                symlist = view.get_symbols()

                refresh_sym_view(sym_view, symlist, view.file_name())

        def on_pre_save(self, view):
                if u'𝌆' in view.name():
                        return
                # this is not absolutely necessary, and prevents views that do not have a file reference from displaying 
                # the symbol list
                # but it solves a console error if the console is activiated, as console is also a view....
                if view.file_name() == None:
                        return

                if not get_sidebar_status(view):
                        return

                sym_view, sym_group, fb_view, fb_group = get_sidebar_views_groups(view)

                if sym_view != None:
                        # Note here is the only place that differs from on_activate_view
                        if sym_view.settings().get('current_file') != view.file_name():
                                sym_view.settings().set('current_file', view.file_name())

                symlist = view.get_symbols()
                refresh_sym_view(sym_view, symlist, view.file_name())
