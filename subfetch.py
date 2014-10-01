#!/usr/bin/python
#
# $id: subfetch.py,v 1.0.0 2014/01/29 20:15:20 mteixeir Exp $
# Copyright (C) 2014
#
# Last Modified: 2014/10/01 17:40:02

import re, os, sys, argparse, struct, xmlrpclib, gzip, base64, StringIO, stat

server = None
token = None
verbose = None
target = None

def hashAndSizeFile(filename): 
        try:
            longlongformat = 'Q'  # unsigned long long little endian
            bytesize = struct.calcsize(longlongformat)
            format= "<%d%s" % (65536//bytesize, longlongformat)

            f = open(filename, "rb")

            filesize = os.fstat(f.fileno()).st_size
            hash = filesize

            if filesize < 65536 * 2:
               return "SizeError"

            buffer= f.read(65536)
            longlongs= struct.unpack(format, buffer)
            hash+= sum(longlongs)

            f.seek(-65536, os.SEEK_END) # size is always > 131072
            buffer= f.read(65536)
            longlongs= struct.unpack(format, buffer)
            hash+= sum(longlongs)
            hash&= 0xFFFFFFFFFFFFFFFF

            f.close()
            returnedhash =  "%016x" % hash
            return returnedhash

        except(IOError):
            return "IOError"

def BaseToFile(base_data, filename):
  compressedstream = base64.decodestring(base_data)
  gzipper = gzip.GzipFile(fileobj=StringIO.StringIO(compressedstream))
  s = gzipper.read()
  gzipper.close()
  subtitle_file = file(filename,'wb')
  subtitle_file.write(s)
  subtitle_file.close()

def main(target, recursive):
  mode = os.stat(target).st_mode
  if not os.access(target, os.R_OK):
    print("Unable to access target: %s" % target)
  else:
    osd_login()
    if stat.S_ISDIR(mode):
      if recursive:
        for root, dirs, files in os.walk(target):
          iterate_dir(root, files)
      else:
        iterate_dir(target)
    elif stat.S_ISREG(mode):
      fetch_file_sub(target)
    else:
      print("Invalid target: %s" % target)
      server.LogOut()
      sys.exit(1)
    server.LogOut()

def osd_login():
  global server, token
  if(verbose): print("Attempting OSD login...")
  server = xmlrpclib.Server("http://api.opensubtitles.org/xml-rpc")
  response = server.LogIn("", "", "en", "OS Test User Agent")
  if(response["status"] != "200 OK"):
    print("Error contacting opensubtitles.org: %s" % response["status"])
    sys.exit(1)
  token = response["token"]
  if(verbose): print("OSD login success [%s]" % token)

def fetch_file_sub(video_file):
  if(not re.match(".*\\.(mkv|MKV|avi|AVI|mp4|MP4)$", video_file)):
    print("Not a valid video file: %s" % video_file)
    sys.exit(1)
  elif(os.path.exists("%s.srt" % video_file[:-4])):
    print("Video already has a subtitle: %s" % video_file)
    sys.exit(0)

  file_hash = hashAndSizeFile(video_file)
  file_size = str(os.path.getsize(video_file))
  if(verbose): print("File %s hash is %s" % (os.path.basename(video_file), file_hash))
  if(verbose): print("Searching subtitle for %s" % file_hash)
  r_search = server.SearchSubtitles(token, [{"sublanguageid": "pob", "moviehash": file_hash, "moviebytesize": file_size}])
  if(not r_search["data"]):
    print("Subtitles not found for %s" % os.path.basename(video_file))
  else:
    print("Downloading subtitle ID %s" % r_search["data"][0]["IDSubtitleFile"])
    r_download = server.DownloadSubtitles(token, [r_search["data"][0]["IDSubtitleFile"]])
    BaseToFile(r_download["data"][0]["data"].encode('ascii'), "%s.srt" % video_file[:-4])

def iterate_dir(topdir, files=None):
  videos = []
  subs = []
  if(verbose): print("Scanning for files in %s..." % (topdir))
  filenames = files if files else os.listdir(topdir)
  for f in filenames:
    if(re.match(".*\\.(mkv|MKV|avi|AVI|mp4|MP4)$", f)):
      videos.append(f)
    elif(re.match(".*\\.(sub|srt)$", f)):
      subs.append(f[:-4])
  if(verbose): print("Found %s videos and %s subs." % (len(videos), len(subs)))

  for v in videos:
    if(v[:-4] not in subs):
      if(verbose): print("File %s doesn't have a sub, need to fetch..." % v)
      fetch_file_sub(os.path.join(topdir, v))


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-t", "--target", help="Video file or Directory to scan (no wildcards ATM)")
  parser.add_argument("-r", "--recursive", action="store_true", help="Search recursively in a directory")
  parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed information")
  args = parser.parse_args()
  verbose = args.verbose
  target = args.target
  recursive = args.recursive
  if(not target):
    print("Please specify a target to scan.")
    sys.exit(1)
  main(target, recursive)
