# Sublime Text 3 Behave

This is supposed to be a Python Behave support plugin for ST3. It calles a dry run of Behave with the `steps` formatter and parsers it to get a full list of steps based on the Behave Python code you have. The list get's refreshed on every save of a `feature` file or a `py` file in the steps directory.

## Credits

I used some of the ideas and code from [Gherkin Auto-Complete Plus](https://github.com/austincrft/sublime-gherkin-auto-complete-plus).

## Compatibility

Tested with Python Behave 1.2.5 on a Ubuntu 14.10. Contributions for making 

## Installation 

I'm still working on making it work with Package Installer.

Just copy the repository into your Sublime Packages directory (most likely in ~/.config/sublime-text3/Packages).

```
$ cd ~/.config/sublime-text3/Packages
$ git clone https://github.com/pkucmus/sublime-behave Behave
```
and restart Sublime.

## Configuration

Go to Preferences -> Package Settings -> Behave -> Settings - User.

Edit the file and save (e.g.):
```
{
    "behave_runner": "/home/user/.virtualenvs/behave/bin/behave"
}
```
