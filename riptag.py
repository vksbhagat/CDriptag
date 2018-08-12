#!/usr/bin/python3

import os, sys
import subprocess
from argparse import ArgumentParser
import libdiscid
import musicbrainzngs as mb
import requests
import json
from getpass import getpass
      
parser = ArgumentParser()
parser.add_argument('-f', '--flac', action='store_true', dest='flac',
                    default=False, help='Rip to FLAC format')
parser.add_argument('-w', '--wav', action='store_true', dest='wav',
                    default=False, help='Rip to WAV format')
parser.add_argument('-o', '--ogg', action='store_true', dest='ogg',
                    default=False, help='Rip to Ogg Vorbis format')
options = parser.parse_args()

# Set up output varieties
if options.wav + options.ogg + options.flac > 1:
    raise parser.error("Only one of -f, -o, -w please")
if options.wav:
    fmt = 'wav'
    encoding = 'wavenc'
elif options.flac:
    fmt = 'flac'
    encoding = 'flacenc'
    from mutagen.flac import FLAC as audiofile
elif options.ogg:
    fmt = 'oga'
    quality = 'quality=0.3'
    encoding = 'vorbisenc {} ! oggmux'.format(quality)
    from mutagen.oggvorbis import OggVorbis as audiofile

# Get MusicBrainz info
this_disc = libdiscid.read(libdiscid.default_device())
mb.set_useragent(app='get-contents', version='0.1')
mb.auth(u=input('Musicbrainz username: '), p=getpass())

release = mb.get_releases_by_discid(this_disc.id, includes=['artists',
                                                            'recordings'])
if release.get('disc'):
    this_release=release['disc']['release-list'][0]

    album = this_release['title']
    artist = this_release['artist-credit'][0]['artist']['name']
    year = this_release['date'].split('-')[0]

    for medium in this_release['medium-list']:
        for disc in medium['disc-list']:
            if disc['id'] == this_disc.id:
                tracks = medium['track-list']
                break

    # We assume here the disc was found. If you see this:
    #   NameError: name 'tracks' is not defined
    # ...then the CD doesn't appear in MusicBrainz and can't be
    # tagged.  Use your MusicBrainz account to create a release for
    # the CD and then try again.
            
    # Get cover art to cover.jpg
    if this_release['cover-art-archive']['artwork'] == 'true':
        url = 'http://coverartarchive.org/release/' + this_release['id']
        art = json.loads(requests.get(url, allow_redirects=True).content)
        for image in art['images']:
            if image['front'] == True:
                cover = requests.get(image['image'], allow_redirects=True)
                fname = '{0} - {1}.jpg'.format(artist, album)
                print('Saved cover art as {}'.format(fname))
                f = open(fname, 'wb')
                f.write(cover.content)
                f.close()
                break

for trackn in range(len(tracks)):
    track = tracks[trackn]['recording']['title']

    # Output file name based on MusicBrainz values
    outfname = '{:02} - {}.{}'.format(trackn+1, track, fmt).replace('/', '-')

    print('Ripping track {}...'.format(outfname))
    cmd = 'gst-launch-1.0 cdiocddasrc track={} ! '.format(trackn+1) + \
            'audioconvert ! {} ! '.format(encoding) + \
            'filesink location="{}"'.format(outfname)
    msgs = subprocess.getoutput(cmd)

    if not options.wav:
        audio = audiofile(outfname)
        print('Tagging track {}...'.format(outfname))
        audio['TITLE'] = track
        audio['TRACKNUMBER'] = str(trackn+1)
        audio['ARTIST'] = artist
        audio['ALBUM'] = album
        audio['DATE'] = year
        audio.save()
