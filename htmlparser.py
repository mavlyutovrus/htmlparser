"""A library for leveraging html in Information extraction tasks

Author: Ruslan Mavlyutov (m-ceros@yandex.ru)
Additional information: http://factex.blogspot.com/

Usage:

1) create HTMLTextBlocksTree:
- from html string:
from  HTMLTextBlocksTree import *
html_string = "<h1>Hello, World!</h1>"
tree = HTMLTextBlocksTree(html_string)
   
- from html file:
from  HTMLTextBlocksTree import *
html_file_name = "test.html"
tree = HTMLTextBlocksTree(filename=html_file_name)


- from URL:
from  HTMLTextBlocksTree import *
url = "http://australianpolitics.com/united-states-of-america/president/list-of-presidents-of-the-united-states"
tree = HTMLTextBlocksTree(url=url)

2) use tree:
- to remove clutter (menu and other static content) from the page:
You will need another tree built from page with same structure, to substract it:

url_substract = "http://australianpolitics.com/constitution-aus"
tree.substract_tree(HTMLTextBlocksTree(url=url_substract))

- to get text elements with similar sense:
similar_sense_groups = tree.get_similar_sense_texts()

- to get all text nodes in normal form:
text_nodes = tree.get_text_nodes()

3) for various usage
- tree implemented as an array of nodes (class Node), each node can be accessed through 
its index (tree[node_index]). 
- bad idea to iterate the tree as an array, since some nodes of the tree might be 
unlinked (not be a part of it after manipulations with tree)
- the right way to iterate the tree is to use iterate_DFS, that perform deep-first search iteration


"""


# -*- encoding: utf8 -*-
from urllib2 import urlopen, URLError
from copy import copy
from lxml import etree

__all__ = ['HTMLTextBlocksTree']


