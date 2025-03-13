# XML Preprocessor
# © Gondwana Software 2024+.
# Returns 0 on success.

xmlpp_DEBUG = False

class xmlpp_error(Exception):   # custom Exception class
    def __init__(self, xmlpp_message, xmlpp_el = None):
        print(f"❌ Preprocessor error: {xmlpp_message}")
        if xmlpp_el is not None: print(f"   Reported line number in source file: {xmlpp_el.sourceline}")
        if xmlpp_DEBUG:
            xmlpp_debug_file.close()
            print("   Log is in debug-pp.txt")

            try: xmlpp_tree
            except NameError: pass
            else:
                print("   State of XML at time of error is in debug-pp.xml")
                if xmlpp_el is not None:
                    xmlpp_el.set("xmlpp-error", xmlpp_message)
                    print("   The relevant element has attribute 'xmlpp-error' in debug-pp.xml")
                xmlpp_tree.write('debug-pp.xml')
                if xmlpp_el is not None:    # read debug-pp.xml to find line number of error
                    xmlpp_parser = xmlpp_ET.XMLParser(remove_comments=True)
                    xmlpp_error_tree = xmlpp_ET.parse('debug-pp.xml', xmlpp_parser)
                    xmlpp_error_el = xmlpp_error_tree.xpath('//*[@xmlpp-error][1]')
                    print(f"   Reported line number in debug-pp.xml: {xmlpp_error_el[0].sourceline}")
        else:
            print("   For more info, run preprocessor with -d argument.")
        exit(1)

import subprocess

def xmlpp_check_modules():
    xmlpp_lxml_spec = importlib.util.find_spec('lxml')
    if xmlpp_lxml_spec is not None: return      # lxml is already installed
    print("The Python's lxml module is not installed; attempting to install it...")
    try:
        subprocess.check_call(['pip', 'install', 'lxml'])
    except Exception as e:
        raise xmlpp_error(f"Couldn't install lxml: {type(e).__name__} {sys.exception()}\n   Install lxml manually with 'pip install lxml'.")

import copy
import importlib.util
import os
import re
import sys
xmlpp_check_modules()
from lxml import etree as xmlpp_ET
from xml.sax.saxutils import unescape

xmlpp_debug_file = None
xmlpp_source_file = xmlpp_dest_file = None
xmlpp_symbols = {}  # associative array (disctionary) of <Symbol> elements, indexed by [id]

def xmlpp_insert(xmlpp_dest, xmlpp_index, xmlpp_source, xmlpp_children_only=False):
    """ Insert source into dest at index. If source.tag=="Dummy" or xmlpp_children_only, insert children only.
        Returns index of element after insertion(s). """
    if xmlpp_children_only or xmlpp_source.tag == "Dummy":
        for xmlpp_child_el in xmlpp_source:    # insert children
            #print("inserting "+xmlpp_child_el.tag)
            xmlpp_dest.insert(xmlpp_index, xmlpp_child_el)
            xmlpp_index += 1
    else:
        xmlpp_dest.insert(xmlpp_index, xmlpp_source)
        xmlpp_index += 1
    return xmlpp_index

