import os
import sys
import subprocess
from jinja2 import Environment, FileSystemLoader
import getpass

USER = getpass.getuser()
BASE_PATH = os.path.join('/home', USER, 'shared/projects/vanifest')
"""
Spec:
 - on click, grey out or something:
   - just jquery?
 - use card rather than list?
"""

def push_to_git(file_to_push):
    """
    May need to run this first before a session (or from bash)
    # subprocess.run(['git', 'config', 'credential.helper', 'store'])
    """
    print('will try pushin', file_to_push)
    commit_msg = 'pushing ' + file_to_push
    subprocess.run(['git', 'add', file_to_push])
    subprocess.run(['git', 'commit', file_to_push, '-m', '"test"'])
    subprocess.run(['git', 'push', 'origin', 'master'])


def make_html(in_path, template_path='template.html', out_path=None,
             name=None):
    """Generates an html file ticklist.

    Input format should use "# " to denote headings, 
    with level dictated by number of # characters. 
    """

    if out_path is None:
        out_filename = os.path.basename(in_path).split('.')[0] + '.html'
        out_path = os.path.join(BASE_PATH, out_filename)
        print('assigned outpath', out_path)

    if name is None:
        name = os.path.basename(in_path)
        name = name.split('.')[0].replace('_', ' ')

    items = [{
                'level': 0,
                'text': name,
                'closures': 0,
                'count': None,
            }]

    open_divs = [0]

    with open(in_path) as f:
        for l in [line for line in f if len(line) > 2]:

            # default level corresponds with element (not heading)
            level = None

            # parse the line
            tag, text = l.split()[0], " ".join(l.split()[1:])
            if tag[0] == '#':
                level = len(tag)

            # the template file will generate a <div> to enclose
            # each block following a heading (including subheadings below)
            # Need to supply information here about the number of open divs
            # that need to be closed when creating each new heading.
            # ..so register a closure for each open div >= current one,
            # Eg if there were already open divs created with headings at
            # levels 1, 2, 4 and a new level 2 was being created, would want
            # to close 4 and 2 (and create a new 2 - done in the html template)
            last = None
            closures = 0
            if level is not None:
                # examine end of open divs
                # if >= level, pop it off and increment closures
                while open_divs[-1] >= level:
                    last = open_divs.pop()
                    closures += 1
                open_divs.append(level)

            items.append({
                'level': level,
                'text': text,
                'closures': closures,
                'count': None,
            })

    get_counts(items)

    pwd = os.getcwd()
    env = Environment(loader=FileSystemLoader(pwd))
    
    with open(out_path, 'w') as f:
        f.write(env.get_template(template_path).render(
            items = items,
            open_divs = len(open_divs),
            name = name,
        ))

    return out_path


def get_counts(table, i=None):
    """Adds a field to each subheading row of input table with the
    number of elements underneath that subheading.

    Each level:
        first find:
            a = number of direct elem children
            b = any subheadings
        return a + sum([get_counts(x) for x in b])
        write this sum into the field 'counts' for present row
    """

    # initialise if required, if we are at first row
    if i is None:
        i = 0

    curr_level = table[i]['level']
    curr_text = table[i]['text']
    # print(f'\nLooking at row {i}, {curr_text}')
    # print(f'-- current level is {curr_level}')
    # print(f'-- current count is {table[i]["count"]}')

    # count direct elements and get list of subheaad
    # --> look forward until next heading at same or above level
    j = 0
    elements = 0
    sub_heads = []

    # need to make it ignore sublevels
    # and only append next level down
    at_current_level = True
    while j < (len(table)- i) - 1:
        # get all levels 1 below
        # get all elements before a sublevel

        j += 1
        # print('\n---- looking forward to row', j + i)

        new_level = table[i + j]['level']
        # print('---- level of forward row is', new_level)

        if new_level is None:
            if at_current_level:
                elements += 1
                # print('---- incrementing elements to', elements)

        elif new_level == curr_level + 1:
            sub_heads.append(i + j)
            # print('---- appending to sub_heads, now ', sub_heads)
            at_current_level = False

        elif new_level <= curr_level:
            # means found a higher level
            # print('---- exiting loop')
            break

    # print(f'found {elements} elements, and sub heads {sub_heads} to look at')
    subh_sum = sum([get_counts(table, x) for x in sub_heads])
    # print(f'after calling get_counts on sub_heads for {curr_text},'
          # f' have a sum of {subh_sum}')
    out = elements + subh_sum
    # print(f'total for {curr_text} is therefore', out)
    table[i]['count'] = out

    return out


def print_help():
    print('Usage: publish_list <md_list_path>')

if __name__ == "__main__":

    if not len(sys.argv) == 2:
        print_help()

    else:
        md_list_path = sys.argv[1] 

        if not os.path.exists(md_list_path):
            print_help()

        else:
            out_path = make_html(md_list_path)
            print(out_path)
            out_filename = os.path.basename(out_path)
            push_to_git(out_filename)
