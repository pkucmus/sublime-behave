import os
import re
from subprocess import CalledProcessError, PIPE, Popen

import sublime
import sublime_plugin


keywords = ['given', 'when', 'then']
completions = {}
steps = set()
missing_steps_notice = (
    'You can implement step definitions for undefined steps '
    'with these snippets'
)


class BehaveMixin(object):

    def index_steps(self):
        steps_definitions = self.get_steps()
        text = steps_definitions.decode('utf-8')
        for line in text.split('\n'):
            if line.startswith('  '):
                line = line.replace('  ', '', 1)
                step_info = line.split(' ')
                step_type = step_info[0].lower()
                if not step_type == '*':
                    steps.add((step_type, ' '.join(step_info[1:])))
            if missing_steps_notice in line:
                break

    def get_steps(self):
        try:
            proc = Popen(
                [
                    '/home/pkucmus/.virtualenvs/behave/bin/behave',
                    '--dry-run',
                    '-f',
                    'steps',
                    '--no-summary',
                    '-s',
                ],
                stdin=PIPE, stdout=PIPE, stderr=PIPE
            )
            return proc.communicate()[0]
        except CalledProcessError as e:
            print(e.output)
            if missing_steps_notice in e.output.decode('utf-8'):
                return e.output
            steps.clear()
            print('Failed to parse steps!')
            sublime.status_message('Failed to parse steps!')
            self.failed_to_parse = True
            raise e

    def parse_variables(self, text):
        for i, var in enumerate(re.findall(r'(\{[\w+]+\})', text), 1):
            text = text.replace(
                var, '${{{}:{}}}'.format(
                    i, var.replace('{', '\\{').replace('}', '\\}')
                )
            )
        return text


class BehaveInsertStepCommand(sublime_plugin.TextCommand, BehaveMixin):

    def run(self, edit, step):
        for region in self.view.sel():
            self.view.insert(edit, region.begin(), step)


class BehaveStepsCommand(sublime_plugin.TextCommand, BehaveMixin):

    def select_item(self, window, idx):
        if idx >= 0:
            window.run_command(
                'behave_insert_step',
                {'step': self.step_list[idx]}
            )

    def run(self, edit):
        self.step_list = ['{} {}'.format(t.capitalize(), d) for t, d in steps]
        if not self.step_list:
            self.view.set_status(
                'behave', 'No steps found - might be a behave error.'
            )
        window = self.view.window()
        window.show_quick_panel(
            items=self.step_list,
            on_select=lambda idx: self.select_item(window, idx)
        )


class BehaveAutocomplete(sublime_plugin.EventListener, BehaveMixin):

    failed_to_parse = False

    def __init__(self):
        self.index_steps()
        print('BehaveAutocomplete initialized!')

    def on_query_completions(self, view, prefix, locations):
        _completions = [sug for key, sug in completions.items()]
        completions.clear()
        return _completions

    def on_modified(self, view):
        view_sel = view.sel()
        if not view_sel:
            return

        if not self._is_gherkin_scope(view):
            return

        view.settings().set('auto_complete', False)

        pos = view_sel[0].end()
        next_char = view.substr(sublime.Region(pos - 1, pos))

        if next_char in (' ', '\n'):
            view.run_command('hide_auto_complete')
            return

        view.run_command('hide_auto_complete')
        self._show_auto_complete(view)
        self._fill_completions(view, pos)

    def _show_auto_complete(self, view):
        def _show_auto_complete():
            view.run_command('auto_complete', {
                'disable_auto_insert': True,
                'api_completions_only': True,
                'next_completion_if_showing': False,
                'auto_complete_commit_on_tab': True,
            })
        sublime.set_timeout(_show_auto_complete, 0)

    def _fill_completions(self, view, location):
        """ Prepares completions for auto-complete list
        :param view: `sublime.View` object
        :type view: sublime.View
        :param location: position of cursor in line
        :type locations: int
        """
        last_keyword = ''
        current_region = view.line(location)
        current_line_text = view.substr(current_region).strip()
        current_line_words = current_line_text.split()

        # Don't fill completions until after first space is typed
        if ' ' not in current_line_text:
            return

        # If first word is keyword, take that one
        if current_line_words and current_line_words[0].lower() in keywords:
            last_keyword = current_line_words[0].lower()
        # Otherwise, reverse iterate through lines until keyword is found
        else:
            all_lines = view.split_by_newlines(sublime.Region(0, view.size()))
            current_index = all_lines.index(current_region)
            for region in reversed(all_lines[0:current_index]):
                region_text = view.substr(region).lstrip()
                split_line = region_text.split(' ', 1)
                if split_line and split_line[0].lower() in keywords:
                    last_keyword = split_line[0].lower()
                    break

        if not last_keyword:
            print(
                'Gherkin Auto-Complete Plus: Could not find \'Given\', '
                '\'When\', or \'Then\' in text.'
            )
            return

        for step_type, step in steps:
            if step_type == last_keyword:
                if len(current_line_words) == 1:
                    step_format = self.parse_variables(step)
                    suggestion = (step + '\t' + step_type, step_format)
                    completions[step] = suggestion

                elif len(current_line_words) > 1:
                    if self._step_matches_line(
                        step.split(), current_line_words
                    ):
                        line_text = ' '.join(current_line_words[1:-1])
                        step = step.replace(line_text, '', 1)

                        step_format = self.parse_variables(step).strip()
                        suggestion = (step + '\t' + step_type, step_format)
                        completions[step] = suggestion

    def _step_matches_line(self, step_words, line_words):
        line_text = ' '.join(line_words[1:])
        step_text = ' '.join(step_words)

        if len(step_text) >= len(line_text):
            return step_text.startswith(line_text)
        else:
            return False

    def _is_gherkin_scope(self, view):

        if view is None:
            return False

        try:
            location = view.sel()[0].begin()
        except IndexError:
            return False

        matcher = 'text.gherkin.feature'

        return view.match_selector(location, matcher)

    def is_step_impl_file(self, filename):
        path, ext = os.path.splitext(filename)
        if 'steps' in path and ext == '.py':
            return True
        return False

    def on_post_save_async(self, view):
        if (
            self.is_step_impl_file(view.file_name()) or
            self._is_gherkin_scope(view)
        ):
            print('Refreshing BehaveAutocomplete.')
            self.index_steps()