def xmlpp_parse_args():     # parse command-line arguments
    global xmlpp_debug_file

    xmlpp_OVERWRITE = False
    xmlpp_USAGE_ERROR = False
    global xmlpp_source_file, xmlpp_dest_file, xmlpp_DEBUG
    for xmlpp_i, xmlpp_arg in enumerate(sys.argv[1:], start=1):
        if xmlpp_arg == "-d": xmlpp_DEBUG = True
        elif xmlpp_arg == "-y": xmlpp_OVERWRITE = True
        elif xmlpp_arg[0] == '-': xmlpp_USAGE_ERROR = True
        elif xmlpp_source_file is not None: xmlpp_dest_file = xmlpp_arg
        else: xmlpp_source_file = xmlpp_arg

    if xmlpp_DEBUG: xmlpp_debug_file = open('debug-pp.txt', 'w')

    if xmlpp_source_file is None or xmlpp_dest_file is None or xmlpp_USAGE_ERROR:
        print("XML Preprocessor 2.0.0")
        print("Usage: preprocess.py sourceFile destinationFile [-d] [-y]")
        print("   -d prints debugging info")
        print("   -y overwrites destinationFile")
        exit(1)

    if not os.path.exists(xmlpp_source_file):
        raise xmlpp_error("can't find "+xmlpp_source_file)

    if os.path.exists(xmlpp_dest_file) and not xmlpp_OVERWRITE:
        xmlpp_overwrite_input = input("Destination file already exists; overwrite it (y/n)? ")
        if (xmlpp_overwrite_input != "y"): exit(2)

def xmlpp_load_source(xmlpp_source):
    # Read source and return tree.

    def xmlpp_load_tree(xmlpp_source):
        # Read source, and recursively splice in <Import> files.
        # Returns tree.

        def xmlpp_process_imports(xmlpp_element, xmlpp_source):
            """Process all Import elements under the given element."""
            xmlpp_index = 0
            while xmlpp_index < len(xmlpp_element):
                xmlpp_child_el = xmlpp_element[xmlpp_index]
                if xmlpp_child_el.tag == "Import":
                    xmlpp_href = xmlpp_child_el.get('href')
                    if xmlpp_DEBUG: print(f"      Found <Import href=\"{xmlpp_href}\" />", file=xmlpp_debug_file)
                    xmlpp_include_path = os.path.join(os.path.dirname(xmlpp_source), xmlpp_href)    # assume href is relative to source
                    if not os.path.exists(xmlpp_include_path):
                        raise xmlpp_error(f"Can't find \"{xmlpp_href}\" imported by \"{xmlpp_source}\".", xmlpp_child_el)
                    xmlpp_element.remove(xmlpp_child_el)    # remove <Import>
                    if xmlpp_href.lower().endswith('.py'):
                        xmlpp_el = xmlpp_ET.Element('Define')
                        with open(xmlpp_include_path, 'r') as xmlpp_file:
                            xmlpp_el.text = f"\n{xmlpp_file.read()}\n"  # \n so as not to interfere with python indentation
                        xmlpp_element.insert(xmlpp_index, xmlpp_el)
                    else:   # assume .xml
                        xmlpp_child_tree = xmlpp_load_tree(xmlpp_include_path)
                        xmlpp_child_root = xmlpp_child_tree.getroot()
                        xmlpp_insert(xmlpp_element, xmlpp_index, xmlpp_child_root)
                else:
                    # Recursively process imports in child elements
                    xmlpp_process_imports(xmlpp_child_el, xmlpp_source)
                xmlpp_index += 1

        if xmlpp_DEBUG: print(f"   Loading \"{xmlpp_source}\"", file=xmlpp_debug_file)
        try:
            xmlpp_parser = xmlpp_ET.XMLParser(remove_comments=True)
            xmlpp_tree = xmlpp_ET.parse(xmlpp_source, xmlpp_parser)
        except Exception as e:
            raise xmlpp_error(f"{type(e).__name__} in \"{xmlpp_source}\": {sys.exception()}")

        xmlpp_root = xmlpp_tree.getroot()

        # Process imports throughout the entire tree
        xmlpp_process_imports(xmlpp_root, xmlpp_source)

        #xmlpp_dump_el(xmlpp_root,"root")
        return xmlpp_tree

    if xmlpp_DEBUG: print(f"Phase 1: loading source file(s)...", file=xmlpp_debug_file)
    return xmlpp_load_tree(xmlpp_source)

