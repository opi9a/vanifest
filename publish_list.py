import os
import sys
import subprocess
from jinja2 import Environment, FileSystemLoader
import getpass

from mylogger import get_timelog

USER = getpass.getuser()
BASE_PATH = os.path.join('/home', USER, 'shared/projects/vanifest')

log_path = os.path.join(BASE_PATH, 'logs', 'publish_list.log.txt')
log = get_timelog(log_path)

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
    init_dir = os.getcwd()
    os.chdir(BASE_PATH)
    commit_msg = 'pushing ' + file_to_push
    subprocess.run(['git', 'add', file_to_push])
    subprocess.run(['git', 'commit', file_to_push, '-m', '"test"'])
    subprocess.run(['git', 'push', 'origin', 'master'])

    os.chdir(init_dir)


def make_html(in_path, template_file='template.html', out_path=None,
             name=None, write_out=True):
    """Generates an html file ticklist.

    Input format should use "# " to denote headings, 
    with level dictated by number of # characters. 
    """

    log.info('making html from ' + in_path)
    log.info(' - out_path passed ' + str(out_path))

    template_path = os.path.join(BASE_PATH, template_file)

    if out_path is None:
        out_filename = os.path.basename(in_path).split('.')[0] + '.html'
        out_path = os.path.join(BASE_PATH, out_filename)
        log.info('assigned out_path ' + out_path)

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

            item = {
                'level': level,
                'text': text,
                'closures': closures,
                'count': None,
            }

            log.info(" ".join(['level:', str(level).rjust(5), 'text:', text]))
            items.append(item)

    out = get_counts(items)


    pwd = os.getcwd()
    env = Environment(loader=FileSystemLoader('/'))
    
    with open(out_path, 'w') as f:
        f.write(env.get_template(template_path).render(
            items = items,
            open_divs = len(open_divs),
            name = name,
        ))

    lev_counts = {}

    for item in items:
        lev_counts[item['level']] = lev_counts.setdefault(item['level'], 0) + 1

    max_level = max([k for k in lev_counts.keys() if k is not None])
    no_levels = sum([lev_counts[x] for x in lev_counts if x is not None])

    print(f'Listed {lev_counts[None]} items in {no_levels} categories, max level of {max_level}')

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
    # log.info(f'\nLooking at row {i}, {curr_text}')
    # log.info(f'-- current level is {curr_level}')
    # log.info(f'-- current count is {table[i]["count"]}')

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
        # log.info(" ".join(['looking forward to row', str(j), str(i)]))

        new_level = table[i + j]['level']
        # log.info(' '.join(['---- level of forward row is', str(new_level)]))

        if new_level is None:
            if at_current_level:
                elements += 1
                # log.info(' '.join(['---- incrementing elements to',
                #                    str(elements)]))

        elif new_level == curr_level + 1:
            sub_heads.append(i + j)
            # log.info(' '.join(['---- appending to sub_heads, now',
            #                    str(sub_heads)]))
            at_current_level = False

        elif new_level <= curr_level:
            # means found a higher level
            # log.info(' '.join(['---- exiting loop']))
            break

    # log.info(f'found {elements} elements, and sub heads {sub_heads} to look at')
    subh_sum = sum([get_counts(table, x) for x in sub_heads])
    # log.info(f'after calling get_counts on sub_heads for {curr_text},'
             # f' have a sum of {subh_sum}')
    out = elements + subh_sum
    # log.info(f'total for {curr_text} is therefore ' + str(out))
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
            out_filename = os.path.basename(out_path)
            push_to_git(out_filename)

            url_base = 'https://opi9a.github.io/vanifest/'
            url = url_base + out_filename
            print('url:', url)
