import re
from functools import partial
from collections import namedtuple

def canonicalize_author(value):
  """Canonicalizes an author name for inclusion in a bibliography entry.  Some
  of the transformations included are:

    * First Last -> Last, First (triggered on the presence of a comma)
    * Ensuring that "et all" appears at the end of the author line if
      the line needed to be transformed.
    * Removing trailing periods.
  
  >>> canonicalize_author("")
  ''

  >>> canonicalize_author("Bryan Kyle")
  'Kyle, Bryan'

  >>> canonicalize_author("Bryan Kyle et all")
  'Kyle, Bryan et all'

  >>> canonicalize_author("Bryan Kyle et all.")
  'Kyle, Bryan et all'

  """
  if not value:
    return ""

  et_all = "et all"

  # Strip trailing periods from the input string.
  # FIXME(bkyle): Handle abbreviated suffixes (Jr., Sr. Phd., etc)
  if value[-1] == ".":
    value = value[:len(value)-1]

  # Strip off "et all" if it exists
  i = value.lower().find(et_all)
  if i > -1:
    value = value[:i] + value[i + len(et_all):]
  else:
    et_all = ""

  # Convert the "first last" to "last, first" iff there is no comma in
  # the vaue and there's at least one space.
  i = value.find(",") 
  if i == -1:
    i = value.find(" ")
    if i > 0:
      first = value[:i].strip()
      last = value[i:].strip()
      value = "%s, %s" % (last, first)

  # Move "et all" to the end
  if et_all:
    value = value.strip() + " " + et_all

  # Strip trailing periods from the input string.
  # FIXME(bkyle): Handle abbreviated suffixes (Jr., Sr. Phd., etc)
  if value[-1] == ".":
    value = value[:len(value)-1]

  return value

def canonicalize_title(value):
  """Canonicalizes a title string for inclusion in a bibliography entry.  Some
  of the transformations included are:

    * Removing leading and trailing quotation marks

  >>> canonicalize_title('"Hello World"')
  'Hello World'
  """

  if not value:
    return ""

  if value[0] == '"':
    value = value[1:]
  if value[-1] == '"':
    value = value[:-1]

  return value


# Template for a bibliography entry.
TEMPLATE = "<author> <title> <pubdate> <ref>"

# Variable represents a variable in the bibliograpy.
# 
# Fields:
#   caption: str containing the prompt to the user when asking for a value.
#   template: str containing a python template that will replace the variable
#     in the bibliography template.  A single ``%s`` included will be replaced
#     by the value given by the user.
#   filter: (Optional) A function that should be called to filter or otherwise
#     format the data from the user before inserting it into the bibliography
#     entry.
Variable = namedtuple("Variable", ["caption", "template", "filter"])

# Variable definitions for bibliography entries.  The key is the name of the variable
# as it's expected to appear in the entry string.  The value is a tuple
VARS = {
  "author": Variable(
    caption="Author (Last, First)",
    template="%s.",
    filter=canonicalize_author
  ),
  "title": Variable(
    caption="Title",
    template="\"%s\"",
    filter=canonicalize_title
  ),
  "pubdate": Variable(
    caption="Publication Date (DD MMM YYYY)",
    template="%s.",
    filter=None
  ),
  "ref": Variable(
    caption="Reference",
    template="<<%s>>",
    filter=None
  ),
}

try:

  import sublime
  import sublime_plugin

  class CreateBibliographyEntryCommand(sublime_plugin.TextCommand):
    """Automates the process of writing a Bibliography entry."""

    def get_next_input_or_insert(self, edit, entry, var=None, text=None):
      """Asks the user for the next piece of information or inserts the bibliography
      entry when all of the data has been collected.

      This method looks through the given ``entry`` string for any template variables.
      If there are missing template variables then the first is selected and the user
      is prompted to enter a value for it.  The implementation configures the ``done``
      callback for the entry prompt to call itself using a ``functools.partial``.

      Args:
        edit: ``sublime.Edit`` instance to use for mutating the buffer.
        entry: str that contains the entry being built.
        var: (Optional) variable to replace with the value of ``text``.
        text: (Optiona) value to replace the specified variable with.
      """

      if text is None:
        text = ""

      if var is not None:
        filter_fn = VARS[var].filter
        if text and filter_fn:
          text = filter_fn(text)
        if text:
          text = VARS[var].template % text
        entry = re.sub("<%s>" % var, text, entry)
        entry = entry.strip()

      vars = re.findall("<(author|title|pubdate|ref)>", entry)
      if len(vars) > 0:
        var = vars[0]
        caption = VARS[vars[0]].caption
        self.view.window().show_input_panel(caption, "", partial(self.get_next_input_or_insert, edit, entry, var), None, None)
      else:
        print(entry)
        self.view.run_command("insert", {"characters": entry})


    def run(self, edit):
      entry = TEMPLATE
      sel = self.view.sel()[0]
      if sel.size() > 0:
        ref = self.view.substr(sel)
        self.get_next_input_or_insert(edit, entry, "ref", ref)
      else:
        self.get_next_input_or_insert(edit, entry)
except ImportError as e:
  # If there was an ImportError that implies that this module was run outside of the context
  # of Sublime.  This can happen when the module is being run as pure Python code for testing
  # In this context, Sublime doesn't matter so this error is fine to ignore.
  pass

if __name__ == "__main__":
  import doctest
  doctest.testmod()