def xmlpp_dump_el(xmlpp_el, xmlpp_el_name, xmlpp_indent=0):     # used with xmlpp_DEBUG
    def xmlpp_dump_recurse(xmlpp_el, xmlpp_indent=0):
        for xmlpp_child_el in xmlpp_el:
            print(f"{' '*xmlpp_indent}{xmlpp_child_el.tag}", file=xmlpp_debug_file)
            xmlpp_dump_recurse(xmlpp_child_el, xmlpp_indent+3)

    print(f"{' '*xmlpp_indent}Dump of {xmlpp_el_name}:", file=xmlpp_debug_file)
    xmlpp_dump_recurse(xmlpp_el,  xmlpp_indent+3)
    #for xmlpp_child_el in xmlpp_el:
    #    print(f"   {xmlpp_child_el.tag}")

def xmlpp_extract_symbols():    # put all <Symbol> elements in xmlpp_symbol_els[] and delete them from tree
    global xmlpp_symbols

    if (xmlpp_DEBUG): print("\nPhase 2: extracting <Symbols>...", file=xmlpp_debug_file)

    xmlpp_symbol_els = []
    for xmlpp_symbol_el in xmlpp_root.iter('Symbol'):
        #print("symbol tag="+xmlpp_el.tag)
        if "id" not in xmlpp_symbol_el.attrib: raise xmlpp_error("<Symbol> is missing 'id' attribute", xmlpp_symbol_el)
        xmlpp_symbol_id = xmlpp_symbol_el.attrib['id']
        if xmlpp_DEBUG:
            print(f"   <Symbol id={xmlpp_symbol_id}>", file=xmlpp_debug_file)
            xmlpp_dump_el(xmlpp_symbol_el,"xmlpp_symbol_el", 6)
        xmlpp_symbols[xmlpp_symbol_id] = xmlpp_symbol_el
        xmlpp_symbol_els.append(xmlpp_symbol_el)    # to delete from root

    for xmlpp_el in xmlpp_symbol_els:
        xmlpp_parent = xmlpp_el.getparent()
        if xmlpp_parent is None: raise xmlpp_error("Can't remove a <Symbol> because it is the root element", xmlpp_parent)
        xmlpp_parent.remove(xmlpp_el)

