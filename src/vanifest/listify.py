import os
from pathlib import Path
import sys
import subprocess
import re
from jinja2 import Environment, FileSystemLoader
import getpass
import argparse

from my_tools.logging import get_timelog, get_filelog

USER = getpass.getuser()
BASE_PATH = Path('~/.vanifest').expanduser()
DATA_PATH = BASE_PATH / 'data'
REMOTE_REPO_PATH = 'https://github.com/opi9a/vanifest.git/'

log_path = Path(BASE_PATH, 'logs', 'listify.log.txt')
log = get_filelog(logfile_path=log_path)


"""
Script and functions for generating lists from appropriately formatted files,
and publishing them on www.opi9a.github.io/vanifest

Usage: python listify.py <filename to listify>

Pass a filepath with a list.  This is ordinarily a .wiki file, and vim has an 
alias automatically running the script for the file being edited (<leader>p).

Only formatting requirement for the input file is that headings are identified
with hashes. More hashes more headings.  Other lines considered list items.

eg file contents

    # groceries
    ## fruit
    apples
    pears
    ## meat
    pig
    duck
    # clothes
    hose

The resulting html is responsive with greying out items, collapsing
categories etc.
"""

def push_to_git(file_to_push):
    """
    Runs all the git commands to add the file, commit and push it to
    the vanifest repo.

    To sort credentials may need to run this first (or from bash)
    # subprocess.run(['git', 'config', 'credential.helper', 'store'])
    """
    print('going to push file at', file_to_push)
    init_dir = os.getcwd()
    os.chdir(DATA_PATH)
    commit_msg = 'pushing ' + str(file_to_push)
    print('commit msg', commit_msg)

    if not '.git' in [x.name for x in DATA_PATH.iterdir()]:
        raise FileNotFoundError('Cannot find .git in ', DATA_PATH)

    with open('_git_output_redirect.txt', 'w') as fp:
        subprocess.run(['git', 'add', file_to_push], stdout=fp)
        subprocess.run(['git', 'commit', file_to_push, '-m', commit_msg], stdout=fp)
        subprocess.run(['git', 'push', 'origin', 'master'], stdout=fp)

    os.chdir(init_dir)


TICK_RE = re.compile(r"\W+x\W*", re.IGNORECASE)

def make_html(in_path, template_path=None, out_path=None,
             name=None, write_out=True, return_items=False):
    """Generates an html file ticklist from an input text file.

    Input format should use "# " to denote headings, 
    with level dictated by number of # characters. 

    Output file automatically concocted from input (-> .html) unless specified
    """

    log.info('making html from ' + in_path)
    log.info(' - out_path passed ' + str(out_path))


    if template_path is None:
        template_path = str(Path(DATA_PATH, 'template.html'))

    if out_path is None:
        out_filename = os.path.basename(in_path).split('.')[0] + '.html'
        out_path = Path(DATA_PATH, out_filename)
        log.info('assigned out_path ' + str(out_path))

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

            # see if item has been pre-ticked, and remove any tickboxes
            ticked = True if TICK_RE.findall(l) else False
            text = re.sub(TICK_RE, "", text)
            text = re.sub("\[ \]", "", text)

            # compose the item dict
            item = {
                'level': level,
                'text': text,
                'closures': closures,
                'count': None,
                'ticked': ticked,
            }

            log.info(" ".join(['level:', str(level).rjust(5), 'text:', text,
                               'ticked', str(ticked)]))
            items.append(item)

    out = get_counts(items)

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

    if return_items:
        return items
    else:
        return out_path



def get_counts(table, i=None):
    """
    Key subfunction used by make_html(), does the tricky bit of (recursively) 
    working out the tree structure of the list, and reflecting that in html.

    Each level:
        first find:
            a = number of direct elem children (i.e. not subheadings)
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
            # increment elements if not already ticked
            if at_current_level and not table[i+j]['ticked']:
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


def f_exists(file_path):
    """
    Helper for argparse
    """
    if os.path.exists(file_path):
        return file_path
    raise argparse.ArgumentTypeError(f'file {file_path} not found')
    


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='make a dynamic html from a '
                                                 'list file and push to github')
    parser.add_argument('list_file_path', type=f_exists)
    parser.add_argument('-t', '--template-path', type=f_exists, default=None)
    parser.add_argument('-o', '--outfile-path', type=f_exists, default=None)
    parser.add_argument('-n', '--name', type=str, default=None)
    parser.add_argument('-w', '--write_out', action='store_false',
                                           help='no write-out')

    args = parser.parse_args()

    out_path = make_html(args.list_file_path,
                         template_path=args.template_path,
                         out_path=args.outfile_path,
                         name=args.name,
                         write_out=args.write_out)

    out_filename = os.path.basename(out_path)
    push_to_git(out_filename)

    url_base = 'https://opi9a.github.io/vanifest/'
    url = url_base + out_filename
    print('url:', url)
