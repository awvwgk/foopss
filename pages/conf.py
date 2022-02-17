project = "Fortran OOP Seminar Series"
author = "Sebastian Ehlert"
copyright = f"2022 {author}"

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinx.ext.intersphinx",
    "sphinx_comments",
]
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "substitution",
    "html_image",
]

html_theme = "sphinx_book_theme"
html_title = "Fortran OOP Seminar Series"
html_logo = "_static/foopss-logo.svg"
html_favicon = "_static/fortran-logo.svg"

_extra_navbar = """
<div class="sd-fs-4">
<!--
<a href="https://fortran-lang.discourse.group/" target="_blank">
    <i class="fab fa-discourse"></i>
</a>
<a href="https://twitter.com/fortranlang" target="_blank">
    <i class="fab fa-twitter"></i>
</a>
<a href="https://github.com/fortran-lang" target="_blank">
    <i class="fab fa-github"></i>
</a>
-->
</div>
"""

html_theme_options = {
    "repository_url": "https://github.com/awvwgk/foopss",
    "repository_branch": "main",
    "use_repository_button": True,
    "use_edit_page_button": True,
    "use_download_button": False,
    "path_to_docs": "pages",
    "show_navbar_depth": 3,
    "logo_only": True,
    "extra_navbar": _extra_navbar,
    #"single_page": True,
}

html_sidebars = {
    "**": ["sidebar-logo.html", "search-field.html"],
}

html_css_files = [
    "css/custom.css",
]
html_static_path = ["_static"]
templates_path = ["_templates"]

master_doc = "index"

comments_config = {}