def xmlpp_replace_all_uses(): # replace all <Use> elements
    if (xmlpp_DEBUG): print("\nPhase 3: replacing <Use>s with <Symbol>s...", file=xmlpp_debug_file)

    def xmlpp_replace_use(xmlpp_el):
        # Recursive.
        xmlpp_index = 0
        while xmlpp_index < len(xmlpp_el):
            xmlpp_child_el = xmlpp_el[xmlpp_index]
            if xmlpp_child_el.tag == "Use":
                xmlpp_href = xmlpp_child_el.get("href")
                if xmlpp_href[0] == '#': xmlpp_href = xmlpp_href[1:]     # [1:] strips # from href
                if xmlpp_DEBUG: print(f'   Replacing <Use href="#{xmlpp_href}">', file=xmlpp_debug_file)
                if xmlpp_href not in xmlpp_symbols: raise xmlpp_error(f"Can't find <Symbol id=\"{xmlpp_href}\" />", xmlpp_child_el)
                xmlpp_symbol = xmlpp_symbols[xmlpp_href]
                xmlpp_delete_list = xmlpp_child_el.findall("Delete")
                xmlpp_transform_list = xmlpp_child_el.findall("Transform")
                #print(len(xmlpp_transform_list))

                # Remove <Use> el and any <Transform>s and <Delete>s within it:
                xmlpp_el.remove(xmlpp_child_el)

                # Clone <Symbol> so <Transform>s don't affect original <Symbol> or subsequent <Use>s:
                xmlpp_symbol_copy = copy.deepcopy(xmlpp_symbol)
                if xmlpp_DEBUG: xmlpp_dump_el(xmlpp_symbol_copy, "xmlpp_symbol_copy", 6)

                # Apply attributes specified in <Use> to all top-level elements in copy:
                #print(xmlpp_el.attrib)
                for xmlpp_symbol_el in xmlpp_symbol_copy:
                    for xmlpp_attrib_name, xmlpp_attrib_value in xmlpp_child_el.attrib.items():
                        if xmlpp_attrib_name != "href":
                            if xmlpp_DEBUG: print(f'      Setting attribute "{xmlpp_attrib_name}" on <{xmlpp_symbol_el.tag}>', file=xmlpp_debug_file)
                            xmlpp_symbol_el.set(xmlpp_attrib_name, xmlpp_attrib_value)

                # recurse, just in case <Symbol> contains nested <Use>s:
                xmlpp_replace_use(xmlpp_symbol_copy)

                # Apply any <Delete> elements:
                if xmlpp_delete_list:
                    for xmlpp_delete in xmlpp_delete_list:
                        if xmlpp_DEBUG: print(f'      Applying <Delete href="{xmlpp_delete.attrib["href"]}">', file=xmlpp_debug_file)
                        xmlpp_delete_els = xmlpp_symbol_copy.findall(xmlpp_delete.attrib["href"])
                        if len(xmlpp_delete_els) == 0:
                            raise xmlpp_error(f'Can\'t find any element to <Delete> with href="{xmlpp_delete.attrib["href"]}"')
                        for xmlpp_delete_el in xmlpp_delete_els:
                            xmlpp_parent = xmlpp_symbol_copy.find(xmlpp_delete.attrib["href"]+"/..")
                            xmlpp_parent.remove(xmlpp_delete_el)
                            if xmlpp_DEBUG: print("         Deleted an element", file=xmlpp_debug_file)

                # Apply any <Transform> elements:
                if xmlpp_transform_list:
                    for xmlpp_transform in xmlpp_transform_list:
                        if xmlpp_DEBUG:
                            print(f'      Applying <Transform href="{xmlpp_transform.attrib["href"]}" target="{xmlpp_transform.attrib["target"]}"...>', file=xmlpp_debug_file)
                        try:
                            xmlpp_transform_els = xmlpp_symbol_copy.findall(xmlpp_transform.attrib["href"])
                        except Exception as e:
                            raise xmlpp_error(f"{type(e).__name__} applying <Transform href=\"{xmlpp_transform.attrib['href']}\"...: {sys.exception()}. href may be invalid.")

                        if len(xmlpp_transform_els) == 0:
                            raise xmlpp_error(f'Can\'t find any element to <Transform> with href="{xmlpp_transform.attrib["href"]}"')
                        for xmlpp_transform_el in xmlpp_transform_els:
                            xmlpp_transform_el.set(xmlpp_transform.attrib["target"], xmlpp_transform.attrib["value"])
                            if xmlpp_DEBUG: print("         Transformed an element", file=xmlpp_debug_file)

                # Insert copy of <Symbol>, potentially modified by <Transform>s, into tree:
                xmlpp_index = xmlpp_insert(xmlpp_el, xmlpp_index, xmlpp_symbol_copy, True)
            else:   # Not <Use>
                xmlpp_replace_use(xmlpp_child_el)   # recurse
                xmlpp_index += 1

    xmlpp_replace_use(xmlpp_root)

