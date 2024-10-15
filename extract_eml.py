#!/usr/bin/env python
# Source: https://gist.github.com/urschrei/5258588
import glob
import os
import email
from email import policy
from multiprocessing import Pool

EXTENSION = 'eml'


def extract(filename):
    """
    Try to extract the attachments from all files in cwd
    """
    # ensure that an output dir exists
    od = 'output'
    os.path.exists(od) or os.makedirs(od)
    output_count = 0
    try:
        with open(filename, 'r') as f:
            msg = email.message_from_file(f, policy=policy.default)
            for attachment in msg.iter_attachments():
                try:
                    output_filename = attachment.get_filename()
                except AttributeError:
                    print('Got string instead of filename for %s. Skipping.' % f.name)
                    continue
                # If no attachments are found, skip this file
                if output_filename:
                    print(f'writing to {output_filename}')
                    with open(os.path.join(od, output_filename), 'wb') as of:
                        try:
                            of.write(attachment.get_payload(decode=True))
                            output_count += 1
                        except TypeError:
                            print("Couldn't get payload for %s" % output_filename)
            if output_count == 0:
                print('No attachment found for file %s!' % f.name)
    # this should catch read and write errors
    except IOError:
        print('Problem with %s or one of its attachments!' % f.name)
    return 1, output_count


def extract_all():
    # let's do this in parallel, using cpu count as number of threads
    pool = Pool(None)
    files = list(glob.iglob('*.%s' % EXTENSION))
    if not files:
        print('No files found')
        return

    print(f'Found {len(files)} files')
    res = pool.map(extract, files)
    pool.close()
    pool.join()
    # 2-element list holding number of files, number of attachments
    numfiles = [sum(i) for i in zip(*res, strict=False)]
    print('Done: Processed {} files with {} attachments.'.format(*numfiles))


if __name__ == '__main__':
    extract_all()
