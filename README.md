htmlparser
==========

A library for leveraging html in Information extraction tasks

Author: Ruslan Mavlyutov (m-ceros@yandex.ru)
Additional information: http://factex.blogspot.com/

Usage:

1) create HTMLTextBlocksTree:
- from html string:
<pre>
from  HTMLTextBlocksTree import *
html_string = "&lt;h1&gt;Hello, World!&lt;/h1&gt;"
tree = HTMLTextBlocksTree(html_string)
</pre>
   
- from html file:
<pre>
from  HTMLTextBlocksTree import *
html_file_name = "test.html"
tree = HTMLTextBlocksTree(filename=html_file_name)
</pre>

- from URL:
<pre>
from  HTMLTextBlocksTree import *
url = "http://australianpolitics.com/united-states-of-america/president/list-of-presidents-of-the-united-states"
tree = HTMLTextBlocksTree(url=url)
</pre>

2) use tree:
- to remove clutter (menu and other static content) from the page:
You will need another tree built from page with same structure, to substract it:
<pre>
url_substract = "http://australianpolitics.com/constitution-aus"
tree.substract_tree(HTMLTextBlocksTree(url=url_substract))
</pre>

- to get text elements with similar sense:
<pre>
similar_sense_groups = tree.get_similar_sense_texts()
</pre>

- to get all text nodes in normal form:
<pre>
text_nodes = tree.get_text_nodes()
</pre>

3) for various usage
- tree implemented as an array of nodes (class Node), each node can be accessed through 
its index (tree[node_index]). 
- bad idea to iterate the tree as an array, since some nodes of the tree might be 
unlinked (not be a part of it after manipulations with tree)
- the right way to iterate the tree is to use iterate_DFS, that perform deep-first search iteration