def xmlpp_expand_all_repeats(): # expand all <Repeat> elements
    if (xmlpp_DEBUG): print("\nPhase 4: expanding <Repeat> elements...", file=xmlpp_debug_file)

    def xmlpp_expand_repeats(xmlpp_el):
        def xmlpp_insert_repeat(xmlpp_parent_el, xmlpp_repeat_els, xmlpp_index, xmlpp_for_var, xmlpp_for_val):
            # Returns final value of xmlpp_index.
            xmlpp_define_el = xmlpp_ET.Element('Define')
            xmlpp_define_el.text = f"{xmlpp_for_var}={xmlpp_for_val}"   # eg, "i=0"
            #print(f"inserting Define at {xmlpp_index}")
            xmlpp_parent_el.insert(xmlpp_index, xmlpp_define_el)
            xmlpp_index += 1
            # Insert xmlpp_repeat_els:
            for xmlpp_child_el in xmlpp_repeat_els:
                #print(f"inserting content at {xmlpp_index}")
                xmlpp_parent_el.insert(xmlpp_index, copy.deepcopy(xmlpp_child_el))  # deepcopy because lxml el can only have one parent
                xmlpp_index += 1
            return xmlpp_index

        xmlpp_index = 0
        while xmlpp_index < len(xmlpp_el):
            xmlpp_child_el = xmlpp_el[xmlpp_index]
            # print(xmlpp_child_el.tag)
            if xmlpp_child_el.tag == "Repeat":
                if "for" not in xmlpp_child_el.attrib: xmlpp_error("<Repeat> missing 'for' attribute.")
                xmlpp_for = xmlpp_child_el.attrib["for"]
                if "in" not in xmlpp_child_el.attrib: xmlpp_error("<Repeat> missing 'in' attribute.")
                xmlpp_in = xmlpp_child_el.attrib["in"]
                if (xmlpp_DEBUG): print(f'   Expanding <Repeat for="{xmlpp_for}" in="{xmlpp_in}">', file=xmlpp_debug_file)
                xmlpp_repeat_els = []
                for xmlpp_repeat_el in xmlpp_child_el:  # make deep copy of each xmlpp_child_el because lxml wants each el to have its own parent
                    xmlpp_repeat_els.append(copy.deepcopy(xmlpp_repeat_el))
                xmlpp_el.remove(xmlpp_child_el)     # remove the <Repeat> element itself
                # construct a string that contains the code to be executed in order to create the required number of copies:
                xmlpp_repeat_code = f'for {xmlpp_for} in {xmlpp_in}: xmlpp_index = xmlpp_insert_repeat(xmlpp_el, xmlpp_repeat_els, xmlpp_index, "{xmlpp_for}", {xmlpp_for})'
                #print(f"before exec: {xmlpp_index}")
                exec(xmlpp_repeat_code, globals(), locals())
                #print(f"after exec: {xmlpp_index}")
                xmlpp_index += 1    # skip over the <Define>, but process the newly-copied elements in case they contain nested <Repeat>s
            else:   # xmlpp_child_el is not <Repeat>
                xmlpp_expand_repeats(xmlpp_child_el)    # recurse
                xmlpp_index += 1

    xmlpp_expand_repeats(xmlpp_root)