class HTMLTextBlocksTree(list):
    class BadEncoding(Exception):
        def __init__(self, value):
            self.value = value
        def __str__(self):
            return repr(self.value)
        
    class MarkZone:
        """information about inline elements, that covered text nodes"""        
        def __init__(self, start = 0, 
                     length = 0, 
                     tag = None, 
                     style_classes = None, 
                     link = None):
            self.start = start;
            self.length = length;
            self.tag = not tag is None and tag or "";
            self.style_classes = not style_classes is None and style_classes or []
            self.link = not link is None and link or "";    
    class Node:
        """implement HTMLTextBlocksTree node features"""
        def __init__(self, 
                     parent_index = -1, 
                     tag = None, 
                     style_classes = None, 
                     child_indices = None, 
                     text = None, 
                     mark_zones = None):
            self.parent_index = parent_index
            #block node properties
            self.tag = not tag is None and tag or ""
            self.style_classes = not style_classes is None and style_classes or []
            self.child_indices = not child_indices is None and child_indices or []
            #text node properties
            self.text = not text is None and text or ""   
            self.mark_zones = not mark_zones is None and mark_zones or []
            self.text_nodes_count = 0
    
    def __init__(self, text = None, filename = None, url = None):
        """ tree constructor
        
        Only one of three arguments should be specified:
        text -- build tree from html string
        filename -- build tree from html file
        url -- fetch html page with url and build tree
        """
        if text is None and not filename is None:
            text = open(filename).read()
        elif text is None and not url is None:
            try:
                request = urlopen(url)
                text = request.read()
                try:
                    encoding = request.headers['content-type'].split('charset=')[-1]
                    encoded = unicode(text, encoding)
                    text = encoded
                except:
                    pass
            except (ValueError, URLError) as error:
                #print error
                raise error
        if not text is None:
            self.__load(text, url)

    def __str__(self, node_index = 0, indent = 0):
        """convert tree to string
        
        node_index -- print subtree, root element with index nodex_index
        """
        if not len(self):
            return "<p>empty tree</p>"        
        if self[node_index].text:
            return "%s%s\n" % (indent * " ",
                               self[node_index].text.replace("\n", " "))
        elif self[node_index].tag:            
            out = "%s<%s>\n" % (indent * " ", self[node_index].tag)
            for child_index in self[node_index].child_indices:
                out +=  self.__str__(child_index, indent + 1)
            out += "%s</%s>\n" % (indent * " ", self[node_index].tag)    
            return out;
        return "";
    
    def substract_tree(self, tree):
        """ substract from self nodes that match with nodes in the tree  """
        self.__binary_operation(tree, substract = True)
    
    def cross_tree(self, tree):
        """ leave only nodes that match with nodes in the tree """
        self.__binary_operation(tree, cross = True)
    

    def iterate_DFS(self, node_index, actor):
        """deep-first search, performs tree iterating and run actor's method on each node
         
         actor have to be a function or an object with method "act" declared as:    
         def act(self, tree, node_index)
        """     
        if hasattr(actor, '__call__'):
            actor(self, node_index);
        else:
            actor.act(self, node_index)
        for child_index in self[node_index].child_indices:
            self.iterate_DFS(child_index, actor)

    def get_text_nodes(self):
        """get indexes of text nodes"""
        class TextBasket():
            def __init__(self, array):
                self.array = array
            def act(self, tree, node_index):
                if tree[node_index].text:
                    self.array += [node_index]
        text_elements = []
        self.iterate_DFS(0, TextBasket(text_elements))
        return text_elements
        
    def get_similar_sense_texts(self):
        """ get groups of text nodes with similar contexts, \
            therefore presumably with similar sense
        """
        text_elements = self.get_text_nodes()     
        text_elements = [(self.__get_node_depth(node_index), node_index) for node_index in text_elements]        
        text_elements.sort() # dont't match elements with different depth
        groups = []
        used = set();        
        matched_nodes = {}
        for index in xrange(len(text_elements)):
            depth, node_index = text_elements[index]
            if node_index in used:
                continue;
            fellows_by_matched_len = {}
            for compare_index in xrange(index + 1, len(text_elements)):
                cmp_depth, cmp_node_index = text_elements[compare_index]
                if cmp_depth != depth:
                    break; # dont't match elements with different depth
                if cmp_node_index in used:
                    continue                
                if self.__check_paths_equality(node_index, cmp_node_index, matched_nodes):
                    matched_len = self.__get_matched_path_len(node_index, 
                                                             cmp_node_index)
                    fellows_by_matched_len.setdefault(matched_len, []).append(cmp_node_index)
            if fellows_by_matched_len:
                fellows = [];
                for group in fellows_by_matched_len.values():
                    if len(group) > len(fellows):
                        fellows = group
                groups += [[node_index] + fellows]
                used = used | set(fellows)
        return groups

    """ private methods further """
    
    def __get_node_depth(self, node_index):
        """length of the node path"""
        depth = 1;
        while self[node_index].parent_index > -1:
            depth += 1;
            node_index = self[node_index].parent_index;
        return depth;
    
    def __build_path(self, node_index):
        """ all node's ancestors starting from root """
        path = [node_index];
        while self[node_index].parent_index > -1:
            path += [self[node_index].parent_index]
            node_index = self[node_index].parent_index
        path.reverse()
        return path
    
    def __check_connection(self, first_index, second_index):
        """ check if first_index and second_index elements are childs \
            of the same node and all siblings between them have same tag
            
            actually it checks if the first and the second are elements of list 
            of same type objects
        """
        siblings = self[self[first_index].parent_index].child_indices
        start = siblings.index(first_index) + 1
        end = siblings.index(second_index) + 1
        for index in xrange(start, end):            
            if not self.__check_tag_match(self[first_index], self[siblings[index]]):
                return False
        return True
    
    def __get_matched_path_len(self, first, second):
        """return length of unmatched part of paths"""
        first_path = self.__build_path(first)
        second_path = self.__build_path(second)
        common_len = 0
        for first_index, second_index in zip(first_path, second_path):
            if first_index == second_index:
                common_len += 1
            else:
                return len(first_path) - common_len
        return 0
    
    def __check_paths_equality(self, first, second, matched_nodes):
        """ check paths equality with respect to their context"""
        if not self.__check_tag_match(self[first], self[second]):
            return False
        first_path = self.__build_path(first)
        second_path = self.__build_path(second)
        if len(first_path) != len(second_path):
            return False
        equal = True
        for depth in xrange(1, len(first_path)):
            #common parents
            if first_path[depth] == second_path[depth]:
                continue;
            key = (min(first_path[depth], second_path[depth]), 
                   max(first_path[depth], second_path[depth]))
            if matched_nodes.has_key(key):
                equal = matched_nodes[key];
                if not equal:
                    break
                continue
            
            if first_path[depth - 1] == second_path[depth - 1]:
                #siblings, is it a range of same elements
                equal = self.__check_connection(first_path[depth], second_path[depth])
            else:
                first_siblings = self[first_path[depth - 1]].child_indices
                first_pos = first_siblings.index(first_path[depth])
                first_siblings_compare = first_siblings[max(0, first_pos - self.__CONTEXT_LENGTH) :
                                                        first_pos + self.__CONTEXT_LENGTH + 1]                
                second_siblings = self[second_path[depth - 1]].child_indices
                second_pos = second_siblings.index(second_path[depth])
                second_siblings_compare = second_siblings[max(0, second_pos - self.__CONTEXT_LENGTH) :
                                                        second_pos + self.__CONTEXT_LENGTH + 1]
                
                first_pos_in_compare = first_siblings_compare.index(first_path[depth])
                second_pos_in_compare = second_siblings_compare.index(second_path[depth])                             
                if (len(second_siblings_compare) != len(first_siblings_compare) or
                        first_pos_in_compare != second_pos_in_compare):
                    equal = False;
                else:
                    for first_sibling, second_sibling in zip(first_siblings_compare, 
                                                             second_siblings_compare):
                        if not self.__check_tag_match(self[first_sibling], 
                                                      self[second_sibling]):
                            equal = False
                            break
            if not equal:
                matched_nodes[key] = False
                break
        return equal

        
    #private methods
    
        
    def __binary_operation(self, tree, substract = False, cross = False):
        """ trees substraction or crossing """
        _, matching = self.__check_matching(tree, 0, 0)
        if substract:
            for node_index, texts_matched in matching:
                total_texts = self[node_index].text_nodes_count
                matched = float(texts_matched) / total_texts >= self.__MIN_PART_FOR_MATCH
                to_remove = substract and matched
                node = self[node_index]
                if to_remove and node.parent_index > -1:
                    self[node.parent_index].child_indices.remove(node_index)
        elif cross:
            matched_nodes = set([node_index for node_index, texts_matched in matching 
                                 if texts_matched])
            for node_index, node in enumerate(self):
                to_remove = not node_index in matched_nodes
                if (to_remove and node.parent_index > -1 and 
                        node_index in self[node.parent_index].child_indices):
                    self[node.parent_index].child_indices.remove(node_index)                
        self.__count_texts_in_nodes(0)
        self.__unlink_text_free_nodes()          
    
    def __check_tag_match(self, first_node, second_node):
        """ check if nodes' tags are same and style classes cross"""
        if first_node.tag != second_node.tag:
            return False;        
        #one node of two has one classId or both don't have classes
        if len(first_node.style_classes) + len(second_node.style_classes) < 2:
            return True
        have_style_cross = (set(first_node.style_classes) & set(second_node.style_classes) 
                            and True or False) 
        return have_style_cross;           
    
    def __check_matching(self, tree, node_index, tree_node_index):
        """ check if the subtree of self and the subtree of tree match  """
        self_node = self[node_index];
        tree_node = tree[tree_node_index];
        if self_node.text:
            matched = (tree_node.text and 
                       (self_node.text.startswith(tree_node.text) or
                        tree_node.text.startswith(self_node.text)));
            if matched:
                return (1, [(node_index, 1)]);
            else:
                return (0, [(node_index, 0)]);
        total_matched = 0
        sub_tree_matching = []
        self_childs = self_node.child_indices
        tree_childs = tree_node.child_indices
        start_pos = 0
        for child_index in self_childs:
            self_child = self[child_index]
            best_match_pos = -1
            best_matched = 0;
            best_matching = [];
            for tree_childs_pos in xrange(start_pos, len(tree_childs)):
                tree_child_index = tree_childs[tree_childs_pos]
                tree_child = tree[tree_child_index]
                if self.__check_tag_match(self_child, tree_child):
                    matched, matching = self.__check_matching(tree, 
                                                              child_index, 
                                                              tree_child_index)
                    if matched > best_matched:
                        best_match_pos = tree_childs_pos
                        best_matched = matched
                        best_matching = matching
            if best_match_pos > -1:
                start_pos = best_match_pos + 1
                total_matched += best_matched
                sub_tree_matching += best_matching
        return (total_matched, [(node_index, total_matched)] + sub_tree_matching)
    
    def __count_texts_in_nodes(self, node_index):
        """ count number of text nodes in node_index's subtree"""
        is_text = self[node_index].text and True or False
        if is_text:
            self[node_index].text_nodes_count = 1
        else:
            self[node_index].text_nodes_count = 0
            for child_index in self[node_index].child_indices:            
                self[node_index].text_nodes_count += self.__count_texts_in_nodes(child_index)
        return self[node_index].text_nodes_count        

 
    __CONTEXT_LENGTH = 2 #for paths matching
    __MIN_PART_FOR_MATCH = 0.9  #for subtree matching   
    __LINK_TAGS = ["a"]
    __LINK_ATTRIBUTES = ["href"]
    __TREE_ROOT_TAG = "root"   
    __LIBXML_HTML_PARSER = etree.HTMLParser()
    __TAGS_TO_SKIP = set(["script", "none", "meta", "link", "iframe", 
                       "style", "object", "noscript"])
    __INLINE_TAGS = set(["a", "abbr", "acronym", "b", "basefont", "bdo", "big", 
                         "br", "cite", "code", "dfn", "em", "font", "i", "img", 
                         "input", "kbd", "label", "q", "s", "samp", "select", 
                         "option", "small", "span", "strike", "strong", "sub", 
                         "sup", "textarea", "tt", "u", "var"]);
    __BLOCK_TAGS = set(["address", "applet", "blockquote", "body", "button", 
                        "center", "dd", "del", "dir", "div", "dl", "dt", 
                        "fieldset", "form", "frameset", "h1", "h2", "h3", "h4", 
                        "h5", "h6", "head", "hr", "html", "iframe", "ins", 
                        "isindex", "li", "link", "map", "menu", "meta", 
                        "noframes", "noscript", "object", "ol", "p", "pre", 
                        "script", "style", "table", "tbody", "td", "tfoot", 
                        "th", "thead", "title", "tr", "ul"]);    

    def __load(self, html_text, url = None):
        lxml_root = etree.fromstring(html_text, self.__LIBXML_HTML_PARSER)
        self.__reset()
        if not url is None:
            self.url = url;        
        root = HTMLTextBlocksTree.Node(tag = self.__TREE_ROOT_TAG)
        self.append(root)
        self.__translate_tree([lxml_root], 0)
        self.__count_texts_in_nodes(0)
        self.__unlink_text_free_nodes()

    def __reset(self):
        self[:] = []
        self.url = "";

    def __get_tag_name(self, lxml_node):        
        tag = (isinstance(lxml_node.tag, basestring) 
               and lxml_node.tag.lower() or "none")
        #remove annoying namespace
        tag = tag[0] == "{" and tag[tag.find("}") + 1 :] or tag;
        return tag;
    
    def __get_classes(self, lxml_node):
        """<tagname class="class1 class2 class3">...</tag>"""
        child_classes = lxml_node.get("class") or ""
        child_classes = ([name.strip() for name in 
                         child_classes.strip().split(" ") if name.strip()])
        return child_classes;
    
    def __get_link_url(self, lxml_node, node_tag):
        if not node_tag in self.__LINK_TAGS:
            return "";
        for link_attribute in self.__LINK_ATTRIBUTES:
            value = lxml_node.get(link_attribute) or "";
            if value:
                return value;
        return "";
   

    
    def __split_mark_zones(self, mark_zones, text_length):
        """ mark zones with defined borders stay with current text node
        others that are unfinished have to be distributed between the current text_node
        and those that follow    
        """
        for_following_usage = []
        for_node = []
        for zone in mark_zones:
            if zone.length == -1:
                zone_copy = copy(zone);
                zone_copy.start = 0;
                for_following_usage += [zone_copy];
                zone.length = text_length - zone.start;
            if zone.length: #don't use empty zones
                for_node += [zone];
        return (for_node, for_following_usage)
    
    def __translate_tree(self, lxml_nodes, parent_index, 
                         text_before = "", mark_zones = []):
        """ convert etree to THTMLTextBlocksTree"""     
        for lxml_node in lxml_nodes:
            if lxml_node is None:
                continue;
            tag = self.__get_tag_name(lxml_node)
            child_classes = self.__get_classes(lxml_node)
            # not wrapped text that occurs before child-nodes: 
            # <parent>text <child1>...</child1>...</parent>
            try:
                text = (isinstance(lxml_node.text, basestring) 
                        and lxml_node.text.strip() or "")
            except UnicodeDecodeError:
                raise self.BadEncoding("Wrong html encoding at %s" % (self.url));
            link = self.__get_link_url(lxml_node, tag)          
            is_block = tag in self.__BLOCK_TAGS
            to_skip = tag in self.__TAGS_TO_SKIP
            
            if text_before and (is_block or to_skip):
                for_node, for_followers = \
                        self.__split_mark_zones(mark_zones, len(text_before))
                child_node = self.Node(text = text_before, 
                                       parent_index = parent_index,
                                       mark_zones = for_node)
                self.append(child_node)
                self[parent_index].child_indices.append(len(self) - 1)
                text_before = ""
                mark_zones = for_followers;              
            if is_block and not to_skip:
                child_node = self.Node(tag = tag, 
                                       style_classes = child_classes,
                                       parent_index = parent_index)
                self.append(child_node)
                node_index = len(self) - 1
                self[parent_index].child_indices.append(node_index)
                text_left, mark_zones = self.__translate_tree(lxml_node, 
                                                                node_index, 
                                                                text, 
                                                                mark_zones)
                if text_left:
                    #make it a child of the block element
                    for_node, for_followers = self.__split_mark_zones(
                                                    mark_zones, len(text_before));                    
                    child_node = HTMLTextBlocksTree.Node(text = text_left, 
                                            parent_index = node_index,
                                            mark_zones = for_node)
                    self.append(child_node)
                    self[node_index].child_indices.append(len(self) - 1)
                    mark_zones = for_followers                      
            elif not to_skip: 
                #inline node, features of which we distribute in mark_zones
                mark_add = ([HTMLTextBlocksTree.MarkZone(
                                                start = len(text_before),
                                                length = -1,
                                                tag = tag, 
                                                style_classes = child_classes, 
                                                link = link)])
                add_len = len(mark_add)
                text_before = " ".join([text_before, text]).strip();
                text_before, subtree_mark_zones = self.__translate_tree(lxml_node, 
                                                    parent_index, 
                                                    text_before, 
                                                    mark_zones + mark_add)
                # close the zones, which were created by this node
                for zone_index in xrange(len(subtree_mark_zones) - 1, -1, -1):
                    if subtree_mark_zones[zone_index].length == -1:
                        subtree_mark_zones[zone_index].length = (len(text_before) -
                                   subtree_mark_zones[zone_index].start);
                        add_len -= 1;
                        if not add_len:
                            break;
                if add_len:
                    break;
                mark_zones = subtree_mark_zones;                   
            # not wrapped text that occurs after child-node: 
            # <parent><child1>...</child1> text_after ... </parent>   
            try:
                text_after = (isinstance(lxml_node.tail, basestring) 
                              and lxml_node.tail.strip() or "");
            except UnicodeDecodeError:
                raise self.BadEncoding("Wrong html encoding at %s" % (self.url));
            text_before = " ".join([text_before, text_after]).strip();
        return (text_before, mark_zones);
    
    def __unlink_text_free_nodes(self):
        """ unlink all subtrees without text nodes """
        for node_index, node in enumerate(self):
            if (node.parent_index > -1 and 
                    node_index in self[node.parent_index].child_indices and 
                    not node.text_nodes_count):
                self[node.parent_index].child_indices.remove(node_index)  




