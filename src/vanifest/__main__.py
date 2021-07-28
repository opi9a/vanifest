import argparse
import os
import sys

from .listify import make_html, push_to_git, f_exists

def main():
    """
    x
    """

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
    print('out_filename', out_filename)
    push_to_git(out_filename)

    url_base = 'https://opi9a.github.io/vanifest/'
    url = url_base + out_filename
    print('url:', url)



if __name__ == '__main__':
    sys.exit(main())