def xmlpp_do_defines_and_expressions(): # execute <Define>s and replace all {expression}s with their results
    if (xmlpp_DEBUG): print("\nPhase 5: processing <Define>s and {expression}s...", file=xmlpp_debug_file)

    def xmlpp_exec_definitions(xmlpp_text, xmlpp_el):
        def xmlpp_find_indent_size(xmlpp_firstLine):
            for xmlpp_index, xmlpp_char in enumerate(xmlpp_firstLine):
                if xmlpp_char != ' ':
                    return xmlpp_index
            return -1   # all characters are spaces

        # Remove first line (text following <Define>):
        xmlpp_firstEOLindex = xmlpp_text.find('\n')
        if xmlpp_firstEOLindex != -1:
            xmlpp_text = xmlpp_text[xmlpp_firstEOLindex+1:]
        if not xmlpp_text.isspace():
            xmlpp_lines = xmlpp_text.split('\n')
            xmlpp_indent_size = xmlpp_find_indent_size(xmlpp_lines[0])
            xmlpp_processed_lines = []
            for xmlpp_line in xmlpp_lines:
                xmlpp_processed_line = xmlpp_line[xmlpp_indent_size:] if xmlpp_line.startswith(' ' * xmlpp_indent_size) else xmlpp_line.lstrip()
                xmlpp_processed_lines.append(xmlpp_processed_line)
            xmlpp_text = '\n'.join(xmlpp_processed_lines)
            #print("Indent size: ",xmlpp_indent_size)
            #print("Before strip:\n\""+el.text+"\"")
            #print("After strip:\n\""+xmlpp_text+"\"\n")
            if xmlpp_DEBUG: print("\n".join(["   <Define>: executing " + line for line in xmlpp_text.split("\n")]), file=xmlpp_debug_file)
            try:
                exec(xmlpp_text, globals())
            except Exception as e:
                raise xmlpp_error(f"{type(e).__name__} executing code in <Define>: {sys.exception()}", xmlpp_el)

    def xmlpp_evalStringWithExpressions(xmlpp_el, xmlpp_s, xmlpp_attrib_name=None):
        # If the string is an expression that returns an XML Element, the Element is returned.
        # Otherwise, returns string with expressions replaced by values, or False if no expressions found.

        def xmlpp_eval_parent(xmlpp_el, xmlpp_exp, xmlpp_attrib_name):
            # Returns arg with PARENT.attrib replaced by value of attrib in parent element.
            # If .attrib isn't specified, uses xmlpp_attrib_name.

            def xmlpp_eval_parent_terms(xmlpp_exp, xmlpp_regexp, xmlpp_attrib_name=None):
                def xmlpp_eval_parent_attrib(xmlpp_el, xmlpp_parent_attrib):
                    # Recurses; returns None if no ancestor has a value for xmlpp_parent_attrib.
                    if xmlpp_DEBUG: print(f'      Looking for <{xmlpp_el.tag} {xmlpp_parent_attrib}="...">', file=xmlpp_debug_file)
                    xmlpp_parent_el = xmlpp_el.getparent()
                    if xmlpp_parent_el is None: return None
                    xmlpp_parent_value = xmlpp_parent_el.get(xmlpp_parent_attrib)
                    if xmlpp_parent_value != None:
                        return xmlpp_parent_value
                    else:
                        return xmlpp_eval_parent_attrib(xmlpp_parent_el, xmlpp_parent_attrib)   # recurse

                # Returns string with PARENT terms replaced.
                xmlpp_matches = re.split(xmlpp_regexp, xmlpp_exp)
                #print(xmlpp_exp,xmlpp_matches)
                # Process all odd-numbered matches[]:
                for xmlpp_matchIndex in range(1, len(xmlpp_matches), 2):
                    xmlpp_parent_attrib = xmlpp_attrib_name if xmlpp_attrib_name else xmlpp_matches[xmlpp_matchIndex].split('.')[1]
                    #print(xmlpp_parent_attrib)
                    xmlpp_attrib_value = xmlpp_eval_parent_attrib(xmlpp_el, xmlpp_parent_attrib)
                    if xmlpp_attrib_value == None:
                        raise xmlpp_error('Can\'t find any PARENT of {0} with attribute named "{1}"'.format(xmlpp_el.tag, xmlpp_parent_attrib), xmlpp_el)
                    xmlpp_matches[xmlpp_matchIndex] = xmlpp_attrib_value
                return "".join(xmlpp_matches)

            # Process PARENT.attribName terms:
            xmlpp_exp = xmlpp_eval_parent_terms(xmlpp_exp, r'(PARENT\.[a-zA-Z-]+)')

            # Process PARENT (without attribName) terms:
            xmlpp_exp = xmlpp_eval_parent_terms(xmlpp_exp, r'(PARENT)', xmlpp_attrib_name)

            # Process SELF.attribName terms:
            #print('processing SELF...')
            xmlpp_matches = re.split(r'(SELF\.[a-zA-Z-]+)', xmlpp_exp)
            #print(xmlpp_exp,xmlpp_matches)
            # Process all odd-numbered matches[]:
            for xmlpp_matchIndex in range(1, len(xmlpp_matches), 2):
                xmlpp_self_attrib = xmlpp_matches[xmlpp_matchIndex].split('.')[1]
                xmlpp_attrib_value = xmlpp_el.get(xmlpp_self_attrib)
                if xmlpp_attrib_value == None:
                    raise xmlpp_error('Can\'t find {0} SELF attribute named "{1}"'.format(xmlpp_el.tag, xmlpp_self_attrib), xmlpp_el)
                #print(f"   {xmlpp_self_attrib}={xmlpp_attrib_value}")
                xmlpp_matches[xmlpp_matchIndex] = xmlpp_attrib_value
            xmlpp_exp = "".join(xmlpp_matches)
            #print(f'done: {xmlpp_exp}')

            return xmlpp_exp

        xmlpp_matches = re.split(r'(\{.*?\})', xmlpp_s)     # TODO 3.9 doesn't work if {} has \n
        if (len(xmlpp_matches) <= 1):
            return False    # no {}
        if (xmlpp_DEBUG): print(f'   Evaluating: <{xmlpp_el.tag} {xmlpp_attrib_name}="{xmlpp_s}">', file=xmlpp_debug_file)
        # Process all odd-numbered matches[]:
        for xmlpp_matchIndex in range(1, len(xmlpp_matches), 2):
            xmlpp_exp = xmlpp_matches[xmlpp_matchIndex][1:-1]   # [1:-1] strips { }
            xmlpp_exp = xmlpp_eval_parent(xmlpp_el, xmlpp_exp, xmlpp_attrib_name)
            if xmlpp_exp == "":
                xmlpp_result = ""
            else:
                try:
                    xmlpp_result = eval(xmlpp_exp)
                except Exception as e:
                    raise xmlpp_error(f"{type(e).__name__} evaluating {{{xmlpp_exp}}}: {sys.exception()}", xmlpp_el)
            if type(xmlpp_result) == type(xmlpp_root):  # string evaluates to an XML Element
                if len(xmlpp_matches) != 3: raise xmlpp_error(f"evaluating \"{xmlpp_s}\": more than one {{expression}} in string when first {{expression}} returns XML.", xmlpp_el)
                if xmlpp_matches[0] != "" or xmlpp_matches[2] != "": raise xmlpp_error(f"evaluating \"{xmlpp_s}\": an {{expression}} that returns XML must be the only content in the string.", xmlpp_el)
                return xmlpp_result
            if '{' in str(xmlpp_result): raise xmlpp_error(f"evaluated expression {xmlpp_exp} seems to contain another expression", xmlpp_el)
            #print(exp,str(result))
            xmlpp_matches[xmlpp_matchIndex] = str(xmlpp_result)
        xmlpp_matches = "".join(xmlpp_matches)
        if xmlpp_DEBUG: print(f'      Result: <{xmlpp_el.tag} {xmlpp_attrib_name}="{xmlpp_matches}"', file=xmlpp_debug_file)
        return xmlpp_matches

    xmlpp_define_els = []   # <Define> elements to delete
    for xmlpp_el in xmlpp_root.iter():
        # print("tag="+xmlpp_el.tag)
        # If element is <Define>, execute its content:
        if xmlpp_el.tag == 'Define':
            if (xmlpp_el.text): xmlpp_exec_definitions(xmlpp_el.text, xmlpp_el)
            if (xmlpp_el.tail): xmlpp_exec_definitions(xmlpp_el.tail, xmlpp_el)       # TODO 3.9 is this sensible?
            xmlpp_define_els.append(xmlpp_el)
            continue
        # Element isn't <Define>, so...
        # Evaluate {expression}s in element's text:
        if xmlpp_el.text:
            xmlpp_text = xmlpp_el.text.strip()
            if (xmlpp_text):
                # print("   tag with text: "+xmlpp_el.tag)
                xmlpp_processedText = xmlpp_evalStringWithExpressions(xmlpp_el, xmlpp_text)
                if xmlpp_processedText is not False:
                    #print("\txmlpp_processedText=\""+xmlpp_processedText+"\"")
                    if isinstance(xmlpp_processedText, str):
                        xmlpp_el.text = xmlpp_processedText
                    else:   # insert XML elements
                        xmlpp_el.text = ""
                        xmlpp_insert(xmlpp_el, 0, xmlpp_processedText)
        # Evaluate {expression}s in element's tail:
        if xmlpp_el.tail:
            xmlpp_tail = xmlpp_el.tail.strip()
            if (xmlpp_tail):
                #print("   tag with tail: "+xmlpp_el.tag)
                xmlpp_processedText = xmlpp_evalStringWithExpressions(xmlpp_el, xmlpp_tail) # may be string, XML or False
                if xmlpp_processedText is not False:
                    if isinstance(xmlpp_processedText, str):
                        #print("\txmlpp_processedText=\""+xmlpp_processedText+"\"")
                        xmlpp_el.tail = xmlpp_processedText
                    else:   # insert XML elements
                        xmlpp_el.tail = ""
                        xmlpp_parent = xmlpp_el.getparent()
                        xmlpp_index = list(xmlpp_parent).index(xmlpp_el) + 1
                        xmlpp_insert(xmlpp_parent, xmlpp_index, xmlpp_processedText)
        # Evaluate {expression}s in element's attributes:
        xmlpp_keys = xmlpp_el.keys()
        # print("   keys=",xmlpp_keys)
        for xmlpp_key in xmlpp_keys:
            xmlpp_value = xmlpp_el.get(xmlpp_key)
            xmlpp_processedValue = xmlpp_evalStringWithExpressions(xmlpp_el, xmlpp_value, xmlpp_key)
            if xmlpp_processedValue != False:
                #print(f"   {xmlpp_key}")
                xmlpp_el.set(xmlpp_key, xmlpp_processedValue)
    # Delete all <Define> elements:
    for xmlpp_el in xmlpp_define_els:
        xmlpp_parent = xmlpp_el.getparent()
        if xmlpp_parent is None: raise xmlpp_error("Can't remove a <Define> because it is the root element", xmlpp_el)
        xmlpp_parent.remove(xmlpp_el)

