import os
import json

def log_item(item):
    print(item)

def print_directory(switch_0, path, tabs=0):
    files.log_item("Files on filesystem:")
    files.log_item("====================")
    for file in os.listdir(path):
        stats = os.stat(path + "/" + file)
        filesize = stats[6]
        isdir = stats[0] & 0x4000

        if filesize < 1000:
            sizestr = str(filesize) + " by"
        elif filesize < 1000000:
            sizestr = "%0.1f KB" % (filesize / 1000)
        else:
            sizestr = "%0.1f MB" % (filesize / 1000000)

        prettyfiles.log_itemname = ""
        for _ in range(tabs):
            prettyfiles.log_itemname += "   "
        prettyfiles.log_itemname += file
        if isdir:
            prettyfiles.log_itemname += "/"
        files.log_item('{0:<40} Size: {1:>10}'.format(prettyfiles.log_itemname, sizestr))

        # recursively files.log_item directory contents
        if isdir:
            files.log_item_directory(path + "/" + file, tabs + 1)
            
def write_file_lines(file_name, lines):
    with open(file_name, "w") as f:
        for line in lines:
            f.write(line + "\n")

def read_file_lines(file_name):
    with open(file_name, "r") as f:
        lines = f.readlines()
        output_lines = [] 
        for line in lines:
            output_lines.append(line.strip())
        return output_lines
    
def write_file_line(file_name, line):
    with open(file_name, "w") as f:
        f.write(line + "\n")

def read_file_line(file_name):
    with open(file_name, "r") as f:
        line = f.read()
        output_line=line.strip()
        return output_line
    
def json_stringify(python_dictionary):
    json_string = json.dumps(python_dictionary)
    return json_string

def json_parse(my_object):
    python_dictionary = json.loads(my_object)
    return python_dictionary

def write_json_file(file_name, python_dictionary):
    json_string=json_stringify(python_dictionary)
    write_file_line(file_name, json_string)
    
def read_json_file(file_name):
    json_string=read_file_line(file_name)
    python_dictionary=json_parse(json_string)
    return python_dictionary
