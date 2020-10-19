import ast
from ast import *
from astunparse import unparse
from ast import Assign
from utils import *

class AssignmentVisitor(ast.NodeVisitor):
    def __init__(self, apiname):
        self.api_only_name = apiname
        self.assignment_dictionary = {}

    def visit_Assign(self, node: Assign):
        # need to process if they are Subscript or just regular name
        assignment_value = node.value
        # only need to replace if the value is a call
        if (isinstance(assignment_value, Call) or isinstance(assignment_value, Attribute) or isinstance(
                assignment_value, Name)) and isinstance(node.targets[0], Name):
            assignment_target = node.targets[0].id

            # print(assignment_target)
            # print(unparse(assignment_value))
            api_name, api_keywords = separate_api_parameter(assignment_value)
            if not self.api_only_name in api_name:
                dict_content = {}
                dict_content["name"] = api_name
                dict_content["key"] = api_keywords
                dict_content["line_no"] = node.lineno
                self.assignment_dictionary[assignment_target] = []
                self.assignment_dictionary[assignment_target].append(dict_content)

class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.import_dictionary = {}

    def visit_Import(self, node):
        import_path = node.names[0].name
        import_alias = node.names[0].asname
        if import_alias is not None:
            self.import_dictionary[import_alias] = import_path

class FromImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.from_import_dict = {}

    def visit_ImportFrom(self, node: ImportFrom):

        module_name = node.module
        imported_name = node.names[0].name
        imported_alias = node.names[0].asname
        if module_name is not None:
            full_path = module_name + "." + imported_name
            if imported_alias is not None:
                self.from_import_dict[imported_alias] = full_path
            else:
                self.from_import_dict[imported_name] = full_path

class ApiFormatterVisitor(ast.NodeVisitor):
    def __init__(self, import_dict, from_import_dict, assign_dict, api_name):
        self.imp_dict = import_dict
        self.from_dict = from_import_dict
        self.ass_dict = assign_dict
        self.return_list = []
        self.api_only_name = api_name

    def visit_Call(self, node: Call):
        has_assignment_change = False
        api_name, keywords = separate_api_parameter(node)
        name_split = api_name.split(".")
        outermost_name = name_split[0]
        hasChange = True
        loop_flag = 0
        while hasChange:
            loop_flag += 1
            if loop_flag > 20:
                hasChange = False
            # first check assignment
            original_form = outermost_name
            if outermost_name in self.ass_dict:
                node_lineno = node.lineno
                # get the correct assignment
                previous_element = self.ass_dict[outermost_name][0]
                for element in self.ass_dict[outermost_name]:
                    element_lineno = element["line_no"]
                    if element_lineno < node_lineno:
                        previous_element = element
                    else:
                        break
                # Use the previous element value to replace the node name
                splitted = previous_element["name"].split(".")
                name_split.pop(0)
                # insert from the end to the beginning
                for item in reversed(splitted):
                    name_split.insert(0, item)
                outermost_name = name_split[0]
                if has_assignment_change:
                    has_multitude_change = True
                has_assignment_change = True
            elif outermost_name in self.from_dict:
                previous_element = self.from_dict[outermost_name]
                splitted = previous_element.split(".")
                name_split.pop(0)
                # insert from the end to the beginning
                for item in reversed(splitted):
                    name_split.insert(0, item)
                outermost_name = name_split[0]
                if has_assignment_change:
                    has_multitude_change = True
            elif outermost_name in self.imp_dict:
                previous_element = self.imp_dict[outermost_name]
                splitted = previous_element.split(".")
                name_split.pop(0)
                # insert from the end to the beginning
                for item in reversed(splitted):
                    name_split.insert(0, item)
                outermost_name = name_split[0]
                if has_assignment_change:
                    has_multitude_change = True
            else:
                hasChange = False
            # To make sure that there are no infinite loop
            if outermost_name == original_form:
                hasChange = False
        api_object = {}
        api_new_name = name_split[0]
        name_split.pop(0)
        for part in name_split:
            api_new_name = api_new_name + "." + part

        api_object["name"] = api_new_name
        api_object["key"] = keywords
        api_object["line_no"] = node.lineno
        api_object["code"] = unparse(node)
        self.return_list.append(api_object)

def separate_api_parameter(node):
    # Loop through the given node from assignment to get all the API Call and keyword
    api_name = getName(node)
    if api_name is None:
        # Special processing if none
        return unparse(node), []
    api_keywords = []
    api_keywords.extend(getKeywordArguments(node))
    scope_list = recurseScope(node)
    for scope in scope_list:
        if scope is not None and getName(scope) is not None:
            api_keywords.extend(getKeywordArguments(scope))
            api_name = getName(scope) + "." + api_name
    separated_signature = api_name + "#"
    last_element = api_keywords[:-1]
    for key in api_keywords:
        separated_signature += key
        if key != last_element:
            separated_signature += ", "
    return api_name, api_keywords

# Tree is the AST of the complete file
def process_api_format(tree, api_name):
    assignmentVisitor = AssignmentVisitor(api_name)
    assignmentVisitor.visit(tree)

    importVisitor = ImportVisitor()
    importVisitor.visit(tree)

    fromImportVisitor = FromImportVisitor()
    fromImportVisitor.visit(tree)

    assign_dict = assignmentVisitor.assignment_dictionary
    import_dict = importVisitor.import_dictionary
    from_import_dict = fromImportVisitor.from_import_dict

    api_formatter_visitor = ApiFormatterVisitor(import_dict, from_import_dict, assign_dict, api_name)
    api_formatter_visitor.visit(tree)

    list_api = api_formatter_visitor.return_list
    return list_api