def xmlpp_remove_data_attributes():
    if (xmlpp_DEBUG): print("\nPhase 6: removing data- attributes...", file=xmlpp_debug_file)
    for xmlpp_el in xmlpp_root.iter():
        for xmlpp_attrib_name in xmlpp_el.keys():
            if xmlpp_attrib_name.startswith("data-"):
                xmlpp_el.attrib.pop(xmlpp_attrib_name, None)

def xmlpp_write_dest(xmlpp_dest_file):
    if xmlpp_DEBUG: print(f"\nPhase 7: writing {xmlpp_dest_file}...", file=xmlpp_debug_file)
    xmlpp_tree.write(xmlpp_dest_file)
    if xmlpp_DEBUG: print(f"\nFinished: no preprocessor errors found.", file=xmlpp_debug_file)

def pp_log(xmlpp_arg, xmlpp_prompt="pp_log arg:"):
    # Console logging function callable from watchface-pp.xml functions and {expression}s.
    #    xmlpp_arg: value to print
    #    xmlpp_prompt: optional string to print before arg.
    # Returns xmlpp_arg.
    print(f"{xmlpp_prompt} value is '{xmlpp_arg}'; type is {type(xmlpp_arg)}")
    return xmlpp_arg

xmlpp_parse_args()
xmlpp_tree = xmlpp_load_source(xmlpp_source_file)
xmlpp_root = xmlpp_tree.getroot()
xmlpp_extract_symbols()
xmlpp_replace_all_uses()
xmlpp_expand_all_repeats()
xmlpp_do_defines_and_expressions()
xmlpp_remove_data_attributes()
xmlpp_write_dest(xmlpp_dest_file)

if xmlpp_DEBUG: xmlpp_debug_file.close()