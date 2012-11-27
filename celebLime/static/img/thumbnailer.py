import os
import sys
import string
import re
from optparse import OptionParser

import Image

class thumbnailer(object):
    """[-w WIDTH] [-h HEIGHT] [SOURCEDIR]... [-d THUMBNAILDIR]"""
    
    def __init__(self, u_src=".", u_dest="./thumbnails", u_width=500, u_height=500):
        self.src = list()
        for t_src in u_src:
            if os.path.isdir(t_src):
                self.src.append(t_src)
            else:
                self.usage("Source directory " + t_src + " does not exist!", self.__doc__)
        
        if os.path.isdir(u_dest):
            self.dest = u_dest
        else:
            try:
                os.mkdir(u_dest)
                self.dest = u_dest
            except IOError:
                self.usage("Destination directory does not exist and could not be created!", self.__doc__)
        
        if u_width > 0:
            self.width = u_width
        else:
            self.usage("Invalid width!", self.__doc__)
        
        if u_height > 0:
            self.height = u_height
        else:
            self.usage("Invalid height!", self.__doc__)
    
    def usage(self, err_msg = None, help_text = "[options]"):
        if err_msg:
            print >> sys.stderr, "Error: %s" % (err_msg)
            print >> sys.stderr, "Usage: %s %s" % (os.path.basename(sys.argv[0]), help_text)
            sys.exit(1)
    
    def run(self):
        for t_src in self.src:
            for src_file in os.listdir(t_src):
                src_file = t_src + os.sep + src_file
                if os.path.isfile(src_file) and re.search("\\.jpe?g$", src_file, re.IGNORECASE):
                    try:
                        img = Image.open(src_file)
                        img.thumbnail((self.width, self.height), Image.ANTIALIAS)
                        img.save(self.dest + os.sep + os.path.basename(src_file), "JPEG")
                    except IOError, e:
                        print >> sys.stderr, "Cannot create thumbnail for ", src_file, ": ", e
                else:
                    print >> sys.stderr, src_file + " is not a valid jpg file"

parser = OptionParser(usage="Usage: %prog " + thumbnailer.__doc__, conflict_handler="resolve")
parser.add_option("-w", "--width", type="int", dest="width", default=500, help="Set the max width of the thumbnails, default: %default")
parser.add_option("-h", "--height", type="int", dest="height", default=500, help="Set the max height of the thumbnails, default: %default")
parser.add_option("-d", "--dest", type="string", dest="dest", default="./thumbnails", help="Set the directory where the thumbnails are stored, default: %default")
(options, args) = parser.parse_args()

if not args:
    args.append(".")

thumb = thumbnailer(args, options.dest, options.width, options.height)
thumb.run();
